---
phase: 262-facepalm-promotions-and-key-move-gate
plan: 03
subsystem: facepalm-fit
tags: [facepalm, refit, features-table, fit-report, D-05, promotion-rule]
requires: ["262-01", "262-02"]
provides:
  - "scripts/blunder_check/refresh_features_material.py: offline recompute of loss / missed with the current rule, Phase 259 pair kept as loss_shipped / missed_shipped"
  - "fit_facepalm.py: old_gate shape, SHAPE_GATES, D-05 reference section, changed-inputs section, shipped_baseline as the Phase 259 rule and shape"
  - "reports/blunder-check/facepalm-features-2026-11-23.tsv and facepalm-fit-2026-11-23.md: the refit the owner checkpoint (plan 06) reads"
affects:
  - scripts/blunder_check/refresh_features_material.py
  - scripts/blunder_check/fit_facepalm.py
key-files:
  created:
    - scripts/blunder_check/refresh_features_material.py
    - tests/scripts/test_refresh_features_material.py
    - reports/blunder-check/facepalm-features-2026-11-23.tsv
    - reports/blunder-check/facepalm-fit-2026-11-23.md
  modified:
    - scripts/blunder_check/fit_facepalm.py
    - tests/scripts/test_fit_facepalm.py
key-decisions:
  - "The refit features are the 2026-11-22 lines (RESEARCH assumption A4: 'today's lines'), recomputed with the promotion rule offline; probabilities and labels copied verbatim"
  - "Constants in the report are the chosen type-gate fit; the old gate and the Phase 259 baseline are information only (259 D-01)"
  - "App untouched: blunder_check_rules.py still holds the Phase 259 constants until plan 07 pastes the confirmed ones"
requirements-completed: [D-01, D-04, D-05]
metrics:
  completed: 2026-11-23
status: complete
actuals:
  tokens: 20000
  tasks: 3
  commits: 3
plan_head_before: c8eb0ce0ac679c7ecd8319cbb4c7ca9b95fa8f3a
plan_head_after: 40ac430e2121f7d805cfb5e71bf9973b8f3e5893
---

# Phase 262 Plan 03: Offline refit on the new rule and gate Summary

The committed 2026-11-22 table was run through the promotion rule offline (no database, no Maia) and refitted under the type-rule gate; the fit report now carries the D-05 old-gate line, the Phase 259 baseline and the rows whose inputs moved. The report is byte-reproducible and nothing was pasted into the app.

## What was built

- **Task 1 (tracer), `1d7747ea4`:** `refresh_features_material.py` (`refresh_row`, `refresh_table`, `RefreshSummary`, `RAW_INPUT_COLUMNS`, `STALE_COLUMN_PREFIXES`, `EXIT_OK`, `EXIT_BAD_TABLE`, `--features` / `--out`). `loss` / `missed` come from `facepalm_material_inputs` on `pre_fen`, `played_uci`, `played_line`, `best_line`; the previous pair (the input's `loss` / `missed` cells, overwriting the older shipped columns the 2026-11-22 table already carried) becomes `loss_shipped` / `missed_shipped`; `played_mat_*` / `best_mat_*` are dropped; a recomputed cell equal in value to the old one keeps the old text, so unchanged rows stay byte-identical. Missing raw column: exit 2, no file written. 13 tests.
  Tracer run printed: `291 rows, 0 without raw inputs, 8 changed; changed rows (n): 31 35 57 139 170 177 231 266`, the same list RESEARCH predicted. The output loads in `fit_facepalm.load_features` with `has_shipped` True and has no `_mat_` column.
- **Task 2, `3057cbb88`:** `fit_facepalm.py`: shape `old_gate` after `chosen`; `SHAPE_GATES` (`shipped_baseline` and `old_gate` pin the loss gate, the rest use the run's gate); `_shape_gate`; `REPLY_PROB_SHAPES` / `SPREAD_SHAPES` decide which terms a shape needs (`missing_reason`) and builds (`design_row`). `shipped_baseline` is now the Phase 259 shape: chosen columns, reply probability when loss > 0, on `loss_shipped` / `missed_shipped`. New sections `_old_gate_section` and `_changed_inputs_section` (omitted when the table has no shipped columns); `FitOutcome` gained `has_shipped`. New tests: `test_shipped_baseline_reads_the_old_pair_with_the_old_gate`, `test_old_gate_reference_section`, `test_changed_inputs_section_lists_rows_whose_pair_moved`, `test_changed_inputs_section_is_absent_without_the_shipped_columns`.
- **Task 3, `40ac430e2`:** `facepalm-features-2026-11-23.tsv` and `facepalm-fit-2026-11-23.md` committed (the 2026-11-23 name did not exist yet). A re-run into `temp/blunder-check/fit-262-03-rerun.md` is `cmp`-identical. `--check-constants` was not run on the new table, by design (the app still holds the Phase 259 constants until plan 07).

## Fit results for the owner checkpoint (plan 06)

Constants (the type-gate fit, as printed in `## Constants`):

```
FACEPALM_INTERCEPT: float = -1.7891
FACEPALM_PLAYED_COEF: float = -0.6193
FACEPALM_LOSS_COEF: float = 0.8879
FACEPALM_MISSED_COEF: float = 0.3993
FACEPALM_BEST_PROB_COEF: float = 1.1635
FACEPALM_REPLY_PROB_COEF: float = 0.8057
```

(Phase 259 values for comparison, from the 2026-11-22 report, are in `facepalm-fit-2026-11-22.md`.)

- Usable rows 268 (139 fair, 129 unfair); 291 in the file, 11 undecided, 2 extra rows, 10 NULL loss.
- CV AUC (10-fold): 0.890, mean over 5 seeds 0.889, spread 0.005. In sample 0.901.
- Set-8 hold-out (fit on sets 1-7, 210 rows; 58 rows in set 8): AUC 0.857; at 0.70 19 passers, 12 fair / 7 unfair.
- Phase 259 baseline (`shipped_baseline`): CV AUC mean 0.908. `|AUC(chosen) - AUC(shipped_baseline)| = 0.019` against 0.02: within range, at the edge of it (RESEARCH Pitfall 7). Printed, never used to choose (259 D-01).
- Old gate (D-05, information only), same rows: CV AUC 0.902, out-of-fold fair / unfair at 0.70 = 99 / 12; the chosen (type gate) fit is 0.889 and 94 / 11.
- D-15 fair / unfair among passers (out of fold, all rows): 0.50: 114 / 23; 0.55: 111 / 21; 0.60: 106 / 17; 0.65: 97 / 14; 0.70: 94 / 11. By type at 0.70: loses 63 / 6, misses 11 / 0, loses_and_misses 20 / 5, neither 0 / 0.
- Changed-inputs rows (8): n 31 (label 1) 1.000 / 0.000 to 1.000 / 5.000; 35 (1) 0.000 / 1.484 to 2.419 / 1.484; 57 (0) 0.000 / 0.000 to 0.000 / 0.129; 139 (0) 0.903 / 0.484 to 2.935 / 0.000; 170 (0) 0.000 / 0.903 to 0.387 / 1.000; 177 (0) 0.000 / 0.000 to 3.871 / 2.323; 231 (1) 0.774 / 0.774 to 1.903 / 1.194; 266 (0) 0.000 / 0.000 to 1.129 / 0.000. Label 177 gets a loss of 3.871 as expected.
- Scores of those eight rows under the chosen constants (in sample, my own computation, not in the report): 31: 0.868, 35: 0.932, 57: 0.204, 139: 0.797, 170: 0.216, 177: 0.981, 231: 0.885, 266: 0.404. Two unfair-labelled rows (177 "a promotion in an endgame race", and 139) land above the 0.70 cut under the new inputs; the checkpoint should look at them.
- "Today's lines" are the 2026-11-22 lines (RESEARCH assumption A4); no new prod pull was made.

## Verification

- `uv run pytest tests/scripts/test_fit_facepalm.py tests/scripts/test_refresh_features_material.py tests/scripts/test_facepalm_features.py`: 72 passed.
- `fit_facepalm.py ... --gate loss --check-constants` on the 2026-11-22 table: exit 0 (Phase 259 history reproduces).
- `ruff check`, `ruff format --check`, `ty check app/ tests/ scripts/` and `check_function_size.py --fail-over-depth 4` on the touched files: clean.
- Mutation check: setting `SHAPE_GATES["shipped_baseline"]` to None makes `test_shipped_baseline_reads_the_old_pair_with_the_old_gate` fail; restored.
- Acceptance greps: `def refresh_table` 1, `_mat_` in the tracer header 0, old-gate heading in `fit_facepalm.py` 1, report section grep 3, `app/services/blunder_check_rules.py` unchanged.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `design_row` read the reply spread for the chosen-shaped shapes**
- **Found during:** Task 2
- **Issue:** the spread was required (`_require`) on every reply-reading row regardless of shape, so a NULL `reply_spread` would have raised for the chosen, Phase 259 baseline and old-gate shapes, which do not use it.
- **Fix:** the spread is read only for the two spread shapes.
- **Files modified:** scripts/blunder_check/fit_facepalm.py
- **Commit:** 3057cbb88

**2. [Rule 2 - Missing critical] `FitOutcome.has_shipped`**
- The changed-inputs section must only render when the table has the shipped columns; the outcome did not carry that, so the field was added.

Other notes: the plan's Task 3 mentions a `gsd/phase-262-...` branch check; this run was in an isolated worktree on `worktree-agent-a3d5b421eca477453`, so the orchestrator owns the branch. The plan 03 files were all in the declared set; `scripts/backfill_promotion_material.py` and `docs/dev-tooling.md` (plan 04) were not touched.

## Known Stubs

None.

## Threat Flags

None. No new network, auth or schema surface; T-262-05 mitigated (previous pair copied verbatim and tested, stale per-depth columns dropped, unchanged rows byte-identical), T-262-06 mitigated (both report files committed, `cmp` re-run identical).

## Self-Check: PASSED

- FOUND: scripts/blunder_check/refresh_features_material.py, tests/scripts/test_refresh_features_material.py, reports/blunder-check/facepalm-features-2026-11-23.tsv, reports/blunder-check/facepalm-fit-2026-11-23.md
- FOUND commits 1d7747ea4, 3057cbb88, 40ac430e2 (ancestors of HEAD)
