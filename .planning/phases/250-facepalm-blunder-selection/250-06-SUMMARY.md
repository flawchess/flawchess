---
phase: 250-facepalm-blunder-selection
plan: 06
subsystem: api
tags: [blunder-check, composition, window-mix, rating-band, selection]

requires:
  - phase: 250-facepalm-blunder-selection
    provides: "require_facepalm picks, served_blunder_plies, FACEPALM_SCORE_MIN gate (plan 03); shipped facepalm constants (plan 04)"
provides:
  - "D-12 slot plans: HERRING_SHARE / OWN_BLUNDER_SHARE / FOREIGN_BLUNDER_SHARE, SlotPlan, draw_slot_plan, draw_blunder_shape, draw_herring_shape, blunder_position_weights"
  - "D-16 HERRING_OWN_SHARE and D-13 FOREIGN_RATING_BAND (150)"
  - "compose_windows by origin: own slots filled first, unfilled own slots converted to foreign (D-15), foreign slots filled within the rating band"
  - "user_level_elo (D-14) replacing reference_elo, DEFAULT_USER_LEVEL_ELO 1500, USER_LEVEL_SCAN_GAMES 200"
  - "recent_rated_games restricted to rated human games via apply_game_filters"
affects: [250-08, 250-09, blunder-check window mix]

actuals:
  tokens: 13354
  tasks: 2
  commits: 2
plan_head_before: 17497f6ad196cab27c0041eb95b65985ebb9253a
plan_head_after: 3fc8ca463e98c6910a72641a3b04fdf919ef2b8f

tech-stack:
  added: []
  patterns:
    - "One generic per-origin fill helper (_fill_from_source) parameterised by a _Source (origin, rounds, Elo window, pick closure) instead of separate own and foreign copies"
    - "A require_facepalm pick that comes back empty marks blunder supply exhausted for that origin; later rounds serve only the herring slots with plain picks"

key-files:
  created: []
  modified:
    - app/services/blunder_check_rules.py
    - app/services/blunder_check_selection.py
    - app/repositories/blunder_check_repository.py
    - tests/services/test_blunder_check_rules.py
    - tests/services/test_blunder_check_selection.py
    - tests/repositories/test_blunder_check_repository.py
    - tests/routers/test_blunder_check_drill.py
    - tests/routers/test_blunder_check_sessions.py

key-decisions:
  - "Composition with the 249 hazard model: window length uniform over WINDOW_LENGTHS for both kinds, blunder position drawn from h(1-h)^(k-1) normalised over 1..L, so the anti-leak rule holds and the herring share equals the D-12 constant"
  - "Foreign level is read once per session start, only when foreign slots remain after the own fill and conversion"
  - "Own herring slots are still served from own games when no own game holds a qualifying blunder (exhausted-blunder flag), so the facepalm gate cannot strand own herrings"

requirements-completed: [D-12, D-13, D-14, D-15, D-16]

coverage:
  - id: D1
    description: "Each slot independently draws herring / own blunder / foreign blunder at one third each; herrings split own / foreign at HERRING_OWN_SHARE; length uniform for both kinds; blunder position follows the conditional hazard weights; sessions are not forced into a 1-1-1 mix"
    requirement: "D-12, D-16"
    verification:
      - kind: unit
        ref: "tests/services/test_blunder_check_rules.py#TestSlotShares"
        status: pass
      - kind: unit
        ref: "tests/services/test_blunder_check_rules.py#TestBlunderPositionWeights"
        status: pass
    human_judgment: false
  - id: D2
    description: "Windows come from the origin their plan names, with at most one window per game and is_own true exactly when the caller owns the game; own slots own supply cannot fill become foreign slots (blunders and herrings), including for a user with no analysed games"
    requirement: "D-12, D-15, D-16"
    verification:
      - kind: unit
        ref: "tests/services/test_blunder_check_selection.py#test_slot_origins_follow_the_drawn_plan"
        status: pass
      - kind: unit
        ref: "tests/services/test_blunder_check_selection.py#test_no_own_supply_gets_foreign_blunders_and_herrings"
        status: pass
      - kind: unit
        ref: "tests/services/test_blunder_check_selection.py#test_own_herrings_are_served_when_no_own_game_holds_a_blunder"
        status: pass
    human_judgment: false
  - id: D3
    description: "The user's level is the median pinned Elo of the newest games in their most-played time control over rated human games (default 1500), and foreign windows have a mover within FOREIGN_RATING_BAND of it, with strangers' out-of-band games and guests' games never composed"
    requirement: "D-13, D-14"
    verification:
      - kind: unit
        ref: "tests/services/test_blunder_check_selection.py#test_user_level_picks_the_most_played_bucket_not_the_most_recent"
        status: pass
      - kind: unit
        ref: "tests/services/test_blunder_check_selection.py#test_foreign_games_within_rating_band_only"
        status: pass
      - kind: unit
        ref: "tests/repositories/test_blunder_check_repository.py#test_recent_rated_games_keeps_rated_human_games_newest_first"
        status: pass
    human_judgment: false

duration: 9 min
completed: 2026-11-13
status: complete
---

# Phase 250 Plan 06: Window Mix and Foreign Level Summary

**Sessions now draw each slot as a herring, an own blunder or a foreign blunder at one third each (herrings split own / foreign like blunders), unfilled own slots fall back to foreign games within 150 pinned Elo of a level taken from the user's most-played rated human time control.**

## Performance

- **Duration:** 9 min
- **Completed:** 2026-11-13
- **Tasks:** 2 (1 tracer, 1 auto/tdd)
- **Files modified:** 8 (3 app, 5 tests)

## Accomplishments

- Tracer: `blunder_check_rules.py` gains the D-12/D-16/D-13 constants, `SlotPlan`, `blunder_position_weights`, `draw_herring_shape`, `draw_blunder_shape` and `draw_slot_plan`. `compose_windows` draws a plan per slot, fills own slots via one generic `_fill_from_source` (rounds bounded by MAX_OWN_BATCHES / new MAX_FOREIGN_BATCHES, `require_facepalm` while a blunder slot is empty), redraws empty shapes of the same kind over the loaded pool, converts still-empty own slots to foreign, then fills and redraws foreign slots. `FOREIGN_ELO_BANDS` and the own-first logic are gone.
- Task 2: `user_level_elo` replaces `reference_elo` (most-played bucket, ties to the newest row, correspondence and bucketless rows ignored for the bucket choice, fallbacks to all rows then to `DEFAULT_USER_LEVEL_ELO`). `recent_rated_games` composes `apply_game_filters(rated=True, opponent_type="human")`. The foreign band is exactly `FOREIGN_RATING_BAND` with no widening.
- Tests: share/length/position/independence over 30000 seeded draws, origin and fallback composer tests (with the is_own ownership invariant), user-level cases, a repository test seeding an unrated game, a computer game, and a second user, and a rating-band test with an out-of-band stranger and a guest.

## Task Commits

1. **Task 1: tracer, slot plans per D-12 filled by origin with own-to-foreign fallback** - `d47daf6fd` (feat)
2. **Task 2: D-14 user level and D-13 band in the composer** - `3fc8ca463` (feat)

## Verification

- `uv run pytest -n auto` over `tests/services tests/repositories tests/routers tests/scripts -k "blunder_check or facepalm"`: 345 passed, 4 skipped. Plan-level file set (rules, selection, repository, drill, sessions): all pass.
- `uv run ty check app/ tests/ scripts/`, `uv run ruff check .` and `ruff format`: clean. `check_function_size.py app/ --fail-over-depth 4`: no breaches.
- Acceptance greps: five constants present in rules.py; `FOREIGN_ELO_BANDS` absent from `app tests`; `draw_window_shape` count 0 in selection.py; `def reference_elo` 0 and `def user_level_elo` 1; `apply_game_filters` in the repository 3 (import, docstring, call); `-k "user_level or rating_band"` reports 7 passed.
- **Mutation checks:** removing the own-to-foreign conversion fails `test_no_own_supply_gets_foreign_blunders_and_herrings` and `test_foreign_games_within_rating_band_only`; relaxing `apply_game_filters` to `rated=None, opponent_type="all"` fails the repository test; dropping the foreign Elo window fails the rating-band test. All reverted.

## Decisions Made

- Blunder-window composition with the 249 hazard model (planner's choice recorded in the plan): length uniform for both kinds, position conditional on the hazard firing within that length.
- Added an exhausted-blunder flag in `_fill_from_source`: without it, a user whose games hold no unserved qualifying blunder (for example every blunder with a NULL `facepalm_score` from a short stored line, the by-design ship-as-fitted state) would lose own herrings to the foreign fallback because the first `require_facepalm` pick returns nothing and the loop would stop. One extra bounded round; covered by `test_own_herrings_are_served_when_no_own_game_holds_a_blunder`.
- `draw_window_shape` and `hazard_position_weights` are kept (calibration scripts and their tests still import them); plan 08 removes what is unused.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Sessions-router tests moved into the Task 1 commit**
- **Found during:** Task 1 verification
- **Issue:** the plan assigns the `tests/routers/test_blunder_check_sessions.py` forcing to Task 2, but with random slot plans four tests there (full six-window session, resume, concurrent start, open-after-start) failed at the Task 1 commit because own-only supply cannot fill foreign slots.
- **Fix:** forced own-blunder slot plans with the same monkeypatch pattern in Task 1 so every commit is green. `test_finish_then_open_is_null_and_start_composes_a_fresh_session` in the drill tests needed the same forcing (own herring shape), which the plan did not list.
- **Files modified:** tests/routers/test_blunder_check_sessions.py, tests/routers/test_blunder_check_drill.py
- **Commit:** d47daf6fd

**2. [Rule 2 - Missing critical functionality] Exhausted-blunder handling for own herrings**
- **Found during:** Task 1 design
- **Issue:** see Decisions Made; the plan's "stop when a pick returns no ids" would convert own herring slots to foreign whenever no own game holds a qualifying blunder.
- **Fix:** `blunders_exhausted` flag plus a covering test.
- **Commit:** d47daf6fd

**3. [Rule 1 - Test bug] Tie-break test compared against raw ratings**
- **Issue:** the count-tie test expected the raw median but rows are pinned (platform and bucket normalised).
- **Fix:** compare with the level of the single-bucket row set.
- **Commit:** 3fc8ca463

**Total deviations:** 3 auto-fixed (1 blocking, 1 missing functionality, 1 test bug). **Impact:** none on scope.

## Known Stubs

None.

## Threat Flags

None. `recent_rated_games` and every pick stay scoped by the caller's `user_id` from the auth dependency (T-250-17, covered by the repository test seeding a second user); `NewWindow.is_own` is asserted against game ownership (T-250-16); query count per start is bounded by MAX_OWN_BATCHES + MAX_FOREIGN_BATCHES plus one level query, redraws reuse loaded pools (T-250-18, plan 09 re-measures on prod).

## Issues Encountered

None. Note for plan 08/09: a user whose own games all carry a NULL `facepalm_score` gets only own herrings and foreign blunders until the D-18 refit, as intended.

## Next Phase Readiness

Plan 08 can remove the now unused `draw_window_shape` / `hazard_position_weights` once the calibration scripts stop importing them; no API schema or frontend change was needed.

## Self-Check: PASSED

- Modified files present; commits `d47daf6fd` and `3fc8ca463` are ancestors of HEAD.

---
*Phase: 250-facepalm-blunder-selection*
*Completed: 2026-11-13*
