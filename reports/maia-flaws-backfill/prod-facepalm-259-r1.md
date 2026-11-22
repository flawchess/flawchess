# Phase 259 R1 on prod: deploy, line pass, reply pass launch

Date: 2026-11-21. Operator: the phase orchestrator, from the detached prod-run worktree
`.claude/worktrees/phase-259-prod` (PRODWT).

## Release

| Item | Value |
|---|---|
| R1 squash commit on main | `c4cb1e699` |
| Release PR | #497, squash-merged to production as `d75996143` |
| Server SHA after deploy | `d7599614` |
| T_DEPLOY (line-pass cutoff) | `2026-11-21T18:10:27+00:00` |
| PRODWT HEAD | `d75996143` (detached at `origin/production`) |
| Forward-port | pushed by `bin/deploy.sh` (`f65edcd32` on main) |

The plan's check "R1 squash SHA is an ancestor of PRODWT HEAD" cannot hold because release PRs
squash. Checked instead: `git diff c4cb1e699 d75996143` is empty (identical trees).

The release also carried Phase 258 (Library Stats recent-sample snapshots) and quick task
261121-n50 (`c3ab036e8`), both already on main.

## Prod checks

| Check | Result |
|---|---|
| S1 connections before the passes | 11 |
| S2 schema head | `d2a6c8e0f259` |
| S3 new columns | 4 rows: `games.facepalm_reply_completed_at`, `game_flaws.maia_best_reply_prob`, `game_flaws.material_loss`, `game_flaws.material_missed` |
| S4 hook live | of 119 blunders in games analysed after T_DEPLOY, 102 have `material_loss` and 102 have `maia_best_reply_prob` (read a few minutes after the deploy; the reply count comes from the hook alone) |
| Benchmark DB revision | `d2a6c8e0f259` (`bin/benchmark_db.sh start`); nothing was listening on :8001, no restart needed; no benchmark backfill (D-10) |

## Line pass

Operator state before launch: the Phase 252 feeder had been stopped by the owner; no other
operator process was running.

| Item | Value |
|---|---|
| Pending at launch | `line_pending_games=1054843` |
| Slice | 50 games, 1 worker, about 1 s, 0 failures (`scores_set=95`, `opponent_scores_set=98`) |
| Run A | 4 workers, `--throttle-ms 50`, launched 18:13:25 UTC, about 190 games/s, stopped cleanly on SIGTERM at 23,700 games (owner asked for 8 workers) |
| Run B | 8 workers, `--throttle-ms 50`, launched 18:15:48 UTC, about 440 games/s, ended 18:55 UTC with `EXIT=0` |
| Run B totals | `games_selected=1031093 games_scored=1031093 games_stamped=1031093 games_write_failed=0 games_score_failed=0 scores_set=2151360 scores_null=152742 opponent_scores_set=2136921 opponent_scores_null=166027` |
| Connections during run | 19 (4 workers), 24 (8 workers) |
| Duration | about 42 minutes in total |

Status after the pass (`--status --mode line --cutoff 2026-11-21T18:10:27+00:00`):

```
line_done_since_cutoff=1055191 line_pending_games=0 user_blunders_total=2357389 user_blunders_with_score=2202366 user_blunders_qualifying=970166 opponent_blunders_total=2356735 opponent_blunders_with_line_facts=2213009 opponent_blunders_with_score=2188485 user_blunders_with_material_inputs=2207928 opponent_blunders_with_material_inputs=2210542
```

Log: `temp/facepalm-backfill/line-prod-259.log` (ends with `EXIT=0`). Shard reports:
`prod-line-20261121T181312Z-*` (slice), `prod-line-20261121T181327Z-*` (run A),
`prod-line-20261121T181549Z-*` (run B).

## Reply pass

Status before the slice (`--status --mode reply`):

```
reply_stamped_games=475 reply_pending_games=1054842 blunders_total=4714215 blunders_with_reply_prob=1525 reply_residue_losing=2651916 unscored_pure_miss_no_best=8242 blunders_without_material_inputs=294822
```

| Item | Value |
|---|---|
| Slice | 50 games, 1 worker, 19 s, `reply_probs_set=214` (about 2.6 games/s and 11 inferences/s per worker) |
| Full run | 12 workers, `--throttle-ms 50`, launched 2026-11-21T19:01:25Z, PID 2012778 |
| Connections with the run up | 30 |
| First pace reading (19:05 UTC) | about 275 games per shard after 4 minutes, roughly 16 games/s over 12 shards |
| Estimate | about 18 hours for 1.05M games; crosses the 02:15 UTC prod reboot |

On a reboot or crash: reopen `bin/prod_db_tunnel.sh` and relaunch the same command from PRODWT;
the per-game stamp resumes it. Log: `temp/facepalm-backfill/reply-prod-259.log`. Completion is
checked in plan 11 Task 2.

## Notes

- The owner approved restarting the Phase 252 feeder beside the reply pass (an exception to the
  one-operator-run rule). A game the feeder re-walks has its five stamps cleared and is rescored
  by the hook in full mode, so it gets its material inputs and reply probability from the
  repaired line and drops out of the reply pass's pending set.
- `blunders_without_material_inputs=294822` is the NULL case (line too short to tell, or no
  usable line); the readiness gate in plan 11 reads the residues.
