---
phase: quick-261119-k9s
plan: 01
subsystem: remote-eval-worker
tags: [worker, concurrency, lanes, asyncio, watchdog]
status: complete
requirements: [LANES-01, LANES-02, LANES-03, LANES-04, LANES-05, LANES-06, LANES-07]
key-files:
  modified:
    - scripts/remote_eval_worker.py
    - tests/test_remote_eval_worker.py
    - REMOTE_WORKER.md
actuals:
  tokens: 11000
  tasks: 3
  commits: 4
plan_head_before: 1b8b3487c36703136cb03c2fb7c7bff621bde479
plan_head_after: 6537896046f5a003a01a506c76f302e275971e5b
---

# Quick 261119-k9s: remote eval worker `--lanes`

`--lanes N` runs N concurrent lease -> eval -> submit cycles on one EnginePool inside one worker process. The default of 1 takes the unchanged single `_run_loop` path.

Commits: `5fe0e05d1` (Task 1), `206056853` (Task 2), `8a242278d` (Task 3), `653789604` (review follow-up, see the end). No file under `app/`, `CHANGELOG.md`, `docker-compose.worker.yml` or `Dockerfile.worker` changed. `WORKER_SCHEMA_VERSION` is still 3.

## Decisions as implemented

- **K-01** `run_worker(lanes=1)` awaits `_run_loop` once with no `lane` argument. Above 1 it logs one line and awaits `_run_lanes`. The EnginePool and one httpx client per target are built once. `lanes > 1` with `loop=False` raises `ValueError("lanes > 1 requires loop mode")`.
- **K-02** `_run_lanes` starts one `asyncio.TaskGroup` task per lane, named `eval-lane-<i>`. Each runs `_run_loop(loop=True, lane=_LaneContext(index, entry_lock, streak))`. Lock and streak are shared. No module-level lane state.
- **K-03** `_run_cycle` rung 2 is now `_try_entry_rung`. With a lane, it runs inside `async with entry_lock`, held from `/entry-lease` through `/entry-submit`. A lane that reaches rung 2 while another holds the lock waits, so the ladder order is unchanged.
- **K-04** `_Heartbeat(path, lanes)` keeps one slot per lane. `last_progress` is a read-only property returning the minimum. `mark(lane)` rewrites the file only when that lane held the oldest slot before the mark (ties count as oldest, so lanes=1 writes on every mark). `_watchdog_checker` and `_is_stalled` are untouched.
- **K-05** Exceptions are absorbed by each lane's own `_run_loop` boundary. The failure policy was extracted to `_on_cycle_failure` and `_TransientStreak`, which also cleared the pre-existing depth-5 breach in `_run_loop`.
- **K-06** `_lane_schedule(lanes, idle_sleep)` returns `(i * idle_sleep, idle_sleep * lanes)`. One `_TransientStreak` is shared by all lanes. Lane logs carry a `[lane N]` prefix through the `_LANE_LABEL` ContextVar, set in `_run_lane`; nothing sets it at lanes=1.
- **K-07** `--lanes < 1` and `--lanes > ceil(--workers / 2)` are rejected by `parser.error`. Constants: `DEFAULT_LANES=1`, `MIN_ENGINES_PER_LANE=2`, `RECOMMENDED_ENGINES_PER_LANE=4`. The STALL_THRESHOLD_S comment block has a "Lanes" paragraph with the bound.
- **K-08** `_effective_lanes` forces 1 for `--once` and `--dry-run`; `main` logs one line when it overrides a requested `--lanes > 1`. The startup line gets ` lanes=N` only when N > 1.

## Per-rung worker-id verdict (K-03)

| Rung | Verdict |
|------|---------|
| 1 explicit atomic | Safe: one `eval_jobs` row claimed per call (SKIP LOCKED), completion keyed on the echoed `job_id`. |
| 2 entry-ply | UNSAFE with a shared worker id: `/entry-submit` stamps every unexpired game leased to the id. Mitigated by the entry lock. |
| 3 idle atomic | No lease, no worker id (lottery). Two lanes can draw the same game, as two workers can today. Accepted. |
| 4 flaw-blob | Safe: `blob_claim_lease.try_lease` refuses any unexpired lease regardless of owner; release is per game. |
| 5 bestmove | No lease, no worker id. Accepted as rung 3. |
| `worker_heartbeats` upsert | Lanes share one row: a short row-lock wait inside the submit transaction's SAVEPOINT. Accepted. |

## Mutation proof (each test seen failing, then restored)

Task 1:

| Mutation | Test(s) that failed |
|----------|---------------------|
| lanes=1 routed through `_run_lanes` | `test_run_worker_single_lane_awaits_run_loop_once` |
| lanes > 1 calls `_run_loop` | `test_run_worker_multi_lane_awaits_run_lanes_once` |
| lanes awaited one after another instead of the TaskGroup | `test_lanes_run_concurrently_on_one_pool` |
| `_on_cycle_failure` returns "raise" always | `test_lane_exception_is_isolated_to_that_lane`, all 5 `test_on_cycle_failure_decision_table` cases |
| `_try_entry_rung` called without the lock | `test_entry_rung_is_serialized_across_lanes` |
| bare `asyncio.create_task`, no await | `test_cancelling_run_lanes_cancels_every_lane` |
| `MIN_ENGINES_PER_LANE = 1` | `test_lanes_above_cap_rejected`, `test_lane_cap_keeps_worst_case_cycle_inside_the_stall_threshold` |
| `--lanes` validation lines removed | `test_lanes_below_one_rejected`, `test_lanes_above_cap_rejected` |

Task 2:

| Mutation | Test(s) that failed |
|----------|---------------------|
| `last_progress` returns max | `test_heartbeat_last_progress_is_the_oldest_lane`, `test_heartbeat_file_is_freshened_only_by_the_oldest_lane`, `test_wedged_lane_trips_the_watchdog_while_siblings_keep_working` |
| `mark` writes the file on every call | `test_heartbeat_file_is_freshened_only_by_the_oldest_lane` |
| `* lanes` dropped in `_lane_schedule` | `test_lane_schedule_staggers_starts_and_scales_idle`, `test_run_lanes_wires_schedule_and_shared_state` |
| label dropped in `_log` | `test_log_carries_the_lane_label_only_inside_a_lane` |

## Checks run (all in the worktree)

- `uv run ruff format --check scripts/remote_eval_worker.py tests/test_remote_eval_worker.py`: clean.
- `uv run ruff check scripts/remote_eval_worker.py tests/test_remote_eval_worker.py`: clean.
- `uv run ty check app/ tests/ scripts/`: all checks passed.
- `uv run python scripts/check_function_size.py scripts/remote_eval_worker.py --fail-over-depth 4`: OK, 49 functions, no breaches (exit 1 at HEAD on `_run_loop`).
- `uv run pytest tests/test_remote_eval_worker.py tests/test_dependency_isolation.py -q`: 140 passed. The 98 pre-existing worker tests are unedited (`git diff` shows no removed lines in the test file); 29 lanes tests were added.
- `--help` lists `--lanes`; `REMOTE_WORKER.md` mentions it.
- The worker script was only ever run with `--help`.

## Deviations from Plan

None. One note: the plan's step "Do a bare `raise` in `_run_loop`" is as implemented.

## Not done / out of scope

- `CHANGELOG.md` is not edited. Precedent: the worker-only commits 4854e54fd, 730bf0633, d8034be40 and 8d315d777 shipped without a bullet, and `[Unreleased]` is user-facing.
- `docker-compose.worker.yml` has no lanes variable (flagged as an option below).
- The full pre-merge gate and the full backend suite were not run; the orchestrator owns them.

## SIGINT discrepancy (K-08), flagged for the orchestrator

The brief says each lane "finishes its in-flight submit as the single loop does today". The current code does not: Python 3.14's `asyncio.Runner` turns the first SIGINT into a cancel of the main task, so today's single loop cancels its in-flight cycle and relies on the server lease TTLs. Lanes behave the same way (the TaskGroup cancels and awaits every lane, `run_worker`'s finally stops the pool once). A graceful submit-drain would change lanes=1 behavior too, so it was not added.

## Operator cautions to relay

1. Every lane adds concurrent submits against prod's single uvicorn process and its 20-connection app pool (prod `max_connections` is 50). Start amalie-nb at 3 lanes and watch latency before going to 7.
2. The Docker worker image stays single-lane unless `docker-compose.worker.yml` gains a lanes variable later.

## Known Stubs

None.

## Threat Flags

None. No new endpoints, auth paths or schema changes; the plan's threat register mitigations (T-01 entry lock, T-02 per-lane heartbeat, T-03 scaled idle plus shared streak) are implemented and covered by the mutation-proven tests above.

## Self-Check: PASSED

- `scripts/remote_eval_worker.py`, `tests/test_remote_eval_worker.py`, `REMOTE_WORKER.md` exist and are committed.
- Commits `5fe0e05d1`, `206056853`, `8a242278d` are ancestors of HEAD (`git rev-list --count 1b8b3487c..HEAD` = 3).

## Review follow-up (261119-k9s-REVIEW.md), commit `653789604`

Orchestrator decisions A to E implemented. Superseded text above: the cap is now `max(1, workers // ENGINES_PER_LANE)` with `ENGINES_PER_LANE = 6` (28 -> 4, 16 -> 2, 12 -> 2, 8 -> 1); `MIN_ENGINES_PER_LANE` and `RECOMMENDED_ENGINES_PER_LANE` are gone, and the "exactly when L <= ceil(W/2)" derivation is removed everywhere. The sizing hint is "about one lane per 6-8 engines (--workers 28 --lanes 3 or 4)".

- **A** Cap, comments (constant, STALL_THRESHOLD_S block, `_max_lanes`, parser error, module docstring, `--lanes` help, REMOTE_WORKER.md) restated as: throughput saturates at about workers/8 lanes; queueing for engines lengthens every cycle and the leases it can outlive are the short ones, `ENTRY_LEASE_TTL_SECONDS = 20` (app/services/eval_drain.py:278) and `LEASE_TTL_SECONDS = 120` (app/services/eval_queue_service.py:89), not the 720 s `BLOB_LEASE_TTL_S`; and the modelled all-timeout cycle must stay under STALL_THRESHOLD_S. Known limits (priority work queues behind backfill, entry batch can outlive its 20 s lease) documented in the module docstring and REMOTE_WORKER.md.
- **B** `_lane_schedule` clamps the stagger (`MAX_LANE_STAGGER_S = 60`) and the lane idle sleep (`MAX_LANE_IDLE_SLEEP_S = 60`, never below `--idle-sleep` itself, so lanes=1 is exactly today). `parse_args` rejects lanes > 1 when `_worst_first_mark_s` (stagger + lane idle sleep) is >= STALL_THRESHOLD_S / 2. A single-lane `--idle-sleep` >= 720 is NOT rejected today (only `> 0` is validated) and would trip the watchdog; left unchanged as instructed.
- **C/D** Watchdog tests run on a virtual clock (`_VirtualClock` replaces `asyncio.sleep`, `_Heartbeat` gained an injectable `clock`), so nothing races wall time. The wedged-lane test is rewritten on it.
- **E** `_run_lanes` waits for the first lane task to end (`asyncio.wait(..., FIRST_COMPLETED)`) and raises `RuntimeError`, so the TaskGroup tears everything down and the child exits non-zero. A lane that returns, raises or ends in a stray `CancelledError` can no longer leave the process on fewer lanes. The existing wiring test was adapted because its `_run_loop` mock used to return at once.

### Re-derived worst case for A(3), from the real constants

An atomic cycle (rungs 1 and 3) runs three first-pass gathers (`_eval_positions`, `_eval_atomic_blob_nodes`, `_eval_targeted_second_best`), each followed by a retry gather drawing on one per-cycle budget of `EVAL_RETRY_MAX_POSITIONS` (8) x `EVAL_RETRY_TIMEOUT_S` (15 s). Modelling every search timing out at `engine._NODES_TIMEOUT_S` (5 s) with up to 100 positions per pass: one cycle is 3 x 100 x 5 + 8 x 15 = 1620 engine-seconds. L lanes in that state on W engines finish after about L x 1620 / W seconds, plus up to 5 HTTP calls x 30 s = 150 s.

- At the cap `W // 6` for every W >= 12 (the worker counts that allow more than one lane): L x 1620 / W <= 1620 / 6 = 270 s, so at most 420 s with HTTP, under 720 s. Example: W=28, L=4 -> 231 s (+150 s). The new test asserts this over W = 12..128 from the module constants.
- The model does NOT bound the lanes=1 case at small W, and that is pre-existing: W=1 -> 1620 s, W=2 -> 810 s exceed 720 s in this all-timeout model (W=3 -> 540 s). The old "500 s at W=1" claim assumed a single pass. Not changed by lanes; flagging it because the old comment implied a guarantee.
- It is also not a guarantee for large games: passes are not limited to 100 positions (the server allows up to 1024 per lease).

### New mutation pairs (each seen failing, then restored)

| Mutation | Test(s) that failed |
|----------|---------------------|
| `ENGINES_PER_LANE = 1` | `test_lanes_above_cap_rejected` (all 5 cases), `test_max_lanes_is_one_lane_per_engines_per_lane`, `test_lane_cap_keeps_modelled_worst_case_cycle_inside_the_stall_threshold` |
| `_lane_schedule` unclamped (`i*idle`, `idle*lanes`) | `test_lane_schedule_clamps_stagger_and_idle_below_the_watchdog`, `test_idle_lanes_with_scaled_idle_sleep_never_trip_the_watchdog` (the reviewer's scenario, scaled 1000x) |
| parse-time idle-sleep check disabled | `test_lanes_with_a_huge_idle_sleep_rejected_but_single_lane_unchanged` |
| `heartbeat.mark(0)` for every lane | `test_healthy_lanes_never_trip_the_watchdog` |
| `last_progress` returns max | `test_wedged_lane_trips_the_watchdog_while_siblings_keep_working` (rewritten, deterministic), plus the two heartbeat tests |
| `_TransientStreak.record` made a no-op | `test_sustained_outage_escalates_exactly_one_event_single_loop`, `test_lanes_share_one_streak_and_escalate_one_event` |
| `_TransientStreak.reset` made a no-op | `test_successful_cycle_resets_the_streak_single_loop`, `test_success_in_any_lane_resets_the_shared_streak` |
| `record` does not store `alerted` | `test_sustained_outage_escalates_exactly_one_event_single_loop` (two escalations) |
| `_run_loop` ignores `lane.streak` | `test_lanes_share_one_streak_and_escalate_one_event`, `test_success_in_any_lane_resets_the_shared_streak` |
| `_run_async` builds `_Heartbeat` with one slot | `test_run_async_builds_one_heartbeat_slot_per_lane[3]` |
| `main()` passes `args.lanes` instead of the effective count | `test_main_hands_the_effective_lane_count_to_run_async` (once and dry-run cases) |
| `_run_lanes` end-of-lane guard removed | `test_run_lanes_fails_the_group_when_one_lane_ends` (returns and cancelled) |

Mutation note: under `heartbeat.mark(0)` the wedged-lane test still passes (the unmarked slots pin the minimum anyway, as the review said); the new healthy-lanes test is the one that catches it.

### Checks after the follow-up

ruff format --check, ruff check, `uv run ty check app/ tests/ scripts/` and the nesting gate (50 functions, no breaches) are clean. `uv run pytest tests/test_remote_eval_worker.py tests/test_dependency_isolation.py -q`: 163 passed. The worker test file run three times in a row: 150 passed each time. No move-prediction model name in the worker file. The REVIEW.md file is untracked and not committed.

Not done (out of scope per the follow-up): engine priority for tier-1 work, nits 8, 9, 11, 12, any `app/` change, Docker.
