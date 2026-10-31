---
sketch: 013
name: out-of-the-opening
question: "How should the per-colour 'came out worse / better' rates look on the Openings Stats tab without reading as a WDL bar?"
winner: "A"
tags: [openings, stats, percentiles, eval, mobile]
---

# Sketch 013: Out of the Opening

## Design Question
A new per-colour section on the Openings Stats tab (above the findings cards, under the sticky
White | Black switch) showing how often the player leaves the opening clearly worse or clearly better,
ranked against benchmark peers at their rating and TC. It must not read as a WDL bar.

## Metric (from the 2026-10-31 explore session, data in `temp/opening-narration/`)
- Per game: user-POV eval at the first middlegame ply minus the colour baseline (+0.25 White,
  −0.25 Black). **Worse** ≤ −1.0, **better** ≥ +1.0. Mate scores count by sign.
- Games that end before the middlegame (~5%): resignation / checkmate / timeout count by result
  (loss → worse, win → better); abandoned and drawn ones are excluded. The §2.1 benchmark recipe drops
  these, which removes the clearest opening disasters.
- Benchmark (9,186 user × colour × TC cells): reliability 0.95 at ≥100 games, colour collapses
  (|d| ≤ 0.15), strongly rating-dependent (worse rate median 35% at 800, 21% at 1600, 13% at 2400), so
  it needs ELO × TC-anchored percentiles. The worse rate predicts score within ELO × TC (−1.0 pp per
  SD) better than the mean eval does; the better rate barely does (+0.6). ±1.0 is the lowest threshold
  on the predictive plateau (0.5 → 3.0 sweep). Within-player SD was rejected (mixes both tails, d 3.85
  on ELO).

## How to View
open .planning/sketches/013-out-of-the-opening/index.html
(White | Black switch; bottom-right: Desktop/Phone, Data = Typical / New user / Analyzing.
Deep links for screenshots: `#b`, `#c-phone`, `#a-pop`, `#a-black-new`.)

## Variants
- **A: Per-TC cards, percentile rows** — one card per TC, two `RankedMetricRow`-style rows with the
  real `PercentileBar` (25–75 band, median tick, dot red/blue/green only when significant). Path of
  least resistance: reuses the Endgames components verbatim.
- **B: One table, rate bars vs peers** — TC rows × Worse / Better columns. The bar axis is the rate
  itself (0–50%), the grey band is the peer IQR, "better to the right" (the worse axis runs reversed).
  Percentile only in the popover. Closer to the 010 gap bars.
- **C: Worse | better, diverging** — per TC one centred axis: worse grows left, better grows right,
  neutral fill, peer bands on each side, percentile words underneath. "Even" is implicit, so there is
  no composition to mistake for W/D/L.
- **D: Per opening (expanded row)** — optional second part: the same two rates inside the repertoire
  expanded row, descriptive only, with a tick at the player's own overall rate (no peer rank, faded
  under 20 games). Answers "which lines produce my bad openings?".

All variants share the popover: what the rate means, a histogram of the player's eval after the opening
with the ±1.0 cuts (selected side dark), and a footer with counts, the peer band, the percentile in
words, the peer definition, filter independence and the rating dependence (percentile chip disclosure
rule).

## What to Look For
- Does any variant still read as W/D/L? (C is the riskiest: two bars from a centre.)
- Is "58th" understandable for an inverted metric, or do the words ("Fewer worse games than 58% of
  peers") have to carry it? A and C show both; B hides the percentile in the popover.
- Per-TC cards (A) vs one table (B): the Openings page has no TC switch, so every played TC is shown.
- Phone: A stacks cards (long), B stacks rows, C stacks labels over the track.
- Popover: is the histogram worth its height?

## Decision (owner, 2026-10-31)

**Winner: A, per-TC cards with percentile rows**, on rating × TC canonical-slice CDFs (the Endgames
machinery). The same two bars come back per opening in the repertoire expanded card, next to Score over
Time, against the peer band instead of a percentile (variant D's idea, with the peer band replacing the
"your overall rate" tick).

Rejected after review:
- **B / opponent framing ("you vs. your opponents", 010-style zero-centred gap):** for a shared
  position-state metric the opponent's centred eval is exactly minus yours, so "opponent came out worse"
  IS "you came out better". Worse and better collapse into one identity (better − worse), and a sharp
  30/30 player reads the same as a solid 12/12 one. See
  `.planning/notes/opponent-mirror-as-self-calibrating-cohort.md` ("When not to use this").
- **C (diverging):** closest to a WDL look.
- **A custom 200-game "current" window:** breaks the canonical-slice symmetry (the CDF and the user value
  must come from the same builder) and gives a wobbly percentile (SE ≈ 2.8 pp vs a ~13 pp peer IQR).
  The section uses the Endgames rule (most recent 3000 games within 36 months per TC, ±100 opponents,
  floor 30, 99% significance gate); current form lives in the per-opening cards, which follow the page
  filters.

Full reasoning: `.planning/notes/out-of-the-opening-metric-design.md`. Seed: `.planning/seeds/SEED-261031-x3l-out-of-the-opening-worse-better-rates.md`.
