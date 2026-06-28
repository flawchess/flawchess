---
quick_id: 260628-r5v
slug: uat-keep-blunder-mistake-icons-on-sideli
date: 2026-06-28
---

# Quick Task: Persist blunder/mistake icons on sideline moves (analysis board)

## UAT feedback

When exploring a sideline in the analysis board, keep the blunder and mistake icons
on every sideline move. Currently only the icon for the *current* move shows; stepping
forward in the line makes the previous move's icon disappear. If easy, also cache the
live engine eval per sideline move so it isn't recomputed when stepping back.

## Root cause

The live free-move classifier (`useLiveMoveFlaw`) grades only the *current* board
position (it needs the live engine's eval of the current node as the "child" eval).
`Analysis.tsx`'s `moveListMarkers` injected that severity solely for `currentNodeId`,
and `VariationTree` only rendered the severity glyph on a variation node when
`isCurrent`. So the glyph rode the current node and vanished on the next move.

The eval *value* is already cached per position by FEN in `engineEvalByFen`
(item 4, cap `LIVE_EVAL_CACHE_MAX`), so the "cache the eval" ask is mostly covered.
What was missing was persisting the derived *classification* per node.

## Changes

1. **Analysis.tsx** — add `liveFlawByNode: Map<NodeId, FlawSeverity>` state + an effect
   that records the current node's blunder/mistake classification as it settles. This is
   the per-node classification cache. Rewrite `moveListMarkers` to merge the persisted map
   (plus the in-flight current-node live severity) into the game flaw markers. Read-time
   guards skip stale ids (reused as main-line after a reload) and deleted nodes. Clear the
   map on Reset.
2. **VariationTree.tsx** — desktop `renderMoveButton` and mobile `varItems`: look up the
   severity marker for variation/free nodes regardless of `isCurrent`, so the glyph paints
   on every explored sideline move.
3. **Tests** — update VariationTree test (15) to assert the glyph now persists on a
   non-current variation node.

## Verification

- `npm run lint && npm test -- --run` (frontend)
- `npx tsc -b` (type check — shared FlawMarkerEntry/FlawSeverity usage)
- Manual: in game mode, play a sideline of 2-3 moves, each blunder/mistake keeps its icon;
  step back and forward, icons persist.
