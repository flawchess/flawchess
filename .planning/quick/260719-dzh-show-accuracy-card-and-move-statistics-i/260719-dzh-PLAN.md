---
quick_id: 260719-dzh
slug: show-accuracy-card-and-move-statistics-i
date: 2026-07-19
status: complete
---

# Quick Task 260719-dzh

## Problem

On the **mobile PWA** analysis board, after playing a bot game and clicking Analyze,
the board opens and analysis runs. When analysis finishes, the eval chart appears in
place (live poll), but the **accuracy card and move statistics stay completely absent**
until a full page refresh.

## Root cause

The mobile/mid tabbed layout (`analysisTabs` in `frontend/src/pages/Analysis.tsx`) hosts
the MoveStats (Accuracies card + move-quality table) in the **"Tags" tab**. That tab's
trigger *and* content were gated on `evalChartReady` **only**, so the tab was added to an
already-mounted Radix `<Tabs>` at the exact moment evals landed. That post-mount tab
insertion does not render in place on mobile — it only appears after a fresh mount
(refresh). The Eval tab, by contrast, is always mounted and merely swaps its body
(pending pill → chart), which is why the eval chart updates correctly in place.

Backend and frontend data are fully atomic and co-gated (verified): a single poll tick
delivers `analysis_state='analyzed'` + `eval_series` + accuracy + flaws together. The bug
is purely the conditionally-mounted Radix tab.

## Fix

Gate the Tags tab trigger + content on `(evalChartReady || evalPending)` — the same
signal the eval chart uses — so the tab is present throughout the analyze flow. Its body
shows the same **Analyzing pill** (`AnalysisPendingPill`) while pending, then the
MoveStats/tags panel once evals land. No late tab insertion → renders in place.

Scope: `frontend/src/pages/Analysis.tsx` (`tagsTab` body + two gate sites + comments).
Desktop 3-column layout is unaffected (it renders MoveStats in a persistent column, not
in tabs).

## Verification

- New RED→GREEN mobile-layout tests in `Analysis.test.tsx` (forces the mobile takeover via
  matchMedia): Tags trigger present while pending (fails without the fix), persists across
  the analyzed transition, and is correctly omitted for an idle unanalyzed game with no
  active eval job.
- Full frontend gate green: `tsc -b`, `eslint`, `knip`, 2312 tests.
