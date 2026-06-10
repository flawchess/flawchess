---
phase: quick-260606-jvg
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - frontend/src/components/stats/RatingChart.tsx
  - frontend/src/components/stats/GlobalStatsCharts.tsx
  - frontend/src/pages/GlobalStats.tsx
  - frontend/src/components/stats/__tests__/RatingChart.test.tsx
  - frontend/src/components/stats/__tests__/GlobalStatsCharts.test.tsx
autonomous: true
requirements: [QUICK-JVG]
must_haves:
  truths:
    - "Rating charts omit a TC series (and its legend entry) when that series has zero data points"
    - "Results by Time Control panel omits rows for TCs that are disabled in the filter"
  artifacts:
    - path: frontend/src/components/stats/RatingChart.tsx
      provides: "Rating chart that renders only TC series with data"
    - path: frontend/src/components/stats/GlobalStatsCharts.tsx
      provides: "Results-by-TC panel gated on the enabled-TC filter set"
  key_links:
    - from: frontend/src/pages/GlobalStats.tsx
      to: frontend/src/components/stats/GlobalStatsCharts.tsx
      via: "enabledTimeControls prop derived from filters.timeControls"
      pattern: "enabledTimeControls"
---

<objective>
Two small frontend bug fixes in the Library > Stats subtab (page component
`GlobalStatsPage` in `frontend/src/pages/GlobalStats.tsx`):

1. Rating charts (`RatingChart`) must not render a time-control series whose data
   array contains zero points. The user has never played bullet, yet "Bullet"
   still appears in the legend. Series with no data points (and their legend
   entries) must be omitted.

2. The "Results by Time Control" panel (`WDLCategoryChart` inside
   `GlobalStatsCharts`) must not show rows for time controls that are disabled in
   the filter panel. When a TC is unchecked, its row must disappear.

Both fixes are purely client-side. The backend `get_global_stats`
(`app/services/stats_service.py`) aggregates `by_time_control` across every TC the
user has played and never receives the `timeControls` filter, so the disabled-TC
row arrives in the payload and must be gated in the component. `RatingChart`
already accepts an `enabledTimeControls` prop for the filter; this plan layers a
"has-data" check on top of it.

Purpose: stop showing empty/disabled time-control entries that confuse users.
Output: updated `RatingChart`, `GlobalStatsCharts`, `GlobalStats.tsx` wiring, plus
regression tests.
</objective>

<execution_context>
@$HOME/.claude/gsd-core/workflows/execute-plan.md
</execution_context>

<context>
@./CLAUDE.md
@frontend/src/components/stats/RatingChart.tsx
@frontend/src/components/stats/GlobalStatsCharts.tsx
@frontend/src/pages/GlobalStats.tsx
@frontend/src/components/stats/__tests__/RatingChart.test.tsx
@frontend/src/types/stats.ts
@frontend/src/types/api.ts

Key facts confirmed during investigation:
- `TimeControl` = `'bullet' | 'blitz' | 'rapid' | 'classical'` (frontend/src/types/api.ts:33).
- `filters.timeControls: TimeControl[] | null` where `null` = all enabled
  (FilterPanel.tsx:42; DEFAULT is `null`).
- `RatingDataPoint` has `time_control_bucket` (lowercase TC) and `rating`.
  `RatingChart` builds `chartData` by grouping points into per-date rows keyed by
  `time_control_bucket`. A TC has "data" iff at least one point exists with that
  `time_control_bucket`.
- `RatingChart` already derives `visibleTcs = enabledTimeControls ?? TIME_CONTROLS`
  (line 51) and maps over it to render `<Line>` series (lines 209-220). The legend
  is `<ChartLegend content={<ChartLegendContent .../>}>` driven by `chartConfig`
  (lines 38-43, 198-200).
- `WDLByCategory.label` for `by_time_control` is title-cased by the backend
  (`key.title()` -> "Bullet"/"Blitz"/"Rapid"/"Classical", stats_service.py:241).
  `GlobalStatsCharts` renders one `WDLChartRow` per `data` entry (GlobalStatsCharts.tsx:36-44).
- `GlobalStatsCharts` is rendered in GlobalStats.tsx:101-104 and does NOT currently
  receive the filter. `RatingChart` IS passed `enabledTimeControls={filters.timeControls}`
  (lines 77, 95).
</context>

<tasks>

<task type="auto">
  <name>Task 1: Omit empty TC series (and legend entries) in RatingChart</name>
  <files>frontend/src/components/stats/RatingChart.tsx</files>
  <action>
In `RatingChart`, compute the set of TCs that actually have at least one data
point, and intersect it with the filter-derived `visibleTcs` so that series with
no data are never rendered AND never appear in the legend.

Steps:
1. Add a memoized `tcsWithData: TimeControl[]` derived from the `data` prop:
   for each `tc` in the existing module-level `TIME_CONTROLS` constant, include it
   only if `data.some((pt) => pt.time_control_bucket === tc)`. Use `useMemo` keyed
   on `data` (consistent with the existing `chartData` useMemo).
2. Change `visibleTcs` so it is the intersection of the filter set and
   `tcsWithData`: start from `enabledTimeControls ?? TIME_CONTROLS`, then
   `.filter((tc) => tcsWithData.includes(tc))`. Keep the existing `TimeControl[]`
   typing. This single `visibleTcs` already drives the `<Line>` series map
   (lines ~209-220), so the `<Line>` series fix is automatic.
3. Legend: the legend currently renders from `chartConfig` (all four entries) via
   `ChartLegendContent`. To hide legend entries for empty/filtered-out series,
   build a `legendConfig` object containing only the `visibleTcs` keys (pick from
   `chartConfig`) and pass that to the `ChartContainer config=` prop instead of
   the full `chartConfig`, OR pass the filtered set down to `ChartLegendContent`.
   Inspect how `ChartLegendContent` (frontend/src/components/ui/chart.tsx) derives
   its items first: if it reads from the chart `config` context, narrowing the
   `config` passed to `ChartContainer` to only `visibleTcs` keys is the minimal fix
   and also keeps the tooltip label lookup intact (tooltip reads `chartConfig[tc]`
   by dataKey, and only visible dataKeys produce payload items, so a narrowed
   config still resolves all rendered series). If `ChartLegendContent` instead
   derives items from the rendered `<Line>` children, no legend change is needed
   beyond the `visibleTcs` map. Choose whichever the actual `ChartLegendContent`
   implementation requires — read it before editing.
4. Keep the existing legend click hide/show (`hiddenKeys`) behavior working for
   the series that remain visible.
5. Do NOT introduce magic strings: reuse the existing `TIME_CONTROLS` constant and
   `chartConfig` keys. No new colors (theme rule) — series colors already come from
   `chartConfig` / `var(--color-${tc})`.
6. Keep mobile/desktop parity: `RatingChart` is a single shared component (no
   separate mobile renderer), so one change covers both.

Edge cases: when `data` is empty the component already early-returns the
"No {platform} games imported" message (line 147) — leave that untouched. When
all series are filtered out but `data` is non-empty (e.g. filter excludes the only
TC with data), the chart renders with no `<Line>` series; the existing yDomain
fallback (`effectiveTcs.length === 0` -> `['auto','auto']`) already handles this
without crashing.
  </action>
  <verify>
    <automated>cd frontend && npm test -- --run src/components/stats/__tests__/RatingChart.test.tsx</automated>
  </verify>
  <done>
RatingChart renders `<Line>` series and legend entries only for TCs that have at
least one data point AND are enabled by `enabledTimeControls`. A user who never
played bullet sees no "Bullet" line and no "Bullet" legend entry. Existing
inactivity-gap tests still pass.
  </done>
</task>

<task type="auto">
  <name>Task 2: Gate Results-by-Time-Control rows on the enabled-TC filter</name>
  <files>frontend/src/components/stats/GlobalStatsCharts.tsx, frontend/src/pages/GlobalStats.tsx</files>
  <action>
Make the "Results by Time Control" panel drop rows for disabled TCs.

Steps:
1. In `GlobalStatsCharts`, add an optional prop
   `enabledTimeControls?: TimeControl[] | null` (import `TimeControl` from
   `@/types/api`). `null`/`undefined` = all enabled (matches the filter store
   convention). This prop applies ONLY to the by-time-control panel, not the
   by-color panel.
2. Before passing `byTimeControl` into the by-TC `WDLCategoryChart`, filter it:
   when `enabledTimeControls` is a non-null array, keep only categories whose
   `label.toLowerCase()` is included in `enabledTimeControls`. Backend labels are
   title-cased ("Bullet"), filter values are lowercase ("bullet"), so compare via
   `label.toLowerCase()`. Do not mutate the prop; build a derived list (a `useMemo`
   is fine, or an inline `.filter` since the parent already memoizes upstream — a
   plain inline filter is acceptable here, it's cheap over <=4 rows).
3. Do not magic-string the four TC names — reuse the lowercase comparison against
   the passed `enabledTimeControls`; no new constant needed since the set comes
   from the prop. If a named constant is genuinely useful, reuse the existing
   `TIME_CONTROLS` pattern rather than duplicating literals.
4. In GlobalStats.tsx, pass `enabledTimeControls={filters.timeControls}` to
   `<GlobalStatsCharts ... />` (GlobalStats.tsx:101-104). The `filters` object is
   already in scope (and already feeds `RatingChart`).
5. The empty-state branch in `WDLCategoryChart` ("No data available.") already
   handles a now-empty `data` array, so if every enabled TC has zero games the
   panel shows the existing empty message — no extra work.
6. No mobile-specific renderer exists for this panel (single component used in both
   layouts), so one change covers desktop and mobile.

Note: the by-color panel and its row gating are out of scope — only the
by-time-control rows are filtered.
  </action>
  <verify>
    <automated>cd frontend && npm test -- --run src/components/stats/__tests__/GlobalStatsCharts.test.tsx</automated>
  </verify>
  <done>
With a TC unchecked in the filter, the "Results by Time Control" panel renders no
row (no `WDLChartRow`) for that TC. With `enabledTimeControls` null/all, all
present TC rows render as before. By-color panel is unchanged.
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 3: Regression tests for both fixes</name>
  <files>frontend/src/components/stats/__tests__/RatingChart.test.tsx, frontend/src/components/stats/__tests__/GlobalStatsCharts.test.tsx</files>
  <behavior>
    RatingChart:
    - Given data with only blitz/rapid points (no bullet), the rendered output
      contains a blitz line/legend but NO bullet line and NO "Bullet" legend text.
    - Given data containing bullet points but `enabledTimeControls={['blitz']}`,
      no bullet line renders (filter still wins).
    GlobalStatsCharts:
    - Given byTimeControl rows for Bullet+Blitz+Rapid+Classical and
      `enabledTimeControls={['blitz','rapid']}`, only Blitz and Rapid rows render
      (assert via the per-row testid `global-stats-by-tc-{label}` e.g.
      `global-stats-by-tc-bullet` is absent, `global-stats-by-tc-blitz` present).
    - Given `enabledTimeControls={null}`, all four rows render.
    - By-color rows are unaffected by `enabledTimeControls`.
  </behavior>
  <action>
Add/extend tests. For RatingChart, extend the existing
`RatingChart.test.tsx` (reuse its `recharts` ResponsiveContainer mock,
`matchMedia`/`ResizeObserver` `beforeAll` stubs, and `makePoint` helper pattern —
note `makePoint` currently hardcodes `time_control_bucket: 'blitz'`; add a variant
or parameter to emit bullet points). Assert on rendered `<Line>` series. Since
recharts `<Line>` renders to SVG paths, prefer asserting on legend text and on the
`data-testid` of the chart, plus query for the series via the chart config: the
most robust assertion is on the legend — assert the legend does NOT contain the
text "Bullet" when no bullet data is present, and DOES contain "Blitz". If the
legend text is not reliably queryable in jsdom (recharts legend rendering can be
sparse under the mock), fall back to asserting on the number of rendered
`recharts-line` className nodes or on dataKey-bearing elements; inspect the actual
rendered DOM in a scratch run to choose the stable selector.

Create `GlobalStatsCharts.test.tsx` as a new file following the same jsdom test
conventions (`// @vitest-environment jsdom`, the recharts mock if WDLChartRow uses
recharts, `cleanup` in `afterEach`). Build minimal `WDLByCategory[]` fixtures
(label + wins/draws/losses/total/pcts). Use the per-row `data-testid`
`global-stats-by-tc-{label.toLowerCase()}` (already emitted at
GlobalStatsCharts.tsx:42) to assert presence/absence of rows. Check whether
`WDLChartRow` needs any DOM stubs (ResizeObserver) and add them if a render error
occurs.

Follow CLAUDE.md frontend test rules; do not weaken assertions to make them pass.
  </action>
  <verify>
    <automated>cd frontend && npm test -- --run src/components/stats/__tests__/RatingChart.test.tsx src/components/stats/__tests__/GlobalStatsCharts.test.tsx</automated>
  </verify>
  <done>
Both test files pass and assert the empty-series-omission (RatingChart) and
disabled-TC-row-omission (GlobalStatsCharts) behaviors. Tests fail if the
production fixes are reverted.
  </done>
</task>

</tasks>

<verification>
Full frontend gate (MANDATORY before marking done, per CLAUDE.md Pre-PR checklist):

```bash
cd frontend && npm run lint && npm test -- --run && npm run build && npm run knip
```

All must pass clean. `npm run build` catches TypeScript errors from the new
`enabledTimeControls` prop and `TimeControl` import; `knip` catches any unused
exports introduced.
</verification>

<success_criteria>
- RatingChart omits any TC series and its legend entry when that series has zero
  data points (bullet no longer shown for a user who never played bullet).
- The filter-derived `enabledTimeControls` still wins (a TC with data but disabled
  in the filter is also omitted).
- "Results by Time Control" panel omits rows for TCs disabled in the filter.
- By-color panel unchanged.
- Mobile and desktop both reflect the changes (shared components).
- `npm run lint`, `npm test -- --run`, `npm run build`, `npm run knip` all pass.
</success_criteria>

<output>
Create `.planning/quick/260606-jvg-rating-charts-in-library-stats-subtab-sh/260606-jvg-SUMMARY.md` when done.
</output>
