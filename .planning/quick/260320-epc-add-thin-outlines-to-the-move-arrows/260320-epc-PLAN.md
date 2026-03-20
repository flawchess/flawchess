---
phase: quick-260320-epc
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - frontend/src/components/board/ChessBoard.tsx
autonomous: true
no_commit: true
must_haves:
  truths:
    - "Move arrows on the chessboard have visible thin outlines"
    - "Outlines improve arrow visibility against board squares of similar color"
  artifacts:
    - path: "frontend/src/components/board/ChessBoard.tsx"
      provides: "Arrow polygon with stroke outline"
      contains: "stroke"
  key_links: []
---

<objective>
Add thin outlines (SVG stroke) to the custom move arrows on the chessboard so they are visually distinct against board squares.

Purpose: Arrows can blend into similarly-colored squares; a thin dark outline provides clear edge definition.
Output: Updated ArrowOverlay component with stroke on each arrow polygon.
</objective>

<execution_context>
@/home/aimfeld/.claude/get-shit-done/workflows/execute-plan.md
@/home/aimfeld/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@frontend/src/components/board/ChessBoard.tsx
@frontend/src/lib/arrowColor.ts
</context>

<tasks>

<task type="auto">
  <name>Task 1: Add thin stroke outline to arrow polygons</name>
  <files>frontend/src/components/board/ChessBoard.tsx</files>
  <action>
In the ArrowOverlay component, add stroke properties to each `<polygon>` element:

1. Add a named constant for outline configuration near the existing arrow constants:
   - `ARROW_OUTLINE_COLOR = 'rgba(0, 0, 0, 0.5)'` — semi-transparent black for subtle edge definition
   - `ARROW_OUTLINE_WIDTH = 1` — thin 1px outline

2. On each `<polygon>` in the ArrowOverlay map, add:
   - `stroke={ARROW_OUTLINE_COLOR}`
   - `strokeWidth={ARROW_OUTLINE_WIDTH}`
   - `strokeLinejoin="round"` — smooth corners on the arrow shape

Do NOT change arrow fill colors, opacity, or dimensions. Only add the outline stroke.
  </action>
  <verify>
    <automated>cd /home/aimfeld/Projects/Python/chessalytics/frontend && npx tsc --noEmit && npm run build 2>&1 | tail -5</automated>
  </verify>
  <done>Arrow polygons have a thin dark outline via SVG stroke. Build passes without errors.</done>
</task>

</tasks>

<verification>
- `npm run build` succeeds
- Visual: arrows on the Openings page board show thin dark outlines around their edges
</verification>

<success_criteria>
- Arrow polygons render with a visible thin outline stroke
- No visual regression to arrow colors, thickness scaling, or opacity
- Frontend builds without errors
</success_criteria>

<output>
After completion, create `.planning/quick/260320-epc-add-thin-outlines-to-the-move-arrows/260320-epc-SUMMARY.md`
</output>
