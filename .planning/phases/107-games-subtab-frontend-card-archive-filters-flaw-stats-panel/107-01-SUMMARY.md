---
phase: 107-games-subtab-frontend-card-archive-filters-flaw-stats-panel
plan: "01"
subsystem: backend-schemas-services
tags: [library, flaw-stats, tag-distribution, backend]
dependency_graph:
  requires: []
  provides: [TagDistribution.miss_rate, TagDistribution.lucky_escape_rate, TagDistribution.while_ahead_rate]
  affects: [GET /api/library/flaw-stats]
tech_stack:
  added: []
  patterns: [flat-float-rate, guard-divide-by-zero, module-level-tag-constants]
key_files:
  created: []
  modified:
    - app/schemas/library.py
    - app/services/library_service.py
    - tests/services/test_library_service.py
decisions:
  - "D-01: Added miss_rate, lucky_escape_rate, while_ahead_rate as flat floats to TagDistribution (no nested dicts), mirroring result_changing_rate precedent exactly"
  - "D-01: Added _MISS_TAG, _LUCKY_ESCAPE_TAG, _WHILE_AHEAD_TAG module-level constants (reusing _RESULT_CHANGING_TAG pattern — no magic strings)"
  - "Pure unit tests (no DB) for rate assertions; only test_miss_rate_and_lucky_escape_rate uses a DB seed to verify the integration path, using _compute_tag_distribution directly for the rate assertions"
metrics:
  duration: "204s"
  completed_date: "2026-06-05"
  tasks_completed: 2
  files_changed: 3
---

# Phase 107 Plan 01: TagDistribution Rate Fields (D-01 Backend Slice) Summary

Three flat float rate fields added to `TagDistribution`: `miss_rate`, `lucky_escape_rate`, `while_ahead_rate`. Each = tag count / total M+B flaws with a `> 0 else 0.0` guard, mirroring the `result_changing_rate` precedent exactly. No migration — computed on-the-fly.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Add flat float rate fields to TagDistribution + compute in _compute_tag_distribution | e5527583 | app/schemas/library.py, app/services/library_service.py |
| 2 | Extend flaw-stats backend tests for three new rates + no-flaws edge | ce5f38be | tests/services/test_library_service.py |

## What Was Built

### app/schemas/library.py

`TagDistribution` extended with three new fields after `phase_histogram`:
- `miss_rate: float` — miss M+B flaws / total M+B flaws; 0.0 when no M+B flaws
- `lucky_escape_rate: float` — lucky-escape M+B flaws / total M+B flaws; 0.0 when no M+B flaws
- `while_ahead_rate: float` — while-ahead M+B flaws / total M+B flaws; 0.0 when no M+B flaws

Each field documented with the same `count / total M+B flaws; 0.0 when there are no M+B flaws` wording as `result_changing_rate`.

### app/services/library_service.py

`_compute_tag_distribution` extended:
- Three module-level constants `_MISS_TAG`, `_LUCKY_ESCAPE_TAG`, `_WHILE_AHEAD_TAG` (FlawTag literals, following `_RESULT_CHANGING_TAG` pattern)
- Three integer counters `miss_count`, `lucky_escape_count`, `while_ahead_count` initialized to 0
- Three `elif` branches in the `for tag in flaw["tags"]` loop after the existing `_RESULT_CHANGING_TAG` branch
- Three rate computations with identical `count / total_flaws if total_flaws > 0 else 0.0` guard
- `return TagDistribution(...)` updated to pass all three rates

### tests/services/test_library_service.py

Three new test methods added to `TestFlawStats`:
- `test_miss_rate_and_lucky_escape_rate` — seeds DB game then calls `_compute_tag_distribution` directly with hand-crafted FlawRecords tagged `miss`/`lucky-escape`; asserts `miss_rate == pytest.approx(0.5)` and `lucky_escape_rate == pytest.approx(0.5)`
- `test_while_ahead_rate` — pure unit test (no DB); 1 `while-ahead` flaw of 2 total → `while_ahead_rate == pytest.approx(0.5)`
- `test_rates_zero_when_no_mb_flaws` — pure unit test (no DB); empty `per_game` list → all three rates `== 0.0`, no `ZeroDivisionError`

## Verification

- `uv run ty check app/ tests/` — 0 errors
- `uv run ruff check app/ tests/` — 0 issues
- `uv run ruff format --check app/ tests/` — all clean
- `uv run pytest -n auto tests/services/test_library_service.py -x` — 16 passed (4 pre-existing + 12 pre-existing + 3 new — wait, 16 total: 5 TestCountGameSeverities + 3 TestCardChips + 1 TestNoEngineAnalysis + 7 TestFlawStats)

## Deviations from Plan

None — plan executed exactly as written. The `_compute_tag_distribution` pure unit test approach (no DB needed for rate assertions) was chosen for `test_while_ahead_rate` and `test_rates_zero_when_no_mb_flaws` following the `TestCardChips` pure-unit style the plan explicitly mentioned as an option.

## Known Stubs

None. All three rate fields are fully wired: the schema declares them, the service computes them from the live tag walk, and the tests exercise them.

## Threat Flags

None. Pure computed aggregates on an existing user-scoped authenticated endpoint — no new route, input, storage, or auth change.

## Self-Check: PASSED

- `/home/aimfeld/Projects/Python/flawchess/app/schemas/library.py` — exists, modified
- `/home/aimfeld/Projects/Python/flawchess/app/services/library_service.py` — exists, modified
- `/home/aimfeld/Projects/Python/flawchess/tests/services/test_library_service.py` — exists, modified
- Commit e5527583 — Task 1 (feat)
- Commit ce5f38be — Task 2 (test)
