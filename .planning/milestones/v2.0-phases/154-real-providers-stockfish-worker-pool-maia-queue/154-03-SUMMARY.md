---
phase: 154-real-providers-stockfish-worker-pool-maia-queue
plan: 03
subsystem: engine
tags: [stockfish, worker-pool, sentry, tdd, gap-closure]

# Dependency graph
requires:
  - phase: 154-01
    provides: adaptive pool sizing, priority queue, lazy spawn/abort surface for workerPool.ts
  - phase: 154-02
    provides: maiaQueue.ts's terminate()/Sentry/graceful-degradation precedent, mirrored here
provides:
  - stopAll()/terminate() reliably settle every in-flight grade() promise (CR-01, CR-02 closed)
  - grade() fail-fast guards for a pre-aborted signal (WR-01) and an empty candidateUcis array (WR-05)
  - Sentry-visible worker failures (async onerror + sync construction throw) under a stockfish-worker-pool tag (WR-03, WR-04)
  - an all-slots-dead pool drains any still-pending request instead of hanging it
  - corrected module/priority-queue docstrings that no longer overstate present-tense priority-ordered dispatch (WR-02, deferred to Phase 155)
affects: [155-mcts-hook-anytime-ui]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Settle-before-null: resolve slot.current with an empty Map BEFORE nulling it in every lifecycle/failure path (stopAll, terminate, onerror), so no grade() promise can be left permanently unresolved."
    - "Per-slot dead flag (not inferred from isReady) drives the pool-wide noLiveSlotRemains() drain check — avoids a false-positive during normal not-yet-ready startup."

key-files:
  created: []
  modified:
    - frontend/src/lib/engine/workerPool.ts
    - frontend/src/lib/engine/__tests__/workerPool.test.ts

key-decisions:
  - "stopAll()/terminate() resolve slot.current with new Map() and null it before the eventual stale bestmove reaches handleLine's existing stopPending/FLAWCHESS-7V discard guard, which already tolerates slot.current === null."
  - "Added a dedicated PoolWorkerSlot.dead boolean rather than inferring 'all slots failed' from isReady === false, since isReady is also false during normal not-yet-initialized startup — an inferred check would false-positive and drain valid pending requests before workers ever get a chance to become ready."
  - "grade() checks slots.length === 0 immediately after ensureSpawned() and resolves empty rather than enqueuing, covering the case where every slot construction attempt threw."
  - "WR-02 (priority channel unreachable) is a documentation-only fix this plan: corrected the file header and priority-queue section docstrings to state request priority/depth are currently always 0 under the frozen 2-arg grade() contract, deferring real priority wiring to Phase 155 per the plan's deferred_findings."

requirements-completed: [POOL-01, POOL-02, POOL-04]

coverage:
  - id: D1
    description: "stopAll() and terminate() settle every in-flight grade() promise with an empty Map instead of hanging (CR-01, CR-02)"
    requirement: POOL-04
    verification:
      - kind: unit
        ref: "frontend/src/lib/engine/__tests__/workerPool.test.ts#stopAll() sends stop to every thinking slot and clears the pending queue"
        status: pass
      - kind: unit
        ref: "frontend/src/lib/engine/__tests__/workerPool.test.ts#CR-02: terminate() resolves an in-flight (dispatched) grade() promise instead of hanging it"
        status: pass
    human_judgment: false
  - id: D2
    description: "grade() fails fast and empty on an already-aborted signal or an empty candidateUcis array, without spawning a worker (WR-01, WR-05)"
    requirement: POOL-04
    verification:
      - kind: unit
        ref: "frontend/src/lib/engine/__tests__/workerPool.test.ts#WR-01: a pre-aborted signal resolves grade() empty immediately with zero Worker constructions"
        status: pass
      - kind: unit
        ref: "frontend/src/lib/engine/__tests__/workerPool.test.ts#WR-05: an empty candidateUcis array resolves grade() empty without dispatching a go message"
        status: pass
    human_judgment: false
  - id: D3
    description: "Async worker.onerror and synchronous construction failures are Sentry-captured under a stockfish-worker-pool tag and settle affected promises; an all-slots-dead pool drains pending requests (WR-03, WR-04)"
    requirement: POOL-01
    verification:
      - kind: unit
        ref: "frontend/src/lib/engine/__tests__/workerPool.test.ts#WR-04: worker.onerror settles the in-flight request and is Sentry-captured with the stockfish-worker-pool tag"
        status: pass
      - kind: unit
        ref: "frontend/src/lib/engine/__tests__/workerPool.test.ts#graceful-degradation floor: a slot construction failure still leaves a smaller live pool, not a throw"
        status: pass
      - kind: unit
        ref: "frontend/src/lib/engine/__tests__/workerPool.test.ts#WR-04: once every slot has failed via onerror, a still-pending (never-dispatched) request drains instead of hanging"
        status: pass
    human_judgment: false
  - id: D4
    description: "Module header and priority-queue docstrings no longer claim present-tense priority-ordered dispatch (WR-02)"
    requirement: POOL-02
    verification:
      - kind: other
        ref: "grep -n 'Phase 155' frontend/src/lib/engine/workerPool.ts"
        status: pass
    human_judgment: false

# Metrics
duration: 25min
completed: 2026-07-06
status: complete
---

# Phase 154 Plan 03: workerPool.ts Gap Closure (stopAll/terminate hang defects + observability) Summary

**Closed two reproduced lifecycle promise-hang defects (CR-01 stopAll, CR-02 terminate) plus abort/input/observability gaps in the Stockfish worker pool, so no `grade()` promise can be left permanently unresolved.**

## Performance

- **Duration:** 25 min
- **Started:** 2026-07-06T15:16:00Z (approx.)
- **Completed:** 2026-07-06T15:40:52Z
- **Tasks:** 3
- **Files modified:** 2

## Accomplishments
- `stopAll()` and `terminate()` now resolve every dispatched (`slot.current`) in-flight `grade()` promise with an empty `Map` before nulling it, closing CR-01/CR-02 — Phase 155's `mctsSearch.dispatchExpansion` can safely `await grade()` and call `stopAll()`/`terminate()` on unmount/navigation without deadlocking.
- `grade()` fails fast and empty (no Worker construction, no enqueue) for an already-aborted `AbortSignal` (WR-01) and for an empty `candidateUcis` array (WR-05), before the cache lookup or `ensureSpawned()`.
- Async `worker.onerror` (script 404/CSP/syntax error) and synchronous `new Worker` construction throws are both Sentry-captured under a `stockfish-worker-pool` source tag; an onerror-failed slot is marked permanently dead (`slot.dead`) and its in-flight request settles; if every slot ends up dead, any still-pending (never-dispatched) request also drains instead of hanging forever.
- Corrected the misleading present-tense "dispatches work toward the currently-highest-scoring root line first" claim in the file header and priority-queue docstring — the ordering machinery is real and unit-tested, but every request currently carries `priority: 0, depth: 0` under the frozen 2-arg `EngineProviders.grade` contract (WR-02, deferred to Phase 155).

## Task Commits

Each task was committed atomically (all TDD RED-then-GREEN within a single feat/fix commit per task, per this plan's `type="auto" tdd="true"` tasks):

1. **Task 1: Settle in-flight requests on stopAll()/terminate() (CR-01, CR-02, IN-04)** - `eea4ec83` (fix)
2. **Task 2: Fail-fast grade() input guards (WR-01, WR-05)** - `e8636e48` (fix)
3. **Task 3: Worker-failure observability + WR-02 docstring honesty (WR-03, WR-04)** - `d12b884c` (fix)

## Files Created/Modified
- `frontend/src/lib/engine/workerPool.ts` - Added settle-in-flight-before-null to `stopAll()`/`terminate()`; added `candidateUcis.length === 0` and `signal?.aborted` early-return guards at the top of `grade()`; added `@sentry/react` import, a `worker.onerror` handler with a new `PoolWorkerSlot.dead` flag, a `noLiveSlotRemains()`/`drainPending()` pair, a non-empty `ensureSpawned()` construction-failure catch, and a `slots.length === 0` post-spawn guard in `grade()`; corrected the file header and priority-queue section docstrings.
- `frontend/src/lib/engine/__tests__/workerPool.test.ts` - Removed the `void second;` line that masked CR-01 and replaced it with an awaited resolution assertion; added a dedicated terminate-in-flight test (CR-02), pre-aborted-signal and empty-candidateUcis tests (WR-01/WR-05), a `worker.onerror` Sentry+settle test and an all-slots-dead-drains-pending test (WR-04), and extended the graceful-degradation test with a Sentry-capture assertion (WR-03); added the `vi.mock('@sentry/react', ...)` module mock and a `MockWorker.simulateError()` helper.

## Decisions Made
- Used a dedicated `PoolWorkerSlot.dead` boolean rather than inferring "all slots failed" from `isReady === false`, because `isReady` is also `false` during normal not-yet-initialized startup — an inference-based check would false-positive and drain valid pending requests before any worker gets the chance to become ready.
- `grade()` checks `slots.length === 0` right after `ensureSpawned()` and resolves empty immediately, covering the case where every slot's construction attempt threw (rather than draining inside `ensureSpawned()` itself, keeping the pool-spawn and request-resolution concerns separate).
- WR-02 is a documentation-only correction this plan, per the plan's own `<deferred_findings>`: the priority channel itself is deliberately NOT wired (no real caller exists until Phase 155's MCTS orchestrator), so only the misleading present-tense docstring claim was fixed.

## Deviations from Plan

None - plan executed exactly as written. All three tasks followed the plan's TDD RED-then-GREEN action prescriptions; no unplanned functionality was added, no architectural changes were needed, and no auth gates were encountered.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- `workerPool.ts` is now safe for Phase 155's `mctsSearch.dispatchExpansion` to `await grade()` and call `stopAll()`/`terminate()` on the D-03 "engine wins, pause the eval bar" gate, on unmount, and on navigation — no lifecycle or failure path can leave a `grade()` promise permanently unresolved.
- WR-02 (real priority/depth values from the MCTS orchestrator) remains an open Phase 155 requirement, tracked forward per this plan's `<deferred_findings>`.
- All pre-existing workerPool tests remain green (28/28 in this file; 1496/1496 across the full frontend suite); `npm run lint` and `npx tsc -b` both pass with zero errors.
- Plan 154-04 (maiaQueue.ts gap closure) is the remaining sibling plan in this phase's gap-closure wave.

---
*Phase: 154-real-providers-stockfish-worker-pool-maia-queue*
*Completed: 2026-07-06*

## Self-Check: PASSED

- FOUND: frontend/src/lib/engine/workerPool.ts
- FOUND: frontend/src/lib/engine/__tests__/workerPool.test.ts
- FOUND: .planning/phases/154-real-providers-stockfish-worker-pool-maia-queue/154-03-SUMMARY.md
- FOUND commits: eea4ec83 (Task 1), e8636e48 (Task 2), d12b884c (Task 3)
