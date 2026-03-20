---
phase: quick
plan: 260320-oiu
type: execute
wave: 1
depends_on: []
files_modified:
  - frontend/src/components/board/ChessBoard.tsx
  - frontend/src/lib/arrowColor.ts
autonomous: true
must_haves:
  truths:
    - "Grey arrows are always drawn beneath red and green arrows"
    - "Red and green arrows are never obscured by grey arrows"
  artifacts:
    - path: "frontend/src/components/board/ChessBoard.tsx"
      provides: "Arrow sorting by color priority in ArrowOverlay"
    - path: "frontend/src/lib/arrowColor.ts"
      provides: "Exported arrow color constants for sorting"
  key_links:
    - from: "frontend/src/components/board/ChessBoard.tsx"
      to: "frontend/src/lib/arrowColor.ts"
      via: "Import color constants for sort comparison"
      pattern: "import.*arrowColor"
---

<objective>
Sort board arrows so grey arrows render first (bottom layer), then red (middle), then green (top layer). This ensures informative win/loss colored arrows are never hidden beneath neutral grey arrows.

Purpose: Fix visual bug where grey arrows sometimes cover more important red/green arrows.
Output: Updated ArrowOverlay with color-priority sorting.
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
  <name>Task 1: Export color constants and sort arrows by render priority</name>
  <files>frontend/src/lib/arrowColor.ts, frontend/src/components/board/ChessBoard.tsx</files>
  <action>
1. In `frontend/src/lib/arrowColor.ts`, export the base color constants (GREEN, RED, GREY) and their hover variants (GREEN_HOVER, RED_HOVER, GREY_HOVER) so they can be imported for comparison. They are currently module-private `const` declarations — add `export` to each.

2. In `frontend/src/components/board/ChessBoard.tsx`, in the `ArrowOverlay` component:
   - Import the 6 color constants from `arrowColor.ts`.
   - Define a color priority map: grey/grey_hover = 0 (draw first), red/red_hover = 1, green/green_hover = 2 (draw last, on top).
   - Before the `arrows.map(...)` rendering loop, sort a copy of the arrows array by this priority (ascending, so grey first).
   - Use `[...arrows].sort(...)` to avoid mutating the prop.
   - The priority lookup should use a `Map<string, number>` or plain object keyed by the exact oklch color strings.
  </action>
  <verify>
    <automated>cd /home/aimfeld/Projects/Python/chessalytics/frontend && npx tsc --noEmit && npm run build</automated>
  </verify>
  <done>Grey arrows always render first (bottom SVG layer), red arrows second, green arrows last (top). TypeScript compiles without errors. Build succeeds.</done>
</task>

</tasks>

<verification>
- `npm run build` passes in frontend directory
- Visual: On Dashboard or Openings page with mixed arrow colors, green/red arrows are always visible on top of grey arrows
</verification>

<success_criteria>
Arrow rendering order is deterministic: grey (bottom) -> red (middle) -> green (top). No colored arrows are obscured by grey arrows.
</success_criteria>

<output>
After completion, create `.planning/quick/260320-oiu-draw-grey-arrows-first-then-red-then-gre/260320-oiu-SUMMARY.md`
</output>
