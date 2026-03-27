---
phase: quick
plan: 260327-nbs
type: execute
wave: 1
depends_on: []
files_modified:
  - frontend/src/components/charts/EndgameConvRecovChart.tsx
autonomous: true
---

<objective>
Show game count alongside conversion/recovery percentages in the Conversion & Recovery chart tooltip. E.g. "73% (45 games)".
</objective>

<tasks>

<task type="auto">
  <name>Task 1: Add game counts to conv/recov chart tooltip</name>
  <files>frontend/src/components/charts/EndgameConvRecovChart.tsx</files>
  <action>
1. Add conversion_games and recovery_games to ConvRecovDataPoint interface
2. Pass them through in the data mapping from categories
3. Show game counts in tooltip: "Conversion: 73.0% (45 games)"
  </action>
  <done>Tooltip shows percentage with game count for both conversion and recovery</done>
</task>

</tasks>
