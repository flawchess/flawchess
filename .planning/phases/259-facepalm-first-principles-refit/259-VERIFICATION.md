---
phase: 259-facepalm-first-principles-refit
verified: 2026-11-22T15:00:00Z
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
  - "scripts/blunder_check/facepalm_features.py"
  - "scripts/blunder_check/fit_facepalm.py"
  - "scripts/blunder_check/miss_labels.py"
  - "scripts/build_facepalm_inputs_index.py"
covered_digest: "v4:sha256:89c77f3bbc4f7d8fbbdd9147e13f6c8beeb2ac90b10470ad8cc46c5aa1cb1ddb"
behavior_unverified: 0
overrides_applied: 0
---

# Phase 259: Facepalm Score Refit on First Principles Verification Report

**Phase Goal:** Make the facepalm score read what a human would read from the lines, then refit it: a quiet-point material rule (an even exchange of any length is neutral), two stored scalars `loss` / `missed` replacing the 9-slot arrays, and a stored best-reply probability replacing the reply spread in the model. Found on prod game 2883555 ply 47.
**Verified:** 2026-11-22
**Status:** passed
**Re-verification:** No, initial verification

There is no REQUIREMENTS.md; the phase is keyed by decisions D-01 to D-18 in 259-CONTEXT.md. Each decision is one must-have truth below.

## Goal Achievement

### Observable Truths (one per decision)

| # | Decision | Status | Evidence |
|---|----------|--------|----------|
| D-01 | First principles decide, AUC only a range check | VERIFIED | `fit_facepalm.py` fixes the shape ("Fixed by first principles (D-01, D-03, D-08), only the coefficients are fitted"); alternatives are listed "information only" in `reports/blunder-check/facepalm-fit-2026-11-22.md`. |
| D-02 | Every depth read at a quiet point, any capture square, static exchange when the line stops inside an exchange | VERIFIED | `app/services/line_material.py`: `_quiet_walk_end` (depth plies, then while the next step captures), `_ends_in_exchange` plus `_best_recapture` settle in `_quiet_loss`; desperado rule shared via `_count_step`. I monkeypatched `_quiet_walk_end` to depth-only and `tests/services/test_line_material.py` fails (n13), so the tests bite. |
| D-03 | Decaying mean over odd depths 1,3,5,7,9 for loss and missed | VERIFIED | `facepalm_inputs.STORED_MATERIAL_INPUT = "decaying_mean"`; `LINE_LOSS_DEPTHS = (1,3,5,7,9)`; `material_loss` / `material_missed` aggregate through `aggregate`. |
| D-04 | Decay ratio 1/2, fixed | VERIFIED | `MATERIAL_DECAY_RATIO = 0.5` in `blunder_check_rules.py`; not among the fitted constants. |
| D-05 | Two scalar columns on `game_flaws`, computed in Python at write time; SQL aggregation twins gone | VERIFIED | `GameFlaw.material_loss` / `material_missed` (REAL, pair-NULL CHECK, non-negative CHECKs); written by `_facepalm_values` through `material_inputs_from_facts` (`maia_flaw_scoring.py:548`); `facepalm_material.py` has no `_sql` builders; score SQL reads scalars only (`_game_flaw_columns`). |
| D-06 | Array drop is the last, human-gated step | VERIFIED | Migration `f3a7b9c1e259` drops both arrays, their shape CHECKs and `ix_game_flaws_blunder_facts`; `alembic heads` = `f3a7b9c1e259`. `grep played_line_material|best_line_material` over app, scripts, tests, frontend/src: 0 hits. Owner decision "drop-now" recorded in 259-15-SUMMARY. |
| D-07 | New stored `maia_best_reply_prob`, blunderer's Elo, from the same post-blunder policy call | VERIFIED | `GameFlaw.maia_best_reply_prob`; `_reply_prob` reads the first token of the stored refutation line from the policy computed by `_derive_reply_spread` at the mover's pinned Elo, no extra inference. Reply pass on prod completed (readiness report: `reply_pending_games=0`, 4,418,658 of 4,729,767 blunders carry it, residue on losing rows 0). |
| D-08 | Reply probability replaces the spread in the model on losing rows; spread column stays stored, unread by the score | VERIFIED | `facepalm_score._key_move_term`: reply term when `loss > 0`, best-move term otherwise; the score twins have no spread input. `maia_reply_spread` is still written (`maia_flaw_scoring.py:545`). Python and SQL twins pinned by `tests/services/test_facepalm_score.py` (passes). Note: the key-move term switches on `loss > 0` (the fit's "loses material" shape), not on the facepalm type; this is the shape the fit report and owner confirmed. |
| D-09 | Review report the owner confirms before the recompute is built | VERIFIED | `reports/blunder-check/quiet-rule-review-2026-11-21.md` groups 322 changed values by cause (279 longer exchange, 43 settled at line end, 0 other, 0 drift), lists before/after rows with analysis links; owner option "confirm-retire" recorded in 259-03-SUMMARY, and plans 04 onward came after it. |
| D-10 | Both sides' blunders, prod only; migration applies to the benchmark DB | VERIFIED | Line pass reports `user_blunders_with_material_inputs` and `opponent_blunders_with_material_inputs` both about 2.21M of about 2.36M each (readiness report). Benchmark DB moved to head by migration only (259-06, 259-15 SUMMARYs), no benchmark backfill, as D-10 requires. |
| D-11 | New columns first, one switch, array drop later | VERIFIED | Three prod releases in this order: R1 (#497, `d75996143`, columns plus hook plus passes), switch (#498, `8e90f094`), drop (#499, `59e1edcb`); commits `c4cb1e699`, `03a935bf7`, `5904c9a61` on main. Operator runs were sequential (reports). |
| D-12 | CV AUC within about 0.02 of the shipped-rule baseline | VERIFIED | Re-measured baseline 0.897; chosen shape 0.908 (5-seed mean, spread 0.006), difference 0.012, "within range" in the fit report. I re-ran `fit_facepalm.py --check-constants` on the committed features TSV: `constants match`, exit 0, chosen-shape section identical to the committed report. |
| D-13 | Fixture game 2883555 ply 47 has `missed = 0` | VERIFIED | `D13_FIXTURE` pinned in `tests/services/line_material_fixtures.py`. I ran `facepalm_material_inputs` on the fixture's FEN and lines directly: `loss=2.935, missed=0.0`. The fit report shows its new score 0.825 (reported, not gated). |
| D-14 | No new label set, sets 1-8 as they are | VERIFIED | `reports/blunder-check/facepalm-labels.tsv` has no commits since the phase was added (`git log f878aeb4c..HEAD`: empty); fit uses 268 usable rows as in the spike. |
| D-15 | One blocking owner checkpoint: model confirmed, SCORE_MIN and STATS_MIN set | VERIFIED | Owner decision 2026-11-22 recorded in 259-11-SUMMARY; `FACEPALM_SCORE_MIN = 0.7`, `FACEPALM_STATS_MIN = 0.7` in `blunder_check_rules.py` with the rationale comment; fair/unfair table at cuts 0.50 to 0.70 and drill pool size (about 33% of user blunders, median 414 windows) present in the fit and calibration reports. Frontend `FACEPALM_HIGH_CUTOFF = 70` consistent. |
| D-16 | Normal release with a changelog bullet | VERIFIED | `CHANGELOG.md` has the user-facing bullet ("Facepalm score: refitted on how a player reads the lines...") plus the two internal bullets; releases #497, #498, #499 live per the operator facts and the 259-06/12/15 SUMMARYs. |
| D-17 | Covering partial index follows the inputs, built CONCURRENTLY before the switch; old index dropped with the array drop | VERIFIED | Model and migration `e2f6a8b0d259` define `ix_game_flaws_facepalm_inputs (user_id, game_id) INCLUDE (ply, maia_played_prob, material_loss, material_missed, maia_best_prob, maia_best_reply_prob) WHERE severity = 2`; built via `scripts/build_facepalm_inputs_index.py` on prod (224 MB, valid, readiness report) before the switch release; the drop migration removes `ix_game_flaws_blunder_facts` first with `DROP INDEX CONCURRENTLY`. |
| D-18 | JIT re-measured, `disable_jit_for_transaction` kept only if numbers support it | VERIFIED | `reports/blunder-check/facepalm-jit-259.md`: EXPLAIN ANALYZE on the largest account (user 95), JIT on/off, 4 runs each; on/off warm median 1.04 (counts) and 1.13 (comparison) against the rule's 1.05, decision "keep". `disable_jit_for_transaction` is still called in `library_repository.py` / `library_service.py`, consistent with the decision. |

**Score:** 18/18 decisions verified

### Required Artifacts / Key Links

| Artifact or link | Status | Details |
|---|---|---|
| `app/services/line_material.py` quiet walk | VERIFIED | Substantive, called by `facepalm_inputs` |
| `app/services/facepalm_inputs.py` | VERIFIED | One write-time function; used by the hook (`maia_flaw_scoring._facepalm_values`) and the features script |
| `app/services/facepalm_score.py` scalar twins | VERIFIED | Python/SQL twins pinned by tests; reads `GameFlaw` scalar columns only |
| `app/models/game_flaw.py` columns and index | VERIFIED | Three new columns, CHECKs, new index; arrays removed, migrations d1e5f7a9c259 to f3a7b9c1e259 chain to a single head |
| Hook to columns | WIRED | `_facepalm_values` and `_reply_prob` feed `FacepalmStats` / `MaiaReplyStats` into the row writers; backfill modes line, reply, spread in `scripts/backfill_maia_flaws.py` |
| Score expression to readers | WIRED | `facepalm_expr` used by library repository, blunder-check selection and stats; the chip and filter share one expression (253 D-10 unchanged) |
| Constants to fit | WIRED | `--check-constants` reproduces all six `FACEPALM_*` coefficients from the committed features TSV |

### Data-Flow Trace (Level 4)

The score inputs flow from stored columns that production passes filled: `material_loss` on about 2.21M user and 2.22M opponent blunders and `maia_best_reply_prob` on 4.42M of 4.73M blunders (readiness report), with the post-switch hook still writing them on live games (259-15-SUMMARY: 461 of 489 and 462 of 489 blunders after the drop). Status: FLOWING. The readiness figures are operator facts from committed reports; I did not query prod.

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|---|---|---|---|
| Fixture ply 47 gives `missed = 0` | `facepalm_material_inputs` on the D13 FEN and lines | `loss=2.9355, missed=0.0` | PASS |
| Constants reproduce from committed features | `fit_facepalm.py --features ...2026-11-22.tsv --check-constants` | "constants match", exit 0 | PASS |
| Quiet extension is load-bearing | monkeypatch `_quiet_walk_end` to depth-only, run line_material tests | fails (`n13`) | PASS (tests bite) |
| Phase test files (services and scripts) | `uv run pytest` on the facepalm, line_material, maia_flaw, fit, features, backfill, index, calibration, metrics, miss_labels files | 78 + 453 passed, 0 failed | PASS |
| Lint, format, types, nesting gate | `ruff check`, `ruff format --check`, `ty check app/ tests/ scripts/`, `check_function_size.py app/ --fail-over-depth 4` | all clean | PASS |
| Single migration head | `alembic heads` | `f3a7b9c1e259 (head)` | PASS |

The full backend (6861 passed, 8 skipped, parallel and serial) and frontend (6740 tests) runs on the final tree are operator facts in 259-15-SUMMARY; I did not rerun them.

### Probe Execution

No probe scripts are declared by this phase. Step 7c: not applicable.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|---|---|---|---|---|
| `scripts/blunder_check/render.py` | 190-194 | Calibration report prose still says the stored facts include "the opponent's reply spread" and "the depth-3 material"; the score no longer reads either | Info | Narrative in a dev report only, no behavior effect. Worth a one-line fix. |
| `app/services/facepalm_material.py`, `app/services/line_material.py` | docstrings | Still describe the dropped Postgres arrays (review IN-01, open) | Info | Documentation drift only. |
| `app/services/facepalm_score.py`, `facepalm_material.py` | `loss_feature`, `missed_feature`, `aggregate`, `depth_3` / `first_stable` inputs | Unused generality, only `decaying_mean` is used (review WR-03, open, owner to schedule) | Warning | Dead-ish code kept deliberately; not a goal gap. D-03 fixes the aggregate, so the alternatives are unused. |
| any phase file | | No `TBD`/`FIXME`/`XXX` debt markers found in the files the phase changed that I scanned | none | |

Review findings WR-01, WR-02 and IN-02 are fixed in `5db6b09f2` with regression tests (`tests/scripts/test_miss_labels.py`, `tests/scripts/test_facepalm_features.py`, both passing).

### Requirements Coverage

No REQUIREMENTS.md. All decisions D-01 to D-18 appear in the plans' `requirements:` frontmatter (D-01 plans 07/11; D-02 to D-04 plan 01; D-05 plans 04/08/09/10/13/14; D-06 plans 13/14/15; D-07 plans 02/04/05/08; D-08 plans 07/09; D-09 plans 02/03; D-10 plans 04/05/06/15; D-11 plans 04/05/06/09/11/12; D-12 plans 02/07/11; D-13 plans 01/02/03/11/12; D-14 plans 03/07/11; D-15 plans 08/11/12; D-16 plan 12; D-17 plans 10/11/12/14; D-18 plans 09/12/14). No orphaned decisions.

### Human Verification Required

None required for the phase goal. Two operator facts the verifier could not observe independently, both documented in committed reports: the prod passes and release state (reports under `reports/maia-flaws-backfill/`) and the post-drop Sentry check that 259-15-SUMMARY defers to this verification. The Sentry check is an operational follow-up, not a phase truth, so it does not change the status. Do it with a quick look at the issue stream since the 13:12Z deploy of `59e1edcb`.

### Gaps Summary

No gaps. The rule, storage, reply probability, refit, owner checkpoints and all three releases are present in the codebase and consistent with the committed evidence. The 0.012 AUC difference is inside the 0.02 range, the constants reproduce from the committed features, the arrays have zero readers and are dropped by a single-head migration, and the fixture row now has a missed gain of 0. Open items are cleanup only: stale docstrings (IN-01), unused aggregate generality (WR-03), and the stale prose in `render.py`. Promotions not counting as material is out of scope (separate seed).

---

_Verified: 2026-11-22_
_Verifier: Claude (gsd-verifier)_
