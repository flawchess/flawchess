---
phase: 241-codebase-cleanup
plan: 61
subsystem: frontend
tags: [naming, rename, refactor, frontend]
requires: ["241-02", "241-03", "241-04", "241-31", "241-43", "241-44", "241-45", "241-50", "241-51"]
provides:
  - EvalConfidencePopover / ScoreConfidenceTooltip naming pair
  - hasAvgEval (PositionResultsPanel)
  - useEvalCoverage hasPendingEvals field
affects: [frontend/src/components/insights, frontend/src/hooks/useEvalCoverage.ts]
tech-stack:
  added: []
  patterns: [rename-map TSV rows with canon_paths scoping for the diff check]
key-files:
  created:
    - .planning/phases/241-codebase-cleanup/rename-maps/241-61.tsv
    - frontend/src/components/insights/EvalConfidencePopover.tsx
    - frontend/src/components/insights/ScoreConfidenceTooltip.tsx
    - frontend/src/components/insights/__tests__/ScoreConfidenceTooltip.test.tsx
  modified:
    - frontend/CLAUDE.md
    - frontend/src/components/charts/PositionResultsPanel.tsx
    - frontend/src/hooks/useEvalCoverage.ts
    - frontend/src/components/EvalCoverageHeader.tsx
key-decisions:
  - "Renamed the Props interfaces together with their components (EvalConfidencePopoverProps, ScoreConfidenceTooltipProps)"
requirements-completed: [D-06, D-07, D-09, D-17]
status: complete
commits: 3
plan_head_before: de0c589be48490081fb7fd1395f04deb9f167a10
plan_head_after: 361b2087a8d3c7064ee2684e5a02223e279b3501
actuals:
  tokens: 40000
  tasks: 3
  commits: 3
duration: 14 min
completed: 2026-10-16
---

# Phase 241 Plan 61: Confidence component, hasAvgEval and hasPendingEvals renames Summary

Pure renames: the confidence popover/tooltip pair now reads Eval/Score, PositionResultsPanel's eval flag is `hasAvgEval`, and useEvalCoverage's `isPending` field is `hasPendingEvals`, with no behavior, testid or Umami key change.

## Renames

| Old | New | Commit | Files touched |
|-----|-----|--------|---------------|
| BulletConfidencePopover (file, component, Props) | EvalConfidencePopover | da2bb3b98 | insights/EvalConfidencePopover.tsx, OpeningFindingCard(.test), ScoreConfidencePopover, EvalConfidenceTooltip (comment), OpeningStatsCard + test, EvalCpuPlaceholder.test, PositionResultsPanel, Openings.statsBoard.test |
| WdlConfidenceTooltip (file, component, Props, test file) | ScoreConfidenceTooltip | da2bb3b98 (same D-09 commit) | insights/ScoreConfidenceTooltip.tsx, __tests__/ScoreConfidenceTooltip.test.tsx, ScoreConfidencePopover, MoveExplorer, frontend/CLAUDE.md |
| hasMgEval (PositionResultsPanel only) | hasAvgEval | 4c6c4e086 | charts/PositionResultsPanel.tsx |
| useEvalCoverage `isPending` | hasPendingEvals | 361b2087a | hooks/useEvalCoverage.ts, EvalCoverageHeader.tsx, 12 tests (below) |

`hasMgEval` stays in OpeningStatsCard.tsx (7), OpeningFindingCard.tsx (7) and the Openings.statsBoard test replica (7); counts unchanged. PositionResultsPanel went 8 to 0.

## isPending counts (before to after, per file)

| File | Before | After |
|------|--------|-------|
| hooks/useEvalCoverage.ts | 3 | 0 |
| components/EvalCoverageHeader.tsx | 3 | 0 |
| components/__tests__/EvalCoverageHeader.test.tsx | 5 | 0 |
| __tests__/noEndgameSkillString.test.tsx | 1 | 0 |
| components/insights/OpeningFindingCard.test.tsx | 1 | 0 |
| pages/__tests__/Endgames.filterVisibility / overallPerformance / readinessGate | 2 each | 1 each (useEndgameInsights mutation mock kept) |
| pages/__tests__/Import.pasteHandoff / queuedState / stateMachine / feedbackAsk | 2 each | 1 each (useImportTrigger mock kept) |
| hooks/__tests__/useEvalCoverage.test.tsx (not in plan list) | 1 | 0 |

## Verification

build (tsc -b), lint, knip (no findings beyond 2 pre-existing config hints), insights/stats/charts/move-explorer/Openings.statsBoard tests (289 pass), hooks + EvalCoverageHeader + noEndgameSkillString + OpeningFindingCard + Endgames + Import tests (916 pass), source_scan_tests.sh (131 pass), `absent` (8 rows, 0 hits) and `diff --plan 241-61` (clean, with `--outside frontend/CLAUDE.md` for the popover group) all pass. Baseline gates were green on the untouched tree.

## Deviations from Plan

**1. [Rule 3 - Blocking] hooks/__tests__/useEvalCoverage.test.tsx also reads `result.current.isPending`**
- **Found during:** Task 3 (grep of readers)
- **Issue:** Not in the plan's files list; would fail after the field rename.
- **Fix:** Renamed the one assertion to `hasPendingEvals` and added the file to the row's canon_paths.
- **Commit:** 361b2087a

**2. [Scope extension] Props interfaces renamed with their components**
- `BulletConfidencePopoverProps` and `WdlConfidenceTooltipProps` are not whole-word matches of the old names; renamed for consistency and given rename-map rows (da2bb3b98).

**3. Rename map covers files under rename-maps/241-61.tsv rows**: the `.tsx` file-stem rows are informational only (the toolkit expands only `.py` file rows); the identifier rows carry the canonicalization.

**Total deviations:** 1 auto-fixed (Rule 3), 1 consistency extension. **Impact:** none on behavior.

## Known Stubs

None.

## Self-Check: PASSED

Created files exist (EvalConfidencePopover.tsx, ScoreConfidenceTooltip.tsx, its test, 241-61.tsv); commits da2bb3b98, 4c6c4e086, 361b2087a are on HEAD.
