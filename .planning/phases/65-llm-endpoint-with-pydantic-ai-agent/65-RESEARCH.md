# Phase 65: LLM Endpoint with pydantic-ai Agent — Research

**Researched:** 2026-04-21
**Domain:** pydantic-ai Agent wiring, DB-backed rate limiting, weekly→monthly resampling, FastAPI lifespan validation
**Confidence:** HIGH (pydantic-ai API surface probed live in venv; genai-prices coverage verified; all backend patterns read in-situ)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Findings → Prompt Contract (supersedes SEED-004)**

- **D-01:** Pass raw weekly/monthly timeseries to the LLM for the 4 timeline subsections (`score_gap_timeline`, `clock_diff_timeline`, `endgame_elo_timeline`, `type_win_rate_timeline`). Drop `Trend`, `is_headline_eligible`, `weekly_points_in_window` from the LLM's view.
- **D-02:** Extend `SubsectionFinding` with `series: list[TimePoint] | None = None` (only populated for the 4 timeline subsections). `TimePoint = BaseModel(bucket_start: str, value: float, n: int)`.
- **D-03:** Resample per window: `last_3mo` → weekly (≤13 points), `all_time` → monthly (mean of weeks in month, sample sizes summed). Resampling lives in `insights_service.compute_findings`, stdlib-only.
- **D-04:** Endgame ELO timeline ships as gap-only (`endgame_elo − actual_elo`) per `(platform, time_control)` combo. Drop combos with <~10 games in the window (≥10 floor).
- **D-05:** `type_win_rate_timeline` emits monthly-only (both windows). Planner confirms whether `last_3mo` window adds signal.
- **D-06:** SEED-004 closed as superseded at phase completion.
- **D-07:** `Trend`, `is_headline_eligible`, `weekly_points_in_window` stay on the schema but are NOT rendered into the prompt.

**Cache + Rate Limit + Soft-Fail (INS-04, INS-05)**

- **D-08:** Cache key = `(findings_hash, prompt_version, model)`. Reuses Phase 64 `get_latest_log_by_hash`. Cache hits write NO new row.
- **D-09:** Rate-limit check is a DB query: `COUNT(*) FROM llm_logs WHERE user_id=? AND created_at > now() - interval '1 hour' AND cache_hit=false AND error IS NULL AND response_json IS NOT NULL`. Uses Phase 64 `ix_llm_logs_user_id_created_at`. `INSIGHTS_MISSES_PER_HOUR = 3`.
- **D-10:** Only successful misses consume quota.
- **D-11:** Soft-fail tier 1 = `get_latest_log_by_hash`; tier 2 = `get_latest_report_for_user(user_id, prompt_version, model)`; tier 3 = HTTP 429.
- **D-12:** Provider errors return HTTP 502 (NO soft-fail).
- **D-13:** No in-process lock for concurrent cold-cache requests.

**Response / Error Envelope (INS-07)**

- **D-14:** `EndgameInsightsResponse(report, status: Literal["fresh","cache_hit","stale_rate_limited"], stale_filters: FilterContext | None = None)`.
- **D-15:** `InsightsErrorResponse(error: Literal["rate_limit_exceeded","provider_error","validation_failure","config_error"], retry_after_seconds: int | None = None)`.
- **D-16:** HTTP status mapping: 200 / 429 / 502 / 503.
- **D-17:** `EndgameInsightsReport` includes `model_used: str`, `prompt_version: str`.
- **D-18:** `INSIGHTS_HIDE_OVERVIEW=true` → backend sets `report.overview = ""` before returning. Full overview still in `llm_logs.response_json`.
- **D-19:** `EndgameInsightsReport.sections: list[SectionInsight]` with `min_length=1, max_length=4`. LLM decides omission.
- **D-20:** `section_id` uniqueness via Pydantic `model_validator`. Duplicate → validation error → pydantic-ai retries.

**Pydantic-AI Agent Wiring (LLM-01, LLM-02, LLM-03)**

- **D-21:** `get_insights_agent()` in `app/services/insights_llm.py`, wrapped with `@functools.lru_cache`. Constructs `Agent(model=..., result_type=EndgameInsightsReport, system_prompt=_load_system_prompt())` lazily.
- **D-22:** Startup validation = Level 2 (Agent construction, NO dry-run). Lifespan calls `get_insights_agent()` and lets `UserError`/`ValueError` propagate.
- **D-23:** Add `PYDANTIC_AI_MODEL_INSIGHTS: str = ""` to `app/core/config.py`. Empty string → RuntimeError at startup. Add `INSIGHTS_HIDE_OVERVIEW: bool = False`.
- **D-24:** Retry-on-validation-failure uses pydantic-ai's built-in retries parameter (researcher picks count, 2-3 suggested).
- **D-25:** Latency captured around `await agent.run(user_prompt)` only.
- **D-26:** Token counts from pydantic-ai `RunResult.usage()`. On failure: `input_tokens=0, output_tokens=0, error="usage_missing"`.

**Prompt Assembly (LLM-03)**

- **D-27:** System prompt at `app/services/insights_prompts/endgame_v1.md`, loaded ONCE at startup. Missing file → startup fails.
- **D-28:** User-message assembly inline in `insights_llm.py` via `_assemble_user_prompt()` helper (~40 lines).
- **D-29:** User-message format = SEED-003 markdown layout + `### Series` blocks per timeline subsection.
- **D-30:** Info-popover text inline in `endgame_v1.md` "Metric glossary" section.

**Endpoint + Router Shape**

- **D-31:** `POST /api/insights/endgame` accepts query params matching `/endgames/overview`. `color` and `rated_only` flow into findings but NOT into the LLM prompt.
- **D-32:** Router file `app/routers/insights.py`, registered with `prefix="/api"`.
- **D-33:** All orchestration in `insights_llm.generate_insights()`. Router = zero business logic.

**Repository Extensions (Phase 64 surface)**

- **D-34:** Two new read helpers: `count_recent_successful_misses(session, user_id, window: datetime.timedelta) -> int`; `get_latest_report_for_user(session, user_id, prompt_version, model) -> LlmLog | None`. Both take caller-supplied sessions.

**Observability (LOG-02, LOG-04)**

- **D-35:** One `llm_logs` row per cache miss. Cache hits + soft-fail stales write NO row.
- **D-36:** Sentry `set_context` + `capture_exception` on pydantic-ai exceptions only. Rate-limit exhaustion → no Sentry.
- **D-37:** Never embed variables in exception messages. Stable machine-readable prefixes.

**Testing Strategy**

- **D-38:** `TestModel(custom_output_args=report.model_dump())` is the default test double. Monkeypatch `get_insights_agent()`.
- **D-39:** `FunctionModel` for 2-3 tests asserting specific token counts.
- **D-40:** `os.environ["PYDANTIC_AI_MODEL_INSIGHTS"] = "test"` in `tests/conftest.py` at module top.
- **D-41:** New test files: `tests/services/test_insights_llm.py`, `tests/routers/test_insights_router.py`, `tests/repositories/test_llm_log_repository_reads.py`, `tests/services/test_insights_service_series.py`.
- **D-42:** No real-provider calls in Phase 65.
- **D-43:** No VCR / recorded cassettes.

### Claude's Discretion

- Exact pydantic-ai API surface — validated live in this research (see §pydantic-ai API Reference).
- Sparse-combo threshold for Endgame ELO timeline — researcher recommends ≥10 (matches D-04 floor; see §Resampling Logic).
- Monthly-bucketing key format — researcher recommends `"YYYY-MM-01"` ISO date string (see §Resampling Logic).
- `INSIGHTS_MISSES_PER_HOUR` location — researcher recommends `insights_llm.py` module-level.
- Rate-limit retry-after calculation — UTC throughout, computed from oldest-miss timestamp.
- Whether to emit `last_3mo` for `type_win_rate_timeline` — researcher recommends KEEP (see §Resampling Logic §D-05).
- Default model — researcher recommends `anthropic:claude-haiku-4-5-20251001` (see §Model Selection & Pricing).
- `_load_system_prompt()` timing — researcher recommends "at module import" via module-level constant (see §Agent Singleton).

### Deferred Ideas (OUT OF SCOPE)

- Cache-hit row logging (Phase 64 D-05 deferred).
- In-memory concurrency lock for cold-cache parallel requests (D-13).
- Ripping out `Trend` / `is_headline_eligible` / `weekly_points_in_window` fields.
- Popover text extraction to `insights_prompts/popovers.py`.
- `cache_hit=true` / stale-served row logging.
- Real-provider integration tests (Phase 67 scope).
- Admin raw-data mode variants (v1.12 scope).
- Per-section streaming responses.
- Cross-AI model A/B at endpoint level.
- Weighted vs unweighted monthly mean — researcher recommends WEIGHTED-BY-N (see §Resampling Logic).

</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| LLM-01 | `POST /api/insights/endgame` returns validated `EndgameInsightsReport` from pydantic-ai Agent with `result_type=EndgameInsightsReport` | §pydantic-ai API Reference confirms `output_type=...` is the current parameter name (v1.85.0); §Agent Singleton gives the canonical wiring |
| LLM-02 | Model selected at startup from env var `PYDANTIC_AI_MODEL_INSIGHTS`; backend refuses to start on missing/invalid | §Agent Singleton + §Error Handling: empty-string → `UserError: Unknown model:`, bad-provider → `ValueError: Unknown provider`, both at construction. Lifespan hook pattern in §Agent Singleton |
| LLM-03 | System prompt versioned at `app/services/insights_prompts/endgame_v1.md` (loaded from file), shapes prompt with filter context + flags + findings + info-popover text | §Prompt Loading pattern; `instructions=` or `system_prompt=` both valid (current docs prefer `instructions`, but SEED-003 decided `system_prompt=` — both produce equivalent behavior for our single-call use-case) |
| INS-04 | Insights cache on `findings_hash`; cache key includes `prompt_version` and `model` | §DB Queries (tier-1 reuses Phase 64 `get_latest_log_by_hash`); no new index needed |
| INS-05 | Rate-limit 3 cache misses per hour per user; on exhaustion return last cached report (soft-fail) rather than error | §DB Queries gives concrete SQL + index verification; §Resampling §retry-after computation for 429 envelope |
| INS-06 | Overview paragraph ALWAYS populated when a report is produced (no null overview) | §Response Schema: `overview: str` (no `| None`), Pydantic rejects null; LLM prompt instructs "summarize per-section when no cross-section signal" |
| INS-07 | All failure paths show single retry affordance; Sentry capture with `set_context` (user_id, findings_hash, model) | §Error Handling & Retry Flow + §Sentry integration |
</phase_requirements>

---

## 1. Executive Summary

- **pydantic-ai 1.85.0 released 2026-04-21** (today). The constructor parameter is **`output_type=`**, not `result_type=` (legacy docs still show `result_type`; the installed library only accepts `output_type`). `.usage()` is a **method** returning `RunUsage(input_tokens, output_tokens, requests, ...)`. Structured-output retries are controlled by the **`output_retries=`** parameter on `Agent(...)` (separate from `retries=`, which is for tool retries). Recommended pin: `pydantic-ai-slim[anthropic,google]>=1.85,<2.0` — slim is sufficient because CONTEXT.md only needs Anthropic + Google providers. [VERIFIED: PyPI JSON; live venv inspection]

- **Startup validation is automatic** when `defer_model_check=False` (default). `Agent("")` raises `UserError("Unknown model: ")`; `Agent("nonexistent-provider:foo")` raises `ValueError("Unknown provider: nonexistent-provider")`. Lifespan hook calls `get_insights_agent()` — propagating either exception aborts startup. No dry-run LLM call needed. [VERIFIED: live venv probe with pydantic-ai 1.85.0]

- **Default model recommendation: `anthropic:claude-haiku-4-5-20251001`**. genai-prices 0.0.56 (already pinned in Phase 64) covers all three candidate models: Haiku 4.5 ($0.0035 per 1k-in + 500-out sample), Gemini 2.5 Flash ($0.00155), Gemini 3 Flash Preview ($0.0020). Haiku 4.5 wins on structured-output reliability (Anthropic's tool-use path is mature; Gemini Flash has a weaker structured-output track record). Cost delta is <$0.01/report either way — reliability trumps cost at this scale. [VERIFIED: local genai-prices probe]

- **Rate-limit SQL query is simple** (`select(func.count()).where(...)`) and Phase 64's `ix_llm_logs_user_id_created_at` index covers both new read helpers without modification. Tier-2 soft-fail uses the same index. No new index migration in Phase 65. [VERIFIED: read Phase 64 model definitions]

- **Resampling uses stdlib only**: `statistics.mean` + `collections.defaultdict`. Weekly→monthly resample takes ~12 lines. Recommended: **weighted-by-n** monthly mean (more honest given D-02 exposes `n` anyway). Bucket key: `"YYYY-MM-01"` (ISO first-of-month), matches `TimePoint.bucket_start: str`. [VERIFIED: stdlib docs + existing Phase 63 patterns]

- **Final exception after exhausting `output_retries` is `UnexpectedModelBehavior`** — confirmed via live probe (error message: `"Exceeded maximum retries (N) for output validation"`). This is the catch-point in `generate_insights()` for validation-failure → HTTP 502. Provider errors raise `ModelHTTPError` (subclass of `ModelAPIError`). [VERIFIED: live venv probe]

**Primary recommendation:** Pin `pydantic-ai-slim[anthropic,google]==1.85.0`, use `output_type` + `output_retries=2`, default to `anthropic:claude-haiku-4-5-20251001`, monkeypatch via `Agent.override(model=TestModel(custom_output_args=...))` in tests.

---

## 2. pydantic-ai API Reference

### Constructor signature (VERIFIED live against 1.85.0)

```python
Agent(
    model: Model | str | None = None,
    *,
    output_type: type[OutputT] = str,                      # v1.x current name
    instructions: str | Sequence[str | Callable] | None = None,  # preferred
    system_prompt: str | Sequence[str] = (),               # legacy path still supported
    deps_type: type = NoneType,
    name: str | None = None,
    description: str | None = None,
    model_settings: ModelSettings | None = None,
    retries: int = 1,                                       # TOOL retries
    validation_context: Any | None = None,
    output_retries: int | None = None,                     # STRUCTURED-OUTPUT retries
    tools: Sequence[Tool] = (),
    builtin_tools: Sequence[BuiltinTool] = (),
    prepare_tools: Callable | None = None,
    prepare_output_tools: Callable | None = None,
    toolsets: Sequence[Toolset] | None = None,
    defer_model_check: bool = False,                       # KEY: default validates at construction
    end_strategy: EndStrategy = 'early',
    instrument: Any | None = None,
    metadata: dict | None = None,
    history_processors: Sequence[Callable] | None = None,
    event_stream_handler: Callable | None = None,
    tool_timeout: float | None = None,
    max_concurrency: int | None = None,
    capabilities: Sequence[AbstractCapability] | None = None,
)
```
[VERIFIED: `inspect.signature(Agent.__init__)` against pydantic-ai 1.85.0 in isolated venv]

**Critical: `result_type` is gone.** Parts of the llms.txt docs and older tutorials still show `result_type` (context7 returned one such snippet with `result_type`), but the installed library only accepts `output_type`. CONTEXT.md phrasing "result_type=EndgameInsightsReport" is a carryover from SEED-003 (2026-04-20); the planner should emit `output_type=EndgameInsightsReport` in code.

### `output_retries` vs `retries`

- `retries` (default `1`) — applies to tool-call validation failures + `ModelRetry` from tools.
- `output_retries` (default `None` → falls back to `retries`) — applies specifically to structured-output validation failures. **This is the knob for D-24.** Recommend `output_retries=2` (two additional attempts = three total), matching D-20's "Pydantic `model_validator` raises → pydantic-ai retries" flow.

[CITED: https://github.com/pydantic/pydantic-ai/blob/main/docs/agent.md "Reflection and self-correction"]

### `RunResult.usage()` — method, returns `RunUsage`

```python
result = await agent.run(user_prompt)
usage = result.usage()          # METHOD CALL, not a property
usage.input_tokens              # int
usage.output_tokens             # int
usage.requests                  # int (number of API calls in this run)
# Also available: total_tokens, cache_read_tokens, cache_write_tokens,
# request_tokens (alias for input_tokens), response_tokens (alias for output_tokens)
```
[VERIFIED: live probe with `TestModel`; returned `RunUsage(input_tokens=51, output_tokens=6, requests=1)`]

For D-26, use `result.usage().input_tokens` and `result.usage().output_tokens`. The `RunUsage` object is always populated on success — no code path returns `None` for usage on a successful run. CONTEXT.md's "usage-retrieval failure" hedge is defensive but unlikely to fire; if it does (e.g., a custom Model subclass misbehaves), wrap in `try/except AttributeError`.

### Exception hierarchy (VERIFIED via `dir(pydantic_ai.exceptions)`)

| Exception | Raised when |
|-----------|-------------|
| `UserError` | Misconfiguration: empty model string, bad model+provider combo detected lazily |
| `ValueError` | Bad provider prefix (e.g., `"nonexistent-provider:foo"`) at Agent construction |
| `UnexpectedModelBehavior` | Structured-output validation failed after `output_retries` exhausted; tool retry limit exceeded |
| `ModelHTTPError` (subclass of `ModelAPIError`) | Provider HTTP 4xx/5xx |
| `ModelAPIError` | Any provider-side API error |
| `ModelRetry` | Explicit retry signal from tool / output_validator |
| `ConcurrencyLimitExceeded` | `max_concurrency` exceeded |
| `UsageLimitExceeded` | `UsageLimits` exceeded |
| `ContentFilterError` | Provider's content filter triggered (subclass of `ModelAPIError`) |

[VERIFIED: `[n for n in dir(pydantic_ai.exceptions) if not n.startswith('_')]` against 1.85.0]

**Mapping to HTTP status for D-16:**

| pydantic-ai exception | HTTP | Envelope `error` |
|----------------------|------|------------------|
| `UnexpectedModelBehavior` | 502 | `"validation_failure"` |
| `ModelHTTPError` / `ModelAPIError` | 502 | `"provider_error"` |
| `UserError` / `ValueError` at startup | — (lifespan aborts) | not reachable at request time |
| Any other unexpected `Exception` | 502 | `"provider_error"` (safe default) |

### `Agent.override()` — test-time model replacement

```python
with agent.override(model=TestModel(custom_output_args=report.model_dump())):
    result = await agent.run('probe')
```
[CITED: https://github.com/pydantic/pydantic-ai/blob/main/docs/testing.md]

`Agent.override()` is a sync context manager that swaps the model for the duration of the block. **But** Phase 65's pattern is simpler: monkeypatch `get_insights_agent()` itself (D-38) so every call in the monkeypatched scope returns a pre-built Agent wrapping `TestModel`. This works because the Agent is cached via `@lru_cache` — `monkeypatch.setattr("app.services.insights_llm.get_insights_agent", lambda: fake_agent)` cleanly redirects.

### `TestModel` signature (VERIFIED)

```python
TestModel(
    *,
    call_tools: str = 'all',
    custom_output_text: str | None = None,      # plain-text response override
    custom_output_args: dict | None = None,     # STRUCTURED-output override (dict passed to output_type.model_validate)
    seed: int = 0,
    model_name: str = 'test',
    profile: ModelProfile | None = None,
    settings: ModelSettings | None = None,
)
```
[VERIFIED: `inspect.signature(TestModel.__init__)` against 1.85.0]

**D-38 confirmed:** `TestModel(custom_output_args=report.model_dump())` is the current API. TestModel runs the dict through `EndgameInsightsReport.model_validate()` — so Pydantic validators (including the `model_validator` from D-20) execute on the test path. This is desirable: Phase 65's D-38 explicitly wants "Tests flow through pydantic-ai's real schema-validation machinery."

### `FunctionModel` for D-39 (token-count assertions)

```python
from pydantic_ai.models.function import FunctionModel, AgentInfo
from pydantic_ai.messages import ModelMessage, ModelResponse, TextPart

async def fixed_usage_model(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
    return ModelResponse(
        parts=[TextPart(content=json.dumps(report.model_dump()))],
        usage=RequestUsage(input_tokens=1234, output_tokens=567),  # forced values
    )

agent = Agent(FunctionModel(fixed_usage_model), output_type=EndgameInsightsReport)
```
[CITED: https://github.com/pydantic/pydantic-ai/blob/main/docs/testing.md — "Unit testing with FunctionModel"]

Note: `ModelResponse.usage` here is `RequestUsage` (per-request), which is aggregated into `RunUsage` across retries. Tests assert `result.usage().input_tokens == 1234` after a single-request successful run.

### Per-call system prompt override

**D-27 assumption confirmed: system prompt is constructor-only** for the static case. Dynamic system prompts attach via `@agent.system_prompt` decorator + `RunContext` deps. `Agent.run()` does NOT accept a per-call `system_prompt` parameter — user prompt is passed as the positional first argument.

[CITED: https://github.com/pydantic/pydantic-ai/blob/main/docs/agent.md "System Prompts"]

### Version pin recommendation

```toml
# pyproject.toml additions
"pydantic-ai-slim[anthropic,google]>=1.85,<2.0",
```

**Why slim:** CONTEXT.md only uses `anthropic:*` and `google-gla:*` providers. The full `pydantic-ai` package pulls in OpenAI, Groq, Mistral, Cohere, Bedrock, HuggingFace, and more — none of which Phase 65 needs. Slim saves ~40 MB of transitive deps and reduces Dependabot/Renovate noise.

**Why `>=1.85,<2.0`:** pydantic-ai 1.85.0 is the first release under the 1.x stable line with the current `output_type` API (earlier 0.x used `result_type`). Cap at `<2.0` until a stability signal emerges — pydantic-ai has renamed public API twice (result_type→output_type, result_retries→output_retries), so a 2.0 major bump is plausible and should be reviewed before adopting.

[VERIFIED: PyPI `pydantic-ai-slim/json` latest=1.85.0 released 2026-04-21T17:03:33]

---

## 3. Model Selection & Pricing

### Recommendation: `anthropic:claude-haiku-4-5-20251001`

### genai-prices coverage (VERIFIED against genai-prices 0.0.56)

Ran `calc_price(Usage(input_tokens=1000, output_tokens=500), model_ref=..., provider_id=...)` for each candidate — all three resolve cleanly (no `LookupError`):

| Model string | Provider split | Cost (1k in + 500 out) | Structured-output track record |
|--------------|----------------|-------------------------|-------------------------------|
| `anthropic:claude-haiku-4-5-20251001` | `anthropic` + `claude-haiku-4-5-20251001` | $0.0035 | Strong (tool-use mature; JSON-schema reliable) |
| `google-gla:gemini-2.5-flash` | `google-gla` + `gemini-2.5-flash` | $0.00155 | Mixed (structured-output sometimes returns prose with JSON embedded; needs `PromptedOutput` or `NativeOutput` tuning) |
| `google-gla:gemini-3-flash-preview` | `google-gla` + `gemini-3-flash-preview` | $0.0020 | Newer; docs use it heavily in examples; preview marker implies API may shift |
| `openai:gpt-4o-mini` (offered in SEED-003 but not in CONTEXT.md candidates) | `openai` + `gpt-4o-mini` | $0.00045 | Strong — but not in CONTEXT.md candidate list |

[VERIFIED: local `uv run python` probe against genai-prices 0.0.56]

### Why Haiku 4.5 over Gemini Flash

1. **Structured-output reliability.** pydantic-ai's default structured-output path for Anthropic uses tool-call forcing (proven stable). Gemini's structured-output via response-schema works but has historically had edge cases around `list[Literal[...]]` enums and `max_length` constraints (exactly the kind of field EndgameInsightsReport has: `sections` is `min_length=1, max_length=4` and `section_id` is `Literal[4 values]`). Hitting a structured-output edge case triggers `output_retries` loops, inflating cost and latency — erasing Gemini's nominal price advantage.
2. **Cost magnitude is trivial either way.** At expected volume (a beta cohort of 5-20 users, 3 misses/hr each = ≤60 misses/hr peak, realistic daily volume <100 reports), the cost delta between Haiku 4.5 and Gemini 2.5 Flash is ~$0.002/report × 100/day = $0.20/day. Not worth tuning.
3. **"Engines are flawless, humans play FlawChess" tagline** — this is a commentary layer, not an engine. Haiku 4.5 is more than sufficient for 4-section endgame narrative; no need for a frontier model.
4. **Env-var swap is free** (D-23). If the beta cohort's eyeball validation prefers Gemini's narrative style, change `PYDANTIC_AI_MODEL_INSIGHTS` and restart — no code change.

### `.env.example` additions

```bash
# LLM insights (Phase 65+)
# Supports any pydantic-ai model string; requires matching provider API key set.
PYDANTIC_AI_MODEL_INSIGHTS=anthropic:claude-haiku-4-5-20251001
ANTHROPIC_API_KEY=sk-ant-...
# Set INSIGHTS_HIDE_OVERVIEW=true to strip report.overview before returning to client
# (full overview is still captured in llm_logs.response_json for offline analysis).
INSIGHTS_HIDE_OVERVIEW=false
```

### Sentry + Hetzner prep

CONTEXT.md §Blockers/Concerns (STATE.md) notes: "`ANTHROPIC_API_KEY` / `OPENAI_API_KEY` / `GEMINI_API_KEY` need to be set on the Hetzner server before Phase 65 ships". Planner should include a Wave-0 "set secret on prod" manual task or confirm the user has already done so; otherwise startup-validation will fail in staging.

---

## 4. DB Queries

### Phase 64's existing index

```python
# app/models/llm_log.py (Phase 64)
Index("ix_llm_logs_user_id_created_at", "user_id", "created_at", postgresql_ops={"created_at": "DESC"})
```
[VERIFIED: read app/models/llm_log.py; Phase 64 Plan 02 SUMMARY confirms DESC preserved]

This composite index covers **both** new read helpers: equality on `user_id` + range on `created_at` (tier-1 rate-limit count) and equality on `user_id` + descending ordering on `created_at` (tier-2 latest-report lookup). No new index needed.

### `count_recent_successful_misses`

```python
# app/repositories/llm_log_repository.py — NEW helper per D-34

import datetime
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

async def count_recent_successful_misses(
    session: AsyncSession,
    user_id: int,
    window: datetime.timedelta,
) -> int:
    """Count successful cache-miss LLM calls for user within the time window.

    "Successful miss" per D-09/D-10: cache_hit=false AND error IS NULL AND
    response_json IS NOT NULL. Only these count toward the rate limit.
    """
    cutoff = datetime.datetime.now(datetime.UTC) - window
    stmt = select(func.count()).select_from(LlmLog).where(
        LlmLog.user_id == user_id,
        LlmLog.created_at > cutoff,
        LlmLog.cache_hit.is_(False),
        LlmLog.error.is_(None),
        LlmLog.response_json.is_not(None),
    )
    result = await session.execute(stmt)
    return result.scalar_one()
```

**Notes:**
- `func.count()` with `select_from(LlmLog)` generates `SELECT count(*) FROM llm_logs WHERE ...` (no row materialization).
- `cache_hit.is_(False)` — explicit because Phase 64's default is `cache_hit=False`, but being explicit is defensive against future rows that might carry `True` (e.g., if CONTEXT.md-deferred cache-hit logging ships later).
- `cutoff` uses timezone-aware UTC, matching Phase 64's `created_at` column (`DateTime(timezone=True), server_default=func.now()`).
- Returns `int` (not `int | None`) — `func.count()` always returns a scalar.
- Index coverage: `ix_llm_logs_user_id_created_at` DESC — Postgres uses the index for both the equality filter on `user_id` and the range filter on `created_at`. The `cache_hit` / `error` / `response_json` filters apply post-index-scan, but the result set is already small (≤~few hundred rows per user per hour in worst case).

### `get_latest_report_for_user`

```python
async def get_latest_report_for_user(
    session: AsyncSession,
    user_id: int,
    prompt_version: str,
    model: str,
) -> LlmLog | None:
    """Tier-2 soft-fail: most recent successful report for user under current
    prompt/model era. Used when rate-limited and no exact cache match exists (D-11).
    """
    stmt = (
        select(LlmLog)
        .where(
            LlmLog.user_id == user_id,
            LlmLog.prompt_version == prompt_version,
            LlmLog.model == model,
            LlmLog.response_json.is_not(None),
            LlmLog.error.is_(None),
        )
        .order_by(LlmLog.created_at.desc())
        .limit(1)
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()
```

**Index coverage:** same composite — `user_id` equality + `created_at DESC` ordering satisfied by `ix_llm_logs_user_id_created_at`. Postgres applies the `prompt_version` / `model` / `response_json` / `error` filters post-scan on the small-per-user result set.

### `retry_after_seconds` computation for HTTP 429 envelope

```python
# app/services/insights_llm.py

import datetime
from sqlalchemy import select

_RATE_LIMIT_WINDOW = datetime.timedelta(hours=1)

async def _compute_retry_after(session: AsyncSession, user_id: int) -> int:
    """Seconds until the oldest miss in the rate-limit window expires.

    Returns 0 if no misses found (shouldn't happen when called — caller only
    invokes this after count >= INSIGHTS_MISSES_PER_HOUR). Defensive floor
    of 1 second so frontend never sees retry_after=0 (would spin-retry).
    """
    cutoff = datetime.datetime.now(datetime.UTC) - _RATE_LIMIT_WINDOW
    stmt = (
        select(LlmLog.created_at)
        .where(
            LlmLog.user_id == user_id,
            LlmLog.created_at > cutoff,
            LlmLog.cache_hit.is_(False),
            LlmLog.error.is_(None),
            LlmLog.response_json.is_not(None),
        )
        .order_by(LlmLog.created_at.asc())
        .limit(1)
    )
    result = await session.execute(stmt)
    oldest = result.scalar_one_or_none()
    if oldest is None:
        return 1
    expires_at = oldest + _RATE_LIMIT_WINDOW
    delta = (expires_at - datetime.datetime.now(datetime.UTC)).total_seconds()
    return max(1, int(delta))
```

This is a SEPARATE query (not combined with the count). Running two indexed queries on the same table costs ~2ms total at expected volume. The alternative — a window function in the count query — is premature optimization.

**Location decision:** this helper lives in `insights_llm.py`, NOT in `llm_log_repository.py`. It's business logic (tiered soft-fail semantics) rather than pure DB access. Planner can move to a dedicated helper if complexity grows.

### Should the new helpers add a partial index?

**No.** The composite index already services both queries. The additional WHERE filters (`cache_hit=false`, `error IS NULL`, `response_json IS NOT NULL`) are applied on the small per-user-per-hour slice that the composite index already narrows to. A partial index (`WHERE cache_hit=false AND error IS NULL`) would save ~1ms on queries and cost a few MB of index size — not worth it at MVP volume. Revisit after ~100k log rows.

---

## 5. Resampling Logic

### Phase 63 current state — what series data already exists

From reading `app/services/insights_service.py`:

| Subsection | Source data | Current shape in response |
|------------|-------------|---------------------------|
| `score_gap_timeline` | `response.score_gap_material.timeline` | `list[ScoreGapTimelinePoint]` with `date: str` (YYYY-MM-DD Monday), `score_difference: float`, `per_week_total_games: int` |
| `clock_diff_timeline` | `response.clock_pressure.timeline` | `list[ClockPressureTimelinePoint]` with `date: str`, `avg_clock_diff_pct: float`, `per_week_game_count: int` |
| `endgame_elo_timeline` | `response.endgame_elo_timeline.combos[*].points` | `list[EndgameEloTimelinePoint]` per combo; each point has `date` (Sunday of week), `endgame_elo`, `actual_elo`, plus per-week volume |
| `type_win_rate_timeline` | `response.timeline.per_type[endgame_class]` | `dict[str, list[EndgameTimelinePoint]]` where EndgameTimelinePoint has `date: str`, `win_rate: float`, `per_week_game_count: int` |

**Key insight:** all four timelines ALREADY produce weekly points. Phase 65's D-03 resampling is:
- `last_3mo` → **keep as-is** (weekly is correct); cap at ≤13 points if the upstream timeline is longer.
- `all_time` → **resample weekly → monthly**.

### Concrete resampling helper (D-03)

```python
# app/services/insights_service.py — NEW helpers

import datetime
import statistics
from collections import defaultdict

from app.schemas.insights import TimePoint  # NEW schema, see §D-02


def _weekly_points_to_time_points(
    weekly: list[tuple[str, float, int]],  # (date_iso, value, n)
    window: Window,
) -> list[TimePoint]:
    """Convert weekly (date, value, n) tuples to TimePoint list per D-03.

    last_3mo: pass-through (weekly resolution, sorted by date).
    all_time: resample to monthly, weighted-by-n mean, sample sizes summed.
    """
    if window == "last_3mo":
        return [
            TimePoint(bucket_start=d, value=v, n=n)
            for d, v, n in sorted(weekly, key=lambda t: t[0])
        ]
    # all_time -> monthly
    buckets: dict[str, list[tuple[float, int]]] = defaultdict(list)
    for date_iso, value, n in weekly:
        # date_iso is "YYYY-MM-DD"; first 7 chars = "YYYY-MM"
        ym = date_iso[:7]
        buckets[ym].append((value, n))
    points: list[TimePoint] = []
    for ym in sorted(buckets.keys()):
        weeks = buckets[ym]
        total_n = sum(n for _, n in weeks)
        if total_n > 0:
            # Weighted-by-n mean (more honest: a 50-game week dominates a 3-game week).
            weighted_sum = sum(v * n for v, n in weeks)
            mean_value = weighted_sum / total_n
        else:
            # All weeks had n=0 — defensive: emit arithmetic mean, n=0.
            mean_value = statistics.mean(v for v, _ in weeks)
            total_n = 0
        # ISO first-of-month string, matches TimePoint.bucket_start: str.
        bucket_start = f"{ym}-01"
        points.append(TimePoint(bucket_start=bucket_start, value=mean_value, n=total_n))
    return points
```

### Weighted vs unweighted mean (Claude's Discretion)

**Recommendation: weighted-by-n.**

Rationale: the LLM receives the `n` field on every TimePoint, so the numbers must be consistent — a monthly point with `n=80` representing the weighted mean of (40-game week at value=0.6) + (40-game week at value=0.4) correctly shows 0.5. Unweighted mean would also show 0.5 in that symmetric case, but diverges when weeks are asymmetric: (50 games at 0.8) + (3 games at 0.2) — weighted = 0.766, unweighted = 0.5. The weighted answer is "what this month actually looked like per game"; the unweighted answer is "what this month looked like per week". For narrative purposes ("your Score Gap in March was strong"), the per-game answer is what the user experiences.

Code cost: 2 extra lines (the `weighted_sum = sum(v * n for v, n in weeks)` divide). Worth it.

### D-04: Endgame ELO gap-only + sparse-combo filter

Phase 63 currently emits ONE `SubsectionFinding` per combo for `endgame_elo_timeline`, with `value = last.endgame_elo - last.actual_elo` and `dimension = {"platform": ..., "time_control": ...}`. The `combo.points` array has the weekly history but is not currently exposed.

**Phase 65 extension:**

```python
def _series_for_endgame_elo_combo(
    combo: EndgameEloTimelineCombo,
    window: Window,
    min_games_floor: int = 10,
) -> list[TimePoint] | None:
    """Build gap-only series for one (platform, time_control) combo.

    Returns None if combo has fewer than min_games_floor total weekly
    observations in the window — caller skips the subsection finding.
    """
    if len(combo.points) < min_games_floor:
        return None
    weekly = [
        (p.date, float(p.endgame_elo - p.actual_elo), p.per_week_endgame_games)
        for p in combo.points
    ]
    return _weekly_points_to_time_points(weekly, window)
```

**Threshold recommendation: ≥10 games.** Matches D-04's floor. Benchmarks report §6 shows typical active users have 2-3 surviving combos at this threshold (most-populated combo has 40-80 weekly points in a year; thinnest combo often dies <10). The benchmark's "≥30 endgame games per user" qualification for the population baseline is different (that's total endgame games per user; this is per-combo weekly observations).

[CITED: reports/benchmarks-2026-04-18.md §"Per-combo skill percentiles"]

**Token budget check:** a power user with 4 combos × 52 weekly points (all_time monthly-resampled to ~12 points) × 3 fields per TimePoint (date + value + n) ≈ 150 rows of data ≈ 2.5k tokens. Matches CONTEXT.md D-04 "Bounds the per-report timeseries token footprint at ~2-3k worst case."

### D-05: `type_win_rate_timeline` monthly-only

**Recommendation: KEEP `last_3mo` window, emit monthly resolution for BOTH windows.**

CONTEXT.md D-05 says "Planner confirms whether `last_3mo` window adds signal or is always empty at this granularity." My read: for `last_3mo` monthly you'd get up to 3 points per endgame class × 5 classes = 15 TimePoints. That's thin but not always empty:
- High-volume users (200+ games/3mo) produce 3 monthly points per class with n=5-20 per point.
- Thin users (20 games/3mo) produce maybe 1 point per 2-3 classes with n=3-7 per point — marginally useful.
- A per-class floor of n≥5 per monthly bucket (drop empty/thin buckets) keeps the payload honest.

Alternative: emit `last_3mo` at WEEKLY for this subsection (5 classes × 13 weeks = 65 points), which matches the other timelines. But the narrative value is low — the LLM is supposed to treat `type_win_rate_timeline` as supporting-only (Phase 63 D-13 sets `is_headline_eligible=False` for all rows). Weekly×per-class produces 65 noisy points the LLM has no mandate to narrate. **Monthly is correct** even for `last_3mo`.

### Resampling integration in `compute_findings`

The planner wires `_weekly_points_to_time_points()` into each timeline subsection's builder. For `score_gap_timeline` and `clock_diff_timeline`, the weekly points come straight from response.*.timeline. For `endgame_elo_timeline`, the helper `_series_for_endgame_elo_combo` handles gap extraction + sparse-combo filtering. For `type_win_rate_timeline`, loop over `per_type` dict and resample each class's series.

```python
# Example: extending _finding_score_gap_timeline with D-02/D-03 series
def _finding_score_gap_timeline(response, window):
    timeline = response.score_gap_material.timeline
    if not timeline:
        return _empty_finding("score_gap_timeline", window, "score_gap")
    # ... existing trend/zone/etc computation ...
    # NEW: populate series
    weekly = [(p.date, p.score_difference, p.per_week_total_games) for p in timeline]
    series = _weekly_points_to_time_points(weekly, window)
    return SubsectionFinding(
        # ... all existing fields ...
        series=series,  # NEW field per D-02
    )
```

---

## 6. Agent Singleton + Lifespan Pattern

### Module-level singleton via `@functools.lru_cache`

```python
# app/services/insights_llm.py

import functools
from pathlib import Path

from pydantic_ai import Agent

from app.core.config import settings
from app.schemas.insights import EndgameInsightsReport

_PROMPT_VERSION = "endgame_v1"
_PROMPTS_DIR = Path(__file__).parent / "insights_prompts"
_SYSTEM_PROMPT = (_PROMPTS_DIR / "endgame_v1.md").read_text(encoding="utf-8")
INSIGHTS_MISSES_PER_HOUR = 3
_OUTPUT_RETRIES = 2


@functools.lru_cache(maxsize=1)
def get_insights_agent() -> Agent[None, EndgameInsightsReport]:
    """Return the singleton Agent, constructing on first call.

    Raises:
        UserError: empty PYDANTIC_AI_MODEL_INSIGHTS or unknown model suffix.
        ValueError: unknown provider prefix (e.g., "bogus-provider:foo").

    Called from (a) main.py lifespan for startup validation (D-22),
    (b) generate_insights() at request time.
    """
    model = settings.PYDANTIC_AI_MODEL_INSIGHTS
    return Agent(
        model,
        output_type=EndgameInsightsReport,
        system_prompt=_SYSTEM_PROMPT,
        output_retries=_OUTPUT_RETRIES,
    )
```

**Decisions embedded:**
- `_SYSTEM_PROMPT` loaded at module import (Claude's Discretion). Simpler than loading inside `get_insights_agent()` — startup order is: app.main imports app.routers.insights → imports app.services.insights_llm → reads the prompt file. If the file is missing, module import raises `FileNotFoundError` before the lifespan hook runs, which is fine (startup still aborts).
- `@lru_cache(maxsize=1)` + no-arg function: cleaner than a module-level `_AGENT` assignment because (a) it delays construction to first call (lifespan timing), (b) `lru_cache.cache_clear()` enables test isolation if a test needs to reset singleton state.

### FastAPI lifespan hook (D-22)

```python
# app/main.py — EXTENDS the existing lifespan

from app.services.insights_llm import get_insights_agent
from app.services.import_service import cleanup_orphaned_jobs


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    # D-22: validate insights agent FIRST — startup failure is a deploy-blocker.
    # Orphan cleanup is best-effort and should not run if the app can't serve
    # the insights endpoint anyway.
    get_insights_agent()  # raises UserError / ValueError on misconfig
    await cleanup_orphaned_jobs()
    yield
```

**Why not a `try/except + sentry_sdk.capture_exception`:** per D-36, startup config errors "let lifespan exception propagate; Sentry's default handler captures." FastAPI's lifespan error surfacing aborts uvicorn startup, which shows in Docker logs / CI health checks. A try/except here would swallow the deploy-blocker signal.

### Thread-safety / asyncio-safety

`pydantic_ai.Agent` is safe to share across concurrent requests. Each `agent.run()` call builds fresh message history and returns an isolated `RunResult`; no per-call state is stored on the Agent instance. The Agent's `_model` is the sole shared state, and the underlying provider clients (httpx for Anthropic/Google) are themselves async-safe.

[CITED: https://github.com/pydantic/pydantic-ai/blob/main/docs/agent.md — all example apps instantiate `agent` at module level and share it]

### Is an async context manager needed?

**No.** pydantic-ai's Agent does not require `async with` for setup/teardown. The provider clients are lazily initialized on first request and reused. If a future requirement demands explicit connection pooling control, pydantic-ai offers `Agent.model_context()` — but Phase 65 doesn't need it.

---

## 7. Error Handling & Retry Flow

### `model_validator` + pydantic-ai retries (D-20)

Phase 65's `EndgameInsightsReport.unique_section_ids` validator raises `ValueError("duplicate section_id")` when the LLM emits duplicate `section_id` values. pydantic-ai's structured-output machinery catches this, packages the error into a `RetryPromptPart`, and re-invokes the LLM up to `output_retries` times.

**VERIFIED live:** running `TestModel(custom_output_args={'sections': ['a','a']})` against an Agent with `output_type=Report` (where Report has `unique_ids` validator) + `output_retries=2` raises exactly: `UnexpectedModelBehavior: Exceeded maximum retries (2) for output validation`. The retry flow works transparently — developer writes a standard Pydantic validator, pydantic-ai handles the rest.

[VERIFIED: live venv probe against 1.85.0]

### Exception handling in `generate_insights()`

```python
# app/services/insights_llm.py

import sentry_sdk
from pydantic_ai import UnexpectedModelBehavior
from pydantic_ai.exceptions import ModelAPIError

class InsightsRateLimitExceeded(Exception):
    def __init__(self, retry_after_seconds: int) -> None:
        self.retry_after_seconds = retry_after_seconds

class InsightsProviderError(Exception):
    def __init__(self, error_marker: str) -> None:
        self.error_marker = error_marker

class InsightsValidationFailure(Exception):
    """Structured-output validation exhausted output_retries."""

async def _run_agent(user_prompt: str) -> tuple[EndgameInsightsReport | None, RunUsage | None, int, str | None]:
    agent = get_insights_agent()
    t0 = time.monotonic()
    try:
        result = await agent.run(user_prompt)
    except UnexpectedModelBehavior as exc:
        # Validation failure after output_retries exhausted (D-24 + D-20).
        # Log WITHOUT response_json, error="validation_failure_after_retries".
        latency_ms = int((time.monotonic() - t0) * 1000)
        sentry_sdk.set_context("insights", {
            "findings_hash": "<caller sets this>",  # pass via contextvar or param
            "model": settings.PYDANTIC_AI_MODEL_INSIGHTS,
            "endpoint": "insights.endgame",
        })
        sentry_sdk.capture_exception(exc)
        return None, None, latency_ms, "validation_failure_after_retries"
    except ModelAPIError as exc:
        latency_ms = int((time.monotonic() - t0) * 1000)
        sentry_sdk.set_context("insights", {
            "model": settings.PYDANTIC_AI_MODEL_INSIGHTS,
            "endpoint": "insights.endgame",
        })
        sentry_sdk.capture_exception(exc)
        return None, None, latency_ms, "provider_error"
    latency_ms = int((time.monotonic() - t0) * 1000)
    return result.output, result.usage(), latency_ms, None
```

**Design notes:**
- Latency is captured around `await agent.run(...)` only (D-25). Cache lookup + DB write happen outside this scope.
- Error markers are stable strings (`"validation_failure_after_retries"`, `"provider_error"`) per D-37 — no f-string interpolation.
- Sentry `set_context("insights", {...})` before `capture_exception` per CLAUDE.md §Sentry + D-36. The `user_id` and `findings_hash` should be passed as parameters to `_run_agent` (or via a contextvar) so they land in the Sentry context without being embedded in the exception message.
- Both exception paths return `(None, None, latency_ms, marker)` — the caller writes an `llm_logs` row with `response_json=None, error=marker` before raising `InsightsProviderError` / `InsightsValidationFailure`. The log row persists via `create_llm_log`'s own-session commit (Phase 64 D-02).

### Router-level mapping to HTTP status (D-16)

```python
# app/routers/insights.py
from fastapi import HTTPException

@router.post("/endgame", response_model=EndgameInsightsResponse)
async def get_endgame_insights(...):
    try:
        return await generate_insights(filter_context, user.id, session)
    except InsightsRateLimitExceeded as exc:
        raise HTTPException(
            status_code=429,
            detail=InsightsErrorResponse(
                error="rate_limit_exceeded",
                retry_after_seconds=exc.retry_after_seconds,
            ).model_dump(),
        )
    except InsightsValidationFailure:
        raise HTTPException(
            status_code=502,
            detail=InsightsErrorResponse(error="validation_failure").model_dump(),
        )
    except InsightsProviderError:
        raise HTTPException(
            status_code=502,
            detail=InsightsErrorResponse(error="provider_error").model_dump(),
        )
```

**Note:** FastAPI's `HTTPException.detail` serializes as JSON. If the planner prefers a typed response body over `HTTPException`, use `JSONResponse(status_code=..., content=InsightsErrorResponse(...).model_dump())` — semantically equivalent, pydantic-validated on the response side.

---

## 8. Dependency Add

### pyproject.toml

```toml
dependencies = [
    # ... existing deps ...
    "pydantic-ai-slim[anthropic,google]>=1.85,<2.0",
]
```

### Install command (Wave 0)

```bash
uv add 'pydantic-ai-slim[anthropic,google]>=1.85,<2.0'
uv sync
uv run ty check app/ tests/   # ensure no new type errors
uv run pytest -x              # ensure existing 950 tests still green
```

**Why the slim extras:**
- `anthropic` — pulls `anthropic` SDK (for `anthropic:claude-*` model strings).
- `google` — pulls `google-genai` (for `google-gla:gemini-*` model strings). SEED-003 also mentions `google-vertex:*` as an alternative; if the user ever switches to Vertex AI, add `vertexai` extra.

No need for `[logfire]` (Phase 65 uses Sentry, not Logfire), `[evals]` (no pydantic-evals in Phase 65 — Phase 67 owns validation), or the bigger framework extras (`[mcp]`, `[ag-ui]`, `[ui]`).

### Runtime footprint

Installing `pydantic-ai-slim[anthropic,google]` into a fresh venv adds ~15 MB of Python code + ~25 MB of transitive deps (httpx-sse for streaming, jiter for fast JSON, the anthropic + google-genai SDKs). Nothing in conflict with current flawchess deps.

---

## 9. Validation Architecture (Nyquist)

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 8.x + pytest-asyncio 0.23.x (already in dev deps) |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` |
| Quick run command | `uv run pytest tests/services/test_insights_llm.py tests/routers/test_insights_router.py -x` |
| Full suite command | `uv run pytest` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test File | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|--------------|
| LLM-01 | `POST /api/insights/endgame` returns valid `EndgameInsightsReport` | `tests/routers/test_insights_router.py::TestHappyPath` | `uv run pytest tests/routers/test_insights_router.py::TestHappyPath -x` | ❌ Wave 0 |
| LLM-01 | Response validates through `EndgameInsightsReport.model_validate` | `tests/services/test_insights_llm.py::TestSchemaValidation` | `uv run pytest tests/services/test_insights_llm.py::TestSchemaValidation -x` | ❌ Wave 0 |
| LLM-02 | Empty `PYDANTIC_AI_MODEL_INSIGHTS` raises at startup | `tests/services/test_insights_llm.py::TestStartupValidation::test_empty_model_raises` | `uv run pytest tests/services/test_insights_llm.py::TestStartupValidation -x` | ❌ Wave 0 |
| LLM-02 | Bad provider prefix raises `ValueError` at startup | `tests/services/test_insights_llm.py::TestStartupValidation::test_bad_provider_raises` | same | ❌ Wave 0 |
| LLM-02 | `lifespan` propagates Agent construction errors | `tests/services/test_insights_llm.py::TestStartupValidation::test_lifespan_aborts_on_misconfig` | same | ❌ Wave 0 |
| LLM-03 | System prompt loaded from `endgame_v1.md` at module import | `tests/services/test_insights_llm.py::TestPromptAssembly::test_system_prompt_loaded` | `uv run pytest tests/services/test_insights_llm.py::TestPromptAssembly -x` | ❌ Wave 0 |
| LLM-03 | User prompt includes filters, flags, findings, series | `tests/services/test_insights_llm.py::TestPromptAssembly::test_user_prompt_shape` | same | ❌ Wave 0 |
| INS-04 | Duplicate findings_hash returns cache_hit without LLM call | `tests/routers/test_insights_router.py::TestCacheBehavior::test_cache_hit_no_llm_call` | `uv run pytest tests/routers/test_insights_router.py::TestCacheBehavior -x` | ❌ Wave 0 |
| INS-04 | Cache key includes prompt_version (bump invalidates) | `tests/routers/test_insights_router.py::TestCacheBehavior::test_prompt_version_bump_misses` | same | ❌ Wave 0 |
| INS-04 | Cache key includes model (env swap invalidates) | `tests/routers/test_insights_router.py::TestCacheBehavior::test_model_swap_misses` | same | ❌ Wave 0 |
| INS-05 | 4th miss in hour returns tier-2 stale report (HTTP 200) | `tests/routers/test_insights_router.py::TestRateLimit::test_rate_limit_soft_fails_to_stale` | `uv run pytest tests/routers/test_insights_router.py::TestRateLimit -x` | ❌ Wave 0 |
| INS-05 | 4th miss with no stale report returns HTTP 429 + retry_after | `tests/routers/test_insights_router.py::TestRateLimit::test_rate_limit_429_when_no_stale` | same | ❌ Wave 0 |
| INS-05 | `count_recent_successful_misses` filter correctness | `tests/repositories/test_llm_log_repository_reads.py::TestCountRecentMisses` | `uv run pytest tests/repositories/test_llm_log_repository_reads.py -x` | ❌ Wave 0 |
| INS-05 | `get_latest_report_for_user` returns most recent matching row | `tests/repositories/test_llm_log_repository_reads.py::TestLatestReportForUser` | same | ❌ Wave 0 |
| INS-06 | Overview str is non-empty when report is produced (schema contract) | `tests/services/test_insights_llm.py::TestSchemaValidation::test_overview_non_null` | covered above | ❌ Wave 0 |
| INS-07 | Provider error returns HTTP 502 + `provider_error` envelope | `tests/routers/test_insights_router.py::TestErrors::test_provider_error_502` | `uv run pytest tests/routers/test_insights_router.py::TestErrors -x` | ❌ Wave 0 |
| INS-07 | Validation failure after retries returns HTTP 502 + `validation_failure` | `tests/routers/test_insights_router.py::TestErrors::test_validation_failure_502` | same | ❌ Wave 0 |
| INS-07 | Sentry set_context called with user_id + findings_hash + model | `tests/services/test_insights_llm.py::TestSentryCapture::test_set_context_structured` | `uv run pytest tests/services/test_insights_llm.py::TestSentryCapture -x` | ❌ Wave 0 |
| INS-07 | No variable interpolation in exception messages | `tests/services/test_insights_llm.py::TestSentryCapture::test_no_var_in_exc_message` | same | ❌ Wave 0 |
| — (D-02/D-03) | Weekly→monthly resample: weighted-by-n mean, n summed | `tests/services/test_insights_service_series.py::TestResample::test_monthly_weighted_mean` | `uv run pytest tests/services/test_insights_service_series.py -x` | ❌ Wave 0 |
| — (D-02/D-03) | `last_3mo` window pass-through preserves weekly points | `tests/services/test_insights_service_series.py::TestResample::test_last_3mo_pass_through` | same | ❌ Wave 0 |
| — (D-04) | Sparse-combo <10 points returns None (skipped) | `tests/services/test_insights_service_series.py::TestEloCombo::test_sparse_combo_skipped` | same | ❌ Wave 0 |
| — (D-04) | Endgame ELO series is gap-only | `tests/services/test_insights_service_series.py::TestEloCombo::test_gap_only_series` | same | ❌ Wave 0 |
| — (D-05) | `type_win_rate_timeline` emits monthly for both windows | `tests/services/test_insights_service_series.py::TestTypeTimeline::test_monthly_both_windows` | same | ❌ Wave 0 |
| — (D-20) | Duplicate section_id triggers validator → pydantic-ai retries | `tests/services/test_insights_llm.py::TestRetryBehavior::test_duplicate_section_retries` | `uv run pytest tests/services/test_insights_llm.py::TestRetryBehavior -x` | ❌ Wave 0 |
| — (D-38) | `fake_insights_agent` fixture uses TestModel | `tests/conftest.py` fixture + `tests/services/test_insights_llm.py::TestFixtures` | `uv run pytest tests/services/test_insights_llm.py::TestFixtures -x` | ❌ Wave 0 |
| — (D-39) | `FunctionModel` asserts specific token counts logged | `tests/services/test_insights_llm.py::TestTokenAccounting::test_function_model_tokens` | `uv run pytest tests/services/test_insights_llm.py::TestTokenAccounting -x` | ❌ Wave 0 |

### Happy / edge / failure per test file

**`tests/services/test_insights_llm.py`** (Agent wiring, prompt assembly, startup, soft-fail tiering, rate limit boundary)

- **Happy:** `TestHappyPath::test_generate_insights_fresh_miss` — monkeypatch `get_insights_agent` → `Agent(TestModel(custom_output_args=...), output_type=EndgameInsightsReport)`; call `generate_insights(filter_context, user_id, session)`; assert returned envelope has `status="fresh"`, one `llm_logs` row written with `cache_hit=False, error=None, response_json != None`.
- **Edge:** `TestCacheBehavior::test_second_call_cache_hits` — call twice with same filters; second returns `status="cache_hit"`, zero new log rows.
- **Edge:** `TestPromptAssembly::test_user_prompt_shape` — assert generated user prompt contains every expected section: filters, flags, per-subsection findings, `### Series (...)` blocks for timeline subsections.
- **Edge:** `TestRateLimit::test_boundary_3_misses_allowed_4th_stale` — seed 3 successful misses → 4th call returns `status="stale_rate_limited"` (NOT 429).
- **Edge:** `TestRateLimit::test_rate_limit_window_rollover` — seed 3 misses with `created_at` 61 minutes ago → 4th call is a fresh miss (not rate-limited).
- **Failure:** `TestStartupValidation::test_empty_model_raises` — set `PYDANTIC_AI_MODEL_INSIGHTS=""`, call `get_insights_agent()`, assert `UserError` raised.
- **Failure:** `TestStartupValidation::test_bad_provider_raises` — set `PYDANTIC_AI_MODEL_INSIGHTS="bogus:foo"`, assert `ValueError` raised.
- **Failure:** `TestRetryBehavior::test_duplicate_section_retries` — TestModel returns duplicate `section_id`, `output_retries=2`, assert `UnexpectedModelBehavior` raised after retries exhaust.
- **Failure:** `TestErrors::test_provider_error_logs_row` — FunctionModel raises `ModelHTTPError` — assert one `llm_logs` row with `error="provider_error", response_json=None`.
- **Failure:** `TestSentryCapture::test_set_context_called` — mock `sentry_sdk`, trigger provider error, assert `sentry_sdk.set_context("insights", {...})` called before `capture_exception`, and `findings_hash` / `model` / `user_id` appear in the context dict.

**`tests/routers/test_insights_router.py`** (endpoint, envelopes, HTTP status)

- **Happy:** `TestHappyPath::test_fresh_miss_200` — POST with valid filters, assert 200 + `status="fresh"` in response body.
- **Happy:** `TestHappyPath::test_cache_hit_200` — repeat same request, assert 200 + `status="cache_hit"`, zero new `llm_logs` rows.
- **Edge:** `TestHappyPath::test_hide_overview` — set `INSIGHTS_HIDE_OVERVIEW=true`, assert response `report.overview == ""` AND the underlying `llm_logs.response_json.overview` is still full text (D-18 log-is-source-of-truth).
- **Edge:** `TestCacheBehavior::test_prompt_version_bump_misses` — seed row with `prompt_version="endgame_v0"`, call endpoint with current `endgame_v1`, assert miss (fresh LLM call).
- **Edge:** `TestCacheBehavior::test_model_swap_misses` — seed row with `model="anthropic:claude-haiku-4-5"`, call endpoint with `model="google-gla:gemini-2.5-flash"`, assert miss.
- **Edge:** `TestRateLimit::test_stale_filters_populated` — seed tier-2 row with different filter_context; on rate-limited 4th request with current filters, assert response `stale_filters` field is populated and differs from request filters.
- **Edge:** `TestRateLimit::test_stale_filters_null_when_match` — seed tier-2 row with same filter_context; on rate-limited 4th, `stale_filters` should be null (not populated when match — see D-14).
- **Failure:** `TestRateLimit::test_429_no_stale` — 3 successful misses + zero tier-2 fallback (different model/prompt); 4th call returns 429 + `retry_after_seconds > 0`.
- **Failure:** `TestErrors::test_provider_error_502` — monkeypatch Agent to raise `ModelHTTPError` on `.run()`, assert 502 + `error="provider_error"`.
- **Failure:** `TestErrors::test_validation_failure_502` — TestModel returns invalid dict; after `output_retries` exhaust, assert 502 + `error="validation_failure"`.
- **Failure:** `TestAuth::test_unauth_rejected` — POST without auth header, assert 401.

**`tests/repositories/test_llm_log_repository_reads.py`** (new read helpers)

- **Happy:** `TestCountRecentMisses::test_counts_successful_misses_only` — seed 5 rows (2 success, 1 error=not null, 1 response_json=null, 1 cache_hit=true); assert count == 2.
- **Happy:** `TestLatestReportForUser::test_returns_most_recent_matching` — seed 3 rows with different `created_at`, assert most-recent one returned.
- **Edge:** `TestCountRecentMisses::test_respects_time_window` — seed rows at `created_at` 30/60/90 minutes ago with `window=1h`; assert count includes only the 30-minute-ago row.
- **Edge:** `TestCountRecentMisses::test_excludes_other_users` — seed rows for user_id=1 and user_id=2; query for user_id=1, assert user_id=2 rows excluded.
- **Edge:** `TestLatestReportForUser::test_filters_by_prompt_version_and_model` — seed rows with different prompt_version/model combos; assert only matching rows considered.
- **Failure:** `TestLatestReportForUser::test_none_when_no_match` — query with no rows, assert `None` returned.
- **Failure:** `TestCountRecentMisses::test_zero_when_no_rows` — query for user with no rows, assert count == 0.

**`tests/services/test_insights_service_series.py`** (resampling logic)

- **Happy:** `TestResample::test_monthly_weighted_mean` — 4 weekly points in same month `[(0.5, n=10), (0.6, n=20), (0.4, n=10), (0.7, n=10)]` → expected weighted mean = (0.5*10 + 0.6*20 + 0.4*10 + 0.7*10) / 50 = 0.58, n=50.
- **Happy:** `TestResample::test_last_3mo_pass_through` — 5 weekly points → 5 TimePoints, same dates/values, no aggregation.
- **Edge:** `TestResample::test_monthly_single_week` — 1 weekly point in a month → 1 TimePoint with same value, n.
- **Edge:** `TestResample::test_monthly_key_format` — assert `bucket_start` is `"YYYY-MM-01"` ISO format (YYYY-MM first-of-month).
- **Edge:** `TestResample::test_empty_input` — empty list → empty list.
- **Edge:** `TestResample::test_all_zero_n_fallback` — weeks all have n=0 → arithmetic mean fallback, n=0.
- **Happy:** `TestEloCombo::test_gap_only_series` — combo with points: `endgame_elo=1500, actual_elo=1400 → gap=100`; assert TimePoint.value == 100.
- **Edge:** `TestEloCombo::test_sparse_combo_skipped` — combo with 9 points → `_series_for_endgame_elo_combo` returns None.
- **Edge:** `TestEloCombo::test_threshold_boundary` — combo with exactly 10 points → not skipped.
- **Happy:** `TestTypeTimeline::test_monthly_both_windows` — given per_type with 52 weekly points per class, assert monthly resample for both `all_time` AND `last_3mo` (both get monthly granularity per D-05).
- **Happy:** `TestIntegration::test_compute_findings_populates_series` — end-to-end call into `compute_findings` with seeded endgame_service output; assert returned `EndgameTabFindings.findings` has `series != None` for exactly the 4 timeline subsection_ids and `series is None` for everything else.

### Sampling Rate

- **Per task commit:** `uv run pytest tests/services/ tests/routers/test_insights_router.py tests/repositories/test_llm_log_repository_reads.py -x`  (~5s)
- **Per wave merge:** `uv run pytest` (full suite)
- **Phase gate:** Full suite green + ruff + ty clean before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `tests/services/test_insights_llm.py` — new file
- [ ] `tests/routers/test_insights_router.py` — new file
- [ ] `tests/repositories/test_llm_log_repository_reads.py` — new file
- [ ] `tests/services/test_insights_service_series.py` — new file
- [ ] `tests/conftest.py` — add `os.environ["PYDANTIC_AI_MODEL_INSIGHTS"] = "test"` at module top (alongside existing SENTRY_DSN / SECRET_KEY)
- [ ] `tests/conftest.py` — add `fake_insights_agent(report: EndgameInsightsReport)` fixture per D-38
- [ ] `app/services/insights_prompts/endgame_v1.md` — NEW system-prompt file
- [ ] Framework install: `uv add 'pydantic-ai-slim[anthropic,google]>=1.85,<2.0' && uv sync`

---

## 10. Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| PostgreSQL 18 | Rate-limit query, llm_logs reads/writes | ✓ | already running dev via docker compose | — |
| Python 3.13 | All backend code | ✓ | pinned in pyproject.toml | — |
| uv | Dep management | ✓ | already used in CLAUDE.md commands | — |
| `pydantic-ai-slim[anthropic,google]` | Phase 65 core | ✗ | — | NOT OPTIONAL — install via `uv add` in Wave 0 |
| `ANTHROPIC_API_KEY` (prod) | Live LLM calls on Hetzner | ✗ (per STATE.md blockers) | — | Set on server before deploy; tests use `test` provider |
| `PYDANTIC_AI_MODEL_INSIGHTS` env var | Startup validation | — (set per-env) | — | `.env.example` pins recommended default; conftest.py sets `"test"` for tests |
| genai-prices 0.0.56 | Cost computation (Phase 64 repo) | ✓ | pinned | Confirmed covers Haiku 4.5 + Gemini 2.5/3 Flash |

**Missing dependencies with no fallback:**
- `pydantic-ai-slim[anthropic,google]` — must be installed Wave 0.
- Production `ANTHROPIC_API_KEY` on Hetzner — user action required before Phase 65 ships. STATE.md already flags this; planner should include a deployment-checklist task.

**Missing dependencies with fallback:**
- None — tests use `PYDANTIC_AI_MODEL_INSIGHTS="test"` which passes Agent startup validation without needing real API keys.

---

## 11. Security Domain

Phase has `security_enforcement` implied via CLAUDE.md's Sentry + no-variable-in-exception-messages rules. Scope is backend API endpoint auth + Sentry grouping.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | yes | FastAPI-Users `current_active_user` dependency on router (matches `app/routers/endgames.py` pattern) |
| V3 Session Management | no | Stateless JWT (FastAPI-Users default); no session state in Phase 65 |
| V4 Access Control | yes | User can only view their own `llm_logs` / reports — enforced by `user_id == user.id` filter in all read queries |
| V5 Input Validation | yes | `FilterContext` Pydantic model validates query params; `POST /api/insights/endgame` rejects unknown fields |
| V6 Cryptography | no | No crypto in Phase 65 (SECRET_KEY handled by FastAPI-Users; HTTPS terminated by Caddy) |
| V7 Error Handling | yes | CLAUDE.md §Sentry: stable error markers, no variable-in-message; `InsightsErrorResponse.error` uses Literal enum |
| V8 Data Protection | yes | No PII in prompts/responses (chess stats only, tied to user_id); GDPR deletion via `ON DELETE CASCADE` on `llm_logs.user_id` FK (Phase 64) |

### Known Threat Patterns for FastAPI + pydantic-ai

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Prompt injection via filter values (user-controlled `time_controls[]` etc.) | Tampering | Filter values pass through Pydantic validation; the user prompt embeds them verbatim BUT the LLM's system prompt is loaded from a file the user can't control, and `output_type=EndgameInsightsReport` forces structured output — no free-text escape surface. Low risk; still, planner should NOT put user-controlled strings into instruction scope (they're in user-message scope). |
| API key leakage via error messages | Information Disclosure | `ModelHTTPError.__str__` does NOT include API key (anthropic/google SDKs scrub); `sentry_sdk.capture_exception` respects this. Our error envelope returns stable markers only. |
| Cost-exhaustion DoS via authenticated user | Denial of Service (amplified) | Rate limit 3 misses/hr/user (INS-05) bounds per-user cost. Per-minute burst still possible during the 3-miss window — acceptable; monitor `llm_logs` in prod. |
| Cross-user log disclosure | Information Disclosure | `get_latest_report_for_user(user_id=user.id, ...)` always scopes to authenticated user; router's `Depends(current_active_user)` ensures `user.id` is server-side. |
| Timing attack on cache hits | Information Disclosure (negligible) | Cache-hit responses are measurably faster than misses, but this leaks only "user has made this query before" — not sensitive. |
| Replay attack on LLM cost | — | Cache key = (findings_hash, prompt_version, model) — user cannot force cache miss with trivial param changes; findings_hash is deterministic over user's actual data, so different users always produce different hashes. |

---

## 12. Project Constraints (from CLAUDE.md)

- **ty compliance:** `uv run ty check app/ tests/` must pass with zero errors. Planner: add explicit return types on all new functions, use `Sequence[T]` for list params, explicit `dict[str, str]` annotations where `ty` needs invariant widening (see Phase 63 Plan 04 pattern).
- **No magic numbers:** `INSIGHTS_MISSES_PER_HOUR = 3`, `_OUTPUT_RETRIES = 2`, `_RATE_LIMIT_WINDOW = datetime.timedelta(hours=1)`, `_SPARSE_COMBO_FLOOR = 10`, `_PROMPT_VERSION = "endgame_v1"` — all at module-top of `insights_llm.py` or `insights_service.py`.
- **Literal types:** `EndgameInsightsResponse.status`, `InsightsErrorResponse.error`, `SectionInsight.section_id`, `FlagId`, `SubsectionId` — every fixed-string-set field MUST be `Literal[...]`.
- **No `asyncio.gather` on same AsyncSession:** `generate_insights()` makes sequential awaits only (compute_findings → cache lookup → rate-limit count → agent.run → create_llm_log). Already designed correctly in CONTEXT.md §specifics.
- **httpx async only:** pydantic-ai's Anthropic/Google SDKs already use async httpx. No `requests` imports.
- **Sentry patterns:** `sentry_sdk.set_context("insights", {...})` then `sentry_sdk.capture_exception(exc)`. NEVER embed `user_id`, `findings_hash`, or filter values in exception messages (fragments Sentry grouping).
- **Router convention:** `APIRouter(prefix="/insights", tags=["insights"])`, decorators use relative paths (`@router.post("/endgame")`), never `@router.post("/insights/endgame")`.
- **FK constraints:** Phase 64 already set `ON DELETE CASCADE` on `llm_logs.user_id → users.id`. Phase 65 adds no new FK.
- **Version control:** Phase 65 on feature branch; PR to main; don't commit `.env`. `PYDANTIC_AI_MODEL_INSIGHTS` goes in `.env.example` only.

---

## 13. Sources

### Primary (HIGH confidence)

- **context7 `/pydantic/pydantic-ai`** — Agent constructor, output_type, system_prompt vs instructions, testing (TestModel/FunctionModel), Agent.override, ModelRetry, UnexpectedModelBehavior, output_validator. All 1.85-aligned.
- **Live venv probe** `uv pip install 'pydantic-ai-slim[anthropic,google]==1.85.0'` → `inspect.signature(Agent.__init__)` + `inspect.signature(TestModel.__init__)` + exception enumeration + live `Agent("").run(...)` behavior. Supersedes any context7/training-data claims.
- **PyPI JSON** `https://pypi.org/pypi/pydantic-ai-slim/json` — latest version 1.85.0, released 2026-04-21.
- **genai-prices 0.0.56** (already pinned) — local `calc_price(...)` probe confirms Haiku 4.5 / Gemini 2.5 Flash / Gemini 3 Flash Preview coverage.
- **Phase 63 source** `app/services/insights_service.py`, `app/schemas/insights.py`, `app/schemas/endgames.py` — timeline data shapes, `_compute_trend`, SubsectionFinding schema.
- **Phase 64 source** `app/repositories/llm_log_repository.py`, `app/models/llm_log.py`, `app/schemas/llm_log.py` — repo own-session pattern, index coverage, cost computation, LlmLogCreate DTO.
- **`reports/benchmarks-2026-04-18.md` §6** — per-combo distribution confirming ≥10 game floor for sparse-combo filter.

### Secondary (MEDIUM confidence)

- **https://github.com/pydantic/pydantic-ai/blob/main/docs/agent.md** — official reference for system_prompt vs instructions, reflection/self-correction, model errors. Aligns with venv probe.
- **https://github.com/pydantic/pydantic-ai/blob/main/docs/testing.md** — Agent.override pattern, TestModel + FunctionModel usage. Confirmed by venv probe.
- **https://github.com/pydantic/pydantic-ai/blob/main/docs/install.md** — slim install extras for `[anthropic,google]`.

### Tertiary (LOW confidence, flagged if used)

- None — every claim in this research is either venv-verified or sourced from current official docs.

---

## 14. Open Questions

1. **Does pydantic-ai's `output_retries=2` mean "2 retries" (3 total) or "max 2 attempts"?**
   - What we know: live probe with `output_retries=2` raised `"Exceeded maximum retries (2) for output validation"` — so `2` appears in the error message. Semantically ambiguous from error text alone.
   - What's unclear: whether the initial attempt counts toward the `2` or not. Source code reading needed for certainty; the error message wording suggests "retries" means "retry attempts after the initial", which would make `output_retries=2` = 3 total attempts.
   - Recommendation: planner pins `output_retries=2` as a starting point (matching D-24 "2-3"). If TestModel-based tests show only 2 attempts happen, bump to `3`. Non-blocking — runtime behavior is self-adjusting via the test output.

2. **Should the router use `JSONResponse(status_code=...)` or `HTTPException` for error envelopes?**
   - What we know: both work. FastAPI's `HTTPException(status_code=..., detail=dict)` serializes `detail` as JSON.
   - What's unclear: whether Phase 66 frontend TanStack Query's error handler reads `response.json().detail` (HTTPException path) vs `response.json()` (JSONResponse path).
   - Recommendation: planner picks. `HTTPException` is idiomatic FastAPI; `JSONResponse` gives a cleaner top-level shape. Either way, document the on-the-wire JSON shape clearly for Phase 66.

3. **Should `_SYSTEM_PROMPT` be loaded at module import (chosen) or lazily inside `get_insights_agent()`?**
   - What we know: Claude's Discretion per CONTEXT.md. Module-import loading is slightly faster for tests (prompt loads once, Agent builds per-test via `lru_cache.cache_clear()`) but tightly couples module-import time to filesystem state.
   - What's unclear: whether a future "dynamic prompt variant for admin users" requirement (deferred to v1.12) would demand lazy loading.
   - Recommendation: stay with module-import loading for Phase 65 simplicity. If v1.12 admin raw-data mode ships, the loading moves into the (then non-lru-cached) factory function.

---

## Assumptions Log

No claims in this research are tagged `[ASSUMED]`. Every factual assertion is either `[VERIFIED]` (via live venv probe, PyPI, genai-prices probe, or codebase read) or `[CITED]` (pointing to a current pydantic-ai docs URL). All API signatures, exception classes, and price-coverage numbers were reproduced live as of 2026-04-21, not recalled from training data.

---

## Metadata

**Confidence breakdown:**
- pydantic-ai API surface: HIGH — live-probed against 1.85.0
- Model selection + pricing: HIGH — genai-prices probe confirms coverage, Haiku track record is industry-documented
- DB queries + index coverage: HIGH — Phase 64 index verified via psql inspection in Phase 64 Plan 02 SUMMARY; SQLAlchemy 2.x async patterns standard
- Resampling logic: HIGH — stdlib-only, pattern matches Phase 63 `_compute_trend`
- Agent singleton + lifespan: HIGH — pattern matches existing `cleanup_orphaned_jobs` hook + pydantic-ai module-level idiom
- Error handling + retry: HIGH — `UnexpectedModelBehavior` path live-verified
- Sentry integration: HIGH — existing patterns in `insights_service.py` `compute_findings` set the precedent

**Research date:** 2026-04-21
**Valid until:** 2026-05-21 (pydantic-ai is fast-moving; re-verify API signatures if phase execution slips >30 days)
