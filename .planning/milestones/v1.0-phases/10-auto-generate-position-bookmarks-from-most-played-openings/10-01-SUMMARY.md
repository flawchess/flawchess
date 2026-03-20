---
phase: 10-auto-generate-position-bookmarks-from-most-played-openings
plan: 01
subsystem: api
tags: [fastapi, postgresql, sqlalchemy, python-chess, zobrist, position-bookmarks]

# Dependency graph
requires:
  - phase: 05-position-bookmarks-and-wdl-charts
    provides: PositionBookmark model, position_bookmark_repository CRUD, schemas
  - phase: 08-rework-games-and-bookmark-tabs
    provides: match_side field on PositionBookmark, compute_hashes service
provides:
  - GET /position-bookmarks/suggestions endpoint returning top 5 white + 5 black positions from ply range 6-14
  - PATCH /position-bookmarks/{id}/match-side endpoint with target_hash recomputation
  - get_existing_full_hashes repository function for bookmark deduplication
  - get_top_positions_for_color repository function for frequency-ranked positions
  - suggest_match_side heuristic based on opponent variation ratio
  - update_match_side repository function with FEN-based hash recomputation
  - PositionSuggestion, SuggestionsResponse, MatchSideUpdateRequest schemas
affects:
  - 10-02 (frontend suggestion UI consuming these endpoints)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - FEN-based hash recomputation — recompute white/black/full hashes by parsing bookmark.fen with chess.Board
    - Opponent variation ratio heuristic — distinct_full_hashes / distinct_games <= 1.5 means "mine" suggestion
    - Over-fetch + post-filter for deduplication in group-by queries

key-files:
  created: []
  modified:
    - app/schemas/position_bookmarks.py
    - app/repositories/position_bookmark_repository.py
    - app/routers/position_bookmarks.py
    - tests/test_bookmark_repository.py

key-decisions:
  - "get_existing_full_hashes uses FEN recomputation not target_hash column: bookmarks store target_hash as white/black/full depending on match_side, so full_hash must be recomputed from FEN for correct deduplication"
  - "suggest_match_side ratio threshold 1.5: distinct_full/distinct_games <= 1.5 returns mine (few opponent variations), else both"
  - "GET /suggestions before /{bookmark_id}: route ordering prevents FastAPI treating 'suggestions' as integer ID"
  - "PATCH /match-side safe after /{bookmark_id}: additional /match-side literal segment disambiguates path"

patterns-established:
  - "E402 fix — moved sys import to top of repository file to comply with ruff linting"

requirements-completed: [AUTOBKM-01, AUTOBKM-02, AUTOBKM-03, AUTOBKM-04]

# Metrics
duration: 4min
completed: 2026-03-15
---

# Phase 10 Plan 01: Suggestion Endpoint and Match-Side Update Summary

**Suggestion API returning top-N opening positions by Zobrist hash frequency with match-side heuristic, plus PATCH endpoint for recomputing target_hash from stored FEN**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-15T10:58:34Z
- **Completed:** 2026-03-15T11:02:34Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- Added `GET /position-bookmarks/suggestions` endpoint grouping game_positions by (white_hash, black_hash, full_hash) for ply 6-14, returning top 5 per color with FEN, SAN moves, opening name/ECO, game count, and suggested_match_side
- Added `PATCH /position-bookmarks/{id}/match-side` endpoint that recomputes target_hash from stored FEN using python-chess + compute_hashes based on new match_side value
- Added 8 new repository integration tests covering get_top_positions_for_color, deduplication, suggest_match_side (mine/both cases), and update_match_side (mine/both/wrong-user)

## Task Commits

Each task was committed atomically:

1. **Task 1: Add suggestion and match_side schemas, repository functions, and tests** - `2b37e8c` (feat)
2. **Task 2: Add suggestions and match_side update router endpoints** - `e9f8f95` (feat)

**Plan metadata:** (docs commit below)

## Files Created/Modified
- `app/schemas/position_bookmarks.py` - Added PositionSuggestion, SuggestionsResponse, MatchSideUpdateRequest schemas
- `app/repositories/position_bookmark_repository.py` - Added get_existing_full_hashes, get_top_positions_for_color, suggest_match_side, update_match_side; moved sys import to top
- `app/routers/position_bookmarks.py` - Added GET /suggestions and PATCH /match-side endpoints
- `tests/test_bookmark_repository.py` - Added TestSuggestions, TestMatchSideHeuristic, TestMatchSideUpdate test classes (8 new tests)

## Decisions Made
- `get_existing_full_hashes` recomputes full_hash from stored FEN rather than reading target_hash directly, because target_hash stores white/black/full hash depending on match_side — recomputation is the only way to reliably get the full_hash for deduplication
- `suggest_match_side` uses ratio = distinct_full_hashes / distinct_games with threshold 1.5 — low ratio means position has few unique opponent variations, so piece-only matching ("mine") is appropriate; high ratio means position varies a lot with opponent moves, so "both" is recommended
- Route ordering: GET /suggestions defined before GET /, to ensure FastAPI does not conflict with /{bookmark_id} routes

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Fixed E402 lint violation in repository file**
- **Found during:** Task 2 (lint check)
- **Issue:** The pre-existing `import sys as _sys` at the bottom of position_bookmark_repository.py (below function definitions) caused ruff E402 lint violation when new stdlib imports were added
- **Fix:** Moved `import sys as _sys` to the top-of-file imports block
- **Files modified:** app/repositories/position_bookmark_repository.py
- **Verification:** `uv run ruff check` passes
- **Committed in:** e9f8f95 (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Pre-existing lint issue surfaced by new imports, fixed inline. No scope creep.

## Issues Encountered
None - implementation followed plan specification exactly.

## Next Phase Readiness
- Backend API surface complete for auto-generate suggestions feature
- Ready for Phase 10 Plan 02: frontend UI consuming GET /suggestions and PATCH /match-side

---
*Phase: 10-auto-generate-position-bookmarks-from-most-played-openings*
*Completed: 2026-03-15*
