---
title: Anchor ladder self-calibration — round-robin the maia/SF anchors against each other to get real internal spacing
trigger_condition: Before the next calibration harness sweep (blocks SEED-102); ideally immediately — it is cheap and everything downstream depends on it
planted_date: 2026-07-13
source: /gsd-explore session 2026-07-13 (bot blend calibration; see .planning/notes/2026-07-13-bot-calibration-findings.md)
---

# SEED-101: Anchor ladder self-calibration

Make the calibration harness's anchors mean something **relative to each other** before using
them to rate anything. Today we assume `maia1500` is 400 points stronger than `maia1100` and
that `sf3 ≈ 1750`. Both assumptions are unverified, and we have strong evidence at least the
first one is wrong.

## Why

Two independent problems with the current anchor pool (details in the note):

1. **Maia rung labels are not human ELO.** The official Maia bots' real lichess ratings show
   the Maia-1 ladder compresses ~3.3x (nominal 1100/1500/1900 → real blitz 1373/1507/1611).
   We run Maia-3, so the magnitude is unknown — but the mechanism (argmax truncates the blunder
   tail at the bottom; no search caps strength at the top) is structural and applies to us.
   If our ladder is similarly compressed, a "400-point anchor window" is only ~120 real ELO
   wide, which independently explains why **all 9 cells of the 2026-07-12 run clamped**.
2. **The Stockfish Skill Level → ELO map is folklore.** `SF_SKILL_ELO = {0:1320, 3:1750,
   5:2200}` (`scripts/lib/calibration-anchors.mjs:38`) is explicitly flagged approximate, and
   168-RESEARCH.md Open Question 2 never closed it.

For Tier-2 work (measuring the *shape* of the bot's strength surface) we do **not** need the
anchor labels to be right. We need their **spacing** to be known. That is directly measurable.

## What

Round-robin the anchors against each other and fit a rating model over the resulting game
graph, producing every anchor's position on **one common internal scale** with real spacing.

- **Maia-argmax rungs:** 700, 1100, 1500, 1900, 2300 (wide — fine 100-ELO steps are false
  precision until spacing is known).
- **SF Skill levels:** 0, 3, 5, plus 1–2 stronger (8, 10) — the blend-1 bot cells reach ~2500
  nominal and currently run off the top of the SF ladder entirely.
- **Cross-family games (maia vs SF) are the important ones** — they put both ladders on the same
  scale, which is what makes the SF anchors usable as an independent check on the maia anchors.
- Fit with a standard logistic/BayesElo-style model over the pairwise results. Anchor the scale
  arbitrarily (e.g. fix `maia1500 = 1500`); SEED-103 supplies the correction to human ELO later.

## Why it's cheap

**Anchor-vs-anchor games have no MCTS in the loop.** The 2026-07-12 run's ~82 games/hr was
dominated by the *bot's* 1–2.5s moves; anchor moves take ~0.09s. These games should run an
order of magnitude faster — a couple of hours, not days. This is the highest
information-per-CPU-hour experiment available.

Don't need a full round-robin: adjacent pairs plus a few long-range skips and cross-family links
is enough to constrain the fit. ~24–30 games/pair.

## What it unblocks

- **SEED-102** — you cannot sensibly pick per-cell anchors without knowing the ladder's real
  spacing, and you cannot combine maia and SF estimates without a common scale.
- Answers whether Maia-3's argmax ladder is compressed like Maia-1's. If it is, the maia anchors
  have a narrow effective dynamic range and the strong bot cells *must* lean on SF anchors.
- Retires 168-RESEARCH.md Open Question 2 (SF Skill → ELO) as a blocker, by making it irrelevant
  for relative work.

## Caveats

- This produces an **internal** scale. It is not human ELO and must never be labeled as such in
  any artifact or UI. See the SEED-091 caveat already carried in the summary TSV.
- Non-transitivity applies here too: maia-argmax and SF-skill fail differently, so a single
  scalar rating over a mixed pool is an approximation. Report the model's fit residuals — large
  cross-family residuals are themselves the signal that style is confounding strength.
