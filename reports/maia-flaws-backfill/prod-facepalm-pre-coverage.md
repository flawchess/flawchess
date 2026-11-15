# Prod facepalm pre-blunder pass and coverage (Phase 254-07)

Date: 2026-11-15 (UTC). All runs from the prod-run worktree (detached at `697ec5fbd`, the R1 production commit)
through the prod DB tunnel with `scripts/backfill_maia_flaws.py --db prod --mode pre`. One Maia inference at the
pre-blunder position per user-side blunder; writes only `maia_best_prob` and `maia_pre_spread` and stamps
`facepalm_pre_completed_at`.

## Before launch

- Client connections on prod at 06:10:45Z: 10 (max_connections 50).
- `--status --mode pre`: `pre_stamped_games=216 pre_pending_games=1037451 user_blunders_total=2321901 user_blunders_with_best_prob=522 user_blunders_with_pre_spread=526`.
- The Phase 252 repair was not connected to prod during the pass (only the app pool and this operator machine).

## Slice

`--workers 1 --limit 50`, run stamp `20261115T061219Z`: 50 games in 12 s (about 4 games per second for one shard),
`pre_scored=98 pre_null=0`, no write or score failure.

## Full run

| Leg | Run stamp | Shards | Start (UTC) | End (UTC) | Games selected | Games stamped | Write failed | Score failed | Exit |
|-----|-----------|--------|-------------|-----------|----------------|---------------|--------------|--------------|------|
| 1 | `20261115T061307Z` | 8 | 06:13:06 | 13:48:58 | 1,037,401 | 518,281 | 0 | 0 | 0 |
| 2 | `20261115T135144Z` | 14 | 13:51:42 | 19:29:07 | 519,120 | 519,090 | 0 | 0 | 0 |

Both legs `--throttle-ms 50`. Leg 1 was stopped on purpose with SIGTERM (it finished its batches and exited 0) so the
pass could be relaunched with 14 shards at the owner's request; the stamp is the checkpoint, so leg 2 selected only
the unstamped games. A Phase 252 benchmark repair with 8 Stockfish engines at idle priority ran on the same machine
throughout.

Pace: leg 1 about 19 games per second (8 shards), leg 2 about 26 games per second (14 shards on 8 physical cores).
Run time 13 h 13 min in total. Prod connections during leg 2: about 27 of 50.

Leg 1 total line:

```
total: games_selected=1037401 games_scored=518300 games_stamped=518281 games_already_stamped=0 games_fingerprint_changed=19 games_missing=0 games_write_failed=0 games_score_failed=0 flaws_scored=0 flaws_null=0 spreads_scored=0 spreads_null=0 scores_set=0 scores_null=0 pre_scored=1120960 pre_null=764 reason_best_move_missing=9743 reason_no_rating=762 reason_ply_beyond_mainline=2
```

Leg 2 total line:

```
total: games_selected=519120 games_scored=519120 games_stamped=519090 games_already_stamped=0 games_fingerprint_changed=30 games_missing=0 games_write_failed=0 games_score_failed=0 flaws_scored=0 flaws_null=0 spreads_scored=0 spreads_null=0 scores_set=0 scores_null=0 pre_scored=1199318 pre_null=175 reason_best_move_missing=8164 reason_invalid_root=17 reason_no_rating=149 reason_ply_beyond_mainline=9
```

No scheduled reboot fell inside the run (it started after 02:15 UTC and ended before the next one).

## Coverage

`--status --mode pre` at 19:30Z:

```
pre_stamped_games=1040211 pre_pending_games=30 user_blunders_total=2326282 user_blunders_with_best_prob=2306902 user_blunders_with_pre_spread=2324907
```

- Pending games: 30 (games whose fingerprint changed during the pass plus new arrivals; the live hook and a later
  catch-up cover them).
- `maia_pre_spread`: 2,324,907 of 2,326,282 user-side blunders (99.94%). The rest have no rating or an invalid root.
- `maia_best_prob`: 2,306,902 of 2,326,282 (99.17%). 17,907 blunders have no stored best move
  (`reason_best_move_missing`), so the probability of the best move cannot be read; their spread is still written.

## Open question 7 (RESEARCH)

The two dev example games (817357 ply 24 and 820181 ply 65) do not exist on prod, so plan 11 passes no `--extra`
rows for them.
