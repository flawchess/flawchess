---
title: Bot personas & playstyle layer — 24-persona roster (4 styles × 6 ELO rungs), persona-pins-everything
trigger_condition: Phases 180/181 done (strength curves + lookup shipped); surfaces at next /gsd-new-milestone scoping. Milestone-sized.
planted_date: 2026-07-12
source: /gsd-explore 2026-07-12 (original 2D-axes sketch); redesigned /gsd-explore 2026-07-21 (roster locked, post-Phase-181 substrate)
---

# SEED-098: Bot personas & playstyle layer

Add distinct playstyles to the bot, surfaced as a roster of **named bot personas** on the
Bots page. Redesigned 2026-07-21 on top of the shipped three-preset substrate (Phases
171/180/181): the original 2D-slider framing is replaced by a concrete persona grid.

## Locked decisions (explore session 2026-07-21)

1. **Persona pins everything.** A persona IS a complete opponent: fixed preset (Human/Light/
   Deep), fixed ELO, fixed style params, opening book, resign/draw-offer policy, avatar, bio.
   No persona × strength picker; the persona frame carries the personality (cf. chess.com
   bots). Custom mode keeps the raw (ELO, preset) knobs for power users.
2. **Full grid: 4 styles × 6 rungs = 24 distinct named characters.**
   - Styles: **The Attacker** (aggressive/complicating), **The Trickster** (defensive/
     complicating, traps/swindles), **The Grinder** (analytics-native: trade-happy, steers to
     endgames, never resigns early — playing it trains exactly what FlawChess measures),
     **The Solid Wall** (defensive/simplifying, system book).
   - Rungs: 800, 1000, 1200, 1400, 1600, 1800 approx blitz (200-ELO steps).
   - Every slot is its own character (name, avatar, bio) — not "Attacker at Hard".
3. **Avatars: AI-generated portrait set** — one consistent style prompt, 24 characters,
   manually curated, committed as static assets.
4. **Goal unchanged: perceived personality, not measurably distinct play.** Cheap levers,
   small strength deltas, persona frame does most of the work.

## Mechanism per rung (dictated by measured preset ranges)

Phase 180/181 measured honest approx-blitz ranges: Human ~900–1400, Light ~1500–1600, Deep
~1600–1800 (`reports/data/bot-strength-lookup.json`). So the rung dictates the preset, and
the preset dictates which style lever is live:

| rungs | preset | live style lever |
|---|---|---|
| 800–1400 | Human (blend 0, no search) | **Prior reweighting**: multiply Maia policy probs by move-feature weights (checks/captures/pawn storms boosted for Attacker; exchanges boosted for Grinder/Wall, penalized for complicators). Needs a cheap chess.js move classifier. |
| 1600 | Light or Deep | **Score shaping** ("Move Curator"): style bonus/malus added to `practicalScore` before the existing softmax in `selectBotMove` — draw contempt, trade bonus/malus, variance preference from MCTS child-score spread. |
| 1800 | Deep | Same score-shaping lever. |

Regime-agnostic levers carry each style's identity across ALL rungs: **opening book**
(Trickster reuses `frontend/src/lib/trollOpenings.ts` nearly free), **draw contempt**,
**resign/draw-offer policy** (Grinder never resigns early).

Both levers get built (each persona is single-regime, but each style spans both regimes).
`botSampling.ts` helpers stay pure; no new search machinery.

**Tier stories**: each style needs a per-level identity, e.g. Trickster = cheap trap lines at
800–1200, swindle mode + high-variance preference at 1600+; Grinder's endgame-steering only
really lands at higher rungs where games reach endgames.

## Perceptibility-per-effort ranking (build in this order)

1. **Per-persona opening books** — cheapest, most perceptible (users judge personality in the
   first 10 moves), and regime-independent.
2. **Draw contempt / resign policy** — small, well-understood knobs.
3. **Prior reweighting by move features** (Human rungs) — chess.js flags: capture, check,
   pawn advance, retreat.
4. **Score shaping + variance bonus** (Light/Deep rungs) — child-score spread already in the
   tree.
5. **NOT in scope**: positional-theme steering ("loves the bishop pair") — WASM Stockfish
   returns one cp number, not eval components.

## Calibration strategy

Style levers shift strength, so **labeled persona ELO = calibrated ELO**, not the raw
setting. Each persona is one fixed (ELO, preset, style) cell on the Phase-173 internal anchor
scale: ~24 cells × ~4 anchors × ~24 games ≈ 2 overnight runs of the Phase-180 harness
(`calibration-harness.mjs` + `scripts/gen_bot_strength_curves.py` pipeline). Per-persona
offset absorbs the style-induced strength delta (Chessiverse-style compensation, but our
light-nudge scope keeps deltas small).

## Strength-honesty constraints (from Phase 180/181 measurements)

- **The 800 rung is below the measured floor** (~900 approx blitz; the two weakest measured
  Human cells are already `beyond_ladder`-flagged extrapolations). Options: measure new
  lower-`bot_elo` cells (same extrapolation caveat) or let the bottom rung be ~900 in
  practice. Bands are ±200 down there; honest labeling matters least at the bottom.
- **1800 is exactly Deep's measured ceiling** (curve plateaus; PAVA pools bot_elo 2300/2600).
  No headroom above without SEED-114 (ladder extension above ~1900 internal).
- The Light/Deep overlap window is narrow (~1500–1800), which is fine under
  persona-pins-everything: users never compare presets at fixed strength.

## Caveats (still live)

- **Maia-3 sac-blindness** (memory `project_engine_self_execution_sac_blindness`): an
  Attacker built on prior reweighting offers sacrifices it can't follow up (no history planes
  → post-sac priors collapse). At club ELO this is acceptable flavor (unsound sacs are
  authentic); don't market the Attacker as "plays sound attacks".
- **D-02/WR-04 invariant in `selectBotMove`**: `policyTemperature` is structurally excluded
  from the bot's search budget. Style params must be NEW fields with their own semantics, not
  a repurposing of the analysis-board temperature transform.
- **BOT-03 invariant**: style params, like ELO, are bot-only inputs — never derived from the
  player's rating or play (the bot stays non-adaptive and measurable).
- ~~Regime-split slider cliff~~ **OBSOLETE** (2026-07-21): the original caveat about styles
  changing character discontinuously as the user drags the blend slider assumed a continuous
  blend axis. Phase 171 + quick 260717-lr9 replaced it with three discrete presets; there is
  no user-facing continuous axis left to fracture across. The regime split survives only as
  the per-rung lever table above — an implementation detail, not a UX cliff.

## Prior art

- Chessiverse playstyles: 2D axes, "Move Curator" score-handicap selection, explicit strength
  compensation — https://chessiverse.com/articles/bots-3-playstyles
- chess.com personality bots: persona framing (avatar/bio/gimmick) carries most of the
  perceived personality; distinct characters per rating rung.
