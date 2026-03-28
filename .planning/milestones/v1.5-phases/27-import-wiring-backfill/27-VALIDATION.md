---
phase: 27
slug: import-wiring-backfill
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-24
---

# Phase 27 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x with pytest-asyncio |
| **Config file** | pyproject.toml |
| **Quick run command** | `uv run pytest tests/test_position_classifier.py tests/test_import_service.py -x` |
| **Full suite command** | `uv run pytest` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/test_position_classifier.py tests/test_import_service.py -x`
- **After every plan wave:** Run `uv run pytest`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 27-01-01 | 01 | 1 | PMETA-05 | unit/integration | `uv run pytest tests/test_import_service.py -x` | ✅ | ⬜ pending |
| 27-02-01 | 02 | 2 | PMETA-05 | integration | `uv run pytest tests/test_backfill.py -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_backfill.py` — stubs for backfill script tests (PMETA-05 backfill path)
- [ ] `scripts/` directory — create if not exists

*Existing infrastructure covers import wiring tests (test_import_service.py exists).*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Backfill runs on production DB without OOM | PMETA-05 | Requires production environment with real data | SSH into server, run script with `docker stats` monitoring |
| VACUUM reduces dead tuples | PMETA-05 | Requires production DB state | Run `SELECT n_dead_tup FROM pg_stat_user_tables WHERE relname='game_positions'` before and after |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
