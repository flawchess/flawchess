# Phase 65: LLM Endpoint with pydantic-ai Agent - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in 65-CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-21
**Phase:** 65 - llm-endpoint-with-pydantic-ai-agent
**Areas discussed:** SEED-004 disposition & prompt contract, Rate limiter, Soft-fail fallback, Response/error envelope, Startup validation, Testing strategy, Endpoint shape & code organization, Overview-hide config & section count

---

## SEED-004 Disposition & Prompt Contract

User surfaced `SEED-004-trend-texture-for-llm-insights.md` as relevant. Presented three dispositions (defer to v1.12, insert a pre-phase, fold into Phase 65). User redirected the whole question: do we even need a deterministic trend pipeline given modern LLMs can read raw weekly points? Planned models: Gemini 3 Flash / Haiku 4.5.

Agreed — the deterministic Trend label + `is_headline_eligible` guardrails are obsolete for small-LLM-narration use cases. Cost is ~2-3k timeseries tokens even at worst case (Endgame ELO fanout of 8 combos × 2 lines × 65 weeks = 1040 points). Aggregation strategy then discussed:

| Option | Description | Selected |
|--------|-------------|----------|
| Pass all timelines at weekly resolution | Simple, ~9k timeseries tokens worst case | |
| Weekly for last_3mo, monthly for all_time | Halves density, same narrative power | ✓ |
| Drop timelines entirely, keep scalar findings | Cheapest, loses trend signal | |
| Separate phase for schema extension | Respects roadmap scope | |

Plus: Endgame ELO emits gap-only (not both lines); drop sparse combos (<10 games in window).

**User's choice:** Resample per window (weekly last_3mo, monthly all_time), Endgame ELO gap-only + sparse-combo filter, `series: list[TimePoint] | None` on SubsectionFinding, SEED-004 closes as superseded.
**Notes:** Added one gray area the user's reframing exposed — worst-case token payload is real and warrants the resampling step even with the "just pass raw points" approach.

---

## Rate Limiter Implementation

| Option | Description | Selected |
|--------|-------------|----------|
| DB query on llm_logs | Uses ix_llm_logs_user_id_created_at index; ~1ms; authoritative | ✓ |
| In-memory sliding window | Sub-millisecond but resets on restart/multiprocess | |

| Sub-option | Description | Selected |
|------------|-------------|----------|
| Count failed provider calls against quota | Stricter; hostile during outages | |
| Count only successful misses | response_json IS NOT NULL AND error IS NULL | ✓ |

**User's choice:** DB-backed, only successful misses count.
**Notes:** User confirmed "keep it simple." Also noted that the "Generate insights" button (INS-01 / Phase 66 scope) means generation is user-click driven, not auto-on-load — confirms rate-limit math.

---

## Soft-Fail Fallback Scope

| Option | Description | Selected |
|--------|-------------|----------|
| Strict same-key only | `get_latest_log_by_hash` — useless in rate-limit scenarios | |
| Any prior successful report, any filters | Guaranteed content but filter-mismatch UX bug | |
| Tiered: exact → any-recent under same prompt/model → 429 | Explicit stale signal via envelope | ✓ |

**User's choice:** Tiered with `status="stale_rate_limited"` + `stale_filters` in envelope. Provider errors return HTTP 502, NOT stale fallback.
**Notes:** Rate-limit soft-fail is the ONLY path that returns content the user didn't just trigger. Provider errors surface as retryable failures — serving stale on provider error blurs "is this fresh?" vs "is the LLM down?".

---

## Response / Error Envelope

| Option | Description | Selected |
|--------|-------------|----------|
| Single 200 envelope with status discriminator | TanStack Query friendly, self-documenting | ✓ |
| HTTP status + headers (X-Cache, X-Stale) | Headers awkward in OpenAPI/TanStack | |
| 200/203/429/502 split | Clever but obscure | |

Envelope details:
- `EndgameInsightsResponse(report, status, stale_filters)` for 200
- `InsightsErrorResponse(error, retry_after_seconds)` for 4xx/5xx
- `error` field is diagnostic; user-facing retry copy owned by frontend
- `report.model_used` + `report.prompt_version` leaked to client for debugging

**User's choice:** Option 1 (single envelope), detailed mapping per D-14 through D-20.

---

## Startup Model Validation

| Option | Description | Selected |
|--------|-------------|----------|
| Level 1: regex on env-var format | Cheapest; misses real typos | |
| Level 2: pydantic-ai Agent construction | Catches most invalidities, no API call | ✓ |
| Level 3: dry-run agent.run() | Catches everything but blocks deploy on provider outages | |

Plus: lazy `get_insights_agent()` with `@lru_cache`, called from FastAPI lifespan for startup validation and from `generate_insights()` at request time. `PYDANTIC_AI_MODEL_INSIGHTS: str = ""` in Settings; empty = unconfigured = startup fails.

**User's choice:** Level 2, lifespan hook, lru_cache'd accessor.

---

## Testing Strategy

| Option | Description | Selected |
|--------|-------------|----------|
| pydantic-ai TestModel (default) | Flows through schema validation; no API keys | ✓ |
| FunctionModel for token-count tests | Fine-grained control where needed | ✓ (secondary) |
| Mock at agent.run() boundary | Skips pydantic-ai validation machinery | |
| VCR cassettes | Brittle; maintenance cost | |

`os.environ["PYDANTIC_AI_MODEL_INSIGHTS"] = "test"` in tests/conftest.py at module top (alongside SENTRY_DSN / SECRET_KEY).

**User's choice:** TestModel default + FunctionModel for token specifics. No real-provider calls in Phase 65 tests (VAL-01 in Phase 67 covers that).

---

## Endpoint Request Shape + Code Organization + Info-Popover Source

| Option | Description | Selected |
|--------|-------------|----------|
| POST with JSON body (FilterContext) | Natural POST semantics | |
| POST with query params matching /endgames/overview | Consistency with existing endgames endpoint; Phase 66 can reuse query-string builder | ✓ |

Code layout: router (`app/routers/insights.py`), orchestration (`app/services/insights_llm.py`), system prompt (`app/services/insights_prompts/endgame_v1.md`), schemas extended in existing `app/schemas/insights.py` (no premature split).

Info-popover source:
| Option | Description | Selected |
|--------|-------------|----------|
| New popovers.py (SEED-003 option a) | Drift risk | |
| Skip in MVP; inline "Metric glossary" in endgame_v1.md | Simplest | ✓ |
| Build-step extraction from JSX | Overkill | |

**User's choice:** Query-param endpoint, service-owned orchestration, schemas in existing file, inline glossary in system prompt.

---

## Overview-Hide Config + Variable Section Count

Overview hide:
| Option | Description | Selected |
|--------|-------------|----------|
| Env var flag, backend strips overview to "" | Simple, stateless, no leakage | ✓ |
| DB-side config | Overkill for one flag | |
| Frontend-driven hiding | Leaks via devtools | |

Log row still captures full overview — response is policy-gated view; log is source of truth.

Section count:
| Option | Description | Selected |
|--------|-------------|----------|
| Always exactly 4 sections | Stable layout, filler "insufficient data" headlines | |
| Variable 1-4, LLM decides via prompt rule | Cleaner UI; trust the LLM | ✓ |
| 4 with `adequate_data: bool` per section | Extra schema complexity | |

`sections: list[SectionInsight]` with `min_length=1, max_length=4`. Pydantic `model_validator` enforces `section_id` uniqueness.

**User's choice:** Env var + backend strip; variable section count with LLM-driven omission.

---

## Claude's Discretion

Items delegated to planner/researcher:
- Exact pydantic-ai API surface (Agent signature, usage attribute, retry param, TestModel constructor) — researcher validates via context7
- Sparse-combo threshold for Endgame ELO timeline (floor: ≥10 games)
- Monthly-bucketing key format (`YYYY-MM` vs ISO first-of-month)
- Whether `last_3mo` window emits for `type_win_rate_timeline` at all
- Default model value in `.env.example` (Haiku 4.5 vs Gemini 2.5/3 Flash)
- Whether `_load_system_prompt` runs at import or in lru_cache first call
- Weighted-by-`n` vs unweighted monthly mean for resampling

---

## Deferred Ideas

- Cache-hit row logging (Phase 64 `cache_hit` column stays unused)
- In-memory lock for cold-cache concurrent requests
- Ripping Trend / is_headline_eligible / weekly_points_in_window from schema (stop feeding, leave on schema)
- Popover text extraction to `popovers.py` (revisit if VAL-01 surfaces drift)
- Real-provider integration tests (Phase 67 scope)
- Admin raw-data mode (v1.12 / SEED-001)
- Per-section streaming responses
- Cross-AI model A/B at endpoint level (out of scope per REQUIREMENTS)
- Weighted monthly mean (Claude's Discretion to planner)
