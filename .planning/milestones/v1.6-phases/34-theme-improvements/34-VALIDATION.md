---
phase: 34
slug: theme-improvements
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-28
---

# Phase 34 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | vitest (frontend), pytest (backend — not needed for this phase) |
| **Config file** | `frontend/vitest.config.ts` |
| **Quick run command** | `cd frontend && npm test` |
| **Full suite command** | `cd frontend && npm test && npm run build` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd frontend && npm test`
- **After every plan wave:** Run `cd frontend && npm test && npm run build`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 34-01-01 | 01 | 1 | THEME-01 | build | `npm run build` | ✅ | ⬜ pending |
| 34-01-02 | 01 | 1 | THEME-02 | visual | Manual inspection | N/A | ⬜ pending |
| 34-02-01 | 02 | 1 | THEME-03 | visual | Manual inspection | N/A | ⬜ pending |
| 34-02-02 | 02 | 1 | THEME-04 | build | `npm run build` | ✅ | ⬜ pending |
| 34-02-03 | 02 | 1 | THEME-05 | visual | Manual inspection | N/A | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements. No new test framework or fixtures needed.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Charcoal containers with noise texture visible | THEME-02 | Visual appearance, CSS aesthetics | Open Endgames tab, verify charcoal background with subtle grain on stat sections |
| Filter buttons span full sidebar width | THEME-03 | Layout visual check | Open Openings page, verify filter buttons fill sidebar width evenly |
| Active subtab has brand brown fill | THEME-05 | Visual color check | Navigate between Moves/Games/Statistics tabs, verify active tab has brown fill |
| Navigation header active tab highlighting | D-11 | Visual appearance | Navigate between pages, verify active nav has lighter background |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
