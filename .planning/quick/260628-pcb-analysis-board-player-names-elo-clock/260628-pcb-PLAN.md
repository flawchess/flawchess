---
quick_id: 260628-pcb
status: complete
---

# Quick Task 260628-pcb: Analysis board player names + ELO + clock (desktop)

## Goal

On the desktop analysis board, show each player's name (with ELO in parentheses)
above and below the board on the left, and their remaining clock at the current
position on the right (clock icon + m:ss).

## Tasks

1. **PlayerBar component** — `frontend/src/components/board/PlayerBar.tsx`
   - One row: `■/□ Name (ELO)` left, `🕑 m:ss` right.
   - Local `formatClock` (m:ss, floored, clamped ≥0) per D-05 (no shared import).
   - Clock omitted when `clockSeconds == null` (imports without %clk).

2. **Wire into Analysis desktop layout** — `frontend/src/pages/Analysis.tsx`
   - `playerClocks` memo: derive per-side remaining clock from `gameData.eval_series`
     at the current ply (`evalChartPly`). Even ply = White, odd = Black (0-based on
     moves; matches `game_positions.ply` and `mainLine` indexing). Keep the latest
     clock ≤ current ply for each side.
   - `playerBar(color)` render helper pulling name/rating/clock from `gameData`.
   - Insert above and below `{boardRow}` in the board column, ordered by
     `boardFlipped` (top = opponent, bottom = the bottom-of-board player). Game mode
     only (`isGameMode && gameData`).

3. **Test** — `PlayerBar.test.tsx` (glyph, name fallback, ELO parens, m:ss
   formatting, zero-pad, negative clamp, clock hidden when null).

## Verification

- `npx tsc -b`, `npm run lint`, `npm run knip`, full `npm test` all green.
- Clock-parity memo validated against the live `/api/library/games/687479`
  response and cross-checked against the dev DB: at ply 69, White 0:24 / Black 1:32.
