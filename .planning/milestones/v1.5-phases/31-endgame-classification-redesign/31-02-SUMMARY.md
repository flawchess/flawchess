---
phase: 31-endgame-classification-redesign
plan: 02
subsystem: backend
tags: [postgres, sqlalchemy, endgame, analytics, repository, service, tests]

# Dependency graph
requires:
  - phase: 31-01
    provides: endgame_class SmallInteger column, EndgameClassInt IntEnum, _CLASS_TO_INT/_INT_TO_CLASS mappings

provides:
  - query_endgame_entry_rows returning (game_id, endgame_class_int, result, user_color, user_material_imbalance) per (game, class) span
  - ENDGAME_PLY_THRESHOLD = 6 constant for minimum ply count per span
  - query_endgame_games filtering endgame_class integer in SQL via span subquery
  - _aggregate_endgame_stats consuming integer endgame_class from rows (no Python classify call)

affects:
  - endgame analytics API — response shape unchanged, semantics updated to multi-class per game

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Two-subquery pattern: span_subq (GROUP BY game_id+endgame_class HAVING >= threshold) + entry_pos_subq (material_imbalance lookup at entry ply)
    - SQL-only endgame_class filtering: integer comparison in span_subq WHERE clause replaces Python-side classify_endgame_class loop

key-files:
  created: []
  modified:
    - app/repositories/endgame_repository.py
    - app/services/endgame_service.py
    - tests/test_endgame_repository.py
    - tests/test_endgame_service.py

key-decisions:
  - "ENDGAME_PLY_THRESHOLD = 6: a game must spend 3+ full moves in an endgame class to count — filters tactical piece sacrifices and transient class changes (Per D-03)"
  - "endgame_games in EndgameStatsResponse now counts (game, class) combinations not unique games — intentional per D-02 (each class gets its own W/D/L count)"
  - "query_endgame_games uses early return (not KeyError) for unknown endgame_class values for robustness"

requirements-completed: []

# Metrics
duration: 10min
completed: 2026-03-26
---

# Phase 31 Plan 02: Endgame Repository & Service Redesign Summary

**Per-position multi-class endgame analytics with 6-ply threshold: repository rewritten to return one row per (game, endgame_class) span, service aggregation updated to use pre-computed integer endgame_class from DB**

## Performance

- **Duration:** ~10 min
- **Started:** 2026-03-26T15:40:00Z
- **Completed:** 2026-03-26T15:51:14Z
- **Tasks:** 2 of 2
- **Files modified:** 4

## Accomplishments

- Rewrote `query_endgame_entry_rows` with two subqueries: `span_subq` (GROUP BY game_id + endgame_class HAVING >= 6 plies) and `entry_pos_subq` (material_imbalance lookup at MIN ply of span)
- Added `ENDGAME_PLY_THRESHOLD = 6` constant to `endgame_repository.py`
- Changed return shape from `(game_id, result, user_color, material_signature, user_material_imbalance)` to `(game_id, endgame_class_int, result, user_color, user_material_imbalance)` — a game now appears once per qualifying class span
- Rewrote `query_endgame_games` to filter `endgame_class` integer directly in SQL via span subquery; removed Python-side `classify_endgame_class` loop; replaced slice-based pagination with SQL OFFSET/LIMIT
- Updated `_aggregate_endgame_stats` to unpack `endgame_class_int` from rows and use `_INT_TO_CLASS[endgame_class_int]` instead of calling `classify_endgame_class`
- Updated docstrings and `endgame_games` comment to reflect multi-class-per-game semantics
- Rewrote `test_endgame_repository.py`: added `endgame_class` param to `_seed_game_position`; updated existing tests to seed >= 6 positions per class; added 3 new tests (ply threshold filtering, multi-class per game, entry imbalance at first ply)
- Rewrote `test_endgame_service.py`: all rows now use integer endgame_class tuple shape; added `test_multi_class_per_game_in_aggregation`

## Task Commits

1. **Task 1: Redesign endgame_repository.py queries** - `e6e3f13` (feat)
2. **Task 2: Update endgame_service.py and all tests** - `c8928b7` (feat)

## Files Created/Modified

- `app/repositories/endgame_repository.py` - Added ENDGAME_PLY_THRESHOLD; rewrote query_endgame_entry_rows and query_endgame_games; updated module docstring
- `app/services/endgame_service.py` - Updated _aggregate_endgame_stats row shape; updated get_endgame_stats docstring and endgame_games comment
- `tests/test_endgame_repository.py` - Added endgame_class param to _seed_game_position; updated tests for >= threshold seeds; added 3 new tests
- `tests/test_endgame_service.py` - Rows use integer endgame_class; added multi-class aggregation test; removed unused pytest_asyncio import

## Decisions Made

- ENDGAME_PLY_THRESHOLD = 6: games must spend at least 3 full moves in an endgame class to be counted — short tactical spans (piece sacrifices, transient class changes) are excluded
- `endgame_games` in `EndgameStatsResponse` now counts (game, class) combinations — a game in two classes contributes 2, which is intentional since each class gets its own independent W/D/L count
- `query_endgame_games` returns ([], 0) early for unknown class strings rather than raising KeyError — clean handling for API validation edge cases

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None — no external service configuration required.

## Known Stubs

None — all data flows from DB through repository to service correctly.

## Next Phase Readiness

- Phase 31 complete — endgame classification redesign fully implemented
- Endgame analytics API response shape unchanged (D-01 confirmed: no frontend changes needed)
- All 423 tests pass

---
*Phase: 31-endgame-classification-redesign*
*Completed: 2026-03-26*
