---
phase: 166
slug: bot-move-selection-core-selectbotmove
status: ready
nyquist_compliant: true
wave_0_complete: false
created: 2026-07-11
---

# Phase 166 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | vitest (frontend) |
| **Config file** | frontend/vitest.config.ts |
| **Quick run command** | `cd frontend && npm test -- --run src/lib/engine` |
| **Full suite command** | `cd frontend && npm test -- --run` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd frontend && npm test -- --run src/lib/engine`
- **After every plan wave:** Run `cd frontend && npm test -- --run`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 60 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 166-01-01 | 01 | 1 | BOT-01, BOT-04 | — | N/A | unit | `cd frontend && npx vitest run src/lib/engine/__tests__/botSampling.test.ts` | ❌ W0 | ⬜ pending |
| 166-01-02 | 01 | 1 | BOT-01, BOT-02, BOT-03, BOT-04 | — | N/A | unit | `cd frontend && npx vitest run src/lib/engine/__tests__/selectBotMove.test.ts` | ❌ W0 | ⬜ pending |
| 166-01-03 | 01 | 1 | BOT-01..BOT-04 (gate) | — | N/A | integration | `cd frontend && npx tsc -b && npm run lint && npm test -- --run` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] Test files for the new `selectBotMove` / sampling helpers — stubs for BOT-01..BOT-04

*Existing vitest infrastructure covers the framework; only new test files are needed.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| ~1–2s bot reply latency on a mid-range phone | BOT-02 | Real-device timing cannot be asserted in unit tests | Play a bullet-TC bot game on a phone; observe reply latency at full-human slider end |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references (test files created by TDD tasks 1–2)
- [x] No watch-mode flags
- [x] Feedback latency < 60s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-07-11
