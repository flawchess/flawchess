---
phase: 149-retire-prune
plan: 01
subsystem: api
tags: [sqlalchemy, alembic, postgresql, fastapi, worker-fleet, telemetry]

# Dependency graph
requires: []
provides:
  - "worker_heartbeats table + WorkerHeartbeat model"
  - "upsert_worker_heartbeat() shared repository helper"
  - "worker_schema_version telemetry landing column (PRUNE-04)"
affects: [150-consolidate-write-path]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "pg_insert(...).on_conflict_do_update(...) upsert-by-PK with per-column accumulate/overwrite/coalesce set_ clauses"

key-files:
  created:
    - app/models/worker_heartbeat.py
    - app/repositories/worker_heartbeat_repository.py
    - alembic/versions/20260704_112059_b4ea823c85be_add_worker_heartbeats_table.py
    - tests/test_worker_heartbeats.py
  modified:
    - app/models/__init__.py
    - app/routers/eval_remote.py
    - tests/test_eval_worker_endpoints.py

key-decisions:
  - "worker_heartbeats.worker_id is String(16), no ForeignKey — matches the worker_id_label truncation invariant; it is a free-form external identity, not an internal-table reference"
  - "worker_schema_version uses sa.func.coalesce(excluded, current) in the upsert set_ clause so entry-submit/flaw-blob-submit (which never send it) can never null out the atomic lane's last known value"
  - "Heartbeat upsert reuses each handler's existing write session — no new session, no asyncio.gather, no lease-endpoint writes (D-04)"

patterns-established:
  - "Pattern: shared single-insertion-point upsert helper called from multiple router handlers via each handler's existing write session (Phase 150 inherits this shape for further write-path consolidation)"

requirements-completed: [PRUNE-06, PRUNE-04]

coverage:
  - id: D1
    description: "worker_heartbeats table + WorkerHeartbeat model exist, migrate up/down cleanly"
    requirement: "PRUNE-06"
    verification:
      - kind: unit
        ref: "uv run alembic upgrade head && uv run alembic downgrade -1 && uv run alembic upgrade head"
        status: pass
      - kind: unit
        ref: "uv run ty check app/"
        status: pass
    human_judgment: false
  - id: D2
    description: "Every live submit lane (entry-submit, flaw-blob-submit, atomic-submit) upserts one worker_heartbeats row keyed by X-Worker-Id, accumulating submit_count/evals_submitted"
    requirement: "PRUNE-06"
    verification:
      - kind: integration
        ref: "tests/test_worker_heartbeats.py#test_worker_heartbeat_accumulates_across_all_three_submit_lanes"
        status: pass
    human_judgment: false
  - id: D3
    description: "worker_schema_version is recorded on atomic-submit and coalesced (never clobbered to NULL) when a later lane omits it"
    requirement: "PRUNE-04"
    verification:
      - kind: integration
        ref: "tests/test_worker_heartbeats.py#test_worker_heartbeat_accumulates_across_all_three_submit_lanes"
        status: pass
    human_judgment: false
  - id: D4
    description: "last_ip populated from request.client.host, or NULL when request.client is None (test client)"
    requirement: "PRUNE-06"
    verification:
      - kind: integration
        ref: "tests/test_worker_heartbeats.py#test_worker_heartbeat_null_client_last_ip"
        status: pass
    human_judgment: false
  - id: D5
    description: "Lease endpoints (entry-lease, atomic-lease, flaw-blob-lease) never upsert a heartbeat — submits only (D-04)"
    requirement: "PRUNE-06"
    verification:
      - kind: unit
        ref: "grep -n upsert_worker_heartbeat( within 40 lines of any lease decorator — none found"
        status: pass
    human_judgment: false

# Metrics
duration: 20min
completed: 2026-07-04
status: complete
---

# Phase 149 Plan 01: Worker Heartbeats Registry Summary

**Server-side `worker_heartbeats` table upserted on every live submit (entry-submit, flaw-blob-submit, atomic-submit) via a shared `pg_insert(...).on_conflict_do_update(...)` helper, landing `worker_schema_version` telemetry as a byproduct with no version-rejection gate.**

## Performance

- **Duration:** ~20 min
- **Started:** 2026-07-04T11:18:20Z
- **Completed:** 2026-07-04T11:37:27Z
- **Tasks:** 2
- **Files modified:** 7

## Accomplishments
- New `WorkerHeartbeat` model (`worker_id` PK VARCHAR(16), `last_ip`, `sf_version`, `worker_schema_version`, `last_seen`, `submit_count`, `evals_submitted`) and a clean single-table Alembic migration, verified reversible (upgrade/downgrade/upgrade).
- New `upsert_worker_heartbeat()` repository helper: accumulates `submit_count`/`evals_submitted`, overwrites `last_ip`/`sf_version`/`last_seen` with the latest value, and coalesces `worker_schema_version` so a lane that omits it (entry-submit, flaw-blob-submit) never clobbers the atomic lane's last known value with NULL.
- Wired into all three live submit handlers (`entry_submit_eval`, `flaw_blob_submit` / `_apply_flaw_blob_submit`, `atomic_submit_eval` / `_apply_atomic_submit`), each call reusing the handler's existing write session — zero new sessions, zero `asyncio.gather`.
- Lease endpoints (`/entry-lease`, `/atomic-lease`, `/flaw-blob-lease`) are untouched — verified no `upsert_worker_heartbeat(` call within 40 lines of any lease route decorator.
- New `tests/test_worker_heartbeats.py` covering cross-lane accumulation, the `worker_schema_version` coalesce guard, and the NULL-`last_ip` path when `request.client` is `None`.

## Task Commits

Each task was committed atomically:

1. **Task 1: WorkerHeartbeat model + migration** - `82a85e88` (feat)
2. **Task 2: Shared upsert helper wired into all three live submit handlers** - `6b629c2c` (feat)

_Note: Task 2's commit also includes a ruff-format line collapse to `app/models/worker_heartbeat.py` and 8 existing `_apply_atomic_submit()` direct-call test sites updated for the new `worker_id`/`last_ip` parameters (mechanical fallout of the signature change, not a separate deviation)._

## Files Created/Modified
- `app/models/worker_heartbeat.py` - `WorkerHeartbeat` SQLAlchemy model
- `app/models/__init__.py` - registers `WorkerHeartbeat` so Alembic autogenerate sees it (import triggers package `__init__` execution)
- `alembic/versions/20260704_112059_b4ea823c85be_add_worker_heartbeats_table.py` - creates `worker_heartbeats`, reversible
- `app/repositories/worker_heartbeat_repository.py` - `upsert_worker_heartbeat()` shared helper
- `app/routers/eval_remote.py` - `Request` import; `worker_id`/`request` params added to `flaw_blob_submit`/`atomic_submit_eval` (entry-submit already had `worker_id`); heartbeat upsert call in each handler's write session
- `tests/test_worker_heartbeats.py` - new test module (2 tests)
- `tests/test_eval_worker_endpoints.py` - 8 existing direct `_apply_atomic_submit()` calls updated with `worker_id="test-worker", last_ip=None`

## Decisions Made
- `worker_id` column is `VARCHAR(16)` matching the `worker_id_label` truncation guarantee exactly (RESEARCH.md Open Question 2), rather than `TEXT` — aligns with the existing `entry_eval_leased_by` precedent.
- `worker_schema_version` coalesce (not overwrite) is enforced in the SQL `set_=` clause itself (`sa.func.coalesce(excluded, current)`), not in application code — race-free under concurrent submits from the same worker_id.
- Heartbeat upsert call sites were placed as the last statement before each handler's `write_session.commit()`, so an idempotent early-return path (e.g. `_apply_flaw_blob_submit`'s "all blobs already written" D-03 no-op, or `entry_submit_eval`'s "no leased games" early return) does not emit telemetry for that particular no-op call — acceptable since the plan's must-haves and tests only require accumulation across substantive submits, not every possible early-return branch.

## Deviations from Plan

None - plan executed exactly as written. The 8 existing test call-site updates in `tests/test_eval_worker_endpoints.py` are mechanical fallout of adding required parameters to `_apply_atomic_submit` (a private helper some existing tests call directly, bypassing the HTTP layer) — not a scope change, required to keep `ty check` and the full suite green.

## Issues Encountered
None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Phase 150 (Consolidate Write Path) inherits `worker_heartbeats` and the shared upsert helper as the single insertion point for fleet-liveness telemetry going forward — no further wiring needed when the write paths are unified.
- No consumer UI exists yet for `worker_heartbeats` (intentional, per PRUNE-06 scope) — the table is queryable directly via SQL for fleet-visibility checks.

---
*Phase: 149-retire-prune*
*Completed: 2026-07-04*

## Self-Check: PASSED

All created files exist on disk; both task commit hashes (`82a85e88`, `6b629c2c`) are present in git history.
