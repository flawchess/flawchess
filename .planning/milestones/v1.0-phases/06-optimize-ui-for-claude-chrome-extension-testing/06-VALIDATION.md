---
phase: 6
slug: optimize-ui-for-claude-chrome-extension-testing
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-13
---

# Phase 6 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | No frontend test framework (vitest/jest not installed). Backend: pytest 8.x |
| **Config file** | `pyproject.toml` [tool.pytest.ini_options] (backend only) |
| **Quick run command** | `npm run lint` (partial — checks some semantic HTML) |
| **Full suite command** | `npm run build && npm run lint` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `npm run lint`
- **After every plan wave:** Run `npm run build && npm run lint`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 06-01-01 | 01 | 1 | Semantic HTML | lint | `npm run lint` | ✅ | ⬜ pending |
| 06-01-02 | 01 | 1 | data-testid attrs | manual-only | — | N/A | ⬜ pending |
| 06-01-03 | 01 | 1 | ARIA labels | manual-only | — | N/A | ⬜ pending |
| 06-02-01 | 02 | 1 | Click-to-move | manual-only | — | N/A | ⬜ pending |
| 06-02-02 | 02 | 1 | Board data-testid | manual-only | — | N/A | ⬜ pending |
| 06-03-01 | 03 | 1 | CLAUDE.md rules | manual-only | — | N/A | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements. No new test framework needed — this phase is frontend DOM attribute and event handler changes validated via browser automation.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| data-testid present on all interactive elements | User constraint | No frontend test framework; validated by Claude Chrome extension | Load app, inspect DOM for data-testid on buttons/inputs/links |
| Click-to-move on chess board | User constraint | Interactive behavior requiring live browser | Click source square, click target square, verify move executes |
| ARIA labels on icon-only buttons | User constraint | DOM attribute inspection | Inspect accessibility tree in browser DevTools |
| Semantic HTML (no div/span onClick) | User constraint | Partial lint coverage only | Review rendered HTML for correct element types |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
