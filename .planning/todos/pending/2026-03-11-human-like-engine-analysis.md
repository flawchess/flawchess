---
created: 2026-03-11T11:08:09.292Z
title: Human-like engine analysis
area: general
files: []
---

## Problem

Modern chess engines (Stockfish, Lc0) evaluate positions objectively, but their recommended moves often include computer-only tactics that no human at a given rating would realistically find. This makes post-game analysis misleading for improving players — a position Stockfish calls "equal" might be practically winning if the only defensive moves require 20-move-deep calculation that even experts can't do over the board.

Existing platforms (lichess, chess.com) show raw engine evaluations without accounting for human playability, leaving a gap between "objectively best" and "best move I could actually find."

## Solution

Two-stage evaluation pipeline per position:

1. **Standard engine evaluation** — Run Stockfish via UCI to generate candidate moves with centipawn scores
2. **Human plausibility filter** — Use a Maia Chess-style model (neural net trained on millions of human games at specific Elo bands: 1100-1900) to score each candidate move's likelihood of being found by a human at the target rating. Prune moves below a plausibility threshold.

Key technical components:
- **Maia Chess** (MIT licensed, based on Lc0 architecture) as the plausibility model — predicts what a human at a given Elo would actually play with ~50%+ accuracy
- **python-chess UCI integration** for Stockfish communication (already in stack)
- Elo-band selector in UI so users can set their rating level
- Results show "practical evaluation" alongside objective evaluation

This is a major feature — likely warrants its own milestone (v2+). Not feasible within the v1 scope which focuses on position-based win/loss analysis.
