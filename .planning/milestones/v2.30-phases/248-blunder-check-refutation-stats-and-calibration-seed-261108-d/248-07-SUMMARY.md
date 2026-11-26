---
phase: 248
plan: 07
status: complete
live_lane_check: passed
---

# 248-07 Summary: prod refutation backfill and coverage (D-11)

- Slice (11-10 05:23 UTC, run_stamp 20261110T052345Z): 50 games, 103 user blunders scored, 0 NULL, base values intact,
  non-target rows untouched.
- Full run (run_stamp 20261110T052610Z, 9 shards, 05:26 to 13:29 UTC, about 8 h): EXIT=0, games_stamped=1,026,584,
  refutations_scored=2,293,321, refutations_null=4,071, refutations_from_pv=13,240, 0 write or score failures.
  Reasons: refutation_missing 2,923, no_rating 860, no_legal_reply 260, invalid_root 17, ply_beyond_mainline 11.
  Pace 8.4 to 8.8 refutations/s per shard (the plan estimated about 6.1).
- Live lanes (the 248-06 deferred check): post-deploy live analyses carried refutation values with no backfill
  (460 games, 678 of 679 user blunders). New imports are covered going forward.
- Catch-up: `--mode full` EXIT=0 with games_selected=0, then `--mode refutation` EXIT=0 with games_selected=0. 76
  base-stamped games still lack the refutation stamp: they have zero flaws, so the selector skips them.
- Coverage (D-11 SQL verbatim, 11-10 ~13:40 UTC): denom 2,301,338, scored 2,297,262, **pct_scored 99.823** (bar 99.000,
  pass). NULL buckets: terminal without pv 1,786 (0.078%), non-terminal with no best_move or pv 1,410 (0.061%, which
  the SQL leaves unbucketed, so it is split by hand), no rating 860 (0.037%), null_other 17 (invalid_root), unstamped 3
  (in flight). All structural buckets are at or below the D-21 probe.
- 247-07: finished in the same pass (99.570% coverage, see 247-07-SUMMARY.md).
- Health: game_flaws 13 GB, 237k dead of 7.65M live; games 4.3 GB, 158k dead of 1.11M live. Autovacuum current.
- Report: `reports/maia-flaws-backfill/prod-refutation-coverage.md` (Slice, Full run, Catch-up, Coverage, Health) plus
  all shard JSONs.
