---
type: quick
slug: tactic-explorer-desktop-horiz-move-list
created: 2026-06-25
---

# Quick Task: Desktop tactic-explorer horizontal move list

## Description

On desktop, the TacticLineExplorer (opened from game cards and flaw cards) should mirror
the mobile layout: replace the vertical `SanLadder` with the horizontal `HorizontalMoveList`
below the board controls, narrow the modal to fit the chessboard while letting it grow
taller, give the move list room for 3 wrapped lines, and stop truncating the missed/allowed
motif badges above the board (truncation is a mobile-only affordance).

## Changes

1. **`TacticMotifChip.tsx`** — add a `noTruncate` prop that disables the
   `MAX_PREFIXED_LABEL_CHARS` truncation of the `"{orientation}: {motif}"` label.

2. **`TacticLineExplorer.tsx`**
   - Desktop layout: single-column stacked (header → board → controls → horizontal move
     list), same as mobile. Remove the two-column board/ladder split.
   - Reuse `HorizontalMoveList` for both surfaces; rename `mobileMoveList` → `moveList` and
     `MOBILE_MOVE_LIST_HEIGHT` → `MOVE_LIST_HEIGHT` (3 wrapped lines, `h-24`).
   - Narrow the Dialog: `sm:max-w-4xl` → `sm:max-w-md`; keep `max-h-[90vh]` so it can grow
     taller for the move list.
   - Board uses `w-full aspect-square` on both surfaces.
   - Pass `noTruncate={!isMobile}` to the header badges.
   - Remove the dead `SanLadder` import + usage and the `DESKTOP_BOARD_COLUMN_WIDTH` const.

3. **Delete `SanLadder.tsx`** — its only consumer was the desktop ladder; knip fails if it
   becomes dead. Update the stale comment reference in `moveNumberLabel.ts`.

## Verification

- `npm run lint && npm test -- --run` (TacticLineExplorer suite + knip clean)
- `npx tsc -b` (type check, shared-type touch)
</content>
</invoke>
