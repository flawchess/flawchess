---
id: SEED-017
status: dormant
planted: 2026-05-16
planted_during: v1.17
trigger_when: next time import pipeline, job lifecycle, or DB-failure handling is in scope — or proactively before the next large-scale import campaign
scope: medium
---

# SEED-017: Import resilience hardening (post-incident FLAWCHESS-56 / FLAWCHESS-3Q follow-up)

## Why This Matters

On 2026-05-16 a Postgres OOM-kill during user 94's **concurrent/duplicate** chess.com import dropped the DB connection mid-import (`PreparedStatement.fetch: connection is closed` — FLAWCHESS-56). The failure-state-recording path then hit a still-recovering DB (`CannotConnectNowError` — FLAWCHESS-3Q), so the job was **never marked failed and stayed `in_progress` indefinitely**.

The shipped memory hotfix (`_BATCH_SIZE` 28→12, `_HASH_MB` 64→32, prod swap 4G; PRs #99/#101) only reduces OOM *probability*. It does not fix the resilience defects, and it is **not a proof**: a single very large import can still spike past the budget. Critically, `STOCKFISH_POOL_SIZE` stays at 4 (deliberate — import speed), so the duplicate-import guard is **load-bearing**: two concurrent imports × pool-of-4 was the exact OOM multiplier in this incident. Until these land, the same failure recurs and silently strands jobs.

## When to Surface

**Trigger:** next time the import pipeline, job lifecycle, or DB-failure handling is touched — or proactively scheduled before any large-scale import campaign (e.g. benchmark ingest, mass reimport).

This seed will surface during `/gsd:new-milestone` when the milestone scope matches import/jobs/DB-resilience work. It should not wait for a milestone if another OOM/stuck-job incident occurs first — promote immediately in that case.

## Scope Estimate

**Medium** — one phase (or two thin phases). Three parts, in priority order:

1. **Atomic duplicate-import guard (TOP PRIORITY).** `POST /imports` (`app/routers/imports.py`) does a non-atomic check-then-act over the in-memory `_jobs` dict, with `await` points (`update_platform_username` + commit) between `find_active_job` and `create_job`. Two near-simultaneous POSTs from the same user both pass the guard → concurrent imports that doubled OOM-relevant memory (the incident's amplifier). Fix: a DB-level **partial unique index** on active jobs per `(user_id, platform)` (status in pending/in_progress), or a Postgres advisory lock, replacing the racy in-memory check. Requires an Alembic migration.

2. **Scheduled / on-reconnect orphan-job reaper.** `cleanup_orphaned_jobs()` (`app/services/import_service.py:140`, wired in `app/main.py` lifespan) only runs at **backend startup**. A Postgres-only restart leaves the backend process up, so orphaned `in_progress` jobs are never reaped until the next backend deploy/restart (in this incident the job only cleared because a deploy happened to restart the backend hours later). Add a periodic task and/or on-DB-reconnect hook so stuck jobs transition to `failed` without needing a backend restart.

3. **Resilient failure-state recording.** The `except Exception` failure handler in `run_import` (`app/services/import_service.py` ~386-410) opens a new session and issues an UPDATE while the DB may still be in crash recovery, raising `CannotConnectNowError`; the inner try/except only logs + `capture_exception`, so the job is never marked `failed`. Add a bounded retry with backoff so the failure write survives a brief DB-recovery window.

Verification: after the fix, run/observe a clean large import, then resolve Sentry FLAWCHESS-56 (issue 120262007) and FLAWCHESS-3Q (issue 115610288). Watch for recurrence.

## Breadcrumbs

- `app/routers/imports.py` — non-atomic `POST /imports` duplicate guard (part 1)
- `app/services/import_service.py:140` `cleanup_orphaned_jobs()`; `~386-410` `run_import` failure handler; `find_active_job` / `create_job` (parts 2 & 3)
- `app/main.py` — lifespan wiring of `cleanup_orphaned_jobs()` (part 2)
- `.planning/debug/import-job-db-conn-closed.md` — full scientific-method root-cause analysis (read this first)
- `CLAUDE.md` → "Production Server" → "OOM recurrence 2026-05-16 (FLAWCHESS-56 / FLAWCHESS-3Q)" note
- Sentry: FLAWCHESS-56 (120262007), FLAWCHESS-3Q (115610288); both `unresolved`
- Related shipped work: PR #99 (hotfix → production), #101 (forward-port → main), #100 (deploy.sh hardening)

## Notes

Memory hotfix is in prod and on main as of 2026-05-16. This seed is purely the deferred *resilience* work — not the memory tuning. Part 1 is the highest-leverage item given `STOCKFISH_POOL_SIZE=4` is intentionally retained.
