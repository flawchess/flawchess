---
phase: 64
slug: llm-logs-table-async-repo
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-20
---

# Phase 64 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x (async via pytest-asyncio) |
| **Config file** | `pyproject.toml` (`[tool.pytest.ini_options]`) |
| **Quick run command** | `uv run pytest tests/repositories/test_llm_log_repository.py tests/models/test_llm_log_cascade.py tests/alembic/test_llm_logs_migration.py -x` |
| **Full suite command** | `uv run ruff check . && uv run ty check app/ tests/ && uv run pytest -x` |
| **Estimated runtime** | ~30 seconds (phase tests only); ~3 min (full suite) |

---

## Sampling Rate

- **After every task commit:** Run the quick command scoped to files touched by the task.
- **After every plan wave:** Run `uv run pytest tests/ -x` plus `uv run ty check app/ tests/`.
- **Before `/gsd-verify-work`:** Full suite must be green (ruff + ty + pytest).
- **Max feedback latency:** 60 seconds.

---

## Per-Task Verification Map

Populated by the planner once PLAN.md files exist. Each task in each plan gets one row here with:
- `Task ID`, `Plan`, `Wave`, `Requirement`, `Threat Ref`, `Secure Behavior`, `Test Type`, `Automated Command`, `File Exists`, `Status`.

---

## Wave 0 Requirements

- [ ] `tests/repositories/test_llm_log_repository.py` — stubs for LOG-01, LOG-02, LOG-04
- [ ] `tests/models/test_llm_log_cascade.py` — stub for LOG-01 cascade (SC #3)
- [ ] `tests/alembic/test_llm_logs_migration.py` — stub for LOG-03 schema smoke (SC #1)
- [ ] `tests/conftest.py` — add `fresh_test_user` fixture if not present (required because D-02 own-session pattern bypasses the rollback-scoped `db_session` fixture)
- [ ] `pyproject.toml` — pin `genai-prices ~= 0.0.56`

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Prod migration `alembic upgrade head` runs on deploy | LOG-01 | Prod DB access; automated smoke uses dev DB | Deploy branch; `ssh flawchess 'cd /opt/flawchess && docker compose logs --tail=50 backend'` — confirm migration applied without error |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
