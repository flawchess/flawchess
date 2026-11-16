---
phase: 256-facepalm-refit-material-aggregated-over-depths
plan: 01
subsystem: scoring
tags: [facepalm, material-input, decaying-mean, sql-twin, parity]
requires: []
provides:
  - "app/services/facepalm_material.py: per-depth loss/gain series, decaying mean, loss gate (Python + SQL builders)"
  - "FacepalmModel.material_input / loss_gate; FACEPALM_MATERIAL_INPUT, FACEPALM_LOSS_GATE, MATERIAL_DECAY_RATIO"
  - "FacepalmFacts carrying the stored 9-slot arrays; material_loss / material_missed"
affects: [256-02, 256-03]
tech-stack:
  added: []
  patterns: ["unrolled scalar CASE per odd depth, Float-typed operands, IS NULL guard before least/greatest"]
key-files:
  created:
    - app/services/facepalm_material.py
    - tests/services/test_facepalm_material.py
  modified:
    - app/services/blunder_check_rules.py
    - app/services/facepalm_score.py
    - app/services/maia_flaw_scoring.py
    - tests/facepalm_seed.py
    - tests/services/test_facepalm_score.py
    - tests/services/facepalm_owner_fixtures.py
    - tests/services/test_facepalm_owner_fixtures.py
    - tests/services/test_maia_flaw_scoring.py
key-decisions:
  - "Defaults FACEPALM_MATERIAL_INPUT='depth_3' and FACEPALM_LOSS_GATE=None keep every shipped score unchanged until the refit ships constants"
  - "A2 (owner to confirm at D-13): a mate within LINE_DEPTH short-circuits loss to MATE_LOSS and missed to model.missed_mate for every input; a later mate enters per depth from its ply on"
  - "Numeric loss gate uses >= (a one-pawn loss at every depth averages exactly 1.0 and counts as losing)"
requirements-completed: [D-03, D-06, D-11]
duration: ~45 min
completed: 2026-11-16
status: complete
actuals:
  tokens: 14000
  tasks: 2
  commits: 2
plan_head_before: 4bb2a21296346d9b016f9b681b0413ec1de72c17
plan_head_after: 372a44fc8ccf3aa9a79bb90df924962bb9c545b1
---

# Phase 256 Plan 01: Decaying-mean material input in both score twins Summary

The facepalm score can now read its loss and missed gain from the weighted mean over the odd depths 1, 3, 5, 7, 9 (weights 1, 1/2, 1/4, 1/8, 1/16, renormalised over known depths) in the Python twin and the SQL twin alike; shipped defaults still score exactly as before.

## Accomplishments

- New `app/services/facepalm_material.py` holding each series once in Python and once as an unrolled SQL builder: `loss_by_depth`, `gain_by_depth`, `decaying_mean`, `single_depth_material`, `loses` and `loss_by_depth_sql`, `gain_by_depth_sql`, `decaying_mean_sql`, `loses_sql`.
- `FacepalmModel` gained `material_input` (`"depth_3"` | `"decaying_mean"`) and `loss_gate`; `FacepalmFacts` now carries the stored arrays (`played_material`, `best_material`), `played_3` / `best_3` are derived properties.
- Public `material_loss` / `material_missed` implement the three-stage rule (D-03 coverage gate, A2 mate short-circuit within LINE_DEPTH, then the model's input); `_spread_term` / `_spread_sql` test "loses material" through `loses` / `loses_sql` (D-11).
- Python/SQL parity proven: two decaying-mean models added to the 6,048-row-style parity grid (`_SHAPE_MODELS`) and to the seeded `facepalm_expr` stored-facts test; `test_new_twin_reproduces_phase_250_score` and the existing parity grid pass with unchanged expected values.
- `maia_flaw_scoring._row_score`, the owner fixtures (constant arrays `[0]*9`/`[3]*9` and `[5]*9`/`[10]*9`, re-verified against `line_facts` / `best_line_facts`), the reader seed helper `_rest_of_z` and `test_maia_flaw_scoring.py` now pass arrays.

## Task Commits

1. Task 1 (tracer): `fd3921d32` feat(256-01): decaying-mean material input in both facepalm score twins
2. Task 2: `372a44fc8` refactor(256-01): app and service tests pass the stored material arrays to FacepalmFacts

Tracer gate: the tracer `<verify>` (material/score/seed tests, 136 passed; ty on its files) was green before Task 2 started; end-of-phase mode, no checkpoint.

## Verification

- `uv run pytest tests/services/test_facepalm_material.py tests/services/test_facepalm_score.py tests/services/test_facepalm_seed.py`: 136 passed
- `uv run pytest tests/services/test_maia_flaw_scoring.py tests/services/test_facepalm_owner_fixtures.py tests/services/test_facepalm_score.py tests/services/test_facepalm_material.py`: 218 passed
- `uv run pytest -n auto -x --ignore=tests/scripts/test_blunder_check_calibration.py --ignore=tests/scripts/test_fit_facepalm.py`: 6573 passed, 19 skipped
- `uv run ty check app/ tests/services/ tests/facepalm_seed.py tests/facepalm_models.py`: clean
- `uv run ruff check .`, `uv run ruff format --check app/ tests/ scripts/`, `check_function_size.py app/ --fail-over-depth 4`: clean

## Deviations from Plan

None - plan executed exactly as written.

## Notes for the orchestrator and later plans

- Intermediate state as planned: `scripts/blunder_check/sample.py`, `scripts/blunder_check/fit_facepalm.py`, `tests/scripts/test_blunder_check_calibration.py` and `tests/scripts/test_fit_facepalm.py` still construct `FacepalmFacts(played_3=..., best_3=...)` and fail until plan 02 migrates them. Whole-tree `ty check app/ tests/ scripts/` is therefore not green here (plan 02 closes it).
- Size of the SQL expression: a decaying-mean model compiles `facepalm_expr` to about 20k characters (each per-depth series appears in both the numerator and the denominator, and the loss expression is reused several times in z). Plan 03 asserts no `unnest`/subquery; if a reader query plan or statement size becomes a concern, the loss could be bound once as a CTE/lateral, but that is outside this plan.
- `single_depth_material` scores like the depth-3 scalar under every input only while no mate lies beyond LINE_DEPTH (a later mate adds per-depth MATE values to the aggregate); documented in its docstring.
- `decaying_mean.py` in `scripts/blunder_check/` is untouched (plan scope); its floor-at-0 gain differs deliberately from the shipped missed floor, which the new per-depth gain follows (`model.missed_floor`).

## Known Stubs

None.

## Threat Flags

None. No new endpoints or trust boundaries; only model constants enter the SQL expression (T-256-01).

## Self-Check: PASSED

- `app/services/facepalm_material.py`, `tests/services/test_facepalm_material.py`: present
- commits `fd3921d32`, `372a44fc8`: ancestors of HEAD
