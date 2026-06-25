---
quick_id: 260625-tbg
title: Make "Free Full-Game Analysis" the new hero feature on the homepage and update SEO texts
date: 2026-06-25
status: complete
commit: 199155f3
---

# Quick Task 260625-tbg — Summary

## What changed

- **`frontend/src/pages/Home.tsx`** — imported `Search` from lucide-react and prepended a
  new `FEATURES[0]` entry: slug `game-analysis`, heading **"Free Full-Game Analysis"**,
  icon `Search`, `imagePosition: 'right'`, screenshot `/screenshots/game-card.png`, four
  bullets (free Stockfish over the whole chess.com + lichess history; every blunder/mistake
  tagged with its tactic; missed vs. allowed with the engine's best line; filter by tactic,
  depth, severity). All five previous features shift down one slot unchanged. The hero
  renders `FEATURES[0]`; the grid renders `FEATURES.slice(1)` with its existing left/right
  alternation, so no `imagePosition` flips were needed.
- **`frontend/index.html`** — refreshed `<title>`, `<meta name="description">`, `og:title`,
  `og:description`, `twitter:title`, `twitter:description` to lead with free game analysis +
  tactic tagging while keeping openings/endgames/time. `og:image` left unchanged.
- **`frontend/vite.config.ts`** — PWA `manifest.description` updated to match the new meta
  description.
- **`CHANGELOG.md`** — added a `### Changed` bullet under `## [Unreleased]`.

## Notes

- Icon switched from `Crosshair` to `Search` per user request mid-task.
- The image `frontend/public/screenshots/game-card.png` is supplied separately by the user;
  the code only references the path. **The card will show a broken image until that file is
  added.**
- The homepage is prerendered (vite-prerender-plugin renders `HomePageContent`), so the new
  FEATURES bullets are baked into the static HTML on build — no separate static copy file.

## Verification

- `npm run lint` — 0 errors (3 pre-existing warnings in generated `coverage/` files only).
- `npx tsc -b` — exit 0.
- `npm test -- --run` — 1150 passed (95 files).

## Follow-up

- Add `frontend/public/screenshots/game-card.png` (a Library game card showing a clean
  tactic, e.g. a fork, with eval chart + both arrows + tactic chips).
