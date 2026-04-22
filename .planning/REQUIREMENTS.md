# Requirements: FlawChess

**Defined:** 2026-04-20

## v1.11 Requirements

Requirements for LLM-first Endgame Insights milestone. Source: `.planning/seeds/SEED-003-llm-based-insights.md`. Each maps to roadmap phases.

### Insights UX

- [x] **INS-01
**: User with beta flag enabled sees a "Generate insights" button on the Endgame tab and can generate an insights report on demand
- [ ] **INS-02**: Generated report renders an overview paragraph (1–2 paragraphs, ≤150 words) above 4 Section blocks, each with a headline (≤12 words) and 0–2 bullets (≤20 words each)
- [x] **INS-03
**: Insights respect the active filter context that meaningfully changes the underlying findings (recency, opponent_strength, time_controls, platforms) — different filter states produce different insights. `color` and `rated_only` are NOT fed into the prompt: they do not materially reshape the cross-section story the LLM tells.
- [x] **INS-04**: Insights cache on `findings_hash` so equivalent filter states reuse the prior report; cache key includes `prompt_version` and `model` so prompt bumps and env-var model swaps invalidate naturally
- [x] **INS-05**: Generation is rate-limited to 3 cache misses per hour per user; on limit exhaustion, the user receives the last cached report (soft-fail) rather than an error
- [x] **INS-06**: The overview paragraph is ALWAYS populated when a report is produced. When no strong cross-section signal is present, the overview summarizes the per-section findings instead of returning null — silence is not a valid overview output
- [x] **INS-07**: All failure paths (structured-output validation, provider error, missing env var at startup) show a single retry affordance copy and are captured in Sentry with `set_context` for `user_id / findings_hash / model` (never embedded in error message, per CLAUDE.md grouping rules)

### Findings Pipeline

- [x] **FIND-01**: `insights_service.py` computes `SubsectionFinding` (metric, value, zone, trend, sample_size, sample_quality, weekly_points_in_window) per subsection × window (`all_time`, `last_3mo`) by consuming `endgame_service.get_overview(filter_context)` — no direct repository access from the service
- [x] **FIND-02**: Zone assignment uses the existing in-code gauge constants as the single source of truth (`SCORE_DIFF_NEUTRAL_*`, `FIXED_GAUGE_ZONES`, `ENDGAME_SKILL_ZONES`, `NEUTRAL_PCT_THRESHOLD`, `NEUTRAL_TIMEOUT_THRESHOLD`). Insights narrative and chart visuals MUST agree by construction — one set of thresholds imported from one module. The 2026-04-18 benchmark report is background context only; if a band needs adjusting, the gauge constant is the place to adjust it.
- [x] **FIND-03**: Three cross-section flags precomputed deterministically: `baseline_lift_mutes_score_gap`, `clock_entry_advantage`, `no_clock_entry_advantage`
- [x] **FIND-04**: Trend quality gate — trend returns `n_a` when weekly-points-in-window is below threshold (start at 20) or slope-to-volatility ratio is below threshold
- [x] **FIND-05**: `findings_hash` is a stable SHA256 of canonical-JSON-serialized `EndgameTabFindings` with `as_of` excluded and keys sorted — so cache does not churn daily

### LLM Endpoint

- [x] **LLM-01**: `POST /api/insights/endgame` endpoint accepts filter context and returns a validated `EndgameInsightsReport` produced by a `pydantic_ai.Agent` with `result_type=EndgameInsightsReport`
- [x] **LLM-02**: Model selected at startup from env var `PYDANTIC_AI_MODEL_INSIGHTS` (accepts any pydantic-ai model string); backend refuses to start if the env var is missing or invalid
- [x] **LLM-03**: System prompt is versioned in `app/services/insights_prompts/endgame_v1.md` (loaded from file, not a string literal) and shapes the prompt with filter context, precomputed flags, findings, and info-popover ground-truth text

### Observability

- [x] **LOG-01**: Alembic migration creates a generic `llm_logs` table (designed for reuse across future LLM features, not endgame-specific) with columns: id, created_at, user_id (FK ON DELETE CASCADE), endpoint, model, prompt_version, findings_hash, filter_context (JSONB), flags (JSONB), system_prompt, user_prompt, response_json (nullable), input_tokens, output_tokens, cost_usd (Numeric(10,6)), latency_ms, cache_hit, error (nullable)
- [ ] **LOG-02**: Every cache-miss LLM call (success or failure) writes exactly one row to `llm_logs` capturing all fields above; cost is computed from `(model, input_tokens, output_tokens)` via `genai-prices` at write time
- [x] **LOG-03**: Indexes created on `(created_at)`, `(user_id, created_at DESC)`, `(findings_hash)`, `(endpoint, created_at DESC)`, and `(model, created_at DESC)` to support time-range, per-user, dedup, per-feature, and model-comparison queries
- [ ] **LOG-04**: Sentry errors on LLM failures use `set_context` for `user_id / findings_hash / model / endpoint` rather than embedding variables in error messages, per CLAUDE.md grouping rules

### Validation

- [ ] **VAL-01**: Ground-truth regression test encodes the SEED-001 canonical user fixture and asserts the 5 correctness behaviors from SEED-003 Notes: (1) does NOT describe Score Gap as "average", (2) DOES mention Endgame Skill as strong, (3) does NOT claim clock-management edge, (4) DOES mention composure at low clock, (5) does NOT double-count Endgame Skill and Endgame ELO gap as independent corroboration
- [ ] **VAL-02**: Admin-impersonation eyeball validation completed across at least 5 real user profiles (high-skill endgame, weak endgame, clock-pressure-skewed, thin-sample, all-typical) before flipping the beta flag; findings captured in the PR description

### Beta Rollout

- [x] **BETA-01
**: Beta access is controlled by a boolean flag on the `users` table (`beta_enabled`). Default `false`. Flipping the flag is a direct DB operation (no user-settings UI, no admin page) — the whole point is a small, hand-picked validation cohort
- [x] **BETA-02
**: Overview paragraph can be independently hidden via backend config so per-section insights can ship while overview quality is being reviewed in the first rollout week

## Future Requirements (v1.12+)

Deferred from SEED-001 per SEED-003's "Relationship to SEED-001" table. Tracked but not in current roadmap.

### Deterministic Schema Tier (SEED-001)

- **ARCH-01**: 8-class deterministic archetype classification (technician, converter, underperformer, clock_hoarder, etc.)
- **ROLE-01**: Role taxonomy schema — effect / mechanism / confound_ruled_out / confound_present / corroboration / null_signal
- **ERA-01**: Era comparison / regime detection (50/50 heuristic over time windows)
- **STAB-01**: Stability pattern across 3+ windows (`stable / evolving / recent_shift / insufficient_data`)
- **LOOK-01**: `lookback_behavior` first-class schema field exposed to the LLM prompt
- **ADMN-01**: Admin raw-data mode — strong-model validation with raw weekly series in the prompt

### Coverage Expansion

- **INS-EXP-01**: Insights for the Openings tab, following the Endgame pattern validated in v1.11
- **INS-EXP-02**: Insights for the Global Stats tab, following the Endgame pattern validated in v1.11
- **BENCH-01**: Rating-stratified population baselines from a Lichess benchmark DB (tracked in SEED-002 as v1.12 scope) — replaces the current self-calibrated gauge constants with population data

## Out of Scope

Explicitly excluded. Documented to prevent scope creep back into SEED-001 territory before real v1.11 usage telemetry is available.

| Feature | Reason |
|---------|--------|
| Phrase library / template renderer | Explicit non-goal — LLM is the renderer in SEED-003 |
| Prompt-fluency spike (Phase 0) | Dropped for v1.11 — risk is absorbed by the regression test + admin-impersonation validation loop |
| User-facing settings UI for the beta flag | Beta flag is a DB-side toggle only; a small hand-picked cohort doesn't need UI plumbing |
| Raw weekly data in the LLM prompt | Admin raw-data mode deferred to v1.12 with SEED-001's admin flow |
| Chart images / SVG in the prompt | Not worth the complexity for MVP |
| User history of prior reports in the prompt | MVP is stateless — no cross-report reasoning |
| Multi-model A/B at the endpoint level | One model per request via env var; model comparisons happen offline by swapping the env var and querying logs |
| Per-game insights ("your Rxh4 was inaccurate") | Engine-analysis territory, separate milestone |
| Benchmarks/percentiles against other users in UI | Privacy + scale question; vehicle is SEED-002, not v1.11 |
| Admin raw-data mode in v1.11 | Deferred to v1.12 (SEED-001) |
| Archetype/role/era/stability output in v1.11 | Deferred to v1.12 (SEED-001) — shipping before real usage telemetry is scope creep |
| Hard style restrictions on LLM output (em-dashes, noun labels, prescriptive advice) | Let the model write naturally in MVP — correctness guards (the three cross-section flags) are in scope; stylistic over-constraint is not |

## Traceability

Which phases cover which requirements. Populated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| INS-01 | Phase 66 | Complete |
| INS-02 | Phase 66 | Pending |
| INS-03 | Phase 66 | Complete |
| INS-04 | Phase 65 | Complete |
| INS-05 | Phase 65 | Complete |
| INS-06 | Phase 65 | Complete |
| INS-07 | Phase 65 | Complete |
| FIND-01 | Phase 63 | Complete |
| FIND-02 | Phase 63 | Complete |
| FIND-03 | Phase 63 | Complete |
| FIND-04 | Phase 63 | Complete |
| FIND-05 | Phase 63 | Complete |
| LLM-01 | Phase 65 | Complete |
| LLM-02 | Phase 65 | Complete |
| LLM-03 | Phase 65 | Complete |
| LOG-01 | Phase 64 | Complete |
| LOG-02 | Phase 64 | Pending |
| LOG-03 | Phase 64 | Complete |
| LOG-04 | Phase 64 | Pending |
| VAL-01 | Phase 67 | Pending |
| VAL-02 | Phase 67 | Pending |
| BETA-01 | Phase 66 | Complete |
| BETA-02 | Phase 66 | Complete |

**Coverage:**
- v1.11 requirements: 23 total
- Mapped to phases: 23 ✓
- Unmapped: 0

### Phase Coverage Summary

| Phase | Requirements | Count |
|-------|--------------|-------|
| Phase 63: Findings Pipeline & Zone Wiring | FIND-01, FIND-02, FIND-03, FIND-04, FIND-05 | 5 |
| Phase 64: `llm_logs` Table & Async Repo | LOG-01, LOG-02, LOG-03, LOG-04 | 4 |
| Phase 65: LLM Endpoint with pydantic-ai Agent | LLM-01, LLM-02, LLM-03, INS-04, INS-05, INS-06, INS-07 | 7 |
| Phase 66: Frontend EndgameInsightsBlock & Beta Flag | INS-01, INS-02, INS-03, BETA-01, BETA-02 | 5 |
| Phase 67: Validation & Beta Rollout | VAL-01, VAL-02 | 2 |
| **Total** | | **23** |

---
*Requirements defined: 2026-04-20*
*Last updated: 2026-04-20 — roadmap created, 23/23 requirements mapped to Phases 63-67*
