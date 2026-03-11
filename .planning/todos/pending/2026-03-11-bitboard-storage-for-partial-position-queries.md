---
created: 2026-03-11T12:47:06.166Z
title: Bitboard storage for partial-position queries
area: database
files:
  - app/models/game_position.py
---

## Problem

Standard Zobrist hashing is all-or-nothing — you can't query for pieces on specific squares from a hash. Users may want to find games matching partial positions, e.g. "all games where black has a pawn on d6, a pawn on c6, and a knight on f6 by move 3." The current three-hash design (full_hash, white_hash, black_hash) cannot support this.

## Solution

Add 12 BIGINT bitboard columns to `game_positions` — one per piece type (white pawn, white knight, ..., black king). Each column stores a 64-bit integer where each bit represents a square. Queries use bitwise AND to check for pieces on specific squares:

```sql
WHERE black_pawn_bb & (1<<19 | 1<<18) = (1<<19 | 1<<18)  -- d6, c6
  AND black_knight_bb & (1<<21) = (1<<21)                  -- f6
  AND ply <= 6
```

Deferred to v2 due to significant storage overhead (12 extra BIGINT columns per row in the hot table). Consider whether partial indexes or a separate table would be more appropriate when implementing.
