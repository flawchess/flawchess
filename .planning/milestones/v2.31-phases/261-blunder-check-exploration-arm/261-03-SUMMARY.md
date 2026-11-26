---
phase: 261-blunder-check-exploration-arm
plan: 03
subsystem: blunder-check
tags: [selection, exploration, facepalm, sampling, tdd]

requires:
  - phase: 261-blunder-check-exploration-arm
    provides: SlotArm, SlotPlan.arm, EXPLORATION_SHARE, arm_probability, _Filled.arm, the serve-time window record
provides:
  - draw_slot_arm and the per-blunder-slot coin flip in draw_slot_plan
  - min_score on the scored probe, the three game picks, judge_game, assign_windows (None = scored rows only)
  - BlunderCandidate.facepalm_score and the cut applied at option time
  - batch provenance (Probe), per-probe exclusion, arm-aware _fill_from_pool, _next_probe, arm-preserving plan rewrites
affects: [261-05 calibration script, 261-06 wire and feedback, 261-07 prod EXPLAIN and release]

actuals:
  tokens: 16000
  tasks: 3
  commits: 3
plan_head_before: 40a07df2960659f37732b7d0a3a68014c9cf150b
plan_head_after: 3a00c08db3b78f139b6ac36bc66117069c264bb7

tech-stack:
  added: []
  patterns:
    - "cut moved from the loader and the judge to option time (assign_windows min_score), so one judged pool serves both arms"
    - "batch provenance: an exploration slot never reads a batch loaded by the conditioned (cut) probe"
    - "dataclasses.replace at every plan rewrite so the arm cannot be silently reset"

key-files:
  created: []
  modified:
    - app/services/blunder_check_rules.py
    - app/repositories/blunder_check_repository.py
    - app/services/blunder_check_candidates.py
    - app/services/blunder_check_selection.py
    - tests/services/test_blunder_check_rules.py
    - tests/services/test_blunder_check_candidates.py
    - tests/services/test_blunder_check_selection.py
    - tests/repositories/test_blunder_check_repository.py

key-decisions:
  - "Plain probes pass min_score explicitly (the default cut) so the pick closures map Probe to (require_facepalm, min_score) in one helper, _probe_args"
  - "Exploration is an arm of the plan only: herring slots always carry the main arm and never flip a coin"
  - "A plain (herring) batch counts as unconditioned on score, so exploration may draw from plain and scored batches, never from cut batches"

patterns-established:
  - "_fill_from_pool is the single place a slot is filled; its exploration-first, main-only-cut split holds for every caller"

requirements-completed: [SEED-261121-t50, D-10, D-11]

coverage:
  - id: C1
    description: "An exploration slot serves a below-cut scored blunder with an EXPLORATION record; a main slot never does; an unscored blunder is served by neither arm"
    requirement: "SEED-261121-t50"
    verification:
      - kind: integration
        ref: "tests/services/test_blunder_check_selection.py#test_exploration_slot_serves_a_below_cut_blunder"
        status: pass
      - kind: integration
        ref: "tests/services/test_blunder_check_selection.py#test_main_slot_never_serves_a_below_cut_blunder"
        status: pass
      - kind: integration
        ref: "tests/services/test_blunder_check_selection.py#test_unscored_blunder_is_served_by_neither_arm"
        status: pass
    human_judgment: false
  - id: C2
    description: "No cut-batch or cut-pass exploration fill; plain scored frame on every path; the arm survives every plan rewrite"
    verification:
      - kind: unit
        ref: "tests/services/test_blunder_check_selection.py#test_exploration_never_draws_from_a_cut_batch"
        status: pass
      - kind: unit
        ref: "tests/services/test_blunder_check_selection.py#test_fill_from_pool_exploration_slot_skips_cut_batch"
        status: pass
      - kind: integration
        ref: "tests/services/test_blunder_check_selection.py#test_refill_from_own_keeps_exploration_off_cut_batches"
        status: pass
      - kind: unit
        ref: "tests/services/test_blunder_check_selection.py#test_pool_exclude_ids_keeps_cut_loaded_games_for_scored_probe"
        status: pass
      - kind: integration
        ref: "tests/services/test_blunder_check_selection.py#test_own_to_foreign_conversion_keeps_the_exploration_arm"
        status: pass
    human_judgment: false
  - id: C3
    description: "One coin flip per blunder slot at EXPLORATION_SHARE, own and foreign alike, never on herrings; the main cut stays 0.7"
    requirement: "SEED-261121-t50"
    verification:
      - kind: unit
        ref: "tests/services/test_blunder_check_rules.py#TestSlotShares.test_exploration_share_per_blunder_origin"
        status: pass
      - kind: unit
        ref: "tests/services/test_blunder_check_rules.py#TestSlotShares.test_named_constants"
        status: pass
    human_judgment: false
  - id: C4
    description: "The scored probe (own, foreign, nearest) keeps below-cut games and still excludes unscored, served, opponent-side and (own) cooled games; the loader returns every scored owner blunder with its five inputs"
    requirement: "D-10"
    verification:
      - kind: integration
        ref: "tests/repositories/test_blunder_check_repository.py#test_pick_own_scored_probe_keeps_below_cut_games"
        status: pass
      - kind: integration
        ref: "tests/repositories/test_blunder_check_repository.py#test_pick_foreign_scored_probe_keeps_below_cut_games"
        status: pass
      - kind: integration
        ref: "tests/repositories/test_blunder_check_repository.py#test_pick_nearest_foreign_scored_probe_keeps_below_cut_games"
        status: pass
      - kind: integration
        ref: "tests/repositories/test_blunder_check_repository.py#test_load_blunder_flaws_returns_every_scored_owner_blunder_with_inputs"
        status: pass
    human_judgment: false

duration: 45min
completed: 2026-11-22
status: complete
---

# Phase 261 Plan 03: Exploration draw Summary

**About one blunder slot in five now draws as exploration: a plain random pick over scored owner-side blunders with no facepalm cut, kept off every cut-probe batch and every cut pass, while the main arm keeps the 0.70 cut and the arm survives every plan rewrite.**

## Accomplishments

- Rules: `draw_slot_arm` and one coin flip per own and foreign blunder slot (after its shape); herring slots keep the main arm.
- Repository: `min_score: float | None = FACEPALM_SCORE_MIN` on `_unserved_qualifying_blunder_exists` and the three picks (None switches the predicate to `IS NOT NULL`, same covering index, no new index, D-10). `load_blunder_flaws` returns every scored owner-side blunder; the 0.70 cut is no longer applied there.
- Candidates: `BlunderCandidate.facepalm_score`; `min_score` on `_blunder_candidate`, `judge_game`, `_blunder_options`, `assign_windows`. The composer judges with `min_score=None` and the cut is applied per slot at option time. Ordering and `rng.choice` are unchanged (never by score).
- Selection: `Probe` (plain / cut / scored), `_Batch.probe`, `_Pool.candidates(for_exploration=)`, `_Pool.loaded_by` / `exclude_ids` (replaces `seen_ids`), `_empty_plans`, `_next_probe`, `_probe_args`. `_fill_from_pool` runs the exploration pass first (no cut, no cut batches), then the main pass over main-arm slots only with the cut, so an exploration slot left empty stays empty for a later scored round, a redraw, or the arm-preserving own-to-foreign conversion. `_redraw_and_refill`, `_refill_from_own` and `_convert_empty_own_to_foreign` use `dataclasses.replace`; no `SlotPlan(` call remains in the module.
- The scored probe excludes only ids a non-cut probe loaded, so cut-loaded games stay in the exploration frame on the foreign-to-own refill path; a cut-loaded game the scored probe re-returns is reloaded as a scored batch.

## Task Commits

1. Task 1 (tracer): `d6ba31e31` feat, repository, candidates and selection changes plus the tracer tests (note: the provenance, per-probe exclusion and arm-preserving rewrites were written in this commit together with the tracer because `_fill_from_pool` and `_next_probe` are one change)
2. Task 2: `08bad5519` test, deterministic detectors for provenance, exclusion and arm survival
3. Task 3: `3a00c08db` feat, coin flip, share test, scored-probe repository tests

## Mutation confirmation (Task 2)

- Making `_Pool.candidates` ignore `for_exploration`: `test_exploration_never_draws_from_a_cut_batch`, `test_fill_from_pool_exploration_slot_skips_cut_batch` and `test_refill_from_own_keeps_exploration_off_cut_batches` failed (3 failed, 38 passed); restored.
- Forcing `arm="main"` in the three `replace(...)` calls: the convert, redraw, refill-trap and own-to-foreign tests failed (4 failed); restored.
- Reverting `exclude_ids("scored")` to every loaded id: the exclusion unit test and the refill trap failed (2 failed); restored.

## Flake audit (Task 3, Pitfall 5)

Files composing sessions checked: `tests/services/test_blunder_check_selection.py`, `tests/services/test_train_settings_service.py`, `tests/routers/test_blunder_check_sessions.py`, `tests/routers/test_blunder_check_drill.py`, `tests/routers/test_train_two_mode_streak.py`, `tests/repositories/test_cross_mode_cooldown.py`, `tests/repositories/test_train_two_mode_streak.py`, `tests/routers/test_train.py`, `tests/test_imports_router.py`, `tests/scripts/test_blunder_check_calibration.py`. Every one either patches `draw_slot_plan` (default main arm) or seeds only 0.95-scored blunders (an exploration slot fills exactly like a main slot) or composes for a user without games; none seeds a below-cut or unscored blunder under the real draw. No `EXPLORATION_SHARE` pin was needed. Three repeated runs of selection + train-settings + sessions router were green (69 passed each), and the spot-check script tests pass with the extra RNG draw.

## Deviations from Plan

None - plan executed exactly as written. Task 1's own-pick test count was kept at exactly three by testing both arms inside `test_unscored_blunder_is_served_by_neither_arm`.

## Issues Encountered

None.

## Known Stubs

None.

## Threat Flags

None. The arm lives only on `SlotPlan`, `_Filled` and the window record; no schema or wire field was added (T-261-06). The no-cut probe has the same EXISTS shape on `ix_game_flaws_facepalm_inputs` (T-261-07); the prod EXPLAIN stays with plan 07.

## Verification

- `uv run pytest -n auto tests/services/ tests/repositories/ tests/routers/ -k "blunder_check or cooldown or two_mode or train_settings" -x`: 355 passed
- Task 3 regression set (repository, calibration script, train settings, sessions / drill / two-mode routers, cooldown): 192 passed
- `uv run ruff format`, `ruff check .`, `uv run ty check app/ tests/ scripts/`, `check_function_size.py app/ --fail-over-depth 4`: clean

## Self-Check: PASSED

- Modified files exist; commits `d6ba31e31`, `08bad5519`, `3a00c08db` are ancestors of HEAD.
