---
quick_id: 260719-m5g
slug: fix-maia-card-gem-tag-for-engine-best-mo
date: 2026-07-19
status: complete
---

# Quick Task 260719-m5g: Maia card gem tag for engine best move before it is played — SUMMARY

## What changed

`frontend/src/pages/Analysis.tsx`, `qualityBySanWithGem` memo (~1313):

1. Gated the stored-data short-circuit (`if (gameHasStoredBestMoveData) return qualityBySan`)
   on a new `playedBestHere = nextNode?.san === reconciledBestSan`. The short-circuit is
   authoritative ONLY when the user actually played the engine best move at that ply
   (the backend only writes a `game_best_moves` row for played==best plies). When the
   played move was non-best, control now falls through to the live `classifyGem` fallback
   so the card marks the engine best (`reconciledBestSan`) as a gem before it is played —
   matching the on-board `gemByNode` badge that already appears once it is played.

2. Switched the live fallback's Maia rung from the reactive ELO slider (`selectedElo`) to
   the pinned mover rating `pinnedEloForMover(sideToMoveFromFen(position))`. Aligns the
   card's pre-play gem with the on-board badge (also pinned) and with Phase 172 /
   SEED-106 D-01. Also fixes a pre-existing sideline inconsistency (off-mainline live
   fallback used the slider while the arrival badge used pinned). Dep array: added
   `pinnedEloForMover`, dropped `selectedElo`.

Live fallback stays gem-only, matching `gemByNode`; `great` remains owned by the stored route.
No backend / stored-data / `gemByNode` changes. C2 gate (`playedIsBest: bestSan === reconciledBestSan`,
163-REVIEW WR-01) preserved.

Also: `CHANGELOG.md` Unreleased → Fixed bullet.

## Verification

- `npx tsc -b` → 0 errors.
- `npm run lint` → 0 errors (3 warnings, all in generated `coverage/`, pre-existing).
- `npm test -- --run` → 172 files, 2313 tests pass (incl. `Analysis.test.tsx`,
  `gemMove.test.ts`, `useGemSweep.test.ts`).
- `npm run knip` → clean.
- Reasoned through the reported case (prod game 1247936, move 46: Rc7?? played, Kd3 best
  = gem): `playedBestHere` false → live fallback runs → Kd3 classified gem → card marks it.

## Flagged: test-coverage gap (follow-up)

No existing test guards the specific new branch (analyzed game + non-best played + card
marks engine-best gem) — reverting the fix would NOT fail any current test. A faithful
regression test is an Analysis.tsx integration test (must seed `maiaState.perElo` +
`gradingState.gradeMap` at a parent node where the mainline next move differs from the
reconciled best, on an analyzed game with a null stored tier). It's non-trivial: the
card's gem surfaces only in hover tooltips / the quality bar, and a gem move (Maia prob
≤20%) never renders as a high-probability chart "leader", so the obvious label-color
assertion doesn't apply. The card's gem *rendering* is already unit-tested in isolation
(`MovesByRatingChart.test.tsx` / `MaiaMoveQualityBar.test.tsx` via the `qualityBySan`
prop); only the map *construction* for this case is unguarded. Recommend adding it as a
small follow-up if this branch is worth locking down.
