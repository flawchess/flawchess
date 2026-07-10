---
quick_id: 260710-e2p
slug: show-flawchess-engine-top-pick-in-maia-c
date: 2026-07-10
status: complete
commit: 9b409161
---

# Summary: FlawChess top pick in Maia tooltip + drop "(played)"

## What changed

- **`frontend/src/pages/Analysis.tsx`** — rewrote the `engineTopLines` memo. The Maia
  tooltip's pinned "FlawChess" row now comes ONLY from the FlawChess Engine's top ranked
  line (`reconciledRankedLines[0]`), carrying its reconciled white-POV objective eval
  (`objectiveEvalCp`/`objectiveEvalMate`). Returns `[]` (drops the row) when the FlawChess
  Engine is off or has no ranked line yet — no more falling back to Stockfish's objective
  best mislabeled as "FlawChess" (the root cause: the two diverge exactly when FlawChess
  trades eval for findability, e.g. exd6 over Rad1).
- **`frontend/src/components/analysis/MovesByRatingChart.tsx`** — removed the `(played)`
  span from `MovesByRatingTooltipContent`; dropped the now-unused `playedSan` prop from that
  component and the `movesTooltipContent` factory. `playedSan` stays on `MovesByRatingChart`
  (drives played-line stroke emphasis).
- **`MovesByRatingChart.test.tsx`** — dropped `playedSan` from the direct tooltip-content
  renders; changed the `'Ne4 (played)'` assertion to `'Ne4'`.

## Verification

- `npx tsc -b` — clean (shared component prop types changed).
- `npm run lint` — 0 errors (3 warnings are pre-existing `coverage/` artifacts).
- `npm run knip` — clean.
- `npm test -- --run` — 137 files, 1690 tests pass.

Not driven in-browser: the tooltip is hover-only behind a loaded game + both engines on;
behavior is fully covered by the direct `MovesByRatingTooltipContent` unit tests and the
pure data-shaping memo change (verified by tsc + reading).

## Out of scope (untouched)

Backend, other tooltips, FlawChess card prose (already correct), the untracked
`frontend/public/screenshots/flawchess-engine.png` (user's screenshot, not committed).
