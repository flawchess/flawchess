---
phase: 164-maia-elo-lichess-blitz-normalization
plan: 02
subsystem: api
tags: [python, fastapi, pydantic, rating-conversion, maia, library-service]

# Dependency graph
requires:
  - "normalize_to_lichess_blitz(rating, platform, source_tc, *, is_correspondence) — Plan 01's pure dispatcher"
provides:
  - "GameFlawCard.white_rating_lichess_blitz / .black_rating_lichess_blitz — nullable Lichess-Blitz-equivalent ratings on GET /api/library/games/{game_id}"
affects: [164-03]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "cast(Platform, game.platform) / cast(TimeControlBucket, game.time_control_bucket) — narrows the DB's plain str columns to the Literal types normalize_to_lichess_blitz requires, mirroring endgame_service.py's existing cast(TimeControlBucket, tc_str) precedent"
    - "Correspondence-check-before-dispatch: is_correspondence_time_control(game.time_control_str) computed once in _build_card, passed into both white/black normalize_to_lichess_blitz calls"

key-files:
  created: []
  modified:
    - app/schemas/library.py
    - app/services/library_service.py
    - tests/services/test_library_service.py

key-decisions:
  - "cast() (not a Platform/TimeControlBucket type redeclaration) narrows game.platform/game.time_control_bucket at the call site — the Game model's columns are plain Mapped[str]/Mapped[str | None], not Literal-typed, so ty requires an explicit narrowing; the same pattern already exists in endgame_service.py"
  - "_seed_db_game extended with optional white_rating/black_rating/time_control_str/time_control_bucket parameters (defaults unchanged: '600+0'/'blitz') rather than adding a parallel seeding helper — keeps one canonical Game-row builder for the whole test file"

patterns-established:
  - "Additive nullable-field extension of GameFlawCard (Pattern from 164-PATTERNS.md) — both new fields default to None so no other GameFlawCard(...) construction site or existing test fixture broke"

requirements-completed: []

coverage:
  - id: D3
    description: "GET /api/library/games/{game_id} returns GameFlawCard with white_rating_lichess_blitz/black_rating_lichess_blitz alongside unchanged raw white_rating/black_rating"
    requirement: "SEED-093"
    verification:
      - kind: integration
        ref: "tests/services/test_library_service.py::TestGetLibraryGame::test_chesscom_blitz_card_has_higher_normalized_rating"
        status: pass
    human_judgment: false
  - id: D4
    description: "chess.com Daily / correspondence games get None for both normalized fields while raw ratings stay populated"
    requirement: "SEED-093"
    verification:
      - kind: integration
        ref: "tests/services/test_library_service.py::TestGetLibraryGame::test_correspondence_game_card_has_none_normalized_ratings"
        status: pass
    human_judgment: false
  - id: D5
    description: "NULL ratings or NULL time_control_bucket yield None normalized fields without raising"
    requirement: "SEED-093"
    verification:
      - kind: integration
        ref: "tests/services/test_library_service.py::TestGetLibraryGame::test_null_rating_card_has_none_normalized_ratings"
        status: pass
    human_judgment: false

# Metrics
duration: 25min
completed: 2026-07-11
status: complete
---

# Phase 164 Plan 02: GameFlawCard Lichess-Blitz Rating Fields Summary

**Two nullable computed fields (`white_rating_lichess_blitz` / `black_rating_lichess_blitz`) now ride `GameFlawCard`, populated in `_build_card` via Plan 01's `normalize_to_lichess_blitz` with a correspondence check running first, and covered by 3 new integration tests.**

## Performance

- **Duration:** ~25 min
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- `GameFlawCard` (`app/schemas/library.py`) gains `white_rating_lichess_blitz: int | None = None` and `black_rating_lichess_blitz: int | None = None`, immediately after the existing raw rating fields, both defaulting to `None` so no other `GameFlawCard(...)` construction site (e.g. `library_repository.py`, if any exist) breaks.
- `_build_card` (`app/services/library_service.py`) computes `is_correspondence = is_correspondence_time_control(game.time_control_str)` once, then calls `normalize_to_lichess_blitz(rating, cast(Platform, game.platform), cast(TimeControlBucket, game.time_control_bucket), is_correspondence=is_correspondence)` for each color, guarded so the call only fires when the rating and `time_control_bucket` are both non-None. `cast()` narrows the Game model's plain `str`/`str | None` columns to the `Literal` types the pure dispatcher requires — the same pattern already used in `endgame_service.py`.
- The raw `white_rating=game.white_rating` / `black_rating=game.black_rating` construction lines are untouched; `git diff` confirms only additions around them.
- `tests/services/test_library_service.py::_seed_db_game` extended with optional `white_rating`/`black_rating`/`time_control_str`/`time_control_bucket` parameters (defaults `None`/`None`/`"600+0"`/`"blitz"` — byte-identical to prior hardcoded behavior for all existing call sites).
- 3 new integration tests added to `TestGetLibraryGame`, exercising the real `get_library_game` serialization path (not a hand-built card):
  1. chess.com blitz, rating 1500 → `white_rating_lichess_blitz == 1780` (a known Table 2 anchor), raw rating unchanged, normalized > raw.
  2. chess.com Daily (`time_control_str="1/172800"`, correspondence) → both normalized fields `None`, raw ratings stay populated.
  3. `white_rating`/`black_rating` both `None` → both normalized fields `None`, no exception.
- `uv run ty check app/ tests/` zero errors; `uv run ruff check app/ tests/` clean; targeted test subset (4 tests) and the full backend suite (`uv run pytest -n auto -x`, 3202 passed / 18 skipped) both green.

## Task Commits

1. **Task 1: Add the two nullable GameFlawCard fields + compute them in _build_card**
   - `93e40971` feat(164-02): add Lichess-blitz-normalized rating fields to GameFlawCard
2. **Task 2: Integration test — _build_card populates the two normalized fields**
   - `f9553b70` test(164-02): cover _build_card's Lichess-blitz-normalized rating fields

## Files Created/Modified
- `app/schemas/library.py` — Added `white_rating_lichess_blitz` / `black_rating_lichess_blitz` nullable fields to `GameFlawCard`, immediately after the existing raw rating fields, with a Phase 164 provenance comment.
- `app/services/library_service.py` — Imported `Platform`/`TimeControlBucket` (`app.schemas.normalization`), `normalize_to_lichess_blitz` (`app.services.chesscom_to_lichess`), and `cast` (`typing`); `_build_card` computes both normalized fields (correspondence-checked first) and passes them into the `GameFlawCard(...)` construction directly below the existing raw rating fields.
- `tests/services/test_library_service.py` — Extended `_seed_db_game` with optional rating/TC-override parameters; added 3 tests to `TestGetLibraryGame` covering blitz-normalization, correspondence, and NULL-rating cases.

## Decisions Made
- `cast(Platform, game.platform)` / `cast(TimeControlBucket, game.time_control_bucket)` at the `normalize_to_lichess_blitz` call site — the `Game` model's `platform` and `time_control_bucket` columns are plain `Mapped[str]` / `Mapped[str | None]`, not `Literal`-typed, so `ty` requires explicit narrowing to satisfy the dispatcher's `Platform`/`TimeControlBucket` parameter types. `endgame_service.py` already establishes this exact `cast(TimeControlBucket, tc_str)` pattern, so no new convention was introduced.
- Extended the existing `_seed_db_game` helper with optional overrides rather than writing a parallel seeding function or hand-rolled `GameModel(...)` construction per test — keeps one canonical Game-row builder for the whole test file; all prior call sites keep their exact original defaults (`time_control_str="600+0"`, `time_control_bucket="blitz"`, ratings `None`).
- `1500` chosen as the chess.com-blitz test rating because it's a documented Table 2 anchor from Plan 01's own test suite (`CHESSCOM_BLITZ_TO_LICHESS[1500]["blitz"] == 1780`), so the expected normalized value is a known constant rather than re-derived math in the test.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- `GameFlawCard.white_rating_lichess_blitz` / `.black_rating_lichess_blitz` are live on `GET /api/library/games/{game_id}`, ready for Plan 03 to mirror the same field names on the TypeScript side (`frontend/src/types/library.ts`) and consume them in `useMaiaEloDefault.ts`'s `deriveRawDefault`.
- No blockers or concerns.

---
*Phase: 164-maia-elo-lichess-blitz-normalization*
*Completed: 2026-07-11*

## Self-Check: PASSED

- FOUND: `.planning/phases/164-maia-elo-lichess-blitz-normalization/164-02-SUMMARY.md`
- FOUND: `white_rating_lichess_blitz: int | None = None` in `app/schemas/library.py`
- FOUND: `normalize_to_lichess_blitz(` call in `app/services/library_service.py`
- FOUND: commits `93e40971`, `f9553b70`
