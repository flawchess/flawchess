---
phase: 13
slug: frontend-move-explorer-component
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-16
---

# Phase 13 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (backend only — no frontend test runner) |
| **Config file** | pyproject.toml |
| **Quick run command** | `uv run pytest tests/test_analysis_service.py -x` |
| **Full suite command** | `uv run pytest` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/test_analysis_service.py -x`
- **After every plan wave:** Run `uv run pytest`
- **Before `/gsd:verify-work`:** Full suite must be green + manual browser verification of all MEXP requirements
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 13-01-01 | 01 | 1 | MEXP-06 | manual | manual browser verification | N/A | ⬜ pending |
| 13-01-02 | 01 | 1 | MEXP-07 | manual | manual browser verification | N/A | ⬜ pending |
| 13-01-03 | 01 | 1 | MEXP-11 | manual | manual browser verification | N/A | ⬜ pending |
| 13-01-04 | 01 | 1 | MEXP-12 | manual | manual browser verification | N/A | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

*Existing infrastructure covers all phase requirements. No backend test gaps — backend API complete from Phase 12. Frontend has no automated test runner; all MEXP verification is manual browser-based.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Explorer table renders with Move/Games/Results columns and WDL bar | MEXP-06 | Frontend-only component, no frontend test runner | Navigate to Dashboard, set a position filter, verify 3-column table appears with stacked WDL bars |
| Clicking move row advances board and refreshes explorer | MEXP-07 | Requires browser interaction and visual verification | Click a move row, verify board position changes and explorer shows new position's moves |
| Transposition icon appears when transposition_count > game_count | MEXP-11 | Requires specific data state and tooltip hover | Find a move with transpositions, verify ⇄ icon and hover tooltip text |
| Board arrows rendered with proportional opacity | MEXP-12 | Visual verification of arrow opacity gradients | Verify arrows appear on board for all explorer moves, most-played has highest opacity |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
