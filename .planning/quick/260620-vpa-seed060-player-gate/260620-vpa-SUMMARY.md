---
quick_id: 260620-vpa
slug: seed060-player-gate
description: "Fix SEED-060 — Games-tab tactic filter omits player_only_gate"
status: complete
date: 2026-06-20
commit: 5eff5f56
---

# Quick Task 260620-vpa — SUMMARY

## What changed

Added `player_only_gate(GameFlaw.ply, Game.user_color)` to the Games-tab
tactic-family EXISTS predicate in `apply_game_filters`
(`app/repositories/query_utils.py`). The EXISTS previously scoped only on
`GameFlaw.game_id == Game.id` and `GameFlaw.user_id == user_id`. Since Phase 113,
`game_flaws` stores BOTH players' flaws (player attributed via ply parity vs
`Game.user_color`), so filtering the Games tab by e.g. `fork` could match a game
whose only fork belonged to the **opponent** — falsely flagging it into the
filter. The fix mirrors the sibling `flaw_exists_from_table` (library_repository.py),
which already applies the D-04 player gate.

## Test

Added `TestQueryFilteredGames::test_tactic_filter_excludes_opponent_only_tactic`
in `tests/test_library_repository.py`. It seeds:
- a PLAYER fork (white user, even ply 2 = white mover) → must match, and
- an OPPONENT-only fork (white user, odd ply 3 = black mover) → must be excluded.

Verified RED before the fix (opponent game leaked into results), GREEN after.

## Verification

- `uv run ty check app/repositories/query_utils.py` → clean.
- `uv run pytest tests/test_library_repository.py tests/test_query_utils.py tests/test_flaw_predicate.py -n auto` → 85 passed.

## Notes

- Sibling SEED-061 (confidence gate) and SEED-062 (comparison orientation basis)
  remain open — handled as separate quick tasks per the user's "one by one" request.
- SEED-060 seed moved to `.planning/seeds/closed/`.

## Commit

- `5eff5f56` fix(library): player-only gate on Games-tab tactic filter (SEED-060)
