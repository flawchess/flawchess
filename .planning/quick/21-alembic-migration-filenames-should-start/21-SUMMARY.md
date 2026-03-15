---
phase: quick-21
plan: "01"
subsystem: database/migrations
tags: [alembic, migrations, devex]
dependency_graph:
  requires: []
  provides: [chronological-migration-filenames]
  affects: [alembic/versions/]
tech_stack:
  added: []
  patterns: [alembic-file_template-utc-timestamp]
key_files:
  created: []
  modified:
    - alembic.ini
    - alembic/versions/20260311_133123_dcef507678d8_initial_schema.py
    - alembic/versions/20260311_142537_9e234104d7f2_add_import_jobs_table.py
    - alembic/versions/20260312_102146_ea8ca9526dcf_add_users_table.py
    - alembic/versions/20260312_114006_d809d42c7521_add_oauth_account_table.py
    - alembic/versions/20260312_212351_0b59137a5005_add_is_computer_game_to_games.py
    - alembic/versions/20260313_095730_00e469a985ef_add_bookmarks_table.py
    - alembic/versions/20260313_123605_f10322cb88b3_add_is_flipped_to_bookmarks.py
    - alembic/versions/20260314_145243_7eb7ce83cdb9_rename_bookmarks_to_position_bookmarks.py
    - alembic/versions/20260314_164203_f009f3b41e8e_add_move_count_to_games_and_usernames_.py
    - alembic/versions/20260314_181258_1c4985e5016a_add_white_black_username_rating_columns.py
    - alembic/versions/20260314_194322_697d7b8842d2_drop_redundant_user_relative_columns.py
decisions:
  - "alembic.ini file_template uses YYYYMMDD_HHMMSS format (no separator between date and time parts, underscore between date and time blocks)"
  - "zoneinfo (stdlib Python 3.9+) handles UTC — no extra tzdata dependency needed"
  - "git mv used for all renames so git tracks file history correctly"
metrics:
  duration: 2min
  completed: "2026-03-15"
  tasks_completed: 2
  files_modified: 12
---

# Phase quick-21 Plan 01: Alembic Migration Filenames Should Start with UTC Timestamp Summary

**One-liner:** Renamed all 11 Alembic migration files with YYYYMMDD_HHMMSS UTC prefix and configured alembic.ini file_template for consistent chronological sorting.

## What Was Built

Migration filenames now sort chronologically when listed alphabetically. The `file_template` in `alembic.ini` ensures all future `alembic revision --autogenerate` calls produce timestamped filenames automatically.

## Tasks Completed

| Task | Description | Commit |
|------|-------------|--------|
| 1 | Configure file_template in alembic.ini and rename all 11 migration files with git mv | a8a0a74 |
| 2 | Verify alembic upgrade head, check, test migration filename format, run pytest | (verification only, no file changes) |

## Verification Results

- `alembic heads` shows single head: `697d7b8842d2`
- `alembic upgrade head` is a no-op (already at head), chain intact
- `alembic check` shows "No new upgrade operations detected"
- Test migration generated as `20260315_085138_39b424c73314_test_timestamp_format.py` — confirms UTC timestamp format
- All 249 tests pass

## Deviations from Plan

None — plan executed exactly as written.

## Self-Check: PASSED

- All 11 renamed files exist in alembic/versions/
- Commit a8a0a74 exists and covers all 12 changed files (11 renames + alembic.ini)
- alembic.ini has file_template and timezone=utc configured
- Tests: 249 passed
