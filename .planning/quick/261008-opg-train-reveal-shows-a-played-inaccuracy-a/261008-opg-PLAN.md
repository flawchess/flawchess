---
quick_id: 261008-opg
mode: quick
type: execute
---

# Quick 261008-opg: Train reveal shows a played inaccuracy as inaccuracy

## Why

Phase 200 D-04/D-05 collapsed a played inaccuracy into "good" on the reveal
(`toDisplayQuality`) because "SOLV-03 already scores it as a correct answer".
Tiered scoring (SEED-119, Phase 191, five days earlier) gives an inaccuracy 1
move point, and Phase 222 added the "+1" chip and "decent move [+1]" copy, so
the reveal shows a green check next to a +1 (prod screenshot, session 1360).
Owner decision 2026-10-08: reverse D-04/D-05 for everything but the "Also fine"
alternatives.

## Tasks

1. `trainArrows.ts`: delete `toDisplayQuality`; `QUALITY_ARROW_COLOR.inaccuracy`
   = `MOVE_QUALITY_INACCURACY`, `TRAIN_STEP_HIGHLIGHT.inaccuracy` =
   `MOVE_HIGHLIGHT_SQUARE`; `markerForQuality` uncollapsed; alternatives map
   inaccuracy to the good badge explicitly.
2. `TrainReveal.tsx` header icon, `useTrainFreePlay.ts` marker + highlight,
   `VariationTree.tsx` comment.
3. Rewrite the collapse tests (trainArrows, TrainReveal); CHANGELOG bullet.

## Verify

`cd frontend && npx vitest run src/lib/__tests__/trainArrows.test.ts src/components/train src/hooks src/components/analysis && npm run lint && npm run build && npm run knip`
