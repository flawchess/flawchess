---
phase: 241-codebase-cleanup
plan: 65
subsystem: frontend
tags: [naming, refactor, library-card]
requires: ["241-38", "241-40", "241-42", "241-51", "241-59"]
provides: [library-card-renames]
affects: [frontend/src/components/library, frontend/src/components/results, frontend/src/pages/Analysis.tsx]
key-files:
  created:
    - .planning/phases/241-codebase-cleanup/rename-maps/241-65.tsv
    - .planning/phases/241-codebase-cleanup/ledgers/241-65.txt
  modified:
    - frontend/src/components/library/EvalChart.tsx
    - frontend/src/components/results/LibraryGameCard.tsx
    - frontend/src/pages/Analysis.tsx
    - frontend/src/components/analysis/AnalysisTabs.tsx
    - frontend/src/components/results/__tests__/LibraryGameCard.test.tsx
    - frontend/src/components/library/TacticMotifChip.tsx
    - frontend/src/components/library/FlawCard.tsx
    - frontend/src/components/library/TacticMotifGroup.tsx
    - frontend/src/components/library/__tests__/TacticMotifChip.test.tsx
    - frontend/src/components/library/TagChip.tsx
    - frontend/src/components/analysis/AnalysisTagsPanel.tsx
requirements-completed: [D-06, D-07, D-09, D-10, D-17]
status: complete
commits: 5
plan_head_before: 9e9a9b676a174dcccffa3d7c8de39741ef181b6f
plan_head_after: 9f2385240
actuals:
  tasks: 3
  commits: 5
---

# Phase 241 Plan 65: Library-card renames Summary

Applied five INVENTORY section 5 renames to the Library card components (renames and comments only, no behavior or testid change).

## Renames

| Old | New | Commit | Files |
|-----|-----|--------|-------|
| `onHoverPlyChange` (EvalChart prop) + LibraryGameCard `hoverPly`/`setHoverPly` (D-09 group, one commit) | `onActivePlyChange` / `scrubPly`/`setScrubPly` | f6a968d89 | EvalChart.tsx, LibraryGameCard.tsx, pages/Analysis.tsx, AnalysisTabs.tsx, LibraryGameCard.test.tsx |
| `renderDesktopExploreButton` | `renderDesktopAnalyzeButton` | 0dc292f85 | LibraryGameCard.tsx |
| `passesContext` | `isUserMarker` | 10e86a066 | LibraryGameCard.tsx |
| `flawId` (TacticMotifChip prop) + INV-L960 | `gameId` | 1f7af1ef3 | TacticMotifChip.tsx, FlawCard.tsx, TacticMotifGroup.tsx, TacticMotifChip.test.tsx |
| `definition` (TagChip boolean prop) | `showDefinitionPopover` | 9f2385240 | TagChip.tsx, LibraryGameCard.tsx, FlawCard.tsx, AnalysisTagsPanel.tsx, TacticMotifChip.tsx (comments) |

- EvalChart's internal `hoverPly` state (real hover) kept its name: occurrence count in EvalChart.tsx unchanged at 17.
- testid templates (`chip-tactic-*-{id}`) keep their values; `definition` identifiers holding definition text (TacticMotifChip local, stats cards, GapPopover) untouched.
- The dead default popover path of TagChip stays (INVENTORY 7.1 #33).

## INV-L960

APPLIED in commit 1f7af1ef3 (see ledgers/241-65.txt). Re-verified: every TacticMotifChip caller passes a game id and TagChip has the `gameId` prop the JSDoc mirrors.

## Verification

Baseline (untouched tree) and after each task: `npm run build` (tsc) clean, `npm run lint` clean, Library/results/analysis tests pass (final run 502 passed), `source_scan_tests.sh` 131 passed, `cleanup.py absent` 6 rows 0 hits, `cleanup.py diff` passes for all touched files.

## Deviations from Plan

**Minor ordering note:** The `renderDesktopAnalyzeButton` commit (0dc292f85) was made before its rename-map row; the row landed in the next commit (10e86a066, `passesContext`). Gates were run on the combined tree before that second commit. No file outside files_modified was edited.

## Self-Check: PASSED
