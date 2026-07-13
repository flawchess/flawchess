---
title: Lichess bot ground-truth calibration — play real humans to convert the internal anchor scale to human ELO
trigger_condition: After SEED-102's surface lands; MANDATORY before any *labeled* bot ships (SEED-091 preset bot cards, SEED-098 personas). NOT a blocker for Phase 171 — see "What this does and does not gate"
planted_date: 2026-07-13
source: /gsd-explore session 2026-07-13 (bot blend calibration; see .planning/notes/2026-07-13-bot-calibration-findings.md)
---

# SEED-103: Lichess bot ground-truth calibration

Run the FlawChess bot as a lichess BOT account against real humans, and use the resulting
rating to correct the offline harness's internal scale to human ELO.

## What this does and does not gate

**Uncalibrated sliders are an exploration tool; calibration is a promise.** You only owe an
honest number when you *print* one.

- **Does NOT gate Phase 171.** 171 exposes raw `bot_elo` and `blend` sliders and makes no claim
  that the bot plays at the selected rating. That is a legitimate shippable surface. 171's real
  blocker is SEED-100 (blend-0 pacing), which is unrelated to calibration.
- **DOES gate anything labeled**: SEED-091's preset bot cards (200-ELO steps, 600–2600),
  SEED-098's personas with an advertised ELO band, and any copy that says "play a 1500 bot".
  A card labeled 1500 that plays at 980 or 2090 depending on an unrelated slider is a lie, and
  the 2026-07-12 data says that is exactly what would happen today.

## Why this is not optional (for labeled bots)

The offline harness **structurally cannot** produce a human ELO number (note, Finding 2):

- Our anchors are search-less (maia-argmax). The bot at blend > 0 runs a real MCTS. Strength is
  **not transitive across playing styles** — a searching bot beats a tactically-blind 1600 far
  more easily than it beats a *human* 1600, because it exploits a systematic blind spot rather
  than winning on general strength.
- That bias is **correlated with the very axis being calibrated** (blend), so it does not cancel
  and cannot be removed by relabeling the anchors. Better anchor labels fix the *scale*; they do
  nothing about the exploit.

Playing actual humans is the only measurement without that flaw. It is also the only measurement
on **the scale FlawChess users are actually rated on** — they import their lichess games, so
lichess blitz is the native unit of the whole product.

Precedent: this is exactly how the Maia team got their numbers. maia1 sits at blitz 1368 with
**RD 45** (lichess's floor) over 421k games.

## Design

**Place the ground-truth points along the blend axis, not the ELO axis.** The anchor bias is
style-correlated, so the correction plausibly *varies with blend* — that is the thing to measure.

Three bot accounts, all at the same `bot_elo` (e.g. 1500), at **blend 0 / 0.5 / 1**. Then:

- Correction roughly **constant** across the three → one global offset, apply to the entire
  SEED-102 surface, done.
- Correction **grows with blend** → you have directly measured the non-transitivity inflation and
  can correct it as a function of `b`.

Either outcome is a win, and both are cheap relative to their value.

**Free sanity check:** if the harness says blend-0 / bot_elo-1500 plays at 980 and lichess says
~1350, that is the anchor compression showing up in ground truth, quantified.

## Mechanics

- Fresh account (**must never have played a human game**), upgraded via
  `POST /api/bot/account/upgrade`.
- Stream incoming events, accept challenges, stream game state, post moves to
  `POST /api/bot/game/{id}/move/{uci}`. Bots play multiple concurrent games and are rated
  normally against humans. Bots are explicitly permitted and must be flagged BOT.
- **The harness is ~80% of the work already** — `scripts/calibration-harness.mjs` drives
  `selectBotMove` headless in Node, and Phase 169 built the clock/deadline machinery. The
  integration is swapping the anchor opponent for the lichess game stream, not a new system.
- Convergence: new accounts start 1500 / RD 350, drop below RD 100 in ~30–50 games; ~150–300
  games gets to roughly ±50, enough to fit a correction.

## The real risk is traffic, not the API

maia1 has 421k blitz games because people seek it out. A brand-new unknown bot account gets far
less human challenge volume, and rating convergence depends entirely on games actually arriving.
**Unverified:** how well a fresh bot attracts opponents, and what self-matchmaking options bots
have. Worth a short feasibility spike before scheduling around this — if traffic is thin, this
stops being "a few days unattended" and becomes a scheduling problem.

Treat this leg as **validated-when-proven**, not assumed.

## Scheduling note

Tier 1 (this) is **wall-clock-bound** (real-time blitz, waiting for opponents — days). Tier 2
(SEED-102) is **CPU-bound** (an overnight run). They are not a strict dependency chain: the
configs worth putting on lichess (blend 0 / 0.5 / 1) are known without the surface, so this can
start in parallel and let games accumulate while SEED-102 computes.

If a blend-mixture redesign is later adopted (see note, Finding 1), note that the **endpoints are
invariant** — `b = 0` (pure Maia policy sample) and `b = 1` (Stockfish argmax) mean the same
thing before and after. Lichess measurements at the endpoints survive the redesign; only interior
blends would need re-running.

## Caveat

Lichess bot-pool ratings can drift from the human pool. maia1's RD 45 suggests convergence is
sound, but treat the correction as ±50, not exact.
