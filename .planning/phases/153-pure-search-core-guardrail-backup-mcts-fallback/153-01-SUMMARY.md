---
phase: 153-pure-search-core-guardrail-backup-mcts-fallback
plan: 01
subsystem: engine
tags: [typescript, engine-core, search, sigmoid, vitest]

# Dependency graph
requires: []
provides:
  - "frozen SearchRunner/EngineProviders/SearchBudget/RankedLine/EngineSnapshot types (types.ts + guardrail.ts)"
  - "leafExpectedScore() root-relative leaf-eval-to-expected-score conversion (leafScore.ts)"
affects: [153-02-backup, 153-03-select, 153-04-mctsSearch, 153-05-fallbackExpectimax, 154-real-providers, 155-react-hook]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Engine core type surface lives in lib/engine/types.ts; MoveGrade is re-exported from moveQuality.ts, never redeclared"
    - "SearchRunner is a frozen function type in guardrail.ts with no logic — both mctsSearch and fallbackExpectimax implement it identically"
    - "rootMover threaded as a constant (computed once via sideToMoveFromFen(rootFen)) through every leaf-score conversion — no per-ply sign flip"

key-files:
  created:
    - frontend/src/lib/engine/types.ts
    - frontend/src/lib/engine/guardrail.ts
    - frontend/src/lib/engine/leafScore.ts
    - frontend/src/lib/engine/__tests__/leafScore.test.ts
  modified: []

key-decisions:
  - "MoveGrade is imported from @/lib/moveQuality and re-exported from types.ts (single import surface for the engine), not redeclared as a structurally-duplicate interface."
  - "leafExpectedScore() wraps liveFlaw.ts's evalToExpectedScore() verbatim — no new sigmoid or mate-cp-equivalent constant."
  - "Mate-near-certainty test thresholds set to 0.95/0.05 (not 0.99/0.01) to match the actual MATE_CP_EQUIVALENT sigmoid output (~0.975/~0.025) rather than an arbitrarily tighter bound."

patterns-established:
  - "Pattern: root-relative score frame — leafExpectedScore(grade, rootMover) always takes rootMover as a caller-supplied constant, never recomputed per node."

requirements-completed: [ENGINE-05, ENGINE-06]

coverage:
  - id: D1
    description: "Frozen SearchRunner/EngineProviders/SearchBudget/RankedLine/EngineSnapshot interface compiles and matches D-04/D-06/D-07/D-08/D-09"
    requirement: "ENGINE-06"
    verification:
      - kind: unit
        ref: "npx tsc -b (zero errors for engine/types.ts and engine/guardrail.ts)"
        status: pass
    human_judgment: false
  - id: D2
    description: "leafExpectedScore() converts a leaf's white-POV Stockfish eval to a root-relative expected score, proven mirrored (not identical) across root colors"
    requirement: "ENGINE-05"
    verification:
      - kind: unit
        ref: "frontend/src/lib/engine/__tests__/leafScore.test.ts (5 tests, all pass)"
        status: pass
    human_judgment: false

duration: 12min
completed: 2026-07-05
status: complete
---

# Phase 153 Plan 01: Frozen Engine Interface + Root-Relative Leaf Score Summary

**Locked `SearchRunner`/`EngineProviders`/`SearchBudget`/`RankedLine`/`EngineSnapshot` contract plus `leafExpectedScore()`, a root-relative wrapper around the existing lichess sigmoid, proven mirrored across root colors by a 5-case fixture test.**

## Performance

- **Duration:** 12 min
- **Started:** 2026-07-05T20:57:30Z (approx, per STATE.md `last_updated` at execution start)
- **Completed:** 2026-07-05T21:00:00Z
- **Tasks:** 2
- **Files modified:** 4 (all new)

## Accomplishments
- `frontend/src/lib/engine/types.ts` establishes the single frozen type surface for the whole v2.0 FlawChess Engine milestone — `Side`, `EngineProviders`, `SearchBudget` (color-keyed `elo: {w, b}`, `extraRootMoves?`), `RankedLine` (root-relative `practicalScore`), `EngineSnapshot` — with `MoveGrade` re-exported from `moveQuality.ts` rather than redeclared.
- `frontend/src/lib/engine/guardrail.ts` establishes the `SearchRunner` function type that both the primary MCTS orchestrator (153-04) and the fallback expectimax (153-05) will implement identically — no logic in this file, only the type.
- `frontend/src/lib/engine/leafScore.ts` wraps `evalToExpectedScore()` from `liveFlaw.ts` with zero reimplementation, converting a leaf's white-POV Stockfish eval into the ROOT player's expected score using `rootMover` as a caller-threaded constant.
- `frontend/src/lib/engine/__tests__/leafScore.test.ts` proves the single subtlest correctness detail in the whole phase: the SAME white-POV `+200cp` grade reads `>0.5` for a White root and `<0.5` for a Black root (mirrored around 0.5, not identical) — plus mate-in-3 and null/null degenerate cases.

## Task Commits

Each task was committed atomically:

1. **Task 1: Frozen engine interface (types.ts + guardrail.ts)** - `deb5c2b1` (feat)
2. **Task 2: Root-relative leaf score wrapper + frame fixture (ENGINE-05)** - `91aeb179` (feat)

_Note: no TDD tasks in this plan — both are `type="auto"` per PLAN.md._

## Files Created/Modified
- `frontend/src/lib/engine/types.ts` - Frozen `Side`/`EngineProviders`/`SearchBudget`/`RankedLine`/`EngineSnapshot` types; re-exports `MoveGrade` from `@/lib/moveQuality`
- `frontend/src/lib/engine/guardrail.ts` - `SearchRunner` function type shared by `mctsSearch` and `fallbackExpectimax`
- `frontend/src/lib/engine/leafScore.ts` - `leafExpectedScore(grade, rootMover)` root-relative eval-to-expected-score wrapper
- `frontend/src/lib/engine/__tests__/leafScore.test.ts` - Root-Relative Frame Fixture (5 tests: white-root, black-root, mate both colors, null/null neutral)

## Decisions Made
- `MoveGrade` re-exported from `@/lib/moveQuality` in `types.ts` rather than redeclared, per RESEARCH "MoveGrade Reuse" — one import surface for the engine core.
- Mate-in-3 near-certainty test assertions use `0.95`/`0.05` thresholds (not `0.99`/`0.01`) after discovering the actual sigmoid output for `MATE_CP_EQUIVALENT` is `~0.975`/`~0.025` — tightening the assertion to the true numeric behavior rather than an arbitrary bound the sigmoid doesn't actually hit.

## Deviations from Plan

None - plan executed exactly as written. The one test-threshold adjustment (0.99→0.95, 0.01→0.05) was a same-task correction made while writing the fixture, not a deviation from the plan's `<action>`/`<acceptance_criteria>` (which specify "near 1.0"/"near 0.0" without a literal numeric bound) — no separate commit or Rule invocation needed.

## Issues Encountered
None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- `types.ts` and `guardrail.ts` are the frozen contract 153-02 (backup.ts), 153-03 (select.ts), 153-04 (mctsSearch.ts), and 153-05 (fallbackExpectimax.ts) will all import against unchanged.
- `leafScore.ts`'s `leafExpectedScore()` is ready to be called from `backup.ts`/`mctsSearch.ts` wherever a `MoveGrade` needs converting into a value fed to the backup rule.
- No blockers. `EngineProviders`, `SearchBudget`, `RankedLine`, `EngineSnapshot`, and `MoveGrade` are not yet imported by any consumer other than this plan's own test file — expected, since 153-02 through 153-05 are the consumers, not this plan.

---
*Phase: 153-pure-search-core-guardrail-backup-mcts-fallback*
*Completed: 2026-07-05*

## Self-Check: PASSED
