---
phase: 33
slug: homepage-readme-seo-update
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-27
---

# Phase 33 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | vitest (frontend) |
| **Config file** | `frontend/vitest.config.ts` |
| **Quick run command** | `cd frontend && npm test` |
| **Full suite command** | `cd frontend && npm test` |
| **Estimated runtime** | ~10 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd frontend && npm test`
- **After every plan wave:** Run `cd frontend && npm test`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 33-01-01 | 01 | 1 | SC-1 | build | `cd frontend && npm run build` | N/A | pending |
| 33-01-02 | 01 | 1 | SC-1 | visual | Manual inspection | N/A | pending |
| 33-02-01 | 02 | 1 | SC-2 | content | `grep "Endgame" README.md` | N/A | pending |
| 33-03-01 | 03 | 1 | SC-3 | content | `grep "endgame" frontend/index.html` | N/A | pending |

*Status: pending / green / red / flaky*

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements. No new test framework or fixtures needed — this is a content/copy update phase.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Homepage visual layout correct | SC-1 | Visual design check — screenshot placement, section ordering, responsive layout | Load homepage on desktop and mobile, verify 5 feature sections render correctly with alternating layout |
| Screenshots display correctly | SC-1 | Requires human-captured screenshots dropped into public/screenshots/ | After screenshots are added, verify each section shows the correct screenshot |
| OG image renders in social shares | SC-3 | Requires external tool (social media debugger) | Use Facebook/Twitter card validators to confirm OG meta renders |

---

## Validation Sign-Off

- [ ] All tasks have automated verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
