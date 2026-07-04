---
created: 2026-03-11T13:10:53.388Z
title: Display opening name from lichess chess-openings database
area: ui
files:
  - frontend/ (Phase 4)
---

## Problem

When users interact with the board (clicking through moves to specify a position for analysis), there's no indication of which opening they're looking at. Lichess maintains a curated open-source database (github.com/lichess-org/chess-openings) with ~3,500 opening entries mapping move sequences to ECO codes and opening names.

## Solution

**Frontend (Phase 4):** Load the lichess chess-openings TSV data as a JSON map at build time. As the user plays moves on the interactive board, prefix-match the current move history (from chess.js) against the longest matching entry. Display the opening name + ECO code near the board.

**Backend (optional enhancement):** Precompute Zobrist hashes for each known opening's final position and store in a `known_openings` table. Join against `game_positions` to show opening names in analysis results with transposition-aware matching.
