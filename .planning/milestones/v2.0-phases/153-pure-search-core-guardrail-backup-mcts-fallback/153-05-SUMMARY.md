---
phase: 153-pure-search-core-guardrail-backup-mcts-fallback
plan: 05
subsystem: engine
tags: [chess-engine, mcts, expectimax, search, typescript, guardrail]

# Dependency graph
requires:
  - phase: 153-01
    provides: types.ts (SearchBudget/EngineProviders/EngineSnapshot/RankedLine/MoveGrade), guardrail.ts (SearchRunner type), leafScore.ts (root-relative sigmoid conversion)
  - phase: 153-02
    provides: backup.ts (backupExpectation/backupRootMax Maia-prior-weighted backup rule)
  - phase: 153-03
    provides: select.ts (truncateAndRenormalize Maia top-k cut)
  - phase: 153-04
    provides: mctsSearch.ts (the primary SearchRunner orchestrator this plan swaps against)
provides:
  - fallbackExpectimax.ts — a depth-limited expectimax implementing the identical SearchRunner contract, reusing backup.ts/leafScore.ts/select.ts
  - SC5 swap-in proof — mctsSearch and fallbackExpectimax assigned to the same SearchRunner-typed variable and run with identical arguments
  - Green phase integration gate (lint, tsc -b, knip, full 1439-test suite) — closes out Phase 153
affects: [154-real-providers-worker-pool, 155-react-hook-anytime-ui]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Sequential (non-concurrent) recursive tree walk as a structurally simpler SearchRunner alternative to MCTS's select/expand/backup loop, still reusing the same pure primitives (backup.ts/leafScore.ts/select.ts) so score semantics cannot silently diverge between the two implementations"
    - "onSnapshot fires once per node-expansion event, propagating backup through already-visited ancestors — same D-10 contract as mctsSearch.ts, achieved via a path-array parameter through the recursion instead of an iterative dispatch loop"

key-files:
  created:
    - frontend/src/lib/engine/fallbackExpectimax.ts
    - frontend/src/lib/engine/__tests__/fallbackExpectimax.test.ts
  modified: []

key-decisions:
  - "fallbackExpectimax walks every child of every expanded node uniformly to budget.maxPlies (no PUCT/visit-based selection), bounded by budget.maxNodes as a hard expansion-event cap and AbortSignal — budget.concurrency is unused since there is no dispatch round to parallelize (purely sequential recursion)"
  - "modalPath and visits reuse the exact same 'most-visited continuation' semantics as mctsSearch.ts's buildModalPath, achieved by incrementing a per-node visits counter identically (node + all ancestors) on every backup propagation, for output-shape parity between the two SearchRunner implementations"
  - "Small tree-bookkeeping helpers (fenSide, terminalValue, applyUciMoveFen) are duplicated locally rather than imported from mctsSearch.ts (not exported, and not part of the reuse-mandated primitive set — RESEARCH Open Question 2 only requires reusing backup.ts/leafScore.ts/select.ts, the correctness-critical math)"
  - "npm run knip passed unchanged with no ignore entry needed — the vitest plugin already treats fallbackExpectimax.test.ts as an entry point covering the new export, so the anticipated knip caveat did not materialize"

requirements-completed: [ENGINE-06]

coverage:
  - id: D1
    description: "fallbackExpectimax.ts — depth-limited expectimax SearchRunner reusing backup.ts/leafScore.ts/select.ts, no reimplemented sigmoid/truncation/backup math"
    requirement: "ENGINE-06"
    verification:
      - kind: unit
        ref: "src/lib/engine/__tests__/fallbackExpectimax.test.ts#fallbackExpectimax — shared-primitive reuse > returns a non-empty rankedLines array sorted by practicalScore descending with UCI rootMove values"
        status: pass
      - kind: unit
        ref: "src/lib/engine/__tests__/fallbackExpectimax.test.ts#fallbackExpectimax — shared-primitive reuse > an unexpanded leaf's practicalScore matches evalToExpectedScore(grade, rootMover) exactly (leafScore.ts reuse)"
        status: pass
    human_judgment: false
  - id: D2
    description: "SC5 swap-in test — mctsSearch and fallbackExpectimax run through one SearchRunner-typed variable with identical (rootFen, budget, providers, onSnapshot, signal) arguments"
    requirement: "ENGINE-06"
    verification:
      - kind: unit
        ref: "src/lib/engine/__tests__/fallbackExpectimax.test.ts#fallbackExpectimax — SC5 guardrail swap-in > runs mctsSearch and fallbackExpectimax through the SAME SearchRunner-typed variable with identical arguments"
        status: pass
    human_judgment: false
  - id: D3
    description: "fallbackExpectimax determinism — bit-identical final snapshot and onSnapshot sequence across two repeated runs"
    verification:
      - kind: unit
        ref: "src/lib/engine/__tests__/fallbackExpectimax.test.ts#fallbackExpectimax — determinism > produces toEqual final snapshots AND toEqual full onSnapshot sequences across two repeated runs"
        status: pass
    human_judgment: false
  - id: D4
    description: "Phase 153 integration gate green: lint, tsc -b (zero errors), knip (unchanged, no ignore entry), full suite (122 files / 1439 tests)"
    requirement: "ENGINE-07"
    verification:
      - kind: other
        ref: "npm run lint && npx tsc -b && npm run knip && npm test -- --run"
        status: pass
    human_judgment: false

duration: 20min
completed: 2026-07-05
status: complete
---

# Phase 153 Plan 05: Depth-Limited Expectimax Fallback + Phase Gate Summary

**`fallbackExpectimax.ts` — a sequential depth-limited expectimax implementing the identical `SearchRunner` contract as `mctsSearch.ts`, reusing `backup.ts`/`leafScore.ts`/`select.ts` verbatim, proven via a same-variable SC5 swap-in test with the full Phase 153 gate (lint/tsc/knip/1439 tests) green.**

## Performance

- **Duration:** 20 min
- **Started:** 2026-07-05T23:44:00Z (approx.)
- **Completed:** 2026-07-05T23:54:07Z
- **Tasks:** 2
- **Files modified:** 2 (both created)

## Accomplishments
- `fallbackExpectimax.ts`: a full uniform depth-first expectimax walk to `budget.maxPlies`, bounded by `budget.maxNodes` and `AbortSignal`, that imports and reuses `backupExpectation`/`backupRootMax` (`backup.ts`), `leafExpectedScore` (`leafScore.ts`), and `truncateAndRenormalize` (`select.ts`) — no second copy of the sigmoid/truncation/backup math anywhere in the file
- SC5 swap-in proven: a single `SearchRunner`-typed variable is assigned `mctsSearch` then `fallbackExpectimax` and run with identical arguments, both returning valid `EngineSnapshot`s
- Fallback determinism verified (bit-identical repeated runs — trivially true given the purely sequential, non-concurrent walk)
- Closed the phase's knip caveat: `npm run knip` passed unchanged (the vitest entry-point plugin already covers the new export via the test file; no `knip.json` edit was required)
- Full Phase 153 integration gate green: `npm run lint` (0 errors), `npx tsc -b` (0 errors across the whole frontend), `npm run knip` (0 issues), `npm test -- --run` (122 test files, 1439 tests, all passing)

## Task Commits

Each task was committed atomically:

1. **Task 1: fallbackExpectimax.ts — depth-limited expectimax reusing shared primitives (ENGINE-06, SC5)** - `364a1cb2` (feat)
2. **Task 2: Swap-in test + phase integration gate (SC5, knip, lint, tsc, full suite)** - `e5f8e34f` (test)

## Files Created/Modified
- `frontend/src/lib/engine/fallbackExpectimax.ts` - depth-limited expectimax `SearchRunner`, reusing `backup.ts`/`leafScore.ts`/`select.ts`; local `FallbackNode` tree with sequential recursive `expandNode` (one policy+grade call = one expansion event, backup+onSnapshot per event, honors `AbortSignal` and `budget.maxNodes`)
- `frontend/src/lib/engine/__tests__/fallbackExpectimax.test.ts` - SC5 swap-in test (single `SearchRunner`-typed variable running both implementations), shared-primitive-reuse correctness tests, and a repeated-run determinism test

## Decisions Made
- `fallbackExpectimax` ignores `budget.concurrency` entirely — there is no dispatch round to parallelize in a purely sequential uniform-depth walk, so the field is simply unused by this runner (still accepted since it's part of the shared `SearchBudget` type both runners take)
- `modalPath`/`visits` on `RankedLine` reuse the same "most-visited continuation" semantics as `mctsSearch.ts` (a `visits` counter incremented on every node + ancestor during backup propagation), giving the two `SearchRunner` implementations comparable output shape even though the underlying selection strategy differs completely
- Small tree-bookkeeping helpers (`fenSide`, `terminalValue`, `applyUciMoveFen`) are duplicated locally in `fallbackExpectimax.ts` rather than imported from `mctsSearch.ts` — they aren't exported there and aren't part of RESEARCH Open Question 2's reuse mandate (only `backup.ts`/`leafScore.ts`/`select.ts`'s correctness-critical math is required to be shared)
- No `knip.json` edit was needed — the anticipated caveat (engine public surface consumed only by tests this phase) did not trip knip's vitest-plugin entry-point detection

## Deviations from Plan

None — plan executed exactly as written. The knip caveat anticipated in the plan's action text did not materialize (knip passed unchanged, as one of the two documented acceptable outcomes), so no `knip.json` edit was made.

## Issues Encountered
- ESLint flagged unused `_elo`/`_side` parameters in the test file's fabricated `policy()` fixture (the fixture didn't need to record calls, unlike `mctsSearch.test.ts`'s ELO-oracle variant). Fixed by dropping the unused parameters from the fixture's function signature (TypeScript allows a narrower-arity implementation of a wider function type) before committing Task 2 — resolved inline, not a plan deviation since it was fixed before any commit landed.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

Phase 153 (Pure Search Core: Guardrail + Backup + MCTS + Fallback) is complete — all 5 plans executed, all ENGINE-01 through ENGINE-07 requirements covered, full test suite green. `frontend/src/lib/engine/` now exposes the frozen public contract (`SearchRunner`, `types.ts`, `mctsSearch`, `fallbackExpectimax`) that Phase 154 (real Maia/Stockfish providers + worker pool) and Phase 155 (React hook + anytime UI) build against unchanged. No blockers.

---
*Phase: 153-pure-search-core-guardrail-backup-mcts-fallback*
*Completed: 2026-07-05*

## Self-Check: PASSED

- FOUND: frontend/src/lib/engine/fallbackExpectimax.ts
- FOUND: frontend/src/lib/engine/__tests__/fallbackExpectimax.test.ts
- FOUND commit: 364a1cb2
- FOUND commit: e5f8e34f
