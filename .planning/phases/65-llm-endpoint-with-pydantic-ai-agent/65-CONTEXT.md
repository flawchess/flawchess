# Phase 65: LLM Endpoint with pydantic-ai Agent - Context

**Gathered:** 2026-04-21
**Status:** Ready for planning
**Requirements:** LLM-01, LLM-02, LLM-03, INS-04, INS-05, INS-06, INS-07

<domain>
## Phase Boundary

Backend-only. Deliver `POST /api/insights/endgame`: a pydantic-ai Agent with `result_type=EndgameInsightsReport`, findings-hash cache on `llm_logs`, DB-backed rate limit (3 successful misses/hr/user), soft-fail to last cached report, and one `llm_logs` row per miss. Ships with:

- Orchestration service `app/services/insights_llm.py` (Agent singleton, prompt assembly, cache/rate-limit/log wiring, response-envelope construction).
- Versioned system prompt at `app/services/insights_prompts/endgame_v1.md` (loaded once at startup, never inline string literals in `.py`).
- Router `app/routers/insights.py` (thin; FilterContext construction + single call into `generate_insights`).
- Response/error envelopes, `EndgameInsightsReport`, and `SectionInsight` Pydantic schemas added to the existing `app/schemas/insights.py`.
- Two new `llm_log_repository` read helpers (`count_recent_successful_misses`, `get_latest_report_for_user`).
- A small schema extension to Phase 63's `SubsectionFinding`: optional `series: list[TimePoint] | None` carrying resampled timeseries for the 4 timeline subsections.
- Resampling logic inside `insights_service.compute_findings` (weekly for `last_3mo`, monthly for `all_time`; Endgame ELO gap-only + sparse-combo filter).

Out of scope: frontend (Phase 66), ground-truth regression tests (Phase 67), beta-flag-flipping (Phase 67), `cache_hit=true` log rows (deferred per Phase 64 D-05 / SEED-003 Open Q).

</domain>

<decisions>
## Implementation Decisions

### Findings → Prompt Contract (supersedes SEED-004)

- **D-01:** Pass raw weekly/monthly timeseries to the LLM for the 4 timeline subsections (`score_gap_timeline`, `clock_diff_timeline`, `endgame_elo_timeline`, `type_win_rate_timeline`). Drop the deterministic trend pipeline from the LLM's view: `Trend`, `is_headline_eligible`, and `weekly_points_in_window` are no longer fed into the prompt. Haiku 4.5 / Gemini Flash 2.5 / 3.x reliably narrate trend, volatility, and recent shifts from a ~50-point series; the 4-label trend enum erases everything interesting. Deterministic cross-section FLAGS stay — those encode correctness the LLM reliably gets wrong without guardrails. Trend narration does not.
- **D-02:** Extend `SubsectionFinding` with `series: list[TimePoint] | None = None` (only populated for the 4 timeline subsections). `TimePoint = BaseModel(bucket_start: str, value: float, n: int)` — ISO-date bucket start + value + sample size. Phase 63 schema gets this one additive optional field; `findings_hash` covers it naturally (already computed via canonical JSON of the findings list).
- **D-03:** Resample per window. `last_3mo` → weekly buckets (≤13 points per series). `all_time` → monthly buckets (`YYYY-MM`, mean of weeks in month, sample sizes summed). Resampling happens inside `insights_service.compute_findings` — Phase 65 does NOT make prompt-assembly responsible for rebucketing. Stdlib-only (`statistics.mean` over grouped weeks).
- **D-04:** Endgame ELO timeline ships as gap-only (`endgame_elo − actual_elo`) per `(platform, time_control)` combo, NOT both lines. Drop combos with fewer than ~10 games in the window (exact threshold picked by planner, but ≥10 is the floor). Typical active user yields 1-2 surviving combos; power users ≤4. Bounds the per-report timeseries token footprint at ~2-3k worst case, ~1k typical.
- **D-05:** `type_win_rate_timeline` emits monthly-only (both windows) — 5-way type split makes weekly noise. Keep all 5 types; planner confirms whether `last_3mo` window adds signal or is always empty at this granularity.
- **D-06:** SEED-004 closes as superseded — its `volatility_cv` / `recent_vs_prior_delta` fields become moot once the LLM sees the raw series. Seed file gets a status update to `closed_superseded_by_phase_65` at phase completion.
- **D-07:** `Trend`, `is_headline_eligible`, `weekly_points_in_window` stay defined on `SubsectionFinding` for now (not ripped out in Phase 65) but are NOT rendered into the LLM prompt. Planner may opt to delete them in Phase 65 as part of the findings→prompt wiring; acceptable either way. `findings_hash` unchanged whether they live or die on the schema — they're serialised values regardless. If deleted, `findings_hash` churns once on deploy (acceptable; cache is a week old at most).

### Cache + Rate Limit + Soft-Fail (INS-04, INS-05)

- **D-08:** Cache key = `(findings_hash, prompt_version, model)`. Reuses Phase 64's `get_latest_log_by_hash` — exact match only. Cache hits produce NO new `llm_logs` row (Phase 64 D-05 default preserved; hit-logging deferred).
- **D-09:** Rate-limit check is a DB query (NOT in-memory): `COUNT(*) FROM llm_logs WHERE user_id=? AND created_at > now() - interval '1 hour' AND cache_hit=false AND error IS NULL AND response_json IS NOT NULL`. Uses Phase 64 D-07's `ix_llm_logs_user_id_created_at` index. Limit constant `INSIGHTS_MISSES_PER_HOUR = 3` lives in `app/services/insights_llm.py`. Rationale: survives restarts; authoritative; no duplicate state; ~1ms overhead is negligible vs the LLM call.
- **D-10:** Only successful misses consume rate-limit quota. `error IS NULL AND response_json IS NOT NULL`. Reasoning: pydantic-ai already retries internally on structured-output failures, so a logged failure is a "real" failure. During a provider outage, users retrying is the correct behavior; locking them out for an hour is worse than the incremental cost. Cost exposure is bounded: true broken-provider scenarios are an infra alert, not a rate-limit concern.
- **D-11:** Soft-fail uses a **tiered** lookup. Tier 1: `get_latest_log_by_hash(findings_hash, prompt_version, model)` — exact match (rare in rate-limit scenarios because if it existed, the current call would have been a cache hit, not a miss). Tier 2: `get_latest_report_for_user(user_id, prompt_version, model)` — user's most recent successful report under current prompt/model era. Tier 3: return HTTP 429 + error envelope (no fallback to serve). Tier 2 is the primary soft-fail path.
- **D-12:** Provider errors (pydantic-ai raises, structured-output validation fails after retries) DO NOT get the soft-fail treatment. They return HTTP 502 with the retry-affordance error envelope. Rationale: serving stale on provider errors confuses "is this fresh?" vs "is the LLM down?" — users need to know the report they're looking at reflects their current state or can be retried. Rate-limit soft-fail is the ONLY path that returns content the user didn't just trigger a regeneration for.
- **D-13:** No in-process lock for concurrent-cold-cache requests. Two parallel identical requests may both miss → 2 LLM calls. Acceptable for MVP volume; revisit if observed.

### Response / Error Envelope (INS-07)

- **D-14:** Success envelope (HTTP 200):
  ```python
  class EndgameInsightsResponse(BaseModel):
      report: EndgameInsightsReport
      status: Literal["fresh", "cache_hit", "stale_rate_limited"]
      stale_filters: FilterContext | None = None  # populated iff status=="stale_rate_limited" AND filters differ
  ```
- **D-15:** Error envelope (HTTP 429 / 502 / 503):
  ```python
  class InsightsErrorResponse(BaseModel):
      error: Literal["rate_limit_exceeded", "provider_error", "validation_failure", "config_error"]
      retry_after_seconds: int | None = None
  ```
  Frontend (Phase 66) owns the user-facing retry copy; backend's `error` field is diagnostic only. `retry_after_seconds` populated for 429 (computed from oldest-miss-in-window); null otherwise.
- **D-16:** HTTP status mapping:
  - 200 → `EndgameInsightsResponse` (fresh | cache_hit | stale_rate_limited)
  - 429 → `InsightsErrorResponse(error="rate_limit_exceeded")` — ONLY when tier-2 fallback also empty
  - 502 → `InsightsErrorResponse(error="provider_error")` (pydantic-ai / provider exception) or `"validation_failure"` (structured-output rejected after retries)
  - 503 → `InsightsErrorResponse(error="config_error")` (startup-validated env var invalid; defensive — should be unreachable in production)
- **D-17:** `EndgameInsightsReport` includes `model_used: str` and `prompt_version: str`. Leaked to client for debugging; lightweight, no secret material. Matches SEED-003's original schema.
- **D-18:** Overview hide = backend strips. When `INSIGHTS_HIDE_OVERVIEW=true`, the service sets `report.overview = ""` before returning. Full overview still captured in the `llm_logs.response_json` for offline analysis — log is source of truth, response is policy-gated view. Frontend treats `""` as "hide section" (Phase 66 concern; locked here so Phase 66 doesn't have to guess).
- **D-19:** `EndgameInsightsReport.sections: list[SectionInsight]` with `min_length=1, max_length=4`. LLM decides omission via system-prompt rule ("Include a section only when its underlying subsection findings have `sample_size > 0` and `sample_quality != 'thin'`"). No backend post-filtering — trust the LLM given it has per-section sample_quality in its input.
- **D-20:** `section_id` uniqueness enforced via a Pydantic `model_validator` on `EndgameInsightsReport`. Duplicate `section_id` → validation error → pydantic-ai retries. Cheap safety net.

### Pydantic-AI Agent Wiring (LLM-01, LLM-02, LLM-03)

- **D-21:** Agent accessor = `get_insights_agent()` in `app/services/insights_llm.py`, wrapped with `@functools.lru_cache`. Constructs `Agent(model=settings.PYDANTIC_AI_MODEL_INSIGHTS, result_type=EndgameInsightsReport, system_prompt=_load_system_prompt())` on first call. Called by (a) the FastAPI `lifespan` startup hook for validation, (b) `generate_insights()` at request time.
- **D-22:** Startup validation = Level 2 (Agent construction only, NO dry-run). In `main.py` lifespan, call `get_insights_agent()` and let `UserError` / `ValueError` propagate. FastAPI refuses to start → Uvicorn exits → CI/deploy marks container unhealthy. No real API call at startup — a provider outage at deploy time should not block deploy.
- **D-23:** Config: add `PYDANTIC_AI_MODEL_INSIGHTS: str = ""` to `app/core/config.py`. Empty-string treated as "unconfigured" → lifespan raises `RuntimeError`. `.env.example` gets the example value (`anthropic:claude-haiku-4-5-20251001` or whatever the shipping default is — planner/researcher picks after context7 check). Add `INSIGHTS_HIDE_OVERVIEW: bool = False` as a separate setting.
- **D-24:** Retry-on-validation-failure delegated to pydantic-ai's built-in `retries` parameter. Planner/researcher picks the count (suggested 2-3) via context7 lookup of pydantic-ai's current Agent signature. No custom retry loop.
- **D-25:** Latency captured around `await agent.run(user_prompt)` only — not around cache lookup or DB writes. `latency_ms` in `llm_logs` is "wall-clock time spent in pydantic-ai / provider" to make log-table queries useful for cost/latency analysis.
- **D-26:** Token counts come from pydantic-ai's `RunResult.usage()` (exact attribute name verified by researcher via context7). On usage-retrieval failure (shouldn't happen on happy path), log with `input_tokens=0, output_tokens=0, error="usage_missing"` — let cost path fall through Phase 64's `cost_unknown` handling.

### Prompt Assembly (LLM-03)

- **D-27:** System prompt lives in `app/services/insights_prompts/endgame_v1.md`. Loaded ONCE at startup (read file, store in module-level constant). Raises `FileNotFoundError` → startup fails if file missing. Subsequent edits require restart to take effect (acceptable; prompt changes are deploy-triggered).
- **D-28:** User-message assembly = inline in `insights_llm.py`. Helper `_assemble_user_prompt(findings: EndgameTabFindings) -> str` takes a findings object and renders it as structured text. No separate `insights_prompts/user_message_template.py` — the builder is maybe 40 lines and pairs with the system prompt conceptually. Split only if it grows past ~80 lines during implementation.
- **D-29:** User-message format = the SEED-003 markdown layout, extended with a `### Series` block per timeline subsection:
  ```
  Filters: recency=last_3mo, opponent=all, tc=[blitz,rapid], platform=chess.com, rated_only=true
  Flags: baseline_lift_mutes_score_gap, no_clock_entry_advantage

  ## Subsection: overall | Games with vs without Endgame
  Metric glossary: [inline per-metric]
  Findings:
  - score_gap (last_3mo): +4.2pp | typical | 487 games | rich
  - score_gap (all_time): +3.8pp | typical | 2140 games | rich

  ### Series (score_gap, last_3mo, weekly)
  2026-01-27: +3.1pp (n=12)
  2026-02-03: +5.8pp (n=14)
  ...

  ### Series (score_gap, all_time, monthly)
  2024-01: +2.4pp (n=45)
  2024-02: +2.9pp (n=52)
  ...
  ```
  The previous zone/trend/sample_quality columns drop the "trend" word — each finding row renders as `metric (window): value | zone | sample_size games | sample_quality`. LLM sees zone + series; derives trend itself.
- **D-30:** Info-popover text lives inline in `endgame_v1.md` as a "Metric glossary" section. Backend owns this text; frontend popovers stay canonical for UI; two evolve independently. SEED-003's Open-Q option (a) — extracting JSX into `popovers.py` — deferred; revisit if Phase 67 eyeball validation surfaces metric-meaning drift.

### Endpoint + Router Shape

- **D-31:** `POST /api/insights/endgame` accepts query params matching `/endgames/overview` (not a JSON body). Reusing the filter-as-query-string convention lets the Phase 66 frontend share query-string builders with `useEndgames.ts`. Router constructs `FilterContext(**params)` internally. `color` and `rated_only` flow into the findings pipeline (for filter-faithful findings) but NOT into the LLM prompt (INS-03).
- **D-32:** Router file = `app/routers/insights.py`, registered in `main.py` via `app.include_router(insights.router, prefix="/api")`. Route prefix `/insights`, tag `insights`. Route body is thin: auth dep + session dep + param-to-FilterContext + call to `insights_llm.generate_insights()` + return envelope.
- **D-33:** All orchestration (cache check → rate limit → Agent call → log write → envelope) lives in `insights_llm.generate_insights()`. Router has zero business logic.

### Repository Extensions (Phase 64 surface)

- **D-34:** Add two new read helpers to `app/repositories/llm_log_repository.py`:
  - `count_recent_successful_misses(session, user_id, window: datetime.timedelta) -> int` — the rate-limit query (D-09).
  - `get_latest_report_for_user(session, user_id, prompt_version, model) -> LlmLog | None` — tier-2 soft-fail fallback (D-11).
  Both take caller-supplied sessions (reads, not writes — matches Phase 64's `get_latest_log_by_hash`). No new write helpers.

### Observability (LOG-02, LOG-04)

- **D-35:** One `llm_logs` row per cache miss (success OR failure). Success → `response_json` populated, `error IS NULL`. Failure → `response_json IS NULL`, `error` populated with a short machine-readable marker (`"provider_timeout"`, `"validation_failure_after_retries"`, `"cost_unknown:<model>"` per Phase 64). Cache hits write NO row; soft-fail stale serves write NO row.
- **D-36:** Sentry captures on every non-trivial exception in `insights_llm.generate_insights()`:
  - Rate-limit exhaustion WITH stale fallback → no Sentry (expected soft-fail).
  - Rate-limit exhaustion WITHOUT stale fallback → no Sentry (user-facing feature, not a bug).
  - pydantic-ai exceptions (provider 5xx, timeout, validation-after-retries) → `sentry_sdk.set_context("insights", {"user_id": ..., "findings_hash": ..., "model": ..., "endpoint": "insights.endgame"})` + `sentry_sdk.capture_exception(exc)`.
  - Startup config errors → let lifespan exception propagate; Sentry's default handler captures.
- **D-37:** Never embed variables in exception messages (CLAUDE.md §Sentry). The `error` column on `llm_logs` uses stable machine-readable prefixes (`"provider_timeout"`, etc.) — NOT f-strings with user_id/findings_hash interpolated.

### Testing Strategy

- **D-38:** pydantic-ai `TestModel` is the default test double. Conftest fixture `fake_insights_agent(report)` monkeypatches `get_insights_agent()` to return `Agent(TestModel(custom_output_args=report.model_dump()), result_type=EndgameInsightsReport)`. Tests flow through pydantic-ai's real schema-validation machinery.
- **D-39:** `FunctionModel` for the 2-3 tests asserting specific token counts (cost-computation wiring).
- **D-40:** Test env var setup = `os.environ["PYDANTIC_AI_MODEL_INSIGHTS"] = "test"` in `tests/conftest.py` at module top (alongside existing `SENTRY_DSN` / `SECRET_KEY`). Pydantic-ai's `test` provider prefix passes startup validation; individual tests override with TestModel/FunctionModel.
- **D-41:** New test files:
  - `tests/services/test_insights_llm.py` — Agent wiring, prompt assembly, startup validation, soft-fail tiering, rate-limit boundary.
  - `tests/routers/test_insights_router.py` — endpoint happy path, cache hit, rate limit, envelopes, error shapes.
  - `tests/repositories/test_llm_log_repository_reads.py` — `count_recent_successful_misses`, `get_latest_report_for_user`.
  - `tests/services/test_insights_service_series.py` — new resampling logic (weekly→monthly, sparse-combo filter, ELO gap-only) added to Phase 63's insights_service.
- **D-42:** No real-provider calls in Phase 65 tests. LLM-output correctness (the 5 VAL-01 regression assertions) = Phase 67 scope.
- **D-43:** No VCR / recorded cassettes. Fragile; not worth MVP maintenance cost.

### Claude's Discretion

- Exact pydantic-ai API surface (signature of `Agent(...)`, how to access `usage`, retry parameter name, TestModel constructor) — researcher validates via context7 before the planner locks. pydantic-ai moves fast.
- Sparse-combo threshold for Endgame ELO timeline — D-04 says "≥10 games" as a floor. Planner may tune after reading the underlying `EndgameEloTimelineCombo` schema and sample distributions.
- Monthly-bucketing key format (`YYYY-MM` string vs ISO first-of-month date) — planner picks; just needs to match the `TimePoint.bucket_start` string field.
- `INSIGHTS_MISSES_PER_HOUR` constant location — `insights_llm.py` module-level, OR a dedicated `app/services/insights_rate_limits.py` if the planner thinks it'll grow. Start in `insights_llm.py`.
- Rate-limit retry-after calculation: oldest-miss-in-window timestamp + 1 hour − now, in seconds. Planner confirms timezone handling (UTC throughout, matches DB).
- Whether to emit `last_3mo` window for `type_win_rate_timeline` at all — D-05 flags this as a planner call; if 5-way split × 13 weeks is always empty/thin, planner may drop the window entirely for that subsection and document.
- Exact default model value for `.env.example` — Haiku 4.5 vs Gemini 2.5/3 Flash is a researcher-driven pick via context7 (check current pydantic-ai support matrix + genai-prices coverage). User mentioned both as candidates; defer the final pick.
- Whether `_load_system_prompt()` reads the file once at module import or in `get_insights_agent()` first call — both work; "at import" is simpler, "in lru_cache" matches the Agent lazy-init pattern. Planner picks.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase Source Documents
- `.planning/seeds/SEED-003-llm-based-insights.md` — the canonical architecture doc. §"Prompt structure", §"Failure modes and handling", §"Observability and logging", §"Response schema", §"Naming collisions to watch", §"Antipatterns to catch in review" are load-bearing. §"What the findings pipeline computes" is SUPERSEDED by Phase 65 D-01 for LLM-prompt purposes (trend label no longer fed; raw series fed instead).
- `.planning/seeds/SEED-004-trend-texture-for-llm-insights.md` — trigger seed for Phase 65 discuss. **Superseded by D-01** — raw-series approach moots its schema additions. Will be marked `closed_superseded_by_phase_65` at phase completion.
- `.planning/REQUIREMENTS.md` §LLM-01..LLM-03, §INS-04..INS-07, §LOG-02, §LOG-04 — locked requirements for this phase.
- `.planning/PROJECT.md` §"Current Milestone: v1.11 LLM-first Endgame Insights" — milestone goal.
- `.planning/phases/63-findings-pipeline-zone-wiring/63-CONTEXT.md` — Phase 63 decisions. D-13 (`is_headline_eligible`), D-14 (Endgame ELO combo fanout), D-15 (trend gate) — Phase 65 stops feeding D-13/D-15 outputs to the LLM but keeps the schema fields for now (D-07). D-14's combo dimension is the basis for D-04's gap-only + sparse-combo filter.
- `.planning/phases/64-llm-logs-table-async-repo/64-CONTEXT.md` — D-02 (repo-owns-session), D-03 (genai-prices in repo), D-05 (cache-hit logging deferred), D-07 (five indexes) — Phase 65 reads-and-writes through this repo and relies on its index coverage for D-09.

### Existing Backend (read before implementing)
- `app/services/insights_service.py` — compute_findings already in prod. Phase 65 extends with resampling logic per D-03/D-04/D-05 and the `series` field population per D-02.
- `app/services/endgame_zones.py` — constants + zone registry. Review to confirm nothing in Phase 65 needs new additions (series resampling thresholds may land here if the planner decides).
- `app/schemas/insights.py` — Phase 63 schemas. Phase 65 extends with `EndgameInsightsReport`, `SectionInsight`, `EndgameInsightsResponse`, `InsightsErrorResponse`, `TimePoint`, and the new optional `SubsectionFinding.series` field.
- `app/schemas/llm_log.py` — Phase 64's `LlmLogCreate` + `LlmLogEndpoint` Literal. `LlmLogEndpoint` already includes `"insights.endgame"` (Phase 64 D-04). No extension needed.
- `app/repositories/llm_log_repository.py` — Phase 64's `create_llm_log` + `get_latest_log_by_hash`. Phase 65 adds two read helpers (D-34).
- `app/routers/endgames.py:27-61` — template for the router file-layout + dependency pattern. Phase 65's router mirrors the auth/session dependency structure.
- `app/main.py` — lifespan hook pattern (`cleanup_orphaned_jobs()` on startup). Phase 65 adds `get_insights_agent()` validation call.
- `app/core/config.py` — add `PYDANTIC_AI_MODEL_INSIGHTS` + `INSIGHTS_HIDE_OVERVIEW` settings here.
- `app/core/ip_rate_limiter.py` — REFERENCE ONLY (in-memory pattern). Phase 65 does NOT use this pattern — DB-backed rate limit per D-09.
- `tests/conftest.py` — env-var-before-import pattern (lines 1-13). Phase 65 extends with `PYDANTIC_AI_MODEL_INSIGHTS="test"`.

### Project Conventions
- `CLAUDE.md` §"Coding Guidelines" — Literal types, no magic numbers, ty compliance (`uv run ty check app/ tests/` must pass zero errors). Every `Literal[...]` field in envelopes.
- `CLAUDE.md` §"Critical Constraints" — `AsyncSession` not safe for `asyncio.gather`. `insights_llm.generate_insights` makes sequential awaits only.
- `CLAUDE.md` §"Error Handling & Sentry" — `sentry_sdk.capture_exception` + `set_context` for structured data; never embed variables in exception messages. Phase 65 D-36 / D-37 apply this.
- `CLAUDE.md` §"Router Convention" — `APIRouter(prefix="/insights", tags=["insights"])` with relative paths in decorators.
- `CLAUDE.md` §"Version Control" — Phase 65 ships on a feature branch + PR. Don't commit `.env`.

### External Libraries (researcher uses context7 before planner locks)
- [`pydantic-ai`](https://ai.pydantic.dev/) — primary dependency. Researcher queries context7 for current `Agent` constructor signature, `TestModel` / `FunctionModel` API, `RunResult.usage()` attribute, retry parameter, error class names (e.g. `UserError`). Add to `pyproject.toml` as part of Phase 65.
- `genai-prices` — already pinned in Phase 64. No Phase 65 changes, but the `model` string format `<provider>:<model>` is what `calc_price` expects (Phase 64 repo handles the split internally per its D-03 implementation).

### Related Reports / Data
- `reports/benchmarks-2026-04-18.md` — population baselines (background context only per Phase 63 FIND-02; not a Phase 65 concern except that the prompt should NOT re-derive them — zones already come from findings).

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **`insights_service.compute_findings`** (Phase 63, `app/services/insights_service.py:91`) — Phase 65's single source for findings. Extended here to populate the new `series` field and do the window-specific resampling (D-02/D-03/D-04/D-05).
- **`llm_log_repository.create_llm_log`** (Phase 64, `app/repositories/llm_log_repository.py:38`) — write path. Already owns genai-prices cost computation + session isolation. Phase 65 just constructs a `LlmLogCreate` and calls it.
- **`llm_log_repository.get_latest_log_by_hash`** (Phase 64, `app/repositories/llm_log_repository.py:118`) — tier-1 soft-fail lookup. Signature already matches Phase 65 needs.
- **FastAPI lifespan hook pattern** (`app/main.py:42-45`) — `cleanup_orphaned_jobs()` is the template for adding `await _validate_insights_agent_at_startup()`.
- **`tests/conftest.py`** env-var-before-import pattern — extend with `PYDANTIC_AI_MODEL_INSIGHTS` (D-40).
- **`tests/seed_fixtures.py` + `seeded_user`** — reuse for router integration tests.

### Established Patterns
- **Module-level async service functions** (see `endgame_service.get_endgame_overview`). Phase 65's `insights_llm.generate_insights` follows the same shape.
- **Router: thin HTTP layer, no business logic** (CLAUDE.md §"Backend Layout"). `insights.py` router body = deps + FilterContext construction + one service call.
- **Pydantic v2 + `Literal` for enum fields** throughout. Every status/error code in envelopes.
- **No magic numbers** — `INSIGHTS_MISSES_PER_HOUR = 3` is the only new threshold; lives in `insights_llm.py` or `insights_rate_limits.py`.
- **Stdlib-only for resampling** — `statistics.mean` over grouped-by-month weeks. No pandas.

### Integration Points
- **Phase 66 (frontend)** consumes `EndgameInsightsResponse`. Lock the envelope shape carefully — Phase 66's TanStack Query hook keys off `status` discriminator. `stale_filters` being populated only on `status=="stale_rate_limited"` is a contract Phase 66 relies on for banner display.
- **Phase 67 (validation)** queries `llm_logs` for the regression test and reads the response envelope for admin-impersonation eyeball validation. `model_used` + `prompt_version` in `EndgameInsightsReport` (D-17) make screenshot-based validation traceable.
- **`main.py` lifespan hook** — Phase 65 adds one line. Planner coordinates with the existing `cleanup_orphaned_jobs()` call (order: validate Agent first, then orphan cleanup, since Agent validation failure is a deploy-blocker but orphan cleanup is best-effort).
- **Test startup order** — `conftest.py` MUST set `PYDANTIC_AI_MODEL_INSIGHTS` before any `from app.main import ...` or `from app.services.insights_llm import ...`. Matches existing `SENTRY_DSN` pattern.

</code_context>

<specifics>
## Specific Ideas

- **`EndgameInsightsReport` shape (illustrative — planner finalizes):**
  ```python
  class SectionInsight(BaseModel):
      section_id: Literal["overall", "metrics_elo", "time_pressure", "type_breakdown"]
      headline: str = Field(..., max_length=120)  # ~12 words × 10 chars
      bullets: list[str] = Field(default_factory=list, max_length=2)  # ≤2 bullets

  class EndgameInsightsReport(BaseModel):
      overview: str  # ≤150 words enforced via prompt, ""=hidden by INSIGHTS_HIDE_OVERVIEW
      sections: list[SectionInsight] = Field(..., min_length=1, max_length=4)
      model_used: str
      prompt_version: str

      @model_validator(mode="after")
      def unique_section_ids(self) -> Self:
          ids = [s.section_id for s in self.sections]
          if len(ids) != len(set(ids)):
              raise ValueError("duplicate section_id")
          return self
  ```
- **`TimePoint` (new schema, landing in `app/schemas/insights.py` alongside `SubsectionFinding`):**
  ```python
  class TimePoint(BaseModel):
      bucket_start: str   # ISO YYYY-MM-DD (first-of-week for last_3mo, first-of-month for all_time)
      value: float
      n: int              # sample size for this bucket
  ```
- **`SubsectionFinding.series` addition:**
  ```python
  series: list[TimePoint] | None = None  # only populated for the 4 timeline subsections
  ```
  Defaults to None — non-timeline findings stay unchanged. `findings_hash` covers this naturally since it already JSON-serialises the findings list.
- **Generate-endpoint flow sketch:**
  ```python
  # app/services/insights_llm.py
  async def generate_insights(filter_context, user_id, session) -> EndgameInsightsResponse:
      findings = await compute_findings(filter_context, session, user_id)
      # Tier 1: exact cache hit
      cached = await get_latest_log_by_hash(session, findings.findings_hash, _PROMPT_VERSION, _MODEL)
      if cached:
          return EndgameInsightsResponse(
              report=EndgameInsightsReport.model_validate(cached.response_json),
              status="cache_hit",
          )
      # Rate limit check
      misses = await count_recent_successful_misses(session, user_id, datetime.timedelta(hours=1))
      if misses >= INSIGHTS_MISSES_PER_HOUR:
          fallback = await get_latest_report_for_user(session, user_id, _PROMPT_VERSION, _MODEL)
          if fallback:
              stale = _maybe_stale_filters(fallback, filter_context)
              return EndgameInsightsResponse(
                  report=EndgameInsightsReport.model_validate(fallback.response_json),
                  status="stale_rate_limited",
                  stale_filters=stale,
              )
          raise InsightsRateLimitExceeded(retry_after_seconds=_compute_retry_after(...))
      # Fresh call
      user_prompt = _assemble_user_prompt(findings)
      report, usage, latency_ms, err = await _run_agent(user_prompt)
      await create_llm_log(LlmLogCreate(
          user_id=user_id, endpoint="insights.endgame", model=_MODEL,
          prompt_version=_PROMPT_VERSION, findings_hash=findings.findings_hash,
          filter_context=filter_context.model_dump(), flags=list(findings.flags),
          system_prompt=_SYSTEM_PROMPT, user_prompt=user_prompt,
          response_json=report.model_dump() if report else None,
          input_tokens=usage.input_tokens, output_tokens=usage.output_tokens,
          latency_ms=latency_ms, cache_hit=False, error=err,
      ))
      if err or report is None:
          raise InsightsProviderError(err)
      report = _maybe_strip_overview(report)
      return EndgameInsightsResponse(report=report, status="fresh")
  ```
  Custom exceptions (`InsightsRateLimitExceeded`, `InsightsProviderError`) caught by the router and mapped to envelope + HTTP status per D-16.

- **`.env.example` additions (planner picks default model after context7 check):**
  ```
  # LLM insights (Phase 65+)
  # Supports any pydantic-ai model string; requires matching provider API key.
  PYDANTIC_AI_MODEL_INSIGHTS=anthropic:claude-haiku-4-5-20251001
  ANTHROPIC_API_KEY=sk-ant-...
  # Hides the overview paragraph in the API response; full overview still logged to llm_logs.
  INSIGHTS_HIDE_OVERVIEW=false
  ```

- **Resampling rule for `all_time` timelines (pseudocode):**
  ```python
  def _resample_monthly(weekly_points: list[tuple[date, float, int]]) -> list[TimePoint]:
      buckets: dict[str, list[tuple[float, int]]] = defaultdict(list)
      for d, v, n in weekly_points:
          buckets[d.strftime("%Y-%m")].append((v, n))
      return [
          TimePoint(bucket_start=f"{ym}-01", value=statistics.mean(v for v, _ in ws), n=sum(n for _, n in ws))
          for ym, ws in sorted(buckets.items())
      ]
  ```
  Weighted mean (by `n`) is a refinement the planner may prefer — call out during planning.

- **Prompt version string: `"endgame_v1"`** initial. Bump to `"endgame_v2"` on any meaningful prompt edit → naturally invalidates cache per D-08.

</specifics>

<deferred>
## Deferred Ideas

- **Cache-hit row logging** — Phase 64's `cache_hit` column stays unused. Re-evaluate when/if telemetry on hit-rate becomes valuable (would double the log volume; not worth it in MVP).
- **In-memory concurrency lock** for cold-cache parallel requests (D-13). Revisit if observed in prod.
- **Ripping out `Trend` / `is_headline_eligible` / `weekly_points_in_window` fields from `SubsectionFinding`** (D-07). Phase 65 stops feeding them to the LLM but leaves them on the schema. Clean up in a later `/gsd-quick` or Phase 67 cleanup if the planner prefers to keep Phase 65 contained.
- **Popover text extraction to `insights_prompts/popovers.py`** (SEED-003 Open Q option (a), D-30). Revisit if VAL-01 regression or admin-impersonation eyeball validation surfaces metric-meaning drift between LLM narration and UI popovers.
- **`cache_hit=true` / stale-served row in `llm_logs`** for accurate cost-telemetry including rate-limited users — deferred per Phase 64 D-05.
- **Real-provider integration tests** (VCR cassettes, live-marker tests) — D-43. Phase 67 owns real-LLM validation.
- **Admin raw-data mode** (raw weekly series in an admin-only variant of the prompt) — v1.12 / SEED-001 scope. D-01 already feeds raw series to all users, so the "admin gets more data" distinction from SEED-001 becomes smaller; revisit then.
- **Per-section streaming responses** (pydantic-ai supports streaming) — MVP returns a single response. Streaming is a UX polish for Phase 66+ if the one-shot latency feels bad.
- **Cross-AI model A/B at the endpoint level** — explicitly out of scope per REQUIREMENTS "Out of Scope" table. Offline comparison via env-var swap + log queries is the only supported mechanism.
- **Tuning the sparse-combo threshold for Endgame ELO (D-04)** — initial floor is ≥10 games; planner picks final value; tune based on log-table analysis post-ship.
- **Weighted (by `n`) vs unweighted monthly mean for resampling** — Claude's Discretion; planner picks. Weighted is more honest but adds one more line.

</deferred>

---

*Phase: 65-llm-endpoint-with-pydantic-ai-agent*
*Context gathered: 2026-04-21*
