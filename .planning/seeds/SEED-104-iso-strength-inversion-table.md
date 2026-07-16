---
title: Per-style strength lookup curves — target ELO → bot_elo per style level, with honest per-style slider ranges
trigger_condition: After SEED-102 (curves) and SEED-103 (correction) land; gates *labeled* bots (SEED-091 preset cards, SEED-098 personas, calibrated custom-bot builder). NOT a blocker for Phase 171, which ships raw uncalibrated sliders
planted_date: 2026-07-13
source: /gsd-explore session 2026-07-13 (bot blend calibration; see .planning/notes/2026-07-13-bot-calibration-findings.md); rescoped 2026-07-15 /gsd-explore (two-style simplification, Option A per-style ranges)
---

# SEED-104: Per-style strength lookup curves

Turn SEED-102's calibrated curves into the shipping artifact: for each of the two style levels,
a lookup `target_elo → bot_elo` with an honest per-style strength range.

## Rescoped 2026-07-15: the 2D inversion table is dead

The original design fit a smooth 2D surface `measured_elo = f(bot_elo, blend)` with an
interaction term, inverted it analytically, and clamped a continuous playstyle slider per
target ELO (the "reachability parallelogram"). Decision (2026-07-15 explore session): the
product ships **two discrete style levels** (blend 0 "human-like", blend 0.05 "engine-like"),
so this collapses to **two 1D curves**, each fit from ~5 measured points and interpolated in
100-ELO steps. No surface, no interaction term, no analytic inversion.

## The problem it still solves

Unchanged from the original: at fixed `bot_elo`, style changes strength massively (2026-07-12
run: bot_elo 1500 played ~980 at blend 0 vs ~2090 at blend 1, uncorrected). Two fixed levels
discretize that coupling but don't remove it — **each level needs its own strength mapping**.
And `bot_elo` is not a rating; it is a Maia-conditioning input. It never surfaces to users.

## The design (Option A: per-style honest ranges)

The user picks a **style** (human-like / engine-like) and a **target strength** (continuous or
100-ELO steps). Each style exposes only the range it can actually reach:

| style | internal | expected reachable range (calibration decides) |
|---|---|---|
| human-like | blend 0, `bot_elo` from curve A | low end down to ~600-ish; ceiling ~1900–2000 (no-search ceiling + Maia ladder top) |
| engine-like | blend 0.05, `bot_elo` from curve B | floor plausibly ~1200+ (search floor); top toward ~2600 |

The two ranges deliberately differ. The overlap zone (roughly 1300–1900, pending measurement)
is where users get a genuine style choice at equal strength — the product's differentiator.
Selecting a style outside its range is impossible by construction, which replaces the old
parallelogram-clamping logic with plain per-style slider bounds.

The measured floor/ceiling of each SEED-102 curve **is** the slider range. Ladder caveat still
applies: Maia-3's validated band is 1100–2000 (`maiaEncoding.ts:35-45`); curve segments built
on `bot_elo` outside that band are extrapolation and should be flagged or trimmed.

## Method

1. Fit each 1D curve `measured_elo = f_style(bot_elo)` to SEED-102's ~5 points (monotone fit;
   isotonic or low-order polynomial — fit, don't tile).
2. Apply the per-style SEED-103 correction to convert to human ELO.
3. Invert each curve into a `target_elo → bot_elo` lookup (100-ELO steps).
4. **Validate the inversion.** Predict "(bot_elo X, human-like) plays 1500", then *run that
   cell* in the harness. Two or three confirmation cells per style. This tests the artifact you
   actually ship, not the model you fit — cheap, and the step most likely to be skipped.

## Consumers (the end-goal architecture, decided 2026-07-15)

The two curves are the **single source of truth for all bot strength claims**:

- **Custom bot builder** (evolution of Phase 171's surface): style toggle + per-style target-ELO
  slider, both reading these curves. Once it consumes them, it is a labeled surface (SEED-103
  gate applies).
- **SEED-091 preset bot cards / SEED-098 personas**: presets become **named points on the same
  curves** ("1400, human-like" = curve lookup) — nothing new to measure per preset. Persona
  perturbations (SEED-098) fold in as measured ELO offsets on top, as that seed already
  proposes; but note SEED-098's own caveat that its levers are split across the blend-0 /
  blend>0 regimes — with only two levels, each persona lever simply belongs to one style.

## Relationship to Phase 171 (decided 2026-07-13, unchanged)

**Phase 171 ships raw, uncalibrated `bot_elo` + `blend` sliders and does not consume these
curves.** Uncalibrated sliders make no promise; 171's actual blocker is SEED-100 (blend-0
pacing). Useful side effect while it exists: play blend 0 vs 0.05 by hand at equal `bot_elo` —
if they are indistinguishable at the board, the two-style product story has a problem, and
perceived difference is the actual product metric (cheaper and more decisive than any
Maia-agreement percentage).
