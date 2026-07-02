---
quick_id: 260702-12z
slug: replace-white-scrollbars-on-desktop-with
date: 2026-07-01
status: complete
commit: 274041f3
---

# Summary: Replace white scrollbars with slim dark scrollbar

Applied the existing `.thin-scrollbar` utility to every nested overflow scroll container
that was still rendering the browser-default chunky/white scrollbar. No new CSS — the
utility (translucent foreground-tinted thumb, transparent track; Firefox + WebKit) already
existed for the analysis move tree.

## Files changed (9)

- `components/layout/SidebarLayout.tsx` — desktop filter/bookmark sidebar panel (reported case)
- `components/analysis/VariationTree.tsx` — desktop move-list empty-state scroller
- `components/board/HorizontalMoveList.tsx` — empty + populated move-chip scrollers
- `components/position-bookmarks/SuggestionsModal.tsx` — suggestions modal body
- `pages/Analysis.tsx` — eval-chart tab scroller
- `pages/Welcome.tsx` — value-split table horizontal scroller
- `components/analysis/EngineLines.tsx` — compact PV horizontal scroller
- `components/filters/MobileFilterDrawer.tsx` — mobile filter drawer body (consistency)
- `components/ui/select.tsx` — Radix select dropdown content

## Verification

- `npm run lint` — 0 errors (3 pre-existing warnings in generated `coverage/` files).
- `npm test -- --run` — 105 files, 1237 tests passed.

CSS-class-only change; no component logic touched, backend untouched.

## Commit

- `274041f3` — style(quick): apply thin-scrollbar to nested overflow containers
