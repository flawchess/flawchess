---
phase: 49
slug: openings-desktop-sidebar
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-09
---

# Phase 49 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | vitest |
| **Config file** | `frontend/vitest.config.ts` |
| **Quick run command** | `npm test -- --run` |
| **Full suite command** | `npm test -- --run` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `npm test -- --run`
- **After every plan wave:** Run `npm test -- --run`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 49-01-01 | 01 | 1 | DESK-01 | — | N/A | manual | Visual check: collapsed strip visible on desktop | N/A | ⬜ pending |
| 49-01-02 | 01 | 1 | DESK-02 | — | N/A | manual | Visual check: icon click opens/switches panels | N/A | ⬜ pending |
| 49-01-03 | 01 | 1 | DESK-03 | — | N/A | manual | Visual check: filter changes update board live | N/A | ⬜ pending |
| 49-01-04 | 01 | 1 | DESK-04 | — | N/A | manual | Visual check: overlay on smaller desktop screens | N/A | ⬜ pending |
| 49-01-05 | 01 | 1 | DESK-05 | — | N/A | manual | Visual check: push layout on larger screens | N/A | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements. This phase is pure UI layout restructuring — no new test stubs needed. Build verification (`npm run build`) catches TypeScript/compilation errors.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Collapsed strip visible with filter/bookmark icons | DESK-01 | CSS layout — cannot be unit tested | Open Openings page on desktop, verify left-edge strip with icons |
| Panel switching without double-click | DESK-02 | User interaction pattern | Click filter icon → panel opens. Click bookmark icon → switches directly |
| Live filter updates while panel open | DESK-03 | Requires running app with data | Change filter values with panel open, verify board updates |
| Overlay mode on smaller desktop | DESK-04 | Viewport-dependent CSS behavior | Resize browser to <1280px width, open panel, verify overlay |
| Push mode on larger desktop | DESK-05 | Viewport-dependent CSS behavior | Resize browser to ≥1280px width, open panel, verify content pushes right |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
