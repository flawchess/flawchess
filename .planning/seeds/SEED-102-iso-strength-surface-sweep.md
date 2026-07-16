---
title: Two-style strength curves — measure strength(bot_elo) at blend 0 and blend 0.05 against self-calibrated anchors
trigger_condition: After SEED-101 (anchor ladder self-calibration) lands; blocks SEED-104
planted_date: 2026-07-13
source: /gsd-explore session 2026-07-13 (bot blend calibration; see .planning/notes/2026-07-13-bot-calibration-findings.md); rescoped 2026-07-15 /gsd-explore (two-style simplification)
---

# SEED-102: Two-style strength curves

Measure the bot's strength as a function of `bot_elo` at exactly **two blend levels**, on the
internal anchor scale from SEED-101. This is the **shape**, not the units — SEED-103 supplies
the correction to human ELO.

## Rescoped 2026-07-15: the 2D surface sweep is dead

The original plan mapped a 5-blend × 3–4-`bot_elo` surface (~1,900 games, ~24h) to support a
continuous playstyle slider. Decision (2026-07-15 explore session): **the product ships only
two style levels**, so the blend interior is discarded and there is nothing to map there.

- **blend 0** — "human-like": one Maia policy call, no search, sample the raw policy.
- **blend 0.05** — "engine-like": full MCTS, near-max sampling temperature. The no-search vs
  full-search regime cliff (Finding 1) is the one style difference that is structurally real;
  0.05 is just over that cliff with maximum move variety. See "Why 0.05" below.

This collapses the blend-interior question ("is (0,1] a usable playstyle axis?") — moot, we
don't ship the interior. It also collapses SEED-104 from a 2D surface fit + inversion into two
small 1D lookup curves.

## Grid

- **blend: 0 and 0.05.** Nothing else.
- **bot_elo: ~5 points per blend level**, spanning the range each level must serve
  (e.g. {700, 1100, 1500, 1900, 2300} — adjust after SEED-101 reveals the ladder's real
  spacing). Each level gets its own honest slider range in the product (Option A, see
  SEED-104), so the two levels may want different point placement: blend 0 serves the low end,
  blend 0.05 the high end, overlapping in the middle.
- **24–30 games per (cell, anchor).** 10 gave ±110 ELO and produced a visibly non-monotone
  ladder. 24 gives ±71 per anchor, ~±35 once ~4 anchors are combined.

## Why 0.05 (decided 2026-07-15 explore session)

The exact value looks arbitrary but is not. Inside (0, 1), blend is **only a temperature
dial**: `selectBotMove.ts` sets `tau = TAU_MAX * (1 - blend)` with `TAU_MAX = 0.1`, a softmax
over `practicalScore` (expected-score units). Every blend in (0, ~0.1] is effectively the same
bot (tau 0.09–0.1); the only real choice is between three temperaments:

| blend | tau | temperament |
|---|---|---|
| ≈0.05 | 0.095 | search + near-max sampling noise |
| 0.5 | 0.05 | search + mid noise |
| 1.0 | argmax | search, deterministic |

Max-noise (≈0.05) wins because:

1. **Argmax is disqualified regardless of strength** — deterministic play lets a user replay a
   memorized winning line move-for-move. A practice bot needs tau > 0.
2. **The floor is the engine level's scarce resource, not the ceiling.** Its risk is being
   unable to play weak, which shrinks the overlap zone where users get a genuine style choice
   at equal strength. Temperature affects strength modestly (the 0.5 → 1 leg bought +154–375
   ELO), so max tau buys the lowest floor available in the search regime. The ceiling is likely
   fine: the top 2026-07-12 cells *swept* their anchors (clamped = lower bounds), and an honest
   post-correction top around 2300–2400 covers essentially the whole user base.
3. **Max tau is not a blunderfest**, because the units are expected score: at tau 0.095 a move
   0.05 worse keeps ~60% relative weight (variety among near-equal moves), but a move 0.3 worse
   gets ~4% (real blunders stay rare). The noise lives among near-equal moves only.

**Hedge in the locate pass:** probe blend 0.05 vs 0.5 at `bot_elo` 1900/2300 (~8 games each,
~30 min) before committing the full run. Ceilings close → 0.05 wins on floor and variety;
0.05's ceiling materially lower → take 0.5 and accept a higher floor.

## The blend 0.05 curve is unmeasured territory

No prior exists for blend 0.05 — at bot_elo 1500 it could sit anywhere between 980 (blend 0)
and 1938 (blend 0.5, both uncorrected). Where it lands also retroactively answers the old
cliff-vs-temperature question for free, but that is now a curiosity, not a decision input.

Expect the **search floor**: full MCTS conditioned on a low Maia prior may be unable to play
weak (a bot_elo-600 prior with real search plausibly still plays 1200+). The measured floor and
ceiling of each curve become the per-style slider bounds in SEED-104 — that is a primary output
of this run, not a nuisance.

## Style metrics — reduced to a sanity check

The original decisive question (does Maia-agreement decline smoothly across the blend axis?) is
moot. What remains: **verify the two shipped levels actually play differently.** Log per cell,
near-free from games already being played:

- **Maia-agreement rate** — fraction of bot moves matching argmax-Maia at its own `bot_elo`.
  Expect high at blend 0, sharply lower at blend 0.05. If they are close, the two "styles" are
  cosmetic and the product story needs rethinking.
- **Stockfish-agreement rate**, **ACPL**, **blunder rate**, draw rate, game length.

## Harness fixes required first

1. **Center the anchor window on the cell's expected strength, not on `bot_elo`.** The current
   `ANCHOR_ELO_WINDOW = 400` brackets around `bot_elo`, but cells sit up to 600 ELO away from
   it — so the informative anchors get pruned (`out_of_window`) and every played anchor sweeps.
   This is why all 9 cells of the 2026-07-12 run clamped. See note, Finding 3.
2. **Locate-then-measure two-pass** instead of a fixed window:
   - *Locate*: ~8 games vs 2 widely-spaced anchors to place the cell. Matters most for the
     blend 0.05 cells, where there is no prior at all.
   - *Measure*: 24–30 games vs the 3–4 anchors bracketing that estimate. Target scores in the
     0.2–0.8 band; anything outside carries almost no information.
3. **Both anchor families enabled.** The 2026-07-12 run used maia anchors only — every row in
   the TSV is `maiaNNNN`, despite `sf0/sf3/sf5` being in the defaults. maia anchors are
   search-less and share the blend-0 bot's blind spot; SF anchors search and fail differently.
   Disagreement between the families is itself a measurement of the style-correlated bias, and
   matters most for the blend-0.05 curve (searching bot vs search-less anchors).
4. **Report per-cell CIs**, not just point estimates.

## Budget

~82 games/hr at `--stockfish-procs 4` (raise if cores allow).

- 2 blends × 5 bot_elo = 10 cells × ~4 anchors × 24 games ≈ **960 games ≈ 12h** (overnight)
- Plus SEED-101's round-robin (~2h) and the locate pass.

Roughly half the original surface-sweep budget.

## Caveat

The output is on the **internal anchor scale**, not human ELO, and must not be labeled as such.
Non-transitivity means the searching blend-0.05 bot's rating against search-less anchors is
inflated in a way no amount of anchor relabeling fixes. SEED-103 is the only source of an
honest absolute number, and its per-style offsets will differ (the inflation applies to one
curve and not the other).
