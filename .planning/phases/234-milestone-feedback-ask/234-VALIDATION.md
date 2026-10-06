---
phase: "234"
slug: "milestone-feedback-ask"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: draft
nyquist_compliant: false
wave_0_complete: false
created: "2026-10-05"
---

# Phase 234 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest + pytest-asyncio (backend), Vitest + Testing Library (frontend) |
| **Config file** | `pyproject.toml` / `tests/conftest.py`; `frontend/vite.config.ts` test block |
| **Quick run command** | `uv run pytest tests/test_feedback_ask.py tests/services/test_feedback_ask_service.py tests/test_feedback_router.py -x` / `cd frontend && npm test -- --run src/components/feedback` |
| **Full suite command** | `uv run pytest -n auto -x` and `cd frontend && npm run lint && npm run build && npm test -- --run && npm run knip` |
| **Estimated runtime** | ~30 seconds quick, ~6 minutes full |

---

## Sampling Rate

- **After every task commit:** Run the quick-run command for the touched side (backend or frontend)
- **After every plan wave:** Run the full suite command
- **Before `/gsd-verify-work`:** Full pre-merge gate must be green
- **Max feedback latency:** 60 seconds
- **Mutation proof:** for the once-per-UTC-day view guard and the round-2 cap (plan 01 T2) and the `source=data.source` write (plan 03 T1), temporarily drop the guard or write and confirm a test fails (project memory: mutation-test gap closures)

---

## Per-Task Verification Map

Filled by the planner from the plans (234-01 backend ask state + eligibility + endpoint, 234-02 frontend shared ask + Import + FeedbackModal props, 234-03 "Sure!" end to end: feedback source attribution + app-level modal host, 234-04 Train + Bots + gate). Requirement → test map (refines 234-RESEARCH.md "Validation Architecture"):

| Requirement | Plan / Task | Behavior | Test Type | Automated Command | File Exists | Status |
|-------------|-------------|----------|-----------|-------------------|-------------|--------|
| FBASK-01 | 01 / T1; 03 / T1 | `prompt_state` defaults `{}` (object, NOT NULL); `feedback.source` defaults `floating_button`; `ck_feedback_source` rejects others; migration round trip | integration | `uv run pytest tests/test_feedback_ask.py -k new_user_prompt_state -x` (01) and `uv run pytest tests/test_feedback_repository.py -x` (03) | ❌ W0 / ✅ extend | ⬜ pending |
| FBASK-02 | 01 / T1 | GET and PUT profile return identical `active_days` + `feedback_ask` | integration | `uv run pytest tests/test_feedback_ask.py -k "profile or get_and_put" -x` | ❌ W0 | ⬜ pending |
| FBASK-03 | 01 / T1, T2 | `resolve_feedback_ask` truth table; `active_days = rows before today + 1` (today counts once); any feedback ends the ask | unit + integration | `uv run pytest tests/services/test_feedback_ask_service.py tests/test_feedback_ask.py -x` | ❌ W0 | ⬜ pending |
| FBASK-04 | 01 / T1, T2 | view/snooze/done transitions, same-day no-op, 3rd-view grace, round 2 after +10, exhaustion, unrelated key preserved, concurrency, guards (422, impersonation, guest, 401) | integration (real Postgres) | `uv run pytest tests/repositories/test_feedback_ask_repository.py tests/test_feedback_ask.py -x` | ❌ W0 | ⬜ pending |
| FBASK-05 | 02 / T2; 03 / T1, T2 | POST /feedback `source` persisted/defaulted/422; modal placeholder + source; profile invalidated after submit | integration + component | `uv run pytest tests/test_feedback_router.py -x` and `cd frontend && npx vitest run src/components/feedback/__tests__/FeedbackModal.test.tsx src/hooks/__tests__/useFeedback.test.tsx` | ✅ extend / ❌ W0 | ⬜ pending |
| FBASK-06 | 02 / T1; 03 / T2 | Bubble render, one view on mount, Later hides before the response, view never resurrects, Sure opens the app-level host that survives unmount, Umami events only on click | component (real QueryClient) | `cd frontend && npx vitest run src/components/feedback/__tests__/FeedbackAskBubble.test.tsx` | ❌ W0 | ⬜ pending |
| FBASK-07 | 02 / T1 | Import page: ask replaces the welcome and explore variants when active (D-03); inactive unchanged | component | `cd frontend && npx vitest run src/pages/__tests__/Import.feedbackAsk.test.tsx` | ❌ W0 | ⬜ pending |
| FBASK-08 | 04 / T1 | Train landing: Hilda after intro done (D-04), no reminder ask, no `max-sm:hidden` while active | component | `cd frontend && npx vitest run src/components/train/__tests__/TrainStartScreen.test.tsx` | ✅ extend | ⬜ pending |
| FBASK-09 | 04 / T2 | Bots roster: Hilda shown, info popover hidden while active | component | `cd frontend && npx vitest run src/components/bots/__tests__/PersonaGrid.test.tsx` | ✅ extend | ⬜ pending |
| FBASK-10 | 02 / T1 | Umami ACTION_TARGETS kebab-case | unit | `cd frontend && npx vitest run src/lib/__tests__/analytics.test.ts` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_feedback_ask.py` — router integration (helper to seed `user_activity` rows; dev clock pinned to a date before the real one; cleanup deletes the user, CASCADE removes activity/feedback) — plan 01 T1/T2
- [ ] `tests/repositories/test_feedback_ask_repository.py` — transition matrix on the rollback-scoped `db_session` — plan 01 T2
- [ ] `tests/services/test_feedback_ask_service.py` — pure truth table — plan 01 T2
- [ ] `frontend/src/components/feedback/__tests__/FeedbackAskBubble.test.tsx` — QueryClientProvider harness (template: `TrainMedalDialogHost.test.tsx`) — plan 02 T1, plan 03 T2
- [ ] `frontend/src/pages/__tests__/Import.feedbackAsk.test.tsx` — Import page harness (template: `Import.queuedState.test.tsx`) — plan 02 T1
- [ ] `frontend/src/hooks/__tests__/useFeedback.test.tsx` — profile invalidation — plan 02 T2

No framework install needed.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| One view per UTC day across all three surfaces, Hilda on all three | FBASK-04/06 | Cross-page browser flow | Seed a dev user with 5 `user_activity` rows; walk Import → Train → Bots on one day; confirm one view counted and Hilda on all three (run it yourself in the browser) |
| Phone width on Train landing | FBASK-08 | Responsive layout | Resize to phone width; Hilda bubble visible above the reminder ask slot |
| Modal survives import poll | FBASK-06 | Live polling | Click "Sure!" during an active import poll; modal and draft persist |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
