---
phase: 167-backend-store-on-finish
plan: 02
subsystem: api
tags: [sqlalchemy, fastapi, pydantic, library, analytics-filters]

requires:
  - phase: 167-backend-store-on-finish
    provides: "Plan 01 — Platform Literal extended with 'flawchess', bot_game_settings model + migration applied to dev DB"
provides:
  - "DEFAULT_EXCLUDED_PLATFORMS constant + platform-None else-branch in apply_game_filters, excluding flawchess from every default analytics population (STORE-07)"
  - "get_library_games opt-in seam that substitutes an explicit platform list including 'flawchess' when the caller passes platform=None (D-03)"
  - "_build_card rating-conversion guard preventing double-conversion of an already-lichess-equivalent flawchess rating (RESEARCH Pitfall 3)"
affects: [167-03-store-bot-game-service, 171-frontend-library-filter-chip]

tech-stack:
  added: []
  patterns:
    - "Single central filter predicate (apply_game_filters) for platform-based exclusion — never scatter per-router platform checks"
    - "Opt-in seam pattern: default-excluded population, explicit override at the one call site that needs it, not a new parameter threaded through the shared filter"

key-files:
  created:
    - tests/repositories/test_query_utils.py
  modified:
    - app/repositories/query_utils.py
    - app/services/library_service.py
    - tests/services/test_library_service.py

key-decisions:
  - "D-02 implemented exactly as locked: DEFAULT_EXCLUDED_PLATFORMS = (\"flawchess\",) module constant; apply_game_filters' platform-None branch now excludes it via Game.platform.notin_(...)."
  - "D-03 implemented via a local variable at the get_library_games call site (library_platform = platform if platform is not None else [...]), not a new apply_game_filters parameter — keeps the exclusion centralized while the opt-in stays scoped to the one surface that needs it."
  - "RESEARCH Pitfall 3 guard added defensively even though it was not yet exposed by any live flawchess data (no bot games exist in the dev DB yet) — the double-conversion bug would otherwise ship silently once Plan 03's store endpoint starts writing rows."

requirements-completed: [STORE-07, STORE-01]

coverage:
  - id: D1
    description: "apply_game_filters excludes platform='flawchess' from the default (platform=None) population, including when opponent_type='bot' is explicitly set"
    requirement: "STORE-07"
    verification:
      - kind: unit
        ref: "tests/repositories/test_query_utils.py::TestApplyGameFiltersFlawchessExclusion::test_bot_opponent_type_excludes_flawchess_but_keeps_imported_bot_game"
        status: pass
      - kind: unit
        ref: "tests/repositories/test_query_utils.py::TestApplyGameFiltersFlawchessExclusion::test_explicit_platform_list_including_flawchess_returns_it"
        status: pass
      - kind: unit
        ref: "tests/repositories/test_query_utils.py::TestApplyGameFiltersFlawchessExclusion::test_human_opponent_type_still_excludes_flawchess"
        status: pass
    human_judgment: false
  - id: D2
    description: "get_library_games includes flawchess games in the Library games list when platform is None (backend opt-in half of STORE-01)"
    requirement: "STORE-01"
    verification:
      - kind: integration
        ref: "tests/services/test_library_service.py::TestNoEngineAnalysis::test_flawchess_game_included_when_platform_is_none"
        status: pass
    human_judgment: false
  - id: D3
    description: "_build_card never double-converts a flawchess game's already-lichess-equivalent rating through normalize_to_lichess_blitz's Table-2 inversion for a non-blitz TC bucket"
    verification:
      - kind: integration
        ref: "tests/services/test_library_service.py::TestGetLibraryGame::test_flawchess_rapid_card_has_identity_normalized_rating"
        status: pass
    human_judgment: false

duration: ~25min
completed: 2026-07-11
status: complete
---

# Phase 167 Plan 02: Analytics Exclusion + Library Opt-In + Rating Guard Summary

**One central `apply_game_filters` predicate hides flawchess bot games from every analytics default, one opt-in seam in `get_library_games` keeps them visible on the Library Games tab, and a `_build_card` guard stops the newly-widened `Platform` Literal from silently double-converting bot-game ratings.**

## Performance

- **Duration:** ~25 min
- **Completed:** 2026-07-11
- **Tasks:** 2/2 completed
- **Files modified:** 4 (2 source, 2 test — 1 new test file, 1 existing test file extended)

## Accomplishments

- Added `DEFAULT_EXCLUDED_PLATFORMS = ("flawchess",)` to `app/repositories/query_utils.py` and an `else` branch in `apply_game_filters` so the default (`platform=None`) population always excludes flawchess — closing the gap where a user explicitly filtering `opponent_type='bot'` on Endgames/Insights/Stats/Openings would otherwise see FlawChess practice games mixed in with real imported bot opponents (RESEARCH Pitfall 1).
- Added an opt-in seam in `library_service.get_library_games`: when the caller's `platform` argument is `None`, it substitutes `["chess.com", "lichess", "flawchess"]` before calling `query_filtered_games`, so the Library Games tab's default view still surfaces flawchess games despite the new central exclusion. Documented inline that the router's `opponent_type` default (still `"human"`) independently gates bot-game visibility and is Phase 171's job (RESEARCH Pitfall 5).
- Fixed the RESEARCH Pitfall 3 landmine: `_build_card`'s two `normalize_to_lichess_blitz` call sites now special-case `game.platform == "flawchess"` and pass the raw rating straight through, since a stored flawchess rating is already lichess-blitz-equivalent (STORE-03's `anchor_rating`) — routing it through the lichess branch's Table-2 inversion for non-blitz buckets would have silently double-converted it.
- New `tests/repositories/test_query_utils.py` (4 tests) proves the D-02 predicate with the RESEARCH-flagged negative-test discipline: the exclusion test uses `opponent_type='bot'` explicitly (not the default `'human'` view, which would pass even without the fix).
- Extended `tests/services/test_library_service.py` with 2 tests: one proving `get_library_games` includes a flawchess game when `platform=None`, one proving rating identity (no double-conversion) for a rapid-bucket flawchess game via `get_library_game`/`_build_card`.

## Task Commits

1. **Task 1: Default-exclude flawchess in apply_game_filters** - `4d29121a` (feat)
2. **Task 2: Library opt-in + flawchess rating-conversion guard** - `8fc972f1` (feat)

**Plan metadata:** (this commit)

## Files Created/Modified

- `app/repositories/query_utils.py` - Added `DEFAULT_EXCLUDED_PLATFORMS` constant and the platform-None else-branch in `apply_game_filters` (D-02).
- `tests/repositories/test_query_utils.py` - New file; 4 tests covering the constant and the exclusion/opt-in/unchanged-human-view behaviors.
- `app/services/library_service.py` - `get_library_games` opt-in seam (`library_platform` local variable); `_build_card`'s two rating-conversion call sites guarded for `platform == "flawchess"`.
- `tests/services/test_library_service.py` - Added `test_flawchess_game_included_when_platform_is_none` (TestNoEngineAnalysis) and `test_flawchess_rapid_card_has_identity_normalized_rating` (TestGetLibraryGame).

## Decisions Made

- Kept the D-03 opt-in as a plain local variable at the single `get_library_games` call site rather than adding a new `apply_game_filters` parameter or a broader `include_flawchess` flag — matches the plan's "one central seam, one opt-in call site" requirement (D-02/D-03) and avoids threading a new parameter through every other caller of `apply_game_filters`.
- Left the Library router's `opponent_type` default untouched, per Pitfall 5 — that wiring (plus the frontend filter chip) is explicitly Phase 171's scope. Documented this limitation directly in `get_library_games`'s docstring so it isn't rediscovered as a surprise later.
- Used `opponent_type="all"` in the new `get_library_games` opt-in test (mirroring an existing test in the same class) so the test isolates the platform seam without needing to also change `is_computer_game` filtering behavior.

## Deviations from Plan

None — plan executed exactly as written. Both tasks matched their `<action>` and `<acceptance_criteria>` blocks with no scope changes; the Pitfall 3 guard, opt-in seam, and exclusion predicate all landed at the exact call sites the plan and PATTERNS.md identified.

## Issues Encountered

None. `uv run ruff format` reformatted one line in the newly-added `test_flawchess_game_included_when_platform_is_none` test (merged a wrapped signature onto one line) — re-verified with a full test rerun after formatting, no behavior change.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

Plan 03 (store service, PGN-only normalizer, `bots` router, `FLAWCHESS_BOT_USERNAME`) can now write `platform='flawchess'` games with confidence that:
- They will stay invisible on every existing analytics default (Endgames, Insights, Stats, Openings) even under an explicit `opponent_type='bot'` filter.
- They will surface correctly on the Library Games tab once Plan 03's rows exist (backend half of STORE-01 done; frontend/router `opponent_type` wiring remains Phase 171's job).
- Their stored (already lichess-blitz-equivalent) ratings will render correctly on Library cards for every TC bucket, not just blitz.

No blockers for Plan 03 or Phase 171.

---
*Phase: 167-backend-store-on-finish*
*Completed: 2026-07-11*

## Self-Check: PASSED

- FOUND: app/repositories/query_utils.py
- FOUND: tests/repositories/test_query_utils.py
- FOUND: app/services/library_service.py
- FOUND: tests/services/test_library_service.py
- FOUND: .planning/phases/167-backend-store-on-finish/167-02-SUMMARY.md
- FOUND commit: 4d29121a
- FOUND commit: 8fc972f1
