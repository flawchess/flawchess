---
phase: 15
slug: chart-consolidation-and-polish
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-17
---

# Phase 15 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | vitest (frontend), pytest 7.x (backend) |
| **Config file** | `frontend/vitest.config.ts`, `pyproject.toml` |
| **Quick run command** | `cd frontend && npm run test -- --run` |
| **Full suite command** | `uv run pytest && cd frontend && npm run test -- --run` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd frontend && npm run test -- --run`
- **After every plan wave:** Run `uv run pytest && cd frontend && npm run test -- --run`
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
| Rating charts appear above WDL charts on Global Stats | TBD | Visual layout order | Open /global-stats, verify rating charts render before Results by Time Control |
| Platform filter filters data correctly | TBD | E2E data flow | Select chess.com only, verify charts show only chess.com data |
| Chart titles visible on Openings Statistics tab | TBD | Visual presence | Navigate to Openings > Statistics, verify h2 headings above each chart |
| Monthly bucketing produces smooth lines | TBD | Visual smoothness | Compare RatingChart line smoothness before/after |

*If none: "All phase behaviors have automated verification."*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
