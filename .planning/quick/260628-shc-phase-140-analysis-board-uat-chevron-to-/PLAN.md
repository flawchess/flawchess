---
quick_id: 260628-shc
slug: phase-140-analysis-board-uat-chevron-to-
date: 2026-06-28
---

# Quick Task: Phase 140 analysis-board UAT — engine-line chevron + sideline grafting

## Problem (UAT feedback for phase 140)

1. **Chevron to expand engine lines.** The two Stockfish PV lines truncate at
   `MAX_PLIES = 5` with no way to see the rest of the line. Each line needs a
   chevron on the right that uncollapses it to reveal the whole PV.

2. **Clicking a line move skips the moves before it.** `EngineLines` calls
   `onMoveClick(from, to)` wired straight to `makeMove`, so clicking move N in a
   line plays *only* move N from the currently shown position — skipping moves
   1..N-1. It should graft the complete sideline up to (and including) the
   clicked move from the current anchor node, then land the board on it.

## Approach

- **`useAnalysisBoard.ts`** — add `playUciLine(uciMoves: string[])`: in one
  `setState`, replay the UCI prefix from `currentNodeId`, reusing an existing
  child when its from/to already matches (no duplicate branches), creating new
  nodes otherwise, then navigate to the LAST node. Distinct from `insertPvLine`
  (which parks at the fork and drives the tactic overlay via `pvLine`): this
  lands on the clicked move and leaves `pvLine`/tactic state untouched.

- **`EngineLines.tsx`** — change `onMoveClick` to `(uciMoves: string[]) => void`.
  Each chip click passes `visibleMoves.slice(0, moveIndex + 1)` (the UCI prefix).
  Add per-row expand state: when `line.moves.length > MAX_PLIES`, show a chevron
  button on the right; expanded rows render `line.moves` in full (and replay SAN
  for all shown moves). Applies to desktop and the compact mobile rows.

- **`Analysis.tsx`** — destructure `playUciLine`, pass it as `onMoveClick` to both
  the desktop and mobile `EngineLines` (replacing `makeMove`).

## Tests

- `EngineLines.test.tsx` — update click assertions to the array signature
  (`onMoveClick(['e2e4'])`); add a test that clicking move index 2 passes the full
  3-move prefix; add a chevron expand test (line with > 5 plies).
- `useAnalysisBoard.test.ts` — add `playUciLine` grafts the full prefix from the
  current node and navigates to the last move; reuses matching children.

## Verification

- `cd frontend && npm run lint && npx tsc -b && npm test -- --run`
- Manual UAT deferred to user.
