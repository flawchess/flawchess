# Phase 259 on prod: reply pass done, readiness gate, covering index

Date: 2026-11-22. Operator: the phase orchestrator. Deployed code read from the prod-run worktree
(`d75996143`) until it was removed; switched code read from the main checkout on the switch-cycle
branch.

## Reply pass

| Item | Value |
|---|---|
| Launched | 2026-11-21T19:01:25Z, PID 2012778, 12 workers, `--throttle-ms 50` |
| Ended | 2026-11-22T11:02Z with `EXIT=0`, about 16 hours, no relaunch (the 02:15 UTC reboot did not interrupt it) |
| Pace | about 79 games per minute per shard at first, 95 to 98 overnight, 77 in the last two hours |

```
total: games_selected=1054792 games_scored=1054792 games_stamped=1044652 games_already_stamped=10140 games_fingerprint_changed=0 games_missing=0 games_write_failed=0 games_score_failed=0 flaws_scored=0 flaws_null=0 spreads_scored=0 spreads_null=0 scores_set=0 scores_null=0 pre_scored=0 pre_null=0 opponent_spreads_scored=0 opponent_spreads_null=0 opponent_pre_scored=0 opponent_pre_null=0 opponent_scores_set=0 opponent_scores_null=0 reason_reply_missing=288044
```

`games_already_stamped=10140`: games the live hook or the Phase 252 feeder had stamped by the time
the pass reached them. No write or score failures. `reason_reply_missing=288044` is the count of
blunders with no reply probability to write (no usable line).

## Readiness counts

`--status --mode reply` (deployed code, 11:03 UTC):

```
reply_stamped_games=1058523 reply_pending_games=0 blunders_total=4729767 blunders_with_reply_prob=4418658 reply_residue_losing=0 unscored_pure_miss_no_best=8300 blunders_without_material_inputs=296674
```

`--status --mode line --cutoff 2026-11-21T18:10:27+00:00` (deployed code, 11:05 UTC):

```
line_done_since_cutoff=1058380 line_pending_games=0 user_blunders_total=2365155 user_blunders_with_score=2209209 user_blunders_qualifying=972755 opponent_blunders_total=2364616 opponent_blunders_with_line_facts=2219916 opponent_blunders_with_score=2195352 user_blunders_with_material_inputs=2214780 opponent_blunders_with_material_inputs=2217432
```

## Coverage, today's expression against the switched one

| Count | Deployed code | Switched code | Change |
|---|---|---|---|
| user_blunders_with_score | 2,209,209 | 2,209,608 | +399 (+0.02%) |
| opponent_blunders_with_score | 2,195,352 | 2,195,716 | +364 (+0.02%) |
| user_blunders_qualifying (cut 0.50) | 972,755 | 1,050,362 | +77,607 (+8.0%), provisional constants |

The switched expression scores slightly more blunders, not fewer, so the 1% stop does not apply.
The readings are a few minutes apart on a live database (`user_blunders_total` was 2,365,155 in
both; `opponent_blunders_total` moved from 2,364,616 to 2,364,620).

Switched-code status lines (11:08 to 11:12 UTC):

```
spread_stamped_games=1059071 spread_pending_games=0 user_blunders_total=2365155 user_blunders_with_spread=2363925 user_blunders_with_score=2209608 user_blunders_qualifying=1050362
line_done_since_cutoff=1058380 line_pending_games=0 user_blunders_total=2365155 user_blunders_with_score=2209608 user_blunders_qualifying=1050362 opponent_blunders_total=2364620 opponent_blunders_with_line_facts=2219920 opponent_blunders_with_score=2195716 user_blunders_with_material_inputs=2214785 opponent_blunders_with_material_inputs=2217436
```

## Prod-run worktree

No backfill process was running; `.claude/worktrees/phase-259-prod` was removed and pruned.

## Covering index ix_game_flaws_facepalm_inputs

| Item | Value |
|---|---|
| Command | `scripts/build_facepalm_inputs_index.py --db prod`, detached, from the switch-cycle branch |
| Before the build | 21 connections, no transaction older than a minute, index absent, `game_flaws` 15 GB |
| Other operator job | the Phase 252 feeder was running; the owner approved building beside it |
| statement_timeout (server default) | 0 |
| maintenance_work_mem | 512MB |
| Sessions on the database at start | 13 |
| Duration | under 50 seconds (launched 11:15:44Z, exited before 11:16:33Z) |
| Result | `ix_game_flaws_facepalm_inputs: valid, definition equals the expected text.`, `EXIT=0` |
| Size | 224 MB |
| indisvalid | true |

Log: `temp/facepalm-backfill/cic-prod-259.log`.
