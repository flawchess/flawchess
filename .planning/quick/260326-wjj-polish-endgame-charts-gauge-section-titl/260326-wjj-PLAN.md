---
phase: quick
plan: 260326-wjj
type: execute
wave: 1
depends_on: []
files_modified:
  - frontend/src/components/charts/EndgamePerformanceSection.tsx
  - frontend/src/components/charts/EndgameGauge.tsx
  - frontend/src/components/charts/EndgameWDLChart.tsx
  - frontend/src/components/charts/EndgameConvRecovChart.tsx
  - frontend/src/components/charts/EndgameTimelineChart.tsx
  - frontend/src/pages/Endgames.tsx
  - frontend/src/types/endgames.ts
autonomous: true
requirements: []
must_haves:
  truths:
    - "Endgame summary info popover stays inline with text, no line break"
    - "WDL category rows have no hover highlight"
    - "Info popovers mentioning material advantage/deficit state the 300cp (3 points) threshold"
    - "Relative Endgame Strength gauge is removed"
    - "Three gauges (Conversion, Recovery, Endgame Skill) display in a single row"
    - "Gauge labels with tooltips appear above each gauge, no redundant label below"
    - "Gauges show colored arc segments (red/yellow/green zones)"
    - "Win Rate Over Time chart (endgame vs non-endgame two-line chart) is removed"
    - "WDL category rows show '<num> games <link-icon>' instead of gamepad icon + count + link"
  artifacts:
    - path: "frontend/src/components/charts/EndgameGauge.tsx"
      provides: "Gauge with colored zone segments and no bottom label"
    - path: "frontend/src/components/charts/EndgamePerformanceSection.tsx"
      provides: "3-gauge row (Conversion, Recovery, Endgame Skill), no Relative Strength"
---

<objective>
Polish endgame performance charts with 9 UI changes: fix inline popover, remove hover highlight, add threshold to popovers, remove Relative Endgame Strength gauge, add Conversion/Recovery gauges in a row with Endgame Skill, move gauge labels above with tooltips, add colored gauge zones, remove Win Rate Over Time chart, simplify WDL game count display.

Purpose: Improve endgame analytics UX clarity and reduce visual noise
Output: Updated chart components with all 9 polish items applied
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@frontend/src/components/charts/EndgamePerformanceSection.tsx
@frontend/src/components/charts/EndgameGauge.tsx
@frontend/src/components/charts/EndgameWDLChart.tsx
@frontend/src/components/charts/EndgameConvRecovChart.tsx
@frontend/src/components/charts/EndgameTimelineChart.tsx
@frontend/src/pages/Endgames.tsx
@frontend/src/types/endgames.ts

<interfaces>
<!-- Key types the executor needs -->

From frontend/src/types/endgames.ts:
```typescript
export interface EndgamePerformanceResponse {
  endgame_wdl: EndgameWDLSummary;
  non_endgame_wdl: EndgameWDLSummary;
  overall_win_rate: number;
  endgame_win_rate: number;
  aggregate_conversion_pct: number;  // 0-100
  aggregate_recovery_pct: number;    // 0-100
  relative_strength: number;         // remove this gauge
  endgame_skill: number;             // 0-100
}
```

Backend threshold constant (app/services/endgame_service.py:130):
```python
_MATERIAL_ADVANTAGE_THRESHOLD = 300  # centipawns = 3 pawn points
```
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Refactor EndgameGauge to support colored zones and top-only labels</name>
  <files>frontend/src/components/charts/EndgameGauge.tsx</files>
  <action>
Modify EndgameGauge component:

1. **Remove bottom label**: Delete the `<p>` element below the SVG that shows `{label}` — the label will now be rendered by the parent (EndgamePerformanceSection) above the gauge.

2. **Add colored zone segments to the background arc**: Instead of a single grey background arc, render 3 background arc segments representing red (0-60%), yellow (60-80%), and green (80-100%) zones. Accept an optional `zones` prop of type `Array<{ from: number; to: number; color: string }>` with a sensible default (the red/yellow/green breakdown above). Each zone is a separate `<path>` with `strokeDasharray` and `strokeDashoffset` to fill only its portion of the arc. Use lower opacity (e.g. 0.25) for zone colors so they read as background hints, not competing with the foreground arc.

3. **Keep the foreground arc and value text as-is** — the foreground arc color still uses `getGaugeColor(pct)` based on value.

4. **Update the props interface**: Add optional `zones?: Array<{ from: number; to: number; color: string }>` prop. Export the default zones as `DEFAULT_GAUGE_ZONES` so the parent can customize per-gauge.
  </action>
  <verify>
    <automated>cd /home/aimfeld/Projects/Python/flawchess/frontend && npx tsc --noEmit 2>&1 | head -30</automated>
  </verify>
  <done>EndgameGauge renders colored zone segments in background, no bottom label, accepts optional zones prop</done>
</task>

<task type="auto">
  <name>Task 2: Restructure EndgamePerformanceSection with 3 gauges and remove Relative Strength</name>
  <files>
    frontend/src/components/charts/EndgamePerformanceSection.tsx
    frontend/src/components/charts/EndgameConvRecovChart.tsx
    frontend/src/components/charts/EndgameTimelineChart.tsx
    frontend/src/pages/Endgames.tsx
  </files>
  <action>
**EndgamePerformanceSection.tsx:**

1. **Remove Relative Endgame Strength gauge entirely** — delete the `RELATIVE_STRENGTH_MAX` const, the entire first gauge `<div>` in the gauges grid, and the related InfoPopover. The `relative_strength` field from the response is no longer used here.

2. **Add Conversion and Recovery gauges**: The gauges grid should now have 3 columns (`grid-cols-3`) showing:
   - **Conversion** gauge: `value={data.aggregate_conversion_pct}`, label "Conversion"
   - **Recovery** gauge: `value={data.aggregate_recovery_pct}`, label "Recovery"
   - **Endgame Skill** gauge: `value={data.endgame_skill}`, label "Endgame Skill"

3. **Move gauge labels above each gauge with tooltips**: Each gauge gets a label+InfoPopover pair above it (as currently done, but now for all 3). Define a shared constant `MATERIAL_ADVANTAGE_POINTS = 3` for the threshold display text. Update tooltip text:
   - Conversion: "Your win rate when entering an endgame with a material advantage of at least {MATERIAL_ADVANTAGE_POINTS} points."
   - Recovery: "Your draw or win rate when entering an endgame with a material deficit of at least {MATERIAL_ADVANTAGE_POINTS} points."
   - Endgame Skill: "A weighted average of your conversion rate (60%) and recovery rate (40%). Measures overall endgame proficiency."

4. **Customize gauge zones per metric**:
   - Conversion: red 0-50%, yellow 50-70%, green 70-100% (converting advantages should be high)
   - Recovery: red 0-20%, yellow 20-40%, green 40-100% (recovery is inherently harder)
   - Endgame Skill: use defaults (red 0-60%, yellow 60-80%, green 80-100%)

**EndgameConvRecovChart.tsx:**

5. **Add threshold to info popover text**: Update the popover to mention the threshold: "Conversion: your win rate when you entered the endgame with a material advantage of at least {MATERIAL_ADVANTAGE_POINTS} points." Same pattern for Recovery with "material deficit". Import the constant from EndgamePerformanceSection or define locally.

**EndgameTimelineChart.tsx:**

6. **Remove Chart 1 (Win Rate Over Time)**: Delete the entire first chart section (the endgame vs non-endgame two-line chart, lines ~72-197). Keep only Chart 2 (Win Rate by Endgame Type). Update the component to render just that chart directly, removing the wrapping `flex flex-col gap-6` div if only one chart remains. Clean up unused imports/variables: `overallChartConfig`, `overallData`.

**Endgames.tsx:**

7. **Fix inline info popover on endgame summary line** (line 77): The InfoPopover after "reached an endgame phase" breaks to a new line because it's a block-level child of `<p>`. Wrap the entire text + popover in a `<span className="inline-flex items-center gap-1 flex-wrap">` or change the `<p>` to a `<span>` with appropriate styling to keep the popover inline.
  </action>
  <verify>
    <automated>cd /home/aimfeld/Projects/Python/flawchess/frontend && npx tsc --noEmit 2>&1 | head -30</automated>
  </verify>
  <done>3 gauges in a row (Conversion, Recovery, Endgame Skill), no Relative Strength, Win Rate Over Time chart removed, inline popover fixed, threshold mentioned in all relevant popovers</done>
</task>

<task type="auto">
  <name>Task 3: Polish WDL chart rows — remove hover highlight and simplify game count display</name>
  <files>frontend/src/components/charts/EndgameWDLChart.tsx</files>
  <action>
1. **Remove hover row highlighting**: In `EndgameCategoryRow`, remove `hover:bg-muted/30` from the outer div's className. Keep the rounded and padding classes.

2. **Simplify game count display**: In the category row header (the flex row with label and game count), replace the current pattern of `<Gamepad2Icon> <count> <ExternalLink>` with `<count> games <ExternalLink>`. Specifically:
   - Remove the `Gamepad2Icon` import and usage
   - Change the right side to: `<span className="text-xs text-muted-foreground">{cat.total} games</span>` followed by the existing `<Link>` with `<ExternalLink>` icon
   - Keep the `(low)` warning for small sample sizes
   - Remove `Gamepad2Icon` from the import statement (keep `ExternalLink`)

3. **Add threshold to the section info popover**: In the main chart heading InfoPopover (testId="endgame-chart-info"), update text to mention: "based on games that reached an endgame phase (at most 6 major/minor pieces on the board)."
  </action>
  <verify>
    <automated>cd /home/aimfeld/Projects/Python/flawchess/frontend && npx tsc --noEmit 2>&1 | head -30</automated>
  </verify>
  <done>WDL rows have no hover highlight, game count shows "N games" with link icon, no gamepad icon</done>
</task>

</tasks>

<verification>
- `npm run build` succeeds with no errors
- Visual check: 3 gauges in a row with colored zones, labels on top
- Visual check: no Relative Endgame Strength gauge
- Visual check: no Win Rate Over Time chart
- Visual check: WDL rows have no hover highlight, show "N games" format
- Visual check: info popover stays inline with endgame summary text
</verification>

<success_criteria>
All 9 UI changes applied: inline popover, no hover highlight, threshold in popovers, no Relative Strength gauge, 3-gauge row, top labels with tooltips, colored gauge zones, no Win Rate Over Time chart, simplified game count display. TypeScript compiles. Build succeeds.
</success_criteria>

<output>
After completion, create `.planning/quick/260326-wjj-polish-endgame-charts-gauge-section-titl/260326-wjj-SUMMARY.md`
</output>
