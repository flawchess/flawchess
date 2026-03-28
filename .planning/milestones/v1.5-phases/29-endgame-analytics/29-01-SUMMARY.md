---
phase: 29-endgame-analytics
plan: "01"
subsystem: api
tags: [fastapi, sqlalchemy, postgresql, pydantic, endgame, chess, analytics]

requires:
  - phase: 27-import-wiring-backfill
    provides: "material_count, material_signature, material_imbalance columns in game_positions"

provides:
  - "GET /api/endgames/stats: W/D/L per endgame category with inline conversion/recovery stats"
  - "GET /api/endgames/games: paginated game list filtered by endgame class"
  - "classify_endgame_class(): pure function mapping material_signature to 6 endgame categories"
  - "ENDGAME_MATERIAL_THRESHOLD = 2600 constant for endgame transition point detection"

affects:
  - phase: 29-02 (frontend EndgamesPage consumes these endpoints)
  - phase: 29-03 (frontend Games sub-tab uses /api/endgames/games)

tech-stack:
  added: []
  patterns:
    - "Endgame entry point = MIN ply per game where material_count < ENDGAME_MATERIAL_THRESHOLD"
    - "Python-side endgame classification from material_signature (not SQL LIKE patterns)"
    - "user_material_imbalance = imbalance * (1 if white else -1) for user-perspective normalization"
    - "query_endgame_games: fetch all entry rows, classify in Python, then paginate (correct for expected data volumes)"

key-files:
  created:
    - app/schemas/endgames.py
    - app/repositories/endgame_repository.py
    - app/services/endgame_service.py
    - app/routers/endgames.py
    - tests/test_endgame_service.py
    - tests/test_endgame_repository.py
  modified:
    - app/main.py

key-decisions:
  - "classify_endgame_class: rook+pawn = rook (not mixed); minor+pawn = mixed; Q+anything = mixed; R+minor = mixed"
  - "No color filter on endgame endpoints per D-02 (stats cover both white and black games)"
  - "Categories sorted by total game count descending per D-05 (not fixed order)"
  - "Conversion and recovery stats are per endgame type, not per game phase (D-11)"

patterns-established:
  - "Endgame repository pattern: entry_ply subquery with MIN(ply) joined back to game_positions"
  - "Sign flip for material_imbalance: multiply by -1 when user_color=black for user-perspective normalization"

requirements-completed: [ENDGM-01, ENDGM-02, ENDGM-03, ENDGM-04, CONV-01, CONV-02, CONV-03]

duration: 5min
completed: 2026-03-26
---

# Phase 29 Plan 01: Endgame Analytics Backend Summary

**Two new REST endpoints with per-category W/D/L + inline conversion/recovery stats via MIN-ply subquery + Python-side endgame classification from material_signature strings**

## Performance

- **Duration:** 5 min
- **Started:** 2026-03-26T09:36:06Z
- **Completed:** 2026-03-26T09:41:12Z
- **Tasks:** 2
- **Files created/modified:** 7

## Accomplishments

- GET /api/endgames/stats returns 6 endgame categories (rook/minor_piece/pawn/queen/mixed/pawnless) with W/D/L + conversion/recovery stats inline, sorted by game count descending
- GET /api/endgames/games returns paginated GameRecord list filtered by endgame_class, reusing existing schema
- 25 new tests (18 unit + 7 integration), all passing; zero regressions across full 404-test suite

## Task Commits

1. **Task 1: Create test stubs for endgame service and repository** - `262e170` (test)
2. **Task 2: Implement schemas, repository, service, and router** - `f297467` (feat)

## Files Created/Modified

- `/home/aimfeld/Projects/Python/flawchess/app/schemas/endgames.py` - Pydantic models: ConversionRecoveryStats, EndgameCategoryStats, EndgameStatsResponse, EndgameGamesResponse
- `/home/aimfeld/Projects/Python/flawchess/app/repositories/endgame_repository.py` - SQL queries with ENDGAME_MATERIAL_THRESHOLD=2600, MIN ply subquery, user_material_imbalance sign flip
- `/home/aimfeld/Projects/Python/flawchess/app/services/endgame_service.py` - classify_endgame_class, _aggregate_endgame_stats, get_endgame_stats, get_endgame_games
- `/home/aimfeld/Projects/Python/flawchess/app/routers/endgames.py` - HTTP layer for /endgames/stats and /endgames/games
- `/home/aimfeld/Projects/Python/flawchess/app/main.py` - Registered endgames_router at /api prefix
- `/home/aimfeld/Projects/Python/flawchess/tests/test_endgame_service.py` - 18 unit tests for classify + aggregate
- `/home/aimfeld/Projects/Python/flawchess/tests/test_endgame_repository.py` - 7 integration tests for repository queries

## Decisions Made

- **classify_endgame_class mixed rules:** rook+pawn remains "rook" (pawn co-exists naturally with rook); minor+pawn = "mixed"; Q+anything_else = "mixed"; R+minor = "mixed". This matches RESEARCH.md specification and the test expectations.
- **user_material_imbalance sign flip in SQL:** Used a CASE expression to multiply material_imbalance by -1 when user_color="black", ensuring positive value always means user has material advantage (white's perspective is stored in DB).
- **query_endgame_games uses Python-side classification:** Fetch all entry rows, call classify_endgame_class in Python, then paginate. Simpler and correct for expected user data volumes (hundreds of games).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed classification: rook+pawn = rook (not mixed)**
- **Found during:** Task 2 (running service tests)
- **Issue:** Initial implementation counted all families (including pawn) to determine "mixed", so KRPP_KRP classified as "mixed" instead of "rook"
- **Fix:** Rewrote classify_endgame_class to use explicit mixed conditions from RESEARCH.md: Q+any, R+minor, minor+pawn. Rook+pawn and queen+pawn are single-family (not mixed).
- **Files modified:** app/services/endgame_service.py
- **Verification:** test_rook_with_pawns passes; all 18 service tests pass
- **Committed in:** f297467 (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 - Bug)
**Impact on plan:** Bug fix necessary for correct classification. No scope creep.

## Issues Encountered

None — aside from the classification bug documented above.

## Known Stubs

None — both endpoints are fully wired to the database.

## Next Phase Readiness

- Backend API complete; ready for Plan 02 (frontend EndgamesPage with Statistics sub-tab)
- Plan 03 (Games sub-tab) can consume GET /api/endgames/games with the GameRecord schema already established
- No blockers

## Self-Check: PASSED

- app/schemas/endgames.py: FOUND
- app/repositories/endgame_repository.py: FOUND
- app/services/endgame_service.py: FOUND
- app/routers/endgames.py: FOUND
- tests/test_endgame_service.py: FOUND
- tests/test_endgame_repository.py: FOUND
- Commit 262e170: FOUND (test - RED phase)
- Commit f297467: FOUND (feat - GREEN phase)

---
*Phase: 29-endgame-analytics*
*Completed: 2026-03-26*
