---
phase: 15-enhanced-game-import-data
plan: 01
subsystem: database
tags: [postgres, sqlalchemy, alembic, python-chess, zobrist, normalization]

# Dependency graph
requires:
  - phase: 11-schema-and-import-pipeline
    provides: game/game_positions models, zobrist module, normalization functions, import service

provides:
  - clock_seconds column on game_positions table (from %clk PGN annotations)
  - termination_raw and termination columns on games table
  - hashes_for_game returns 6-tuples including clock_seconds
  - 180s time control correctly classified as blitz (not bullet)
  - username-scoped incremental sync boundary (prevents cross-username pollution)

affects: [15-02-plan, import-pipeline, game-metadata-api]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "6-tuple unpacking for zobrist positions: (ply, white_hash, black_hash, full_hash, move_san, clock_seconds)"
    - "Termination normalization: platform-specific string -> canonical bucket (checkmate|resignation|timeout|draw|abandoned|unknown)"
    - "Username-scoped sync boundary: get_latest_for_user_platform includes username filter"

key-files:
  created:
    - alembic/versions/20260318_193652_6dc12353580e_add_clock_seconds_termination_columns.py
  modified:
    - app/models/game.py
    - app/models/game_position.py
    - app/services/zobrist.py
    - app/services/normalization.py
    - app/services/import_service.py
    - app/repositories/import_job_repository.py
    - app/repositories/game_repository.py
    - tests/test_zobrist.py
    - tests/test_normalization.py

key-decisions:
  - "180s time control is blitz: strict < 180 for bullet (was <=180), so 3+0 and 180+0 are both blitz"
  - "clock_seconds stored as Float nullable — None when PGN lacks %clk or for final position rows"
  - "Termination extracted from losing player result (chess.com) or status field (lichess)"
  - "username-scoped sync: get_latest_for_user_platform adds username param to WHERE clause"

patterns-established:
  - "TDD for behavioral changes: failing tests written first, implementation follows"
  - "6-tuple unpacking in _flush_batch: for ply, white_hash, black_hash, full_hash, move_san, clock_seconds in hash_tuples"

requirements-completed: [EIGD-01, EIGD-02, EIGD-03, EIGD-04]

# Metrics
duration: 5min
completed: 2026-03-18
---

# Phase 15 Plan 01: Enhanced Game Import Data - Backend Pipeline Summary

**Clock extraction from %clk PGN annotations, termination reason normalization for both platforms, 180s blitz boundary fix, and username-scoped incremental sync**

## Performance

- **Duration:** 5 min
- **Started:** 2026-03-18T19:33:08Z
- **Completed:** 2026-03-18T19:38:30Z
- **Tasks:** 2
- **Files modified:** 9

## Accomplishments

- Added `clock_seconds` (Float nullable) to `game_positions` table; `hashes_for_game` now returns 6-tuples extracting `%clk` annotations via `node.clock()`
- Added `termination_raw` and `termination` to `games` table with platform-specific mapping dicts for chess.com and lichess
- Fixed time control boundary: `180+0` now correctly classified as blitz; `179+0` and below as bullet
- Fixed multi-username import: `get_latest_for_user_platform` now filters by `username` so a second username on the same platform starts a full fetch independently

## Task Commits

Each task was committed atomically:

1. **Task 1: Models, migration, zobrist clock extraction, and normalization changes** - `6c54c87` (feat)
2. **Task 2: Import service integration and username sync fix** - `8977dfc` (feat)

**Plan metadata:** (docs commit follows)

_Note: Task 1 used TDD — failing tests written first, then implementation_

## Files Created/Modified

- `app/models/game.py` - Added termination_raw (String 50) and termination (String 20) columns
- `app/models/game_position.py` - Added clock_seconds (Float nullable) column
- `app/services/zobrist.py` - Returns 6-tuples; uses mainline() nodes with node.clock() for clock extraction
- `app/services/normalization.py` - Added _CHESSCOM_TERMINATION_MAP, _LICHESS_STATUS_MAP; fixed bullet boundary; extracts termination in both normalize functions
- `app/services/import_service.py` - Updated _flush_batch to unpack 6-tuple and include clock_seconds in position rows; passes job.username to sync boundary query
- `app/repositories/import_job_repository.py` - Added username parameter to get_latest_for_user_platform
- `app/repositories/game_repository.py` - Updated docstring to reflect 8 columns per position row
- `alembic/versions/20260318_193652_6dc12353580e_add_clock_seconds_termination_columns.py` - Migration adding all 3 new columns
- `tests/test_zobrist.py` - New tests for clock extraction with/without %clk; updated 5-tuple tests to 6-tuple
- `tests/test_normalization.py` - Updated bullet boundary test; new termination tests for chess.com and lichess

## Decisions Made

- 180s time control is blitz: the CLAUDE.md said `<=180s = bullet`, but the plan spec correctly changes this to strict `< 180` so 3+0 (180s) is blitz. This matches chess.com/lichess classification conventions.
- clock_seconds stored as `Float` (not `Numeric`) for simplicity; sub-second precision (e.g. 598.3) is preserved without needing decimal arithmetic.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Updated existing test tuple unpacking from 5 to 6 elements**
- **Found during:** Task 1 (GREEN phase - running tests after implementing 6-tuple return)
- **Issue:** Existing tests `test_hashes_for_game_returns_int64_values` and `test_hashes_for_game_returns_move_san` used 5-element tuple unpacking and 5-tuple length assertion, which broke when hashes_for_game was changed to return 6-tuples
- **Fix:** Updated unpacking pattern `_, wh, bh, fh, _` to `_, wh, bh, fh, _, _` and changed `len(r) == 5` to `len(r) == 6`
- **Files modified:** tests/test_zobrist.py
- **Verification:** All 93 tests pass
- **Committed in:** 6c54c87 (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 - bug)
**Impact on plan:** The tuple unpacking fix was a direct consequence of the intentional return type change. No scope creep.

## Issues Encountered

None - all changes applied cleanly.

## Next Phase Readiness

- Database schema and migration in place; clock_seconds and termination data will be populated on next import
- Plan 02 can use termination data for game metadata enrichment in API responses
- Username-scoped sync fix means users can now import both chess.com usernames independently

## Self-Check: PASSED

- app/models/game.py: FOUND
- app/models/game_position.py: FOUND
- app/services/zobrist.py: FOUND
- app/services/normalization.py: FOUND
- 15-01-SUMMARY.md: FOUND
- Commit 6c54c87: FOUND
- Commit 8977dfc: FOUND

---
*Phase: 15-enhanced-game-import-data*
*Completed: 2026-03-18*
