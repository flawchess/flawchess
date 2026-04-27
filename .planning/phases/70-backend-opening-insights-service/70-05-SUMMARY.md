---
phase: 70-backend-opening-insights-service
plan: "05"
subsystem: backend-router-and-docs
tags: [opening-insights, router, fastapi, security, requirements, changelog]
dependency_graph:
  requires: [70-01, 70-04]
  provides: ["POST /api/insights/openings"]
  affects:
    - app/routers/insights.py
    - app/schemas/opening_insights.py
    - tests/routers/test_insights_openings.py
    - .planning/REQUIREMENTS.md
    - .planning/milestones/v1.13-ROADMAP.md
    - CHANGELOG.md
tech_stack:
  added: []
  patterns: [fastapi-current-active-user, pydantic-extra-forbid, thin-router-pass-through]
key_files:
  created: []
  modified:
    - app/routers/insights.py
    - app/schemas/opening_insights.py
    - tests/routers/test_insights_openings.py
    - .planning/REQUIREMENTS.md
    - .planning/milestones/v1.13-ROADMAP.md
    - CHANGELOG.md
decisions:
  - "Route mounted as relative path `/openings` on existing `/insights` APIRouter (CLAUDE.md §Router Convention) — full URL POST /api/insights/openings"
  - "OpeningInsightsRequest gets `model_config = ConfigDict(extra='forbid')` — defense-in-depth against user_id smuggling; the schema also has no user_id field"
  - "Router does NOT call `_validate_full_history_filters` (D-14) — every filter reshapes findings; regression-locked by test_post_openings_endpoint_does_NOT_apply_full_history_gate"
  - "No try/except in the router — exceptions propagate to FastAPI's global handler (Sentry-wired in app/main.py); service-layer Sentry capture in Plan 70-04 already covers context"
metrics:
  shipped_in_pr: "#66 (df9b689)"
  router_lines_added: 26
  router_test_lines: 154
  source_docs_amended: 3
  tests_passing: "all 6 router contract tests"
ship_status: shipped
---

# Phase 70 Plan 05: HTTP Boundary + Source-Document Reconciliation (retroactive summary)

**One-liner:** Wired the POST /api/insights/openings route, locked the security gate, and reconciled REQUIREMENTS / ROADMAP / CHANGELOG with the algorithm redesign — phase-closing commit.

## Tasks Completed

| Task | Name | Files |
|------|------|-------|
| 1 | POST /openings route + extra=forbid security gate; turn 6 router tests green | app/routers/insights.py, app/schemas/opening_insights.py, tests/routers/test_insights_openings.py |
| 2 | Apply REQUIREMENTS.md (D-15/D-16/D-17), v1.13-ROADMAP.md (D-15), CHANGELOG.md amendments | .planning/REQUIREMENTS.md, .planning/milestones/v1.13-ROADMAP.md, CHANGELOG.md |

## What Was Built

- `@router.post("/openings", response_model=OpeningInsightsResponse)` on the existing `/insights` APIRouter. Thin pass-through: `await compute_insights(session=session, user_id=user.id, request=request)`. user_id derived from `current_active_user` only.
- `OpeningInsightsRequest.model_config = ConfigDict(extra="forbid")` — unknown body fields (including user_id) return 422. The schema also has zero `user_id`-related fields.
- 6 router contract tests pass: 401 without auth; 200 + four-section response with valid auth; 422 on invalid recency value; 422 on user_id smuggle; 200 (NOT 400) on filters that would trigger the endgame full-history gate; filter-equivalence for two identical authenticated POSTs.
- REQUIREMENTS.md INSIGHT-CORE-02/04/05 amended per D-15/D-16 (transition aggregation, MIN_GAMES_PER_CANDIDATE = 20 floor, strict `>` 0.55 boundary, bookmarks NOT consumed).
- v1.13-ROADMAP.md Phase 70 success-criterion 2 and 4 rewritten per D-15.
- CHANGELOG.md `[Unreleased]` § Changed: one bullet covering the algorithm shift + classifier alignment + ix_gp_user_game_ply.

## Deviations from Plan

None — plan executed as written, including the coupled-commit pattern with Plan 70-04 (single PR #66).

## Verification

Full backend gate green: `uv run ruff check .` + `uv run ty check app/ tests/` + `uv run pytest -x` all pass. Route registered on FastAPI app (`/api/insights/openings` discoverable in `app.routes`).

## Follow-up

- Production deploy of the CONCURRENTLY migration: ~30-60s wall time on Hikaru-class users.
- Sentry tag `openings.attribution.unmatched_dropped` introduced in Plan 70-04 — monitor drop rate post-deploy to validate parent-lineage walk coverage.
- Phase 71 frontend follow-up consumes this endpoint via `useOpeningInsights` hook.

## Self-Check

- [x] POST /api/insights/openings registered with current_active_user dependency
- [x] OpeningInsightsRequest has extra="forbid" and no user_id field
- [x] Router does NOT call _validate_full_history_filters
- [x] All 6 router tests pass
- [x] REQUIREMENTS / ROADMAP / CHANGELOG reflect the algorithm redesign
- [x] Shipped as part of PR #66 (df9b689)
