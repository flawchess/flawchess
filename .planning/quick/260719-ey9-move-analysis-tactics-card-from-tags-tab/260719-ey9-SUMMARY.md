---
quick_id: 260719-ey9
title: Move analysis tactics card to Eval tab; rename Tags tab to Stats
date: 2026-07-19
status: complete
commit: e3639218
---

# Quick Task 260719-ey9 — Summary

## What changed

`frontend/src/pages/Analysis.tsx` (the mid-range and mobile analysis layouts both
reuse the `analysisTabs` tabbed panel verbatim, so a single edit covers both):

- **Tactics card relocated** — the Missed/Allowed/Context tags card
  (`AnalysisTagsPanel` `section='tags'`) now renders at the **bottom of the Eval tab**,
  below the eval chart (`{evalChartReady && <div className="px-3">{tagsPanel(false, 'tags')}</div>}`).
- **Tags tab → "Stats"** — the renamed tab shows only the MoveStats / accuracy card
  (`tagsPanel(false, 'stats')`). Its lucide `Tag` icon was swapped for
  `ChartNoAxesColumn` (chart-no-axes-column). The in-flight Analyzing-pill behavior and
  the `(evalChartReady || evalPending)` presence gate (quick 260719-dzh) are preserved.
- Tab `value`/`data-testid` renamed `tags` → `stats` (`analysis-tab-stats`); the local
  const `tagsTab` → `statsTab`; `Tag` import removed, `ChartNoAxesColumn` added.
- Stale docstrings updated (`… | FlawChess | Stats)`), and the three
  `analysis-tab-tags` test assertions renamed to `analysis-tab-stats`.

Desktop 3-column layout is untouched — it already renders the `'stats'` and `'tags'`
sections separately and does not use `analysisTabs`.

## Verification

- `npx tsc -b` — clean
- `npm run lint` — 0 errors (3 pre-existing warnings in `coverage/`, unrelated)
- `npm run knip` — clean
- `npm test -- --run Analysis.test.tsx AnalysisTagsPanel.test.tsx` — 63 passed

## Notes

Visual UAT (mobile/mid viewport, an analyzed game loaded) is recommended but optional:
the change is a JSX reposition covered by the existing tab-strip tests and a passing
type-check. Only one layout tree renders at a time, so the `analysis-tags-section`
testid appearing in both the desktop board stage and the mid/mobile Eval tab never
collides in the DOM.
