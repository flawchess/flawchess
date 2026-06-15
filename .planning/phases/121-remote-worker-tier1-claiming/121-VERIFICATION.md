---
phase: 121-remote-worker-tier1-claiming
verified: 2026-06-15T10:00:00Z
status: passed
score: 8/8
overrides_applied: 0
---

# Phase 121: Remote-Worker Tier-1 Claiming — Verification Report

**Phase Goal:** A remote eval worker can claim tier-1 (single-game "analyze") requests,
not just the tier-3 idle backlog, so when the server pool is mid-game on another job, a
second idle machine can pick up a freshly-enqueued single-game analysis and shorten
click-to-pickup latency. FCFS — server's in-process drain still usually wins tier-1 when
idle; this targets the server-busy overflow case. Bias-tier-1-to-faster-box and
interruptible tier-3 are explicitly DEFERRED.

**Verified:** 2026-06-15  
**Status:** PASSED  
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | POST /api/eval/remote/lease calls claim_eval_job (tier-1 > tier-2 > tier-3), not _claim_tier3_derived | VERIFIED | `grep -c "_claim_tier3_derived" app/routers/eval_remote.py` → 0; line 337: `claim = await claim_eval_job(worker_id=_WORKER_ID_REMOTE)` |
| 2 | Lease response carries job_id = eval_jobs.id for tier-1/tier-2, None for tier-3 | VERIFIED | `app/schemas/eval_remote.py:27` `job_id: int | None = None` on `LeaseResponse`; router line 394: `job_id=claim.job_id` passed into response; tier-3 mock asserts `body["job_id"] is None` in `test_lease_returns_positions` |
| 3 | Worker echoes job_id back on submit without interpreting it | VERIFIED | `scripts/remote_eval_worker.py:168` `job_id = data.get("job_id")`; line 183 `"job_id": job_id` in submit payload |
| 4 | Submit stamps eval_jobs only when job_id present AND row status='leased' AND stamp_complete=True; tier-3 (job_id=None) writes nothing; late submits are no-ops | VERIFIED | `app/routers/eval_remote.py:283-293`: `if body.job_id is not None and stamp_complete:` + `WHERE jobs_table.c.status == "leased"`; R3 test asserts stamp, R4 asserts tier-3 no-write, R5 asserts late-submit no-op |
| 5 | WR-01 fix: lichess-eval defer path calls release_job(job_id) so the eval_jobs row returns to 'pending' immediately | VERIFIED | `app/routers/eval_remote.py:352-355`: `if claim.job_id is not None: await release_job(claim.job_id)`; `release_job` exists at `eval_queue_service.py:533`; `test_lichess_eval_game_claim_releases_lease` asserts status='pending' and leased_by=None after deferral |
| 6 | DEFAULT_IDLE_SLEEP == 1.0 in scripts/remote_eval_worker.py | VERIFIED | `scripts/remote_eval_worker.py:59`: `DEFAULT_IDLE_SLEEP: float = 1.0`; comment documents the change from 5.0; R6 constant test asserts equality |
| 7 | Operator-token auth (require_operator_token) unchanged on both endpoints | VERIFIED | `app/routers/eval_remote.py:315,401`: both `lease_eval_game` and `submit_eval` carry `_auth: Annotated[None, Depends(require_operator_token)]`; existing auth tests (403/401) all pass |
| 8 | Deferred scope fence honored: no bias-to-fast-box / server grace-yield / interruptible-tier-3 / ply-batch chunking added | VERIFIED | `grep "grace.yield\|bias.*fast\|interruptible\|ply.batch\|chunking"` across all three modified files → no matches |

**Score:** 8/8 truths verified

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `app/schemas/eval_remote.py` | `job_id: int | None = None` on LeaseResponse and SubmitRequest | VERIFIED | Lines 27 and 45 — both fields present with opaque-token comment |
| `app/routers/eval_remote.py` | claim_eval_job wired; _claim_tier3_derived removed; _apply_submit stamps eval_jobs when job_id present | VERIFIED | Import on line 56; claim call on line 337; stamp at lines 283-293; dead import count = 0 |
| `scripts/remote_eval_worker.py` | DEFAULT_IDLE_SLEEP = 1.0 + job_id echo on submit | VERIFIED | Line 59 constant; line 168 data.get + line 183 payload key |
| `tests/test_eval_worker_endpoints.py` | TestTier1Claiming class + re-targeted claim mocks + WR-01 test | VERIFIED | 17 tests collected, all 17 pass; class contains R1/R3/R4/R5/R6/WR-01 |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `app/routers/eval_remote.py:lease_eval_game` | `app.services.eval_queue_service.claim_eval_job` | Direct call, no caller-owned session | VERIFIED | Line 337: bare `await claim_eval_job(worker_id=_WORKER_ID_REMOTE)` — no `async with async_session_maker()` wrapper |
| `app/routers/eval_remote.py:_apply_submit` | eval_jobs UPDATE | `WHERE id == body.job_id AND status == 'leased'` | VERIFIED | Lines 283-293: guard condition + SQLAlchemy update statement |
| `scripts/remote_eval_worker.py:_run_cycle` | submit payload | `job_id = data.get("job_id")` echoed back | VERIFIED | Line 168 reads from lease response dict; line 183 includes it in submit payload |
| `app/routers/eval_remote.py:lease_eval_game` (lichess defer) | `app.services.eval_queue_service.release_job` | `await release_job(claim.job_id)` | VERIFIED | Lines 352-355: guarded by `if claim.job_id is not None` |

---

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Tier-3 lease returns job_id=None | `test_lease_returns_positions` | assert `body["job_id"] is None` passes | PASS |
| Tier-1 lease returns correct job_id (R1) | `TestTier1Claiming::test_tier1_lease_returns_job_id` | assert `body["job_id"] == 42` passes | PASS |
| Submit stamps eval_jobs (R3) | `TestTier1Claiming::test_submit_with_job_id_stamps_eval_jobs` | status='completed', completed_at IS NOT NULL | PASS |
| Tier-3 submit does not touch eval_jobs (R4) | `TestTier1Claiming::test_submit_without_job_id_does_not_touch_eval_jobs` | sentinel row status='leased' unchanged | PASS |
| Late-submit no-op (R5) | `TestTier1Claiming::test_late_submit_does_not_corrupt_eval_jobs` | non-'leased' row unchanged after submit | PASS |
| WR-01 lichess defer releases lease | `TestTier1Claiming::test_lichess_eval_game_claim_releases_lease` | status='pending', leased_by=None | PASS |
| DEFAULT_IDLE_SLEEP == 1.0 (R6) | `TestTier1Claiming::test_default_idle_sleep_is_one_second` | assertion passes | PASS |
| Full eval worker suite | `uv run pytest tests/test_eval_worker_endpoints.py -x` | 17/17 passed in 4.00s | PASS |

---

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| — | — | None | — | No TBD/FIXME/XXX markers, no stubs, no dead imports in modified files |

---

### Human Verification Required

None. All observable truths verified programmatically via code inspection and automated tests.

The PLAN listed a manual soak as a non-completion gate ("run the server drain + remote_eval_worker.py against dev DB; enqueue several single-game analyses while the server pool is mid-game; confirm each job is claimed exactly once"). This is correctly scoped as a monitoring/confidence check, not a code correctness gate. The SKIP LOCKED double-claim protection is DB-level and covered by existing QUEUE-06 tests; the stamp path is proven by R3/R5. No human verification item is required to declare the phase goal achieved.

---

## Summary

All 8 must-have truths are verified. The codebase delivers the phase goal exactly as specified:

- `lease_eval_game` now calls `claim_eval_job(worker_id="remote-worker")` (tier-1 > tier-2 > tier-3, SKIP LOCKED, stale-lease sweep) — the dead `_claim_tier3_derived` import is gone (count = 0).
- The `job_id` opaque token threads lease → submit: `LeaseResponse.job_id` carries `eval_jobs.id` for tier-1/tier-2, `None` for tier-3; `SubmitRequest.job_id` echoes it back; `_apply_submit` stamps `eval_jobs` only when both `body.job_id is not None` and `stamp_complete=True`, guarded by `WHERE status='leased'`.
- WR-01 (review finding): the lichess-eval defer path calls `release_job(claim.job_id)` before returning 204, so the `eval_jobs` row returns to 'pending' immediately instead of sitting leased for the full 120s TTL.
- `DEFAULT_IDLE_SLEEP` lowered from 5.0 to 1.0.
- Operator-token auth unchanged on both endpoints.
- Deferred items (bias-to-fast-box, interruptible tier-3) are absent from all modified files.
- 17 eval-worker tests pass (including all TestTier1Claiming tests: R1, R3, R4, R5, R6, WR-01); ty and ruff are clean.

---

_Verified: 2026-06-15T10:00:00Z_  
_Verifier: Claude (gsd-verifier)_
