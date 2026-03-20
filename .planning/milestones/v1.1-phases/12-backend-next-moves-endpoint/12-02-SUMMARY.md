---
phase: 12-backend-next-moves-endpoint
plan: 02
subsystem: api
tags: [fastapi, sqlalchemy, postgresql, pydantic, python-chess, pytest, zobrist]

# Dependency graph
requires:
  - phase: 12-backend-next-moves-endpoint
    provides: NextMovesRequest/Entry/Response schemas, query_next_moves, query_transposition_counts

provides:
  - get_next_moves async service function in app/services/analysis_service.py
  - _fetch_result_fens async helper (PGN replay via python-chess for result_fen)
  - POST /analysis/next-moves endpoint in app/routers/analysis.py
  - TestGetNextMoves and TestNextMovesSorting test classes in tests/test_analysis_service.py
  - _seed_game_with_positions multi-position seed helper in tests/test_analysis_service.py

affects:
  - 13-frontend-move-explorer (consumes POST /analysis/next-moves returning NextMovesResponse)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "PGN replay via chess.pgn.read_game + board.push(move) loop to compute board_fen at target ply"
    - "DISTINCT ON full_hash batch query to get one sample (game_id, ply) per result_hash efficiently"
    - "Two-query batch for result_fens: sample positions then PGNs — avoids N+1 DB round-trips"
    - "position_stats uses query_all_results with GamePosition.full_hash (not match_side)"

key-files:
  created: []
  modified:
    - app/services/analysis_service.py
    - app/routers/analysis.py
    - tests/test_analysis_service.py

key-decisions:
  - "result_fen computed via PGN replay (not stored) — push N moves in mainline to reach ply N, extract board.board_fen()"
  - "Two-phase batch for result_fens: DISTINCT ON sample + separate PGN batch — single query each, no N+1"
  - "position_stats always uses full_hash (not match_side) for next-moves endpoint per plan spec"
  - "transposition_count fallback to game_count if hash missing from trans_counts dict"

patterns-established:
  - "Service layer orchestrates multiple repository calls: query_all_results, query_next_moves, query_transposition_counts, _fetch_result_fens"
  - "TDD: RED tests first (import fails), GREEN implementation, full suite verification"

requirements-completed: [MEXP-04, MEXP-05, MEXP-10]

# Metrics
duration: 3min
completed: 2026-03-16
---

# Phase 12 Plan 02: get_next_moves Service and POST /analysis/next-moves Endpoint Summary

**FastAPI POST /analysis/next-moves endpoint with service-layer orchestration: W/D/L position stats, per-move aggregation, transposition counts, result_fen via python-chess PGN replay, and frequency/win_rate sorting**

## Performance

- **Duration:** ~3 min
- **Started:** 2026-03-16T20:13:59Z
- **Completed:** 2026-03-16T20:17:00Z
- **Tasks:** 2 (3 commits including TDD RED)
- **Files modified:** 3

## Accomplishments
- Implemented get_next_moves service function orchestrating query_all_results (position_stats), query_next_moves (move aggregation), query_transposition_counts (batch lookup), and _fetch_result_fens (PGN replay)
- Added _fetch_result_fens helper using DISTINCT ON batch query + PGN batch fetch to compute board_fen per result_hash without N+1 queries
- Wired POST /analysis/next-moves router endpoint with correct dependency injection and NextMovesResponse return type
- 6 new service integration tests covering basic W/D/L, result_fen board_fen format, empty position, transposition_count >= game_count, frequency sort, win_rate sort

## Task Commits

Each task was committed atomically:

1. **Task 1 RED: Failing tests for get_next_moves** - `905f345` (test)
2. **Task 1 GREEN: Implement get_next_moves service function** - `bbd3fc0` (feat)
3. **Task 2: Wire POST /analysis/next-moves router endpoint** - `a9d8b03` (feat)

**Plan metadata:** (docs commit — see below)

_Note: TDD tasks have multiple commits (test RED → feat GREEN)_

## Files Created/Modified
- `app/services/analysis_service.py` - Added _fetch_result_fens helper and get_next_moves orchestration function
- `app/routers/analysis.py` - Added POST /analysis/next-moves endpoint
- `tests/test_analysis_service.py` - Added _seed_game_with_positions helper, TestGetNextMoves and TestNextMovesSorting test classes

## Decisions Made
- result_fen computed at query time via PGN replay (push N moves in mainline, call board.board_fen()) rather than stored — avoids schema changes and stays consistent with CLAUDE.md constraint to use board_fen not fen
- Two-phase batch approach for result_fens: DISTINCT ON full_hash sample query + separate batch PGN fetch — avoids N+1 while keeping code clear
- position_stats always uses GamePosition.full_hash (not the request's match_side concept) — next-moves endpoint has no match_side field by design

## Deviations from Plan
None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- POST /analysis/next-moves endpoint fully functional, returning NextMovesResponse with position_stats + sorted moves + result_fen + transposition_count
- Phase 13 (Frontend Move Explorer Component) can now consume the endpoint
- All filters (time_control, platform, rated, opponent_type, recency, color) apply consistently across position_stats, move aggregation, and transposition counts

## Self-Check: PASSED

- app/services/analysis_service.py: FOUND (contains async def get_next_moves, async def _fetch_result_fens, board.board_fen())
- app/routers/analysis.py: FOUND (contains @router.post("/analysis/next-moves", NextMovesRequest, NextMovesResponse)
- tests/test_analysis_service.py: FOUND (contains class TestGetNextMoves, class TestNextMovesSorting, _seed_game_with_positions)
- Commit 905f345 (RED tests): FOUND
- Commit bbd3fc0 (GREEN service): FOUND
- Commit a9d8b03 (router): FOUND
- Full test suite: 278 passed

---
*Phase: 12-backend-next-moves-endpoint*
*Completed: 2026-03-16*
