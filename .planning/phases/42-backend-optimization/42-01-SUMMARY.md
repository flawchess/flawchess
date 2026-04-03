---
phase: 42-backend-optimization
plan: "01"
subsystem: backend/openings
tags: [sql-aggregation, optimization, refactor, tdd]
dependency_graph:
  requires: []
  provides: [query_wdl_counts, sql-wdl-aggregation]
  affects: [openings_service, openings_repository]
tech_stack:
  added: []
  patterns: [func.count().filter() SQL aggregation with subquery dedup]
key_files:
  created: []
  modified:
    - app/repositories/openings_repository.py
    - app/services/openings_service.py
    - tests/test_openings_repository.py
decisions:
  - "query_wdl_counts uses subquery wrapping of _build_base_query to preserve DISTINCT dedup before outer aggregate"
  - "endgame_service._build_wdl_summary() intentionally left in Python per D-02 (rows already in memory for timeline computation)"
  - "BOPT-02 verified and closed — no Alembic migration needed (all column types already optimal)"
metrics:
  duration: "3 minutes"
  completed: "2026-04-03"
  tasks_completed: 2
  files_modified: 3
---

# Phase 42 Plan 01: SQL WDL Aggregation and Column Type Verification Summary

SQL aggregation for W/D/L counting via `query_wdl_counts()` using `func.count().filter()` with subquery deduplication, replacing two Python counting loops in `openings_service.py`.

## What Was Built

### Task 1: query_wdl_counts() and openings_service refactor (TDD)

Added `query_wdl_counts()` to `app/repositories/openings_repository.py`:
- Takes the same parameters as `query_all_results()` 
- Wraps `_build_base_query()` (which uses `DISTINCT ON game_id` for transposition dedup) as a named subquery
- Applies `func.count().filter(win_cond/draw_cond/loss_cond)` on the subquery columns — same pattern as `stats_repository.py`
- Returns `result.one()` — always exactly one row, even when total=0

Refactored `app/services/openings_service.py`:
- `analyze()`: replaced `query_all_results()` call + Python `for result, user_color in all_rows:` loop with single `query_wdl_counts()` call
- `get_next_moves()`: same replacement for `position_stats` computation
- Removed `query_all_results` from imports (no longer used in the service)
- `derive_user_result()` retained — still used in `get_time_series()` and game record construction

Added 5 integration tests in `TestQueryWDLCounts`:
- Basic counts with target_hash (1W 1D 1L)
- All-games mode (target_hash=None)
- Filter application (time_control + color combined)
- Zero-match edge case (returns 0,0,0,0 not empty)
- Transposition dedup (game at 2 plies counted once)

### Task 2: BOPT-02 Column Type Verification (read-only)

Confirmed all `game_positions` columns are already optimal:
- `ply`: SmallInteger (max ~600, fits in 32767)
- `full_hash`, `white_hash`, `black_hash`: BigInteger (required for 64-bit Zobrist hashes)
- `clock_seconds`: Float(24) = PostgreSQL REAL (4 bytes, not 8)
- `material_count`, `material_imbalance`, `piece_count`, `mixedness`, `eval_cp`, `eval_mate`, `endgame_class`: SmallInteger
- `has_opposite_color_bishops`, `backrank_sparse`: Boolean

Confirmed all `games` columns are already optimal:
- `white_acpl`, `black_acpl`, `white_inaccuracies`, `white_mistakes`, `white_blunders`, `black_inaccuracies`, `black_mistakes`, `black_blunders`: SmallInteger
- `white_accuracy`, `black_accuracy`: Float(24) = REAL

**BOPT-02 verified and closed — no Alembic migration needed.**

## Decisions Made

- **Subquery wrapping for dedup**: `_build_base_query()` uses `DISTINCT ON game_id` (PostgreSQL). Wrapping it as a subquery before the outer `SELECT COUNT()` aggregate ensures transpositions are counted once. This is the same approach used by `stats_repository.query_position_wdl_batch()`.
- **endgame_service._build_wdl_summary() stays in Python** (D-02): The endgame rows are already fetched for rolling-window timeline computation; a separate SQL aggregate would add a DB round-trip with no data-transfer benefit.
- **BOPT-02 closed without migration**: The RESEARCH.md already confirmed all column types are optimal. This plan verified that finding and formally closes the requirement.

## Deviations from Plan

None — plan executed exactly as written.

## Verification

- `uv run pytest tests/test_openings_repository.py tests/test_openings_service.py -x` → 49 passed
- `uv run pytest` → 490 passed, 0 failures
- `uv run ruff check app/repositories/openings_repository.py app/services/openings_service.py` → All checks passed
- `uv run ty check app/ tests/` → All checks passed
- `openings_service.py` no longer contains `for result, user_color in all_rows:` loops
- `openings_repository.py` contains `query_wdl_counts()` with `func.count().filter(win_cond).label("wins")`
- `openings_repository.py` contains `.select_from(dedup)` in the aggregate query

## Commits

1. `cc9baee` — test(42-01): add failing tests for query_wdl_counts (RED)
2. `612dc0c` — feat(42-01): replace Python W/D/L loops with SQL aggregation via query_wdl_counts

## Self-Check: PASSED

- app/repositories/openings_repository.py: FOUND
- app/services/openings_service.py: FOUND
- tests/test_openings_repository.py: FOUND
- .planning/phases/42-backend-optimization/42-01-SUMMARY.md: FOUND
- Commit cc9baee (RED tests): FOUND
- Commit 612dc0c (GREEN implementation): FOUND
- `query_wdl_counts` present in openings_repository.py: YES
- Python W/D/L loop (`for result, user_color in all_rows`) removed from openings_service.py: YES (0 occurrences)
