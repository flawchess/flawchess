---
phase: 03-analysis-api
plan: 01
subsystem: api
tags: [fastapi, sqlalchemy, pydantic, postgresql, zobrist]

requires:
  - phase: 01-data-foundation
    provides: Game and GamePosition SQLAlchemy models with Zobrist hash columns and composite indexes
  - phase: 02-import-pipeline
    provides: Populated games and game_positions tables; async DB session factory

provides:
  - POST /analysis/positions endpoint returning W/D/L stats and paginated game list
  - AnalysisRequest/AnalysisResponse/WDLStats/GameRecord Pydantic v2 schemas
  - analysis_repository with DISTINCT deduplication and dynamic filter chaining
  - analysis_service with derive_user_result and recency_cutoff helpers

affects: [04-frontend-auth]

tech-stack:
  added: []
  patterns:
    - "Repository _build_base_query helper for shared filter logic across count and paginated queries"
    - "DISTINCT by game.id in query prevents transposition double-counting (same position at multiple plies)"
    - "Service computes stats from lightweight (result, user_color) tuples, separate from full Game pagination query"

key-files:
  created:
    - app/schemas/analysis.py
    - app/repositories/analysis_repository.py
    - app/services/analysis_service.py
    - app/routers/analysis.py
  modified:
    - app/main.py

key-decisions:
  - "DISTINCT by Game.id in _build_base_query prevents double-counting when position hash appears at multiple plies in same game"
  - "query_all_results fetches only (result, user_color) columns for stats — avoids loading full ORM objects"
  - "Count subquery wraps deduplicated game IDs via subquery(); scalar_one() for total before pagination"
  - "recency_cutoff returns None for None/'all' enabling clean optional filter passthrough"

patterns-established:
  - "Repository _build_base_query: shared base query with select_entity parameter for reuse in count vs paginated queries"
  - "Service orchestration: fetch all rows for stats, fetch paginated rows for display — two separate DB calls"

requirements-completed: [ANL-02, ANL-03, FLT-01, FLT-02, FLT-03, FLT-04, RES-01, RES-02, RES-03]

duration: 2min
completed: 2026-03-11
---

# Phase 3 Plan 01: Analysis API Summary

**POST /analysis/positions endpoint returning W/D/L stats and paginated game list filtered by Zobrist hash and optional time-control/rated/recency/color filters**

## Performance

- **Duration:** ~2 min
- **Started:** 2026-03-11T14:49:12Z
- **Completed:** 2026-03-11T14:51:17Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments

- Created four-layer analysis stack: schemas -> repository -> service -> router
- Repository uses DISTINCT by game_id so a position appearing at multiple plies counts the game only once
- Stats computation is separated from pagination: lightweight (result, user_color) query for W/D/L, full Game objects only for the paginated list
- All filters (time_control, rated, recency, color) are optional and dynamically applied via filter chaining
- Zero-match case returns all-zero stats with empty game list (not 404)
- POST /analysis/positions registered and reachable in FastAPI app

## Task Commits

1. **Task 1: Create Pydantic schemas and analysis repository** - `6eef4a3` (feat)
2. **Task 2: Create analysis service and router with main.py wiring** - `28bbec3` (feat)

## Files Created/Modified

- `app/schemas/analysis.py` - AnalysisRequest, WDLStats, GameRecord, AnalysisResponse Pydantic v2 models
- `app/repositories/analysis_repository.py` - query_all_results, query_matching_games, HASH_COLUMN_MAP, _build_base_query helper
- `app/services/analysis_service.py` - derive_user_result, recency_cutoff, RECENCY_DELTAS, analyze() orchestrator
- `app/routers/analysis.py` - POST /analysis/positions with user_id=1 placeholder (TODO phase-4)
- `app/main.py` - Added include_router(analysis.router)

## Decisions Made

- DISTINCT by Game.id applied in `_build_base_query` to prevent transposition double-counting (same position at multiple plies in one game).
- Stats computed from lightweight (result, user_color) tuple fetch; separate from full Game pagination — keeps stats accurate for total even when limit < matched_count.
- Count subquery wraps the deduplicated game IDs via SQLAlchemy `.subquery()` + `func.count()` so the total reflects distinct matched games.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Analysis API is complete and ready for frontend integration in Phase 4
- user_id is hardcoded to 1 (TODO phase-4) — same pattern as the import router
- FastAPI-Users auth wiring in Phase 4 will replace both user_id=1 placeholders

---
*Phase: 03-analysis-api*
*Completed: 2026-03-11*

## Self-Check: PASSED

- app/schemas/analysis.py: FOUND
- app/repositories/analysis_repository.py: FOUND
- app/services/analysis_service.py: FOUND
- app/routers/analysis.py: FOUND
- Commit 6eef4a3: FOUND
- Commit 28bbec3: FOUND
