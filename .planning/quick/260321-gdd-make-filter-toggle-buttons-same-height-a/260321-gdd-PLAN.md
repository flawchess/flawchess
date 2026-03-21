---
phase: quick
plan: 260321-gdd
type: execute
wave: 1
depends_on: []
files_modified:
  - frontend/src/components/filters/FilterPanel.tsx
autonomous: true
requirements: []
must_haves:
  truths:
    - "Time control and Platform filter buttons have the same height as ToggleGroup items and Select dropdowns on mobile (44px / min-h-11)"
    - "On desktop (sm+), all filter controls remain compact at their current sizes"
  artifacts:
    - path: "frontend/src/components/filters/FilterPanel.tsx"
      provides: "Consistent height filter toggle buttons"
  key_links: []
---

<objective>
Make the custom toggle buttons (Time Control, Platform) in FilterPanel match the height of ToggleGroupItems and SelectTrigger on both mobile and desktop.

Purpose: Currently, Time Control and Platform buttons use `px-3 py-2 sm:px-2 sm:py-0.5` which produces a different (shorter) height than the `min-h-11 sm:min-h-0` pattern used by ToggleGroupItems (Rated, Opponent) and SelectTrigger (Recency). This creates visual inconsistency.
Output: All filter controls at uniform 44px height on mobile, compact on desktop.
</objective>

<execution_context>
@/home/aimfeld/.claude/get-shit-done/workflows/execute-plan.md
@/home/aimfeld/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@frontend/src/components/filters/FilterPanel.tsx
</context>

<tasks>

<task type="auto">
  <name>Task 1: Align custom filter button heights with ToggleGroup/Select heights</name>
  <files>frontend/src/components/filters/FilterPanel.tsx</files>
  <action>
In FilterPanel.tsx, update the className on both the Time Control buttons (line ~102) and Platform buttons (line ~126).

Current classes: `rounded border px-3 py-2 sm:px-2 sm:py-0.5 text-xs transition-colors`

Add `min-h-11 sm:min-h-0` to match the established mobile touch target pattern used by ToggleGroupItems and SelectTrigger in the same component. Keep existing padding as-is since min-h handles the height constraint.

Updated classes: `rounded border px-3 py-2 sm:px-2 sm:py-0.5 text-xs transition-colors min-h-11 sm:min-h-0`

This is the same pattern documented in STATE.md: "min-h-11 sm:min-h-0 on ToggleGroupItems individually for per-item 44px height on mobile".
  </action>
  <verify>
    <automated>cd /home/aimfeld/Projects/Python/chessalytics/frontend && npx tsc --noEmit 2>&1 | head -20</automated>
  </verify>
  <done>Time Control and Platform buttons have min-h-11 sm:min-h-0 matching ToggleGroupItems and SelectTrigger. All filter controls are visually consistent height on mobile (44px) and compact on desktop.</done>
</task>

</tasks>

<verification>
- `npm run build` succeeds
- Visual: on mobile viewport, all filter controls (Time Control buttons, Platform buttons, Rated toggle, Opponent toggle, Recency select) are the same height (44px)
- Visual: on desktop viewport, all controls remain compact
</verification>

<success_criteria>
All filter controls in FilterPanel render at uniform 44px height on mobile and compact height on desktop sm+ breakpoint.
</success_criteria>

<output>
After completion, create `.planning/quick/260321-gdd-make-filter-toggle-buttons-same-height-a/260321-gdd-SUMMARY.md`
</output>
