---
quick_id: 260616-pjh
title: Stamp lichess_evals_at at import time
status: complete
date: 2026-06-16
commit: c635f3d4
---

# Quick Task 260616-pjh — Summary

## Problem

`games.lichess_evals_at` (the Lichess-eval provenance column) was introduced in
Phase 117 with **only** a one-time migration backfill
(`20260613_120000_phase_117_queue_pv.py`, condition `white_blunders IS NOT NULL`).
**No live import-path code ever set it.**

Consequence: any Lichess game imported *after* that migration — notably after a
delete + re-import — that arrived WITH Lichess computer analysis got
`lichess_evals_at = NULL`. That makes it match `needs_engine_full_evals`
(`full_evals_completed_at IS NULL AND lichess_evals_at IS NULL`), so our Stockfish
drain re-analyzes it from scratch despite it already carrying per-ply %evals.

Confirmed on prod after user 95's stress-test delete+reimport: **5,152** of their
19,705 Lichess games were in this state (per-ply `eval_cp` present on every
position, yet flagged `needs_engine_full_evals = TRUE`). It also leaves
`has_engine_full_evals = FALSE` for them, corrupting the Lichess-vs-engine
provenance split downstream logic relies on.

## Fix

`app/services/import_service.py`:

- New helper `_stamp_lichess_evals_at(session, new_game_ids)` ("Stage 5d"), called
  from `_flush_batch` right after the Stage 5c covered-games classify, inside the
  same caller-owned batch transaction (WR-05).
- Stamps `lichess_evals_at = NOW()` for newly imported games matching the
  migration's exact condition: `platform = 'lichess' AND white_blunders IS NOT NULL
  AND lichess_evals_at IS NULL`.
  - `platform = 'lichess'` future-proofs the case where engine-filled oracle counts
    eventually blur the `white_blunders` signal (Phase 117 note / CLAUDE.md); at
    import time `white_blunders` can only be Lichess-sourced (our engine has not run
    on a freshly imported game).
  - `lichess_evals_at IS NULL` keeps it idempotent on re-runs.
- **Implemented with the Table-level `bindparam("b_id")` executemany pattern, NOT
  `id.in_([...])`.** The first draft used `.in_(new_game_ids)`, which inlines game
  ids into the SQL text — caught by the existing
  `test_stage5_sql_text_invariant_across_batches` guard (FLAWCHESS-56 / Phase 90:
  per-batch SQL text regrows SQLAlchemy's compile cache + asyncpg's prepared-stmt
  LRU and OOM-killed prod). The bindparam form keeps the compiled text invariant.

No Alembic migration (column already exists; this is a live-write-path fix only).

## Tests

`tests/test_import_service.py::TestStampLichessEvalsAtRealDb` (DB-backed, real
per-run Postgres session):

- `test_stamps_only_lichess_analyzed_games` — Lichess+analyzed stamped (incl.
  `white_blunders=0`, the falsy-but-not-NULL case); Lichess-unanalyzed and
  chess.com left NULL.
- `test_does_not_overwrite_existing_timestamp` — idempotent (preset timestamp
  preserved).
- `test_empty_ids_is_noop` — empty batch issues no UPDATE.

## Verification

- `uv run ruff format` / `ruff check` — clean.
- `uv run ty check app/ tests/` — zero errors.
- `tests/test_import_service.py` — 64 passed (incl. 3 new + the SQL-invariant guard).
- Full backend suite **serial** (CI-equivalent, D-02): the 4 flaked files +
  import file → 111 passed.

## Notes / out of scope

- **Pre-existing xdist flakiness observed**: under `pytest -n auto` the full suite
  showed 2–3 *different* stats-repository / stats-service tests failing with an
  asyncpg `ProgrammingError` on each run (non-deterministic, different tests each
  time, none touching import code; all pass in isolation and serially). Not caused
  by this change. Worth a separate look if it persists, but out of scope here.
- This fix only affects **newly imported** games. The ~5,152 already-misflagged
  Lichess games on prod (and any other users in the same state) still have
  `lichess_evals_at = NULL` — a one-time backfill UPDATE on prod would correct them
  and reclaim the wasted engine queueing. Flagged to the user; not run as part of
  this task.
