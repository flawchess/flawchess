---
title: Eliminate per-request game_positions aggregation family (import-time per-game columns)
trigger_condition: When data grows toward ~10× current, OR a specific endgame/openings/stats slow-query complaint appears in prod
planted_date: 2026-07-03
source: reports/code-review-fable-2026-07-02.md (finding #5, plus 3.1/3.2/3.3/3.4)
---

# SEED-077: Kill the per-request `game_positions` aggregation family

The `GET /endgames/overview` path re-derives "which games have ≥6 endgame plies" from
`game_positions` ~7× per request, independently, in serial repo functions
(`endgame_repository.py:43-66, 206-225, 363-382, 560-616, 656-756, 827-840`); the insights
path doubles it on cache miss. Sibling offenders share the disease: `canonical_slice_sql`
CTEs omit `user_id` so the covering index `ix_gp_user_endgame_game` is unusable (#3.2);
`query_opening_phase_entry_metrics_batch` is a measured ~1.3 s query (#3.3); Opening
Insights scans ply 0–16 × all games twice, uncached (#3.4); Stats tab rebuilds the same
filtered set ~6× (#3.5).

## Why deferred (not doing it now)

Prod is healthy: no recurring query above ~300 ms, cache hit 99.86%. The report itself
frames this as "will not survive 10× data growth" — headroom, not current pain. The 135 s
incident it references (quick-260617-pu4) already happened and was mitigated. The durable
fix is a whole phase; doing it now is premature.

## Durable fix (the phase, when triggered)

Persist per-game endgame facts on `games` at import time so the dashboard never touches
`game_positions`: `endgame_entry_ply`, `endgame_entry_eval_cp/mate`, `endgame_ply_count`,
per-class span info, plus `mg_entry_eval_cp/mate SMALLINT` for the opening pillar (#3.3).
Migration + backfill script (`--db dev|prod`, prod via tunnel) + rewrite of
`endgame_repository`, `canonical_slice_sql`, `stats_repository`, `openings_repository` +
EXPLAIN verification against prod query shapes.

## Cheap immediate wins that can ride along (or go first if a query complaint lands)

- **#3.2 one line per CTE**: add `user_id` predicate to the `canonical_slice_sql` CTEs so
  `ix_gp_user_endgame_game` is used. No index change.
- **#3.3**: add `user_id` to `phase_entry_subq`.
- Rewrite the two `Game.id.notin_(subq)` anti-joins as `NOT EXISTS`
  (`endgame_repository.py:596, 738`) — `NOT IN` can't be planned as an anti-join.
- **#3.4**: replace the partial index with `(user_id, full_hash, move_san) INCLUDE
  (ply, game_id) WHERE ply <= 28`; cache keyed on (user_id, filter hash, last_import_at).

Related: SEED-041 (prod DB query/index tuning), SEED-038 (game_flaws materialization).
