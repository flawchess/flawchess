---
phase: 256-facepalm-refit-material-aggregated-over-depths
reviewed: 2026-11-16T12:00:00Z
depth: standard
files_reviewed: 19
files_reviewed_list:
  - app/services/blunder_check_rules.py
  - app/services/facepalm_material.py
  - app/services/facepalm_score.py
  - app/services/maia_flaw_scoring.py
  - scripts/blunder_check/decaying_mean.py
  - scripts/blunder_check/fit_facepalm.py
  - scripts/blunder_check/sample.py
  - tests/facepalm_models.py
  - tests/facepalm_seed.py
  - tests/scripts/test_backfill_maia_flaws.py
  - tests/scripts/test_blunder_check_calibration.py
  - tests/scripts/test_decaying_mean.py
  - tests/scripts/test_fit_facepalm.py
  - tests/scripts/test_miss_labels.py
  - tests/services/facepalm_owner_fixtures.py
  - tests/services/test_facepalm_material.py
  - tests/services/test_facepalm_owner_fixtures.py
  - tests/services/test_facepalm_score.py
  - tests/services/test_maia_flaw_scoring.py
findings:
  critical: 0
  warning: 3
  info: 5
  total: 8
status: issues_found
---

# Phase 256: Code Review Report

**Reviewed:** 2026-11-16
**Depth:** standard
**Files Reviewed:** 19
**Status:** issues_found

## Summary

I reviewed the diff against `4bb2a21296` for all 19 files, plus the surrounding code the diff touches. I also ran the checks that would settle the areas you flagged.

**What held up under attack (no finding):**
- **Python/SQL twin parity.** I ran my own randomized parity fuzz against the live dev PostgreSQL. It used `facepalm_score` against `facepalm_score_sql` over `VALUES` rows. The rows had arrays of length 0 to 9, NULL slots, mates at plies 0 to 10 on both lines, NULL prob/spread/best_prob/pre_spread, and lambda in {0, 0.5, 1}. The models were 3 material inputs x 3 spread forms x gates {None, 1.0, 2.5} x split/combined x missed floor {None, 0}, with non-zero best_prob and pre_spread coefficients. That is 100,800 comparisons with 0 mismatches (tolerance 1e-9, NULL/None agreement exact). The script is in the scratchpad: `/tmp/claude-1000/-home-aimfeld-Projects-Games-flawchess/745d09f2-c329-4bfc-8e13-58447da8e2d8/scratchpad/fuzz_parity.py`.
- **Slot/depth indexing.** The 0-based Python and 1-based SQL indexing agree, via `material_at_depth` and `played[depth]`.
- **Decay weights.** Renormalisation over missing slots is identical in both twins.
- **`first_stable`.** The fallback order and the NULL-never-pairs rule are identical.
- **Gate boundary.** `>=` is consistent in `loses`, `loses_sql`, `_spec_exclusion` and the report text.
- **Hold-out leakage.** `input_holdout` runs the whole staged pipeline on `TRAIN_SETS` rows only and only scores set 8. Choices and coefficients cannot see set 8.
- **Per-candidate row exclusion.** `_spec_exclusion` mirrors what the shipped twin reads (spread under `always` or when `loses`, best_prob on a pure miss under `best_prob_for_misses`). On the shipped features table every candidate keeps all 261 rows, so the difference has no effect on the shipped numbers.
- **Cache version.** The v4 cache round-trips both arrays as tuples, and v3 is refused.
- **`--check-constants`.** I re-ran it on `facepalm-features-2026-11-16.tsv` with `facepalm-labels.tsv`, and the shipped constants match the refit.
- **Static checks.** `ruff check`, `ruff format --check` and `check_function_size.py` are clean.

No bugs, security issues or twin divergences were found. The three warnings are about model behaviour and evidence that the shipped configuration does not fully stand on, plus one brittle test. The info items are maintainability points.

## Warnings

### WR-01: "Loses material" gate None is hair-trigger under the decaying mean (score discontinuity)

**File:** `app/services/facepalm_material.py:207-213`, `app/services/facepalm_score.py:383-392`, `app/services/blunder_check_rules.py:109` (`FACEPALM_LOSS_GATE = None`)

**Issue:** The shipped model is `decaying_mean` + `best_prob_for_misses` + gate None, so `loses(loss, None)` is `loss > 0`. The loss is now a weighted mean over five depths with a per-depth floor of 0. Any positive loss at any single known depth makes the aggregate positive, however small its weight. Such a row is reclassified from "pure miss" (best-move term) to "loses material" (spread term). The two branches differ by several logits, so a transient one-pawn loss visible only at depth 9 (aggregate loss 0.032) flips the row's branch.

I confirmed it with the shipped twin (lambda 1.0, played_prob 0.05, spread 2.0, best_prob 0.01, best line `[4]*9`):
- played line `[0]*9`: score 0.0031
- played line `[0]*8 + [-1]`: score 0.7727

The depth_3 input did not have this property, because a depth-3 integer loss of at least 1 is a real loss. The gate=1.0 candidate exists to cure this. It is dismissed on CV, but CV is dominated by integer-loss rows where the two gates agree. The test `test_loss_gate_one_on_fractional_mean` documents the divergence but does not assess its effect on ranking.

**Fix:** Either ship gate 1.0, or gate on the depth-3 loss (the coverage-gate slot) instead of the aggregate. Or make the choice with a stage that scores rows where the gates disagree, since set 8 was drawn for exactly such disagreement. If gate None is kept deliberately, record the discontinuity in the `FACEPALM_LOSS_GATE` comment so the owner's checkpoint decision is visible in code.

### WR-02: Shipped material input is contradicted by the only fresh data, at the shipped cut

**File:** `app/services/blunder_check_rules.py:100-109` (`FACEPALM_MATERIAL_INPUT = "decaying_mean"`, `FACEPALM_SCORE_MIN = 0.5`); `scripts/blunder_check/fit_facepalm.py:1577-1597`

**Issue:** The report's own D-08 check, reproduced by re-running the fit, shows the pipeline fitted on sets 1-7 and scored on blind set 8 (58 decided rows):

| input | set-8 AUC | passers at 0.50 (fair/unfair) | at 0.70 (fair/unfair) |
|---|---|---|---|
| decaying_mean (shipped) | 0.821 | 23 (12/11), 52% fair | 14 (9/5) |
| depth_3 | 0.835 | 16 (11/5), 69% fair | 11 (9/2) |
| first_stable | 0.727 | | |

The shipped input has worse set-8 AUC, and at the shipped cut of 0.5 it admits twice as many unfair rows (11 against 5) for one more fair row. The script flags this as "Disagreement" and the owner accepted it, so this is not an implementation bug. The CV AUC that picked `decaying_mean` (0.902 against 0.879) is computed over all sets, including set 8. Set 8 was drawn specifically where the two inputs disagree, so the CV comparison is the less independent of the two.

The owner fixtures also regress. The two missed-gain rows that were the stated motivation now score 0.063 and 0.104, down from 0.146 and 0.154. The in-repo comment says they "cannot be lifted by aggregating over depths". The drill is therefore shipping a refit that the held-out data and the motivating fixtures do not support. The evidence is real but small (about 58 rows, as `SET_EIGHT_SIZE_NOTE` admits).

**Fix:** Treat the choice as provisional. Either re-evaluate on a fresh set 9 drawn independently of the depth_3/decaying_mean disagreement, or ship depth_3 (which beat the shipped input on set 8 at every cut up to 0.7) until that is done. At minimum, record the set-8 numbers next to `FACEPALM_MATERIAL_INPUT`, so the unresolved "Disagreement" is visible to the next reader of the constants.

### WR-03: Owner-fixture test pins an observed regression and hard-codes refit output

**File:** `tests/services/test_facepalm_owner_fixtures.py:~126-147` (`test_owner_fixtures_score_lower_under_the_refit_and_stay_below_the_cut`, `EXPECTED_SHIPPED_SCORE`); same pattern at `:~170-178`

**Issue:** The test asserts `shipped < previous` and `shipped == approx(0.0632 / 0.1044, abs=5e-5)`. This turns "the owner's two should-qualify fixtures score lower than under the previous model" into a passing invariant. The test is also tied to the exact fitted constants, so any future refit, even an improvement that lifts the fixtures, fails the suite and forces an edit of magic numbers. The previous version asserted `shipped > frozen`, so the test direction was flipped to match the new outcome rather than to guard a property. The sibling assertion `shipped < FACEPALM_SCORE_MIN` has the same weakness: it will force a rewrite exactly when the product improves.

**Fix:** Drop the pinned numbers and the `shipped < previous` assertion. Keep the twin-versus-SQL agreement, which is the actual regression guard. If the fixtures are meant as a tracked benchmark, move them to a report line, as the fit script already does for commented rows, instead of a unit test.

## Info

### IN-01: Test name no longer matches what it asserts

**File:** `tests/services/test_maia_flaw_scoring.py:2073-2087`

**Issue:** `test_best_move_missing_keeps_loss_only_score` now asserts `score.scores_set == 0`. The row is unscored under `best_prob_for_misses`, so the name says the opposite of the assertion.

**Fix:** Rename to something like `test_best_move_missing_leaves_a_pure_miss_unscored`.

### IN-02: Wrong comment and a vacuous `first_stable` branch in the fractional-mean gate test

**File:** `tests/services/test_facepalm_score.py:687-706`

**Issue:** The comment says a one-pawn loss at depth 1 "discounts to 1 under first_stable". For `_odd_array(-1, 0, 0, 0, 0)` the first stable pair is `(0, 0)` at index 1, so `first_stable` returns 0 and the row does not lose material. The `if material_input == "decaying_mean":` guard means the parametrized `first_stable` case only runs the `constant` rows. The fractional gate behaviour of `first_stable` is therefore untested, and the comment is wrong.

**Fix:** Fix the comment. Add an explicit `first_stable` fractional-loss case, for example loss 1 at depth 3 only, which discounts to 0.5, with the gate-1.0 versus gate-None expectations.

### IN-03: Pure-miss rows without `maia_best_prob` silently become unscored; the impact is not quantified

**File:** `app/services/facepalm_score.py:368-380`, `:516-527`

**Issue:** The D-04 / 254 WR-01 change means every no-loss row whose `maia_best_prob` is NULL (best move missing, or not yet backfilled) now drops out of the drill and the library entirely. Before this phase it scored as if the best move were likely. The tests were updated to seed `maia_best_prob` everywhere, which confirms the behaviour change is wide. Nothing in the phase measures how many production flaws this affects (`facepalm-expression-prod-check.md` predates it).

**Fix:** Run one read-only prod count (`maia_best_prob IS NULL` among scored-before / unscored-now pure-miss blunders) and put the figure in the phase summary or the changelog entry.

### IN-04: Fit report mixes depth-3 bookkeeping with aggregate-input results

**File:** `scripts/blunder_check/fit_facepalm.py:1872-1878`, `:2188-2217`

**Issue:** `_row_material_type`, `_best_line_null` and the D-13 "by material type" and "pure-miss pass rate" tables classify rows by depth-3 material only, while the chosen model scores the aggregated lines. For `decaying_mean` a row labelled "neither" or "misses" by depth 3 can be a positive loss in the score. The tables are labelled information-only, but they describe a different partition than the one the model uses.

**Fix:** Add a one-line note in the report that the types are depth-3 types, or classify with `loses(loss, gate)` under the chosen spec.

### IN-05: `fit_facepalm.py` is a 2,569-line module with stale prose and inconsistent boundaries

**File:** `scripts/blunder_check/fit_facepalm.py:1-28`, `:940-960`, `:1207-1266`, `:2010-2014`

**Issue:**
- The module docstring still describes only the legacy and Phase 254 schemas. It says nothing about material inputs, the set-8 hold-out or `--material-input`.
- `choose_loss_floor` ties on `<` AUC_TIE_TOLERANCE while `choose_candidate` and `choose_material_input` tie on `<=`, so the same tolerance is applied inconsistently.
- `SET_EIGHT_SIZE_NOTE` hard-codes "about 55 decided rows" (the table has 58).
- Imports are out of order (`scripts.blunder_check.metrics` before `app.services.*`).

**Fix:** Update the docstring, unify the tie boundary or comment why they differ, derive the row count in the note from the data, and consider splitting the module (loading and design, selection, report).

---

_Reviewed: 2026-11-16_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
