---
phase: 255-feature-discovery-dot-route
plan: 01
subsystem: api
tags: [fastapi, postgres, jsonb, prompt_state, feature-route, pydantic]
requires: []
provides:
  - "users.prompt_state.feature_route storage with a guarded DONE transition"
  - "POST /api/users/me/feature-route (done, any launch step, guests included)"
  - "profile.feature_route on GET/PUT /api/users/me/profile"
affects: [255-02, 255-03, 255-04]
tech-stack:
  added: []
  patterns:
    - "guarded UPDATE ... RETURNING on users.prompt_state with nested steps merge (copied from feedback ask, minus the guest exclusion)"
    - "fail-closed profile view: corrupt stored state gives null plus one Sentry capture"
key-files:
  created:
    - app/schemas/feature_route.py
    - app/repositories/feature_route_repository.py
    - app/services/feature_route_service.py
    - tests/test_feature_route.py
  modified:
    - app/schemas/users.py
    - app/routers/users.py
key-decisions:
  - "Step IDs are the nine D-06 strings (import, train, bots, openings, openings-played-as, openings-filters, openings-stats, endgames, library-stats), append-only"
  - "A visit to a skipped step upgrades it to done (A-4); a repeated done keeps the first record"
  - "with_dot records whether the step was current when resolved (A-5), for measuring the route in Postgres"
requirements-completed: [D-04, D-06, D-09, D-11, D-15, D-19]
duration: 20 min
completed: 2026-11-15
status: complete
commits: 4
plan_head_before: 52edb6de98c62e9430cf5d2aa65e96c550b20405
plan_head_after: 63d7d08b03d435a45ceae2f133bd67c8ae127151
actuals:
  tokens: 5500
  tasks: 2
  commits: 4
coverage:
  - deliverable: "Route state stored in users.prompt_state.feature_route via guarded DONE UPDATE, nested merge, feedback_v1 preserved"
    human_judgment: false
    verification:
      - kind: test
        ref: "tests/test_feature_route.py#test_second_step_keeps_first_and_repeat_is_noop"
        status: pass
      - kind: test
        ref: "tests/test_feature_route.py#test_done_keeps_feedback_state"
        status: pass
  - deliverable: "Fail-closed profile view and impersonation no-write"
    human_judgment: false
    verification:
      - kind: test
        ref: "tests/test_feature_route.py#test_build_view_corrupt_state_fails_closed"
        status: pass
      - kind: test
        ref: "tests/test_feature_route.py#test_impersonated_session_never_writes"
        status: pass
  - deliverable: "POST /users/me/feature-route and profile.feature_route, guests included, survives promotion"
    human_judgment: false
    verification:
      - kind: test
        ref: "tests/test_feature_route.py#test_post_done_is_stored_returned_and_idempotent"
        status: pass
      - kind: test
        ref: "tests/test_feature_route.py#test_guest_route_is_stored_and_survives_email_promotion"
        status: pass
      - kind: test
        ref: "tests/test_feature_route.py#test_profile_feature_route_is_empty_and_reads_never_write"
        status: pass
  - deliverable: "Step ID list pinned in D-06 order"
    human_judgment: false
    verification:
      - kind: test
        ref: "tests/test_feature_route.py#test_step_ids_are_pinned_in_d06_order"
        status: pass
---

# Phase 255 Plan 01: Feature Route Storage and API Summary

Server-side feature-discovery route state on `users.prompt_state.feature_route`: a guarded DONE transition, `POST /users/me/feature-route` and `profile.feature_route`, for registered users and guests alike.

## Accomplishments

- Schema module with `FEATURE_ROUTE_KEY`, the nine-step `FeatureRouteStepId` Literal in D-06 order (pinned by a list test), and the stored-state models (`extra="forbid"`, steps keyed by plain `str` so a stored ID always validates).
- Repository with one CAST-typed guarded `UPDATE ... RETURNING` (`_DONE_SQL`): nested `steps` merge, only the `feature_route` key replaced (`feedback_v1` survives), no guest exclusion (D-19), absent or skipped may become done, a repeat matches no row and the service re-reads.
- Service: `build_feature_route_view` (no I/O, fail closed with one Sentry capture) and `apply_feature_route_action` (impersonation never writes, always 200 and idempotent, rollback plus capture on a corrupt RETURNING value).
- `UserProfileResponse.feature_route` set in the shared `_build_profile_response` (zero extra queries, reads never write) and `POST /users/me/feature-route` with the same dependencies as the feedback ask endpoint.

## Task Commits

| Task | Commit | Type |
| ---- | ------ | ---- |
| 1 RED | 78f1d63f6 | test |
| 1 GREEN | 538687666 | feat |
| 2 RED | c3315bfdd | test |
| 2 GREEN | 63d7d08b0 | feat |

## Deviations from Plan

None - plan executed exactly as written.

Verification: `uv run pytest tests/test_feature_route.py -x` (10 passed), the related `test_feedback_ask.py`, `test_guest_auth.py`, `test_users_router.py`, `test_users_profile_impersonation_field.py` and `test_users_first_touch.py` still pass, `ruff check`, `ty check app/ tests/ scripts/` and `check_function_size.py app/ --fail-over-depth 4` are clean. All acceptance greps hold (`NOT is_guest` count is 0).

## Known Stubs

None.

## Threat Flags

None. The new endpoint and profile field are the ones in the plan's threat model (T-255-01..04); mitigations are in place (user id only from `current_active_user`, Literal-restricted step, `extra="forbid"`, impersonation no-op, fail-closed view).

## Next Phase Readiness

Plan 255-02 can mirror `FeatureRouteStepId` / `FeatureRouteState` in `frontend/src/types/users.ts` and consume `profile.feature_route` and the POST endpoint. The `current` and `skip` actions (and the `current` SQL) are deliberately absent here and arrive in plan 255-04.

## Self-Check: PASSED

All four created files exist, all four commits are ancestors of HEAD, and the task acceptance criteria re-ran green.
