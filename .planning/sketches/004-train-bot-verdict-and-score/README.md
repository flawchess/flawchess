---
sketch: 004
name: train-bot-verdict-and-score
question: "How does a bot deliver the per-puzzle verdict with its return date, and sum up the session ahead of the reminder ask?"
winner: "Synthesis"
tags: [train, bots, reveal, score-screen, spaced-repetition, mobile, SEED-166]
---

# Sketch 004: Train bot verdict and score screen

## Design Question
SEED-166 scope B: every verdict ends with when the position returns (Anki-style, from
`SolveResponse.due_date`), and the score screen explains spaced repetition before asking for
"Remind me". Stern bots (Tank, Diesel, Gus) front 0–1 point verdicts, friendly bots (Pip, Bruno,
Shelly) front 2–3; the voice is always encouraging and forward-looking. Where does the bot go on
the reveal and on the score screen?

## How to View
open .planning/sketches/004-train-bot-verdict-and-score/index.html

Avatars load from `frontend/src/assets/personas/*.webp` by relative path, so open from the repo.

## Variants
- **Synthesis (selected)** — A's bot row moved directly under the board; the bubble carries the verdict with the point pills inline ("Good call on the position +1, wrong move +0. We'll try this one again in the next session."), then the action buttons (Analyze, Next; Solution appears once the board departs the reveal position) on their own row inside the bubble. No sound toggle (moves to a settings page later). First session adds a Hilda bubble between the verdict and the cards explaining the cards (tap to see the line, step through) and the buttons. Score screen = A's.
- **A: Bot row above the verdict cards** — the sketch-003 chat row, spoken by the outcome bot, sits between the Solution/Analyze/Next row and the cards. The points pop over the board carries the bot's face. Score screen: the bubble replaces the "Session complete" heading, badge and points move below it.
- **B: Bot folded into the guess card** — the outcome bot is a 40px avatar in the Guess card header and its line is the header text; no extra row. Score screen: badge stays on top, bot bubble (tail up) sits between points and buttons.

## States (pills inside each phone)
Reveal: 0 / 1 / 2 / 3 points and "warm-up" (herring or filler, no return promise). Score screen: first session (full spaced-repetition explanation + list of what returns) vs later session (one line).

## What to Look For
- Is the bot line the first thing read under the board, and does the verdict still read as the user's own result rather than a comment on them?
- Does the return date land ("next session" / "in 4 days") without a second sentence?
- Score screen: does the explanation earn the "Remind me" ask, or is it too long for the moment?
- A vs B: voice (a row) vs icon (a header).
