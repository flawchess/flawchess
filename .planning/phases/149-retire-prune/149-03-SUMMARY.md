---
phase: 149-retire-prune
plan: 03
subsystem: api
tags: [fastapi, sqlalchemy, pytest, eval-worker, remote-worker, dead-code-removal]

# Dependency graph
requires:
  - phase: 149-01
    provides: worker_heartbeats registry wired into _apply_atomic_submit (job_id / worker_schema_version fields this plan's new tests depend on)
provides:
  - Deletion of the Gen-1 remote-eval protocol (POST /lease, POST /submit, _apply_submit, worker _handle_full_ply_response)
  - Atomic-lane test coverage for job_id -> eval_jobs completion-stamping (real / stale / none) and the is_lichess_eval_game release+204 branch, ported before the Gen-1 tests were deleted
  - Surgical removal of 29 Gen-1-only / Gen-1-dependent tests from tests/test_eval_worker_endpoints.py; all entry/atomic/flaw-blob lane tests untouched
affects: [150-consolidate-write-path]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Coverage-before-deletion: when a test class is the SOLE end-to-end coverage of a shared code path (eval_jobs stamping, lichess-skip), port replacement tests to the surviving lane in one commit BEFORE deleting the class in a later commit — never delete-then-backfill"
    - "Relocate, don't delete, a test whose assertion is unrelated to the deletion trigger even when it lives inside the doomed class/file region (test_default_idle_sleep_is_one_second moved to module level)"

key-files:
  created: []
  modified:
    - tests/test_eval_worker_endpoints.py
    - app/routers/eval_remote.py
    - scripts/remote_eval_worker.py

key-decisions:
  - "Deleted 29 Gen-1 tests, not the RESEARCH-cited ~28 — TestMultipv2BlobsRemote actually has 3 /submit-only methods, not 2 as 149-RESEARCH.md's surgery map stated; verified via a full AST + URL-reference scan of all 95 original test functions before any deletion"
  - "test_default_idle_sleep_is_one_second (tests scripts/remote_eval_worker.py's DEFAULT_IDLE_SLEEP constant, not a /lease or /submit behavior) relocated out of TestTier1Claiming to a standalone module-level function instead of being deleted with the rest of the class"
  - "Did not port dedicated atomic-lane tests for the scope= query param or the X-Worker-Id header on /atomic-lease (Gen-1's test_scope_* / test_worker_id_*_full_lease) — both endpoints share the exact same claim_eval_job()/worker_id_label() call sites as the deleted lease_eval_game, and worker_id_label is already exercised via the kept entry-lease variants; per the plan's own text this duplication is moot, not a coverage gap requiring Task-1-style porting"

requirements-completed: [PRUNE-01]

coverage:
  - id: D1
    description: "Atomic-lane tests added for job_id -> eval_jobs completion-stamping (real job_id, late/stale job_id no-op, job_id=None) and the is_lichess_eval_game release+204 branch, all passing BEFORE any Gen-1 deletion"
    requirement: "PRUNE-01"
    verification:
      - kind: unit
        ref: "tests/test_eval_worker_endpoints.py::TestAtomicSubmitEndpoint::test_atomic_submit_with_job_id_stamps_eval_jobs"
        status: pass
      - kind: unit
        ref: "tests/test_eval_worker_endpoints.py::TestAtomicSubmitEndpoint::test_atomic_submit_late_job_id_is_noop"
        status: pass
      - kind: unit
        ref: "tests/test_eval_worker_endpoints.py::TestAtomicSubmitEndpoint::test_atomic_submit_without_job_id_does_not_touch_eval_jobs"
        status: pass
      - kind: unit
        ref: "tests/test_eval_worker_endpoints.py::TestAtomicLeaseEndpoint::test_atomic_lease_lichess_eval_game_releases_lease"
        status: pass
    human_judgment: false
  - id: D2
    description: "POST /lease, POST /submit, _apply_submit, and the worker's _handle_full_ply_response handler no longer exist; all live lanes (/entry-lease, /entry-submit, /atomic-lease, /atomic-submit, /flaw-blob-lease, /flaw-blob-submit) remain registered"
    requirement: "PRUNE-01"
    verification:
      - kind: other
        ref: "grep -rn 'def _apply_submit|_handle_full_ply_response' app/ scripts/ (empty output)"
        status: pass
      - kind: other
        ref: "grep -n '\"/flaw-blob-' app/routers/eval_remote.py (2 routes present)"
        status: pass
      - kind: unit
        ref: "uv run ty check app/ tests/"
        status: pass
    human_judgment: false
  - id: D3
    description: "Surgical test removal: exactly the Gen-1-only/Gen-1-dependent tests deleted; all entry/atomic/flaw-blob lane tests and the 4 new atomic replacement tests remain, full backend suite green"
    requirement: "PRUNE-01"
    verification:
      - kind: unit
        ref: "uv run pytest tests/test_eval_worker_endpoints.py (70 passed; was 95, -29 deleted +4 added)"
        status: pass
      - kind: unit
        ref: "uv run pytest -n auto -x (full backend suite)"
        status: pass
    human_judgment: false

# Metrics
duration: 25min
completed: 2026-07-04
status: complete
---

# Phase 149 Plan 03: Retire the Gen-1 eval protocol Summary

**Deleted `POST /lease` + `POST /submit` + `_apply_submit` + the worker's dead `_handle_full_ply_response` handler, after first porting the only end-to-end coverage of job_id→eval_jobs stamping and the lichess-eval-game release branch to the atomic lane**

## Performance

- **Duration:** ~25 min
- **Started:** 2026-07-04T13:47Z (approx, file reads)
- **Completed:** 2026-07-04T14:08:55+02:00
- **Tasks:** 3
- **Files modified:** 3 (`tests/test_eval_worker_endpoints.py`, `app/routers/eval_remote.py`, `scripts/remote_eval_worker.py`)

## Accomplishments

- Added 4 atomic-lane tests (`TestAtomicSubmitEndpoint`/`TestAtomicLeaseEndpoint`) porting `TestTier1Claiming`'s job_id-stamping and lichess-eval-game-release coverage, confirmed green **before** any deletion — closing the coverage gap 149-RESEARCH.md's Pitfall 1 warned about.
- Deleted the dead Gen-1 protocol server-side: `POST /lease`, `POST /submit`, `_apply_submit` (`app/routers/eval_remote.py`), and the worker's already-unreachable `_handle_full_ply_response` (`scripts/remote_eval_worker.py`). `_build_lease_positions` and every helper `_apply_submit` called are shared with `/atomic-lease`/`/atomic-submit` and were left untouched.
- Surgically removed 29 Gen-1-only/Gen-1-dependent tests from `tests/test_eval_worker_endpoints.py` (95 → 70 collected, after +4 new), relocating the one non-Gen-1-specific test in the doomed class (`test_default_idle_sleep_is_one_second`) to module level instead of deleting it.
- Full backend suite green (3183 passed, 18 skipped) and `ty check app/ tests/` zero errors after each task.

## Task Commits

Each task was committed atomically:

1. **Task 1: Port job_id stamping + lichess-skip coverage to the atomic lane** - `0770a11a` (test)
2. **Task 2: Delete Gen-1 endpoints, _apply_submit, and the worker handler** - `99b07b67` (feat)
3. **Task 3: Surgical removal of the 28(29) Gen-1 tests** - `628beacf` (test)

**Plan metadata:** (this commit, below)

## Files Created/Modified

- `tests/test_eval_worker_endpoints.py` - Added 4 atomic-lane replacement tests (Task 1); removed 29 Gen-1-only/Gen-1-dependent tests, relocated 1 test, dropped dangling `_LEASE_URL`/`_SUBMIT_URL` constants and stale docstring bullets (Task 3)
- `app/routers/eval_remote.py` - Deleted `POST /lease`, `POST /submit`, `_apply_submit`; dropped now-unused `SubmitRequest`/`SubmitResponse`/`LeaseResponse`/`PvNode` imports; updated module + endpoint docstrings
- `scripts/remote_eval_worker.py` - Deleted `_handle_full_ply_response` (already unreachable per Phase 147 D-02/D-05); updated stale "old pair stays live" comments

## Decisions Made

- **29 tests deleted, not ~28.** A full AST-based scan of all 95 original test functions/methods, tagged by which of the 8 endpoint-URL constants each references, found `TestMultipv2BlobsRemote` has 3 `/submit`-only methods (not 2 as 149-RESEARCH.md's surgery map stated). Used the mechanically-verified count over the RESEARCH prose per Pitfall 5's own guidance ("re-run the line-boundary scan to get fresh numbers"). The plan's acceptance criteria used "~28" explicitly allowing this variance.
- **Relocated, not deleted, `test_default_idle_sleep_is_one_second`.** This test asserts `scripts/remote_eval_worker.py::DEFAULT_IDLE_SLEEP == 1.0` — a worker-script constant used by every lane's D-06 ladder (not a `/lease` or `/submit` behavior), so it doesn't belong in the "Gen-1 coverage" bucket the plan asked to port or delete. Moved to a standalone module-level function immediately before where `TestTier1Claiming` used to live.
- **No new atomic-lane test for the `scope=` param or `X-Worker-Id` on `/atomic-lease`.** Both concepts are already exercised on the exact same code path: `atomic_lease_eval_game` calls `claim_eval_job(worker_id=worker_id, scope=scope)` identically to the deleted `lease_eval_game`, and `worker_id_label` is already exercised by the kept `entry-lease` worker-id tests. This mirrors the plan's own framing of these three deletions as moot duplication, distinct from the job_id/lichess-skip gap that Task 1 was specifically scoped to close.

## Deviations from Plan

None requiring Rule 1-4 classification — the only variance from the plan's literal numbers is the 28→29 test count above, which the plan's own acceptance criteria phrased as an approximation ("~28") and attributed to a documented RESEARCH miscount (Pitfall 5 anticipated line-number/count drift during surgical deletion).

## Issues Encountered

None. All three tasks executed in the required order (coverage-port → deletion → test-surgery); each task's verification command passed on first run.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- The remote eval worker fleet now has exactly two live write-path lanes in this router (`/atomic-lease`+`/atomic-submit`, `/entry-lease`+`/entry-submit`) plus the isolated `/flaw-blob-lease`+`/flaw-blob-submit` tier-4 pair — down from three, setting up Phase 150 (Consolidate Write Path) to unify the remaining two rather than three copies.
- **Manual follow-up before this branch merges/deploys:** 149-RESEARCH.md's Runtime State Inventory calls for re-running the prod-log zero-legacy-traffic grep (`docker compose logs backend | grep -c '/eval/remote/submit '` filtered to a recent window) immediately before shipping, since the "zero /lease+/submit hits" claim was last verified in the CONTEXT.md session, not re-run here. Not blocking for phase completion — deferred to the deploy/ship step per CLAUDE.md's deploy skill.
- 149-04 (if any) or Phase 150 can proceed; no blockers from this plan.

---
*Phase: 149-retire-prune*
*Completed: 2026-07-04*

## Self-Check: PASSED

All claimed files and commit hashes verified present.
