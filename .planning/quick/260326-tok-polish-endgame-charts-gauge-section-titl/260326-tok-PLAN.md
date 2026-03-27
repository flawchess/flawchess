---
type: quick
autonomous: true
files_modified:
  - frontend/src/components/charts/EndgamePerformanceSection.tsx
  - frontend/src/components/charts/EndgameWDLChart.tsx
  - frontend/src/components/charts/EndgameConvRecovChart.tsx
  - frontend/src/components/charts/EndgameTimelineChart.tsx
---

<objective>
Polish the endgame charts UI with four targeted improvements:
1. Add section-title info popovers to EndgamePerformanceSection (with gauge explanations), EndgameConvRecovChart, and EndgameTimelineChart.
2. Format WDL stats consistently (one decimal place in WDLRow percentages).
3. Remove the "More" collapsible from each EndgameWDLChart category row (conversion/recovery mini-bars are redundant with EndgameConvRecovChart).
4. Add per-gauge tooltip labels inside EndgameGauge or from EndgamePerformanceSection to explain "Relative Endgame Strength" and "Endgame Skill" metrics.
</objective>

<context>
@frontend/src/components/charts/EndgamePerformanceSection.tsx
@frontend/src/components/charts/EndgameWDLChart.tsx
@frontend/src/components/charts/EndgameConvRecovChart.tsx
@frontend/src/components/charts/EndgameTimelineChart.tsx
@frontend/src/components/ui/info-popover.tsx
</context>

<tasks>

<task type="auto">
  <name>Task 1: Add section-title info popovers and fix WDL formatting in EndgamePerformanceSection</name>
  <files>frontend/src/components/charts/EndgamePerformanceSection.tsx</files>
  <action>
    1. Import `InfoPopover` from `@/components/ui/info-popover`.

    2. Replace the plain `<h3>Endgame Performance</h3>` heading with an inline-flex heading that includes an InfoPopover:
       - Section title: "Endgame Performance"
       - Popover content: Explains that this section compares win rates in endgame vs non-endgame positions, and that Relative Endgame Strength and Endgame Skill are computed from those rates.
       - testId: `"perf-section-info"`, ariaLabel: `"Endgame Performance info"`, side: `"top"`

    3. Add an InfoPopover to the "Relative Endgame Strength" gauge label area. Since `EndgameGauge` only accepts `value`, `maxValue`, and `label`, add the tooltip inline in `EndgamePerformanceSection` below the `<EndgameGauge>` component or by wrapping each gauge in a labeled `<div>` with a title row that includes the InfoPopover.

       Preferred approach: wrap each `EndgameGauge` in a `<div className="flex flex-col items-center gap-1">` and add a title row above the SVG:
       ```tsx
       <div className="flex flex-col items-center gap-0">
         <div className="flex items-center gap-1 text-xs text-muted-foreground">
           <span>Relative Endgame Strength</span>
           <InfoPopover ariaLabel="Relative Endgame Strength info" testId="gauge-relative-strength-info" side="top">
             Your win rate in endgame games as a percentage of your overall win rate. 100% means identical performance; above 100% means you outperform your baseline in endgames.
           </InfoPopover>
         </div>
         <EndgameGauge value={data.relative_strength} maxValue={RELATIVE_STRENGTH_MAX} label="Relative Endgame Strength" />
       </div>
       ```
       Do the same for "Endgame Skill":
       - InfoPopover content: "How often you win or draw when entering an endgame with a material advantage (conversion), or escape with a draw or win when at a deficit (recovery). Averaged across both metrics."
       - testId: `"gauge-endgame-skill-info"`, ariaLabel: `"Endgame Skill info"`

    4. In `WDLRow`, change `wdl.win_pct.toFixed(0)` → `wdl.win_pct.toFixed(1)` (and same for draw_pct, loss_pct) so WDL stats show one decimal place (e.g., "W: 45.2%"), consistent with chart tooltip precision.
  </action>
  <verify>npm run build 2>&1 | tail -5</verify>
  <done>EndgamePerformanceSection has info icon on "Endgame Performance" heading and per-gauge info icons; WDL stats show one decimal place.</done>
</task>

<task type="auto">
  <name>Task 2: Remove "More" collapsibles from EndgameWDLChart and add info popovers to ConvRecov and Timeline charts</name>
  <files>
    frontend/src/components/charts/EndgameWDLChart.tsx
    frontend/src/components/charts/EndgameConvRecovChart.tsx
    frontend/src/components/charts/EndgameTimelineChart.tsx
  </files>
  <action>
    **EndgameWDLChart.tsx:**
    1. Remove the entire `{hasConvRecov && (...)}` Collapsible block from `EndgameCategoryRow` (lines ~187-230). This removes the "More" toggle and conversion/recovery mini-bars that are now redundant with the EndgameConvRecovChart below.
    2. Remove the now-unused `moreOpen` / `setMoreOpen` state and the `hasConvRecov` prop from `CategoryRowProps`.
    3. Remove unused imports: `useState`, `ChevronDown`, `ChevronUp`, `Collapsible`, `CollapsibleTrigger`, `CollapsibleContent` — only if no longer used elsewhere in the file.
    4. Remove `hasConvRecov` from the `EndgameCategoryRow` call sites in `EndgameWDLChart`.

    **EndgameConvRecovChart.tsx:**
    1. Import `InfoPopover` from `@/components/ui/info-popover`.
    2. Change the section heading from `<h3 className="text-base font-semibold mb-3">Conversion &amp; Recovery by Endgame Type</h3>` to an inline-flex version with an InfoPopover:
       - testId: `"conv-recov-chart-info"`, ariaLabel: `"Conversion and Recovery info"`, side: `"top"`
       - Popover content: "Conversion: your win rate when you entered the endgame with a material advantage. Recovery: your draw+win rate when you entered the endgame with a material deficit."

    **EndgameTimelineChart.tsx:**
    1. Import `InfoPopover` from `@/components/ui/info-popover`.
    2. Add InfoPopover to "Win Rate Over Time" section heading:
       - testId: `"timeline-overall-info"`, ariaLabel: `"Win Rate Over Time info"`, side: `"top"`
       - Content: "Rolling-window win rate over time, comparing games that reached an endgame phase vs. those that did not. Each point represents a window of recent games."
    3. Add InfoPopover to "Win Rate by Endgame Type" section heading:
       - testId: `"timeline-per-type-info"`, ariaLabel: `"Win Rate by Endgame Type info"`, side: `"top"`
       - Content: "Rolling-window win rate over time for each endgame type. Click legend items to toggle individual series."

    For all three heading modifications, use the pattern already established in EndgameWDLChart:
    ```tsx
    <h3 className="text-base font-semibold mb-3">
      <span className="inline-flex items-center gap-1">
        Section Title
        <InfoPopover ...>...</InfoPopover>
      </span>
    </h3>
    ```
  </action>
  <verify>npm run build 2>&1 | tail -5</verify>
  <done>No "More" collapsibles in EndgameWDLChart rows; all three chart section titles have info popovers; build passes with no TypeScript errors.</done>
</task>

</tasks>

<success_criteria>
- npm run build passes with no errors
- EndgamePerformanceSection: "Endgame Performance" heading has info icon; each gauge has adjacent info icon
- EndgameWDLChart: no "More" collapsible per row; conversion/recovery mini-bars removed
- EndgameConvRecovChart: section heading has info popover
- EndgameTimelineChart: both chart headings have info popovers
- WDL percentages in EndgamePerformanceSection show one decimal place
</success_criteria>
