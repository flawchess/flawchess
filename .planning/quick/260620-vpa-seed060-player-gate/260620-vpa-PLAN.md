---
quick_id: 260620-vpa
slug: seed060-player-gate
description: "Fix SEED-060 — Games-tab tactic filter omits player_only_gate"
status: planned
---

# Quick Task 260620-vpa: Games-tab tactic filter player gate

## Problem

The Games-tab tactic-family EXISTS in `app/repositories/query_utils.py`
(`apply_game_filters`, ~lines 247-258) scopes only on `GameFlaw.game_id == Game.id`
and `GameFlaw.user_id == user_id`. Since Phase 113, `game_flaws` stores BOTH players'
flaws (player attributed via ply parity vs `Game.user_color`), so the EXISTS matches
**opponent-only** tactics too. The filter is meant to surface the user's own tactical
mistakes. The sibling `flaw_exists_from_table` (library_repository.py:380-387) already
gates correctly with `player_only_gate(GameFlaw.ply, Game.user_color)`.

## Task

1. Add `player_only_gate(_GameFlaw.ply, Game.user_color)` to the Games-tab tactic
   EXISTS predicate in `apply_game_filters`. `player_only_gate` is defined in the same
   module (no import needed); `Game.user_color` is in scope because the EXISTS already
   correlates on `Game.id`.
   - **files:** `app/repositories/query_utils.py`
   - **verify:** `uv run ty check app/`
   - **done:** EXISTS includes the player gate, mirroring `flaw_exists_from_table`.

2. Add a regression test: seed a game where only the OPPONENT committed a family-X
   tactic and assert the game is NOT returned by the Games-tab tactic-family filter.
   - **files:** tactic-filter test module (existing query_utils / library filter tests)
   - **verify:** `uv run pytest <new test> -p no:cacheprovider`
   - **done:** test fails before the fix, passes after.

## must_haves

- truths: Games-tab tactic filter matches only the player's own tactics, not opponent tactics.
- artifacts: player gate predicate in `apply_game_filters` tactic EXISTS; regression test.
- key_links: `app/repositories/query_utils.py`, `app/repositories/library_repository.py` (reference).
