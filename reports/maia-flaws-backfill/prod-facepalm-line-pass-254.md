# Prod facepalm line pass (Phase 254-11)

Date: 2026-11-15 (UTC). `scripts/backfill_maia_flaws.py --db prod --mode line`, run from the prod-run worktree
re-pointed to `origin/production` at `130978073` (contains the R2 squash `5d9075796` via release `9c22730c6`).

## Precondition: Phase 252 not awaited (D-21)

The plan's precondition (Phase 252's prod repair finished) was waived by the owner on 2026-11-15 (CONTEXT D-21).
The pass ran on the lines as stored. A blunder whose line does not reach depth 3 keeps a NULL material slot
(D-18): it is skipped, not guessed. After Phase 252's prod repair, one more line pass with a new cutoff fills the
remaining gaps. `252-06-SUMMARY.md` does not exist yet.

## Run

- Cutoff `T = 2026-11-15T19:34:08+00:00`.
- Client connections on prod before launch (19:33:55Z): 12 of 50.
- Status before: `line_done_since_cutoff=0 line_pending_games=1039836 user_blunders_total=2326317 user_blunders_with_score=1855076 user_blunders_qualifying=618439`.
- Slice (`--workers 1 --limit 50`): 50 games in about 1 s, `scores_set=66 scores_null=44`, no failure.
- Full pass: `--workers 4 --throttle-ms 50`, 19:35:43 to 20:46:00 UTC (70 min, about 250 games per second), exit 0.

```
total: games_selected=1039785 games_scored=1039785 games_stamped=1039780 games_already_stamped=2 games_fingerprint_changed=3 games_missing=0 games_write_failed=0 games_score_failed=0 flaws_scored=0 flaws_null=0 spreads_scored=0 spreads_null=0 scores_set=1950592 scores_null=375215 pre_scored=0 pre_null=0 reason_invalid_root=17 reason_ply_beyond_mainline=11
```

- Status after (20:47Z): `line_done_since_cutoff=1040264 line_pending_games=3 user_blunders_total=2326913 user_blunders_with_score=1951340 user_blunders_qualifying=627406`.

Scored blunders rose from 1,855,076 to 1,951,340 and qualifying ones from 618,439 to 627,406 (pre-refit constants):
lines that Phase 252's feeder and go-forward analysis had already repaired now reach depth 3.

## Coverage (user-side blunders, read-only query at 20:50Z)

| Fact | Rows | Share of 2,326,929 |
|---|---|---|
| played line material array present | 2,177,425 | 93.6% |
| played line reaches depth 3 | 1,952,230 | 83.9% |
| played line mates within 3 plies | 74,110 | 3.2% |
| played line unknown at depth 3 (no material, no mate): unscored | 374,699 | 16.1% |
| best line material array present | 1,947,722 | 83.7% |
| best line reaches depth 3 | 1,832,415 | 78.7% |
| best line mates within 3 plies | 28,825 | 1.2% |
| best line unknown at depth 3 (D-18: missed term 0) | 494,514 | 21.3% |

These gaps are what the post-252 gap-fill pass is for.
