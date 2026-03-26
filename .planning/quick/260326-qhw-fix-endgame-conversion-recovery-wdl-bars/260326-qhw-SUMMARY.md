---
phase: quick
plan: 260326-qhw
subsystem: endgame-analytics
tags: [frontend, backend, charts, endgames]
dependency_graph:
  requires: []
  provides: [granular-conversion-recovery-wdl]
  affects: [EndgameWDLChart, endgame_service, endgames_schema]
tech_stack:
  added: []
  patterns: [3-segment-wdl-bar, granular-stat-fields]
key_files:
  created: []
  modified:
    - app/schemas/endgames.py
    - app/services/endgame_service.py
    - frontend/src/types/endgames.ts
    - frontend/src/components/charts/EndgameWDLChart.tsx
    - tests/test_endgame_service.py
decisions:
  - recovery_saves kept as derived field (wins + draws) for backward compatibility
  - conversion_losses computed as (games - wins - draws) rather than tracked separately, consistent with schema field
metrics:
  duration: ~12 minutes
  completed: 2026-03-26
  tasks_completed: 2
  files_modified: 5
---

# Quick Task 260326-qhw: Fix Endgame Conversion/Recovery WDL Bars Summary

**One-liner:** Expanded conversion/recovery mini-bars from 2-segment (win/loss and save/loss) to full 3-segment W/D/L bars by adding granular draw/loss fields to both backend schema and frontend renderer.

## Tasks Completed

| # | Task | Commit | Files |
|---|------|--------|-------|
| 1 | Add granular W/D/L fields to backend schema and service | f151f9d | app/schemas/endgames.py, app/services/endgame_service.py, tests/test_endgame_service.py |
| 2 | Update frontend types and render 3-segment conversion/recovery bars | a868425 | frontend/src/types/endgames.ts, frontend/src/components/charts/EndgameWDLChart.tsx |

## What Changed

### Backend (Task 1)

**`app/schemas/endgames.py` — `ConversionRecoveryStats`:**
- Added `conversion_draws: int` — draws when up material
- Added `conversion_losses: int` — losses when up material (= conversion_games - wins - draws)
- Added `recovery_wins: int` — wins when down material
- Added `recovery_draws: int` — draws when down material
- Kept `recovery_saves: int` for backward compatibility (derived as wins + draws)

**`app/services/endgame_service.py` — `_aggregate_endgame_stats()`:**
- Changed `conv` accumulator to track `draws` in addition to `wins`
- Changed `recov` accumulator to track `wins` and `draws` separately (replacing `saves`)
- `recovery_saves` now derived as `wins + draws` when constructing the schema object
- `conversion_losses` computed from `games - wins - draws`

**`tests/test_endgame_service.py`:**
- `test_conversion_pct_per_category`: Added a draw row; now asserts `conversion_draws == 1`, `conversion_losses == 1`, `conversion_wins == 1`, `conversion_games == 3`
- `test_recovery_pct_per_category`: Updated to assert `recovery_wins == 1`, `recovery_draws == 1`, `recovery_saves == 2`

### Frontend (Task 2)

**`frontend/src/types/endgames.ts`:**
- Added `conversion_draws`, `conversion_losses`, `recovery_wins`, `recovery_draws` to `ConversionRecoveryStats`

**`frontend/src/components/charts/EndgameWDLChart.tsx`:**
- Added new fields to `CategoryData` interface
- Added new fields to data mapping in `EndgameWDLChart`
- Replaced 2-segment conversion bar (win/loss) with 3-segment (win/draw/loss)
- Replaced 2-segment recovery bar (save/loss) with 3-segment (win/draw/loss)

## Deviations from Plan

None — plan executed exactly as written.

## Verification

- `uv run pytest tests/test_endgame_service.py -x -v` — 24/24 tests passed
- `cd frontend && npm run build` — TypeScript compiled without errors, build succeeded

## Self-Check: PASSED

- `f151f9d` — confirmed in git log
- `a868425` — confirmed in git log
- All modified files verified to exist and contain the expected changes
