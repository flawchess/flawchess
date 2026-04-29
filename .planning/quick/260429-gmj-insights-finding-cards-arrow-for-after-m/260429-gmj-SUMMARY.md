---
phase: quick-260429-gmj
plan: 01
subsystem: frontend/insights
tags: [insights, arrows, mini-board, openings, ux]
requires: []
provides:
  - "frontend/src/lib/sanToSquares.ts: SAN → {from,to} helper"
  - "frontend/src/components/board/arrowGeometry.ts: shared squareToCoords + buildArrowPath"
  - "frontend/src/components/board/MiniBoard.tsx: optional arrows prop with thin SVG overlay"
affects:
  - "frontend/src/components/insights/OpeningFindingCard.tsx (renders arrow on each finding card)"
  - "frontend/src/components/board/ChessBoard.tsx (now imports geometry from arrowGeometry.ts)"
key-files:
  created:
    - frontend/src/lib/sanToSquares.ts
    - frontend/src/lib/sanToSquares.test.ts
    - frontend/src/components/board/arrowGeometry.ts
  modified:
    - frontend/src/components/board/MiniBoard.tsx
    - frontend/src/components/board/LazyMiniBoard.tsx
    - frontend/src/components/board/ChessBoard.tsx
    - frontend/src/components/insights/OpeningFindingCard.tsx
    - frontend/src/components/insights/OpeningFindingCard.test.tsx
decisions:
  - "Extract squareToCoords + buildArrowPath into arrowGeometry.ts so MiniBoard and ChessBoard share one geometry implementation (CLAUDE.md single-implementation rule)"
  - "MiniBoard arrows use FIXED proportions (shaft 0.07, head 0.22, head ratio 0.7) distinct from ChessBoard's normalized 0–1 scale — fine, decorative, no width modulation"
  - "MockIntersectionObserver in OpeningFindingCard.test.tsx now fires its callback synchronously on observe() so LazyMiniBoard mounts during tests (option (a) from PLAN.md)"
metrics:
  duration: 6m
  tasks_completed: 2
  files_changed: 9
  completed: 2026-04-29
---

# Quick Task 260429-gmj: Insights Finding Cards — score-colored after-move arrow Summary

Each Insights finding card now renders a fine, score-colored arrow on its mini board pointing from the candidate move's source square to its target square — making the "what moved and how did it score" answerable at a glance without reading SAN text.

## What was built

- **`sanToSquares(fen, san)` helper** in `frontend/src/lib/sanToSquares.ts`. Wraps a `new Chess(fen).move(san)` call in try/catch; returns `{ from, to }` on success or `null` on illegal SAN, malformed FEN, or any other chess.js exception. Lets call sites consume the result with a simple ternary instead of try/catch.

- **Shared `arrowGeometry.ts`** in `frontend/src/components/board/`. Hosts `squareToCoords` and `buildArrowPath`, the SVG-arrow math that previously lived only in `ChessBoard.tsx`. Both `ChessBoard.tsx` and the new `MiniBoard` overlay import from this single source — the CLAUDE.md "single implementation" rule that the shared `query_utils.py` follows on the backend.

- **`MiniBoard` arrow overlay**. Accepts an optional `arrows?: ReadonlyArray<{ from, to, color }>` prop. When non-empty, renders an absolutely-positioned `<svg data-testid="mini-board-arrow-overlay">` sibling layered over the Chessboard with one `<path>` per arrow. Geometry constants live as named module-top constants (`MINI_SHAFT_WIDTH = 0.07`, `MINI_HEAD_WIDTH = 0.22`, `MINI_HEAD_LENGTH_RATIO = 0.7`, `MINI_ARROW_OPACITY = 0.85`, `MINI_TIP_OVERSHOOT = 0.10`). Skips degenerate same-square arrows defensively. SVG is `pointerEvents: 'none'` so card buttons stay clickable.

- **`LazyMiniBoard` forwards arrows**. Same prop signature added and passed straight through to `<MiniBoard>`.

- **`OpeningFindingCard` wiring**. Computes `moveSquares = sanToSquares(finding.entry_fen, finding.candidate_move_san)` once, builds an `arrows` array with `color: borderLeftColor` (the same hex from `getSeverityBorderColor` that tints the card's left border), and passes it to BOTH the `sm:hidden` mobile branch and the `hidden sm:flex` desktop branch (CLAUDE.md "Always apply changes to mobile too"). When `moveSquares` is null, `arrows` is `undefined` and the card simply renders without an overlay.

## Tests

- `sanToSquares.test.ts` — 7 cases: starting-position e4, Nc3, kingside castling for white and black, illegal SAN (xx99), illegal-in-FEN move (Nxd4 from start), malformed FEN. All ensure no exception escapes.

- `OpeningFindingCard.test.tsx` — added `describe('Quick task 260429-gmj — score-colored after-move arrow')` block:
  - **Test A**: arrow overlay renders in BOTH mobile and desktop branches (`getAllByTestId('mini-board-arrow-overlay').length === 2`).
  - **Test B** (parameterized over 4 combos): arrow `<path>` `fill` attribute equals `getSeverityBorderColor(classification, severity)` — `weakness/major → DARK_RED`, `weakness/minor → LIGHT_RED`, `strength/major → DARK_GREEN`, `strength/minor → LIGHT_GREEN`. Robust to jsdom hex/rgb normalization.
  - **Test C**: illegal SAN ("Zz9") → card renders, no overlay element present.
  - **Test D**: `color === 'black'` (flipped board) still renders the overlay.

- Replaced the `MockIntersectionObserver` in `OpeningFindingCard.test.tsx` with one whose `observe()` synchronously invokes the callback with `[{ isIntersecting: true }]`, so `LazyMiniBoard`'s gate flips to `visible=true` and `MiniBoard` actually mounts in tests. This was option (a) from the plan — preferred because it exercises the real component code path instead of mocking `LazyMiniBoard` away.

## Verification

`cd frontend && npx tsc --noEmit && npm run lint && npx vitest run src/components/insights/OpeningFindingCard.test.tsx src/lib/sanToSquares.test.ts && npm run knip`:

- **tsc**: zero errors
- **lint**: zero errors (3 pre-existing warnings under `coverage/` are unrelated artifacts)
- **vitest** (targeted): 42 tests pass (35 existing + 7 sanToSquares)
- **vitest** (full repo, sanity): 206/206 pass across 18 files
- **knip**: zero issues — `arrowGeometry.ts` exports are imported by both `ChessBoard.tsx` and `MiniBoard.tsx`

## Deviations from Plan

None. The plan executed exactly as written. The two TDD cycles (RED → GREEN per task) both produced the expected red gate before implementation.

One small judgment call worth noting: I added two extra `sanToSquares` test cases beyond the five in `<behavior>` (illegal-in-FEN as a separate case from purely unparseable SAN, and a malformed-FEN case) because they directly exercise the chess.js v1.x throw paths the helper has to swallow. Net 7 tests instead of 5; same intent.

## Commits

| Hash    | Type | Message                                                                |
| ------- | ---- | ---------------------------------------------------------------------- |
| 1342fdb | test | add failing tests for sanToSquares helper                              |
| 36eb0af | feat | add sanToSquares helper + MiniBoard arrow overlay                      |
| 74acf9e | test | add failing tests for score-colored after-move arrow                   |
| de187ed | feat | wire score-colored after-move arrow into OpeningFindingCard            |

## Self-Check: PASSED

- `frontend/src/lib/sanToSquares.ts` exists
- `frontend/src/lib/sanToSquares.test.ts` exists
- `frontend/src/components/board/arrowGeometry.ts` exists
- All 4 commits present in `git log`
- All gates green: tsc, lint, vitest (targeted + full), knip
