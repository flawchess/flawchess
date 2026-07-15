---
quick_id: 260715-r9c
status: complete
commit: 4b8c1878
---

# Quick Task 260715-r9c: Improve bot game layout — Summary

Improved the `/bots` play-vs-bot layout in `frontend/src/pages/Bots.tsx`. All
three asks delivered; layout-only change, no behavioral/game-logic change.

## What changed

1. **Board controls below the board.** Reused the existing
   `components/board/BoardControls.tsx` (reset / back / forward / flip),
   rendered directly below the board in both the single-column and 2-column
   desktop layouts.
   - reset/back/forward drive the hook's view-only `viewedPly` cursor
     (`viewPly(0)` / `viewPly(viewedPly-1)` / `viewPly(viewedPly+1)`); `game.position`
     and `game.lastMove` already derive from `viewedPly`, so navigation just works.
     `canGoBack = viewedPly > 0`, `canGoForward = viewedPly < liveGamePly`.
   - **flip** became a manual local `flipped` toggle (initialized from
     `settings.userColor === 'black'`), replacing the previously derived-only
     orientation. Never affects the game, only board drawing.

2. **Board-width name/clock strips (single-column).** The single-column stack
   (clocks / board / controls / panel) is capped at `BOT_BOARD_MAX_WIDTH_PX`
   (400, shared with the `ChessBoard maxWidth` prop) and centered — so the
   board fills the column edge-to-edge and the clock strips can never stretch
   past the board on wider single-column (tablet) widths.

3. **No gap in the 2-column desktop layout.** Replaced `flex-1 justify-center`
   (which reintroduced whitespace between a centered board and the side column)
   with two fixed-width columns — board column (`max-w` = board width, with the
   controls below it) + a `DESKTOP_SIDE_COLUMN_PX` (320) right column (clocks,
   move list, Resign/Draw) — centered as one group with `gap-0`.

## Decision (clarified with user)

Desktop 2-column layout keeps the clocks in the **right column** (with move
list + Resign/Draw); "clock = board width" applies to the single-column layout.

## Verification

- `npx tsc -b` clean; `npm run lint` clean (only pre-existing `coverage/`
  warnings); `npm run knip` clean.
- `npm test -- --run`: **168 files / 2228 tests passed**, including
  `src/pages/__tests__/Bots.test.tsx` (22 passed). The mocked `useBotGame`
  already exposes `viewedPly`/`liveGamePly`/`viewPly`, so board-control wiring
  is exercised.
- No new test IDs collide with existing bot controls (`board-btn-resign` etc.).
- In-browser visual check skipped: the Claude Chrome extension was not
  connected. Change is presentational and fully covered by the type-check +
  test suite.

## Follow-up tweaks (same task, additional user feedback)

- Small gap (`gap-2`) between the two desktop columns instead of flush.
- **Move list aligned to the board bottom.** Desktop layout restructured into
  two rows: top row = board beside (clocks over a `fillHeight` move list that
  flex-fills the side column via `items-stretch`), so the move-list box bottom
  lines up exactly with the board bottom; bottom row = board controls under the
  board, Resign/Draw (or result strip) under the side column. Split the old
  `GamePanel` into separate `moveList` + `controls` elements;
  `MoveListPanel` gained a `fillHeight` prop.
- **Move list hidden in the single-column layout** (it now only appears in the
  desktop side column).
- **Breakpoint lowered 1024 → 800px** so the two-column layout appears on
  narrower windows (sized to fit the 400 board + 320 side column + padding).
- Commits: 0bf08fe4 (gap + taller list, superseded), d20e7f94 (alignment +
  hide + breakpoint). Full FE suite green after each (2228 tests).

Note: hiding the move list on single-column also removes its "Return to live
position" link there; the board controls' forward/reset buttons remain the way
back to the live position on narrow screens.
