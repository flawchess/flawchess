---
phase: 241-codebase-cleanup
plan: 59
subsystem: frontend-naming
tags: [cleanup, naming, analysis, rename]

requires:
  - phase: 241-04
    provides: "cleanup.py absent/diff tooling and rename-map canonicalization"
provides:
  - "Five analysis-surface renames from INVENTORY section 5, one refactor(naming) commit each"
  - "rename-maps/241-59.tsv with scoped rows for all five renames (six rows: PlayerBar and PlayerBarProps, storedTierByPly and storedTierByPlySize are separate rows)"
affects: [241-65]

actuals:
  tokens: 6000
  tasks: 3
  commits: 5
plan_head_before: de0c589be48490081fb7fd1395f04deb9f167a10
plan_head_after: f4bce39af7160712131115d3b8e63c62692d07dd

key-files:
  created:
    - .planning/phases/241-codebase-cleanup/rename-maps/241-59.tsv
  modified:
    - frontend/src/components/analysis/VariationTree.tsx
    - frontend/src/components/analysis/AnalysisPlayerBar.tsx
    - frontend/src/components/analysis/AnalysisBoardStage.tsx
    - frontend/src/pages/Analysis.tsx
    - frontend/src/components/analysis/EngineLines.tsx
    - frontend/src/components/analysis/FlawChessEngineLines.tsx
    - frontend/src/components/analysis/FlawChessAgreementVerdict.tsx
    - frontend/src/components/train/TrainLineChips.tsx
    - frontend/src/components/analysis/__tests__/FlawChessEngineLines.test.tsx
    - frontend/src/hooks/analysis/useAnalysisEngineLines.ts
    - frontend/src/hooks/analysis/useAnalysisGemMarkers.ts
    - frontend/src/hooks/useGemSweep.ts
    - frontend/src/hooks/analysis/__tests__/useAnalysisEngineLines.test.ts

key-decisions:
  - "Left two comment mentions of `PlayerBar` in AnalysisPlayerBar.tsx (the pasted-headers doc, lines 15 and 18) unchanged: they describe the board-level PlayerBar's freed clock slot, not the wrapper"
  - "Left the prose mention of PlayerBar in pages/__tests__/Analysis.test.tsx:2933 unchanged (outside files_modified; INVENTORY marks it prose only)"

requirements-completed: [D-04, D-06, D-07, D-17]

duration: ~25min
completed: 2026-10-16
status: complete
---

# Phase 241 Plan 59: Analysis surface renames Summary

**Five analysis-surface identifiers renamed to say what they hold (variant-named trees, `AnalysisPlayerBar`, `formatEval`, `storedGemGreatByPly`), with the board `PlayerBar` and OverallSection's `formatScore` left alone.**

## Accomplishments

| # | Rename | Commit | Files touched |
|---|--------|--------|---------------|
| a | `DesktopTree` → `VerticalTree` | 64781256f | VariationTree.tsx |
| b | `MobileTree` → `WrapTree` (incl. the `preview` JSDoc mention) | 94ac2365d | VariationTree.tsx |
| c | analysis wrapper `PlayerBar` → `AnalysisPlayerBar`, `PlayerBarProps` → `AnalysisPlayerBarProps` | 938c072c5 | AnalysisPlayerBar.tsx, AnalysisBoardStage.tsx, pages/Analysis.tsx |
| d | `formatScore` → `formatEval` | 2711dd505 | EngineLines.tsx, FlawChessEngineLines.tsx, FlawChessAgreementVerdict.tsx, train/TrainLineChips.tsx, __tests__/FlawChessEngineLines.test.tsx |
| e | `storedTierByPly` → `storedGemGreatByPly`, `storedTierByPlySize` → `storedGemGreatByPlySize` | f4bce39af | pages/Analysis.tsx, useAnalysisEngineLines.ts, useAnalysisGemMarkers.ts, useGemSweep.ts, __tests__/useAnalysisEngineLines.test.ts |

Scope guards held: `components/board/PlayerBar.tsx` is unmodified; `endgames/stats/OverallSection.tsx` still has 4 `formatScore` occurrences (unchanged); the testid `variation-tree-desktop` is unchanged (2 occurrences before and after); no alias, no helper consolidation.

## Verification

- Baseline (untouched tree): `npm run build` and `npm run lint` clean.
- After each commit: `npm run build` (tsc) and `npm run lint` clean; `cleanup.py absent` 0 hits (final: 5 rows checked); `cleanup.py diff --plan 241-59` clean on the touched files.
- Tests: VariationTree (29), analysis components + Analysis page (323), train components (1000 of 1001 pass), hooks/analysis + useGemSweep + Analysis page (140), source_scan_tests.sh (131).

## Deviations from Plan

None - plan executed exactly as written.

Note: one test in the broader `src/components/train` run (TrainStreakCard "streak up: the flame ignites...") failed once under the full parallel run and passed 24/24 when rerun alone. The file is not touched by this plan (animation timing flake), so it was not fixed.

## Known Stubs

None.

## Self-Check: PASSED

- rename-maps/241-59.tsv exists with scoped rows; all five renamed symbols present in the touched files, old names absent in scope.
- All five commits (64781256f, 94ac2365d, 938c072c5, 2711dd505, f4bce39af) are ancestors of HEAD.
