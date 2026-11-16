---
phase: 256-facepalm-refit-material-aggregated-over-depths
plan: 02
subsystem: scoring
tags: [facepalm, fit-loader, calibration-cache, material-arrays]
requires: ["256-01"]
provides:
  - "FitRow.played_material / best_material (9-slot tuples) read from the nine played_mat_N / best_mat_N cells; played_3 / best_3 as properties"
  - "PLAYED_MAT_COLUMNS / BEST_MAT_COLUMNS in fit_facepalm.py"
  - "Calibration cache version 4: BlunderRecord / FlawRow carry both 9-slot arrays"
affects: [256-03, 256-04, 256-07]
tech-stack:
  added: []
  patterns: ["scalar depth-3 views as read-only properties over the stored array (material_at_depth)"]
key-files:
  created: []
  modified:
    - scripts/blunder_check/fit_facepalm.py
    - tests/scripts/test_fit_facepalm.py
    - scripts/blunder_check/sample.py
    - tests/scripts/test_blunder_check_calibration.py
key-decisions:
  - "Column-name tuples are defined locally in fit_facepalm.py (not imported from facepalm_features.py, which loads Maia)"
  - "The existing version-mismatch test (version 2) was converted to test_cache_version_3_is_refused rather than adding a second near-duplicate test"
requirements-completed: [D-06, D-13]
duration: ~50 min (about 12 min of it the full suite)
completed: 2026-11-16
status: complete
actuals:
  tokens: 9000
  tasks: 2
  commits: 2
plan_head_before: 4843efa3ca8dffaa6bed88bffdae1433a370b99f
plan_head_after: 51ade2770
---

# Phase 256 Plan 02: Script-side callers move to the stored material arrays Summary

The fit loader and the calibration cache now keep both full 9-slot material lines, so the aggregate inputs of plans 04 to 07 score real lines instead of depth 3; the Phase 254 constants still reproduce and the whole tree is green again.

## Accomplishments

- `FitRow` carries `played_material` / `best_material`; `played_3` / `best_3` are properties via `material_at_depth(..., LINE_DEPTH)`. The positional field order up to `line_mate_ply` is unchanged. `_facts_row` reads the nine cells of each line; a legacy row carries `single_depth_material(-line_loss_3)`. `score_extras` passes the arrays to `FacepalmFacts`.
- `fit_facepalm.py --check-constants` on `reports/blunder-check/facepalm-features-2026-11-15.tsv` still prints "constants match" and exits 0 (T-256-22).
- `sample.py`: `FlawRow` and `BlunderRecord` keep both arrays whole (`_flaw_row` no longer shrinks them to depth 3); `to_dict` writes lists, `from_dict` restores tuples; `BlunderRecord.played_3` / `best_3` are read-only properties so `render.py` and `spot_check.py` needed no edit. `CACHE_VERSION = 4`; a version 3 cache is refused (T-256-04).
- Tests: `test_fit_loads_both_schemas` asserts nine slots on facts rows and `single_depth_material(-line_loss_3)` on legacy rows; the calibration tests pass arrays to `FacepalmFacts`, the DB-seeded test asserts the arrays reach the record whole, the round-trip test asserts restored arrays and the stored list form.

## Task Commits

1. Task 1 (tracer): `fa859966d` feat(256-02): fit loader keeps both 9-slot material arrays
2. Task 2: `51ade2770` feat(256-02): calibration cache v4 carries both 9-slot material arrays

Tracer gate: the tracer `<verify>` (test_fit_facepalm 41 passed, `--check-constants` match, ty on its files) was green before Task 2 started; end-of-phase mode, no checkpoint.

## Verification

- `uv run pytest tests/scripts/test_fit_facepalm.py`: 41 passed
- `uv run python scripts/blunder_check/fit_facepalm.py --features reports/blunder-check/facepalm-features-2026-11-15.tsv --out temp/blunder-check/fit-check-256-02.md --check-constants`: "constants match", exit 0
- `uv run pytest tests/scripts/test_blunder_check_calibration.py tests/scripts/test_blunder_check_metrics.py tests/scripts/test_miss_labels.py tests/scripts/test_facepalm_features.py`: 166 passed
- `uv run ty check app/ tests/ scripts/`: All checks passed
- `uv run pytest -n auto -x`: 6690 passed, 19 skipped (full backend suite, 12 min)
- `uv run ruff check .`, `uv run ruff format --check app/ tests/ scripts/ analysis/`, `scripts/check_function_size.py app/ --fail-over-depth 4`: clean

## Deviations from Plan

None - plan executed exactly as written. (Note: the plan allowed adding `test_cache_version_3_is_refused` only if no mismatch test existed; the existing version-2 mismatch test was repurposed into it, since its "version 3" message match had to change anyway.)

## Notes for later plans

- The synthetic facts writer in `tests/scripts/test_fit_facepalm.py` still fills only the depth-3 cells (plan 04 widens it), so the other slots of synthetic rows are `None`.
- The plan-commit ledger file (`gsd-plan-head-before-256-02`) could not be written from the worktree sandbox; `plan_head_before` is the dispatch base `4843efa3c`, and `commits: 2` is `git rev-list --count 4843efa3c..HEAD` before this SUMMARY commit.

## Known Stubs

None.

## Threat Flags

None. No new endpoints or trust boundaries.

## Self-Check: PASSED

- `scripts/blunder_check/fit_facepalm.py`, `scripts/blunder_check/sample.py`, both test files: present and modified
- commits `fa859966d`, `51ade2770`: ancestors of HEAD
