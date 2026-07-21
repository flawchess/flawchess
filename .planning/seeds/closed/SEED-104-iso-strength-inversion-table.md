---
title: Per-preset strength lookup curves — target blitz ELO → bot_elo for Human/Light/Deep, via the internal − G + C offset model, with honest per-preset ranges and an approximate-ELO disclaimer
trigger_condition: After SEED-102 (three curves + per-preset G) lands. Gates *labeled* bots (preset cards, SEED-098 personas, calibrated custom-bot builder). NOT a blocker for the raw uncalibrated slider surface
planted_date: 2026-07-13
source: /gsd-explore 2026-07-13 (see .planning/notes/2026-07-13-bot-calibration-findings.md); rescoped 2026-07-15 (two-style, Option A ranges); re-rescoped 2026-07-19 (three presets, literature-based absolute pin — SEED-103 closed)
---

# SEED-104: Per-preset strength lookup curves

Turn SEED-102's three internal-scale curves into the shipping artifact: for each preset, a
lookup `target_blitz_elo → bot_elo` with an honest per-preset range, an **approximate** ELO
label, and a disclaimer.

## The offset model (decided 2026-07-19 — no human ground truth)

Since SEED-103 (lichess-vs-humans) is **closed**, the absolute scale is set by literature, not
by our own play. The full conversion is:

```
human_blitz(preset, bot_elo) = internal_rating(preset, bot_elo)  −  G_preset  +  C
```

| term | source | value / status |
|---|---|---|
| `internal_rating(preset, bot_elo)` | SEED-102 curves (per preset) | measured |
| `G_preset` | SEED-102 cross-family split (`rating_vs_Maia − rating_vs_SF`) | measured; ≈0 Human, +ve Light/Deep |
| `C` | literature (Maia-3 blitz-calibrated by construction; Maia-1 `@maia5`=1581) | **`+40 ± 100`**, single shared constant, hand-tunable |

`C` is one number for all three presets (the shared internal→human-blitz zero-point). `G_preset`
is per-preset (removes each searching preset's inflation vs the search-less anchors). Both live as
named constants in the shipping code; `C` is the knob you refine from experience.

## Why the model is trustworthy enough to print (with a disclaimer)

- **Units are right by construction.** Maia-3's ELO input is trained on lichess *blitz*;
  conditioning on 1500 predicts a lichess-1500-blitz player's move. So the internal scale is
  already a blitz scale, not an arbitrary one — only the strength zero-point (`C`) is uncertain.
- **`C` is small and bounded.** `internal-1500 ≈ human-blitz 1500–1580` (Maia-1 argmax `@maia5`
  plays real blitz 1581, +80 over label). Midpoint `+40`, honest band `±100`.
- **The searching presets don't get a free ride.** Their inflation vs search-less anchors is
  measured as `G_preset` and subtracted, so "1500 Human" and "1500 Deep" map to genuinely
  comparable human strength (to within the `±100` band).

Print an **approximate** blitz ELO with a disclaimer (decided 2026-07-19). Do not print a hard
number. A small human sample could later tighten `C` from ±100 to ±50 (an optional future task,
NOT planned — see SEED-103 in `closed/`).

## Per-preset honest ranges (Option A)

The user picks a **preset** (Human / Light / Deep) and a **target strength**; each preset exposes
only the range it can actually reach:

| preset | internal | expected reachable range (SEED-102 measures the real bounds) |
|---|---|---|
| Human | blend 0 | low end ~600-ish; ceiling ~1900–2000 (no-search + Maia ladder top) |
| Light | blend 0.05 | floor plausibly ~1200+ (search floor); mid range, high variety |
| Deep | blend 0.5 | floor similar to Light; **top toward ~2600** (higher ceiling) |

The ranges deliberately differ. The overlap zone (roughly 1300–1900, pending measurement) is where
users get a genuine style choice at ~equal strength — the product differentiator, honest only
because `G_preset` was subtracted. Selecting outside a preset's range is impossible by construction
(plain per-preset slider bounds). The measured floor/ceiling of each SEED-102 curve **is** the
slider range. Ladder caveat: Maia-3's validated band is 1100–2000 (`maiaEncoding.ts`); curve
segments on `bot_elo` outside that band are extrapolation and should be flagged or trimmed.

## Method

1. Fit each of the three 1D curves `internal_rating = f_preset(bot_elo)` to SEED-102's ~5 points
   (monotone fit; isotonic or low-order polynomial — fit, don't tile).
2. Apply `− G_preset + C` to convert each curve to approximate human blitz ELO.
3. Invert each curve into a `target_blitz_elo → bot_elo` lookup (100-ELO steps).
4. **Validate the inversion.** Predict "(bot_elo X, Deep) plays 1700", then *run that cell* in the
   harness. Two or three confirmation cells per preset. Tests the shipped artifact, not the fitted
   model — cheap, and the step most likely to be skipped.

## Consumers (end-goal architecture)

The three curves are the **single source of truth for all bot strength claims**:

- **Custom bot builder**: preset toggle (Human/Light/Deep) + per-preset target-ELO slider, both
  reading these curves. A labeled surface (approximate-ELO disclaimer applies).
- **Preset bot cards / SEED-098 personas**: presets become named points on the curves
  ("1400, Human" = curve lookup) — nothing new to measure per card. SEED-098 persona perturbations
  fold in as measured ELO offsets on top; each persona lever belongs to exactly one preset (its
  blend regime).

## Relationship to the raw uncalibrated slider surface

The raw `bot_elo` + `blend` slider surface makes no strength promise and does not consume these
curves. These curves are what turn that surface into a *labeled* one. Useful side check while the
raw surface exists: play Human vs Light vs Deep by hand at equal `bot_elo` — perceived difference
(Human clearly search-less; Light/Deep clearly stronger, Deep the ceiling) is the real product
metric, cheaper and more decisive than any agreement percentage.
