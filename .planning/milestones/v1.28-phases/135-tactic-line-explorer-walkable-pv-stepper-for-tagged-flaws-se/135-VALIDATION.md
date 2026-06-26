---
phase: 135
slug: tactic-line-explorer-walkable-pv-stepper-for-tagged-flaws-se
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-06-24
---

# Phase 135 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Backend: pytest 8.x · Frontend: vitest |
| **Config file** | `pyproject.toml` (pytest) · `frontend/vitest.config.ts` |
| **Quick run command** | `uv run pytest -n auto tests/test_<new>.py` · `cd frontend && npm test -- --run <file>` |
| **Full suite command** | `uv run pytest -n auto` · `cd frontend && npm run lint && npm test -- --run` |
| **Estimated runtime** | ~60–120 seconds (targeted) |

---

## Sampling Rate

- **After every task commit:** Run the relevant quick command (backend or frontend)
- **After every plan wave:** Run the full suite for the touched stack
- **Before `/gsd-verify-work`:** Full suite must be green (backend pytest + frontend lint/test; `npx tsc -b` when shared types change)
- **Max feedback latency:** ~120 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| TBD | — | — | — | — | — | — | — | — | ⬜ pending |

*Populated by the planner/executor as tasks are defined. Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] Backend: new test module for the `tactic-lines` endpoint (PV anchoring n vs n+1, allowed +1 offset, short-PV graceful handling, IDOR/ownership)
- [ ] Frontend: vitest spec for `useTacticLine` (depth counter floor-0, payoff flag, orientation reset-to-root)

*If existing infrastructure covers a requirement, no new Wave 0 file is needed.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Nested Dialog→Drawer stacking + return-to-Game on mobile (D-01/D-05) | — | Focus/scroll-trap behavior needs real touch device | Open Game modal → Explore → close; confirm return to Game view, no scroll lock |
| Arrow/depth-label rendering on the large board | — | Visual fidelity vs miniboard | Compare explorer root arrows + depth badges to the miniboard for the same flaw |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 120s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
