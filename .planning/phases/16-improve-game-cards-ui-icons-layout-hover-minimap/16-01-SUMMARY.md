---
phase: 16-improve-game-cards-ui-icons-layout-hover-minimap
plan: 01
subsystem: api
tags: [python-chess, zobrist, sqlalchemy, pydantic, typescript, pgn]

# Dependency graph
requires:
  - phase: 15-enhanced-game-import-data
    provides: import pipeline with move_count, termination, time_control_str
provides:
  - result_fen column on Game model (nullable VARCHAR 100)
  - hashes_for_game() returns (hash_tuples, result_fen) 2-tuple
  - Import pipeline stores result_fen via sa_update alongside move_count
  - GameRecord API schema exposes result_fen (backend Pydantic + frontend TypeScript)
affects: [16-02-hover-minimap, game-cards-ui]

# Tech tracking
tech-stack:
  added: []
  patterns: [board.board_fen() captured at import time inside existing PGN replay loop at zero extra cost]

key-files:
  created: []
  modified:
    - app/services/zobrist.py
    - app/models/game.py
    - app/services/import_service.py
    - app/schemas/analysis.py
    - frontend/src/types/api.ts
    - tests/test_zobrist.py
    - tests/test_import_service.py

key-decisions:
  - "hashes_for_game() 2-tuple return: (hash_tuples, result_fen) — breaking change handled by updating all call sites and mocks in the same plan"
  - "result_fen stored as VARCHAR(100) nullable — board_fen() output is ~70 chars max, 100 is safe headroom"
  - "result_fen computed inside existing hashes_for_game loop, not a separate PGN re-parse — zero additional overhead"

patterns-established:
  - "board.board_fen() captured after the final board.push() in hashes_for_game, returned alongside hash_tuples"
  - "Import service unpacks (hash_tuples, result_fen) from hashes_for_game, stores result_fen in the same sa_update as move_count"

requirements-completed: [GCUI-01, GCUI-02]

# Metrics
duration: 4min
completed: 2026-03-18
---

# Phase 16 Plan 01: Add result_fen Storage at Import Time Summary

**result_fen (final board position FEN) added to Game model, zobrist module, import pipeline, and API schemas — enables hover minimap on game cards without query-time PGN re-parsing**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-18T21:06:28Z
- **Completed:** 2026-03-18T21:10:18Z
- **Tasks:** 2
- **Files modified:** 7

## Accomplishments
- `hashes_for_game()` now returns `(hash_tuples, result_fen)` 2-tuple where `result_fen` is `board.board_fen()` after the final move
- `Game` model has `result_fen: Mapped[str | None] = mapped_column(String(100), nullable=True)` column
- Import pipeline stores `result_fen` alongside `move_count` in `sa_update` — no second PGN parse needed
- `GameRecord` Pydantic schema and TypeScript interface both include `result_fen: string | null`
- All 48 tests in `test_zobrist.py` and `test_import_service.py` pass with updated call sites and mocks

## Task Commits

Each task was committed atomically:

1. **Task 1: Add result_fen to backend model, zobrist, import service, and schemas** - `4e77053` (feat)
2. **Task 2: Update test suites for new hashes_for_game signature** - `afecc8b` (test)

**Plan metadata:** (docs commit to follow)

## Files Created/Modified
- `app/services/zobrist.py` - New signature returns (list, str|None) 2-tuple; result_fen = board.board_fen() after final position
- `app/models/game.py` - Added result_fen nullable VARCHAR(100) column after move_count
- `app/services/import_service.py` - Unpacks (hash_tuples, result_fen); stores result_fen in sa_update values
- `app/schemas/analysis.py` - GameRecord class has result_fen: str | None = None
- `frontend/src/types/api.ts` - GameRecord interface has result_fen: string | null
- `tests/test_zobrist.py` - All call sites updated to 2-tuple unpack; 2 new tests added
- `tests/test_import_service.py` - Mock return values corrected to (list_of_6tuples, result_fen) shape

## Decisions Made
- result_fen computed inside existing `hashes_for_game()` loop (after final `board.push()`), not a separate PGN parse — zero overhead
- VARCHAR(100) for result_fen — `board.board_fen()` output is ~70 chars for starting position, 100 is safe headroom

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed pre-existing broken mock tuples in test_import_service.py**
- **Found during:** Task 2 (update test suites)
- **Issue:** All `hashes_for_game` mocks in test_import_service.py returned 5-tuples (missing `clock_seconds`) instead of 6-tuples. The tests "passed" only because exceptions were silently swallowed in the `try/except` block. With our change, these mocks now need to return the correct 2-tuple shape anyway.
- **Fix:** Updated all 3 mock `return_value` entries to `(list_of_6tuples, result_fen_string)` format with correct 6-element inner tuples
- **Files modified:** tests/test_import_service.py
- **Verification:** `uv run pytest tests/test_import_service.py -x` passes
- **Committed in:** afecc8b (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 — bug in test mocks)
**Impact on plan:** Fix was necessary since mocks had to be updated for the new 2-tuple return shape anyway. No scope creep.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- `result_fen` is now stored at import time and exposed via the API
- Plan 16-02 can use `result_fen` from `GameRecord` to render the hover minimap on game cards
- A DB migration will be needed before deploying (new `result_fen` column on `games` table)

---
*Phase: 16-improve-game-cards-ui-icons-layout-hover-minimap*
*Completed: 2026-03-18*
