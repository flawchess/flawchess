---
phase: 1
slug: data-foundation
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-11
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x + pytest-asyncio 0.23.x |
| **Config file** | `pyproject.toml` — `[tool.pytest.ini_options]` with `asyncio_mode = "auto"` |
| **Quick run command** | `uv run pytest tests/test_zobrist.py -x` |
| **Full suite command** | `uv run pytest` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/test_zobrist.py -x`
- **After every plan wave:** Run `uv run pytest`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 1-01-01 | 01 | 0 | IMP-06 | unit | `uv run pytest tests/test_zobrist.py -x` | ❌ W0 | ⬜ pending |
| 1-01-02 | 01 | 0 | INFRA-01 | smoke | `uv run alembic upgrade head` | ❌ W0 | ⬜ pending |
| 1-01-03 | 01 | 0 | INFRA-03 | integration | `uv run pytest tests/test_schema.py::test_duplicate_rejected -x` | ❌ W0 | ⬜ pending |
| 1-01-04 | 01 | 0 | IMP-05 | smoke | `uv run alembic upgrade head` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/__init__.py` — package marker
- [ ] `tests/conftest.py` — shared fixtures (chess.Board instances, minimal async session for integration tests)
- [ ] `tests/test_zobrist.py` — covers IMP-06 (hash module unit tests, no DB needed)
- [ ] `tests/test_schema.py` — covers INFRA-01, INFRA-03, IMP-05 (requires live test DB or async engine with `create_all`)
- [ ] Framework install: `uv add --dev pytest pytest-asyncio` — verify in pyproject.toml

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Composite indexes visible in DB | INFRA-01 | Requires psql introspection | Run `uv run alembic upgrade head`, then `\d game_positions` in psql to verify indexes |
| All metadata columns present | IMP-05 | Schema verification | Run `\d games` in psql after migration |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
