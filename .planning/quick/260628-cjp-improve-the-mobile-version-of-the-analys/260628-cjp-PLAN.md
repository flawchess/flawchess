---
quick_id: 260628-cjp
title: Improve the mobile version of the analysis page
status: planned
date: 2026-06-28
---

# Quick Task 260628-cjp — Mobile analysis page redesign

## Goal

Redesign the **mobile** (`< sm`, 640px) layout of `/analysis` so the page takes over
the app shell chrome, matching a chess.com-style mobile analysis board:

1. **Header** — replace the logo header with a back button (browser back, `navigate(-1)`).
2. **Footer** — replace the main mobile nav bar with the board controls (the page owns the footer).
3. **Engine lines** — show the two Stockfish PV lines *above the board*, without the engine info card header.
4. **Tabs** — a 2-tab view (Moves | Eval chart), Moves default, filling all vertical space between board and controls footer.

Desktop (`≥ sm`) layout stays **unchanged**.

## Key decisions (sensible defaults from a detailed spec)

- **Breakpoint** = `< 640px` (`sm`), matching where the shell already swaps to mobile chrome.
- **One tree at a time** via a `useIsMobile()` matchMedia hook — NOT CSS `hidden` — to avoid
  double-mounting the board / eval-chart / variation-tree (duplicate `id`/`data-testid`, double react-chessboard).
  jsdom `matchMedia` is mocked to `matches:false`, so all existing tests stay on the unchanged desktop tree.
- **Move list = vertical**: "use all vertical space" implies the tall scrollable paired list, not the
  current horizontal mobile strip. Add `variant?: 'responsive' | 'vertical'` to `VariationTree`.
- **Engine toggle dropped on mobile** (no card header → no toggle); engine stays on by default.
- **Free-play mode** (no `game_id`): no eval chart → render only the move list (no tab bar).
- **Footer controls are in-flow** (last flex child of a full-height column), not `fixed` — cleaner fill,
  no padding hacks. Shell's `MobileBottomBar` is suppressed on the analysis route.

## Tasks

### Task 1 — `VariationTree` vertical variant
- File: `frontend/src/components/analysis/VariationTree.tsx`
- Add `variant?: 'responsive' | 'vertical'` prop (default `'responsive'`).
- When `'vertical'`, render `DesktopTree` regardless of breakpoint (fills + scrolls).
- Verify: `npm test -- --run VariationTree` green; `npx tsc -b` clean.

### Task 2 — App shell route takeover
- File: `frontend/src/App.tsx`
- Add `AnalysisMobileHeader` (mobile-only: back button `navigate(-1)`, title "Analysis", no logo).
- In `ProtectedLayout`, branch on `isAnalysisRoute`:
  - wrap header+main in a `flex flex-col h-[100dvh] sm:h-auto sm:block` container (full-height flex chain on mobile only);
  - render `AnalysisMobileHeader` instead of `MobileHeader`; suppress `MobileBottomBar` + `MobileMoreDrawer`;
  - main = `flex-1 min-h-0 flex flex-col sm:block sm:flex-none` (no `pb-16`).
- Keep `InstallPromptBanner` / `FeedbackButton` as fixed siblings.
- Verify: `npx tsc -b` clean; desktop layout visually unchanged.

### Task 3 — Analysis page mobile tree
- File: `frontend/src/pages/Analysis.tsx`
- Add `useIsMobile()` (640px). After the existing hooks, branch:
  - `!isMobile` → existing desktop return (unchanged).
  - `isMobile` → new full-height flex column: engine lines (no card) → board+EvalBar → tab bar →
    tab content (flex-1, Moves=vertical VariationTree default, Eval=EvalChart; free-play = moves only) →
    in-flow board-controls footer.
- New testids: `analysis-tab-moves`, `analysis-tab-eval`, `analysis-mobile-footer`, `btn-analysis-back` (header).
- Verify: full frontend gate (`npm run lint && npm test -- --run && npx tsc -b`).

## must_haves

- Existing `Analysis.test.tsx` + `VariationTree.test.tsx` stay green (desktop path untouched).
- `npx tsc -b` zero errors; `npm run lint` clean; `npm run build` succeeds.
- Desktop `/analysis` unchanged.
</content>
</invoke>
