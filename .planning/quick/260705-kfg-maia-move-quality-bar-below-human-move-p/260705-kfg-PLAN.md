---
quick_id: 260705-kfg
title: Maia move-quality bar below Human Move Probability chart
status: planned
date: 2026-07-05
---

# Quick Task 260705-kfg — Maia move-quality bar

Implement a stacked horizontal quality bar (mockup: `screenshots/maia-bar.png`) below the
Human Move Probability chart + ELO slider in the Maia panel. It aggregates the shown Maia
candidate moves at the selected ELO by their Stockfish-graded quality bucket.

## Locked decisions (from clarifying questions)

- **Lists reveal on hover** — bar alone by default; hovering (or tapping) a segment reveals
  ONLY that segment's move list under the bar.
- **Board display = colored arrows** — hovering a segment draws an arrow per move in that
  bucket, tinted the bucket's severity color (red/orange/yellow/green).
- **"Good Moves" combines `best` ∪ `good`** into a single green segment (matches mockup).
- Segments split into **4 buckets**: Blunders (red), Mistakes (orange), Inaccuracies
  (yellow), Good Moves (green). Ungraded (streaming) moves collapse into a trailing,
  non-interactive neutral "pending" segment so widths stay stable during grading.
- **No icons inside the bars** (mockup had glyphs — omit them).
- Segment order left→right: blunder, mistake, inaccuracy, good, (pending).
- Widths are normalized over the shown moves so the bar always fills.
- Per-move % shown in the hover list is the raw Maia probability (matches chart tooltip).

## Tasks

### Task 1 — pure bucketing helper + test (`moveQuality.ts`)
- Add `QualityBucketKey`, `QualityBucket`, and `bucketMovesByQuality(perElo, selectedElo,
  shownSans, qualityBySan)` returning the 5 ordered buckets, each with `moves`
  (`{san, probability}` sorted desc) and `probabilityMass`. `best`+`good` → `good`;
  undefined quality → `pending`.
- Reuses the existing private `nearestByElo` rung lookup.
- `files`: `frontend/src/lib/moveQuality.ts`, `frontend/src/lib/__tests__/moveQuality.test.ts`
- `verify`: `npm test -- --run moveQuality`
- `done`: helper unit-tested (grouping, ordering, mass, pending).

### Task 2 — `MaiaMoveQualityBar` component
- New `frontend/src/components/analysis/MaiaMoveQualityBar.tsx`: renders the stacked bar
  from `bucketMovesByQuality`, hover/tap reveals the active bucket's move list, and calls
  `onHoverMovesChange({san,color}[] | null)` up to the page for board arrows.
- Bucket → label + color mapping (theme constants) lives here. Segments are `<button>`s
  with `aria-label` + `data-testid="maia-quality-segment-<key>"`; container
  `data-testid="maia-move-quality-bar"`; hovered list `data-testid="maia-quality-hovered-list"`.
- Renders null when there is no shown-move mass.
- `files`: new component (+ small test optional).

### Task 3 — wire panel + page (arrows on board)
- `MaiaHumanPanel`: add `onHoverMovesChange` prop, render `<MaiaMoveQualityBar>` below the
  `EloSelector` (both desktop + mobile compact call sites already share this component).
- `Analysis.tsx`: `hoveredQualityMoves` state; pass `onHoverMovesChange` to both panel
  instances; derive `qualityHoverArrows` (SAN→from/to via chess.js at `position`, tinted
  bucket color); merge so hover arrows take precedence over game/tactic arrows.
- `files`: `MaiaHumanPanel.tsx`, `Analysis.tsx`.
- `verify`: `npm run lint`, `npx tsc -b`, `npm test -- --run`.
- `done`: bar shows below slider; hovering a segment lists its moves + draws severity-colored
  arrows on the board; desktop + mobile parity.

## Verify (whole task)
- `cd frontend && npm run lint && npx tsc -b && npm test -- --run` all green.
- No `text-xs` in new primary content; interactive elements have `data-testid`.
