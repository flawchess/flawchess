---
phase: 76
plan: "01"
subsystem: backend
tags:
  - backend
  - shared-helper
  - opening-insights
dependency_graph:
  requires: []
  provides:
    - app.services.score_confidence.compute_confidence_bucket
  affects:
    - app.services.opening_insights_service
    - Plan 76-02 (NextMoveEntry payload will import compute_confidence_bucket)
tech_stack:
  added: []
  patterns:
    - "Single-module Wald confidence helper; consumers import by name"
    - "D-03 sort key: (confidence DESC, |score - 0.50| DESC)"
key_files:
  created:
    - app/services/score_confidence.py
    - tests/services/test_score_confidence.py
  modified:
    - app/services/opening_insights_service.py
    - tests/services/test_opening_insights_service.py
decisions:
  - "Renamed `l` parameter to `losses` in compute_confidence_bucket to satisfy ruff E741 (ambiguous variable name); positional callers unaffected"
  - "Kept _make_row helper in test_opening_insights_service.py (used by 15+ tests); plan said to remove it but that would break the existing test suite"
metrics:
  duration_seconds: 339
  completed_date: "2026-04-28"
  tasks_completed: 3
  files_created: 2
  files_modified: 2
---

# Phase 76 Plan 01: Extract compute_confidence_bucket + D-03 sort rewrite Summary

Extracted Phase 75's `_compute_confidence` into `app/services/score_confidence.compute_confidence_bucket(w, d, losses, n)` as the single implementation of the trinomial Wald formula, and re-sorted `_rank_section` by `(confidence DESC, |score - 0.50| DESC)` per D-03.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Create test_score_confidence.py (Wave 0 RED) | 5254893 | tests/services/test_score_confidence.py |
| 2 | Create score_confidence.py, migrate body, update service | 6898ae6 | app/services/score_confidence.py, app/services/opening_insights_service.py, tests/services/test_opening_insights_service.py, tests/services/test_score_confidence.py |
| 3 | Re-sort _rank_section by confidence + score distance | 45e641b | app/services/opening_insights_service.py, tests/services/test_opening_insights_service.py, app/services/score_confidence.py, tests/services/test_score_confidence.py |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed incorrect confidence bucket assertion in test_n10_floor_balanced**
- **Found during:** Task 2 (running tests after creating score_confidence.py)
- **Issue:** Plan specified `assert confidence == "low"` for `compute_confidence_bucket(w=2, d=6, losses=2, n=10)`. The Wald formula gives half_width = 1.96 * sqrt(0.10/10) = 0.196 which is <= 0.20, so the correct bucket is "medium" not "low".
- **Fix:** Updated assertion to `confidence == "medium"` with a comment explaining the math
- **Files modified:** tests/services/test_score_confidence.py
- **Commit:** 45e641b (included in Task 3 commit)

**2. [Rule 3 - Blocking] Renamed `l` parameter to `losses` to satisfy ruff E741**
- **Found during:** Task 3 verification (full ruff check)
- **Issue:** Ruff E741 flags single-letter `l` as ambiguous variable name. Would block CI.
- **Fix:** Renamed parameter from `l` to `losses` in `compute_confidence_bucket` signature and all keyword-argument call sites; positional callers (opening_insights_service.py) unaffected
- **Files modified:** app/services/score_confidence.py, tests/services/test_score_confidence.py, tests/services/test_opening_insights_service.py
- **Commit:** 45e641b

**3. [Rule 1 - Bug] Kept _make_row helper in test_opening_insights_service.py**
- **Found during:** Task 2 planning
- **Issue:** Plan instruction said "Delete the eight `test_compute_confidence_*` tests AND the `_make_row` helper". However `_make_row` is used by 15+ other tests in the file. Removing it would break the entire test suite.
- **Fix:** Kept `_make_row`, deleted only the 8 `test_compute_confidence_*` tests as intended
- **Files modified:** tests/services/test_opening_insights_service.py

## Verification Results

```
uv run pytest tests/services/test_score_confidence.py tests/services/test_opening_insights_service.py
33 passed in 0.16s

uv run ty check app/ tests/
All checks passed!

uv run ruff check app/ tests/
All checks passed!
```

## Self-Check: PASSED

- `app/services/score_confidence.py` exists: FOUND
- `tests/services/test_score_confidence.py` exists: FOUND (9 tests)
- `def _compute_confidence` removed from opening_insights_service.py: CONFIRMED
- `from app.services.score_confidence import compute_confidence_bucket` in opening_insights_service.py: CONFIRMED
- `_CONFIDENCE_RANK` and `abs(f.score - 0.5)` in opening_insights_service.py: CONFIRMED
- `test_ranking_confidence_desc_then_score_distance_desc` exists in test file: CONFIRMED
- `test_ranking_severity_desc_then_n_games_desc` removed: CONFIRMED
- Commits 5254893, 6898ae6, 45e641b exist: CONFIRMED
