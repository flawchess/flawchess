---
phase: 256-facepalm-refit-material-aggregated-over-depths
verified: 2026-11-16T23:10:00Z
status: passed
score: 7/7 must-haves verified
covered_files:
  - ".planning/phases/256-facepalm-refit-material-aggregated-over-depths/256-01-PLAN.md"
  - ".planning/phases/256-facepalm-refit-material-aggregated-over-depths/256-01-SUMMARY.md"
  - ".planning/phases/256-facepalm-refit-material-aggregated-over-depths/256-02-PLAN.md"
  - ".planning/phases/256-facepalm-refit-material-aggregated-over-depths/256-02-SUMMARY.md"
  - ".planning/phases/256-facepalm-refit-material-aggregated-over-depths/256-03-PLAN.md"
  - ".planning/phases/256-facepalm-refit-material-aggregated-over-depths/256-03-SUMMARY.md"
  - ".planning/phases/256-facepalm-refit-material-aggregated-over-depths/256-04-PLAN.md"
  - ".planning/phases/256-facepalm-refit-material-aggregated-over-depths/256-04-SUMMARY.md"
  - ".planning/phases/256-facepalm-refit-material-aggregated-over-depths/256-05-PLAN.md"
  - ".planning/phases/256-facepalm-refit-material-aggregated-over-depths/256-05-SUMMARY.md"
  - ".planning/phases/256-facepalm-refit-material-aggregated-over-depths/256-06-PLAN.md"
  - ".planning/phases/256-facepalm-refit-material-aggregated-over-depths/256-06-SUMMARY.md"
  - ".planning/phases/256-facepalm-refit-material-aggregated-over-depths/256-07-PLAN.md"
  - ".planning/phases/256-facepalm-refit-material-aggregated-over-depths/256-07-SUMMARY.md"
  - ".planning/phases/256-facepalm-refit-material-aggregated-over-depths/256-08-PLAN.md"
  - ".planning/phases/256-facepalm-refit-material-aggregated-over-depths/256-08-SUMMARY.md"
  - "CHANGELOG.md"
  - "app/services/blunder_check_rules.py"
  - "app/services/facepalm_material.py"
  - "app/services/facepalm_score.py"
  - "app/services/maia_flaw_scoring.py"
  - "reports/blunder-check/facepalm-features-2026-11-16.tsv"
  - "reports/blunder-check/facepalm-fit-2026-11-16.md"
  - "scripts/blunder_check/decaying_mean.py"
  - "scripts/blunder_check/fit_facepalm.py"
  - "scripts/blunder_check/sample.py"
  - "tests/scripts/test_fit_facepalm.py"
  - "tests/services/test_facepalm_score.py"
covered_digest: "v4:sha256:7eec03ea51d3e502d52a4c0b4691f6afb05e8d9ac3070e914fa4355637f312ce"
behavior_unverified: 0
overrides_applied: 0
advisory:
  - finding: "WR-01 (review): loss gate None is hair-trigger under the decaying mean; a one-pawn loss at depth 9 alone flips a pure miss from 0.003 to 0.773 (reproduced)"
    category: other
    reason: "Gate chosen by the fit (D-11) and confirmed by the owner; real model discontinuity, rare in practice. Follow-up: ship gate 1.0 or gate on the depth-3 loss"
    evidence_status: "reproduced with the shipped twin"
  - finding: "WR-02 (review): on the blind set 8 depth_3 beats the shipped decaying_mean (AUC 0.835 vs 0.821; at 0.5, 11 vs 5 unfair among passers per review)"
    category: other
    reason: "Flagged by the report as a D-08 disagreement and settled by the owner for the CV choice with the numbers in front of them (256-07-SUMMARY). Accepted trade-off, not a defect"
    evidence_status: "report lines 41-55 of facepalm-fit-2026-11-16.md"
  - finding: "WR-03 (review): owner-fixture test pins refit-specific numbers and the direction 'shipped < previous'"
    category: other
    reason: "Test brittleness; the twin parity guard it carries stays valid. Follow-up"
    evidence_status: "tests/services/test_facepalm_owner_fixtures.py"
---

# Phase 256: Facepalm Refit on Material Aggregated over Depths Verification Report

**Phase Goal:** Replace the depth-3-only material inputs of the facepalm score (loss of the played line, missed gain of the best line) with an aggregate over the stored odd depths 1, 3, 5, 7, 9; refit on label sets 1 to 8 and release new constants. Candidates: decaying mean, first stable value (discounted by onset), depth 3 reference. No backfill, no new stored facts; score stays a query-time expression in both twins.
**Verified:** 2026-11-16
**Status:** passed (with three advisory warnings from the code review, none of which negates the goal)
**Re-verification:** No, initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Both score twins compute the chosen aggregate from the stored 9-slot arrays; no new column, no backfill | VERIFIED | `app/services/facepalm_material.py` (new, 341 lines) holds Python and SQL builders (`decaying_mean`/`_sql`, `first_stable`/`_sql`, `loss_by_depth`/`_sql`, `gain_by_depth`/`_sql`, `loses`/`_sql`), unrolled over depths 1,3,5,7,9. `facepalm_score.py` `material_loss`/`material_missed` and `_loss_sql`/`_missed_sql` dispatch on `model.material_input`. `facepalm_expr` binds `GameFlaw.played_line_material` / `best_line_material` (facepalm_score.py:604-606). The diff vs merge-base touches no `alembic/` and no `frontend/src/`; `app/models/game_flaw.py` is untouched by this phase (its diff to `main` is main's newer work, not this branch). |
| 2 | Python and SQL twins stay in parity and are pinned by tests | VERIFIED | `test_sql_twin_parity_every_shape`, `test_sql_twin_parity_aggregate_inputs`, `test_loss_gate_*`, `test_aggregate_inputs_leave_the_same_rows_unscored` against dev Postgres. I ran the five phase test modules: 465 passed. The reviewer's independent 100,800-row randomized fuzz found 0 mismatches. |
| 3 | The fit compares the three candidates (decaying mean, first stable, depth 3) inside the full model, by repeated CV over sets 1-8, with the set-8 hold-out, and states its choice | VERIFIED | `reports/blunder-check/facepalm-fit-2026-11-16.md` "Material input" table: decaying_mean CV AUC 0.902 (spread 0.006), first_stable 0.877, depth_3 0.879; set-8 hold-out columns present; "Chosen input: decaying_mean", D-08 disagreement flagged in the report. Each input runs the whole staged pipeline (stage 1 material form, stage 2 spread form and gate, stage 3b pre-spread), satisfying D-14. |
| 4 | New `FACEPALM_*` constants released and reproduce from the committed features TSV | VERIFIED | `blunder_check_rules.py`: INTERCEPT -1.2172, PLAYED -0.6083, SPREAD -0.3617, LOSS 1.1643, MISSED_COEF 0.3538 (was 0.0891), MISSED_FLOOR 0, BEST_PROB 1.9618, `FACEPALM_MATERIAL_INPUT = "decaying_mean"`, `FACEPALM_LOSS_GATE = None`, `FACEPALM_SCORE_MIN = 0.5`. I ran `fit_facepalm.py --features ...2026-11-16.tsv --labels ... --check-constants`: "constants match: the shipped FACEPALM_MODEL is the refit of this features table", exit 0. `test_shipped_constants_reproduce_from_the_refit_features` runs the same without monkeypatching. |
| 5 | WR-01 (254) fixed: a no-loss row with NULL `maia_best_prob` is unscored in both twins; WR-03 fixed in the fit (spread-form aware exclusion, counted in the report) | VERIFIED | `_pure_miss_term` returns None when best_prob is None (facepalm_score.py:368-380) and `_pure_miss_sql` mirrors it; tests `test_pure_miss_without_best_prob_is_unscored`, `test_losing_row_without_best_prob_keeps_its_score`, `test_expr_unscores_pure_miss_without_best_prob`. Fit: `_spec_exclusion` (fit_facepalm.py:443) per candidate; report "Data" section lists per-form excluded counts and "rows that qualify only under a gated form: 0"; tests `test_spec_exclusion_*`. |
| 6 | Owner checkpoint held: input and `FACEPALM_SCORE_MIN` set by the owner; D-13 information shown | VERIFIED | 256-07-SUMMARY records the verbatim owner reply `input=decaying_mean (cv choice), FACEPALM_SCORE_MIN=0.5` after the cut table, set-8 hold-out and the D-08 disagreement were shown. Fit report "Owner checks" has the 15+ commented set-7/8 rows with old and new scores, pure-miss pass rate at each cut, and Window 14 handling. Window 14 (game 2099808 ply 23) is unscored (played line one ply long), so it stays below the cut; pinned by a test in `test_facepalm_score.py`. Owner fixtures score 0.0632 / 0.1044, still below the cut and reported honestly (lower than the old 0.146 / 0.154). |
| 7 | Released as a normal constants and code release with a changelog bullet; no migration, no backfill | VERIFIED | `CHANGELOG.md` `[Unreleased]` / Changed carries the facepalm refit bullet naming the score change and the WR-01 unscoring. No alembic or frontend diff. |

**Score:** 7/7 truths verified (0 present, behavior-unverified)

### Decision coverage D-01 to D-15

| Decision | Plan(s) | Status | Evidence |
|---|---|---|---|
| D-01 labels gate | 07 | SATISFIED | 60 set-8 rows labelled and committed before the run (07-SUMMARY, gate exit 0); `facepalm-labels.tsv` has 60 rows for n 241-300 |
| D-02 no wait for 252 | 07 | SATISFIED | 07-SUMMARY documents 252's repair not yet run; features pulled as-is |
| D-03 depth 3 still required | 01, 03 | SATISFIED | `material_loss`/`_loss_sql` return None when depth-3 slot is NULL and no mate within LINE_DEPTH; `test_aggregate_inputs_leave_the_same_rows_unscored` |
| D-04 no-loss + NULL best_prob unscored | 03 | SATISFIED | see truth 5 |
| D-05 fit excludes such rows and counts them | 04 | SATISFIED | `_spec_exclusion`, report "Data" section |
| D-06 three candidates, same input for loss and gain | 01-05 | SATISFIED | `MaterialInput = Literal[depth_3, decaying_mean, first_stable]`; one input applies to loss and gain |
| D-07 repeated CV on seed means, existing criteria | 05 | SATISFIED | report: 5 seeds, CV AUC then fair share |
| D-08 set-8 hold-out, disagreement flagged | 06, 07 | SATISFIED | report "Material input" + "Sets 1-7 vs set 8"; disagreement flagged and escalated to owner |
| D-09 mean wins ties vs depth 3 | 05 | SATISFIED | tie rule in `choose_material_input`; here the mean won on CV outright (0.902 vs 0.879) |
| D-10 final constants on all eight sets | 05, 08 | SATISFIED | features include all 290 label rows; `--check-constants` reproduces |
| D-11 loss gate by the fit, one named constant for both twins | 01, 03, 07, 08 | SATISFIED | `FACEPALM_LOSS_GATE`, `loses`/`loses_sql`; fit compared None vs 1, chose None (see advisory WR-01) |
| D-12 WR-03 spread-form aware exclusion | 04 | SATISFIED | see truth 5 |
| D-13 one blocking owner checkpoint with the listed information | 02, 05, 06, 07, 08 | SATISFIED | see truth 6 |
| D-14 material-form, spread-form, optional-input stages re-run | 04, 05 | SATISFIED | stage 1 / 2 / 3b sections per input in the report |
| D-15 normal release, changelog bullet, no migration | 08 | SATISFIED | see truth 7 |

All 15 decisions are claimed by at least one plan's `requirements:` frontmatter (01: D-03 D-06 D-11; 02: D-06 D-13; 03: D-03 D-04 D-06 D-11; 04: D-05 D-06 D-11 D-12 D-14; 05: D-06 D-07 D-09 D-10 D-13 D-14; 06: D-08 D-13; 07: D-01 D-02 D-07 D-08 D-11 D-13; 08: D-10 D-11 D-13 D-15). No orphaned decision.

### Required Artifacts

| Artifact | Status | Details |
|---|---|---|
| `app/services/facepalm_material.py` | VERIFIED | substantive, imported by `facepalm_score.py`, tested |
| `app/services/facepalm_score.py` | VERIFIED | model carries `material_input` and `loss_gate`; both twins |
| `app/services/blunder_check_rules.py` | VERIFIED | new constants, `MATERIAL_DECAY_RATIO = 0.5` |
| `scripts/blunder_check/fit_facepalm.py` | VERIFIED | staged per input, hold-out, owner section, `--check-constants` |
| `reports/blunder-check/facepalm-features-2026-11-16.tsv`, `facepalm-fit-2026-11-16.md`, calibration and spot-check reports | VERIFIED | all four committed |
| `CHANGELOG.md` bullet | VERIFIED | present |

### Key Link Verification

| From | To | Status |
|---|---|---|
| `facepalm_expr` | `GameFlaw.played_line_material` / `best_line_material` | WIRED (facepalm_score.py:604-606) |
| `maia_flaw_scoring.py` writer | arrays + scoring path (`played_material=row["played_line_material"]`) | WIRED |
| shipped `FACEPALM_MODEL` | refit of committed features | WIRED (`--check-constants` exit 0, run by me) |
| fit script | app twins (shared `facepalm_material` implementation, sampler shares the mean) | WIRED |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|---|---|---|---|
| Phase test modules | `pytest tests/services/test_facepalm_score.py test_facepalm_material.py test_facepalm_owner_fixtures.py tests/scripts/test_fit_facepalm.py test_decaying_mean.py -n auto` | 465 passed | PASS |
| Constants reproduce | `fit_facepalm.py ... --check-constants` | match, exit 0 | PASS |
| Gate discontinuity (review WR-01) | `facepalm_score` with played `[0]*9` vs `[0]*8+[-1]` | 0.0031 vs 0.7727 | reproduced (advisory) |

Orchestrator ran `ty check` clean and the full suite (6958 passed, 19 skipped) after wave 8; I did not re-run those.

### Anti-Patterns Found

No TBD/FIXME/XXX debt markers or stubs found in the new modules in the checks run; no blockers.

### Review warnings, judged against the goal

- **WR-01 (gate None, hair-trigger):** real behaviour, reproduced. It does not negate the goal: the gate was an explicit fit-decided choice (D-11), the owner approved the fitted model, and in-sample AUC/fair share under the shipped gate are as reported. It is a quality risk for rows with a late tiny loss, so follow-up material (ship gate 1.0 or gate on the depth-3 loss).
- **WR-02 (set-8 prefers depth_3):** the D-08 mechanism worked as designed: the disagreement was flagged, the numbers were shown, and the owner chose the CV input knowingly. Accepted owner trade-off, not a goal failure. The set-8 comparison is on 58 rows, which the report itself says is noisy.
- **WR-03 (brittle owner-fixture test):** test hygiene only. Follow-up.
- Info items IN-01 to IN-05 (misnamed test, vacuous branch and wrong comment, no prod count for the WR-01 unscoring, depth-3-based report tables, oversized fit module) do not affect the goal.

### Human Verification Required

None open. The owner checkpoint (the only human-gated item of the phase) was completed in this run.

### Notes for the integrator (not gaps)

- `main` has advanced since the branch base (opponent-blunder Maia work). `git merge-tree` shows the only textual conflict is `.planning/STATE.md`; `maia_flaw_scoring.py`, `CHANGELOG.md` and two test files auto-merge. The full pre-merge gate should be re-run on the merged tree, since auto-merge of `maia_flaw_scoring.py` and its tests is the part most likely to interact with WR-01 (D-04).
- 07-SUMMARY notes one unidentified test that failed once after wave 3 and passed on reruns; it has not recurred.
- Phase 252's line repair has not run on prod, so prod scores will shift again when it does (D-02 accepts this; no re-run planned).

### Gaps Summary

No gaps. All 15 decisions are covered, the aggregate input is implemented in both twins with parity tests, the fit compares the three candidates with a hold-out, the owner's decision is recorded, and the shipped constants reproduce from the committed features table.

---

_Verified: 2026-11-16_
_Verifier: Claude (gsd-verifier)_
