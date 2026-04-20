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

The Endgame tab already surfaces a lot of data (the Games-with-vs-without-Endgame table with its Score Gap column, the Endgame Metrics section with Conversion / Parity / Recovery gauges and the Endgame Skill composite, Time Pressure vs Performance, Time Pressure at Endgame Entry + clock-diff timeline, Results by Endgame Type, Conversion & Recovery by Endgame Type, and in v1.10 the new Endgame ELO Timeline from Phases 56/57). Users see the numbers but still have to synthesize conclusions themselves: is this area good or bad for me, is it improving, and crucially — how do these sections relate to each other?

A glanceable Insights section per tab (headline + 2 bullets) translates the numbers into plain-language findings, tailored to the active filters (recency, opponent strength, color, etc.). Filters reshape the data more than anything else on the page, so insights have to reflect them or they're misleading.

The bigger payoff comes from cross-section synthesis: a user with poor endgame skill AND poor time pressure stats probably has a time management problem, not an endgame technique problem. Templates can't naturally derive that inversion; an LLM handed structured findings from every section can. That's the feature that makes FlawChess more than a stats dashboard.

Second-order payoff: cross-section reasoning is *hard*, even for data scientists. A live design discussion walked through one real user whose Endgame ELO (chess.com Blitz combo) sat +100 above Actual ELO while their raw Score Gap stayed neutral (+5pp). Reconciling the two required reasoning about material-adjustment (the Conversion / Parity / Recovery split behind Endgame Skill), selection effects, baseline-lift confounds, and skill-at-clock-level vs clock-entry-advantage. An untrained user will not reach that conclusion unaided. The insights pipeline is explicitly designed to encode this kind of reasoning deterministically.

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
2. Per-section findings implementations (7 sections on the Endgame tab — see "Sections in Scope" below) with multi-window computation (`all_time`, `last_1y`, `last_3mo`) and trend-quality gating
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

Conventions pinned from the current UI (the schema below depends on these):

- **Score Gap** (`metric="score_gap"`) = (user's endgame Score %) − (user's non-endgame Score %). It's a within-user comparison, NOT user vs opponent. The UI popover on "Games with vs without Endgame" spells this out: "a positive value can mean stronger endgames *or* weaker non-endgame play." Insight copy must not contradict that.
- **Endgame Skill** (`metric="endgame_skill"`) = simple average of Conversion Win %, Parity Score %, Recovery Save % over the scope. Material-stratified by construction. 45–55% is the typical band (`~52%` median, per the skill-cohort calibration referenced in `docs/endgame-analysis-v2.md`).
- **Endgame ELO** (`metric="endgame_elo"`) = `actual_elo + 400 · log10(skill / (1 − skill))` where `skill` is Endgame Skill over the user's **trailing 100 endgame games** in a specific (platform, time control) combo. Computed per combo only — Glicko-1 (chess.com) and Glicko-2 (lichess) scales aren't comparable, so aggregating across platforms is meaningless.
- **Endgame ELO gap** (`metric="endgame_elo_gap"`) = Endgame ELO − Actual ELO. This is **the same signal as Endgame Skill for a single combo**, just expressed in ELO units. It is NOT independent evidence — treat them as one observation when counting archetype corroboration.
- **Avg clock diff** (`metric="avg_clock_diff_at_endgame"`) = (user's avg clock %) − (opponent's avg clock %), as % of base time, measured at endgame entry. UI neutral band is **±10%** (`CLOCK_DIFF_NEUTRAL_PCT = 10`).
- **Net timeout rate** (`metric="net_timeout_rate"`) = (timeout wins − timeout losses) / total endgame games.
- **Diff vs opponent in mirror bucket** (`metric="<bucket>_diff_vs_opp"` for `conversion` / `parity` / `recovery` / `endgame_skill`) = user's rate − opponents' rate in the symmetric material situation. Distinct signal from Score Gap; UI Diff column colors ±5pp neutral.
- **Time-pressure skill edge** (`metric="time_pressure_skill_edge_low_clock"`) = My Score % − Opponent's Score % aggregated over low-base-time buckets (% of base time remaining at endgame entry). UI chart: "Time Pressure vs Performance".
- **Neutral-band constants** (documented for phrase-library lookup): `CLOCK_DIFF_NEUTRAL_PCT = 10` (Avg clock diff, clock-diff timeline), `SCORE_DIFF_NEUTRAL_PP = 5` (Score Gap, per-bucket Diff, per-type Diff).
- **All-time prefilled, pre-recency lookback (the rolling-100 timelines).** The three rolling timelines in `endgame_service.py` — `SCORE_GAP_TIMELINE_WINDOW`, `CLOCK_PRESSURE_TIMELINE_WINDOW`, `ENDGAME_ELO_TIMELINE_WINDOW`, all set to 100 — deliberately call the data layer with `recency_cutoff=None` and filter the output series by date *after* computing the rolling means (`endgame_service.py:1711-1731`, `:1809-1828`). Every timeline point in a `last_3mo` view has already consumed up to 100 earlier games from the user's full history. **Non-recency filters DO propagate into the lookback** (time_control, platform, rated, opponent_type, opponent_strength, elo_threshold), so "stronger opponents + last 3mo" means the 100-game lookback is over stronger-opponents games only, reaching back in calendar time until 100 such games are found. Any finding derived from these timelines therefore inherits an "all-time-prefilled, pre-recency" lookback that cannot be flipped off; the temporal `window` controls only which timeline points are *visible*, not which games *feed* each point. Non-timeline section findings (Endgame Skill zone, raw Score Gap, per-bucket Diff vs mirror bucket, per-type Diff) do NOT have this property — they recompute cleanly from within-window games. This distinction matters throughout the schema (see `LookbackBehavior` below) and for how short-window confidence is driven (see Temporal Structure § short windows).

```python
Zone = Literal["very_weak", "weak", "typical", "strong", "very_strong"]
Trend = Literal["improving", "declining", "stable", "volatile", "n_a"]
SampleQuality = Literal["rich", "adequate", "thin", "insufficient"]
Severity = Literal["headline", "supporting", "aside"]
Confidence = Literal["high", "medium", "low"]
Window = Literal["all_time", "last_1y", "last_3mo"]
LookbackBehavior = Literal[
    "window_bounded",               # metric recomputes cleanly from
                                    # within-window games only (e.g.,
                                    # endgame_skill zone, score_gap value,
                                    # per-bucket diff vs mirror bucket,
                                    # per-type diff).
    "all_time_prefilled_pre_recency"  # metric comes from a rolling-100
                                    # timeline fetched with
                                    # recency_cutoff=None; each point's
                                    # lookback reaches back in calendar time
                                    # until 100 qualifying games are found.
                                    # Non-recency filters (tc, platform,
                                    # opponent_strength, etc.) still apply
                                    # to the lookback. Applies to
                                    # endgame_elo, endgame_elo_gap, and
                                    # trend findings derived from the
                                    # Score Gap timeline or the clock-diff
                                    # timeline.
]
StabilityPattern = Literal[
    "stable", "evolving", "recent_shift", "insufficient_data"
]
CrossSectionRole = Literal[
    "effect",              # what's happening (e.g., endgame_elo_gap +100 in chess.com Blitz)
    "mechanism",           # why (e.g., skill at low-base-time buckets)
    "confound_ruled_out",  # what it's NOT (e.g., not a clock-entry advantage)
    "confound_present",    # why the naive metric misleads (e.g., baseline-lift on Score Gap)
    "corroboration",       # INDEPENDENT measurements agreeing — note: for a
                           # single combo, endgame_skill and endgame_elo_gap
                           # are NOT independent (same signal, different units)
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
    "lookback_dominated_by_prior_period",  # for all_time_prefilled_pre_recency
                                            # metrics when the trailing-100
                                            # lookback is >50% older than the
                                            # recency window — downgrade the
                                            # finding and attach the
                                            # "reflects older play" caveat.
    "few_weekly_points_in_window",          # for timeline-derived findings:
                                            # confidence depends on how
                                            # many weekly samples landed
                                            # INSIDE the recency window,
                                            # not on raw game count.
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
    combo: tuple[str, str] | None = None   # (platform, tc) when finding is
                                           # per-combo (endgame_elo,
                                           # endgame_elo_gap). None otherwise.
    lookback_behavior: LookbackBehavior    # whether the metric is cleanly
                                           # window-bounded or comes from
                                           # an all-time-prefilled rolling
                                           # timeline — drives confidence
                                           # modelling and the "most of the
                                           # lookback is outside your
                                           # selected window" caveat.
    lookback_in_window_pct: float | None = None  # only for
                                           # all_time_prefilled_pre_recency
                                           # findings: of the games that
                                           # fed the latest timeline point
                                           # in the window, what fraction
                                           # were played inside the window.
                                           # Below ~50% triggers the
                                           # lookback-dominance caveat.

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
    section_id: Literal[
        "overall",                      # Games with vs without Endgame
        "endgame_metrics",              # Conv / Parity / Recovery + Endgame Skill gauges
        "time_pressure_vs_performance", # My Score % vs Opp Score % by % base time
        "time_pressure_at_entry",       # Avg clock diff, Net timeout rate, clock-diff timeline
        "endgame_elo_timeline",         # per-combo Endgame ELO vs Actual ELO
        "results_by_endgame_type",      # WDL + You/Opp/Diff per type
        "conversion_recovery_by_type",  # Conversion & Recovery rates per type
    ]
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
- **Regime detection (v1.11 heuristic, v1.12 statistical).** For users with 2+ years of history: split the Endgame Skill timeline in half by calendar. If means differ by >5pp and ranges don't overlap, emit an era-comparison finding and label the earlier window an "earlier era." Defer Bayesian changepoint / CUSUM to v1.12 — the heuristic is enough for most cases.
- **Rolling-timeline lookback is pre-recency by design.** The three 100-game rolling timelines (Score Gap, clock-diff, Endgame ELO) always prefill from all-time history and only filter the *output* by recency cutoff. Findings derived from these timelines (`endgame_elo`, `endgame_elo_gap`, Score-Gap-timeline trends, clock-diff-timeline trends) are tagged `lookback_behavior="all_time_prefilled_pre_recency"` and must be handled differently from window-bounded section findings:
  - **Computation.** Take a temporal statistic of the pre-existing in-window timeline points (latest point for a zone finding, first-vs-last delta for a trend finding, median for a stability check). Do NOT recompute the metric from within-window games only — that would disagree with what the user sees on the tab.
  - **Confidence.** The sample-quality driver is how many weekly points the timeline emits *inside* the recency window (`few_weekly_points_in_window`), not raw endgame-game count inside the window. A user with 150 endgame games in the last 3 months but no qualifying weekly points (e.g. split across combos thinly) has thin timeline coverage despite a healthy game count.
  - **Lookback-dominance caveat.** When the latest in-window timeline point's 100-game lookback is more than ~50% played BEFORE the recency window opens (tracked via `lookback_in_window_pct < 0.5`), attach the `lookback_dominated_by_prior_period` driver and downgrade confidence. Insight copy must say something like "most of this number reflects play from before your selected window" rather than reporting the Endgame ELO gap as a fresh observation.
  - **Filter propagation.** The lookback IS filter-bounded on non-recency dimensions. So "stronger opponents + last 3mo" Endgame ELO is built from up to 100 prior games against stronger opponents — which can reach back years for selective filters. Insight copy for tight filter combinations should acknowledge this.

The result: the pipeline produces the right kind of output for both extremes.

- **5-year history**: "you've been a technician since 2023; earlier era (2020-2022) shows a different archetype. Here's what changed."
- **6 months with 80 games**: "zone assignments at medium confidence; trend claims suppressed; tentative archetype based on recent window only."

### Archetype Synthesis

Archetype assignment is deterministic so it's auditable and stable across reports. Each archetype is defined by a signature pattern of findings:

| Archetype | Signature |
|---|---|
| `technician` | high **Endgame Skill** (zone ≥ `strong`) + modest/negative **Score Gap** (baseline-lift signature) + Endgame Skill behaves consistently across the user's active (platform, tc) combos. Endgame ELO gap is the same signal restated in ELO units, not an independent corroboration. |
| `tactician` | neutral/weak **Endgame Skill** + positive **Score Gap**. Implies non-endgame play is pulling score up while endgame technique is unremarkable. |
| `grinder` | positive **Parity (Score %)** + positive **Recovery (Save %)** vs mirror bucket + positive **time-pressure skill edge at low-base-time buckets** + clock-entry parity (|Avg clock diff| ≤ 10%). |
| `time_cracker` | **My Score %** >> **Opponent's Score %** at low-base-time buckets (Time Pressure vs Performance), regardless of Parity / Recovery. |
| `clock_hoarder` | user enters endgames with materially more clock than opponents (**Avg clock diff > +10%**, outside the UI neutral band); score advantage concentrated in low-opponent-clock buckets. |
| `solid_all_around` | all zones typical, no strong directional findings |
| `underperformer` | negative Endgame Skill AND negative Score Gap (both signals pointing weak — no need to double-count with Endgame ELO gap). |
| `insufficient_data` | sample_quality is `thin` or `insufficient` for any load-bearing section |

Each archetype maps to:

- **Narrative framing** (phrase library): e.g. "You're a technician — strong endgame technique relative to your rating."
- **Practical advice**: e.g. "Your improvement path likely runs through openings and middlegame, not more endgame study."
- **Evidence links**: list of `Finding.id`s that justify the assignment.

When multiple archetypes could apply per (combo × window), pick the one with the highest confidence and emit the runner-up as a supporting finding (e.g., "also shows signs of `time_cracker` in blitz specifically").

### Material-Adjusted Precedence

**Endgame Skill** is material-stratified by construction (it's the average of Conversion / Parity / Recovery rates). **Score Gap** is not — it's the raw endgame Score % minus non-endgame Score %, with no control for material balance at endgame entry. When the two disagree:

- **Agree in direction, disagree in magnitude** (e.g., Endgame Skill in the `strong` zone → Endgame ELO gap per combo ~+100, but Score Gap only +5pp): Endgame Skill is primary. Score Gap is framed as "consistent but muted due to skill lifting both the endgame and non-endgame baselines" — emit a `confound_present` cross-section finding explaining the baseline-lift effect. This mirrors exactly the caveat in the UI's own Score Gap popover, so the insight does not contradict the page.
- **Disagree in direction**: high-severity caveat. One is wrong or the sample is unstable — emit a `caveat` finding and downgrade archetype confidence.

This prevents templates from writing "your endgames are about the same as your non-endgame play" (a reading of a near-zero Score Gap) when the material-stratified truth is "your endgame technique is above your rating level, but your non-endgame baseline is also strong, which mutes the raw gap."

### Disambiguation Requirements

Certain findings are prone to obvious misinterpretations. The insights_service must mechanically check paired findings before emitting them:

- **"Handles time pressure better"**: before emitting, check **Avg clock diff at endgame entry** (Time Pressure at Endgame Entry section). If Avg clock diff > +10% of base time (outside the UI's `NEUTRAL_PCT_THRESHOLD`), frame as "both composure and clock-management edge." If within ±10% (UI neutral band), frame as "composure edge only — you don't arrive with more time, but you play better when time is short." Never conflate the two. The ±10% threshold must match the UI so insight copy agrees with what users see on the page.
- **"Endgame is a strength"**: before emitting, confirm **Endgame Skill** zone is `strong` or `very_strong`. Raw **Score Gap** alone is insufficient (fails the baseline-lift check) — and the UI's own Score Gap popover already explicitly warns of this ambiguity, so the insight must not contradict the UI caveat.
- **"Improving over time"**: before emitting, confirm trend-quality gate passed (≥20 weekly points, slope-to-volatility above threshold). Applies per-section, including to the clock-diff timeline and the Endgame ELO timeline. Otherwise emit `direction="n_a"` instead.
- **Rolling-timeline findings in a short window**: before emitting any `lookback_behavior="all_time_prefilled_pre_recency"` finding (Endgame ELO, Score-Gap-timeline trend, clock-diff-timeline trend) for a non-`all_time` window, compute `lookback_in_window_pct` for the latest in-window timeline point. If <50%, downgrade confidence and prepend the `lookback_dominated_by_prior_period` caveat ("reflects mostly pre-window play"). Never let the LLM or template imply this is a fresh-period measurement.

These checks are deterministic and belong in the backend — not in the LLM prompt. LLMs will otherwise get this wrong (this was empirically demonstrated in the design discussion).

### Sections in Scope

Seven user-visible sections on the Endgame tab. (The seed originally undercounted at four by grouping by container component; the user-visible section list is what drives the insights pipeline because that's what the tab's own info popovers define and what insight copy must reference.) Each section's findings are computed per window (`all_time`, `last_1y`, `last_3mo`):

| Section (`section_id`) | UI heading | Headline candidates | Supporting |
|---|---|---|---|
| `overall` | Games with vs without Endgame | `score_gap` zone & sign (window-bounded), with baseline-lift caveat if Endgame Skill is strong/very_strong | Endgame vs non-endgame Score % rows, sample volume. Score-Gap-*timeline* trend, if emitted, is `all_time_prefilled_pre_recency`. |
| `endgame_metrics` | Endgame Metrics | `endgame_skill` zone (composite), strongest/weakest of `conversion` / `parity` / `recovery` | Per-bucket gauges vs fixed skill-cohort target band, per-bucket `_diff_vs_opp` (mirror bucket), skill trend |
| `time_pressure_vs_performance` | Time Pressure vs Performance | `time_pressure_skill_edge_low_clock` zone (My Score % vs Opponent's Score % at low base-time buckets) | Shape of the My / Opponent curves across base-time buckets, dot-size / sample-size caveats |
| `time_pressure_at_entry` | Time Pressure at Endgame Entry | `avg_clock_diff_at_endgame` zone (±10% neutral band, window-bounded), `net_timeout_rate` zone | Per-time-control breakdown. Clock-diff *timeline* trend is `all_time_prefilled_pre_recency` and subject to the lookback-dominance caveat. |
| `endgame_elo_timeline` (Phases 56+57) | Endgame ELO Timeline | Per-combo `endgame_elo_gap` (always carries `combo`; `all_time_prefilled_pre_recency` lookback), divergence between Actual and Endgame ELO trajectories | Cross-combo consistency of Endgame Skill, era comparison when 2+ years of history, `lookback_dominated_by_prior_period` / `few_weekly_points_in_window` caveats |
| `results_by_endgame_type` | Results by Endgame Type | Weakest & strongest type buckets (N ≥ threshold) using You vs Opp Diff (±5pp neutral band) | Most frequent type, caveat that a game can count toward multiple types |
| `conversion_recovery_by_type` | Conversion & Recovery by Endgame Type | Type-specific Conversion or Recovery outliers | Asymmetries between Conversion and Recovery within a type |

### Cross-Section Synthesis (where the LLM earns its keep)

Every cross-section finding carries a `role` so the LLM narrates a pre-structured causal graph instead of rediscovering it:

- **Effect (`role=effect`)**: "Endgame ELO gap ~+100 above Actual ELO in chess.com Blitz (combo-tagged)" — the headline observation. Always carries the combo tag for Endgame ELO findings.
- **Mechanism (`role=mechanism`)**: "My Score % > Opponent's Score % at low-base-time buckets (Time Pressure vs Performance)" — why the effect exists.
- **Confound ruled out (`role=confound_ruled_out`)**: "Avg clock diff at endgame entry is within ±10% — user does NOT enter endgames with materially more clock" — preempts the obvious alternative explanation.
- **Confound present (`role=confound_present`)**: "Non-endgame baseline is also elevated, so raw Score Gap understates the true endgame edge" — explains why a naive metric lies.
- **Corroboration (`role=corroboration`)**: **INDEPENDENT** signals agreeing — e.g. Endgame Skill behaves similarly across the user's active (platform, tc) combos (cross-combo consistency), OR a strong Endgame Skill zone agrees in direction with a positive per-bucket `_diff_vs_opp` in the same bucket. Do NOT treat Endgame Skill and Endgame ELO gap in the same combo as independent — they are algebraically the same signal.
- **Null signal (`role=null_signal`)**: a neutral/typical value that matters *because* it rules a mechanism out. Must be emitted, not suppressed.

**Worked example** (the real user profile from the design discussion): Endgame Skill ≈ 64% (chess.com Blitz), Endgame ELO ~100 above Actual ELO in that combo, Score Gap +5pp, positive time-pressure skill edge at low-base-time buckets, Avg clock diff within ±10%. Findings graph:

1. `effect`: "Endgame Skill ≈ 64% (chess.com Blitz) → Endgame ELO sits ~100 above Actual ELO in the same combo (same signal, ELO units)"
2. `mechanism`: "My Score % > Opponent's Score % at low-base-time buckets (Time Pressure vs Performance chart)"
3. `confound_ruled_out`: "Avg clock diff at endgame entry within ±10% — no clock-entry advantage"
4. `confound_present`: "Strong non-endgame baseline mutes the raw Score Gap (+5pp reads neutral but is consistent with a real endgame edge)"
5. `corroboration` (across combos, not skill-vs-ELO-gap): "Endgame Skill is similarly elevated in blitz and rapid — the edge isn't a bullet-only artifact"
6. Archetype: `grinder` with blitz specialization — confidence backed by cross-combo consistency and the ruled-out clock-entry confound

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
- **Rolling-timeline temporal statistic per window.** For `lookback_behavior="all_time_prefilled_pre_recency"` findings (Endgame ELO, Score-Gap-timeline trend, clock-diff-timeline trend), a `last_3mo` finding has to pick a representative statistic of the in-window timeline points: latest point, median, first-vs-last delta (for trend), or a blend. Latest point is most aligned with "what does the user see today?" but can be noisy; median is smoother but lags real changes. Pick one rule per `kind` (zone / trend / stability) and document it.
- **Per-combo Endgame Skill.** The Endgame ELO timeline already computes Endgame Skill per combo (trailing-100). Should the `endgame_metrics` section also expose per-combo Endgame Skill findings (so cross-combo consistency is its own first-class finding), or should the consistency signal be derived from the timeline?
- **Headline severity when Score Gap and Endgame ELO disagree within one combo.** Endgame ELO is material-stratified (Endgame Skill under the hood); Score Gap is not. Material-Adjusted Precedence says Endgame Skill wins on magnitude — but Score Gap is visible higher on the page. Should the insight headline lead with what's visually prominent (Score Gap) and caveat with material-adjusted reality, or lead with the material-adjusted truth and explain away the visible number?

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

- **Do not start before Phases 56 and 57 land.** Insights synthesize across the Endgame tab's sections, and the Endgame ELO Timeline is one of them — without it, cross-section synthesis loses the Endgame-Skill-in-ELO-units framing and the per-combo consistency signal that backs several archetypes. Phase 57 and 57.1 are complete as of 2026-04-19.
- **Reference chat context:** the full design discussion preceding this seed spans two threads — (1) original cost math, caching, schema sketch, and section → finding mapping table (2026-04-18); and (2) a refinement covering role taxonomy, archetype synthesis, temporal structure (multi-window + regime detection), material-adjusted precedence, disambiguation requirements, configurable model tier, and admin raw-data mode (2026-04-19). When v1.11 opens, `/gsd-discuss-phase` should start from this seed and expand open questions, not re-derive decisions already made.
- **MVP slicing recommendation:** ship templates-only in v1.11, but include the full findings schema (roles, confidence, temporal structure, archetype assignment, era comparison, admin weekly-data payload) from day one. Templates can render any subset of the schema at reduced fluency. Adding schema fields later requires re-running the findings cache and reworking template lookup tables — front-load the schema design, back-load the AI rendering.
- **Admin raw-data mode is a validation tool, not a feature.** Its purpose is to catch cases where the computed-findings pipeline misses something a strong model reading raw data would catch. Expect the first several runs to surface schema gaps; treat those as the primary deliverable of admin mode, not the narratives themselves. Plan for at least one iteration cycle where schema gaps identified via admin mode are fed back into the findings service.
- **Ground-truth test case:** the user profile from the 2026-04-19 discussion — Endgame Skill ≈ 64% (chess.com Blitz combo), Endgame ELO ~100 above Actual ELO in that combo, Score Gap +5pp, Avg clock diff within ±10% (no clock-entry advantage), positive time-pressure skill edge at low-base-time buckets, cross-combo consistency of Endgame Skill across blitz/rapid, archetype `grinder` with blitz specialization — is the canonical regression case. If the system can't produce a narrative matching the reasoning derived in conversation (including correctly *not* double-counting Endgame Skill and the Endgame ELO gap as separate corroboration), the findings schema is underspecified. Encode this profile as a synthetic test fixture in the insights_service test suite.
