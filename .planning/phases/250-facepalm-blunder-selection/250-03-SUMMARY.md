---
phase: 250-facepalm-blunder-selection
plan: 03
subsystem: api
tags: [blunder-check, facepalm, sqlalchemy, selection, no-repeat]

requires:
  - phase: 250-facepalm-blunder-selection
    provides: "game_flaws.facepalm_score column and FACEPALM_SCORE_MIN (plan 01)"
provides:
  - "BlunderFlawRow.facepalm_score / FlawLike.facepalm_score; load_blunder_flaws filters facepalm_score >= FACEPALM_SCORE_MIN in SQL and the pure judge re-checks it"
  - "ServedSets.served_blunder_plies read from blunder_check_windows.blunder_ply (permanent no-repeat, D-17)"
  - "require_facepalm keyword on pick_own_game_ids / pick_foreign_game_ids via _unserved_qualifying_blunder_exists"
  - "SeedBlunder.facepalm_score and SEED_FACEPALM_SCORE test seed constant"
affects: [250-04, 250-05, 250-06, 250-08, blunder-check window mix]

actuals:
  tokens: 11328
  tasks: 2
  commits: 2
plan_head_before: bd283f13bb77ad4097dd40a4d094e583e85d0d76
plan_head_after: bc79e93e872c8ae705455eb00fb6e76204a36c0f

tech-stack:
  added: []
  patterns:
    - "Two-level EXISTS/NOT EXISTS probes use correlate_except(<inner table>) so the outer games table or TABLESAMPLE alias is not pulled into the inner FROM as a cross join"
    - "Candidate quality gate lives twice on purpose: plain SQL filter in the loader, same predicate re-checked in the pure judge"

key-files:
  created: []
  modified:
    - app/repositories/blunder_check_repository.py
    - app/services/blunder_check_candidates.py
    - app/services/blunder_check_selection.py
    - tests/blunder_check_seed.py
    - tests/services/test_blunder_check_candidates.py
    - tests/repositories/test_blunder_check_repository.py
    - tests/services/test_blunder_check_selection.py
    - tests/routers/test_blunder_check_drill.py

key-decisions:
  - "served_for_games derives served_blunder_plies and judged_ranges from the single existing windows query instead of a second select; one round trip fewer, same ix_blunder_check_windows_user_game access path"
  - "The 249 D-06 thresholds and findability helpers stay in blunder_check_rules.py (the calibration report still imports them); only candidates.py stopped importing them"

patterns-established:
  - "require_facepalm picks: EXISTS game_flaws row at or above FACEPALM_SCORE_MIN AND NOT EXISTS a window of the caller whose blunder_ply equals that flaw ply"

requirements-completed: [D-01, D-09, D-17]

coverage:
  - id: D1
    description: "Only blunders with facepalm_score >= FACEPALM_SCORE_MIN reach the drill: SQL filter in load_blunder_flaws, re-check in the pure judge, identical for allowed, pure-miss and mixed blunders, NULL never qualifies"
    requirement: "D-01, D-09"
    verification:
      - kind: unit
        ref: "tests/repositories/test_blunder_check_repository.py#test_facepalm_loader_and_judge_keep_only_qualifying"
        status: pass
      - kind: unit
        ref: "tests/services/test_blunder_check_candidates.py#TestFacepalmPredicate"
        status: pass
      - kind: unit
        ref: "tests/services/test_blunder_check_selection.py#test_facepalm_only_qualifying_blunders_are_composed"
        status: pass
    human_judgment: false
  - id: D2
    description: "A blunder served in any window is never composed again, including a window that ended on a false alarm before the blunder"
    requirement: "D-17"
    verification:
      - kind: unit
        ref: "tests/repositories/test_blunder_check_repository.py#test_served_blunder_counts_once_its_window_was_served"
        status: pass
      - kind: unit
        ref: "tests/services/test_blunder_check_selection.py#test_repeat_false_alarm_before_blunder_is_never_served_again"
        status: pass
      - kind: unit
        ref: "tests/routers/test_blunder_check_drill.py#test_false_alarm_keeps_safe_points_and_the_blunder_is_never_served_again"
        status: pass
    human_judgment: false
  - id: D3
    description: "pick_own_game_ids / pick_foreign_game_ids with require_facepalm keep only games holding a qualifying blunder the caller has not been served; windows served to another user do not hide a game"
    requirement: "D-09"
    verification:
      - kind: unit
        ref: "tests/repositories/test_blunder_check_repository.py#test_pick_own_require_facepalm_skips_games_without_unserved_qualifying_blunder"
        status: pass
      - kind: unit
        ref: "tests/repositories/test_blunder_check_repository.py#test_pick_foreign_require_facepalm_skips_games_without_unserved_qualifying_blunder"
        status: pass
    human_judgment: false

duration: 25 min
completed: 2026-11-13
status: complete
---

# Phase 250 Plan 03: Facepalm Gate in Selection and Permanent No-Repeat Summary

**Blunder-check candidates now qualify on the stored `facepalm_score >= FACEPALM_SCORE_MIN` (SQL filter plus pure re-check, no per-case special handling), a served blunder is never composed again even after a false alarm, and the game picks can ask for games holding an unserved qualifying blunder.**

## Performance

- **Duration:** 25 min
- **Completed:** 2026-11-13
- **Tasks:** 2 (1 tracer, 1 auto/tdd)
- **Files modified:** 8 (3 app, 5 tests)

## Accomplishments

- Tracer: `BlunderFlawRow` and the `FlawLike` protocol swap the four Maia pair fields for `facepalm_score`; `load_blunder_flaws` filters on the threshold in SQL and `_blunder_candidate` re-checks it after the miss-case "unclassified" drop. The D-06 findability block and its imports are gone from `blunder_check_candidates.py`.
- `served_for_games` now reads `blunder_check_windows.blunder_ply`, so `ServedSets.served_blunder_plies` covers every window ever served to the caller; the 249 false-alarm exception is removed.
- `require_facepalm` on both picks via `_unserved_qualifying_blunder_exists` (EXISTS on `game_flaws`, NOT EXISTS on the caller's windows); `require_facepalm=False` keeps today's behaviour.
- Tests: TestFindability replaced by TestFacepalmPredicate (7 cases, boundary at exactly `FACEPALM_SCORE_MIN` and minus 1e-6, same outcome for allowed / pure-miss / mixed); loader+judge tracer; compose-level facepalm test over all `_SEEDS`; own and foreign pick tests (foreign includes a second user's window to prove user scoping); the three false-alarm tests inverted.

## Task Commits

1. **Task 1: tracer, facepalm gate in loader and judge** - `77ee2068e` (feat)
2. **Task 2: permanent no-repeat and qualifying-blunder picks** - `bc79e93e8` (feat)

## Verification

- `uv run pytest` over candidates, rules, selection, repository, drill, sessions and `tests/scripts` (`-n auto`): 878 passed, 3 skipped.
- `uv run ty check app/ tests/ scripts/`: all checks passed. `uv run ruff check` / format clean. `check_function_size.py app/ --fail-over-depth 4`: no breaches.
- Acceptance greps: `maia_refutation_|maia_best_` count is 0 in the repository, candidates and seed module; `prompted_blunder_plies|.prompted|prompted_stmt` prints nothing under `app tests`; `require_facepalm` appears 6 times in the repository; the old `leaves_it_eligible` test name is gone.
- **Mutation check (D-17):** temporarily restoring the answer-joined served query made exactly three tests fail (`test_served_blunder_counts_once_its_window_was_served`, `test_repeat_false_alarm_before_blunder_is_never_served_again`, `test_false_alarm_keeps_safe_points_and_the_blunder_is_never_served_again`); reverted, all pass again.

## Decisions Made

- Folded the served-blunder query into the existing windows query rather than adding a second select (the plan described one select of `game_id, blunder_ply`; the windows query already returns `blunder_ply` for the same rows and filter, so a separate select would only add a round trip).
- Left `REFUTATION_PROB_MIN`, `BEST_PROB_MIN`, `FindabilityInputs` and `findable` in `blunder_check_rules.py`; the calibration scripts and `tests/scripts/test_blunder_check_metrics.py` still use them (removal is plan 08).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Two-level EXISTS cross-joined the games table**
- **Found during:** Task 2 (pick test returned no games)
- **Issue:** the NOT EXISTS subquery inside the flaw EXISTS auto-correlates only one level, so `games` (or the TABLESAMPLE alias) was added to its FROM list as a cross join and the predicate became false.
- **Fix:** `.correlate_except(BlunderCheckWindow)` on the inner exists, with a comment at the fix site.
- **Files modified:** app/repositories/blunder_check_repository.py
- **Commit:** bc79e93e8

**2. [Rule 3 - Blocking] ty rejected an `InstrumentedAttribute` for a `ColumnElement` parameter**
- **Fix:** typed the helper parameter as `SQLColumnExpression[int]`.
- **Commit:** bc79e93e8

**Total deviations:** 2 auto-fixed (1 bug, 1 type blocker). **Impact:** none on scope.

## Known Stubs

None.

## Threat Flags

None. Every new query filters `BlunderCheckWindow.user_id` by the caller's id (T-250-08, covered by the foreign pick and served-set isolation assertions); only game ids leave the repository (T-250-09); the predicate is a SQLAlchemy expression over a module constant (T-250-10).

## Issues Encountered

`tests/repositories` failures of the form `MissingGreenlet` in teardown logs appear when an assertion fails inside a test; they are teardown noise, not a separate bug.

## Next Phase Readiness

Plan 06 can use `require_facepalm=True` for blunder slots; the API schema and frontend are untouched.

## Self-Check: PASSED

- Modified files all present; commits `77ee2068e` and `bc79e93e8` are ancestors of HEAD.

---
*Phase: 250-facepalm-blunder-selection*
*Completed: 2026-11-13*
