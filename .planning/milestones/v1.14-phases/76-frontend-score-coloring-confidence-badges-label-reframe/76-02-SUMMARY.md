---
phase: 76
plan: "02"
subsystem: backend/schema
tags:
  - backend
  - schema
  - move-explorer
  - openings
dependency_graph:
  requires:
    - "76-01: score_confidence module (compute_confidence_bucket)"
  provides:
    - "NextMoveEntry.score/confidence/p_value fields in API payload"
    - "CI structural assertion: single compute_confidence_bucket implementation"
  affects:
    - "frontend/src/types (NextMoveEntry type must be updated in Plan 04)"
    - "Plan 05: Conf column and score-based row tint can consume backend values"
tech_stack:
  added: []
  patterns:
    - "Schema extension: additive fields with Pydantic Field constraints"
    - "TDD: RED/GREEN cycle for schema+service extension"
key_files:
  created: []
  modified:
    - app/schemas/openings.py
    - app/services/openings_service.py
    - tests/test_openings_service.py
    - tests/services/test_opening_insights_arrow_consistency.py
decisions:
  - "score=0.5 sentinel for zero-game rows (gc==0), matching opening_insights_service pattern"
  - "Fields positioned last in NextMoveEntry to minimize diff churn on existing callers"
  - "D-22 consistency test uses structural assertion (inspect.getsource) not regex, because confidence has no arrowColor.ts constant (D-23 forbids confidence on arrows)"
metrics:
  duration: "~8 minutes"
  completed: "2026-04-28T14:26:03Z"
  tasks_completed: 2
  files_changed: 4
---

# Phase 76 Plan 02: NextMoveEntry Score/Confidence Payload Extension Summary

NextMoveEntry schema extended with score/confidence/p_value fields; moves-explorer now ships the same three Wald-confidence fields as OpeningInsightFinding, computed via the shared compute_confidence_bucket helper from Plan 01.

## Tasks Completed

| # | Name | Commit | Files |
|---|------|--------|-------|
| 1 (RED) | Add failing test for NextMoveEntry score/confidence/p_value | 0921785 | tests/test_openings_service.py |
| 1 (GREEN) | Extend NextMoveEntry schema and populate in service | cfe6cdb | app/schemas/openings.py, app/services/openings_service.py |
| 2 | Extend CI consistency test with D-22 structural assertion | 52038a6 | tests/services/test_opening_insights_arrow_consistency.py |

## What Was Built

**Task 1 — NextMoveEntry schema + service extension:**

- Added `score: float = Field(ge=0.0, le=1.0)`, `confidence: Literal["low","medium","high"]`, and `p_value: float = Field(ge=0.0, le=1.0)` to `NextMoveEntry` in `app/schemas/openings.py`.
- Added `from app.services.score_confidence import compute_confidence_bucket` to `openings_service.py`.
- In the per-row build loop of `get_next_moves`: computes `score = (w + 0.5 * d) / gc` and calls `compute_confidence_bucket(w, d, lo, gc)` before constructing each `NextMoveEntry`.
- New test `TestNextMovesScoreConfidence.test_get_next_moves_populates_score_confidence_p_value` seeds 3 games (2 wins + 1 loss), calls `get_next_moves`, and cross-checks all three fields against the helper's direct output.

**Task 2 — CI consistency structural assertion:**

- Appended `test_compute_confidence_bucket_is_single_implementation` to `tests/services/test_opening_insights_arrow_consistency.py` (5 tests total, 4 existing + 1 new).
- Asserts `score_confidence.compute_confidence_bucket` exists (D-06 module requirement).
- Asserts `opening_insights_service` has no local `_compute_confidence` (no duplicate formula).
- Asserts `openings_service` source contains `compute_confidence_bucket` (second consumer verified).

## Verification

- `uv run pytest tests/test_openings_service.py tests/services/test_opening_insights_arrow_consistency.py` — 27 passed
- `uv run ty check app/ tests/` — All checks passed
- `uv run ruff check app/ tests/` — All checks passed

## Deviations from Plan

None — plan executed exactly as written.

## Self-Check: PASSED

- `app/schemas/openings.py` modified with score/confidence/p_value fields: FOUND
- `app/services/openings_service.py` imports compute_confidence_bucket: FOUND
- `tests/test_openings_service.py` has new test: FOUND
- `tests/services/test_opening_insights_arrow_consistency.py` has D-22 structural test: FOUND
- Commits 0921785, cfe6cdb, 52038a6: FOUND
