---
phase: 259-facepalm-first-principles-refit
verified: 2026-11-22T16:00:00Z
status: passed
score: 18/18 decisions verified
covered_files:
  - ".planning/phases/259-facepalm-first-principles-refit/259-01-PLAN.md"
  - ".planning/phases/259-facepalm-first-principles-refit/259-01-SUMMARY.md"
  - ".planning/phases/259-facepalm-first-principles-refit/259-02-PLAN.md"
  - ".planning/phases/259-facepalm-first-principles-refit/259-02-SUMMARY.md"
  - ".planning/phases/259-facepalm-first-principles-refit/259-03-PLAN.md"
  - ".planning/phases/259-facepalm-first-principles-refit/259-03-SUMMARY.md"
  - ".planning/phases/259-facepalm-first-principles-refit/259-04-PLAN.md"
  - ".planning/phases/259-facepalm-first-principles-refit/259-04-SUMMARY.md"
  - ".planning/phases/259-facepalm-first-principles-refit/259-05-PLAN.md"
  - ".planning/phases/259-facepalm-first-principles-refit/259-05-SUMMARY.md"
  - ".planning/phases/259-facepalm-first-principles-refit/259-06-PLAN.md"
  - ".planning/phases/259-facepalm-first-principles-refit/259-06-SUMMARY.md"
  - ".planning/phases/259-facepalm-first-principles-refit/259-07-PLAN.md"
  - ".planning/phases/259-facepalm-first-principles-refit/259-07-SUMMARY.md"
  - ".planning/phases/259-facepalm-first-principles-refit/259-08-PLAN.md"
  - ".planning/phases/259-facepalm-first-principles-refit/259-08-SUMMARY.md"
  - ".planning/phases/259-facepalm-first-principles-refit/259-09-PLAN.md"
  - ".planning/phases/259-facepalm-first-principles-refit/259-09-SUMMARY.md"
  - ".planning/phases/259-facepalm-first-principles-refit/259-10-PLAN.md"
  - ".planning/phases/259-facepalm-first-principles-refit/259-10-SUMMARY.md"
  - ".planning/phases/259-facepalm-first-principles-refit/259-11-PLAN.md"
  - ".planning/phases/259-facepalm-first-principles-refit/259-11-SUMMARY.md"
  - ".planning/phases/259-facepalm-first-principles-refit/259-12-PLAN.md"
  - ".planning/phases/259-facepalm-first-principles-refit/259-12-SUMMARY.md"
  - ".planning/phases/259-facepalm-first-principles-refit/259-13-PLAN.md"
  - ".planning/phases/259-facepalm-first-principles-refit/259-13-SUMMARY.md"
  - ".planning/phases/259-facepalm-first-principles-refit/259-14-PLAN.md"
  - ".planning/phases/259-facepalm-first-principles-refit/259-14-SUMMARY.md"
  - ".planning/phases/259-facepalm-first-principles-refit/259-15-PLAN.md"
  - ".planning/phases/259-facepalm-first-principles-refit/259-15-SUMMARY.md"
  - "alembic/versions/20261122_120000_d1e5f7a9c259_phase_259_facepalm_scalars.py"
  - "alembic/versions/20261122_130000_d2a6c8e0f259_phase_259_facepalm_reply_stamp.py"
  - "alembic/versions/20261124_120000_e2f6a8b0d259_phase_259_ix_game_flaws_facepalm_inputs.py"
  - "alembic/versions/20261128_120000_f3a7b9c1e259_phase_259_drop_material_arrays.py"
  - "app/models/game.py"
  - "app/models/game_flaw.py"
  - "app/repositories/game_flaws_repository.py"
  - "app/repositories/library_repository.py"
  - "app/services/blunder_check_rules.py"
  - "app/services/facepalm_inputs.py"
  - "app/services/facepalm_material.py"
  - "app/services/facepalm_score.py"
  - "app/services/line_material.py"
  - "app/services/maia_flaw_scoring.py"
  - "app/services/maia_flaw_stats.py"
  - "reports/blunder-check/facepalm-features-2026-11-22.tsv"
  - "reports/blunder-check/facepalm-fit-2026-11-22.md"
  - "scripts/backfill_maia_flaws.py"
  - "scripts/blunder_check/decaying_mean.py"
  - "scripts/blunder_check/facepalm_features.py"
  - "scripts/blunder_check/fit_facepalm.py"
  - "scripts/blunder_check/miss_labels.py"
  - "scripts/blunder_check/render.py"
  - "scripts/build_facepalm_inputs_index.py"
covered_digest: "v4:sha256:dd9458e327c55641fddcbb7686bf315f34b6d147844ed1696c7b3f42bb06af5c"
behavior_unverified: 0
overrides_applied: 0
re_verification:
  previous_status: passed
  previous_score: 18/18
  gaps_closed: []
  gaps_remaining: []
  regressions: []
---

# Phase 259: Facepalm Score Refit on First Principles Verification Report

**Phase Goal:** Make the facepalm score read what a human would read from the lines, then refit it: a quiet-point material rule (an even exchange of any length is neutral), two stored scalars `loss` / `missed` replacing the 9-slot arrays, and a stored best-reply probability replacing the reply spread in the model. Found on prod game 2883555 ply 47.
**Verified:** 2026-11-22
**Status:** passed
**Re-verification:** Yes. The first report (status passed, 18/18) went stale when commit `a4a3932fa` ("one stored material rule", review WR-03 and IN-01) changed covered files. This run re-checked every decision against the current tree, with the focus on D-02 to D-05, D-08, D-12, D-13 and D-15.

There is no REQUIREMENTS.md; the phase is keyed by decisions D-01 to D-18 in 259-CONTEXT.md. Each decision is one must-have truth below.

## What the refactor changed, and what it did not

`a4a3932fa` touched 13 files. I read the whole diff.

- `material_loss` / `material_missed` (`app/services/facepalm_score.py`) lost the `material_input` parameter. Both always return the decaying mean over `loss_by_depth` / `gain_by_depth`. The mate short-circuit (`mate_ply <= LINE_DEPTH` gives `MATE_LOSS` / `missed_mate`) and the unknown depth-3 gate (`None` for loss, `0.0` for missed) are unchanged.
- Deleted: `first_stable`, `aggregate`, `AggregateInput`, `loss_feature`, `missed_feature`, `MaterialInput`, `STORED_MATERIAL_INPUT`. A grep over `app scripts tests frontend/src analysis` finds zero remaining references to any of them, nor to `material_input=`.
- `app/services/line_material.py` (the quiet walk, D-02) changed docstrings and a comment only. `_quiet_walk_end`, `_ends_in_exchange`, `_best_recapture` are untouched.
- The score twins (`facepalm_score`, `facepalm_score_sql`, `_key_move_term`) are untouched. `_key_move_term` still uses the reply term when `loss > 0` and the best-move term otherwise (D-08).
- `render.py`, `decaying_mean.py`, `miss_labels.py`, `backfill_maia_flaws.py` and the docstrings changed text only. This closes the three Info/Warning items the first report listed (stale `render.py` prose, IN-01 docstrings, WR-03 unused generality). `259-REVIEW-DISPOSITION.md` marks WR-01, WR-02, WR-03, IN-01 and IN-02 all fixed.

The stored write path before and after is the same function of the same inputs. The mean was already the only path the write-time hook used (`facepalm_inputs.material_inputs_from_facts` passed `decaying_mean`). So the refactor is a deletion of unreachable branches, not a behavior change. This matches the operator fact that all 291 stored rows recompute identically, and I confirmed the same through the checks below.

## Goal Achievement

### Observable Truths (one per decision)

| # | Decision | Status | Evidence |
|---|----------|--------|----------|
| D-01 | First principles decide, AUC only a range check | VERIFIED | `fit_facepalm.py` fixes the shape and fits only the coefficients; alternatives are "information only" in `reports/blunder-check/facepalm-fit-2026-11-22.md`. Untouched by the refactor. |
| D-02 | Every depth read at a quiet point, any capture square, static exchange when the line stops inside an exchange | VERIFIED | `app/services/line_material.py` quiet walk unchanged in code (diff is docstring and comment only). `tests/services/test_line_material.py` passes in this run (1087 passed across the phase test set). The first verification's mutation (quiet walk reduced to depth-only makes the tests fail) still applies since the code is byte-identical outside comments. |
| D-03 | Decaying mean over odd depths 1,3,5,7,9 for loss and missed | VERIFIED | `LINE_LOSS_DEPTHS = (1,3,5,7,9)`; `material_loss` and `material_missed` now call `decaying_mean(loss_by_depth(...))` / `decaying_mean(gain_by_depth(...))` unconditionally (read at `facepalm_score.py` lines 150-205). `STORED_MATERIAL_INPUT` is gone because there is no alternative left to select. The decaying mean is the only code path. |
| D-04 | Decay ratio 1/2, fixed | VERIFIED | `MATERIAL_DECAY_RATIO: float = 0.5` (`blunder_check_rules.py:108`), comment says fixed by the owner, not fitted. Mutation: I set it to 0.4, and `test_write_time_material_rule_is_pinned` and `test_d13_missed_gain_is_zero_under_the_quiet_rule` among 12 tests failed. I restored it to 0.5; `git status` is clean. |
| D-05 | Two scalar columns on `game_flaws`, computed in Python at write time; SQL aggregation twins gone | VERIFIED | `GameFlaw.material_loss` / `material_missed`; `facepalm_inputs.facepalm_material_inputs` / `material_inputs_from_facts` call `material_loss` / `material_missed` with the signature that no longer takes `material_input`; `maia_flaw_scoring._facepalm_values` feeds them to the row writers. Callers all match the new signature (ty clean over `app tests scripts`). No `_sql` aggregation builders in `facepalm_material.py`. |
| D-06 | Array drop is the last, human-gated step | VERIFIED | Migration `f3a7b9c1e259` drops both arrays, their CHECKs and `ix_game_flaws_blunder_facts`; `alembic heads` = `f3a7b9c1e259 (head)`. grep for `played_line_material` / `best_line_material` over app, scripts, tests, frontend/src: 0 hits. Owner decision "drop-now" in 259-15-SUMMARY. |
| D-07 | New stored `maia_best_reply_prob`, blunderer's Elo, from the same post-blunder policy call | VERIFIED | `GameFlaw.maia_best_reply_prob`; `_reply_prob` in the hook reads the stored refutation line's first token from the policy of `_derive_reply_spread`; prod pass completed per the committed readiness reports (operator fact). |
| D-08 | Reply probability replaces the spread in the model on losing rows; spread stays stored, unread by the score | VERIFIED | `_key_move_term`: `loss > 0` gives the reply term, otherwise the best-move term; SQL twin is an explicit CASE with the NULL guard first. `maia_reply_spread` is still written (`maia_flaw_scoring.py:545`) and read by no score twin. `tests/services/test_facepalm_score.py` pins Python against SQL and passes after the refactor. |
| D-09 | Review report the owner confirms before the recompute is built | VERIFIED | `reports/blunder-check/quiet-rule-review-2026-11-21.md` (322 changed values by cause); owner "confirm-retire" recorded in 259-03-SUMMARY. Unchanged. |
| D-10 | Both sides' blunders, prod only; migration applies to the benchmark DB | VERIFIED | Readiness report: user and opponent blunders both carry the material inputs (about 2.21M each). Benchmark DB moved by migration only. Unchanged (operator fact, committed reports). |
| D-11 | New columns first, one switch, array drop later | VERIFIED | Releases #497, #498, #499 in that order, commits `c4cb1e699`, `03a935bf7`, `5904c9a61` on main. |
| D-12 | CV AUC within about 0.02 of the shipped-rule baseline | VERIFIED | Baseline 0.897 vs chosen shape 0.908, difference 0.012, in the committed fit report. I re-ran `fit_facepalm.py --features reports/blunder-check/facepalm-features-2026-11-22.tsv --out <scratch> --check-constants` on the current tree: prints "constants match: the app constants are the refit of this features table", exit 0. A diff of the regenerated report against the committed one differs only in the owner-comments table, which needs `--labels` that I did not pass; the chosen-shape section is identical. |
| D-13 | Fixture game 2883555 ply 47 has `missed = 0` | VERIFIED | I ran `facepalm_material_inputs` on `D13_FIXTURE` (FEN, played move, refutation line, best line) with the post-refactor code: `MaterialInputs(loss=2.935483870967742, missed=0.0)`. `tests/services/test_facepalm_inputs.py::test_d13_missed_gain_is_zero_under_the_quiet_rule` passes, and fails under the decay-ratio mutation, so the test bites. |
| D-14 | No new label set, sets 1-8 as they are | VERIFIED | `reports/blunder-check/facepalm-labels.tsv` last committed in `b2a66e3b7` (phase 256); no phase 259 commit touches it. |
| D-15 | One blocking owner checkpoint: model confirmed, SCORE_MIN and STATS_MIN set | VERIFIED | `FACEPALM_SCORE_MIN = 0.7` and `FACEPALM_STATS_MIN = 0.7` in `blunder_check_rules.py` (lines 64, 69) with the rationale comment. The coefficients reproduce from the committed features (D-12 check), so the cuts rest on the model the app runs. Owner decision recorded in 259-11-SUMMARY (operator fact). |
| D-16 | Normal release with a changelog bullet | VERIFIED | `CHANGELOG.md` has the user-facing Facepalm score bullets and the "Internal: removed the old per-depth material columns" bullet. Releases per operator facts. |
| D-17 | Covering partial index follows the inputs, built CONCURRENTLY before the switch; old index dropped with the array drop | VERIFIED | `ix_game_flaws_facepalm_inputs` in `app/models/game_flaw.py` and migration `e2f6a8b0d259`; the drop migration removes the old index. Build on prod is an operator fact in the readiness report. |
| D-18 | JIT re-measured, `disable_jit_for_transaction` kept only if numbers support it | VERIFIED | `reports/blunder-check/facepalm-jit-259.md` decision "keep"; `disable_jit_for_transaction` still defined and called in `library_repository.py` (lines 1679, 1720). |

**Score:** 18/18 decisions verified

### Required Artifacts / Key Links

| Artifact or link | Status | Details |
|---|---|---|
| `app/services/line_material.py` quiet walk | VERIFIED | Substantive, code unchanged by the refactor, called by `facepalm_inputs` |
| `app/services/facepalm_inputs.py` | VERIFIED | One write-time function, no `STORED_MATERIAL_INPUT`; used by the hook and the features script |
| `app/services/facepalm_score.py` | VERIFIED | `material_loss` / `material_missed` single-rule, Python/SQL score twins pinned by tests |
| `app/services/facepalm_material.py` | VERIFIED | `loss_by_depth`, `gain_by_depth`, `decaying_mean` only; `__all__` matches the module |
| `app/models/game_flaw.py` columns and index | VERIFIED | Scalars, reply prob, index; arrays removed; single alembic head |
| Hook to columns | WIRED | `_facepalm_values` and `_reply_prob` to the row writers; backfill modes line, reply, spread in `scripts/backfill_maia_flaws.py` |
| Score expression to readers | WIRED | `facepalm_expr` used by the library repository, blunder-check selection and stats |
| Constants to fit | WIRED | `--check-constants` reproduces the `FACEPALM_*` coefficients from the committed features TSV on the post-refactor tree |

### Data-Flow Trace (Level 4)

Score inputs flow from the stored scalar and reply-probability columns that the prod passes filled (about 2.21M user and 2.22M opponent blunders with `material_loss`, 4.42M of 4.73M with `maia_best_reply_prob`; operator facts from the committed readiness reports, not queried). The refactor changes no column, so the flow is unchanged. Status: FLOWING.

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|---|---|---|---|
| Fixture ply 47 gives `missed = 0` | `facepalm_material_inputs` on `D13_FIXTURE` | `loss=2.935, missed=0.0` | PASS |
| Constants reproduce from committed features | `fit_facepalm.py --features ...2026-11-22.tsv --out <scratch> --check-constants` | "constants match", exit 0 | PASS |
| Pinned rule bites | set `MATERIAL_DECAY_RATIO` to 0.4, run facepalm material/score/inputs tests | 12 failed; restored, `git status` clean | PASS |
| Phase test set | `uv run pytest -n auto` on test_facepalm_score, test_facepalm_material, test_facepalm_inputs, test_line_material, test_maia_flaw_scoring, test_maia_flaw_stats and `tests/scripts` | 1087 passed | PASS |
| Lint, format, types, nesting gate | `ruff check .`, `ruff format --check app tests scripts`, `ty check app/ tests/ scripts/`, `check_function_size.py app/ --fail-over-depth 4` | all clean (1667 functions, no breaches) | PASS |
| Single migration head | `alembic heads` | `f3a7b9c1e259 (head)` | PASS |

The full backend run on the post-refactor tree (6856 passed, 8 skipped) and the recompute of all 291 stored label rows are operator facts; I did not rerun the full suite.

### Probe Execution

No probe scripts declared by this phase. Step 7c: not applicable.

### Anti-Patterns Found

None. The three Info/Warning items of the first report are fixed by the refactor (stale `render.py` prose, IN-01 docstrings, WR-03 unused generality). No `TBD`/`FIXME`/`XXX` markers in the changed files that I scanned.

### Requirements Coverage

No REQUIREMENTS.md. All decisions D-01 to D-18 appear in the plans' `requirements:` frontmatter. No orphaned decisions.

### Human Verification Required

None for the phase goal. Two operator facts I could not observe independently, both documented in committed reports: the prod passes and release state, and the post-drop Sentry check deferred by 259-15-SUMMARY (an operational follow-up, not a phase truth). One deployment note: the refactor is on main but not deployed; prod runs the pre-refactor code, which computes the same stored values (the deleted branches were unreachable from the write path), so there is no behavior divergence to wait on.

### Gaps Summary

No gaps and no regressions. The refactor is a pure deletion of unreachable aggregate variants plus text fixes. The quiet walk, the decaying-mean rule, the decay ratio, the scalar columns, the reply-probability key-move term, the D-13 fixture, the constants reproducibility and the 0.7 cuts all still hold on the current tree, and the tests that guard them still fail when the rule is perturbed.

---

_Verified: 2026-11-22_
_Verifier: Claude (gsd-verifier)_
