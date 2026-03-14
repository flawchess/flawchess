---
phase: quick-11
plan: 11
type: execute
wave: 1
depends_on: []
files_modified:
  - frontend/src/components/ui/chart.tsx
  - frontend/src/components/stats/GlobalStatsCharts.tsx
  - frontend/src/components/bookmarks/WDLBarChart.tsx
autonomous: true
requirements: [QUICK-11]
must_haves:
  truths:
    - "Clicking a legend label in any Recharts chart toggles that series on/off"
    - "Hidden series legend labels appear visually dimmed (opacity + line-through)"
    - "RatingChart and WinRateChart legend toggle continues to work (already implemented)"
    - "GlobalStatsCharts (WDL by TC and by Color) legend toggle hides/shows bar segments"
    - "WDLBarChart (bookmark WDL comparison) legend toggle hides/shows bar segments"
  artifacts:
    - path: "frontend/src/components/ui/chart.tsx"
      provides: "ChartLegendContent with hiddenKeys visual feedback"
    - path: "frontend/src/components/stats/GlobalStatsCharts.tsx"
      provides: "WDLCategoryChart with legend toggle state"
    - path: "frontend/src/components/bookmarks/WDLBarChart.tsx"
      provides: "WDLBarChart with legend toggle state"
  key_links:
    - from: "ChartLegendContent"
      to: "hiddenKeys prop"
      via: "optional hiddenKeys Set renders dimmed legend items"
      pattern: "hiddenKeys.*opacity"
---

<objective>
Add interactive legend toggle to all Recharts charts so clicking a legend label hides/shows that series.

Purpose: Let users focus on specific data series by toggling others off, standard chart interaction pattern.
Output: All 4 chart components support clickable legend toggle with visual feedback on hidden items.
</objective>

<execution_context>
@/home/aimfeld/.claude/get-shit-done/workflows/execute-plan.md
@/home/aimfeld/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@frontend/src/components/ui/chart.tsx
@frontend/src/components/stats/RatingChart.tsx
@frontend/src/components/stats/GlobalStatsCharts.tsx
@frontend/src/components/bookmarks/WinRateChart.tsx
@frontend/src/components/bookmarks/WDLBarChart.tsx

<interfaces>
<!-- RatingChart and WinRateChart already have working toggle logic (hiddenKeys state,
     handleLegendClick callback, hide prop on Line, onClick on ChartLegend).
     Only missing piece: ChartLegendContent does not visually indicate hidden state.
     GlobalStatsCharts and WDLBarChart have no toggle logic at all. -->

From chart.tsx (ChartLegendContent props):
```typescript
// Current: no hiddenKeys prop — legend items always look active
function ChartLegendContent({
  className, hideIcon, payload, verticalAlign, nameKey,
}: ...)
```

From RatingChart.tsx (existing toggle pattern to replicate):
```typescript
const [hiddenKeys, setHiddenKeys] = useState<Set<string>>(new Set());
const handleLegendClick = useCallback((dataKey: string) => {
  setHiddenKeys((prev) => { const next = new Set(prev); next.has(dataKey) ? next.delete(dataKey) : next.add(dataKey); return next; });
}, []);
// On ChartLegend: onClick={(e) => { if (e?.dataKey) handleLegendClick(e.dataKey as string); }}
// On Line: hide={hiddenKeys.has(tc)}
```
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Add hiddenKeys visual feedback to ChartLegendContent</name>
  <files>frontend/src/components/ui/chart.tsx</files>
  <action>
Add an optional `hiddenKeys` prop (type `Set<string>`) to ChartLegendContent. When a legend item's dataKey is in hiddenKeys, render it with `opacity-50` and `line-through` text decoration to visually indicate the series is hidden. Add `cursor-pointer` to all legend items so users know they are clickable.

Specifically in ChartLegendContent:
1. Add `hiddenKeys?: Set<string>` to the destructured props
2. On the outer div of each legend item, add `cursor-pointer` class
3. Check if `key` (the dataKey) is in `hiddenKeys` — if so, add `opacity-50 line-through` classes to the legend item div
4. Do NOT change any other behavior — this is purely additive

Then update RatingChart.tsx and WinRateChart.tsx to pass `hiddenKeys` to ChartLegendContent so their existing toggle gets the visual feedback:
- `<ChartLegend content={<ChartLegendContent hiddenKeys={hiddenKeys} />} ... />`
  </action>
  <verify>
    <automated>cd /home/aimfeld/Projects/Python/chessalytics/frontend && npx tsc --noEmit 2>&1 | head -30</automated>
  </verify>
  <done>ChartLegendContent accepts optional hiddenKeys prop, renders hidden items with opacity-50 and line-through. RatingChart and WinRateChart pass hiddenKeys to get visual feedback.</done>
</task>

<task type="auto">
  <name>Task 2: Add legend toggle to GlobalStatsCharts and WDLBarChart</name>
  <files>frontend/src/components/stats/GlobalStatsCharts.tsx, frontend/src/components/bookmarks/WDLBarChart.tsx</files>
  <action>
Add the same toggle pattern used in RatingChart to both bar chart components.

For WDLCategoryChart (inside GlobalStatsCharts.tsx):
1. Add `useState` and `useCallback` imports
2. Add `const [hiddenKeys, setHiddenKeys] = useState<Set<string>>(new Set())`
3. Add `handleLegendClick` callback (same pattern as RatingChart)
4. On ChartLegend: add `onClick={(e) => { if (e?.dataKey) handleLegendClick(e.dataKey as string); }}`
5. Pass hiddenKeys to ChartLegendContent: `content={<ChartLegendContent hiddenKeys={hiddenKeys} />}`
6. Add `hide={hiddenKeys.has('win_pct')}` to win_pct Bar, same for draw_pct and loss_pct

For WDLBarChart:
1. Same pattern — add hiddenKeys state, handleLegendClick, onClick on ChartLegend, hiddenKeys on ChartLegendContent, hide prop on each Bar
  </action>
  <verify>
    <automated>cd /home/aimfeld/Projects/Python/chessalytics/frontend && npx tsc --noEmit 2>&1 | head -30 && npm run build 2>&1 | tail -5</automated>
  </verify>
  <done>All 4 chart components (RatingChart, WinRateChart, GlobalStatsCharts, WDLBarChart) support legend click toggle with visual dimming of hidden series.</done>
</task>

</tasks>

<verification>
1. `cd frontend && npm run build` succeeds with no errors
2. All charts render legends with cursor-pointer styling
3. Clicking a legend item toggles series visibility and dims the legend label
</verification>

<success_criteria>
- Clicking any legend label in any Recharts chart toggles that series on/off
- Hidden series have dimmed (opacity-50) and struck-through legend labels
- All 4 chart components use the same consistent toggle pattern
- Frontend builds without errors
</success_criteria>

<output>
After completion, create `.planning/quick/11-toggle-series-on-off-by-clicking-legend-/11-SUMMARY.md`
</output>
