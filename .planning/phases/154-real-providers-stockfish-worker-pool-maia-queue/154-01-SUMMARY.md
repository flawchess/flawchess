---
phase: 154-real-providers-stockfish-worker-pool-maia-queue
plan: 01
subsystem: engine
tags: [stockfish, wasm, web-worker, priority-queue, mcts, vitest]

# Dependency graph
requires:
  - phase: 153-pure-search-core-guardrail-backup-mcts-fallback
    provides: "Frozen EngineProviders/SearchBudget/RankedLine/EngineSnapshot contract; MoveGrade type; the useStockfishGradingEngine single-worker precedent this pool generalizes"
provides:
  - "workerPool.ts: createWorkerPool() factory implementing EngineProviders.grade() with a real 2-4-worker Stockfish.wasm pool"
  - "Priority queue (enqueue/dequeueHighestPriority) scheduling grading work toward highest-priority requests first, never FIFO"
  - "computePoolSize(): device-adaptive pool sizing (mobile=2, desktop=clamp(cores-2,2,4))"
  - "Lazy spawn, AbortSignal-per-call, stopAll(), terminate() lifecycle surface for Phase 155 to consume"
affects: [155-react-hook-anytime-ui, maiaQueue.ts]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "N independent copies of an already-shipped single-worker UCI state machine (useStockfishGradingEngine), coordinated by a priority queue instead of a rewrite"
    - "Plain array + linear max-scan priority queue (no heap library) — correct and fast enough at this workload's scale"
    - "Pool-level (not per-worker) FIFO grade cache, keyed by FEN"
    - "Lazy Worker spawn on first call, graceful-degradation floor (per-slot try/catch) instead of throwing on construction failure"

key-files:
  created:
    - frontend/src/lib/engine/workerPool.ts
    - frontend/src/lib/engine/__tests__/workerPool.test.ts
  modified: []

key-decisions:
  - "grade() enqueues internal requests with priority=0/depth=0 (no priority channel exists on the frozen 2-arg EngineProviders.grade signature) — the priority QUEUE machinery itself is fully built and unit-tested per POOL-02, ready for a future caller that supplies real priorities; wiring an actual root-line-derived priority value is out of this plan's scope (Claude's Discretion per CONTEXT.md)"
  - "AbortSignal is an ADDITIONAL third parameter beyond EngineProviders.grade's frozen 2-arg signature — TypeScript's optional-parameter assignability rule keeps pool.grade structurally assignable to EngineProviders['grade'], verified by a type-level test"
  - "Info lines with a non-'exact' bound (lowerbound/upperbound) are dropped rather than committed to the accumulator, avoiding alpha-beta search jitter in the grade map"
  - "terminate() clears slots via slots.length = 0 (not reassignment) to keep the pool's internal state a stable const across the closure"

patterns-established:
  - "Pattern: forking an already-proven single-instance Worker state machine into an N-instance pool via a priority queue, rather than inventing a new worker protocol"

requirements-completed: [POOL-01, POOL-02, POOL-04]

coverage:
  - id: D1
    description: "grade(fen, candidateUcis) returns a Map keyed by pv[0] (the UCI move), white-POV cp, never by the multipv rank index"
    requirement: POOL-01
    verification:
      - kind: unit
        ref: "frontend/src/lib/engine/__tests__/workerPool.test.ts#grade() resolves a Map keyed by pv[0] (UCI), white-POV normalized"
        status: pass
      - kind: unit
        ref: "frontend/src/lib/engine/__tests__/workerPool.test.ts#multipv-rank-swap regression: two lines swapping multipv rank between depths stay keyed by their own move"
        status: pass
    human_judgment: false
  - id: D2
    description: "A higher-priority pending grade request dispatches to a free worker before a lower-priority one enqueued earlier (not FIFO)"
    requirement: POOL-02
    verification:
      - kind: unit
        ref: "frontend/src/lib/engine/__tests__/workerPool.test.ts#dequeues the higher-priority request first, regardless of enqueue order"
        status: pass
      - kind: unit
        ref: "frontend/src/lib/engine/__tests__/workerPool.test.ts#breaks a priority tie by shallower depth first"
        status: pass
      - kind: unit
        ref: "frontend/src/lib/engine/__tests__/workerPool.test.ts#breaks a priority+depth tie by ascending candidateUcis[0] string"
        status: pass
    human_judgment: false
  - id: D3
    description: "Pool size is 2 on mobile (hardwareConcurrency<=4 OR pointer:coarse) and clamp(cores-2,2,4) on desktop"
    requirement: POOL-04
    verification:
      - kind: unit
        ref: "frontend/src/lib/engine/__tests__/workerPool.test.ts#computePoolSize (all 6 branch cases)"
        status: pass
    human_judgment: false
  - id: D4
    description: "The pool exposes a clean abort/lifecycle surface: optional AbortSignal per grade() call plus stopAll()/terminate()"
    requirement: POOL-04
    verification:
      - kind: unit
        ref: "frontend/src/lib/engine/__tests__/workerPool.test.ts#stopAll() sends stop to every thinking slot and clears the pending queue"
        status: pass
      - kind: unit
        ref: "frontend/src/lib/engine/__tests__/workerPool.test.ts#terminate() calls worker.terminate() on every slot"
        status: pass
      - kind: unit
        ref: "frontend/src/lib/engine/__tests__/workerPool.test.ts#an AbortSignal aborting an unstarted (still-pending) request removes it from the pending queue"
        status: pass
    human_judgment: false
  - id: D5
    description: "Workers are spawned lazily on first grade() and terminated on teardown; no eager page-load spawn"
    requirement: POOL-04
    verification:
      - kind: unit
        ref: "frontend/src/lib/engine/__tests__/workerPool.test.ts#D-02: no Worker is constructed until the first grade() call (lazy spawn)"
        status: pass
      - kind: unit
        ref: "frontend/src/lib/engine/__tests__/workerPool.test.ts#a later grade() call re-spawns workers after terminate()"
        status: pass
    human_judgment: false
  - id: D6
    description: "SC4 real-device mobile-memory-ceiling UAT (no tab reload/crash across a multi-position review session)"
    verification: []
    human_judgment: true
    rationale: "No React hook/UI exists to drive the pool until Phase 155 wires it into /analysis — this is a HUMAN-UAT gate deferred by design, recorded in 154-VALIDATION.md Manual-Only Verifications per the plan's own verification section"

# Metrics
duration: 15min
completed: 2026-07-06
status: complete
---

# Phase 154 Plan 01: Stockfish Worker Pool Summary

**`workerPool.ts` — a lazily-spawned, device-adaptive 2-4 Stockfish.wasm worker pool implementing `EngineProviders.grade()` with a priority-queued, pv[0]-keyed, abortable dispatch surface**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-07-06T16:03:00Z (approx.)
- **Completed:** 2026-07-06T16:18:18Z
- **Tasks:** 3
- **Files modified:** 2 (both new)

## Accomplishments
- `enqueue`/`dequeueHighestPriority`: a plain-array priority queue (priority desc, then depth asc, then ascending `candidateUcis[0]` — never insertion order), unit-proven not-FIFO (POOL-02)
- `computePoolSize()`: device-adaptive sizing — mobile (`hardwareConcurrency<=4` OR coarse pointer) always 2, desktop `clamp(cores-2, 2, 4)` — no UA-sniffing, no `deviceMemory` (POOL-04/D-01)
- `createWorkerPool()`: N independent `idle`/`thinking`/`stopping` worker-slot state machines (reproducing `useStockfishGradingEngine`'s stop-before-go/FLAWCHESS-7V discipline per-slot), dispatching via the priority queue; `grade()` resolves a `Map<uci, MoveGrade>` keyed by `pv[0]`, white-POV normalized, with a multipv-rank-swap regression test proving identity is never derived from the reordering `multipv` rank field (POOL-01, SC5)
- Single pool-level per-FEN grade cache (FIFO, `GRADE_CACHE_MAX`) shared across all slots — a repeat `grade()` for an already-graded FEN issues no new `go`
- Lazy spawn on first `grade()` call (D-02), optional `AbortSignal` per `grade()` call, `stopAll()`, and `terminate()` (which resets internal state so a later `grade()` re-spawns) — the full abort/lifecycle surface Phase 155 will consume (D-03)
- Graceful-degradation floor: a per-slot worker construction failure is caught, leaving a smaller live pool instead of throwing (Pitfall 1)
- SC5 grep audit clean: no `.multipv` read anywhere in `workerPool.ts` as a grade-map key

## Task Commits

Each task was committed atomically:

1. **Task 1: Priority queue + adaptive pool-size heuristic** - `82af431b` (feat)
2. **Task 2: Per-worker slot state machine + grade() dispatch** - `98880be0` (feat)
3. **Task 3: Pool factory + abort/lifecycle surface + SC5 grep audit** - `6a498b9e` (feat)

_Note: TDD RED tests (compile/import failures) were verified before each implementation commit but were not committed separately — each task's test additions and implementation landed together in one commit per the task's own scope, since the RED state was a transient pre-commit verification step, not a standalone deliverable._

## Files Created/Modified
- `frontend/src/lib/engine/workerPool.ts` (391 lines) - `createWorkerPool` factory, `WorkerPool`/`PoolWorkerSlot`/`QueuedGradeRequest` types, `enqueue`/`dequeueHighestPriority`/`computePoolSize` pure functions, all tunable constants
- `frontend/src/lib/engine/__tests__/workerPool.test.ts` (406 lines) - mock-Worker vitest suite: priority-queue ordering/tie-breaks, computePoolSize branches, pv[0]-keying + rank-swap regression, cache-hit, concurrent-slot dispatch, lazy-spawn, stopAll/terminate, AbortSignal, type-level EngineProviders.grade assignability, graceful-degradation floor

## Decisions Made
- `grade()`'s internal `QueuedGradeRequest` uses `priority: 0, depth: 0` for every call, since the frozen 2-arg `EngineProviders.grade(fen, candidateUcis)` signature has no channel for a caller-supplied priority. The priority queue's ORDERING logic (POOL-02) is fully built and unit-tested via direct `enqueue`/`dequeueHighestPriority` calls; wiring a real root-line-derived priority value into `grade()` itself is explicitly Claude's Discretion / out of this phase's scope per CONTEXT.md, and is a natural extension point for Phase 155's `mctsSearch.ts` integration if it turns out to matter in practice.
- `pool.grade`'s third `signal?: AbortSignal` parameter keeps the function structurally assignable to `EngineProviders['grade']` (TypeScript's optional-trailing-parameter assignability rule) — verified with a type-level `const providerGrade: EngineProviders['grade'] = pool.grade` test.
- Info lines with `bound !== 'exact'` (lowerbound/upperbound) are dropped rather than written into a slot's accumulator, avoiding alpha-beta search-window jitter in the returned grades.

## Deviations from Plan

None — plan executed exactly as written. All three tasks' `<behavior>`/`<action>`/`<acceptance_criteria>` were implemented and verified as specified; no bugs, missing critical functionality, or blocking issues were encountered.

## Issues Encountered

One test-design correction during Task 3 authoring (not a deviation from the PLAN, a self-caught test bug): the initial `stopAll()`/AbortSignal tests assumed the FIRST-enqueued `grade()` call would occupy the first-ready worker slot, but the priority queue's own tie-break rule (ascending `candidateUcis[0]` string) actually dispatches whichever request has the lexicographically smaller candidate UCI first when priorities and depths tie. Corrected the tests' assertions to match the queue's real (and correct) tie-break behavior before running them green — no production code changed as a result.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

`workerPool.ts` is a complete, unit-tested implementation of `EngineProviders.grade()` ready for Phase 155 to import and wire into a React hook alongside `maiaQueue.ts` (Plan 02 of this phase). The abort/lifecycle surface (`signal` param, `stopAll()`, `terminate()`) is the exact shape Phase 155's `useFlawChessEngine.ts` needs to gate the pool against the standalone `useStockfishEngine` eval bar (D-03) — no further shape changes anticipated. SC4's real-device mobile-memory-ceiling UAT remains deferred to Phase 155 (no UI exists yet to drive it), tracked in `154-VALIDATION.md` Manual-Only Verifications.

---
*Phase: 154-real-providers-stockfish-worker-pool-maia-queue*
*Completed: 2026-07-06*

## Self-Check: PASSED

- FOUND: frontend/src/lib/engine/workerPool.ts
- FOUND: frontend/src/lib/engine/__tests__/workerPool.test.ts
- FOUND: commit 82af431b
- FOUND: commit 98880be0
- FOUND: commit 6a498b9e
