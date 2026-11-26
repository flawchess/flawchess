---
phase: 248-blunder-check-refutation-stats-and-calibration-seed-261108-d
plan: 04
subsystem: scripts/blunder-check-calibration
tags: [calibration, read-only, sampler, report, findability, hazard-model, SEED-261108-dk0]
status: complete
requires: ["248-01", "248-02"]
provides:
  - "scripts/blunder_check/sample.py: read-only engine, deterministic md5-residue sample, batch loader, per-game/per-blunder records, exact per-user aggregates, JSON cache"
  - "scripts/blunder_check/render.py: markdown sections of the calibration report (How to read, Sample, Control, Cases, Findability grid, Eval band, Window fit, Herring supply, Supply per user, Provenance)"
  - "scripts/blunder_check_calibration.py: CLI (--db dev|prod, sampling, thresholds, --cache/--from-cache, --out-dir, --date, --overwrite)"
affects: [248-05, 248-08]
requirements-completed: [D-13, D-14, D-15, D-16, D-23]
key-files:
  created:
    - scripts/blunder_check/sample.py
    - scripts/blunder_check/render.py
    - scripts/blunder_check_calibration.py
    - tests/scripts/test_blunder_check_calibration.py
  modified: []
decisions:
  - "Guest games are loaded (GameRecord.is_guest) but excluded from every report section except the sample counts, because guest flaws are never Maia-scored and would read as NULL pairs"
  - "Mixed blunders use R = X' = t on one grid in the findability table; allowed varies R, pure miss varies X'"
  - "Per-user supply: usable blunder window rate per user-side blunder (findable, in band, split pure/non-pure), fit share hazard-weighted over usable blunders; herring windows per user = games x L-uniform herring windows per game of the bucket"
  - "Unrated games keep a GameRecord (bucket None) but produce no BlunderRecord; they are counted"
  - "Aggregates and cache for the CLI are one read-only session; the cache holds user ids (gitignored temp/) but the rendered report never does"
metrics:
  completed: "2026-11-09"
commits: 2
plan_head_before: 934952a2edb70e651b21490a0e517cb3158fd96c
plan_head_after: a03fa1f8f3eb991a6ebcdea62715e646191963df
actuals:
  tokens: 20500
  tasks: 2
  commits: 2
---

# Phase 248 Plan 04: Blunder-check calibration sampler and report Summary

**A read-only, deterministic calibration run that turns per-ply evals into the D-13..D-16 and D-23 report sections through the flaw classifier's own expected-score pass, renderable byte-identically from a JSON cache.**

## What was built

- `sample.py`: `make_readonly_engine` (asyncpg `server_settings`: `default_transaction_read_only=on`, `statement_timeout`=30 min, pool of one); `select_sample_game_ids` (fully evaluated games on chess.com/lichess, md5 residue mod 1000 below `--sample-permille`, reusing `SHARD_RESIDUE_SQL`); three short SELECTs per 500-game batch; `build_game_records` (skips and counts ply-gap games, `_run_all_moves_pass` for severities and ES, `pinned_elo_for_mover` for the bucket, `mover_is_white_at_ply` for user parity, `blunder_es`/`miss_case`/`flaw_control` from plan 02); `fetch_user_groups` (exact per-user game and user-side blunder counts per provenance/platform/TC/50-point rating group, non-guest only, `~is_opponent_expr`); `write_cache`/`read_cache`.
- `render.py`: ten report sections plus pure helpers (`usable_blunders`, `fit_shares`, `bucket_rates`, `user_supply`, `percentile`). All shares print their n. The "How to read" section states population, sampling, ES convention, case meanings, and that the constants are a recommendation only.
- CLI: refuses to overwrite a same-day report without `--overwrite`, exit 5 when nothing is collected, banner prints database name and server address only.

## Tracer gate

Tracer (`type=tracer`) verified end to end (tests green, dev run wrote the report with Control and Cases sections) before expansion; `HUMAN_VERIFY_MODE` end-of-phase with automated-only verify, so no checkpoint.

## Dev results (smoke only; dev is not the calibration population)

Dev DB (head `c4e9b1d7f248`): 9756 fully evaluated chess.com/lichess games.

- **D-13 control:** first 500 games 3167 / 3167 = 100.0%; full dev sample (9731 games, 25 skipped for a ply gap) 60140 / 60142 = 99.997%. Well above the 99% bar, so no convention problem and nothing to explain before plan 05.
- **Cache round trip:** `--from-cache` output `diff`s identical to the DB run, on the 500-game and the full-dev reports.
- **Coverage on dev:** the refutation pair is mostly NULL (no dev backfill ran): 255 allowed and 58 pure-miss blunders scored in the full sample, so the 500-game report shows only unscored counts. Where scored (1200-1599, n=204 allowed): 75.5% pass at R=0.20, 65.2% via rank 1 alone. These numbers are not calibration evidence; plan 08 reads prod.
- Dev reports and caches are under the gitignored `temp/blunder-check/` (`blunder-check-calibration-2026-11-09.md`, `dev-cache.json`, `full/`, `from-cache/`).
- Full dev run took about 20 s (16 s collection) at 100% of dev, so the 2.5% default on prod is cheap on CPU; the prod cost is the aggregate scans, bounded by the 30-minute statement timeout.

## Mutation proofs (each applied, test failed, then restored; suite back to 19 passed)

| Mutation | Failing test |
| --- | --- |
| (a) window-fit wiring passes band (0.0, 1.0) instead of the chosen band for the preceding moves (the plan's required proof) | `TestWindowFit::test_out_of_band_preceding_move_blocks_longer_positions` |
| (b) per-user blunder aggregate counts both sides (`is_opponent_expr \| ~is_opponent_expr`) | `TestUserGroupAggregates::test_exact_counts_for_non_guest_users_only` |
| (c) non-guest predicate in the aggregates replaced by a tautology | same test |

## Verification

- `uv run pytest tests/scripts/test_blunder_check_calibration.py tests/scripts/test_blunder_check_metrics.py`: 50 passed. `uv run pytest -n auto -x`: 5853 passed, 20 skipped.
- `ruff format`/`ruff check` on own files clean; `uv run ty check app/ tests/ scripts/`: All checks passed; `check_function_size.py scripts/blunder_check scripts/blunder_check_calibration.py --fail-over-depth 4`: no breaches.
- Acceptance greps on the dev report: `## Control`, `## Cases by Elo bucket`, `## Findability grid`, `## Eval band`, `## Window fit`, `## Herring supply`, `## Supply per user`, `## Provenance` each appear once; `default_transaction_read_only` appears in `sample.py`.

## Deviations from Plan

None to the deliverables. Notes:

- The cache functions, `Collection` and `UserGroup` landed in the Task 1 commit (the CLI's `--cache`/`--from-cache` flags are specified in Task 1); the per-user aggregates (`fetch_user_groups`, `group_elo_bucket`) and all Task 2 sections landed in the Task 2 commit.
- `commits: 2` is this plan's own count; the `rev-list` range from `plan_head_before` also contains plan 248-03's commits (concurrent executor in the same worktree).
- `actuals.tokens` is chars/4 over the four files changed (82,183 chars).

## Known Stubs

None. (Dev `NULL` pairs are real unscored data, reported as such.)

## Threat Flags

None new. T-248-08 mitigated and tested (read-only `SHOW` returns `on`, an `UPDATE` raises `DBAPIError`; the script has no write statement). T-248-09 mitigated (pool of one, 500-game batches, named 30-minute timeout, 2.5% default). T-248-10 mitigated: the rendered report holds aggregates only; the user ids needed for per-user percentiles live only in the gitignored cache.

## Notes for plan 05 and plan 08

- Plan 08 runs `--db prod` only after both backfills finish (CLAUDE.md prod runbook, tunnel `bin/prod_db_tunnel.sh`), writes to `reports/blunder-check/`, and should pass `--cache` so the report can be re-rendered with other thresholds without hitting prod again.
- The per-user supply is an estimate by design (rating-group midpoint approximates the exact per-game Elo); on dev the "Supply per user" usable-window percentiles read 0 for the 500-game report because no sampled pair was scored.

## Self-Check: PASSED

- Files exist: `scripts/blunder_check/sample.py`, `scripts/blunder_check/render.py`, `scripts/blunder_check_calibration.py`, `tests/scripts/test_blunder_check_calibration.py`, dev report and cache under `temp/blunder-check/`.
- Commits `1b70dc4ef` and `a03fa1f8f` are ancestors of HEAD on the phase branch.
