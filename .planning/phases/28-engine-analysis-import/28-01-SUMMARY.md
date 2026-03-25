---
phase: 28-engine-analysis-import
plan: 01
subsystem: backend
tags: [schema, migration, normalization, engine-analysis, lichess, chess.com]
dependency_graph:
  requires: []
  provides: [engine-analysis-schema, accuracy-normalization, lichess-evals-param]
  affects: [game_repository, import_pipeline]
tech_stack:
  added: []
  patterns: [tdd, alembic-autogenerate]
key_files:
  created:
    - alembic/versions/20260325_213250_cf839d2edbf8_add_engine_analysis_columns.py
  modified:
    - app/models/game.py
    - app/models/game_position.py
    - app/services/normalization.py
    - app/services/lichess_client.py
    - app/repositories/game_repository.py
    - tests/test_normalization.py
decisions:
  - "white_accuracy/black_accuracy use Float(24) (REAL, 4 bytes) matching clock_seconds type convention"
  - "eval_cp/eval_mate use SmallInteger — centipawn values fit in -32768..32767 and mate-in values are small"
  - "chunk_size 2700->2300 to stay within asyncpg 32767 arg limit with 14 columns per position row"
  - "Alembic autogenerate also detected a no-op REAL->Float(24) change for clock_seconds; kept as it normalizes the type representation"
metrics:
  duration: 8m
  completed: "2026-03-25"
  tasks_completed: 1
  files_changed: 6
---

# Phase 28 Plan 01: Schema + Normalization Foundation Summary

Foundation layer for engine analysis import: 4 nullable DB columns, Alembic migration, chess.com accuracy extraction in normalization, lichess evals API param, chunk_size corrected for 14-column rows.

## Tasks Completed

| # | Task | Commit | Files |
|---|------|--------|-------|
| 1 (RED) | Failing tests for accuracy extraction | ac52ce2 | tests/test_normalization.py |
| 1 (GREEN) | Schema + normalization + lichess + chunk_size | 19dabe1 | 6 files |

## What Was Built

### Database Schema (4 new nullable columns)

**games table:**
- `white_accuracy Float(24)` — game-level accuracy % from chess.com (NULL for lichess and unanalyzed games)
- `black_accuracy Float(24)` — game-level accuracy % from chess.com

**game_positions table:**
- `eval_cp SmallInteger` — centipawn eval from lichess %eval PGN annotations (NULL for chess.com and unanalyzed)
- `eval_mate SmallInteger` — mate-in N from lichess %eval (NULL when position is not forced mate)

### Alembic Migration

`20260325_213250_cf839d2edbf8_add_engine_analysis_columns.py` — applies cleanly, adds all 4 columns. Also normalizes `clock_seconds` type representation from `REAL()` to `Float(precision=24)` (no-op in PostgreSQL, both map to float4).

### Normalization (chess.com)

`normalize_chesscom_game()` now extracts accuracies:
```python
accuracies = game.get("accuracies", {})
white_accuracy: float | None = accuracies.get("white")
black_accuracy: float | None = accuracies.get("black")
```
Returned as `"white_accuracy"` and `"black_accuracy"` keys. `normalize_lichess_game()` intentionally does NOT include these fields — lichess provides no game-level accuracy.

### Lichess API

`evals=True` added to params dict — enables `%eval` PGN annotations in streamed games when prior computer analysis exists on lichess.

### Repository chunk_size

Updated from 2700 to 2300 with corrected comment (14 columns: 8 original + 4 position metadata + 2 eval).

### Tests

`TestChesscomAccuracy` class added with 4 tests:
- `test_accuracy_present` — both accuracy fields extracted correctly
- `test_no_accuracies_key` — both fields are None when key absent
- `test_partial_accuracies` — partial accuracies handled gracefully
- `test_lichess_no_accuracy` — lichess result has no accuracy keys

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None — all columns are nullable by design (engine analysis data is absent for most games). The columns will be populated by subsequent plans in this phase.

## Self-Check: PASSED

- [x] `app/models/game.py` contains `white_accuracy` and `black_accuracy`
- [x] `app/models/game_position.py` contains `eval_cp` and `eval_mate`
- [x] Migration file `20260325_213250_cf839d2edbf8_add_engine_analysis_columns.py` exists
- [x] `app/services/normalization.py` contains `accuracies = game.get("accuracies", {})`
- [x] `app/services/lichess_client.py` contains `"evals": True`
- [x] `app/repositories/game_repository.py` contains `chunk_size = 2300`
- [x] All 81 normalization tests pass
- [x] Migration applies cleanly
- [x] Commits ac52ce2 and 19dabe1 exist
