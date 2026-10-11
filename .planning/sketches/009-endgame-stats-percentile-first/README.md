---
sketch: 009
name: endgame-stats-percentile-first
question: "How do we make the Endgame Stats bullet/gauge sections readable when zone colors (population IQR) and peer percentiles disagree?"
winner: "Round 2: percentile-first, ranked values displayed, one percentile bar per metric"
tags: [endgames, stats, percentiles, gauges, bullet-charts, mobile, SEED-196]
---

# Sketch 009: Endgame Stats, Percentile-First

## Design Question
Each metric on the Endgame Stats page carries three verdicts that can contradict each other:
zone color (population p25-p75 per TC, filtered all-history value), the peer percentile chip
(rating peers, last 36 months, filter-independent, ranks a *different* value than the one shown),
and the magnifier popover's z-test verdict. Gauges duplicate the WDL bar. How do we simplify?

Baseline screenshots: `temp/endgame-redesign/01-*.jpg` to `18-*.png` (2026-10-11, dev, mobile width).

## How to View
open .planning/sketches/009-endgame-stats-percentile-first/index.html
(TC switches are synced; hover a percentile for the popover; "Show design notes" toggles the annotations)

## Round 1 to round 2 (owner decisions 2026-10-11)
- Percentiles are the main metric. Display the **ranked value** (the peer-sample value), not the
  filtered whole-history value.
- Grey "typical range" is acceptable for Endgame Type Breakdown (no per-type percentiles).
- Keep the "Compared to similar-rated players" card for now; may be removed later.
- Statistical details (n, CI, p-value) stay, greyed out below a separator in the popover.
- Clock Gap at Endgame Entry timeline: grey band instead of red/blue/green zones.

## Illustrative data
Percentiles, ranked values and anchors are real dev data (user 1, blitz/rapid). The ranked-sample
WDL splits, with/without-endgame scores, entry evals and the stats footers are **made up** because
the backend does not compute them on the ranked sample yet.
