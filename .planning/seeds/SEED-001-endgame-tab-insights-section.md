---
id: SEED-001
status: dormant
planted: 2026-04-18
planted_during: v1.10 Advanced Analytics (executing, 82% complete at plant time)
trigger_when: milestone v1.11 opens
scope: large
---

# SEED-001: Insights section on Endgame tab (and later other tabs)

## Why This Matters

The Endgame tab already surfaces a lot of data (Endgame Skill composite, Score Gap timeline, Time Pressure stats, Endgame Type Breakdown, and in v1.10 the new Endgame ELO breakdown + timeline from Phases 56/57). Users see the numbers but still have to synthesize conclusions themselves: is this area good or bad for me, is it improving, and crucially — how do these sections relate to each other?

A glanceable Insights section per tab (headline + 2 bullets) translates the numbers into plain-language findings, tailored to the active filters (recency, opponent strength, color, etc.). Filters reshape the data more than anything else on the page, so insights have to reflect them or they're misleading.

The bigger payoff comes from cross-section synthesis: a user with poor endgame skill AND poor time pressure stats probably has a time management problem, not an endgame technique problem. Templates can't naturally derive that inversion; an LLM handed structured findings from every section can. That's the feature that makes FlawChess more than a stats dashboard.

## When to Surface

**Trigger:** Milestone v1.11 opens (user explicit)

This seed should be presented during `/gsd-new-milestone` when:
- The user starts planning v1.11
- OR the milestone scope mentions "insights", "AI summary", "recommendations", "natural language findings"
- OR the roadmap references consolidating / explaining existing analytics

Do NOT surface during v1.10 — current milestone is implementing the underlying analytics (Endgame ELO via Phases 56/57) that the Insights feature will summarize. Insights must consume those completed services, not parallel-develop them.

## Scope Estimate

**Large** — a full milestone's worth of work, not a single phase. Expected decomposition:

1. Backend findings computation service + schemas (`insights_service.py`, `app/schemas/insights.py`)
2. Per-section findings implementations (4 sections on the Endgame tab)
3. Template phrase library + frontend rendering component
4. AI report endpoint (Haiku 4.5) + findings-hash cache + rate limiter
5. UI: button placement, loading/error states, section-anchor navigation from report text
6. Optional: extend to Openings and Stats tabs (or defer to v1.12)

Phases 1-3 could ship as v1.11 MVP (templates only, no AI). Phases 4-5 could follow in v1.11 or v1.12 depending on appetite.

## Design Decisions (Already Brainstormed)

The full design discussion happened in the conversation preceding this seed. Preserve these decisions through the `/gsd-discuss-phase` for each v1.11 phase:

### Architecture

- **Hybrid deterministic+LLM approach.** Backend computes structured `InsightFindings` per section (zones, trends, comparisons, caveats). Frontend renders via template phrase library. Later, an optional AI report endpoint passes the same findings JSON to Haiku 4.5 for cross-section synthesis.
- **Whole-tab endpoint, not per-section.** Cross-section synthesis needs all sections anyway, and whole-tab caching is simpler.
- **New service: `app/services/insights_service.py`** consumes existing section service outputs; does NOT recompute stats.

### Schema (Pydantic sketch)

```python
Zone = Literal["very_weak", "weak", "typical", "strong", "very_strong"]
Trend = Literal["improving", "declining", "stable", "volatile", "n_a"]
SampleQuality = Literal["rich", "adequate", "thin", "insufficient"]
Severity = Literal["headline", "supporting", "aside"]

class Finding(BaseModel):
    kind: Literal["zone", "trend", "comparison", "caveat"]
    metric: str                      # stable id for phrase lookup
    severity: Severity
    value: float | None = None
    zone: Zone | None = None
    direction: Trend | None = None
    slope: float | None = None       # for trends; signed, per week
    label: str | None = None         # e.g. "Rook endings"
    ref_label: str | None = None
    ref_value: float | None = None

class FilterContext(BaseModel):
    recency: Literal["all_time", "1m", "3m", "6m", "1y"]
    opponent_strength: Literal["all", "stronger", "weaker", "equal"]
    color: Literal["all", "white", "black"]
    time_controls: list[str]
    platforms: list[str]
    rated_only: bool

class SectionFindings(BaseModel):
    section_id: Literal["overall", "time_pressure", "type_breakdown", "endgame_elo"]
    sample_quality: SampleQuality
    games_in_scope: int
    findings: list[Finding]          # severity-ordered

class EndgameTabFindings(BaseModel):
    as_of: str                       # ISO date
    filters: FilterContext
    sections: list[SectionFindings]
    cross_section: list[Finding]     # computed correlations, LLM input only
```

### Sections in Scope

Four sections on the Endgame tab (not three — Phase 57's Endgame ELO section counts):

| Section | Headline candidates | Supporting |
|---|---|---|
| **Overall** | `endgame_skill` zone, `score_gap` sign | Strongest/weakest of Conversion/Parity/Recovery, skill trend |
| **Time Pressure** | `net_clock_diff_at_endgame` zone, `timeout_rate` zone | Conversion when ahead vs behind, trend |
| **Type Breakdown** | Weakest bucket (N ≥ threshold), strongest bucket | Most frequent bucket, asymmetries |
| **Endgame ELO** (Phases 56+57) | Largest negative `combo_gap`, diverging combo trend | Platform/TC comparisons, sample caveats |

### Cross-Section Synthesis (where LLM earns its keep)

- **Corroboration**: high `endgame_skill` + positive `combo_gap` across combos → "endings are genuinely your strength." Two independent computations agreeing = high-confidence claim.
- **Divergence**: low `endgame_skill` + *positive* `combo_gap` → "weakness is in openings/middlegame, not endings." Templates can't derive this naturally.
- **Causal chain**: low `time_pressure.net_clock_diff` + negative `overall.score_gap` → emit `time_pressure_drives_endgame` cross-section finding with `severity=headline`. LLM gets this pre-labeled, no reasoning over raw timelines required.

### AI Report Cost/UX Controls

- **Cost math:** Haiku 4.5, ~500 tokens in + ~400 tokens out ≈ **$0.003/report**. Budget isn't the real constraint.
- **Cache on `findings_hash`, not `filter_hash`** — many filter combinations round to identical findings (e.g., "last 3 months" and "last 6 months" against stronger opponents can produce same zone ratings and trend classifications).
- **Rate limit applies to cache MISSES, not requests** (3/hr/user). A user flipping filters shouldn't burn quota on duplicates.
- **Soft-fail on limit:** show last cached report rather than hard block. Free-platform users forgive slow updates more than denial.
- **Button-triggered, not auto.** Hide button when `sample_quality = insufficient`. Consider one-time "Try AI insights" nudge after user views the tab twice.
- **Placement:** bottom of tab, with section-anchor links in report text so "your endgame issue is time pressure" can jump to the Time Pressure section.

### Open Questions for v1.11 Discuss Phase

- Per-section findings computation order: does each section compute its own findings via a dedicated helper, or one pass over a unified data structure?
- Template phrase library format: TypeScript object map keyed by `{metric, severity, zone}` vs. translation-style key lookup (`insights.endgame.overall.skill.strong.headline`)?
- Findings schema versioning (for cache invalidation when new findings are added in later milestones)
- Ship templates-only first, or ship AI report in the same milestone?
- Whether to extend to Openings and Stats tabs in v1.11, or defer those to v1.12

### Not in Scope

- **Proper statistical significance testing on trends** — use simple slope + volatility bucketing; p-values are overkill for UI narrative and create false precision.
- **Per-game insights** ("your Rxh4 was inaccurate") — that's engine-analysis territory, separate milestone.
- **Benchmarks/percentiles against other users** — separate privacy + scale question, defer.

## Breadcrumbs

### Sections that will receive Insights (Endgame tab)

- `frontend/src/components/charts/EndgamePerformanceSection.tsx` — Overall Performance section container
- `frontend/src/components/charts/EndgameScoreGapSection.tsx` — Score Gap + Endgame Skill composite (includes current `endgameSkill()` helper; Phase 56 will port to backend)
- `frontend/src/components/charts/EndgameTimePressureSection.tsx` — Time Pressure section container
- `frontend/src/components/charts/EndgameClockPressureSection.tsx` — clock-diff stats and timeline
- (future) Endgame ELO section — Phase 57 will create `EndgameEloTimelineSection.tsx`; Phase 56 creates the breakdown table

### Backend services that the Insights service will consume

- `app/services/endgame_service.py` — provides section-level stats, timeline data, and the `_compute_weekly_rolling_series` pattern used for trend detection
- `app/services/stats_service.py` — rating history and cross-section context
- `app/repositories/query_utils.py` — `apply_game_filters()` (insights must respect the same filter context)

### Related planning artifacts

- `.planning/phases/52-endgame-tab-performance/` — original endgame tab design
- `.planning/phases/53-endgame-score-gap-material-breakdown/` — Conversion/Parity/Recovery inputs to Endgame Skill
- `.planning/phases/54-time-pressure-clock-stats-table/` — Time Pressure section origin
- `.planning/phases/55-time-pressure-performance-chart/`
- `.planning/phases/57-endgame-elo-timeline-chart/57-CONTEXT.md` — currently-active phase, design for Endgame ELO timeline (must complete before v1.11)
- `.planning/quick/260418-nlh-add-endgame-skill-metric-as-simple-avera/260418-nlh-SUMMARY.md` — Endgame Skill composite decisions (45-55% blue band semantics, ~52% typical)
- `docs/endgame-analysis-v2.md` — overall endgame analytics spec; §5 min-sample-size convention (10 games)

### Project conventions the Insights feature must follow

- `CLAUDE.md` §Frontend — theme constants in `theme.ts`, `noUncheckedIndexedAccess`, mobile parity rule, `data-testid` rules
- `CLAUDE.md` §Coding Guidelines — type safety, ty compliance, no magic numbers, Literal types for enum-like strings
- `CLAUDE.md` §Communication Style — em-dash guidance applies to user-facing insight copy (tooltips, headlines, bullets)
- `CLAUDE.md` §Error Handling & Sentry — AI report endpoint must `capture_exception` on failures; skip trivial rate-limit exceptions

## Notes

- **Do not start before Phases 56 and 57 land.** Insights synthesize across the four Endgame sections, and the Endgame ELO section is the fourth. Without it, cross-section synthesis loses one of its strongest signals (the skill-vs-gap corroboration/divergence pattern).
- **Reference chat context:** the full design discussion preceding this seed includes cost math validation, caching subtlety, button-vs-auto tradeoff analysis, schema sketch, section → finding mapping table, and cross-section diagnostic examples. When v1.11 opens, `/gsd-discuss-phase` should start from this seed and expand open questions, not re-derive decisions already made.
- **MVP slicing recommendation:** ship templates-only in v1.11. The AI report is the "wow" feature but it depends on well-designed findings. Templates force the findings schema to prove its value first; AI report becomes a thin rendering layer on top.
