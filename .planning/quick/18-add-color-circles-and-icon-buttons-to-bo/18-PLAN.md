---
phase: quick-18
plan: 1
type: execute
wave: 1
depends_on: []
files_modified:
  - frontend/src/components/position-bookmarks/PositionBookmarkCard.tsx
autonomous: true
requirements: [QUICK-18]
must_haves:
  truths:
    - "Bookmark card shows filled circle for played-as-white"
    - "Bookmark card shows empty circle for played-as-black"
    - "Bookmark card shows half-filled circle for played-as-any (color=null)"
    - "Load button is an icon button instead of text"
    - "Delete button shows a trashcan icon instead of 'x'"
  artifacts:
    - path: "frontend/src/components/position-bookmarks/PositionBookmarkCard.tsx"
      provides: "Updated bookmark card with color circles and icon buttons"
  key_links: []
---

<objective>
Add color indicator circles and icon buttons to PositionBookmarkCard.

Purpose: Visual consistency with GameCard's circle convention and cleaner icon-based actions.
Output: Updated PositionBookmarkCard.tsx with color circles and lucide-react icon buttons.
</objective>

<execution_context>
@/home/aimfeld/.claude/get-shit-done/workflows/execute-plan.md
@/home/aimfeld/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@frontend/src/components/position-bookmarks/PositionBookmarkCard.tsx
@frontend/src/components/results/GameCard.tsx
@frontend/src/types/position_bookmarks.ts

<interfaces>
From frontend/src/types/position_bookmarks.ts:
```typescript
export interface PositionBookmarkResponse {
  id: number;
  label: string;
  color: 'white' | 'black' | null;  // null = any color
  // ... other fields
}
```

From frontend/src/components/results/GameCard.tsx (circle convention):
```typescript
// White player uses filled circle: ●
// Black player uses empty circle: ○
```

lucide-react icons available in project: Upload, Trash2, ExternalLink, X, etc.
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Add color circles and replace text buttons with icon buttons</name>
  <files>frontend/src/components/position-bookmarks/PositionBookmarkCard.tsx</files>
  <action>
Modify PositionBookmarkCard.tsx:

1. Import `Upload` and `Trash2` from `lucide-react`.

2. Add a color indicator circle between the drag handle and the label. Use the bookmark's `color` field:
   - `color === 'white'`: filled circle `●` (like GameCard white player)
   - `color === 'black'`: empty circle `○` (like GameCard black player)
   - `color === null` (any): half-filled circle `◐`
   Style: `text-muted-foreground shrink-0 text-sm` class on a span. Add `data-testid="bookmark-color-{bookmark.id}"` and `aria-label` describing the color ("Played as white", "Played as black", "Played as any").

3. Replace the "Load" text Button with an icon-only button using `Upload` icon (size 14-16px). Keep variant="ghost", size="icon" (use h-7 w-7). Add `aria-label="Load bookmark"` per CLAUDE.md rules. Keep existing `data-testid`, `onMouseDown`, and `onClick` handlers.

4. Replace the "x" text in the Delete Button with `Trash2` icon (size 14-16px). Keep variant="ghost", size="icon" (use h-7 w-7). Keep existing `data-testid`, `aria-label`, `onMouseDown`, `onClick`, `disabled` props. Keep the `hover:text-destructive` styling.
  </action>
  <verify>
    <automated>cd /home/aimfeld/Projects/Python/chessalytics/frontend && npx tsc --noEmit && npm run lint</automated>
  </verify>
  <done>Bookmark cards display color indicator circles (filled/empty/half) matching the GameCard convention, Load button is an Upload icon, Delete button is a Trash2 icon. All interactive elements have data-testid and aria-label attributes.</done>
</task>

</tasks>

<verification>
- TypeScript compiles without errors
- ESLint passes
- Visual check: bookmark cards show circle indicators and icon buttons
</verification>

<success_criteria>
- Each bookmark card shows the appropriate circle based on its color field
- Load and Delete are icon-only buttons with proper accessibility attributes
- No regressions in existing bookmark functionality (edit label, drag reorder, load, delete)
</success_criteria>

<output>
After completion, create `.planning/quick/18-add-color-circles-and-icon-buttons-to-bo/18-SUMMARY.md`
</output>
