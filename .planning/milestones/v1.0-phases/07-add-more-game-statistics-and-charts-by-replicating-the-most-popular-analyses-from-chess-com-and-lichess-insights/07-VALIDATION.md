---
phase: 7
slug: add-more-game-statistics-and-charts-by-replicating-the-most-popular-analyses-from-chess-com-and-lichess-insights
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-14
---

# Phase 7 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (backend, 199 tests passing) + Vitest (frontend) |
| **Config file** | pyproject.toml (`[tool.pytest.ini_options]`) |
| **Quick run command** | `uv run pytest tests/test_normalization.py tests/test_stats_repository.py tests/test_stats_router.py -x -q` |
| **Full suite command** | `uv run pytest -x -q` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/test_normalization.py tests/test_stats_repository.py tests/test_stats_router.py -x -q`
- **After every plan wave:** Run `uv run pytest -x -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 07-01-01 | 01 | 1 | STATS-01 | unit | `uv run pytest tests/test_normalization.py -x -q` | ✅ (extend) | ⬜ pending |
| 07-02-01 | 02 | 1 | STATS-02 | unit | `uv run pytest tests/test_stats_repository.py -x -q` | ❌ W0 | ⬜ pending |
| 07-02-02 | 02 | 1 | STATS-03 | unit | `uv run pytest tests/test_stats_repository.py -x -q` | ❌ W0 | ⬜ pending |
| 07-02-03 | 02 | 1 | STATS-04 | unit | `uv run pytest tests/test_stats_repository.py -x -q` | ❌ W0 | ⬜ pending |
| 07-02-04 | 02 | 1 | STATS-05 | unit | `uv run pytest tests/test_stats_repository.py -x -q` | ❌ W0 | ⬜ pending |
| 07-03-01 | 03 | 2 | STATS-06 | integration | `uv run pytest tests/test_stats_router.py -x -q` | ❌ W0 | ⬜ pending |
| 07-03-02 | 03 | 2 | STATS-07 | integration | `uv run pytest tests/test_stats_router.py -x -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_stats_repository.py` — stubs for STATS-02, STATS-03, STATS-04, STATS-05
- [ ] `tests/test_stats_router.py` — stubs for STATS-06, STATS-07

*Extend existing `tests/test_normalization.py` for STATS-01 — no new file needed.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Rating charts render correctly per platform | STATS-02 | Visual chart rendering | Open /rating, verify separate chess.com and lichess charts with togglable time control lines |
| Navigation shows 5 items correctly | NAV | Visual layout | Check nav bar shows Analysis, Bookmarks, Openings, Rating, Global Stats |
| Results by color/TC charts display correctly | STATS-03/04 | Visual chart rendering | Open /global-stats, verify WDL bars for time control and color |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
