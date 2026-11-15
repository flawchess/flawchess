---
phase: "255"
slug: "feature-discovery-dot-route"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
status: draft
nyquist_compliant: false
wave_0_complete: false
created: "2026-11-15"
---

# Phase 255 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Source: `255-RESEARCH.md` § Validation Architecture.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Backend: pytest (`asyncio_mode = "auto"`, per-worker cloned Postgres DB). Frontend: vitest (jsdom per file) |
| **Config file** | `pyproject.toml`, `frontend/vite.config.ts` |
| **Quick run command** | `uv run pytest tests/test_feature_route.py tests/test_migration_255_feature_route_seed.py -x` and `cd frontend && npx vitest run src/lib/__tests__/featureRoute.test.ts src/App.test.tsx` |
| **Full suite command** | `uv run pytest -n auto -x` and `cd frontend && npm run lint && npm run build && npm test -- --run && npm run knip` |
| **Estimated runtime** | quick ~60 seconds, full ~10 minutes |

---

## Sampling Rate

- **After every task commit:** Run the quick-run files touched by the task
- **After every plan wave:** Run `uv run pytest -n auto -x` and `cd frontend && npm test -- --run`
- **Before `/gsd-verify-work`:** The full CLAUDE.md pre-merge gate must be green (ruff format/check, ty x2, function-size gate, pytest `-n auto -x`, frontend lint/build/test/knip)
- **Max feedback latency:** 120 seconds for the quick run

---

## Per-Task Verification Map

Task IDs are filled in by the planner. Behaviours that must be covered (decision IDs stand in for requirement IDs):

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 255-01-01 | 01 | 1 | D-04, D-15, D-09 registry drift (backend) | T-255-02, T-255-03, T-255-04 | Guarded DONE keeps earlier steps and `feedback_v1`; repeat is a no-op; corrupt state fails closed with one Sentry capture; impersonation never writes; `get_args(FeatureRouteStepId)` in D-06 order | integration | `uv run pytest tests/test_feature_route.py -x` | ❌ W0 (created by 255-01-01) | ⬜ pending |
| 255-01-02 | 01 | 1 | D-04, D-19, D-11 | T-255-01 | Only the authenticated user's own row is written; guest writes allowed; promotion keeps state; profile GET writes nothing | integration | `uv run pytest tests/test_feature_route.py -x` | ✅ (extend) | ⬜ pending |
| 255-02-01 | 02 | 2 | D-14, D-15, D-18 (tracer e2e) | T-255-14, T-255-05 | Recorder posts done import on `/library/import`; no write for impersonation, null state or a locked target; backend leg re-runs the 255-01 pytest | component + integration | `uv run pytest tests/test_feature_route.py -x` and `cd frontend && npx vitest run src/components/feature-route/__tests__/FeatureRouteRecorder.test.tsx` | ❌ W0 (created by 255-02-01) | ⬜ pending |
| 255-02-01 | 02 | 2 | D-17, D-18, D-14, D-21 (header and bottom bar) | — | N/A | component | `cd frontend && npx vitest run src/App.test.tsx` | ✅ (rewrite) | ⬜ pending |
| 255-02-02, 255-04-02 | 02, 04 | 2, 3 | D-02, D-06, D-12 | — | N/A | unit | `cd frontend && npx vitest run src/lib/__tests__/featureRoute.test.ts` | ❌ W0 (created by 255-02-02) | ⬜ pending |
| 255-02-02 | 02 | 2 | D-03 | — | N/A | unit | `cd frontend && npx vitest run src/lib/__tests__/featureRoute.test.ts` | ❌ W0 (created by 255-02-02) | ⬜ pending |
| 255-02-02 | 02 | 2 | Locked targets (D-23 pause): a locked first unresolved step gives no dot and hides later steps, incl. a games-free step placed after a locked one (reordered-route case); Train and Bots never locked | — | N/A | unit | `cd frontend && npx vitest run src/lib/__tests__/featureRoute.test.ts` | ❌ W0 (created by 255-02-02) | ⬜ pending |
| 255-01-01, 255-02-02 | 01, 02 | 1, 2 | D-09 registry drift | — | N/A | unit | `uv run pytest tests/test_feature_route.py -x` (`get_args`) and `cd frontend && npx vitest run src/lib/__tests__/featureRoute.test.ts` | ❌ W0 | ⬜ pending |
| 255-03-01 | 03 | 3 | D-02, D-03, D-12, D-17, D-23 (all three nav surfaces, More drawer; zero-game account paused on openings shows no dot) | — | N/A | component | `cd frontend && npx vitest run src/App.test.tsx` | ✅ (extend) | ⬜ pending |
| 255-03-02 | 03 | 3 | Cleanup (D-04 retired keys), typed fixtures | T-255-15 | Only `user_flag:` keys and the two hint keys are removed; storage errors swallowed | unit | `cd frontend && npx vitest run src/lib/__tests__/retiredLocalStorage.test.ts` | ✅ (extend) | ⬜ pending |
| 255-04-01 | 04 | 3 | D-10, D-11 | T-255-06 | Skip rejected before 3 active days, accepted at since+3; `current` repost does not reset the stamp; profile GET writes nothing | integration | `uv run pytest tests/test_feature_route.py -x` | ✅ (extend) | ⬜ pending |
| 255-04-01 | 04 | 3 | D-15 | — | `done` recorded for a non-current step; skipped then done upgrades | integration | `uv run pytest tests/test_feature_route.py -x` | ✅ (extend) | ⬜ pending |
| 255-04-01 | 04 | 3 | D-23 clock paused (server) | T-255-16, T-255-17 | `delete_all_games_for_user` (router, guest purge, re-import script) removes `feature_route.current` (steps and `feedback_v1` kept, rows without a stamp untouched); a skip after it is a no-op; the next `current` restarts the clock; the callers' existing tests stay green | integration | `uv run pytest tests/test_feature_route.py -x`, `uv run pytest tests/test_imports_router.py -x -k DeleteAllGames` and `uv run pytest tests/test_guest_cleanup_service.py tests/test_reimport.py -x` | ✅ (extend) | ⬜ pending |
| 255-04-02 | 04 | 3 | D-23 clock paused (client) | — | No `current` and no skip planned while the first unresolved step is locked; after a skip a locked next step gets no stamp; a removed stamp is re-stamped with the unlock day's active days | unit | `cd frontend && npx vitest run src/lib/__tests__/featureRoute.test.ts` | ❌ W0 (created by 255-02-02) | ⬜ pending |
| 255-04-01 | 04 | 3 | Guards | T-255-01, T-255-02, T-255-03, T-255-04 | Impersonation no-op; unknown step/action and extra keys return 422; auth required; `feedback_v1` preserved; duplicate posts idempotent; corrupt state fails closed | integration | `uv run pytest tests/test_feature_route.py -x` | ✅ (extend) | ⬜ pending |
| 255-04-03 | 04 | 3 | D-16, D-22 | T-255-08 | Migration seeds exactly the launch step IDs for existing rows incl. guests, preserves `feedback_v1`, idempotent, downgrade removes only `feature_route` | migration | `uv run pytest tests/test_migration_255_feature_route_seed.py -x` | ❌ W0 (created by 255-04-03) | ⬜ pending |
| 255-06-01, 255-06-02 | 06 | 3 | D-21 | T-255-12 | N/A | component | `cd frontend && npx vitest run src/pages/__tests__/Train.subnav.test.tsx src/components/train/__tests__/TrainStartScreen.test.tsx` | ✅ (extend) | ⬜ pending |
| 255-05-02 | 05 | 3 | D-07, D-13 (incl. any click on the mobile Stats colour switch) | T-255-10 | N/A | component | `cd frontend && npx vitest run src/pages/__tests__/Openings.render.test.tsx src/components/openings/__tests__/OpeningColorSwitch.test.tsx` | ✅ (extend) | ⬜ pending |
| 255-05-01 | 05 | 3 | Subtab dots (D-03, D-20; zero-game Library Stats paused, D-23) | — | N/A | component | `cd frontend && npx vitest run src/pages/library/__tests__/LibraryPage.reroute.test.tsx src/pages/__tests__/Openings.render.test.tsx` | ✅ (extend) | ⬜ pending |
| 255-07-01 | 07 | 4 | Full gate, single Alembic head | T-255-13 | N/A | gate | CLAUDE.md pre-merge gate (Plan 07 Task 1) | ✅ | ⬜ pending |
| 255-07-02 | 07 | 4 | Dot geometry walk (D-02, D-03, D-20); D-23 pause (a zero-game account sees no dot after Import, Train and Bots until its games are imported) | — | N/A | manual | checkpoint:human-verify route walk at 1280 px and 390 px | — | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_feature_route.py` — endpoint, guards, auto-skip clock
- [ ] `tests/test_migration_255_feature_route_seed.py` — existing-user seed
- [ ] `frontend/src/lib/__tests__/featureRoute.test.ts` — registry and arbiter
- [ ] Profile fixtures updated for the new `feature_route` field (plan 255-03 Task 2)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Dot geometry on subtabs, sidebar controls and the mobile drawer path | D-03, D-20, D-23 | Visual placement is not asserted by jsdom | Browser UAT on desktop and mobile widths with a fresh signup: walk the route and check at most one dot at a time, none while a zero-game account is paused on the locked Openings step |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 120s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
