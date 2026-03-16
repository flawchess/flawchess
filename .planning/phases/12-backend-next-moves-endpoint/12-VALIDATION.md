---
phase: 12
slug: backend-next-moves-endpoint
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-16
---

# Phase 12 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x + pytest-asyncio (asyncio_mode = "auto") |
| **Config file** | pyproject.toml `[tool.pytest.ini_options]` |
| **Quick run command** | `uv run pytest tests/test_analysis_repository.py -x` |
| **Full suite command** | `uv run pytest -x` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/test_analysis_repository.py -x`
- **After every plan wave:** Run `uv run pytest -x`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 12-01-01 | 01 | 1 | MEXP-04 | integration | `uv run pytest tests/test_analysis_repository.py::TestNextMoves -x` | ❌ W0 | ⬜ pending |
| 12-01-02 | 01 | 1 | MEXP-04 | integration | `uv run pytest tests/test_analysis_repository.py::TestNextMovesFilters -x` | ❌ W0 | ⬜ pending |
| 12-01-03 | 01 | 1 | MEXP-05 | integration | `uv run pytest tests/test_analysis_repository.py::TestNextMovesTranspositions -x` | ❌ W0 | ⬜ pending |
| 12-01-04 | 01 | 1 | MEXP-10 | integration | `uv run pytest tests/test_analysis_repository.py::TestTranspositionCounts -x` | ❌ W0 | ⬜ pending |
| 12-01-05 | 01 | 1 | MEXP-04 | integration | `uv run pytest tests/test_analysis_service.py::TestGetNextMoves -x` | ❌ W0 | ⬜ pending |
| 12-01-06 | 01 | 1 | MEXP-04 | integration | `uv run pytest tests/test_analysis_service.py::TestNextMovesSorting -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_analysis_repository.py` — extend with `TestNextMoves`, `TestNextMovesFilters`, `TestNextMovesTranspositions`, `TestTranspositionCounts` classes
- [ ] `tests/test_analysis_service.py` — extend with `TestGetNextMoves`, `TestNextMovesSorting` classes
- [ ] No new framework install needed — pytest-asyncio already configured

---

## Manual-Only Verifications

*All phase behaviors have automated verification.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
