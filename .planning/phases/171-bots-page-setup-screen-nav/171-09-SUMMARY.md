---
phase: 171-bots-page-setup-screen-nav
plan: 09
subsystem: ui
tags: [react, bot-play, chessboard, gap-closure]

# Dependency graph
requires:
  - phase: 171
    plan: 08
    provides: "Bots.tsx handleAnalyze CTA and Bots.test.tsx harness this plan extends with a ChessBoard mock"
provides:
  - "useBotGame exposes UseBotGameState.lastMove, derived from viewedPly (not the live tail)"
  - "Bots.tsx's shared `board` const passes lastMove to ChessBoard, closing 171 UAT gap 2"
affects: [bots]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Single replay pass producing BOTH the displayed FEN and its originating move's from/to squares, mirroring useChessGame.ts's computeInitialChessState capture-on-final-iteration pattern"

key-files:
  created: []
  modified:
    - frontend/src/hooks/useBotGame.ts
    - frontend/src/hooks/__tests__/useBotGame.test.ts
    - frontend/src/pages/Bots.tsx
    - frontend/src/pages/__tests__/Bots.test.tsx

key-decisions:
  - "fenAtPly renamed to replayToPly and returns { fen, lastMove } from ONE replay pass, not a second useMemo — avoids double-replaying moveHistory on every render"
  - "lastMove derives from viewedPly, never the live tail, so scrubbing the move list moves the highlight with it (lichess/chess.com behavior); pinned by a dedicated anti-stale-highlight test"
  - "No snapshot/migration surface added — BotGameSnapshot stays PGN-based; lastMove is free on resume via the existing restoredHistory replay"
  - "Bots.test.tsx's Bots page test never queried board internals before this plan (confirmed zero `square-`/`chessboard` hits), so adding a ChessBoard stub mock was safe"

patterns-established: []

requirements-completed: [PLAY-10]

coverage:
  - id: D1
    description: "useBotGame's UseBotGameState gains lastMove: { from, to } | null, derived from viewedPly in the same useMemo as position. Null at ply 0 / fresh game; the user's move after they play; the bot's move after it replies; the ply-1 move (not the live tail) when scrubbed back via viewPly(1); null again at viewPly(0); the live tail again after returnToLive(); non-null on the first render of a resumed game."
    requirement: "PLAY-10"
    verification:
      - kind: unit
        ref: "frontend/src/hooks/__tests__/useBotGame.test.ts#last-move highlight (171 UAT gap 2)"
        status: pass
    human_judgment: false
  - id: D2
    description: "Bots.tsx's shared `board` const (consumed by both renderDesktopLayout and renderMobileLayout) passes lastMove={game.lastMove} to ChessBoard — a single edit satisfies mobile parity. Confirmed exactly one <ChessBoard call site exists."
    requirement: "PLAY-10"
    verification:
      - kind: unit
        ref: "frontend/src/pages/__tests__/Bots.test.tsx#Bot board passes lastMove through to ChessBoard (171 UAT gap 2)"
        status: pass
    human_judgment: false

duration: 8min
completed: 2026-07-14
status: complete
---

# Phase 171 Plan 09: Bot board last-move highlight Summary

**`useBotGame` now derives and exposes `lastMove` from `viewedPly` in the same replay pass as `position`, and `Bots.tsx`'s shared board const wires it into `ChessBoard`, so the bot board highlights the last played move in the app's standard yellow — following the move list, not the live tail.**

## Performance

- **Duration:** ~8 min
- **Started:** 2026-07-14
- **Completed:** 2026-07-14T17:09:47+02:00
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- `fenAtPly` renamed to `replayToPly`, now returning `{ fen, lastMove }` from a single replay pass — no double-replay of `moveHistory` on every render
- `UseBotGameState.lastMove` derives from `viewedPly` (not the live tail), pinned by a dedicated anti-stale-highlight test that reverts the derivation and confirms it fails
- Resume works for free: `BotGameSnapshot` stays PGN-based, `lastMove` is computed from the existing `restoredHistory` replay with no snapshot/migration change
- `Bots.tsx`'s shared `board` const passes `lastMove={game.lastMove}` to `ChessBoard`, satisfying desktop + mobile parity in one edit
- `Bots.test.tsx` gained a `ChessBoard` stub (`data-testid="chessboard"`, `data-last-move`) and a `lastMove` field on the pre-existing `FakeGameHandle`/mock factory — the assertion boundary the plan called out as non-trivial plumbing
- Both wiring points mutation-verified: reverting `useBotGame`'s viewedPly-derivation to a live-tail derivation, and deleting the `lastMove` prop in `Bots.tsx`, each turned the specific pinning test red (confirmed, then reverted before committing)
- `ChessBoard.tsx` and `theme.ts` are unmodified — no new colour constant introduced, per the plan's reuse mandate

## Task Commits

Each task was committed atomically (TDD RED → GREEN per task):

1. **Task 1: useBotGame derives and exposes lastMove from viewedPly**
   - `48fdd051` test(171-09): add failing tests for bot board last-move highlight
   - `35229f55` feat(171-09): expose lastMove from useBotGame, derived from viewedPly
2. **Task 2: Pass lastMove to the bot board (desktop + mobile in one edit)**
   - `ab12261b` test(171-09): add failing test for bot board lastMove wiring
   - `9f461295` feat(171-09): pass lastMove from useBotGame to the bot board

_Note: both tasks are TDD — test commit written and confirmed red (verified via `npm test`) before the implementation commit._

## Files Created/Modified
- `frontend/src/hooks/useBotGame.ts` — `replayToPly` (renamed from `fenAtPly`, now also captures from/to), `UseBotGameState.lastMove`, `position`/`lastMove` destructured from the one `useMemo`, added to the hook's return object
- `frontend/src/hooks/__tests__/useBotGame.test.ts` — `describe('last-move highlight (171 UAT gap 2)')`, 7 tests
- `frontend/src/pages/Bots.tsx` — the shared `board` const gains `lastMove={game.lastMove}`
- `frontend/src/pages/__tests__/Bots.test.tsx` — `ChessBoard` stub mock, `FakeGameHandle.lastMove` field + mock-factory read + `beforeEach` reset, `describe('Bot board passes lastMove through to ChessBoard (171 UAT gap 2)')`, 2 tests

## Decisions Made
- Single replay pass (not a second `useMemo`) produces both `position` and `lastMove` — avoids re-walking `moveHistory` twice per render
- `lastMove` derives from `viewedPly`, never the live tail — lichess/chess.com behavior, consistent with `useChessGame`'s own `currentPly`-derived `lastMove`
- No snapshot type change — `lastMove` is a pure derived value, free on resume via `restoredHistory`

## Deviations from Plan

None — plan executed exactly as written, including both required mutation checks (viewedPly-to-live-tail reversion in `useBotGame.ts`, `lastMove` prop deletion in `Bots.tsx`), each confirmed red then restored before committing.

## Issues Encountered

None.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

Gap 2 of the 171 UAT (minor, test 3) is closed. One more gap-closure plan (171-10) remains from the UAT diagnosis session per `.planning/phases/171-bots-page-setup-screen-nav/171-UAT.md`.

---
*Phase: 171-bots-page-setup-screen-nav*
*Completed: 2026-07-14*
