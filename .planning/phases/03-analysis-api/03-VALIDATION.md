---
phase: 3
slug: analysis-api
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-11
---

# Phase 3 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x + pytest-asyncio 0.23.x |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` — `asyncio_mode = "auto"` |
| **Quick run command** | `uv run pytest tests/test_analysis_repository.py tests/test_analysis_service.py -x` |
| **Full suite command** | `uv run pytest` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/test_analysis_repository.py tests/test_analysis_service.py -x`
- **After every plan wave:** Run `uv run pytest`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 03-01-01 | 01 | 1 | ANL-02 | unit | `uv run pytest tests/test_analysis_repository.py::TestMatchSide -x` | ❌ W0 | ⬜ pending |
| 03-01-02 | 01 | 1 | ANL-03 | unit | `uv run pytest tests/test_analysis_service.py::TestWDLStats -x` | ❌ W0 | ⬜ pending |
| 03-01-03 | 01 | 1 | FLT-01 | unit | `uv run pytest tests/test_analysis_repository.py::TestFilters::test_time_control_filter -x` | ❌ W0 | ⬜ pending |
| 03-01-04 | 01 | 1 | FLT-02 | unit | `uv run pytest tests/test_analysis_repository.py::TestFilters::test_rated_filter -x` | ❌ W0 | ⬜ pending |
| 03-01-05 | 01 | 1 | FLT-03 | unit | `uv run pytest tests/test_analysis_repository.py::TestFilters::test_recency_filter -x` | ❌ W0 | ⬜ pending |
| 03-01-06 | 01 | 1 | FLT-04 | unit | `uv run pytest tests/test_analysis_repository.py::TestFilters::test_color_filter -x` | ❌ W0 | ⬜ pending |
| 03-01-07 | 01 | 1 | RES-01 | unit | `uv run pytest tests/test_analysis_service.py::TestGameRecord -x` | ❌ W0 | ⬜ pending |
| 03-01-08 | 01 | 1 | RES-02 | unit | `uv run pytest tests/test_analysis_service.py::TestGameRecord::test_platform_url -x` | ❌ W0 | ⬜ pending |
| 03-01-09 | 01 | 1 | RES-03 | unit | `uv run pytest tests/test_analysis_service.py::TestPagination -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_analysis_repository.py` — stubs for ANL-02, FLT-01, FLT-02, FLT-03, FLT-04, transposition deduplication
- [ ] `tests/test_analysis_service.py` — stubs for ANL-03, RES-01, RES-02, RES-03, zero-result edge case
- [ ] No new framework install needed — pytest + pytest-asyncio + `db_session` fixture already configured

---

## Manual-Only Verifications

*All phase behaviors have automated verification.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
