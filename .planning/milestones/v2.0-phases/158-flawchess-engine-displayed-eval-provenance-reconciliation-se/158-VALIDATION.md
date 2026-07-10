---
phase: 158
slug: flawchess-engine-displayed-eval-provenance-reconciliation-se
status: approved
nyquist_compliant: true
wave_0_complete: false
created: 2026-07-07
---

# Phase 158 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | vitest (frontend) |
| **Config file** | `frontend/vite.config.ts` |
| **Quick run command** | `cd frontend && npm test -- --run <changed test files>` |
| **Full suite command** | `cd frontend && npm run lint && npm test -- --run && npx tsc -b` |
| **Estimated runtime** | ~60 seconds |

---

## Sampling Rate

- **After every task commit:** Run the quick command on the touched test files
- **After every plan wave:** Run the full suite command
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 90 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| (filled by planner) | | | SEED-087 | — | N/A | unit | `cd frontend && npm test -- --run` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] Unit-test stubs for the UCI-keyed lookup/precedence module — covered by 158-02 (type: tdd; tests land with the module in Wave 1)

*Existing vitest infrastructure covers the framework; no new install.*

**Measurement-task exemption (plan-checker warning 1, resolved 2026-07-07):** 158-01 Task 1
(headless Node WASM depth-vs-movetime measurement) intentionally has no automated `<verify>` —
it produces *data*, not code, mirroring the Phase 151.1 headless-WASM spike precedent. Its
verification is structural: 158-01 Task 2 consumes the measured values as named constants and
carries the automated checks (grep for absence of the old `depth 14` budget, `npx tsc -b`,
hook tests). This rationale replaces a formal Wave-0 pairing for that task; `nyquist_compliant`
is set accordingly.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Cross-card eval identity on a live position | SEED-087 | Requires real WASM engines streaming in a browser | On `/analysis`, find a move shown on all three cards (exd5/Bc5 class); confirm one identical number everywhere, including Maia line colors matching the displayed evals |
| No precedence flapping during refinement | SEED-087 | Streaming timing is browser-real-time | Watch a fresh position settle; displayed evals must not visibly flip between grading-run and free-run values |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 90s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
