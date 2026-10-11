---
id: SEED-196
status: closed. Resolved by Phase 238 (squash c51f85c19 on main, 2026-10-11), including the owner UAT rounds (peers card dropped).
promoted_to: Phase 238
promoted: 2026-10-11
planted: 2026-10-11
planted_during: ad-hoc Endgame Stats UX review (no phase in flight; next standalone phase is 238)
trigger_when: owner picks the Endgame Stats redesign as a phase (owner asked for it to be implemented in a phase, 2026-10-11)
scope: medium-large (backend ranked-sample payload + frontend rework of 4 sections; likely 1 phase with 2-3 plans, possibly split backend/frontend)
---

# SEED-196: Endgame Stats page redesign, percentile-first

Design: `.planning/sketches/009-endgame-stats-percentile-first/` (round 2, owner-approved direction).
Baseline screenshots (gitignored, local only): `temp/endgame-redesign/01-*.jpg` to `18-*.png`.

## Why This Matters

The bullet-chart and gauge sections of the Endgame Stats tab are hard to understand. Each metric carries
**three verdicts that can contradict each other**, all painted in the same red/blue/green:

| Signal | Reference | Sample |
|---|---|---|
| Zone color (bullet bands, gauge arc, colored number) | population p25-p75 per TC, ratings pooled | filtered, whole history |
| Percentile chip | rating peers (cohort CDF at the user's anchor Elo) | last 36 months, opponents ±100 Elo, filter-independent |
| Magnifier popover verdict | z-test vs 0 ("Likely a real relative weakness, p = 0.000") | filtered, whole history |

Observed on dev data (owner account, 2026-10-11):
- Endgame Score Gap −13%: red number, red bar zone, popover says "real weakness", but the chip is blue (27th, "typical").
- Rapid Recovery 21.6%: gauge needle in the neutral blue zone (21.8-33.3%), chip red (24th).
- The chip ranks a different number than the one printed next to it: rapid Conversion shows 71.5% (480 games,
  filtered), the chip's 46th percentile is for 74.6% (299 games, ranked sample).
- Gauges duplicate the WDL bar right below them: Conversion = win %, Recovery = W + D, Parity = score.
- One bullet row can carry 9 elements (3 zone bands, value bar, center tick, CI whisker, colored number,
  magnifier, chip, CPU icon). The Overall section alone has 6 bullets in 4 cards.

The LLM narration already leads with percentiles (Phase 102 v37), so making the percentile the single
visible verdict aligns the page with Shelly.

## Locked decisions (owner, 2026-10-11)

1. **Percentiles are the main metric.** One visual for every peer-ranked metric: a 0-100 percentile bar with the
   typical band (25-75) shaded, median tick, and a dot colored by band (red < 25, blue 25-75, green > 75).
   Values stay uncolored. No zone bands, no CI whiskers, no zone-colored numbers on ranked metrics.
2. **Display the ranked value**, not the filtered whole-history value ("a value over a player's whole game
   history is not that relevant"). The big number, its WDL bar, and the percentile must describe the same games.
3. **Statistical details stay in the tooltip**, greyed out below a separator (n, 95% CI, p-value where it
   applies). One popover per metric: plain WHAT + sign convention, the percentile statement, the four
   disclosures (cohort, recent-games basis, filter independence, anchor composition per
   `feedback_percentile_chip_tooltip_disclosure`), then the grey stats footer. This merges today's
   `MetricStatPopover` and `PercentileChip` popovers.
4. **Gauges are removed.** A bracket under the WDL bar marks what the rate counts (wins / wins + draws / score).
5. **Endgame Type Breakdown becomes a table** (rows = types; columns = results WDL, Score, Conversion,
   Recovery, vs. engine). No per-type peer percentiles exist, so the only signals are a grey "typical range"
   (existing `PER_CLASS_TC_GAUGE_ZONES` / type score-gap band) with a white "you" tick and an amber
   "below typical" value. Rows under ~100 games faded. No red/green in this section. Mobile: stacked rows.
6. **Clock Gap at Endgame Entry timeline:** the three ±5% zones become one grey "typical" band, and the
   line/dots are neutral (today `zoneColor()` paints points). Consistent with the time-pressure curve,
   whose per-bin zones also become one grey band.
7. **"Compared to similar-rated players" card ships** (all 11 percentiles for the selected TC on one 0-100 axis,
   grouped: endgame results / winning-balanced-losing / clock). The owner may remove it later; each row
   should link to its section because the names are hard to read out of context.
8. **One TC switch per section, synced across sections**, replacing the Blitz/Rapid accordions. The Overall
   section becomes per-TC too (the averaged "across your time controls" chip retires).
9. Unchanged: Shelly block at top, per-section narration headline slots, Endgame Score Gap over Time,
   Endgame ELO Timeline (its green/red band is out of scope).

## Peer percentile coverage (what exists today)

11 metric families per TC in `user_benchmark_percentiles` (`app/services/user_benchmark_percentiles_service.py`,
Stage A `score_gap`, Stage B the other 10), ranked against `benchmark_cohort_cdf` (anchor Elo every 50, full
quantile table, so a value-axis strip is possible later):

| Section | Ranked | Not ranked (plain numbers, no color) |
|---|---|---|
| Overall | `score_gap`, `achievable_score_gap` | Endgame / Non-Endgame Score, Entry Eval, Expected Score, timelines |
| Endgame Metrics | `conversion_rate`, `parity_rate`, `recovery_rate`, `score_gap_conv`, `score_gap_parity`, `recovery_score_gap` | none |
| Time Pressure | `clock_gap`, `net_flag_rate`, `time_pressure_score_gap` | per-quintile score gaps (curve) |
| Type Breakdown | none | everything (grey typical range only) |

## Work implied (for discuss/plan)

**Backend: ranked-sample payload.** `user_benchmark_percentiles` stores only `value` + `n_games` per
(metric, TC). Decision 2 needs, on the same ranked sample (last 36 months, opponents ±100 Elo, per TC):
WDL for conversion/parity/recovery, with/without-endgame scores + WDL, entry eval / expected / actual score,
and the CI / p-value inputs. Options: extend the Stage A/B per-user CTEs (`app/services/canonical_slice_sql.py`)
to persist the components, or compute on read with the same canonical slice. Keep CDF-side and user-side SQL
byte-identical (D-10 source-mode parity). `score_gap_percentile` / `achievable_score_gap_percentile` /
`per_tc_breakdown` (aggregated chips) can retire.

**Frontend.** New `PercentileBar` component (+ the profile dot-plot), unified metric popover, metric cards
without `EndgameGauge`, Overall reduced to 2 cards, Type Breakdown table, grey bands in
`EndgameClockDiffOverTimeChart` and `ScoreGapByTimePressureChart`, synced TC switch. `MiniBulletChart` stays
(Openings uses it); `EndgameGauge` and `PercentileChip` likely delete. Update the "Endgame Statistics
Concepts" accordion copy. Knip will flag dead zone exports in `generated/endgameZones.ts`.

**LLM payload alignment.** `insights_service.py` narrates percentile findings from `percentile_value` (ranked)
but zone findings from the filtered `stats.rate` (line ~1011). After the redesign the UI shows ranked values,
so narrated numbers must come from the ranked sample too, or Shelly's numbers will not match the page.

## Open questions for discuss-phase

- **What do filters still do on this tab?** If every stat section shows the filter-independent ranked sample,
  filters only affect the timelines and the Games tab. Options: hide/disable non-applicable filters on Stats,
  or keep a filtered fallback for users/TCs without a ranked anchor. Needs an explicit decision.
- TCs below the anchor floor (no percentile): show the value with "not enough games to rank", or hide the TC?
- Does the Type Breakdown table also switch to the ranked sample (consistency), or keep filtered history?
- Default TC on load: most-played TC in the ranked sample?
- Guest / no-eval users: Stage B percentiles depend on evals; what does a card show before Stage B lands?

## Breadcrumbs

- `frontend/src/pages/Endgames.tsx` (section layout, `SectionInsightSlot`)
- `frontend/src/components/charts/EndgameOverallPerformanceSection.tsx`, `EndgameOverallCard.tsx`,
  `EndgameOverallEntryCard.tsx`, `EndgameOverallScoreGapRow.tsx`
- `frontend/src/components/charts/EndgameMetricsByTcSection.tsx`, `EndgameMetricsByTcCard.tsx`, `EndgameGauge.tsx`
- `frontend/src/components/charts/EndgameTimePressureSection.tsx`, `EndgameTimePressureCard.tsx`,
  `ScoreGapByTimePressureChart.tsx`, `EndgameClockDiffOverTimeChart.tsx`
- `frontend/src/components/charts/EndgameTypeBreakdownSection.tsx`, `EndgameTypeCard.tsx`
- `frontend/src/components/charts/PercentileChip.tsx`, `MiniBulletChart.tsx`,
  `frontend/src/components/popovers/MetricStatPopover.tsx`, `MetricStatTooltip.tsx`
- `frontend/src/generated/endgameZones.ts` (from `app/services/endgame_zones.py`)
- `app/services/user_benchmark_percentiles_service.py`, `app/services/canonical_slice_sql.py`,
  `app/schemas/endgames.py`, `app/services/endgame_service.py`, `app/services/insights_service.py`
- Closed predecessor: `.planning/seeds/closed/SEED-019-global-percentile-annotations-on-endgame-metrics.md`
- Memory: percentile chip disclosure contract, percentile as primary narration signal, no flame icons on chips
