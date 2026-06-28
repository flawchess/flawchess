---
quick_id: 260628-ojq
title: "Phase 140 UAT: tactic-colored arrows on flaw/game cards and analysis board sideline"
status: complete
date: 2026-06-28
---

# Quick Task 260628-ojq

## Goal

Phase 140 UAT feedback: a board arrow (or sideline move) that belongs to a missed
or allowed tactic should be drawn in that tactic's color instead of the generic
severity / best-move color, so the arrow color matches the tactic chips.

Tactic colors (theme.ts, set in Quick 260628-1t5):
- **allowed** → `TAC_ALLOWED` (teal, hue 200)
- **missed** → `TAC_MISSED` (magenta, hue 330 — the UAT calls it "violet")

## Scope

1. **FlawCard** (`components/library/FlawCard.tsx`)
   - Allowed tactic → played-move (flaw) arrow teal instead of severity red/orange.
   - Missed tactic → best-move arrow magenta instead of blue.
   - Gate each recolor on the same orientation + motif condition that decides whether
     the matching tactic chip renders, so arrow color and chip never disagree.

2. **LibraryGameCard** (`components/results/LibraryGameCard.tsx`)
   - Allowed tactic → the following-best (opponent's response) arrow teal instead of blue.
   - Missed tactic → already drawn via the violet should-have-played arrow, no change.

3. **Analysis board sideline** (`pages/Analysis.tsx` + `lib/tacticArrows.ts`)
   - Move list: color every sideline move from the fork up to and including the depth-0
     resolving move in the orientation color (was: only the resolving move).
   - Arrows (`buildPvArrow`): countdown arrows up to depth 0 painted in the orientation
     color (teal/magenta) instead of blue; past the punchline keeps the neutral payoff color.

## Tasks

1. Recolor the two FlawCard arrows by tactic orientation.
2. Recolor the LibraryGameCard following-best arrow teal for allowed tactics.
3. Extend `sidelineNodeColors` to color the whole sideline up to depth 0.
4. Recolor `buildPvArrow` countdown arrows in the orientation color until depth 0.

## Verification

- `npx tsc -b`, `npm run lint`, `npm run knip` clean.
- Full frontend test suite green.
