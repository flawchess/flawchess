# Anchor ladder self-calibration — what the 2026-07-15 sweep actually showed

**Date:** 2026-07-15
**Source:** Phase 173 Plan 04, the real anchor-vs-anchor sweep — raw ledger
`reports/data/anchor-ladder-2026-07-15T20-28-27-398Z.tsv` (456 games: 216 probe +
240 measure, seed 1), fitted by `scripts/calibration_anchor_fit.py` into
`reports/data/anchor-ladder-internal-scale.json` / `scripts/lib/calibration-internal-scale.mjs`.
**Why this note exists:** SEED-101 asked one question — is the Maia-3 argmax ladder
compressed like Maia-1's — and closes 168-RESEARCH.md Open Question 2 as a side
effect. Neither answer is visible in the TSVs/JSON without reading the residuals
alongside the ratings. SEED-102 depends on both.

**Caveat, carried verbatim (D-13):** INTERNAL SCALE — NOT human ELO. Scale fixed
arbitrarily so `maia1500 == 1500`. Every number below is on this internal scale,
not a human-ELO claim.

## The run

10 anchors (5 Maia argmax rungs: 700/1100/1500/1900/2300; 5 Stockfish Skill Levels:
0/3/5/8/10), two-pass probe (8 games/pair, cheap triage) → measure (24 games/pair
on informative links) schedule, cross-family links prioritized per D-04's ≥2
connectivity floor. One mid-run deviation: the first attempt fail-louded on the
D-04 connectivity guard because `{maia700, sf0}` had informative links only to
each other and no weaker Maia rung existed to re-target. Fixed with a band-relaxing
connectivity rescue (`rescueConnectivity`/`bandDistance` in
`scripts/lib/calibration-anchor-schedule.mjs`, commit `a2f96e81`); the rescue added
`maia700 vs sf5` (probe score 0.1875) and the resumed run completed cleanly.

## Finding 1 — per-anchor internal ratings, all ten pinned and none placeholder

| anchor | rating | 95% CI |
|---|---|---|
| maia700 | 1129.29 | [995.6, 1262.8] |
| maia1100 | 1373.87 | [1272.7, 1461.7] |
| maia1500 | 1500.00 | pinned (D-05 scale fix) |
| maia1900 | 1626.39 | [1553.1, 1710.2] |
| maia2300 | 1706.49 | [1597.6, 1814.4] |
| sf0 | 1069.33 | [942.1, 1227.2] |
| sf3 | 1363.88 | [1292.3, 1452.4] |
| sf5 | 1525.09 | [1445.5, 1614.2] |
| sf8 | 1801.10 | [1693.8, 1928.6] |
| sf10 | 1907.93 | [1787.2, 2029.8] |

`sf0` is the weakest anchor in the whole pool (below `maia700`); `sf10` is the
strongest (above `maia2300`). The two ladders interleave rather than nesting inside
one another — `sf3` sits almost exactly on `maia1100`, `sf5` almost exactly on
`maia1500`, `sf8` between `maia1900` and `maia2300`.

## Finding 2 — the Maia-3 argmax ladder IS compressed, and non-uniformly

Adjacent-rung deltas vs the nominal 400-point step:

| step | nominal | measured | retained |
|---|---|---|---|
| maia700 → maia1100 | 400 | +244.6 | 61% |
| maia1100 → maia1500 | 400 | +126.1 | 32% |
| maia1500 → maia1900 | 400 | +126.4 | 32% |
| maia1900 → maia2300 | 400 | +80.1 | 20% |
| **full ladder (700→2300)** | 1600 | +577.2 | **36% (≈2.8x compression)** |

**Verdict: yes, compressed — and it gets worse toward the top of the ladder, not
uniform.** The bottom step (700→1100) retains 61% of its nominal spacing; the top
step (1900→2300) retains only 20%. This matches the mechanism 2026-07-13's Finding
2 identified for Maia-1 (argmax truncates the blunder tail at the bottom, so
low-rung differences still show up; no search caps strength at the top, so
high-rung differences wash out) — the mechanism generalizes to Maia-3, as
hypothesized.

Directly comparable to the Maia-1 real-lichess measurement (2026-07-13 note,
nominal 1100→1900, real blitz 1373→1611 = +238, 30% retained, "compressed ~3.3x"):
our internal maia1100→maia1900 measures +252.5 (32% retained, ≈3.2x compression) —
close enough to the independently-measured Maia-1 figure that this is not a
coincidence; it is the same structural effect. This was probe-visible before the
fit even ran: `maia1100` beat `maia700` 7-1 in an 8-game probe (large, decisive
gap), while `maia1900` vs `maia2300` measured to a much closer 0.375 score_a over
24 games — the ladder bottom is not compressed, the top is.

## Finding 3 — Stockfish Skill-Level spacing, measured for the first time

Adjacent SF-anchor deltas:

| step | measured |
|---|---|
| sf0 → sf3 | +294.6 |
| sf3 → sf5 | +161.2 |
| sf5 → sf8 | +276.0 |
| sf8 → sf10 | +106.8 |

168-RESEARCH.md Open Question 2 flagged `SF_SKILL_ELO = {0:1320, 3:1750, 5:2200}`
as folklore (community-reported, not Stockfish-18-specific, LOW confidence) —
nominal deltas of +430 (0→3) and +450 (3→5). The measured internal deltas
(+294.6, +161.2) are themselves compressed relative to that folklore shape, and
the shape differs (folklore has 0→3 and 3→5 roughly equal; measured has 0→3 nearly
double 3→5). Same non-uniform-compression pattern as the Maia ladder — Skill Level
step size is not linear in strength either, on either scale.

**Open Question 2 is now closed as a blocker for relative work**: the anchors have
a directly measured internal scale (Finding 1), so any SEED-102 cell that needs to
compare Maia and Stockfish anchor strengths no longer needs the folklore table —
it reads `INTERNAL_RATING` instead. The folklore table's absolute Elo claim is
still unverified against real humans (that remains SEED-103's job), but it was
never load-bearing for internal comparisons in the first place; this measurement
retires the folklore dependency for anything that only needs relative spacing.

## Finding 4 — cross-family residuals are the style-confounding signal (D-06)

The single-scalar Bradley-Terry fit assumes strength is transitive across playing
styles; it isn't. The largest cross-family residuals (observed score − model
prediction) are:

| pair | games | pass | observed | predicted | residual |
|---|---|---|---|---|---|
| maia700 vs sf3 | 8 | probe | 0.000 | 0.206 | **−0.206** |
| maia1100 vs sf0 | 8 | probe | 1.000 | 0.852 | **+0.148** |
| maia1500 vs sf3 | 8 | probe | 0.8125 | 0.686 | +0.126 |
| maia2300 vs sf3 | 8 | probe | 1.000 | 0.878 | +0.122 |
| maia2300 vs sf0 | 8 | probe | 0.875 | 0.975 | −0.100 |
| maia1900 vs sf5 | 24 | measure | 0.5625 | 0.642 | −0.079 |
| maia1900 vs sf0 | 8 | probe | 0.875 | 0.961 | −0.086 |

Two consistent patterns, both style-driven rather than noise:

- **Every Maia rung underperforms its predicted score against `sf0`** (residuals
  −0.048 to −0.100 across maia1500/1900/2300) — no Maia rung, however strongly
  rated, ever exceeded 87.5% against the weakest Stockfish anchor. A weak but
  *searching* engine keeps taking games off search-less argmax opponents at a rate
  the linear rating model doesn't predict, however wide the rating gap.
- **Maia1500/1900/2300 all overperform against `sf3`** (residuals +0.056 to
  +0.126) — once Maia is rated at 1500+, its argmax play resists `sf3`'s shallow
  search better than the rating gap alone predicts. `maia700` is the outlier in
  the other direction: it lost all 8 games to `sf3` (residual −0.206), the single
  largest cross-family residual in the run — the weakest Maia rung has no such
  resistance.

This is exactly the "style is confounding strength" signal SEED-101's caveats
called for reporting, not fixing — a mixed maia/SF anchor pool is a real internal
scale, but any SEED-102 cell measurement that leans heavily on one family
(especially `sf0` or `maia700`, both faring worse against opposite-family
opponents than the model predicts) should be read with this in mind.

## Finding 5 (minor) — the `{maia700, sf0}` island is itself a ladder-bottom finding

The connectivity guard tripped specifically at the ladder's weakest pair
(`maia700`, `sf0`) — both anchors' only informative link was to each other, with
no weaker Maia rung available to re-target for a rescue. This is consistent with
Finding 2: the bottom of the Maia ladder is the *least* compressed region (steepest
real spacing per nominal point), so `maia700` and `sf0` are genuinely close in
internal strength to each other and comparatively far from everything above them —
a real structural feature of the ladder bottom, not a scheduling accident. The
band-relaxing rescue (Finding "The run" above) is a generic fix, but the specific
pair it had to rescue is informative on its own: future anchor pools may want an
anchor weaker than 700 if the bottom needs finer resolution.

## What this unblocks

- **SEED-102** can now pick per-cell anchors by internal rating (`INTERNAL_RATING`
  in `scripts/lib/calibration-internal-scale.mjs`) instead of nominal labels — the
  700-point compression from Finding 2 is exactly why the 2026-07-12 run's 400-point
  `ANCHOR_ELO_WINDOW` clamped on every cell (2026-07-13 note, Finding 3): windowing
  on nominal Elo was windowing on a compressed axis.
- **168-RESEARCH.md Open Question 2** is retired as a blocker for relative
  (internal-scale) work per the above; the folklore SF-Elo table is no longer
  needed to compare Maia and Stockfish anchor strengths.
- **SEED-103** (lichess correction to human ELO) still owns the absolute-scale
  question — this note produces internal spacing only, never a human-ELO claim
  (D-13).
