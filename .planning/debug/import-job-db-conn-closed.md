---
slug: import-job-db-conn-closed
status: diagnosed
trigger: |
  Two prod Sentry errors causing user 94's import jobs to fail or get stuck in_progress:
  - FLAWCHESS-56 (issue 120262007): InterfaceError: cannot call PreparedStatement.fetch(): the underlying connection is closed — at import_service.py:798 in _apply_eval_results
  - FLAWCHESS-3Q (issue 115610288): CannotConnectNowError: the database system is not yet accepting connections — at import_service.py:398 in run_import while recording failure state
created: 2026-05-16
updated: 2026-05-16
---

# Debug Session: import-job-db-conn-closed

## Symptoms

- **Expected behavior:** User 94's chess.com game import completes successfully; on transient DB failure the import job is reliably marked `failed` (not left stuck `in_progress`).
- **Actual behavior:** Import jobs for user 94 are either `failed` or stuck `in_progress`. The DB connection dies mid-import, and the failure-state-recording code path also fails because the DB is still unavailable.
- **Error messages:**
  - FLAWCHESS-56: `InterfaceError ... cannot call PreparedStatement.fetch(): the underlying connection is closed` — eval UPDATE at `import_service.py:798` in `_apply_eval_results`.
  - FLAWCHESS-3Q: `CannotConnectNowError: the database system is not yet accepting connections` — `import_service.py:398` recording failure state.
- **Timeline:** Both events 2026-05-16T06:22:04–06Z, same trace_id, server dbe6bf8ac81c.
- **Reproduction:** Triggered by user 94 running game import(s), correlated with a Postgres OOM-kill / crash-recovery restart mid-import.

## Key context

- CLAUDE.md: prod Postgres OOM-killed during large import 2026-03-22; swap added, `_BATCH_SIZE` reduced 50→10. This is a recurrence with an incomplete/regressed mitigation.

## Current Focus

- hypothesis: CORRECTED (2026-05-16, prod experiment) — the OOM is driven by a **real unbounded memory leak in the Python import-worker process**, ~0.48 MB per game imported, linear from game 1. A **single import OOMs prod on its own** (~10 GB for a 20k-game account). The previously-recorded root cause (concurrent-duplicate pair + Phase 41.1 batch/eval regression as the necessary trigger) is **disproven** — concurrency was at most a 2x amplifier, never a prerequisite. The leak is NOT in the Stockfish pool and NOT in `_restart_worker` (engine count pinned at pool size = 4, RSS flat at 1241 MB across 43 samples through deep memory pressure). It is NOT the SQLAlchemy ORM identity map (insert path is Core `pg_insert(...).values()`, read path is column-only `select(Game.id, Game.platform_game_id)` — neither populates the identity map).
- next_action: implement fix (code change — should be scoped as a GSD phase). Diagnosis complete.
- test: DONE — local tracemalloc harness, real PGN batches through `_flush_batch` on one long-lived `AsyncSession`, no engine pool. CONFIRMED the hypothesis.
- result: b5→b10 RSS 104→169 MB (~13 MB/batch ≈ ~465 KB/game, matching prod's 0.48 MB/game). Dominant *growing* Python frames: `sqlalchemy/sql/compiler.py:1770` (+1947 KB / +6 large objects, SQL compilation) and `asyncpg/connection.py:481` (+925 KB / +20, per-connection prepared-statement cache). Confirms per-batch unique SQL text being compiled+prepared+cached unbounded on the import-lifetime connection. The growing import also slows progressively (cache lookup/prepare cost) — the tracemalloc run timed out at 600 s having reached only b10.
- reasoning_checkpoint: (n/a)
- tdd_checkpoint: (n/a)

## Evidence

- timestamp: 2026-05-16 — Both Sentry issues share trace_id 565fae5f21414e77964f828e216036d4, server dbe6bf8ac81c, within 2s. FLAWCHESS-56 = connection closed mid-eval-UPDATE; FLAWCHESS-3Q = DB not accepting connections when recording failure.
- timestamp: 2026-05-16 — Prod `import_jobs` for user 94 shows TWO concurrent chess.com jobs started 2s apart: `27764c56` (started 05:55:18, status=failed, InterfaceError, 8901 imported) and `cc9bcef0` (started 05:55:16, status=in_progress STUCK, completed_at=NULL, 9212 imported). Two simultaneous imports for the same user doubled import-side memory.
- timestamp: 2026-05-16 — Prod Postgres container logs: `06:22:01 client backend (PID 1154281) was terminated by signal 9: Killed` → `terminating any other active server processes` → `06:22:02 database system was not properly shut down; automatic recovery in progress` → `06:22:04 FATAL: the database system is not yet accepting connections` (= exactly FLAWCHESS-3Q).
- timestamp: 2026-05-16 — Host dmesg: `[Sat May 16 06:22:09] stockfish invoked oom-killer ... Out of memory: Killed process 253640 (postgres) total-vm:3140296kB anon-rss:507420kB shmem-rss:448396kB`. The OOM killer was invoked by a STOCKFISH allocation; Postgres was the chosen victim. Prod box: 7.6GB RAM, only 2GB swap.
- timestamp: 2026-05-16 — Memory-pressure regression: `_BATCH_SIZE` reduced 50→10 on 2026-03-22 (commit f3b36b7e, OOM mitigation) was raised back to **28** on 2026-04-03 by Phase 41.1 "Import speed optimization" (commit ca4cc5d4). Phase 41.1 also added the per-batch Stockfish eval pass (`asyncio.gather` over `engine_service.evaluate` in `_flush_batch`, `_apply_eval_results`). Prod runs `STOCKFISH_POOL_SIZE=4` (4 concurrent engines, 64MB Hash each). The OOM-mitigation was effectively reverted and compounded by new per-batch engine memory.
- timestamp: 2026-05-16 — Facet (2) code defect: on a Postgres crash-restart the `except Exception` failure handler (`import_service.py:386-410`) opens a new session and tries an UPDATE while the DB is still in recovery → raises `CannotConnectNowError`, caught by the inner try/except which only logs+captures. The job is never marked `failed` and stays `in_progress` forever (the `cc9bcef0` row). `cleanup_orphaned_jobs()` (main.py lifespan) only runs on a backend *restart*; a Postgres-only restart leaves the backend up, so orphaned in_progress jobs are never reaped until the next backend deploy/restart.
- timestamp: 2026-05-16 — Facet (3) contributing defect: `POST /imports` duplicate guard (`routers/imports.py:51-68`) is a non-atomic check-then-act over the in-memory `_jobs` dict with `await` points (`update_platform_username` + commit) between `find_active_job` and `create_job`. Two near-simultaneous POSTs from user 94 both passed the guard, producing two concurrent jobs. NOTE: now reclassified as a minor amplifier, not a root cause (see prod experiment below).
- timestamp: 2026-05-16 — **PROD CONTROLLED EXPERIMENT (authorized).** Single (non-concurrent) import of `FaustinoOro` chess.com into disposable guest user 95 on prod, stock PR #99 settings (`_BATCH_SIZE=12`, `_HASH_MB=32`, `STOCKFISH_POOL_SIZE=4`). 43 read-only samples over ~7.5 min via host `/proc/*/comm` (in-container `pgrep` is absent — earlier in-container counts were a false 0). Results: stockfish process count **flat at 4** and summed stockfish RSS **flat at 1241 MB** the entire run, through avail 3601→1443 MB with swap untouched. Host mem used climbed **linearly +290 MB/min** (~0.48 MB / game imported at 9.7 games/s). Backend restart reclaimed ~3.7 GB instantly (6.7→2.9 GB), proving the leak is wholly in the import-worker Python heap and freed on process death. No OOM occurred (stopped in time). Trace: `.planning/debug/oom-trace-user94-2026-05-16.log` (the earlier real-incident kernel capture) plus this experiment's sampling.
- timestamp: 2026-05-16 — Static read: `bulk_insert_games`/`bulk_insert_positions` are Core `insert().values()` (no ORM instances tracked); `_collect_position_rows` reads via `select(Game.id, Game.platform_game_id)` (column-only Rows, not mapped entities). The ORM identity map does not accumulate; `expire_on_commit=False` is a latent footgun but not the leak vector here. `EnginePool` is structurally bounded (fixed size, in-place slot replacement, indices always re-queued).

## Eliminated

- "Single large import alone could NOT cause OOM / a concurrent pair was required" — **ELIMINATED (was the prior conclusion; now disproven).** Prod experiment: one non-concurrent import leaks ~0.48 MB/game → ~10 GB for a 20k-game account → OOMs alone. Concurrency only doubles the slope.
- "`_restart_worker` orphans wedged Stockfish subprocesses under memory pressure" — **ELIMINATED.** Engine count pinned at pool size (4) and RSS flat (1241 MB) across the entire pressure ramp.
- "SQLAlchemy ORM identity-map growth (`expire_on_commit=False` + long-lived session)" — **ELIMINATED.** Insert path is Core; read path is column-only. No mapped instances accumulate.
- "Generic transient network blip" — eliminated; the original 06:22Z prod logs show a definite OOM-kill + crash recovery, not a network drop.

## Resolution

- status: SUPERSEDED — the root cause below was disproven by the 2026-05-16 prod controlled experiment. Retained for history.
- root_cause (SUPERSEDED, incorrect): "OOM driven by Phase 41.1 batch-size/eval regression + a non-atomic duplicate guard letting a concurrent pair run." Disproven: a single non-concurrent import OOMs on its own; the engine pool and `_restart_worker` are bounded; the regression knobs only change the *rate*.
- root_cause (CURRENT, empirically established): A **real unbounded memory leak in the import-worker Python process**, ~0.48 MB per game imported, linear from the first game, freed only on process death. `run_import` (import_service.py:281) opens **one** `async_session_maker()` `AsyncSession` and reuses it for **every** batch of the entire import (per-batch `session.commit()` only, `expire_on_commit=False`, no `expunge`/session recycle). The growing allocation is in the SQLAlchemy/asyncpg layer on that long-lived connection — NOT the ORM identity map (insert path Core, read path column-only), NOT the Stockfish pool, NOT `_restart_worker`. The 06:22Z Sentry errors (FLAWCHESS-56 / -3Q) remain valid downstream symptoms of the resulting Postgres OOM-kill + crash recovery; only the *cause* of the OOM is corrected. Exact allocation line pending local `tracemalloc` localization (see Current Focus).
- confirmed_mechanism (tracemalloc, 2026-05-16): `_flush_batch` Stage 5 builds a literal `case(rows_result.move_counts, value=Game.id)` (one `WHEN` per game) + `case(fen_case_map, ...)` + `update(Game).where(Game.id.in_(list(...)))`. The id set differs every batch → a unique SQL text per batch → SQLAlchemy recompiles (`compiler.py:1770`) and asyncpg prepares+caches a new server-side statement (`connection.py:481`) each batch, retained for the whole import on the single session/connection (`import_service.py:281`). `pg_insert(Game).values(game_rows)` / `insert(GamePosition).values(chunk)` with variable row counts is a secondary contributor (text varies with batch fill / chunk size). Net: linear ~0.48 MB/game + progressive slowdown.
- fix (REVISED, mechanism now pinned): (1) **Primary — make the per-batch SQL text invariant.** Replace the literal `case()`+`IN` bulk UPDATE in `_flush_batch` Stage 5 with a bound-parameter `executemany`: `await session.execute(update(Game).where(Game.id == bindparam("b_id")).values(move_count=bindparam("mc"), result_fen=bindparam("rf")), [ {...} for each game ])` — one invariant statement text, params vary → no per-batch compile/prepare, also a throughput win. Defense-in-depth: scope `async with async_session_maker()` per batch in `run_import` (import_service.py:281 loop) so any per-connection cache is discarded each batch; and/or set asyncpg `statement_cache_size` low via `create_async_engine(connect_args=...)`. Note `pg_insert(...).values(list)` is acceptable if batch size is constant; the last partial batch and variable position-chunk sizes are minor and fixed by the same per-batch session recycling. (2) Still valid independently: resilient failure-state recording with retry across a DB-recovery window. (3) Still valid: reap orphaned `in_progress` jobs on a schedule / DB reconnect, not only at backend startup (a *backend* restart on 2026-05-16 did correctly reap user 94 & 95's orphans → confirms the gap is specifically the Postgres-only-restart case). (4) Duplicate-import guard: DEMOTE to nice-to-have — it does NOT prevent recurrence (single import OOMs alone); keep only as a UX/data-hygiene measure. (5) Backfill obsolete — all stuck jobs were reaped by the 2026-05-16 backend restart; user 95 experiment data was deleted.
- specialist_hint: python
</content>
</invoke>
