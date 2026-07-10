---
quick_id: 260710-k7n
slug: engine-hero-homepage
date: 2026-07-10
status: complete
commit: c039196b
---

# Quick Task 260710-k7n — Summary

FlawChess Engine promoted to the hero feature on the public homepage, and added as the lead feature in the README.

## Changes

- **`frontend/src/pages/Home.tsx`** — imported `ChessKnight` from lucide-react; prepended a new `flawchess-engine` entry to `FEATURES` so it is `FEATURES[0]` (the hero). Heading "Your Best Practical Move", `ChessKnight` icon, screenshot `/screenshots/flawchess-engine.png`, `imagePosition: 'right'`, 3 bullets (practical-move value incl. follow-ups, trap/swindle finding, Stockfish+Maia + Play-style dial). `game-analysis` now sits at #2. No layout code changed — both the desktop right column and the mobile charcoal section read `heroFeature = FEATURES[0]`.
- **`README.md`** — added a **FlawChess Engine** bullet as the first item in `## Features`; rewrote the "What is FlawChess?" intro paragraph to headline the engine and removed the Zobrist-hash and AI-narrated-insights sentences (per user request).
- **`frontend/public/screenshots/flawchess-engine.png`** — committed the hero asset (was untracked).
- **Hero title color (follow-up):** the hero heading "Your Best Practical Move" now renders in `FLAWCHESS_ENGINE_ACCENT` (gold, `oklch(0.78 0.14 80)`) — the same accent the analysis-page FlawChess card uses. Imported from `theme.ts`, applied to both hero render paths (desktop right column + mobile section) only; the other feature cards keep the default heading color.

## Decisions / deviations

- **Bullet punctuation:** the locked copy from the `/gsd-explore` session used em-dashes as clause separators. Rendered them as **colons** in `Home.tsx` to match the five sibling feature cards (which use colons) and the project's em-dash-sparingly rule. Content unchanged. README bullets keep `—` because every README feature bullet uses that style.
- **4th bullet deferred:** "Play the FlawChess bots" intentionally NOT added — waits on the bots feature (SEED-091).

## Verification

- `npm run lint` — 0 errors (3 pre-existing `coverage/` warnings, unrelated).
- `npx tsc -b` — exit 0.
- `npm run knip` — clean.
- `npx vitest run src/pages/__tests__` — 7 files, 66 tests passed.

## Note for the user

Committed directly on `main` (the working tree was already on `main` after phase 162's squash-merge). Both commits are ahead of `origin/main` and NOT pushed — push when ready.
