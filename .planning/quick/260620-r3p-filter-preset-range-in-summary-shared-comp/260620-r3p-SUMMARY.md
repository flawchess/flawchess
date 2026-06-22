---
quick_id: 260620-r3p
status: complete
phase: 130
commits:
  - eaccc350  # frontend: filter preset polish + shared PresetRangeFilter
---

# Quick Task 260620-r3p — Summary

Polished the **Tactic Difficulty** and **Opponent Strength** filters and extracted a
shared `PresetRangeFilter` component from the two near-identical clones.

## What changed

**Shared component** — `components/filters/PresetRangeFilter.tsx` (new). Purely
presentational: label row + InfoPopover + active-summary span, preset chip grid, and a
dual-thumb `Slider`. Both wrappers (`TacticDepthFilter`, `OpponentStrengthFilter`) now
pass their domain results in as props and own only the domain logic. data-testids
unchanged (derived from a `testIdPrefix`); the Opponent root div gained a
`filter-opponent-strength` testid (previously absent).

**Range moved to the top-right summary label** (not the chips, after a user iteration):
- `tacticDepth.formatDepthSummary` → `Intermediate: 0-5` for a preset, bare `2-4`
  (or `3` when min === max) for a custom range. The "Depth" word was dropped.
- `opponentStrength.formatRangeSummary` → `Stronger: ≥+50`, `Similar: ±100`,
  `Weaker: ≤−50`, `Any` via a new module-private `PRESET_SUMMARY_LABELS` map.
- Preset chips are back to plain names (`Beginner` / `Stronger` / …).

**Scale labels removed** — the tick-label rows below both sliders (`0`/`11` and
`≤−200 / 0 / ≥+200`) are gone.

**Cleanup** — Opponent info-popover prose now reads its numbers from the existing
`STRONG_WEAK_THRESHOLD` / `PRESET_THRESHOLD` / `SLIDER_STEP` constants instead of
hard-coded `50` / `100` (no rendered change).

## Verification

Full frontend gate green: `npx tsc -b`, `npm run lint`, `npm run knip` clean;
`npm test -- --run` → 1049 passed. Live screenshot skipped (Chrome extension not
connected); dev server was up on :5173 for manual eyeballing.

On `gsd/phase-130-tactic-tag-improvements-and-fixes`; not pushed.
