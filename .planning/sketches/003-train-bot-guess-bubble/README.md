---
sketch: 003
name: train-bot-guess-bubble
question: "Where does the bot avatar + speech bubble carrying the guess prompt sit on a phone so it draws the eye without crowding the board?"
winner: "A"
tags: [train, bots, onboarding, mobile, SEED-166]
---

# Sketch 003: Train bot guess bubble

## Design Question
SEED-166: 52 of 70 never-finishers left the first puzzle without moving. The guess prompt
("Before you move with white, decide: [One critical move] [Several fine moves]") fits under the
board on a phone but nothing draws the eye to it, and a dragged piece snaps back silently. The
bot personas become the voice of Train. Where does the avatar + bubble go, and do the buttons
live inside the bubble or stay in their row?

## How to View
open .planning/sketches/003-train-bot-guess-bubble/index.html

Avatars load from `frontend/src/assets/personas/*.webp` by relative path, so open from the repo.

## Variants
- **A: Chat row under board** — 56px avatar left with name, bubble with tail on the right, the two guess buttons inside the bubble. First session is a 3-bubble stepper (Tank → Hilda → Hilda + buttons).
- **B: Bubble docked to board, buttons outside** — avatar overlaps the bubble's corner as a badge, bubble is a full-width callout, the existing button row stays untouched below it.
- **C: Avatar chip inline (least change)** — 28px avatar in front of today's one-line prompt, no bubble; first-session copy becomes a card above.

## States (cycle with the pills inside each phone)
Regular session · First session (stepper) · Piece dropped before guessing (bubble nudges + highlights, copy becomes "Decide first, then move") · After the guess ("Now play a move for white").
Tap any piece on the board to trigger the drop state.

## What to Look For
- With the first-session copy loaded, is the board still fully visible and are the buttons still on screen at 375px?
- Do the buttons read as the bot's question (A) or as a separate control (B, C)?
- Does the "decide first" nudge feel like feedback or like a scold?
- Avatar size: 56 (A) vs 44 (B) vs 28 (C). Which is the smallest that still has a face?
