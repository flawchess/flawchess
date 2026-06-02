# Phase 102: Endgame LLM Statistical-Reasoning Rework (v1.23) - Context

**Gathered:** 2026-06-01
**Status:** Ready for planning

<domain>
## Phase Boundary

Upgrade the endgame-insights LLM **payload + prompt** so the model reasons over the
v1.17–v1.21 metric set with **percentile annotations** wired in (the page-level,
game-count-weighted value the chip shows) and **narrates time-pressure** (Score Gap by
Remaining Time, Clock Gap, Net Flag Rate). The metric *set* is already aligned with the
page, so this needs **ZERO new frontend cards** — it is payload + prompt only. Bump
`_PROMPT_VERSION` `endgame_v35` → `endgame_v36` (cache invalidation is automatic via the
cache key). UAT-dominated phase.

**Explicitly OUT of scope:**
- New frontend cards (the metric set is already displayed).
- Recommendations-section rework (deferred to `SEED-034`).
- Restoring the Phase 88.1-removed surfaces *on the page* (page is fine; payload-only).

</domain>

<decisions>
## Implementation Decisions

The full scope and the bulk of the locked decisions live in the `/gsd-explore` note
(`.planning/notes/v1.23-phase-102-endgame-llm-statistical-reasoning.md`) and
REQUIREMENTS LLM-01..07. This section records (a) the decisions that note explicitly
deferred to discuss-phase, now locked, and (b) a restatement of the load-bearing locks
so the planner does not have to re-derive them.

### Statistical depth in the payload
- **D-01 (CI bounds): OUT.** No confidence-interval fields are added to the payload, and
  the prompt does not teach CI recitation. Rationale: `sample_quality` (rich/adequate/thin)
  + `within-noise` + `[near edge]` markers already cover the precision/hedging dimension CI
  would inform; raw bounds push the model toward "95% CI [54%, 66%]" jargon that
  `feedback_popover_copy_minimalism` and `feedback_llm_prompt_design` steer away from. This
  finalizes the note's "LIKELY NO" recommendation and refines LLM-01/LLM-02 (their original
  CI-narration text is superseded — percentile is the committed statistical enrichment, CI
  is out).
- **D-02 (P-values): OUT.** Unchanged from the note — redundant with the zone band, conflicts
  with `feedback_llm_significance_signal`. No `p_value` / `verdict` fields in the payload.
- **D-03 (Percentiles): IN.** Per-metric percentile fields added to the payload for the
  in-scope v1.17/v1.19/v1.21 metric set, as non-breaking optional fields alongside the
  existing `zone` + `sample_quality`. Feed the **page-level, game-count-weighted** value
  (the same number the page-level chip shows) so the LLM and the chip agree.

### Percentile-as-gate guard (LLM-03)
- **D-04: Approach (a) locked — percentile-only enrichment under the zone gate.** The cohort
  `zone` field remains the **sole** gate on *whether* a metric is narrated. Percentile informs
  only *how* an already-gated narration is phrased. The prompt guard MUST state explicitly that
  an extreme percentile inside a `typical` zone does **not** open the gate or trigger narration
  — percentile is never a second significance signal. Preserves `feedback_llm_significance_signal`
  and `feedback_llm_prompt_design` (no precomputed stories). No parallel sig field is added
  (consistent with `feedback_llm_significance_signal`: tighten the cohort band, don't add a
  parallel `verdict`).
  - **⚠ REVERSED during execution (2026-06-01, user direction, Plan 102-04 / `endgame_v37`).**
    D-04 above is **superseded**. Percentile is now a **primary, preferred** narration signal:
    a metric is narratable when EITHER its `zone` is non-typical OR its `pctl` is extreme
    (`< 25` or `> 75`) AND `quality` is `adequate`/`rich`. When a percentile exists, the prompt
    LEADS with percentile framing (cohort-relative — vs equally-strong peers) and uses zone as
    supporting context. Rationale: percentile controls for rating where the zone does not.
    D-01/D-02 (no CI, no p-values) and D-05 (cohort framing) are unchanged; the percentile is
    still not a *statistical-test* signal, so the spirit of `feedback_llm_significance_signal`
    (no `p_value`/`verdict` field) holds. Also enriched: each `pctl=` now carries the rating
    anchor + `n_games` + `value`, and coverage extended from {score_gap, achievable_score_gap}
    to all 11 percentile-bearing metrics. See `feedback_percentile_primary_narration_signal`.
- **D-05 (cohort framing): match the chips.** Where percentile is woven into narration, use
  cohort framing ("vs other ~{anchor}-rated players"), NOT global-pool framing — consistent
  with `feedback_percentile_chip_tooltip_disclosure` and the chip tooltip copy.
- **D-05a (added during execution 2026-06-01, user direction, Plan 102-05 / `endgame_v38`):
  the anchor is Lichess-equivalent.** `user_rating_anchors.anchor_rating` is a game-weighted
  median of converted-chess.com (Glicko-1 → typically-higher Lichess Glicko-2 scale) + native
  lichess ratings. chess.com-heavy users were confused at being compared to higher-numbered
  peers. Payload now exposes the per-TC platform composition (`RatingAnchorContext`: anchor +
  n_chesscom/n_lichess games + chesscom/lichess native medians) via a rendered `## Rating basis`
  block; the prompt teaches a ONE-TIME chess.com→Lichess conversion clarification mirroring the
  four `PercentileChipPopoverBody` disclosure branches (pure-cc / mixed / pure-lichess / suppressed),
  so pure-lichess users get no conversion note. Consistent with `feedback_percentile_chip_tooltip_disclosure`
  and D-10. See `[[feedback_percentile_primary_narration_signal]]`.

### Time-pressure narration
- **D-06: Time-pressure metrics get percentile annotations where available, granularity-matched.**
  The three surfaces to narrate are **Score Gap by Remaining Time** (the per-bucket decomposition
  Phase 88.1 stripped — the genuine payload add), **Clock Gap** (`avg_clock_diff_pct`), and
  **Net Flag Rate** (`net_timeout_rate`). For metrics that carry a v1.19 TPCTL percentile,
  include it under the same zone gate. **Framing matches the surface granularity:** per-TC
  narration uses the chip's **direct per-TC TPCTL** (no game-count weighting); any page-aggregated
  metric uses the **game-count-weighted** value, consistent with D-03. Same zone-as-gate rule
  (D-04) applies — percentile never opens the gate.
- **D-07 (plan-time verification, NOT a decision to re-ask):** Before wiring, confirm against
  live code: (1) which of the three time-pressure metrics already carry scalars vs need the
  per-bucket Score-Gap-by-time decomposition added; (2) which carry TPCTL and at what
  granularity they are narrated; (3) the actual bucket count of "Score Gap by Remaining Time"
  (the note flags 4 vs 5 quintiles — `time-pressure-stats-rework.md` says 5, the user said 4;
  verify against the live chart). Do not trust prior-agent summaries — the `/gsd-explore`
  agent's payload/frontend mapping was wrong twice (see the note's "Lesson for planning").

### Data Analysis (`overview` field) length policy
- **D-08: Relax the cap with a signal-gated ceiling.** Current cap is "1-3 short paragraphs,
  ~300 words" (`app/prompts/endgame_insights.md:9` and `:190`). New policy:
  - **Default stays concise** (~250-300 words) for typical reports.
  - The model **MAY** extend to **up to ~500 words / up to 5 short paragraphs** *only when ≥3
    distinct, non-overlapping narratable signals exist* (e.g. an overall-gap story + a
    time-pressure story + a type-weakness story, each in a non-typical zone). More metrics in
    the payload (percentiles + time-pressure) = more legitimately to say.
  - **All existing guards preserved:** silence-is-not-valid, no-fabrication, within-noise,
    flat-trend. This is permission to go longer when warranted, NOT a mandate to pad. Weak or
    redundant paragraphs are still forbidden.
  - Consistent with `feedback_llm_prompt_design` ("longer overviews OK") and the 2026-06-01
    ROADMAP note ("allow longer Data Analysis narration").

### Prompt version + cache
- **D-09: Bump `_PROMPT_VERSION` `endgame_v35` → `endgame_v36`.** Cache invalidation is automatic
  via the `_PROMPT_VERSION` cache key in `app/services/insights_llm.py`. Do NOT retroactively
  invalidate prior cached reports beyond that mechanism (preserves LLM-06 / backwards compat).

### Vocabulary audit scope
- **D-10: Audit the system prompt's UI-vocabulary mapping against BOTH surfaces.** (a) the
  Endgame Statistics Concepts accordion in `frontend/src/pages/Endgames.tsx` (~382–580, the
  authoritative label/definition source), AND (b) the tooltip info-icon popover bodies
  (`MetricStatPopover`, `WdlConfidenceTooltip`, `EvalConfidenceTooltip`, `AchievableScorePopover`,
  the percentile-chip tooltip). The LLM must narrate with the same terms and sign conventions the
  tooltips explain, so the report and the hover-help never contradict each other.

### Claude's Discretion
The user delegated all four discuss-phase decisions ("the provided info should be enough to
let you make an informed decision"). D-01, D-04, D-06, and D-08 above are the resolutions of
those four deferred decisions, locked to the `/gsd-explore` note's recommendation where it gave
one (CI out, approach-a) and to a concrete, guard-preserving call where it asked for specifics
(time-pressure framing, overview length). The planner has normal latitude on implementation
mechanics (payload field names, prompt prose structure) as long as these decisions hold.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Scope + locked decisions (read FIRST)
- `.planning/notes/v1.23-phase-102-endgame-llm-statistical-reasoning.md` — the durable
  `/gsd-explore` scoping record; overrides the stale assumptions in the original
  REQUIREMENTS LLM-01..07 text. Contains the "Lesson for planning" (re-verify all
  present/absent-in-payload claims against live code).
- `.planning/REQUIREMENTS.md` LLM-01..07 — phase requirements (refined 2026-06-01; this
  CONTEXT.md's D-01 further narrows LLM-01/02 to drop CI).
- `.planning/notes/time-pressure-stats-rework.md` — Phase 88 time-pressure design; its
  "LLM narration = future phase" deferral is now Phase 102. Source for the Score-Gap-by-time
  bucket structure (verify count at plan time).

### Backend — payload, prompt, findings, zones (the surface being changed)
- `app/services/insights_llm.py` — `_PROMPT_VERSION`, `_assemble_user_prompt()`,
  `_SECTION_LAYOUT`. Where the percentile + time-pressure payload additions and the version
  bump land.
- `app/prompts/endgame_insights.md` — the system prompt. `overview` cap at lines 9 + 190;
  the field is rendered as the "Data Analysis" card. Where the vocabulary audit + length
  relaxation + percentile/time-pressure narration teaching land.
- `app/services/insights_service.py` — `compute_findings()`; per-type conv/recov narration
  consumer (`_findings_conversion_recovery_by_type`).
- `app/services/endgame_zones.py` — `MetricId`, `ZONE_REGISTRY`, `BUCKETED_ZONE_REGISTRY`,
  `assign_per_class_zone`. The zone gate registry.
- `app/routers/insights.py` — `POST /api/insights/endgame` endpoint.

### Percentile data source (already on the API, LLM-05 consumes)
- v1.19 PCTL/TPCTL/PRPCR fields + v1.21 per-(metric, TC) cohort percentiles
  (`benchmark_cohort_cdf` table). Confirm shape at plan time.
- `reports/benchmarks-latest.md` — source of truth for "typical" / normative copy
  (`feedback_benchmark_source_of_truth`).

### Frontend — vocabulary + render targets (read-only for this phase; NOT modified)
- `frontend/src/pages/Endgames.tsx` concepts accordion (~382–580) — authoritative vocabulary
  source for the audit.
- Tooltip popover bodies: `MetricStatPopover`, `WdlConfidenceTooltip`, `EvalConfidenceTooltip`,
  `AchievableScorePopover`, percentile-chip tooltip — second audit surface (D-10).
- `frontend/src/components/insights/EndgameInsightsBlock.tsx` — renders the three stacked
  cards: Player Profile, **Data Analysis** (`:286`, = `overview`), Recommendations.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **`_PROMPT_VERSION` cache key** (`insights_llm.py:69`) — bumping the constant is the entire
  cache-invalidation mechanism; no manual cache purge needed (D-09).
- **`sample_quality` / `within-noise` / `[near edge]` markers** — already in the payload;
  these are the precision/hedging signals that make CI bounds redundant (D-01).
- **Zone registry + `assign_per_class_zone`** (`endgame_zones.py`) — the existing gate; percentile
  layers on top without touching the gate logic (D-04).
- **v1.19/v1.21 percentile fields already on the API** — LLM-05 consumes existing data; the work
  is plumbing them into the payload + teaching the prompt, not computing new percentiles.

### Established Patterns
- **Zone band is the significance signal, never a parallel field** — every prior version (v29,
  v31, v33+) explicitly refused to add `p_value` / `verdict`. D-02/D-04 continue this.
- **Dual-label terminology + glossary lockstep** — prompt prose, chart titles, and popover copy
  are kept in sync on every version bump; the D-10 audit is the formalized version of this.
- **Versioned prompt changelog** — `_PROMPT_VERSION`'s inline comment carries a full per-version
  history; v36 must append its rationale in the same style.

### Integration Points
- Percentile + time-pressure additions enter via `_assemble_user_prompt()` (payload) and
  `endgame_insights.md` (prompt teaching). No frontend, no DB schema, no new endpoint.

</code_context>

<specifics>
## Specific Ideas

- The `overview` → "Data Analysis" card length relaxation (D-08) is the user-visible behavior
  change most likely to need UAT tuning — budget a UAT pass specifically checking that longer
  narration only fires when warranted (≥3 distinct signals) and does not pad on sparse users.
- Time-pressure "Score Gap by Remaining Time" is the only genuine *new* payload structure (the
  per-bucket decomposition Phase 88.1 stripped); Clock Gap + Net Flag Rate scalars may already
  be present — verify (D-07).

</specifics>

<deferred>
## Deferred Ideas

- **Recommendations-section rework** — captured as `SEED-034-endgame-llm-recommendations-rework.md`.
  Explicitly NOT in Phase 102 scope.
- **Restoring Phase 88.1-removed surfaces on the page** — not needed; the page is fine, this phase
  is payload-only.

</deferred>

---

*Phase: 102-endgame-llm-statistical-reasoning-rework-v1-23*
*Context gathered: 2026-06-01*
