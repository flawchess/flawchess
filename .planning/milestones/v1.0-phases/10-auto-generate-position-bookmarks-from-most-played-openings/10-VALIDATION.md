---
phase: 10
slug: auto-generate-position-bookmarks-from-most-played-openings
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-15
---

# Phase 10 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (backend), vitest (frontend) |
| **Config file** | pyproject.toml, frontend/vitest.config.ts |
| **Quick run command** | `uv run pytest tests/ -x -q` |
| **Full suite command** | `uv run pytest tests/ && cd frontend && npm run lint && npm run build` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/ -x -q`
- **After every plan wave:** Run `uv run pytest tests/ && cd frontend && npm run lint && npm run build`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 10-01-01 | 01 | 1 | Top positions query | unit | `uv run pytest tests/test_suggestions.py -x` | ❌ W0 | ⬜ pending |
| 10-01-02 | 01 | 1 | FEN/moves recovery | unit | `uv run pytest tests/test_suggestions.py -x` | ❌ W0 | ⬜ pending |
| 10-01-03 | 01 | 1 | Piece filter heuristic | unit | `uv run pytest tests/test_suggestions.py -x` | ❌ W0 | ⬜ pending |
| 10-02-01 | 02 | 1 | match_side update endpoint | unit | `uv run pytest tests/test_bookmarks.py -x` | ❌ W0 | ⬜ pending |
| 10-03-01 | 03 | 2 | Mini board rendering | manual | visual check | N/A | ⬜ pending |
| 10-03-02 | 03 | 2 | Generation modal UI | manual | visual + lint | N/A | ⬜ pending |
| 10-03-03 | 03 | 2 | Inline piece filter | manual | visual + lint | N/A | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_bookmark_suggestions.py` — stubs for suggestion endpoint tests
- [ ] `tests/test_bookmark_update.py` — stubs for match_side update tests

*Existing test infrastructure (conftest, fixtures, DB setup) covers all shared needs.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Mini board renders correctly | Mini board views | Visual rendering at 80px | Load bookmark list, verify small boards display correct positions |
| Generation modal layout | Suggestion modal | Complex UI interaction | Click "Suggest bookmarks", verify modal shows mini boards, counts, filters |
| Inline piece filter toggle | Bookmark card control | UI interaction | Change piece filter on card, verify it persists |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
