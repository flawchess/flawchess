---
phase: 240-train-first-session-onboarding-load
plan: 01
subsystem: api
tags: [alembic, postgres, fastapi, sqlalchemy, onboarding, train]

requires:
  - phase: 222-train-bot-onboarding
    provides: "POST /train/onboarding/{step}, stamp_onboarding_step, reveal_walkthrough_seen_at (now retired)"
provides:
  - "train_settings.reveal_tour_stage SmallInteger 0..3 (CHECK ck_train_settings_reveal_tour_stage), forward-only"
  - "POST /train/onboarding/reveal_tour_1..3 advancing the stage; retired walkthrough step name returns 422"
  - "reveal_tour_stage on every TrainSettingsResponse (GET/PUT settings, every onboarding POST)"
  - "REVEAL_TOUR_STAGE_MAX constant in app/services/train_scheduler.py"
affects: [240-03, 240-04, 240-07, train-frontend, deploy]

actuals:
  tokens: 45000
  tasks: 2
  commits: 2
plan_head_before: 37398801f3e73bb03007b92e84c20716604baa04
plan_head_after: 5f8b987f6024d1667ebda4313fa87b8f1f075eb0

tech-stack:
  added: []
  patterns:
    - "Fixed step->target-stage dict (_REVEAL_TOUR_TARGET_STAGE) beside the step->column dict; a test pins that the two partition the OnboardingStep Literal"
    - "Forward-only guarded UPDATE (advance to N only from N-1), the counter analogue of the IS NULL first-write-wins stamp"

key-files:
  created:
    - alembic/versions/20261015_194346_5448f030de58_phase_240_reveal_tour_stage.py
    - tests/test_migration_240_reveal_tour_stage.py
  modified:
    - app/services/train_scheduler.py
    - app/models/train_settings.py
    - app/schemas/train.py
    - app/repositories/train_repository.py
    - app/routers/train.py
    - scripts/reset_train_state.py
    - tests/routers/test_train.py
    - tests/repositories/test_train_repository.py
    - tests/scripts/test_reset_train_state.py

key-decisions:
  - "Kept POST /train/onboarding/{step} and the single stamp_onboarding_step entry point; reveal_tour_1..3 map to stages through a fixed dict, no router dispatch, no TypeGuard"
  - "Migration is one revision (add, CHECK, backfill 3 where the old timestamp was set, drop) with a literal 3 bound, frozen from the model constant"
  - "reveal_tour_stage is response-only: absent from TrainSettingsUpdate and upsert_settings values/set_ (T-240-01)"

patterns-established:
  - "Server-owned progress counters: response-only, advanced by a dedicated endpoint with a guarded N-1 -> N UPDATE, CHECK-bounded in the DB"

requirements-completed: [D-09, D-10, D-11, D-12]

coverage:
  - id: D1
    description: "reveal_tour_1, _2, _3 advance the stage 0 -> 1 -> 2 -> 3; out-of-order and replayed POSTs are no-ops and the stage never moves backwards"
    requirement: "D-09"
    verification:
      - kind: integration
        ref: "tests/routers/test_train.py#test_onboarding_reveal_tour_advances_in_order"
        status: pass
      - kind: integration
        ref: "tests/routers/test_train.py#test_onboarding_reveal_tour_out_of_order_is_noop"
        status: pass
      - kind: integration
        ref: "tests/routers/test_train.py#test_onboarding_reveal_tour_replay_never_moves_backwards"
        status: pass
      - kind: integration
        ref: "tests/repositories/test_train_repository.py#test_stamp_onboarding_step_reveal_tour_forward_only"
        status: pass
    human_judgment: false
  - id: D2
    description: "Migration backfills stage 3 where the old timestamp was set (else 0), drops the old column, CHECK rejects 4 and -1, downgrade restores the old column"
    requirement: "D-10"
    verification:
      - kind: integration
        ref: "tests/test_migration_240_reveal_tour_stage.py"
        status: pass
    human_judgment: false
  - id: D3
    description: "The retired walkthrough step name 422s with no write; settings responses expose reveal_tour_stage and not the old key; a PUT cannot change the stage"
    requirement: "D-11"
    verification:
      - kind: integration
        ref: "tests/routers/test_train.py#test_onboarding_retired_walkthrough_step_is_422"
        status: pass
      - kind: integration
        ref: "tests/routers/test_train.py#test_put_settings_cannot_smuggle_onboarding_seen_timestamp"
        status: pass
      - kind: integration
        ref: "tests/routers/test_train.py#test_get_settings_exposes_onboarding_state"
        status: pass
    human_judgment: false
  - id: D4
    description: "intro_seen_at / sr_explained_at keep first-write-wins semantics and mid-onboarding users start the split tour at stage 0; reset script resets the stage to 0"
    requirement: "D-12"
    verification:
      - kind: integration
        ref: "tests/routers/test_train.py#test_onboarding_each_step_writes_only_its_own_column"
        status: pass
      - kind: integration
        ref: "tests/scripts/test_reset_train_state.py#test_reset_clears_streak_snapshot_but_keeps_schedule"
        status: pass
      - kind: unit
        ref: "tests/repositories/test_train_repository.py#test_onboarding_step_dicts_partition_the_literal"
        status: pass
    human_judgment: false

duration: 10min
completed: 2026-10-15
status: complete
---

# Phase 240 Plan 01: Reveal Tour Stage (backend) Summary

**Forward-only `reveal_tour_stage` 0..3 counter replaces the Phase 222 walkthrough timestamp through migration `5448f030de58`, model, repository, schema, router and reset script, with the retired step name hard-cut to 422.**

## Performance

- **Duration:** ~10 min
- **Started:** 2026-10-15T19:38Z
- **Completed:** 2026-10-15T19:49Z
- **Tasks:** 2
- **Files modified:** 11 (2 created, 9 modified)

## Accomplishments

- Alembic migration **`5448f030de58`** (down_revision `778c806092fb`, now the single head, applied to the dev DB): adds `reveal_tour_stage` SmallInteger NOT NULL DEFAULT 0 with `ck_train_settings_reveal_tour_stage` (0..3), backfills 3 where the old timestamp was non-null, drops the old column. Downgrade restores the column and stamps an approximate `now()` for stage-3 rows. Plan 07's funnel note and the deploy reference this revision id.
- `stamp_onboarding_step` stays the single entry point: `intro`/`sr_explained` keep the guarded `IS NULL` timestamp stamp; `reveal_tour_N` runs `_advance_reveal_tour_stage`, a guarded `WHERE reveal_tour_stage = N-1` UPDATE, so replay, concurrent duplicate and out-of-order POSTs match zero rows.
- `OnboardingStep` is now `intro | sr_explained | reveal_tour_1 | reveal_tour_2 | reveal_tour_3`; the old name is gone (422, no shim).
- `TrainSettingsResponse.reveal_tour_stage: int` is returned by GET/PUT settings and every onboarding POST; `TrainSettingsUpdate` is untouched.
- `scripts/reset_train_state.py` resets the stage to 0.
- Tests: migration test (3 cases), repository forward-only + Literal-partition tests, four new router tests plus adapted 422/smuggle/exposes/defaults tests. A mutation check (guard weakened to `< target_stage`) failed the out-of-order router test and the repository forward-only test, confirming they bite.

## Task Commits

1. **Task 1: reveal_tour_stage end to end (tracer)** - `4de8e2c84` (feat)
2. **Task 2: migration, repository and reset-script coverage** - `5f8b987f6` (test)

**Plan metadata:** committed separately after this file (docs).

## Deviations from Plan

None - plan executed exactly as written. Note on ordering: Task 1 is a `type="tracer"` task whose router tests were adapted in the same commit as the implementation (per the plan text), so no separate RED commit exists; the Task 2 mutation check above is the proof the new tests fail against a broken guard. The plan is `type: execute`, so no TDD gate section applies.

**Total deviations:** 0.

## Verification

- `uv run alembic heads`: single head `5448f030de58`; `alembic current` on dev DB: `5448f030de58 (head)`.
- `uv run pytest -n auto -x`: 5472 passed, 19 skipped.
- `uv run ty check app/ tests/ scripts/`: clean. `ruff check` and `ruff format --check`: clean. `check_function_size.py app/ --fail-over-depth 4`: no breaches.
- `grep -rn "reveal_walkthrough" app/ scripts/`: no hits. `REVEAL_TOUR_STAGE_MAX` present in both the scheduler and the model; `"reveal_tour_1": 1` present in the repository; no new `getattr`.

## Known Stubs

None.

## Threat Flags

None. All changes fall under the plan's `<threat_model>` (T-240-01..04 mitigated by tests; T-240-05 accepted).

## Issues Encountered

None. Deploy note: the migration drops a column, so a stale PWA tab POSTing `reveal_walkthrough` gets a 422 until it reloads (D-11, accepted). The frontend still reads the old field until plan 03 lands; frontend and backend should ship in the same release.

## Self-Check: PASSED

- FOUND: alembic/versions/20261015_194346_5448f030de58_phase_240_reveal_tour_stage.py
- FOUND: tests/test_migration_240_reveal_tour_stage.py
- FOUND commits: 4de8e2c84, 5f8b987f6 (ancestors of HEAD)
