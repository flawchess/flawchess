---
phase: 164-maia-elo-lichess-blitz-normalization
plan: 01
subsystem: api
tags: [python, rating-conversion, maia, chesscom_to_lichess]

# Dependency graph
requires: []
provides:
  - "_invert_table2_column(rating, column) — inverts Table 2's Bullet/Rapid/Classical Lichess columns back to a chess.com-Blitz anchor, handling Classical's None-gap and 3-way 1935 tie"
  - "normalize_to_lichess_blitz(rating, platform, source_tc, *, is_correspondence) — public dispatcher normalizing any (platform, source_tc) rating to its Lichess-Blitz equivalent"
affects: [164-02, 164-03]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Filtered (anchor, value) pairs before bisect scan — the None-gap-safe inversion variant of _invert_intra_tc's assert-based scan, needed because Table 2's classical column has real None rows"
    - "Caller-supplied is_correspondence boolean keeps a pure-math module free of an app.services.normalization dependency edge"

key-files:
  created: []
  modified:
    - app/services/chesscom_to_lichess.py
    - tests/services/test_chesscom_to_lichess.py

key-decisions:
  - "Leftmost-tie-wins via bisect_left's exact-match branch resolves the classical column's 3-way 1935 tie to the lowest anchor (1500) — the zero-width interpolation guard is kept as a second line of defense but the exact-match short-circuit is what actually fires for this snapshot's tie"
  - "chess.com Daily is represented via is_correspondence=True rather than a distinct source_tc literal — TimeControlBucket (reused from app.schemas.normalization) has no 'daily' member; Daily/correspondence games bucket under whichever TC the DB assigned and are caught by the is_correspondence short-circuit regardless"
  - "lichess+blitz excluded from the 'six convertible combos' out-of-range parametrize — it is an unconditional identity mapping with no range check, so it never returns None"

patterns-established:
  - "Pattern 2 (filtered-pairs table inversion) and Pattern 3 (special-case-first dispatcher) from 164-PATTERNS.md implemented verbatim"

requirements-completed: [SEED-093]

coverage:
  - id: D1
    description: "_invert_table2_column inverts Table 2's Bullet/Rapid/Classical columns, filtering None rows and resolving the classical 3-way 1935 tie to the lowest anchor (1500)"
    requirement: "SEED-093"
    verification:
      - kind: unit
        ref: "tests/services/test_chesscom_to_lichess.py#test_invert_table2_column_classical_tie_returns_lowest_anchor"
        status: pass
      - kind: unit
        ref: "tests/services/test_chesscom_to_lichess.py#test_invert_table2_column_classical_none_gap_returns_none"
        status: pass
      - kind: unit
        ref: "tests/services/test_chesscom_to_lichess.py#test_invert_table2_column_rapid_exact_anchor_matches_known_row"
        status: pass
    human_judgment: false
  - id: D2
    description: "normalize_to_lichess_blitz dispatches all six convertible (platform, source_tc) paths, chess.com classical -> None, correspondence -> None for both platforms, and out-of-range -> None"
    requirement: "SEED-093"
    verification:
      - kind: unit
        ref: "tests/services/test_chesscom_to_lichess.py#test_normalize_to_lichess_blitz_chesscom_blitz_through_table2"
        status: pass
      - kind: unit
        ref: "tests/services/test_chesscom_to_lichess.py#test_normalize_to_lichess_blitz_correspondence_returns_none_chesscom"
        status: pass
      - kind: unit
        ref: "tests/services/test_chesscom_to_lichess.py#test_normalize_to_lichess_blitz_out_of_range_below_min_returns_none"
        status: pass
    human_judgment: false

# Metrics
duration: 20min
completed: 2026-07-11
status: complete
---

# Phase 164 Plan 01: Maia ELO Lichess-Blitz Normalization Primitive Summary

**Two new pure-Python functions in `chesscom_to_lichess.py` — `_invert_table2_column` and `normalize_to_lichess_blitz` — normalize any (platform, source_tc) chess rating to its Lichess-Blitz equivalent, with 22 new unit tests covering every source path and the classical-column tie/None-gap edges.**

## Performance

- **Duration:** ~20 min
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- `_invert_table2_column(rating, column)` inverts Table 2's Bullet/Rapid/Classical Lichess-scale columns back to a chess.com-Blitz anchor, filtering None rows (classical is None above chess.com Blitz 2700) and resolving the classical column's 3-way 1935 tie to the lowest anchor (1500) via leftmost-tie-wins `bisect_left`.
- `normalize_to_lichess_blitz(rating, platform, source_tc, *, is_correspondence)` is the single public dispatcher: correspondence → None (both platforms), chess.com classical → None (no native ChessGoals mapping), chess.com bullet/blitz/rapid chain through the existing `convert_chesscom_to_lichess`, lichess blitz is identity, lichess bullet/rapid/classical chain through the new inversion into the Table 2 blitz column.
- 22 new tests added (34 → 56 total in the file), all green; `uv run ty check` zero errors; `uv run ruff check`/`format` clean.
- Neither lookup table (`CHESSCOM_INTRA_TC`, `CHESSCOM_BLITZ_TO_LICHESS`) nor `_invert_intra_tc` was modified — verified via the additive-only diff.

## Task Commits

Each task followed RED → GREEN (tdd="true"):

1. **Task 1: Add `_invert_table2_column`**
   - `f2168504` test(164-01): add failing tests for _invert_table2_column
   - `78921eea` feat(164-01): implement _invert_table2_column
2. **Task 2: Add `normalize_to_lichess_blitz` dispatcher + full source-path tests**
   - `8f928c53` test(164-01): add failing tests for normalize_to_lichess_blitz
   - `81456b8c` feat(164-01): implement normalize_to_lichess_blitz dispatcher

_TDD tasks each produced a test → feat commit pair; no refactor commit was needed (no post-GREEN cleanup required)._

## Files Created/Modified
- `app/services/chesscom_to_lichess.py` - Added `_invert_table2_column` (Table 2 column inversion) and `normalize_to_lichess_blitz` (public dispatcher); imported `Platform`/`TimeControlBucket` from `app.schemas.normalization`; added a Phase 164 provenance note to the module docstring.
- `tests/services/test_chesscom_to_lichess.py` - Added 5 tests for `_invert_table2_column` (exact-anchor, mid-range interpolation, classical tie, classical None-gap, below-min/above-max) and 17 tests for `normalize_to_lichess_blitz` (all 6 convertible source paths, chess.com-classical → None, correspondence → None for both platforms, and 12 parametrized out-of-range cases across the 6 convertible combos).

## Decisions Made
- Leftmost-tie-wins via `bisect_left`'s exact-match branch is what actually resolves the classical column's 3-way 1935 tie to anchor 1500 for this snapshot (the zero-width `hi_val == lo_val` interpolation guard is retained as defensive code per the plan's action spec, but is not the branch exercised by the tie test given the table's current shape — the exact-match short-circuit fires first since `bisect_left` returns the leftmost duplicate).
- chess.com Daily is represented via `is_correspondence=True` rather than a distinct `source_tc` literal, since `TimeControlBucket` (reused from `app.schemas.normalization`, no re-declared type per the plan's key_links) has no `"daily"` member — Daily/correspondence games bucket under whichever TC the DB assigned and are caught by the `is_correspondence` short-circuit regardless of that bucket.
- `lichess`+`blitz` was excluded from the "six convertible combos" out-of-range parametrize test set — it's an unconditional identity mapping with no range check (`return rating` unconditionally), so it can never produce `None` from an out-of-range input. This leaves exactly 6 combos: chess.com{blitz,bullet,rapid} + lichess{bullet,rapid,classical}.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- `normalize_to_lichess_blitz` is ready for Plan 02 to wire into `GameFlawCard`/`_build_card` (`app/schemas/library.py`, `app/services/library_service.py`) and Plan 03 to consume on the frontend via `useMaiaEloDefault.ts`.
- No blockers or concerns.

---
*Phase: 164-maia-elo-lichess-blitz-normalization*
*Completed: 2026-07-11*

## Self-Check: PASSED

- FOUND: `.planning/phases/164-maia-elo-lichess-blitz-normalization/164-01-SUMMARY.md`
- FOUND: `def _invert_table2_column(` in `app/services/chesscom_to_lichess.py`
- FOUND: `def normalize_to_lichess_blitz(` in `app/services/chesscom_to_lichess.py`
- FOUND: commits `f2168504`, `78921eea`, `8f928c53`, `81456b8c`, `0687bb27`
