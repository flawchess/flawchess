---
phase: 155-react-hook-anytime-ui-free-analysis
plan: 02
subsystem: ui
tags: [react, typescript, hooks, mcts, stockfish, maia, vitest]

# Dependency graph
requires:
  - phase: 154-worker-pool-real-providers
    provides: "createWorkerPool() + createMaiaQueue() factories implementing the frozen EngineProviders contract, computePoolSize()"
  - phase: 153-pure-search-core
    provides: "mctsSearch (frozen SearchRunner), SearchBudget/RankedLine/EngineSnapshot/EngineProviders types"
  - phase: 155-01
    provides: "Wave 0 test scaffold for useFlawChessEngine.test.ts (it.todo placeholders)"
provides:
  - "useFlawChessEngine({ fen, enabled, elo }) hook — the single integration point Plan 04 mounts"
  - "onSnapshot leaky-bucket throttle mechanism (~150ms, immediate first commit)"
  - "Abort + pool.stopAll() regression guard on FEN navigation (Pitfall 1)"
affects: [155-04-Analysis-integration]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Leaky-bucket throttle for onSnapshot: commit immediately if >150ms since last commit, else schedule exactly one trailing commit of the LATEST snapshot, reset per fresh search for guaranteed first-paint"
    - "Provider lifecycle (WorkerPool + MaiaQueue) created once per enabled-lifetime in a useEffect gated on `enabled`, never recreated per FEN — mirrors useStockfishEngine's Worker-lifecycle effect"

key-files:
  created:
    - frontend/src/hooks/useFlawChessEngine.ts
  modified:
    - frontend/src/hooks/__tests__/useFlawChessEngine.test.ts

key-decisions:
  - "budget.elo = { w: elo, b: elo } — both colors share the single on-page ELO in free analysis (D-07/Open Question 2); true self/opponent asymmetry deferred to Phase 157"
  - "extraRootMoves left unset on SearchBudget (155-RESEARCH.md A5) — no wiring needed this phase"
  - "lastCommitAtRef reset to 0 at the start of every fresh mctsSearch call (not just on hook mount) so the FIRST onSnapshot of EVERY search paints immediately, not just the hook's initial mount"
  - "abortControllerRef.abort() + pool.stopAll() called unconditionally at the top of the search-trigger effect body (including the very first search, where stopAll is a harmless no-op) rather than only on subsequent navigations — matches 155-RESEARCH.md Pattern 2 literally and keeps the guard unconditional rather than conditionally skipped"

patterns-established:
  - "onSnapshot throttle: a distinct mechanism from the existing RAPID_STEP_DEBOUNCE_MS FEN-navigation debounce, reusing the same 150ms constant value for two different purposes (throttling output commits vs debouncing input navigation)"

requirements-completed: [DISPLAY-01]

coverage:
  - id: D1
    description: "useFlawChessEngine emits the first snapshot's ranked lines near-instantly and throttles subsequent onSnapshot commits at ~150ms (a throttle, not a debounce)"
    requirement: "DISPLAY-01"
    verification:
      - kind: unit
        ref: "frontend/src/hooks/__tests__/useFlawChessEngine.test.ts#throttle: first onSnapshot commits near-instantly; later snapshots throttle at ~150ms"
        status: pass
    human_judgment: false
  - id: D2
    description: "Navigating to a new FEN aborts the previous run's AbortController AND calls pool.stopAll() before starting the new mctsSearch (Pitfall 1 regression guard)"
    requirement: "DISPLAY-01"
    verification:
      - kind: unit
        ref: "frontend/src/hooks/__tests__/useFlawChessEngine.test.ts#abort: navigating to a new FEN aborts the previous run AND calls pool.stopAll()"
        status: pass
    human_judgment: false
  - id: D3
    description: "WorkerPool + MaiaQueue instances are created once per enabled-lifetime (lazy-spawn preserved), not per FEN, and terminated on cleanup; budget uses named tunable constants + shared-ELO pair + computePoolSize()-derived concurrency"
    verification:
      - kind: unit
        ref: "npx tsc -b --noEmit (type-check confirms shape) + npx vitest run src/hooks/__tests__/useFlawChessEngine.test.ts (both tests exercise the single-creation lifecycle indirectly via mock call counts)"
        status: pass
    human_judgment: false

# Metrics
duration: 10min
completed: 2026-07-06
status: complete
---

# Phase 155 Plan 02: useFlawChessEngine Hook (Anytime Emit, FEN Navigation, Abort/StopAll) Summary

**`useFlawChessEngine({ fen, enabled, elo })` wires the frozen `mctsSearch` SearchRunner against the real Phase 154 `WorkerPool`/`MaiaQueue` providers, throttling live `onSnapshot` output into React state at ~150ms while guaranteeing near-instant first paint and a Pitfall-1-safe abort+stopAll on every FEN navigation.**

## Performance

- **Duration:** 10 min
- **Started:** 2026-07-06T19:49:56+02:00
- **Completed:** 2026-07-06T19:57:04+02:00
- **Tasks:** 2
- **Files modified:** 2 (1 created, 1 filled-in test scaffold)

## Accomplishments
- `useFlawChessEngine.ts` created: provider lifecycle (`createWorkerPool()`/`createMaiaQueue()`) gated on `enabled`, created once per enabled-lifetime and terminated on cleanup — never recreated per FEN, preserving Phase 154's lazy-spawn + FEN-cache design
- Adaptive settled-vs-rapid FEN debounce reused verbatim from `useStockfishEngine.ts` (`RAPID_STEP_DEBOUNCE_MS = 150`)
- Pitfall 1 regression guard implemented: on every debounced FEN, `abortControllerRef.current?.abort()` AND `pool.stopAll()` both fire before the new `mctsSearch` call — the AbortSignal alone never reaches `dispatchExpansion`'s `policy()`/`grade()` calls, so `stopAll()` is load-bearing, not redundant
- `onSnapshot` leaky-bucket throttle implemented (NOT a debounce, Pitfall 3): immediate commit if >150ms since the last commit, else exactly one trailing commit of the LATEST snapshot; `lastCommitAtRef` is reset to 0 at the start of every fresh search so the first-paint guarantee holds for every navigation, not just the hook's initial mount
- Named tunable budget constants `FLAWCHESS_ENGINE_MAX_NODES` (400) and `FLAWCHESS_ENGINE_MAX_PLIES` (8, within the locked [6,10] SEED-082 band), `concurrency: computePoolSize()`, `elo: { w: elo, b: elo }` (D-07)
- Test scaffold's two `it.todo` placeholders converted to real tests: mocked `createWorkerPool`/`createMaiaQueue`/`mctsSearch` factories, driving `onSnapshot` directly via captured mock call args and asserting on the mocked pool's `stopAll` + `AbortSignal.aborted`

## Task Commits

Each task was committed atomically:

1. **Task 1: Implement useFlawChessEngine (provider lifecycle + FEN trigger + abort/stopAll + throttle)** - `6b06dcbe` (feat)
2. **Task 2: Fill in the hook test — throttle + abort/stopAll regression guards (DISPLAY-01)** - `fb0e1f27` (test)

**Plan metadata:** (this commit)

## Files Created/Modified
- `frontend/src/hooks/useFlawChessEngine.ts` - New hook: provider lifecycle, FEN debounce trigger, abort+stopAll guard, onSnapshot throttle, flat data return
- `frontend/src/hooks/__tests__/useFlawChessEngine.test.ts` - Wave 0 `it.todo` placeholders converted to real throttle + abort regression tests

## Decisions Made
- `budget.elo = { w: elo, b: elo }` — both colors share the single on-page ELO control in free analysis (D-07/Open Question 2); true self/opponent asymmetry is deferred to Phase 157's game-review overlay
- `extraRootMoves` left unset on `SearchBudget` (155-RESEARCH.md Assumption A5) — no wiring needed this phase
- `lastCommitAtRef` reset to 0 at the start of every fresh `mctsSearch` invocation (not only at hook-mount time), so the D-09 "first snapshot near-instant" guarantee holds on every FEN navigation, not just the initial mount
- `abortControllerRef.current?.abort()` + `pool.stopAll()` are called unconditionally at the top of the search-trigger effect (including the very first search, where `stopAll()` is a harmless no-op since nothing is in flight yet) — matches 155-RESEARCH.md Pattern 2's literal recommended shape rather than adding a conditional skip for the first call

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None. One test-authoring correction during Task 2: the first draft of the "abort" test asserted `pool.stopAll()` was NOT called before the first search — this contradicts the hook's actual (and intended) behavior of calling `stopAll()` unconditionally on every search including the first. Fixed by tracking the baseline call count before navigation and asserting the count strictly increased after navigating, rather than asserting zero prior calls. This was a test-fixture correction, not a hook bug (Rule 1 scope: fixed inline before the task commit, not tracked as a plan deviation since no plan-specified behavior changed).

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- `useFlawChessEngine` is ready for Plan 04's `Analysis.tsx` integration: returns `{ rankedLines, nodesEvaluated, budgetExhausted, isSearching, isReady }`, flat data only, no JSX
- Plan 03 (`FlawChessEngineLines.tsx`) can proceed independently — it only consumes `RankedLine[]`/`EngineSnapshot` shapes, not this hook directly
- Full frontend suite green: 126 passed / 1 skipped test files, 1509 passed / 2 todo tests (the remaining 2 todos are Plan 03's `FlawChessEngineLines.test.tsx` scaffold, out of this plan's scope); `npx tsc -b --noEmit` and `npm run lint` both clean

---
*Phase: 155-react-hook-anytime-ui-free-analysis*
*Completed: 2026-07-06*

## Self-Check: PASSED

Both created/modified source files and the SUMMARY.md itself verified present on disk; both commit hashes (6b06dcbe, fb0e1f27) verified present in git log.
