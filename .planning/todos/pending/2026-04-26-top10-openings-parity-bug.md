---
created: 2026-04-26
title: Fix top-10 most-played openings parity filter (drop ply_count % 2 constraint)
area: backend / stats
files:
  - app/repositories/stats_repository.py
prereq_for: v1.13 (SEED-005 Opening Insights) — Phase A reuses this service-layer call
---

# Fix top-10 most-played openings parity filter

## Problem

`query_top_openings_sql_wdl` in `app/repositories/stats_repository.py:264-265` filters opening entries by ply parity:

```python
# White openings end on odd ply (white's last move), black on even ply
_openings_dedup.c.ply_count % 2 == (1 if color == "white" else 0),
```

This excludes any named opening whose defining move is by the *other* color from the user's top-10 — i.e. black users never see white-defined openings (and vice versa). Concrete bug: `Caro-Kann Defense: Hillbilly Attack` (B10, `1.e4 c6 2.Bc4`, ply 3, odd) has 816 dev-DB games tagged with `user_color='black'` but is invisible in the black top-10 because ply 3 is odd.

Population impact: 48% of named ECO openings (1599 of 3301) are white-defined; black users systematically miss roughly half of all eligible matches.

## Solution

Drop the parity filter. The `Game.user_color == color` clause already restricts to the user's color games. `(eco, name)` is unique in `openings_dedup` (verified — zero duplicate (eco, name) pairs), so removing parity does not introduce JOIN duplication.

The displayed FEN remains the canonical named-opening position (e.g. after `2.Bc4` for Hillbilly Attack). This is a sensible Stats-tab anchor and is also the entry position v1.13 Opening Insights will scan from for candidate-move analysis (the user's color is whoever happens to be to-move at that FEN).

## Verification

- [ ] Drop the parity line; keep `min_ply` floor.
- [ ] Confirm via `mcp__flawchess-db__query` that the user's black top-10 now includes Hillbilly Attack (816 games in dev DB).
- [ ] Spot-check that white-user top-10 still includes black-defined openings the user plays (e.g. Sicilian as white: ply-2 `1.e4 c5`).
- [ ] Run existing stats tests; add one regression test asserting that an opening tagged with `user_color != defining_color` appears in that color's top-10.

## Why pre-v1.13

v1.13 (SEED-005) Phase A reuses `query_top_openings_sql_wdl` as the entry-position scan input. Fixing it as a standalone `/gsd-quick` keeps v1.13's Phase A focused on insight-generation rather than algo correctness, and means the service-layer call is trustworthy by the time insights build on it.

## Notes

User reported 91 games for the missing entry; dev DB shows 816 all-time. Discrepancy likely explained by an active recency / time-control filter at the moment of report.
