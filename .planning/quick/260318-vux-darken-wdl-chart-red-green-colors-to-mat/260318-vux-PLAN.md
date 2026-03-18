---
phase: quick
plan: 260318-vux
type: execute
wave: 1
depends_on: []
files_modified:
  - frontend/src/components/results/WDLBar.tsx
  - frontend/src/components/charts/WDLBarChart.tsx
  - frontend/src/components/stats/GlobalStatsCharts.tsx
  - frontend/src/components/move-explorer/MoveExplorer.tsx
autonomous: true
requirements: []
must_haves:
  truths:
    - "WDL green (win) and red (loss) bar colors are noticeably darker than before"
    - "Win/loss/draw colors have similar perceived brightness to the blue arrow hover color (#0a3d6b)"
    - "All WDL color usages are consistent across WDLBar, WDLBarChart, GlobalStatsCharts, and MoveExplorer tooltips"
  artifacts:
    - path: "frontend/src/components/results/WDLBar.tsx"
      provides: "Canonical WDL color constants"
      contains: "WDL_WIN"
    - path: "frontend/src/components/charts/WDLBarChart.tsx"
      provides: "WDL bar chart with darkened colors"
      contains: "oklch"
    - path: "frontend/src/components/stats/GlobalStatsCharts.tsx"
      provides: "Global stats WDL chart with darkened colors"
      contains: "oklch"
  key_links:
    - from: "frontend/src/components/results/WDLBar.tsx"
      to: "frontend/src/components/move-explorer/MoveExplorer.tsx"
      via: "WDL_WIN, WDL_DRAW, WDL_LOSS imports"
      pattern: "import.*WDL_WIN.*WDLBar"
---

<objective>
Darken the green (win) and red (loss) colors used in WDL charts and the Moves tab so they match the brightness/darkness of the blue arrow hover color (#0a3d6b) on the chessboard.

Purpose: The current green and red are too bright/saturated relative to the dark blue board arrows, creating visual inconsistency.
Output: All WDL color definitions updated to darker tones across all 4 files that define or use them.
</objective>

<execution_context>
@/home/aimfeld/.claude/get-shit-done/workflows/execute-plan.md
@/home/aimfeld/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@frontend/src/components/results/WDLBar.tsx
@frontend/src/components/charts/WDLBarChart.tsx
@frontend/src/components/stats/GlobalStatsCharts.tsx
@frontend/src/components/move-explorer/MoveExplorer.tsx
</context>

<tasks>

<task type="auto">
  <name>Task 1: Darken WDL win/loss colors across all components</name>
  <files>
    frontend/src/components/results/WDLBar.tsx
    frontend/src/components/charts/WDLBarChart.tsx
    frontend/src/components/stats/GlobalStatsCharts.tsx
  </files>
  <action>
The blue arrow hover color #0a3d6b converts to approximately oklch(0.30 0.07 245). The current WDL colors have lightness 0.55 for win/loss — far too bright by comparison. Darken them to approximately lightness 0.40-0.45 while keeping them distinct and readable against the dark UI background.

Update the three canonical color values:

1. In `frontend/src/components/results/WDLBar.tsx` — update the exported constants:
   - `WDL_WIN`: change from `oklch(0.55 0.18 145)` to `oklch(0.45 0.16 145)` (darker green, slightly less saturated)
   - `WDL_LOSS`: change from `oklch(0.55 0.2 25)` to `oklch(0.45 0.17 25)` (darker red, slightly less saturated)
   - `WDL_DRAW`: leave at `oklch(0.65 0.01 260)` (already a muted gray-blue, appropriate contrast)

2. In `frontend/src/components/charts/WDLBarChart.tsx` — update `chartConfig`:
   - `win_pct.color`: change to `oklch(0.45 0.16 145)`
   - `loss_pct.color`: change to `oklch(0.45 0.17 25)`
   - `draw_pct.color`: leave unchanged
   - Also update tooltip text classes from `text-green-500` to `text-green-600` and `text-red-500` to `text-red-600` so tooltip text matches the darker bar colors

3. In `frontend/src/components/stats/GlobalStatsCharts.tsx` — update `chartConfig`:
   - Same oklch changes as WDLBarChart
   - Same tooltip text class changes (`text-green-500` to `text-green-600`, `text-red-500` to `text-red-600`)

The MoveExplorer.tsx already imports WDL_WIN/WDL_DRAW/WDL_LOSS from WDLBar.tsx so it will pick up the changes automatically — no edits needed there.
  </action>
  <verify>
    <automated>cd /home/aimfeld/Projects/Python/chessalytics/frontend && npm run build 2>&1 | tail -5</automated>
  </verify>
  <done>
    - WDL_WIN and WDL_LOSS constants use oklch lightness ~0.45 (down from 0.55)
    - All three files (WDLBar, WDLBarChart, GlobalStatsCharts) use identical darker color values
    - Tooltip text classes use -600 variants instead of -500
    - Frontend builds without errors
  </done>
</task>

</tasks>

<verification>
- `npm run build` succeeds
- Grep confirms all oklch win/loss colors use lightness 0.45 consistently across all files
- No remaining references to the old `oklch(0.55 0.18 145)` or `oklch(0.55 0.2 25)` values
</verification>

<success_criteria>
WDL bar colors for wins and losses are visibly darker, matching the muted tone of the chessboard blue arrow color, while remaining distinguishable from each other and from the draw color.
</success_criteria>

<output>
After completion, create `.planning/quick/260318-vux-darken-wdl-chart-red-green-colors-to-mat/260318-vux-SUMMARY.md`
</output>
