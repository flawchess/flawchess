---
phase: quick-9
plan: 01
subsystem: stats
tags: [bugfix, frontend, backend]
dependency_graph:
  requires: []
  provides: [global-stats-wdl-correct, rating-chart-adaptive-yaxis]
  affects: [stats_service, RatingChart]
tech_stack:
  added: []
  patterns: [outcome-mapping-dict, recharts-dynamic-domain]
key_files:
  created: []
  modified:
    - app/services/stats_service.py
    - frontend/src/components/stats/RatingChart.tsx
decisions:
  - Used _OUTCOME_KEY_MAP dict instead of string concatenation to prevent "losss" KeyError
  - yDomain useMemo depends on both chartData and hiddenKeys so legend toggles trigger recalc
metrics:
  duration: 5min
  completed: "2026-03-14"
---

# Quick Task 9: Some Fixes for Phase 7 Summary

Two targeted bugfixes: replaced "loss"+"s" string concat that produced "losss" KeyError with explicit mapping dict, and added adaptive Recharts YAxis domain that floors/ceils to nearest 100 based on visible time-control data.

## Tasks Completed

| # | Name | Commit | Files |
|---|------|--------|-------|
| 1 | Fix _aggregate_wdl KeyError for "losss" | 71a6eae | app/services/stats_service.py |
| 2 | Add adaptive Y-axis domain to RatingChart | befcb4c | frontend/src/components/stats/RatingChart.tsx |

## Changes Made

### Task 1: Fix _aggregate_wdl KeyError

**Problem:** `_aggregate_wdl()` used `outcome + "s"` to build the dict key. When `derive_user_result()` returned `"loss"`, this produced `"losss"` — a key not present in `{"wins": 0, "draws": 0, "losses": 0}`, causing a `KeyError` and 500 on `GET /stats/global`.

**Fix:** Added module-level `_OUTCOME_KEY_MAP = {"win": "wins", "draw": "draws", "loss": "losses"}` and replaced the concat with `_OUTCOME_KEY_MAP[outcome]`.

### Task 2: Adaptive RatingChart Y-axis

**Problem:** `<YAxis />` had no `domain` prop, so Recharts defaulted to starting at 0 — making rating charts for players rated 800-1200 show a huge empty area below.

**Fix:** Added `yDomain` `useMemo` hook that:
1. Filters `TIME_CONTROLS` to visible keys (not in `hiddenKeys`)
2. Scans `chartData` rows for min/max ratings of visible TCs
3. Floors min and ceils max to nearest 100
4. Falls back to `['auto', 'auto']` if no data
5. Applied as `<YAxis domain={yDomain} />`

Domain recalculates whenever `chartData` or `hiddenKeys` changes, so toggling legend items updates the axis range.

## Deviations from Plan

None - plan executed exactly as written.

## Self-Check

- [x] `app/services/stats_service.py` modified with `_OUTCOME_KEY_MAP`
- [x] `frontend/src/components/stats/RatingChart.tsx` modified with adaptive `yDomain`
- [x] Task 1 commit 71a6eae exists
- [x] Task 2 commit befcb4c exists
- [x] TypeScript compiles without errors

## Self-Check: PASSED
