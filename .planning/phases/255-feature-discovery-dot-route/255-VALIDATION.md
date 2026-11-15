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
| TBD | TBD | TBD | D-04, D-19 | — | Only the authenticated user's own row is written; guest writes allowed; promotion keeps state | integration | `uv run pytest tests/test_feature_route.py -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | D-10, D-11 | — | Skip rejected before 3 active days, accepted at since+3; `current` repost does not reset the stamp; profile GET writes nothing | integration | `uv run pytest tests/test_feature_route.py -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | D-15 | — | `done` recorded for a non-current step; skipped then done upgrades | integration | `uv run pytest tests/test_feature_route.py -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | Guards | T-255-xx | Impersonation no-op; unknown step/action and extra keys return 422; auth required; `feedback_v1` preserved; duplicate posts idempotent; corrupt state fails closed | integration | `uv run pytest tests/test_feature_route.py -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | D-16, D-22 | — | Migration seeds exactly the launch step IDs for existing rows incl. guests, preserves `feedback_v1`, idempotent, downgrade removes only `feature_route` | migration | `uv run pytest tests/test_migration_255_feature_route_seed.py -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | D-02, D-06, D-12 | — | N/A | unit | `cd frontend && npx vitest run src/lib/__tests__/featureRoute.test.ts` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | D-03 | — | N/A | unit | `cd frontend && npx vitest run src/lib/__tests__/featureRoute.test.ts` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | Locked targets | — | N/A | unit | `cd frontend && npx vitest run src/lib/__tests__/featureRoute.test.ts` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | D-09 registry drift | — | N/A | unit | vitest registry test plus pytest `get_args` check | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | D-17, D-18, D-14 | — | N/A | component | `cd frontend && npx vitest run src/App.test.tsx` | ✅ (rewrite) | ⬜ pending |
| TBD | TBD | TBD | D-21 | — | N/A | component | `cd frontend && npx vitest run src/pages/__tests__/Train.subnav.test.tsx` (path per research) | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | D-07, D-13 | — | N/A | component | `cd frontend && npx vitest run src/pages/__tests__/Openings.render.test.tsx` | ✅ (extend) | ⬜ pending |
| TBD | TBD | TBD | Subtab dots | — | N/A | component | Library and Openings subtab tests | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | Cleanup | — | N/A | unit | `cd frontend && npx vitest run src/lib/__tests__/retiredLocalStorage.test.ts` | ✅ (extend) | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_feature_route.py` — endpoint, guards, auto-skip clock
- [ ] `tests/test_migration_255_feature_route_seed.py` — existing-user seed
- [ ] `frontend/src/lib/__tests__/featureRoute.test.ts` — registry and arbiter
- [ ] Profile fixtures updated for the new `feature_route` field

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Dot geometry on subtabs, sidebar controls and the mobile drawer path | D-03, D-20 | Visual placement is not asserted by jsdom | Browser UAT on desktop and mobile widths with a fresh signup: walk the route and check one dot at a time |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 120s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
