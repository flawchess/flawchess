---
id: SEED-060
status: dormant
planted: 2026-06-20
planted_during: v1.28 Tactic Tagging (Phase 129)
trigger_when: when next touching the Games-tab flaw/tactic filters, the Library query layer, or any tactic-filter accuracy work
scope: small
---

# SEED-060: Games-tab tactic filter omits player_only_gate (flags opponent-only tactics)

## Why This Matters

The Games-tab tactic-family filter can flag a game into the filter result because the
**opponent** (not the user) allowed or missed a tactic in that family. Since Phase 113,
`game_flaws` stores BOTH players' flaws, so a tactic EXISTS scoped only on `game_id +
user_id` matches opponent flaws too. This is a correctness defect: the filter is meant to
surface the user's own tactical mistakes, and silently including opponent tactics inflates
and mis-scopes the Games list. It also makes the Games surface inconsistent with the
Flaws-tab path, which already gates correctly.

## When to Surface

**Trigger:** when next touching the Games-tab flaw/tactic filters, the Library query layer
(`query_utils.py` / `library_repository.py`), or any tactic-filter accuracy work.

Surfaces during `/gsd-new-milestone` when the milestone scope touches Library filtering or
tactic-tagging accuracy.

## Scope Estimate

**Small** — a few hours. One correlated-subquery predicate plus tests. The correct value is
already established by the sibling implementation, so this is a targeted fix, not a design
task.

## Breadcrumbs

- `app/repositories/query_utils.py` (~lines 244-255) — the Games-surface tactic EXISTS that
  scopes only on `game_id` + `user_id`, with no `player_only_gate(GameFlaw.ply, Game.user_color)`.
- `app/repositories/library_repository.py` (~lines 352-359) — `flaw_exists_from_table`, the
  sibling that DOES apply `player_only_gate` "so an opponent-only flaw does not falsely flag
  a game". Use this as the reference for the correct predicate.
- `Game` is correlatable via `Game.id`, so the EXISTS subquery can reach `Game.user_color`
  for the gate.
- Source: Phase 129 code review **WR-02** — see
  `.planning/phases/129-tactic-filter-ui/129-REVIEW.md`.
- Related background: memory `project_game_flaws_both_players_scope` (game_flaws covers both
  players; player attributed via ply parity vs user_color).

## Notes

Pre-existing from Phase 126; Phase 129 widened this branch (orientation/depth) without
correcting it, which made the asymmetry with `flaw_exists_from_table` starker. Not exploitable
as a security issue (still user-scoped), purely a filter-accuracy correctness bug. Fix: add the
player gate to the EXISTS predicate. Add a test seeding a game where only the opponent committed
the tactic and asserting it is NOT returned by the Games-tab tactic-family filter.
