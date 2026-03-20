---
phase: 18
slug: mobile-navigation
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-20
---

# Phase 18 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | None installed (no vitest/jest in frontend) |
| **Config file** | None — no frontend test framework this phase |
| **Quick run command** | `npm run lint` |
| **Full suite command** | `npm run build` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `npm run lint`
- **After every plan wave:** Run `npm run build`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 18-01-01 | 01 | 1 | NAV-01 | manual-only | `npm run build` | N/A | ⬜ pending |
| 18-01-02 | 01 | 1 | NAV-02 | manual-only | `npm run build` | N/A | ⬜ pending |
| 18-01-03 | 01 | 1 | NAV-03 | manual-only | `npm run build` | N/A | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements. No test framework is being added in this phase — validation relies on TypeScript compilation and manual responsive verification.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Bottom bar hidden ≥640px; visible <640px; "More" opens drawer | NAV-01 | Layout/visual behavior requires real viewport | Chrome DevTools → 375px width; verify bottom bar visible, hamburger opens drawer |
| Active route highlighted; drawer closes on nav link tap | NAV-02 | Interactive navigation behavior | Tap each nav link in drawer; verify route change + drawer close |
| Safe-area insets on notched iPhone PWA | NAV-03 | Requires physical device or accurate simulator | Test on iPhone in standalone PWA mode; verify no notch/Dynamic Island overlap |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
