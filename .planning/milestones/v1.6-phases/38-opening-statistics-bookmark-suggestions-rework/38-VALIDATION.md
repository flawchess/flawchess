---
phase: 38
slug: opening-statistics-bookmark-suggestions-rework
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-29
---

# Phase 38 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | vitest (frontend), pytest (backend) |
| **Config file** | `frontend/vitest.config.ts`, `pyproject.toml` |
| **Quick run command** | `cd frontend && npm test` / `uv run pytest tests/ -x` |
| **Full suite command** | `cd frontend && npm test && cd .. && uv run pytest` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run quick test command for affected area
- **After every plan wave:** Run full suite command
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| TBD | TBD | TBD | TBD | TBD | TBD | TBD | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

*Existing infrastructure covers all phase requirements.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Section reorder renders correctly | Phase goal | Visual layout verification | Open Opening Statistics tab, verify section order matches spec |
| Bookmark card layout redesign | Phase goal | Visual layout verification | Check bookmark cards show bigger minimap, new button row layout |
| Chart-enable toggle UX | Phase goal | Interactive behavior | Toggle chart-enable on/off, verify charts update accordingly |
| Default openings in charts (no bookmarks) | Phase goal | Requires empty bookmark state | Delete all bookmarks, verify top 3 white/black openings appear in charts |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
