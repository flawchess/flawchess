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
- **Mutation proof:** for the once-per-UTC-day view guard and the round-2 cap, temporarily drop the guard clause and confirm a test fails (project memory: mutation-test gap closures)

---

## Per-Task Verification Map

Filled by the planner/executor from the plans. Requirement → test map from 234-RESEARCH.md "Validation Architecture":

| Requirement | Behavior | Test Type | Automated Command | File Exists | Status |
|-------------|----------|-----------|-------------------|-------------|--------|
| FBASK-01 | `prompt_state` defaults `{}`; `feedback.source` defaults `floating_button`, CHECK rejects others | integration | `uv run pytest tests/test_feedback_ask.py -k migration_defaults -x` | ❌ W0 | ⬜ pending |
| FBASK-02 | GET and PUT profile return identical `active_days` + `feedback_ask` | integration | `uv run pytest tests/test_feedback_ask.py -k profile -x` | ❌ W0 | ⬜ pending |
| FBASK-03 | `resolve_feedback_ask` truth table; today-inclusive `active_days` | unit + integration | `uv run pytest tests/services/test_feedback_ask_service.py -x` | ❌ W0 | ⬜ pending |
| FBASK-04 | view/snooze/done atomic transitions, same-day no-op, concurrency, guards (422, impersonation, guest) | integration (real Postgres) | `uv run pytest tests/test_feedback_ask.py -k "transition or concurrent or guards" -x` | ❌ W0 | ⬜ pending |
| FBASK-05 | POST /feedback `source` persisted/defaulted/validated; modal placeholder + source | integration + component | `uv run pytest tests/test_feedback_router.py -x` | ✅ extend | ⬜ pending |
| FBASK-06 | Bubble render, view on mount, Later/Sure behavior, app-level modal host survives unmount, Umami events | component | `cd frontend && npm test -- --run src/components/feedback` | ❌ W0 | ⬜ pending |
| FBASK-07 | Import page: ask replaces EXPLORE_PARTS and welcome variants when active | component | `cd frontend && npm test -- --run src/components/import src/pages/__tests__/Import` | ✅ extend | ⬜ pending |
| FBASK-08 | Train landing: Hilda after intro done, no reminder ask, visible on phones | component | `cd frontend && npm test -- --run src/components/train/__tests__/TrainStartScreen.test.tsx` | ✅ extend | ⬜ pending |
| FBASK-09 | Bots roster: info popover hidden, Hilda shown while active | component | `cd frontend && npm test -- --run src/components/bots/__tests__/PersonaGrid.test.tsx` | ✅ extend | ⬜ pending |
| FBASK-10 | Umami ACTION_TARGETS kebab-case | unit | `cd frontend && npm test -- --run src/lib/__tests__/analytics.test.ts` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_feedback_ask.py` — router + repository integration (helper to seed `user_activity` rows; cleanup deletes the user, CASCADE removes activity/feedback)
- [ ] `tests/services/test_feedback_ask_service.py` — pure truth table
- [ ] `frontend/src/components/feedback/__tests__/FeedbackAskBubble.test.tsx` — QueryClientProvider harness (template: `FeedbackButton.test.tsx`)

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
