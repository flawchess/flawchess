---
title: Iso-strength inversion table — (target_elo, style) → (bot_elo, blend), so the playstyle slider stops being a secret strength slider
trigger_condition: After SEED-102 (surface) and SEED-103 (correction) land; gates *labeled* bots (SEED-091 preset cards, SEED-098 personas). NOT a blocker for Phase 171, which ships raw uncalibrated sliders
planted_date: 2026-07-13
source: /gsd-explore session 2026-07-13 (bot blend calibration; see .planning/notes/2026-07-13-bot-calibration-findings.md)
---

# SEED-104: Iso-strength inversion table

Invert the calibrated strength surface so the two user-facing sliders become **independent**.

## The problem it solves

Today the two knobs are coupled, and the coupling is invisible to the user. From the 2026-07-12
run: a user picks **ELO 1500**, then drags the playstyle slider toward human, and the bot
silently drops to ~980. Drags it toward Stockfish and it jumps to ~2090. **The playstyle slider
is secretly a ±500 ELO strength slider.**

Separately, `bot_elo` is not a rating at all — it is a Maia-conditioning input. Exposing it to
users as "the bot's ELO" is a lie, and the harness numbers show how big a lie.

## The design

Keep **both** sliders. Make them mean what they say.

| | user sees | internal |
|---|---|---|
| slider 1 | target playing strength | — |
| slider 2 | playstyle (human ↔ precise) | — |
| | | lookup `(target, style)` → `(bot_elo, blend)` |

Dragging the playstyle slider now holds strength roughly constant and only changes *how* the bot
plays — walking it along an iso-strength curve. `bot_elo` never surfaces.

**Illustrative iso-curve for target ~1500** (from the uncorrected 2026-07-12 data — real numbers
come from SEED-102 + SEED-103):

| playstyle | bot_elo needed |
|---|---|
| blend 0 (human) | ~1930 |
| blend 0.5 | ~1210 |
| blend 1 (precise) | ~890 |

## Method

1. Fit a smooth surface `measured_elo = f(bot_elo, blend)` to the SEED-102 grid (an interaction
   term is needed — the `bot_elo` slope varies by blend: ~0.75 at blend 0, ~1.2 at blend 0.5,
   ~1.0 at blend 1). Fit, don't tile.
2. Apply the SEED-103 correction to convert to human ELO.
3. Invert analytically into the lookup table.
4. **Validate the inversion.** Predict "(bot_elo 1210, blend 0.5) plays 1500", then *run that
   cell*. Three or four confirmation cells. This tests the artifact you actually ship, not the
   model you fit — cheap, and the step most likely to be skipped.

## The reachability parallelogram — a real UI constraint

Iso-strength curves run off the Maia ladder (600–2600) at the corners:

- **Target 2200 at full-human** needs `bot_elo` ≈ 2900 — past the 2600 ceiling.
- **Target 800 at full-precise** needs `bot_elo` ≈ 200 — below the 600 floor.

So the reachable region is a **parallelogram, not a rectangle**: "very human *and* very strong"
and "very precise *and* very weak" are both unreachable. The playstyle slider's usable range has
to shrink at the extremes of the ELO range. Clamp its endpoints per target ELO (honest) rather
than letting it travel full width while strength silently drifts (the current failure mode,
reintroduced).

Also note the ladder's own validated band is only **1100–2000** (`maiaEncoding.ts:35-45`);
600–1000 and 2100–2600 are extrapolation. The corners are doubly shaky.

## Open question this depends on

Whether the **blend interior is a real playstyle axis at all** (note, Finding 1). If SEED-102's
Maia-agreement-rate metric shows a cliff — 100% at blend 0, ~30% at blend 0.05, flat thereafter —
then the "style" slider has one human notch and N engine notches, and no inversion table can fix
that. The strength coupling and the style axis are **two separate defects**: this seed fixes the
first; the second would need a blend-formula redesign (a log-linear Maia × Stockfish mixture in
the sampling weights, so both terms are live at every blend).

**Do not presume that redesign is needed.** SEED-102 measures it.

## Relationship to Phase 171 (decided 2026-07-13)

**Phase 171 ships raw, uncalibrated `bot_elo` + `blend` sliders and does not consume this table.**
That is deliberate: uncalibrated sliders make no promise, and 171's actual blocker is SEED-100
(blend-0 pacing). This seed gates the *labeled* surfaces — SEED-091's preset bot cards and
SEED-098's personas — where an advertised ELO becomes a claim we have to honour.

Useful side effect: 171 is also the **cheapest probe of the style-axis question** that SEED-102
would otherwise spend 18–24h on. Play blend 0 / 0.05 / 0.25 / 0.5 / 1 by hand. If 0.05 and 0.5
are indistinguishable at the board, the interior is degenerate and you know it more convincingly
than any Maia-agreement percentage would tell you — perceived difference is the actual product
metric. Do this before committing to the expensive sweep.

## Downstream

- **SEED-098** (bot personas) composes cleanly: a persona becomes a perturbation of the
  iso-strength surface, its ELO offset measured once and folded into this lookup — which is
  already what SEED-098's calibration section proposes. But see SEED-098's own caveat section:
  its two levers (Maia prior reweighting, `practicalScore` shaping) are currently split across
  the blend-0 / blend>0 regimes, and **neither works across the whole slider**. That is the same
  underlying defect as the style-axis question above.
