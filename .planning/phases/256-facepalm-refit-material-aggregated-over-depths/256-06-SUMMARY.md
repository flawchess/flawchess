---
phase: 256-facepalm-refit-material-aggregated-over-depths
plan: 06
subsystem: scoring-fit
tags: [facepalm, fit, holdout, set-8, owner-checkpoint, d-08, d-13]
requires: ["256-05"]
provides:
  - "TRAIN_SETS / TEST_SET = sets 1-7 vs set 8 (TRAIN_SETS_TEXT '1-7'); the legacy split kept as LEGACY_TRAIN_SETS / LEGACY_TEST_SET / LEGACY_TRAIN_SETS_TEXT"
  - "input_holdout: each input's whole staged pipeline run on sets 1-7 only, its final scored on set 8"
  - "holdout_disagreement + FactsOutcome.holdout_disagreement: flag when another input beats the CV choice on set 8 by more than AUC_TIE_TOLERANCE"
  - "--labels, LabelNote, load_label_notes and the '## Owner checks' section (commented rows old/new, added rows old/new per cut, pure-miss pass rate per cut)"
affects: [256-07]
tech-stack:
  added: []
  patterns:
    - "holdout of a model-selection pipeline: rerun the selection on the training rows, never refit a spec chosen with the test rows"
    - "hold-out headings derived from the split constants, never literals"
key-files:
  created: []
  modified:
    - scripts/blunder_check/fit_facepalm.py
    - tests/scripts/test_fit_facepalm.py
key-decisions:
  - "The disagreement compares set-8 AUCs only; an input without a set-8 AUC (set 8 absent, one label class, unfittable) never wins and never triggers the flag"
  - "--labels on a legacy-schema table is a FitError, and a labels file without n or comment fails before the fit runs"
  - "The owner section sits right after the chosen input's hold-out section; the other-input blocks (each with its own '### Sets 1-7 vs set 8') follow it, Extra rows and Constants stay last"
requirements-completed: [D-08, D-13]
duration: ~1h
completed: 2026-11-16
status: complete
coverage:
  - id: D1
    description: "Each input's whole pipeline is refitted on sets 1-7 and its final model scored on set 8; flipping every set-8 label leaves the sets-1-7 pipeline (spec and coefficients) unchanged"
    requirement: "D-08"
    verification:
      - kind: unit
        ref: "tests/scripts/test_fit_facepalm.py#test_set_eight_holdout_runs_the_pipeline_on_sets_one_to_seven"
        status: pass
      - kind: unit
        ref: "tests/scripts/test_fit_facepalm.py#test_every_input_carries_its_own_set_eight_holdout"
        status: pass
    human_judgment: false
  - id: D2
    description: "A disagreement line appears when the best set-8 input differs from the CV choice and beats it by more than AUC_TIE_TOLERANCE, and only then; a table without set 8 gives the 'train or holdout set is empty' note"
    requirement: "D-08"
    verification:
      - kind: unit
        ref: "tests/scripts/test_fit_facepalm.py#test_holdout_disagreement_is_flagged"
        status: pass
      - kind: unit
        ref: "tests/scripts/test_fit_facepalm.py#test_a_table_without_set_eight_says_the_holdout_is_empty"
        status: pass
    human_judgment: false
  - id: D3
    description: "The legacy table keeps its own hold-out (sets 1-5 and 7 vs set 6) with a heading derived from the split constants, and still reproduces the frozen Phase 250 model"
    requirement: "D-08"
    verification:
      - kind: unit
        ref: "tests/scripts/test_fit_facepalm.py#test_report_has_every_section_and_scores_the_extra_row"
        status: pass
      - kind: unit
        ref: "tests/scripts/test_fit_facepalm.py#test_check_constants_legacy_still_passes"
        status: pass
    human_judgment: false
  - id: D4
    description: "With --labels the owner section lists every commented label row verbatim with its old and new score (n/a for an unscored row, 'not in features' for a missing n); without it the section says to pass --labels; a labels file without n or comment is a FitError"
    requirement: "D-13"
    verification:
      - kind: unit
        ref: "tests/scripts/test_fit_facepalm.py#test_owner_section_lists_commented_rows"
        status: pass
      - kind: unit
        ref: "tests/scripts/test_fit_facepalm.py#test_owner_section_without_labels_says_so"
        status: pass
      - kind: unit
        ref: "tests/scripts/test_fit_facepalm.py#test_labels_file_without_comment_column_is_an_error"
        status: pass
    human_judgment: false
  - id: D5
    description: "The owner section shows each added row (Window 14) old and new against every cut and the pure-miss pass rate at every cut, from the chosen candidate's out-of-fold scores"
    requirement: "D-13"
    verification:
      - kind: unit
        ref: "tests/scripts/test_fit_facepalm.py#test_owner_section_scores_extra_rows_old_and_new"
        status: pass
      - kind: unit
        ref: "tests/scripts/test_fit_facepalm.py#test_owner_section_pure_miss_pass_rates"
        status: pass
    human_judgment: false
actuals:
  tokens: 12300
  tasks: 2
  commits: 3
plan_head_before: 141de9d65eb2115c8ed27c621b91835269ba5f44
plan_head_after: a54186571cd227dd9a644eb5e26d2913f576beaa
---

# Phase 256 Plan 06: Set-8 hold-out per input and the owner section Summary

The fit now checks every material input on set 8 with a pipeline that never saw it, flags a disagreement with the cross-validated choice, and prints an owner section (commented rows old and new, added rows against each cut, pure-miss pass rates) for the D-13 checkpoint.

## Accomplishments

- **Split constants (D-08).** `TRAIN_SETS` is sets 1-7, `TEST_SET` is "8", `TRAIN_SETS_TEXT` is "1-7". The legacy 2026-11-13 table keeps its own split as `LEGACY_TRAIN_SETS` / `LEGACY_TEST_SET` / `LEGACY_TRAIN_SETS_TEXT`. `_holdout` and `_split_section` take the split as parameters, and the heading is `## Sets {train_text} vs set {test_set}`, so the old literal that named the wrong train sets (research Pitfall 3) is gone.
- **`input_holdout` (D-08, Pitfall 2).** Runs `run_input_pipeline` on the base-usable rows of sets 1-7 only (all stage choices and the final coefficients come from them), then scores the spec's own usable set-8 rows with `sigmoid(design @ coef)`. It returns the AUC and the passer table at `thresholds_for(threshold)`. This replaces the old facts-path `_holdout` call, which refitted a spec that had been chosen with the test set included. `InputOutcome.holdout` carries the result; the small frozen `PipelineModes` dataclass carries the forcing flags so the hold-out reruns the same forced stages as the main run.
- **Disagreement flag.** `holdout_disagreement` names the best set-8 input when it differs from the CV choice and beats the chosen input's set-8 AUC by more than `AUC_TIE_TOLERANCE`; the text says the owner settles it at the D-13 checkpoint. `FactsOutcome.holdout_disagreement` carries it into the report.
- **Report.** "## Material input (D-06, D-07, D-08, D-09)" gains set-8 rows, set-8 AUC and set-8 fair / unfair at the cut per input, the disagreement line when present, and the note that set 8 has about 55 decided rows so its AUC moves by several hundredths. The chosen input's hold-out is "## Sets 1-7 vs set 8"; each other input's sits under its "## Other input" block as a level-3 heading.
- **Owner section (D-13).** `--labels` (facts schema only) feeds `load_label_notes` (commented rows only; a missing `n` or `comment` column is a FitError raised before the fit runs; a row without a comment cell is skipped). "## Owner checks" lists each commented row (n, set, label, link, comment verbatim with pipes escaped, old score under `FACEPALM_MODEL`, new score under the chosen model, both with the drill lambda), each added row (Window 14 among them) old and new against each cut, and the pure-miss pass rate at each cut from the chosen candidate's out-of-fold scores, plus the line about the two owner fixtures. `row_score` factors the per-row scoring out of `score_extras`.
- **Real runs on the committed 2026-11-15 table (no set 8 in it, informational).** The hold-out sections say "train or holdout set is empty" and the comparison table has the set-8 columns. With `--labels reports/blunder-check/facepalm-labels.tsv` the owner section lists all 15 commented set-7 rows (n 211 to 240) with old and new scores, plus 13 commented set-8 rows as "not in features" (the table predates set 8), and the pure-miss pass rate is 0.286 / 0.254 / 0.206 / 0.127 / 0.048 at the cuts 0.5 / 0.6 / 0.7 / 0.8 / 0.9 (63 pure-miss rows). Plan 07 runs this on the real table.

## Task Commits

1. Task 1 (tracer): `4ebe05f32` feat(256-06): fit each input on sets 1-7 and score set 8, flag a disagreement (D-08)
2. Task 2 RED: `56c4fda2d` test(256-06): add failing tests for the D-13 owner section
3. Task 2 GREEN: `a54186571` feat(256-06): add the owner section and --labels for the D-13 checkpoint

Tracer gate: end-of-phase mode with an automated-only `<verify>`. Re-run before Task 2: the two named tests, the whole test file (64 passed) and the real-table fit with `grep "^## Sets 1-7 vs set 8"`, all green. Logged: tracer verified end-to-end, expanding. No checkpoint.

## TDD evidence (Task 2)

- RED: the five owner-section tests and the `--help` flags test all failed on the planned behaviour: `--labels` was an unrecognised argument (`assert 2 == 0` on the exit code, the `'comment'` message assertion, the `--help` assertion) or the report had no "## Owner checks" section (`assert OWNER_HEADING in report`). `gsd-tools check tdd-red-evidence` on the pytest JUnit report of `test_owner_section_without_labels_says_so` returned `RED_EVIDENCE_OK` (`target_test_failed`, format junit). Semantic assessment: the target test ran and failed on the planned assertion (the report has no owner section), not on an import, syntax or fixture fault. One RED pass initially failed with `IndexError` from a bare `split(...)[1]`; the helper `_owner_text` now asserts the heading first so RED is an assertion failure, and that change is in the RED commit.
- Mutation proof (T-256-13): making `input_holdout` train on sets 1-7 plus 8 made `test_set_eight_holdout_runs_the_pipeline_on_sets_one_to_seven` fail (`Extra items in the left set: '8'`); restored, 4 of 4 Task 1 tests passed.
- GREEN: `a54186571`, 69 passed in the file. One test fixture was corrected in the GREEN commit: `test_owner_section_scores_extra_rows_old_and_new` first read the extra row from `facts_run.outcome.extras`, which is empty because that outcome is fitted on the usable rows only; it now reads the unlabelled row from the features table. No REFACTOR commit.

## Verification

- `uv run pytest tests/scripts/test_fit_facepalm.py`: 69 passed (the 2026-11-15 depth-3 refit pin and the legacy `--check-constants` pin both pass)
- `uv run pytest -n auto` (full backend suite): 6957 passed, 19 skipped, 167 s
- `uv run ruff check .`: clean; `uv run ruff format --check app/ tests/ scripts/ analysis/`: 620 files already formatted
- `uv run ty check app/ tests/ scripts/`: All checks passed; `uv run --project analysis --with ty ty check analysis/`: All checks passed
- `uv run python scripts/check_function_size.py app/ --fail-over-depth 4`: OK, no breaches
- `fit_facepalm.py --features ...2026-11-15.tsv --out temp/blunder-check/fit-holdout-256-06.md`: exit 0, "## Sets 1-7 vs set 8" with the empty-set note, set-8 columns in the comparison table
- `fit_facepalm.py --features ...2026-11-15.tsv --labels ...facepalm-labels.tsv --out temp/blunder-check/fit-owner-256-06.md`: exit 0; `grep -c "^| 2[0-4][0-9] | 7 |"` prints 15; the label-211 comment "currently 6%, should be at least 90%" is in the report

## Deviations from Plan

**1. [Documented adjustment] `holdout_disagreement` takes the input outcomes, not a prebuilt value**
- Signature `holdout_disagreement(inputs, chosen_input)`; the test builds its cases by `dataclasses.replace` on real `InputOutcome` / `SplitResult` values of the fixture run, as the plan describes. `FactsOutcome.holdout_disagreement` defaults to None, `InputOutcome.holdout` defaults to a `NO_HOLDOUT` placeholder (what `run_input_pipeline` returns before the caller fills it).
- Files: scripts/blunder_check/fit_facepalm.py. Commit `4ebe05f32`.

**2. [Documented adjustment] `FactsOutcome.split` kept, `PipelineModes` and `row_score` added**
- `FactsOutcome.split` stays and is the chosen input's hold-out (the renderer and tests read it); `PipelineModes` bundles the four forcing flags so `input_holdout(base_usable, settings, material_input, modes)` has the plan's four-argument shape; `row_score` factors the per-row score out of `score_extras` for the owner section. `_pipelines` now takes `PipelineModes` instead of four keyword arguments.
- Files: scripts/blunder_check/fit_facepalm.py. Commits `4ebe05f32`, `a54186571`.

**3. [Documented adjustment] `--labels` on a legacy table is an error**
- Not in the plan: the owner section exists for the facts schema only, so silently ignoring the flag on a legacy table would hide a mistake. `_check_flags` raises FitError.

**4. [Test adaptation] `FACTS_SETS` is 8**
- The synthetic table now spans sets 1 to 8 as planned. `test_unlabelled_set_eight_rows_are_extras_not_fit_rows` kept its intent without any fixture change (it appends unlabelled set-8 rows, which are still extras).

**Total deviations:** 4 documented adjustments, none of them Rules 1-4. **Impact:** none on the plan's behaviour; all inside the declared files.

## Notes for the owner and later plans

- The 2026-11-15 table's unlabelled `extra` row scores "n/a" under both the old and the new model in the added-rows table (a NULL input in that row), so Window 14 against the cut cannot be read from this table. Plan 07 regenerates the features table with the extra row (`--extra 2099808:23`); check that row first.
- The owner fixtures (games 817357 ply 24, 820181 ply 65) are not in the features table; the section only points to `tests/services/facepalm_owner_fixtures.py`, scoring them stays a checkpoint step.
- The hold-out reruns each input's whole pipeline once more on sets 1-7, so a facts fit costs roughly twice as long as before; on the synthetic 1200-row table the whole test file still runs in about a minute.
- Set 8 has about 55 decided rows: a disagreement flag is a prompt for the owner's judgement, not a verdict.

## Known Stubs

None.

## Threat Flags

None. No new endpoints, auth paths or schema changes. T-256-13 (set 8 leaking into the hold-out) is mitigated and mutation-tested; T-256-12 (blind set-8 key) holds: the fit reads only `--features` and `--labels`, the key under `temp/` was never read or added; T-256-11 (comments and links copied into the report) is accepted as planned.

## Self-Check: PASSED

- `scripts/blunder_check/fit_facepalm.py` defines `def input_holdout(`, `def load_label_notes(`, `def _owner_section(` and `--labels`; `tests/scripts/test_fit_facepalm.py` defines the named tests: present and committed
- commits `4ebe05f32`, `56c4fda2d`, `a54186571`: ancestors of HEAD
- `commits: 3` measured from the plan-head ledger (`141de9d65eb2..HEAD`)
- working tree clean before this SUMMARY
