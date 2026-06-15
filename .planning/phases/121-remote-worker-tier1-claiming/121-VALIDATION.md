---
phase: 121
slug: remote-worker-tier1-claiming
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-06-15
---

# Phase 121 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x (async, per-run DB clone from migrated template) |
| **Config file** | `pyproject.toml` + `tests/conftest.py` |
| **Quick run command** | `uv run pytest tests/test_eval_worker_endpoints.py` |
| **Full suite command** | `uv run pytest -n auto` |
| **Estimated runtime** | quick ~10–30s · full ~few min |

No DB reset required — tests run against the per-run cloned test DB (`tests/conftest.py`).

---

## Sampling Rate

- **After every task commit:** Run the quick command for the touched area (eval worker endpoints / eval queue service).
- **After every plan wave:** Run `uv run pytest -n auto` (full backend suite).
- **Before `/gsd-verify-work`:** Full suite + `uv run ty check app/ tests/` must be green.
- **Max feedback latency:** ~30 seconds (quick), few minutes (full).

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 121-01-* | 01 | 1 | tier-1 claim via lease | — | lease handler claims tier-1 > tier-2 > tier-3 via `claim_eval_job`; returns 204 on no work | unit | `uv run pytest tests/test_eval_worker_endpoints.py` | ✅ existing (mocks updated) | ⬜ pending |
| 121-01-* | 01 | 1 | job_id round-trip + submit stamp | — | submit stamps `eval_jobs.status='completed'` only when `job_id` present AND `status='leased'`; tier-3 (`job_id=None`) writes nothing | unit | `uv run pytest tests/test_eval_worker_endpoints.py` | ✅ existing | ⬜ pending |
| 121-01-* | 01 | 1 | no double-claim under FCFS | — | concurrent server-drain + remote lease never double-claim (SKIP LOCKED) | integration | `uv run pytest -n auto -k eval_queue` | ⚠️ may need new test | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] Update `tests/test_eval_worker_endpoints.py` — two existing tests mock `_claim_tier3_derived` directly and will break after the import swap; re-target them to mock `claim_eval_job` returning a `ClaimedJob` (with and without `job_id`).
- [ ] Add a test asserting the submit handler stamps `eval_jobs` only when `job_id` is present and `status='leased'` (late-submit guard), and writes nothing for `job_id=None`.

*Existing infrastructure (pytest + per-run DB clone) covers all other phase requirements.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Soak: concurrent server drain + remote worker, no tier-1/tier-3 double-claim and submit correctly stamps `eval_jobs` | SEED-048 verification | Requires a real second worker process + live enqueue under load; not reproducible in unit tests | Run server drain + `scripts/remote_eval_worker.py` against dev DB, enqueue several single-game analyses while server is mid-game, confirm each job is claimed once and stamped `completed`. |

---

## Validation Sign-Off

- [ ] All tasks have automated verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s (quick)
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
