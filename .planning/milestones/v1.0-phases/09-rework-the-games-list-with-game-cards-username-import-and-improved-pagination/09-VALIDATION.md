---
phase: 9
slug: rework-the-games-list-with-game-cards-username-import-and-improved-pagination
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-14
---

# Phase 9 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest + pytest-asyncio |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `uv run pytest tests/ -x -q` |
| **Full suite command** | `uv run pytest` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/ -x -q`
- **After every plan wave:** Run `uv run pytest`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 09-01-01 | 01 | 1 | move_count column | unit | `uv run pytest tests/test_import_service.py::test_move_count_populated -x` | ❌ W0 | ⬜ pending |
| 09-01-02 | 01 | 1 | username columns | unit | `uv run pytest tests/test_users_router.py -x` | ❌ W0 | ⬜ pending |
| 09-01-03 | 01 | 1 | GET /users/me/profile | integration | `uv run pytest tests/test_users_router.py::test_get_profile -x` | ❌ W0 | ⬜ pending |
| 09-01-04 | 01 | 1 | PUT /users/me/profile | integration | `uv run pytest tests/test_users_router.py::test_put_profile -x` | ❌ W0 | ⬜ pending |
| 09-02-01 | 02 | 1 | GameRecord expansion | unit | `uv run pytest tests/test_analysis_service.py -x` | Extend existing | ⬜ pending |
| 09-02-02 | 02 | 1 | import saves username | unit | `uv run pytest tests/test_import_service.py::test_username_saved_after_import -x` | ❌ W0 | ⬜ pending |
| 09-03-01 | 03 | 2 | Game cards render | manual-only | N/A | N/A | ⬜ pending |
| 09-03-02 | 03 | 2 | Pagination truncation | manual-only | N/A | N/A | ⬜ pending |
| 09-03-03 | 03 | 2 | Import modal redesign | manual-only | N/A | N/A | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_users_router.py` — stubs for profile GET/PUT endpoints (new file)
- [ ] Extend `tests/test_import_service.py` — add `test_username_saved_after_import` and `test_move_count_populated`

*Existing infrastructure covers all other phase requirements.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Game cards render with correct layout | Game card layout | No frontend test infrastructure | Verify cards show result badge, opponent, ratings, opening, TC, date, moves with correct visual hierarchy |
| Pagination shows truncated page numbers | Pagination improvements | Visual verification needed | Navigate multi-page results, verify `< 1 2 3 ... N >` pattern |
| Import modal two-mode UI | Import modal redesign | Interactive UI flow | Test first-time (input fields) and returning user (sync buttons) flows |
| Alembic migration up/down | DB schema changes | Structural validation | Run `alembic upgrade head` and `alembic downgrade -1` |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
