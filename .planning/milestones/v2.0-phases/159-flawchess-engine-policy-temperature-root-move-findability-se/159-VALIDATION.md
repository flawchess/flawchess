---
phase: 159
slug: flawchess-engine-policy-temperature-root-move-findability-se
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-07-07
---

# Phase 159 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | vitest (frontend) |
| **Config file** | `frontend/vite.config.ts` |
| **Quick run command** | `cd frontend && npm test -- --run src/lib/flawchess` |
| **Full suite command** | `cd frontend && npm run lint && npm test -- --run && npx tsc -b` |
| **Estimated runtime** | ~60 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd frontend && npm test -- --run src/lib/flawchess`
- **After every plan wave:** Run `cd frontend && npm run lint && npm test -- --run && npx tsc -b`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 120 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 159-01-01 | 01 | 1 | SEED-085 | — | N/A | unit (TDD) | `cd frontend && npx vitest run src/lib/engine/__tests__/findability.test.ts` | ❌ new | ⬜ pending |
| 159-01-02 | 01 | 1 | SEED-085 | — | N/A | unit + types | `cd frontend && npx vitest run src/lib/engine/__tests__/mctsSearch.test.ts src/lib/engine/__tests__/fallbackExpectimax.test.ts src/lib/engine/__tests__/findability.test.ts && npx tsc -b` | ✅ | ⬜ pending |
| 159-02-01 | 02 | 1 | SEED-085 | — | N/A | unit (TDD) | `cd frontend && npx vitest run src/lib/flawChessVerdict.test.ts` | ✅ | ⬜ pending |
| 159-02-02 | 02 | 1 | SEED-085 | — | N/A | component + types | `cd frontend && npx vitest run src/components/analysis/__tests__/FlawChessAgreementVerdict.test.tsx && npx tsc -b` | ✅ | ⬜ pending |
| 159-03-01 | 03 | 2 | SEED-085 | T-159-06 | temperature=1 is a strict no-op (determinism preserved) | unit (TDD) | `cd frontend && npx vitest run src/lib/engine/__tests__/policyTemperature.test.ts src/lib/engine/__tests__/treeCommon.test.ts` | ❌ new | ⬜ pending |
| 159-03-02 | 03 | 2 | SEED-085 | T-159-06 | no-op short-circuit at both runner call sites | unit + types | `cd frontend && npx vitest run src/lib/engine/__tests__/mctsSearch.test.ts src/lib/engine/__tests__/fallbackExpectimax.test.ts && npx tsc -b` | ✅ | ⬜ pending |
| 159-04-01 | 04 | 3 | SEED-085 | T-159-08 | slider center maps to exactly 1 (`=== 1` test) | component (TDD) + types | `cd frontend && npx vitest run src/components/analysis/__tests__/TemperatureSelector.test.tsx && npx tsc -b` | ❌ new | ⬜ pending |
| 159-04-02 | 04 | 3 | SEED-085 | — | N/A | types + lint | `cd frontend && npx tsc -b && npm run lint` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements (vitest already configured; new test files are created by their TDD tasks, not a Wave 0).

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Temperature slider UX + verdict copy vs Maia chart consistency in live UI | SEED-085 | Visual/interactive judgment | Run dev server, open FlawChess Engine analysis, move ELO + temperature sliders, confirm ranked lines and verdict prose stay consistent with the Maia chart |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 120s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
