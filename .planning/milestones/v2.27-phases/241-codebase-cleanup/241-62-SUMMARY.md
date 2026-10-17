---
phase: 241-codebase-cleanup
plan: 62
subsystem: frontend
tags: [naming, refactor, endgames, charts]
requires: [241-02, 241-03, 241-04, 241-42, 241-43, 241-51]
provides:
  - endgame-insights report names unified (insights / insightBySection / generateState)
  - rename-maps/241-62.tsv
affects: [frontend/src/components/endgames, frontend/src/components/insights, frontend/src/components/charts, frontend/src/components/library]
key-files:
  created:
    - .planning/phases/241-codebase-cleanup/rename-maps/241-62.tsv
  modified:
    - frontend/src/components/endgames/useEndgameInsightsState.ts
    - frontend/src/components/endgames/EndgameStatsTab.tsx
    - frontend/src/components/insights/EndgameInsightsBlock.tsx
    - frontend/src/components/insights/__tests__/EndgameInsightsBlock.test.tsx
    - frontend/src/components/endgames/stats/TypeTable.tsx
    - frontend/src/components/charts/EndgameScoreOverTimeChart.tsx
    - frontend/src/components/endgames/stats/OverallSection.tsx
    - frontend/src/components/charts/__tests__/EndgameScoreOverTimeChart.test.tsx
    - frontend/src/components/endgames/EndgameStatsTab.test.tsx
    - frontend/src/components/charts/EndgameEloTimelineSection.tsx
    - frontend/src/components/endgames/stats/rankedMetrics.ts
    - frontend/src/components/library/analysisCoverageCopy.ts (renamed from .tsx)
decisions:
  - "RenderedState.response alignment skipped (D-08 optional)"
status: complete
commits: 6
plan_head_before: de0c589be48490081fb7fd1395f04deb9f167a10
plan_head_after: 47faa5ac9f4693dd6855cf4bf30941d29856c2f2
actuals:
  tokens: 6000
  tasks: 3
  commits: 6
---

# Phase 241 Plan 62: Endgame stats and chart renames Summary

Applied the INVENTORY section 5 endgame-stats and chart renames (one D-09 group plus five renames, one a file extension change) with no behavior change.

## Renames

| Old | New | Commit | Files |
|-----|-----|--------|-------|
| `matchingInsights`, `sectionBySection`, EndgameInsightsBlock props `rendered` / `hasRendered` / `mutation` (D-09 group) | `insights`, `insightBySection`, `insights` / `hasInsights` / `generateState` | 176d46d2a | useEndgameInsightsState.ts, EndgameStatsTab.tsx, EndgameInsightsBlock.tsx, EndgameInsightsBlock.test.tsx |
| `vsEngineValue`, `VS_ENGINE_DOMAIN` | `achievableScoreGapValue`, `ACHIEVABLE_SCORE_GAP_DOMAIN` | 5efc4293f | TypeTable.tsx |
| EndgameScoreOverTimeChart prop `window` | `windowSize` | 99aa322d3 | EndgameScoreOverTimeChart.tsx, OverallSection.tsx, EndgameScoreOverTimeChart.test.tsx, EndgameStatsTab.test.tsx |
| `barChartData` | `chartDataWithVolume` | 6789e287c | EndgameEloTimelineSection.tsx |
| `MIN_PERCENT` / `MAX_PERCENT` | `PERCENTILE_DISPLAY_MIN` / `PERCENTILE_DISPLAY_MAX` | 86b53ef56 | rankedMetrics.ts |
| analysisCoverageCopy.tsx | analysisCoverageCopy.ts (R100, no import changes) | 47faa5ac9 | analysisCoverageCopy.ts |

Kept as specified: the global `window` uses (useIsMobile in the chart), the `data-window` attributes, `hooks/useEngineAssets.ts` `MIN_PERCENT`/`MAX_PERCENT`, and all testids. `insights` was checked and was not already bound in the hook or the block scope.

## Verification

Baseline gates on the untouched tree were green. After all renames: `npm run build` (tsc), `npm run lint`, `npm run knip` (only the two pre-existing configuration hints), vitest for `src/components/endgames`, `src/components/charts`, `src/components/insights` and `src/components/library` (all pass), the frontend source-scan tests (9 files, 131 tests), `cleanup.py absent` (9 rows, 0 hits) and `cleanup.py diff --plan 241-62` all pass.

## Deviations from Plan

None - plan executed exactly as written. The Python half of `source_scan_tests.sh` was not run (frontend-only plan, no Python files touched). A few English-prose comment lines that describe the renamed props in EndgameInsightsBlock.tsx and the block test were updated to the new names.

## Known Stubs

None.

## Self-Check: PASSED

All six commits exist on the worktree branch; rename-maps/241-62.tsv and analysisCoverageCopy.ts are present.
