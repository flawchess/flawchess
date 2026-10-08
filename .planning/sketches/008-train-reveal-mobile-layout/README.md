---
sketch: 008
name: train-reveal-mobile-layout
question: "How should the post-solve reveal (lines, verdict, free play, Solution/Analyze/Next) use a phone screen?"
winner: "Combined (A+B+C+D), phone + desktop"
tags: [train, reveal, mobile, lines, free-play, layout]
---

# Sketch 008: Train Reveal Mobile Layout

## Design Question
On a 390x844 phone the line cards get ~24% of the first view (board 38%, bot bubble 23%,
nav 7%). Which structure lets a player compare Your / Best / Game, step the lines, and
explore freely without scrolling, and without two separate modes (cards vs. free play)?

Baseline screenshots: `temp/puzzle-reveal-ux/` (2026-10-08, dev, puzzle 8 of 9).

## How to View
open .planning/sketches/008-train-reveal-mobile-layout/index.html
(or the published artifact on a phone; the variant picker is the top bar)

## Variants
- **0: Current** — today's reveal rebuilt as the baseline (bubble, four cards, free-play swap, Solution button).
- **A: Lines panel** — three chips (You / Best / Game with SAN + eval) + one wrapping move list for the selected line.
- **B: One move tree** — the three lines are pre-loaded branches; piece moves fork sidelines in place; ⏮ replaces Solution; board controls always in the bottom bar.
- **C: Verdict strip** — the bubble collapses to one tappable line with points + Next; Your-call card folded in.
- **D: Bottom action bar** — ⏮ ‹ › ⇅ + Analyze + Next pinned at the bottom for the whole reveal.
- **★ Combined · phone** — strip + chips + tree list + action bar; fits the first view without scrolling.
  Round 2 (owner feedback): the reveal opens with **You** selected and only the selected chip's arrow + mark
  opaque (others fade to ~20-30% instead of hiding); **You merges with Best or Game** into one chip
  ("You = Best", "You = Game") when the moves coincide. Scenario picker in the sketch bar.
- **★ Combined · desktop** — same model at 1280x800: board left with ⏮ ‹ › ⇅ + Analyze/Next under it,
  full verdict bubble + chips + move tree on the right; ← → / Home keys.

## What to Look For
- Can you still compare the three moves at a glance once they are chips instead of cards?
- Does forking a sideline mid-line (B / combo) feel natural, and is ⏮ an adequate stand-in for Solution?
- Does the one-line verdict lose the teaching moment, or is the tap-to-expand enough?
- Thumb reach: Next in the bottom bar vs. inside the bubble.
