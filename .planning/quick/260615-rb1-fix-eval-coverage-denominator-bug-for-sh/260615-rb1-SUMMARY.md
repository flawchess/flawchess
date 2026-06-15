---
phase: quick-260615-rb1
plan: 01
subsystem: flaws / library eval-coverage gate
tags: [bugfix, eval-coverage, analyzed-gate, sql-python-parity]
requires: []
provides:
  - "Terminal-position-excluded eval-coverage denominator in both mirrored gates"
affects:
  - app/services/flaws_service.py
  - app/repositories/library_repository.py
tech-stack:
  added: []
  patterns:
    - "SQL/Python gate parity: COUNT(*) - 1 mirrors len(positions) - 1"
key-files:
  created: []
  modified:
    - app/services/flaws_service.py
    - app/repositories/library_repository.py
    - tests/services/test_flaws_service.py
    - tests/test_library_repository.py
    - CHANGELOG.md
decisions:
  - "Denominator = movable positions (total - 1), guarded at <=1 position -> 0.0, in both gates"
metrics:
  duration: ~10m
  completed: 2026-06-15
---

# Quick Task 260615-rb1: Fix Eval-Coverage Denominator Bug for Short Games Summary

Fixed a confirmed prod bug where short fully-analyzed games (7-8 plies) failed the eval-coverage gate because the structurally-unevaluable terminal position was counted in the denominator, capping coverage at N/(N+1) < 0.90 and leaving 445 prod games stuck with the "Analyze" pill and NULL oracle columns.

## What Changed

- **`app/services/flaws_service.py::_compute_eval_coverage`** — denominator changed from `len(positions)` to `len(positions) - 1` (movable positions only; the terminal position after the last move never carries an eval). Guard rewritten to return `0.0` for `len(positions) <= 1` (covers empty + single-position, prevents div-by-zero). Docstring corrected (deleted the wrong "(N-1)/N well above 0.90, no special case needed" claim — that reasoning was the bug) and a bug-fix comment added per CLAUDE.md. The `EVAL_COVERAGE_MIN` comment block was corrected (fully-analyzed games now score 1.0 at any length, not 80/81 ≈ 98.8%).
- **`app/repositories/library_repository.py::_analyzed_game_ids_subquery`** — SQL denominator mirrored to `func.count() - 1` with a `HAVING and_(func.count() > 1, coverage >= EVAL_COVERAGE_MIN)` guard. Added `and_` to the sqlalchemy import (was missing). Docstring updated with the corrected SQL sketch and the count guard. Still uses the imported `EVAL_COVERAGE_MIN` constant (no `0.90` literal).
- Tests updated/added in both `tests/services/test_flaws_service.py` and `tests/test_library_repository.py` (see below).
- CHANGELOG `[Unreleased] > Fixed` bullet added.

## Semantic parity check (constraint-mandated)

The CRITICAL semantic check requested in the constraints was verified: `_compute_eval_coverage` receives positions from `flaws_repository.fetch_game_positions_ordered`, which selects ALL `GamePosition` rows for `(game_id, user_id)` with no extra filter. The SQL subquery groups all `GamePosition` rows by `game_id` scoped to the same `user_id`. Both therefore count the identical per-game row set, so `func.count()` == `len(positions)` and `func.count() - 1` == `len(positions) - 1` count exactly the same terminal-excluded set. No drift; the subtraction is symmetric and safe. (No surfacing needed — the check passed.)

## Tasks Completed

| Task | Name | Commit | Files |
| ---- | ---- | ------ | ----- |
| 1 | Fix denominator in both mirrored gates | 831bae38 | app/services/flaws_service.py, app/repositories/library_repository.py |
| 2 | Update and extend tests for both gates | 281c16d5 | tests/services/test_flaws_service.py, tests/test_library_repository.py |
| 3 | CHANGELOG entry + full local gate | 0ac8fdb7 | CHANGELOG.md |

## Tests

Kernel (`tests/services/test_flaws_service.py::TestEvalCoverageGate`):
- `test_full_coverage_minus_final_ply` — updated assertion `80/81` -> `1.0`.
- `test_below_threshold_returns_low_coverage` — updated assertion `0.5` -> `5/9`, still `< EVAL_COVERAGE_MIN`.
- `test_single_position_returns_zero` — NEW: single-position guard returns `0.0`.
- `test_short_fully_analyzed_game_clears_gate` — NEW: 7-ply fully-analyzed game scores `1.0`.

Kernel public API (`TestClassifyGameFlaws`):
- `test_short_fully_analyzed_game_not_marked_unanalyzed` — NEW: a short fully-analyzed game returns a list, not `GameNotAnalyzed`.

SQL gate (`tests/test_library_repository.py::TestAnalyzedDenominator`):
- `test_short_fully_analyzed_game_is_analyzed` — NEW: a seeded 7-ply fully-analyzed game appears in `analyzed_game_ids`, proving the SQL gate agrees with the Python kernel.
- `test_analyzed_denominator_counts_only_covered_games` — confirmed still passing (9/(10-1) = 1.0, still analyzed).

## Deviations from Plan

None — plan executed exactly as written.

## Verification

- `uv run ty check app/ tests/` — All checks passed (0 errors).
- `uv run ruff format app/ tests/` — 237 files left unchanged.
- `uv run ruff check app/ tests/ --fix` — All checks passed.
- `uv run pytest -n auto -x` — 2653 passed, 10 skipped, 2 (pre-existing, unrelated) warnings.
- No frontend files edited (the frontend only consumes the API "analyzed" flag), so frontend lint/tests were not required.

## Scope Boundaries Honored

No migration, no prod backfill, no `eval_drain`/queue changes, no frontend edits. The 445 stuck prod games will resolve once re-classified through the corrected gate (out of scope for this task).

## Self-Check: PASSED

- Files exist: app/services/flaws_service.py, app/repositories/library_repository.py, tests/services/test_flaws_service.py, tests/test_library_repository.py, CHANGELOG.md — all FOUND.
- Commits exist: 831bae38, 281c16d5, 0ac8fdb7 — all in git log.
