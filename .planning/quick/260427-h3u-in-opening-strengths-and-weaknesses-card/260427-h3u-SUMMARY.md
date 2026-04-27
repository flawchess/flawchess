---
quick_id: 260427-h3u
slug: in-opening-strengths-and-weaknesses-card
status: complete
date: 2026-04-27
commit: ae44c6e
---

# Quick Task 260427-h3u: SUMMARY

## What changed

In each Opening Strengths/Weaknesses finding card (`OpeningFindingCard`):

- Removed the whole-card deep-link `<a href="/openings/explorer">` wrapper. The card body is now a plain `<div>` with no click handler.
- Removed the `(n=<x>)` indicator from the prose line.
- Removed the `ExternalLink` icon previously rendered in the top-right of the header.
- Added a new row inside the card with two explicit links:
  - **Moves** — `ArrowRightLeft` icon (matches the Moves tab trigger), deep-links to the Move Explorer (calls `onFindingClick`).
  - **`<n>` Games** — `FolderOpen` icon (matches `MostPlayedOpeningsTable`), deep-links to the Games subtab pre-filtered to that opening (calls `onOpenGames`).
- Both links use a `Tooltip` and the same `text-muted-foreground hover:text-foreground transition-colors` styling as the Games link in `MostPlayedOpeningsTable`.
- Layout: links row sits on its own line, after the prose, in both the mobile and desktop layouts.

## Files

- `frontend/src/components/insights/OpeningFindingCard.tsx` — UI refactor.
- `frontend/src/components/insights/OpeningInsightsBlock.tsx` — new `onOpenGames` prop plumbed through `SectionsContent` → `FindingsSection` → `OpeningFindingCard`.
- `frontend/src/pages/Openings.tsx` — new `handleOpenFindingGames` callback (mirrors `handleOpenFinding` but routes to `/openings/games`); passed to `OpeningInsightsBlock`.
- `frontend/src/components/insights/OpeningFindingCard.test.tsx` — tests updated: dropped `(n=…)` and aria-label assertions, replaced whole-card click test with separate Moves and Games button tests.
- `frontend/src/components/insights/OpeningInsightsBlock.test.tsx` — tests updated: pass `onOpenGames` everywhere; replaced card-click test with two tests covering each link.

## Verification

- `npm test -- --run OpeningFindingCard OpeningInsightsBlock` — 19 tests passed (2 files).
- `npm run lint` — 0 errors (3 pre-existing warnings in `coverage/`, unrelated).
- `npx tsc --noEmit` — clean.
- `npm run build` — builds successfully.

## Commit

- `ae44c6e` feat(quick-260427-h3u): replace whole-card deeplink in OpeningFindingCard with explicit Moves + Games links
