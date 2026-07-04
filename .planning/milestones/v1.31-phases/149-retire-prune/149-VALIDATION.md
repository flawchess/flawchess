---
phase: 149
slug: retire-prune
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-07-04
---

# Phase 149 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (per-run cloned DB, parallel-safe) |
| **Config file** | `pyproject.toml` / `tests/conftest.py` |
| **Quick run command** | `uv run pytest tests/test_eval_worker_endpoints.py tests/test_imports.py -x` |
| **Full suite command** | `uv run pytest -n auto -x` |
| **Estimated runtime** | ~90–180 seconds (full suite) |

---

## Sampling Rate

- **After every task commit:** Run the quick run command scoped to the touched module
- **After every plan wave:** Run `uv run pytest -n auto -x`
- **Before `/gsd-verify-work`:** Full suite must be green + `uv run ty check app/ tests/` zero errors
- **Max feedback latency:** ~180 seconds

---

## Per-Task Verification Map

*Populated by the planner from PLAN.md tasks. Deletion tasks verify via "full suite green + no live-lane regression"; migration tasks verify via alembic up/down reversibility + a targeted behavior test.*

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 149-01 | 01 | 1 | PRUNE-06, PRUNE-04 | — | Heartbeat upsert wired into 3 live submit lanes; version telemetry only (no authz on X-Worker-Id) | unit+migration | `uv run pytest tests/test_eval_worker_endpoints.py && uv run alembic upgrade head && uv run alembic downgrade -1` | ✅ | ⬜ pending |
| 149-02 | 02 | 1 | PRUNE-03 | — | Unknown chess.com result skips via None + Sentry capture; GameResult not widened | unit | `uv run pytest tests/ -k normalize` | ✅ | ⬜ pending |
| 149-03 | 03 | 2 | PRUNE-01 | — | Gen-1 lanes gone, entry/atomic/flaw-blob lanes intact | unit | `uv run pytest tests/test_eval_worker_endpoints.py` | ✅ | ⬜ pending |
| 149-04 | 04 | 2 | PRUNE-02 | — | Dead weight removed, no live-path behavior change | unit | `uv run pytest -n auto -x` | ✅ | ⬜ pending |
| 149-05 | 05 | 2 | PRUNE-05 | — | Durable import guard; user-scoped IntegrityError idempotency | unit+migration | `uv run pytest tests/test_imports.py && uv run alembic upgrade head && uv run alembic downgrade -1` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky. Per-task granularity + `nyquist_compliant: true` finalized before `/gsd-verify-work`.*

---

## Wave 0 Requirements

- [ ] Atomic-lane `job_id` completion-stamping test (RESEARCH Pitfall 1 — no atomic equivalent exists before deleting `TestTier1Claiming`)

*Otherwise: existing infrastructure covers all phase requirements — this is a deletion + migration phase against a mature suite.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Prod fleet emits heartbeats after deploy | PRUNE-06 | Requires live worker fleet traffic | Post-deploy: `SELECT worker_id, last_seen, submit_count FROM worker_heartbeats ORDER BY last_seen DESC` shows recent rows |

*All in-scope server behaviors have automated verification; the above is post-deploy observability only.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 180s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
