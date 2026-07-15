---
phase: 164-maia-elo-lichess-blitz-normalization
plan: 04
subsystem: api
tags: [maia, elo-normalization, chesscom, lichess, gap-closure]

# Dependency graph
requires:
  - phase: 164-maia-elo-lichess-blitz-normalization (plan 01)
    provides: normalize_to_lichess_blitz dispatch function and its original chess.com classical -> None contract (now reversed)
  - phase: 164-maia-elo-lichess-blitz-normalization (plan 03)
    provides: Maia ELO slider consuming *_lichess_blitz with a raw-rating `?? raw` fallback
provides:
  - "normalize_to_lichess_blitz maps chess.com classical (non-correspondence) -> rapid-scale conversion instead of None"
  - "Renamed/inverted unit test proving the classical->rapid mapping"
  - "New integration test pinning the converted card fields for a chess.com classical, non-correspondence game"
affects: []

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "chess.com classical bucket treated as rapid-scale via a typed effective_tc local, mirroring the module's existing _BUCKET_TO_SOURCE_TC convention used by the SQL composed-grid pipeline"

key-files:
  created: []
  modified:
    - app/services/chesscom_to_lichess.py
    - tests/services/test_chesscom_to_lichess.py
    - tests/services/test_library_service.py

key-decisions:
  - "Reversed 164-01's must-have (chess.com classical returns None) per locked user decision: DB count showed 105/149,553 (0.070%) chess.com games are classical-bucketed non-correspondence, all legitimate long real-time controls (3600+45, 1500+10, 3600) — fix rather than accept-the-risk"

patterns-established: []

requirements-completed: [SEED-093]

coverage:
  - id: D1
    description: "normalize_to_lichess_blitz maps chess.com classical (non-correspondence) to the rapid-scale Lichess-blitz conversion instead of None"
    requirement: "SEED-093"
    verification:
      - kind: unit
        ref: "tests/services/test_chesscom_to_lichess.py#test_normalize_to_lichess_blitz_chesscom_classical_maps_to_rapid"
        status: pass
      - kind: unit
        ref: "tests/services/test_chesscom_to_lichess.py#test_normalize_to_lichess_blitz_correspondence_returns_none_chesscom"
        status: pass
    human_judgment: false
  - id: D2
    description: "A chess.com classical-bucket, non-correspondence game's serialized GameFlawCard carries the converted rapid-scale normalized rating fields"
    requirement: "SEED-093"
    verification:
      - kind: integration
        ref: "tests/services/test_library_service.py::TestGetLibraryGame#test_chesscom_classical_noncorrespondence_card_has_normalized_rating"
        status: pass
      - kind: integration
        ref: "tests/services/test_library_service.py::TestGetLibraryGame#test_correspondence_game_card_has_none_normalized_ratings"
        status: pass
    human_judgment: false

# Metrics
duration: 15min
completed: 2026-07-11
status: complete
---

# Phase 164 Plan 04: chess.com classical -> rapid gap closure Summary

**Fixed `normalize_to_lichess_blitz` to map chess.com classical-bucketed, non-correspondence games onto the rapid conversion column instead of returning `None`, closing the raw-rating fallback that was seating the Maia ELO slider at the wrong scale for ~0.070% of chess.com games.**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-07-11T10:15:00Z (approx)
- **Completed:** 2026-07-11T10:25:07Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- `normalize_to_lichess_blitz`'s chess.com branch now maps `classical` -> `rapid` via a typed `effective_tc: ChessComSourceTC` local before calling `convert_chesscom_to_lichess`, matching the module's existing `_BUCKET_TO_SOURCE_TC` convention already relied on by the SQL composed-grid pipeline. The `is_correspondence` guard (chess.com Daily) is untouched and still short-circuits first.
- Docstring updated to describe the new classical -> rapid behavior and why (agreement between the two code paths; DB count showed these are rare but legitimate long real-time games).
- Renamed/inverted unit test: `test_normalize_to_lichess_blitz_chesscom_classical_returns_none` -> `test_normalize_to_lichess_blitz_chesscom_classical_maps_to_rapid`, now asserting the rapid-scale converted (non-None) value. The sibling correspondence test (`is_correspondence=True` -> `None`) is unchanged and still passes.
- New integration test `test_chesscom_classical_noncorrespondence_card_has_normalized_rating` in `TestGetLibraryGame` seeds a chess.com game with `time_control_bucket="classical"` and `time_control_str="1800+30"` (no Daily `/` separator) and asserts both `white_rating_lichess_blitz`/`black_rating_lichess_blitz` equal the rapid-scale conversion, while raw ratings stay untouched.

## Task Commits

Each task was committed atomically:

1. **Task 1: Map chess.com classical -> rapid in normalize_to_lichess_blitz + invert its unit test** - `c4b6d0b3` (fix)
2. **Task 2: Add IN-02 integration test for a chess.com classical-bucket non-correspondence game** - `914e896c` (test)

_Note: Task 1 was declared `tdd="true"` in the plan, but since it modifies an existing branch (rather than adding wholly new behavior from a red test), the fix and its inverted unit-test assertion were committed together as a single `fix` commit — the plan's own task description groups the source change and the test inversion as one atomic unit of work ("rewrite the branch" + "invert the now-stale test"), not a separate RED/GREEN pair._

## Files Created/Modified
- `app/services/chesscom_to_lichess.py` - `normalize_to_lichess_blitz`'s chess.com branch maps `classical` -> `rapid` via typed `effective_tc`; docstring updated
- `tests/services/test_chesscom_to_lichess.py` - renamed/inverted `test_normalize_to_lichess_blitz_chesscom_classical_maps_to_rapid`
- `tests/services/test_library_service.py` - new `test_chesscom_classical_noncorrespondence_card_has_normalized_rating` in `TestGetLibraryGame`

## Decisions Made
- Reversed the 164-01 must-have that specified chess.com classical returns `None`. Rationale (already locked before this plan was authored): the DB count showed 105/149,553 (0.070%) chess.com games are classical-bucketed, non-correspondence, and all are legitimate long real-time controls (`3600+45` x73, `1500+10` x11, `3600` x6) — worth converting rather than accepting the raw-rating fallback as risk.

## Deviations from Plan

None - plan executed exactly as written. The commit-grouping note above (Task 1 as a single `fix` commit rather than separate RED/GREEN commits) is a documentation clarification, not a deviation from the plan's `<action>` instructions, which described the source change and test inversion as one task.

## Issues Encountered
None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Phase 164's single verified gap (VERIFICATION.md Truth #13 / REVIEW.md WR-01) is closed. The Maia ELO slider now normalizes chess.com classical, non-correspondence ratings through the rapid-scale conversion instead of falling back to the raw rating.
- Full pre-merge gate confirmed green for the touched files: `ruff format`, `ruff check --fix`, `ty check` (zero errors), and `pytest -n auto` on both touched test modules (95 passed).
- No blockers for squash-merge to `main`.

---
*Phase: 164-maia-elo-lichess-blitz-normalization*
*Completed: 2026-07-11*

## Self-Check: PASSED
- FOUND: .planning/phases/164-maia-elo-lichess-blitz-normalization/164-04-SUMMARY.md
- FOUND: c4b6d0b3 (fix commit)
- FOUND: 914e896c (test commit)
