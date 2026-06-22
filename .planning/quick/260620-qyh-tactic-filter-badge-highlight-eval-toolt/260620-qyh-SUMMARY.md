---
quick_id: 260620-qyh
status: complete
date: 2026-06-20
---

# Quick Task 260620-qyh — Summary

Three frontend-only tactic-UI fixes for Phase 130 (Library Games + Flaws tabs).
Executed inline (no subagents) — small, mechanical UI tweaks.

## Changes

### 1. Active-filter ring on tactic-motif chips
`frontend/src/components/library/TacticMotifChip.tsx` — the chip now subscribes to
`useFlawFilterStore` and applies `ACTIVE_FILTER_RING_CLASS` (ring color = family
color) when its tactic family is in `flawFilter.tacticFamilies` and the orientation
filter (`either` or the chip's own orientation) matches. Mirrors `TagChip`'s D-05
ring exactly, so both the Games card (`LibraryGameCard`) and Flaws card (`FlawCard`)
get it with no call-site changes.

### 2. Missed/allowed prefix in the eval-chart tooltip
`frontend/src/components/library/EvalChart.tsx` — replaced the allowed-only,
prefix-less tactic line with a `tooltipTactics` list built from the active marker's
`allowed_tactic_motif` + `missed_tactic_motif` (beta-gated, family-mapped). Each
`<li>` renders `"<orientation>: <label>"` with the family icon/color, matching the
dual-orientation chips (allowed listed before missed).

### 3. Show tooltip when opening a game on a flaw ply
`frontend/src/components/library/EvalChart.tsx` — added a `didRevealInitialTooltip`
mount effect: when `initialPly != null` (FlawCard modal) it sets `sliderFocused` and
focuses the slider on fine pointers, surfacing the tooltip immediately. Mirrors the
existing `commandedPly` reveal; dismissable as usual (blur / outside-touch). The
Games subtab passes no `initialPly`, so it is unaffected.

## Verification

- `npm run lint` — clean
- `npx tsc -b` — clean
- `npm test -- --run` — 90 files, 1072 tests passed

No EvalChart unit test exists (only `EvalCoverageBadge`), so none to update. No
backend changes. CHANGELOG `[Unreleased] > Fixed` updated.

## Commits

- `1104ffc2` fix(library): eval tooltip tactic prefix + show tooltip on flaw-ply open
- (prior) fix(library): highlight tactic chips with active-filter ring when filtered
</content>
