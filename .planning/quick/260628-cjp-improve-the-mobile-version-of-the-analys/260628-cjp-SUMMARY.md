---
quick_id: 260628-cjp
title: Improve the mobile version of the analysis page
status: complete
date: 2026-06-28
---

# Quick Task 260628-cjp — Summary

Redesigned the **mobile** (`< 640px`) layout of `/analysis` into a chess.com-style
takeover, leaving the desktop layout (`≥ sm`) untouched.

## What changed

1. **Header** — on the analysis route, a back button (browser `navigate(-1)`) + "Analysis"
   title replaces the logo header (`AnalysisMobileHeader` in `App.tsx`).
2. **Footer** — the shell's mobile bottom nav + More drawer are suppressed on `/analysis`;
   the page renders its own in-flow board-controls footer (Reset / Back / Forward / Flip).
3. **Engine lines on top** — the two Stockfish PV lines now sit above the board with no
   info-card header (skeleton while loading).
4. **2-tab view** — a Moves | Eval-chart tab view fills all vertical space between the board
   and the footer. Moves is the default and uses a vertical, scrollable move list (new
   `variant="vertical"` on `VariationTree`). Free-play mode (no game) shows only the move
   list, no tab bar (there is no eval chart).

## How

- **Single tree per breakpoint**: a local `useIsMobile()` (matchMedia 640px) renders the
  mobile OR desktop tree, never both — a CSS `hidden` split would have double-mounted the
  board / eval-chart / variation-tree (duplicate `id`/`data-testid`, two react-chessboards).
  Browser-verified `boardCount === 1` in the mobile tree.
- **Full-height fill**: `ProtectedLayout` wraps the analysis route in a mobile-only
  `h-[100dvh]` flex column (`sm:h-auto sm:block` reverts to desktop block flow), giving the
  page's `flex-1` tab content a bounded height to fill. The board / move list / controls /
  eval chart are factored into shared render consts reused by both trees (no duplication/drift).

## Files

- `frontend/src/App.tsx` — `AnalysisMobileHeader`; `ProtectedLayout` analysis-route branch.
- `frontend/src/pages/Analysis.tsx` — `useIsMobile`, shared render consts, mobile tree.
- `frontend/src/components/analysis/VariationTree.tsx` — `variant?: 'responsive' | 'vertical'`.

## Verification

- `npx tsc -b` clean; `npm run lint` clean (only pre-existing `coverage/` warnings);
  `npm run knip` clean; full suite **1214 tests pass**; `npm run build` succeeds.
- Existing `Analysis.test.tsx` / `VariationTree.test.tsx` unchanged-green (jsdom `matchMedia`
  is mocked to `matches:false`, so tests exercise the untouched desktop tree).
- Browser DOM check (game mode) confirmed: engine lines on top, single board, Moves tab
  active by default, footer with the 4 controls, desktop engine card absent. Pixel-level
  fill could not be screenshotted because the WM refused to shrink the window below 640px
  and the shell+page breakpoints must agree for the flex chain to bind — verified by
  construction + reasoning instead.

## Decisions (defaults from a detailed spec — flag in UAT if any differ)

- Mobile breakpoint = `< 640px` (matches the shell's existing mobile-chrome swap).
- Move list = vertical scrollable list ("use all vertical space" implies vertical, not the
  former horizontal strip).
- Engine toggle dropped on mobile (no card header → no toggle); engine stays on.
- Free-play mode: move list only, no tabs.
</content>
