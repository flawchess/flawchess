---
phase: quick-261119-k9s
reviewed: 2026-11-19T14:20:00Z
depth: deep
files_reviewed: 3
files_reviewed_list:
  - scripts/remote_eval_worker.py
  - tests/test_remote_eval_worker.py
  - REMOTE_WORKER.md
findings:
  critical: 0
  warning: 7
  info: 5
  total: 12
  necessity: 0
status: issues_found
---

# Quick 261119-k9s: Code Review Report (remote eval worker `--lanes`)

**Reviewed:** 2026-11-19T14:20:00Z
**Depth:** deep (no depth was passed; the ten claims to attack are cross-file, so call chains were traced into the server)
**Files Reviewed:** 3 (diff `b9a9bdefe..HEAD`)
**Status:** issues_found

Server-side paths read to attack the claims (not in the diff, no findings filed against them): `app/routers/eval_remote.py`, `app/services/eval_queue_service.py`, `app/services/blob_claim_lease.py`, `app/services/engine.py`, `app/services/eval_apply.py` (completion decision, flaw-blob apply, bestmove apply, heartbeat ordering), `app/services/eval_entry.py`, `app/services/eval_drain.py` (lease constants), `app/repositories/worker_heartbeat_repository.py`, `docker-compose.worker.yml` (heartbeat-file reader).

## Summary

No data-corrupting defect was found. The lanes=1 path is behaviorally identical to `b9a9bdefe` as far as a branch-by-branch read can tell, and the same-worker-id analysis for rungs 1, 3, 4 and 5 holds on the server code. No finding is a blocker for the default (`--lanes 1`) or for a first prod run at `--lanes 3`.

What does not hold is the set of timing claims around the shared engine pool:

- The pool is one FIFO queue with no priority. Entry-ply batches (server lease 20 s) and explicit tier-1 jobs (server lease 120 s) now wait behind sibling lanes' backfill passes. Both TTLs were sized for a worker that gives a leased game the whole pool. This is the main reason not to go to 7 lanes yet (WR-01, WR-02).
- The cap formula is not an upper bound for the real cycle shape and breaks at the hard cap it is supposed to justify (WR-03).
- `idle_sleep x lanes` creates a watchdog false positive that lanes=1 does not have. Reproduced by execution (WR-04).
- The sizing hint (one lane per 4 engines) is not derived from the plan's own measurement (WR-05).
- Two production-relevant mutations survive the full test file, and one new test races the wall clock (WR-06, WR-07).

Runtime evidence in this review came from scratch plugins and scratch tests kept outside the repo. No source or test file was edited, the worker script was never run, and only `tests/test_remote_eval_worker.py` was executed (serially).

### Verdict per claim

| # | Claim | Result |
|---|-------|--------|
| 1 | Rung 1 safe under one worker id | Not broken for correctness. `_claim_queued_job` claims one row per call, completion and release are keyed on `job_id` with a `status='leased'` guard, the sweep is owner-agnostic. Timing side effect: WR-02. |
| 2 | Rungs 3 and 5 as safe as two workers | Not broken. No per-worker-id state on either rung; `/bestmove-lease` does not even read the id. Only `/entry-submit` keys on the id. The `worker_heartbeats` upsert is the last statement before commit in all four submit transactions, so same-id lanes add a commit-length row-lock wait and no new deadlock cycle. No rate limiter on these routes. Cost only: more duplicate draws on the two lease-less lotteries. |
| 3 | Rung 4 lease safe with one owner, several games | Not broken in practice. One theoretical hole, unreachable: IN-02. |
| 4 | Entry lock held lease through submit on every path | Not broken on the worker side: `async with` covers 204, exception, cancellation and dry-run, and one lock across both backends is correct (cross-backend serialization is needless but harmless, the two backends have separate databases). Residual, pre-existing and not a regression: IN-01. |
| 5 | EnginePool safe for concurrent gathers | Not broken. The pool has no single-caller state (no counters, no pool-level restart); `_restart_worker` only touches the slot its caller still holds; the per-search timeout starts after acquisition (`engine.py:642` then `:659`); a cancelled gather finishes only after its children have run their `finally`, so `pool.stop()` never sees an in-flight search. Missing priority is the issue, not safety: WR-01, WR-02. |
| 6 | Cap math | Broken as a bound: WR-03. Server TTLs a slower cycle can exceed: WR-01 (20 s), WR-02 (120 s). `BLOB_LEASE_TTL_S` stays valid. |
| 7 | Watchdog | A healthy lane cannot mask a wedged one (min over slots), and the file rule is sound: the file's age is never greater than the in-memory minimum's age, so the Docker mtime check cannot go stale before the watchdog fires. False positive found: WR-04. Entry-lock waits and failure back-off do not reach 720 s at 7 lanes or fewer. |
| 8 | lanes=1 equivalence | Not broken. All four branches match old and new on record, capture, sleep, re-raise and control flow. Note that the tests would not catch a difference in streak bookkeeping: WR-06(b). |
| 9 | Shared-client effects | Not broken: httpx defaults are 100 connections and 20 keep-alive (checked on the installed version), the ContextVar label stays inside lane tasks, shutdown order is lanes, then clients, then pool. Two side notes: IN-03, IN-05. |
| 10 | Tests | Broken in three places: WR-03 (arithmetic-only test), WR-06, WR-07. |

## Warnings

### WR-01: Entry-ply lease (20 s server TTL) can expire while its evals queue behind sibling lanes; the batch is then silently discarded

**File:** `scripts/remote_eval_worker.py:1148-1157` (rung 2 under the lock), `:643-670` (`_eval_entry_positions`), `app/services/engine.py:529,642` (one FIFO queue), `app/services/eval_drain.py:275-278` (`ENTRY_LEASE_TTL_SECONDS = 20`, sized as "seconds of work ... divided by N cores"), `app/routers/eval_remote.py:746,763-764`
**Issue:** The lock serializes entry leases across lanes, but the entry batch's depth-15 searches go to the tail of the same FIFO engine queue as every other lane's 1M-node passes. The server's 20 s lease clock starts at `/entry-lease`. If the lane's submit lands after it, the guard `entry_eval_lease_expiry > now()` matches nothing, the handler returns `stamped_count=0` and all evals are dropped. The worker logs `Entry-submit complete: game_ids=[], stamped_count=0` as if it had succeeded.

Scenario: entry backlog crosses 300 while six sibling lanes are mid-cycle on tier-3 games (about 80 positions each at about 1.2 s): roughly 6 x 96 engine-seconds / 28 engines, about 20 s of queue ahead of the entry batch, plus two HTTP round trips. The batch expires. With rung 1 empty this costs about one batch per backlog episode, because the other lanes then converge on the lock and the pool empties. While tier-1 jobs keep flowing it repeats on every batch, and each wasted batch also hides 50 games from the server pool for 20 s. At 3 lanes the same estimate is about 7 s, inside the TTL.

K-03's "today's throughput and no regression" is therefore false whenever other lanes hold engine work. No data is corrupted; the games are re-leased.
**Confidence:** Queue order, TTL and the discard path verified by reading. The seconds are estimates from the plan's single measurement, not measured.
**Fix:** Start the lease clock with a free pool. After taking the lock, stop siblings from starting new engine passes and wait for in-flight ones to drain before calling `/entry-lease`:
```python
async with entry_lock:
    pool_gate.clear()              # siblings await pool_gate.wait() before each gather
    await in_flight_passes.wait_zero()
    try:
        entry_outcome = await _try_entry_rung(...)
    finally:
        pool_gate.set()
```
Alternatively give engine acquisition a priority (entry, then explicit, then backfill), see WR-02. At minimum, log a warning when `/entry-submit` answers `stamped_count == 0` for a non-empty submit.

### WR-02: Explicit tier-1 jobs queue behind backfill passes (priority inversion); the 120 s job lease can now expire on a fast box

**File:** `scripts/remote_eval_worker.py:1138-1145` (rung 1), `:600-629` (`_eval_atomic_game`: three gathers plus a retry gather after each), `app/services/engine.py:529,642`, `app/services/eval_queue_service.py:86-89` (`LEASE_TTL_SECONDS = 120`), `:203-222` (sweep)
**Issue:** At lanes=1 a tier-1 game (a user's explicit request) gets all engines for its whole cycle. With lanes, each of its three passes joins the tail of the shared queue behind whatever the other lanes have queued. Once the pool is saturated, which is the purpose of the feature, the wall clock of every game is roughly L times its single-lane search time. The ladder gives tier-1 priority at lease time and the pool then takes it away at eval time.

Scenario at `--workers 28 --lanes 7`, taking the plan's 84 engine-seconds per tier-4 game: the steady-state queue holds about 17 s of work, a tier-1 game pays that three times, so about 55 s against about 6 s today. A long tier-1 game (about twice typical size) passes 120 s, `_sweep_expired_leases` returns the job to pending, and a sibling lane or another worker evaluates the same game again. The second submit is harmless (`status='leased'` guard, idempotent writes), so the cost is user-visible latency plus duplicated engine time. With 7 lanes this box also polls rung 1 about seven times as often, so it wins more tier-1 jobs and then serves them slower.
**Confidence:** Mechanism verified by reading. The magnitude depends on how saturated the pool is; it tends to zero if engines are idle.
**Fix:** Worker-only option: put a priority gate in front of the pool calls (an `asyncio.PriorityQueue` of W tokens, priority = rung), so explicit and entry work overtake queued backfill positions. Until then keep prod at 3 lanes and compare tier-1 lease-to-submit time before and after.

### WR-03: The cap derivation is not an upper bound for the real cycle, and it fails at the hard cap it is meant to justify

**File:** `scripts/remote_eval_worker.py:93-98`, `:184-188`, `:1787-1793`; `tests/test_remote_eval_worker.py:2215-2224`
**Issue:** `((2L-1) x 500 s + 120 s) / W` models one 100-position pass plus one retry pass. Against the code:

1. An atomic cycle (rungs 1 and 3) issues three gathers (`_eval_positions`, `_eval_atomic_blob_nodes`, `_eval_targeted_second_best`) and `_retry_timed_out` adds a gather after each, so up to six queue entries, each of which can wait behind one pass from every other lane. In the comment's own all-timeout model that is about `(6 x (L-1) x 400..500 + own) / W`: about 250 s at W=28, L=3; 550 to 680 s at L=7; 1100 to 1400 s at L=14. L=14 is accepted by `parse_args` (and asserted accepted by `test_lanes_within_cap_accepted`) and exceeds `STALL_THRESHOLD_S`.
2. "100 positions" is not a limit. `/atomic-lease` and `/flaw-blob-lease` both return up to `MAX_SUBMIT_EVALS = 1024` positions (`eval_remote.py:574,942`). This was already true at lanes=1; lanes multiply it.
3. HTTP time (up to 30 s per call) and entry-lock waits are outside the formula.
4. "exactly when L <= ceil(W/2)" is false as arithmetic: at W=28 the formula stays under 620 s up to L=17. The cap is only sufficient under the two-queue-entry model, not equivalent to it.

At the intended `--workers 28 --lanes 3..7` the margin is real: realistic cycles are about 55 to 230 s. The defect is that the hard cap, the comments and the test claim a guarantee that does not exist. The test hard-codes `500.0` and re-derives `ceil(W/2)`, so it checks algebra against the constant under test, never queueing behavior. It would still pass if the pool were LIFO or the cycle had ten passes.
**Fix:** Either lower the hard cap to what the multi-pass model supports (about `ceil(W/4)`, which is the current recommendation anyway), or keep it and reword the comments to "sufficient under a one-pass-plus-retry model; atomic cycles and long games are not bounded by it". Replace the literal with `_NODES_TIMEOUT_S` and the real pass count, or drop the test.

### WR-04: `--idle-sleep` multiplied by lanes makes the watchdog kill a healthy idle worker in a loop

**File:** `scripts/remote_eval_worker.py:1540-1547` (`_lane_schedule`), `:1565-1566` (start delay), `:1181-1184` (idle sleep inside the cycle, before the mark at `:907-908`), `:1916-1917` (only `idle_sleep > 0` is validated), `:1962` (all slots stamped before the pool starts)
**Issue:** Lane i starts after `i x idle_sleep` and its first all-204 cycle sleeps `idle_sleep x lanes` before returning, so its first mark comes at about `(i + L) x idle_sleep`; for the last lane `(2L-1) x idle_sleep`. In steady state the gap between marks is `L x idle_sleep`. Nothing ties either to `STALL_THRESHOLD_S`.

Scenario: `--idle-sleep 60 --lanes 7` on empty queues. Lane 6's first mark is due at 780 s, the watchdog fires at 720 s, `os._exit(1)`, the supervisor relaunches, and the same thing repeats every 12 minutes with a Sentry message and 28 engine respawns each time. At lanes=1 the same flag is safe up to 720 s. The safe range shrinks to `720 / (2L-1)`: about 55 s at 7 lanes, about 27 s at 14.
**Confidence:** Verified by execution at the production ratio scaled down (threshold 0.72 s, idle 0.06 s): lanes=1 no trip, lanes=7 tripped at 0.73 s, lanes=7 with idle 0.01 s no trip.
**Fix:**
```python
if (2 * args.lanes - 1) * args.idle_sleep >= STALL_THRESHOLD_S / 2:
    parser.error("--idle-sleep x lanes is too long for the stall watchdog; ...")
```
or cap the per-lane idle sleep at a constant well below the threshold.

### WR-05: The sizing hint (one lane per 4 engines, "28 -> 7") is not derived from the measurement that motivates the feature

**File:** `scripts/remote_eval_worker.py:99-100` (`RECOMMENDED_ENGINES_PER_LANE = 4`), `:27-36`, `:1841-1845`; `REMOTE_WORKER.md:43-47`
**Issue:** The plan's measurement is about 3 s searching and about 4 s HTTP per tier-4 game at 28 engines. If those 3 s use the whole pool, one lane keeps the engines busy 3/7 of the time and the pool saturates at `ceil(1 + t_http / t_search)` = 3 lanes. Lanes 4 to 7 then add no games per hour. They add queue time per game (WR-01, WR-02), longer lease holds, more duplicate draws on the lease-less tier-3 and tier-4b lotteries (hold time and concurrent holders both rise), and four more request streams against the single uvicorn process. The same arithmetic gives 2 lanes for a 16-core volunteer box where the doc says 4.
**Confidence:** Derived, not measured. If a typical tier-4 game has fewer FENs than engines, the search phase does not fill the pool and more lanes do help. The point stands either way: the constant has no stated basis.
**Fix:** Derive the hint from engine-busy time (log busy engine-seconds per cycle, or infer from games per hour at 2, 3 and 4 lanes) and state it as "raise lanes only while games per hour still rises". In `REMOTE_WORKER.md`, recommend 2 to 3 and drop the 7-lane example until measured.

### WR-06: Two production-relevant mutations pass the whole test file; lane wiring into the watchdog and the shared streak are untested

**File:** `tests/test_remote_eval_worker.py:2302-2342`, `:2237-2252`, `:2350-2375`; code under test `scripts/remote_eval_worker.py:906-908`, `:1047-1056`, `:1962`
**Issue:** Both mutations were applied through a scratch pytest plugin (no source edit) and the file was run serially: 127 passed each time.

(a) `_run_loop` marks slot 0 for every lane (the lane index dropped at `:908`, which is exactly Task 1's intermediate state). In a scratch run with three healthy lanes this mutation trips the watchdog (tripped with 41 submits completed; unmutated code: no trip, 161 submits). In production it would kill the worker every 720 s. `test_wedged_lane_trips_the_watchdog_while_siblings_keep_working` still passes, for the wrong reason: the unmarked slots pin the minimum. There is no test that healthy lanes do not trip the watchdog.

(b) `_TransientStreak.record` and `.reset` replaced by no-ops. Nothing fails. The decision table never inspects the streak, the wiring test only compares `id()`, and the older streak tests call `_handle_transient_failure` directly. So "one Sentry event per outage across all lanes" (K-06), "a success resets the streak", and the lanes=1 equivalence of the refactored bookkeeping rest on reading only.

(c) No test references `_run_async` or `main`. If `_run_async` built `_Heartbeat(path)` with one slot while running N lanes, `mark(1)` would raise `IndexError` at `:715`, outside `_run_loop`'s `try`, and take the TaskGroup down in a relaunch loop.
**Fix:** Add: a healthy-lanes test (N lanes plus the checker, assert no exit while each slot advances); a `_run_loop` level streak test (failing client, patched `time.time`, two lanes, exactly one `capture_message`, then one success and a new streak); a `_run_async` test asserting the heartbeat has `lanes` slots and `run_worker` receives the same number.

### WR-07: The wedged-lane test races wall clock against work done

**File:** `tests/test_remote_eval_worker.py:2302-2342`
**Issue:** The checker fires 0.3 s after the heartbeat is created, whatever the lanes have done by then, and the test then asserts `stats.total_submits >= 5`. Two healthy lanes need about 150 ms of unimpeded event-loop time inside that window (six 5 ms sleeps per cycle). On a loaded box (16 xdist workers, or the SCHED_IDLE starvation this repo has already hit) the loop easily runs three to four times slower, fewer than 5 submits complete, and the test fails with the feature intact.
**Fix:** Remove the race: start the checker only after `total_submits >= 5` has been observed, or drive the checker with a patched clock instead of real time.

## Info

### IN-01: The entry lock is released when the client gives up, while the server-side lease or submit can still be live (pre-existing, not a regression)

**File:** `scripts/remote_eval_worker.py:1156-1157`; `app/routers/eval_remote.py:731-753,806`
**Issue:** A `ReadTimeout` on `/entry-lease` after the server committed the claim, or on `/entry-submit` while the handler is still running, exits the `async with`. The next lane leases at once, and its submit (or the first lane's late handler) stamps the orphaned batch complete with no evals, since the guard selects every unexpired game leased to the id. The same happens at lanes=1, where the next cycle follows about 1 s later, well inside the 20 s TTL. The lock cannot close this; only a batch token echoed on submit can.
**Fix:** Out of scope here. Server side: return a lease token from `/entry-lease` and key `/entry-submit` on it.

### IN-02: With one owner label, `release_lease`'s owner guard no longer separates a late lane from the current holder (unreachable today)

**File:** `app/services/blob_claim_lease.py:64-75`
**Issue:** If lane A's lease on a game expired and lane B then leased the same game, A's late submit would pass `held[1] != owner` and delete B's live lease. Two different worker ids are protected against this. It cannot happen today: the lease lasts 720 s from lease time and lane A's watchdog slot was stamped before the lease request, so the process is killed first (up to the 15 s poll interval).
**Fix:** None needed now. Keep in mind if `BLOB_LEASE_TTL_S` is ever lowered or `STALL_THRESHOLD_S` raised.

### IN-03: A lane that ends with a `CancelledError` the group did not issue disappears silently

**File:** `scripts/remote_eval_worker.py:892-893`, `:1601-1607`, `:1616-1631`
**Issue:** `asyncio.TaskGroup` ignores a child that finishes cancelled (checked on 3.14.3: the group exits normally and the sibling keeps running). If a `CancelledError` ever surfaces inside a lane without the lane task being cancelled, the process runs on L-1 lanes with no log line until the watchdog kills it 720 s later. At lanes=1 the same event ends the process at once and the supervisor relaunches in 3 s. No such source was found in the engine path; this is a robustness gap, and the docstring's failure semantics do not mention it.
**Fix:** Wrap the `_run_loop` call in `_run_lane` so that a `CancelledError` arriving while `asyncio.current_task().cancelling() == 0` is logged and re-raised as a `RuntimeError`, which fails the whole group.

### IN-04: The stagger is applied once; the "pickup latency stays about idle_sleep" claim only holds until lanes drift

**File:** `scripts/remote_eval_worker.py:1565-1566`, `:1595-1598`
**Issue:** After the first busy period each lane's idle phase is wherever its last game ended, so on fully empty queues the gap between polls can approach `idle_sleep x lanes` (7 s at 7 lanes). `DEFAULT_IDLE_SLEEP` was lowered from 5 s to 1 s for exactly this latency (comment at `:103-106`). Low impact while the backfill queues are never empty.
**Fix:** Correct the docstring, or re-phase: have an idle lane sleep until the next multiple of `idle_sleep` offset by its index.

### IN-05 (suspected): `HTTP_TIMEOUT_S` stays at 30 s while submit concurrency against one uvicorn process multiplies

**File:** `scripts/remote_eval_worker.py:107`, `:1687`
**Issue:** If the measured 4 s of HTTP per game is mostly server CPU on the single event loop (PGN replay, classify, re-score), latency per request grows roughly with the number of concurrent lanes and approaches 30 s near 7. A submit that times out on the client usually still commits on the server, but the lane records a transient failure, backs off `idle_sleep x lanes` and does not mark progress. Not verified: the split between network, database wait and CPU inside those 4 s is unknown.
**Fix:** Before going past 3 lanes, compare the lease-to-submit log timestamps per lane and the per-worker hole rate (`holes_submitted / plies_leased` in `worker_heartbeats`) against the single-lane baseline.

---

_Reviewed: 2026-11-19T14:20:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: deep_
