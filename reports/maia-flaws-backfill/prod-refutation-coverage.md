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

## Catch-up

Both runs ran after the full run, 2026-11-10 ~13:31 UTC, `--workers 9`:

- `--mode full` (`prod-catchup-full.log`, run_stamp `20261110T133134Z`): EXIT=0, games_selected=0
- `--mode refutation` (`prod-catchup-refutation.log`, run_stamp `20261110T133202Z`): EXIT=0, games_selected=0

The live lanes kept every newly scored game current during the 8 h run. 76 games remain base-stamped without the
refutation stamp. All 76 have zero `game_flaws` rows today (stamped 11-09 before the deploy, flaws removed since), so the
selector's `EXISTS (game_flaws)` skips them and they have nothing to score.

## Coverage

D-11 coverage SQL (248-RESEARCH, verbatim) on prod via MCP, 2026-11-10 ~13:40 UTC:

| denom | scored | pct_scored | null_unstamped | null_no_rating | null_terminal_no_pv | null_pv_pending | null_other |
|---|---|---|---|---|---|---|---|
| 2,301,338 | 2,297,262 | **99.823** | 3 | 860 | 1,786 | 0 | 17 |

Pass (D-11 bar 99.000). NULLs total 4,076 (0.177%), largest first:

| Bucket | Rows | Share of denom | D-21 probe | Explanation |
|---|---|---|---|---|
| Terminal ply+1 with neither best_move nor pv | 1,786 | 0.078% | ~0.07% | Blunder on the last move or into a finished position (1,741 lichess, 34 engine, 11 with no ply+1 row) |
| Non-terminal ply+1, best_move and pv NULL, PV pass done | 1,410 | 0.061% | ~0.07% | Not in a named SQL bucket (falls between null_pv_pending and null_other), so split here: 972 engine games, 438 lichess games. Shard reason `refutation_missing` |
| Mover rating NULL | 860 | 0.037% | ~0.05% | Shard reason `no_rating` (860, exact match) |
| null_other (best_move or pv present) | 17 | 0.001% | n/a | Shard reason `invalid_root` (17, exact match) |
| Unstamped | 3 | 0.000% | n/a | Games stamped by neither the backfill nor yet the live lane at query time (in flight) |

Reconciliation with the summed shard reasons (full run plus slice): refutation_missing 2,923 + no_legal_reply 260 +
ply_beyond_mainline 11 = 3,194 against the two structural buckets 1,786 + 1,410 = 3,196 (the gap of 2 comes from
live-lane scoring). `no_legal_reply` (checkmate after the blunder, so no reply exists) lands in the terminal
bucket. refutations_from_pv = 13,240 (0.58% of scored values took the refutation from the pv fallback). All three
structural buckets sit at or below the D-21 probe estimates.

## Health

Read-only, 2026-11-10 ~13:40 UTC (no VACUUM, MCP role is read-only):

| Table | n_live_tup | n_dead_tup | last_autovacuum | last_autoanalyze | Total size |
|---|---|---|---|---|---|
| game_flaws | 7,653,589 | 237,178 | 12:21 | 11:35 | 13 GB |
| games | 1,112,665 | 158,374 | 11:06 | 12:49 | 4.3 GB |

Autovacuum keeps up during the run (dead tuples about 3% and 14% of live rows), so there is nothing to raise.
