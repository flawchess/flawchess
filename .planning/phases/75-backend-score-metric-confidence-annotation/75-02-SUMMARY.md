---
phase: 75
plan: 02
subsystem: openings-insights-schema
tags:
  - openings
  - insights
  - schemas
  - pydantic
dependency_graph:
  requires:
    - app/repositories/query_utils.py::DEFAULT_ELO_THRESHOLD (unchanged Phase 70 import)
  provides:
    - OpeningInsightFinding API contract with score/confidence/p_value (D-09)
  affects:
    - app/services/opening_insights_service.py (transient breakage; Plan 03 fixes)
    - tests/test_opening_insights_service.py (transient breakage; Plan 03 fixes)
    - tests/test_opening_insights_router.py (transient breakage; Plan 03 fixes)
tech_stack:
  added: []
  patterns:
    - Pydantic v2 Literal[...] enum-validated string fields (confidence)
    - Documented field semantics via inline comments anchored to phase-level decisions (D-09)
key_files:
  created: []
  modified:
    - app/schemas/opening_insights.py
decisions:
  - D-09 — replace win_rate/loss_rate with score-based classification annotated by Wald confidence
metrics:
  duration: ~5 min
  completed: 2026-04-28
requirements:
  - INSIGHT-SCORE-01
  - INSIGHT-SCORE-06
---

# Phase 75 Plan 02: OpeningInsightFinding Contract Update Summary

Apply D-09 to the OpeningInsightFinding Pydantic schema: remove redundant `loss_rate`
and `win_rate`, add `confidence: Literal["low", "medium", "high"]` and `p_value: float`,
keep `score` (now promoted to the canonical classification metric).

## What Changed

`app/schemas/opening_insights.py` — single class body modified, no imports or other
classes touched.

### Removed

- `win_rate: float` (was used as classifier for strengths under Phase 70 D-04)
- `loss_rate: float` (was used as classifier for weaknesses under Phase 70 D-04)

Both are now derivable from `score` and the W/D/L counts already in the response.

### Added

- `confidence: Literal["low", "medium", "high"]` — bucketed Trinomial Wald 95% CI
  half-width on the score statistic (Phase 75 D-05/D-06).
- `p_value: float` — two-sided p-value for H0: score = 0.50 (Phase 75 D-05/D-09).

### Kept and reannotated

- `score: float` — comment promoted from "informative only per D-06" to
  "canonical classification metric (Phase 75 D-09)".

### Docstring

Tag list extended from `(D-03, D-05, D-25)` to `(D-03, D-05, D-25; Phase 75 D-09)`,
plus a new sentence documenting the v1.14 contract migration.

## Out of Scope (Plan 03 owns)

This plan ships only the API shape. Plan 03 implements the producer side in
`compute_insights()`:

- Computing `score`, `confidence`, `p_value` from the W/D/L counts
- Wiring the new fields into the four-section response builder
- Updating `tests/test_opening_insights_service.py` and
  `tests/test_opening_insights_router.py` to construct `OpeningInsightFinding`
  with the new shape

## Known Transient Failures

Until Plan 03 lands, the following test modules will fail to construct
`OpeningInsightFinding` because they pass `win_rate=...`, `loss_rate=...` and omit
`confidence`/`p_value`:

- `tests/test_opening_insights_service.py`
- `tests/test_opening_insights_router.py`
- Any downstream test importing those fixtures

This breakage is expected within the Plan 02 boundary and explicitly resolved by
Plan 03 (per plan's own acceptance criteria, last bullet).

## Verification

- `uv run ty check app/schemas/opening_insights.py` — passes (zero errors).
- `uv run ruff format --check app/schemas/opening_insights.py` — passes after
  ruff applied its preferred wrapping for the long Literal annotation.
- Pydantic v2 round-trip: `model_validate` accepts the new shape, `model_dump`
  returns exactly the expected key set (no `win_rate`/`loss_rate`, includes
  `confidence`/`p_value`/`score`). Literal validation rejects strings outside
  `{"low", "medium", "high"}`.

## Deviations from Plan

### Rule 3 — Auto-applied ruff format

**Found during:** Task 1 verification (`ruff format --check` initially failed)

**Issue:** ruff wraps the long `entry_san_sequence` and `confidence` annotations
across multiple lines per project format settings. The plan's grep verification
pattern `grep -q "confidence: Literal\[\"low\", \"medium\", \"high\"\]"` matches
only single-line form.

**Fix:** Ran `uv run ruff format app/schemas/opening_insights.py` to apply the
project's canonical formatting. The wrapped form is functionally identical
(Pydantic accepts it; ty check passes; round-trip validation works correctly).

**Files modified:** `app/schemas/opening_insights.py`

**Commit:** included in 8563f52

This is the project's standard formatter — fix is mandatory per CLAUDE.md
(`uv run ruff format .`). The plan's literal grep snippet was overly strict
about layout; the acceptance criteria (field presence, Literal validation,
ty pass) are all met.

## Threat Flags

None. T-75-02 (Information Disclosure) is `accept` per the plan's threat register —
new fields are derived from already-exposed W/D/L counts. No new trust boundary,
no new sensitive data, no auth surface change.

## Self-Check: PASSED

- File `app/schemas/opening_insights.py` exists and contains the new fields.
- Commit `8563f52` exists in `git log` on branch `worktree-agent-a254cc1cf6e05f24d`.
- ty check passes.
- ruff format check passes.
- Pydantic v2 round-trip succeeds; Literal validation enforced.
