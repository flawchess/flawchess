---
phase: quick
plan: 260321-erm
subsystem: frontend
tags: [mobile, ux, game-card, bookmark-card, responsive]
dependency_graph:
  requires: []
  provides: [mobile-optimized-game-card-player-display, mobile-visible-bookmark-minimap]
  affects: [GameCard, PositionBookmarkCard]
tech_stack:
  added: []
  patterns: [tailwind-responsive-sm-breakpoint, break-words-wrapping]
key_files:
  modified:
    - frontend/src/components/results/GameCard.tsx
    - frontend/src/components/position-bookmarks/PositionBookmarkCard.tsx
  created: []
decisions:
  - "Use single MiniBoard at size 60 for BookmarkCard (not two responsive renders) — simpler, adequate as thumbnail"
  - "Use sm:hidden / hidden sm:inline pair to toggle mobile vs desktop player display in GameCard"
metrics:
  duration: 5 minutes
  completed: 2026-03-21
---

# Quick Task 260321-erm: Mobile UX — Hide Player Name in Game Card Summary

**One-liner:** Mobile GameCard shows opponent-only with color symbol; BookmarkCard shows mini board at all sizes with wrapping label.

## Tasks Completed

| # | Task | Commit | Files |
|---|------|--------|-------|
| 1 | Show only opponent in GameCard on mobile | 2d91c57 | GameCard.tsx |
| 2 | Show minimap and allow label wrapping in BookmarkCard | 2d91c57 | PositionBookmarkCard.tsx |

## Changes Made

### GameCard.tsx

- Derived `opponentName`, `opponentRating`, `opponentColorSymbol` from `game.user_color`.
- Added a mobile-only span (`sm:hidden`) showing only the opponent color symbol + name + rating.
- Wrapped the existing full "white vs black" display in `hidden sm:inline` for desktop only.

### PositionBookmarkCard.tsx

- Removed `hidden sm:block` from the mini board container — board is now always visible.
- Changed `size` from 80 to 60 — more compact, appropriate as a list thumbnail at all screen sizes.
- Replaced `truncate` with `break-words` on the label button so long labels wrap naturally on narrow screens.

## Deviations from Plan

None — plan executed exactly as written. Used a single MiniBoard at size 60 rather than two responsive renders (plan offered this as the simpler option).

## Self-Check

- [x] `frontend/src/components/results/GameCard.tsx` modified and committed
- [x] `frontend/src/components/position-bookmarks/PositionBookmarkCard.tsx` modified and committed
- [x] TypeScript compile: no errors
- [x] Production build: success (2d91c57)
