---
phase: 71-frontend-stats-subtab-openinginsightsblock
plan: "01"
subsystem: backend-schema-service
tags: [opening-insights, schema, pydantic, tdd]
dependency_graph:
  requires: [phase-70-opening-insights-service]
  provides: [entry_san_sequence-wire-field]
  affects: [app/schemas/opening_insights.py, app/services/opening_insights_service.py]
tech_stack:
  added: []
  patterns: [pydantic-v2-required-field, tdd-red-green]
key_files:
  created: []
  modified:
    - app/schemas/opening_insights.py
    - app/services/opening_insights_service.py
    - tests/services/test_opening_insights_service.py
decisions:
  - "entry_san_sequence is required (no default) — empty entry position would mask a genuine bug since entry_ply >= 3 always"
  - "Field placed between entry_fen and entry_full_hash for logical grouping with other entry-* fields"
metrics:
  duration: "~10 minutes"
  completed: "2026-04-27"
  tasks_completed: 2
  files_modified: 3
---

# Phase 71 Plan 01: Add entry_san_sequence to OpeningInsightFinding Summary

**One-liner:** Additive `entry_san_sequence: list[str]` field on `OpeningInsightFinding` schema, wired from the already-fetched repository row column, unblocking Phase 71 frontend deep-link replay (D-13).

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Add entry_san_sequence field to OpeningInsightFinding schema | 868d9ab | app/schemas/opening_insights.py |
| 2 | Pass entry_san_sequence through service constructor + extend test coverage | a28afaa | app/services/opening_insights_service.py, tests/services/test_opening_insights_service.py |

## What Was Built

- `OpeningInsightFinding.entry_san_sequence: list[str]` field added between `entry_fen` and `entry_full_hash` in the Pydantic schema. Required (no default) since entry_ply >= 3 always yields a non-empty sequence.
- Service constructor now passes `entry_san_sequence=list(row.entry_san_sequence or [])` to `OpeningInsightFinding(...)`. No new query, no migration — `row.entry_san_sequence` was already fetched by the repository and used internally for FEN replay.
- New test `test_finding_includes_entry_san_sequence` asserts: list type, all-string elements, length >= 3, and FEN-replay consistency (replaying the sequence on a fresh `chess.Board` must reproduce `finding.entry_fen`).
- All 22 tests pass (20 opening insights + 2 arrow consistency).

## Deviations from Plan

None — plan executed exactly as written.

## TDD Gate Compliance

- RED: Schema field added in Task 1 caused existing tests to fail with `ValidationError: entry_san_sequence Field required` before the service constructor was updated.
- GREEN: Service constructor fix + new test passed all 22 tests.
- No REFACTOR needed.

## Known Stubs

None — `entry_san_sequence` is fully wired from repository row to wire schema.

## Threat Flags

None — no new network endpoints, auth paths, or schema changes at trust boundaries. The field is purely additive on an existing response model.

## Self-Check: PASSED

- [x] app/schemas/opening_insights.py exists and contains `entry_san_sequence: list[str]`
- [x] app/services/opening_insights_service.py exists and contains `entry_san_sequence=list(row.entry_san_sequence or [])`
- [x] tests/services/test_opening_insights_service.py exists and contains `entry_san_sequence` assertions
- [x] Commit 868d9ab exists (schema)
- [x] Commit a28afaa exists (service + tests)
- [x] All 22 tests pass
- [x] ty check app/ tests/ passes with zero errors
- [x] ruff check passes with zero errors
