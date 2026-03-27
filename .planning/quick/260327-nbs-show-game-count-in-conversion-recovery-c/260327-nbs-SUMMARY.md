---
phase: quick
plan: 260327-nbs
status: complete
---

# Quick Task 260327-nbs: Show game count in conversion recovery chart

## What Changed

- **EndgameConvRecovChart.tsx**: Added `conversion_games` and `recovery_games` to the data point interface and tooltip display. Tooltip now shows e.g. "Conversion: 73.0% (45 games)" instead of just "Conversion: 73.0%".

## Files Modified

- `frontend/src/components/charts/EndgameConvRecovChart.tsx`
