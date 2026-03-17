---
phase: quick
plan: 260317-qjf
type: execute
wave: 1
depends_on: []
files_modified:
  - frontend/src/components/position-bookmarks/PositionBookmarkList.tsx
  - frontend/src/components/position-bookmarks/PositionBookmarkCard.tsx
autonomous: true
must_haves:
  truths:
    - "Suggest bookmarks button is the same size as the Bookmark button"
    - "Each bookmark card shows a color circle (white or black) to the left of the label"
  artifacts:
    - path: "frontend/src/components/position-bookmarks/PositionBookmarkList.tsx"
      provides: "Suggest bookmarks button with size=lg"
    - path: "frontend/src/components/position-bookmarks/PositionBookmarkCard.tsx"
      provides: "Color circle indicator on bookmark cards"
  key_links:
    - from: "PositionBookmarkCard"
      to: "bookmark.color"
      via: "color circle rendering"
      pattern: "rounded-full.*bg-(white|zinc)"
---

<objective>
Match the "Suggest bookmarks" button size to the "Bookmark" button, and add color indicator circles to bookmark cards.

Purpose: Visual consistency between buttons, and at-a-glance color identification on bookmarks.
Output: Updated PositionBookmarkList.tsx and PositionBookmarkCard.tsx
</objective>

<execution_context>
@/home/aimfeld/.claude/get-shit-done/workflows/execute-plan.md
@/home/aimfeld/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@frontend/src/components/position-bookmarks/PositionBookmarkList.tsx
@frontend/src/components/position-bookmarks/PositionBookmarkCard.tsx
@frontend/src/pages/Openings.tsx (lines 304-311 — color circle style reference)
@frontend/src/types/position_bookmarks.ts

<interfaces>
<!-- The Bookmark button in Openings.tsx uses size="lg": -->
```tsx
<Button variant="outline" size="lg" className="w-full" ...>
```

<!-- The Suggest bookmarks button currently has NO size prop (defaults to "default"): -->
```tsx
<Button variant="outline" className="w-full mt-2" ...>
```

<!-- Color circle style from "Played as" filter in Openings.tsx: -->
```tsx
<!-- White: -->
<span className="inline-block h-3 w-3 rounded-full border border-muted-foreground bg-white mr-1" />
<!-- Black: -->
<span className="inline-block h-3 w-3 rounded-full border border-muted-foreground bg-zinc-900 mr-1" />
```

<!-- PositionBookmarkResponse has color field: -->
```typescript
color: 'white' | 'black' | null;
```
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Match Suggest bookmarks button size and add color circles to bookmark cards</name>
  <files>
    frontend/src/components/position-bookmarks/PositionBookmarkList.tsx
    frontend/src/components/position-bookmarks/PositionBookmarkCard.tsx
  </files>
  <action>
1. In PositionBookmarkList.tsx, add `size="lg"` to the "Suggest bookmarks" Button (line 73) to match the Bookmark button which uses `size="lg"`.

2. In PositionBookmarkCard.tsx, add a color circle immediately to the LEFT of the bookmark label (both the display button and the editing input). Use the exact same circle style as the "Played as" filter in Openings.tsx:
   - White: `<span className="inline-block h-3 w-3 rounded-full border border-muted-foreground bg-white shrink-0" />`
   - Black: `<span className="inline-block h-3 w-3 rounded-full border border-muted-foreground bg-zinc-900 shrink-0" />`
   - If `bookmark.color` is null, do not render a circle.

   Place the circle inside the label+filter stacked div, in a horizontal flex wrapper around the circle and label. The circle should appear on the same line as the label text, to its left.

   Specifically, wrap the label area (the isEditing ternary, lines 104-124) in a `<div className="flex items-center gap-1.5">` containing:
   - The color circle (conditionally rendered based on bookmark.color)
   - The existing label button/input

   Add `data-testid={`bookmark-color-${bookmark.id}`}` to the circle span.
  </action>
  <verify>
    <automated>cd /home/aimfeld/Projects/Python/chessalytics/frontend && npx tsc --noEmit && npm run lint</automated>
  </verify>
  <done>
    - Suggest bookmarks button renders at the same size as the Bookmark button (both size="lg")
    - Each bookmark card with a non-null color shows a white or black circle to the left of the label
    - Circles use the same style as the "Played as" filter circles
  </done>
</task>

</tasks>

<verification>
- TypeScript compiles without errors
- Lint passes
- Visual: Suggest bookmarks and Bookmark buttons are same height
- Visual: Bookmark cards show color circles matching the Played as filter style
</verification>

<success_criteria>
Both buttons are visually consistent in size, and bookmark cards clearly indicate which color they were saved for via a circle indicator.
</success_criteria>

<output>
After completion, create `.planning/quick/260317-qjf-match-suggest-bookmarks-button-size-add-/260317-qjf-SUMMARY.md`
</output>
