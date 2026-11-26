---
phase: 255-feature-discovery-dot-route
plan: 04
subsystem: api
tags: [fastapi, postgres, jsonb, alembic, react, feature-route, vitest]
requires:
  - phase: 255-feature-discovery-dot-route
    provides: "guarded DONE transition and POST /users/me/feature-route (255-01), registry, arbiter and recorder (255-02)"
provides:
  - "guarded CURRENT and SKIP transitions on users.prompt_state.feature_route (skip applies at since_days + 3 active days)"
  - "clear_current, called from delete_all_games_for_user (D-23 stamp removal)"
  - "client clock: isCandidateExpired, skip and current planning, optimistic current and skip"
  - "data-only seed migration c3f8e2a6d255: nine launch step IDs done for every existing user"
affects: [255-05, 255-06, 255-07]
tech-stack:
  added: []
  patterns:
    - "server twin of a client rule enforced in the UPDATE's WHERE guard (skip cannot fire early)"
    - "locked step never stamped or skipped (findCandidate stop rule), existing stamp removed when all games are deleted"
key-files:
  created:
    - alembic/versions/20261115_180000_c3f8e2a6d255_phase_255_feature_route_seed.py
    - tests/test_migration_255_feature_route_seed.py
  modified:
    - app/schemas/feature_route.py
    - app/repositories/feature_route_repository.py
    - app/repositories/game_repository.py
    - app/services/feature_route_service.py
    - tests/test_feature_route.py
    - frontend/src/types/users.ts
    - frontend/src/lib/featureRoute.ts
    - frontend/src/lib/__tests__/featureRoute.test.ts
    - frontend/src/hooks/useFeatureRoute.ts
    - frontend/src/hooks/useRecordFeatureRoute.ts
    - frontend/src/components/feature-route/FeatureRouteRecorder.tsx
    - frontend/src/components/feature-route/__tests__/FeatureRouteRecorder.test.tsx
key-decisions:
  - "A step that was current when its target locked again restarts its clock on unlock (A-7): delete_all_games_for_user removes feature_route.current unconditionally; a sub-day lock (readiness fetch, import in flight) leaves the stamp"
  - "The server does not compute the lock; the client rule plus the removed stamp suffice (T-255-17)"
  - "The recorder forgets its sent current/skip keys whenever the stored stamp changes, so a stamp removed by delete-all-games can be re-posted in the same session"
requirements-completed: [D-04, D-09, D-10, D-11, D-12, D-15, D-16, D-19, D-22, D-23]
duration: 45 min
completed: 2026-11-15
status: complete
commits: 5
plan_head_before: 58a29047ee55b0459e1063086e3f390e39d7e896
plan_head_after: 7d1b44440beea55fee393287a09ce19e5ccbbe27
actuals:
  tokens: 30000
  tasks: 3
  commits: 5
coverage:
  - deliverable: "D-10 clock: skip is a no-op at since_days + 2 and applies at + 3, enforced in SQL"
    human_judgment: false
    verification:
      - kind: test
        ref: "tests/test_feature_route.py#test_skip_timeline_applies_exactly_at_since_days_plus_three"
        status: pass
  - deliverable: "D-11 / D-15 / D-19: re-posted current keeps since_days, GETs write nothing, with_dot follows current, guests stamp and skip"
    human_judgment: false
    verification:
      - kind: test
        ref: "tests/test_feature_route.py#test_current_repost_keeps_since_days_and_reads_never_write"
        status: pass
      - kind: test
        ref: "tests/test_feature_route.py#test_done_with_dot_follows_current_and_upgrades_skip"
        status: pass
      - kind: test
        ref: "tests/test_feature_route.py#test_guest_stamps_current_and_skips"
        status: pass
  - deliverable: "Guards: impersonation, 422/401, feedback_v1, concurrency, corrupt state"
    human_judgment: false
    verification:
      - kind: test
        ref: "tests/test_feature_route.py (impersonation, validation, feedback, concurrent, corrupt cases)"
        status: pass
  - deliverable: "D-23 server: delete-all-games removes the current stamp, refuses a later skip, clock restarts on unlock; untouched rows stay byte-identical"
    human_judgment: false
    verification:
      - kind: test
        ref: "tests/test_feature_route.py#test_delete_all_games_removes_current_stamp_and_restarts_the_clock"
        status: pass
      - kind: test
        ref: "tests/test_feature_route.py#test_delete_all_games_for_user_clears_the_stamp_for_every_caller"
        status: pass
  - deliverable: "D-10 / D-12 / D-23 client: expiry, skip then current planning, no stamp or skip while the first unresolved step is locked"
    human_judgment: false
    verification:
      - kind: test
        ref: "frontend/src/lib/__tests__/featureRoute.test.ts (the 3-active-day clock, locked steps never run the clock)"
        status: pass
      - kind: test
        ref: "frontend/src/components/feature-route/__tests__/FeatureRouteRecorder.test.tsx#(f),(g)"
        status: pass
  - deliverable: "D-16 / D-22 seed migration: nine IDs done for every existing row, idempotent, feedback_v1 survives, new rows start {}"
    human_judgment: false
    verification:
      - kind: test
        ref: "tests/test_migration_255_feature_route_seed.py"
        status: pass
---

# Phase 255 Plan 04: Route Clock and Seed Summary

The route now has a clock and a starting point: an ignored step auto-skips after three active days with the dot on it (server-enforced), a locked step never runs the clock, and every account existing at deploy starts with the launch route done.

## Accomplishments

- Server: `_CURRENT_SQL` (stamps `current` once per step transition, repeat keeps `since_days`), `_SKIP_SQL` (guard: stored current is the step, step unresolved, `active_days >= since_days + FEATURE_ROUTE_SKIP_ACTIVE_DAYS`), `_CLEAR_CURRENT_SQL`. The service computes the today-inclusive count via `feedback_ask_repository.count_active_days_before + 1`, the same count as `profile.active_days`.
- D-23: `game_repository.delete_all_games_for_user` calls `feature_route_repository.clear_current`, so the router, the inactive-guest purge and `scripts/reimport_games.py` all remove the stamp inside their own transaction. The `current IS NOT NULL` guard keeps rows without a stamp, or without `feature_route`, byte-identical.
- Client: `isCandidateExpired`, `resolveRouteDot` yields null for an expired candidate, `planRouteWrites` returns done requests then a skip for an expired candidate then a current stamp for the resulting candidate, all through `findCandidate` (the one copy of the D-23 stop rule). `applyRouteWrite` and `isRouteWriteNeeded` gained the current and skip branches; `useRouteCtx` supplies `activeDays` from the profile and the mutation's optimistic patch uses it.
- Migration `c3f8e2a6d255` (down_revision `a7d2c9e1b254`, the single head before and after): data-only, ids hard-coded, `WHERE prompt_state->'feature_route' IS NULL`, downgrade removes only `feature_route`. Round-trip on the dev DB (`upgrade head`, `downgrade -1`, `upgrade head`) ran clean.

## Task Commits

| Task | Commit | Type |
| ---- | ------ | ---- |
| 1 RED (server clock, D-23, guards) | 574f9f981 | test |
| 1 GREEN | 4e567c016 | feat |
| 2 RED (client clock) | 604aa82ca | test |
| 2 GREEN | 12b4d2b4f | feat |
| 3 (seed migration and tests) | 7d1b44440 | feat |

## Mutation check (D-23 re-lock)

Replacing the `clear_current` call in `delete_all_games_for_user` with `pass` made `test_delete_all_games_removes_current_stamp_and_restarts_the_clock` and `test_delete_all_games_for_user_clears_the_stamp_for_every_caller` fail (2 failed, 21 passed). The call was restored and all 23 tests in `tests/test_feature_route.py` pass.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] FeatureRouteRecorder.tsx needed an edit although the plan expected it unchanged**
- **Found during:** Task 2
- **Issue:** The recorder built its own `RouteCtx` literal (`{ pathname, navUnlocked }`), which no longer type-checks once `activeDays` is required, so the clock could never see the active-day count. Its sent-key ref (`action:step`) would also have blocked re-stamping `current openings` after delete-all-games removed the stamp in the same session, defeating the D-23 restart until a reload.
- **Fix:** The recorder passes `activeDays` from `useRouteCtx`, and forgets its sent current/skip keys whenever the stored stamp signature changes (done keys stay). A server no-op that leaves the stamp unchanged keeps the keys, so no POST loop. Two recorder test cases (f: skip then current, g: locked step posts nothing) were added.
- **Files modified:** frontend/src/components/feature-route/FeatureRouteRecorder.tsx, frontend/src/components/feature-route/__tests__/FeatureRouteRecorder.test.tsx
- **Commit:** 12b4d2b4f

**2. [Rule 1 - Test adaptation] Plan 255-02 planRouteWrites cases now filter to done requests**
- **Found during:** Task 2
- **Issue:** Six cases asserted the exact `planRouteWrites` output for done recording; the new current stamp legitimately appears in that output.
- **Fix:** Those cases use a `doneWrites` helper (filters `action === 'done'`); the clock behaviour has its own cases. No assertion about done recording was weakened.
- **Commit:** 12b4d2b4f

Otherwise the plan was executed as written. The seed test compares step IDs as a set because jsonb does not preserve key order.

## Known Stubs

None.

## Threat Flags

None. The new surface (current and skip on the existing endpoint, the stamp removal, the seed) is covered by T-255-06..09, T-255-16 and T-255-17.

## Verification Run

- `tests/test_feature_route.py` 23 passed; `tests/test_migration_255_feature_route_seed.py` 4 passed; `tests/test_imports_router.py -k DeleteAllGames` 8 passed; `tests/test_guest_cleanup_service.py tests/test_reimport.py` 23 passed. The full backend suite is deferred to plan 255-07 as instructed.
- `ruff check`, `ruff format --check`, `ty check app/ tests/ scripts/`, `check_function_size.py app/ --fail-over-depth 4`: clean. `alembic heads`: `c3f8e2a6d255 (head)` only.
- Frontend: `featureRoute.test.ts` and `FeatureRouteRecorder.test.tsx` 48 passed, `npm run lint`, `npm run build` clean; `npm run knip` reports only the two pre-existing configuration hints (no unused exports or files).
- Acceptance greps: `FEATURE_ROUTE_SKIP_ACTIVE_DAYS` defined in both stacks with value 3, `NOT is_guest` count 0, `feature_route_repository.clear_current` count 1 in game_repository.py, `from app` count 0 in the migration.

## Next Phase Readiness

Plans 255-05 and 255-06 can use `useRouteDot` and `useRecordFeatureRoute` for subtab and control dots; the clock needs no further wiring. The dev DB was seeded by the round-trip, so route UAT needs a fresh signup.

## Self-Check: PASSED

All created files exist, and commits 574f9f981, 4e567c016, 604aa82ca, 12b4d2b4f and 7d1b44440 are ancestors of HEAD.
