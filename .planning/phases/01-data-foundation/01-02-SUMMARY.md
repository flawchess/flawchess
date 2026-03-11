---
phase: 01-data-foundation
plan: 02
subsystem: database
tags: [python-chess, zobrist, hashing, postgresql, bigint, tdd, pytest]

# Dependency graph
requires:
  - phase: 01-data-foundation/01-01
    provides: SQLAlchemy models with BIGINT columns for white_hash/black_hash/full_hash

provides:
  - compute_hashes(board) returning (white_hash, black_hash, full_hash) as signed int64
  - hashes_for_game(pgn_text) returning list of (ply, wh, bh, fh) tuples
  - Color-independent hashing: white_hash changes only on white moves, black_hash only on black moves
  - 16 passing unit tests covering determinism, color-independence, BIGINT safety, PGN parsing

affects: [02-import-pipeline, 03-analysis-api]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "POLYGLOT_RANDOM_ARRAY indexing: 64 * ((piece_type - 1) * 2 + color_pivot) + square"
    - "ctypes.c_int64(h).value for unsigned-to-signed int64 conversion"
    - "Color-specific hashing by iterating board.occupied_co[color] squares"
    - "hashes_for_game returns empty list for empty/invalid/move-less PGN"

key-files:
  created:
    - app/services/zobrist.py
    - tests/__init__.py
    - tests/conftest.py
    - tests/test_zobrist.py
  modified: []

key-decisions:
  - "color_pivot: 0 for WHITE, 1 for BLACK — matches polyglot standard even/odd entries per piece type"
  - "hashes_for_game returns [] for PGN with no mainline moves (garbage input treated as invalid)"
  - "ply 0 included in hashes_for_game output — represents initial board state before any move"

patterns-established:
  - "TDD workflow: RED (ImportError) -> GREEN (all pass) -> REFACTOR (ruff clean)"

requirements-completed: [IMP-06]

# Metrics
duration: 3min
completed: 2026-03-11
---

# Phase 1 Plan 2: Zobrist Hash Computation Module Summary

**Deterministic three-hash scheme (white_hash, black_hash, full_hash) using python-chess POLYGLOT_RANDOM_ARRAY with ctypes.c_int64 conversion for PostgreSQL BIGINT safety, verified by 16 TDD tests.**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-11T12:34:41Z
- **Completed:** 2026-03-11T12:37:27Z
- **Tasks:** 3 (RED / GREEN / REFACTOR)
- **Files modified:** 4

## Accomplishments

- `app/services/zobrist.py` ships `compute_hashes()` and `hashes_for_game()` — the two functions all downstream import and analysis code will depend on
- Color-independent hashing confirmed: moving only white pieces changes `white_hash` but not `black_hash`, and vice versa — enables position queries scoped to one player's piece placement
- 16 unit tests cover determinism, different-position divergence, color independence, BIGINT range, empty board, PGN parsing edge cases, and transposition equivalence

## Task Commits

Each task was committed atomically:

1. **RED: Write failing tests** - `0dd4187` (test)
2. **GREEN + REFACTOR: Implement module, fix tests, lint** - `3139e1a` (feat)

_Note: GREEN and REFACTOR merged into one commit after iterating on two test correctness issues discovered during GREEN._

**Plan metadata:** (docs commit follows)

## Files Created/Modified

- `app/services/zobrist.py` - Zobrist hash module: `_color_hash()`, `compute_hashes()`, `hashes_for_game()`
- `tests/__init__.py` - Package marker for test discovery
- `tests/conftest.py` - `starting_board` and `empty_board` fixtures
- `tests/test_zobrist.py` - 16 unit tests for all hash behaviors

## Decisions Made

- **color_pivot convention**: 0 for WHITE, 1 for BLACK, matching the polyglot standard (white = even array indices per piece type, black = odd). Ensures the scheme is consistent with the built-in `chess.polyglot.zobrist_hash`.
- **Empty board hash**: `white_hash = 0` and `black_hash = 0` when no pieces of that color exist (XOR identity). `full_hash` is whatever the library returns for an empty board.
- **Invalid PGN handling**: `hashes_for_game()` returns `[]` when `read_game()` returns `None` (null parse) OR when the parsed game has no mainline moves (garbage input that python-chess partially parses). Keeps callers from receiving a ply-0-only list that looks valid.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Corrected ply count in test_hashes_for_game_includes_ply_zero**
- **Found during:** GREEN phase (first test run)
- **Issue:** Plan spec stated "For PGN '1. e4 e5 2. Nf3 *', returns 5 entries (ply 0 through 4)" but this PGN has only 3 half-moves (e4, e5, Nf3), producing 4 entries (ply 0-3). The plan had an off-by-one in the spec.
- **Fix:** Updated test assertion from `len == 5` / `plies == [0,1,2,3,4]` to `len == 4` / `plies == [0,1,2,3]`
- **Files modified:** tests/test_zobrist.py
- **Verification:** Test passes with corrected assertion
- **Committed in:** `3139e1a`

**2. [Rule 1 - Bug] Fixed invalid PGN behavior to return empty list**
- **Found during:** GREEN phase (first test run)
- **Issue:** python-chess `read_game("not a pgn at all !!!")` returns a Game object with 0 moves rather than None, so the original implementation returned `[(0, ...)]` for garbage input. Test expected `[]`.
- **Fix:** Added `if not moves: return []` check after extracting `list(game.mainline_moves())`. Games with no moves are treated as unparseable.
- **Files modified:** app/services/zobrist.py
- **Verification:** test_hashes_for_game_invalid_pgn passes; test_hashes_for_game_empty_pgn (empty string still returns None from read_game) also passes
- **Committed in:** `3139e1a`

---

**Total deviations:** 2 auto-fixed (both Rule 1 - Bug)
**Impact on plan:** Both fixes correct specification/implementation mismatches. No scope creep.

## Issues Encountered

None beyond the two test correctness issues documented above.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- `compute_hashes()` and `hashes_for_game()` are ready for the import pipeline (Phase 2) to call on every PGN parsed from chess.com/lichess
- `game_positions` table schema (from 01-01) stores `white_hash`, `black_hash`, `full_hash` as BIGINT — the types now have a verified producer
- All hash values confirmed to fit PostgreSQL BIGINT range

## Self-Check: PASSED

- app/services/zobrist.py: FOUND
- tests/test_zobrist.py: FOUND
- tests/conftest.py: FOUND
- tests/__init__.py: FOUND
- Commit 0dd4187 (RED): FOUND
- Commit 3139e1a (GREEN): FOUND

---
*Phase: 01-data-foundation*
*Completed: 2026-03-11*
