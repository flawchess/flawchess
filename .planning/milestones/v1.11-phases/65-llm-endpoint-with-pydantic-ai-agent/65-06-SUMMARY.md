---
phase: 65-llm-endpoint-with-pydantic-ai-agent
plan: "06"
subsystem: backend
tags: [fastapi, router, lifespan, pydantic-ai, llm, http, tdd, changelog]
dependency_graph:
  requires:
    - 65-01 (pydantic-ai installed, settings, system prompt, conftest env var)
    - 65-02 (EndgameInsightsReport, EndgameInsightsResponse, InsightsErrorResponse schemas)
    - 65-05 (generate_insights, get_insights_agent, InsightsRateLimitExceeded, InsightsProviderError, InsightsValidationFailure)
  provides:
    - app/routers/insights.py with POST /insights/endgame + exception-to-HTTP mapping
    - app/main.py lifespan extended with get_insights_agent() startup validation
    - app/main.py includes insights_router under /api
    - tests/test_insights_router.py — 9 end-to-end router tests
    - CHANGELOG.md [Unreleased] Phase 65 bullet
    - SEED-004 closed
  affects:
    - Phase 66 (frontend) depends on POST /api/insights/endgame HTTP contract
tech_stack:
  added: []
  patterns:
    - JSONResponse for error envelopes (not HTTPException) — clean top-level JSON shape per RESEARCH.md §7
    - lifespan calls get_insights_agent() before cleanup_orphaned_jobs() — deploy-blocker contract D-22
    - authed_user_with_session fixture seeds LlmLog rows directly to bypass cost_unknown:test error column
    - FunctionModel with Any-typed callback for error path tests (no pydantic_ai_slim import)
key_files:
  created:
    - app/routers/insights.py
    - tests/test_insights_router.py
  modified:
    - app/main.py
    - CHANGELOG.md
    - .planning/seeds/SEED-004-trend-texture-for-llm-insights.md
decisions:
  - "Used JSONResponse(status_code=..., content=InsightsErrorResponse(...).model_dump()) for error responses — cleaner top-level shape than HTTPException(detail=...) per RESEARCH.md §7"
  - "Cache-hit test seeds a pre-existing LlmLog row with error=None directly rather than relying on a two-request sequence — cost_unknown:test suffix on the 'test' provider model causes get_latest_log_by_hash (error IS NULL filter) to miss rows written by generate_insights in tests"
  - "Rate-limit tests use prompt_version='endgame_v0' for miss rows to be counted by count_recent_successful_misses but excluded by get_latest_report_for_user — same pattern as Plan 05 tests"
  - "FunctionModel error-path tests use 'Any' typed callback parameters to avoid importing pydantic_ai_slim internals"
metrics:
  duration_minutes: 7
  completed_date: "2026-04-21"
  tasks_completed: 4
  tasks_total: 4
  files_created: 2
  files_modified: 3
---

# Phase 65 Plan 06: HTTP Router + Lifespan Wiring + End-to-End Tests Summary

`POST /api/insights/endgame` HTTP surface wired: thin router with exception-to-HTTP mapping, lifespan startup validation of Agent config, 9 end-to-end router tests covering all 5 HTTP status paths, CHANGELOG.md updated, and SEED-004 closed.

## Tasks Completed

| Task | Name | Commit | Key Files |
|------|------|--------|-----------|
| 1 | Create app/routers/insights.py with POST /endgame + exception mapping | 0f2e39a | app/routers/insights.py |
| 2 | Extend app/main.py: register router + add get_insights_agent() to lifespan | 1db59d1 | app/main.py |
| 3 | Create tests/test_insights_router.py with 9 end-to-end tests | 11c95be | tests/test_insights_router.py |
| 4 | Update CHANGELOG.md [Unreleased] and flip SEED-004 to closed | 6ea618e | CHANGELOG.md, .planning/seeds/SEED-004-... |

## What Was Built

### `app/routers/insights.py`

`APIRouter(prefix="/insights", tags=["insights"])` with a single route `POST /endgame`. Thin HTTP layer per D-33:

- Dependencies: `current_active_user` + `get_async_session` (mirrors `endgames.py` layout).
- Query params match `/endgames/overview` signature: `time_control`, `platform`, `recency`, `rated`, `opponent_strength`, `color`.
- Constructs `FilterContext` from params; calls `await insights_llm.generate_insights(filter_context, user.id, session)`.
- Exception-to-HTTP mapping per D-16:
  - `InsightsRateLimitExceeded` → 429 + `InsightsErrorResponse(error="rate_limit_exceeded", retry_after_seconds=N)`
  - `InsightsValidationFailure` → 502 + `InsightsErrorResponse(error="validation_failure")`
  - `InsightsProviderError` → 502 + `InsightsErrorResponse(error="provider_error")`
- Uses `JSONResponse(status_code=..., content=model.model_dump())` for error responses — clean top-level JSON shape.

### `app/main.py` changes

Two additions:

1. **Imports**: `from app.routers.insights import router as insights_router` and `from app.services.insights_llm import get_insights_agent`.
2. **Lifespan**: `get_insights_agent()` called BEFORE `cleanup_orphaned_jobs()` per D-22 — a misconfigured `PYDANTIC_AI_MODEL_INSIGHTS` aborts uvicorn startup before any best-effort cleanup runs.
3. **include_router**: `app.include_router(insights_router, prefix="/api")` placed between `endgames_router` and `users_router`.

Route confirmed: `uv run python -c "from app.main import app; print([r.path for r in app.routes if '/insights/' in r.path])"` → `['/api/insights/endgame']`.

### `tests/test_insights_router.py`

9 tests across 6 classes:

- `TestAuth` (1): unauthenticated POST → 401
- `TestHappyPath` (2): fresh miss → 200 + `status="fresh"`; cache hit via pre-seeded row → 200 + `status="cache_hit"`
- `TestRateLimit` (2): 3 rate-limit misses without tier-2 → 429 + envelope; with tier-2 → 200 + `status="stale_rate_limited"`
- `TestErrors` (2): FunctionModel raises `ModelHTTPError` → 502 `provider_error`; FunctionModel raises `UnexpectedModelBehavior` → 502 `validation_failure`
- `TestHideOverview` (1): `INSIGHTS_HIDE_OVERVIEW=True` → 200 + `report.overview == ""`
- `TestFilterPassing` (1): `time_control=blitz&platform=chess.com` params flow into `FilterContext.time_controls`/`.platforms`

No real provider calls. All LLM interactions mocked via `fake_insights_agent` (TestModel) or `FunctionModel`.

### CHANGELOG.md

Added under `## [Unreleased]`:
- `### Added`: Phase 65 LLM insights endpoint bullet
- `### Changed`: `SubsectionFinding.series` extension bullet

### SEED-004

Status flipped from `dormant` to `closed_superseded_by_phase_65`. Closure note added to body explaining the raw-series approach (D-01) made the seed's `volatility_cv`/`recent_vs_prior_delta` proposals unnecessary.

## Test Suite Results

| Suite | Count | Status |
|-------|-------|--------|
| test_insights_router.py (new) | 9 | All pass |
| Full suite (excluding pre-existing test_reclassify failure) | 1018 | All pass |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] .unique() required for User query with joined eager loads**
- **Found during:** Task 3 test run
- **Issue:** `result.scalar_one()` on a `select(User)` query raised `InvalidRequestError` because FastAPI-Users adds joined eager loads to the User model. SQLAlchemy requires `.unique()` before `.scalar_one()` in this case.
- **Fix:** Changed `result.scalar_one()` to `result.unique().scalar_one()` in the `authed_user_with_session` fixture.
- **Files modified:** `tests/test_insights_router.py`
- **Commit:** `11c95be`

**2. [Rule 1 - Bug] Cache-hit test required direct row seeding instead of two-request flow**
- **Found during:** Task 3 test run
- **Issue:** `create_llm_log` appends `"; cost_unknown:test"` to the `error` column for the `"test"` provider model. `get_latest_log_by_hash` filters `error IS NULL`, so it cannot find rows written by `generate_insights` in the test environment. The two-request approach (first request writes row, second request hits cache) always returned `status="fresh"` on the second call.
- **Fix:** Pre-seeded a `LlmLog` row with `error=None` and `response_json=valid_report.model_dump()` directly via `async_sessionmaker`. One HTTP request then hits this pre-seeded row. Same pattern documented in 65-05-SUMMARY.md deviation #3.
- **Files modified:** `tests/test_insights_router.py`
- **Commit:** `11c95be`

**3. [Rule 1 - Bug] Wrong pydantic_ai import path for FunctionModel error tests**
- **Found during:** Task 3 ty check
- **Issue:** Test draft used `from pydantic_ai_slim.pydantic_ai.messages import ModelMessage, ModelResponse` — this path does not resolve as a top-level package under `pydantic_ai`. ty reported `unresolved-import`.
- **Fix:** Used `Any`-typed callback parameters for FunctionModel functions (no import of internal message types needed), matching the pattern in `test_insights_llm.py`.
- **Files modified:** `tests/test_insights_router.py`
- **Commit:** `11c95be`

## Known Stubs

None. All four tasks delivered complete implementation. No placeholder values or TODO markers.

## Threat Surface Scan

`POST /api/insights/endgame` is the new HTTP entry point. All threat mitigations from the plan's threat register are implemented:

| Threat | Mitigation | Verified |
|--------|-----------|---------|
| T-65-01: Auth bypass | `Depends(current_active_user)` on route | `test_unauthenticated_returns_401` |
| T-65-02: Rate-limit evasion | Router passes `user.id` from dependency, never from request | code review |
| T-65-05: Error body leak | `InsightsErrorResponse` uses stable Literal markers only | `test_provider_error_returns_502`, `test_validation_failure_returns_502` |
| T-65-06: Misconfig startup | `get_insights_agent()` before `cleanup_orphaned_jobs()` in lifespan | lifespan code + manual verify |
| T-65-02: Cost exhaustion | 3-miss rate limit enforced by service layer | `test_429_when_rate_limited_without_tier2` |

## Self-Check: PASSED

- `app/routers/insights.py` exists: FOUND
- `tests/test_insights_router.py` exists: FOUND
- `app/main.py` contains `get_insights_agent()` before `cleanup_orphaned_jobs`: FOUND
- `app/main.py` contains `app.include_router(insights_router`: FOUND
- `CHANGELOG.md` contains "Phase 65": FOUND
- `SEED-004` status `closed_superseded_by_phase_65`: FOUND
- Commit `0f2e39a` (insights router): FOUND
- Commit `1db59d1` (main.py wiring): FOUND
- Commit `11c95be` (router tests): FOUND
- Commit `6ea618e` (CHANGELOG + SEED-004): FOUND
- `uv run ty check app/ tests/`: 0 errors
- `uv run ruff check app/ tests/`: 0 errors
- `uv run pytest tests/test_insights_router.py`: 9 passed
- Full suite (excluding test_reclassify): 1018 passed
- Route `/api/insights/endgame` registered: CONFIRMED
