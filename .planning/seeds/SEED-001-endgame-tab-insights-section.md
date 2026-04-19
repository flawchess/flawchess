---
id: SEED-001
status: dormant
planted: 2026-04-18
refined: 2026-04-19
planted_during: v1.10 Advanced Analytics (executing, 82% complete at plant time)
trigger_when: milestone v1.11 opens
scope: large
---

# SEED-001: Insights section on Endgame tab (and later other tabs)

## Why This Matters

The Endgame tab already surfaces a lot of data (Endgame Skill composite, Score Gap timeline, Time Pressure stats, Endgame Type Breakdown, and in v1.10 the new Endgame ELO breakdown + timeline from Phases 56/57). Users see the numbers but still have to synthesize conclusions themselves: is this area good or bad for me, is it improving, and crucially — how do these sections relate to each other?

A glanceable Insights section per tab (headline + 2 bullets) translates the numbers into plain-language findings, tailored to the active filters (recency, opponent strength, color, etc.). Filters reshape the data more than anything else on the page, so insights have to reflect them or they're misleading.

The bigger payoff comes from cross-section synthesis: a user with poor endgame skill AND poor time pressure stats probably has a time management problem, not an endgame technique problem. Templates can't naturally derive that inversion; an LLM handed structured findings from every section can. That's the feature that makes FlawChess more than a stats dashboard.

Second-order payoff: cross-section reasoning is *hard*, even for data scientists. A live design discussion walked through one real user whose Endgame ELO sat +100 above Actual ELO while their raw Score Diff stayed neutral (+5pp). Reconciling the two required reasoning about material-adjustment, selection effects, baseline-lift confounds, and skill-at-clock-level vs clock-entry-advantage. An untrained user will not reach that conclusion unaided. The insights pipeline is explicitly designed to encode this kind of reasoning deterministically.

## When to Surface

**Trigger:** Milestone v1.11 opens (user explicit)

This seed should be presented during `/gsd-new-milestone` when:
- The user starts planning v1.11
- OR the milestone scope mentions "insights", "AI summary", "recommendations", "natural language findings"
- OR the roadmap references consolidating / explaining existing analytics

Do NOT surface during v1.10 — current milestone is implementing the underlying analytics (Endgame ELO via Phases 56/57) that the Insights feature will summarize. Insights must consume those completed services, not parallel-develop them.

## Scope Estimate

**Large** — a full milestone's worth of work, not a single phase. Expected decomposition:

1. Backend findings computation service + schemas (`insights_service.py`, `app/schemas/insights.py`) with role taxonomy, confidence, and temporal scope
2. Per-section findings implementations (4 sections on the Endgame tab) with multi-window computation (`all_time`, `last_1y`, `last_3mo`) and trend-quality gating
3. Cross-section synthesis: role-typed cross-section findings (effect, mechanism, confound_ruled_out, confound_present, corroboration, null_signal) and archetype assignment per (combo × window)
4. Stability detection + era comparison (heuristic changepoint for v1.11; defer statistical changepoint to v1.12)
5. Template phrase library + frontend rendering component (archetype-aware, temporally-aware framing)
6. AI report endpoint with configurable model tier (Haiku 4.5 default for users; Sonnet 4.6 / Opus 4.7 available for admin) + findings-hash cache + rate limiter
7. Admin-only mode: raw weekly datapoints included in the LLM payload alongside computed findings, enabling side-by-side comparison between "insights from raw data" and "insights from computed patterns" — validates the findings pipeline against ground truth
8. UI: button placement, loading/error states, section-anchor navigation from report text
9. Optional: extend to Openings and Stats tabs (or defer to v1.12)

Phases 1-3 could ship as v1.11 MVP (templates only, no AI). Phases 4-7 could follow in v1.11 or v1.12 depending on appetite. Admin raw-data mode (#7) is the highest-leverage validation tool and can be prioritized independently of user-facing polish if the goal is to improve the findings schema quickly.

## Design Decisions (Already Brainstormed)

The full design discussion happened in the conversation preceding this seed, across two threads: (1) original architecture and cost analysis (2026-04-18), and (2) temporal structure, role taxonomy, archetypes, and admin validation mode (2026-04-19). Preserve these decisions through the `/gsd-discuss-phase` for each v1.11 phase.

### Architecture

- **Hybrid deterministic+LLM approach.** Backend computes structured `InsightFindings` per section (zones, trends, comparisons, caveats) with role tags and confidence. Frontend renders via template phrase library. An optional AI report endpoint passes the same findings JSON to an LLM for narrative synthesis.
- **Configurable model tier.** Default user-facing model is Haiku 4.5 (cost-optimized). Admin mode accepts Sonnet 4.6 or Opus 4.7 to serve as a validation harness — comparing a strong model's narrative against the templates surfaces cases where the findings schema underspecifies or misleads.
- **Whole-tab endpoint, not per-section.** Cross-section synthesis needs all sections anyway, and whole-tab caching is simpler.
- **New service: `app/services/insights_service.py`** consumes existing section service outputs; does NOT recompute stats. Adds a temporal-windowing layer that re-runs section findings over configurable windows.
- **Archetype assignment is deterministic (backend logic), not LLM-inferred.** The LLM narrates a pre-structured graph of role-tagged findings. It does not reason over raw timelines and it does not classify. This keeps LLM failure modes bounded and lets templates substitute for the LLM with minimal quality loss.

### Schema (Pydantic sketch)

```python
Zone = Literal["very_weak", "weak", "typical", "strong", "very_strong"]
Trend = Literal["improving", "declining", "stable", "volatile", "n_a"]
SampleQuality = Literal["rich", "adequate", "thin", "insufficient"]
Severity = Literal["headline", "supporting", "aside"]
Confidence = Literal["high", "medium", "low"]
Window = Literal["all_time", "last_1y", "last_3mo"]
StabilityPattern = Literal[
    "stable", "evolving", "recent_shift", "insufficient_data"
]
CrossSectionRole = Literal[
    "effect",              # what's happening (e.g., endgame ELO +100)
    "mechanism",           # why (e.g., skill at low-clock buckets)
    "confound_ruled_out",  # what it's NOT (e.g., not a clock advantage)
    "confound_present",    # why the naive metric misleads
    "corroboration",       # two independent measurements agreeing
    "null_signal",         # neutral value that matters for ruling-out
]
PlayerArchetype = Literal[
    "technician",          # strong endgames, weaker opening/middle
    "tactician",           # opposite: crushes middlegame, endgames average
    "grinder",             # wins close/worse positions via pressure skill
    "time_cracker",        # handles low clock better than peers
    "clock_hoarder",       # gains edge by arriving with more time
    "solid_all_around",    # no dramatic phase differences
    "underperformer",      # all phases below rating expectation
    "insufficient_data",
]
ConfidenceDriver = Literal[
    "large_sample", "small_sample",
    "corroborated", "sole_signal",
    "stable_trend", "volatile_trend", "short_window",
]

class Finding(BaseModel):
    id: str                          # stable id for cross-referencing
    kind: Literal["zone", "trend", "comparison", "caveat"]
    metric: str                      # stable id for phrase lookup
    severity: Severity
    confidence: Confidence
    confidence_drivers: list[ConfidenceDriver]
    value: float | None = None
    zone: Zone | None = None
    direction: Trend | None = None
    slope: float | None = None       # for trends; signed, per week
    label: str | None = None         # e.g. "Rook endings"
    ref_label: str | None = None
    ref_value: float | None = None

class CrossSectionFinding(Finding):
    role: CrossSectionRole
    supports: list[str]              # IDs of findings this links to

class FilterContext(BaseModel):
    recency: Literal["all_time", "1m", "3m", "6m", "1y"]
    opponent_strength: Literal["all", "stronger", "weaker", "equal"]
    color: Literal["all", "white", "black"]
    time_controls: list[str]
    platforms: list[str]
    rated_only: bool

class SectionFindings(BaseModel):
    section_id: Literal["overall", "time_pressure", "type_breakdown", "endgame_elo"]
    window: Window
    stability_vs_all_time: StabilityPattern | None
    sample_quality: SampleQuality
    games_in_scope: int
    findings: list[Finding]          # severity-ordered

class ArchetypeAssignment(BaseModel):
    combo: tuple[str, str] | Literal["all_combos"]   # (platform, tc) or aggregated
    window: Window
    archetype: PlayerArchetype
    confidence: Confidence
    evidence_finding_ids: list[str]

class EraComparison(BaseModel):
    metric: str
    recent_value: float
    baseline_value: float
    delta: float
    significance: Literal["major_change", "minor_change", "stable"]
    era_label: str | None            # e.g., "2022-01 to 2023-09"

class WeeklyDatapoint(BaseModel):
    """Admin-mode payload: raw weekly series from the underlying charts.
    Not exposed in the standard user-facing payload. Included only when
    the admin flag is set, to let strong models reason over raw data
    and surface gaps in the computed-findings pipeline."""
    section_id: str
    series_id: str                   # e.g., "composite_skill_chesscom_blitz"
    week: str                        # ISO week start date
    value: float
    sample_size: int

class EndgameTabFindings(BaseModel):
    as_of: str                       # ISO date
    filters: FilterContext
    sections: list[SectionFindings]  # includes all computed windows
    cross_section: list[CrossSectionFinding]
    archetypes: list[ArchetypeAssignment]
    era_comparisons: list[EraComparison]
    # admin-only: populated when request includes admin=true
    raw_weekly: list[WeeklyDatapoint] | None = None
```

### Temporal Structure

The snapshot-oriented "one filter, one archetype" design fails for multi-year histories (archetype labels average across regime changes) and short windows (thin samples produce confident-sounding noise). The insights pipeline is instead temporally structured:

- **Multi-window findings.** Each section independently computes findings over `all_time`, `last_1y`, and `last_3mo` windows when data permits. Confidence decays as the window shrinks and as sample size falls.
- **Stability assessment.** When the same section yields different zone/trend/archetype across windows, emit a `StabilityPattern`: `stable` (windows agree), `evolving` (gradual drift), `recent_shift` (last_3mo materially differs from last_1y), or `insufficient_data`.
- **Per-(combo × window) archetype matrix.** Archetype assignment is not a single per-user label. It's a matrix indexed by (platform, time_control) × window, sample-gated per cell. The synthesis picks the richest cell as the primary archetype and narrates variation across the matrix. This explicitly handles users whose playstyle differs between bullet and classical, or whose archetype has shifted over time.
- **Trend-quality gating.** Trend findings (`slope`, `direction`) are suppressed when the window contains fewer than 20 weekly points, or when slope-to-volatility ratio is below a threshold. Replace with `direction="n_a"`. This prevents short-window reports from hallucinating trends from noise.
- **Regime detection (v1.11 heuristic, v1.12 statistical).** For users with 2+ years of history: split the composite skill timeline in half by calendar. If means differ by >5pp and ranges don't overlap, emit an era-comparison finding and label the earlier window an "earlier era." Defer Bayesian changepoint / CUSUM to v1.12 — the heuristic is enough for most cases.

The result: the pipeline produces the right kind of output for both extremes.

- **5-year history**: "you've been a technician since 2023; earlier era (2020-2022) shows a different archetype. Here's what changed."
- **6 months with 80 games**: "zone assignments at medium confidence; trend claims suppressed; tentative archetype based on recent window only."

### Archetype Synthesis

Archetype assignment is deterministic so it's auditable and stable across reports. Each archetype is defined by a signature pattern of findings:

| Archetype | Signature |
|---|---|
| `technician` | high composite skill + positive endgame ELO gap + modest/negative Score Diff |
| `tactician` | neutral composite skill + negative endgame ELO gap + positive Score Diff |
| `grinder` | positive Parity + positive Recovery + time-pressure skill edge + no clock-entry advantage |
| `time_cracker` | user Score% at low-clock buckets >> opponents' Score% at same buckets, regardless of Parity/Recovery |
| `clock_hoarder` | user enters endgames with materially more clock than opponents (>+10% of base time); score advantage concentrated in low-opponent-clock buckets |
| `solid_all_around` | all zones typical, no strong directional findings |
| `underperformer` | composite skill, ELO gap, Score Diff all negative |
| `insufficient_data` | sample_quality is `thin` or `insufficient` for any load-bearing section |

Each archetype maps to:

- **Narrative framing** (phrase library): e.g. "You're a technician — strong endgame technique relative to your rating."
- **Practical advice**: e.g. "Your improvement path likely runs through openings and middlegame, not more endgame study."
- **Evidence links**: list of `Finding.id`s that justify the assignment.

When multiple archetypes could apply per (combo × window), pick the one with the highest confidence and emit the runner-up as a supporting finding (e.g., "also shows signs of `time_cracker` in blitz specifically").

### Material-Adjusted Precedence

When composite skill (material-adjusted) and raw Score% gap (not material-adjusted) disagree:

- **Agree in direction, disagree in magnitude** (e.g., composite +100 ELO, Score Diff +5pp): composite is primary. Raw gap is framed as "consistent but muted due to skill lifting both baselines" — emit a `confound_present` cross-section finding explaining the baseline-lift effect.
- **Disagree in direction**: high-severity caveat. One is wrong or the sample is unstable — emit a `caveat` finding and downgrade archetype confidence.

This prevents templates from writing "your endgames are about the same as your middlegame" when the material-adjusted truth is "your endgame technique is above your rating level but your non-endgame baseline is also strong."

### Disambiguation Requirements

Certain findings are prone to obvious misinterpretations. The insights_service must mechanically check paired findings before emitting them:

- **"Handles time pressure better"**: before emitting, check the Clock Pressure chart. If user also has a clock-entry advantage (>+5% of base time), frame as "both composure and clock-management edge." If no clock-entry advantage, frame as "composure edge only — you don't arrive with more time, but you play better when time is short." Never conflate the two.
- **"Endgame is a strength"**: before emitting, confirm composite skill zone is `strong` or `very_strong`. Raw Score Diff alone is insufficient (fails the baseline-lift check).
- **"Improving over time"**: before emitting, confirm trend-quality gate passed (≥20 weekly points, slope-to-volatility above threshold). Otherwise emit `direction="n_a"` instead.

These checks are deterministic and belong in the backend — not in the LLM prompt. LLMs will otherwise get this wrong (this was empirically demonstrated in the design discussion).

### Sections in Scope

Four sections on the Endgame tab (not three — Phase 57's Endgame ELO section counts). Each section's findings are computed per window (`all_time`, `last_1y`, `last_3mo`):

| Section | Headline candidates | Supporting |
|---|---|---|
| **Overall** | `endgame_skill` zone, `score_gap` sign | Strongest/weakest of Conversion/Parity/Recovery, skill trend |
| **Time Pressure** | `net_clock_diff_at_endgame` zone, `timeout_rate` zone, skill-at-low-clock edge vs opponents | Conversion when ahead vs behind, trend |
| **Type Breakdown** | Weakest bucket (N ≥ threshold), strongest bucket | Most frequent bucket, asymmetries |
| **Endgame ELO** (Phases 56+57) | Largest negative `combo_gap`, diverging combo trend, per-combo archetype | Platform/TC comparisons, sample caveats, era comparison when 2+ years of history |

### Cross-Section Synthesis (where the LLM earns its keep)

Every cross-section finding carries a `role` so the LLM narrates a pre-structured causal graph instead of rediscovering it:

- **Effect (`role=effect`)**: "endgame ELO +100 above actual ELO" — the headline observation.
- **Mechanism (`role=mechanism`)**: "user scores higher than opponents at the same low-clock buckets" — why the effect exists.
- **Confound ruled out (`role=confound_ruled_out`)**: "user does NOT enter endgames with more clock" — preempts the obvious alternative explanation.
- **Confound present (`role=confound_present`)**: "non-endgame baseline is also elevated, so raw Score Diff understates the true endgame edge" — explains why a naive metric lies.
- **Corroboration (`role=corroboration`)**: high `endgame_skill` + positive `combo_gap` across combos agreeing.
- **Null signal (`role=null_signal`)**: a neutral/typical value that matters *because* it rules a mechanism out. Must be emitted, not suppressed.

**Worked example** (the real user profile from the design discussion): endgame ELO +100, Score Diff +5pp, time-pressure skill edge, no clock-entry advantage. Findings graph:

1. `effect`: "Composite skill 64% → endgame ELO ~100 above actual"
2. `mechanism`: "Higher Score% than opponents at low-clock buckets"
3. `confound_ruled_out`: "Clock-entry time is near-parity with opponents"
4. `confound_present`: "Strong non-endgame baseline mutes the raw Score Diff comparison"
5. Archetype: `grinder` with blitz specialization

The LLM narrates this graph in order. Templates can substitute for the LLM at reduced fluency but preserved correctness. **Use this worked example as a ground-truth regression test for the findings pipeline and the AI prompt.**

### AI Report Cost/UX Controls

- **Configurable model tier.** User-facing reports default to Haiku 4.5. Admin requests can specify Sonnet 4.6 or Opus 4.7 for validation work.
  - **Haiku 4.5**: ~500 tokens in + ~400 tokens out ≈ **$0.003/report**. Good enough for template-backed narrative over computed findings.
  - **Sonnet 4.6**: ~10x the cost. Use when the findings graph is complex (e.g., multi-era histories with regime changes) or when validating template output.
  - **Opus 4.7 (admin only)**: reserved for deep validation — e.g., comparing LLM-derived insights from raw weekly data against the computed-findings pipeline output.
- **Admin raw-data mode.** When request flag `admin=true` is set, the LLM payload includes `raw_weekly: list[WeeklyDatapoint]` alongside the structured findings. This lets a strong model reason directly over the underlying series and produce an "insights from raw" narrative that can be compared against the "insights from computed findings" narrative. Divergences between the two are the primary signal for improving the findings schema: if the raw-data narrative surfaces something the computed-findings narrative misses, the findings pipeline has a gap to close.
  - Gated behind admin auth, not a user toggle.
  - Payload can balloon (e.g., 150 weekly points × 4 sections × ~10 series = ~6000 tokens). Use only with strong models.
  - Cache separately (`findings_hash + admin_flag + model_id`) to avoid cross-contamination with user-facing cache.
  - Expected primary output: a delta report listing what each narrative surfaced that the other missed, not two parallel narratives for their own sake.
- **Cache on `findings_hash`, not `filter_hash`** — many filter combinations round to identical findings (e.g., "last 3 months" and "last 6 months" against stronger opponents can produce same zone ratings and trend classifications).
- **Rate limit applies to cache MISSES, not requests** (3/hr/user for user-facing; admin is unlimited). A user flipping filters shouldn't burn quota on duplicates.
- **Soft-fail on limit:** show last cached report rather than hard block. Free-platform users forgive slow updates more than denial.
- **Button-triggered, not auto.** Hide button when `sample_quality = insufficient`. Consider one-time "Try AI insights" nudge after user views the tab twice.
- **Placement:** bottom of tab, with section-anchor links in report text so "your endgame issue is time pressure" can jump to the Time Pressure section.
- **Prompt is versioned code, not a string literal.** Store the LLM prompt as `app/services/insights_prompts/endgame_v1.md` with few-shot examples demonstrating correct mechanism-vs-effect framing, archetype narration, and material-adjusted precedence handling. Review like code. Admin-mode prompt is a separate file (`endgame_admin_v1.md`) with instructions to produce a comparative narrative (raw-data narrative vs findings narrative, with delta).

### Open Questions for v1.11 Discuss Phase

- Per-section findings computation order: does each section compute its own findings via a dedicated helper, or one pass over a unified data structure?
- Template phrase library format: TypeScript object map keyed by `{metric, severity, zone}` vs. translation-style key lookup (`insights.endgame.overall.skill.strong.headline`)?
- Findings schema versioning (for cache invalidation when new findings are added in later milestones).
- Ship templates-only first, or ship AI report in the same milestone?
- Whether to extend to Openings and Stats tabs in v1.11, or defer those to v1.12.
- How to surface multi-window and per-combo archetype outputs in the UI without overwhelming users — default to the richest window with "view more" disclosure, or always show all?
- Regime detection heuristic: 50/50 calendar split, 50/50 game-count split, or fixed date anchors? 50/50 calendar is simplest but skewed for users whose activity surged recently.
- Admin raw-data mode: does the comparison output (raw narrative vs findings narrative) justify a dedicated admin UI page, or is it a one-off internal tool invoked by API?
- Archetype stability vs reactivity: how many weeks of `recent_shift` before the archetype itself is reassigned vs flagged as a candidate?
- When `insufficient_data` is the archetype for all (combo × window) cells: emit nothing, emit a single "not enough data" summary, or emit per-cell `insufficient_data` findings so the user understands *which* filters produce coverage?

### Not in Scope

- **Per-game insights** ("your Rxh4 was inaccurate") — that's engine-analysis territory, separate milestone.
- **Benchmarks/percentiles against other users** — separate privacy + scale question, defer.
- **Player clustering across users** — a user's archetype is derived from their own data only, not by comparison to a population of users. Benchmark data (if used later) informs zone thresholds, not archetype assignment.
- **Bayesian changepoint / CUSUM** — defer to v1.12. The 50/50 heuristic is enough for v1.11.
- **LLM-driven archetype assignment** — archetype is deterministic (backend logic), not LLM-inferred. The LLM narrates, it does not classify.
- **Full statistical significance testing on trends** — trend-quality gating (weekly-point count + slope-to-volatility) is lightweight significance logic and is IN scope. p-values / confidence intervals as UI output are not.

## Breadcrumbs

### Sections that will receive Insights (Endgame tab)

- `frontend/src/components/charts/EndgamePerformanceSection.tsx` — Overall Performance section container
- `frontend/src/components/charts/EndgameScoreGapSection.tsx` — Score Gap + Endgame Skill composite (includes current `endgameSkill()` helper; Phase 56 will port to backend)
- `frontend/src/components/charts/EndgameTimePressureSection.tsx` — Time Pressure section container
- `frontend/src/components/charts/EndgameClockPressureSection.tsx` — clock-diff stats and timeline
- `frontend/src/components/charts/EndgameEloTimelineSection.tsx` — Endgame ELO timeline (Phase 57)

### Backend services that the Insights service will consume

- `app/services/endgame_service.py` — provides section-level stats, timeline data, and the `_compute_weekly_rolling_series` pattern used for trend detection
- `app/services/stats_service.py` — rating history and cross-section context
- `app/repositories/query_utils.py` — `apply_game_filters()` (insights must respect the same filter context)

### Related planning artifacts

- `.planning/phases/52-endgame-tab-performance/` — original endgame tab design
- `.planning/phases/53-endgame-score-gap-material-breakdown/` — Conversion/Parity/Recovery inputs to Endgame Skill
- `.planning/phases/54-time-pressure-clock-stats-table/` — Time Pressure section origin
- `.planning/phases/55-time-pressure-performance-chart/`
- `.planning/phases/57-endgame-elo-timeline-chart/57-CONTEXT.md` — design for Endgame ELO timeline
- `.planning/phases/57.1-endgame-elo-timeline-polish/` — polish phase for Endgame ELO timeline
- `.planning/quick/260418-nlh-add-endgame-skill-metric-as-simple-avera/260418-nlh-SUMMARY.md` — Endgame Skill composite decisions (45-55% blue band semantics, ~52% typical)
- `docs/endgame-analysis-v2.md` — overall endgame analytics spec; §5 min-sample-size convention (10 games)

### Project conventions the Insights feature must follow

- `CLAUDE.md` §Frontend — theme constants in `theme.ts`, `noUncheckedIndexedAccess`, mobile parity rule, `data-testid` rules
- `CLAUDE.md` §Coding Guidelines — type safety, ty compliance, no magic numbers, Literal types for enum-like strings
- `CLAUDE.md` §Communication Style — em-dash guidance applies to user-facing insight copy (tooltips, headlines, bullets)
- `CLAUDE.md` §Error Handling & Sentry — AI report endpoint must `capture_exception` on failures; skip trivial rate-limit exceptions

## Notes

- **Do not start before Phases 56 and 57 land.** Insights synthesize across the four Endgame sections, and the Endgame ELO section is the fourth. Without it, cross-section synthesis loses one of its strongest signals (the skill-vs-gap corroboration/divergence pattern). Phase 57 and 57.1 are complete as of 2026-04-19.
- **Reference chat context:** the full design discussion preceding this seed spans two threads — (1) original cost math, caching, schema sketch, and section → finding mapping table (2026-04-18); and (2) a refinement covering role taxonomy, archetype synthesis, temporal structure (multi-window + regime detection), material-adjusted precedence, disambiguation requirements, configurable model tier, and admin raw-data mode (2026-04-19). When v1.11 opens, `/gsd-discuss-phase` should start from this seed and expand open questions, not re-derive decisions already made.
- **MVP slicing recommendation:** ship templates-only in v1.11, but include the full findings schema (roles, confidence, temporal structure, archetype assignment, era comparison, admin weekly-data payload) from day one. Templates can render any subset of the schema at reduced fluency. Adding schema fields later requires re-running the findings cache and reworking template lookup tables — front-load the schema design, back-load the AI rendering.
- **Admin raw-data mode is a validation tool, not a feature.** Its purpose is to catch cases where the computed-findings pipeline misses something a strong model reading raw data would catch. Expect the first several runs to surface schema gaps; treat those as the primary deliverable of admin mode, not the narratives themselves. Plan for at least one iteration cycle where schema gaps identified via admin mode are fed back into the findings service.
- **Ground-truth test case:** the user profile from the 2026-04-19 discussion — endgame ELO +100 above actual, Score Diff +5pp, net clock-parity at endgame entry, skill-at-low-clock edge, archetype `grinder` with blitz specialization — is the canonical regression case. If the system can't produce a narrative matching the reasoning derived in conversation, the findings schema is underspecified. Encode this profile as a synthetic test fixture in the insights_service test suite.
