---
phase: 249-blunder-check-playable-mvp
plan: 01
subsystem: blunder-check
tags: [blunder-check, selection-rules, hazard-model, pure-core, tdd]
status: complete
requires:
  - phase: 248-blunder-check-calibration
    provides: selection math in scripts/blunder_check/metrics.py and spot_check.py
provides:
  - app/services/blunder_check_rules.py (single implementation of the selection rules + scoring/session constants)
  - app/services/blunder_check_candidates.py (judge_game, assign_windows, points_possible, lead_in_start)
affects: [249-02, 249-03, blunder-check session builder, blunder-check calibration report]
tech-stack:
  added: []
  patterns:
    - "App owns the selection math; scripts re-export it through an explicit __all__"
    - "Draw shapes first, pick candidates to fit the drawn position (never derive position from a blunder)"
key-files:
  created:
    - app/services/blunder_check_rules.py
    - app/services/blunder_check_candidates.py
    - tests/services/test_blunder_check_rules.py
    - tests/services/test_blunder_check_candidates.py
  modified:
    - scripts/blunder_check/metrics.py
    - scripts/blunder_check/spot_check.py
key-decisions:
  - "MAX_MISS_SHARE and capped_blunder_supply stay in scripts/ only (D-07: no miss cap in app code)"
  - "FlawLike is a read-only Protocol so plan 02's repository row satisfies it without an import from repositories"
  - "assign_windows picks uniformly over eligible (game, candidate) options sorted by (game_id, first ply, blunder ply) for seed reproducibility"
metrics:
  duration: ~35 min
  completed: 2026-11-10
actuals:
  tokens: 18000
  tasks: 2
  commits: 3
plan_head_before: 205eeb98cb6994fb4b743645f00b7a999aaeed74
plan_head_after: dbddeb3f2ede9c2d5d58a1e52765d4de9b88272b
---

# Phase 249 Plan 01: Selection rules in the app and the pure composition core Summary

The Phase 248 selection math now lives once in `app/services/blunder_check_rules.py`, the calibration report re-exports it, and `app/services/blunder_check_candidates.py` judges games into blunder candidates and herring runs and fills hazard-drawn slots (D-03..D-08, D-11, D-14).

## Tasks

### Task 1 (tracer): one implementation of the selection rules
Commit `bee5e8aa6`.
- Moved `HAZARD`, `WINDOW_LENGTHS`, `LEAD_IN_PLIES`, `MAX_BLUNDER_POSITION`, `MissCase`, `MoveJudgement`, `HazardWeights`, `FindabilityInputs`, `user_move_judgements`, `blunder_es`, `miss_case`, `in_band`, `blunder_fits_position`, `hazard_position_weights`, `_pair_passes`, `findable`, `herring_flags`, `count_herring_windows` from `scripts/blunder_check/metrics.py`, and `WindowShape` + `draw_window_shape` from `spot_check.py`, verbatim into the app module.
- Added `max_fit_position` (monotone scan, stops at first failing k) and the named constants `REFUTATION_PROB_MIN=0.3`, `BEST_PROB_MIN=0.2`, `ES_BAND_LOW=0.10`, `ES_BAND_HIGH=0.90`, `BLUNDER_CHECK_SESSION_WINDOWS=6`, `SAFE_POINTS=1`, `BLUNDER_POINTS=3`, `BETTER_MOVE_POINTS=MOVE_TIER_POINTS["good"]`.
- `metrics.py` imports and re-exports through an explicit `__all__`; `spot_check.py` imports `WindowShape`/`draw_window_shape` from the app. `git diff --stat -- tests/scripts/` is empty: the 75 Phase 248 script tests pass unchanged.
- COVERAGE.md already held the required declaration line (written at planning time), so no change.

### Task 2 (tdd): judge a game, assign hazard-drawn slots
- RED `e76b551dc`: 44 tests plus a stub-behavior skeleton of the module (final data shapes, functions returning empty/zero) so imports resolve. 41 failed on assertions (`assert None is not None`, `0 == 7`, empty-pick unpacking); `gsd_run check tdd-red-evidence` on the JUnit report returned `RED_EVIDENCE_OK` (target test `test_assign_fills_the_rarest_slot_first`). The 3 tests that were green in RED are the hazard-draw tests, which exercise `draw_window_shape` already ported in Task 1; they pin D-03/D-11 for the app copy rather than driving new code. Semantic assessment: every failing test failed on the planned behavior, none on import/collection errors.
- GREEN `dbddeb3f2`: `judge_game` (contiguity check, one `_run_all_moves_pass`, `_blunder_candidate` with severity/parity/key-ply/prompted/recomputed-severity/findability/max-fit guards, `_herring_runs` sliding per length with served-range exclusion), `assign_windows` (rarest first, one window per game, seeded, unfillable slot absent), `points_possible`, `lead_in_start`, `judged_plies_for`.
- No REFACTOR commit needed.

## Verification

- `uv run pytest tests/services/test_blunder_check_candidates.py tests/services/test_blunder_check_rules.py tests/scripts/test_blunder_check_metrics.py tests/scripts/test_blunder_check_calibration.py`: all green (53 new + 75 Phase 248 tests).
- `uv run ty check app/ tests/ scripts/`: clean. `uv run ruff check` and `ruff format`: clean.
- `uv run python scripts/check_function_size.py app/ --fail-over-depth 4`: no breaches.
- Acceptance greps: moved function defs count 0 in metrics.py / 4 in rules; `draw_window_shape` def count 0 in spot_check.py; `MAX_MISS_SHARE` absent from `app/`; no `maia_played`/`is_capture`/`gives_check` in the new modules; 37 tests match the `-k` filter (>= 12).

## Deviations from Plan

None - plan executed as written. One judgement call: the RED commit carries a stub-behavior skeleton of `blunder_check_candidates.py` (not only tests) so tests fail on assertions rather than on import errors, which the TDD reference classifies as INVALID_RED.

## Interface notes for later plans

- `FlawLike` needs `ply`, `severity` (stored SMALLINT, blunder = 2), `is_miss`, and the four Maia prob/rank fields; `judge_game` is called with `key_plies`, `prompted_blunder_plies` and `served_ply_ranges` (inclusive ply bounds) supplied by the caller.
- `GameCandidates.herrings` has one key per `WINDOW_LENGTHS` entry; `WindowPick.judged_plies` are user-move plies (blunder last for blunder windows), `first_ply - 1` is the opponent reply preceding the first judged move (the opponent's blunder for a pure miss at position 1).
- Importing `GamePosition` standalone needs all models imported (mapper configuration); pytest conftest handles this, a bare script must import `app.models.user` first.

## Known Stubs

None.

## Threat Flags

None. T-249-01 mitigated: severity and ES come only from `_run_all_moves_pass`, and a stored blunder must be recomputed as "blunder" (tests `test_stored_blunder_not_recomputed_as_blunder_is_excluded`, `test_stored_mistake_is_not_a_blunder_candidate`).

## Self-Check: PASSED
