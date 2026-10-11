# Phase 238: Endgame Stats Percentile-First Redesign - Context

**Gathered:** 2026-10-11
**Status:** Ready for planning

<domain>
## Phase Boundary

Make the Endgame Stats tab readable by giving every metric one verdict: a peer percentile on the
**ranked sample** (rated, human opponents, opponents ±100 Elo, last 36 months, ≤3000 games per TC).
The big number, its WDL bar and the percentile describe the same games. Gauges, zone-colored numbers,
CI whiskers and the per-metric z-test verdict leave the visible UI; statistical detail moves to a greyed
footer in one merged popover per metric. Sections get one synced TC switch instead of accordions.

The SEED-196 locked decisions (1-9) and the sketch 009 round 2 layout are the design. This discussion
resolved the five open questions from ROADMAP.md: filters, below-floor TCs, Type table sample, default
TC, and pre-Stage-B card state. No new capabilities beyond SEED-196.

</domain>

<decisions>
## Implementation Decisions

### Carried forward from SEED-196 (locked 2026-10-11, do not re-ask)
- **D-00a:** Percentile bar (0-100, typical band 25-75 shaded, median tick, dot red <25 / blue 25-75 / green >75) is the only verdict on peer-ranked metrics. Values uncolored.
- **D-00b:** Display the ranked value, not the filtered whole-history value.
- **D-00c:** One popover per metric: WHAT + sign, percentile statement + the four disclosures (cohort, recent-games basis, filter independence, anchor composition), then n / 95% CI / p-value greyed below a separator. Merges `MetricStatPopover` and `PercentileChip`.
- **D-00d:** Gauges removed; bracket under the WDL bar marks what the rate counts.
- **D-00e:** Endgame Type Breakdown becomes a table with grey typical ranges, white "you" tick, amber below-typical value, rows under ~100 games faded, no red/green, stacked rows on mobile.
- **D-00f:** Clock Gap timeline and time-pressure curve: one grey typical band, neutral line/dots.
- **D-00g:** "Compared to similar-rated players" dot-plot card ships; rows link to their sections.
- **D-00h:** One TC switch per section, synced; Overall becomes per-TC (2 cards); aggregated cross-TC chips retire.
- **D-00i:** Unchanged: Shelly block, per-section narration slots, Endgame Score Gap over Time, Endgame ELO Timeline visuals.

### Filters on the Stats tab
- **D-01:** The Stats tab ignores filters entirely. Every Stats section reads the ranked sample per TC. Filters keep working on the Games tab. — **Reversibility:** costly — reintroducing filtered values means a second value path per section and brings back the dual-value problem.
- **D-02:** The filter panel (desktop sidebar and mobile filter button/drawer) is **hidden** while the Stats tab is active and reappears on the Games tab. Applied filter state is preserved (not reset) while hidden.
- **D-03:** Both timelines (Endgame Score Gap over Time, Endgame ELO Timeline) switch to the ranked sample and follow the section TC switch. The ELO Timeline keeps its existing green/red band (only the data source changes).
- **D-04:** Shelly insights become filter-independent: one report per user, no reset-filters-before-Generate step, no per-filter-state cache key (the `opponent_strength` exception in `_validate_full_history_filters` and the frontend `toInsightsFilters` / `areFiltersEqual` cache plumbing go away). Narrated numbers come from the ranked sample (SEED-196 payload alignment). — **Reversibility:** costly — touches the insights request contract, server cache keying and the frontend cache.

### Ranked-sample scope
- **D-05:** The Endgame Type Breakdown table also uses the ranked sample per TC and follows the TC switch. Accept more rows under the fade threshold. Grey typical ranges stay the existing population zones (`PER_CLASS_TC_GAUGE_ZONES` / type score-gap band).
- **D-06:** Time Pressure curve (per-quintile score gaps) and Clock Gap timeline use the ranked sample per TC.
- **D-07:** Values are **computed on read** from the canonical ranked slice (reuse `canonical_slice_sql.py`; CDF-side and user-side SQL stay byte-identical). Percentiles stay as persisted by Stage A/B.
- **D-08:** No drift handling between a fresh on-read value and the stored percentile. Owner: percentiles are recomputed very quickly on import. Do not add "percentile updating" states or value/n mismatch disclosures.

### Missing-percentile states
- **D-09:** TC below the 30-game anchor floor (`MEDIAN_ANCHOR_MIN_GAMES`): TC stays in the switch, cards show ranked-sample values + WDL, the percentile bar slot reads "Not enough games to rank yet (18 of 30)" with no colored dot. The dot-plot card omits that TC (or hides when the selected TC is unranked).
- **D-10:** No TC above the floor: same per-TC treatment as D-09; the dot-plot card hides. If the ranked sample is empty (0 qualifying games in every TC), the Stats tab shows one empty state explaining what counts (rated, human opponents, ±100 Elo, last 36 months) and pointing to the Games tab.
- **D-11:** Stage B not landed (entry evals pending, so value and percentile are missing for conversion/parity/recovery/clock metrics): the card keeps its layout and shows a muted line like "Analyzing your games, this fills in once evaluations finish" instead of value/bar. Cards whose data is ready (e.g. Endgame Score Gap from Stage A) render normally. No new polling. If evals exist but the percentile row is not written yet, show the value with a "not ranked yet" style slot (same visual family as D-09).

### TC switch
- **D-12:** Default TC on load = TC with the most ranked-sample games, ties to the faster TC; prefer an above-floor TC when one exists.
- **D-13:** Selected TC is remembered across visits in `localStorage` (try/catch, render fine without it); fall back to D-12 when the stored TC has no ranked games.
- **D-14:** The switch lists only TCs with ≥1 ranked-sample game, same list in every section. Below-floor TCs are listed (D-09); zero-game TCs are omitted.

### Claude's Discretion
- Plan split (backend ranked-sample payload vs frontend rework; likely 2-3 plans).
- Exact copy for empty / pending / not-ranked states (follow popover copy minimalism; disclosure contract applies to the percentile popover only).
- Where the on-read computation lives (extend endgame stats endpoint vs new endpoint) and response schema shape, as long as aggregated cross-TC fields (`score_gap_percentile`, `achievable_score_gap_percentile`, `per_tc_breakdown`) retire.
- Whether the TC-switch state lives in a small shared store or URL; persistence per D-13 regardless.
- Which p-value / CI rows apply per metric in the popover footer.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Design and locked decisions
- `.planning/seeds/SEED-196-endgame-stats-percentile-first-redesign.md` — locked decisions 1-9, peer percentile coverage table, work implied, breadcrumbs
- `.planning/sketches/009-endgame-stats-percentile-first/index.html` — owner-approved round 2 layout (synced TC switches, popover, design notes toggle)
- `.planning/sketches/009-endgame-stats-percentile-first/README.md` — round 1 → 2 decisions; which sketch data is real vs made up
- `.planning/ROADMAP.md` §Phase 238 — goal, guardrails, open questions (answered here)
- `.planning/seeds/closed/SEED-019-global-percentile-annotations-on-endgame-metrics.md` — closed predecessor

### Ranked sample and percentiles
- `app/services/canonical_slice_sql.py` — ranked slice definition (`RECENCY_WINDOW_MONTHS=36`, `RECENT_GAMES_PER_TC_CAP=3000`, `_EQUAL_FOOTING_TOL=100`, `MEDIAN_ANCHOR_MIN_GAMES=30`); CDF-side/user-side byte-identity (D-10 source-mode parity)
- `app/services/user_benchmark_percentiles_service.py` — Stage A (import completion) / Stage B (eval drain), anchors, suppression rule
- `.planning/notes/percentile-anchor-d12-reversal.md` — blended anchor + per-platform disclosure

### Payload and narration
- `app/schemas/endgames.py` — current percentile fields, `per_tc_breakdown`, chip popover inputs
- `app/services/endgame_service.py` — current filtered stats
- `app/services/insights_service.py` (~line 1011 zone findings from filtered `stats.rate`) — must narrate ranked values
- `app/routers/insights.py` `_validate_full_history_filters` — filter gate to retire per D-04

### Frontend
- `frontend/src/pages/Endgames.tsx` — tabs, filter panel, insights cache (`useCachedEndgameInsights`, `toInsightsFilters`, `areFiltersEqual`)
- Section components listed in SEED-196 Breadcrumbs (`EndgameOverall*`, `EndgameMetricsByTc*`, `EndgameTimePressure*`, `EndgameTypeBreakdownSection`, `EndgameTypeCard`, `ScoreGapByTimePressureChart`, `EndgameClockDiffOverTimeChart`, `EndgameGauge`, `PercentileChip`, `MetricStatPopover`, `MetricStatTooltip`)
- `frontend/src/generated/endgameZones.ts` (from `app/services/endgame_zones.py`) — knip will flag dead zone exports; regenerate via `scripts/gen_*.py`
- `frontend/CLAUDE.md` — styling, testids, Umami

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- Canonical slice SQL builders: on-read ranked values must reuse them, not re-derive the slice.
- `MiniBulletChart` stays (Openings uses it); do not delete.
- `useFilterStore` module-level filter state: keep intact for the Games tab; hiding the panel must not clear it.

### Established Patterns
- Percentile tooltip disclosure contract (memory `feedback_percentile_chip_tooltip_disclosure`): cohort composition, recent-games basis, filter independence, rating correlation. Required in the merged popover.
- No flame icons on percentile UI (memory `feedback_no_flame_icons`).
- Percentile is the primary LLM narration signal (Phase 102 v37); narration must use ranked values.
- Benchmarks (`reports/benchmark/benchmarks-latest.md`) are the source of truth for "typical" copy.

### Integration Points
- Stage A runs at import completion, Stage B at eval drain: the pending state (D-11) keys off missing Stage B rows / missing evals.
- Guests: eval queue excludes guests except tier 1, so guest Stage B metrics may stay pending; D-10/D-11 cover the UI.
- Insights request/cache contract changes (D-04) span router, service cache key, and frontend hook.

</code_context>

<specifics>
## Specific Ideas

- Not-ranked slot copy shape: "Not enough games to rank yet (18 of 30)".
- Pending slot copy shape: "Analyzing your games, this fills in once evaluations finish".
- Empty-state copy must name what qualifies: rated, human opponents, opponents within ±100 Elo, last 36 months.

</specifics>

<deferred>
## Deferred Ideas

- Removing the "Compared to similar-rated players" card (owner may drop it after living with it).
- Value-axis percentile strips (the full quantile table allows them later; SEED-196 note).
- Restyling the Endgame ELO Timeline band (explicitly kept as-is, D-03).

</deferred>

---

*Phase: 238-endgame-stats-percentile-first*
*Context gathered: 2026-10-11*
