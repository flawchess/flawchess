---
phase: 29
slug: endgame-analytics
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-26
---

# Phase 29 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x (backend) / vitest (frontend) |
| **Config file** | `pyproject.toml` (backend) / `vite.config.ts` (frontend) |
| **Quick run command** | `uv run pytest tests/ -x --tb=short` |
| **Full suite command** | `uv run pytest && npm test` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/ -x --tb=short`
- **After every plan wave:** Run `uv run pytest && npm test`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 29-01-01 | 01 | 1 | ENDGM-01 | unit | `uv run pytest tests/test_endgame_service.py` | ❌ W0 | ⬜ pending |
| 29-01-02 | 01 | 1 | ENDGM-02 | unit | `uv run pytest tests/test_endgame_service.py` | ❌ W0 | ⬜ pending |
| 29-01-03 | 01 | 1 | ENDGM-03 | unit | `uv run pytest tests/test_endgame_service.py` | ❌ W0 | ⬜ pending |
| 29-01-04 | 01 | 1 | ENDGM-04 | unit | `uv run pytest tests/test_endgame_service.py` | ❌ W0 | ⬜ pending |
| 29-01-05 | 01 | 1 | CONV-01 | unit | `uv run pytest tests/test_endgame_service.py` | ❌ W0 | ⬜ pending |
| 29-01-06 | 01 | 1 | CONV-02 | unit | `uv run pytest tests/test_endgame_service.py` | ❌ W0 | ⬜ pending |
| 29-01-07 | 01 | 1 | CONV-03 | unit | `uv run pytest tests/test_endgame_service.py` | ❌ W0 | ⬜ pending |
| 29-02-01 | 02 | 2 | ENDGM-01 | integration | `npm test` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_endgame_service.py` — stubs for ENDGM-01 through ENDGM-04, CONV-01 through CONV-03
- [ ] `tests/test_endgame_repository.py` — stubs for endgame query functions

*Existing test infrastructure (pytest, conftest.py with DB fixtures) covers framework needs.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Mobile layout at 375px width | SC-6 | Visual layout verification | Open /endgames on 375px viewport, verify filters collapse, chart renders, no horizontal scroll |
| Empty state display | SC-5 | Visual + UX verification | View /endgames with a user who has no endgame data, verify meaningful message shown |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
