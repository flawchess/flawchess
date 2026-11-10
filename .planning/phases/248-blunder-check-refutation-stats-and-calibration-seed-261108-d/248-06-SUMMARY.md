---
phase: 248
plan: 06
status: in-progress
---

# 248-06 Summary: ship go-forward refutation scoring

## Task 1: owner go-ahead (blocking-human checkpoint)

- Owner's literal answer (2026-11-09, ~20:40 UTC): `merge-and-deploy`
- Given before 247-07 ended; Task 2 held until the precondition held.
- 247-07 end state: `temp/maia-flaws-backfill/prod-full.log` has 1 `EXIT=` line, `EXIT=0` at 2026-11-10 00:18:38 UTC
  (run stamp 20261109T080843Z, 9 shards). Total line: games_selected=603193 games_scored=603193 games_stamped=603190
  games_already_stamped=3 games_write_failed=0 games_score_failed=0 flaws_scored=4520564 flaws_null=9739.
  The 247-07 python process (PID 3148890) is gone and no `backfill_maia_flaws.py` process is alive.
- 247-07 catch-up and coverage (its Task 3): pending (no 247-07-SUMMARY.md). Per D-12 it runs after this deploy with the
  new code as `--mode full` (plan 07 Task 3). 247-07 Task 2 step 5 (prod-coverage.md "Full run" section, shard JSON
  commit) also not done yet.
