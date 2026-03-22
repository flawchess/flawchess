---
phase: quick
plan: 260322-kpe
subsystem: backend
tags: [bug-fix, time-control, normalization, migration]
dependency_graph:
  requires: []
  provides: [corrected-time-control-bucketing]
  affects: [games.time_control_bucket, import-pipeline]
tech_stack:
  added: []
  patterns: [alembic-data-migration]
key_files:
  modified:
    - app/services/normalization.py
    - tests/test_normalization.py
    - CLAUDE.md
  created:
    - alembic/versions/20260322_135825_b5b8170c0f72_fix_time_control_bucket_for_600s_games.py
decisions:
  - Changed threshold from <= 600 to < 600: 10+0 is universally considered rapid in chess
  - Migration covers all time_control_str patterns yielding exactly 600s estimated (600, 560+1, ... 200+10)
metrics:
  duration: ~10 minutes
  completed: 2026-03-22
  tasks_completed: 2
  files_modified: 4
---

# Quick Task 260322-kpe: Fix Wrong Time Control Bucket Assignment

**One-liner:** Fixed off-by-one threshold in parse_time_control: changed `<= 600` to `< 600` so 10+0 (600s) correctly maps to rapid instead of blitz, with data migration for existing games.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Fix bucketing logic, tests, and CLAUDE.md | ae1b199 | normalization.py, test_normalization.py, CLAUDE.md |
| 2 | Data migration to fix existing games | 60c0cf8 | alembic/versions/...fix_time_control_bucket_for_600s_games.py |

## Changes Made

### Task 1: Code Fix

**`app/services/normalization.py`** line 62: `estimated <= 600` changed to `estimated < 600`.

Updated docstring example from `'600+0' -> ('blitz', 600)` to `'600+0' -> ('rapid', 600)` and corrected threshold table to use `< 180s` and `< 600s`.

**`tests/test_normalization.py`:** Four test updates:
- `test_blitz_no_increment` renamed to `test_rapid_no_increment` with corrected assertion
- `test_blitz_boundary` renamed to `test_600_is_rapid` with corrected assertion
- Added `test_599_is_blitz` to verify the boundary from below
- Fixed `test_time_control_parsed` in `TestNormalizeChesscomGame` (also used `600+0`)

**`CLAUDE.md`:** Updated threshold documentation: `<=180s = bullet, <=600s = blitz` changed to `<180s = bullet, <600s = blitz`.

### Task 2: Data Migration

Created Alembic migration `b5b8170c0f72` that updates existing games where `time_control_bucket = 'blitz'` and the estimated duration is exactly 600s. Covers 11 `time_control_str` patterns: `600`, `560+1`, `520+2`, `480+3`, `440+4`, `400+5`, `360+6`, `320+7`, `280+8`, `240+9`, `200+10`. Downgrade reverts to blitz.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Additional test using 600+0 needed updating**
- **Found during:** Task 1 verification (pytest run)
- **Issue:** `TestNormalizeChesscomGame.test_time_control_parsed` used `600+0` and asserted `bucket == "blitz"` — not listed in the plan's targeted tests
- **Fix:** Updated assertion to `bucket == "rapid"` to match corrected behavior
- **Files modified:** tests/test_normalization.py
- **Commit:** ae1b199

## Known Stubs

None.

## Self-Check: PASSED

- app/services/normalization.py: FOUND
- tests/test_normalization.py: FOUND
- CLAUDE.md: FOUND
- alembic/versions/20260322_135825_b5b8170c0f72_fix_time_control_bucket_for_600s_games.py: FOUND
- Commit ae1b199: FOUND
- Commit 60c0cf8: FOUND
