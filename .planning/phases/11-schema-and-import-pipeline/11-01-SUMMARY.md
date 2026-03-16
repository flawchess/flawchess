---
phase: 11-schema-and-import-pipeline
plan: 01
subsystem: database
tags: [postgresql, sqlalchemy, alembic, python-chess, zobrist, import-pipeline]

# Dependency graph
requires: []
provides:
  - move_san VARCHAR(10) nullable column on game_positions table
  - Covering index ix_gp_user_full_hash_move_san (user_id, full_hash, move_san)
  - hashes_for_game returns 5-tuples (ply, white_hash, black_hash, full_hash, move_san)
  - Import pipeline populates move_san in every game_positions row
affects: [12-backend-next-moves-endpoint]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "hashes_for_game 5-tuple: (ply, white_hash, black_hash, full_hash, move_san) — compute SAN before board.push(), final position has None"
    - "Covering index pattern: ix_gp_user_full_hash_move_san enables Phase 12 next-moves aggregation without join"

key-files:
  created:
    - alembic/versions/20260316_180737_d861bce078a5_add_move_san_to_game_positions.py
  modified:
    - app/models/game_position.py
    - app/services/zobrist.py
    - app/services/import_service.py
    - app/repositories/game_repository.py
    - tests/test_zobrist.py
    - tests/test_import_service.py
    - tests/test_game_repository.py

key-decisions:
  - "move_san ply semantics: ply-0 has first move SAN (e.g. 'e4'), final position row has NULL — not the reverse"
  - "board.san(move) called BEFORE board.push(move) — board must be in pre-move position for correct SAN"
  - "ix_gp_user_full_hash_move_san is additive — existing indexes (ix_gp_user_full_hash, ix_gp_user_white_hash, ix_gp_user_black_hash) preserved"

patterns-established:
  - "TDD red-green for zobrist: write failing tests, then restructure hashes_for_game, then verify green"
  - "Mock return values for hashes_for_game must be 5-tuples (ply, wh, bh, fh, move_san) in all test mocks"

requirements-completed: [MEXP-01, MEXP-02, MEXP-03]

# Metrics
duration: 4min
completed: 2026-03-16
---

# Phase 11 Plan 01: Schema and Import Pipeline Summary

**move_san column + covering index added to game_positions; hashes_for_game extended to 5-tuples with SAN computed before board.push(); import pipeline updated to persist move_san**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-16T18:06:22Z
- **Completed:** 2026-03-16T18:10:34Z
- **Tasks:** 2
- **Files modified:** 7

## Accomplishments
- Added `move_san VARCHAR(10) nullable` column to `game_positions` via Alembic migration (d861bce078a5)
- Added covering index `ix_gp_user_full_hash_move_san` on `(user_id, full_hash, move_san)` for Phase 12 next-moves queries
- Restructured `hashes_for_game` to return 5-tuples with SAN of move played FROM each position; final position row has `None`
- Updated import pipeline `_flush_batch` to unpack 5-tuples and include `move_san` in every position row dict
- Added 5 new tests in test_zobrist.py; added test_position_rows_include_move_san and test_insert_positions_with_move_san; full suite: 265 passed

## Task Commits

Each task was committed atomically:

1. **Task 1: Add move_san to GamePosition model, create migration, restructure hashes_for_game** - `9a34408` (feat)
2. **Task 2: Update import pipeline and remaining tests for move_san** - `ab1d2a5` (feat)

**Plan metadata:** (docs commit follows)

_Note: Task 1 used TDD (RED → GREEN): tests written first, then implementation, then migration applied._

## Files Created/Modified
- `app/models/game_position.py` - Added move_san Mapped[Optional[str]] column and ix_gp_user_full_hash_move_san index
- `app/services/zobrist.py` - hashes_for_game now returns list[tuple[int, int, int, int, str | None]] 5-tuples
- `app/services/import_service.py` - _flush_batch unpacks 5-tuples and adds move_san to position_rows
- `app/repositories/game_repository.py` - Updated bulk_insert_positions docstring to include move_san key
- `alembic/versions/20260316_180737_d861bce078a5_add_move_san_to_game_positions.py` - Migration: add_column + create_index
- `tests/test_zobrist.py` - Updated 5-tuple unpack; added 4 new tests for move_san semantics
- `tests/test_import_service.py` - Updated 2 mock return values to 5-tuples; added test_position_rows_include_move_san
- `tests/test_game_repository.py` - Updated test_insert_positions; added test_insert_positions_with_move_san

## Decisions Made
- move_san ply semantics: ply-0 row has the first move SAN (not None) — the STATE.md note saying "ply-0 has NULL" was superseded by the plan's explicit behavior spec
- `board.san(move)` must be called BEFORE `board.push(move)` — the board must be in pre-move position for correct SAN resolution
- The new covering index is additive — all three existing query-pattern indexes are kept intact

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- game_positions now has move_san populated on every row for new imports
- ix_gp_user_full_hash_move_san index ready for Phase 12 next-moves aggregation queries
- Existing data in DB will not have move_san (DB wipe accepted for v1.1 per STATE.md decision)

## Self-Check: PASSED

All created files exist. Both task commits verified in git log.

---
*Phase: 11-schema-and-import-pipeline*
*Completed: 2026-03-16*
