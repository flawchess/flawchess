---
phase: quick-19
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - frontend/src/components/stats/RatingChart.tsx
autonomous: false
requirements: [QUICK-19]

must_haves:
  truths:
    - "X-axis tick labels never repeat the same month label consecutively"
    - "Tick intervals are equal-distance in time"
    - "Tick interval adapts to the data time range (e.g. monthly for 1-2 years, quarterly for 3+ years)"
    - "Y-axis behavior unchanged"
  artifacts:
    - path: "frontend/src/components/stats/RatingChart.tsx"
      provides: "Adaptive x-axis tick computation"
  key_links: []
---

<objective>
Fix x-axis in RatingChart so tick labels are evenly spaced at adaptive time intervals instead of repeating the same month label multiple times.

Purpose: The current chart has one data point per game, all using date strings. Recharts with `interval="preserveStartEnd"` shows too many tick marks, causing repeated labels like "Jan 21, Jan 21, Jan 21". The fix computes explicit tick positions at equal time intervals adapted to the data range.

Output: Updated RatingChart.tsx with adaptive x-axis ticks.
</objective>

<execution_context>
@/home/aimfeld/.claude/get-shit-done/workflows/execute-plan.md
@/home/aimfeld/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@frontend/src/components/stats/RatingChart.tsx
@frontend/src/types/stats.ts
</context>

<tasks>

<task type="auto">
  <name>Task 1: Implement adaptive equal-distance x-axis ticks in RatingChart</name>
  <files>frontend/src/components/stats/RatingChart.tsx</files>
  <action>
Replace the current XAxis configuration with explicit computed ticks. The approach:

1. Add a `useMemo` hook that computes x-axis ticks from `chartData`:
   - Extract the full date range: parse min/max date strings from the data (format "YYYY-MM-DD")
   - Compute the time span in months
   - Choose an adaptive interval based on span:
     - <= 6 months: every month
     - <= 18 months: every 2 months
     - <= 36 months: every 3 months (quarterly)
     - <= 72 months: every 6 months
     - > 72 months: every 12 months
   - Generate tick date strings at the chosen interval, starting from the first month boundary at or before min date, ending at or after max date
   - Each tick is a "YYYY-MM-DD" string (first day of month) that matches the `date` dataKey format

2. Update the XAxis component:
   - Remove `interval="preserveStartEnd"`
   - Add `ticks={xTicks}` with the computed tick array
   - Add `type="category"` (keeps string-based axis matching the data)
   - Keep `tickFormatter={formatDate}` as-is (already formats to "Mon YY")
   - Add `tick={{ fontSize: 12 }}` for readability
   - Add `allowDuplicatedCategory={false}` to prevent any remaining duplicates

3. The tick values MUST be actual date strings that exist in the chartData array OR use the approach of filtering chartData dates to the nearest tick. Since chartData has one entry per game (not per month), the ticks need to reference actual data dates. Best approach: generate the ideal tick dates, then for each ideal tick, find the closest actual date string in chartData. If no data point is close enough, skip that tick.

   Alternative simpler approach (preferred): Use a numeric x-axis instead of category:
   - Convert date strings to timestamps (number) in chartData rows: add a `dateTs` field
   - Use `dataKey="dateTs"` on XAxis with `type="number"` and `scale="time"`
   - Compute tick positions as timestamps at the adaptive interval boundaries
   - The `tickFormatter` converts timestamp back to "Mon YY" display format
   - Set `domain={[minTs, maxTs]}` on XAxis

   This is cleaner because Recharts numeric axes handle tick positioning natively.

Implementation detail for the numeric approach:
- In the `chartData` useMemo, add `dateTs: new Date(point.date).getTime()` to each row
- Create `xTicks` useMemo: compute interval, generate first-of-month timestamps
- XAxis: `dataKey="dateTs"` `type="number"` `scale="time"` `domain={[minTs, maxTs]}` `ticks={xTicks}` `tickFormatter={(ts: number) => new Date(ts).toLocaleDateString('en-US', { month: 'short', year: '2-digit' })}`
- Remove the standalone `formatDate` function (now inline in tickFormatter)

Keep the tooltip label formatter working: update the tooltip to format the dateTs back to a readable date string.
  </action>
  <verify>
    <automated>cd /home/aimfeld/Projects/Python/chessalytics/frontend && npm run build</automated>
  </verify>
  <done>
    - RatingChart x-axis shows evenly spaced date ticks with no repeated labels
    - Tick interval adapts to data time range (monthly for short ranges, quarterly/yearly for long ranges)
    - Tooltip still shows readable date
    - Y-axis behavior unchanged
    - Build passes with no errors
  </done>
</task>

<task type="checkpoint:human-verify" gate="blocking">
  <name>Task 2: Verify adaptive x-axis ticks visually</name>
  <files>frontend/src/components/stats/RatingChart.tsx</files>
  <action>
    Human verifies the RatingChart x-axis displays correctly across different recency filters.
  </action>
  <verify>Visual inspection by user</verify>
  <done>User confirms x-axis ticks are evenly spaced, non-repeating, and adapt to time range</done>
  <what-built>Adaptive equal-distance x-axis ticks in RatingChart</what-built>
  <how-to-verify>
    1. Navigate to the Rating page
    2. With "All time" selected, verify x-axis ticks are evenly spaced and no labels repeat
    3. Switch recency filter to "Past month", "3 months", "1 year" -- verify tick intervals adapt appropriately (more granular for shorter ranges)
    4. Verify tooltip still shows correct date and rating on hover
    5. Verify Y-axis ticks are unchanged
  </how-to-verify>
  <resume-signal>Type "approved" or describe issues</resume-signal>
</task>

</tasks>

<verification>
- `npm run build` passes
- X-axis labels are unique (no consecutive repeats)
- Tick spacing is visually equal-distance
</verification>

<success_criteria>
RatingChart x-axis displays evenly spaced, non-repeating date labels that adapt their interval to the time range of the data.
</success_criteria>

<output>
After completion, create `.planning/quick/19-fix-x-axis-in-rating-charts-adaptive-equ/19-SUMMARY.md`
</output>
