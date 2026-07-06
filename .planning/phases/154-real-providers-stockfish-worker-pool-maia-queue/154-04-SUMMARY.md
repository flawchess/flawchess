---
phase: 154-real-providers-stockfish-worker-pool-maia-queue
plan: 04
subsystem: engine
tags: [maiaQueue, web-worker, sentry, vitest, gap-closure]

# Dependency graph
requires:
  - phase: 154-02
    provides: maiaQueue.ts requestPolicy pipeline + worker lifecycle (dedup/cache/FIFO/SAN-UCI, terminate/Sentry)
  - phase: 154-VERIFICATION
    provides: reproduced CR-03 deadlock (Truth #6 FAILED) + WR-03 async-onerror gap
provides:
  - handleMessage's error branch drains `pending` (not just `currentBatch`) and drops the dead worker when a `{type:'error'}` message arrives pre-ready, so the queue self-heals instead of deadlocking permanently (CR-03)
  - worker.onerror handler in ensureSpawned() capturing async Worker script-load failures to Sentry under the `maia-queue-worker` tag, settling every affected promise (WR-03)
  - shared settleAllAndDropWorker() helper reused by both failure paths
affects: [155-react-hook-anytime-ui]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Web Worker lifecycle self-heal: on any unrecoverable worker failure (pre-ready message error OR async onerror), settle every stranded promise to {} and null the worker reference so the next call re-spawns fresh, rather than leaving a permanently-dead worker referenced."

key-files:
  created: []
  modified:
    - frontend/src/lib/engine/maiaQueue.ts
    - frontend/src/lib/engine/__tests__/maiaQueue.test.ts

key-decisions:
  - "Task 1 committed as a standalone inline fix (no shared helper yet) to keep its commit self-contained and independently green; Task 2 then extracted the shared settleAllAndDropWorker() helper and layered the onerror handler on top, per the plan's explicit permission to factor shared logic in Task 2"
  - "Post-ready worker-error path (worker still alive) is unchanged: resolves currentBatch and calls processQueue() to keep serving the rest of the queue -- only the pre-ready and async-onerror paths (worker unrecoverable) reset isReady and drop the worker"

requirements-completed: [POOL-03]

coverage:
  - id: D1
    description: "A worker {type:'error'} arriving before 'ready' drains every pending policy() promise (resolves each to {}) and drops the dead worker so a subsequent policy() call spawns a fresh Worker instead of hanging forever (CR-03)"
    requirement: "POOL-03"
    verification:
      - kind: unit
        ref: "frontend/src/lib/engine/__tests__/maiaQueue.test.ts > drains pending and drops the dead worker on a PRE-READY error, so a later policy() re-spawns a fresh Worker (CR-03)"
        status: pass
    human_judgment: false
  - id: D2
    description: "An asynchronous worker.onerror (script-load failure) is captured to Sentry under the maia-queue-worker source tag and settles every pending/in-flight policy() promise instead of hanging (WR-03)"
    requirement: "POOL-03"
    verification:
      - kind: unit
        ref: "frontend/src/lib/engine/__tests__/maiaQueue.test.ts > captures an asynchronous worker.onerror (script-load failure) to Sentry, settles the pending promise, and re-spawns on the next policy() call (WR-03)"
        status: pass
    human_judgment: false

duration: 20min
completed: 2026-07-06
status: complete
---

# Phase 154 Plan 04: maiaQueue Worker-Error Deadlock Gap Closure Summary

**Closed the reproduced CR-03 pre-ready worker-init-error deadlock in maiaQueue.ts and added the missing async worker.onerror handler (WR-03), so a Maia ONNX worker failure now self-heals instead of permanently hanging every policy() promise.**

## Performance

- **Duration:** ~20 min
- **Completed:** 2026-07-06
- **Tasks:** 2/2 completed
- **Files modified:** 2

## Accomplishments

- `handleMessage`'s `error` branch now drains `pending` (not just `currentBatch`, which is null pre-ready) and drops the dead worker (`terminate()` + `worker = null`, leaving `isReady = false`) whenever the error arrives before the worker ever reported `ready` — the permanent no-drop-FIFO deadlock (154-VERIFICATION Truth #6 / CR-03) is closed.
- Added `w.onerror` in `ensureSpawned()` to catch asynchronous Worker script-load failures (404 / CSP / syntax error) that `new Worker(...)` never throws synchronously for — these previously hung every queued request with zero Sentry visibility (WR-03).
- Extracted a shared `settleAllAndDropWorker()` helper reused by both failure paths (pre-ready message-error and async onerror), keeping the self-heal contract in one place.
- The existing post-ready worker-error path (worker still alive) is untouched — it still resolves only `currentBatch` and calls `processQueue()` to keep serving the rest of the queue.
- Two new regression tests added; all 18 tests in `maiaQueue.test.ts` pass (16 pre-existing + 2 new), full frontend suite (124 files, 1498 tests) green, `npm run lint` and `npx tsc -b` both clean.

## Task Commits

Each task was committed atomically:

1. **Task 1: Drain pending + drop dead worker on a pre-ready worker error (CR-03)** - `44203a20` (fix)
2. **Task 2: worker.onerror handler for async Worker script-load failure (WR-03)** - `7cec5839` (feat)

_Note: both tasks were TDD (RED test written and confirmed failing/hanging against pre-fix source, then GREEN implementation), but combined into a single commit per task rather than separate `test(...)`/`feat(...)` commits — consistent with this phase's established per-task commit granularity (see 154-01/02/03 decisions in STATE.md)._

## Files Created/Modified

- `frontend/src/lib/engine/maiaQueue.ts` - `handleMessage`'s error branch drains `pending` and drops the dead worker on a pre-ready error; new `settleAllAndDropWorker()` helper; `ensureSpawned()` gains a `w.onerror` handler for async script-load failures
- `frontend/src/lib/engine/__tests__/maiaQueue.test.ts` - `MockWorker` gains `onerror`/`simulateError()`; two new regression tests (pre-ready-error self-heal, async-onerror self-heal)

## Decisions Made

- Task 1 committed as a standalone inline fix (no shared helper) so its commit is self-contained and independently verifiable; Task 2 then extracted `settleAllAndDropWorker()` and added the `onerror` handler on top, per the plan's explicit instruction that Task 2 may factor shared logic with Task 1.
- The post-ready worker-error case is deliberately left unchanged — the worker is still alive in that case, so continuing to serve the queue via `processQueue()` is correct and was already tested (existing test at former lines 268-280, now earlier in the file after the two Task 1/2 tests were inserted).

## Deviations from Plan

None — plan executed exactly as written for both tasks. Both RED tests were authored first and confirmed hanging (5s timeout) against the pre-fix source before implementing the GREEN fix, per the plan's TDD instruction.

## Verification Results

- `cd frontend && npm test -- --run src/lib/engine/__tests__/maiaQueue.test.ts` — 18/18 pass.
- `cd frontend && npm run lint` — 0 errors (3 pre-existing unrelated warnings in `coverage/` generated files).
- `cd frontend && npx tsc -b` — 0 errors.
- Full frontend suite: `npm test -- --run` — 124 test files, 1498 tests, all passing (no regressions).
- 154-VERIFICATION.md Truth #6 re-verified: the scratch-test scenario (policy() issued, pre-ready `{type:'error'}` emitted) now resolves the pending promise to `{}` (was: timeout) and a following `policy()` constructs a new Worker (`createdWorkers` length 2).
- WR-03 re-verified: `worker.onerror` present in `ensureSpawned`; the onerror test asserts the `maia-queue-worker` Sentry tag and a re-spawn on the next call.
- Module docstring guarantee (maiaQueue.ts lines 26-29: "a construction failure or a worker error settles every affected promise instead of leaving it hanging") now holds for the pre-ready message-error path AND the async script-load-error path, not just construction/currentBatch.

## Threat Flags

None — both threats in the plan's threat register (T-154-04-01 CR-03, T-154-04-02 WR-03) were the explicit `mitigate` targets of Task 1 and Task 2 respectively; no new unaddressed surface introduced.

## Next Steps

- Phase 154 is now fully gap-closed (154-01 through 154-04 all complete). Per STATE.md, the recommended next step is `/gsd-plan-phase 155` (React hook + anytime UI), which will be the first real caller of `maiaQueue.policy()` via `mctsSearch.dispatchExpansion`.

## Self-Check: PASSED

- FOUND: frontend/src/lib/engine/maiaQueue.ts
- FOUND: frontend/src/lib/engine/__tests__/maiaQueue.test.ts
- FOUND: .planning/phases/154-real-providers-stockfish-worker-pool-maia-queue/154-04-SUMMARY.md
- FOUND: commit 44203a20
- FOUND: commit 7cec5839
