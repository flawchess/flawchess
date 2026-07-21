# Bot strength lookup curves — what the Phase-180 sweep actually ships

**Date:** 2026-07-21
**Source:** Phase 180's landed sweep output `reports/data/bot-curves-internal-scale.json`
(15 measured cells across Human/Light/Deep), fitted by `scripts/gen_bot_strength_curves.py`
into `reports/data/bot-strength-lookup.json` / `frontend/src/generated/botStrengthCurves.ts`.
**Why this note exists:** SEED-104 asked for a shipping `target_blitz_elo -> bot_elo` lookup
per preset. The gen script and its two committed artifacts are the machine-readable answer;
this note is the human-readable one — what the measured curves actually look like, why the
`beyond_ladder` flag on two Human cells does NOT mean what it sounds like, and (once the
operator confirmation run below is complete) whether the shipped inversion held up when tested
off-grid.

**Caveat, carried verbatim (D-13/SEED-104):** the underlying scale is an INTERNAL calibration
scale, not human ELO. Every `approx_blitz_elo` value below is a rough conversion via the shared
offset model, carrying a per-preset uncertainty band — read it as a guide, not a precise rating.

## 1. The shipped offset model, as built

`scripts/gen_bot_strength_curves.py` fits `internal_rating = f_preset(bot_elo)` per preset via
hand-rolled Pool-Adjacent-Violators isotonic regression over the 5 measured
`rating_vs_maia` points, then converts to an approximate human blitz ELO via:

```
approx_blitz = internal_rating - G_preset_combined + C
```

`C = BLITZ_OFFSET_C = 40` (a literature constant, not refit from data; retuning it is a
one-line change + regenerate, no refit). `G_preset_combined` is the **pooled** per-preset
style-gap correction (never a per-cell `g_preset`, never `rating_vs_sf`) — pooling over 5 cells
smooths the noisy per-cell swing, which is as wide as 61–313 for Light.

| preset | blend | `g_preset_combined` | blanket ± band |
|---|---|---|---|
| Human | 0.0 | 40.95 | 225 |
| Light | 0.05 | 186.24 | 200 |
| Deep | 0.5 | 247.18 | 250 |

The blanket band per preset (D-03) is `C`'s own ±100 uncertainty plus the preset's mean
measured-cell CI half-width, rounded to the nearest 25 — a derived number, not a magic one.
Inversion is **lowest-`bot_elo`-wins** on any flat/plateau segment (D-07): a target ELO landing
inside a plateau always resolves to the plateau's lowest `bot_elo`, so the lookup never claims
a higher setting buys strength it doesn't.

Shipped approx-blitz ranges (`reports/data/bot-strength-lookup.json`, floor rounded up /
ceiling rounded down to the nearest 100, D-10):

| preset | floor | ceiling |
|---|---|---|
| Human | 900 | 1400 |
| Light | 1500 | 1600 |
| Deep | 1600 | 1800 |

## 2. Measured-curve realities

**Light is non-monotone.** Raw `rating_vs_maia` at bot_elo 1100 is 1638.9, but at bot_elo 1300
it drops to 1512.8 — a real, measured dip, not noise the fit should smooth away. PAVA pools
these two points into one flat plateau block valued 1575.8, and the shipped lookup's Light
floor (bot_elo 1100) is attributed to that plateau's *lowest* `bot_elo`, per D-07. This is not
a bug to "fix" with a smoothed spline; a spline would invent strength the measured data doesn't
show.

**Deep dips at bot_elo 2600 and plateaus.** Raw `rating_vs_maia` climbs from 1783.5 (bot_elo
1100) to 2118.3 (bot_elo 2300), then *falls* to 2064.3 at bot_elo 2600. PAVA pools 2300 and
2600 into Deep's ceiling plateau, valued ≈2091.3 internal — meaning Deep's approx-blitz
**ceiling lands at 1800**, well below the seed's originally hoped ~2600. This is exactly the
"Deep is a ceiling, not a different feel" finding from Phase 180: Light and Deep differ only in
sampling temperature, not in how far the strength curve reaches. Extending the ladder above
~1900 internal to chase a higher Deep ceiling is out of this phase's scope and is already
captured as `SEED-114-stronger-bots-above-1900-ladder-extension`.

**Human tops out around 1474 internal at bot_elo 2300** — the highest-rated Human cell
measured. Human's curve stays fully monotone across all 5 points, so PAVA is a no-op there;
every measured point keeps its own block.

## 3. The `beyond_ladder` mechanism, resolved (D-08)

Two Human cells (bot_elo 700 and bot_elo 1100) carry `beyond_ladder: true` in the frozen input.
It is tempting to read this as "these `bot_elo` values fall outside Maia-3's validated
policy-conditioning range" — Maia-3's argmax band is documented as 1100–2000 in
`frontend/src/lib/maiaEncoding.ts`, and bot_elo 1100 sitting right at that band's edge makes the
conflation easy. **That reading is wrong**, and a future reader must not "fix" the flag by
excluding these cells.

The actual mechanism: `beyond_ladder` is set by `bracketBeyondLadder()`
(`scripts/lib/calibration-bot-cell-schedule.mjs`) when a cell's **measured internal rating**
(not its `bot_elo` label) falls below the internal-scale anchor ladder's own floor, `sf0`, the
weakest fixed anchor, measured at 1069.33 (`.planning/notes/2026-07-15-anchor-ladder-...`
findings). Human bot_elo=1100's measured `rating_vs_maia` is 1006.2, below `sf0`; bot_elo=700's
is 882.2, further below still. Both cells are simply weaker than any anchor in the ladder used
to measure them — a boundary condition of the measurement methodology, not evidence the
`bot_elo` input itself was invalid.

D-08's decision stands: **both cells stay IN the fit and the lookup, flagged as extrapolated**
(`extrapolated_bot_elos: [700, 1100]` in the shipped JSON's Human component). Dropping them
would silently raise Human's floor from ~900 to ~1100+ approx-blitz, contradicting the explicit
product goal — the bot builder wants genuinely weak bots, and Human's whole point is reaching
down to them.

## 4. The narrower-than-hoped style-choice overlap zone (D-09)

Light and Deep's measured floors (bot_elo 1100) land at ~1500 and ~1600 approx-blitz
respectively, higher than the phase originally hoped for a low-end overlap. Combined with
Deep's ~1800 ceiling (§2), the genuine "same strength, different style" choice between Light
and Deep only exists in a narrow window, roughly **1500–1800 approx-blitz** — rather than the
wider band the seed anticipated. This phase does not pursue additional low-end measurement to
widen it (D-09); if the narrow window later hurts the product (e.g. a user picking between
Light/Deep finds almost no strength-matched pair to compare), it is a candidate for a future
seed, not a re-fit of this phase's data.

## 5. Confirmation run (HUMAN-UAT — to be filled)

Per D-11's split delivery (mirrors Phase 180's D-01 precedent), this phase's interactive work
ends here: the gen pipeline, the shipped lookup artifact, and the confirmation-cell prediction
file (`reports/data/bot-strength-confirmation-predictions.json`) all land in this commit. The
actual overnight confirmation run (playing real games at each predicted off-grid `bot_elo` and
checking whether the measured result lands where predicted) is an **operator-run step**, done
by hand outside this session.

**Predicted cells** (from `bot-strength-confirmation-predictions.json`; each row's `harness_cmd`
+ `fit_cmd` is the exact runbook to reproduce it):

| preset | target blitz ELO | predicted bot_elo | predicted internal | 95% CI |
|---|---|---|---|---|
| Human | 1000 | 1083 | 1001.0 | [856.0, 1094.7] |
| Human | 1200 | 1588 | 1200.7 | [1096.6, 1300.7] |
| Human | 1300 | 1741 | 1300.9 | [1196.8, 1414.6] |
| Light | 1533 | 1781 | 1679.3 | [1591.0, 1780.5] |
| Light | 1567 | 1820 | 1713.4 | [1622.4, 1825.3] |
| Deep | 1667 | 1298 | 1874.1 | [1755.7, 2059.6] |
| Deep | 1733 | 1442 | 1940.0 | [1813.7, 2138.5] |

Every predicted `bot_elo` above is strictly off the measured 5-point grid per preset (D-11/
D-12) — this is a genuine test of the shipped inversion, not a re-measurement of an already-
known point.

**Pass criterion (D-13):** the confirmation cell's measured `rating_vs_maia` (same fit basis as
the shipped lookup) must fall within the recorded `[ci95_lo, ci95_hi]` band. The band itself is
computed by the locked interpolated-CI rule: inverse-variance-pooled and spread-widened when
the predicted `bot_elo` lands inside a merged PAVA plateau, linearly interpolated between
neighboring blocks' own CIs otherwise (see `scripts/gen_bot_strength_confirmation_cells.py`'s
module docstring for the full formula).

**On failure (D-14):** no hand-tuning, no band-widening to paper over a miss. Fold the
confirmation games into the fit dataset (append the new measured cells to
`bot-curves-internal-scale.json`'s `cells` array) and re-run
`uv run python scripts/gen_bot_strength_curves.py` to regenerate the lookup + TS artifact from
scratch. Document the resulting shift (which preset's range moved, and by how much) in an
update to this note.

**Result:** _not yet run — this section is the placeholder the operator confirmation run fills
in._
