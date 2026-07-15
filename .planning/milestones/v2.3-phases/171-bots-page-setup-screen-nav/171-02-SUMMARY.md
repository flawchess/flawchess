---
phase: 171-bots-page-setup-screen-nav
plan: 02
subsystem: api
tags: [fastapi, pydantic, react, typescript, rating-normalization]

# Dependency graph
requires:
  - phase: 94.4
    provides: user_rating_anchors table + fetch_anchors_for_user repository (blended lichess-equivalent median per TC bucket)
  - phase: 164
    provides: lichess-blitz normalization precedent (normalize_to_lichess_blitz, useMaiaEloDefault D-07 game-mode branch)
  - phase: 167
    provides: store_bot_game_service's precedent use of the same blitz-bucket anchor for stamping a stored bot game's player rating
provides:
  - "GET/PUT /users/me/profile now return lichess_blitz_equivalent_rating (int | null), the caller's own blitz-bucket user_rating_anchors.anchor_rating"
  - "Frontend UserProfile + MaiaEloProfile types carry the new field"
  - "Analysis board's free-play ELO default (useMaiaEloDefault) reads the normalized field instead of the raw current_rating (D-08 fix)"
affects: [171-05-setup-screen, bots-page]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Module-private _lichess_blitz_equivalent_rating() helper mirrors the existing _primary_current_rating() precedent in app/routers/users.py"
    - "UI-DEFAULT-ONLY / BOT-03 comment convention: any rating field derived for slider defaults must carry an explicit non-adaptivity note at both the schema field and the helper"

key-files:
  created: []
  modified:
    - app/schemas/users.py
    - app/routers/users.py
    - tests/test_users_router.py
    - frontend/src/types/users.ts
    - frontend/src/hooks/useMaiaEloDefault.ts
    - frontend/src/hooks/__tests__/useMaiaEloDefault.test.ts

key-decisions:
  - "_lichess_blitz_equivalent_rating() reads anchors.get('blitz') only; rapid/classical-only users deliberately get None (D-07 semantic, not a bug)"
  - "MaiaEloProfile.lichess_blitz_equivalent_rating added as a required (non-optional) field alongside the existing current_rating, matching the backend contract; current_rating is kept on both TS types for other consumers, not deleted"
  - "Test fixture profile() helper widened to take both currentRating and lichessBlitzEquivalentRating (default null), with a differing-values case (1900 vs 1650) that turns red if the D-08 repoint is ever reverted"

patterns-established:
  - "Rating-default fields sourced from user_rating_anchors must be documented UI DEFAULT ONLY / BOT-03 at both the Pydantic field and the TS interface field"

requirements-completed: [PLAY-02]

coverage:
  - id: D1
    description: "GET/PUT /users/me/profile return lichess_blitz_equivalent_rating sourced from the caller's own blitz-bucket anchor; null for no-anchor and non-blitz-only-anchor users"
    requirement: "PLAY-02"
    verification:
      - kind: integration
        ref: "tests/test_users_router.py::TestProfileLichessBlitzEquivalentRating#test_profile_returns_null_lichess_blitz_when_no_anchors"
        status: pass
      - kind: integration
        ref: "tests/test_users_router.py::TestProfileLichessBlitzEquivalentRating#test_profile_returns_lichess_blitz_anchor_rating"
        status: pass
      - kind: integration
        ref: "tests/test_users_router.py::TestProfileLichessBlitzEquivalentRating#test_profile_returns_null_lichess_blitz_when_only_non_blitz_anchors"
        status: pass
      - kind: integration
        ref: "tests/test_users_router.py::TestProfileLichessBlitzEquivalentRating#test_put_profile_returns_lichess_blitz_anchor_rating"
        status: pass
    human_judgment: false
  - id: D2
    description: "Analysis board's free-play ELO default reads the normalized lichess_blitz_equivalent_rating instead of the raw current_rating (D-08)"
    requirement: "PLAY-02"
    verification:
      - kind: unit
        ref: "frontend/src/hooks/__tests__/useMaiaEloDefault.test.ts#free play: resolves from profile.lichess_blitz_equivalent_rating, NOT the raw current_rating (D-08)"
        status: pass
      - kind: unit
        ref: "frontend/src/hooks/__tests__/useMaiaEloDefault.test.ts#free play: lichess_blitz_equivalent_rating null falls back to FREE_PLAY_DEFAULT_ELO regardless of current_rating"
        status: pass
    human_judgment: false

duration: 6min
completed: 2026-07-14
status: complete
---

# Phase 171 Plan 02: Lichess-Blitz Equivalent Rating Profile Field Summary

**Exposed the user's blitz-bucket `user_rating_anchors.anchor_rating` as `lichess_blitz_equivalent_rating` on `/users/me/profile`, and repointed the analysis board's free-play ELO default at it instead of the raw, chess.com-inflated `current_rating`.**

## Performance

- **Duration:** 6 min
- **Started:** 2026-07-14T11:39:00+02:00 (approx.)
- **Completed:** 2026-07-14T11:45:00+02:00
- **Tasks:** 3
- **Files modified:** 6

## Accomplishments
- `UserProfileResponse.lichess_blitz_equivalent_rating` (new, `int | None`) added and wired into both `get_profile` and `update_profile` via a new `_lichess_blitz_equivalent_rating()` helper reading `fetch_anchors_for_user(...).get("blitz")`
- Four new backend tests pin the value, the no-anchor null case, the deliberate non-blitz-only-anchor null case, and PUT/GET parity
- `UserProfile` (frontend) and `MaiaEloProfile` (hook) types widened with the same field; `useMaiaEloDefault`'s free-play branch now reads `profile.lichess_blitz_equivalent_rating` instead of `profile.current_rating` (D-08)
- Frontend hook tests widened with a mutation-visible differing-values case (raw 1900 vs normalized 1650) so a revert of the one-line repoint turns the test red

## Task Commits

Each task was committed atomically:

1. **Task 1: Add the lichess_blitz_equivalent_rating field to the profile schema and both handlers** - `5db241e7` (feat)
2. **Task 2: Backend tests for the new field (V-12)** - `348b9616` (test)
3. **Task 3: Frontend type + D-08 free-play ELO default repoint** - `e767afc7` (feat)

_Note: no TDD RED/GREEN split was applied per-task since each task's own `<verify>` block runs tests inline; deviation-free, single-commit-per-task execution._

## Files Created/Modified
- `app/schemas/users.py` - `UserProfileResponse.lichess_blitz_equivalent_rating: int | None = None`, with D-07/BOT-03 doc comment
- `app/routers/users.py` - `_lichess_blitz_equivalent_rating()` helper; both `get_profile` and `update_profile` call `fetch_anchors_for_user(session, user_id=user.id)` and pass the derived value
- `tests/test_users_router.py` - `TestProfileLichessBlitzEquivalentRating` (4 new tests)
- `frontend/src/types/users.ts` - `UserProfile.lichess_blitz_equivalent_rating: number | null`
- `frontend/src/hooks/useMaiaEloDefault.ts` - `MaiaEloProfile.lichess_blitz_equivalent_rating`; `deriveRawDefault`'s free-play return repointed; docstring updated to cite D-08
- `frontend/src/hooks/__tests__/useMaiaEloDefault.test.ts` - `profile()` fixture widened (2-arg); 4 free-play cases (repoint-pinning differing-values case, null-anchor fallback, undefined-profile fallback, out-of-ladder clamp)

## Decisions Made
- `_lichess_blitz_equivalent_rating()` reads only the `"blitz"` TC bucket — rapid/classical-only anchor users correctly get `None`, matching D-07's deliberate semantic (not aggregated across TCs)
- `MaiaEloProfile.lichess_blitz_equivalent_rating` made required (non-optional), matching the always-present backend field; `current_rating` retained on both TS types (not deleted) since other call sites still read it
- Test `profile()` helper widened to accept `(currentRating, lichessBlitzEquivalentRating = null)` rather than adding a second helper, keeping existing call sites at other test cases (game-mode tests use `profile: undefined` and are unaffected)

## Deviations from Plan

None - plan executed exactly as written. `app/repositories/__init__.py` is intentionally empty (submodule-style imports), so no changes were needed there beyond adding `user_rating_anchors_repository` to the existing `from app.repositories import ...` line as specified.

## Issues Encountered
- Initial import attempt (`from app.models.user_rating_anchors import RatingAnchorRow, TimeControlBucket`) failed `ty check` because `RatingAnchorRow` lives in `app/repositories/user_rating_anchors_repository.py`, not the model module. Fixed inline (Rule 1 — trivial import-path bug) by importing `RatingAnchorRow` from its actual module; `TimeControlBucket` import from the model module was correct as-is.
- Test method names initially used a `blitz_anchor` naming pattern that didn't match the plan's `-k lichess_blitz` verify filter; renamed to include `lichess_blitz` literally in each test name (Rule 1 — verification-command fidelity) so `pytest -k lichess_blitz` collects all 4 new cases as the plan's acceptance criteria requires.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- `lichess_blitz_equivalent_rating` is live on `/users/me/profile` and consumed by the analysis board's free-play default; Plan 05 (Bots page setup screen) can now default its ELO slider from the same normalized field via `useUserProfile()`.
- No blockers.

---
*Phase: 171-bots-page-setup-screen-nav*
*Completed: 2026-07-14*

## Self-Check: PASSED

All 7 modified/created files verified present on disk; all 3 task commits (`5db241e7`, `348b9616`, `e767afc7`) verified present in git log.
