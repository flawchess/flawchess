---
sketch: 014
name: train-today-two-modes
question: "How does the Train Today page carry two training modes (personalized puzzles, blunder check) with a streak that needs both?"
winner: "B"
tags: [train, landing, blunder-check, streak, mobile, SEED-261108-dk0]
---

# Sketch 014: Train Today with two modes

## Design Question
Phase 251 puts blunder check on the Today page next to personalized puzzles, and the streak needs both
sessions. Which layout keeps the Start buttons above the phone fold, makes the both-required rule visible,
and still has room for the one-line pitch, "How it works" and the per-mode session size?

Decisions behind it: `.planning/seeds/SEED-261108-dk0-blunder-check-training.md`, "Phase 251 decisions".

## How to View
open .planning/sketches/014-train-today-two-modes/index.html (reuses 005's flame.js/flame.css)

Top bar: set each mode to Pending / In progress / Done / Off, toggle the launch notice and the
"No rated games" level picker, switch Phone / Desktop. Deep links for screenshots:
`#desk,p=done,b=progress,norated`.

## Variants
- **A: Three full cards** — streak card with a two-item checklist, then one complete card per mode (badge,
  pitch, How it works, Start, session-size slider).
- **B: One Today card** — the checklist rows are the launchers (name, badge, Start/Resume); pitch,
  How it works and session size sit in collapsed rows below.
- **C: One Start button** — a single CTA in the streak card runs the next pending mode; slim mode cards
  below carry the badge, pitch and session size but no Start.

## What to Look For
- Which Start buttons land above the dashed fold on the phone.
- Whether the checklist reads as "both are needed for the streak".
- The four card states, especially Off ("Turn on") and Done.
- Desktop: two mode cards side by side (A, C) against Today left, settings right (B).
- Drag a session-size slider to 0: the mode turns off; the last active mode refuses.

## Decision (2026-11-18)
**Winner: B — One Today card.** One card holds the flame, the freeze meter and a launcher row per mode
(name, red pending badge, Start / Resume, a checkmark when done, "Turn on" when off). The rows double as the
streak checklist, so the both-required rule and both Start buttons sit above the phone fold. The pitch,
"How it works", the guest level picker and the session-size slider live in one collapsed row per mode below,
followed by the shared Train schedule row. Desktop: Today card left, settings rows right.

Open (proposed, not decided): show the one-line pitch under the Blunder Check row until the user's first
completed session, since B hides the pitch behind a tap and existing users need to discover the new mode.
