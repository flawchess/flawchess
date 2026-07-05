---
phase: 151-maia-in-the-browser-all-position-surfaces
plan: 03
subsystem: api
tags: [fastapi, sqlalchemy, pydantic, react, typescript]

requires:
  - phase: none
    provides: independent Wave 1 plan — no dependency on Maia ONNX contract
provides:
  - "GET/PUT /users/me/profile now returns current_rating: int | null"
  - "game_repository.get_current_rating_by_platform() — index-backed, read-only"
  - "frontend UserProfile.current_rating: number | null"
affects: [151-06 (free-play ELO-selector default, D-07)]

tech-stack:
  added: []
  patterns:
    - "Insertion-ordered dict as an implicit recency contract: get_current_rating_by_platform
       builds its per-platform dict by scanning ORDER BY played_at DESC in Python and keeping
       the first occurrence per platform, so the first dict key is always the platform of the
       user's single most-recent game — callers needing one scalar take next(iter(dict.values()))
       instead of a second query."

key-files:
  created: []
  modified:
    - app/repositories/game_repository.py
    - app/schemas/users.py
    - app/routers/users.py
    - frontend/src/types/users.ts
    - tests/test_game_repository.py
    - tests/test_users_router.py

key-decisions:
  - "Single query ordered by played_at DESC (rides ix_games_user_played_at), reduced to
     one row per platform in Python — avoids N per-platform round-trips per the plan's
     explicit instruction, and avoids a SQL window function for a 2-platform read."
  - "The per-platform dict's insertion order (not a second query, not an extra return field)
     is the mechanism the router uses to pick the single scalar current_rating — the first
     key inserted is provably the platform of the overall most-recent game, since that row
     is the first one scanned in DESC order and therefore also the first occurrence of its
     own platform."
  - "Tests placed in the existing tests/test_game_repository.py (repository-level, 3 behavior
     scenarios + recency-ordering + multi-platform + unrated) and tests/test_users_router.py
     (endpoint-level, 2 scenarios) rather than a new tests/test_users.py named in the plan —
     matches the project's existing repository-vs-router test split (no test_users.py exists;
     test_users_router.py is the established home for /users/me/profile tests)."

requirements-completed: []  # MAIA-04 is shared across Plans 03/04/06 — only partially delivered
                            # here (the "rating at game time" data source). Left [ ] Pending in
                            # REQUIREMENTS.md; Plans 04/06 close it (per-ELO curve + Maia WDL).

coverage:
  - id: D1
    description: "GET /users/me/profile returns current_rating (per-platform most-recent-game
      rating) or null when the user has no rated games"
    requirement: "MAIA-04"
    verification:
      - kind: unit
        ref: "tests/test_game_repository.py::TestGetCurrentRatingByPlatform (6 tests: white-most-recent, black-most-recent, no-games, recency-ordering, multi-platform, unrated)"
        status: pass
      - kind: integration
        ref: "tests/test_users_router.py::TestProfileCurrentRating (2 tests: null-with-no-games, current-rating-from-most-recent-game)"
        status: pass
    human_judgment: false
  - id: D2
    description: "Frontend UserProfile type exposes current_rating: number | null, matching backend field name/nullability"
    requirement: "MAIA-04"
    verification:
      - kind: unit
        ref: "npx tsc -b (frontend/src/types/users.ts)"
        status: pass
    human_judgment: false

duration: 20min
completed: 2026-07-05
status: complete
---

# Phase 151 Plan 03: current_rating on /users/me/profile Summary

**Added a read-only `current_rating` field to `/users/me/profile`, sourced from the user's
most-recent-game rating via a single index-backed query — the data source Plan 06's free-play
ELO-selector default (D-07) needs but didn't exist before this plan.**

## Performance

- **Duration:** ~20 min
- **Completed:** 2026-07-05
- **Tasks:** 2 (Task 1 TDD: repository + schema + router; Task 2: frontend type)
- **Files modified:** 6 (4 backend, 1 frontend type, plus tests split across 2 existing test files)

## Accomplishments
- `game_repository.get_current_rating_by_platform(session, user_id) -> dict[str, int | None]`:
  one query ordered by `played_at DESC` (rides `ix_games_user_played_at`), reduced to one row
  per platform in Python. Returns each platform's rating from the user's most recent game on
  that platform, keyed on the user's color (`white_rating` if `user_color == "white"` else
  `black_rating`).
- `UserProfileResponse.current_rating: int | None = None` wired into **both** assembly sites
  in `app/routers/users.py` (`get_profile` and `update_profile`) via a small
  `_primary_current_rating()` helper that takes the first value of the insertion-ordered dict.
- `frontend/src/types/users.ts`: `UserProfile.current_rating: number | null`, matching the
  backend field name and nullability exactly.
- No migration, no schema change, no DB write — a pure read-only field addition as specified.

## Task Commits

Each task was committed atomically (TDD RED → GREEN for Task 1):

1. **Task 1 RED: failing tests for current_rating** - `15826ac8` (test)
2. **Task 1 GREEN: repository query + response field** - `8038a492` (feat)
3. **Task 2: frontend type field** - `e55fc13d` (feat)

_No REFACTOR commit needed — implementation was minimal and clean on first pass._

## TDD Gate Compliance

- RED gate: `15826ac8` (`test(151-03): add failing tests for current_rating (MAIA-04)`) —
  confirmed failing via `ImportError: cannot import name 'get_current_rating_by_platform'`
  before any implementation existed.
- GREEN gate: `8038a492` (`feat(151-03): add current_rating to /users/me/profile (MAIA-04)`) —
  all 8 new tests (6 repository + 2 router) plus the full 3171-test backend suite pass.
- Gate sequence verified in git log: test → feat, in order. Compliant.

## Files Created/Modified
- `app/repositories/game_repository.py` - Added `get_current_rating_by_platform()`
- `app/schemas/users.py` - Added `UserProfileResponse.current_rating: int | None = None`
- `app/routers/users.py` - Added `_primary_current_rating()` helper; wired into `get_profile` and `update_profile`
- `frontend/src/types/users.ts` - Added `UserProfile.current_rating: number | null`
- `tests/test_game_repository.py` - `TestGetCurrentRatingByPlatform` (6 tests)
- `tests/test_users_router.py` - `TestProfileCurrentRating` (2 tests)

## Decisions Made
- Single query + Python-side per-platform reduction (not a SQL window function, not N
  per-platform queries) per the plan's explicit action text — simplest correct implementation
  for exactly 2 platforms.
- The per-platform dict's insertion order is the load-bearing mechanism for picking the scalar
  `current_rating` — documented in both the repository function's docstring and the router's
  `_primary_current_rating()` docstring so future readers don't need to reverse-engineer why
  dict ordering matters.
- Test placement: repository-level behavior tests in `tests/test_game_repository.py` (matches
  where `count_games_by_platform` etc. are already tested) and one endpoint-level test class in
  `tests/test_users_router.py` (matches where all other `/users/me/profile` field tests live),
  rather than creating a new `tests/test_users.py` as literally named in the plan's
  `files_modified` list — this file doesn't exist in the project and the plan's own naming
  doesn't match the established convention split. See "Deviations from Plan" below.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking/convention] Tests placed in existing files, not a new `tests/test_users.py`**
- **Found during:** Task 1 (writing the RED tests)
- **Issue:** The plan's `files_modified` frontmatter lists `tests/test_users.py`, but no such
  file exists in the project. The established convention splits repository-level tests
  (`tests/test_game_repository.py`) from router/endpoint-level tests
  (`tests/test_users_router.py`) — creating a third, overlapping `test_users.py` would
  duplicate/fragment existing coverage for `/users/me/profile`.
- **Fix:** Added `TestGetCurrentRatingByPlatform` (6 tests) to `tests/test_game_repository.py`
  and `TestProfileCurrentRating` (2 tests) to `tests/test_users_router.py` instead. This is a
  stricter superset of the plan's `<acceptance_criteria>` (white-most-recent, black-most-recent,
  no-games→null are all covered, plus recency-ordering, multi-platform, and unrated-game edge
  cases the plan didn't explicitly list).
- **Files modified:** `tests/test_game_repository.py`, `tests/test_users_router.py` (in place
  of the plan's `tests/test_users.py`)
- **Verification:** `uv run pytest -n auto tests/test_game_repository.py tests/test_users_router.py -x` — 33 passed. Full suite `uv run pytest -n auto` — 3171 passed, 18 skipped.
- **Committed in:** `15826ac8` (RED), `8038a492` (GREEN)

---

**2. [Rule 3 - Blocking/correctness] Reverted premature MAIA-04 requirement-complete flip**
- **Found during:** State updates (after `requirements.mark-complete MAIA-04`)
- **Issue:** The plan's frontmatter declares `requirements: [MAIA-04]`, so the standard
  `requirements.mark-complete` step flipped `MAIA-04` to `[x]` Complete in REQUIREMENTS.md.
  But `MAIA-04` is ALSO listed in `151-04-PLAN.md` and `151-06-PLAN.md`'s frontmatter
  (`requirements: [MAIA-02, MAIA-03, MAIA-04, MAIA-05, MAIA-06, SURF-05]` and
  `requirements: [SURF-04, SURF-05, MAIA-04, MAIA-05, MAIA-06, LIC-02, VALID-01]`
  respectively) — neither of which has executed yet. MAIA-04's actual text requires "the full
  per-ELO probability curve... plus the position's Maia WDL value" — the ONNX-inference half of
  the requirement, not delivered by this plan at all.
- **Fix:** Manually reverted the checkbox (`[ ]` Pending) and traceability-table row in
  `REQUIREMENTS.md`, adding an inline note that Plan 03 only delivers the "rating at game time"
  data-source slice of MAIA-04; Plans 04/06 will actually close it.
- **Files modified:** `.planning/REQUIREMENTS.md`
- **Verification:** Manual read-back of the requirement text and both other plans' frontmatter
  `requirements:` fields confirms the shared-ID pattern.
- **Committed in:** final plan-metadata commit (see below)

---

**Total deviations:** 2 auto-fixed (1 test-file-location convention fix, 1 requirement-tracking
correction)
**Impact on plan:** No scope creep; the actual `current_rating` behavior and artifacts match
the plan exactly. The requirement-tracking correction prevents REQUIREMENTS.md from reporting
MAIA-04 as done before the ONNX inference half (Plans 04/06) actually ships.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- `current_rating` is live on `/users/me/profile` and typed on the frontend — Plan 06 (free-play
  ELO-selector default, D-07) can now read `useUserProfile().data?.current_rating` directly.
- No blockers for Wave 1 continuation or Wave 2+ (ONNX contract plans are independent of this one).

---
*Phase: 151-maia-in-the-browser-all-position-surfaces*
*Completed: 2026-07-05*

## Self-Check: PASSED

All created/modified files verified present on disk; all 3 task commits (`15826ac8`, `8038a492`, `e55fc13d`) verified present in git log.
