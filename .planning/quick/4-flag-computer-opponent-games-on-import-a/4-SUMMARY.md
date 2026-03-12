---
phase: quick-4
plan: 4
subsystem: backend/import-pipeline
tags: [normalization, import, computer-detection, opening-names, migration]
dependency_graph:
  requires: []
  provides: [is_computer_game-column, chesscom-opening-names, computer-detection]
  affects: [game-import, normalization]
tech_stack:
  added: []
  patterns: [regex-slug-parsing, bot-title-detection]
key_files:
  created:
    - alembic/versions/0b59137a5005_add_is_computer_game_to_games.py
  modified:
    - app/models/game.py
    - app/services/normalization.py
    - tests/test_normalization.py
decisions:
  - "Used server_default=sa.text('false') in migration to avoid table rewrite for existing rows"
  - "Detect chess.com computer via is_computer field on opponent player object (not user player)"
  - "Detect lichess BOT via opponent player.user.title upper-cased == 'BOT' (case-insensitive)"
  - "Parse chess.com opening name from eco URL slug by stripping trailing ECO code and replacing hyphens"
metrics:
  duration: 8min
  completed: "2026-03-12"
  tasks_completed: 2
  files_modified: 4
---

# Phase quick-4: Flag Computer Opponent Games on Import Summary

**One-liner:** Added is_computer_game DB column with migration, chess.com/lichess computer detection in normalizers, and chess.com opening name parsing from eco URL slug.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Add is_computer_game column and migration | 323ee84 | app/models/game.py, alembic/versions/0b59137a5005_... |
| 2 (RED) | Write failing tests for computer detection + opening names | c302fbc | tests/test_normalization.py |
| 2 (GREEN) | Implement computer detection and opening name parsing | a2479c2 | app/services/normalization.py |

## What Was Built

### DB Schema Change
- Added `is_computer_game: Mapped[bool]` to the `Game` model in the Flags section
- Alembic migration `0b59137a5005` adds `is_computer_game` column with `server_default=false` so existing rows default to False without a table rewrite

### chess.com Computer Detection
- `normalize_chesscom_game` now checks the opponent player object for `is_computer: true`
- The opponent is determined relative to the importing user (not simply "white" or "black")

### lichess BOT Detection
- `normalize_lichess_game` now checks `opponent_player.user.title.upper() == "BOT"`
- Case-insensitive comparison handles edge cases like "bot" or "Bot"

### chess.com Opening Name Parsing
- New helper `_extract_chesscom_opening_name(eco_url)` strips the trailing ECO code (`-C40`) from the URL slug and replaces hyphens with spaces
- Handles missing ECO suffix (returns full slug with hyphens replaced)
- Returns None when eco_url is None/empty
- `normalize_chesscom_game` now populates `opening_name` from the eco URL (previously always None)

## Verification

- 58 normalization tests pass (29 existing + 9 new computer/opening tests)
- Migration applied — alembic at head: 0b59137a5005
- ruff check passes on app/services/normalization.py

## Deviations from Plan

None — plan executed exactly as written.

## Self-Check: PASSED

Files exist:
- app/models/game.py — FOUND, contains is_computer_game
- app/services/normalization.py — FOUND, contains _extract_chesscom_opening_name
- alembic/versions/0b59137a5005_add_is_computer_game_to_games.py — FOUND

Commits exist:
- 323ee84 — FOUND
- c302fbc — FOUND
- a2479c2 — FOUND
