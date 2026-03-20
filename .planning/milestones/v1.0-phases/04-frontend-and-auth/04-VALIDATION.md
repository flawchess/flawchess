---
phase: 4
slug: frontend-and-auth
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-12
---

# Phase 4 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x + pytest-asyncio 0.23.x (backend); no frontend test framework (manual UAT) |
| **Config file** | `pyproject.toml` (`[tool.pytest.ini_options]`, `asyncio_mode = "auto"`) |
| **Quick run command** | `uv run pytest tests/test_auth.py -x` |
| **Full suite command** | `uv run pytest` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/test_auth.py -x`
- **After every plan wave:** Run `uv run pytest`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 04-01-01 | 01 | 0 | AUTH-01 | integration | `uv run pytest tests/test_auth.py::test_register -x` | ❌ W0 | ⬜ pending |
| 04-01-02 | 01 | 0 | AUTH-01 | integration | `uv run pytest tests/test_auth.py::test_login -x` | ❌ W0 | ⬜ pending |
| 04-01-03 | 01 | 0 | AUTH-02 | integration | `uv run pytest tests/test_auth.py::test_analysis_requires_auth -x` | ❌ W0 | ⬜ pending |
| 04-01-04 | 01 | 0 | AUTH-02 | integration | `uv run pytest tests/test_auth.py::test_import_requires_auth -x` | ❌ W0 | ⬜ pending |
| 04-01-05 | 01 | 0 | AUTH-02 | integration | `uv run pytest tests/test_auth.py::test_user_isolation -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_auth.py` — stubs for AUTH-01, AUTH-02 (register, login, 401 protection, user isolation)
- [ ] `tests/conftest.py` — add `create_test_user()` async fixture using fastapi-users UserManager
- [ ] Backend: `uv add "fastapi-users[sqlalchemy,oauth]" httpx-oauth` — install auth dependencies

*Existing test infrastructure in `tests/` covers phases 1-3; new `test_auth.py` needed for phase 4 auth requirements.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Zobrist JS hash matches Python hash for starting position | ANL-01 | Browser-only JS execution | Open browser console, compute hash for starting FEN, compare with Python `zobrist.compute_hash()` output |
| Zobrist JS hash matches Python hash after 1.e4 | ANL-01 | Browser-only JS execution | Play 1.e4 on board, verify hash in console matches Python computation |
| Interactive board allows position input via moves | ANL-01 | UI interaction | Play moves on board, verify move list updates, navigate back/forward, reset works |
| Filter controls update results without reload | ANL-01 | UI interaction | Change time control, rated, color filters — verify results update in-place |
| Import modal opens, submits, shows progress toast | AUTH-01 | UI interaction | Click Import Games, enter username, submit, verify toast appears with progress |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
