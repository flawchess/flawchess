---
quick_id: 260702-12z
slug: replace-white-scrollbars-on-desktop-with
date: 2026-07-01
---

# Quick Task: Replace white scrollbars with slim dark scrollbar

## Goal

Replace the browser-default chunky/white scrollbars on nested overflow containers
(desktop) with the existing `.thin-scrollbar` utility (the translucent foreground-tinted
scrollbar already used by the analysis move list), so scroll surfaces read as
dark-mode-friendly instead of out of place.

## Approach

`.thin-scrollbar` already exists in `frontend/src/index.css` (Firefox `scrollbar-*` +
WebKit `::-webkit-scrollbar` pseudo-elements). No new CSS needed — just apply the class
to every nested overflow scroll container that was still showing the default scrollbar.

## Containers updated

- `components/layout/SidebarLayout.tsx` — desktop filter/bookmark sidebar panel (the reported case)
- `components/analysis/VariationTree.tsx` — desktop move-list empty-state scroller
- `components/board/HorizontalMoveList.tsx` — both empty + populated move-chip scrollers
- `components/position-bookmarks/SuggestionsModal.tsx` — suggestions modal body
- `pages/Analysis.tsx` — mobile eval-chart tab scroller
- `pages/Welcome.tsx` — value-split table horizontal scroller
- `components/analysis/EngineLines.tsx` — compact PV horizontal scroller
- `components/filters/MobileFilterDrawer.tsx` — mobile filter drawer body (consistency)
- `components/ui/select.tsx` — Radix select dropdown content

## Out of scope

- Native page scrollbar (library games list) — already acceptable, intentionally native.
- `no-scrollbar` surfaces (cmdk command palette) — deliberately hidden.

## Verification

Frontend lint + full test suite green (CSS-class-only change, no logic touched).
