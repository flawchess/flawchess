---
phase: 117-priority-queue-flaw-integration
plan: "02"
subsystem: eval-queue-service
tags: [eval-queue, skip-locked, lease-report, priority-queue, admin-endpoint]
dependency_graph:
  requires: [117-01, eval-jobs-table, EvalJob-model]
  provides: [claim_eval_job, report_job_complete, requeue_expired_leases, enqueue_tier1_game, admin-tier1-trigger]
  affects: [eval_drain, admin_router, flaws_service]
tech_stack:
  added: []
  patterns: [skip-locked-cte-via-sa-text, pg_insert-on_conflict_do_nothing-partial-index, tier3-derived-pick]
key_files:
  created:
    - app/services/eval_queue_service.py
    - tests/services/test_eval_queue.py
  modified:
    - app/routers/admin.py
    - app/schemas/admin.py
decisions:
  - "LEASE_TTL_SECONDS=120 (2x worst-case tier-2/3 game: 60 plies x 0.98s/ply = ~59s; tier-1 fan-out ~10s)"
  - "TTL passed as str('120') to sa.text bound params — asyncpg requires string for || concat in interval cast"
  - "Tier-3 is a derived pick (no pre-populated eval_jobs rows); job_id=None signals drain to mark full_evals_completed_at directly"
  - "on_conflict_do_nothing uses index_where=sa.text(\"status IN ('pending', 'leased')\") to match the partial unique index"
  - "is_analyzed derived from lichess_evals_at IS NOT NULL per D-117-07"
  - "EnqueueTier1Response with Literal status field added to app/schemas/admin.py"
metrics:
  duration: "~9 minutes"
  completed: "2026-06-13T09:26:00Z"
  tasks_completed: 3
  files_modified: 4
---

# Phase 117 Plan 02: Tiered Priority Queue Service Summary

**One-liner:** PostgreSQL SKIP LOCKED tiered priority queue with lease/report contract, tier-3 derived backlog pick, guest exclusion on every path, and a superuser-gated admin trigger for QUEUE-03 fan-out verification.

## What Was Built

**Queue service** (`app/services/eval_queue_service.py`):

- `claim_eval_job(worker_id)` — tier-1 > tier-2 > tier-3 pick. Tier-1/2 uses a `SELECT FOR UPDATE OF ej SKIP LOCKED` CTE via `sa.text` with parameterized `:worker_id` and `:ttl` (no f-string interpolation, V5 SQL-injection safety). Within a tier: oldest-pending user first (round-robin approximation, QUEUE-02); within a user: classical > rapid > blitz > bullet then most-recent (D-117-04 CASE). Guest exclusion via `JOIN users WHERE NOT is_guest` on both the CTE and tier-3 derived pick (QUEUE-08). Tier-3 is a derived query over `games WHERE full_evals_completed_at IS NULL AND NOT is_guest` — no pre-populated rows. Returns `ClaimedJob(game_id, user_id, tier, is_analyzed, job_id)` or `None`. `is_analyzed` derived from `lichess_evals_at IS NOT NULL` (D-117-07). `job_id=None` for tier-3.
- `report_job_complete(job_id)` — sets `status='completed'`, `completed_at=now` for a leased job.
- `requeue_expired_leases()` — resets `status='pending'` for rows with `lease_expiry < now()`. Also called inline at the top of each `claim_eval_job` call.
- `enqueue_tier1_game(game_id, user_id)` — guest-guarded `pg_insert(EvalJob).on_conflict_do_nothing(index_elements=["game_id"], index_where=sa.text("status IN ('pending', 'leased')"))` targeting the partial unique index. Returns `True` if inserted, `False` for guest or already-queued.
- Constants: `LEASE_TTL_SECONDS=120`, `WORKER_ID_SERVER_POOL="server-pool"`, `EvalJobStatus` Literal.

**Admin endpoint** (`app/routers/admin.py`, `app/schemas/admin.py`):

- `POST /admin/eval/enqueue-tier1/{game_id}` — superuser-gated (`Depends(current_superuser)`) internal trigger (D-117-05 / QUEUE-03). 404 on missing game (EXPECTED — not Sentry-captured per admin router convention). Delegates to `enqueue_tier1_game`. Returns `EnqueueTier1Response(status, game_id)` with `status` in `{"enqueued", "skipped_guest", "already_queued"}`.

**Wave 0 tests** (`tests/services/test_eval_queue.py`):

Six tests covering all six required behaviors (QUEUE-01/02/05/06/08):
- `test_tier_priority` — tier-1 job claimed before tier-3-eligible game (QUEUE-01)
- `test_round_robin` — user A served before user B by MIN(created_at) (QUEUE-02)
- `test_tc_ordering` — classical before bullet same user (D-117-04)
- `test_tier3_derived` — game with no eval_jobs row → `job_id=None`, `tier=3` (QUEUE-05)
- `test_lease_expiry` — expired lease requeued, re-claimable (QUEUE-06)
- `test_guest_exclusion` — guest game never claimed; `enqueue_tier1_game` returns `False` (QUEUE-08)

## Verification Results

- `uv run pytest tests/services/test_eval_queue.py -x` — 6/6 passed
- `uv run ty check app/ tests/` — zero errors
- `uv run ruff check app/ tests/` — clean
- Admin endpoint registered: `python -c "from app.main import app; ... assert any('enqueue-tier1' in p for p in paths)"` — pass
- No f-strings in `sa.text` CTE (grep confirmed)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] asyncpg integer bind for string operand in interval cast**
- **Found during:** Task 3 test run (first attempt)
- **Issue:** `(:ttl || ' seconds')::interval` in the SKIP LOCKED CTE requires the `:ttl` param to be a string, but `LEASE_TTL_SECONDS` is `int`. asyncpg raised `DataError: invalid input for query argument $2: 120 (expected str, got int)`.
- **Fix:** Pass `str(lease_ttl_seconds)` instead of `lease_ttl_seconds` in the parameter dict.
- **Files modified:** `app/services/eval_queue_service.py`
- **Commit:** `6feaad3e` (included in test commit)

**2. [Rule 2 - Minor] Tier returned from queued job claim**
- **Found during:** Task 1 review
- **Issue:** Original `_claim_queued_job` didn't include `tier` in the RETURNING clause, so `ClaimedJob.tier` was hardcoded as `TIER_EXPLICIT` for all tier-1/2 claims.
- **Fix:** Added `candidate.tier` to the CTE's RETURNING clause and updated the function signature to return 5-tuple including tier.
- **Files modified:** `app/services/eval_queue_service.py`

**3. [Rule 2 - Minor] `on_conflict_do_nothing` index_where for partial unique**
- **Found during:** Task 1 implementation review
- **Issue:** `on_conflict_do_nothing(index_elements=["game_id"])` without `index_where` may fail to match the partial unique index `uq_eval_jobs_game_active (WHERE status IN ('pending','leased'))` in PostgreSQL.
- **Fix:** Added `index_where=sa.text("status IN ('pending', 'leased')")` to precisely target the partial unique index.
- **Files modified:** `app/services/eval_queue_service.py`

## Known Stubs

None. All functions are fully implemented and tested against real PostgreSQL via the per-run isolated test DB.

## Threat Flags

None. All threat mitigations from the plan's threat model were applied:
- T-117-04: superuser gate on admin trigger (Depends(current_superuser)) — implemented
- T-117-05: no unbounded fan-out; only superusers can enqueue tier-1 in Phase 117 — implemented
- T-117-06: guest exclusion on every tier and enqueue path — implemented
- T-117-07: parameterized sa.text (no string interpolation) — implemented

## Self-Check: PASSED

Files created/exist:
- /home/aimfeld/Projects/Python/flawchess/app/services/eval_queue_service.py FOUND
- /home/aimfeld/Projects/Python/flawchess/tests/services/test_eval_queue.py FOUND

Files modified exist:
- /home/aimfeld/Projects/Python/flawchess/app/routers/admin.py FOUND
- /home/aimfeld/Projects/Python/flawchess/app/schemas/admin.py FOUND

Commits exist:
- f12a528b: feat(117-02): eval_queue_service FOUND
- 070e5b9d: feat(117-02): POST /admin/eval/enqueue-tier1 FOUND
- 6feaad3e: test(117-02): Wave 0 queue tests FOUND
