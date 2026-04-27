---
phase: 70-backend-opening-insights-service
plan: "01"
subsystem: backend-schema-test-scaffolding
tags: [opening-insights, schema, pydantic, tdd, wave-0]
dependency_graph:
  requires: []
  provides: [opening-insights-schema, wave-0-test-scaffolding]
  affects:
    - app/schemas/opening_insights.py
    - tests/services/test_opening_insights_service.py
    - tests/repositories/test_opening_insights_repository.py
    - tests/services/test_opening_insights_arrow_consistency.py
    - tests/routers/test_insights_openings.py
tech_stack:
  added: []
  patterns: [pydantic-v2-literal-validation, tdd-red, importorskip-guards]
key_files:
  created:
    - app/schemas/opening_insights.py
    - tests/services/test_opening_insights_service.py
    - tests/repositories/test_opening_insights_repository.py
    - tests/services/test_opening_insights_arrow_consistency.py
    - tests/routers/test_insights_openings.py
    - tests/repositories/__init__.py
    - tests/routers/__init__.py
  modified: []
decisions:
  - "Schema decoupled from app.schemas.insights.FilterContext (D-11) — fresh request shape for openings even though the filter axes overlap with endgame insights"
  - "64-bit hash fields typed as `str` to survive JSON precision (entry_full_hash, resulting_full_hash) per OpeningWDL.full_hash convention"
  - "No `source` field on findings (D-18 — bookmarks dropped as algorithm input)"
  - "Wave 0 tests use pytest.importorskip + NotImplementedError so they collect cleanly but fail until downstream waves implement"
metrics:
  shipped_in_pr: "#66 (df9b689)"
  files_created: 7
  schema_lines: 73
ship_status: shipped
---

# Phase 70 Plan 01: Schemas + Wave 0 Test Scaffolding (retroactive summary)

**One-liner:** Locked the OpeningInsightsRequest/Finding/Response Pydantic v2 contract and laid down failing-by-design Wave 0 tests that downstream plans flipped green.

## Tasks Completed

| Task | Name | Files |
|------|------|-------|
| 1 | OpeningInsightsRequest / OpeningInsightFinding / OpeningInsightsResponse schemas | app/schemas/opening_insights.py |
| 2 | Wave 0 test scaffolding (service, repository, arrow-consistency, router) | tests/{services,repositories,routers}/test_opening_insights_*.py |

## What Was Built

- `app/schemas/opening_insights.py` (~73 lines) — three Pydantic v2 models with Literal-enum validation on recency, time_control, platform, opponent_type, opponent_strength, color. Hash fields `str`-typed at the API boundary; no FilterContext reuse from app.schemas.insights.
- 4 new test files plus 2 `__init__.py` markers under `tests/repositories/` and `tests/routers/`. Each test file uses `pytest.importorskip` against the not-yet-existing service/router modules so the suite stays collectable through Wave 1, then turns red once those modules land in Wave 2-4.
- Test names pinned the per-requirement coverage matrix from RESEARCH.md §Test Map (classification boundaries, evidence floor, dedupe, attribution, ranking, caps, color optimization, bookmarks-not-consumed regression).

## Deviations from Plan

None worth noting — schema and test scaffolding shipped as planned. The schema gained an `entry_san_sequence` field later in Phase 71 Plan 01 (not part of this plan).

## TDD Gate Compliance

RED — all four Wave 0 test files collect under pytest but fail (importorskip-skipped or NotImplementedError-raising). No spurious passes.

## Self-Check

- [x] app/schemas/opening_insights.py exists and ty/ruff clean
- [x] Schema has no FilterContext import (D-11)
- [x] Schema has no `source` field (D-18)
- [x] All 4 Wave 0 test files exist with required test function names
- [x] Shipped as part of PR #66 (df9b689)
