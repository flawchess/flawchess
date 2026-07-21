---
title: Three-preset strength curves — measure the bot's internal-scale strength at blend 0, 0.05, 0.5 against the Phase-173 anchor ladder
trigger_condition: READY NOW — SEED-101 (Phase 173) landed the internal anchor scale. This is the recommended next phase. Blocks SEED-104
planted_date: 2026-07-13
source: /gsd-explore 2026-07-13 (bot blend calibration; see .planning/notes/2026-07-13-bot-calibration-findings.md); rescoped 2026-07-15 (two-style); re-rescoped 2026-07-19 (three presets, no human ground truth — SEED-103 closed)
---

# SEED-102: Three-preset strength curves

Measure the bot's strength as a function of `bot_elo` at **three** blend levels, on the
internal anchor scale from SEED-101 (Phase 173, now landed). This is the **shape** of each
preset's strength curve plus the **style-inflation gap** that lets us convert to human blitz
ELO without ever playing a human.

## Status (2026-07-19): unblocked but UNRUN

This seed is NOT done — an earlier session conflated it with SEED-101/Phase 173. Phase 173
delivered the *anchor* self-calibration (the ruler: 10 anchors with measured internal ratings
in `scripts/lib/calibration-internal-scale.mjs`, pinned `maia1500 == 1500`). SEED-102 is the
*next* step: measuring where the **bot** lands on that ruler. The only bot-measurement run in
`reports/data/` is still the clamped 2026-07-12 run, and `calibration-harness.mjs` does not yet
import the internal scale — so it still windows on nominal `bot_elo`, the exact bug that clamped
every 2026-07-12 cell. Fixing that is task 1 below.

## Three presets, not two (decided 2026-07-19)

The product ships **three** style levels, surfaced as presets:

| preset | blend | regime | role |
|---|---|---|---|
| **Human** | 0 | one Maia policy call, **no search**, sample the raw policy | lowest floor, capped ceiling (no-search + Maia ladder top) |
| **Light** | 0.05 | full MCTS, near-max sampling temperature (tau ≈ 0.095) | mid range, max move variety |
| **Deep** | 0.5 | full MCTS, less noise (tau ≈ 0.05) | **higher strength ceiling** (same engine/depth as Light, just more deterministic) |

**Deep is a ceiling, not a different feel** (decided 2026-07-19). Inside `(0,1)` blend is only a
softmax temperature dial (`tau = TAU_MAX·(1−blend)`, `TAU_MAX = 0.1`): Light and Deep run the
*same* MCTS at the *same* depth and differ only in sampling determinism. The one qualitative
cliff on the whole axis is **blend 0 (no search) vs blend >0 (search)** — that is the Human↔Light
divide. Do not market Deep as "deeper"; it is the same engine playing with less variety, which
buys a higher ceiling (the 0.5→1 leg bought +154/+198/+375 ELO on the 2026-07-12 run, so 0.05→0.5
buys a meaningful ceiling bump while staying non-deterministic — see D-01 of the "why not argmax"
note below).

Why not argmax (blend 1)? Deterministic play lets a user replay a memorized winning line
move-for-move; a practice bot needs tau > 0. Deep at 0.5 is the highest-ceiling *non-deterministic*
option.

## Why this run is the whole calibration (no human ground truth)

SEED-103 (play real humans on lichess) is **closed** (2026-07-19) — wall-clock-bound, too slow,
and unnecessary given the decomposition below. This run + one literature-based constant fully
replaces it. The target conversion is:

```
human_blitz(preset) = internal_rating(bot_elo)  −  G_preset  +  C
```

- **`internal_rating(bot_elo)`** — the per-preset strength curve THIS run measures.
- **`G_preset`** — the **style-inflation gap**: how much a searching preset overperforms the
  search-less Maia anchor family relative to the searching Stockfish family. **This run measures
  it for free** (see "Cross-family split" below). ≈0 for Human (blend 0 plays like the Maia
  anchors), positive for Light/Deep (they search and exploit the search-less family — SEED-101
  Finding 4 measured the mechanism: no Maia rung ever beat even the weakest searching SF anchor
  by the margin its rating gap predicted).
- **`C ≈ +40 ± 100`** — a single shared absolute pin, from the literature, NOT measured here:
  Maia-3's ELO input is lichess-blitz-calibrated *by construction* (trained on lichess blitz;
  conditioning on 1500 = "predict the move a lichess-1500-blitz player makes"), and Maia-1's
  argmax `@maia5` (rung 1500) plays real lichess blitz **1581** (+80 over label). So
  `internal-1500 ≈ human-blitz 1500–1580`. Documented in SEED-104; refined later from experience.

So this run produces everything except `C`, and `C` comes off a paper + a lichess profile.

## Grid

- **blend: 0, 0.05, and 0.5.** Three rows.
- **bot_elo: ~5 points per blend**, spanning the range each preset must serve (e.g.
  {700, 1100, 1500, 1900, 2300} — adjust after inspecting the anchor spacing in
  `calibration-internal-scale.mjs`). Each preset gets its own honest slider range (SEED-104), so
  the three rows may want different point placement: Human serves the low end, Light the middle,
  Deep the high end, overlapping in the middle.
- **24–30 games per (cell, anchor).** 10 gave ±110 ELO and a non-monotone ladder; 24 gives ±71
  per anchor, ~±35 once ~4 anchors combine.

## Cross-family split — a first-class output, not a sanity check

Rate **every preset against BOTH anchor families** (Maia argmax rungs AND Stockfish skill levels),
and report each preset's rating vs each family **separately**. The gap
`rating_vs_Maia − rating_vs_SF` **is** `G_preset` — the no-human measurement of that preset's
style inflation. Expect ≈0 for Human, materially positive for Light/Deep. This is the load-bearing
new output of this run (SEED-101 Finding 4 already showed the cross-family residuals exist and are
style-driven, not noise). The 2026-07-12 run used maia anchors only — every TSV row is `maiaNNNN`;
that omission is exactly what this fixes.

## Also log (near-free from games already played)

- **Maia-agreement rate** — fraction of bot moves matching argmax-Maia at its own `bot_elo`.
  Expect high at blend 0, sharply lower at 0.05/0.5. Confirms the three presets actually play
  differently.
- **Stockfish-agreement rate**, **ACPL**, **blunder rate**, draw rate, game length.

## Harness fixes required first

1. **Integrate the internal scale.** Import `scripts/lib/calibration-internal-scale.mjs` into
   `calibration-harness.mjs` and window / pick anchors by **`INTERNAL_RATING`**, not nominal
   `bot_elo`. The 2026-07-12 `ANCHOR_ELO_WINDOW = 400` bracketed on nominal Elo, but the ladder
   is ~2.8x compressed (Phase 173 Finding 2) and cells sit up to 600 nominal ELO from their
   `bot_elo` — so the informative anchors got pruned and every cell swept. This is task 1.
2. **Locate-then-measure two-pass** (as Phase 173's anchor sweep used): ~8 games vs 2 widely
   spaced anchors to place the cell, then 24–30 games vs the 3–4 anchors bracketing that estimate.
   Matters most for the blend 0.05/0.5 cells, which have no prior.
3. **Both anchor families enabled** (see Cross-family split above).
4. **Report per-cell CIs**, not just point estimates.

## Budget

~82 games/hr at `--stockfish-procs 4` (raise if cores allow).

- 3 blends × 5 bot_elo = 15 cells × ~4 anchors × 24 games ≈ **1,440 games ≈ 18h** (overnight;
  ~50% more than the two-preset scope because of the third row).
- Plus the locate pass (~1–2h).

## Caveat

The primary output is on the **internal anchor scale**. Absolute human ELO comes only from
`C` (literature, ±100). Non-transitivity means the searching presets' raw internal rating is
inflated vs search-less anchors — which is precisely why `G_preset` is measured and subtracted
rather than ignored. Any cell leaning heavily on one anchor family (especially `sf0` or `maia700`,
both style-outliers per Phase 173 Finding 4) should be read with that in mind.
