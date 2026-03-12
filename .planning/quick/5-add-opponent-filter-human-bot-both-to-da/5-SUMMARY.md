---
phase: quick-5
plan: 1
subsystem: analysis
tags: [filter, opponent, frontend, backend]
dependency_graph:
  requires: [quick-4]
  provides: [opponent_type filter end-to-end]
  affects: [analysis API, FilterPanel, Dashboard]
tech_stack:
  added: []
  patterns: [ToggleGroup single-select for required filter, Literal union default value]
key_files:
  created: []
  modified:
    - app/schemas/analysis.py
    - app/repositories/analysis_repository.py
    - app/services/analysis_service.py
    - frontend/src/types/api.ts
    - frontend/src/components/filters/FilterPanel.tsx
    - frontend/src/pages/Dashboard.tsx
    - tests/test_analysis_repository.py
decisions:
  - opponent_type defaults to "human" (not null) — required field with fixed default, not optional filter
  - Tests updated with opponent_type="both" to preserve existing behavior (no filter applied)
metrics:
  duration: 6min
  completed_date: "2026-03-12"
  tasks: 2
  files: 7
---

# Quick Task 5: Add Opponent Filter (Human / Bot / Both) Summary

**One-liner:** Human/Bot/Both toggle in More filters wired end-to-end through `is_computer_game` DB column, defaulting to Human to exclude computer games from analysis.

## Tasks Completed

| # | Task | Commit |
|---|------|--------|
| 1 | Add opponent_type filter to backend schema and repository | 6b2d254 |
| 2 | Add opponent filter UI to FilterPanel and wire through Dashboard | 011e56a |

## What Was Built

**Backend:**
- `AnalysisRequest.opponent_type: Literal["human", "bot", "both"] = "human"` — required field with default, placed after `rated`
- `_build_base_query` applies `Game.is_computer_game == False` for "human", `== True` for "bot", no filter for "both"
- `query_all_results` and `query_matching_games` both accept and forward `opponent_type`
- `analysis_service.analyze` passes `opponent_type=request.opponent_type` at both call sites

**Frontend:**
- `OpponentType = 'human' | 'bot' | 'both'` type and `opponent_type?: OpponentType` added to `AnalysisRequest` in `api.ts`
- `FilterState.opponentType: OpponentType` with `DEFAULT_FILTERS.opponentType = 'human'`
- Opponent `ToggleGroup` (Human / Bot / Both) inserted in More filters directly below Rated
- `Dashboard.tsx` passes `opponent_type: filters.opponentType` in both `handleAnalyze` and `handlePageChange`
- Empty-state hint updated to mention opponent filter

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Updated test_analysis_repository.py with new required parameter**
- **Found during:** Task 1 verification (tests failed)
- **Issue:** All direct repository calls in tests were missing the new `opponent_type` parameter
- **Fix:** Added `opponent_type="both"` to all 11 test call sites — preserves existing test behavior (no filter applied)
- **Files modified:** `tests/test_analysis_repository.py`
- **Commit:** 6b2d254 (included in Task 1 commit)

## Verification

- 175 tests pass (`uv run pytest tests/ -x -q`)
- `uv run ruff check` passes with no errors
- `npm run build` passes with no TypeScript errors
- Default filter state sends `opponent_type: "human"` — computer games excluded unless Bot or Both selected

## Self-Check: PASSED

- app/schemas/analysis.py: opponent_type field present
- app/repositories/analysis_repository.py: is_computer_game filter applied
- frontend/src/components/filters/FilterPanel.tsx: Opponent ToggleGroup present
- Commits 6b2d254 and 011e56a exist
