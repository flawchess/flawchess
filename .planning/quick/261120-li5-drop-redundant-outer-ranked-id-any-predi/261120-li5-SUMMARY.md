---
quick_id: 261120-li5
status: complete
completed: 2026-11-20
commit: d06c5847b
branch: main (squash of quick/ranked-stats-redundant-any)
files_modified:
  - app/repositories/endgame_repository.py
  - tests/test_endgame_repository.py
  - CHANGELOG.md
---

# Quick 261120-li5 summary: redundant outer ranked-id `ANY` in endgame queries

## What changed

- `app/repositories/endgame_repository.py`: `apply_game_filters(..., game_ids=None)` in
  `query_endgame_entry_rows`, `query_endgame_bucket_rows`, `query_clock_stats_rows` and the
  endgame (`IN` subquery) half of `query_endgame_performance_rows`. The ranked-id restriction
  now lives only inside the grouped `game_positions` aggregation. The non-endgame (`NOT IN`)
  half keeps the outer predicate, because there it is the only ranked-id restriction. Each
  fix site is commented with the cause, the measurement and a "do not add back" note.
- `tests/test_endgame_repository.py`: `TestRankedGameIdsRestriction`:
  - behavioural: games A (endgame, ranked), B (endgame, unranked), C (no endgame, ranked),
    D (neither); every query returns only the ranked games.
  - shape pin: captures executed SQL; `games.id = ANY` must be absent everywhere except the
    `NOT IN` half. **Fails with the fix reverted** (checked by stashing the repository change),
    passes with it. The behavioural test passes either way, as it should (results unchanged).
- `CHANGELOG.md`: Fixed bullet under `[Unreleased]`.

## Root cause

With the outer `games.id = ANY(:ids)` present, the planner multiplied `user_id` x `ANY` x
platform selectivities into a 1-row estimate for `games`, chose a nested loop with `games`
outer, and re-executed the whole grouped aggregate once per ranked game. Prod EXPLAIN ANALYZE,
user 1388, 1,435 literal ids, clock-stats shape:

| | time | shared buffers | aggregate loops |
|---|---|---|---|
| before | 14,510 ms | 6,564,533 | 1,435 |
| outer predicate removed | 30 ms | 8,908 | 1 |

It hit mid-size users whose statistics produced the 1-row estimate, which is why the endpoint
was bimodal (Sentry 30 d: p50 531 ms, p95 82 s, max 110.6 s).

## Verification

- `ruff format` / `ruff check` / `ty check` on both files: clean.
- Full backend suite in the worktree: 7,112 passed, 28 skipped. The one collection error
  (`tests/scripts/test_fit_facepalm.py`, no numpy) is the fresh-worktree dependency group; after
  `uv sync --group maia-inference` it passes (70 passed).
- Prod timing probe (read-only, this branch's code against prod data, `fetch_ranked_inputs`
  end to end):

| user | ranked ids | before | after |
|---|---|---|---|
| 1388 | 1,435 | 25,260 ms (clock query 19.5 s) | 907 ms |
| 1521 | 1,151 | 15,125 ms (clock query 11.0 s) | 467 ms |
| 11 | 2,852 | 4,728 ms | 1,009 ms |
| 288 | 2,342 | 3,682 ms | 953 ms |
| 95 | 2,014 | not captured | 891 ms |

After the fix, every endgame query is 35-216 ms for every user tested. The "after" runs had a
warmer cache than the first "before" runs, but the same-cache EXPLAIN pair above (14.5 s vs
30 ms) isolates the plan change.

## Not done

- Merged to `main` as squash commit `d06c5847b` after the full pre-merge gate passed (backend 7,200 passed; frontend lint, build, 6,634 tests, knip). Not yet deployed.
- Remaining per-request time (~0.5-1 s) is dominated by the endgame/non-endgame performance
  rows and the `recent_capped` slice fetch, not by the plan pathology. No further change proposed.
