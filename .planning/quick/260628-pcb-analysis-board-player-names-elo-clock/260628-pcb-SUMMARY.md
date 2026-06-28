---
quick_id: 260628-pcb
status: complete
---

# Quick Task 260628-pcb — Summary

Added player name + ELO and remaining clock to the **desktop** analysis board.

## Changes

- **New** `frontend/src/components/board/PlayerBar.tsx` — a player info row: `■/□ Name
  (ELO)` on the left, clock (lucide `Clock` icon + `m:ss`) on the right. Local
  `formatClock` (floored, clamped ≥ 0). Clock is hidden when `clockSeconds` is null
  (imports without a `%clk` annotation, e.g. some chess.com games).
- **`frontend/src/pages/Analysis.tsx`** —
  - `playerClocks` memo derives each side's remaining clock from `gameData.eval_series`
    at the current ply (`evalChartPly`): even ply = White, odd = Black (0-based on
    moves). Latest clock ≤ current ply wins per side.
  - `playerBar(color)` helper + two `PlayerBar` rows inserted above and below the board
    in the board column, ordered by `boardFlipped`. Game mode only.
  - **Engine-card alignment** (follow-up): an invisible spacer mirroring the top player
    bar is rendered at the top of the right column (desktop/`lg` only) so the Stockfish
    card top lines up with the board top rather than the player-bar top. `lg:-mb-2`
    trims the right column's `gap-4` to the board column's `gap-2` so the offsets match.
- **New** `frontend/src/components/board/__tests__/PlayerBar.test.tsx` — 8 tests.

## Verification

- `npx tsc -b` ✓, `npm run lint` ✓ (only pre-existing warnings in generated `coverage/`),
  `npm run knip` ✓, full `npm test` 1222 passed ✓.
- Integration cross-check: ran the exact `playerClocks` algorithm against the live
  `/api/library/games/687479` API response — White `aimfeld (1773)` / Black
  `Square1111 (1704)`, `user_color: white`. At ply 0: White 10:00, Black hidden; at
  ply 69: White 0:24 / Black 1:32 — matches the dev DB (`game_positions.clock_seconds`)
  exactly.

## Scope notes / follow-ups

- **Desktop only**, as requested. The mobile `/analysis` takeover (260628-cjp) does not
  show player bars; adding them there is a natural follow-up if wanted.
- A desktop browser screenshot wasn't captured: the Claude-in-Chrome window stayed
  locked at ~400px inner width (`resize_window` reported success but had no effect), so
  only the mobile tree rendered. Verified via the API/DB cross-check + unit tests instead.
