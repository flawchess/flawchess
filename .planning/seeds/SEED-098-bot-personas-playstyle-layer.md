---
title: Bot personas & playstyle layer — 2D (aggression × complexity) style params + named persona roster
trigger_condition: v2.3 Bot Play shipped (Phases 169-171 done); surfaces at next /gsd-new-milestone scoping
planted_date: 2026-07-12
source: /gsd-explore session 2026-07-12 (playstyles beyond ELO and blend; Chessiverse prior-art review)
---

# SEED-098: Bot personas & playstyle layer

Add distinct playstyles to the v2.3 bot on top of the two existing strength knobs (ELO,
human↔stockfish blend), surfaced as a roster of **named bot personas** on the Bots page.

## Locked decisions (explore session 2026-07-12)

1. **Goal: perceived personality, not measurably distinct play.** The user should *feel*
   they're playing a different opponent. This picks the cheap levers (opening books, prior
   nudges, small score shaping) and deliberately keeps strength deltas small so the Phase 168
   (ELO × blend) calibration map stays roughly valid per ELO, with styles a thin layer on top.
2. **Presentation: named bot personas** (name, avatar, one-line bio, fixed ELO band + style
   preset), not a bare style dropdown. Personality perception is mostly manufactured by the
   frame (cf. chess.com's "Nelson loves his queen"); the setup screen becomes "pick an
   opponent". Personas are presets over the underlying (ELO, blend, aggression, complexity)
   knobs — a custom mode exposing raw settings can stay for power users.

## Design: two continuous style axes, personas as points

Adopt Chessiverse's 2D framework (https://chessiverse.com/articles/bots-3-playstyles):
**Defensive↔Aggressive** × **Simplifying↔Complicating**. Internally, two scalar params in
`BotSettings`:

- `aggression ∈ [-1, 1]` modulates:
  - **Prior reweighting**: multiply Maia policy probabilities by move-feature weights
    (checks, captures, forward/pawn-storm moves boosted at +; retreats/consolidation at −).
    Applies in both the full-human path (`samplePolicy`) and as tree priors in `mctsSearch`.
  - **Draw contempt** in `practicalScore`: an aggressive bot scores draws closer to a loss;
    a defensive one tolerates them.
- `complexity ∈ [-1, 1]` modulates:
  - **Trade-move prior multipliers** (simplifiers boost exchanges, complicators penalize them).
  - **Variance preference**: the MCTS tree already exposes a sharpness signal — the spread of
    child `practicalScore`s under a node. Complicators get a variance bonus, simplifiers a
    penalty, folded into the score used for sampling/argmax.

The style-dependent score handicap is Chessiverse's "Move Curator" pattern: "a queen trade
for a Savage needs to be a *very strong* move to be selected" = a style bonus/malus added to
`practicalScore` before the existing softmax/argmax in `selectBotMove`. No new search
machinery; `botSampling.ts` helpers stay pure.

## Persona roster (v1 — names are placeholders)

| Persona | Quadrant (Chessiverse analog) | Primary mechanism |
|---|---|---|
| **The Attacker** | aggressive ± complicating (Hunter/Savage) | Gambit/attacking book, prior boost on checks/captures/pawn storms, draw-averse contempt |
| **The Trickster** | defensive + complicating (Observer) | Trap/troll lines (reuse `frontend/src/lib/trollOpenings.ts`), high-variance preference, swindle mode when losing |
| **The Grinder** | (no Chessiverse analog — analytics-native original) | Trade-happy priors, steers into endgames, draw-tolerant, never resigns early. Playing them trains exactly what FlawChess's endgame stats measure |
| **The Solid Wall** | defensive + simplifying (Guardian) | System-opening book (London/Slav-ish), low-variance preference, happy to simplify/take draws |
| *(default bot)* | center (Mediator) | Current v2.3 behavior, aggression = complexity = 0 |

Extra per-persona fields beyond the two axes: opening book, ELO band, blend preset,
resign/draw-offer policy (Grinder: no early resign), avatar + bio copy.

## Perceptibility-per-effort ranking (build in this order)

1. **Per-persona opening books** — cheapest and most perceptible; users judge personality in
   the first 10 moves. Trickster's book comes nearly free from `trollOpenings.ts`.
2. **Draw contempt / resign policy** — small, well-understood knobs.
3. **Prior reweighting by move features** — needs a cheap move classifier (chess.js flags:
   capture, check, pawn advance direction, piece retreat).
4. **Variance bonus from MCTS child-score spread** — data already in the tree.
5. **NOT in scope**: positional-theme steering (e.g. "loves the bishop pair") — WASM
   Stockfish returns one cp number, not eval components.

## Calibration strategy

Chessiverse reports style conversion costs "several hundred points" of raw strength, which
they compensate so a 2000 Savage ≈ 2000 Mediator in strength. With our light-nudge scope the
deltas should be much smaller, but they are not zero:

- Any lever touching priors or `practicalScore` shifts strength; each persona therefore needs
  a **per-persona ELO offset** measured once by the Phase 168 headless harness at a few
  anchors (not a full per-style grid — the perceived-personality scope keeps this bounded).
- Labeled persona ELO = calibrated ELO, not raw setting.

## Caveats

- **Both style levers are currently regime-split — neither works across the whole slider**
  (added 2026-07-13, see `.planning/notes/2026-07-13-bot-calibration-findings.md` Finding 1).
  `selectBotMove` is a three-way regime dispatch, not a mix: at **blend = 0** there is no search
  at all, so no `practicalScore` exists and the **score-shaping lever is dead**; at **blend > 0**
  the move is chosen by softmax over `practicalScore` and the Maia prior only steers tree
  expansion, so the **prior-reweighting lever is nearly dead**. An Attacker built today would
  change character *discontinuously* as the user moves the playstyle slider, with the two
  mechanisms handing off at the cliff. Whether this needs a blend-formula redesign (log-linear
  Maia × Stockfish mixture, so both terms are live at every blend) is **measurable, not yet
  established** — SEED-102's Maia-agreement-rate metric settles it. Check that result before
  building on the current substrate.
- **Maia-3 sac-blindness** (see memory `project_engine_self_execution_sac_blindness`): an
  Attacker built on prior reweighting will offer sacrifices it can't follow up (no history
  planes → post-sac follow-up priors collapse). At club ELO this is acceptable flavor
  (unsound sacs are a feature), but don't market the Attacker as "plays sound attacks".
- **D-02/WR-04 invariant in `selectBotMove`**: `policyTemperature` is structurally excluded
  from the bot's search budget. Style params must be NEW fields with their own semantics, not
  a repurposing of the analysis-board temperature transform.
- **BOT-03 invariant**: style params, like ELO, are bot-only inputs — never derived from the
  player's rating or play (the bot must stay non-adaptive and measurable).

## Prior art

- Chessiverse playstyles: 2D axes, 5 categories (Guardian/Observer/Mediator/Hunter/Savage),
  "Move Curator" score-handicap selection, explicit strength compensation —
  https://chessiverse.com/articles/bots-3-playstyles
- chess.com personality bots: persona framing (avatar/bio/gimmick) carries most of the
  perceived personality.
