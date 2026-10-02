---
sketch: 005
name: streak-flame-and-freezes
question: "What should the 3-layer streak flame and the freeze meter look like, and how should the diff-driven animations feel?"
winner: "A (Concentric) + Snowflake icon"
tags: [train, streak, flame, freezes, animation, mobile, SEED-181]
---

# Sketch 005: Streak flame + freezes

## Design Question
Which flame silhouette keeps the streak number legible at hero (170px) and card (64px) size for 1-3 digits,
which freeze icon reads as clearly "cold, separate from the streak", and do the five arrival states
(ignite / freeze used / freeze earned / quiet reset / static) feel right?

## How to View
open .planning/sketches/005-streak-flame-and-freezes/index.html
(or serve the repo root: `python3 -m http.server 8765` → http://127.0.0.1:8765/.planning/sketches/005-streak-flame-and-freezes/)

## Variants
- **A: Concentric** — one flame silhouette repeated at 100/76/56% (red/orange/yellow), number in the bowl.
- **B: Licks** — three distinct layer shapes with offset tips, more organic fire.
- **C: Chunky drop** — symmetric teardrop, biggest number, least "fire-like".

Freeze icon (independent axis): Snowflake / Snowflake disc / Ice cube.

## What to Look For
- Number legibility at 64px for 7, 52, 365.
- Freeze row vs flame: hot vs cold must never read as one concept.
- Freeze-used beat: sad but not punishing (flame stays lit, frost sweep).
- Ignite length (~1.5s) and that reduced-motion shows only the final state.

Shared code `flame.js` / `flame.css` is reused by sketch 006.

## Decision (2026-10-02)
**Winner: A — Concentric** flame (one silhouette at 100/76/56%, red/orange/yellow) with the
**plain stroke Snowflake** freeze icon (icy blue filled, grey outline empty). Card size 64px.
