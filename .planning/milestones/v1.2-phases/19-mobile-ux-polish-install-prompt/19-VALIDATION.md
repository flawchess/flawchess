---
phase: 19
slug: mobile-ux-polish-install-prompt
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-20
---

# Phase 19 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (backend regression guard) — no frontend test framework |
| **Config file** | none — uses `uv run pytest` defaults |
| **Quick run command** | `uv run pytest -x` |
| **Full suite command** | `uv run pytest` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest -x`
- **After every plan wave:** Run `uv run pytest`
- **Before `/gsd:verify-work`:** Full suite must be green + manual mobile verification
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 19-01-01 | 01 | 1 | UX-03 | manual | Manual: test touch on physical device | N/A | ⬜ pending |
| 19-01-02 | 01 | 1 | UX-03 | manual | Manual: test drag-and-drop on mobile | N/A | ⬜ pending |
| 19-02-01 | 02 | 1 | UX-04 | manual | Manual: test at 375px viewport | N/A | ⬜ pending |
| 19-02-02 | 02 | 1 | UX-01 | manual | Manual: measure tap targets | N/A | ⬜ pending |
| 19-02-03 | 02 | 1 | UX-02 | manual | Manual: check horizontal scroll at 375px | N/A | ⬜ pending |
| 19-03-01 | 03 | 2 | PWA-04 | manual | Manual: Android Chrome install prompt | N/A | ⬜ pending |
| 19-03-02 | 03 | 2 | PWA-05 | manual | Manual: iOS Safari install banner | N/A | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements. No frontend test infrastructure exists — all UX requirements are inherently manual-only (visual layout, touch events, device-specific behavior). This is expected for a UI polish phase. Backend tests are unchanged.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| 44px touch targets on mobile | UX-01 | Visual/physical measurement on device | Set viewport to 375px, inspect button heights in DevTools |
| No horizontal scroll at 375px | UX-02 | Visual check across all pages | Navigate each page at 375px, verify no horizontal scrollbar |
| Chessboard click-to-move on touch | UX-03 | Touch event behavior on physical device | Tap piece then tap destination on iOS Safari + Android Chrome |
| Chessboard drag-and-drop on touch | UX-03 | Device-specific rendering (black screen bug) | Long-press and drag piece on Android Chrome + iOS Safari |
| Openings layout on mobile | UX-04 | Visual layout + scroll behavior | Scroll Openings page at 375px, verify sticky board + content access |
| Android install prompt | PWA-04 | Requires actual Chrome engagement heuristics | Visit site in Android Chrome, interact, verify prompt appears |
| iOS install banner | PWA-05 | Requires iOS Safari standalone detection | Visit site in iOS Safari, verify "Add to Home Screen" banner |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
