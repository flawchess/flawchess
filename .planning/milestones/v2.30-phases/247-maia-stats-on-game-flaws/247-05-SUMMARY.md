---
phase: 247-maia-stats-on-game-flaws
plan: 05
subsystem: maia-flaw-backfill
tags: [maia, backfill, sharding, multiprocessing, checkpoint]
requires: ["247-01", "247-02"]
provides:
  - "scripts/backfill_maia_flaws.py: sharded multi-process stamp-checkpointed Maia flaw backfill with --status"
affects: [247-06, 247-07]
status: complete
commits: 3
plan_head_before: b80cf5bb1303ce739728bbb6d48416583be6f6e5
plan_head_after: fed1bb4f32b7028be4cbe4b1168c0bf1e97de99f
actuals:
  tokens: 12400
  tasks: 3
  commits: 3
tech-stack:
  added: []
  patterns:
    - "md5 hash-residue shards (never rank windows), spawn-context shard processes, one single-threaded ORT session and a one-connection pool each"
    - "stamp as checkpoint: selector is games.maia_flaws_completed_at IS NULL, write is require_unstamped=True"
key-files:
  created:
    - scripts/backfill_maia_flaws.py
    - tests/scripts/test_backfill_maia_flaws.py
  modified:
    - docs/dev-tooling.md
key-decisions:
  - "Batch write failure retries each game in its own transaction; a batch with any per-game failure counts toward MAX_CONSECUTIVE_BATCH_FAILURES (5), which ends the shard with EXIT_SHARD_FAILED"
  - "flaws_scored counts flaw rows that received Maia values; all-NULL rows are flaws_null and their MaiaReason lands in reasons (only for games actually stamped, or would-be in a dry run, so skipped games never double count)"
  - "Parent SIGTERM/SIGINT forwards terminate() to the shard children and keeps joining, so the combined total line still prints"
  - "Score-time exceptions other than MaiaInferenceUnavailableError are Sentry-captured per game (games_score_failed) and leave the game unstamped; MaiaInferenceUnavailableError aborts the shard with EXIT_MAIA_UNAVAILABLE"
requirements-completed: [D-06, D-10, D-11, D-13, D-16]
---

# Phase 247 Plan 05: Maia flaw backfill script Summary

`scripts/backfill_maia_flaws.py --db {dev,benchmark,prod}` selects unstamped games with flaws by md5 shard in user-activity/recency order, scores them from PGN-replayed boards through the shared scorer, stamps each game in the same transaction as its eight-column write, and is idempotent on re-run (the stamp is the checkpoint).

## Accomplishments

- Selector (verbatim from the plan truths): `games JOIN users WHERE maia_flaws_completed_at IS NULL AND EXISTS (game_flaws) AND md5-residue % num_shards = shard [AND user_id]`, ordered `u.last_activity DESC NULLS LAST, g.played_at DESC NULLS LAST, g.id DESC`. Bound parameters only. Zero-flaw games are never selected.
- `run_shard`: own engine (`pool_size=1`) via `db_url_for_target`, id snapshot at shard start, per batch short read session, `score_game(inputs, None)` (PGN replay, D-06), one write session with `require_unstamped=True`, per-batch progress line with `flush=True`, throttle, graceful stop after the current batch, JSON report in a `finally`.
- CLI: `--db` restricted to dev/benchmark/prod (D-16), `--workers`, `--num-shards`, `--shard` (in-process), `--user-id`, `--limit`, `--batch-games` (capped at 50), `--throttle-ms`, `--dry-run`, `--report-dir`, `--status` (four SELECT-only counts). Target banner prints `current_database / inet_server_addr:port`, never the URL.
- `_shard_process_entry` starts Maia with `intra_op_num_threads=1`, returns `EXIT_MAIA_UNAVAILABLE` (3) without opening a session when Maia is absent; the parent spawns one process per shard (spawn context), joins, and prints one combined `total:` line.
- `docs/dev-tooling.md` inventory bullet added.

## Tests (`tests/scripts/test_backfill_maia_flaws.py`, 10 tests, test user 247_001)

Tracer plus: shard partition disjoint/exhaustive (12 games, 3 shards), rerun selects nothing and changes nothing, mid-run stamped game reported `already_stamped` and not overwritten, corrupted `game_flaws.fen` counted as `fen_mismatch` with the game still stamped, dry run writes nothing, `--db` choices (test rejected), `db_url_for_target("benchmark")` delegation through a real engine build, shard exits `EXIT_MAIA_UNAVAILABLE` without running, status counts (function and the printed CLI line).

## Mutation proofs

- `require_unstamped=True` -> `False` in `run_shard`: `test_rerun_skips_game_stamped_mid_run` failed (9 passed, 1 failed). Restored.
- `maia_flaws_completed_at IS NULL` predicate dropped from the selector: `test_rerun_selects_nothing_and_changes_nothing` failed (`games_selected == 3`, expected 0). Restored: 10 passed.

## Dev smokes (Task 3)

- Single process, `--db dev --workers 1 --user-id 28 --limit 200`: exit 0 (via the `total:` line and report; the shell `PIPESTATUS` check was lost to zsh), games_stamped=200, flaws_scored=1342, flaws_null=0, 12.9 flaws/s sustained, wall 1:46. Reasons: best_missing=428, second_missing=544, second_equals_best=5 (dev `game_positions.best_move` is sparsely populated for user 28).
- `--status --db dev --user-id 28`: `stamped_games=200 unstamped_games_with_flaws=2680 flaws_with_maia=1342 flaws_total=18639`, exit 0.
- Multi-process, `--workers 3 --user-id 28 --limit 20`: exit 0, three shard reports sharing run_stamp `20261108T195449Z`, 60 games stamped, 356 flaws scored, 11.8 to 12.1 flaws/s per shard, wall 14.0 s (3 processes at 253% CPU).
- Measured ~77 ms per position (1 / 12.9 flaws/s, includes DB and replay), matching plan 01's 80.5 ms ORT figure. Plan 07 sizing input: 7.6M flaws at ~13 flaws/s/process is ~162 CPU-hours, ~18 h wall at 9 processes (before any CPU contention).
- Reports and logs are in the gitignored `temp/maia-flaws-backfill/`.
- Side effect: 260 dev games of user 28 are now stamped with Maia values (expected for the smoke).

## Verification

- `uv run pytest -n auto -q`: 5761 passed, 20 skipped.
- `uv run ty check app/ tests/ scripts/`: All checks passed. `ruff format --check` and `ruff check` clean. `check_function_size.py app/ --fail-over-depth 4`: no breaches.

## Deviations from Plan

### Not done (orchestrator constraint)

**1. Benchmark dry-run and `bin/benchmark_db.sh start` skipped.** The plan's Task 3 step 3 and acceptance criterion require a `--db benchmark --dry-run` smoke, but the dispatch for this run forbids connecting to the benchmark DB ("dev DB only"). The benchmark path is covered at unit level (`test_resolve_url_delegates_to_db_url_for_target` builds a real engine through `db_url_for_target("benchmark")`; `test_dry_run_writes_nothing`), but the real D-10 smoke against the local benchmark DB (exit 0, flaws_scored > 0, games_stamped == 0) is still open. It needs `bin/benchmark_db.sh start` (applies the 247 migration to the benchmark DB) and then `PYTHONUNBUFFERED=1 uv run python scripts/backfill_maia_flaws.py --db benchmark --workers 1 --limit 50 --dry-run --report-dir temp/maia-flaws-backfill`. The orchestrator or owner should run it.

### Additions

- `ShardReport` gained `games_score_failed`, `flaws_null` and `aborted_reason` beyond the planned field list (needed to distinguish score-time failures, all-NULL rows and abort causes).
- `fetch_status` extracted as a separate function so the status counts are testable without the CLI.

Otherwise the plan was executed as written.

## Known Stubs

None.

## Threat Flags

None. T-247-09 (bound parameters only), T-247-10 (URL never printed, banner shows database/addr/port, reports hold counters only), T-247-11 (pool_size=1, batches capped at 50 games, `--throttle-ms`, graceful SIGTERM) are implemented as planned.

## Self-Check: PASSED

scripts/backfill_maia_flaws.py, tests/scripts/test_backfill_maia_flaws.py and docs/dev-tooling.md verified present; commits 7d68ee1ed, 619bf49d3, fed1bb4f3 verified on the branch.
