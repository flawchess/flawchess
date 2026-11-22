---
phase: 259-facepalm-first-principles-refit
plan: 07
subsystem: tooling
tags: [facepalm, fit, logistic-regression, check-constants, test-trim]

requires:
  - phase: 259-03
    provides: "reports/blunder-check/facepalm-features-2026-11-21.tsv (scalar schema) and the D-09 decision confirm-retire"
  - phase: 259-06
    provides: "R1 on main, SW cycle branch"
provides:
  - "scripts/blunder_check/fit_facepalm.py rewritten: fixed-shape scalar fit of the six FACEPALM_* coefficients, D-12 alternatives (information only), D-15 cut table, --check-constants over six constants"
  - "scripts/blunder_check/metrics.py material_type_of(loss, missed)"
  - "tests/scripts/test_fit_facepalm.py trimmed from 70 tests / 123.6 s to 21 tests / 17.3 s"
affects: [259-09, 259-11]

actuals:
  tokens: 16700
  tasks: 3
  commits: 2
commits: 2
plan_head_before: 1af919b93ff991eedd2fcf673bdd17cbf554d3ee
plan_head_after: 7b8982ba02cbb7ae3e863c996a5c2dbab3199758

tech-stack:
  added: []
  patterns:
    - "the fit tool never imports the score twin; it reads the app only through the rules module (PLAYED_PROB_OFFSET, FACEPALM_* by attribute)"
    - "design-row column order equals CONSTANT_NAMES order, so the coefficient vector maps to the constants block directly"

key-files:
  created: []
  modified:
    - scripts/blunder_check/fit_facepalm.py
    - scripts/blunder_check/metrics.py
    - tests/scripts/test_fit_facepalm.py
    - tests/scripts/test_blunder_check_metrics.py
    - tests/scripts/test_facepalm_features.py

key-decisions:
  - "Design column order is intercept, played, loss, missed, best_prob, reply_prob (CONSTANT_NAMES order), not the plan prose order (reply before best): the vector maps to the six constants without a permutation"
  - "The D-12 range check compares the repeated-seed mean CV AUC of chosen and shipped_baseline, not a single-seed AUC"
  - "An empty `missed` cell is read as 0.0 (254 D-18), an empty `loss` as NULL (row excluded)"
  - "Open question 6: retired (owner, plan 03), no scripts/blunder_check/legacy/ package"

requirements-completed: [D-01, D-03, D-08, D-12, D-14]

coverage:
  - id: D1
    description: "Fit has one fixed shape and fits only six coefficients; staged selection and forced-shape flags are gone"
    requirement: "D-01"
    verification:
      - kind: unit
        ref: "tests/scripts/test_fit_facepalm.py#test_synthetic_recovery_and_constants_block"
        status: pass
      - kind: unit
        ref: "tests/scripts/test_fit_facepalm.py#test_help_lists_the_documented_flags"
        status: pass
    human_judgment: false
  - id: D2
    description: "Design row gates the reply term to losing rows and the best term to non-losing rows; exclusions counted per reason"
    requirement: "D-08"
    verification:
      - kind: unit
        ref: "tests/scripts/test_fit_facepalm.py#test_design_row_gates_reply_and_best_terms_by_loss"
        status: pass
      - kind: unit
        ref: "tests/scripts/test_fit_facepalm.py#test_exclusions_are_counted_per_reason"
        status: pass
    human_judgment: false
  - id: D3
    description: "Information-only alternatives section with the |delta AUC| range check; constants stay the chosen fit"
    requirement: "D-12"
    verification:
      - kind: unit
        ref: "tests/scripts/test_fit_facepalm.py#test_alternatives_section_is_information_only"
        status: pass
    human_judgment: false
  - id: D4
    description: "Label sets 1 to 8 as they are, set 8 hold-out, fair / unfair among passers at the D-15 cuts out of fold"
    requirement: "D-14"
    verification:
      - kind: unit
        ref: "tests/scripts/test_fit_facepalm.py#test_d15_cut_table_lists_every_cut"
        status: pass
      - kind: unit
        ref: "tests/scripts/test_fit_facepalm.py#test_fit_runs_on_the_committed_259_features"
        status: pass
    human_judgment: false
  - id: D5
    description: "--check-constants refits and compares the six constants within 1e-4, exit 6 with a table, a missing name is a mismatch row"
    requirement: "D-03"
    verification:
      - kind: unit
        ref: "tests/scripts/test_fit_facepalm.py#test_check_constants_exits_6_and_prints_the_table_on_a_mismatch"
        status: pass
      - kind: unit
        ref: "tests/scripts/test_fit_facepalm.py#test_check_constants_exits_0_when_the_app_constants_are_the_refit"
        status: pass
    human_judgment: false
  - id: D6
    description: "Fit tests trimmed to what ships and the trim is measured (after total below before)"
    verification:
      - kind: other
        ref: "uv run pytest tests/scripts/test_fit_facepalm.py --durations=5: 70 passed in 123.57s before, 21 passed in 17.29s after"
        status: pass
    human_judgment: false

duration: 45min
completed: 2026-11-21
status: complete
---

# Phase 259 Plan 07: Fixed-Shape Fit Tool Summary

**The fit tool now fits exactly six coefficients of the first-principles shape (played, loss, missed, best-move probability on non-losing rows, reply probability on losing rows) from the scalar features table, prints the D-12 alternatives and the D-15 cut table as information, and its tests dropped from 123.6 s to 17.3 s.**

## Performance

- **Duration:** about 45 min
- **Completed:** 2026-11-21
- **Tasks:** 3/3 (Task 3 is the confirm-retire branch: nothing to build)
- **Files modified:** 5

## Accomplishments

- `fit_facepalm.py` rewritten from 2569 to about 1100 lines: one loader for the plan 02 columns (older tables without `loss` / `missed` / `reply_prob` are rejected with `FitError`; `loss_shipped` / `missed_shipped` are optional), `ScalarFitRow`, `ScalarCoefs`, `design_row(row, shape)`, `scalar_score(row, coefs)`, `ShapeName`, `D15_CUTS`, `AUC_RANGE`, the two new exclusion reasons. The staged selection, `CandidateSpec`, the forced-shape flags and the legacy / facts schemas are gone. The tool imports neither the score twin nor its model (`grep -cE "FacepalmModel|FACEPALM_MODEL|from app.services.facepalm_score"` prints 0).
- Report on the committed 2026-11-21 table (268 usable rows, 139 fair / 129 unfair; 10 rows excluded for NULL loss, 11 undecided, 2 extras): chosen shape CV AUC 0.908 (mean of 5 seeds, spread 0.006). Alternatives on the same 268 rows: shipped_baseline 0.897, quiet_spread 0.903, quiet_spread_reply 0.910, chosen 0.908. `|AUC(chosen) - AUC(shipped_baseline)|` = 0.012 against the 0.02 range: **within range**. Set 8 hold-out (fit on sets 1-7, 58 rows): AUC 0.838.
- D-15 table, out of fold, all rows: at cut 0.50 118 fair / 25 unfair, 0.55 116 / 21, 0.60 109 / 18, 0.65 105 / 17, 0.70 98 / 11 (also split by material type in the report).
- Candidate constants from this table, information only (plan 09 pastes from plan 11's fresh pull, not from here): `FACEPALM_INTERCEPT -1.4308`, `PLAYED_COEF -0.6065`, `LOSS_COEF 0.8379`, `MISSED_COEF 0.4971`, `BEST_PROB_COEF 2.0786`, `REPLY_PROB_COEF 0.9133`. Extra rows: Window 14 (game 2099808 ply 23) scores 0.091 (below the 0.7 cut); the D-13 row (game 2883555 ply 47) scores 0.825.
- `--check-constants` against the app today exits 6 with a table (the old constants differ, `FACEPALM_REPLY_PROB_COEF` is a `missing` row), as designed: plan 09 adds the constant.
- `metrics.material_type_of(loss, missed)` added and pinned; `material_type` stays for render.py and miss_labels.py (plan 08).

## Test trim (owner scope addition), `uv run pytest tests/scripts/test_fit_facepalm.py --durations=5`

Before (HEAD `1af919b93`, 70 tests):

```
11.39s call     test_check_constants_compares_against_the_forced_fit
10.02s setup    test_staged_selection_is_deterministic
9.86s call      test_staged_selection_is_deterministic
8.15s call      test_loss_gate_flag_forces_one_gate
7.40s setup     test_synthetic_recovery_and_constants_block
70 passed, 2 warnings in 123.57s (0:02:03)
```

After (21 tests):

```
7.05s setup    test_fit_runs_on_the_committed_259_features   (module import)
4.77s call     test_help_lists_the_documented_flags          (two --help subprocesses)
0.97s setup    test_synthetic_recovery_and_constants_block   (the 6000-row module fixture)
0.91s call     test_owner_section_lists_commented_rows
0.82s call     test_alternatives_section_is_information_only
21 passed, 2 warnings in 17.29s
```

The after total (17.29 s) is lower than the before total (123.57 s). Removed by name: every staged-selection, forced-flag, loss-floor, legacy-schema, facts-schema and fit-vs-old-twin test listed in the plan (the file no longer mentions the Phase 250 / 254 test models module). `test_design_matrix_is_the_shipped_twin` has no replacement here; the fit-vs-twin parity test lands in plan 09. The nesting-heavy new tests added: `test_design_row_gates_reply_and_best_terms_by_loss`, `test_scalar_score_is_the_logistic_of_the_chosen_shape`, `test_alternatives_section_is_information_only` (the single smoke test, pinning that the constants stay the chosen fit when `quiet_spread_reply` scores highest), `test_d15_cut_table_lists_every_cut`. `test_check_constants_reports_every_field_that_moved` became `..._every_constant_that_moved`.

## Task Commits

1. **Task 1: tracer, fixed-shape fit end to end** - `c3f784f31` (feat)
2. **Task 2: fit tests trimmed, material_type_of pinned, loader test re-pointed** - `7b8982ba0` (test)
3. **Task 3: open question 6** - no commit (confirm-retire: no `scripts/blunder_check/legacy/`; `test -d scripts/blunder_check/legacy` fails)

**Plan metadata:** the commit that carries this SUMMARY (docs: complete plan)

## Decisions Made

- Design columns follow CONSTANT_NAMES order (best before reply), a deliberate swap of the plan prose order, so the fitted vector is the constants block.
- The range check uses the 5-seed mean CV AUC of both shapes.
- Open question 6: retired (owner, plan 03).

## Deviations from Plan

None - plan executed exactly as written, with these small interpretations:

- The tracer test was committed with Task 1 in a file reduced to that one test (the old test file could not run against the rewritten tool); Task 2 then wrote the final file.
- Task 2's synthetic recovery test uses 6000 rows with tolerance 0.15 (1500 rows left an intercept error of 0.48, statistical noise confirmed at 30000 rows where it is 0.05); runtime stays under 1 s per fit.
- Quick task 261121-n50 had already deleted some script tests; every test name the plan lists for removal that was still present was removed, and none had to be restored.
- A stale comment remains in `app/services/blunder_check_rules.py` (lines 74-81: fit command with the 2026-11-16 table and `--check-constants`) and in `scripts/blunder_check/facepalm_features.py` (lines 13, 92, 115 mention the old schemas). They belong to plan 09's constants rewrite and were left alone.

## Issues Encountered

None.

## Known Stubs

None.

## Threat Flags

None. T-259-16: `--check-constants` over the six names with a tolerance, seeded deterministic CV, byte-identical report test. T-259-17: the shape is fixed in code, the alternatives section is printed only and `test_alternatives_section_is_information_only` pins that the constants stay the chosen fit.

## Verification

- `uv run python scripts/blunder_check/fit_facepalm.py --features reports/blunder-check/facepalm-features-2026-11-21.tsv --labels reports/blunder-check/facepalm-labels.tsv --out temp/blunder-check/fit-259-07.md` exits 0, the report has one `## Constants` heading with six lines, four alternative rows and a "within range" line.
- `uv run pytest tests/scripts/test_fit_facepalm.py tests/scripts/test_blunder_check_metrics.py tests/scripts/test_facepalm_features.py` 99 passed.
- `uv run ty check app/ tests/ scripts/` and `uv run ruff check app/ tests/ scripts/` clean.
- Acceptance greps: `FacepalmModel|FACEPALM_MODEL|from app.services.facepalm_score` in fit_facepalm.py 0; `def material_type_of` 1; `FACEPALM_REPLY_PROB_COEF` in fit_facepalm.py 1; `def test_staged_selection_is_deterministic` 0; `facepalm_models` in the test file 0; `def test_alternatives_section_is_information_only` 1.

## Next Phase Readiness

Plan 09 can add `FACEPALM_REPLY_PROB_COEF` and the other constants and then use `--check-constants` as its drift gate, and add the fit-vs-twin parity test against `scalar_score`. Plan 11 runs the fit on a fresh prod pull for the D-15 checkpoint.

## Self-Check: PASSED

- `scripts/blunder_check/fit_facepalm.py`, `scripts/blunder_check/metrics.py`, `tests/scripts/test_fit_facepalm.py`, `tests/scripts/test_blunder_check_metrics.py`, `tests/scripts/test_facepalm_features.py` exist; `scripts/blunder_check/legacy` does not (intended).
- Commits `c3f784f31` and `7b8982ba0` are ancestors of HEAD; `git rev-list --count 1af919b93..HEAD` = 2 at SUMMARY time.

---
*Phase: 259-facepalm-first-principles-refit*
*Completed: 2026-11-21*
