---
phase: 254-facepalm-score-missed-gains-and-loss-aversion-knob-seed-2611
plan: 15
subsystem: backend-services
tags: [facepalm-score, sql-twin, loss-aversion, lambda, tdd]
requires:
  - phase: 254-01
    provides: "LineFacts.material_at (signed depth-3 material) and material_at_depth reader"
provides:
  - "missed_feature (D-05, D-18) and the lam-aware Python and SQL score twins"
  - "FacepalmModel with the D-06/D-07/D-08 shape fields, FacepalmFacts, FacepalmColumns"
  - "FACEPALM_DRILL_LAMBDA / FACEPALM_LIBRARY_LAMBDA and the pre-refit shape constants"
affects: [254-16, 254-17, 254-18, facepalm-readers, facepalm-fit]
tech-stack:
  added: []
  patterns:
    - "Model shape chosen by Literal-typed constants branched at build time, so the SQL stays a plain expression"
    - "A zero coefficient omits its term in both twins; every NULL guard is an explicit CASE"
key-files:
  created: []
  modified:
    - app/services/facepalm_score.py
    - app/services/blunder_check_rules.py
    - app/services/maia_flaw_scoring.py
    - scripts/blunder_check/fit_facepalm.py
    - tests/services/test_facepalm_score.py
    - tests/services/test_maia_flaw_scoring.py
key-decisions:
  - "Combined form is loss_coef * (loss + lam * missed); the missed term's z weight is _missed_weight(model, lam), shared by both twins and omitted at 0.0"
  - "played_prob, reply_spread (always form) and the played-line loss stay required inputs; only the new optional terms are omitted at zero coefficient"
  - "missed_feature returns 0.0 when played_3 is None as well as when best_3 is None, so Python and SQL agree (the loss term already unscores a row with no played line and no mate)"
  - "The hook passes no best-line or pre-blunder facts yet (plan 16 adds them); the stored value is the Phase 250 score"
requirements-completed: [D-01, D-03, D-04, D-05, D-06, D-07, D-08, D-10, D-12, D-18]
coverage:
  - id: D1
    description: "D-05 missed term with the D-18 unknown-best-line rule and the missed-mate value"
    requirement: "D-05"
    verification:
      - kind: unit
        ref: "tests/services/test_facepalm_score.py#test_missed_feature_d05_table"
        status: pass
      - kind: unit
        ref: "tests/services/test_facepalm_score.py#test_missed_feature_floor_cap_unknown_and_mate"
        status: pass
    human_judgment: false
  - id: D2
    description: "Pre-refit constants reproduce the Phase 250 score for every lambda in both twins"
    requirement: "D-12"
    verification:
      - kind: unit
        ref: "tests/services/test_facepalm_score.py#test_new_twin_reproduces_phase_250_score"
        status: pass
      - kind: integration
        ref: "tests/services/test_facepalm_score.py#test_sql_twin_parity_material_forms"
        status: pass
      - kind: other
        ref: "uv run python scripts/blunder_check/fit_facepalm.py --features reports/blunder-check/facepalm-features-2026-11-13.tsv --check-constants"
        status: pass
    human_judgment: false
  - id: D3
    description: "Lambda knob: two separate constants, required keyword, lam 0 = loss-only score, range-checked"
    requirement: "D-03"
    verification:
      - kind: unit
        ref: "tests/services/test_facepalm_score.py#test_missed_term_lambda"
        status: pass
      - kind: unit
        ref: "tests/services/test_facepalm_score.py#test_lambda_constants_are_separate_and_in_range"
        status: pass
    human_judgment: false
  - id: D4
    description: "Full model space (material forms, three spread forms, optional inputs) with SQL/Python parity over NULL in every input"
    requirement: "D-01"
    verification:
      - kind: integration
        ref: "tests/services/test_facepalm_score.py#test_sql_twin_parity_every_shape"
        status: pass
      - kind: integration
        ref: "tests/services/test_facepalm_score.py#test_zero_coefficient_input_never_unscores"
        status: pass
      - kind: integration
        ref: "tests/services/test_facepalm_score.py#test_gated_spread_null_with_zero_loss"
        status: pass
    human_judgment: false
duration: 45 min
completed: 2026-11-14
status: complete
plan_head_before: dcddbb32c5b2c951c38aef1c247da101cace50df
plan_head_after: 487d629264da1e296580563e766cbc17e68b7265
commits: 4
actuals:
  tokens: 14000
  tasks: 3
  commits: 4
---

# Phase 254 Plan 15: Facepalm score model with the missed term and lambda Summary

Both facepalm score twins now carry the D-05 missed term, a required lambda keyword and every D-06/D-07/D-08 model shape selected by constants, with the pre-refit constants reproducing the Phase 250 score exactly.

## Accomplishments

- `missed_feature(played_3, best_3, best_mate_ply, ...)`: `best_3 - max(0, played_3)` with optional floor, cap and a missed-mate value; an unknown best line contributes 0 (D-18). The D-05 table (loss/missed 5/0, 0/5, 5/3) is a unit test.
- `facepalm_score(facts, *, lam, model)` and `facepalm_score_sql(columns, *, lam, model)`: lam is a required keyword, range-checked against `FACEPALM_LAMBDA_MIN/MAX`, and multiplies only the missed term (combined: `loss_coef * (loss + lam * missed)`, split: `missed_coef * lam * missed`). The SQL twin reads slot 3 of the signed `ARRAY(SmallInteger)` columns.
- `FacepalmModel` holds `material_form` (combined / split), `spread_form` (always / loss_only / best_prob_for_misses), `best_prob_coef`, `pre_spread_coef` and the missed floor/cap/mate. `FACEPALM_MODEL` is built from new `FACEPALM_*` constants whose pre-refit values (split, missed_coef 0.0, always, 0.0, 0.0) reproduce today's score, so the later refit is a constants-only change. `__post_init__` rejects an active missed term with a loss floor other than 0 (D-05).
- `FACEPALM_DRILL_LAMBDA = 1.0` and `FACEPALM_LIBRARY_LAMBDA = 1.0` are two separate constants (D-03, D-04). No forcing-flag input (D-10).
- Zero-coefficient terms are omitted at build time in both twins and every NULL guard is an explicit CASE, so a NULL unused input never unscores a row; gated spread forms keep a pure miss with a NULL spread scored.
- The hook (`_facepalm_values`) and `fit_facepalm.score_extras` call the new signature with `lam=FACEPALM_DRILL_LAMBDA`; stored values are unchanged and `--check-constants` still reproduces the shipped constants from the legacy TSV.

## Task Commits

1. **Task 1 (tracer): missed term and lambda through both twins** - `4cec38d76` (feat)
2. **Task 2 (TDD RED): parity grid over every shape and gated-spread NULL cases** - `1aeb2ee59` (test)
3. **Task 2 (TDD GREEN): spread forms and optional inputs in both twins** - `0bf91e733` (feat)
4. **Task 3: hook and fit script on the new signature** - `487d62926` (refactor)

Tracer gate: the tracer `<verify>` is automated-only, so it was re-run end to end (40 passed at that point) before expansion.

## Files Created/Modified

- `app/services/facepalm_score.py` - model fields, `FacepalmFacts`/`FacepalmColumns`, `missed_feature`, both twins with lam
- `app/services/blunder_check_rules.py` - `MaterialForm`/`SpreadForm`, shape selectors, lambda constants and bounds
- `app/services/maia_flaw_scoring.py` - `_facepalm_values` on the new twin
- `scripts/blunder_check/fit_facepalm.py` - `score_extras` on the new twin
- `tests/services/test_facepalm_score.py` - rewritten to the new API: D-05 table, Phase 250 reproduction, lambda, parity grid (about 6000 NULL-laden rows plus extreme rows) over 8 model shapes x 3 lambdas
- `tests/services/test_maia_flaw_scoring.py` - three expected-score computations on the new signature

## Decisions Made

See key-decisions. Mutation check: changing the SQL gate `loss > 0` to `loss >= 0` makes `test_sql_twin_parity_every_shape[1.0-loss_only]` fail, so the parity grid does exercise the gated form.

## Deviations from Plan

None - plan executed exactly as written. Two test-harness notes, not plan deviations: the parity helper prepends a fully non-NULL "typing row" to every VALUES chunk (PostgreSQL types a column of bare NULLs as text) and chunks the grid to stay under asyncpg's 32767 bind-parameter limit.

## Issues Encountered

- The per-plan commit ledger under the git dir could not be written from the worktree, so `plan_head_before` is the dispatch base SHA; `commits: 4` was measured with `git rev-list --count` against it.
- Duration is an estimate (the start time was not captured).

## Known Stubs

None.

## Threat Flags

None. T-254-02 mitigated (zero-coefficient omission, explicit CASE guards, NULL-in-every-input parity grid); T-254-03 mitigated (extreme-value rows in the grid under the shipped model).

## Next Phase Readiness

Plans that store the signed arrays and best-line facts can build `FacepalmColumns` from the new `game_flaws` columns and call `facepalm_score_sql(..., lam=FACEPALM_*_LAMBDA)`; plan 16 adds the best-line / best-prob / pre-spread inputs to the hook (it currently passes None for them, and the model terms are off).

## Self-Check: PASSED

Files exist, commits `4cec38d76`, `1aeb2ee59`, `0bf91e733`, `487d62926` are on HEAD. Verified: `uv run pytest tests/services/test_facepalm_score.py tests/services/test_maia_flaw_scoring.py tests/scripts/test_fit_facepalm.py tests/scripts/test_facepalm_features.py tests/services/test_line_material.py -n auto` (226 passed), `uv run ty check app/ tests/ scripts/` clean, `check_function_size.py app/ --fail-over-depth 4` clean, `--check-constants` exits 0.
