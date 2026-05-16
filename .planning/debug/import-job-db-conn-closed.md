---
slug: import-job-db-conn-closed
status: resolved
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

- hypothesis: CONFIRMED — OOM killer (triggered by a Stockfish allocation) killed Postgres, causing crash recovery; both Sentry errors are downstream symptoms.
- next_action: (complete — root cause found, fix proposed)
- test: (n/a — diagnosis confirmed from prod logs + DB state)
- expecting: (n/a)
- reasoning_checkpoint: (n/a)
- tdd_checkpoint: (n/a)

## Evidence

- timestamp: 2026-05-16 — Both Sentry issues share trace_id 565fae5f21414e77964f828e216036d4, server dbe6bf8ac81c, within 2s. FLAWCHESS-56 = connection closed mid-eval-UPDATE; FLAWCHESS-3Q = DB not accepting connections when recording failure.
- timestamp: 2026-05-16 — Prod `import_jobs` for user 94 shows TWO concurrent chess.com jobs started 2s apart: `27764c56` (started 05:55:18, status=failed, InterfaceError, 8901 imported) and `cc9bcef0` (started 05:55:16, status=in_progress STUCK, completed_at=NULL, 9212 imported). Two simultaneous imports for the same user doubled import-side memory.
- timestamp: 2026-05-16 — Prod Postgres container logs: `06:22:01 client backend (PID 1154281) was terminated by signal 9: Killed` → `terminating any other active server processes` → `06:22:02 database system was not properly shut down; automatic recovery in progress` → `06:22:04 FATAL: the database system is not yet accepting connections` (= exactly FLAWCHESS-3Q).
- timestamp: 2026-05-16 — Host dmesg: `[Sat May 16 06:22:09] stockfish invoked oom-killer ... Out of memory: Killed process 253640 (postgres) total-vm:3140296kB anon-rss:507420kB shmem-rss:448396kB`. The OOM killer was invoked by a STOCKFISH allocation; Postgres was the chosen victim. Prod box: 7.6GB RAM, only 2GB swap.
- timestamp: 2026-05-16 — Memory-pressure regression: `_BATCH_SIZE` reduced 50→10 on 2026-03-22 (commit f3b36b7e, OOM mitigation) was raised back to **28** on 2026-04-03 by Phase 41.1 "Import speed optimization" (commit ca4cc5d4). Phase 41.1 also added the per-batch Stockfish eval pass (`asyncio.gather` over `engine_service.evaluate` in `_flush_batch`, `_apply_eval_results`). Prod runs `STOCKFISH_POOL_SIZE=4` (4 concurrent engines, 64MB Hash each). The OOM-mitigation was effectively reverted and compounded by new per-batch engine memory.
- timestamp: 2026-05-16 — Facet (2) code defect: on a Postgres crash-restart the `except Exception` failure handler (`import_service.py:386-410`) opens a new session and tries an UPDATE while the DB is still in recovery → raises `CannotConnectNowError`, caught by the inner try/except which only logs+captures. The job is never marked `failed` and stays `in_progress` forever (the `cc9bcef0` row). `cleanup_orphaned_jobs()` (main.py lifespan) only runs on a backend *restart*; a Postgres-only restart leaves the backend up, so orphaned in_progress jobs are never reaped until the next backend deploy/restart.
- timestamp: 2026-05-16 — Facet (3) contributing defect: `POST /imports` duplicate guard (`routers/imports.py:51-68`) is a non-atomic check-then-act over the in-memory `_jobs` dict with `await` points (`update_platform_username` + commit) between `find_active_job` and `create_job`. Two near-simultaneous POSTs from user 94 both passed the guard, producing the two concurrent jobs that doubled OOM-relevant memory.

## Eliminated

- "Single large import alone caused OOM" — partially: a *concurrent pair* of imports plus the Phase 41.1 batch-size + eval-pass regression is what pushed it over. Single-import path is heavier than pre-Phase-41.1 but the duplicate-job race was a real amplifier here.
- "Generic transient network blip" — eliminated; prod logs show a definite OOM-kill + crash recovery, not a network drop.

## Resolution

- root_cause: An OOM-kill of Postgres (invoked by a Stockfish allocation) during user 94's import caused a crash-recovery restart, surfacing as `connection is closed` (FLAWCHESS-56) and `database system is not yet accepting connections` (FLAWCHESS-3Q). The OOM was driven by a regression: Phase 41.1 (commit ca4cc5d4, 2026-04-03) raised `_BATCH_SIZE` from the 10 set as the 2026-03-22 OOM mitigation back to 28 AND added a per-batch Stockfish eval pass (pool size 4 on prod), effectively reverting and compounding the prior mitigation. A non-atomic duplicate-import guard let two concurrent jobs for user 94 run, doubling import-side memory and amplifying the OOM. Separately, the failure-recording path cannot mark the job `failed` when the DB is still in recovery, and `cleanup_orphaned_jobs()` only runs on backend restart (not a Postgres-only restart), so the job is stuck `in_progress` indefinitely.
- fix: Multi-part. (1) Reduce memory pressure: lower `_BATCH_SIZE` back toward 10–12 and/or reduce prod `STOCKFISH_POOL_SIZE` and `_HASH_MB`, and raise prod swap above 2GB (the 2026-03-22 mitigation that was reverted). (2) Make failure-state recording resilient: retry the `update_import_job` failure write with backoff so it survives a brief DB-recovery window. (3) Reap orphaned `in_progress` jobs on a schedule / on DB reconnect, not only at backend startup, so a Postgres-only restart still transitions stuck jobs to `failed`. (4) Make the `POST /imports` duplicate guard atomic (DB unique partial index on active jobs per user+platform, or a lock) to prevent concurrent duplicate imports. (5) Backfill: manually mark the stuck `cc9bcef0` job `failed` in prod (write op — requires user/ops action, MCP prod is read-only).
- specialist_hint: python
</content>
</invoke>
