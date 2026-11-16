---
phase: 256-facepalm-refit-material-aggregated-over-depths
plan: 05
subsystem: scoring-fit
tags: [facepalm, fit, material-input, input-choice, assumptions, d-13]
requires: ["256-01", "256-02", "256-03", "256-04"]
provides:
  - "MATERIAL_INPUTS = (decaying_mean, first_stable, depth_3), the tie-break order of D-09"
  - "InputOutcome / run_input_pipeline: the staged pipeline (stages 1-3) once per input"
  - "choose_material_input: CV AUC mean, then fair share at the cut, then the MATERIAL_INPUTS order"
  - "Report: '## Material input (D-06, D-07, D-09)' comparison table, '## Other input: <input>' stage tables, an Assumptions list (A1, A2, A4, per-depth loss floor, missed floor and cap) in the chosen-model section"
affects: [256-06, 256-07]
tech-stack:
  added: []
  patterns:
    - "one pipeline per input; the chosen input's final is the run's model (D-10)"
    - "tie-break by list order, not by free coefficients, at the input level (D-09)"
key-files:
  created: []
  modified:
    - scripts/blunder_check/fit_facepalm.py
    - tests/scripts/test_fit_facepalm.py
key-decisions:
  - "A forced --material-input runs one pipeline and its reason string names the flag ('forced by --material-input X, the only input fitted')"
  - "In auto mode an input whose pipeline cannot be fitted at all is listed under 'not fitted' instead of aborting the run; a forced input still raises FitError"
  - "Other inputs' stage tables sit between the hold-out section and 'Extra rows', so '## Constants' stays the last section"
requirements-completed: [D-06, D-07, D-09, D-10, D-13, D-14]
duration: ~45 min (about 2 min of it the full suite)
completed: 2026-11-16
status: complete
coverage:
  - id: D1
    description: "Auto mode runs the full staged pipeline once per input and the report compares the three finals in one table; a forced input runs one pipeline and names its flag"
    requirement: "D-06"
    verification:
      - kind: unit
        ref: "tests/scripts/test_fit_facepalm.py#test_material_input_auto_compares_three_inputs"
        status: pass
    human_judgment: false
  - id: D2
    description: "The input is chosen by seed-mean CV AUC, then the fair share, then the MATERIAL_INPUTS order (a decaying-mean vs depth-3 tie goes to the decaying mean)"
    requirement: "D-07"
    verification:
      - kind: unit
        ref: "tests/scripts/test_fit_facepalm.py#test_choose_material_input_rules"
        status: pass
    human_judgment: false
  - id: D3
    description: "The constants block is the chosen input's final fitted on every labelled set, and its FACEPALM_MATERIAL_INPUT equals the 'Chosen input' line"
    requirement: "D-10"
    verification:
      - kind: unit
        ref: "tests/scripts/test_fit_facepalm.py#test_constants_block_is_the_chosen_input_final"
        status: pass
    human_judgment: false
  - id: D4
    description: "The chosen-model section states A1, A2, A4, the per-depth loss floor and the chosen missed floor and cap, rendered from the shipped constants"
    requirement: "D-13"
    verification:
      - kind: unit
        ref: "tests/scripts/test_fit_facepalm.py#test_report_states_the_assumptions"
        status: pass
    human_judgment: false
  - id: D5
    description: "The refactor pins hold: the depth-3 fit still reproduces the 2026-11-15 constants and the legacy table the Phase 250 model"
    requirement: "D-14"
    verification:
      - kind: unit
        ref: "tests/scripts/test_fit_facepalm.py#test_depth_3_fit_reproduces_the_2026_11_15_constants"
        status: pass
      - kind: unit
        ref: "tests/scripts/test_fit_facepalm.py#test_check_constants_legacy_still_passes"
        status: pass
    human_judgment: false
actuals:
  tokens: 5400
  tasks: 2
  commits: 3
plan_head_before: 037dcb3813a8f608a14424c0328a1fe7df4a21ce
plan_head_after: 10f6c88ca0b700f2d6cb34c8aef39fcadfa824f4
---

# Phase 256 Plan 05: Three-input comparison and the D-13 assumptions Summary

One fit command now runs the staged pipeline once per material input (decaying mean, first stable, depth 3), picks the input by seed-mean CV AUC then fair share then the fixed preference order, ships that input's final as the constants block, and states the A1, A2 and A4 assumptions next to the chosen model.

## Accomplishments

- **Per-input pipeline (D-06, D-14).** `MATERIAL_INPUTS`, the frozen `InputOutcome` (input, stages 1-3, final) and `run_input_pipeline` re-run plan 04's material-form, spread-form and optional-input stages for each input. Nothing is assumed from the shipped shape. `run_input_pipeline` takes one extra optional keyword, `input_mode`, which only labels a forced input in the stage-1 text.
- **Input choice (D-07, D-09).** `choose_material_input` copies the first two steps of `choose_candidate` (AUC tolerance, then fair share tolerance) and breaks a remaining tie by list order, not by free coefficients. The reason string names the deciding rule (AUC, fair share, or the D-09 order).
- **Constants are the chosen final (D-10).** `FactsOutcome.stage1/2/3/chosen/model` are the chosen input's; the final is fitted on every usable row of every labelled set. `FactsOutcome` gains `inputs`, `input_reason` and `input_failures`.
- **Report.** After Data: "## Material input (D-06, D-07, D-09)" with one row per input (final candidate, rows, CV AUC mean and spread, fair share mean) and "Chosen input: X. Reason: ...". The chosen input's stage sections follow as before; the other inputs' stage tables come as "## Other input: X" (level-3 headings) before Extra rows, so Constants stays last. The report stays deterministic.
- **Assumptions (D-13).** The chosen-model section lists A1 (first stable), A2 (mate short-circuit within LINE_DEPTH), A4 (the gate uses "at least"), the per-depth loss floor and the chosen missed floor and cap. The numbers are rendered from `MATERIAL_DECAY_RATIO`, `LINE_DEPTH`, `MATE_LOSS` and `FACTS_LOSS_FLOOR`.
- **Real run (informational, plan 07 does the owner run).** On `reports/blunder-check/facepalm-features-2026-11-15.tsv` (199 usable rows, 7 sets): decaying_mean CV AUC mean 0.913, first_stable 0.877, depth_3 0.874, so the decaying mean wins on AUC (reason: higher cross-validated AUC). This is a pre-set-8 table, so it says nothing final.

## Task Commits

1. Task 1 (tracer): `5802faded` feat(256-05): run the staged pipeline once per material input and choose by CV (D-06, D-07, D-09)
2. Task 2 RED: `ac23137be` test(256-05): failing test for the chosen-model assumptions list (D-13)
3. Task 2 GREEN: `10f6c88ca` feat(256-05): state the D-13 assumptions in the chosen-model section

Tracer gate: end-of-phase mode and an automated-only `<verify>`: the two named tests, the whole test file (58 passed) and the real-table fit with `grep "^## Material input"` were re-run green before Task 2 started; no checkpoint.

## TDD evidence (Task 2)

- RED: `test_report_states_the_assumptions` fails on `assert 'Assumptions' in <chosen-model section>`. `gsd-tools check tdd-red-evidence` on the pytest JUnit report returned `RED_EVIDENCE_OK` (`target_test_failed`). Semantic assessment: the target ran and failed on the planned assertion, not on an import or fixture fault. The other two Task 2 tests already passed in the RED run: `test_constants_block_is_the_chosen_input_final` pins D-10 behaviour that Task 1 implemented (it is a characterization test, so it could not be RED), and `test_help_lists_the_documented_flags` now also lists `--loss-gate`, which plan 04 added.
- Mutation proof for the characterization test (T-256-24): changing `model=chosen.model` to `model=inputs[-1].chosen.model` in `run_facts_fit` made `test_constants_block_is_the_chosen_input_final` fail (`assert 'depth_3' == 'decaying_mean'`); restored, 60 passed.
- GREEN: `10f6c88ca`, 60 passed in the file. No REFACTOR commit.

## Verification

- `uv run pytest tests/scripts/test_fit_facepalm.py`: 60 passed
- `uv run pytest -n auto` (full backend suite): 6948 passed, 19 skipped, 126 s
- `uv run ruff check .`: clean; `uv run ruff format --check app/ tests/ scripts/ analysis/`: 620 files already formatted
- `uv run ty check app/ tests/ scripts/`: All checks passed
- `uv run python scripts/check_function_size.py app/ --fail-over-depth 4`: OK, no breaches
- `fit_facepalm.py --features reports/blunder-check/facepalm-features-2026-11-15.tsv --out temp/blunder-check/fit-auto-256-05.md`: exit 0; the report has "## Material input", one row each for decaying_mean, first_stable and depth_3, a "Chosen input:" line, and the Assumptions list with the A1, A2 and A4 lines
- `test_check_constants_legacy_still_passes` and `test_depth_3_fit_reproduces_the_2026_11_15_constants`: pass

## Deviations from Plan

**1. [Documented adjustment] Two existing tests forced to depth 3 / compared against another forced input**
- `test_exclusion_counts_per_spread_form_in_data_section` blanks the spreads of rows that are pure misses at depth 3, so its counts are only meaningful on that input; it now passes `--material-input depth_3` (the plan names this approach for tests that read depth 3).
- `test_forced_decaying_mean_round_trips_through_check_constants` compared the decaying-mean model with an unforced run, which fitted depth 3 before this plan. The unforced run now picks the decaying mean on that table (so it matches), so the "does not reproduce" leg uses `--material-input depth_3` instead.
- Files: tests/scripts/test_fit_facepalm.py. Commit `5802faded`.

**2. [Documented adjustment] Extra optional keyword and `input_failures`**
- `run_input_pipeline` has an optional `input_mode` keyword beyond the plan's signature (needed so stage 1 can label a forced input), and `FactsOutcome` has `input_failures` besides the planned `inputs` and `input_reason`: in auto mode an input whose pipeline cannot be fitted at all is reported under "not fitted" instead of aborting the run.

**3. [Documented adjustment] Report order**
- The plan lists "Other input" blocks after the hold-out section; they sit there, with Extra rows and Constants still after them, so the constants block stays the last section (tests and tooling split on "## Constants").

**Total deviations:** 3 documented adjustments, none of them Rules 1-4. **Impact:** none on the plan's behaviour; all inside the declared files.

## Notes for the owner and later plans

- The facts-schema hold-out is still "fit the chosen spec on `TRAIN_SETS`, score set 6" on the chosen input; plan 06 replaces it with the per-input set-8 hold-out (research Pitfall 2) and adds `--labels`. `FACTS_SETS` stays 7 here.
- `--check-constants` of an auto run reproduces the shipped model only when the shipped model is the auto choice; after a forced run use the same `--material-input`, `--material-form`, `--spread-form` and `--loss-gate` flags (unchanged from plan 04).
- Reading the comparison table: rows can differ between inputs (a NULL fact excludes a row only where the form reads it), so the table lists each final's row count next to its AUC.

## Known Stubs

None.

## Threat Flags

None. No new endpoints, auth paths, or schema changes; the fit still reads committed files only. T-256-23 (the comparison table prints every input's rows, AUC mean and spread, fair share, and the deciding rule) and T-256-24 (constants block parsed back and compared with the chosen input's final) are mitigated and tested.

## Self-Check: PASSED

- `scripts/blunder_check/fit_facepalm.py`, `tests/scripts/test_fit_facepalm.py`: present and committed
- commits `5802faded`, `ac23137be`, `10f6c88ca`: ancestors of HEAD
- `commits: 3` measured from the plan-head ledger (`037dcb3813a8..HEAD`)
- working tree clean before this SUMMARY
