---
phase: 5
slug: position-bookmarks-and-w-d-l-comparison-charts
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-13
---

# Phase 5 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x + pytest-asyncio 0.23.x |
| **Config file** | `pyproject.toml` — `[tool.pytest.ini_options]` with `asyncio_mode = "auto"` |
| **Quick run command** | `uv run pytest tests/test_bookmark_repository.py -x` |
| **Full suite command** | `uv run pytest` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/test_bookmark_repository.py -x`
- **After every plan wave:** Run `uv run pytest`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 5-01-01 | 01 | 0 | BKM-01 | integration | `uv run pytest tests/test_bookmark_repository.py::TestCRUD -x` | ❌ W0 | ⬜ pending |
| 5-01-02 | 01 | 0 | BKM-02 | integration | `uv run pytest tests/test_bookmark_repository.py::TestReorder -x` | ❌ W0 | ⬜ pending |
| 5-01-03 | 01 | 0 | BKM-05 | integration | `uv run pytest tests/test_bookmark_repository.py::TestIsolation -x` | ❌ W0 | ⬜ pending |
| 5-02-01 | 02 | 0 | BKM-03 | integration | `uv run pytest tests/test_analysis_repository.py::TestTimeSeries -x` | ❌ W0 | ⬜ pending |
| 5-02-02 | 02 | 0 | BKM-04 | integration | `uv run pytest tests/test_analysis_repository.py::TestTimeSeries::test_gap_months -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_bookmark_repository.py` — stubs for BKM-01 (CRUD), BKM-02 (reorder), BKM-05 (user isolation)
- [ ] `tests/test_analysis_repository.py` — append `TestTimeSeries` class for BKM-03, BKM-04
- [ ] Alembic migration for `bookmarks` table — required before any repository test can run

*If none: "Existing infrastructure covers all phase requirements."*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Drag-and-drop reorder persists after page reload | BKM-02 | Frontend interaction, no headless test | 1. Go to /bookmarks, drag a bookmark to new position. 2. Reload page. 3. Verify order is preserved. |
| [Load] bookmark navigates to / with board pre-populated | BKM-06 | Navigation + board state, React Router state not easily unit-testable | 1. On /bookmarks, click [Load] on a bookmark. 2. Verify / loads with correct moves replayed and filters set. |
| Inline label edit saves on blur | BKM-07 | UI interaction, no automated coverage | 1. Click bookmark label to edit. 2. Type new name. 3. Click elsewhere. 4. Verify label updated in list and persisted after reload. |
| Win rate chart shows gaps for months with 0 games | BKM-04 | Visual chart gap rendering | 1. Find or create a bookmark with sparse history. 2. Verify chart line has visible gaps (not drops to 0%) for months with no games. |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
