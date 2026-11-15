# Prod line material copy and parity (Phase 254 release R1)

Date: 2026-11-14 (UTC). Plan 254-06 Task 3.

## Release

- R1 squash commit on main: `adbdf856a`. Release PR #478, squash-merged to production as `697ec5fbd`.
- Deployed through `bin/deploy.sh`, finished 2026-11-14T23:38Z, server SHA verified as `697ec5fb`. Site HTTP 200.
- Forward-port of the production merge commit pushed to main as `2b9c62ce4`.
- The release also carried Phase 253 (facepalm score in the library UI) and the library filter changes that were on
  main and not yet deployed.
- Prod schema after the deploy: `alembic_version` = `a7d2c9e1b254`; the five new `game_flaws` columns are present.
- Live hook: the first game whose Maia hook ran after the deploy has `best_line_material` and `maia_pre_spread` on
  its 4 flaw rows (read 2026-11-15T00:00Z).

## Prod-run worktree

- `/home/aimfeld/Projects/Games/flawchess/.claude/worktrees/phase-254-prod`, detached at `697ec5fbd` (`origin/production`).
- Its tree is identical to the R1 squash commit `adbdf856a` (`git diff --stat` empty). The squash commit is not an
  ancestor of production, because releases are squash-merged; tree equality is the check that applies.

## Benchmark DB

- `bin/benchmark_db.sh start` applied the migration; head is `a7d2c9e1b254`.
- `SELECT count(*) FROM game_flaws WHERE facepalm_score IS NOT NULL` = 2515. No benchmark backfill in this phase.
- The benchmark-lane backend on :8001 was left running, not restarted.

## Copy

- Connections before launch (`SELECT count(*) FROM pg_stat_activity`): 13. Pending rows before launch: 2,169,540.
- Slice (5 batches, `--throttle-ms 50`): 23,621 rows in about 5 s, about 4,700 rows per second.
  Report `copy-line-material-20261114T234043Z.json`.
- Full run, detached from the prod-run worktree, launched 2026-11-14T23:41:04Z, PID 931463:
  `total: batches=557 games_scanned=1113914 rows_copied=2145919 cursor=3288312 stopped_early=False dry_run=False`,
  `EXIT=0`, elapsed 1045.5 s (about 17 min, about 2,050 rows per second including the throttle).
  Report `copy-line-material-20261114T234105Z.json`.
- One connection, no other operator process during the copy. Connections after the run: 17.

## Status

`copy_pending_rows=0 copied_rows=2169544`

## Parity (gate for R2)

`stored_scored=1850930 expression_scored=1850930 both_scored=1850930 max_abs_diff=1.003345291294977e-07 cut_side_mismatches=0`

Exit 0. The expression over the copied facts equals the stored `facepalm_score` within 1e-6 on every scored user
blunder, and no row sits on a different side of `FACEPALM_SCORE_MIN`.
