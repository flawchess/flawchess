---
quick_id: 260608-ac1
slug: a-few-additions-to-phase-110-tag-filter-
status: complete
date: 2026-06-08
---

# Quick Task 260608-ac1 — Summary

Five frontend additions to the Library Games card (Phase 110 follow-up). Frontend-only;
no backend/API change (all needed data already on `GameFlawCard.flaw_markers`).

## What changed

1. **Active-filter ring on Blunder/Mistake badges** — `SeverityBadge` now subscribes to
   `useFlawFilterStore` and rings (same `ACTIVE_FILTER_RING_CLASS` as TagChip) when the
   severity filter is narrowed to exactly that severity. The filter default is both M+B on,
   so the ring is gated on `severity.length === 1` — it marks the *active constraint*, not
   the default. Inaccuracy never rings (not a filterable severity).
2. **Occurrence counts on tag chips** — `TagChip` takes an optional `count`, rendered
   count-first like the severity badges. `LibraryGameCard` computes per-tag counts from the
   user's (`is_user`) M/B `flaw_markers`. FlawsTab omits `count` (one flaw per row).
3. **Smaller tag chips** — chip text `text-sm` → `text-xs`; severity badges unchanged.
4. **"Inacc." → "Inaccuracies"** in `SeverityBadge`.
5. **Hover-to-highlight eval markers** — hovering a tag chip or a B/M severity badge sets a
   transient `highlight` state in `LibraryGameCard`, which derives a `highlightedPlies` set
   (scoped to `is_user` M/B markers) passed to `EvalChart`. Matching markers enlarge to full
   opacity; the rest dim. Empty set is a no-op (never dims everything).

## Files

- `frontend/src/components/library/SeverityBadge.tsx` — label, ring, onHover
- `frontend/src/components/library/TagChip.tsx` — count, onHover, text-xs
- `frontend/src/components/library/EvalChart.tsx` — `highlightedPlies` prop + dot emphasis/dim
- `frontend/src/components/results/LibraryGameCard.tsx` — tagCounts/highlight wiring, severity row `flex-nowrap` → `flex-wrap`
- Tests: `TagChip.test.tsx` (count + onHover + text-xs), new `SeverityBadge.test.tsx`

## Decisions

- **User-only scope (D2):** tag counts AND highlight use `is_user` markers, so a chip's number
  equals the number of dots that highlight on hover, and matches the user-only chips/counts.
- **Ring semantics (D1):** narrowed-severity gate (length===1) to avoid an always-on ring.
- **Layout (D4):** "Inaccuracies" is much wider than "Inacc."; switched the desktop severity
  row to `flex-wrap` so it wraps inside the 1/3-width column instead of overflowing.

## ⚠️ Guideline deviation (flagged)

CLAUDE.md sets `text-sm` as a hard minimum font size "even for badges," with an exception only
for hover tooltips. Item 3 (`text-xs` tag chips) intentionally overrides that floor per explicit
request. Not CI-enforced (no font-size lint rule). Revert the one `text-xs` in `TagChip.tsx` if
the readability tradeoff isn't worth it.

## Gates

GREEN — eslint clean, `tsc --noEmit` 0 errors, knip clean, vitest **842 passed** (72 files),
incl. 27 in the two affected suites. Backend untouched (no Python changes).

Commits: `9889c425` (components + tests), plus wiring + docs commit. On
`gsd/phase-110-flaw-tag-taxonomy-overhaul-rename-impact-family-rebuild-tool`; not pushed.

## Not done / follow-up

- HUMAN-UAT pending — items 1, 3, 5 are visual (ring, smaller font, hover dim/highlight).
- Confirm the `flex-wrap` severity row reads acceptably on the narrowest desktop column.
