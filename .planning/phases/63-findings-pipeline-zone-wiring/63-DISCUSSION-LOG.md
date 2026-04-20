# Phase 63: Findings Pipeline & Zone Wiring - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in 63-CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-20
**Phase:** 63 — findings-pipeline-zone-wiring
**Areas discussed:** Gauge constants colocation, Zone schema (3 vs 5), Flags + open-question bands, Schema shape + quality gates

---

## Gray Area Selection

| Option | Description | Selected |
|--------|-------------|----------|
| Gauge constants colocation | FIND-02 says insights narrative and chart visuals share ONE module. Today all zone constants live in frontend TS. Options: Python-authoritative + codegen TS, Python mirror + consistency test, API-exposed at runtime, or keep TS and expose via endpoint the backend also calls. | ✓ |
| Zone schema: 3 vs 5 | SEED-003 uses Literal[very_weak, weak, typical, strong, very_strong]. Current gauges are 3-zone (danger/neutral/success). Collapse Zone to 3 for MVP, extend gauges+constants to 5 (adds UI work), or split outer zones via p10/p90 in Python only. | ✓ |
| Flags + open-question bands | Two SEED-003 decisions locked for discuss-phase: notable_endgame_elo_divergence add vs defer; Recovery [0.30,0.40] keep vs [0.25,0.35] re-center. Plus benchmark tightenings adopt vs defer. | ✓ |
| Schema shape + quality gates | SubsectionFinding field set, Endgame ELO per-combo handling, supporting-finding linking, headline gating, trend-quality threshold + slope/volatility ratio + sample-quality cutoffs. | ✓ |

---

## Gauge Constants Colocation

### Q1: Where does the authoritative copy of the gauge constants live?

| Option | Description | Selected |
|--------|-------------|----------|
| Python authoritative + TS generated | Move thresholds to app/services/endgame_zones.py. Add scripts/gen_endgame_zones_ts.py emitting frontend/src/generated/endgameZones.ts. CI runs gen + git diff check. Single source, hard to drift. | ✓ |
| Python mirror + consistency test | Mirror values; add test that parses TS file and asserts equality. Two sources, no codegen. Drift caught in CI, not prevented. | |
| API-exposed at runtime | Expose via GET /api/endgames/zones; frontend fetches at boot. Single source, but adds network hop and non-trivial frontend refactor. | |
| Backend duplicates without enforcement | Cheapest now, riskiest later. Visual & narrative drift becomes silent. Not aligned with FIND-02. | |

### Q2: Does the frontend gauge wiring change land in Phase 63, or stay TS-only this phase?

| Option | Description | Selected |
|--------|-------------|----------|
| Defer FE refactor; Python-only Phase 63 | Add Python constants + generator script + CI guard. Frontend keeps current imports. Switch frontend in a follow-up or Phase 66. Keeps Phase 63 backend-only. | ✓ |
| Refactor FE in Phase 63 | Same phase rewires gauge components. Larger PR, mixed backend+frontend, but no 'two sources' window between phases. | |
| Open separate Phase 62.x quick task first | Pull centralization out as own quick task before Phase 63. Phase 63 then imports from now-Python module. Adds sequencing overhead. | |

### Q3: Scope of constants to move

| Option | Description | Selected |
|--------|-------------|----------|
| Zone thresholds only (numerical) | Move FIXED_GAUGE_ZONES, ENDGAME_SKILL_ZONES, NEUTRAL_PCT_THRESHOLD, NEUTRAL_TIMEOUT_THRESHOLD, SCORE_GAP_NEUTRAL_MIN/MAX. Colors stay in theme.ts. | ✓ |
| Thresholds + zone color references | Move both threshold values AND zone color identifiers. Adds complexity for no v1.11 win. | |
| Everything gauge-related into one module | Threshold boundaries + colors + bucket labels + display formatters. Most disruptive; scope creeps far beyond Phase 63. | |

### Q4: Module shape — flat constants or structured registry?

| Option | Description | Selected |
|--------|-------------|----------|
| Structured registry (per-metric dataclass) | ZONE_REGISTRY: Mapping[MetricId, ZoneSpec] with assign_zone() helper. Easy to extend, harder to misuse. | ✓ |
| Flat module-level constants | Mirrors TS file 1:1. Simplest port, no abstraction. | |
| Pydantic models for zones | ZoneSpec as BaseModel. Slightly heavier than dataclass; consistent with project's pydantic-everywhere lean. | |

---

## Zone Schema (3 vs 5)

### Q1: How many zones does the Zone Literal carry in v1.11?

| Option | Description | Selected |
|--------|-------------|----------|
| 3 zones — collapse for MVP | Zone = Literal['weak', 'typical', 'strong']. Maps 1:1 to existing gauges. Insights and visuals 'agree by construction' (FIND-02) without FE change. Revisit in v1.12 with SEED-002. | ✓ |
| 5 zones — add p10/p90, update gauges | Extend registry with per-metric p10/p90 from benchmark report; update gauge components to render 5 visual bands. Larger scope. | |
| 5 zones in schema, 3 in gauges (hybrid) | Python registry exposes p10/p90, gauges keep 3 visual bands. Violates 'agree by construction'. Not recommended. | |

### Q2: 3-zone Literal values

| Option | Description | Selected |
|--------|-------------|----------|
| weak / typical / strong | Direct rename of gauge danger/neutral/success to outcome-language. 'Typical' aligns with SEED-003 prose. Easiest to extend to 5 later. | ✓ |
| danger / neutral / success | Reuses gauge color-zone naming verbatim. Bleeds visual semantics into a data field the LLM reads. Harder to extend to 5. | |
| below_typical / typical / above_typical | Direction-neutral framing. Forces LLM to look up direction-per-metric. Prompt overhead. | |

### Q3: Direction encoding for signed/inverted metrics

| Option | Description | Selected |
|--------|-------------|----------|
| ZoneSpec has explicit direction field | direction: Literal['higher_is_better', 'lower_is_better']. assign_zone() applies direction correctly. Net Timeout = lower_is_better; rest = higher_is_better. | ✓ |
| Per-metric assign_zone callable | Registry holds (typical_lower, typical_upper, assign_fn). Maximum flexibility; zone logic spreads across the file. | |
| No direction field; metric_id-aware assign_zone | Single assign_zone hardcodes inverted metrics via INVERTED_METRICS set. Less explicit; review requires checking two places. | |

### Q4: Initial registry contents

| Option | Description | Selected |
|--------|-------------|----------|
| All 10 subsection-level metrics | score_gap, endgame_skill, conv/parity/recov per material bucket, avg_clock_diff_pct, net_timeout_rate, endgame_elo_gap. Covers every subsection's headline-eligible metric. | ✓ |
| Headline metrics only (5–6) | Skip net_timeout_rate (no gauge) and per-bucket conversion variants. Smaller surface; per-bucket variants computed via lookup. | |
| Start narrower, add iteratively | Ship score_gap, endgame_skill, conversion only. Add others as Phase 65/66 needs them. Risks reopening this file in every downstream phase. | |

---

## Flags + Open-Question Bands

### Q1: Add notable_endgame_elo_divergence flag in Phase 63?

| Option | Description | Selected |
|--------|-------------|----------|
| Ship 4 flags now | Add notable_endgame_elo_divergence to FlagId. Addresses SEED-003 regression assertion #5. ~10% of users at p90. Without it, LLM has no precomputed handle on the divergence. | ✓ |
| Defer — ship FIND-03's three flags | Add as follow-up quick task or in Phase 65. Lower Phase 63 scope, but regression test needs the flag handle by Phase 67 — deferring kicks the can. | |

**User's choice:** Ship 4 flags now (per recommendation; user note: "I don't really understand what this is about, let's go with your recommendation")
**Notes:** Explained inline that the flag prevents the LLM from double-counting "strong Endgame Skill" + "Endgame ELO 100 above Actual ELO" as two independent observations — they're the same observation. Flag fires only on |gap| > 100 so the LLM frames the divergence direction once and stays silent otherwise.

### Q2: Recovery typical band

| Option | Description | Selected |
|--------|-------------|----------|
| Re-center to [0.25, 0.35] | Pooled median 0.32 sits in middle. Insights are descriptive ('vs typical FlawChess users'), so 'typical = median behavior' is honest. Single-line TS edit on EndgameScoreGapSection.tsx. | ✓ |
| Keep [0.30, 0.40] as design target | Treats Recovery as aspirational benchmark. Visual unchanged. ~half of users read 'weak Recovery' when they're statistically typical. | |

### Q3: Other benchmark tightenings

| Option | Description | Selected |
|--------|-------------|----------|
| Defer to a separate quick task before Phase 65 | Phase 63 keeps existing constants except Recovery. Other tightenings ship as /gsd-quick task between Phases 64 and 65. Easier to review/revert in isolation. | ✓ |
| Adopt all tightenings in Phase 63 | Bundle all band changes since we're touching the constants module. Bigger FE diff in a 'backend-only' phase. | |
| Adopt none of the tightenings; Recovery [0.30, 0.40] | Only valid if Q2 also picks Keep. Zero TS changes. Most conservative. | |

### Q4: Cross-section flag rules

| Option | Description | Selected |
|--------|-------------|----------|
| Lock SEED-003 rules; thresholds via registry | All flag thresholds reference registry constants so future band changes auto-propagate. SEED-003 rules used verbatim. | ✓ |
| Tighten baseline_lift to require 'strong' on BOTH endgame_skill AND a second-section signal | Stricter rule reduces false positives. Risks missing real cases. | |
| Loosen baseline_lift to also fire on 'strong' Endgame Skill regardless of Score Gap zone | Fires more broadly. Risks LLM applying 'don't say average' even when Score Gap is genuinely positive. | |

---

## Schema Shape + Quality Gates

### Q1: Endgame ELO per-(platform, time-control) representation

| Option | Description | Selected |
|--------|-------------|----------|
| Fan out: one finding per combo | SubsectionFinding fires once per (platform, time_control) combo — typically 2×4 = up to 8 entries. Matches Phase 57 data shape. notable_endgame_elo_divergence flag fires if ANY combo's |gap| > 100. | ✓ |
| Single finding with structured value | One finding with value: dict[combo_key, gap_value]. Compact but breaks the 'value: float' contract; needs polymorphic field. | |
| Flag-only — no per-combo finding | Just emit notable_endgame_elo_divergence flag. LLM has nothing to point at. Starves the reasoning. | |

### Q2: Parent/headline-gating fields on SubsectionFinding

| Option | Description | Selected |
|--------|-------------|----------|
| Add parent_subsection_id + is_headline_eligible | Optional parent_subsection_id (None for top-level). is_headline_eligible: bool gates score_gap_timeline / clock_diff_timeline. NO lookback_role/lookback_behavior — precomputed implicitly per SEED-003. | ✓ |
| Add only parent_subsection_id; gate via trend == 'n_a' | Smaller schema. LLM treats supporting via prompt rule. Less explicit. | |
| Stay flat — no parent/headline fields | Type-timeline findings emit alongside parent type findings. Risks LLM treating supporting findings as headline. | |

### Q3: Trend-quality gate

| Option | Description | Selected |
|--------|-------------|----------|
| Both gates: weekly_points >= 20 AND slope/volatility >= 0.5 | Lock both per FIND-04. Constants in registry (TREND_MIN_WEEKLY_POINTS = 20, TREND_MIN_SLOPE_VOL_RATIO = 0.5 placeholder). Either failure → trend = 'n_a'. | ✓ |
| Count gate only (>= 20 weekly points) | Drop slope/volatility. Simpler. But ships FIND-04 partially. | |
| Count gate at 15 | Pre-empts SEED-003's 'lower to 15' iteration. Noisier trends in LLM prompt for thin samples. | |

### Q4: Sample-quality bands

| Option | Description | Selected |
|--------|-------------|----------|
| Per-subsection thresholds in the registry | SAMPLE_QUALITY_BANDS: dict[subsection_id, tuple[int, int]]. score_gap (50, 200), results_by_endgame_type (10, 40 per-type). Each subsection's denominator stays honest. | ✓ |
| Global thresholds + per-type override | Single GLOBAL_SAMPLE_BANDS = (50, 200) plus TYPE_BREAKDOWN_OVERRIDE = (10, 40). Less precise; covers 80% case. | |
| Defer to follow-up; ship 'rich' for everything | Hardcode sample_quality = 'rich'. Violates FIND-01's sample_quality semantics; thin-sample profile is a Phase 67 regression target. | |

---

## Claude's Discretion

Areas where the user said "you decide" or where Claude has flexibility per the CONTEXT decisions:
- Exact file/test layout (`app/services/insights_service.py`, `app/services/endgame_zones.py`, `app/schemas/insights.py`, `scripts/gen_endgame_zones_ts.py`, `tests/services/test_insights_service.py`, `tests/services/test_endgame_zones_consistency.py`).
- `findings_hash` serializer choice (Pydantic `model_dump_json` vs `json.dumps(model_dump(mode="json"), sort_keys=True)`).
- `MetricId` overloading vs separate signature for bucket-keyed lookups.
- Empty-window null-value convention (NaN vs 0.0 vs sentinel).
- Bucket-aware Conv/Parity/Recov fan-out under `endgame_metrics` subsection.

## Deferred Ideas

- 5-zone schema (`very_weak`/`very_strong`) — v1.12 with SEED-002 baselines.
- Benchmark band tightenings (Score Gap ±10pp→±8pp, Clock Diff ±10%→±7%, Endgame Skill upper 0.55→0.59) — quick task between Phases 64 and 65.
- FE consumer switch to `frontend/src/generated/endgameZones.ts` — quick task or Phase 66.
- `lookback_behavior` / `lookback_role` schema field — SEED-001 deferred parts; not in v1.11.
- Cache-hit logging policy — Phase 65 decision.
- Info-popover text extraction (`app/services/insights_prompts/popovers.py`) — Phase 65 decision.
