---
phase: 238-endgame-stats-percentile-first
plan: 05
subsystem: ui
tags: [react, typescript, recharts, percentiles, endgames, tailwind]

requires:
  - phase: 238-02
    provides: ranked payload time_pressure, clock_diff_timeline and type_categories per TC
  - phase: 238-03
    provides: RankedMetricRow, PercentileBar, TcSwitch, useEndgameStatsTc, rankedMetrics vocabulary, EndgameStatsTab, rankedFixtures
provides:
  - "MetricsSection/MetricsCard: per-TC Conversion, Parity, Recovery cards with an uncolored ranked rate, a bracketed WDL bar and two percentile rows, no gauge"
  - "TimePressureSection: per-TC clock timeline, score-vs-clock curve and three percentile rows"
  - "EndgameClockDiffOverTimeChart and ScoreGapByTimePressureChart reworked to one grey typical band, neutral line/dots/tooltip swatch, no z-test verdict line"
  - "TypeTable: per-TC type table with grey typical-range cells, white tick, amber only below range, faded low-sample rows, stacked mobile layout"
  - "Filter-free EndgameStatsTab (props: tier2, onCategorySelect) and rewritten concepts accordion"
affects: [238-06, 238-07]

plan_head_before: 1052c3a407318eea73f850cfb3c9f88414549099
plan_head_after: de3065046b3751a46ae4f9d54448d2fed055ace7
actuals:
  tokens: 31600
  tasks: 3
  commits: 5

tech-stack:
  added: []
  patterns:
    - "Per-TC section = useEndgameStatsTc + own TcSwitch + section root carrying the SECTION_ID anchor and a children slot for the narration"
    - "Reworked chart tests pin the neutral colors through theme constants (NEUTRAL_SERIES_COLOR, TYPICAL_BAND_FILL) and compare swatches through a reference element because jsdom normalizes oklch"
    - "Range cell = grey band + white tick on a named-constant domain, amber text only below the band"

key-files:
  created:
    - frontend/src/components/endgames/stats/MetricsCard.tsx
    - frontend/src/components/endgames/stats/MetricsCard.test.tsx
    - frontend/src/components/endgames/stats/MetricsSection.tsx
    - frontend/src/components/endgames/stats/TimePressureSection.tsx
    - frontend/src/components/endgames/stats/TimePressureSection.test.tsx
    - frontend/src/components/endgames/stats/TypeTable.tsx
    - frontend/src/components/endgames/stats/TypeTable.test.tsx
    - frontend/src/components/endgames/useEndgameInsightsState.ts
  modified:
    - frontend/src/components/endgames/EndgameStatsTab.tsx
    - frontend/src/components/endgames/EndgameStatsTab.test.tsx
    - frontend/src/components/charts/EndgameClockDiffOverTimeChart.tsx
    - frontend/src/components/charts/ScoreGapByTimePressureChart.tsx
    - frontend/src/components/charts/__tests__/EndgameClockDiffOverTimeChart.test.tsx
    - frontend/src/components/charts/__tests__/ScoreGapByTimePressureChart.test.tsx
    - frontend/src/pages/Endgames.tsx
    - frontend/src/pages/__tests__/Endgames.readinessGate.test.tsx
    - frontend/src/pages/__tests__/Endgames.overallPerformance.test.tsx
    - frontend/src/lib/theme.ts

key-decisions:
  - "The transitional insights state moved out of EndgameStatsTab into useEndgameInsightsState.ts, which reads the filter store itself; this is how the Tab can be genuinely filter-free (grep for FilterState/appliedFilters is 0) while the insights cache stays filter-keyed until plan 238-07"
  - "Bucket card dimming is a card-colored veil over the uncounted WDL segments (MiniWDLBar untouched); bracket and veil colors live in theme.ts"
  - "The curve keeps its CI ErrorBar whiskers and the tooltip CI/test footnotes: the plan only asked to drop zone bands, zone colors and the verdict line (A12)"
  - "The type table skips HIDDEN_ENDGAME_CLASSES defensively even though the backend already excludes mixed and pawnless"

patterns-established:
  - "Stats-tab sections read only the ranked payload and the shared TC store; the Tab receives no overview, statsData or filter props"

requirements-completed: [D-00a, D-00d, D-00e, D-00f, D-00h, D-01, D-05, D-06]

coverage:
  - id: D1
    description: "Metrics card: uncolored ranked rate with game count, WDL bar from the same bucket, bracket over wins / wins + draws / score, vs. peers and vs. engine rows, no gauge, pending line instead of number and bar"
    requirement: "D-00d"
    verification:
      - kind: unit
        ref: "frontend/src/components/endgames/stats/MetricsCard.test.tsx"
        status: pass
    human_judgment: true
    rationale: "Bracket geometry, label placement and the dim veil are layout choices verified only by eye"
  - id: D2
    description: "Clock Gap timeline and score-vs-clock curve each render exactly one grey typical band, neutral line, dots and tooltip swatch; curve tooltip has no 'Likely/Possibly a real' verdict and shows the p-value greyed"
    requirement: "D-00f"
    verification:
      - kind: unit
        ref: "frontend/src/components/charts/__tests__/EndgameClockDiffOverTimeChart.test.tsx"
        status: pass
      - kind: unit
        ref: "frontend/src/components/charts/__tests__/ScoreGapByTimePressureChart.test.tsx"
        status: pass
    human_judgment: true
    rationale: "Contrast of the 9% grey band and the neutral line on the dark card needs a visual pass"
  - id: D3
    description: "Time Pressure section follows the synced TC switch with timeline (hidden without clock points), curve and three percentile rows"
    requirement: "D-06"
    verification:
      - kind: unit
        ref: "frontend/src/components/endgames/stats/TimePressureSection.test.tsx"
        status: pass
    human_judgment: false
  - id: D4
    description: "Type table: typical-range cells from PER_CLASS_TC_GAUGE_ZONES, tick clamped into the domain, amber only below the range, no red or green outside the WDL bar, faded rows under 100 games, stacked captions below md, games link, empty branch"
    requirement: "D-00e"
    verification:
      - kind: unit
        ref: "frontend/src/components/endgames/stats/TypeTable.test.tsx"
        status: pass
    human_judgment: true
    rationale: "Mobile stacked layout (grid rows with captions) is only verifiable on a real narrow viewport"
  - id: D5
    description: "Stats tab is driven by the ranked payload and one synced TC switch and receives no filter or overview props"
    requirement: "D-01"
    verification:
      - kind: unit
        ref: "frontend/src/components/endgames/EndgameStatsTab.test.tsx#mounts the five ranked sections and switches them all from one switch (D-01, D-00h)"
        status: pass
      - kind: integration
        ref: "frontend/src/pages/__tests__/Endgames.readinessGate.test.tsx"
        status: pass
    human_judgment: false
  - id: D6
    description: "Concepts accordion describes percentile bars, grey typical ranges and the per-TC ranked sample, with no gauge, color-zone, badge or weighted-chip wording"
    requirement: "D-00h"
    verification:
      - kind: other
        ref: "grep of EndgameStatsTab.tsx for gauge|color zone|badge|weighted returns nothing"
        status: pass
    human_judgment: true
    rationale: "Copy tone and accuracy against the benchmark report need an editorial read"

duration: ~55min
completed: 2026-10-11
status: complete
---

# Phase 238 Plan 05: Metrics, Time Pressure and Type sections on the ranked payload Summary

**All four remaining Stats sections now read the ranked payload and the synced TC switch: gauge-free Metrics cards with a bracketed WDL bar, a Time Pressure section with one grey typical band and neutral marks, and a type table with grey typical-range cells, on a Stats tab that takes no filter or overview props.**

## Performance

- **Duration:** about 55 min
- **Tasks:** 3 (1 tracer, 2 TDD)
- **Files:** 18 touched (8 created, 10 modified); 5 commits

## Accomplishments

- `MetricsCard` / `MetricsSection` (D-00d): per bucket the ranked rate is the uncolored big number with its game count; the WDL bar comes from the same `RankedBucketOut`; a bracket spans the wins (Conversion) or wins plus draws (Recovery) with the uncounted segments veiled, Parity only carries its "score (W + ½D)" label; then "{Name} vs. peers" and "vs. engine expectation" `RankedMetricRow`s. A pending rate shows the pending line instead of number and bar (D-11).
- `TimePressureSection` (D-06): one `TcSwitch`, the clock timeline card (hidden when the TC has no clock points), and a card with the curve plus "Your clock vs. peers" (Clock Gap at entry, Net Flag Rate, Score under time pressure).
- Charts (D-00f): `EndgameClockDiffOverTimeChart` and `ScoreGapByTimePressureChart` each render exactly one `ReferenceArea` (±`NEUTRAL_PCT_THRESHOLD` and `PRESSURE_SCORE_GAP_NEUTRAL_MIN/MAX`) filled with `TYPICAL_BAND_FILL` and a small "typical" label; line, dots and tooltip swatch use `NEUTRAL_SERIES_COLOR`. The curve tooltip lost the verdict line and shows the p-value greyed. Prop signatures unchanged (A17).
- `TypeTable` (D-00e, D-05): rows for the selected TC; conversion, recovery and vs.-engine cells show a grey band from `PER_CLASS_TC_GAUGE_ZONES[class][tc]` with a white tick clamped into a named-constant domain; value text is amber only below the band; rows under `TYPE_ROW_LOW_CONFIDENCE_GAMES = 100` are faded; below md each row stacks with per-cell captions; the per-type games link and the empty branch are kept.
- Filter-free tab (D-01): `EndgameStatsTab` props are `{ tier2, onCategorySelect }`; the page no longer passes overview, stats or filter state to it. The concepts accordion was rewritten (percentile bars, grey typical ranges, per-TC ranked sample, no weighted-mean step, no Opponent Strength filter advice).
- Old section components are unmounted but untouched on disk for the 238-06 sweep; `MiniBulletChart` is untouched. Gates: `npm run lint`, `npm run build`, `npm run knip` clean; full `npm test` 331 files / 5569 tests passing.

## Task Commits

1. **Task 1 (tracer): Metrics cards on the ranked payload** - `f6936fe6c` (feat)
2. **Task 2 RED: failing tests for Time Pressure and neutral single-band charts** - `2c3e9ba9d` (test)
3. **Task 2 GREEN: Time Pressure section, one grey band, neutral marks** - `94b6b45d5` (feat)
4. **Task 3 RED: failing tests for the type table** - `7003bb885` (test)
5. **Task 3 GREEN: type table, filter-free tab, concepts copy** - `de3065046` (feat)

**Plan metadata:** committed separately (docs: complete plan).

## TDD Gate Compliance

- **Tracer gate (Task 1):** `<verify>` (stats + page tests, then `npm run build`) re-run green before expanding; "Tracer verified end-to-end, expanding". Task 1 is a tracer (no RED/GREEN split required).
- **Task 2 RED:** 12 chart tests plus 4 section tests failed against the old charts and a render-nothing `TimePressureSection` scaffold. Observed failures: `expected 3 to be 1` (band count), `expected 'white' to be 'oklch(0.95 0 0)'` (line stroke), `expected 'oklch(0.5 0.14 145)' to be 'oklch(0.95 0 0)'` (zone-colored swatch), `element mock-pressure-curve present: expected null not to be null` (scaffold). Each failed on the planned assertion. The clock tooltip had to be extracted into `ClockGapTooltipContent` (behavior-preserving) in the RED commit so the swatch was testable. The machine classifier `gsd-tools check tdd-red-evidence` was not run for this plan (the Stats-tab Vitest output was assessed by hand against the planned assertions); this is a process gap versus the strict reference, not a missing RED commit.
- **Task 3 RED:** 14 of 15 type-table tests failed against a render-nothing scaffold (`element type-row-rook present: expected null not to be null` and siblings). One test ("draws no red or green outside the WDL bar") passed vacuously against the empty scaffold; it was made meaningful in GREEN by scoping it to the table and then holding with real content.
- **Mutation check (GREEN):** flipping the amber condition from `value < band[0]` to `value > band[1]` failed "turns the value amber only when it is below the typical range"; reverted.
- No REFACTOR commit was needed.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Insights state extracted into `useEndgameInsightsState.ts`**
- **Found during:** Task 3
- **Issue:** The plan requires `grep -c "FilterState\|appliedFilters" EndgameStatsTab.tsx` to be 0 and "no filter state at all", but the insights cache and `useCachedEndgameInsights` are still keyed by the applied filters until plan 238-07 (the Tab got them from the page as `appliedFilters`/`setAppliedFilters`).
- **Fix:** moved `useEndgameInsightsState` verbatim into `frontend/src/components/endgames/useEndgameInsightsState.ts`, which calls `useFilterStore()` itself. The Tab and every section are now filter-free; plan 238-07 removes the store read when it makes the report filter-free. 238-07's task text says to edit the insights state "in EndgameStatsTab"; the code to change is now in this hook file.
- **Commit:** `de3065046`

**2. [Rule 3 - Blocking] Mocks added to `EndgameStatsTab.test.tsx`**
- **Found during:** Task 2
- **Issue:** the Tab now mounts the real `TimePressureSection`, whose charts need `window.matchMedia`, absent in that test.
- **Fix:** mock the two time-pressure charts there (and drop the obsolete overview props from `renderTab`); added a test that the five ranked sections mount and share one TC switch.
- **Commit:** `94b6b45d5`, `de3065046`

**3. [Rule 2 - Missing critical] Tooltip provider in the type-table test**
- **Found during:** Task 3
- **Issue:** the games link uses `Tooltip`, which requires `TooltipProvider` (provided app-wide in `App.tsx`).
- **Fix:** the test wraps in `TooltipProvider`, like `EndgameTypeCard.test.tsx` does.
- **Commit:** `de3065046`

### Execution notes (no impact on scope)

- Fallback path for the old time-pressure card/section tests was not needed: they stay green against the reworked charts and nothing was deleted.
- `lib/theme.ts` gained `METRIC_BRACKET_COLOR`, `METRIC_BRACKET_DIM_OVERLAY`, `TYPICAL_BAND_FILL`, `NEUTRAL_SERIES_COLOR`, `TYPICAL_BELOW_VALUE` and `TYPICAL_YOU_TICK`; the type-table track and band reuse `PERCENTILE_TRACK` / `PERCENTILE_TYPICAL_BAND` from 238-03. Nothing was removed.
- The curve keeps its `ErrorBar` CI whiskers and the tooltip's "Independent two-sample test." and CI footnotes; the plan's behavior block only removes zone bands, zone colors and the verdict line. The phase success criterion mentions "CI whiskers" on the Stats tab; if the owner wants the curve whiskers gone too, that is a small follow-up in `ScoreGapByTimePressureChart.tsx` (its tests currently assert them).
- The Metrics rate row repeats the rate next to its percentile bar (the big number above it is the same value); `RankedMetricRow` has no hide-value option and was outside this plan's files.
- The Metrics, Time Pressure and Type sections are shown for every TC in the payload, with no per-TC minimum-games card floor (the old `MIN_GAMES_PER_TC_CARD` eligibility filter is gone); sample-size honesty comes from the percentile status slots and the faded type rows.

**Total deviations:** 3 small auto-fixes (2 Rule 3, 1 Rule 2). **Impact:** one pointer change for plan 238-07 (insights state location); nothing else.

## Authentication Gates

None.

## Issues Encountered

- `ChartTooltipBox`/Recharts tooltips cannot be hovered in jsdom, so the clock tooltip was extracted into an exported component for testing, matching how `ScoreGapTooltipContent` already worked.
- `TcSwitch` buttons carry `aria-invalid:...destructive` utility classes, so the "no red or green" assertion scans the table only.

## Known Stubs

None. The unmounted old section components (`EndgameMetricsByTcSection`, `EndgameTimePressureSection`, `EndgameTypeBreakdownSection`, `EndgameOverallPerformanceSection`, gauge, chips, stat popovers, `percentileAnchor`, `EndgameOverallShared`) remain on disk for plan 238-06, reachable only through their own tests (A17); knip is green.

## Threat Flags

None. No new network surface; the sections render numeric payload values through React/Recharts text nodes (T-238-14), old `PANEL_TARGETS` entries remain registered (T-238-15), and no packages were installed (T-238-SC).

## Next Phase Readiness

Ready for 238-06 (mechanical sweep of the unmounted components, tests, `percentileAnchor.ts`, `EndgameOverallShared.ts`, and retired-name comments such as the `lib/theme.ts` line mentioning `EndgameGauge`) and 238-07 (filter-free insights: edit `useEndgameInsightsState.ts`, drop its `useFilterStore` read; hide the filter UI on the Stats tab; Games tab onto `/endgames/stats`). The page still calls `useEndgameOverview` for the Games tab's category stats until 238-07.

## Self-Check: PASSED

- Created files exist: MetricsCard(.test), MetricsSection, TimePressureSection(.test), TypeTable(.test), useEndgameInsightsState
- Commits `f6936fe6c`, `2c3e9ba9d`, `94b6b45d5`, `7003bb885`, `de3065046` are ancestors of HEAD
- Acceptance greps: old section imports 0 in Tab, page and both page tests; `FilterState|appliedFilters` 0 in the Tab; `EndgameGauge` 0 in MetricsCard; `ZONE_DANGER|ZONE_SUCCESS` 0 in TypeTable and both charts; exactly one `<ReferenceArea` in each chart; `MiniBulletChart.tsx` present
