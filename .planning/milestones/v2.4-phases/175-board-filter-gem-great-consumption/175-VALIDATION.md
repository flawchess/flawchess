---
phase: 175
slug: board-filter-gem-great-consumption
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-07-16
---

# Phase 175 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x (backend), vitest (frontend) |
| **Config file** | `pyproject.toml` (pytest), `frontend/vitest.config.ts` |
| **Quick run command** | `uv run pytest -n auto <nodeid>` / `cd frontend && npm test -- --run <file>` |
| **Full suite command** | `uv run pytest -n auto` / `cd frontend && npm test -- --run` |
| **Estimated runtime** | ~90 seconds (backend), ~30 seconds (frontend) |

---

## Sampling Rate

- **After every task commit:** Run the relevant quick command
- **After every plan wave:** Run the full suite for the touched stack
- **Before `/gsd-verify-work`:** Full backend + frontend suites must be green
- **Max feedback latency:** 120 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| *(seeded — populated by the planner / validate-phase)* | | | | | | | | | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

*Populated by validate-phase — existing pytest + vitest infrastructure is expected to cover all phase requirements.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Gem/great markers render instantly on an analyzed-game board with no sweep flash | BOARD-01 | Visual/timing behavior on real analyzed game | Open an analyzed game on the analysis board; confirm markers appear on first paint without a background-sweep delay |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 120s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
