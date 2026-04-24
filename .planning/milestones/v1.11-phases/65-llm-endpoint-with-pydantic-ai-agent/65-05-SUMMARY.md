---
phase: 65-llm-endpoint-with-pydantic-ai-agent
plan: "05"
subsystem: backend
tags: [pydantic-ai, llm, orchestration, cache, rate-limit, soft-fail, sentry, tdd]
dependency_graph:
  requires:
    - 65-01 (pydantic-ai installed, settings, system prompt, conftest env var)
    - 65-02 (EndgameInsightsReport, EndgameInsightsResponse, InsightsErrorResponse schemas)
    - 65-03 (compute_findings populates series on 4 timeline subsections)
    - 65-04 (count_recent_successful_misses, get_latest_report_for_user repo helpers)
  provides:
    - app/services/insights_llm.py with generate_insights, get_insights_agent, all helpers
    - InsightsRateLimitExceeded, InsightsProviderError, InsightsValidationFailure exceptions
    - INSIGHTS_MISSES_PER_HOUR=3, _PROMPT_VERSION='endgame_v1' public constants
    - tests/services/test_insights_llm.py with 20 tests covering LLM-01/LLM-02/INS-04/INS-05/INS-06
    - fake_insights_agent fixture in tests/conftest.py
  affects:
    - Plan 06 (router calls generate_insights as sole orchestration entry point)
tech_stack:
  added: []
  patterns:
    - functools.lru_cache(maxsize=1) for Agent singleton — single instance across app lifetime
    - Tiered cache: tier-1 exact hash match, tier-2 user+era fallback, tier-3 HTTP 429
    - create_llm_log owns its session (Phase 64 D-02) — log row persists even if caller rolls back
    - Sentry set_context with structured dict (user_id, findings_hash, model, endpoint); never f-strings
    - All session awaits sequential (CLAUDE.md AsyncSession constraint; no asyncio.gather)
    - FunctionModel + TestModel for test doubles; FunctionModel raises ModelHTTPError for error path tests
    - Seeded miss rows use old prompt_version to avoid polluting tier-2 fallback lookups
key_files:
  created:
    - app/services/insights_llm.py
    - tests/services/test_insights_llm.py
  modified:
    - tests/conftest.py
decisions:
  - "_SYSTEM_PROMPT loaded at module import (not lazily in get_insights_agent) — fail-fast if file missing"
  - "generate_insights reads model = settings.PYDANTIC_AI_MODEL_INSIGHTS at call time (not at import) — tests can monkeypatch settings before calling"
  - "Test seed rows for rate-limit tests use prompt_version='endgame_v0' to be counted by count_recent_successful_misses but excluded by get_latest_report_for_user (prompt_version filter)"
  - "row.error assertions use startswith() not == because create_llm_log appends '; cost_unknown:test' for the test provider model"
  - "fake_insights_agent fixture saves original get_insights_agent reference before monkeypatching so teardown can call cache_clear() on the real lru_cache function"
metrics:
  duration_minutes: 12
  completed_date: "2026-04-21"
  tasks_completed: 4
  tasks_total: 4
  files_created: 2
  files_modified: 1
---

# Phase 65 Plan 05: LLM Orchestration Service Summary

`app/services/insights_llm.py` — the Phase 65 orchestration core — ships with full tier-1 cache, rate-limit, tier-2 soft-fail, fresh LLM call, Sentry capture, and log-row write. 20 tests cover all LLM-01/LLM-02/INS-04/INS-05/INS-06 behaviors using TestModel and FunctionModel with no real provider calls.

## Tasks Completed

| Task | Name | Commit | Key Files |
|------|------|--------|-----------|
| 1 | insights_llm.py skeleton (constants, exceptions, agent singleton) | 4d1b83a | app/services/insights_llm.py |
| 2 | Helper functions (_assemble_user_prompt, _maybe_strip_overview, _maybe_stale_filters, _compute_retry_after, _run_agent) | 4d1b83a | app/services/insights_llm.py |
| 3 | generate_insights orchestrator + fake_insights_agent conftest fixture | 8ab761f | app/services/insights_llm.py, tests/conftest.py |
| 4 | test_insights_llm.py — 20 tests across 8 classes | 89484e8 | tests/services/test_insights_llm.py |

## What Was Built

### `app/services/insights_llm.py`

**Constants:**
- `INSIGHTS_MISSES_PER_HOUR = 3` — rate-limit quota per D-09
- `_PROMPT_VERSION = "endgame_v1"` — cache key component; bump on prompt edit
- `_OUTPUT_RETRIES = 2` — pydantic-ai output retry count per D-24
- `_RATE_LIMIT_WINDOW = timedelta(hours=1)`
- `_ENDPOINT: LlmLogEndpoint = "insights.endgame"` — typed Literal for LlmLogCreate

**Module-level `_SYSTEM_PROMPT`:** Loaded from `endgame_v1.md` at import time — module cannot be imported if the file is missing (D-27 fail-fast behavior).

**Exceptions (router maps to HTTP status in Plan 06):**
- `InsightsRateLimitExceeded(retry_after_seconds: int)` → 429
- `InsightsProviderError(error_marker: str)` → 502
- `InsightsValidationFailure(error_marker: str)` → 502

**`get_insights_agent()`:** `@functools.lru_cache(maxsize=1)` singleton. Constructs `Agent(model, output_type=EndgameInsightsReport, system_prompt=_SYSTEM_PROMPT, output_retries=2)`. Raises `UserError` on empty model string, `ValueError` on bad provider prefix. Called by lifespan for startup validation (Plan 06) and by `generate_insights` at request time.

**`_assemble_user_prompt(findings)`:** Renders `EndgameTabFindings` as structured text per D-29 format. Excludes `color` and `rated_only` from the Filters line (INS-03/D-31). Emits `### Series (metric, window, resolution)` blocks only for the 4 timeline subsections with `series is not None`. Resolution: weekly for `last_3mo` (except `type_win_rate_timeline` which is always monthly per D-05), monthly for `all_time`.

**`_maybe_strip_overview(report)`:** Returns a copy with `overview=""` if `settings.INSIGHTS_HIDE_OVERVIEW` is True; otherwise returns unchanged (D-18).

**`_maybe_stale_filters(fallback_log, current)`:** Compares fallback's `filter_context` to current `FilterContext`, excluding `color` and `rated_only` from comparison (INS-03). Returns the fallback `FilterContext` if they differ (banner shown), `None` if identical.

**`_compute_retry_after(session, user_id)`:** Queries oldest successful miss in the 1h window, returns seconds until it ages out (floor=1).

**`_run_agent(user_prompt, user_id, findings_hash)`:** Wraps `await agent.run(user_prompt)` with latency timing. Catches `UnexpectedModelBehavior` → `"validation_failure_after_retries"`, `ModelAPIError` → `"provider_error"`, unknown `Exception` → `"provider_error"`. All error paths call `sentry_sdk.set_context("insights", {...})` + `sentry_sdk.capture_exception(exc)` per D-36/D-37.

**`generate_insights(filter_context, user_id, session)`:** Five-path orchestration:
1. `compute_findings` → findings + findings_hash
2. Tier-1: `get_latest_log_by_hash` → `cache_hit` (no log row)
3. Rate-limit: `count_recent_successful_misses` >= 3 → tier-2: `get_latest_report_for_user` → `stale_rate_limited` OR raise `InsightsRateLimitExceeded`
4. Fresh: `_assemble_user_prompt` → `_run_agent` → `create_llm_log` (exactly one row)
5. On error marker → raise `InsightsValidationFailure` or `InsightsProviderError`

### `tests/conftest.py` addition

`fake_insights_agent` fixture: yields a factory `_install(report)` that clears the lru_cache and monkeypatches `get_insights_agent` to return a TestModel-backed Agent. Teardown calls `cache_clear()` on the saved original reference (not the monkeypatched lambda).

### `tests/services/test_insights_llm.py`

20 tests across 8 classes:
- `TestStartupValidation` (3): UserError on empty model, ValueError on bad provider, valid test model
- `TestPromptAssembly` (3): prompt shape with series blocks, system prompt from file, color/rated_only excluded
- `TestHappyPath` (1): fresh miss returns `status="fresh"` + log row written
- `TestCacheBehavior` (3): seeded row cache hit, prompt_version bump misses, model swap misses
- `TestRateLimit` (3): stale with tier-2 fallback, 429 without tier-2, window rollover
- `TestErrors` (2): provider error logs row + raises, validation failure logs row + raises
- `TestSentryCapture` (2): set_context with structured data, no dynamic variable in exception message
- `TestHideOverview` (3): strip response overview, keep when flag false, log has full text

## Test Suite Results

| Suite | Count | Status |
|-------|-------|--------|
| test_insights_llm.py (new) | 20 | All pass |
| test_insights_service_series.py (Plan 03) | 16 | All pass |
| test_llm_log_repository_reads.py (Plan 04) | 10 | All pass |
| test_llm_log_repository.py (Phase 64) | 4 | All pass |
| Full suite (excluding pre-existing test_reclassify failure) | 1009 | All pass |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - ty compliance] ty:ignore on Agent return type**
- **Found during:** Task 1 ty check
- **Issue:** ty cannot infer `Agent[None, EndgameInsightsReport]` from a `str` variable passed to `Agent(model, ...)` — reports `invalid-return-type`
- **Fix:** Added `# ty: ignore[invalid-return-type]` with explanation on the `return Agent(...)` line
- **Files modified:** `app/services/insights_llm.py`
- **Commit:** `4d1b83a`

**2. [Rule 1 - Bug] fake_insights_agent fixture teardown AttributeError**
- **Found during:** Task 4 test run
- **Issue:** Fixture teardown called `insights_llm.get_insights_agent.cache_clear()` but after monkeypatching, the module attribute is a plain lambda (no `cache_clear`). `monkeypatch` restores AFTER the `yield` teardown runs, so the name binding is still the lambda during teardown.
- **Fix:** Saved `original_get_insights_agent = insights_llm.get_insights_agent` before patching; teardown calls `original_get_insights_agent.cache_clear()`
- **Files modified:** `tests/conftest.py`
- **Commit:** `89484e8`

**3. [Rule 1 - Bug] Test assertions adjusted for cost_unknown:test error suffix**
- **Found during:** Task 4 test run
- **Issue:** The "test" model is unknown to genai-prices; `create_llm_log` appends `"; cost_unknown:test"` to the error column. Tests checking `row.error == "validation_failure_after_retries"` failed with the suffix present. `get_latest_log_by_hash` (which filters `error IS NULL`) cannot find fresh-miss rows written via generate_insights.
- **Fix:** (a) Changed `row.error == ...` to `row.error.startswith(...)` for error-row assertions. (b) Changed fresh-miss log query to direct SQL (by user_id + findings_hash, no error filter) instead of `get_latest_log_by_hash`. (c) Cache-hit test now seeds a pre-existing row with `error=None` directly rather than relying on a prior generate_insights call.
- **Files modified:** `tests/services/test_insights_llm.py`
- **Commit:** `89484e8`

**4. [Rule 1 - Bug] Rate-limit test data collision**
- **Found during:** Task 4 test run
- **Issue:** Rate-limit miss rows used `findings_hash="b"*64` (same as what `_fake_compute_findings` returns), so tier-1 cache lookup found the miss row and tried `model_validate({"ok": True})` → `ValidationError`. Also, `get_latest_report_for_user` found the miss rows as tier-2 fallback when they contained invalid JSON.
- **Fix:** (a) Miss rows now use distinct findings_hashes (`"c"*64`, `"k"*64`) so tier-1 misses them. (b) All seeded rows for rate-limit tests contain valid `EndgameInsightsReport` JSON. (c) For the "no tier-2" scenario: used `prompt_version="endgame_v0"` so `count_recent_successful_misses` counts them (no prompt_version filter) but `get_latest_report_for_user` excludes them (has prompt_version filter).
- **Files modified:** `tests/services/test_insights_llm.py`
- **Commit:** `89484e8`

## Known Stubs

None. All five paths in `generate_insights` are implemented and tested. No placeholder values flow to consumers.

## Threat Surface Scan

No new network endpoints introduced. `generate_insights` is an internal service function; the router (Plan 06) owns the HTTP boundary. Sentry captures follow D-36/D-37 (set_context with structured data, no variable interpolation in exception messages). The threat mitigations registered in the plan (T-65-02, T-65-03, T-65-04, T-65-05, T-65-06, T-65-07) are all implemented and verified by the test suite.

## Self-Check: PASSED

- `app/services/insights_llm.py` exists: FOUND
- `tests/services/test_insights_llm.py` exists: FOUND
- `tests/conftest.py` has `fake_insights_agent`: FOUND
- Commit `4d1b83a` (insights_llm.py): FOUND
- Commit `8ab761f` (conftest.py fixture): FOUND
- Commit `89484e8` (test_insights_llm.py): FOUND
- `uv run ty check app/ tests/`: 0 errors
- `uv run ruff check app/ tests/`: 0 errors
- `uv run pytest tests/services/test_insights_llm.py`: 20 passed
- Full suite (excluding pre-existing test_reclassify failure): 1009 passed
