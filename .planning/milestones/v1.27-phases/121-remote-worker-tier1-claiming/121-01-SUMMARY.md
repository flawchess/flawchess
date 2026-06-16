---
phase: 121-remote-worker-tier1-claiming
plan: "01"
subsystem: eval-worker
tags:
  - eval
  - remote-worker
  - tier-1
  - queue
  - lease
  - submit
dependency_graph:
  requires:
    - "120-01: remote eval worker lease/submit protocol"
    - "119-01: eval_jobs queue + claim_eval_job"
  provides:
    - "tier-1 claiming via lease endpoint (not just tier-3)"
    - "job_id round-trip: lease → submit"
    - "eval_jobs stamp on submit completion"
  affects:
    - "app/routers/eval_remote.py: lease handler now tier-aware"
    - "scripts/remote_eval_worker.py: 1.0s idle poll interval"
tech_stack:
  added: []
  patterns:
    - "claim_eval_job owns its sessions — never call inside caller-owned context"
    - "WHERE status='leased' idempotency guard on eval_jobs stamp UPDATE"
    - "Opaque token threading: server assigns, worker echoes, server interprets"
key_files:
  created: []
  modified:
    - tests/test_eval_worker_endpoints.py
    - app/schemas/eval_remote.py
    - app/routers/eval_remote.py
    - scripts/remote_eval_worker.py
decisions:
  - "Use _WORKER_ID_REMOTE = 'remote-worker' named constant (not inline string) for leased_by traceability"
  - "eval_jobs stamp lives inside the write session in _apply_submit (atomic with eval/flaw writes)"
  - "Stamp only when stamp_complete=True (Path A or C) — Path B stays leased for sweep retry"
metrics:
  duration: "~12 minutes"
  completed_date: "2026-06-15"
  tasks_completed: 3
  files_changed: 4
---

# Phase 121 Plan 01: Remote-worker tier-1 claiming Summary

Let the remote eval worker claim tier-1 (and tier-2) single-game analyze requests through the lease/submit contract via `claim_eval_job`, with an opaque `job_id` token round-trip that enables `eval_jobs` stamping on submit and a 1.0s idle poll for fast tier-1 pickup.

## Tasks Completed

| Task | Name | Commit | Key Files |
|------|------|--------|-----------|
| 1 | Re-target broken claim mocks + add tier-1/job_id/stamp tests (RED) | `4076df90` | tests/test_eval_worker_endpoints.py |
| 2 | Wire lease to claim_eval_job, thread job_id through schemas + submit stamp | `86ee2b89` | app/schemas/eval_remote.py, app/routers/eval_remote.py |
| 3 | Worker idle sleep 1.0 + job_id echo on submit | `910fdea3` | scripts/remote_eval_worker.py, tests/test_eval_worker_endpoints.py (ruff) |

## What Was Built

### Schema changes (app/schemas/eval_remote.py)

Added `job_id: int | None = None` to both `LeaseResponse` and `SubmitRequest`. The field is optional with `None` default, preserving backward compatibility for workers that don't send it.

### Router changes (app/routers/eval_remote.py)

- Removed `from app.services.eval_queue_service import _claim_tier3_derived` import.
- Added `from app.services.eval_queue_service import claim_eval_job` and `from app.models.eval_jobs import EvalJob`.
- Added `_WORKER_ID_REMOTE = "remote-worker"` named constant for `leased_by` traceability.
- Rewrote `lease_eval_game` to call `claim_eval_job(worker_id=_WORKER_ID_REMOTE)` directly (no caller session — the service owns its sessions).
- Destructures `ClaimedJob` fields (not the old 3-tuple from `_claim_tier3_derived`).
- Returns `job_id=claim.job_id` in `LeaseResponse` (int for tier-1/2, None for tier-3).
- Added `eval_jobs` stamp in `_apply_submit` write session:
  ```python
  if body.job_id is not None and stamp_complete:
      update(EvalJob.__table__)
          .where(id == body.job_id, status == "leased")
          .values(status="completed", completed_at=now_ts)
  ```
  The `WHERE status='leased'` predicate is the late-submit / idempotency guard (T-121-01).

### Worker changes (scripts/remote_eval_worker.py)

- `DEFAULT_IDLE_SLEEP: float = 1.0` (was 5.0). Comment explains only the empty-queue path sleeps; the busy path is a tight loop.
- Reads `job_id = data.get("job_id")` from the lease response dict.
- Adds `"job_id": job_id` to the submit payload. Worker stores and echoes it without interpreting it.

### Test changes (tests/test_eval_worker_endpoints.py)

- Re-targeted two existing tests from mocking `_claim_tier3_derived` to mocking `claim_eval_job` (returns `ClaimedJob` instances, not 3-tuples).
- Added `assert body["job_id"] is None` in the tier-3 lease test.
- Added `_get_eval_job` and `_seed_eval_job` helper functions.
- Added `TestTier1Claiming` class with 5 tests:
  - R1: tier-1 claim returns correct `job_id` from `ClaimedJob` mock
  - R3: submit with `job_id` stamps `eval_jobs` to `status='completed'` with `completed_at` set
  - R4: submit with `job_id=None` leaves a sentinel `eval_jobs` row untouched
  - R5: submit against non-`'leased'` row is a no-op (late-submit guard proof)
  - R6: `DEFAULT_IDLE_SLEEP == 1.0` constant assertion

## Deviations from Plan

None — plan executed exactly as written. The single discretionary choice (using `_WORKER_ID_REMOTE` constant instead of inline `"remote-worker"`) is explicitly listed in the plan as Claude's discretion.

## Threat Surface Scan

No new network endpoints, auth paths, file access patterns, or schema changes introduced. The `job_id` field on `SubmitRequest` is within the existing `require_operator_token`-protected boundary. The `WHERE status='leased'` guard caps blast radius to at most marking an already-leased job completed (T-121-01 disposition: accept). No new threat surface.

## Verification Gates

- `uv run pytest -n auto`: 2637 passed, 10 skipped — GREEN
- `uv run ty check app/ tests/`: 0 errors — GREEN
- `uv run ruff check app/ tests/`: 0 issues — GREEN
- `grep -c "_claim_tier3_derived" app/routers/eval_remote.py`: 0 — dead import removed
- `grep -n "status == \"leased\"" app/routers/eval_remote.py`: present in `_apply_submit`
- `grep -n "DEFAULT_IDLE_SLEEP" scripts/remote_eval_worker.py`: `DEFAULT_IDLE_SLEEP: float = 1.0`

## Self-Check: PASSED

- `tests/test_eval_worker_endpoints.py` — exists, 16 tests collected, all pass
- `app/schemas/eval_remote.py` — exists, `job_id: int | None = None` in both models
- `app/routers/eval_remote.py` — exists, `claim_eval_job` imported, `_claim_tier3_derived` absent
- `scripts/remote_eval_worker.py` — exists, `DEFAULT_IDLE_SLEEP: float = 1.0`, `job_id` echoed
- Commits `4076df90`, `86ee2b89`, `910fdea3` — all present in git log
