---
phase: 256-facepalm-refit-material-aggregated-over-depths
plan: 08
subsystem: scoring-constants
tags: [facepalm, refit, constants, ship, changelog, d-10, d-11, d-13, d-15]
requires: ["256-07"]
provides:
  - "Refitted FACEPALM_* constants (decaying_mean input, loss gate None, FACEPALM_SCORE_MIN 0.5) in app/services/blunder_check_rules.py"
  - "test_shipped_constants_reproduce_from_the_refit_features: --check-constants on the committed 2026-11-16 features, no monkeypatch"
  - "Window 14 and owner-fixture tests pinned under the shipped model"
  - "CHANGELOG bullet under [Unreleased] / Changed"
affects: []
tech-stack:
  added: []
  patterns: []
key-files:
  created: []
  modified:
    - app/services/blunder_check_rules.py
    - tests/scripts/test_fit_facepalm.py
    - tests/services/test_facepalm_score.py
    - tests/services/test_facepalm_owner_fixtures.py
    - CHANGELOG.md
key-decisions:
  - "Constants pasted verbatim from reports/blunder-check/facepalm-fit-2026-11-16.md (## Constants), never hand-adjusted"
  - "FACEPALM_SCORE_MIN stays 0.5 (owner kept it at the 256-07 checkpoint against a 0.7 recommendation)"
requirements-completed: [D-10, D-11, D-13, D-15]
duration: ~35 min
completed: 2026-11-16
status: complete
commits: 3
plan_head_before: 42fe97bbda6e0eaa1b6b45dd4f1aa7ea0759119e
plan_head_after: 390d2d7884ba97553acba3f56b01e0482dcb6a47
actuals:
  tokens: 9000
  tasks: 3
  commits: 3
---

# Phase 256 Plan 08: Ship the refit Summary

The accepted three-input refit ships as a constants-only change: decaying-mean material input, no loss gate, cut unchanged at 0.5, with a test that re-derives the constants from the committed features table on every suite run.

## What changed

- `app/services/blunder_check_rules.py`: INTERCEPT -1.2172, PLAYED -0.6083, SPREAD -0.3617, LOSS 1.1643, MISSED_COEF 0.3538, MISSED_FLOOR 0 (was None), BEST_PROB 1.9618, `FACEPALM_MATERIAL_INPUT = "decaying_mean"` (was depth_3), `FACEPALM_LOSS_GATE = None`, `FACEPALM_SCORE_MIN = 0.5`. Provenance comments name `facepalm-features-2026-11-16.tsv`, `facepalm-fit-2026-11-16.md` and the `--check-constants` command (no forced flag). Drill and library lambda stay 1.0.
- `tests/scripts/test_fit_facepalm.py`: `REFIT_FEATURES`, `REFIT_FIT_FLAGS = ()` and `test_shipped_constants_reproduce_from_the_refit_features` (exit 0 against the real shipped model). `test_depth_3_fit_reproduces_the_2026_11_15_constants` still passes.
- `tests/services/test_facepalm_score.py`: `_FEATURES_TSV` points at the 2026-11-16 table; Window 14 now carries the nine-slot played and best arrays and is asserted `None or < FACEPALM_SCORE_MIN` (it is unscored: played line is one ply long). `test_known_d04_constants` already asserted 0.5 and needed no change.
- `tests/services/test_facepalm_owner_fixtures.py`: compares against `PHASE_254_MODEL` instead of `PHASE_250_MODEL`. Observed outcome, in both the Python and the SQL test: 817357 ply 24 scores 0.0632 (was 0.1458), 820181 ply 65 scores 0.1044 (was 0.1540); both lower than before and below 0.5. The KNOWN SHORTFALL comment is rewritten to say this plainly (information the owner accepted at D-13, not a fitting target).
- `CHANGELOG.md`: one bullet under `## [Unreleased]` / `### Changed`.

## Verification

- `uv run ruff format` (620 files unchanged), `uv run ruff check .` clean, `uv run ty check app/ tests/ scripts/` clean, analysis ty clean, `check_function_size.py app/ --fail-over-depth 4`: no breaches.
- `uv run pytest -n auto`: 6958 passed, 19 skipped (107 s).
- Frontend: `npm run lint`, `npm run build`, `npm test -- --run`, `npm run knip` all exit 0.
- `git diff main --stat -- alembic/ frontend/src/` is empty: no migration, no frontend change.

## Deviations from Plan

None in scope. Notes:

- The plan's checks name branch `gsd/phase-256-...`; this run was on the worktree branch `worktree-agent-a3262ddbba27270a5`, so that check was not applicable.
- The owner-fixture outcome is the opposite direction from the old test (lower, not higher, than the previous model). The plan allowed for either; recorded as observed in 256-07.
- Not squash-merged and not deployed, as the plan requires.

## Known Stubs

None.

## Self-Check: PASSED

- Commits `3247e3e0d`, `97b4ec5ab`, `390d2d788` exist on the branch.
- All five modified files exist and `git status --short` was empty after the last task commit.
