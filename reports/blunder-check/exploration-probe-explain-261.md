# Phase 261 D-10: prod EXPLAIN of the exploration probe

Date: 2026-11-22. Target: prod, read-only, one connection (`make_readonly_engine`), `EXPLAIN (ANALYZE, BUFFERS)`.
Statements: the four compiled picks from `temp/261-explore/pick-explain.sql` (user_id 28, level 1500, raw range 850..2150, limit 40, pool 400, `TABLESAMPLE system(2.0)`, `require_facepalm=True`).

## Statement shapes

- **foreign cut**: `pick_foreign_game_ids`, default `min_score` (facepalm score `>= 0.7` inside the `EXISTS` on `game_flaws`).
- **foreign scored**: same statement with `min_score=None` (score `IS NOT NULL`). This is the exploration probe.
- **nearest cut**: `pick_nearest_foreign_game_ids`, nearest 400 sampled games by rating distance, then the `EXISTS` with the 0.7 cut, `ORDER BY random() LIMIT 40`.
- **nearest scored**: same statement with `min_score=None`.

## Timings

Run 1 is the cold run, runs 2 to 4 are warm. `TABLESAMPLE SYSTEM` draws a different sample each run, so the warm median is the figure used.

| Statement | Exec ms (cold, warm x3) | Planning ms (cold, warm x3) | Warm median ms | Rows |
|---|---|---|---|---|
| foreign cut | 98.109, 115.813, 157.072, 101.327 | 10.806, 1.443, 0.732, 1.403 | 115.813 | 40 each run |
| foreign scored | 50.524, 48.104, 46.46, 38.919 | 1.485, 1.469, 1.476, 1.902 | 46.46 | 40 each run |
| nearest cut | 481.905, 389.443, 450.725, 512.909 | 1.811, 1.374, 1.297, 1.305 | 450.725 | 40 each run |
| nearest scored | 319.348, 339.1, 358.306, 319.741 | 0.816, 0.656, 0.65, 0.662 | 339.1 | 40 each run |

## Scan nodes on game_flaws and buffers

| Statement | game_flaws scan node (all four runs) | Seq Scan on game_flaws | Buffers per run (top node) |
|---|---|---|---|
| foreign cut | Index Scan using ix_game_flaws_game_id on game_flaws | no | shared hit=453 read=398 / shared hit=534 read=475 dirtied=3 / shared hit=703 read=623 dirtied=4 / shared hit=457 read=387 dirtied=1 |
| foreign scored | Index Scan using ix_game_flaws_game_id on game_flaws | no | shared hit=309 read=201 / shared hit=295 read=202 / shared hit=346 read=212 dirtied=1 / shared hit=323 read=181 dirtied=1 |
| nearest cut | Index Scan using ix_game_flaws_game_id on game_flaws | no | shared hit=1852 read=8339 dirtied=16 / shared hit=1995 read=7969 dirtied=14 / shared hit=2059 read=7930 dirtied=32 / shared hit=2186 read=8180 dirtied=15 |
| nearest scored | Index Scan using ix_game_flaws_game_id on game_flaws | no | shared hit=2038 read=7406 dirtied=4 / shared hit=2159 read=7331 dirtied=3 / shared hit=2084 read=7324 dirtied=10 / shared hit=2201 read=7301 dirtied=8 |

## Verdict rule (D-10)

Pass when, for both the foreign and the nearest pick, the scored statement has no Seq Scan on `game_flaws` and its warm median is at most max(2 x the matching cut statement's warm median, 200 ms).

- foreign: scored 46.46 ms against a bound of max(2 x 115.813, 200) = 231.6 ms, no Seq Scan: pass
- nearest: scored 339.1 ms against a bound of max(2 x 450.725, 200) = 901.5 ms, no Seq Scan: pass

Both scored statements ran faster than their cut counterparts in this sample: without the cut the `EXISTS` is satisfied by the first scored owner-side blunder of a game, so fewer `game_flaws` rows are visited before `LIMIT 40` fills. Every run read `game_flaws` through `ix_game_flaws_game_id`. No new index is needed.

Caveat: one measurement session of four runs per statement, with run-to-run spread of roughly 20 to 60 percent on the cut statements. The margin to the bound is 5x (foreign) and 2.7x (nearest), well outside that spread.

verdict: pass
