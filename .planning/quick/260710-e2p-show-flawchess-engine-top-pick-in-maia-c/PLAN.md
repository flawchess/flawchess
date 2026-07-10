---
quick_id: 260710-e2p
slug: show-flawchess-engine-top-pick-in-maia-c
date: 2026-07-10
---

# Quick Task: FlawChess top pick in Maia tooltip + drop "(played)"

## Problem

The Maia "Moves by Rating" chart tooltip pins a first row labeled **"FlawChess"**, but
`engineTopLines` was sourced from **standalone Stockfish** whenever Stockfish was on
(only falling back to the FlawChess Engine when Stockfish was off). So the pinned row
showed Stockfish's *objective best* move (e.g. Rad1) mislabeled as "FlawChess", while the
FlawChess Engine card showed its actual practical pick (e.g. exd6). The two diverge exactly
when FlawChess trades objective eval for human findability — the interesting case.

Also: the tooltip appends a muted **"(played)"** tag to whichever move was played in the
game. User wants that removed.

## Changes (option 2 — show the real FlawChess pick)

1. **`frontend/src/pages/Analysis.tsx`** — rewrite the `engineTopLines` memo to source the
   pinned row ONLY from the FlawChess Engine's top practical pick
   (`reconciledRankedLines[0]`), using its reconciled white-POV objective eval
   (`objectiveEvalCp`/`objectiveEvalMate`). Returns `[]` (drops the row) when the FlawChess
   Engine is off or has no ranked line yet — never falls back to a mislabeled Stockfish pick.

2. **`frontend/src/components/analysis/MovesByRatingChart.tsx`** — remove the `(played)`
   span from `MovesByRatingTooltipContent`. Drop the now-unused `playedSan` prop from that
   component and from the `movesTooltipContent` factory. `playedSan` stays on
   `MovesByRatingChart` itself (still drives played-line stroke emphasis).

3. **`frontend/src/components/analysis/__tests__/MovesByRatingChart.test.tsx`** — drop the
   `playedSan` prop from the direct `MovesByRatingTooltipContent` renders and change the
   `'Ne4 (played)'` assertion to `'Ne4'`. Full-chart renders keep `playedSan` (emphasis).

## Verification

- `npm run lint && npx tsc -b && npm test -- --run` (frontend gate; tsc because shared
  component prop types change — per run-tsc-before-integrating memory).
- Manual reasoning: with FlawChess on, tooltip row 1 = FC top pick + its objective eval +
  Maia prob; with FlawChess off, no pinned row. No "(played)" anywhere in the tooltip.

## Out of scope

Backend, other tooltips, the FlawChess card prose (already correct).
