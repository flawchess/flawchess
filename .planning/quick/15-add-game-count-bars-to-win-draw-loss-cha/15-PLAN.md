---
phase: quick-15
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - frontend/src/components/charts/WDLBarChart.tsx
autonomous: true
requirements: [quick-15]

must_haves:
  truths:
    - "Each opening/bookmark shows a game count bar alongside the W/D/L stacked bar"
    - "Game count bar has grey border and transparent fill"
    - "Openings are sorted by game count in descending order"
  artifacts:
    - path: "frontend/src/components/charts/WDLBarChart.tsx"
      provides: "WDL bar chart with grouped game count bars, sorted by game count"
  key_links:
    - from: "frontend/src/components/charts/WDLBarChart.tsx"
      to: "wdlStatsMap"
      via: "total field used for game_count bar and sorting"
      pattern: "game_count|total"
---

<objective>
Add a game count bar as a grouped bar to each opening/bookmark in the Win/Draw/Loss chart, and sort openings by game count descending.

Purpose: Users can see at a glance how many games each opening has, providing context for the W/D/L percentages.
Output: Updated WDLBarChart component with game count bars and sorted data.
</objective>

<execution_context>
@/home/aimfeld/.claude/get-shit-done/workflows/execute-plan.md
@/home/aimfeld/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@frontend/src/components/charts/WDLBarChart.tsx
@frontend/src/pages/Openings.tsx
</context>

<tasks>

<task type="auto">
  <name>Task 1: Add game count bars and sort by game count</name>
  <files>frontend/src/components/charts/WDLBarChart.tsx</files>
  <action>
Modify WDLBarChart.tsx to:

1. **Sort data by game count descending**: After the `.filter().map()` chain, add `.sort((a, b) => b.total - a.total)` so openings with the most games appear at the top.

2. **Add game_count field to data**: In the `.map()` callback, add `game_count: t` to the returned object (the total game count for each bookmark).

3. **Add game_count to chartConfig**: Add a new entry:
   ```
   game_count: { label: 'Games', color: 'transparent' }
   ```

4. **Convert from stacked bars to grouped bars with game count**: The current chart uses `stackId="wdl"` for the three W/D/L bars. Keep the W/D/L bars stacked together (stackId="wdl") but add a separate `<Bar>` for game_count WITHOUT a stackId so it renders as a grouped bar next to the stacked WDL bar.

5. **Style the game count bar**: Use `fill="transparent"` and `stroke="oklch(0.6 0 0)"` (grey) with `strokeWidth={1}`. Set the Bar's `style` or use the `shape` prop if needed to achieve the grey border + transparent fill look. The simplest approach: use the Bar component with `fill="transparent"` and add a custom `shape` render prop that draws a rect with grey stroke:
   ```tsx
   <Bar
     dataKey="game_count"
     fill="transparent"
     name="Games"
     shape={(props: any) => {
       const { x, y, width, height } = props;
       return (
         <rect x={x} y={y} width={width} height={height}
           fill="transparent" stroke="oklch(0.6 0 0)" strokeWidth={1} />
       );
     }}
   />
   ```

6. **Update the XAxis**: The X-axis currently shows 0-100% (for percentages). With game_count added as a grouped bar, the domain needs to accommodate both percentage values (0-100) and game count values. Use a **secondary XAxis** (xAxisId) approach:
   - Keep the existing XAxis with `xAxisId="pct"` for percentage bars (domain [0, 100])
   - Add a second XAxis with `xAxisId="count"` for game count, positioned at top, with `hide={true}` (auto-domain)
   - Assign `xAxisId="pct"` to the three WDL Bars
   - Assign `xAxisId="count"` to the game_count Bar

   This way the WDL bars scale to 100% and game count bars scale independently.

7. **Update tooltip**: Add game count display. The tooltip already shows "Total: X games" at the bottom, which covers this. No changes needed to the tooltip content since `d.total` is already displayed.

8. **Increase row height slightly** to accommodate the grouped bar: Change the height calculation from `data.length * 48 + 60` to `data.length * 64 + 60` to give more vertical space for two bar rows per opening.

9. **Update ChartLegend**: The legend will automatically pick up the new "Games" entry from chartConfig. Ensure the legend renders correctly with all four entries.
  </action>
  <verify>
    <automated>cd /home/aimfeld/Projects/Python/chessalytics/frontend && npx tsc --noEmit && npm run lint</automated>
  </verify>
  <done>WDLBarChart shows a game count bar (grey border, transparent fill) grouped alongside the stacked W/D/L bars for each opening. Openings are sorted by game count descending. TypeScript compiles and lint passes.</done>
</task>

</tasks>

<verification>
- `cd frontend && npx tsc --noEmit` passes
- `cd frontend && npm run lint` passes
- `cd frontend && npm run build` succeeds
</verification>

<success_criteria>
- Each opening in the WDL chart has a grouped game count bar with grey border and transparent fill
- Openings are sorted by game count in descending order (most games at top)
- The W/D/L percentage bars remain stacked and function as before
- Tooltip continues to show complete stats
</success_criteria>

<output>
After completion, create `.planning/quick/15-add-game-count-bars-to-win-draw-loss-cha/15-SUMMARY.md`
</output>
