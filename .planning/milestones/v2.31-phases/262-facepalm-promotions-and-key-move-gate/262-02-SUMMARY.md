---
phase: 262-facepalm-promotions-and-key-move-gate
plan: 02
subsystem: facepalm-score
tags: [facepalm, key-move-gate, sql-twin, fit-tool, D-04]
requires: []
provides:
  - "is_allowed_loss / _allowed_loss_sql: one allowed-loss condition for the type and the key-move gate"
  - "fit_facepalm --gate {type,loss}: GateName, _reads_reply, gate threaded through the fit"
affects:
  - app/services/facepalm_score.py
  - scripts/blunder_check/fit_facepalm.py
  - scripts/blunder_check/facepalm_features.py
  - scripts/backfill_maia_flaws.py
tech-stack:
  added: []
  patterns: ["one shared condition per twin side, NULL guard first in the SQL CASE"]
key-files:
  created: []
  modified:
    - app/services/facepalm_score.py
    - tests/services/test_facepalm_score.py
    - scripts/blunder_check/fit_facepalm.py
    - tests/scripts/test_fit_facepalm.py
    - scripts/blunder_check/facepalm_features.py
    - tests/scripts/test_facepalm_features.py
    - scripts/backfill_maia_flaws.py
    - tests/scripts/test_backfill_maia_flaws.py
    - app/services/blunder_check_rules.py
decisions:
  - "D-04 implemented: the key-move term reads the reply exactly on an allowed loss (loss > 0 and loss >= missed, NULL missed read as 0.0), the best move otherwise, no minimum loss"
  - "The FACEPALM_* values are untouched (plan 07 pastes the refit); a gate change is a constants-style deploy with no UPDATE pass"
  - "The loss gate survives only as the fit tool's --gate loss, to reproduce the Phase 259 constants and for the D-05 reference line"
metrics:
  duration: "about 40 minutes"
  completed: 2026-11-23
status: complete
actuals:
  tokens: 11200
  tasks: 3
  commits: 3
plan_head_before: 57cafb6e4a6efd581ee2db528018eba62f6f5e1a
plan_head_after: bed0c181d4eaf1c2ff0556b0bbc196ee468ac1ba
---

# Phase 262 Plan 02: Key-move gate follows the type rule Summary

The facepalm score now reads the opponent's reply on an allowed loss only and the best move on every other row, through one shared condition (`is_allowed_loss` in Python, `_allowed_loss_sql` in SQL) that also decides the facepalm type, in both twins, in the fit tool and in the two status counters that mirrored the old loss-only gate.

## What changed

- **Task 1 (tracer), `d71f20b81`:** `is_allowed_loss(loss, missed)` and `_allowed_loss_sql(columns)` added to `app/services/facepalm_score.py` (public in `__all__`). `_key_move_term`, `_key_move_sql` (NULL guard still the first CASE branch), `facepalm_type_of` and `facepalm_type_sql` all read them. Module docstring updated. Tests: `test_is_allowed_loss_rule`, `test_mixed_row_reads_the_best_move_term`, a mixed case in `test_facepalm_type_of_rule`, and a mixed stored row (loss 1.0, missed 3.0, best 0.3, reply NULL) in `_STORED_FACT_ROWS`, asserted scored in Postgres and equal to the Python twin. Tracer re-verified end to end (parity grids unchanged and green) before expanding.
- **Task 2, `8ed87210c`:** `fit_facepalm.py` gains `GateName`, `GATES`, `DEFAULT_GATE = "type"`, `_reads_reply` and a `gate` parameter through `missing_reason`, `_exclusion_reason`, `split_usable`, `design_row`, `design_matrix`, `scalar_score`, `fit_shape`, `holdout_split`, `fit_alternatives`, `score_extras`, `run_fit`, plus the CLI flag `--gate`. `FitOutcome` also carries `gate` so the owner-section scores use the run's gate. Reason strings reworded per the plan. `synthetic_rows` draws labels with the type gate; the shipped-constants reproduction test passes `--gate loss`.
- **Task 3, `bed0c181d`:** `_has_null_score_input` (features) uses `is_allowed_loss`; `_fetch_reply_status` filters `reply_residue_losing` / `unscored_pure_miss_no_best` on `facepalm_type_expr()` (key names and order unchanged); the comment above `FACEPALM_INTERCEPT` states the type-rule formula and that the values were fitted under the loss gate. No constant value changed.

## Verification

- `uv run python scripts/blunder_check/fit_facepalm.py --features reports/blunder-check/facepalm-features-2026-11-22.tsv --labels reports/blunder-check/facepalm-labels.tsv --gate loss --check-constants`: exit 0 (constants match).
- Full backend suite `uv run pytest -n auto`: 6974 passed, 8 skipped. An earlier `-x` run tripped once on `tests/test_eval_worker_endpoints.py::test_lease_lifo` under xdist; the file passes serially (135 passed) and the repeat full run is green, so it is an unrelated parallel flake.
- `ruff check`, `ruff format --check`, `ty check app/ tests/ scripts/` and the nesting-depth gate: clean.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `test_zero_coefficient_omits_its_term` asserted `material_missed` absent at lam 0**
- **Found during:** Task 1
- **Issue:** the allowed-loss gate (D-04) now reads `material_missed` through a coalesce even when lambda is 0, so the compiled expression names the column once.
- **Fix:** the assertion now counts `game_flaws.material_missed` (1 at lam 0, 2 at lam 1); the NULL-missed-at-lam-0 row stays scored (the coalesce).
- **Files modified:** tests/services/test_facepalm_score.py
- **Commit:** d71f20b81

**2. [Rule 2 - Missing critical] `FitOutcome` carries the run's gate**
- **Found during:** Task 2
- **Issue:** the plan threads `gate` through the fit functions but the owner section (`_note_row`) rescored commented rows with the default gate, which would be wrong under `--gate loss`.
- **Fix:** added `gate` to `FitOutcome` and passed it to `_note_row`.
- **Commit:** 8ed87210c

`_reply_game` ply 8 needed no explicit `_set_flaw`: the seeded pair (loss 2.0, missed 1.0) is already an allowed loss.

## Known Stubs

None.

## Threat Flags

None. The expression still reads the same two columns of `ix_game_flaws_facepalm_inputs` and stays under 2000 characters (`test_score_and_type_expressions_are_small`); plan 06 owns the prod EXPLAIN.

## Self-Check: PASSED

- FOUND: app/services/facepalm_score.py (`def is_allowed_loss`), scripts/blunder_check/fit_facepalm.py (`def _reads_reply`, `--gate`)
- FOUND commits: d71f20b81, 8ed87210c, bed0c181d (ancestors of HEAD)
