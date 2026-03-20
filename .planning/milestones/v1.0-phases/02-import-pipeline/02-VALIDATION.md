---
phase: 2
slug: import-pipeline
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-11
---

# Phase 2 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x + pytest-asyncio 0.23.x |
| **Config file** | `pyproject.toml` (`asyncio_mode = "auto"`) |
| **Quick run command** | `uv run pytest tests/test_import*.py -x` |
| **Full suite command** | `uv run pytest` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/test_import*.py -x`
- **After every plan wave:** Run `uv run pytest`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 02-01-01 | 01 | 1 | IMP-01 | unit | `uv run pytest tests/test_chesscom_client.py -x` | ❌ W0 | ⬜ pending |
| 02-01-02 | 01 | 1 | IMP-01 | unit | `uv run pytest tests/test_chesscom_client.py::test_invalid_username -x` | ❌ W0 | ⬜ pending |
| 02-02-01 | 02 | 1 | IMP-02 | unit | `uv run pytest tests/test_lichess_client.py -x` | ❌ W0 | ⬜ pending |
| 02-02-02 | 02 | 1 | IMP-02 | unit | `uv run pytest tests/test_lichess_client.py::test_invalid_username -x` | ❌ W0 | ⬜ pending |
| 02-03-01 | 03 | 2 | IMP-03 | unit | `uv run pytest tests/test_import_service.py::test_incremental_sync -x` | ❌ W0 | ⬜ pending |
| 02-03-02 | 03 | 2 | IMP-03 | unit | `uv run pytest tests/test_import_service.py::test_last_synced_at -x` | ❌ W0 | ⬜ pending |
| 02-04-01 | 04 | 2 | IMP-04 | unit | `uv run pytest tests/test_import_service.py::test_job_lifecycle -x` | ❌ W0 | ⬜ pending |
| 02-04-02 | 04 | 2 | IMP-04 | unit | `uv run pytest tests/test_imports_router.py::test_unknown_job -x` | ❌ W0 | ⬜ pending |
| 02-05-01 | 05 | 2 | INFRA-02 | integration | `uv run pytest tests/test_imports_router.py::test_nonblocking -x` | ❌ W0 | ⬜ pending |
| 02-06-01 | 01 | 1 | IMP-01+02 | unit | `uv run pytest tests/test_normalization.py::test_variant_filter -x` | ❌ W0 | ⬜ pending |
| 02-06-02 | 01 | 1 | IMP-01+02 | unit | `uv run pytest tests/test_normalization.py::test_time_control_bucket -x` | ❌ W0 | ⬜ pending |
| 02-06-03 | 01 | 1 | IMP-01+02 | unit | `uv run pytest tests/test_game_repository.py::test_duplicate_skip -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_chesscom_client.py` — stubs for IMP-01 normalization and error handling
- [ ] `tests/test_lichess_client.py` — stubs for IMP-02 normalization and NDJSON parsing
- [ ] `tests/test_import_service.py` — stubs for IMP-03, IMP-04 job lifecycle
- [ ] `tests/test_imports_router.py` — stubs for INFRA-02 non-blocking, IMP-04 polling
- [ ] `tests/test_normalization.py` — stubs for variant filtering, time control bucketing, result mapping
- [ ] `tests/test_game_repository.py` — stubs for bulk insert + ON CONFLICT DO NOTHING
- [ ] `tests/conftest.py` — add AsyncSession mock fixture (extend existing conftest)

*No new framework install needed — pytest + pytest-asyncio already in dev-dependencies.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Live chess.com API integration | IMP-01 | Requires real API call to chess.com | Run import with a known chess.com username, verify games imported |
| Live lichess API integration | IMP-02 | Requires real API call to lichess | Run import with a known lichess username, verify games imported |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
