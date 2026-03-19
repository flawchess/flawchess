---
phase: quick
plan: 260319-owl
type: execute
wave: 1
depends_on: []
files_modified:
  - frontend/src/components/results/WDLBar.tsx
  - frontend/src/components/charts/WDLBarChart.tsx
autonomous: true
requirements: []
must_haves:
  truths:
    - "Draw color in WDL bar and WDL bar chart matches the brightness of win/loss colors"
  artifacts:
    - path: "frontend/src/components/results/WDLBar.tsx"
      provides: "WDL_DRAW constant with lightness 0.45"
      contains: "oklch(0.45"
    - path: "frontend/src/components/charts/WDLBarChart.tsx"
      provides: "Draw chart config color with lightness 0.45"
      contains: "oklch(0.45"
  key_links: []
---

<objective>
Darken the WDL draw color from oklch(0.65 0.01 260) to oklch(0.45 0.01 260) so it matches the brightness (lightness=0.45) of the win and loss colors.

Purpose: The current draw grey is too bright relative to the green/red, making the bar look unbalanced.
Output: Updated color constants in both WDL components.
</objective>

<execution_context>
@/home/aimfeld/.claude/get-shit-done/workflows/execute-plan.md
@/home/aimfeld/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@frontend/src/components/results/WDLBar.tsx
@frontend/src/components/charts/WDLBarChart.tsx
</context>

<tasks>

<task type="auto">
  <name>Task 1: Darken draw color in both WDL components</name>
  <files>frontend/src/components/results/WDLBar.tsx, frontend/src/components/charts/WDLBarChart.tsx</files>
  <action>
In WDLBar.tsx line 5, change:
  `export const WDL_DRAW = 'oklch(0.65 0.01 260)';`
to:
  `export const WDL_DRAW = 'oklch(0.45 0.01 260)';`

In WDLBarChart.tsx line 19, change:
  `draw_pct: { label: 'Draws', color: 'oklch(0.65 0.01 260)' },`
to:
  `draw_pct: { label: 'Draws', color: 'oklch(0.45 0.01 260)' },`

Both files must use the exact same draw color value. The lightness drops from 0.65 to 0.45 to match WDL_WIN and WDL_LOSS.
  </action>
  <verify>
    <automated>cd /home/aimfeld/Projects/Python/chessalytics/frontend && npx tsc --noEmit && grep -n "0.65" src/components/results/WDLBar.tsx src/components/charts/WDLBarChart.tsx | wc -l</automated>
  </verify>
  <done>Both files use oklch(0.45 0.01 260) for draw color. No occurrences of 0.65 lightness remain. TypeScript compiles clean.</done>
</task>

</tasks>

<verification>
- `grep "oklch(0.45 0.01 260)" frontend/src/components/results/WDLBar.tsx frontend/src/components/charts/WDLBarChart.tsx` returns matches in both files
- No remaining references to `oklch(0.65` in either file
- `npm run build` succeeds
</verification>

<success_criteria>
Draw color lightness matches win/loss lightness (all 0.45) across both WDL components.
</success_criteria>

<output>
After completion, create `.planning/quick/260319-owl-make-draw-color-darker-grey-in-wdl-so-it/260319-owl-SUMMARY.md`
</output>
