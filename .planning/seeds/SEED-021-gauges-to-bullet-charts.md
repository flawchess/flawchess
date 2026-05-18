---
id: SEED-021
status: open
planted: 2026-05-18
planted_during: /gsd-explore session reviewing /endgames/stats chart quality — explored whether to delete the gauges; concluded keep-for-now, replace later as a single encoding refactor
trigger_when: Surface when either (a) the colour-blind-mode work is scoped (it touches the same WDL/zone-band/gauge components and shares the encoding refactor), or (b) the next endgame-stats visualization pass is being planned, or (c) users report difficulty comparing the per-type Conversion/Recovery across endgame types.
scope: phase (single, ~3-4 plans) — replace Conversion/Parity/Recovery gauges + the per-type gauge grid with bullet bars carrying CI + significance, with headline emphasis via size/typography/position rather than chart type
depends_on: none (Endgame Overall Performance card restructure and timeline annotations are independent)
---

# SEED-021: Replace endgame gauges with bullet charts

## Why This Matters

The Endgame Metrics section (Conversion / Parity / Recovery) and the Endgame Type Breakdown grid currently use radial gauges. Gauges are an inferior statistical encoding: no confidence interval, no hypothesis test, low data-ink, redundant (the number is printed anyway), and poor for cross-comparison. The project already has a trusted bullet-band encoding (zoned track + whisker/box marker) used everywhere else on the page for "your value vs benchmark zone".

Two reasons this was deferred, not done now:

1. **The gauges' worst flaw doesn't bite where they headline.** Conversion / Parity / Recovery are not commensurable (different denominators, different meaning) — users don't compare them against each other, so the "gauges are bad for comparison" critique is weak there. The salience and visual-variety value is real for headline metrics.
2. **It's the same refactor as colour-blind mode.** Both touch the WDL bars, zone bands, and gauge components. Doing them together avoids churning the same files twice.

The strongest case for replacement is the **per-type breakdown** (10 tiny needles showing the *same* metric across 5 endgame types, where comparison is the entire point).

## Target Design (when triggered)

- Replace gauges with the existing bullet-band encoding, extended with a CI whisker + a significance marker (the math helpers from Phase 85.1 / 87.2 already exist).
- Achieve "these are the headline three" via **scale, typography, and position**, not via a distinct chart type — a large bold bullet bar visually distinct from the small per-type rows.
- Convert the per-type Conversion/Recovery gauge grid to compact bullet rows for vertical-scan comparison.

See [[../notes/endgame-stats-viz-decisions]] (threads 1 & 7) for full rationale.
