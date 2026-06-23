---
quick_id: 260623-6pd
status: complete
title: Surface shipped tier-3 tactic tags in an Advanced filter group + cards/eval-chart/legend
date: 2026-06-23
commits:
  - 954be4a2 feat(260623-6pd): surface shipped tier-3 tactic families in filter + comparison grid
  - 71648e9c feat(260623-6pd): add collapsible Advanced tier-3 tactic group to filter + cards
---

# Quick Task 260623-6pd — Summary

Surfaced the shipped Phase-132 tier-3 tactic motifs everywhere the existing tactic
families appear, behind a new collapsible **Advanced** group in the Library tags filter.

## What shipped

- **New Advanced filter group** (collapsed by default) below "Checkmate, Checks &
  Discoveries" in the Library tags panel — present on both the Games and Flaws subtabs
  and their mobile drawers (all four mount `FlawFilterControl`, which is registry-driven).
  It contains 6 families: **x-ray** (relocated from Piece Attacks) plus the 5 newly-shipped
  tier-3 motifs **deflection, intermezzo, interference, clearance, capturing-defender**.
  The toggle carries a "Advanced · N" selected-count badge and the Tags-icon legend.
- **Full tactic-tag parity** for the tier-3 motifs: game/flaw card chips, eval-chart
  click-to-cycle through datapoints, eval-chart datapoint tooltip, and the tags-info-icon
  legend explanations. All of these derive from the shared tactic registry, so registering
  the families lit them up without touching the card/chart/legend components.
- **Comparison grid** (FlawStatsPanel you-vs-opponent) now spans 15 families (top-6 + 9
  overflow), per the locked decision for full parity.

## How it works (no detector/data changes)

The cook-aligned tier-3 detectors already fire at `TACTIC_CONFIDENCE_HIGH` (100), so the
backend chip-read path already returns these motifs (they pass the `_TACTIC_CHIP_CONFIDENCE_MIN`
lever). They were invisible only because (a) the frontend drops motifs with no family and
(b) the family filter / comparison grid iterate `FAMILY_TO_MOTIF_INTS`. The fix is purely
registry: 5 keys added to `FAMILY_TO_MOTIF_INTS` (backend) and 5 families + the `advanced`
group added to `tacticComparisonMeta.ts` (frontend). `attraction`, `self-interference`, and
`sacrifice` stay unmapped (suppressed, 0 TP, no chip data).

## Files

- `app/repositories/library_repository.py` — 5 tier-3 keys in `FAMILY_TO_MOTIF_INTS`.
- `frontend/src/lib/theme.ts` — 5 `TAC_*`/`_BG` aliases (single-blue convention preserved).
- `frontend/src/lib/tacticComparisonMeta.ts` — `TacticFamily` union, colors, icons,
  `advanced` group, family defs (x-ray relocated + 5 new); stale "10 families" comments fixed.
- `frontend/src/components/filters/FlawFilterControl.tsx` — extracted `TacticFamilyGroup`,
  added the collapsible Advanced section + count badge + legend.
- Tests: `tests/services/test_tactic_comparison_service.py` (taxonomy 10→15),
  `FlawFilterControl.test.tsx` (9 always-on families + Advanced collapsible coverage).

## Verification (all green)

- Backend: `ruff format`/`check`, `ty check app/ tests/`, `pytest -n auto` over the
  comparison-service file (12) + library/tactic surface (236 passed, 6 skipped).
- Frontend: `tsc -b`, `npm run lint` (0 errors), `knip` clean, full suite **1093 passed**.

## Out of scope / notes

No DB migration (families are query-time grouping). No re-analysis/backfill — whether a
given historical flaw already carries a tier-3 tag depends on when it was analyzed; new
analyses tag at confidence 100. Card chips + eval-chart tooltip remain beta-gated
(`beta_enabled`), unchanged. Live browser confirmation of cycling/tooltip is data-dependent;
behavior is covered by the existing motif-agnostic tests plus the registry resolution.
