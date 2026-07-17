---
title: Lichess bot ground-truth calibration — play real humans to convert the internal anchor scale to human ELO
trigger_condition: After SEED-102's curves land; MANDATORY before any *labeled* bot ships (SEED-091 preset bot cards, SEED-098 personas, calibrated custom-bot sliders). NOT a blocker for Phase 171 — see "What this does and does not gate"
planted_date: 2026-07-13
source: /gsd-explore session 2026-07-13 (bot blend calibration; see .planning/notes/2026-07-13-bot-calibration-findings.md); rescoped 2026-07-15 /gsd-explore (two-style simplification — 2 accounts instead of 3)
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
- **DOES gate anything labeled**: SEED-091's preset bot cards, SEED-098's personas with an
  advertised ELO band, any copy that says "play a 1500 bot", **and the calibrated custom-bot
  builder** (decided 2026-07-15): once the custom bot's strength slider means *target ELO*
  rather than raw `bot_elo`, it is a labeled surface too and sits behind this same gate.

## Why this is not optional (for labeled bots)

The offline harness **structurally cannot** produce a human ELO number (note, Finding 2):

- Our anchors are search-less (maia-argmax). The engine-like bot (blend 0.05) runs a real MCTS.
  Strength is **not transitive across playing styles** — a searching bot beats a
  tactically-blind 1600 far more easily than it beats a *human* 1600, because it exploits a
  systematic blind spot rather than winning on general strength.
- That bias is **correlated with the style level being calibrated**, so it does not cancel and
  cannot be removed by relabeling the anchors. Better anchor labels fix the *scale*; they do
  nothing about the exploit.

Playing actual humans is the only measurement without that flaw. It is also the only measurement
on **the scale FlawChess users are actually rated on** — they import their lichess games, so
lichess blitz is the native unit of the whole product.

Precedent: this is exactly how the Maia team got their numbers. maia1 sits at blitz 1368 with
**RD 45** (lichess's floor) over 421k games.

## Design (rescoped 2026-07-15)

With only two shipped style levels, the "does the correction vary with blend?" question
collapses to **one offset per style level**.

**Two bot accounts**, both at the same `bot_elo` (e.g. 1500):

- **blend 0** (human-like) — also directly quantifies the Maia ladder compression in ground
  truth (harness says ~980 uncorrected; if lichess says ~1350, that's the compression measured).
- **blend 0.05** (engine-like) — directly measures the non-transitivity inflation for the
  searching regime.

Each account's lichess rating minus its SEED-102 internal rating is that style's correction;
apply it to the whole 1D curve. If budget allows a third account later, a second point on one
of the curves (different `bot_elo`) validates that the correction is a constant offset rather
than a slope change — but two accounts is the minimum viable design.

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
(SEED-102) is **CPU-bound** (an overnight run). They are not a strict dependency chain: the two
configs worth putting on lichess (blend 0 and 0.05 at bot_elo 1500) are known without the
curves, so this can start in parallel and let games accumulate while SEED-102 computes.

Note that `b = 0` (pure Maia policy sample) is invariant under any future engine change to the
blend formula; the blend-0.05 account would need re-running if the search/sampling regime is
ever redesigned.

## Caveat

Lichess bot-pool ratings can drift from the human pool. maia1's RD 45 suggests convergence is
sound, but treat the correction as ±50, not exact.
