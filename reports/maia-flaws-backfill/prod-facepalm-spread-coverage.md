# Prod facepalm spread backfill and coverage (Phase 250-09)

Date: 2026-11-14. Release: PR #475 (`cd9450066` on `production`), deployed 2026-11-13T22:38:21Z, alembic head
`e8b3c6d2f250`. All runs from the operator machine through the prod DB tunnel with
`scripts/backfill_maia_flaws.py --db prod --mode spread`.

## Slice

- Start 2026-11-13T22:39:02Z, `--workers 1 --limit 50` (run stamp `20261113T223903Z`).
- 50 games, 103 spreads scored, 101 scores set, 0 write or score failures.
- O2 (rows stamped since the slice start): spread_rows = 103, out_of_scope_rows = 0.
- Hook check 33 minutes after the deploy (O3): 12 games scored by the live hook, all 12 with the facepalm stamp.

## Full run

Two legs, both `--workers 12 --throttle-ms 50`. The Phase 252 repair was not running on this machine, so 12 shards
were used instead of the planned 6 to 8. Prod connections stayed at 28 of 50 during the run.

| Leg | Run stamp | Start (UTC) | End (UTC) | Games selected | Games stamped | Write failed | Score failed | Exit |
|-----|-----------|-------------|-----------|----------------|---------------|--------------|--------------|------|
| 1 | `20261113T224021Z` | 2026-11-13 22:40:20 | 2026-11-14 02:15:13 | 1,035,052 | 431,892 | 3,000 | 0 | 4 |
| 2 | `20261114T021731Z` | 2026-11-14 02:17:31 | 2026-11-14 07:30:34 | 603,160 | 603,154 | 0 | 0 | 0 |

Leg 1 was cut short by a scheduled reboot of the prod server at 02:15 UTC (Postgres restarted at 02:15:29). All 12
shards lost the database within seconds and aborted with `too_many_batch_failures` (250 unwritten games per shard).
No data was lost: the unwritten games stayed unstamped and leg 2 picked them up after the tunnel was reopened.

Leg 1 total line:

```
total: games_selected=1035052 games_scored=432500 games_stamped=431892 games_already_stamped=0 games_fingerprint_changed=8 games_missing=0 games_write_failed=3000 games_score_failed=0 flaws_scored=0 flaws_null=0 refutations_scored=0 refutations_null=0 refutations_from_pv=0 spreads_scored=944420 spreads_null=903 scores_set=757217 scores_null=188106 reason_no_legal_reply=160 reason_no_rating=741 reason_ply_beyond_mainline=2 reason_refutation_missing=1400
```

Leg 2 total line:

```
total: games_selected=603160 games_scored=603160 games_stamped=603154 games_already_stamped=0 games_fingerprint_changed=6 games_missing=0 games_write_failed=0 games_score_failed=0 flaws_scored=0 flaws_null=0 refutations_scored=0 refutations_null=0 refutations_from_pv=0 spreads_scored=1370720 spreads_null=293 scores_set=1089066 scores_null=281947 reason_invalid_root=17 reason_no_legal_reply=100 reason_no_rating=167 reason_ply_beyond_mainline=9 reason_refutation_missing=1471
```

Pace: about 32 games per second across 12 shards (about 2.7 per second per shard), 8 h 48 min of run time in total.

## Catch-up

Run 2026-11-14 07:32:55 to 07:38:52 UTC, `--workers 2 --throttle-ms 50`.

- `--mode full` (games never base-scored): 1,060 selected, 1,041 stamped, 19 already stamped, 0 failures. 6,440 flaws
  and 1,756 spreads scored. No facepalm scores were set for these games (scores_null = 1,757,
  reason_refutation_missing = 1,756): their blunders have no stored refutation yet.
- `--mode spread` again: 6 selected, 6 stamped, 20 spreads scored, 15 scores set.
- `--status --mode spread` before the catch-up: spread_stamped_games = 1,035,206, spread_pending_games = 6.

## Coverage

O1 at 2026-11-14 07:39 UTC (user-side blunders of base-stamped games):

| Measure | Value |
|---------|-------|
| user_blunders | 2,318,467 |
| with_spread | 2,317,270 |
| pct_with_spread | 99.948 (bar: 99.0, passed) |
| with_score | 1,846,677 |
| pct_with_score | 79.651 |
| qualifying (facepalm_score >= 0.7) | 616,310 |
| null_no_line | 152,567 |
| null_short_line_or_no_played_prob | 318,026 |
| null_no_spread | 1,197 |
| in_unstamped_games | 0 |

About 20% of user blunders have a spread but no score. These are blunders whose stored line is missing or shorter
than 3 plies; they stay unscored until the Phase 252 line repair finishes and the D-18 refit pass (plan 250-10)
re-scores them.

## Health

At 2026-11-14 07:39 UTC: `game_flaws` total size 13 GB (heap 12 GB), 7,711,426 live tuples, 728,979 dead tuples
(9.45%), last autovacuum 03:43:58 UTC, last autoanalyze 07:24:43 UTC. Prod connections 21 with the calibration
running. Sentry showed no errors during the run.
