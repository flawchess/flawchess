---
phase: 65-llm-endpoint-with-pydantic-ai-agent
plan: "02"
subsystem: schemas
tags: [pydantic, schemas, llm, insights, tdd]
dependency_graph:
  requires: []
  provides:
    - app/schemas/insights.py::TimePoint
    - app/schemas/insights.py::SectionInsight
    - app/schemas/insights.py::EndgameInsightsReport
    - app/schemas/insights.py::EndgameInsightsResponse
    - app/schemas/insights.py::InsightsErrorResponse
    - app/schemas/insights.py::InsightsStatus
    - app/schemas/insights.py::InsightsError
    - app/schemas/insights.py::SubsectionFinding.series
  affects:
    - app/schemas/insights.py (extended)
    - tests/test_insights_schema.py (extended)
tech_stack:
  added: []
  patterns:
    - Pydantic v2 model_validator(mode="after") for cross-field validation
    - Forward reference string annotation for self-referential model (TimePoint in SubsectionFinding)
    - model_rebuild() to resolve forward references after full class definitions
key_files:
  created: []
  modified:
    - app/schemas/insights.py
    - tests/test_insights_schema.py
decisions:
  - "Used string forward reference 'TimePoint' in SubsectionFinding.series annotation + model_rebuild() call to resolve; avoids reordering class definitions"
  - "Updated two Phase 63 tests (test_field_order_locked, test_all_contains_expected_names) to reflect planned schema extension — these were intentionally broken by Phase 65 additions"
  - "Used ty: ignore[...] syntax (not type: ignore) per CLAUDE.md for all intentional type violations in tests"
metrics:
  duration_seconds: 367
  completed_date: "2026-04-21"
  tasks_completed: 2
  files_modified: 2
---

# Phase 65 Plan 02: Phase 65 Pydantic Schema Extensions Summary

Phase 65 schema contract landed: 5 new Pydantic classes, 2 Literal aliases, and one append-only field extension to the existing `SubsectionFinding` model. All 48 tests pass (22 new + 26 existing); ty and ruff clean; full suite 970 passed.

## What Was Built

### New Literal Aliases (2)

- `InsightsStatus = Literal["fresh", "cache_hit", "stale_rate_limited"]` — HTTP 200 response discriminator for Plan 05/06/07 and Phase 66 TanStack Query branching.
- `InsightsError = Literal["rate_limit_exceeded", "provider_error", "validation_failure", "config_error"]` — HTTP 4xx/5xx error codes; frontend owns user-facing copy.

### New Pydantic Classes (5)

| Class | Purpose |
|-------|---------|
| `TimePoint` | One point on a resampled timeseries (bucket_start: ISO date, value: float, n: int) |
| `SectionInsight` | One LLM report section (section_id: SectionId, headline <=120 chars, bullets <=2) |
| `EndgameInsightsReport` | Full LLM output (overview: str, sections 1-4, model_used, prompt_version) + unique_section_ids validator |
| `EndgameInsightsResponse` | HTTP 200 envelope (report, status: InsightsStatus, stale_filters: FilterContext | None) |
| `InsightsErrorResponse` | HTTP 4xx/5xx envelope (error: InsightsError, retry_after_seconds: int | None) |

### SubsectionFinding Extension (1 field)

`series: list["TimePoint"] | None = None` appended as the LAST field after `dimension`. Declaration order is load-bearing for `findings_hash` stability — confirmed by `TestSubsectionFindingSeries::test_series_declaration_is_last_field`.

### `__all__` Growth

11 exports (Phase 63) -> 18 exports (Phase 65). Added: `EndgameInsightsReport`, `EndgameInsightsResponse`, `InsightsError`, `InsightsErrorResponse`, `InsightsStatus`, `SectionInsight`, `TimePoint`.

## Test Count Added

22 new tests across 6 new test classes:
- `TestTimePoint` (2 tests)
- `TestSectionInsight` (4 tests)
- `TestEndgameInsightsReport` (6 tests)
- `TestEndgameInsightsResponse` (3 tests)
- `TestInsightsErrorResponse` (3 tests)
- `TestSubsectionFindingSeries` (3 tests, including hash-stability invariant assertion)

## Hash Stability Confirmation

`SubsectionFinding.model_fields.keys()[-1] == "series"` asserted by test. Pre-Phase-65 rows (no `series` in their JSON) continue to hash identically because Pydantic serialises absent optional fields as null — and the `series=None` value is consistent whether decoded by old or new code.

## TDD Gate Compliance

- RED commit: `3a977ac` — failing tests (ImportError on non-existent schemas)
- GREEN commit: `3dfbf7b` — schema implementation + test updates; all 48 pass

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Updated two Phase 63 tests broken by planned Phase 65 additions**
- **Found during:** GREEN phase after running full test suite
- **Issue:** `TestSubsectionFinding::test_field_order_locked` asserted 12 fields; Phase 65 adds `series` as 13th. `TestModuleAll::test_all_contains_expected_names` asserted the old 11-name `__all__`; Phase 65 adds 7 more.
- **Fix:** Updated both tests to include the new field and new exports — this is the intended post-Phase-65 state documented in the plan.
- **Files modified:** `tests/test_insights_schema.py`
- **Commit:** `3dfbf7b`

**2. [Rule 2 - ty compliance] Replaced `type: ignore` with `ty: ignore` in new test code**
- **Found during:** GREEN phase ty check
- **Issue:** Plan template used `# type: ignore[...]` syntax; CLAUDE.md requires `# ty: ignore[rule-name]` throughout.
- **Fix:** Changed all 5 intentional type-violation suppressions in new tests to use `ty: ignore[missing-argument]` or `ty: ignore[invalid-argument-type]`.
- **Files modified:** `tests/test_insights_schema.py`
- **Commit:** `3dfbf7b`

**3. [Rule 2 - Forward reference resolution] Added `model_rebuild()` call**
- **Found during:** Implementation
- **Issue:** `SubsectionFinding.series` uses `list["TimePoint"] | None` with a forward reference because `TimePoint` is defined after `SubsectionFinding` in the file (per plan's ordering: new classes go after `EndgameTabFindings`). Without `model_rebuild()`, Pydantic cannot resolve the forward ref at runtime.
- **Fix:** Added `SubsectionFinding.model_rebuild()` at the end of the module after `TimePoint` is fully defined.
- **Files modified:** `app/schemas/insights.py`
- **Commit:** `3dfbf7b`

## Known Stubs

None. All schemas are fully wired — no placeholder values or TODO fields.

## Threat Flags

No new threat surface introduced. The schemas implement mitigations T-65-10, T-65-11, and T-65-12 as planned.

## Self-Check: PASSED

| Item | Status |
|------|--------|
| `app/schemas/insights.py` | FOUND |
| `tests/test_insights_schema.py` | FOUND |
| `65-02-SUMMARY.md` | FOUND |
| Commit `3a977ac` (RED tests) | FOUND |
| Commit `3dfbf7b` (GREEN impl) | FOUND |
