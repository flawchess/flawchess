---
phase: quick-260425-nlv
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - frontend/src/components/results/GameCard.tsx
  - frontend/src/components/position-bookmarks/PositionBookmarkCard.tsx
autonomous: true
requirements:
  - QUICK-260425-NLV
must_haves:
  truths:
    - "GameCard outer container is a vertical flex (flex flex-col gap-2); top row contains result badge, both player names, and platform link spanning full card width; mini board sits below-left with opening + metadata below-right."
    - "GameCard no longer renders a separate sm:hidden 'opponent only' line — the always-visible '■ White (rating) vs □ Black (rating)' format applies at all breakpoints."
    - "GameCard no longer derives opponentName, opponentRating, or opponentColorSymbol locally."
    - "PositionBookmarkCard outer container is a vertical flex (flex flex-col gap-2); top row contains drag handle, color circle, and label spanning full card width; mini board sits below-left with piece-filter ToggleGroup and button row below-right."
    - "PositionBookmarkCard truncates long labels via the Tailwind `truncate` utility (with min-w-0); truncateLabel function and MAX_DISPLAY_LABEL_LENGTH constant are deleted."
    - "All data-testid attributes, aria-labels, dnd-kit sortable bindings, and inline-edit handlers are preserved unchanged."
    - "Frontend lint and type-check pass after the refactor."
  artifacts:
    - path: "frontend/src/components/results/GameCard.tsx"
      provides: "GameCard with full-width identifier line on top and board+content body row below"
    - path: "frontend/src/components/position-bookmarks/PositionBookmarkCard.tsx"
      provides: "PositionBookmarkCard with full-width label line on top, board+controls body row below, and CSS-only label truncation"
  key_links:
    - from: "GameCard.tsx outer container"
      to: "result-color stripe"
      via: "border-l-4 + BORDER_CLASSES[user_result] preserved on outer flex flex-col"
      pattern: "border-l-4.*BORDER_CLASSES"
    - from: "PositionBookmarkCard.tsx outer container"
      to: "dnd-kit useSortable"
      via: "setNodeRef, style, attributes stay on outer; {...listeners} moves to drag handle in top row"
      pattern: "setNodeRef|listeners"
---

<objective>
Restructure two card components so the identifier line spans the full card width on top, with the mini chessboard on the left and the rest of the content on the right below.

- **GameCard** (`frontend/src/components/results/GameCard.tsx`): top row = result badge + both player names + platform link. Body row = mini board left, opening + metadata right.
- **PositionBookmarkCard** (`frontend/src/components/position-bookmarks/PositionBookmarkCard.tsx`): top row = drag handle + color circle + label. Body row = mini board left, piece-filter ToggleGroup + button row right.

Frontend-only refactor. No backend, no API, no DB changes.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
</execution_context>

<context>
@CLAUDE.md
@frontend/src/components/results/GameCard.tsx
@frontend/src/components/position-bookmarks/PositionBookmarkCard.tsx
</context>

<tasks>

<task type="auto">
  <name>Task 1: Restructure GameCard.tsx layout</name>
  <files>frontend/src/components/results/GameCard.tsx</files>
  <action>
  Change the outer container of `GameCard` from a horizontal flex (`flex gap-3 items-center`) to a vertical flex (`flex flex-col gap-2`). Keep all other classes on the outer container — `border-l-4`, `BORDER_CLASSES[game.user_result]`, `charcoal-texture`, `border border-border/20`, `rounded`, `px-4 py-3`, and the `data-testid={`game-card-${game.game_id}`}`.

  **Top row (full width)** — preserve the existing Row 1 markup, with the following changes:
  - Drop the `sm:hidden` mobile-only variant `<span>` (the "opponent only" line).
  - Make the desktop variant (`hidden sm:inline`) the always-visible variant by removing those classes — it now renders at all breakpoints.
  - Keep the result badge, the always-visible "■ White (rating) vs □ Black (rating)" line, and the right-aligned platform icon + external link (with `ml-auto`).

  **Body row** — wrap the existing LazyMiniBoard and the existing right column in a new `<div className="flex gap-3 items-start">`:
  - Left child: existing `<LazyMiniBoard ... />` block (unchanged).
  - Right child: a new `<div className="flex-1 min-w-0 flex flex-col gap-2">` containing the existing Row 2 (opening name) and Row 3 (metadata) blocks. Drop the `mt-2` from those two inner divs since the parent `gap-2` now handles spacing.

  Remove the now-unused local derivations near the top of the component: `opponentName`, `opponentRating`, `opponentColorSymbol`. Keep `whiteName`, `blackName`, `whiteRating`, `blackRating` since the always-visible line uses them.

  Preserve every existing `data-testid` (game-card-{id}, game-card-link-{id}, game-card-opening-{id}, game-card-tc-{id}, game-card-termination-{id}) and `aria-label` on the same elements. Do not change icons, copy, or formatting helpers.
  </action>
  <verify>
    <automated>cd frontend && npm run lint && npx tsc --noEmit</automated>
    <manual>npm run dev → /results: identifier line spans the full card width; mini board sits below-left; opening + metadata sit below-right; the colored result left-border still spans the entire card height; platform link still right-aligned. Verify at ~360px viewport: no horizontal overflow.</manual>
  </verify>
  <done>
    - Outer container: `flex flex-col gap-2` (plus preserved border/padding/data-testid)
    - Single top row with result badge + both players + platform link (no sm:hidden / hidden sm:inline pair)
    - Body row: `flex gap-3 items-start` with LazyMiniBoard + right column (`flex-1 min-w-0 flex flex-col gap-2`)
    - `opponentName`, `opponentRating`, `opponentColorSymbol` local derivations removed
    - `mt-2` removed from inner rows; spacing comes from parent `gap-2`
    - All existing `data-testid` and `aria-label` attributes preserved
    - `npm run lint` and `npx tsc --noEmit` pass
  </done>
</task>

<task type="auto">
  <name>Task 2: Restructure PositionBookmarkCard.tsx layout</name>
  <files>frontend/src/components/position-bookmarks/PositionBookmarkCard.tsx</files>
  <action>
  Change the outer container of `PositionBookmarkCard` from a horizontal flex (`flex items-center gap-2`) to a vertical flex (`flex flex-col gap-2`). Keep `setNodeRef`, `style`, `{...attributes}`, the existing classes (`rounded-md bg-card px-3 py-2`), and `data-testid={`bookmark-card-${bookmark.id}`}` on the outer container. The dnd-kit sortable bindings stay on the outer.

  **Top row (full width)** — a new `<div className="flex items-center gap-1.5">` containing, in order:
  1. The drag handle `<span>` (with `{...listeners}`, the `cursor-grab touch-none select-none text-muted-foreground shrink-0` classes, and the `aria-label="Drag to reorder"`). It moves from the outer container into this top row.
  2. The existing color-circle `<span>` (when `bookmark.color` is truthy) — unchanged.
  3. The label button OR input (the `isEditing` ternary). Apply Tailwind `truncate` and `min-w-0` to the button so the label can ellipsis-overflow inside its flex row. Keep `title={bookmark.label}` for the hover tooltip. Render `bookmark.label` directly — do not call `truncateLabel`.

  **Body row** — a new `<div className="flex gap-2 items-start">` containing:
  - Left child: the existing MiniBoard wrapper `<div>` (with `shrink-0`, `data-testid={`bookmark-mini-board-${bookmark.id}`}`, the `style={{ opacity: ..., transition: ... }}` attribute, and the `<MiniBoard fen={bookmark.fen} flipped={bookmark.is_flipped} size={84} />` inside) — unchanged.
  - Right child: a new `<div className="flex-1 min-w-0 flex flex-col gap-1">` containing the existing piece-filter ToggleGroup block and the existing button row `<div className="flex items-center justify-between">`. Drop the `mt-1` from the button row since the parent `gap-1` now handles spacing.

  **Delete** at module scope:
  - The `MAX_DISPLAY_LABEL_LENGTH` constant.
  - The `truncateLabel` function and its docstring/comment.

  Preserve every existing `data-testid` (bookmark-card-{id}, bookmark-mini-board-{id}, bookmark-color-{id}, bookmark-label-input-{id}, bookmark-label-{id}, bookmark-match-side-{id}, bookmark-match-side-{id}-mine|opponent|both, bookmark-chart-toggle-{id}, bookmark-btn-load-{id}, bookmark-btn-delete-{id}) and `aria-label` on the same elements. Inline-edit handlers (`handleLabelClick`, `handleLabelBlur`, `handleLabelKeyDown`) and the `isDirtyRef`/`onMouseDown` patterns remain unchanged. Do not change `useSortable`, mutations, or any other logic.
  </action>
  <verify>
    <automated>cd frontend && npm run lint && npx tsc --noEmit</automated>
    <manual>npm run dev → /openings, open Bookmarks panel: label line spans the full card width with ellipsis on long labels (full text in hover tooltip); drag-and-drop reorder still works (handle now in top row); mini board sits below-left; toggle + button row sit below-right; inline label edit still works (click → input → Enter saves, Escape reverts). Verify at ~360px viewport: no horizontal overflow.</manual>
  </verify>
  <done>
    - Outer container: `flex flex-col gap-2` with `setNodeRef`/`style`/`{...attributes}` preserved
    - Top row: drag handle (with `{...listeners}`) + color circle + label button/input, all in one `flex items-center gap-1.5` row
    - Label button uses Tailwind `truncate` + `min-w-0` and renders `bookmark.label` directly; `title={bookmark.label}` retained
    - Body row: `flex gap-2 items-start` with MiniBoard + right column (`flex-1 min-w-0 flex flex-col gap-1`)
    - `MAX_DISPLAY_LABEL_LENGTH` constant removed
    - `truncateLabel` function removed
    - `mt-1` removed from button row; spacing comes from parent `gap-1`
    - All existing `data-testid` and `aria-label` attributes preserved
    - dnd-kit sortable still works (outer container holds `setNodeRef`/`style`/`attributes`; drag handle holds `listeners`)
    - Inline label edit still works
    - `npm run lint` and `npx tsc --noEmit` pass
  </done>
</task>

</tasks>

<verification>
After both tasks complete, from `frontend/`:

```
npm run lint
npx tsc --noEmit
```

Both must pass with zero errors. Visually confirm via `npm run dev`:

1. **/results** — GameCard: identifier line full-width on top, mini board below-left, opening + metadata below-right, colored result left-border spans the whole card.
2. **/openings → Bookmarks panel** — PositionBookmarkCard: drag handle + label line full-width on top, mini board below-left, toggle + buttons below-right. Drag-reorder and inline label edit still work.
3. Resize to ~360px width — both cards remain readable with no horizontal overflow.
</verification>

<success_criteria>
- Both files committed with the new vertical-flex layout
- GameCard's `sm:hidden`/`hidden sm:inline` player-name pair collapsed into a single always-visible line
- `opponentName`, `opponentRating`, `opponentColorSymbol`, `truncateLabel`, `MAX_DISPLAY_LABEL_LENGTH` removed
- All `data-testid` and `aria-label` attributes preserved on the same elements
- dnd-kit reorder, inline label edit, lazy mini-board observer, and platform link all still work
- `npm run lint` and `npx tsc --noEmit` pass
</success_criteria>

<output>
After completion, create `.planning/quick/260425-nlv-restructure-gamecard-and-positionbookmar/260425-nlv-SUMMARY.md` summarizing what was changed in each file with frontmatter `status: complete`.
</output>
