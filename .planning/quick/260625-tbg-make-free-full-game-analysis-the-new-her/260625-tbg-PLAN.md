---
quick_id: 260625-tbg
title: Make "Free Full-Game Analysis" the new hero feature on the homepage and update SEO texts
date: 2026-06-25
status: planned
---

# Quick Task 260625-tbg

## Goal

Promote the v1.28 work (free full-game Stockfish analysis of chess.com + lichess
games, with broad tactic tagging of flaws) to the homepage hero feature, demote the
other features one slot, and refresh the SEO meta to match.

## Tasks

1. **frontend/src/pages/Home.tsx** — import `Crosshair` from lucide-react and PREPEND a
   new `FEATURES[0]` entry (slug `game-analysis`, heading "Free Full-Game Analysis",
   icon `Search`, `imagePosition: 'right'`, screenshot `/screenshots/game-card.png`,
   4 desc bullets). All existing features shift down one slot, unchanged. The hero is
   rendered from `FEATURES[0]`; the grid renders `FEATURES.slice(1)` with its existing
   left/right alternation, so no `imagePosition` flips are needed.

2. **frontend/index.html** — update `<title>`, `<meta name="description">`, `og:title`,
   `og:description`, `twitter:title`, `twitter:description` to lead with free game
   analysis + tactic tagging while keeping openings/endgames/time. Leave `og:image`.

3. **frontend/vite.config.ts** — update PWA `manifest.description` to match the new
   meta description.

## Notes

- The image file `frontend/public/screenshots/game-card.png` is supplied separately by
  the user; the code only references the path.
- Homepage is prerendered (vite-prerender-plugin renders `HomePageContent`), so the new
  FEATURES bullets are baked into static HTML automatically — no separate static copy.

## Verify

- `cd frontend && npm run lint && npx tsc -b && npm test -- --run`
- Add a brief `### Changed` bullet under `## [Unreleased]` in CHANGELOG.md (user-facing copy).
