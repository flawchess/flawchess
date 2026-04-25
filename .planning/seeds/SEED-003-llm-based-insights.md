---
id: SEED-003
status: closed_implemented_in_v1_11
planted: 2026-04-20
closed: 2026-04-25
planted_during: v1.10 Advanced Analytics (executing, post-Phase 57.1)
trigger_when: milestone v1.11 opens
scope: milestone
supersedes_for_v1_11: SEED-001 (SEED-001 becomes v1.12+ scope)
---

# SEED-003: LLM-first Insights MVP for the Endgame tab

> **Closed 2026-04-25 — implemented as milestone v1.11 (LLM-first Endgame Insights), shipped 2026-04-24.** The MVP path described here (LLM narration via pydantic-ai over a stripped-down findings pipeline, two-window computation, deferred archetypes/era comparison/admin raw-data mode) was executed across Phases 63–67. SEED-001's deferred deterministic features remain candidates for v1.12+. SEED-002 (benchmark DB) and SEED-004 (closed, superseded by Phase 65) are the related seeds. Kept on disk for design-rationale reference; do not re-surface.

## Why This Matters

SEED-001 designs a comprehensive deterministic insights pipeline (role taxonomy, archetype synthesis, era comparison, stability patterns, lookback-behavior tagging, phrase library) with an optional LLM narration layer on top. The design is internally coherent, but it front-loads a large schema before any validation and treats the LLM as a v2 add-on. Two problems with that path:

1. **The "templates only, no AI" MVP is the most engineering-heavy path.** A phrase library plus deterministic archetype classification plus role taxonomy plus era heuristics is weeks of work before a single user reads an insight. Meanwhile a cost-efficient LLM (e.g. a small tier of Claude, GPT, or Gemini, selected via env var, see below) comes in well under $0.01 per report and is cheaper than the phrase library is to build, and fluent enough that the templates' fluency benefits disappear.
2. **N=1 validation for an 8-class archetype system is risky.** The ground-truth fixture in SEED-001 is one real user. Labels like `technician`, `underperformer`, `clock_hoarder` are strong claims; getting them wrong for other users erodes trust on a dashboard that's supposed to clarify, not confuse.

SEED-003 takes a different MVP path: ship LLM narration via [pydantic-ai](https://ai.pydantic.dev/) from day one over a stripped-down findings pipeline. The pipeline still owns numbers, zone assignment, trend gating, and a small set of cross-section flags the LLM must not get wrong. Everything the LLM can plausibly do (cross-section reasoning, metric-meaning framing, confidence hedging) moves to the prompt. The underlying model is selected via env var (`PYDANTIC_AI_MODEL_INSIGHTS`) and swappable at will across providers. Ship it to yourself and 3–5 beta users, read their reactions, then let v1.12 decide which of SEED-001's deferred parts (archetypes, role taxonomy, era comparison, stability matrix, admin raw-data mode) are actually worth building.

**This is an MVP seed, not a replacement for SEED-001.** SEED-001's material-adjusted precedence rule, clock-diff disambiguation, and lookback-behavior analysis remain the canonical reference for *what insights should correctly say*. SEED-003 is *how to ship a first version* that makes those rules load-bearing without building the full schema upfront.

## When to Surface

**Trigger:** Milestone v1.11 opens

This seed should be presented during `/gsd-new-milestone` when:
- The user starts planning v1.11
- OR the milestone scope mentions "insights", "AI summary", "natural language findings"
- OR the roadmap references consolidating / explaining existing analytics

When surfaced, present SEED-001 and SEED-003 together. SEED-003 is the v1.11 recommendation; SEED-001 becomes the v1.12+ scope for the deterministic features SEED-003 defers.

Do NOT surface during v1.10 — current milestone is implementing the underlying analytics (Endgame ELO via Phases 56/57, complete as of 2026-04-19) that Insights will consume.

## Relationship to SEED-001

| Area | SEED-001 (v1.12+) | SEED-003 (v1.11 MVP) |
|---|---|---|
| Renderer | Template phrase library, LLM optional | LLM via pydantic-ai (env-configurable), no templates |
| Archetype classification | Deterministic 8-class system | Deferred. LLM describes, does not label. |
| Role taxonomy (effect/mechanism/confound) | Explicit schema | Implicit in LLM narration |
| Era comparison / regime detection | 50/50 heuristic | Deferred to v1.12 |
| Stability pattern across windows | `stable / evolving / recent_shift / insufficient_data` | Deferred. Two windows only. |
| Multi-window computation | 3 windows (`all_time`, `last_1y`, `last_3mo`) | 2 windows (`all_time`, `last_3mo`) |
| Lookback-behavior tagging | First-class schema field | Precomputed at compute time, not exposed in MVP schema |
| Cross-section reasoning | Role-typed findings graph | Overview paragraph from LLM |
| Admin raw-data mode | In scope | Deferred to v1.12 |
| Material-adjusted precedence | Rule + phrase library + caveat finding | Boolean flag → prompt rule |
| Clock-diff disambiguation | Paired-findings check at compute time | Boolean flag → prompt rule |

SEED-001's design decisions for the deferred parts are preserved, not rejected. When v1.12 opens and we know what users actually want, SEED-001 is the reference for how to build it.

## Scope Estimate

**Full milestone** — smaller than SEED-001 but not trivial. Expected decomposition:

1. Backend findings computation service (`insights_service.py`) + Pydantic schemas (`app/schemas/insights.py`) — reads existing section service outputs, computes zone / trend / sample-quality / flags per subsection × window
2. Zone thresholds wired from `reports/benchmarks-2026-04-18.md` recommendations (no longer a blocker — bands are in hand; see "Zone bands" section below). Refresh once mid-milestone if the user base grows materially before ship.
3. LLM endpoint (`/api/insights/endgame`) backed by a pydantic-ai Agent with structured output (`result_type=EndgameInsightsReport`). Model selected via env var `PYDANTIC_AI_MODEL_INSIGHTS` (swappable across providers at any time). Findings-hash cache, 3 misses/hr/user rate limit, soft-fail-to-cache on limit.
4. Postgres log table (`insights_llm_logs`) + Alembic migration + async repository — one row per LLM call capturing prompt, response, token counts, cost (via `genai-prices`), latency, cache-hit flag, and errors. Used for prompt-engineering iteration, cost monitoring, and regression analysis.
5. Frontend Insights component — renders overview paragraph + 4 Section blocks inline on the Endgame tab (or at the top as the first visual block), behind a beta flag
6. Ground-truth regression test — canonical user profile from SEED-001's worked example encoded as a synthetic fixture; snapshot-test the LLM output against expected claims (material-adjusted precedence triggered, no clock-entry advantage noted, cross-combo consistency mentioned)
7. Beta toggle + usage telemetry — capture which users enabled, how often they regenerated, any errors

Target: 2–3 weeks of focused build, not a full milestone's worth. If v1.11 has additional scope (bug fixes, Openings tab extensions, benchmark-DB groundwork from SEED-002), this fits alongside.

**Recommended sequence:**

- **Phase 0 — Prompt-fluency spike (1 day, before any pipeline work).** Hand-craft a findings JSON for one impersonated user, run it through the candidate model(s) with a draft system prompt, eyeball 3–5 outputs. Validates the central bet ("a small LLM is fluent enough") before building the findings pipeline. If fluency fails, the milestone shape changes; better to find out before week 2.
- Items 1 (findings service) and 2 (zone-band wiring) run in parallel. Item 2 is now a wiring task, not a calibration task — bands come from `reports/benchmarks-2026-04-18.md` and the gauge-band update phase (see "Zone bands" below). Both must complete before item 3 (LLM endpoint) produces meaningful output.
- Item 4 (log table) should land with item 3, not after. The log IS the prompt-engineering harness (see Notes) — iterating on prompts without the log means comparing output quality by memory, which wastes iterations.
- Item 6 (regression test) follows item 3 directly; writing the fixture before the first real LLM call prevents shipping a prompt tuned to outputs the test never codified. **Use admin user impersonation to extend regression coverage beyond the canonical N=1 fixture** — sample 5–10 real users across different filter combos and eyeball-validate before flipping the beta flag.
- Item 5 (frontend) and item 7 (beta toggle) ship last. Keep the frontend on a beta flag that defaults off — you want the first live sessions to be you and 3–5 invited beta users, not the entire user base.

## Design Decisions

### Architecture

- **Single LLM call per tab request**, not per Section. Cross-section reasoning is the whole point; splitting into 4 calls forces a 5th synthesis call. One prompt to iterate, one cache key (`findings_hash + prompt_version + model_id`), one failure mode.
- **Structured output via pydantic-ai.** The endpoint wraps a `pydantic_ai.Agent` configured with `result_type=EndgameInsightsReport`. pydantic-ai handles the provider-specific structured-output mechanism (JSON schema / tool-call / response_format) so the application code stays provider-agnostic. Any pydantic-ai-supported model that reliably returns structured output for this payload size is acceptable.
- **Model selected at runtime via env var `PYDANTIC_AI_MODEL_INSIGHTS`.** Accepts any pydantic-ai model string (`anthropic:claude-haiku-4-5-20251001`, `openai:gpt-4o-mini`, `google-gla:gemini-2.5-flash`, etc.). Changing the env var and restarting the backend swaps the model without code changes. Default pinned in `.env.example`; production choice tracked in deployment notes, not committed.
- **Whole-tab endpoint**: `POST /api/insights/endgame` with filter context in the body. Insights are not auto-generated — user clicks "Generate insights" button.
- **Cache on `findings_hash`, not filter hash.** Many filter combinations round to identical findings; caching on the hash deduplicates across equivalent filter states. Cache key is `(findings_hash, prompt_version, model_id)` so changing the env-var model or bumping the prompt version naturally invalidates cached reports.
- **Rate limit applies to cache misses only** (3/hr/user). Filter-flipping shouldn't burn quota on duplicates. Soft-fail on limit: return last cached report rather than hard block.

### Data source and findings-hash composition

- **insights_service consumes the existing composite endpoint**, not the repositories. `endgame_service.get_overview(filter_context)` (already serving `GET /api/endgames/overview`) returns the 7 data shapes the subsection components render. insights_service transforms this composite into `list[SubsectionFinding]`. Reusing the service layer guarantees filter semantics (time control bucketing, opponent strength, color, recency) stay consistent with the page — re-implementing filter logic is a known-bad path.
- **`findings_hash` composition**: SHA256 of the canonical-JSON serialization of `EndgameTabFindings` with `as_of` EXCLUDED and keys sorted. Excluding `as_of` means identical findings on different days cache-hit; otherwise cache churns daily for no benefit. Confirm the JSON serializer produces identical output across Python sessions (Pydantic's `model_dump_json()` with sorted-keys is the reference).
- **Cache storage**: Postgres is fine for MVP (same row of `insights_llm_logs` indexed by `findings_hash` doubles as cache), no Redis needed. The "last cached report" for soft-fail-on-limit is `SELECT response_json FROM insights_llm_logs WHERE findings_hash=? AND prompt_version=? AND model=? AND error IS NULL ORDER BY created_at DESC LIMIT 1`.

### Naming collisions to watch

Three "overall" / "overview" concepts live in this feature. All three appear in the same codebase areas; mixing them up is the most likely first-day bug.

| Identifier | What it is | Where |
|---|---|---|
| `/api/endgames/overview` | Existing composite endpoint returning all endgame data shapes | `app/routers/endgames.py`, `endgame_service.get_overview()` |
| `EndgameInsightsReport.overview` | The LLM-generated cross-section paragraph (1–2 paragraphs, nullable) | `app/schemas/insights.py` |
| `section_id="overall"` | The first Section (Endgame Overall Performance), an enum value on `SectionInsight` | `app/schemas/insights.py` |
| `subsection_id="overall"` | The first Subsection (Games with vs without Endgame), an enum value on `SubsectionFinding` | `app/schemas/insights.py` |

**Disambiguation discipline:** in code, always qualify (`report.overview`, `SectionInsight.section_id == "overall"`, `endgame_service.get_overview(...)`). In prose (doc strings, log messages, comments), use the full name ("overview paragraph", "overall section", "overall subsection", "overview endpoint"). Do not rename `overall` to something unique — it matches the UI heading and the seed's discussion vocabulary, and renaming leaks into user-facing copy. Discipline > renames.

### Failure modes and handling

Four failure modes the pipeline must handle explicitly. All four should write a log row with `error` populated so they're visible in the log-table harness.

1. **pydantic-ai structured-output validation fails.** The LLM returned something that doesn't coerce to `EndgameInsightsReport`. pydantic-ai retries up to `retries=N` automatically; after exhaustion, surface as HTTP 502 and show the user a retry affordance. Do NOT fall back to a partial report — the schema is the contract.
2. **Provider API error** (rate limit, 5xx, timeout, invalid auth). Log + HTTP 502 + retry affordance. Do NOT auto-retry beyond pydantic-ai's built-in retries — the user's click triggered this; their click can trigger the retry.
3. **`PYDANTIC_AI_MODEL_INSIGHTS` not set or invalid at startup.** Fail loudly on application startup, not on first request. Startup check: read the env var, attempt to construct the `pydantic_ai.Agent`, call a dry-run method or validate the model string. If it fails, the backend should refuse to start so deployment catches it before users do.
4. **`genai-prices` doesn't know the model.** Fall back to `cost_usd = 0` and set `error` to `"cost_unknown:<model>"` so the log row still writes. The insight delivery path does not depend on cost accounting; cost monitoring tolerates a few unknown rows.

Frontend handles all four identically: show "Something went wrong generating insights. Try again in a moment." with a retry button. The per-section insights and overview remain blank; do not render placeholder text that could be mistaken for real content.

### Observability and logging

Every LLM call (cache miss) writes one row to a dedicated Postgres table. This is the primary tool for prompt iteration, cost monitoring, and regression analysis — treat the log as a first-class feature, not operational noise.

```python
# app/models/insights_llm_log.py (SQLAlchemy)
class InsightsLlmLog(Base):
    __tablename__ = "insights_llm_logs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True,
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    endpoint: Mapped[str] = mapped_column(String, nullable=False)
    # Model identifier returned by pydantic-ai (provider:model form)
    model: Mapped[str] = mapped_column(String, nullable=False)
    prompt_version: Mapped[str] = mapped_column(String, nullable=False)
    findings_hash: Mapped[str] = mapped_column(String, nullable=False, index=True)
    filter_context: Mapped[dict] = mapped_column(JSONB, nullable=False)
    flags: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    system_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    user_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    response_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    input_tokens: Mapped[int] = mapped_column(Integer, nullable=False)
    output_tokens: Mapped[int] = mapped_column(Integer, nullable=False)
    cost_usd: Mapped[Decimal] = mapped_column(Numeric(10, 6), nullable=False)
    latency_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    cache_hit: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
```

**Fields explained:**

- `model` — the pydantic-ai model identifier at the time of the call (e.g. `anthropic:claude-haiku-4-5-20251001`). Captures exactly which model produced the output so comparisons across env-var swaps remain valid.
- `prompt_version` — the versioned system prompt (e.g. `endgame_v1`). Bumping the version forces cache invalidation AND tags log rows so prompt iterations can be A/B analyzed offline.
- `findings_hash` — lets us group duplicate requests, see which finding patterns are common, and identify findings shapes that produce bad output.
- `filter_context` / `flags` — full context needed to reproduce the prompt during offline debugging without touching prod.
- `system_prompt` / `user_prompt` / `response_json` — full text for prompt-engineering iteration. Not PII-sensitive (chess stats only), so no redaction needed. `response_json` is null on error.
- `input_tokens` / `output_tokens` — pulled from pydantic-ai's `Usage` object on the result.
- `cost_usd` — computed via [`genai-prices`](https://github.com/pydantic/genai-prices) from `(model, input_tokens, output_tokens)`. Stored at write time rather than computed at query time so historical cost is preserved even when provider pricing changes.
- `latency_ms` — wall-clock time from request to response return. Includes pydantic-ai overhead and provider latency.
- `cache_hit` — set `true` for rows written when serving from cache (if we decide to log cache hits at all; see Open Questions). Default behavior: log cache misses only, leave this field unused in MVP.
- `error` — populated when the pydantic-ai call fails or the structured-output validation rejects the response. On error, `response_json` stays null and `input_tokens`/`output_tokens`/`cost_usd` capture whatever usage was consumed before failure.

**Indexes for the common query patterns:** `(created_at)` for time-range scans, `(user_id, created_at DESC)` for per-user history, `(findings_hash)` for dedup analysis, `(model, created_at DESC)` for model A/B comparisons.

**Retention:** keep indefinitely in MVP (low volume, high iteration value). Revisit when the table crosses ~1M rows or the cost-monitoring story matures into a proper dashboard.

**Privacy:** no PII is included (no game PGNs, no opponent usernames). The prompts contain only aggregated statistics about the calling user's own play, tied to `user_id`. GDPR deletion: row cascades via the `user_id` FK on user deletion.

### Zone bands (sourced from `reports/benchmarks-2026-04-18.md`)

Zone calibration is no longer an open question — the 2026-04-18 benchmark snapshot (n=37 active users, ≥30 endgame games each) produced concrete recommendations per metric. The insights pipeline wires these directly; the gauge components on the Endgame tab should be updated to match in the same milestone so the narrative and the visual zone agree.

Recommended bands (5-zone mapping for insights — `very_weak / weak / typical / strong / very_strong`):

| Metric | Source constant | Recommendation | Notes |
|---|---|---|---|
| Score Gap (endgame vs non-endgame) | `SCORE_DIFF_NEUTRAL_*` | `typical` band ±8pp (was ±10pp) | Pooled p25–p75 of users; tighten so half of meaningfully-skewed users stop reading "neutral". |
| Conversion (Win % at +1 material) | `FIXED_GAUGE_ZONES.conversion` | `[0.65, 0.75]` typical (keep) | Pooled median 0.72 sits dead-center. |
| Parity (Score % at ±0 material) | `FIXED_GAUGE_ZONES.parity` | `[0.45, 0.55]` typical (keep) | Pooled median 0.52. High-ELO drift (0.54–0.58) reads as "above neutral", which is correct. |
| Recovery (Save % at -1 material) | `FIXED_GAUGE_ZONES.recovery` | `[0.30, 0.40]` typical (decision needed) | Benchmarks suggest re-centering to `[0.25, 0.35]` so the pooled median 0.32 sits in the middle, OR keeping `[0.30, 0.40]` as the design target. **Lock this in `/gsd-discuss-phase`** — insights and gauges must agree. |
| Endgame Skill (composite) | `ENDGAME_SKILL_ZONES` | Widen upper bound: `[0–0.45 / 0.45–0.59 / 0.59–1.0]` | Pooled p25–p75 = `[0.47, 0.59]`. Today's `0.55` upper bound flags ~30% of users as "success" while they're still inside the typical cohort. |
| Clock diff at endgame entry (% base time) | `NEUTRAL_PCT_THRESHOLD` | ±7% (was ±10%) | Pooled p25–p75 across blitz/rapid; the current ±10% swallows almost the whole population. |
| Net timeout rate | `NEUTRAL_TIMEOUT_THRESHOLD` | ±5pp (keep) | Bullet skews positive (signal expected); blitz/rapid fit comfortably inside ±5pp. |
| Endgame ELO vs Actual ELO gap | (no UI constant yet) | `\|gap\| > 100 Elo` flags as "notable" | Pooled p90; ~10% of users at any snapshot. New flag candidate, see "Cross-section flags" below. |

**Five-zone mapping rule.** The benchmark report gives 3-zone bands (danger / neutral / success). For the insights pipeline's 5-zone schema, split each outer zone in half at p10/p90 of the pooled distribution: `very_weak < p10 < weak < typical_lower < typical < typical_upper < strong < p90 < very_strong`. Use the per-metric percentile tables in the benchmark report (Section 1 has full p05/p10/p25/p50/p75/p90/p95 for Score Diff; Section 5 has the same for Endgame Skill; Sections 2/3 give the cell-level distributions for Conversion/Parity/Recovery/Clock).

**Sample-size caveat.** n=37 active users is a small base for tail estimates (p05/p95 are noisy). The bands are good enough for v1.11 MVP; SEED-002 (v1.12+) replaces them with rating-stratified population baselines from a Lichess benchmark DB. Treat these bands as v1 and expect them to move once SEED-002 lands.

**New cross-section flag candidate.** The benchmark report surfaces an Endgame ELO gap signal that wasn't in the original three flags. Consider adding:

- `notable_endgame_elo_divergence`: set when `|endgame_elo − actual_elo| > 100` for the active filter combo. Prompt rule: lead with the divergence direction ("your endgame play pulls your rating up" / "your endgames are dragging your rating down") only when the flag is set; never speculate without it. Roughly 10% of users qualify, matching the "noteworthy signal" intent.

Decide in `/gsd-discuss-phase` whether to ship this flag in v1.11 or defer.

### What the findings pipeline computes

Per subsection × window, two windows only (`all_time`, `last_3mo`):

```python
Zone = Literal["very_weak", "weak", "typical", "strong", "very_strong"]
Trend = Literal["improving", "declining", "stable", "n_a"]
SampleQuality = Literal["rich", "adequate", "thin"]
Window = Literal["all_time", "last_3mo"]

class SubsectionFinding(BaseModel):
    subsection_id: str        # one of the 10 subsection ids
    window: Window
    metric: str               # stable id, e.g. "endgame_skill", "score_gap"
    value: float
    zone: Zone
    trend: Trend
    weekly_points_in_window: int  # gates trend: <20 → n_a
    sample_size: int
    sample_quality: SampleQuality

class FilterContext(BaseModel):
    recency: Literal[
        "all_time", "week", "month", "3months", "6months",
        "year", "3years", "5years",
    ]
    opponent_strength: Literal["all", "stronger", "weaker", "equal"]
    color: Literal["all", "white", "black"]
    time_controls: list[str]
    platforms: list[str]
    rated_only: bool

class EndgameTabFindings(BaseModel):
    as_of: str                # ISO date
    filters: FilterContext
    findings: list[SubsectionFinding]
    flags: list[Literal[
        "baseline_lift_mutes_score_gap",
        "no_clock_entry_advantage",
        "clock_entry_advantage",
    ]]
```

**What the pipeline owns:**

1. Raw metric computation (Score Gap, Endgame Skill, Conversion / Parity / Recovery, Avg clock diff, etc.)
2. Zone assignment against FlawChess-wide benchmarks per metric (requires calibration run — see Open Questions)
3. Trend direction + quality gating (≥20 weekly points AND slope-to-volatility above threshold, else `n_a`)
4. Sample-quality classification per subsection
5. Three cross-section flags for guardrails the LLM must not get wrong:
   - `baseline_lift_mutes_score_gap`: set when `endgame_skill` zone is `strong` or `very_strong` AND `score_gap` zone is `typical` or `weak`. Prompt rule: don't describe Score Gap as "endgame is average."
   - `clock_entry_advantage`: set when `avg_clock_diff_at_endgame` value > +10% of base time.
   - `no_clock_entry_advantage`: set when `|avg_clock_diff_at_endgame|` value ≤ 10% of base time. Prompt rule: frame "handles time pressure better" as composure only.

**What the pipeline does NOT compute (deferred to v1.12+, per SEED-001):**

Archetype, role taxonomy, era comparison, stability pattern, `lookback_behavior` schema tags, `confidence_drivers`, `supports` graph, cross-combo consistency as a first-class finding, admin raw-data payload.

### Prompt structure

**System prompt** (~400 tokens, versioned as `app/services/insights_prompts/endgame_v1.md`):

```
You are FlawChess's endgame analyst. You translate computed endgame
statistics into plain-language summaries for chess players.

You receive:
- The user's active filters.
- Subsection findings: metric, value, zone (vs typical FlawChess users),
  trend, and sample quality, per subsection and per window.
- The info-popover text shown on each subsection of the tab. Treat this
  as ground truth for what each metric means. Do not contradict it.
- Precomputed flags for cross-section caveats that are easy to get wrong.

Produce a JSON response with:
- An `overview`: 1-2 paragraphs (~60-150 words total) of cross-section
  reasoning linking at least 2 different main sections. Show the
  reasoning chain, not just conclusions. Stay observational, not
  prescriptive (describe what is, do not tell the user what to work on).
  Return null when no cross-section signal is present — do not pad.
- A `sections` list: exactly 4 section insights, one per main section,
  each with one headline (<= 12 words) and 0-2 bullets (each <= 20 words).

Rules:
1. If flag `baseline_lift_mutes_score_gap` is set, do NOT describe Score
   Gap alone as "endgame is average" or "same as non-endgame play."
   Lead with Endgame Skill; frame Score Gap as muted by a strong
   non-endgame baseline.
2. If flag `no_clock_entry_advantage` is set and you claim "handles time
   pressure better", frame as composure edge only, not clock-management.
   If `clock_entry_advantage` is set, frame as both.
3. Endgame Skill and Endgame ELO gap within the same (platform, time
   control) are ONE observation, not independent corroboration.
4. If trend is `n_a`, skip the trend claim. Never speculate direction.
5. If sample_quality is `thin`, hedge ("tentatively", "limited sample").
6. Do NOT label the user with a noun ("technician", "grinder", etc.)
   in MVP. Describe patterns, not identities.
7. Do NOT give prescriptive advice ("you should work on X") in MVP.
8. No em-dashes in any output. Use commas, periods, or colons.
9. Respond in the JSON schema provided — no prose outside it.
```

**User message** (assembled per request, ~400 tokens):

```
Filters: recency=last_3mo, opponent=all, color=all,
  tc=[blitz,rapid], platform=chess.com, rated_only=true

Flags: baseline_lift_mutes_score_gap, no_clock_entry_advantage

## Subsection: overall | Games with vs without Endgame
Info-popover: "Compares your win/draw/loss rates in games that reached
an endgame phase versus those that did not. Score Gap = endgame Score %
minus non-endgame Score %. A positive value can mean stronger endgames
OR weaker non-endgame play."
Findings:
- score_gap (last_3mo): +4.2pp | typical | stable | 487 games, 52 weeks | rich
- score_gap (all_time): +3.8pp | typical | stable | 2140 games, 180 weeks | rich

## Subsection: endgame_metrics | Endgame Metrics
Info-popover: "Games split by material on entering endgame: Conversion
(lead >= +1), Parity (balanced), Recovery (trail <= -1). Endgame Skill =
average of the three rates. Gauges compare to fixed FlawChess
skill-cohort targets."
Findings:
- endgame_skill (last_3mo): 61% | strong | improving | 312 games, 48 weeks | rich
- conversion_win_pct (last_3mo): 72% | strong | improving
- parity_score_pct (last_3mo): 54% | typical | stable
- recovery_save_pct (last_3mo): 47% | typical | stable
- endgame_skill (all_time): 58% | strong | stable | 1890 games, 172 weeks | rich

[... 8 more subsections ...]
```

**What's fed, what's not:**

| Input | In MVP prompt? | Reason |
|---|---|---|
| User-facing info-popover text | Yes | Ground truth for metric meaning; keeps LLM aligned with UI |
| Computed findings JSON | Yes | Pre-validated numbers; no hallucination risk |
| Precomputed flags | Yes | Deterministic guardrails for things LLMs get wrong |
| Filter context | Yes | Disambiguates "vs stronger opponents" framing |
| Raw weekly data | No | Admin mode only; deferred to v1.12 (SEED-001) |
| Chart images / SVG | No | Not worth the complexity |
| User's history of prior reports | No | Stateless for v1.11 |

### Response schema

```python
class SectionInsight(BaseModel):
    section_id: Literal[
        "overall",              # Endgame Overall Performance
        "metrics_elo",          # Endgame Metrics and ELO
        "time_pressure",        # Time Pressure
        "type_breakdown",       # Endgame Type Breakdown
    ]
    headline: str               # <= 12 words
    bullets: list[str]          # 0-2, each <= 20 words

class EndgameInsightsReport(BaseModel):
    overview: str | None        # 1-2 paragraphs, <= 150 words, or null
    sections: list[SectionInsight]  # exactly 4, one per section_id
    model_used: str             # pydantic-ai model id at the time of the call
    prompt_version: str         # e.g. "endgame_v1"
```

### Overview design

The overview is where cross-section reasoning lives and is the highest-risk, highest-value piece of output.

- **Position first**, above the 4 section blocks. If one paragraph earns the most reading time, it's the cross-section read — don't bury it.
- **Length: 1–2 paragraphs, ≤150 words.** Longer than the per-section bullets because cross-section reasoning needs room to show the chain. Wordy LLMs are easier to spot than terse-but-wrong LLMs, so the length cap also helps judge quality.
- **Must cite ≥2 different sections**, or return null. If the overview can only reference one section, it isn't earning its keep over the section's own headline.
- **Allow null.** When all findings are typical/stable/unremarkable and no cross-section disagreement exists, return null rather than fabricate. Null renders as nothing. Silence beats filler. Cache the null result like any other.
- **Observational, not prescriptive** in MVP. "Your Conversion is strong but your time-pressure performance erodes at low clock" is in scope. "You should work on X" is not. Prescriptive advice needs validation data we don't have.
- **Beta flag for the first run** of real users. If cross-section reasoning is weak or fabricates connections, hide the overview without hiding the per-section insights (lower risk profile — they narrate precomputed zones/trends).

### Naming convention

**Section** (4) and **Subsection** (10). Used consistently throughout backend schemas, frontend components, prompt text, and test fixtures.

- 4 main H2 groupings on the Endgame tab → `Section` / `section_id`
- 10 data subsections (and any timeline subsections promoted to first-class) → `Subsection` / `subsection_id`

The SEED-001 `SectionFindings.section_id` Literal currently enumerates subsection ids. That's a stale name from before the 10-subsection count landed. Rename at MVP implementation time to `SubsectionFinding.subsection_id`.

Do NOT use "H2" in code. It's a UI-layer term that doesn't survive rename-refactors well.

## Sections in Scope

Four **Sections**, ten data **Subsections** (plus the Endgame statistics concepts accordion, which is documentation and produces no findings).

| Section (`section_id`) | Subsections (`subsection_id`) |
|---|---|
| `overall` — Endgame Overall Performance | `overall` (Games with vs without Endgame), `score_gap_timeline` (Endgame vs Non-Endgame Score Gap over Time) |
| `metrics_elo` — Endgame Metrics and ELO | `endgame_metrics` (Endgame Metrics: Conversion / Parity / Recovery / Endgame Skill), `endgame_elo_timeline` (Endgame ELO Timeline) |
| `time_pressure` — Time Pressure | `time_pressure_at_entry` (Time Pressure at Endgame Entry), `clock_diff_timeline` (Average Clock Difference over Time), `time_pressure_vs_performance` (Time Pressure vs Performance) |
| `type_breakdown` — Endgame Type Breakdown | `results_by_endgame_type`, `conversion_recovery_by_type`, `type_win_rate_timeline` |

**Supporting-only subsection** (never produces a headline finding, only supporting findings under its parent):
- `type_win_rate_timeline` — per-type timelines are almost always underpowered (samples split 5 ways). Trend findings it emits attach as supporting findings under `results_by_endgame_type`.

**Headline-eligible but gated** (headline only when trend-quality gate passes):
- `score_gap_timeline`, `clock_diff_timeline` — both are `all_time_prefilled_pre_recency` in the SEED-001 lookback sense. Current-state headlines already live in their parents (`overall`, `time_pressure_at_entry`). These timelines only earn a headline when a clear trend or recent shift is detectable; otherwise they demote to supporting findings under the parent. MVP: compute them with two windows but do not tag `lookback_behavior` in the schema (precomputed at compute time to gate the headline flag, but not exposed to the LLM directly).

## Open Questions for v1.11 Discuss Phase

- **Zone threshold calibration.** ~~Run `/benchmarks` on prod~~ — **done as of `reports/benchmarks-2026-04-18.md`.** Bands are wired from that report (see "Zone bands" section). Two follow-on decisions remain: (a) Recovery `[0.30, 0.40]` keep-as-target vs re-center to `[0.25, 0.35]`, (b) whether to add the `notable_endgame_elo_divergence` flag (`|gap| > 100 Elo`) in v1.11 or defer. (c) When to refresh: re-run `/benchmarks` once before ship if the user count has materially grown, but do not re-derive bands from scratch.
- **Trend-quality gate threshold.** Start with SEED-001's "≥20 weekly points" rule. Revisit after looking at real data — if too many trends gate to `n_a`, lower to 15.
- **Sample-quality bands per subsection.** What game count is `thin` vs `adequate` vs `rich`? `results_by_endgame_type` needs per-type thresholds because types split samples 5 ways.
- **Default `PYDANTIC_AI_MODEL_INSIGHTS` value.** Which model does the v1.11 release ship with as the production default? Pick one cost-efficient model that reliably produces structured output for this payload size and pin it in `.env.example`. Re-evaluate every milestone; the env var design means swapping costs nothing.
- **Cache-hit logging.** Do we write a log row on cache hits (for usage/telemetry visibility) or only on misses (for cost/prompt-iteration only)? Cache hits are free but high-volume; logging them bloats the table without adding prompt-engineering value. Default: log misses only in MVP, add lightweight hit counter later if needed.
- **`genai-prices` coverage.** Confirm all models we might swap to via env var are covered by genai-prices. If a model isn't covered, `cost_usd` computation fails — decide whether to fall back to zero + log a warning, or refuse to use uncovered models.
- **Beta flag surface.** One global toggle, or per-user opt-in via user settings? Per-user opt-in is safer for a first-rollout.
- **Whether the overview paragraph ships with the first release or hides by default for 1 week while the per-section insights are validated.** Recommend: ship overview hidden by default in v1.11 release; reviewing usage + sentiment before enabling by default in v1.11.1.
- **Info-popover text maintenance.** The info-popovers are currently JSX spread across component files. Options: (a) extract to a central `app/services/insights_prompts/popovers.py` for the LLM to read, (b) keep JSX canonical and have a build step extract text for the prompt, (c) manually maintain parallel copies. (a) or (b) are preferable to (c) for drift prevention.
- **Endgame statistics concepts accordion** — currently documentation only. Does anything in its content belong in the system prompt as additional ground truth for the LLM (e.g., the "endgame phase ≥ 6 half-moves" definition)? Probably yes, at least for the endgame-phase definition so the LLM doesn't re-derive it incorrectly.
- **Rendering of null overview.** If overview is null, is there a UI affordance (small text "No cross-section signal right now — see per-section insights below") or does the overview section simply not render? Default: do not render.
- **What to do when fewer than 4 sections have adequate data.** If `time_pressure` has no qualifying games (rare but possible with tight filters), does the response still include a `section_id: "time_pressure"` insight with empty bullets and a "not enough data" headline, or is that section omitted? Default: omit the section entirely from the `sections` list; render the UI gracefully.

## Not in Scope (v1.11)

Everything deferred from SEED-001 per the "Relationship to SEED-001" table. Specifically:

- Archetype classification (8-class deterministic system). LLM describes patterns; does not label users with nouns.
- Role taxonomy (`effect / mechanism / confound_ruled_out / confound_present / corroboration / null_signal`) as a schema tier. LLM narration encodes roles implicitly.
- Era comparison and regime detection. Single window pair (`all_time`, `last_3mo`) in MVP; stability patterns across 3+ windows is v1.12.
- Admin raw-data mode. Strong-model validation (passing raw weekly series to a high-tier model for comparative narrative) moves to v1.12 with SEED-001's admin flow.
- Multi-model A/B at the endpoint level. MVP uses one model per request (whichever `PYDANTIC_AI_MODEL_INSIGHTS` points to). Comparing models means changing the env var between runs and querying the log table offline, not running two providers per request.
- Per-game insights ("your Rxh4 was inaccurate") — engine-analysis territory, separate milestone.
- Benchmarks/percentiles against other users. Separate privacy + scale question, deferred; SEED-002 is the right vehicle.
- Openings and Stats tab insights. Extend the pattern in v1.12 after v1.11 Endgame insights ships.
- Statistical significance on trends (p-values, CIs in UI). Trend-quality gating is in scope; formal significance output is not.
- Phrase library / template renderer. Explicit non-goal; the LLM is the renderer.

## Breadcrumbs

### Components and services the Insights feature consumes

- `app/services/endgame_service.py` — provides section-level stats, timeline data, and the `_compute_weekly_rolling_series` pattern for trend detection
- `app/services/stats_service.py` — rating history and cross-section context
- `app/repositories/query_utils.py` — `apply_game_filters()` (insights must respect the same filter context)
- `frontend/src/components/charts/Endgame*.tsx` — 10 subsection components whose info-popover text needs to feed the prompt

### New files the Insights feature creates

- `app/services/insights_service.py` — findings computation (zone / trend / sample-quality / flags per subsection × window)
- `app/services/insights_llm.py` — pydantic-ai `Agent` wrapper, prompt assembly, structured-output call, log-row construction; reads `PYDANTIC_AI_MODEL_INSIGHTS` at startup
- `app/services/insights_prompts/endgame_v1.md` — versioned system prompt
- `app/services/insights_prompts/popovers.py` (or equivalent) — info-popover text pulled from/mirrored from the frontend components
- `app/schemas/insights.py` — Pydantic schemas (`SubsectionFinding`, `EndgameTabFindings`, `SectionInsight`, `EndgameInsightsReport`)
- `app/models/insights_llm_log.py` — SQLAlchemy ORM model for `insights_llm_logs` table
- `app/repositories/insights_llm_log_repo.py` — async write + basic read helpers for the log table
- `alembic/versions/<rev>_create_insights_llm_logs.py` — migration creating the table and indexes
- `app/routers/insights.py` — `POST /api/insights/endgame` endpoint
- `frontend/src/components/insights/EndgameInsightsBlock.tsx` — overview + 4 section blocks, beta-flagged
- `frontend/src/hooks/useEndgameInsights.ts` — TanStack Query hook, cache-aware
- `tests/services/test_insights_service.py` — zone / trend / flag computation unit tests
- `tests/services/test_insights_llm_snapshot.py` — ground-truth regression against the SEED-001 canonical user profile

### Related planning artifacts

- `.planning/seeds/SEED-001-endgame-tab-insights-section.md` — source of the insights concept. SEED-003 defers most of SEED-001's schema work to v1.12.
- `.planning/seeds/SEED-002-benchmark-db-population-baselines.md` — v1.12 upgrade path for population-stratified zone thresholds (MVP uses self-referential + `/benchmarks` calibration).
- `reports/benchmarks-2026-04-18.md` — **the calibration source of truth for v1.11 zone bands.** Per-metric pooled percentiles (n=37 active users), gauge-band recommendations, and the pooled `|gap| > 100 Elo` "notable" threshold for the new flag candidate. Read alongside this seed when wiring `insights_service.py`'s zone assignment.
- `docs/endgame-analysis-v2.md` — overall endgame analytics spec
- `.planning/quick/260418-nlh-add-endgame-skill-metric-as-simple-avera/260418-nlh-SUMMARY.md` — Endgame Skill composite decisions

### Project conventions the Insights feature must follow

- `CLAUDE.md` §Coding Guidelines — type safety, ty compliance, no magic numbers, `Literal` types for enums
- `CLAUDE.md` §Frontend — theme constants in `theme.ts`, `noUncheckedIndexedAccess`, mobile parity, `data-testid` rules
- `CLAUDE.md` §Communication Style — em-dash guidance applies to user-facing insight copy AND to the LLM's output (explicit prompt rule #8)
- `CLAUDE.md` §Error Handling & Sentry — LLM endpoint must `capture_exception` on failures; skip trivial rate-limit exceptions; use `set_context` for `user_id / findings_hash / model_id` (don't embed in error message, per grouping rules)
- `CLAUDE.md` §Database Design Rules — FK constraints with explicit `ondelete=CASCADE` on `user_id`; appropriate column types (BigInteger for log id, SmallInteger where sufficient, Numeric(10,6) for `cost_usd`)
- `CLAUDE.md` §Version Control — `.env.example` gets `PYDANTIC_AI_MODEL_INSIGHTS`; production env var lives in `/opt/flawchess/.env` on the Hetzner server, never committed

### LLM integration

- **SDK**: [`pydantic-ai`](https://ai.pydantic.dev/) (`pydantic_ai.Agent` with `result_type=EndgameInsightsReport`). Provider-agnostic — switching providers is an env-var change, not a code change.
- **Model selection**: env var `PYDANTIC_AI_MODEL_INSIGHTS` (e.g. `anthropic:claude-haiku-4-5-20251001`, `openai:gpt-4o-mini`, `google-gla:gemini-2.5-flash`). Read once at startup; restart backend to swap.
- **Cost accounting**: [`genai-prices`](https://github.com/pydantic/genai-prices) maps `(model, input_tokens, output_tokens)` to `cost_usd`, stored at write time in `insights_llm_logs.cost_usd`.
- **Provider API keys**: `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `GEMINI_API_KEY`, etc., depending on which provider the env var points to. Document required keys per provider in `.env.example`.
- **The `claude-api` skill** is the reference for Anthropic SDK patterns, but SEED-003 does NOT use the Anthropic SDK directly — pydantic-ai is the abstraction layer. Defer to pydantic-ai docs (via `context7` MCP) for Agent configuration and usage tracking.

## Notes

- **Zone threshold calibration is no longer a blocker.** ~~Before any LLM call produces meaningful output, zone bands must be set per metric from real FlawChess data.~~ The 2026-04-18 `/benchmarks` run (`reports/benchmarks-2026-04-18.md`) provides bands for every metric in scope; the "Zone bands" subsection translates them into the 5-zone schema. Wiring is a small task, not a calibration phase. Sample size (n=37 users) is acceptable for v1.11; SEED-002 replaces these bands with rating-stratified population baselines in v1.12.
- **Admin user impersonation is the eyeball-validation tool.** The N=1 fixture problem from SEED-001 is materially reduced by the existing impersonation feature. During the prompt-fluency spike (Phase 0) and again before flipping the beta flag, impersonate 5–10 real users covering: a high-skill endgame profile, a weak-endgame profile, a clock-pressure-skewed profile, a thin-sample profile, and a "everything typical" profile. Read the generated insights as that user. Catches prompt-engineering blind spots that snapshot-testing one canonical user cannot. Capture findings as a manual checklist in the PR description; do not codify as automated tests until SEED-002's larger benchmark dataset enables real cross-user assertions.
- **The log table is the prompt-engineering harness.** Iteration cadence during v1.11 development should be: bump prompt version → run against a fixture set → query the log for the new `prompt_version` → compare input/output token counts, cost, and output quality against the prior version. Don't skip the log table even if it feels like scaffolding; it's the fastest path to a good prompt.
- **Ground-truth regression test is mandatory.** Encode the SEED-001 canonical user profile (Endgame Skill ≈ 64% chess.com Blitz, Endgame ELO ~100 above Actual ELO in that combo, Score Gap +5pp, Avg clock diff within ±10%, positive time-pressure skill edge at low-clock buckets) as a synthetic fixture. Snapshot-test that the LLM's output:
  1. Does NOT describe Score Gap as "average" (flag: `baseline_lift_mutes_score_gap`)
  2. DOES mention Endgame Skill as strong
  3. Does NOT claim clock-management edge (flag: `no_clock_entry_advantage`)
  4. DOES mention composure at low clock
  5. Does NOT double-count Endgame Skill and Endgame ELO gap as independent corroboration
  6. Uses no em-dashes
  If any of 1-6 regress, fix the system prompt and re-run. Run the regression against whichever model `PYDANTIC_AI_MODEL_INSIGHTS` currently points to; the assertions are about *output*, not about which model produced it.
- **Prompt is versioned code, not a string literal.** `app/services/insights_prompts/endgame_v1.md` with few-shot examples. Review prompt changes like code changes. Bump version → cache key changes → forces regeneration. The log table's `prompt_version` column makes A/B analysis across prompt revisions trivial.
- **Exit criteria for v1.11 (prevents scope creep back to SEED-001).** Ship when all of the following are true; do NOT bolt on archetypes/roles/era/stability/admin-mode in the same milestone even if the LLM output suggests they'd help. Those are v1.12 scope by definition:
  1. Zone bands from `reports/benchmarks-2026-04-18.md` wired into `insights_service.py`; gauge components on the Endgame tab updated to match (insights and gauges agree).
  2. `POST /api/insights/endgame` returns a valid `EndgameInsightsReport` for the canonical user fixture AND has been eyeball-validated via admin impersonation for at least 5 real users across different skill profiles and filter combinations (high-skill, weak-skill, clock-skewed, thin-sample, all-typical).
  3. `insights_llm_logs` is populated in prod with `cost_usd`, `input_tokens`, `output_tokens`, `latency_ms`, `prompt_version`, `model` for every miss.
  4. Regression test (6 assertions from the note above) passes against the currently-configured `PYDANTIC_AI_MODEL_INSIGHTS` model.
  5. Beta flag defaults off; a small flag set of users (you + 3–5 invited) can enable insights via user settings.
  6. Overview paragraph can be independently hidden via config (per the Overview-design "beta flag for the first run" rule).
  Adding archetypes, roles, era comparison, stability, or admin raw-data BEFORE these six criteria ship is scope creep. Once they ship, real usage telemetry determines v1.12 priorities.
- **When v1.11 ships, SEED-001 gets a "triggered_by: v1.12" update** and becomes the reference for which deferred parts (archetypes, role graph, era comparison, stability matrix, admin raw-data mode) to promote next, informed by real usage telemetry from v1.11 (queried from `insights_llm_logs`).
- **Antipatterns to catch in review.** Flag these if they appear in a PR during v1.11:
  - Any `if archetype == ...` branch in code — archetypes are v1.12.
  - Any repository-direct query from `insights_service.py` — should go through `endgame_service.get_overview()`.
  - Any hardcoded model string in code — must come from `PYDANTIC_AI_MODEL_INSIGHTS`.
  - Any `findings_hash` computation that includes `as_of` — cache will churn daily.
  - Any prompt string literal inline in `.py` — prompts live in `insights_prompts/*.md`, loaded at startup.
  - Any em-dash in user-facing insight copy (CLAUDE.md rule) or in the system prompt's examples.
  - Any code reading `response_format`, `json_schema`, or provider-specific SDK types — pydantic-ai abstracts all of this.
- **Reference chat context:** this seed was refined on 2026-04-20 in a conversation that (1) enumerated the 10 Endgame tab subsections from the frontend components, (2) established Section / Subsection naming, (3) decided on single-call LLM architecture, (4) sized the overview to 1–2 paragraphs (not one sentence) so output quality can be judged before deciding whether to hide it, (5) confirmed the stats pipeline is still required even with LLM-first rendering, (6) switched the implementation to pydantic-ai with env-var-driven model selection and a dedicated Postgres log table for prompts/responses/tokens/cost. A second pass later the same day (7) wired in the 2026-04-18 benchmark report as the calibration source so zone bands are no longer an open question, (8) added admin impersonation as the eyeball-validation tool that closes the N=1 fixture gap, and (9) added Phase 0 (prompt-fluency spike) as the de-risking step before the findings pipeline is built. When v1.11 opens, `/gsd-discuss-phase` should start from this seed and expand the Open Questions rather than re-derive the architecture.
