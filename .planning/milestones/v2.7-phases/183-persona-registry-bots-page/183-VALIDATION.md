---
phase: 183
slug: persona-registry-bots-page
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-07-22
---

# Phase 183 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | vitest (frontend) |
| **Config file** | frontend/vite.config.ts |
| **Quick run command** | `cd frontend && npx vitest run <changed-test-file>` |
| **Full suite command** | `cd frontend && npm test -- --run` |
| **Estimated runtime** | ~60 seconds (full), <10s (single file) |

---

## Sampling Rate

- **After every task commit:** Run `cd frontend && npx vitest run <relevant test file>`
- **After every plan wave:** Run `cd frontend && npm test -- --run && npm run lint`
- **Before `/gsd-verify-work`:** Full suite green + `npx tsc -b` clean (lint/test do not type-check)
- **Max feedback latency:** 90 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 183-01-01 | 01 | 1 | PERS-03 | — | N/A | unit (TDD) | `cd frontend && npm test -- --run src/lib/personas/__tests__/personaRegistry.test.ts` | ❌ new | ⬜ pending |
| 183-01-02 | 01 | 1 | AVAT-01 | — | N/A | type/lint | `cd frontend && npx tsc -b && npm run lint` | ✅ | ⬜ pending |
| 183-01-03 | 01 | 1 | PERS-02 | T: localStorage tamper | shape-validated parse, Sentry-once | unit (TDD) | `cd frontend && npm test -- --run src/lib/personas/__tests__/botPersonaSetupSettings.test.ts` | ❌ new | ⬜ pending |
| 183-02-01 | 02 | 1 | PERS-02 | — | N/A | unit (TDD) | `cd frontend && npm test -- --run src/lib/__tests__/botDrawGate.test.ts` | ✅ | ⬜ pending |
| 183-03-01 | 03 | 2 | PERS-02/04 | T: snapshot tamper | additive optional field, no version bump | unit (TDD) | `cd frontend && npm test -- --run src/lib/__tests__/botGameSnapshot.test.ts && npx tsc -b` | ✅ | ⬜ pending |
| 183-03-02 | 03 | 2 | PERS-02 | — | N/A | unit | `cd frontend && npm test -- --run src/hooks/__tests__/useBotGame.test.tsx && npx tsc -b` | ✅ | ⬜ pending |
| 183-04-01 | 04 | 2 | PERS-01 | — | bios rendered as text, never HTML | unit | `cd frontend && npm test -- --run src/components/bots/__tests__/PersonaGrid.test.tsx src/components/bots/__tests__/PersonaCard.test.tsx` | ❌ new | ⬜ pending |
| 183-04-02 | 04 | 2 | PERS-02 | — | N/A | unit | `cd frontend && npm test -- --run src/components/bots/__tests__/PersonaDetailSurface.test.tsx` | ❌ new | ⬜ pending |
| 183-04-03 | 04 | 2 | PERS-01/04 | — | N/A | unit | `cd frontend && npm test -- --run src/pages/__tests__/Bots.test.tsx && npx tsc -b` | ✅ | ⬜ pending |
| 183-05-01 | 05 | 3 | AVAT-01 | — | N/A | unit | `cd frontend && npm test -- --run src/components/bots/__tests__/ClockDisplay.test.tsx && npx tsc -b` | ✅ | ⬜ pending |
| 183-05-02 | 05 | 3 | PERS-02 | — | N/A | unit | `cd frontend && npm test -- --run src/components/bots/__tests__/BotDrawOfferBanner.test.tsx && npx tsc -b` | ❌ new | ⬜ pending |
| 183-05-03 | 05 | 3 | PERS-02, AVAT-02 | — | N/A | unit | `cd frontend && npm test -- --run src/pages/__tests__/Bots.test.tsx && npx tsc -b` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky · "❌ new" in File Exists = test file created by the task (TDD or new component test)*

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements (vitest configured, test patterns established in `frontend/src/lib/engine/*.test.ts` and hook tests).

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Persona grid visual layout, detail surface, placeholder avatars | PERS-01, AVAT-01 | Visual appearance judgment | Open /bots, browse grid, open detail dialogs on desktop + mobile widths |
| Roster content review (names/bios) | AVAT-02 | Editorial curation (D-13) | User reviews full roster in UAT, requests swaps |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references (none — existing infrastructure suffices)
- [x] No watch-mode flags
- [x] Feedback latency < 90s
- [ ] `nyquist_compliant: true` set in frontmatter (flipped by /gsd-validate-phase after execution)

**Approval:** pending
