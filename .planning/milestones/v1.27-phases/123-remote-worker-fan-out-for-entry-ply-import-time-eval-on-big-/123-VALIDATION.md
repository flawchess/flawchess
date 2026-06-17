---
phase: 123
slug: remote-worker-fan-out-for-entry-ply-import-time-eval-on-big
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-06-16
---

# Phase 123 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x (async, per-run Postgres DB) |
| **Config file** | `pyproject.toml` (`[tool.pytest.ini_options]`) |
| **Quick run command** | `uv run pytest tests/test_eval_worker_endpoints.py` |
| **Full suite command** | `uv run pytest -n auto` |
| **Estimated runtime** | ~60–90 seconds (full suite, parallel) |

---

## Sampling Rate

- **After every task commit:** Run the targeted endpoint/drain test file for the surface touched
- **After every plan wave:** Run `uv run pytest -n auto`
- **Before `/gsd-verify-work`:** Full suite must be green + `uv run ty check app/ tests/` clean
- **Max feedback latency:** ~90 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 123-01-01 | 01 | 1 | D-3/D-9 | — | Migration adds nullable lease columns (`VARCHAR(16)` leased_by); no data loss | unit | `uv run pytest tests/test_eval_worker_endpoints.py` | ✅ | ⬜ pending |
| 123-01-02 | 01 | 1 | D-01/D-3/D-4 | — | Shared SKIP-LOCKED LIFO `_claim_entry_eval_games` partitions games; no double-lease | unit | `uv run pytest tests/ -k drain` | ✅ | ⬜ pending |
| 123-01-03 | 01 | 1 | D-02/D-03 | — | `_pick_pending_game_ids` server-lease (always drains, not backlog-gated); `ENTRY_LEASE_*` constants | unit | `uv run pytest tests/ -k drain` | ✅ | ⬜ pending |
| 123-02-01 | 02 | 2 | D-05/D-10 | — | `scope` param `Literal[...] \| None`; absent → bundled tier-1>2>3 unchanged | unit | `uv run pytest tests/test_eval_worker_endpoints.py` | ✅ | ⬜ pending |
| 123-02-02 | 02 | 2 | D-2/D-5/D-7 | T-123-01 | `/entry-lease`+`/entry-submit` via `require_operator_token`; D-5 probe `OFFSET=THRESHOLD-1`; `_apply_eval_results` NO-shift | unit | `uv run pytest tests/test_eval_worker_endpoints.py` | ✅ | ⬜ pending |
| 123-02-03 | 02 | 2 | D-05/D-10 | T-123-01 | Endpoint round-trip + auth-reject + `X-Worker-Id`-absent → `"remote-worker"` tests | unit | `uv run pytest tests/test_eval_worker_endpoints.py` | ✅ | ⬜ pending |
| 123-03-01 | 03 | 3 | D-10 | — | `--worker-id` flag + random base36 generator (<10 chars); `X-Worker-Id` header | unit | `uv run pytest tests/ -k worker` | ✅ | ⬜ pending |
| 123-03-02 | 03 | 3 | D-1/D-6/D-8 | — | Ladder (explicit→entry-lease→idle); `pool.evaluate` depth-15 NOT `evaluate_nodes_with_pv` | unit | `uv run pytest tests/ -k worker` | ✅ | ⬜ pending |
| 123-03-03 | 03 | 3 | D-1/D-6 | — | Ladder sequencing + entry-ply default-on regression tests | unit | `uv run pytest tests/ -k worker` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

*Task IDs are indicative of the 3-plan / 3-wave structure; each PLAN.md holds the authoritative task list and `<automated>` verify blocks.*

---

## Wave 0 Requirements

*Existing infrastructure covers all phase requirements.* `tests/test_eval_worker_endpoints.py` already exercises the lease/submit endpoint patterns (operator-token auth, claim round-trips); the per-run Postgres template applies the new migration automatically, so lease-column behavior is testable without new fixtures.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| End-to-end big-first-import latency reduction | SEED-051 goal | Requires a real ≥300-game import against a live worker fleet; not reproducible in unit tests | Trigger a big first import in dev/prod with an entry-capable worker running; confirm `evals_completed_at` populates faster than server-pool-only and that `entry_eval_leased_by` shows distinct worker IDs |
| Mixed-fleet backward compat | SEED-051 D-05/D-10 | Needs an old (scope-absent, header-absent) worker binary alongside a new one | Run an un-upgraded worker against the new server; confirm it still drains full-ply and never touches entry-ply, and `leased_by` falls back to `"remote-worker"` |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 90s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
