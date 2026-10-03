---
phase: 227-browser-engine-continuous-dispatch-against-a-relaxed-determi
plan: 10
subsystem: engine
tags: [mcts, continuous-dispatch, abort, determinism, tdd, mutation-tests]

requires:
  - phase: 227-09
    provides: "reviewed design (REVIEW-A/B SOUND, round 2) and the pre-registered accept rule"
provides:
  - "mctsSearch continuous dispatch behind SearchBudget.dispatchMode (round stays the default and is behavior-unchanged)"
  - "applyAndReport / discoverDeadEnd / SearchContext / SearchCounters shared by both loops; runRoundLoop, runContinuousLoop, fillContinuous, drainSettled"
  - "Pre-extraction round-loop goldens (inline digests, c=1 and c=4) and 73 continuous-mode tests, 16 mutations proven"
  - "dispatch-mode.check.mjs --mode continuous prints DISPATCH-PROBE continuous -> continuous"
affects: [227-11, 227-12, 227-13]

plan_head_before: 9f0b6be78c4fcbe43afcc54d1c6421c4b0d7d084
plan_head_after: 08bf6c94edb38eea54901ae93c7029ab3309a4f9

actuals:
  tokens: 27000
  tasks: 3
  commits: 6

tech-stack:
  added: []
  patterns:
    - "Settled queue + single-shot wake: fill, await exactly one wake, drain everything in arrival order"
    - "Inner AbortController handed to every dispatch, aborted in finally; outer signal gets one { once: true } listener removed in finally"
    - "Digest goldens (sha256 of snapshot sequence, final snapshot, ordered call lists) stored inline in the test file"

key-files:
  created:
    - frontend/src/lib/engine/__tests__/mctsSearch.continuous.test.ts
    - frontend/src/lib/engine/__tests__/searchTestProviders.ts
  modified:
    - frontend/src/lib/engine/mctsSearch.ts
    - frontend/src/lib/engine/__tests__/mctsSearch.test.ts
    - frontend/src/lib/engine/deadlineSearch.ts
    - frontend/src/lib/engine/__tests__/deadlineSearch.test.ts

key-decisions:
  - "Goldens live inline in mctsSearch.continuous.test.ts as digests plus a readable summary, not as .snap or reports/ files, because accept-rule content assertion 2 pins the set of files this plan may change"
  - "The round-3 fill guard uses the inner dispatch signal (aborted synchronously by the single outer-abort listener), which is the same condition as the outer signal and avoids a sixth parameter"
  - "Out-of-list comment rewordings (botBudget.ts, types.ts, maiaQueue.ts, scripts) and the requestPolicy one-liner are NOT made: deferred until after the gate"

requirements-completed: []

coverage:
  - id: D1
    description: "Continuous dispatch runs end to end behind the flag; round mode is unchanged"
    verification:
      - kind: unit
        ref: "frontend/src/lib/engine/__tests__/mctsSearch.continuous.test.ts#c=1 identity, omitted is round, pre-extraction goldens"
        status: pass
      - kind: other
        ref: "node --import ./scripts/lib/frontend-alias-hook.mjs scripts/lib/dispatch-mode.check.mjs --mode continuous => DISPATCH-PROBE continuous -> continuous"
        status: pass
    human_judgment: false
  - id: D2
    description: "Every continuous-mode invariant (abort/stop, budget, root guard, pending exclusion, fill, rejection, wakeup, listener) is guarded by a test that fails without its guard"
    verification:
      - kind: unit
        ref: "frontend/src/lib/engine/__tests__/mctsSearch.continuous.test.ts (73 tests; 16 mutations, table below)"
        status: pass
    human_judgment: false
  - id: D3
    description: "Deadline cut in continuous mode returns the last snapshot before the cut and applies nothing after it"
    verification:
      - kind: unit
        ref: "frontend/src/lib/engine/__tests__/deadlineSearch.test.ts#continuous mode (Phase 227 D-09/D-13)"
        status: pass
      - kind: other
        ref: "engine-dispatch-stop-rule.mjs --dispatch-mode continuous smoke, CONTINUOUS-SMOKE OK 5"
        status: pass
    human_judgment: false
  - id: D4
    description: "Post-extraction --hash clear parity re-run (accept-rule content assertion 4, Plan 227-11 precondition)"
    verification: []
    human_judgment: true
    rationale: "Pending the orchestrator (about 8 minutes of engine time, deliberately not run in this dispatch). Run it on commit 58540ce43."

duration: 40min
completed: 2026-10-02
status: complete
---

# Phase 227 Plan 10: Continuous dispatch in mctsSearch Summary

**mctsSearch now has a continuous dispatch loop (fill, one wake, drain in arrival order, inner AbortController, single outer listener) behind `dispatchMode`; at c=1 it matches round mode and the pre-extraction goldens byte for byte, round mode is behavior-unchanged, and `FLAWCHESS_DISPATCH_MODE` is still `'round'`.**

## Commits (in order, all on `worktree-agent-abed4a64702334958`)

Design SOUND commit `7bb93b943` and accept-rule commit `7fb704a65` are both ancestors of the first mctsSearch.ts commit
(verified with `git merge-base --is-ancestor`); no Phase 227 commit touched mctsSearch.ts before `58540ce43`.

| SHA | Commit |
|---|---|
| `c4a6db4cb` | `test(227-10)`: pre-extraction round-loop goldens, shared providers moved from mctsSearch.test.ts (no mctsSearch.ts change) |
| `58540ce43` | `refactor(227-10)`: extract `applyAndReport` / `discoverDeadEnd` / `SearchContext` / `SearchCounters` from the round loop, **no continuous code**. This is the commit the `--hash clear` parity re-run belongs on |
| `135515975` | `test(227-10)`: RED (arrival order and fill fail; probe exits 3) |
| `a7a209e9b` | `feat(227-10)`: continuous loop, comment rewording, c=1 identity and divergence fixtures (GREEN) |
| `55f7155cb` | `test(227-10)`: guard tests for every invariant, each mutation-checked |
| `08bf6c94e` | `feat(227-10)`: deadlineSearch comment and continuous deadline test |

## What was built

- `runContinuousLoop` / `fillContinuous` / `drainSettled` exactly as the reviewed sketch, including the round-2 repairs: the
  `!signal.aborted && !st.earlyStop` guard before the single `await` (R2B-2) and abort/early stop checked before acting on a
  rejected item, so post-stop rejections are dropped (R2A-6). D-10 fill guard, per-fill block clearing in a `finally`, inner
  controller aborted in `finally`, one `{ once: true }` outer listener removed in `finally`.
- Round mode: `runRoundLoop` is today's loop calling the shared helpers; `mctsSearch` selects the loop with
  `budget.dispatchMode === 'continuous'`, anything else (including omitted) is round.
- Design 2.11 comment rewordings inside `mctsSearch.ts` (module header, `isPending`, `isBlocked`, `stopRuleSatisfied`,
  `selectPath` doc and root guard, `applyExpansion`, `dispatchExpansion`, the gradeRoot routing comment, the 8XN-7 comment,
  the round-loop apply comment) and `deadlineSearch.ts` (overrun bound for both modes).
- Probe: `dispatch-mode.check.mjs --mode continuous` prints `DISPATCH-PROBE continuous -> continuous` (exit 0); the default
  run still prints `DISPATCH-PROBE round -> round`. `FLAWCHESS_DISPATCH_MODE` is still `'round'` (`botBudget.ts:76`).

## TDD record

RED commit `135515975`: `arrival order` failed with `expected [ { rankedLines: [ …(3) ], …(3) } ] to have a length of 2 but
got 1` and `fill` with `expected [ … ] to have a length of 4 but got 3` (continuous still ran the round barrier loop), and
`dispatch-mode.check.mjs --mode continuous` exited 3 (`DISPATCH-PROBE continuous -> round`). The c=1 identity,
omitted-vs-round and c=4 smoke tests pass vacuously before the implementation (the flag was ignored), so the genuine RED
evidence is the two tests plus the probe. `gsd_run check tdd-red-evidence` was not available in this environment, so no
evidence record file was produced. GREEN `a7a209e9b`; no REFACTOR commit beyond the extraction (which precedes RED by design).

Tracer gate (Task 1): re-ran `-t "c=1"` (26 passed), the engine suite, both probe modes, lint, build and knip after the
GREEN commit: all clean.

## Mutation table (every guard reverted, failing tests named, guard restored)

Run against `mctsSearch.ts` with `git checkout --` between mutations; test file: `mctsSearch.continuous.test.ts` unless noted.

| # | Reverted guard | Tests that failed |
|---|---|---|
| M1 | remove `signal.aborted \|\| st.earlyStop` check before apply (plan 1) | `after abort: an abort fired inside onSnapshot discards ...`; `early stop: results queued behind the stopping apply ...`; both `rejection: ... queued behind ...` (R2A-6) |
| M2 | stop aborting the inner controller in `finally` (plan 2) | `early stop: results queued ...` (signals not aborted); `early stop: a policy that settles after the stop ...`; `rejection: ... aborts every sibling` |
| M3 | drop per-fill block clearing (plan 3) | `fill: a peaked non-root policy keeps concurrency-many ...`; `fill: a block set in one fill is cleared before the next ...` |
| M4 | loosen D-10 guard to `nodesEvaluated < maxNodes` (plan 4) | 6 `budget:` tests, 6 `c=4 completes` tests, both `fill:` tests, `wakeup: settle during drain` |
| M5 | skip removing the outer listener (plan 5) | both `listener:` tests |
| M6 | wake assigned after an `await` (macrotask before the wake promise), covers "second await" (plan 6) | `wakeup: a search over already-resolved providers completes` (reports `pending` at the 1 s bound); 7 more time out at 20 s |
| M7 | swallow rejected settlements (plan 7) | `rejection: a rejected provider call rejects the search ...`; `listener: ... when the search rejects` |
| M8 | drop `!signal.aborted && !st.earlyStop` before the wait (R2B-2) | `wakeup: an abort raised synchronously inside a provider during a fill still returns ...` |
| M9 | drop `notify()` from `onOuterAbort` (round-3 item 2) | `wakeup: a timer-driven abort wakes a loop ...`; `c=1 abort in flight ...`; `c=1 late rejection ...`; `after abort: grades that settle ...`; arrival order, fill, root guard (cleanup hangs); and `deadlineSearch.test.ts` continuous test |
| M10 | test `kind === 'rejected'` before the abort/early-stop test (R2A-6) | both `rejection: ... queued behind ...` tests |
| M11 | drop `+ inFlight` from the fill guard | 6 `budget:`, 6 `c=4 completes`, both `fill:` tests |
| M12 | root guard: remove `root.isPending` from `selectPath` (Y-9) | `root guard: exactly one dispatch ...`; `arrival order: no leaf is ever dispatched twice`; `early stop: a policy that settles ...`; and 15 round-mode goldens / omitted-equals-round tests at c>=2 |
| M13 | drop the new `!dispatchSignal.aborted` fill term (round-3 item 1) | `wakeup: an abort raised synchronously ... stops the fill` (policy calls 4, expected 2) |
| M14 | fill guard without `+ inFlight` at c=1 | `fill:` tests only: at c=1 the fill structurally runs only when nothing is in flight, so this alone is not visible to the identity tests |
| M14b | M14 plus a second `fillContinuous` per iteration ("fill runs while a result is in flight") | 11 `c=1 ... continuous equals round and the golden` tests, arrival order, fill, c=1 abort in flight, late rejection |
| M15 | rethrow a late rejection from the settle handler | `c=1 late rejection after abort ...`; `rejection: ...` (3 unhandled rejection events) |
| M16 | drop `leaf.isPending = true` in `fillContinuous` | `arrival order: no leaf is ever dispatched twice`; `root guard`; `early stop: a policy that settles ...` |

Extraction safety (design 2.12 row): dropping the visit bump in `discoverDeadEnd` fails `dead-ends` c=1 and c=4 and `chains`
c=1 and c=2; changing `>=` to `>` on the `budgetExhausted` flag in `applyAndReport` fails 18 goldens. Dropping
`propagateClosure` from `discoverDeadEnd` is **not** observable in these fixtures (the search ends identically, by block
instead of by closure); that line was moved verbatim, and the clear-hash parity re-run is the real-provider backstop.

## Task 3 smoke and checks

- Continuous real-engine smoke (`engine-dispatch-stop-rule.mjs --dispatch-mode continuous --procs 4 --pool-size 4 --openings 1
  --maia-fifo`, out dir in the scratchpad, 5 positions, 18 s): `Dispatch mode probe: requested=continuous observed=continuous`,
  python check `CONTINUOUS-SMOKE OK 5` (every row labelled continuous, nodes at stop <= 50).

  | position | nodes at stop | stop | wall | loop_lag_max_ms |
  |---|---|---|---|---|
  | italian | 17 | early-stop | 2.1 s | 10 |
  | middlegame | 50 | budget | 6.1 s | 8 |
  | sharp | 15 | early-stop | 2.3 s | 4 |
  | endgame | 11 | early-stop | 1.3 s | 1 |
  | C50 | 50 | budget | 4.6 s | 5 |

- Default (round) run of the same script, same set: `requested=round observed=round`, 5 rows, nodes 16/50/15/8/50, wall
  2.6/8.7/3.1/1.4/5.5 s. These two runs are smoke checks, not interleaved or probe-normalized, so the wall difference is
  **not** evidence. Under warm hash with worker Maia, round mode is not bit-reproducible run to run (design 1.4, owner
  direction 2026-10-02), so "bit-identical in the harness" is not asserted; the identity claims are the vitest goldens and the
  clear-hash parity check.
- `--self-test` of `engine-dispatch-stop-rule.mjs`, `engine-move-quality.mjs`, `engine-grading-depth-ab.mjs`: all pass.
- Full frontend suite: 284 files, 4562 tests passed; `npm run lint`, `npm run build` (tsc -b), `npm run knip`: clean.

## Pending for the orchestrator

- **Post-extraction `--hash clear` parity re-run (design 2.4, accept-rule content assertion 4): NOT run here.** Run the
  Plan 227-08 clear-hash round-mode gate (worker Maia, stop off and on, 60 rows each) and
  `tripwire --mq-dir <rerun>/worker --baseline-dir reports/data/continuous-dispatch-227/tripwire/parity-clear/main`.
  The extraction-only commit is `58540ce43` (no continuous code in it). Round mode is behavior-unchanged in every later
  commit (the goldens at c=1 and c=4 and all round suites pass at HEAD), so running at HEAD `08bf6c94e` is equivalent in
  practice, but the rule says "after the extraction and before any continuous code", which names `58540ce43`. Record the
  PASS in this SUMMARY or the 227-11 run metadata; Plan 227-11 refuses to start without it.
- Plan 227-11 should record `I` and assert accept-rule content assertions 1 to 3. Assertion 2 holds at HEAD:
  `git diff --name-only 7fb704a65 HEAD -- . ':!.planning'` lists the six allowed frontend files plus the comment-only
  `scripts/` files from `dcba1ba14`.

## Deviations from Plan

### Design overrides the plan (as instructed)

- **Round loop is refactored, not "verbatim"**: design 2.1/2.4 made pre-extraction goldens (commit `c4a6db4cb`) a precondition
  of the extraction (`58540ce43`). Names follow the design: `SearchContext` (read-only inputs) and `SearchCounters` (the four
  former locals), `applyAndReport`, `discoverDeadEnd`, `runRoundLoop`, `runContinuousLoop`, `fillContinuous`, `Settled`. One
  helper beyond the sketch: `drainSettled` (keeps `runContinuousLoop` at nesting depth 3), plus `stopReasonOf` / `snapshotOf`.
- **Goldens are inline digests, not vitest golden files**: accept-rule assertion 2 lists the six files this plan may change, so
  a `.snap` or `reports/` file would invalidate the gate data. Each golden is the sha256 (20 hex chars) of the JSON of
  {onSnapshot sequence, returned snapshot, ordered policy() and grade() call lists after quiescence} with a readable summary
  beside it. 12 fixtures x c=1 and c=4 (c=2 as well for `chains`): plain, stop-rule, dead-ends, terminal, degenerate,
  empty-grade (8XN-7), extra-root-moves, grade-root, abort-in-snapshot, pre-aborted, peaked, chains. `terminal`, `peaked`
  and `chains` are additions to the design's list (`chains` is the fixture that actually exercises `isBlocked` at c>1;
  `peaked` produces identical output at every c because the broad root is exhausted first).
- **`runContinuousLoop` waits through a shared `wake` handoff exactly as the sketch**; sketch variable names changed slightly
  (`item`, `waiter`).

### Round-3 reviewer items from the coordinator (all four folded in; design.md untouched)

1. **Fill guard**: added `!dispatchSignal.aborted` as the first term of the `fillContinuous` loop guard. It uses the inner
   dispatch signal, which the single outer-abort listener aborts synchronously, so it is the same condition as the outer
   signal without a sixth parameter. No effect on c=1 identity (the one dispatch is the pass's last action; all 11 c=1
   identity tests pass). R2B-2 fixture extended: after the synchronous abort inside the first non-root `policy()`, exactly
   2 `policy()` calls exist (root plus the aborting one). Mutation M13 (drop the term) fails it; M8 (drop the wait guard) fails it too.
2. **Timer-driven abort test** made mutation-proof: the grades are hand-settled and never settle by themselves, the abort comes
   from a `setTimeout` macrotask, and the test asserts the search resolved with no provider settled and every in-flight grade
   signal aborted. M9 (drop `notify()`) now fails it, the c=1 abort-in-flight fixture, and the new `deadlineSearch.test.ts`
   continuous test (grade delays 70 ms so no settlement lands inside the deadline window).
3. **Comment rewordings inside `mctsSearch.ts`**: the gradeRoot paragraph ("bit-identity claim ... scoped per (concurrency,
   pool size)") and the root-guard comment ("two concurrent dispatch slots in the very first round") were reworded.
4. **`maxNodes` precondition**: `fillContinuous`'s doc states `maxNodes` is assumed to be a positive integer and not validated.

### Deferred until after the gate (outside the six allowed files; not edited)

Per the coordinator's correction and accept-rule content assertion 2, these comment rewordings are NOT made:

- `frontend/src/lib/engine/botBudget.ts:63` ("app == harness determinism holds exactly")
- `frontend/src/lib/engine/types.ts:66` (stop rule "in the mctsSearch canonical apply-order loop") and `:119-121` ("the
  byte-identical A21S barrier loop": say behavior-identical, proven by the pre-extraction goldens and the clear-hash parity re-run)
- `frontend/src/lib/engine/maiaQueue.ts:259-263` ("the orchestrator's own apply loop breaks on `signal.aborted` ...")
- `scripts/` tooling comments still saying "canonical apply-order loop" (for example the header of
  `scripts/engine-dispatch-stop-rule.mjs`)
- The `requestPolicy` aborted-signal one-liner in `maiaQueue.ts` (R2B-5): it is behavior, it is outside the six files, and the
  design only "flags" it. Not made. Cost if left: one wasted Maia inference after a continuous stop in the app, in a narrow
  race (the chart-join fallback). Nothing is applied, so claim (d) holds.

### Other

- **[Rule 3 - blocking] `npm ci`** in `frontend/` and `scripts/` (lockfiles only, nothing added) because the fresh worktree had
  no `node_modules`.
- **A stray scratch file** `/home/aimfeld/Projects/Python/flawchess/.claude/tmp_goldens_unused.txt` was created by a mistyped
  redirect during golden capture and removed immediately (it was never tracked or committed).
- `gsd_run` was not available in this environment, so `check tdd-red-evidence` and `gsd_run query ...` state verbs were not
  used; `STATE.md` and `ROADMAP.md` were not touched, as ordered.

## Known Stubs

None.

## Threat Flags

None. T-227-17 (apply after abort / early stop) is mitigated by the discard check, tests `after abort` and `early stop`,
mutations M1 and M12; T-227-18 (stale grades) by the inner controller, tests `early stop` and `listener`, mutations M2, M5 and
M9. T-227-SC: no package was added.

## Self-Check: PASSED

- Created files exist: `mctsSearch.continuous.test.ts`, `searchTestProviders.ts` (FOUND).
- Commits found: `c4a6db4cb`, `58540ce43`, `135515975`, `a7a209e9b`, `55f7155cb`, `08bf6c94e`.
- `git rev-list --count 9f0b6be78..HEAD` = 6 before this SUMMARY commit (`commits: 6`).
- Plan verify: `-t "c=1"` 26 passed; engine suite 34 files / 777 tests; both probe modes; `npm run lint`, `npm run build`,
  `npm run knip` clean; `grep "FLAWCHESS_DISPATCH_MODE: DispatchMode = 'round'"` matches; one test per behavior keyword
  (`after abort`, `early stop`, `budget`, `arrival order`, `fill`, `root guard`, `rejection`, `wakeup`, `listener`, `c=1`,
  `omitted`) exists.

## Post-extraction parity re-run (orchestrator, 2026-10-02)

Run at `58540ce43` (helper extraction done, no continuous code yet), in a throwaway worktree, exactly as design §2.4
requires: `engine-move-quality.mjs --dispatch-mode round --repeats 1 --maia-fifo --hash clear --grade-depth 18
--procs 4 --pool-size 4`, fixture `move-quality-226.tsv`, stop off (331 s) and on (103 s), worker-thread Maia, compared
with the committed main-thread baseline by `engine_dispatch_227_verdict.py tripwire --baseline-dir
reports/data/continuous-dispatch-227/tripwire/parity-clear/main`:

**TRIPWIRE PASS** (0 of 60 rows differ in each stop mode; twin exit 0). Round mode is behavior-identical to the
pre-extraction code on real providers. Data kept local (`temp/parity-58540-out/`), not committed, per accept-rule
content assertion 2.

Post-merge gate at `7581bb6fb`: `DISPATCH-PROBE round -> round`, `DISPATCH-PROBE continuous -> continuous`,
`FLAWCHESS_DISPATCH_MODE` still `'round'`, engine + hooks vitest 1342 passed, lint and build clean.
