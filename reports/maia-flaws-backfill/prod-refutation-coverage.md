# Prod refutation backfill coverage (Phase 248, D-11)

The prod backfill of `game_flaws.maia_refutation_prob` / `maia_refutation_rank` (the chance that a player at the
blunderer's rating finds the punishing reply) and the `games.maia_refutation_completed_at` stamp. Prod runs the
Phase 248 code since deploy e60dd130 (2026-11-10 00:36 UTC).

## Slice

- When: 2026-11-10 05:23:45 UTC, run_stamp `20261110T052345Z`
- Command: `PYTHONUNBUFFERED=1 uv run python -u scripts/backfill_maia_flaws.py --db prod --mode refutation --shard 0 --num-shards 9 --limit 50 --report-dir temp/maia-refutation-backfill`
- Banner: `target: --db prod -> database=flawchess server=172.18.0.2:5432` (prod behind the tunnel on 15432)
- Exit 0. Total line: games_selected=50 games_scored=50 games_stamped=50 games_already_stamped=0
  games_fingerprint_changed=0 games_missing=0 games_write_failed=0 games_score_failed=0 refutations_scored=103
  refutations_null=0 refutations_from_pv=0, reasons `{}`, elapsed 16.8 s
- Shard JSON: `prod-refutation-20261110T052345Z-shard0.json`

Baseline before the slice (248-06): refutation_stamped_games=0, refutation_unstamped_games_with_flaws=1,026,634,
user_blunders_with_refutation=0, user_blunders_total=2,297,495.

Prod MCP spot-check on the 50 slice games (stamped in the last 30 minutes):

| Check | Value |
|---|---|
| Games refutation-stamped | 50 |
| Base stamp missing or later than refutation stamp | 0 |
| User-side blunders (severity 2, user parity) | 103 |
| ... with prob in (0, 1] and rank >= 1 | 103 |
| ... with `maia_played_prob` NULL (base value lost) | 0 |
| Other flaw rows (opponent flaws, user mistakes) | 277 |
| ... carrying a refutation value | 0 |
| Rows with only one of prob/rank set | 0 |
| Refutation prob min / median / mean / max | 0.017 / 0.530 / 0.526 / 0.999 |
| Refutation is Maia's top move (rank 1) | 69 of 103 |
| Max rank | 6 |

After the slice: games with the refutation stamp = 50; base-stamped games without it = 1,026,660; games with flaws
but no base stamp = 0.

Pace: 6.14 refutations/s for one shard (includes model load on 50 games). ETA for the full run, per the plan formula
(2,297,495 - 103) / (9 x 6.14) = about 41,600 s, so roughly 11.5 h. That is an upper-bound estimate on throughput per
shard: 9 Maia shards share 8 physical cores, so the observed full-run rate may come in lower.

## Full run

- When: 2026-11-10 05:26:10 to 13:29:14 UTC (about 8 h 03 min), run_stamp `20261110T052610Z`, 9 shards
- Command: `setsid nohup bash -c 'PYTHONUNBUFFERED=1 uv run python -u scripts/backfill_maia_flaws.py --db prod --mode refutation --workers 9 --report-dir temp/maia-refutation-backfill; echo EXIT=$?'`
- Exit 0 (one `EXIT=` line in the log, no tracebacks). Total line: games_selected=1026584 games_scored=1026584
  games_stamped=1026584 games_already_stamped=0 games_fingerprint_changed=0 games_missing=0 games_write_failed=0
  games_score_failed=0 refutations_scored=2293321 refutations_null=4071 refutations_from_pv=13240
- Null reasons: refutation_missing=2923, no_rating=860, no_legal_reply=260, invalid_root=17, ply_beyond_mainline=11
- Pace: about 8.4 to 8.8 refutations/s per shard, so the plan's 11.5 h estimate was pessimistic
- Shard JSONs: `prod-refutation-20261110T052610Z-shard{0..8}.json`

Prod state right after the run (MCP): refutation-stamped games 1,028,905 (backfill plus live lanes since deploy),
base-stamped games without the refutation stamp 76 (live imports since the run started, picked up by the catch-up),
games with flaws but no base stamp 0. User-side blunders 2,301,294, of which 2,297,221 (99.82%) carry a refutation
value.

Live lanes: games scored by the live eval lanes after the deploy carried the refutation value without any backfill
(460 games, 678 of 679 user blunders with a refutation value), so new imports are covered going forward.
