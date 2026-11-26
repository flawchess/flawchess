---
phase: 256-facepalm-refit-material-aggregated-over-depths
plan: 04
subsystem: scoring-fit
tags: [facepalm, fit, material-input, loss-gate, wr-03, d-05, per-candidate-rows]
requires: ["256-01", "256-02", "256-03"]
provides:
  - "CandidateSpec.material_input / loss_gate; the design matrix reads the loss and the missed gain through the twins' material_loss / material_missed"
  - "_spec_exclusion / spec_usable: per-candidate row filter (WR-03, D-05, D-12) built on the twins' own `loses` predicate"
  - "CandidateFit.rows (aligned with oof); stage tables show a rows column; D-13 tables and the hold-out use the chosen candidate's rows"
  - "Stage 2 compares loss_only and best_prob_for_misses at gate none and 1 (LOSS_GATE_CANDIDATES); --loss-gate and --material-input flags"
  - "FACEPALM_MATERIAL_INPUT and FACEPALM_LOSS_GATE in the constants block and --check-constants"
  - "tests/facepalm_models.PHASE_254_MODEL and the 2026-11-15 reproduction test"
affects: [256-05, 256-06, 256-07]
tech-stack:
  added: []
  patterns:
    - "base filter shared by every candidate + a per-spec filter that mirrors what the shipped twin reads"
    - "the fit calls the twins' own input functions (material_loss / material_missed / loses), so fitted == shipped"
key-files:
  created: []
  modified:
    - scripts/blunder_check/fit_facepalm.py
    - tests/scripts/test_fit_facepalm.py
    - tests/facepalm_models.py
key-decisions:
  - "EXCLUSION_REASONS stays the full set but split into BASE_EXCLUSION_REASONS (counted by split_usable) and SPEC_EXCLUSION_REASONS (counted per candidate by spec_usable), so the base Data lines never print a misleading 'NULL reply_spread: 0'"
  - "The legacy (Phase 250) fit keeps its NULL-spread exclusion through split_usable_legacy: Form A / B read the spread on every row"
  - "--material-input auto fits depth_3 only until plan 05 (DEFAULT_MATERIAL_INPUT); a value forces the input and the stage-1 forced_by text says so"
requirements-completed: [D-05, D-06, D-11, D-12, D-14]
duration: ~15 min (about 2.5 min of it the full suite)
completed: 2026-11-16
status: complete
coverage:
  - id: D1
    description: "The fit fits any material input and either loss gate; the constants block prints FACEPALM_MATERIAL_INPUT / FACEPALM_LOSS_GATE and --check-constants compares both exactly"
    requirement: "D-06"
    verification:
      - kind: unit
        ref: "tests/scripts/test_fit_facepalm.py#test_forced_decaying_mean_round_trips_through_check_constants"
        status: pass
      - kind: unit
        ref: "tests/scripts/test_fit_facepalm.py#test_design_matrix_is_the_shipped_twin"
        status: pass
      - kind: unit
        ref: "tests/scripts/test_fit_facepalm.py#test_check_constants_reports_every_field_that_moved"
        status: pass
    human_judgment: false
  - id: D2
    description: "The depth-3 refit of the 2026-11-15 features table still reproduces the shipped Phase 254 constants (refactor pin, PHASE_254_MODEL)"
    requirement: "D-14"
    verification:
      - kind: unit
        ref: "tests/scripts/test_fit_facepalm.py#test_depth_3_fit_reproduces_the_2026_11_15_constants"
        status: pass
    human_judgment: false
  - id: D3
    description: "254 WR-03 fixed in the fit: a NULL reply spread row stays in the fit for a gated form that does not read it; proven by a revert run"
    requirement: "D-12"
    verification:
      - kind: unit
        ref: "tests/scripts/test_fit_facepalm.py#test_spec_exclusion_keeps_null_spread_pure_miss_under_gated_form"
        status: pass
      - kind: unit
        ref: "tests/scripts/test_fit_facepalm.py#test_spec_exclusion_uses_the_loss_gate_on_a_fractional_mean"
        status: pass
    human_judgment: false
  - id: D4
    description: "D-05: a no-loss row with a NULL best_prob is excluded from a best_prob_for_misses candidate's fit and counted in the report"
    requirement: "D-05"
    verification:
      - kind: unit
        ref: "tests/scripts/test_fit_facepalm.py#test_spec_exclusion_drops_pure_miss_without_best_prob"
        status: pass
      - kind: unit
        ref: "tests/scripts/test_fit_facepalm.py#test_exclusion_counts_per_spread_form_in_data_section"
        status: pass
    human_judgment: false
  - id: D5
    description: "Stage 2 compares the loss gates (none first so a tie keeps no gate) and --loss-gate forces one; every candidate carries its own rows and the D-13 tables use them"
    requirement: "D-11"
    verification:
      - kind: unit
        ref: "tests/scripts/test_fit_facepalm.py#test_stage_two_lists_gate_candidates"
        status: pass
      - kind: unit
        ref: "tests/scripts/test_fit_facepalm.py#test_loss_gate_flag_forces_one_gate"
        status: pass
      - kind: unit
        ref: "tests/scripts/test_fit_facepalm.py#test_d13_tables_align_with_the_chosen_rows_after_exclusion"
        status: pass
    human_judgment: false
actuals:
  tokens: 13100
  tasks: 2
  commits: 3
plan_head_before: 68f17f06b20ed8848ba6785c2d9a35009e990fba
plan_head_after: 8c795306b
---

# Phase 256 Plan 04: Fit any material input and loss gate, WR-03 and D-05 per-candidate rows Summary

The fit script now fits any of the three material inputs and either loss gate through the shipped twins' own input functions, fits each candidate on exactly the rows its twin would score (254 WR-03 and D-05 fixed), and still reproduces the 2026-11-15 constants from the committed table.

## Accomplishments

- **Input- and gate-aware candidates (D-06, D-11).** `CandidateSpec` gains `material_input` and `loss_gate` (last fields, so positional constructions stay valid; `always` with a gate raises). `spec_row_values` reads the loss and missed gain through `material_loss` / `material_missed` for the spec's input and the gate through `loses`, the predicate the twins use. `model_from_spec`, `spec_label` (starts with the input, shows the gate on gated forms), `MODEL_CONSTANT_NAMES`, `model_constants_block` and `_EXACT_FIELDS` carry `FACEPALM_MATERIAL_INPUT` and `FACEPALM_LOSS_GATE`.
- **Refactor pin.** `PHASE_254_MODEL` is frozen in `tests/facepalm_models.py`; `--material-input depth_3 --check-constants` on `facepalm-features-2026-11-15.tsv` exits 0, also after the per-candidate row change (that table has 0 NULL spread and 0 NULL best prob).
- **WR-03 (D-12).** The base filter no longer drops NULL `reply_spread` rows; `_spec_exclusion` decides per candidate (NULL spread excludes only where the form reads it: `always`, or a losing row under a gated form). `spec_row_values` reads the spread only behind the `gated_off` guard.
- **D-05.** Under `best_prob_for_misses` a row that does not lose material and has a NULL `best_prob` is excluded from that candidate's fit (REASON_NO_BEST_PROB), matching the WR-01 twin behaviour from plan 03. Additive or unused best probability still reads NULL as 0.
- **Per-candidate rows.** `CandidateFit.rows` (aligned with `oof`); `fit_candidate` filters with `spec_usable`; stage tables get a `rows` column (research Pitfall 1); `_d13_sections` and the set-6 hold-out use the chosen candidate's rows.
- **Data section.** Per spread form and gate: rows fitted and rows excluded per reason, plus the number of rows that qualify only under a gated form (D-12).
- **Stage 2 (D-11, D-14).** `always` incumbent, then `loss_only` and `best_prob_for_misses` each at gate none and gate 1, none first so a full tie keeps no gate. Stage 1 and stage 3 run on the candidate's input. `--material-input` (auto fits depth 3 until plan 05) and `--loss-gate` (auto / none / 1) are reported through the stages' `forced_by` text and rejected on a legacy table. The chosen-model section states the input and the gate in words.
- **Synthetic writer.** All nine slots of both lines are filled from a separate generator (`FACTS_SEED + 1`), so the depth-3 columns and every existing label are unchanged; a NULL depth-3 value leaves the whole line empty.

## Task Commits

1. Task 1 (tracer): `840ce77bb` feat(256-04): fit any material input; constants block and --check-constants carry input and gate
2. Task 2 RED: `36341beb3` test(256-04): failing tests for per-candidate rows, WR-03 and the stage-2 loss gate
3. Task 2 GREEN: `8c795306b` feat(256-04): per-candidate rows, WR-03 / D-05 exclusion and the stage-2 loss gate

Tracer gate: end-of-phase mode and an automated-only `<verify>`: the tracer verify (`-k "2026_11_15 or round_trips or design_matrix_is_the_shipped_twin"`, 13 passed, then the whole file, 49 passed) was green before Task 2 started; no checkpoint.

## TDD evidence (Task 2)

- RED: `test_spec_exclusion_keeps_null_spread_pure_miss_under_gated_form` fails on `assert [] == [FitRow(...)]` (the base filter still drops a NULL-spread row). `gsd-tools check tdd-red-evidence` on the pytest JUnit report returned `RED_EVIDENCE_OK` (`target_test_failed`). Semantic assessment: the target ran and failed on the planned assertion, not on an import or fixture fault. Of the 9 tests failing in the RED run, 8 fail on assertions about the planned behaviour; `test_loss_gate_flag_forces_one_gate` fails with `SystemExit: 2` (argparse rejects the not-yet-existing `--loss-gate`) and `test_d13_tables_align...` with an `AttributeError` before the `rows` field was filled. The RED commit contains stubs (`_spec_exclusion` returning None, `spec_usable` returning every row, `REASON_NO_BEST_PROB`, `LOSS_GATE_CANDIDATES`, `LossGateMode`, an unused `gate_mode` parameter, `CandidateFit.rows` defaulting to `()`) because a test cannot name a symbol that does not exist.
- GREEN: `8c795306b`, 56 passed in the file. No REFACTOR commit.

## Gap-closure proof (WR-03 and D-05 revert runs)

With the spread read moved back above the `gated_off` guard (`_require(row.reply_spread)` before the gate), `uv run pytest tests/scripts/test_fit_facepalm.py -k exclusion` gave 2 failed, 4 passed:

- `test_spec_exclusion_keeps_null_spread_pure_miss_under_gated_form`
- `test_d13_tables_align_with_the_chosen_rows_after_exclusion` (the gated candidates cannot be fitted: "design matrix needs usable rows only")

With the D-05 branch of `_spec_exclusion` disabled (`... and row.best_prob is None and False`) the run gave 1 failed, 5 passed: `test_spec_exclusion_drops_pure_miss_without_best_prob`. Both mutations were restored with `git checkout -- scripts/blunder_check/fit_facepalm.py`; with the fix, 6 passed (`-k exclusion`) and 56 passed for the whole file.

## Verification

- `uv run pytest tests/scripts/test_fit_facepalm.py tests/scripts/test_decaying_mean.py`: 246 passed
- `uv run pytest -n auto` (full backend suite): 6944 passed, 19 skipped, 146 s; no intermittent failure seen
- `uv run ruff check .`: clean; `uv run ruff format --check app/ tests/ scripts/ analysis/`: 620 files already formatted
- `uv run ty check app/ tests/ scripts/`: All checks passed
- `uv run python scripts/check_function_size.py app/ --fail-over-depth 4`: OK, no breaches
- `fit_facepalm.py --features reports/blunder-check/facepalm-features-2026-11-13.tsv --out temp/blunder-check/fit-check-256-04-legacy.md`: exit 0 (legacy schema still fits)
- `fit_facepalm.py --features reports/blunder-check/facepalm-features-2026-11-15.tsv --check-constants`: "constants match"
- Acceptance criteria re-checked: `PHASE_254_MODEL` has `best_prob_coef=1.0405`; `MODEL_CONSTANT_NAMES` holds both new names; `material_loss(` is called in `_spec_loss`, which `spec_row_values` and `_spec_exclusion` use; `--help` lists `--material-input` and `--loss-gate`; `def _spec_exclusion(`, `REASON_NO_BEST_PROB`, `LOSS_GATE_CANDIDATES: tuple[float | None, ...] = (None, 1.0)` and `CandidateFit.rows` exist.

## Deviations from Plan

**1. [Rule 1 - Bug] Legacy fit lost its NULL-spread exclusion**
- **Found during:** Task 2 (removing the spread check from the base filter)
- **Issue:** The legacy (Phase 250) Form A / Form B design matrix reads the reply spread on every row. With the spread check gone from `_exclusion_reason`, a NULL spread would have raised `FitError` in the legacy path.
- **Fix:** `split_usable_legacy` (base filter plus the NULL-spread exclusion, counted under `REASON_NO_SPREAD`) is used by `run_fit` only. The facts-schema path uses `split_usable` and per-candidate `spec_usable`.
- **Files modified:** scripts/blunder_check/fit_facepalm.py
- **Commit:** `8c795306b`

**2. [Documented adjustment] `EXCLUSION_REASONS` split in two**
- The plan says to add `REASON_NO_BEST_PROB` to `EXCLUSION_REASONS`. It is there, but `split_usable` counts only `BASE_EXCLUSION_REASONS`; `REASON_NO_SPREAD` and `REASON_NO_BEST_PROB` are per-candidate (`SPEC_EXCLUSION_REASONS`, counted by `spec_usable`). Otherwise the base Data lines would print two reasons as 0 that the base filter can never produce.

**3. [Documented adjustment] Stage-table header and test assertion**
- The `rows` column sits right after the candidate name (`| candidate | rows | free coefs | ...`); the report tests assert `"| candidate | rows |"` because `"| rows |"` also matches the D-13 tables and would pass trivially.

**Total deviations:** 3 (1 Rule 1, 2 documented adjustments). **Impact:** none on the plan's behaviour; all inside the declared files.

## Notes for the owner and later plans

- Until plan 05, `--material-input auto` fits `depth_3` only (`DEFAULT_MATERIAL_INPUT`); the three-input comparison, `choose_material_input`, and the set-8 hold-out per input (research Pitfall 2) are plan 05 / 06. The hold-out here is still "fit the chosen spec on `TRAIN_SETS`, score set 6", now on the chosen candidate's rows.
- Under `depth_3` the two gates give identical fits on integer losses (visible in the 2026-11-15 stage 2 table: gate none and gate 1 rows are identical), so the tie keeps no gate and the reproduction holds.
- `--check-constants` after a forced run needs the same flags (`--material-input`, `--loss-gate`, `--spread-form`) as the run that produced the constants; `test_forced_decaying_mean_round_trips_through_check_constants` pins that.

## Known Stubs

None. (The RED stubs `_spec_exclusion`, `spec_usable`, the unused `gate_mode` and `CandidateFit.rows = ()` were replaced in `8c795306b`.)

## Threat Flags

None. No new endpoints, auth paths, or schema changes; the fit still reads committed files only (T-256-08: `load_features` is unchanged and still requires all nine slots on a facts table).

## Self-Check: PASSED

- `scripts/blunder_check/fit_facepalm.py`, `tests/scripts/test_fit_facepalm.py`, `tests/facepalm_models.py`: present and committed
- commits `840ce77bb`, `36341beb3`, `8c795306b`: ancestors of HEAD
- working tree clean before this SUMMARY
