---
quick_id: 260625-isp
title: "Phase 135 mobile UAT: full-width board + shared horizontal move list"
status: planned
---

# Quick Task 260625-isp

## Description

More UAT feedback for Phase 135 (TacticLineExplorer), **mobile only**:

1. Make the chessboard use the whole width of the viewport.
2. Replace the vertical move list (SanLadder) with a horizontal one, like the
   Openings move list (`board/MoveList.tsx`). Keep the blunder/mistake severity
   glyph and the colored depth-0 (punchline) move. Create a **shared component**.
3. The horizontal move list must be tall enough to show 3 lines of moves without
   scrolling.

Desktop layout is unchanged: it keeps the two-column board + vertical SanLadder
(it has the horizontal space for a side column). Existing desktop tests assert
SanLadder testids and stay green.

## Tasks

### Task 1 — Shared `HorizontalMoveList` component
- **Files:** `frontend/src/components/board/HorizontalMoveList.tsx` (new)
- **Action:** Extract the horizontal wrapping move-list shell from
  `MoveList.tsx` into a reusable presentational component. Generic item model
  (`HorizontalMoveItem`: ply, optional numberLabel, san, isCurrent, optional
  color override, dimmed flag, trailing node, testId, ariaLabel). Fixed-height
  scroll box via a `heightClass` prop (default matches Openings `h-12 sm:h-18`),
  auto-scroll to the current move, click-to-jump.
- **Verify:** `npx tsc -b` passes; component renders flat wrapping chips.
- **Done:** Component exists and is importable.

### Task 2 — Refactor Openings `MoveList` onto the shared component
- **Files:** `frontend/src/components/board/MoveList.tsx`
- **Action:** Build items from `moveHistory` (white move gets `N.` number label,
  black none) and render via `HorizontalMoveList`. Preserve `move-${ply}`
  testids, aria-labels, "No moves yet" empty state, and `h-12 sm:h-18` height.
- **Verify:** `npm test` (Openings tests, if any) + `tsc -b`.
- **Done:** MoveList is a thin wrapper; Openings UI unchanged.

### Task 3 — TacticLineExplorer mobile: full-width board + horizontal list
- **Files:** `frontend/src/components/library/TacticLineExplorer.tsx`
- **Action:** Mobile branch only — board full viewport width (stacked), controls
  below, then a horizontal move list (built from the active PV) tall enough for
  3 lines (`h-24`). Per-move decoration: punchline color (depth 0), payoff /
  flaw-lead-in dimmed, severity glyph (testid `tactic-san-flaw-severity-*`) on
  the allowed-line lead-in move, current-step highlight, click → `goToMove`.
  Remove the mobile board-column width constant. Desktop keeps SanLadder.
- **Verify:** `npm test` (TacticLineExplorer suite), `npm run lint`, `tsc -b`.
- **Done:** Mobile drawer shows full-width board + 3-line horizontal move list.

## must_haves
- Shared horizontal move-list component used by both Openings and the tactic explorer.
- Mobile board spans full drawer width; vertical ladder replaced by horizontal list.
- Severity glyph + colored punchline move preserved on mobile.
- 3 lines of moves visible without scrolling.
- All frontend tests + lint + tsc pass.
