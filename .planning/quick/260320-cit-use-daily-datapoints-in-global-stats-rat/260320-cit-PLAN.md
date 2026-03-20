---
phase: quick-260320-cit
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - frontend/src/components/stats/RatingChart.tsx
autonomous: true
requirements: [QUICK-260320-CIT]
must_haves:
  truths:
    - "Rating chart uses daily grouping when data spans < 1 year"
    - "Rating chart uses weekly grouping when data spans >= 1 year and < 3 years"
    - "Rating chart uses monthly grouping when data spans >= 3 years"
    - "X-axis labels format adapts to granularity (Mar 15, Mar 10, Mar '26)"
    - "Tooltip shows correctly formatted date for active granularity"
  artifacts:
    - path: "frontend/src/components/stats/RatingChart.tsx"
      provides: "Adaptive granularity rating chart"
      contains: "determineGranularity"
  key_links:
    - from: "RatingChart.tsx granularity detection"
      to: "grouping key computation"
      via: "date span calculation from data array"
      pattern: "granularity.*day|week|month"
---

<objective>
Change the RatingChart from always-monthly grouping to adaptive granularity based on data date range.

Purpose: Show finer-grained rating progression for users with shorter history — daily points for < 1 year, weekly for 1-3 years, monthly for 3+ years.
Output: Updated RatingChart.tsx with adaptive granularity logic.
</objective>

<execution_context>
@/home/aimfeld/.claude/get-shit-done/workflows/execute-plan.md
@/home/aimfeld/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@frontend/src/components/stats/RatingChart.tsx
@frontend/src/types/stats.ts

<interfaces>
From frontend/src/types/stats.ts:
```typescript
export interface RatingDataPoint {
  date: string;       // Full date string, e.g. "2025-06-15"
  rating: number;
  time_control_bucket: string;
}
```

Current grouping in RatingChart.tsx:
- Slices `pt.date.slice(0, 7)` to get "YYYY-MM" key
- Uses `formatMonth` for x-axis labels and tooltip
- XAxis dataKey is "month"
- Backend sends per-game data sorted chronologically
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Add adaptive granularity logic to RatingChart</name>
  <files>frontend/src/components/stats/RatingChart.tsx</files>
  <action>
Refactor RatingChart.tsx to support adaptive date granularity:

1. Define a `Granularity` type: `'day' | 'week' | 'month'`

2. Add `determineGranularity(data: RatingDataPoint[]): Granularity` function:
   - Compute date span: parse first and last `data[].date` as Date objects, compute difference in days
   - < 365 days → 'day'
   - < 1095 days (3 * 365) → 'week'
   - >= 1095 days → 'month'

3. Add `getBucketKey(dateStr: string, granularity: Granularity): string` function:
   - 'day': return dateStr as-is (YYYY-MM-DD)
   - 'week': compute ISO week start (Monday) — `new Date(dateStr)`, subtract to previous Monday, format as YYYY-MM-DD. This gives stable weekly buckets.
   - 'month': return `dateStr.slice(0, 7)` (current behavior)

4. Add `formatBucketLabel(key: string, granularity: Granularity): string` function:
   - 'day': format as "Mar 15" — `toLocaleDateString('en-US', { month: 'short', day: 'numeric' })`
   - 'week': format as "Mar 10" — same format (shows week start date)
   - 'month': use existing `formatMonth` logic — "Mar '26"

5. Refactor the `chartData` useMemo:
   - Call `determineGranularity(data)` to get granularity
   - Replace hardcoded `pt.date.slice(0, 7)` with `getBucketKey(pt.date, granularity)`
   - Change the record key from `month` to `bucket` (generic name)
   - Return `{ data: Array.from(map.values()), granularity }` from the memo

6. Update XAxis:
   - Change `dataKey` from "month" to "bucket"
   - Change `tickFormatter` to use `formatBucketLabel` with the computed granularity

7. Update ChartTooltip content:
   - Replace `formatMonth(label)` with `formatBucketLabel(label, granularity)`

8. Keep all other logic identical: hiddenKeys toggling, yDomain/yTicks computation, line rendering, legend, chartConfig.
  </action>
  <verify>
    <automated>cd /home/aimfeld/Projects/Python/chessalytics/frontend && npx tsc --noEmit 2>&1 | head -30</automated>
  </verify>
  <done>
    - RatingChart compiles with no TypeScript errors
    - Granularity is determined from data date span: daily (< 1yr), weekly (1-3yr), monthly (3+yr)
    - X-axis labels adapt to granularity format
    - Tooltip date label adapts to granularity format
    - Existing monthly behavior preserved for 3+ year spans
  </done>
</task>

</tasks>

<verification>
- `cd frontend && npx tsc --noEmit` passes with no errors
- `cd frontend && npm run build` succeeds
- Visual spot-check: rating chart renders with appropriate granularity for user's data
</verification>

<success_criteria>
Rating charts on Global Stats page use adaptive granularity — daily for short history, weekly for medium, monthly for long — with correctly formatted axis labels and tooltips.
</success_criteria>

<output>
After completion, create `.planning/quick/260320-cit-use-daily-datapoints-in-global-stats-rat/260320-cit-SUMMARY.md`
</output>
