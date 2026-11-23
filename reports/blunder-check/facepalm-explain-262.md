# Phase 262: index-only check of the facepalm readers under the type-rule gate

Date: 2026-11-23, before the Phase 262 release. Database: prod, read-only, one connection, JIT off
(as the readers run). Account: user 95, the largest one (40,165 games in the default filter, 2,130
analyzed games in the recent window). The line-repair feed (`repair_short_lines.py feed`) was running
on prod at the same time, with the owner's go-ahead.

## What was measured

The two statements the facepalm readers send, captured from the real reader functions with the
default library filters (platform chess.com and lichess, human opponents) and the Phase 262
candidate constants in the working tree (type-rule gate, 262 D-04), rendered with literal binds and
run three times each under `EXPLAIN (ANALYZE, BUFFERS)`. Helper: the gitignored
`temp/facepalm-262/gen_explain_sql.py --db prod --user-id 95`.

| Statement | Reader | SQL size |
|---|---|---|
| counts | `library_repository.fetch_facepalm_counts` (Flaws Timeline band) | 1,364 bytes |
| comparison | `library_repository.fetch_facepalm_comparison` (Facepalm blunders card, recent window) | 23,623 bytes |

The comparison statement is larger than in the Phase 259 measure (4,352 bytes) because it now carries
the recent window's analyzed game ids as a literal list (Phase 258).

## Timings (execution time, ms)

| Statement | run 0 | run 1 | run 2 | planning |
|---|---|---|---|---|
| counts | 195.2 | 178.9 | 171.7 | 0.6 to 0.7 |
| comparison | 17.6 | 17.7 | 17.6 | 2.8 to 2.9 |

Phase 259 measured 188.4 ms (counts) with JIT off on the same account, so the new gate costs nothing
measurable.

## The game_flaws scan node

| Statement | Node |
|---|---|
| counts | `Index Only Scan using ix_game_flaws_facepalm_inputs on game_flaws (actual rows=1.98 loops=40165)` |
| comparison | `Index Only Scan using ix_game_flaws_facepalm_inputs on game_flaws (actual rows=3.44 loops=2130)` |

## Verdict

Both readers read `game_flaws` index-only through `ix_game_flaws_facepalm_inputs` under the new gate.
The gate reads `material_missed` and `maia_best_prob`, both already in the index, so no index rebuild
is needed (RESEARCH Finding 6). The same check on dev (user 28) gave the same node for both statements.
