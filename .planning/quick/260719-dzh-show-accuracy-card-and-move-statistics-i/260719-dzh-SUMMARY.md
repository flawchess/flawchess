---
quick_id: 260719-dzh
slug: show-accuracy-card-and-move-statistics-i
date: 2026-07-19
status: complete
subsystem: ui
tags: [react, radix-tabs, analysis, bot-play, mobile-pwa]
---

# Summary — Quick Task 260719-dzh

Fixed: on mobile PWA, the accuracy card + move statistics did not appear when bot-game
analysis finished (only after a page refresh), while the eval chart appeared correctly in
place.

## What changed

`frontend/src/pages/Analysis.tsx` — the mobile/mid "Tags" tab (which hosts the MoveStats
Accuracies + move-quality panel) was gated on `evalChartReady` only, so it was inserted
into an already-mounted Radix `<Tabs>` at the instant evals landed — a post-mount tab add
that never rendered in place on mobile (needed a reload). Regated the Tags trigger +
content on `(evalChartReady || evalPending)` (the same signal the eval chart uses), so the
tab is present throughout analysis: it shows the same `AnalysisPendingPill` ("Analyzing"
badge) while pending, then swaps to the MoveStats/tags panel once evals land — in place,
no reload. Idle unanalyzed games (no active eval job) still omit the tab.

Desktop 3-column layout was already correct (MoveStats lives in a persistent column, not a
tab) and is untouched.

## Investigation note

Ruled out (via code + a passing frontend transition probe) that the divergence was in the
data or gate layer: backend commits `analysis_state='analyzed'` + `eval_series` + accuracy
+ flaws atomically (`apply_full_eval`), and the frontend eval chart / MoveStats co-gate on
the same `gameData`. The bug was specific to the mobile tabbed layout's conditionally
mounted Radix tab — surfaced by the user's clarification (mobile PWA; "completely absent"
until refresh; eval chart shows an Analyzing badge first).

## Verification

- New RED→GREEN tests in `Analysis.test.tsx` ("Mobile Tags tab" describe): force the
  mobile takeover via matchMedia; assert the Tags trigger is present while pending (fails
  without the fix — confirmed by revert), persists across the analyzed transition, and is
  omitted for an idle unanalyzed game.
- Frontend gate green: `npx tsc -b`, `npm run lint`, `npm run knip`, `vitest run`
  (172 files, 2312 tests). Frontend-only change — no backend files touched.

## Files

- `frontend/src/pages/Analysis.tsx` (modified)
- `frontend/src/pages/__tests__/Analysis.test.tsx` (modified — 2 new tests)
