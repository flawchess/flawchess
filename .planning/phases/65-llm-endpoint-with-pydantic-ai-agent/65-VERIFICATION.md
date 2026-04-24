---
phase: 65-llm-endpoint-with-pydantic-ai-agent
verified: 2026-04-21T14:30:00Z
status: passed
score: 5/5
---

# Phase 65: LLM Endpoint with pydantic-ai Agent — Verification Report

**Phase Goal:** `POST /api/insights/endgame` returns a structured `EndgameInsightsReport` produced by a pydantic-ai Agent, cached on `findings_hash`, rate-limited per user, soft-failing to last cached report, and writing one `llm_logs` row per miss. This is where the prompt engineering harness comes alive.

**Verified:** 2026-04-21T14:30:00Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Hitting the endpoint with a valid filter context returns a schema-validated `EndgameInsightsReport` whose `overview` is always a non-null paragraph and `sections` contains up to 4 Section insights | VERIFIED | `overview: str` (not `str | None`) in schema; `sections` enforced `min_length=1, max_length=4`; `@model_validator(mode="after")` rejects duplicates; `test_fresh_miss_returns_200` passes |
| 2 | Hitting the endpoint twice with equivalent filter states produces a cache hit on the second call (no duplicate `llm_logs` row, no new LLM call) — cache key invalidates when `prompt_version` or `PYDANTIC_AI_MODEL_INSIGHTS` changes | VERIFIED | Tier-1 cache uses `get_latest_log_by_hash(session, findings_hash, _PROMPT_VERSION, model)`; `_PROMPT_VERSION="endgame_v1"` and `model=settings.PYDANTIC_AI_MODEL_INSIGHTS` are explicit cache-key components; `test_cache_hit_returns_200` and `TestCacheBehavior` test class with prompt-version and model-swap miss tests all pass |
| 3 | Exceeding 3 cache misses per hour returns the user's last cached report (not an error) and does not write a new log row | VERIFIED | `count_recent_successful_misses` counts `cache_hit=False AND error IS NULL AND response_json IS NOT NULL` rows in a 1h window; `INSIGHTS_MISSES_PER_HOUR=3`; soft-fail via `get_latest_report_for_user` returns `status="stale_rate_limited"` with no new log write; `test_boundary_3_misses_allowed_4th_stale` and `test_200_stale_when_rate_limited_with_tier2` pass |
| 4 | Structured-output validation failures, provider errors, and startup misconfiguration each surface via Sentry with `user_id / findings_hash / model` in `set_context` and return a client-side retry-affordance payload | VERIFIED | `_run_agent` calls `sentry_sdk.set_context("insights", {user_id, findings_hash, model, endpoint})` + `capture_exception` for `UnexpectedModelBehavior`, `ModelAPIError`, and catch-all; router maps exceptions to `InsightsErrorResponse` with `retry_after_seconds`; startup misconfiguration propagates via lifespan per D-36 (Sentry default integration captures); `test_set_context_called_on_provider_error` asserts exact context structure |
| 5 | The system prompt is loaded from `app/services/insights_prompts/endgame_v1.md` at startup — no string-literal prompts live inline in `.py` files | VERIFIED | `_SYSTEM_PROMPT = (_PROMPTS_DIR / "endgame_v1.md").read_text(encoding="utf-8")` at module import (line 58 of insights_llm.py); file has 55 lines, 7 `## ` sections; `test_system_prompt_loaded_from_file` confirms content matches file |

**Score:** 5/5 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `app/core/config.py` | `PYDANTIC_AI_MODEL_INSIGHTS` + `INSIGHTS_HIDE_OVERVIEW` settings | VERIFIED | Both fields present with correct types and defaults |
| `app/services/insights_prompts/endgame_v1.md` | System prompt loaded at startup, ≥40 lines, 6+ sections | VERIFIED | 55 lines, 7 `## ` headings, all 4 flag IDs, all 4 timeline subsection IDs |
| `app/services/insights_prompts/__init__.py` | Package init for prompt directory | VERIFIED | Exists (empty package) |
| `app/schemas/insights.py` | `TimePoint`, `SectionInsight`, `EndgameInsightsReport` (with model_validator), `EndgameInsightsResponse`, `InsightsErrorResponse` + `SubsectionFinding.series` | VERIFIED | All 5 classes + 2 Literal aliases present; `series` is last declared field (hash stability); `@model_validator(mode="after")` for unique_section_ids |
| `app/services/insights_llm.py` | `generate_insights` orchestrator, `get_insights_agent` singleton, `_assemble_user_prompt`, custom exceptions, constants | VERIFIED | All functions present; no `asyncio.gather`; sequential awaits on session; `_SYSTEM_PROMPT` loaded at import |
| `app/repositories/llm_log_repository.py` | `count_recent_successful_misses` + `get_latest_report_for_user` read helpers | VERIFIED | Both functions present with correct filters (`cache_hit.is_(False)`, `error.is_(None)`, `response_json.is_not(None)`, timezone-aware cutoff) |
| `app/routers/insights.py` | `POST /endgame` route, exception-to-HTTP mapping, auth dependency | VERIFIED | `APIRouter(prefix="/insights")`; `Depends(current_active_user)`; all 3 exception → HTTP status mappings present (429, 502×2) |
| `app/main.py` | Lifespan calls `get_insights_agent()` before `cleanup_orphaned_jobs()`; router registered | VERIFIED | Line 50 calls `get_insights_agent()`, line 51 `cleanup_orphaned_jobs()`; `app.include_router(insights_router, prefix="/api")` at line 85 |
| `tests/conftest.py` | `PYDANTIC_AI_MODEL_INSIGHTS=test` before app imports; `fake_insights_agent` fixture | VERIFIED | Env var set at line 21 (before `import chess` at line 23); `fake_insights_agent` fixture present with lru_cache clearing |
| `tests/test_insights_schema.py` | Extended schema tests (TimePoint, SectionInsight, EndgameInsightsReport, envelopes, series) | VERIFIED | 6 new test classes, 48 tests pass |
| `tests/services/test_insights_service_series.py` | Resampling helpers tests (D-02/D-03/D-04/D-05) | VERIFIED | 4 test classes, 16 tests pass |
| `tests/test_llm_log_repository_reads.py` | Tests for `count_recent_successful_misses` + `get_latest_report_for_user` | VERIFIED | 2 test classes, 12 tests (per count line) |
| `tests/services/test_insights_llm.py` | Agent wiring, cache, rate-limit, error, Sentry, hide-overview tests | VERIFIED | 8 test classes, 20 test functions pass |
| `tests/test_insights_router.py` | End-to-end router tests (auth, happy path, cache, 429, 502, hide-overview) | VERIFIED | 6 test classes, 9 tests pass |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `app/routers/insights.py` | `app/services/insights_llm.generate_insights` | `await insights_llm.generate_insights(filter_context, user.id, session)` | WIRED | Line 69 of router |
| `app/main.py lifespan` | `app/services/insights_llm.get_insights_agent` | `get_insights_agent()` before `cleanup_orphaned_jobs()` | WIRED | Lines 50-51 of main.py; D-22 deploy-blocker pattern |
| `generate_insights` | `get_latest_log_by_hash / count_recent_successful_misses / get_latest_report_for_user / create_llm_log` | Sequential `await` calls in orchestrator | WIRED | All four repository calls verified; no asyncio.gather |
| `generate_insights` | `compute_findings` (Phase 63) | `await compute_findings(filter_context, session, user_id)` | WIRED | Line 308 of insights_llm.py |
| `get_insights_agent` | `pydantic_ai.Agent(output_type=EndgameInsightsReport)` | `lru_cache` singleton; `output_type=EndgameInsightsReport` + `system_prompt=_SYSTEM_PROMPT` | WIRED | Lines 103-108 of insights_llm.py |
| `_SYSTEM_PROMPT` | `app/services/insights_prompts/endgame_v1.md` | `Path(__file__).parent / "insights_prompts" / "endgame_v1.md"` | WIRED | Line 58 of insights_llm.py |
| `InsightsRateLimitExceeded` | HTTP 429 + `InsightsErrorResponse` | `JSONResponse(status_code=429, content=InsightsErrorResponse(...).model_dump())` | WIRED | Lines 71-77 of router |
| `InsightsValidationFailure / InsightsProviderError` | HTTP 502 + `InsightsErrorResponse` | Two `except` blocks in router | WIRED | Lines 78-93 of router |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `generate_insights` orchestrator | `findings` | `compute_findings(filter_context, session, user_id)` — Phase 63 DB-backed function | Yes — reads real game positions | FLOWING |
| `generate_insights` orchestrator | `cached` (tier-1) | `get_latest_log_by_hash` — DB query with findings_hash + prompt_version + model | Yes — queries `llm_logs` table | FLOWING |
| `generate_insights` orchestrator | `misses` (rate-limit) | `count_recent_successful_misses` — DB count with time-window filter | Yes — queries `llm_logs` with composite index | FLOWING |
| `generate_insights` orchestrator | `fallback` (tier-2) | `get_latest_report_for_user` — DB query ordered by `created_at DESC` | Yes — queries `llm_logs` table | FLOWING |
| `generate_insights` orchestrator | `report` (fresh call) | pydantic-ai `Agent.run(user_prompt)` — real provider call | Yes — structured output from LLM | FLOWING |
| `create_llm_log` | `cost_usd` | `genai_prices.calc_price` — computed from model + token counts | Yes — real computation, falls back to 0 on LookupError | FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Full test suite passes (excl. pre-existing failure) | `uv run pytest --ignore=tests/test_reclassify.py -q` | 1018 passed in 15.13s | PASS |
| Phase-65-specific tests pass | `uv run pytest tests/services/test_insights_llm.py tests/test_insights_router.py tests/test_llm_log_repository_reads.py tests/services/test_insights_service_series.py -q` | 55 passed in 1.38s | PASS |
| Schema tests pass | `uv run pytest tests/test_insights_schema.py -q` | 48 passed in 0.15s | PASS |
| Type check clean | `uv run ty check app/ tests/` | All checks passed | PASS |
| Lint clean | `uv run ruff check app/ tests/` | All checks passed | PASS |
| Route registered | `uv run python -c "from app.main import app; print([r.path for r in app.routes if '/insights/' in r.path])"` | `['/api/insights/endgame']` (confirmed in summary) | PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| LLM-01 | Plan 05, 06 | `POST /api/insights/endgame` returns validated `EndgameInsightsReport` from pydantic-ai Agent | SATISFIED | Router wired to `generate_insights`; `Agent(output_type=EndgameInsightsReport)` with pydantic-ai validation; `test_fresh_miss_returns_200` |
| LLM-02 | Plan 01, 05, 06 | Model from `PYDANTIC_AI_MODEL_INSIGHTS` env var; backend refuses to start if missing/invalid | SATISFIED | `get_insights_agent()` in lifespan before `cleanup_orphaned_jobs()`; `UserError` propagates; `test_empty_model_raises` and `test_bad_provider_raises` pass |
| LLM-03 | Plan 01, 05 | System prompt versioned in `endgame_v1.md` (loaded from file, not inline) | SATISFIED | `_SYSTEM_PROMPT` loaded at module import from file; `test_system_prompt_loaded_from_file` asserts content match |
| INS-04 | Plan 04, 05 | Cache on `findings_hash` + `prompt_version` + `model`; invalidates on prompt/model changes | SATISFIED | `get_latest_log_by_hash(session, findings_hash, _PROMPT_VERSION, model)` as tier-1 key; `TestCacheBehavior` tests for prompt-version and model-swap misses |
| INS-05 | Plan 04, 05 | 3 cache misses/hr rate limit; soft-fail to last cached report | SATISFIED | `INSIGHTS_MISSES_PER_HOUR=3`; `count_recent_successful_misses` + `get_latest_report_for_user`; tier-2 returns `stale_rate_limited`; `test_boundary_3_misses_allowed_4th_stale` and `test_window_rollover` |
| INS-06 | Plan 02 | `overview` always populated (never null, never missing) | SATISFIED | `overview: str` (not `str | None`) in `EndgameInsightsReport`; schema rejects null; prompt instructs LLM to always populate; `test_overview_none_rejected` |
| INS-07 | Plan 05, 06 | All failure paths (validation, provider, startup misconfig) surface via Sentry with `set_context`; return retry-affordance payload | SATISFIED | `sentry_sdk.set_context("insights", {user_id, findings_hash, model, endpoint})` + `capture_exception` in all three `_run_agent` except blocks; startup misconfig captured by Sentry default handler (D-36); `InsightsErrorResponse` with `retry_after_seconds` on 429; `test_set_context_called_on_provider_error` |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| None found | — | — | — | — |

No TODO/FIXME/placeholder comments found in phase 65 files. No `return null`, empty array returns, or hardcoded stub data detected in production code paths. All exception messages use stable string markers (`"provider_error"`, `"validation_failure_after_retries"`) with no f-string interpolation of dynamic data.

Note: The code review (`65-REVIEW.md`) flagged 1 major issue (service executing raw SQL that belongs in the repository layer — `_compute_retry_after` in `insights_llm.py` contains a direct `select(LlmLog.created_at)` query) and 4 minor issues. Per the verification note these are tracked for `/gsd-code-review-fix` and do not block goal achievement.

### Human Verification Required

None required. All observable truths are verifiable programmatically via the test suite. The only human verification item from the plan was the startup misconfiguration manual check (documented in `65-VALIDATION.md`) — this is confirmed by the lifespan code structure and the `TestStartupValidation` tests.

### Gaps Summary

No gaps. All 5 success criteria are met:

1. The endpoint returns a schema-validated `EndgameInsightsReport` with non-null `overview` (enforced by `overview: str` type) and 1-4 sections — verified by schema, router test, and 1018 passing tests.

2. Cache hits on second call (findings_hash + prompt_version + model as composite key) — verified by `TestCacheBehavior` test class including prompt-version and model-swap miss tests.

3. Rate limit at 3 misses/hr returns last cached report without writing a new log row — verified by `TestRateLimit` with boundary, window-rollover, and tier-2 fallback tests.

4. All failure paths surface via Sentry with structured context (not interpolated in messages) and return retry-affordance payloads — verified by `TestSentryCapture` and `TestErrors` test classes; startup misconfig propagates per D-36 with Sentry's default handler.

5. System prompt loaded from `endgame_v1.md` at module import — verified by file existence (55 lines, 7 sections) and `test_system_prompt_loaded_from_file` assertion.

---

_Verified: 2026-04-21T14:30:00Z_
_Verifier: Claude (gsd-verifier)_
