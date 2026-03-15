---
phase: quick-22
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - frontend/src/pages/Dashboard.tsx
  - frontend/src/components/filters/FilterPanel.tsx
autonomous: true
requirements: [QUICK-22]
must_haves:
  truths:
    - "Played as filter only shows White and Black options, no Any"
    - "Default filter color is white (not null)"
    - "Selecting White sets board orientation to white (not flipped)"
    - "Selecting Black sets board orientation to black (flipped)"
    - "Board flips automatically when Played as filter changes"
  artifacts:
    - path: "frontend/src/pages/Dashboard.tsx"
      provides: "Played as toggle without Any, board flip on color change"
    - path: "frontend/src/components/filters/FilterPanel.tsx"
      provides: "Updated DEFAULT_FILTERS with color: 'white' instead of null"
  key_links:
    - from: "Dashboard.tsx Played as onValueChange"
      to: "setBoardFlipped"
      via: "color change handler"
      pattern: "setBoardFlipped.*color"
---

<objective>
Remove the "Any" option from the "Played as" filter toggle and default to "white". When the user changes the Played as filter, automatically flip the board to match (white = not flipped, black = flipped).

Purpose: Simplify the color filter (Any is rarely useful) and sync board orientation with the selected color for a more intuitive experience.
Output: Updated Dashboard.tsx and FilterPanel.tsx with simplified color filter and auto-flip behavior.
</objective>

<execution_context>
@/home/aimfeld/.claude/get-shit-done/workflows/execute-plan.md
@/home/aimfeld/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@frontend/src/pages/Dashboard.tsx
@frontend/src/components/filters/FilterPanel.tsx
@frontend/src/types/api.ts
</context>

<interfaces>
From frontend/src/components/filters/FilterPanel.tsx:
```typescript
export interface FilterState {
  // ...
  color: Color | null; // null = any
}
export const DEFAULT_FILTERS: FilterState = {
  // ...
  color: null,
};
```

From frontend/src/types/api.ts:
```typescript
export type Color = 'white' | 'black';
```
</interfaces>

<tasks>

<task type="auto">
  <name>Task 1: Remove Any option from Played as filter and auto-flip board on color change</name>
  <files>frontend/src/pages/Dashboard.tsx, frontend/src/components/filters/FilterPanel.tsx</files>
  <action>
1. In `frontend/src/components/filters/FilterPanel.tsx`:
   - Change `DEFAULT_FILTERS.color` from `null` to `'white'`.
   - Change the `FilterState` type for `color` from `Color | null` to `Color` (remove null union and the `// null = any` comment).

2. In `frontend/src/pages/Dashboard.tsx`:
   - Remove the `<ToggleGroupItem value="any" ...>Any</ToggleGroupItem>` line (line ~324).
   - Update the `value` prop on the Played as ToggleGroup from `filters.color ?? 'any'` to just `filters.color`.
   - Update the `onValueChange` handler: instead of checking for 'any' and setting null, simply set the color and also flip the board. Replace the current handler with:
     ```typescript
     onValueChange={(v) => {
       if (!v) return;
       const color = v as Color;
       setFilters(prev => ({ ...prev, color }));
       setBoardFlipped(color === 'black');
     }}
     ```
   - Remove the `data-testid="filter-played-as-any"` toggle item.
   - In `handleLoadBookmark`, update the color assignment: change `color: bkm.color ?? null` to `color: bkm.color ?? 'white'` (fallback to white instead of null for legacy bookmarks).
   - Fix any TypeScript references that use `filters.color` with null checks — since color is now always 'white' or 'black', remove unnecessary null coalescing.

3. Ensure the initial board state is consistent: `boardFlipped` starts as `false` and `DEFAULT_FILTERS.color` is `'white'`, which is correct (white = not flipped).
  </action>
  <verify>
    <automated>cd /home/aimfeld/Projects/Python/chessalytics/frontend && npx tsc --noEmit && npm run lint</automated>
  </verify>
  <done>
    - Played as filter shows only "White" and "Black" toggle options
    - Default color is "white" (not null)
    - Changing Played as to "Black" flips the board; changing to "White" un-flips it
    - TypeScript compiles cleanly with no null-related color errors
    - ESLint passes
  </done>
</task>

</tasks>

<verification>
- `npx tsc --noEmit` passes (no type errors from removing null from Color field)
- `npm run lint` passes
- `npm run build` succeeds
</verification>

<success_criteria>
- Played as filter has exactly 2 options: White and Black
- Default selection is White with board not flipped
- Selecting Black flips the board; selecting White un-flips it
- No "Any" option visible anywhere in the UI
- All TypeScript and lint checks pass
</success_criteria>

<output>
After completion, create `.planning/quick/22-remove-any-option-from-played-as-filter-/22-SUMMARY.md`
</output>
