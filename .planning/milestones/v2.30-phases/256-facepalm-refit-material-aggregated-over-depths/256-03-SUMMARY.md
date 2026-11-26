---
phase: 256-facepalm-refit-material-aggregated-over-depths
plan: 03
subsystem: scoring
tags: [facepalm, wr-01, first-stable, loss-gate, sql-twin-parity]
requires: ["256-01", "256-02"]
provides:
  - "_pure_miss_term / _pure_miss_sql: WR-01 fix in both twins (D-04)"
  - "first_stable / first_stable_sql, aggregate / aggregate_sql (exhaustive over MaterialInput via assert_never) in app/services/facepalm_material.py"
  - "MaterialInput = Literal['depth_3', 'decaying_mean', 'first_stable']"
  - "tests/facepalm_seed.SEED_BEST_PROB, tests/scripts/test_blunder_check_calibration.DEFAULT_BEST_PROB"
  - "Aggregate parity grid (_AGGREGATE_GRID, test_sql_twin_parity_aggregate_inputs) over input x spread form x gate x lambda"
  - "scripts/blunder_check/decaying_mean.py sources its depths, ratio, weights and mean from facepalm_material"
affects: [256-04, 256-05, 256-06, 256-07]
tech-stack:
  added: []
  patterns:
    - "one CASE ladder for first_stable (stable pairs first, fallbacks from the last depth backwards)"
    - "aggregate dispatch by match + assert_never so a new MaterialInput value fails ty"
key-files:
  created: []
  modified:
    - app/services/facepalm_score.py
    - app/services/facepalm_material.py
    - app/services/blunder_check_rules.py
    - scripts/blunder_check/decaying_mean.py
    - tests/services/test_facepalm_score.py
    - tests/services/test_facepalm_material.py
    - tests/facepalm_seed.py
    - tests/scripts/test_blunder_check_calibration.py
    - tests/scripts/test_decaying_mean.py
    - tests/scripts/test_backfill_maia_flaws.py
    - tests/services/test_maia_flaw_scoring.py
key-decisions:
  - "first_stable (A1, for the owner at D-13): first odd-depth pair with equal known values, discounted by MATERIAL_DECAY_RATIO ** onset index; no stable pair falls back to the last known value discounted by its own index"
  - "A lone depth-3 slot (single_depth_material) therefore scores 3 * 0.5 under first_stable, unlike the other inputs; the single_depth test and the helper docstring say so"
  - "The aggregate dispatch lives in facepalm_material (aggregate / aggregate_sql) so the score twins stay flat"
requirements-completed: [D-03, D-04, D-06, D-11]
duration: ~95 min (about 25 min of it full-suite runs)
completed: 2026-11-16
status: complete
actuals:
  tokens: 9400
  tasks: 3
  commits: 4
plan_head_before: 8f54c654496f48ba2d1ab77be1bf9e40dcabf511
plan_head_after: d3d50ba8d
---

# Phase 256 Plan 03: WR-01 fix, first stable input, loss gate parity Summary

Both score twins now leave a no-loss row with an unknown best-move probability unscored under `best_prob_for_misses` (254 WR-01), implement the third material input `first_stable`, and agree on every input x spread form x gate x lambda over a dedicated parity grid; the set-8 sampler shares the app's decaying mean.

## Accomplishments

- **WR-01 (D-04).** `_pure_miss_term` (Python) and `_pure_miss_sql` (SQL) replace `_best_prob_term` / `_best_prob_sql` on the `best_prob_for_misses` pure-miss branch: None / NULL for a NULL best-move probability, 0.0 for a coefficient of exactly 0.0, the scaled log otherwise. The additive path (`_optional_terms`, `_optional_sql`) is unchanged and still reads NULL as 0. Fix-site comments say what broke and why; the module docstring's spread and optional rules are updated.
- **First stable input (D-06, A1).** `first_stable` / `first_stable_sql` in `facepalm_material.py`; `material_loss`, `material_missed`, `_loss_sql`, `_missed_sql` go through `aggregate` / `aggregate_sql` (a `match` with `assert_never`, so a fourth `MaterialInput` value fails `ty`). Same coverage gate, mate short-circuit and "missed None becomes 0.0" as the decaying mean (D-03).
- **Loss gate (D-11).** Tests pin `loses` / `loses_sql` at gates None and 1.0: a 0.52 decaying-mean loss is losing under None and not under 1.0, a constant one-pawn loss (mean exactly 1.0) is losing under both (A4, `>=`); under `depth_3` the two gates give identical scores on integer losses in both twins.
- **Parity grid.** `_AGGREGATE_GRID` (6,144 rows: NULLs, 3- and 5-slot arrays, NULL slots inside an array, garbage even slots, played mate ply 1/3/5, best mate ply 0/2/4, NULL best line, spread and best probability). `test_sql_twin_parity_aggregate_inputs` collects 20 ids (2 inputs x 5 spread-form/gate shapes x 2 lambdas), all pass. `first_stable` models were added to the shape-parity and stored-facts `facepalm_expr` tests.
- **Compiled shape (T-256-07).** `test_aggregate_expression_is_one_scalar_expression` asserts no `unnest` and no SELECT in the compiled `facepalm_expr` of a decaying-mean and a first-stable model.
- **Sampler (Task 3).** `scripts/blunder_check/decaying_mean.py` keeps its public names but imports the depths, ratio, weights and mean from `facepalm_material`; parity tests pin `decaying_mean`, `loss_series` (vs `loss_by_depth`, floor 0) and `gain_series` (vs `gain_by_depth`, floor 0, shipped cap and mate) to the app over arrays x mate plies.

## Task Commits

1. Task 1 (tracer): `bd20422b7` fix(256-03): unscore a pure miss without a best-move probability in both twins
2. Task 2 RED: `ce378392d` test(256-03): failing tests for first_stable, the loss gate and the aggregate parity grid
3. Task 2 GREEN: `30016ab09` feat(256-03): first_stable material input and the loss gate in both twins
4. Task 3: `d3d50ba8d` refactor(256-03): the set-8 sampler shares the app's decaying-mean arithmetic

Tracer gate: end-of-phase mode and an automated-only `<verify>`: the tracer `<verify>` (`-k best_prob`, then the full suite) was green before Task 2 started; no checkpoint.

## TDD evidence (Task 2)

- RED: `test_first_stable_values` fails on `assert None == 3.0` (the RED stub of `first_stable` returns None), also `test_first_stable_score_value` and `test_single_depth_material_scores_like_the_depth_3_scalar[first_stable]`. `gsd_run check tdd-red-evidence` on the pytest JUnit report returned `RED_EVIDENCE_OK` (`target_test_failed`). Semantic assessment: the target ran and failed on the planned assertion, not on an import or fixture fault. The RED commit contains two stubs (`first_stable`, `first_stable_sql`) and the `MaterialInput` extension, because a test cannot name a symbol that does not exist (a missing import is INVALID_RED).
- Honest limit: while `material_input="first_stable"` still fell through to the depth-3 branch in both twins, the parity-grid tests passed trivially (both twins agreed on the wrong value); only the value-level tests were red. The grid's discriminating power was shown afterwards by mutation: reversing the SQL fallback order of `first_stable_sql` fails 10 of the 34 `aggregate_inputs` / `first_stable` tests, and restoring it passes all 34.
- GREEN: `30016ab09`. No REFACTOR commit.

## Gap-closure proof (WR-01 revert run)

With the pure-miss branch pointed back at `_best_prob_term` (Python) and `_best_prob_sql` (SQL), `uv run pytest tests/services/test_facepalm_score.py -k best_prob` gave 5 failed, 16 passed:

- `test_pure_miss_without_best_prob_is_unscored[2.0-depth_3]`, `[2.0-decaying_mean]`, `[None-depth_3]`, `[None-decaying_mean]`
- `test_expr_unscores_pure_miss_without_best_prob`

With the fix restored: 21 passed.

## Verification

- `uv run pytest tests/services/test_facepalm_score.py tests/services/test_facepalm_material.py`: 196 passed
- `uv run pytest tests/services/test_facepalm_score.py -k "parity or gate"`: 98 passed
- `uv run pytest tests/scripts/test_decaying_mean.py tests/scripts/test_miss_labels.py`: 220 passed
- `uv run ruff check .`: clean; `uv run ruff format app/ tests/ scripts/ analysis/`: unchanged
- `uv run ty check app/ tests/ scripts/`: All checks passed
- `uv run python scripts/check_function_size.py app/ --fail-over-depth 4`: OK, no breaches
- `uv run pytest -n auto`: 6929 passed, 19 skipped (full backend suite, 12m41s)

## Deviations from Plan

**1. [Rule 1 - Bug exposed by the fix] Reader and service tests that scored a pure miss without a best-move probability**
- **Found during:** Task 1 (full suite after the WR-01 fix)
- **Issue:** WR-01 changes the shipped model's behaviour for any seeded pure miss without `maia_best_prob`. Besides the files the plan lists (`tests/facepalm_seed.py`, `tests/scripts/test_blunder_check_calibration.py`), two more test files seeded such rows: `tests/scripts/test_backfill_maia_flaws.py` and `tests/services/test_maia_flaw_scoring.py` (plan Task 1 step 5 says to fix the seeding of every reader test the change breaks).
- **Fix:** seed a best-move probability (`_SEEDED_PRE["maia_best_prob"]` in the backfill tests, `_STORED_BEST_PROB = 0.3` in the scoring tests) and pass it to the expected `FacepalmFacts`. The assertions' intent is unchanged except one: `test_best_move_missing_keeps_loss_only_score` asserted that a blunder with a missing best move is still scored on the loss alone. That blunder loses no material, so under D-04 it is now unscored; the test now asserts `scores_set == 0` and its docstring says why. This is WR-01 itself changing the expected value (plan Task 1 step 4 asks to note any such change).
- **Files modified:** tests/scripts/test_backfill_maia_flaws.py, tests/services/test_maia_flaw_scoring.py
- **Commit:** `bd20422b7`

**2. [Rule 3 - Blocking] `_blunder` helper default for `best_prob`**
- In `tests/scripts/test_blunder_check_calibration.py` the helper's `best_prob` default became "the seeded one when `score` is given, else None" (`_UNSET` sentinel) so score-seeded no-loss rows stay scored; an explicit `None` still keeps a row unscored. The plan's `DEFAULT_BEST_PROB = 0.2` is used for the `misses` and `neither` rows of `TestSectionMaterialTypes`.

**3. [Documented adjustment] `single_depth_material` and first_stable**
- A lone depth-3 slot is not "the same under every input": `first_stable` discounts it by its onset index (3 * 0.5). The docstring of `single_depth_material` and `test_single_depth_material_scores_like_the_depth_3_scalar` now say so. No effect on `depth_3` / `decaying_mean`.

**Total deviations:** 3 (1 Rule 1, 1 Rule 3, 1 documentation). **Impact:** test-only beyond the plan's scope list; no production behaviour beyond D-04 / D-06 / D-11.

## Notes for the owner and later plans

- **A1 (first_stable definition) is an assumption** carried from research Pattern 2 rule 7 and is for the owner to confirm at D-13: onset discount reuses `MATERIAL_DECAY_RATIO`, a gain or loss series is compared on the per-depth values (after cap and floor), and a mate beyond `LINE_DEPTH` enters per depth before the comparison.
- First stable compares floats with `==`. Per-depth values are small integers or mate values, so equality is exact in both twins.
- Plan 04's fit must add `maia_best_prob`-aware row filtering (WR-03 / D-05): rows excluded for NULL best probability under `best_prob_for_misses` now match what the shipped twins leave unscored.
- The WR-01 live effect (0.68% of scored prod rows, 14,826 of 2,178,931 on 2026-11-16) is not measured here; it takes effect on deploy.

## Known Stubs

None. (The RED stubs of `first_stable` / `first_stable_sql` were replaced in `30016ab09`.)

## Threat Flags

None. No new endpoints, auth paths or schema changes.

## Self-Check: PASSED

- `_pure_miss_term`, `_pure_miss_sql`, `_best_prob_term`, `_best_prob_sql` all defined in `app/services/facepalm_score.py`
- `test_pure_miss_without_best_prob_is_unscored`, `test_expr_unscores_pure_miss_without_best_prob`, `SEED_BEST_PROB: Final[float] = 0.2`, `MaterialInput = Literal["depth_3", "decaying_mean", "first_stable"]`, `first_stable`, `first_stable_sql`, and the `facepalm_material` import in the sampler: present
- commits `bd20422b7`, `ce378392d`, `30016ab09`, `d3d50ba8d`: ancestors of HEAD
