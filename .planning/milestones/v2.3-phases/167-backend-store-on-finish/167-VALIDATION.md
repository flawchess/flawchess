---
phase: 167
slug: backend-store-on-finish
status: planned
nyquist_compliant: true
wave_0_complete: false
created: 2026-07-11
---

# Phase 167 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x (async) |
| **Config file** | `pyproject.toml` (pytest config) + `tests/conftest.py` (per-run cloned DB) |
| **Quick run command** | `uv run pytest tests/services/test_store_service.py tests/routers/test_bots.py` |
| **Full suite command** | `uv run pytest -n auto -x` |
| **Estimated runtime** | ~5 s (targeted) / full suite parallel |

---

## Sampling Rate

- **After every task commit:** Run the targeted quick command for the touched file(s)
- **After every plan wave:** Run `uv run pytest -n auto -x`
- **Before `/gsd-verify-work`:** Full suite + `uv run ty check app/ tests/` green
- **Max feedback latency:** ~10 seconds (targeted)

---

## Per-Task Verification Map

> Filled by the planner from PLAN.md tasks. One row per task; every task must map to an automated command or a Wave 0 dependency.

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| P01-T1 | 167-01 | 1 | STORE-05 | T-167-01/02/03 | Request schema has no server-owned fields; UUID + blend-range + PGN-size validation | unit | `uv run pytest tests/schemas/test_bots.py -x` | ❌ W0 | ⬜ pending |
| P01-T2 | 167-01 | 1 | STORE-04, STORE-03 | T-167-04 | rating_source TEXT+CHECK; FK CASCADE | integration | `uv run pytest tests/repositories/test_bot_game_settings_repository.py -x` | ❌ W0 | ⬜ pending |
| P02-T1 | 167-02 | 1 | STORE-07 | T-167-05 | Flawchess excluded from default population even under opponent_type='bot' | unit/integration | `uv run pytest tests/repositories/test_query_utils.py -x` | ❌ W0 | ⬜ pending |
| P02-T2 | 167-02 | 1 | STORE-01, STORE-07 | T-167-06 | Library opt-in; no rating double-conversion | integration | `uv run pytest tests/services/test_library_service.py -x` | ⚠️ extend | ⬜ pending |
| P03-T1 | 167-03 | 2 | STORE-02 | T-167-07/08 | [%clk]/result gate → None (422); server-derived fields | unit | `uv run pytest tests/services/test_normalization.py -x` | ⚠️ extend | ⬜ pending |
| P03-T2 | 167-03 | 2 | STORE-03, STORE-05 | T-167-08/09/11 | Server-derived rating; idempotent single-transaction store | integration | `uv run pytest tests/services/test_store_bot_game_service.py -x` | ❌ W0 | ⬜ pending |
| P03-T3 | 167-03 | 2 | STORE-01, STORE-06 | T-167-07/10 | 422 gate; drain-eligible; guest-safe user_id from JWT | integration | `uv run pytest tests/routers/test_bots.py -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/services/test_store_service.py` — store + normalize + rating-conversion + idempotency stubs (STORE-01..06)
- [ ] `tests/routers/test_bots.py` — POST `/bots/games` contract, 422 `[%clk]` gate (STORE-02), auth/guest (STORE-06)
- [ ] `tests/repositories/test_query_utils.py` (extend) — `flawchess` default-exclusion (STORE-07) if not covered by existing file
- [ ] Reuse existing `tests/conftest.py` fixtures (per-run cloned DB) — no new framework, no DB reset

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Cold-drain auto-analyzes a stored non-guest bot game | STORE-01/06 | Drain is a background lottery process; end-to-end timing not deterministic in a unit test | Assert only that the stored game lands `evals_completed_at IS NULL` and is drain-eligible; full drain is covered by existing drain tests |

*The auto-analysis wiring itself is verified structurally (game is drain-eligible); the drain loop has its own suite.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
