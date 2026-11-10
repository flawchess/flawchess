# Phase 247 prod Maia flaw backfill: coverage

Baselines before the run (plan 06, 2026-11-08, prod via tunnel): 7,611,640 flaws in 1,025,382 fully
evaluated games with flaws (S4), mover rating NULL 32,113, `game_flaws` 11 GB, `games` 4.3 GB (S5),
0 stamped games. Prod disk: 87 GB free of 150 GB.

## Slice

- Command: `PYTHONUNBUFFERED=1 uv run python -u scripts/backfill_maia_flaws.py --db prod --shard 0 --num-shards 9 --limit 50`
- run_stamp: `20261108T211536Z` (report `prod-20261108T211536Z-shard0.json`), exit 0, 32 s wall, 11.4 flaws/s
- Counters: games_selected=50, games_stamped=50, flaws_scored=380, flaws_null=0, games_fingerprint_changed=0,
  games_write_failed=0, reason_second_equals_best=30, reason_second_missing=17
- Prod check over the 50 stamped games (380 flaws): maia_played_prob NULL 0, out of (0, 1] 0, played rank < 1 0,
  effective moves < 1 0, best pair NULL 0, second pair NULL 47 (= 30 + 17, matches the reason counters).
  Means: played prob 0.238, played rank 3.40, effective moves 5.21.
- Spot-check:

| game_id | ply | sev | played p / rank | best p / rank | second p / rank | eff. moves |
|---|---|---|---|---|---|---|
| 1457383 | 84 | 1 | 0.903 / 1 | 0.0063 / 8 | 0.0071 / 7 | 1.69 |
| 1457653 | 37 | 2 | 0.036 / 3 | 0.795 / 1 | 0.0001 / 13 | 2.01 |
| 1457472 | 90 | 2 | 0.069 / 5 | 0.269 / 2 | 0.016 / 6 | 5.02 |

## Full run

Three segments of one `--db prod` run, each a SIGTERM stop plus a relaunch of the same command (the stamp is the
checkpoint), log `temp/maia-flaws-backfill/prod-full.log`:

| Segment | run_stamp | Shards | When (UTC) | games_stamped | flaws_scored | flaws_null | End |
|---|---|---|---|---|---|---|---|
| 1 | `20261108T211707Z` | 9 | 11-08 21:17 to 11-09 06:07 | 339,050 | 2,456,314 | 17,352 | stopped to retry at 14 workers |
| 2 | `20261109T060805Z` | 14 | 11-09 06:08 to 08:08 | 83,500 | 604,852 | 5,126 | stopped, 14 shards exhausted prod max_connections (30 at the time) and ran slower per shard |
| 3 | `20261109T080843Z` | 9 | 11-09 08:08 to 11-10 00:18 | 603,190 (+3 already stamped) | 4,520,564 | 9,739 | EXIT=0 |

Combined: games_stamped=1,025,740 games_write_failed=0 games_score_failed=0 games_fingerprint_changed=0
flaws_scored=7,581,730 flaws_null=32,217, wall time about 27 h. Reason buckets (summed): second_missing=1,067,262,
second_equals_best=480,534, best_missing=71,177, no_rating=32,117, single_legal_move=3,161, ply_beyond_mainline=66,
invalid_root=34. Shard JSONs: `prod-20261108T211707Z-shard{0..8}.json`, `prod-20261109T060805Z-shard{0..13}.json`,
`prod-20261109T080843Z-shard{0..8}.json`.

## Catch-up

Per D-12 the catch-up ran after the Phase 248 deploy with the new code as `--mode full` (Phase 248 plan 07 Task 3,
log `temp/maia-refutation-backfill/prod-catchup-full.log`, run_stamp `20261110T133134Z`): EXIT=0, games_selected=0.
The live lanes stamped every game imported or re-analyzed since the deploy. After the catch-up (2026-11-10 ~13:35 UTC):
base-stamped games 1,029,016, unstamped games with flaws 0, so the planner's sanity ratio (unstamped / stamped,
rule of thumb 0.5%, not a gate) is 0.000%.

## Coverage

D-12 coverage SQL (247-RESEARCH Pattern 6, verbatim) on prod via MCP, 2026-11-10 ~13:40 UTC:

| denom | scored | pct_scored | null_unstamped | null_no_rating | null_other | best_pair_null | second_pair_null |
|---|---|---|---|---|---|---|---|
| 7,633,581 | 7,600,786 | **99.570** | 0 | 32,682 | 113 | 68,736 | 1,552,134 |

Pass (D-12 bar 99.000). The denominator grew from 7,611,640 (plan 06 S4 baseline) through new imports.

- null_no_rating 32,682 (0.43%): mover rating NULL, matching the S4 baseline of 32,113 plus new imports.
- null_other 113: ply_beyond_mainline 66 plus invalid_root 34 from the shard reasons; the other 13 come from the live
  lanes, which do not write shard reports.
- best_pair_null 68,736 and second_pair_null 1,552,134 are not pass/fail. They track the reason counters
  best_missing (71,177) and second_missing + second_equals_best (1,547,796). The difference comes from live-lane
  scoring and reclassified games.

## Health

Read-only, 2026-11-10 ~13:40 UTC: `game_flaws` n_live_tup 7,653,589, n_dead_tup 237,178, last autovacuum 12:21, last
autoanalyze 11:35, total size 13 GB (11 GB before the run, which also includes the Phase 248 refutation pass).
`games` n_live_tup 1,112,665, n_dead_tup 158,374, 4.3 GB. Dead tuples are about 3% of live rows on both tables, so no
VACUUM is needed and there is nothing to raise.
