---
sketch: 006
name: train-landing-hero
question: "Where does the streak flame live on the Train landing at phone width, next to the Start CTA?"
winner: "A"
tags: [train, landing, hero, layout, mobile, schedule, SEED-181]
---

# Sketch 006: Train landing hero

## Design Question
On a 375px phone, which layout puts the flame and a full-width Start button in one glance above the fold,
and does collapsing the Train schedule card to a summary row work?

## How to View
open .planning/sketches/006-train-landing-hero/index.html (three phones side by side; reuses 005's flame.js/flame.css)

## Variants
- **A: Flame beside the CTA** — compact hero card: flame left, freezes + Start in the right column.
- **B: Centered hero** — big centered flame, freezes, full-width Start inside one hero card.
- **C: Minimal change** — today's Streak/Puzzle pool cards with the flame swapped in, Start full-width on top.

All three: Puzzle pool as two stat tiles (A/B) or today's card (C); Train schedule collapsed to
"Mo–Fr · 6 puzzles · 16:00" (tap to expand; day toggles filled brown when selected).

## What to Look For
- Start + flame above the fold; how much vertical space each hero costs.
- Whether the collapsed schedule summary is enough, and whether the filled day toggles fix the
  "all seven look the same grey" ambiguity.

## Decision (2026-10-02)
**Winner: A — Flame beside the CTA.** Compact hero card: ~92px flame left; right column holds
"Session streak · N of M this week", the 7-slot freeze meter and the full-width Start button.
Puzzle pool as two stat tiles; Train schedule collapsed to a summary row with filled day toggles.
