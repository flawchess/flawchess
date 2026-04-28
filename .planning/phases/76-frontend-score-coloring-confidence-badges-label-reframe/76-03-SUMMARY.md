---
phase: 76-frontend-score-coloring-confidence-badges-label-reframe
plan: 03
subsystem: ui
tags: [react, typescript, vitest, arrowColor, openingInsights, score-based-coloring]

# Dependency graph
requires:
  - phase: 75-backend-score-metric-confidence-annotation
    provides: "SCORE_PIVOT, MINOR_EFFECT_SCORE, MAJOR_EFFECT_SCORE additive constants in arrowColor.ts"

provides:
  - "getArrowColor(score, gameCount, isHovered) with score-based effect-size buckets"
  - "LIGHT_COLOR_THRESHOLD and DARK_COLOR_THRESHOLD removed from arrowColor.ts"
  - "MIN_GAMES_FOR_INSIGHT, INSIGHT_RATE_THRESHOLD, INSIGHT_THRESHOLD_COPY removed from openingInsights.ts"
  - "Score-based boundary tests in arrowColor.test.ts (25 tests, all green)"
  - "Regression guard in openingInsights.test.ts for removed constants"

affects: [76-05-PLAN, MoveExplorer.tsx call site update in Plan 05]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "score-based effect-size color buckets: >=0.60 DARK_GREEN, >=0.55 LIGHT_GREEN, <=0.40 DARK_RED, <=0.45 LIGHT_RED"
    - "TDD RED/GREEN with per-phase commit sequence: test commit then feat commit"

key-files:
  created: []
  modified:
    - frontend/src/lib/arrowColor.ts
    - frontend/src/lib/arrowColor.test.ts
    - frontend/src/lib/openingInsights.ts
    - frontend/src/lib/openingInsights.test.ts

key-decisions:
  - "arrowSortKey kept with existing (color: string) signature — plan's interface section was aspirational; actual implementation unchanged"
  - "OPENING_INSIGHTS_POPOVER_COPY goes in OpeningInsightsBlock.tsx (JSX co-location), not openingInsights.ts — avoids .ts to .tsx rename"

patterns-established:
  - "Score-based color encoding: score in [0,1], pivot 0.50, strict >= / <= boundaries matching backend classification"

requirements-completed:
  - INSIGHT-UI-01
  - INSIGHT-UI-02
  - INSIGHT-UI-06

# Metrics
duration: 12min
completed: 2026-04-28
---

# Phase 76 Plan 03: arrowColor Score-Based Rewrite and openingInsights Cleanup Summary

**getArrowColor rewritten to score-based (W+0.5D)/N buckets with strict >=/<= boundaries; dead win/loss-rate constants and stale openingInsights exports removed; 38 tests green**

## Performance

- **Duration:** 12 min
- **Started:** 2026-04-28T16:12:00Z
- **Completed:** 2026-04-28T16:16:30Z
- **Tasks:** 3 (TDD: 1 RED commit + 1 GREEN commit + 1 refactor commit)
- **Files modified:** 4

## Accomplishments
- Rewrote `getArrowColor` from `(winPct, lossPct, gameCount, isHovered)` to `(score, gameCount, isHovered)` using score-based effect-size thresholds from Phase 75
- Removed dead constants `LIGHT_COLOR_THRESHOLD` and `DARK_COLOR_THRESHOLD` from `arrowColor.ts`; `npm run knip` green
- Removed stale `MIN_GAMES_FOR_INSIGHT = 20`, `INSIGHT_RATE_THRESHOLD = 55`, `INSIGHT_THRESHOLD_COPY` from `openingInsights.ts`
- Added 25 score-based boundary tests in `arrowColor.test.ts` and regression guard in `openingInsights.test.ts`

## Task Commits

Each task was committed atomically:

1. **Task 1: Rewrite arrowColor.test.ts for score-based signature (TDD RED)** - `0e941f9` (test)
2. **Task 2: Rewrite getArrowColor body and signature; remove dead constants (TDD GREEN)** - `c8019aa` (feat)
3. **Task 3: Clean up openingInsights.ts and rewrite its test** - `fc72b10` (refactor)

**Plan metadata:** committed as part of this summary commit

_Note: Tasks 1 and 2 form a TDD RED/GREEN pair as required by the plan._

## Files Created/Modified
- `frontend/src/lib/arrowColor.ts` - New score-based `getArrowColor` signature and body; removed `LIGHT_COLOR_THRESHOLD`, `DARK_COLOR_THRESHOLD`
- `frontend/src/lib/arrowColor.test.ts` - Full rewrite with 25 score-based boundary tests (Phase 76 RED/GREEN TDD)
- `frontend/src/lib/openingInsights.ts` - Removed 3 stale exports; added JSX co-location note for popover copy
- `frontend/src/lib/openingInsights.test.ts` - Dropped stale-constant describe block; added regression guard for removed exports

## Decisions Made
- `arrowSortKey` kept as `(color: string): number` — the plan's `<interfaces>` section showed `(score, gameCount)` aspirationally but task 2 explicitly said "Keep unchanged: arrowSortKey". The existing color-string API is correct.
- `OPENING_INSIGHTS_POPOVER_COPY` stays in `OpeningInsightsBlock.tsx` (JSX co-location per PATTERNS.md Open Question 3 answer). Documented in `openingInsights.ts` leading comment.

## Deviations from Plan

None — plan executed exactly as written. The `arrowSortKey` interface discrepancy in the plan's `<interfaces>` section vs. task 2 instructions was resolved by following the more specific task-level instruction ("Keep unchanged").

## Issues Encountered
- Frontend dependencies were not installed in the worktree — ran `npm install` before first test run. Not a deviation, just worktree setup.
- `npx tsc --noEmit` expected to fail at `MoveExplorer.tsx:228` (old 4-arg `getArrowColor` call site). This is documented in the plan as acceptable mid-wave; Plan 05 (Wave 3) fixes the call site.

## User Setup Required
None — no external service configuration required.

## Next Phase Readiness
- `getArrowColor(score, gameCount, isHovered)` is ready for Plan 05 (MoveExplorer call-site update)
- `openingInsights.ts` is clean; `getSeverityBorderColor` and `trimMoveSequence` remain for Plans 06 and 07
- `npm run knip` green; all 38 lib tests green

---
*Phase: 76-frontend-score-coloring-confidence-badges-label-reframe*
*Completed: 2026-04-28*
