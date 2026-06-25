---
quick_id: 260625-isp
title: "Phase 135 mobile UAT: full-width board + shared horizontal move list"
status: complete
date: 2026-06-25
commit: 28427264
---

# Quick Task 260625-isp — Summary

Phase 135 (TacticLineExplorer) mobile UAT polish.

## What changed

1. **Full-width board on mobile.** The mobile drawer layout was a two-column
   split (board at 58% width, vertical SAN ladder beside it). It now stacks
   vertically: full-width board → BoardControls → horizontal move list. Removed
   the `MOBILE_BOARD_COLUMN_WIDTH` constant.

2. **Vertical ladder → horizontal move list (mobile).** Replaced `SanLadder`
   (mobile only) with a horizontal, wrapping move list styled like the Openings
   move list. It keeps the tactic-specific decorations:
   - colored depth-0 punchline move,
   - dimmed payoff / flaw-lead-in moves,
   - blunder/mistake severity glyph on the allowed-line flaw move
     (`tactic-san-flaw-severity-*` testid preserved),
   - current-step highlight + click-to-jump (`goToMove`).

3. **Shared component.** New `frontend/src/components/board/HorizontalMoveList.tsx`
   — a generic, presentational horizontal move list (item model with optional
   number label, color override, dimmed flag, trailing node, testId). Both the
   Openings `MoveList` and the tactic explorer mobile list now render through it.
   The `moveLabel` numbering helper moved to `frontend/src/lib/moveNumberLabel.ts`
   (shared by `SanLadder` + the tactic list; avoids a react-refresh lint error
   from exporting a function out of a component file).

4. **3 lines without scrolling.** The mobile list box height is `h-24` (≈96px),
   enough for 3 wrapped `text-sm` rows.

Desktop is unchanged: it keeps the two-column board + vertical `SanLadder`
(plenty of horizontal space for a side column).

## Files

- `frontend/src/components/board/HorizontalMoveList.tsx` (new — shared component)
- `frontend/src/components/board/MoveList.tsx` (refactored onto the shared component)
- `frontend/src/components/library/TacticLineExplorer.tsx` (mobile layout + list)
- `frontend/src/components/library/SanLadder.tsx` (moveLabel moved out)
- `frontend/src/lib/moveNumberLabel.ts` (new — shared numbering helper)

## Gates

- `npx tsc -b` clean
- `npm run lint` clean, `npm run knip` clean
- `npm test -- --run` 1136/1136 (incl. TacticLineExplorer 16/16)

## Commit

`28427264` on `gsd/phase-135-tactic-line-explorer-walkable-pv-stepper-for-tagged-flaws-se` (not pushed).

## Notes / follow-up

- HUMAN visual-verify on a real phone: full-width board, 3-line move list fits,
  punchline color + severity glyph visible, tap-to-jump works.
