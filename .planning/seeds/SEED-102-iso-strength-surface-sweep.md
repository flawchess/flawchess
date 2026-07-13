---
title: Tier-2 iso-strength surface sweep — map (bot_elo × blend) against self-calibrated anchors, with style metrics
trigger_condition: After SEED-101 (anchor ladder self-calibration) lands; blocks SEED-104 and gates the blend-mixture decision
planted_date: 2026-07-13
source: /gsd-explore session 2026-07-13 (bot blend calibration; see .planning/notes/2026-07-13-bot-calibration-findings.md)
---

# SEED-102: Tier-2 iso-strength surface sweep

Map the bot's strength surface over `(bot_elo × blend)` on the internal anchor scale from
SEED-101. This is the **shape**, not the units — SEED-103 supplies the correction to human ELO.

This run also **adjudicates the blend-mixture question** (see note, Finding 1). Do not commit
to an engine redesign of the blend formula before it lands.

## Grid

- **blend: 0, 0.05, 0.25, 0.5, 1** — 0.75 dropped deliberately (the 0.5 → 1 leg bought only
  +154/+198/+375 in the 2026-07-12 run; the upper interior is the least informative region and
  all the action is near zero).
- **bot_elo: 1100, 1500, 1900** at minimum (continuity with the prior run). **Prefer
  {900, 1300, 1700, 2100}** if budget allows — hitting target 1500 at blend 1 needs `bot_elo`
  ≈ 890, which is *below* the 3-point grid and would force SEED-104 to extrapolate rather than
  interpolate.
- **24–30 games per (cell, anchor).** 10 gave ±110 ELO and produced a visibly non-monotone
  ladder. 24 gives ±71 per anchor, ~±35 once ~4 anchors are combined.

## The blend ≈ 0.05 cell is the single highest-information cell

It separates the two effects currently confounded in the 980 → 1938 jump at bot_elo 1500: the
**regime cliff** (no-search → full MCTS) versus the **temperature change** (tau 0.1 → 0.05).

- Lands near **1700–1900** → the cliff is nearly the whole jump, the blend interior is a narrow
  band, and the axis is degenerate as a strength dial.
- Lands near **1200–1400** → the axis is far more continuous than the code structure suggests,
  and a mixture redesign is probably unnecessary.

## Style metrics per cell — the part that answers the actual product question

**Strength is not the product question.** The goal is a *range of playstyles*, and ELO estimates
structurally cannot tell you whether you have one. Log per cell, from games already being played:

- **Maia-agreement rate** — fraction of the bot's moves matching argmax-Maia at its own
  `bot_elo`. This is the operational definition of "how human is this bot". **The decisive
  metric.** Plot it against blend:
  - Falls off a cliff (100% at blend 0 → ~30% at blend 0.05 → flat through blend 1) → the style
    axis is dead; you ship one human bot and N engine bots.
  - Declines smoothly across the range → you have a real playstyle dial and the current
    architecture is fine.
- **Stockfish-agreement rate**, **ACPL**, **blunder rate**, draw rate, game length.

Near-free: the harness already runs Stockfish for adjudication.

## Harness fixes required first

1. **Center the anchor window on the cell's expected strength, not on `bot_elo`.** The current
   `ANCHOR_ELO_WINDOW = 400` brackets around `bot_elo`, but cells sit up to 600 ELO away from
   it — so the informative anchors get pruned (`out_of_window`) and every played anchor sweeps.
   This is why all 9 cells clamped. See note, Finding 3.
2. **Locate-then-measure two-pass** instead of a fixed window:
   - *Locate*: ~8 games vs 2 widely-spaced anchors to place the cell. Matters most for the
     blend 0.05 and 0.25 cells, where there is no prior at all — they could sit anywhere between
     980 and 1938.
   - *Measure*: 24–30 games vs the 3–4 anchors bracketing that estimate. Target scores in the
     0.2–0.8 band; anything outside carries almost no information.
3. **Both anchor families enabled.** The 2026-07-12 run used maia anchors only — every row in
   the TSV is `maiaNNNN`, despite `sf0/sf3/sf5` being in the defaults. maia anchors are
   search-less and share the bot's own blind spot; SF anchors search and fail differently.
   Disagreement between the families is itself a measurement of the style-correlated bias.
4. **Report per-cell CIs**, not just point estimates.

## Budget

~82 games/hr at `--stockfish-procs 4` (raise if cores allow).

- 3 bot_elo × 5 blends = 15 cells × ~4 anchors × 24 games ≈ **1,450 games ≈ 18h**
- 4 bot_elo × 5 blends = 20 cells ≈ **1,900 games ≈ 24h**

Plus SEED-101's round-robin (~2h) and the locate pass.

## Caveat

The output is on the **internal anchor scale**, not human ELO, and must not be labeled as such.
Non-transitivity means a searching bot's rating against search-less anchors is inflated in a
way no amount of anchor relabeling fixes. SEED-103 is the only source of an honest absolute
number.
