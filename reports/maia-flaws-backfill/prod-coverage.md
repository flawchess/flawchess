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
