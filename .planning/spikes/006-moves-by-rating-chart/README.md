---
spike: 006
name: moves-by-rating-chart
type: standard
validates: "Given a position's per-ELO move-probability data, when rendered, then it matches the reference 'Moves by Rating' screenshot: per-move lines over ELO, you-are-here marker, top-N ∪ {blunder,best} cap, theme colors, paired with the Pillar A verdict"
verdict: VALIDATED
related: [004]
tags: [maia, recharts, ui, chart, seed-081]
---

# Spike 006: "Moves by Rating" chart

## What This Validates

That we can render the chart from the screenshots — and pair it with the Pillar A verbal
verdict — faithfully, with the locked cap rule (top-N by peak probability ∪ {your move, best})
and a "you are here" ELO marker.

## How to Run

Open `index.html` in a browser (self-contained, no deps, no build). Hover/tap the chart for a
per-ELO tooltip of every shown move's probability.

> **Spike vs production:** this spike hand-rolls the chart as inline SVG so it runs with zero
> build. The **real build uses Recharts** (`recharts@3.8.1`, already a frontend dep) — a
> `<LineChart>` with one `<Line>` per shown move, a `<ReferenceLine x={playerElo}>` for the
> marker, colors from `theme.ts`. The spike proves the *shape, cap logic, and verdict pairing*;
> porting to Recharts is mechanical.

## What to Expect

- The **Ne4 example** from the screenshot: `Ne4` (your blunder, salmon) humps to a peak ~1800
  then decays; `O-O` (best, green) mirrors it with a dip; minor moves sit low.
- A brown **"you 1500"** dashed vertical marker.
- Emphasis: blunder + best drawn thick/opaque, others thin/muted, each end-labeled.
- A **verdict banner** above the chart ("Growth edge — drill this", salience × trainability).
- A **cap note** listing which moves were hidden below the top-N ∪ {blunder,best} rule.

## Investigation Trail

- Data are representative curves matching the reference screenshot (real values come from the
  Maia inference in the build — spike 004). Chose 11 ELO samples (600→2600 step 200) and a
  Catmull-Rom smoothing to mimic Recharts `type="monotone"`.
- Implemented the **cap rule** exactly as locked: sort by each move's *peak* probability across
  the ELO range, keep top 5, then `union` the blunder and best moves even if below the cut.
  Ranking by peak (not by prob-at-your-ELO) keeps a line visible if it dominates at *any*
  level — which is what makes the hump/crossover legible.
- Added hover tooltip (per-ELO probabilities, sorted) so the chart *feels* live, not static.

## Results

**VERDICT: VALIDATED** (pending the user's visual confirmation — see checkpoint). The reference
visual reproduces cleanly, the cap rule and the you-are-here marker work, and pairing the
verdict banner with the chart demonstrates the "takeaway + evidence" model from the seed. No
blocker; production port to Recharts is mechanical.
