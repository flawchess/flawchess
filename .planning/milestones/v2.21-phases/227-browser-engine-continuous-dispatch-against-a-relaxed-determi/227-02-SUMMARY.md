---
phase: 227-browser-engine-continuous-dispatch-against-a-relaxed-determi
plan: 02
subsystem: engine
tags: [mcts, dispatch-mode, stockfish-pool, fifo, harness-probe, typescript]

requires:
  - phase: 226
    provides: "gradeRoot root fan-out, relaxed determinism contract (D-05 read through D-01)"
provides:
  - "DispatchMode type and optional SearchBudget.dispatchMode (omitted = round)"
  - "FLAWCHESS_DISPATCH_MODE = 'round' single app == harness constant"
  - "Both app search budgets (bot, analysis) carry the flag, still inert"
  - "scripts/lib/dispatch-mode.mjs probe that observes which dispatch loop mctsSearch executed"
  - "App Stockfish queue FIFO among equal (priority, depth) requests"
affects: [227-03, 227-10, 227-13, harness gate scripts]

actuals:
  tokens: 7500
  tasks: 2
  commits: 3
plan_head_before: 5747916856992a7422efac837c2ae69948edd1b3
plan_head_after: 0edd4a7c69c874b00624fe9dbdb5ee44cf6dc74a

tech-stack:
  added: []
  patterns:
    - "Harness mode flags are verified by observing executed behavior (deferred mock grades), never by label"
    - "Single shared constant for app and harness (T-168.5-04-01 pattern) extended to dispatch mode"

key-files:
  created:
    - scripts/lib/dispatch-mode.mjs
    - scripts/lib/dispatch-mode.check.mjs
  modified:
    - frontend/src/lib/engine/types.ts
    - frontend/src/lib/engine/botBudget.ts
    - frontend/src/hooks/useBotGame.ts
    - frontend/src/hooks/useFlawChessEngine.ts
    - frontend/src/lib/engine/workerPoolState.ts
    - frontend/src/lib/engine/__tests__/workerPool.test.ts
    - frontend/src/lib/engine/gradingLadder.ts

key-decisions:
  - "Probe expects 1 + PROBE_CONCURRENCY grade calls after the root settles (not the plan's literal 2): the engine fills both concurrency slots once the root applies"
  - "Probe asserts it really settled the root and exactly one in-flight grade before observing, so a probe edited to skip the settle cannot read 'round' for any engine"
  - "check.mjs also drives the probe against synthetic round and continuous searches so the 'continuous' verdict is exercised before Plan 227-10 lands the real loop"

patterns-established:
  - "assertDispatchModeLive(search, mode): every gate script calls this at startup; exit 3 = continuous requested but round executed"

requirements-completed: []

duration: 25min
completed: 2026-10-02
status: complete
---

# Phase 227 Plan 02: Dispatch-mode flag and FIFO queue Summary

**Inert `dispatchMode` flag wired from one shared constant into both app budgets, a harness probe that observes which dispatch loop `mctsSearch` really ran (continuous requests exit 3 until the loop exists), and an arrival-order (FIFO) tie-break in the app Stockfish queue.**

## Performance

- **Duration:** about 25 min
- **Tasks:** 2 of 2
- **Files:** 2 created, 7 modified

## Accomplishments

- `types.ts`: `DispatchMode = 'round' | 'continuous'` and `SearchBudget.dispatchMode?: DispatchMode` (omitted = round, so every existing caller, test and fixture gate is unchanged).
- `botBudget.ts`: `FLAWCHESS_DISPATCH_MODE: DispatchMode = 'round'`, the single definition for the hooks and every harness script. Shipping is a one-line flip, rollback is flipping it back.
- `useBotGame.ts` (`BOT_SEARCH_BUDGET`) and `useFlawChessEngine.ts` (analysis budget) both pass `dispatchMode: FLAWCHESS_DISPATCH_MODE`.
- `scripts/lib/dispatch-mode.mjs`: `DISPATCH_MODES`, `parseDispatchModeFlag`, `defaultDispatchMode` (reads the app constant), `probeDispatchMode`, `assertDispatchModeLive`, `DISPATCH_MODE_NOT_LIVE_EXIT = 3`, and the fixed messages. The probe runs the real `mctsSearch` against deferred mock grades and reports `'continuous'` iff a new grade call appears while another in-flight expansion is still unsettled.
- `scripts/lib/dispatch-mode.check.mjs`: prints `DISPATCH-PROBE <requested> -> <observed>`; `--mode round` exits 0; `--mode continuous` prints `CONTINUOUS-NOT-IMPLEMENTED` and exits 3 today.
- `workerPoolState.ts` `dequeueHighestPriority`: removed the first-candidate-UCI tie-break, so equal (priority, depth) requests are served in arrival order, matching the Node harness pool. Fix-site comment records D-19 / N-3.
- `gradingLadder.ts`: comment now states the real cache key `${fen}|${gradingDepth}` (Y-14).

## Task Commits

1. Task 1 (tracer): flag end to end plus probe: `db59be43b` (`feat(227-02)`)
2. Task 2 RED: failing FIFO tests: `05f7561f3` (`test(227-02)`)
3. Task 2 GREEN: FIFO queue, hook call sites, Y-14 comment: `0edd4a7c6` (`feat(227-02)`)

Tracer gate: the Task 1 `<verify>` commands were re-run end to end (round -> round exit 0; continuous exit 3; `npm run build` clean) before expansion.

## Verification Results

- `dispatch-mode.check.mjs`: `DISPATCH-PROBE round -> round` (exit 0); `--mode continuous` exit 3. PASS.
- `npx vitest run src/lib/engine`: 33 files, 703 tests passed. `npx vitest run src/hooks`: 40 files, 565 tests passed.
- `npm run lint`, `npm run build` (tsc -b + vite), `npm run knip` (exit 0): clean.
- Acceptance greps: `export type DispatchMode`, `dispatchMode?: DispatchMode`, `FLAWCHESS_DISPATCH_MODE: DispatchMode = 'round'`, one `dispatchMode: FLAWCHESS_DISPATCH_MODE` per hook, `D-19` fix-site comment: all PASS.
- RED evidence (Task 2): both target FIFO tests failed on their ordering assertions (`FEN_FIRST` expected first; `FEN_WAITING` expected, received `FEN_NEWER_0`) before the implementation change.

## Mutation Checks

- **Probe (T-227-03):** replaced `grader.settle(1)` with a comment. The check exited 1 with `DISPATCH-PROBE-UNEXPECTED: ...` instead of silently reporting round. Restored.
- **FIFO (T-227-04):** restored the UCI tie-break clause in `dequeueHighestPriority`. Both `serves equal-priority, equal-depth requests FIFO ...` and `FIFO: an earlier request is never overtaken by later equal requests` failed. Restored.

## Round-mode bit-identity statement (D-19)

The engine search code (`mctsSearch.ts` and everything under it) is untouched. Every existing c = 4 `mctsSearch`, `roundFill`, `deadlineSearch`, `selectBotMove` test passes unchanged. Node fixture gates use the harness pool, which was always FIFO. In the real-pool `workerPool.test.ts` suite, the only tests that changed are the one that asserted the old queue order itself (rewritten to FIFO) and two that depended on it incidentally (see Deviations); all other real-pool tests pass unchanged. In the browser, queue order can change which worker (and so which warm hash) grades a request on pool 2, which is within the accepted SEED-130 warm-hash nondeterminism.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug in plan] Probe grade-call count off by one**
- **Found during:** Task 1
- **Issue:** The plan said to require "exactly 2 recorded grade calls" after the root grade resolves, and read "a third grade call" as continuous. With `concurrency = 2` the engine fills both slots after the root applies, so 3 grade calls (root + 2 children) are recorded in both modes; continuous is observable only as a 4th call after one child settles.
- **Fix:** Expected count is `1 + PROBE_CONCURRENCY` (3); continuous is a call beyond that. Documented in the module doc comment.
- **Files modified:** `scripts/lib/dispatch-mode.mjs`
- **Commit:** `db59be43b`

**2. [Rule 2 - Missing critical] Probe self-verification and synthetic-search coverage**
- **Found during:** Task 1
- **Issue:** The planned mutation (skip resolving the second grade) would not trip a count-based probe: round observes "no further call" either way, so a probe that never settled anything would read round for every engine. The `'continuous'` verdict also could not be exercised before Plan 227-10.
- **Fix:** The probe asserts the root and exactly one in-flight grade were really settled before observing (throws the unexpected-shape error otherwise); `check.mjs` additionally runs the probe against synthetic round and continuous searches and checks the reverse mismatch exits 1.
- **Files modified:** `scripts/lib/dispatch-mode.mjs`, `scripts/lib/dispatch-mode.check.mjs`
- **Commit:** `db59be43b`

**3. [Rule 1 - Bug] Two real-pool tests depended on the old UCI tie-break**
- **Found during:** Task 2 (full engine run after the FIFO change)
- **Issue:** `an AbortSignal aborting an unstarted (still-pending) request removes it from the pending queue` timed out (it enqueued the abortable request first and relied on `'d7d5' < 'e7e5'` to dispatch the other one ahead of it). `stopAll() sends stop to every thinking slot...` relied on the same ordering in a comment but passed either way. Two comments in the gradeRoot pending-queue test described the old tie-break.
- **Fix:** Swapped the enqueue order of the two calls in both tests so the intended request is dispatched under FIFO; refreshed the stale comments. No production change beyond the planned one.
- **Files modified:** `frontend/src/lib/engine/__tests__/workerPool.test.ts`
- **Commit:** `0edd4a7c6`

**Total deviations:** 3 auto-fixed (2 Rule 1, 1 Rule 2). **Impact:** none on scope; all within the plan's files, and the round-mode statement above holds.

## Known Stubs

None. `dispatchMode` is intentionally inert (round) until Plan 227-10 adds the continuous loop and Plan 227-13 records the owner's ship decision.

## Threat Flags

None. No new network endpoints, auth paths or schema changes. T-227-03 and T-227-04 mitigated and mutation-checked; T-227-SC: no packages added (`npm ci` in the worktree only installs from the lockfile).

## Self-Check

- Created files exist: `scripts/lib/dispatch-mode.mjs`, `scripts/lib/dispatch-mode.check.mjs`: FOUND
- Commits `db59be43b`, `05f7561f3`, `0edd4a7c6` present on branch: FOUND
- No edits to `frontend/src/lib/engine/mctsSearch.ts`, no change to request priority/depth values, `FLAWCHESS_DISPATCH_MODE` is `'round'`.

## Self-Check: PASSED
