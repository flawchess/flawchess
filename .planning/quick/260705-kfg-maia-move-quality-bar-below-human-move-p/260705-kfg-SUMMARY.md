---
quick_id: 260705-kfg
title: Maia move-quality bar below Human Move Probability chart
status: complete
date: 2026-07-05
---

# Quick Task 260705-kfg — Summary

Added a stacked "move-quality" bar below the Human Move Probability chart + ELO slider on
`/analysis` (mockup `screenshots/maia-bar.png`), plus its hover interaction and board arrows.

## What shipped

- **`bucketMovesByQuality` (pure helper, `moveQuality.ts`)** — groups the shown candidate
  SANs into ordered display buckets `[blunder, mistake, inaccuracy, good, pending]`, weighting
  each by its Maia probability at the rung nearest the selected ELO. The grader's separate
  `best` and `good` fold into one green **Good Moves** bucket; ungraded (streaming) moves fall
  into a neutral `pending` bucket so segment widths stay stable during grading. Unit-tested
  (8 new cases): grouping, fixed ordering, mass, within-bucket sort, pending, missing-rung.
- **`MaiaMoveQualityBar` component** — renders the stacked bar (widths normalized so it always
  fills, no icons inside). Hovering/tapping a segment reveals **only that segment's** move list
  under the bar and lifts its moves (`{san, color}`) via `onHoverMovesChange`. Renders null
  until Maia produces probabilities. Behavior-tested (4 cases).
- **`MaiaHumanPanel`** — new `onHoverMovesChange` prop; renders the bar below the `EloSelector`
  (shared by desktop + mobile compact, so both surfaces get it).
- **`Analysis.tsx`** — `hoveredQualityMoves` state wired to both panel instances; derives
  `qualityHoverArrows` by replaying each hovered SAN at the current position (chess.js,
  illegal → skipped) tinted its severity color, and merges them so they take precedence over
  the game/tactic arrow overlays in both game mode and free play.

## Locked decisions (clarified with user)

- Move lists **reveal on hover** (bar alone by default), board display = **colored arrows**,
  **Good Moves = best ∪ good** (single green segment). Segment colors: red/orange/yellow/green
  reuse the existing `MOVE_QUALITY_*` theme constants (mistakes orange, inaccuracies yellow).

## Verification

- `npm run lint` (0 errors), `npx tsc -b` (clean), `npm run knip` (clean), `npm test -- --run`
  (**115 files / 1363 tests pass**), including the two new suites and the fixed `MaiaHumanPanel`
  test. New component's hover→list→arrow-lift contract exercised directly by its test.

## Notes

- Stayed on the current phase branch (`gsd/phase-151.1-…`) rather than forking a quick-branch
  off `main`, because this extends active, uncommitted 151.1 chart work (`engineTopLines` /
  `designatedBestSan` threading) already in the working tree. That pre-existing WIP —
  including `MovesByRatingChart.tsx` changes I did not author — was swept into the feature
  commit alongside the new bar, since it's one coherent 151.1 increment on this branch.
- Fixed the stale `MaiaHumanPanel.test.tsx`: it rendered the panel without the now-required
  `shownSans`/`qualityBySan`/`engineTopLines` props (previously harmless because
  `MovesByRatingChart` short-circuits on empty `perElo`; the new bar reads `shownSans`
  unconditionally).
