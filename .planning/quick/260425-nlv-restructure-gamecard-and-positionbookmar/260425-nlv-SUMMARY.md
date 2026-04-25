---
quick_id: 260425-nlv
description: Restructure GameCard and PositionBookmarkCard layouts (full-width identifier line on top, board left + content right below)
date: 2026-04-25
status: complete
---

# Quick Task 260425-nlv — Summary

## What changed

### `frontend/src/components/results/GameCard.tsx` (commit `67c20cd`)
- Outer container: `flex gap-3 items-center` → `flex flex-col gap-2`. All other classes preserved (`border-l-4`, `BORDER_CLASSES[user_result]`, `charcoal-texture`, `border border-border/20`, `rounded`, `px-4 py-3`, `data-testid`).
- Top row (full width): result badge + always-visible `■ White (rating) vs □ Black (rating)` + platform icon/link with `ml-auto`.
- Dropped the `sm:hidden` mobile-only opponent variant and the `hidden sm:inline` qualifier on the desktop variant — single always-visible line at all breakpoints.
- New body row `flex gap-3 items-start` containing `LazyMiniBoard` (left) and right column `flex-1 min-w-0 flex flex-col gap-2` with the opening-name row and metadata row.
- Removed unused locals: `opponentName`, `opponentRating`, `opponentColorSymbol`.
- Removed `mt-2` from inner rows (parent `gap-2` now handles spacing).

### `frontend/src/components/position-bookmarks/PositionBookmarkCard.tsx` (commit `5a7ad30`)
- Outer container: `flex items-center gap-2` → `flex flex-col gap-2`. `setNodeRef`, `style`, `{...attributes}`, `data-testid` preserved.
- Top row (full width, `flex items-center gap-1.5`): drag handle (now carrying `{...listeners}`) + color circle + label button/input.
- Label button uses Tailwind `truncate` with `min-w-0 flex-1`; renders `bookmark.label` directly. `title={bookmark.label}` still surfaces full text on hover.
- Editing input gets `flex-1` so it fills the available row width.
- New body row `flex gap-2 items-start` containing the existing MiniBoard wrapper (left) and right column `flex-1 min-w-0 flex flex-col gap-1` with the piece-filter ToggleGroup and button row.
- Removed `mt-1` from button row (parent `gap-1` now handles spacing).
- Deleted `MAX_DISPLAY_LABEL_LENGTH` constant and the `truncateLabel` function (with its docstring) at module scope.

## Preserved across both files
- All `data-testid` attributes on the same elements.
- All `aria-label` attributes.
- dnd-kit `useSortable` bindings (outer holds `setNodeRef`/`style`/`attributes`; drag handle holds `listeners`).
- Inline-edit handlers (`handleLabelClick`, `handleLabelBlur`, `handleLabelKeyDown`) and `isDirtyRef` pattern.
- Lazy mini-board IntersectionObserver; platform-link Tooltip; Result badge classes.
- Chess.com/lichess platform icon and external-link tooltip.

## Trade-off (accepted upfront)
Dropping `truncateLabel` means long bookmark labels truncate via CSS ellipsis, no longer preserving the trailing ECO suffix (e.g. `(B12)`). The full label is still available via the hover `title` tooltip and via the inline-edit input on click. The user explicitly chose this in plan-mode discussion.

## Verification
- `cd frontend && npm run lint` → 0 errors (3 warnings are pre-existing in `coverage/` artifacts).
- `cd frontend && npx tsc --noEmit` → exit 0, no errors.
- Visual verification (`npm run dev` at `/results` and `/openings → Bookmarks panel`) is left to the user, including 360px-viewport check, drag-reorder smoke test, and inline label-edit smoke test.

## Commits
- `67c20cd` — refactor(ui): GameCard full-width identifier line + body row layout
- `5a7ad30` — refactor(ui): PositionBookmarkCard full-width label line + CSS truncate
