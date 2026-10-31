# Phase 243: Out of the Opening Worse/Better Rates (SEED-206) - Context

**Gathered:** 2026-10-31
**Status:** Ready for planning

<domain>
## Phase Boundary

The phase answers "compared to players at my level, how solid am I out of the opening?" with a new "Out of the
opening" section at the top of the Openings Stats tab. It ranks two rates against rating × TC peer CDFs: the share
of games the user leaves the opening clearly worse (primary) and clearly better (secondary). It shows one
game-weighted value per colour for the colour selected in the sticky White | Black switch.

The backend comes first: a canonical-slice builder, CDF regeneration, the Stage B per-user family, the ranked read
path and a parity test. The frontend follows: the section card and its popover.

Out of scope: per-opening worse/better bars in the repertoire expanded card, LLM narration, and a histogram in the
popover (see D-09).

</domain>

<decisions>
## Implementation Decisions

The locked decisions in SEED-206 (`.planning/seeds/SEED-206-out-of-the-opening-worse-better-rates.md`) carry over
verbatim and are summarised here so the planner has them in one place. This discussion settled the seed's open
questions and dropped the popover histogram.

### Metric (from SEED-206, locked)
- **D-01:** Value = the user-POV eval at the first middlegame ply minus the colour baseline
  (`EVAL_BASELINE_PAWNS_WHITE` +0.25, `EVAL_BASELINE_PAWNS_BLACK` −0.25 in
  `app/services/opening_insights_constants.py`).
  - **Worse** if ≤ −1.0, **better** if ≥ +1.0. A mate score counts by its sign.
  - The ±1.0 cut is a named constant, never a bare literal.
- **D-02:** A game that ends before the middlegame counts by result when it ends by resignation, checkmate or
  timeout (a loss counts as worse, a win as better). Abandoned games and draws are excluded.
- **D-03:** Copy says "eval", never "pawns". For example: "an eval 1.0 or more below a typical opening position".

### Peer basis and CDF shape
- **D-04 (discussed):** **One CDF per TC per rate, pooled over colours.**
  - Each benchmark peer contributes one point per colour × TC that passes the floor, so up to 2 points per TC.
  - Both colours are ranked against the same curve.
  - That means 2 new metric ids (worse rate, better rate), not 4.
  - Justification: colour |d| ≤ 0.15 at every threshold (design note, benchmark tables).
  - Rejected: one CDF per colour (half the points per anchor cell, no evidence of need), and pooling each peer's
    two colours into one rate (it mismatches the per-colour user value we display).
  - **Reversibility:** costly. The new metric ids land in `benchmark_cohort_cdf` and in the
    `user_benchmark_percentiles` metric column, which is a native Postgres ENUM (`benchmark_metric_enum`).
    Switching to per-colour later means new ids plus a CDF regeneration.
- **D-05 (SEED-206):** A new canonical-slice builder in `app/services/canonical_slice_sql.py`, shared by
  `scripts/gen_global_percentile_cdf.py` and `app/services/user_benchmark_percentiles_service.py`.
  - Slice: the most recent 3000 games within 36 months per TC (`RECENT_GAMES_PER_TC_CAP`,
    `RECENCY_WINDOW_MONTHS`), rated games only, opponents within ±100.
  - Floor: 30 qualifying games per colour × TC. The same floor applies to peers (for CDF points) and to the user.
  - Filter-independent: page filters never change it.
  - The chess.com → lichess rating mapping applies as it does for the Endgames anchors.
- **D-06 (SEED-206):** Rank per TC, display collapsed over TC. The CDF stays per TC because the peer key is rating
  per TC.

### Collapse, weights and significance (SEED-206 proposals, adopted as defaults)
- **D-07:** **Headline percentile per colour** = the user's per-TC percentiles averaged, weighted by **qualifying**
  games in each TC that passes the floor.
  - A qualifying game is one that reached the middlegame with an eval, or ended early by result per D-02. It is
    not every slice game.
  - A TC below the floor is dropped from both the headline and the gate, and listed in the popover as below
    floor.
  - The headline is an approximation, not a true percentile against a mixed-TC peer group. The copy must not
    overclaim it.
- **D-08:** **95% red/green gate.**
  - Pool the user's worse (better) count over the passing TCs. Its Wilson 95% CI must exclude the game-weighted
    peer median Σ w_tc · p50_tc(rating_tc), with the same weights as D-07.
  - Use `OPENING_INSIGHTS_CI_Z_95`, matching the Openings page (Phase 242 D-33), not the 99% used on Endgames and
    the Library.
  - The Endgames ranked-metric gate hardcodes `VERDICT_CI_Z_99` (`app/services/endgame_ranked_service.py`,
    `_wilson_interval`, `_rate_significant`). Pass z in as a parameter; never fork or reuse the 99% path as is.
- **Below-floor state:** if the selected colour has no TC that passes the floor, show the below-floor state as on
  Endgames. The colour that passes still renders when the user switches to it.

### Section UI (SEED-206, sketch 013 Variant A, collapsed)
- One "Out of the opening" card at the top of the Stats tab, under the sticky White | Black switch, for the
  selected colour only. It is not one card per TC, a deviation from sketch 013.
- The card has two `RankedMetricRow` + `PercentileBar` rows:
  - **Worse** is the primary row.
  - **Better** is styled as the lesser row and never drives the card's headline.
- The words carry the inverted meaning: "Fewer worse games than 58% of peers".
- Below-floor and pending states work as on Endgames.
- No stacked worse / even / better bar: it reads as W/D/L.

### Popover
- **D-09 (discussed, overrides ROADMAP and SEED-206):** **No histogram in the popover.** No other percentile
  popover has a chart, so this one follows the `RankedMetricPopover` structure
  (`frontend/src/components/endgames/stats/RankedMetricPopover.tsx`):
  - a plain WHAT sentence;
  - the percentile statement in words, with its disclosures;
  - a separator;
  - a greyed stats footer.

  The ROADMAP phase text and SEED-206 still mention the histogram. Ignore those lines.
- **D-10:** The **per-TC breakdown** stays. It is a compact list, not a chart: rate, percentile and qualifying games
  for each passing TC, plus each below-floor TC listed as such. This is where a bullet vs. slower-TC split becomes
  visible.
- **D-11:** The footer reports the counts (pooled k of n), the peer band, and a **95%** CI (the Endgames footer says
  99%).
- **D-12:** The disclosures carry the percentile-chip contract:
  - the peers are benchmarked lichess players, **not FlawChess users**;
  - ranked games only (rated, opponents within ±100, last 36 months);
  - **filter independence**: unlike the Endgames Stats tab, the Openings page has filters, so this line is
    required;
  - rating dependence (the worse rate drops steeply with rating).

  The FlawChess population skews high (pooled mean centred eval about +40 cp vs about 0 in the benchmark), so
  expect mostly green. The "who the peers are" line carries real weight.

### Tests
- A parity test of the slice builder: the CDF path and the user path produce identical per-user values.
- A per-eval-source check (lichess eval vs local full vs entry-lane), report-only and not a gate. SEED-206's
  feasibility data shows under ~1 pp difference.

### Claude's Discretion
- The storage shape for per-user percentiles: `user_benchmark_percentiles` has PK (user_id, metric,
  time_control_bucket) and **no colour column**, so per-colour user rows need either a colour column or per-colour
  metric ids. The planner picks one, consistent with D-04 (the CDF stays colour-pooled either way).
- How the API shape returns the collapsed headline, per-TC breakdown and gate result.
- The Umami popover target. Reuse the `popover-open` verb, and give the testid a `tc` segment only where
  `popoverTargetFromTestId` collapses it.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase design
- `.planning/seeds/SEED-206-out-of-the-opening-worse-better-rates.md`: locked decisions, rejected options (do not
  reopen), feasibility findings (floor coverage, eval source, cross-TC agreement, FlawChess skew). Its histogram
  line is superseded by D-09.
- `.planning/notes/out-of-the-opening-metric-design.md`: reasoning, benchmark tables (reliability, colour/TC/ELO d,
  score per SD), the threshold sweep.
- `.planning/sketches/013-out-of-the-opening/index.html`: Variant A card and copy. Ignore its per-TC cards and its
  histogram (superseded by D-06 and D-09). `analysis/` holds the benchmark scripts.
- `.planning/ROADMAP.md` § Phase 243: the goal statement. Its popover histogram is superseded by D-09.

### Related decisions
- `.planning/notes/percentile-chip-canonical-slice.md`: the canonical-slice contract the new builder follows.
- `.planning/notes/opponent-mirror-as-self-calibrating-cohort.md` "Governing rule": why shared-state metrics get a
  peer distribution, not a you-vs-opponent gap.
- Phase 242 artifacts (Openings Stats tab, sticky colour switch, baseline centring, D-33 95% gate):
  `.planning/phases/242-*/` or `milestones/*-phases/242-*/`.
- `reports/benchmark/benchmarks-latest.md` §2.1, §5.6, §5.15: benchmark source of truth.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `app/services/canonical_slice_sql.py`: `ranked_games_sql(tc)`, `_recent_capped_per_tc_cte`,
  `equal_footing_filter_sql`, `selected_users_cte(source=...)` and the `per_user_cte_*` builders are the pattern
  for the new builder, shared between benchmark and single user.
- `app/services/user_benchmark_percentiles_service.py`: `compute_stage_b`, `_per_user_cte_for_family_and_tc`,
  `compute_anchors_for_user` and `is_below_anchor_floor` cover the Stage B family wiring and the rating anchors.
- `scripts/gen_global_percentile_cdf.py` (`IN_SCOPE_METRICS`) and
  `app/repositories/benchmark_cohort_cdf_repository.py` cover CDF regeneration and the read path. The CDF table is
  keyed (metric, anchor_elo, tc, percentile), with no colour column, which fits D-04.
- `app/services/global_percentile_cdf.py`: the `CdfMetricId` Literal, where the new ids are added.
- `wilson_bounds` and `ci_excludes`, used in `endgame_ranked_service.py`, are reusable with z = 1.96.
- Frontend: `RankedMetricRow.tsx`, `PercentileBar.tsx` (`RankStatusLine` covers below-floor and pending),
  `RankedMetricPopover.tsx` (structure and disclosures), `rankedMetrics.ts` (`displayPercentile`, typical-range
  constants, `COPY_CHANCE`), `MetricInfoPopover`.
- `frontend/src/pages/openings/StatsTab.tsx` and `components/openings/stats/OpeningColorSwitch.tsx` provide the
  section host and the selected colour.

### Established Patterns
- Below-floor → no `user_benchmark_percentiles` row; the chip suppresses on a missing entry.
- `app/services/position_classifier.py` holds the phase rule (lichess Divider) that defines the first middlegame
  ply.
- **Flag:** `benchmark_metric_enum` is a native Postgres ENUM. CLAUDE.md says to align such columns with TEXT +
  CHECK when touched. The planner should either fold that alignment in (if cheap) or flag it explicitly, not
  silently extend the ENUM without a note.
- The eval ply convention: see memory "eval_cp has TWO ply conventions". SEED-206 measured the effect at ±1.0 as
  under ~1 pp, hence the report-only per-source check.

### Integration Points
- A new Stage B family in the per-user percentile recompute pipeline.
- The CDF regen script (a new metric family) and the benchmark DB lane.
- An API endpoint or field for the Openings Stats tab (alongside the Phase 242 stats payload).
- The top of `StatsTab.tsx`, under the sticky colour switch, desktop and phone.

</code_context>

<specifics>
## Specific Ideas

- The popover mirrors the Endgames ranked popover exactly, plus the per-TC list (D-10) and the filter-independence
  line (D-12). No charts.
- The inverted wording for the worse row: "Fewer worse games than N% of peers". The better row: "More better games
  than N% of peers".

</specifics>

<deferred>
## Deferred Ideas

- **Opening LLM narration consuming these percentiles:** out of scope (ROADMAP). It is the open SEED-206 item and
  belongs to a later narration phase.
- **Per-opening worse/better bars in the repertoire expanded card:** cut by the owner. The original design is
  preserved in SEED-206.
- **An "out of the opening over time" chart:** mentioned in the design note as a possible later addition.

</deferred>

---

*Phase: 243-out-of-the-opening-worse-better-rates*
*Context gathered: 2026-10-31*
