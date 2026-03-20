---
phase: 14
slug: ui-restructuring
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-17
---

# Phase 14 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest + pytest-asyncio (backend); no frontend test framework configured |
| **Config file** | `pyproject.toml` (backend: `asyncio_mode = "auto"`) |
| **Quick run command** | `uv run pytest tests/ -x -q` |
| **Full suite command** | `uv run pytest` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/ -x -q`
- **After every plan wave:** Run `uv run pytest`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 14-01-01 | 01 | 1 | UIRS-01 | manual-only | Browser: navigate to /openings/explorer, /openings/games, /openings/statistics | N/A | ⬜ pending |
| 14-01-02 | 01 | 1 | UIRS-02 | manual-only | Browser: set filter, switch tab, verify filter unchanged | N/A | ⬜ pending |
| 14-02-01 | 02 | 1 | UIRS-03 | manual-only | Browser: navigate to /import, verify controls | N/A | ⬜ pending |
| 14-02-02 | 02 | 1 | UIRS-04 | manual-only | Browser: inspect nav header for 4 items | N/A | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Existing infrastructure covers all backend requirements. No frontend test files to create (no frontend test framework in the project).

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Three sub-tabs exist at /openings/* URLs | UIRS-01 | Frontend-only, no test framework | Navigate to each URL directly, verify tab renders |
| Filter state persists across tab switches | UIRS-02 | Requires interactive browser session | Set filters, switch tabs, verify filters unchanged |
| /import page shows all import controls | UIRS-03 | Frontend-only, no test framework | Navigate to /import, verify username input, platform select, import button |
| Nav shows exactly 4 items | UIRS-04 | Frontend-only, no test framework | Inspect NavHeader for Import, Openings, Rating, Global Stats |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
