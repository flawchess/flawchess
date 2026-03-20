---
phase: 16
slug: improve-game-cards-ui-icons-layout-hover-minimap
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-18
---

# Phase 16 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (backend); no frontend test framework |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `uv run pytest tests/test_zobrist.py tests/test_import_service.py -x` |
| **Full suite command** | `uv run pytest` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/test_zobrist.py tests/test_import_service.py -x`
- **After every plan wave:** Run `uv run pytest`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 16-01-01 | 01 | 1 | result_fen column | unit | `uv run pytest tests/test_zobrist.py -x` | ✅ needs update | ⬜ pending |
| 16-01-02 | 01 | 1 | result_fen import | unit | `uv run pytest tests/test_import_service.py -x` | ✅ needs update | ⬜ pending |
| 16-01-03 | 01 | 1 | result_fen API response | unit | `uv run pytest tests/test_analysis_service.py -x` | ✅ may need update | ⬜ pending |
| 16-02-01 | 02 | 2 | card 3-row layout | manual/visual | — | ❌ no frontend tests | ⬜ pending |
| 16-02-02 | 02 | 2 | icons on metadata | manual/visual | — | ❌ no frontend tests | ⬜ pending |
| 16-02-03 | 02 | 2 | null field handling | manual/visual | — | ❌ no frontend tests | ⬜ pending |
| 16-02-04 | 02 | 2 | hover minimap | manual/visual | — | ❌ no frontend tests | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_zobrist.py` — update existing tests for new 2-tuple return from `hashes_for_game()`
- [ ] `tests/test_import_service.py` — verify `result_fen` is passed to storage

*Existing infrastructure covers backend requirements. No frontend test framework to add.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| 3-row card layout | Card restructure | Visual/CSS layout | Inspect game cards in Games tab — verify 3 rows: result+players, opening, metadata |
| Icons on metadata | Icon integration | Visual rendering | Verify Clock, Calendar, Swords/Flag, Hash, BookOpen icons appear in correct positions |
| Null field handling | No NaN display | Edge case visual | Import daily chess.com games (null time_control_seconds) — verify no "NaN" shown |
| Hover minimap (desktop) | result_fen display | Interactive behavior | Hover over a game card — tooltip with 120px MiniBoard should appear showing final position |
| Tap minimap (mobile) | result_fen display | Touch interaction | Tap a game card on mobile viewport — inline minimap should expand below metadata |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
