---
sketch: 002
name: flaw-stats-panel
question: "How does the Flaw-Stats panel above the games list arrange per-severity rates + tag distribution (tempo split, result-changing, phase) + trend-over-time + the % analyzed / N denominator?"
winner: "A"
tags: [panel, stats, library, games, charts, mobile]
phase: 107
---

# Sketch 002: Flaw-Stats Panel

## Design Question
The milestone centerpiece. Above the games card list, over the filtered analyzed-only set, the
panel shows: per-severity **rates** (per game / per 100 moves), the full **tag distribution**
(tempo split, result-changing rate, opportunity rates, phase histogram), a **trend-over-time**
series (the headline "am I blundering less than I used to?"), and the explicit **`% analyzed` + N
denominator** so it never implies clean games where evals are simply absent. What information
hierarchy makes this skimmable without burying the trend?

## How to View
open .planning/sketches/002-flaw-stats-panel/index.html

The per-game / per-100-moves toggle changes the numbers live; the trend chart is the declining
blunder-rate headline. Toolbar (bottom-right) constrains width — try 420 to feel mobile reflow.

## Variants
- **A: Horizontal stat band + trend** — severity-rate cells in one row (denominator pinned right),
  a compact tag-distribution block, then the full-width trend. Linear "how often → what kind →
  over time" read.
- **B: Two-column + full-width trend** — left card = severity rates + denominator, right card =
  full tag breakdown (tempo stacked bar, opportunity/impact rates, phase histogram), trend spans
  below. Cleanest "how many vs what kind" separation.
- **C: Compact KPI tiles** — dense tile grid (number + label + delta), trend as a wide sparkline
  tile, denominator as its own tile; full breakdown moves behind a "View tag breakdown ▸" link.
  Shortest panel; weakest at showing the distribution at rest.

## What to Look For
- Is the **trend** prominent enough? It's the headline insight — should it ever be the *first*
  thing, not last (A/B put it below)?
- Does the **denominator** (% analyzed + N) read clearly without dominating?
- **Tempo split** as a stacked bar vs separate bars — legible?
- How short can the panel get before a long card list? (C is shortest.)
- **Mobile** (420px): which layout reflows most gracefully above the cards?
- Per-game vs per-100-moves — is the toggle the right control, or show both?
