---
phase: quick-10
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - frontend/src/components/stats/RatingChart.tsx
autonomous: true
requirements: [QUICK-10]

must_haves:
  truths:
    - "Y-axis ticks on RatingChart are uniformly spaced"
    - "Y-axis domain aligns with the chosen tick step boundaries"
    - "Tick step size adapts to data range (smaller ranges get finer ticks)"
  artifacts:
    - path: "frontend/src/components/stats/RatingChart.tsx"
      provides: "Uniform Y-axis ticks via explicit ticks prop"
      contains: "ticks="
  key_links:
    - from: "yDomain computation"
      to: "YAxis ticks prop"
      via: "shared step size and aligned boundaries"
      pattern: "ticks=.*yTicks"
---

<objective>
Fix the RatingChart Y-axis to display uniformly spaced tick marks instead of Recharts' default unevenly-spaced auto-ticks.

Purpose: The current chart shows irregular Y-axis spacing because no explicit `ticks` prop is set on `<YAxis>`. This makes the chart harder to read.
Output: Updated RatingChart.tsx with computed uniform tick values.
</objective>

<execution_context>
@/home/aimfeld/.claude/get-shit-done/workflows/execute-plan.md
@/home/aimfeld/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@frontend/src/components/stats/RatingChart.tsx
</context>

<tasks>

<task type="auto">
  <name>Task 1: Add uniform Y-axis tick computation and pass ticks prop</name>
  <files>frontend/src/components/stats/RatingChart.tsx</files>
  <action>
In the existing `yDomain` useMemo (lines 58-77), also compute explicit tick values and return both domain and ticks together. Alternatively, create a second useMemo that derives ticks from yDomain.

Implementation details:

1. Choose a "nice" step size based on the data range. Use this logic:
   - range = max - min (of visible ratings)
   - Pick step from candidates [10, 20, 50, 100, 200, 500] such that range/step produces roughly 4-8 ticks (aim for ~5-6 ticks). A simple approach: pick the largest step where `range / step >= 4`, falling back to the smallest step if none qualify.

2. Round domain boundaries to align with the chosen step:
   - domainMin = Math.floor(min / step) * step
   - domainMax = Math.ceil(max / step) * step
   - This replaces the current rounding to nearest 100.

3. Generate tick array: iterate from domainMin to domainMax (inclusive) by step.

4. Refactor the useMemo to return an object `{ domain, ticks }` (or use a second useMemo). Update the JSX:
   - `<YAxis domain={yDomain} ticks={yTicks} />` (or destructured equivalent)

5. Keep the existing `['auto', 'auto']` fallback for edge cases (no visible TCs, no finite data). When domain is 'auto', do NOT pass the ticks prop (let Recharts auto-handle).

6. Edge case: if min === max (all ratings identical), use a small range around that value (e.g., min-50 to max+50) so ticks are still meaningful.
  </action>
  <verify>
    <automated>cd /home/aimfeld/Projects/Python/chessalytics/frontend && npx tsc --noEmit && npm run lint</automated>
  </verify>
  <done>YAxis receives explicit uniform tick values computed from a "nice" step size. Domain boundaries align with tick step. Chart compiles and lints cleanly.</done>
</task>

</tasks>

<verification>
- `npm run build` succeeds
- Visual check: Y-axis ticks are evenly spaced on the RatingChart
</verification>

<success_criteria>
- RatingChart Y-axis displays uniformly spaced ticks
- Step size adapts to data range (e.g., 50-point steps for narrow ranges, 100-200 for wide ranges)
- Domain min/max align with tick boundaries (no orphan ticks)
- No TypeScript or lint errors
</success_criteria>

<output>
After completion, create `.planning/quick/10-fix-y-axis-ticks-on-chess-com-rating-cha/10-SUMMARY.md`
</output>
