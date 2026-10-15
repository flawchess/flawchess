---
phase: "240"
slug: "train-first-session-onboarding-load"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: draft
nyquist_compliant: false
wave_0_complete: false
created: "2026-10-15"
---

# Phase 240 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (async, per-session cloned PostgreSQL DB) + Vitest (jsdom) |
| **Config file** | `pyproject.toml` / `tests/conftest.py`; `frontend/vite.config.ts` test block + `frontend/src/vitest.setup.ts` |
| **Quick run command** | backend: `uv run pytest tests/routers/test_train.py -k "onboarding or settings" -x`; frontend: `cd frontend && npx vitest run src/lib/__tests__/trainBotCopy.test.ts` |
| **Full suite command** | `uv run pytest -n auto -x` and `cd frontend && npm run lint && npm run build && npm test -- --run && npm run knip` |
| **Estimated runtime** | ~30 seconds quick, ~6 minutes full |

---

## Sampling Rate

- **After every task commit:** quick command for the touched area, plus `npm run build` for any frontend type change (vitest does not type-check; narrowing `IntroStep` breaks `trainBubbleState.test.ts` only under `tsc -b`)
- **After every plan wave:** full suite for the touched stack
- **Before `/gsd-verify-work`:** full pre-merge gate from CLAUDE.md green, including `scripts/check_function_size.py app/ --fail-over-depth 4`
- **Max feedback latency:** 60 seconds

---

## Per-Task Verification Map

Requirement-level map from 240-RESEARCH.md §Validation Architecture (task IDs filled by the planner).

| Decision | Behavior | Test Type | Automated Command | File Exists | Status |
|----------|----------|-----------|-------------------|-------------|--------|
| D-01 | intro is [welcome, closing], count 2 for every audience | unit + component | `cd frontend && npx vitest run src/lib/__tests__/trainBotCopy.test.ts -t intro` / `TrainSolveScreen.test.tsx -t "intro stepper"` | ✅ rewrite | ⬜ pending |
| D-02 | no warm-up step in intro; warm-up verdict tail unchanged | unit | `trainBotCopy.test.ts` | ✅ | ⬜ pending |
| D-03/D-04 | P1 copy per device × answer kind; herring and soft map to several | unit + component | `-t tour` in both files | ❌ W0 | ⬜ pending |
| D-05/D-06 | part split, every step ≤145, no points mention, no em-dash | unit | `trainBotCopy.test.ts -t tour` | ✅ rewrite | ⬜ pending |
| D-07/D-08 | one part per reveal (latch), stamp on leaving last step, abandon stamps nothing | component | `TrainSolveScreen.test.tsx -t tour` | ❌ W0 latch | ⬜ pending |
| D-09/D-11 | forward-only stage advance; old step → 422 | router + repo | `uv run pytest tests/routers/test_train.py -k onboarding -x` | ✅ adapt | ⬜ pending |
| D-10 | migration backfill 3/0, old column dropped, downgrade restores | migration | `uv run pytest tests/test_migration_240_reveal_tour_stage.py -x` | ❌ W0 | ⬜ pending |
| D-13/D-14/D-15 | first-ever session reorder (sharp slot 0, several in 1-2), later sessions untouched | unit + repo | `uv run pytest tests/repositories/test_train_repository.py -k first_session -x` | ❌ W0 | ⬜ pending |
| D-16/D-17/D-18/D-21 | rationale in all first-completed branches, stamp in any branch, no returning-counts sentence | unit + component | `trainBotCopy.test.ts -t scoreBubbleCopy` / `TrainScoreScreen.test.tsx -t "score bubble"` | ✅ rewrite/flip | ⬜ pending |
| D-19 | exact copy strings | unit | string equality per variant | ❌ new | ⬜ pending |
| D-20/D-23 | shared spotlight class on every target, chips row highlighted, reduced motion; per-part counter | component | `TrainSolveScreen.test.tsx -t "ring follows"` rewrite | ✅ rewrite | ⬜ pending |
| D-22 | landing reminder ask gated on stage ≥ 3 | component | `TrainStartScreen.test.tsx` | ✅ adapt | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_migration_240_reveal_tour_stage.py` — BASE_REVISION `778c806092fb`, pattern `tests/test_migration_186_user_import_settings.py`
- [ ] First-session reorder tests in `tests/repositories/test_train_repository.py` (pure helper table + integration + not-first-ever case)
- [ ] Tour latch test in `frontend/src/components/train/__tests__/TrainSolveScreen.test.tsx`

---

## Manual-Only Verifications

| Behavior | Decision | Why Manual | Test Instructions |
|----------|----------|------------|-------------------|
| Score stays above the fold at 375x667 with worst-case ~230-char line 1 | D-16 | layout | browser UAT at 390x844, 375x667, desktop |
| Glow not clipped (board row, fixed phone action bar), overlay reads as Hilda | D-20 | visual | browser UAT, all three tour parts |
| Prod funnel "before" snapshot | Measure | needs prod tunnel + MCP (orchestrator/human only) | run SEED-200 SQL before the migration deploys; commit as `240-FUNNEL-BEFORE.md` |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
