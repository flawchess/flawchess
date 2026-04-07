---
phase: 48-conversion-recovery-persistence-filter
plan: 01
subsystem: backend-endgame-analytics
tags: [endgame, conversion, recovery, persistence, threshold, analytics]
dependency_graph:
  requires: []
  provides: [endgame-persistence-filter, endgame-100cp-threshold]
  affects: [endgame_repository, endgame_service, endgame-conversion-recovery-metrics]
tech_stack:
  added: []
  patterns: [array_agg persistence indexing, 6-element row shape]
key_files:
  created: []
  modified:
    - app/repositories/endgame_repository.py
    - app/services/endgame_service.py
    - tests/test_endgame_service.py
    - tests/test_endgame_repository.py
decisions:
  - PERSISTENCE_PLIES=4 constant in repository, not service — keeps SQL logic with SQL code
  - SIGNIFICANT_IMBALANCE_CP kept as commented constant in timeline query for documentation
  - _entry_row test helper sets imbalance_after=imbalance so gauge tests aren't affected by persistence
metrics:
  duration: 7 minutes
  completed: 2026-04-07
  tasks_completed: 2
  tasks_total: 2
  files_changed: 4
---

# Phase 48 Plan 01: Persistence Filter and Threshold Lowering Summary

Persistence filter added to endgame conversion/recovery classification. Material imbalance must hold at BOTH endgame entry AND 4 plies later (entry+4) to count as conversion/recovery. Threshold lowered from 300cp to 100cp — persistence requirement eliminates transient trade noise that previously required the high threshold.

## Tasks Completed

| Task | Description | Commit |
|------|-------------|--------|
| 1 | Add persistence field to repository queries and lower thresholds | 2ab9f3a |
| 2 | Add persistence check to service layer and update tests | 1c96c12 |

## What Was Built

### Repository Changes (`endgame_repository.py`)

- Added `PERSISTENCE_PLIES = 4` module-level constant
- `query_endgame_entry_rows`: added `imbalance_after_persistence_agg` using `array_agg()[PERSISTENCE_PLIES + 1]` (safe because spans require >= 6 plies). Added `user_material_imbalance_after` as 6th column in result rows
- `query_conv_recov_timeline_rows`: same `imbalance_after_persistence_agg` pattern, `SIGNIFICANT_IMBALANCE_CP` lowered to 100, **removed** the `WHERE abs >= threshold` filter (service now handles this), added `user_material_imbalance_after` as 5th column

### Service Changes (`endgame_service.py`)

- `_MATERIAL_ADVANTAGE_THRESHOLD` lowered from 300 to 100 with updated comment explaining the change
- `_aggregate_endgame_stats`: loop now unpacks 6 elements per row. Conversion check requires both `user_material_imbalance >= 100` AND `user_material_imbalance_after >= 100`. Recovery check requires both `<= -100`
- `get_conv_recov_timeline`: updated filtering from `r[3]` only to `r[3] AND r[4]` persistence check

### Test Changes

- `TestAggregateEndgameStats`: all row tuples updated to 6 elements (added matching after-value)
- `test_conversion_pct_per_category`: updated for 100cp threshold, added row with non-persistent imbalance (200cp entry, 50cp after) that should NOT count
- `test_recovery_pct_per_category`: same pattern for recovery
- `TestEndgameGaugeCalculations._entry_row`: sets `imbalance_after = imbalance` so gauge formula tests aren't affected by the persistence requirement
- Added `test_persistence_filter_excludes_transient_imbalance`: verifies 200cp/50cp and -300cp/-80cp are excluded, while 150cp/120cp and -200cp/-150cp qualify
- Added `test_persistence_none_after_value_excluded`: None safety guard test
- `test_endgame_repository.py`: updated row unpacking to 6 elements, added assertion that `user_material_imbalance_after == 50` (from ply=24 in the seeded test data)

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None.

## Threat Flags

None — no new trust boundaries or user input handling introduced. Same analytics columns, additional array index access only.

## Self-Check: PASSED

- SUMMARY.md: FOUND
- endgame_repository.py: FOUND, contains PERSISTENCE_PLIES = 4 and user_material_imbalance_after
- endgame_service.py: FOUND, contains _MATERIAL_ADVANTAGE_THRESHOLD = 100 and user_material_imbalance_after
- test_endgame_service.py: FOUND, contains test_persistence_filter_excludes_transient_imbalance and test_persistence_none_after_value_excluded
- test_endgame_repository.py: FOUND, updated row unpacking
- Commit 2ab9f3a (Task 1): FOUND
- Commit 1c96c12 (Task 2): FOUND
- All 61 tests pass
