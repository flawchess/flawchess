---
phase: 247
plan: 07
status: complete
---

# 247-07 Summary: prod Maia flaw backfill and coverage

- Slice (11-08 21:15 UTC): 50 games, 380 flaws, 0 NULL, every check passed (`prod-coverage.md` "Slice").
- Full run: three segments of the same command, each a SIGTERM stop plus a relaunch with the stamp as checkpoint: 9 shards,
  then 14 (stopped because 14 shards exhausted prod max_connections, then 30), then 9 shards to EXIT=0 at 11-10 00:18 UTC.
  Combined: 1,025,740 games stamped, 7,581,730 flaws scored, 32,217 NULL, 0 write or score failures, about 27 h.
- Catch-up (D-12): ran after the Phase 248 deploy as `--mode full` with the new code (248-07 Task 3), EXIT=0,
  games_selected=0. Unstamped games with flaws: 0 (0.000% of 1,029,016 stamped).
- Coverage (D-12, Pattern 6 SQL verbatim, 11-10 ~13:40 UTC): denom 7,633,581, scored 7,600,786, **pct_scored 99.570**
  (bar 99.000, pass). null_unstamped 0, null_no_rating 32,682, null_other 113 (ply_beyond_mainline 66 + invalid_root
  34 + 13 from live lanes), best_pair_null 68,736, second_pair_null 1,552,134.
- Health: game_flaws dead tuples 237k of 7.65M live, autovacuum current. Nothing to raise.
- Report: `reports/maia-flaws-backfill/prod-coverage.md` (Slice, Full run, Catch-up, Coverage, Health) plus all shard JSONs.
