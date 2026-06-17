---
phase: 120
slug: headless-remote-trusted-operator-eval-worker-seed-048
status: draft
nyquist_compliant: true
wave_0_complete: true
created: 2026-06-14
---

# Phase 120 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x (async, per-run DB isolation) |
| **Config file** | pyproject.toml / tests/conftest.py |
| **Quick run command** | `uv run pytest tests/test_eval_worker_endpoints.py` |
| **Full suite command** | `uv run pytest -n auto` |
| **Estimated runtime** | ~quick: <30s · full: several min |

---

## Sampling Rate

- **After every task commit:** Run the relevant `uv run pytest <nodeid>` quick command
- **After every plan wave:** Run `uv run pytest -n auto`
- **Before `/gsd-verify-work`:** Full suite must be green + `uv run ty check app/ tests/` zero errors
- **Max feedback latency:** ~30 seconds (quick)

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 120-01-01 | 01 | 1 | D-1/D-5/D-6 (config + schemas + version helper) | — | Settings default empty (fail-closed in dev/CI) | smoke | `uv run ty check app/ && uv run python -c "from app.schemas.eval_remote import LeaseResponse, SubmitRequest, SubmitResponse"` | ✅ self | ⬜ pending |
| 120-02-01 | 02 | 2 | D-2/D-3/D-4/D-5/D-6 (lease + submit router) | T-120-01/02/03 | Constant-time token check; SEED-044 applied server-side; 401/403 without token | integration | `uv run pytest tests/test_eval_worker_endpoints.py -k "lease or submit or version"` | ✅ 120-02-02 | ⬜ pending |
| 120-02-02 | 02 | 2 | D-2/D-3/D-4/D-5/D-6 (integration tests) | T-120-01/02/03 | Auth, version gate, server-side shift, completion stamp, idempotency each named-tested | integration | `uv run pytest tests/test_eval_worker_endpoints.py -x` | ✅ self | ⬜ pending |
| 120-03-01 | 03 | 2 | D-1/D-2/D-3/D-5/D-6 (CLI worker) | T-120-01/02/03 | Token only in header (never logged); no client-side shift | smoke + HUMAN-UAT | `uv run ruff check scripts/remote_eval_worker.py && uv run python scripts/remote_eval_worker.py --help >/dev/null` + AST/grep no-shift assert | ✅ self | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

*No separate Wave 0 plan is warranted for this small, coarse-granularity phase.* The integration tests live in `tests/test_eval_worker_endpoints.py`, **co-located in plan 120-02** (Task 2) alongside the router they exercise (Task 1) — both in Wave 2. Plans 120-01 and 120-03 carry their own automated verification (ty/ruff/import smoke + AST/grep asserts), so no task chain runs without an automated check.

- [x] `tests/test_eval_worker_endpoints.py` — integration tests for lease + submit + auth + version gate (created in 120-02 Task 2)
- [x] Existing `tests/conftest.py` fixtures (per-run DB, authed client) cover setup

*Existing infrastructure (per-run DB, async client fixtures) covers most needs; only the new endpoint test file is added, co-located in 120-02.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| End-to-end worker run against a live server | D-1/D-3 | Requires the CLI worker + a running server + Stockfish binary | Run the worker CLI against a local dev server, confirm a game's evals land and `full_evals_completed_at` is stamped |

*Most endpoint behaviors have automated verification; the full worker loop is HUMAN-UAT.*

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references (tests co-located in 120-02; no separate Wave 0 plan)
- [x] No watch-mode flags
- [x] Feedback latency < 30s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved
