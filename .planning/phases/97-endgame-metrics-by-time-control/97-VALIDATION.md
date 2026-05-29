---
phase: 97
slug: endgame-metrics-by-time-control
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-29
---

# Phase 97 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x (backend) + vitest (frontend) |
| **Config file** | `pyproject.toml` (pytest) / `frontend/vitest.config.ts` |
| **Quick run command** | `uv run pytest tests/test_endgame_service.py -x` |
| **Full suite command** | `uv run pytest -x && ( cd frontend && npm test -- --run )` |
| **Estimated runtime** | ~90 seconds |

---

## Sampling Rate

- **After every task commit:** Run the relevant quick command (backend `uv run pytest <file> -x`, frontend `npm test -- --run <file>`)
- **After every plan wave:** Run the full suite command
- **Before `/gsd-verify-work`:** Full suite must be green + `uv run ty check app/ tests/` + `cd frontend && npm run lint && npm run knip`
- **Max feedback latency:** 90 seconds

---

## Per-Task Verification Map

> Filled by the planner from PLAN.md tasks. One row per task.

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| TBD | — | — | standalone | — | N/A | unit | TBD | TBD | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- Existing infrastructure (pytest + vitest) covers all phase verification. No new framework install required.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Per-TC cards render responsively on desktop + mobile | SC-6 | Visual layout parity is hard to assert automatically | Load Endgames page at desktop + mobile widths; confirm one card per eligible TC in bullet/blitz/rapid/classical order, metric blocks side-by-side on desktop and stacked on mobile |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 90s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
