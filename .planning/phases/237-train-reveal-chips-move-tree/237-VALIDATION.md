---
phase: "237"
slug: "train-reveal-chips-move-tree"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: draft
nyquist_compliant: false
wave_0_complete: false
created: "2026-10-09"
---

# Phase 237 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Source: `237-RESEARCH.md` § Validation Architecture.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Vitest 5 + @testing-library/react 16 (jsdom); pytest via uv (telemetry schema only) |
| **Config file** | `frontend/vite.config.ts` (`test:` block, `src/vitest.setup.ts`); `pyproject.toml` |
| **Quick run command** | `cd frontend && npx vitest run src/hooks/__tests__/useTrainRevealTree.test.ts src/lib/__tests__/trainArrows.test.ts src/lib/__tests__/trainBotCopy.test.ts` |
| **Full suite command** | `cd frontend && npm run lint && npm run build && npm test -- --run && npm run knip`; `uv run pytest -n auto -x` |
| **Estimated runtime** | ~30 s quick, ~6 min full |

---

## Sampling Rate

- **After every task commit:** the touched test files (`npx vitest run <files>`), plus `npm run build` when shared types change
- **After every plan wave:** `cd frontend && npm run lint && npm run build && npm test -- --run && npm run knip`; `uv run pytest tests/schemas tests/routers/test_train.py -x` when telemetry schema changed
- **Before `/gsd-verify-work`:** full CLAUDE.md pre-merge gate green, plus agent-run browser UAT at 390x844, 375x667, 768x1024, 1280x800
- **Max feedback latency:** 60 seconds per task

---

## Per-Task Verification Map

Filled by the planner per task (`<automated>` + `<fails_when>`). Behaviour → test mapping the plans must cover:

| Behaviour | Decision | Test Type | Automated Command | File Exists |
|-----------|----------|-----------|-------------------|-------------|
| `graftLine` grafts with reuse, never moves `currentNodeId` | R4 | unit | `npx vitest run src/hooks/__tests__/useAnalysisBoard.test.ts` | ✅ add cases |
| Three lines seeded, late line grafts without moving the board | R4 / D-03 | unit (hook) | `npx vitest run src/hooks/__tests__/useTrainRevealTree.test.ts` | ❌ W0 |
| Chip focus derivation, root-move focus/clear | R3 / D-01, D-04 | unit (hook) | same | ❌ W0 |
| Known move = no fork; first free node = fork | R4 / D-13 | unit | same + `useTrainPuzzleTelemetry.test.ts` | ✅/❌ |
| Grading markers only on free nodes | R4 | unit | ported from `useTrainFreePlay.test.ts` | ✅ port |
| Chip groups merge You = Best / You = Game | R2 / D-02 | unit (pure) | `npx vitest run src/lib/__tests__/trainRevealLines.test.ts` | ❌ W0 |
| Focus overlay dims (not filters) arrows/marks | R3 | unit (pure) | `npx vitest run src/lib/__tests__/trainArrows.test.ts` | ✅ rewrite |
| `ChessBoard` honours `opacity` | R3 | unit | `npx vitest run src/components/board/__tests__/` | ✅ add |
| Verdict strip collapsed/expand content | R1 / D-05..D-08 | component | `npx vitest run src/components/train/__tests__/TrainVerdictStrip.test.tsx` | ❌ W0 |
| Action bar for whole reveal (<sm and sm..lg) | R5 | component | `TrainSolveScreen.test.tsx`, `App.test.tsx` | ✅ rewrite |
| Desktop ← → Home | R6 | unit | `useBoardNavigationInput` + hook tests | ✅/❌ |
| Tour copy ≤145 chars, screen-conditional | R7 / D-09 | unit | `trainBotCopy.test.ts` | ✅ update |
| Tour spotlight targets | R7 / D-10 | component | `TrainSolveScreen.test.tsx` walkthrough block | ✅ rewrite |
| SOLV-02: forks never reach grading | guardrail | component | `TrainSolveScreen.test.tsx` | ✅ port |
| Herring / server-graded marks kept | guardrail | component | `TrainSolveScreen.test.tsx` Phase 236 block | ✅ port |
| Restored reveal restores chip + tree | guardrail | unit + page | `trainRevealCache.test.ts`, `Train.solveLoop.test.tsx` | ✅ extend |
| Telemetry v2 shape, v1 still valid, parity | D-12 | unit + pytest | `useTrainPuzzleTelemetry.test.ts`; `uv run pytest tests/schemas/test_train_telemetry_schema.py tests/schemas/test_train_telemetry_parity.py` | ✅ update |
| Umami fires only on user actions | D-14 | component | `trackFeature` spy in TrainSolveScreen tests | ✅ add |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `frontend/src/hooks/__tests__/useTrainRevealTree.test.ts`
- [ ] `frontend/src/lib/__tests__/trainRevealLines.test.ts`
- [ ] `frontend/src/components/train/__tests__/TrainVerdictStrip.test.tsx`
- [ ] Shared `waitForReveal()` helper + stable reveal sentinel replacing the `train-verdict-guess` waits
- [ ] ChessBoard mock exposes arrow/marker opacities

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| First reveal view fits 390x844 with no scroll | R5 | jsdom has no layout | Agent browser UAT: same-origin 390x844 iframe, assert `scrollHeight <= innerHeight` |
| Tour readable, spotlight reaches bottom bar | R7 / D-11 | layout + overlay | Agent browser UAT at 390x844, 375x667, desktop |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
