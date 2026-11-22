# D-18: JIT re-measure on the scalar facepalm expression

Date: 2026-11-22, a few minutes after the switch release went live (server `8e90f094`, schema
`e2f6a8b0d259`). Database: prod, read-only, one connection. Account: user 95, the largest one
(about 165,000 blunders, 40,079 fully evaluated games in the default filter).

## What was measured

The two statements the facepalm readers run, compiled from the switched code on main with the
default filters (platform chess.com and lichess, human opponents) and literal binds:

| Statement | Reader | SQL size |
|---|---|---|
| counts | `library_repository.fetch_facepalm_counts` (Flaws Timeline band) | 1,290 bytes |
| comparison | `library_repository.fetch_facepalm_comparison` (Facepalm blunders card) | 4,352 bytes |

Phase 257 measured a 34 KB expression; the scalar expression is far smaller, which is why the
question is open again. Each statement ran under `EXPLAIN (ANALYZE, BUFFERS)` four times with
`SET jit = off`, then four times with `SET jit = on`. Run 0 is the first run of its setting, runs
1 to 3 are the warm ones.

## Timings (execution time, ms)

| Statement | jit | run 0 | run 1 | run 2 | run 3 | warm median | planning (warm) |
|---|---|---|---|---|---|---|---|
| counts | off | 3390.5 | 266.7 | 179.8 | 188.4 | 188.4 | 0.5 |
| counts | on | 203.1 | 195.6 | 191.0 | 204.8 | 195.6 | 0.6 |
| comparison | off | 271.8 | 257.1 | 253.1 | 249.0 | 253.1 | 0.7 |
| comparison | on | 277.3 | 294.2 | 267.9 | 287.2 | 287.2 | 0.7 |

The 3.4 s first run of counts with jit off is the cold cache (it was the very first statement of
the session), not a JIT effect.

JIT block when on (no inlining, no optimization: the plans stay under those cost thresholds):

| Statement | Functions | Generation | Inlining | Optimization | Emission | Total |
|---|---|---|---|---|---|---|
| counts | 35 | 4.2 to 4.4 ms | 0 | 1.4 ms | 28.2 to 30.1 ms | 33.9 to 35.7 ms |
| comparison | 34 | 9.2 to 10.0 ms | 0 | 3.2 to 3.5 ms | 55.6 to 57.3 ms | 68.4 to 70.4 ms |

## Scan nodes

Both statements, with JIT on and off, read `game_flaws` through
`Index Only Scan using ix_game_flaws_facepalm_inputs` (D-17), driven by a bitmap scan of the
user's games (`ix_games_user_played_at` for counts, `ix_games_user_full_evals` for comparison).

`Heap Fetches: 90021` on the index-only scan: the index was built an hour before and many
`game_flaws` pages are not yet marked all-visible after the backfill's updates, so the scan still
visits the heap for those rows. Autovacuum will bring this down; the timings above include it.

## Decision

Rule (D-18): remove `disable_jit_for_transaction` only if, for both statements, the JIT-on warm
median is at most 1.05 times the JIT-off warm median.

| Statement | on / off warm median | Within 1.05 |
|---|---|---|
| counts | 195.6 / 188.4 = 1.04 | yes |
| comparison | 287.2 / 253.1 = 1.13 | no |

decision: keep

JIT costs about 35 ms on the comparison statement and buys nothing, so the readers keep turning
it off. The cost is now tens of milliseconds, not the seconds Phase 257 measured.

Raw plans: `temp/facepalm-259/plan_*_95_jit*_*.txt` (gitignored).
