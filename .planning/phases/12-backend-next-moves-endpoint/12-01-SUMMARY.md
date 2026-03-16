---
phase: 12-backend-next-moves-endpoint
plan: 01
subsystem: api
tags: [sqlalchemy, postgresql, pydantic, pytest, aggregation, zobrist]

# Dependency graph
requires:
  - phase: 11-schema-and-import-pipeline
    provides: move_san column on game_positions, covering index ix_gp_user_full_hash_move_san
provides:
  - NextMovesRequest, NextMoveEntry, NextMovesResponse Pydantic schemas in app/schemas/analysis.py
  - query_next_moves repository function with per-move W/D/L aggregation via COUNT(DISTINCT CASE WHEN)
  - query_transposition_counts repository function for batch {result_hash: count} lookups
  - _apply_game_filters shared helper for consistent filter application across aggregation functions
affects:
  - 12-backend-next-moves-endpoint (plan 02: service + router layers use these schemas and repository functions)
  - 13-frontend-move-explorer (consumes NextMovesResponse contract)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Self-join aliased GamePosition (gp1/gp2) on game_id + ply+1 to get result_hash in single query"
    - "COUNT(DISTINCT CASE WHEN result THEN game_id ELSE NULL) for per-group W/D/L without N+1 queries"
    - "_apply_game_filters helper to share filter WHERE clauses across multiple aggregation functions"
    - "BigInt string coercion field_validator for required (non-nullable) target_hash"

key-files:
  created: []
  modified:
    - app/schemas/analysis.py
    - app/repositories/analysis_repository.py
    - tests/test_analysis_repository.py

key-decisions:
  - "query_next_moves uses self-join (gp1/gp2) instead of subquery to get both move_san and result_hash in one round-trip"
  - "_apply_game_filters extracted as shared helper rather than inlining in each function — avoids filter drift"
  - "COUNT(DISTINCT CASE WHEN) confirmed working with SQLAlchemy 2.x via func.count(case_expr.distinct())"
  - "query_transposition_counts returns empty dict for empty input without hitting DB"

patterns-established:
  - "Aggregation functions use _apply_game_filters for consistent WHERE clause application"
  - "TDD for repository integration tests: write failing tests, commit RED, implement, commit GREEN"

requirements-completed: [MEXP-04, MEXP-05, MEXP-10]

# Metrics
duration: 3min
completed: 2026-03-16
---

# Phase 12 Plan 01: NextMoves Schemas and Repository Aggregation Queries Summary

**Pydantic schemas (NextMovesRequest/Entry/Response) and two SQLAlchemy aggregation functions using self-join + COUNT(DISTINCT CASE WHEN) for per-move W/D/L stats with transposition dedup**

## Performance

- **Duration:** ~3 min
- **Started:** 2026-03-16T20:07:03Z
- **Completed:** 2026-03-16T20:10:00Z
- **Tasks:** 2 (4 commits including TDD RED)
- **Files modified:** 3

## Accomplishments
- Added NextMovesRequest (required target_hash, filter fields, sort_by), NextMoveEntry (W/D/L + result_hash/fen + transposition_count), NextMovesResponse (position_stats + moves) schemas
- Implemented query_next_moves with gp1/gp2 self-join and COUNT(DISTINCT CASE WHEN) for W/D/L — transposition-safe, NULL move_san excluded
- Implemented query_transposition_counts batch IN() lookup for {result_hash: count} with same filter application
- Extracted _apply_game_filters shared helper to prevent filter drift across repository functions
- 7 new integration tests covering basic aggregation, transposition dedup, filters, and null exclusion — all pass

## Task Commits

Each task was committed atomically:

1. **Task 1: Add NextMoves schemas** - `669b577` (feat)
2. **Task 2 RED: Failing tests for repository functions** - `88e0063` (test)
3. **Task 2 GREEN: Implement query_next_moves and query_transposition_counts** - `1366011` (feat)

**Plan metadata:** (docs commit — see below)

_Note: TDD tasks have multiple commits (test RED → feat GREEN)_

## Files Created/Modified
- `app/schemas/analysis.py` - Added NextMovesRequest, NextMoveEntry, NextMovesResponse schemas
- `app/repositories/analysis_repository.py` - Added _apply_game_filters, query_next_moves, query_transposition_counts
- `tests/test_analysis_repository.py` - Updated _seed_game with move_san param, added _add_position helper, 5 new test classes (7 tests)

## Decisions Made
- Self-join gp1/gp2 on (game_id, ply+1) to get result_hash in single aggregation query — avoids separate lookup round-trip
- _apply_game_filters extracted rather than duplicated in both new functions — ensures consistent filter behavior
- COUNT(DISTINCT CASE WHEN) with SQLAlchemy's func.count(case_expr.distinct()) — confirmed working in PostgreSQL via integration test verification
- Empty result_hash_list returns {} without DB hit — safe early return

## Deviations from Plan
None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Schemas and data layer complete; plan 02 can implement get_next_moves service function and POST /analysis/next-moves router
- result_fen computation (via python-chess PGN replay) is the main remaining task in the service layer
- All filter logic is encapsulated in _apply_game_filters — service layer passes filter params through directly

## Self-Check: PASSED

- app/schemas/analysis.py: FOUND
- app/repositories/analysis_repository.py: FOUND
- .planning/phases/12-backend-next-moves-endpoint/12-01-SUMMARY.md: FOUND
- Commit 669b577 (schemas): FOUND
- Commit 88e0063 (tests RED): FOUND
- Commit 1366011 (implementation): FOUND

---
*Phase: 12-backend-next-moves-endpoint*
*Completed: 2026-03-16*
