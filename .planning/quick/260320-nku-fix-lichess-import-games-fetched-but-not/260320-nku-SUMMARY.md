---
phase: quick
plan: 260320-nku
subsystem: backend/database
tags: [bug-fix, multi-user, constraint, migration, tdd]
dependency_graph:
  requires: []
  provides: [per-user game deduplication]
  affects: [app/models/game.py, app/repositories/game_repository.py, alembic]
tech_stack:
  added: []
  patterns: [ON CONFLICT DO NOTHING with per-user unique constraint]
key_files:
  created:
    - alembic/versions/20260320_160254_9549c5e62259_make_game_unique_constraint_per_user.py
  modified:
    - app/models/game.py
    - app/repositories/game_repository.py
    - tests/test_game_repository.py
decisions:
  - Per-user unique constraint (user_id, platform, platform_game_id) replaces global (platform, platform_game_id)
metrics:
  duration: "138s"
  completed: "2026-03-20"
  tasks_completed: 2
  files_changed: 4
---

# Phase quick Plan 260320-nku: Fix Lichess Import Games Fetched But Not Saved Summary

**One-liner:** Changed `games` unique constraint from global `(platform, platform_game_id)` to per-user `(user_id, platform, platform_game_id)` via migration + model + repository update.

## What Was Built

Multi-user correctness fix: when two different users import the same lichess username, both now get their own copy of each game. Previously, user 2's import would silently discard all games because the global unique constraint considered them duplicates of user 1's rows.

### Root Cause

`UniqueConstraint("platform", "platform_game_id", name="uq_games_platform_game_id")` was global — no `user_id` column. The `ON CONFLICT DO NOTHING` in `bulk_insert_games` would skip every game already imported by any user.

### Fix

| File | Change |
|------|--------|
| `app/models/game.py` | Constraint changed to `(user_id, platform, platform_game_id)` named `uq_games_user_platform_game_id` |
| `app/repositories/game_repository.py` | `on_conflict_do_nothing` references new constraint name |
| `tests/test_game_repository.py` | Added `test_different_users_can_import_same_game` and `test_same_user_duplicate_still_skipped` |
| `alembic/versions/20260320_160254_*` | Migration: drops old constraint, creates new one; fully reversible |

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Add multi-user test + fix model and repository | 8a1c58f | tests/test_game_repository.py, app/models/game.py, app/repositories/game_repository.py |
| 2 | Create Alembic migration | 7044165 | alembic/versions/20260320_160254_9549c5e62259_... |

## Verification

- `uv run pytest tests/test_game_repository.py -x -v` — 16 passed
- `uv run alembic upgrade head` — migration applied cleanly
- `uv run ruff check app/models/game.py app/repositories/game_repository.py` — F821 on line 66 is pre-existing (suppressed with `# type: ignore[name-defined]`)

## Deviations from Plan

None — plan executed exactly as written.

The TDD RED/GREEN/commit split was combined into one commit (8a1c58f) because the tests, model, and repository were all staged together. The migration was committed separately as Task 2 (7044165).
