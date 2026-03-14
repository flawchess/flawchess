---
phase: quick-17
plan: "01"
subsystem: frontend
tags: [ui, layout, import]
dependency_graph:
  requires: []
  provides: [inline-import-button]
  affects: [Dashboard, GameCardList]
tech_stack:
  added: []
  patterns: [optional-slot-prop]
key_files:
  created: []
  modified:
    - frontend/src/components/results/GameCardList.tsx
    - frontend/src/pages/Dashboard.tsx
decisions:
  - "headerAction prop pattern: optional ReactNode slot on GameCardList gives Dashboard full control over button content without coupling the list component to import logic"
metrics:
  duration: 5min
  completed: "2026-03-14"
---

# Quick Task 17: Move Import Button Inline with Matched Games Count Summary

**One-liner:** Import button moved inline with matched games count row via optional `headerAction` ReactNode slot on GameCardList.

## What Was Built

Added an optional `headerAction?: ReactNode` prop to `GameCardList`. The matched count `<p>` element was replaced with a flex row (`justify-between items-center`) where the count text sits on the left and `headerAction` renders on the right when provided.

In `Dashboard.tsx`, the standalone `<div className="flex justify-end">` import button block was removed from `rightColumn`. An `inlineImportButton` JSX variable was defined once and passed as `headerAction` to both the filtered (analysis) and unfiltered (default) `GameCardList` usages.

The `data-testid="btn-import"` attribute is preserved on the button. Empty-state import CTAs (`importButton` variable, `data-testid="btn-import-cta"`) are untouched — they remain for users with zero games.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Add headerAction prop and move Import button inline | 1ec5551 | GameCardList.tsx, Dashboard.tsx |

## Deviations from Plan

None — plan executed exactly as written.

## Self-Check

- [x] `frontend/src/components/results/GameCardList.tsx` modified with `headerAction` prop
- [x] `frontend/src/pages/Dashboard.tsx` standalone import button removed, `headerAction` passed to both GameCardList usages
- [x] Commit 1ec5551 exists
- [x] `npm run build` succeeds
- [x] `npx tsc --noEmit` passes (no errors in modified files)
- [x] Pre-existing lint errors in unmodified shadcn/ui files not introduced by this task

## Self-Check: PASSED
