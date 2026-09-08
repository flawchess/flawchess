# FlawChess Benchmark Lane Report — rapid — 2026-09-08

- **Tranche**: rapid
- **Snapshot taken**: 2026-09-08T15:43:55Z

## Tranche progress

Exact `COUNT(*)` aggregates, `benchmark_selection` joined to the `games` completion columns, split by `lichess_arm`.

| Arm | Selected | full_evals_done | full_pv_done | best_moves_done | blobs_done |
|---|---|---|---|---|---|
| lichess_arm | 34,777 | 34,777 | 34,777 | 34,777 | 34,777 |
| never_analyzed_arm | 60,846 | 60,759 | 60,759 | 60,759 | 60,759 |

- **benchmark_lichess_eval_snapshot rows (lichess arm only)**: 2,599,458
- **Percent complete (best_moves_done / selected)**: 99.9%

## Downstream row counts (SC6)

Each row is an exact `COUNT(*)` scoped to this tranche via a join through `benchmark_selection` -- never a `pg_class.reltuples` estimate.

| Metric | Count |
|---|---|
| `game_positions` rows with non-NULL `best_move` | 6,498,862 |
| `game_positions` rows with non-NULL `pv` | 1,062,524 |
| `game_flaws` rows | 634,118 |
| `game_best_moves` rows | 789,428 |

## Provenance

Every row above is scoped to this tranche via `benchmark_selection`. `benchmark_selection.lichess_arm` is the split key for eval provenance: rows with `lichess_arm IS TRUE` were re-evaluated by our Stockfish despite having lichess evals at import time (`BENCHMARK_HOMOGENIZE_EVAL_SOURCE`, D-03); a game with no `benchmark_selection` row at all remains untouched, lichess-classified data. See `.claude/skills/benchmarks/SKILL.md` § 5 "Mixed eval provenance in `game_flaws`" for the full disclosure (D-06).
