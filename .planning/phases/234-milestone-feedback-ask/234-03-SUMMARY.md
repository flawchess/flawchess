---
phase: 234-milestone-feedback-ask
plan: 03
subsystem: feedback
tags: [feedback-ask, feedback-source, modal-host, hilda, sentry]
requires:
  - "feedback.source column and ck_feedback_source (plan 01, migration f4b9d2c7e815)"
  - "FeedbackModal source/placeholder props, FeedbackAskBubble (plan 02)"
provides:
  - "FeedbackCreate.source (FeedbackSource Literal) persisted by create_feedback"
  - "Sentry feedback_source tag on the feedback signal"
  - "App-level FeedbackAskModalHost and the openFeedbackAskModal store"
affects:
  - "plan 04 (Train landing and Bots roster reuse the bubble; Sure now opens the modal there too)"
tech-stack:
  added: []
  patterns:
    - "Module store + useSyncExternalStore for a cross-tree modal flag (playActive.ts pattern)"
key-files:
  created:
    - frontend/src/components/feedback/FeedbackAskModalHost.tsx
  modified:
    - app/schemas/feedback.py
    - app/repositories/feedback_repository.py
    - app/services/feedback_service.py
    - tests/test_feedback_router.py
    - tests/test_feedback_repository.py
    - frontend/src/lib/feedbackAsk.ts
    - frontend/src/components/feedback/FeedbackAskBubble.tsx
    - frontend/src/App.tsx
    - frontend/src/components/feedback/__tests__/FeedbackAskBubble.test.tsx
key-decisions:
  - "Sure opens the modal before POSTing done so the dialog is up before the cache patch unmounts the bubble"
  - "The host fires no Umami event: the submission is a DB row carrying its source"
requirements-completed: [FBASK-01, FBASK-05, FBASK-06]
duration: ~20 min
completed: 2026-10-06
status: complete
actuals:
  tokens: 9000
  tasks: 2
  commits: 3
plan_head_before: 55e0068b5181b647350918878590246e5306a64e
plan_head_after: 36b16b0d579e09e11376512497699f5cf5589105
---

# Phase 234 Plan 03: Sure! opens an app-level feedback modal, feedback source persisted Summary

POST /api/feedback now stores `feedback.source` (Pydantic Literal over the DB CHECK, default `floating_button`), and Hilda's "Sure!" opens an app-level `FeedbackAskModalHost` (placeholder "What's one thing you'd change or add?") that survives the bubble unmounting and submits with `source: 'milestone_ask'`.

## Accomplishments

- **Tracer (Task 1):** `FeedbackSource = Literal["floating_button", "milestone_ask"]` on `FeedbackCreate.source` (default keeps a stale SPA bundle working), `create_feedback` writes `source=data.source`, and `push_sentry_signal` adds a distinct `feedback_source` tag while the existing `source="feedback"` tag is untouched. `TestFeedbackSource` covers default, `milestone_ask`, and `bogus` -> 422 with zero rows written; repository tests cover the round-trip and the `ck_feedback_source` IntegrityError backstop. Each router test registers its own user (own rate-limit bucket).
- **Task 2 (TDD):** `feedbackAsk.ts` gained `FEEDBACK_ASK_PLACEHOLDER` and a module store (`openFeedbackAskModal`, `closeFeedbackAskModal`, `useFeedbackAskModalOpen`). `FeedbackAskModalHost` renders `FeedbackModal source="milestone_ask"`, mounted once in each `ProtectedLayout` return branch (outside the analysis branch's `hidden md:block` wrapper, not behind `!playActive`). The Sure handler is now `trackFeature` -> `openFeedbackAskModal()` -> `mutate('done')`.

## Mutation proof (tracer)

Removing `source=data.source` from `create_feedback` turned `TestFeedbackSource::test_milestone_ask_source_is_stored` and `TestFeedbackRepository::test_create_feedback_stores_milestone_ask_source` red (2 failed, 22 passed; the row stored the ORM default). Restored; 24 passed.

## TDD Gate Compliance

- RED (`da5c657b5`): 4 new tests fail with `Unable to find an element by: [data-testid="feedback-text"]` / `"feedback-modal"` (the target assertions on the modal opening), the 5 pre-existing tests pass. To avoid an import-failure RED, the commit includes no-op scaffolds (`openFeedbackAskModal`/`closeFeedbackAskModal` no-ops, `useFeedbackAskModalOpen` returning false, host returning an empty fragment). Semantic assessment: the failures are the planned behavior gap, not setup faults.
- GREEN (`36b16b0d5`): real store, host, handler and App mounts; 20/20 tests in the two feedback test files pass, full suite 5164/5164.
- No refactor commit.

## Task Commits

| Task | Commit | Description |
| ---- | ------ | ----------- |
| 1 (tracer) | baa3bb899 | Source persisted end to end (schema, repository, Sentry tag, tests) |
| 2 RED | da5c657b5 | Failing tests for the Sure! modal host |
| 2 GREEN | 36b16b0d5 | Store, host, handler change, App mounts |

## Deviations from Plan

None - plan executed exactly as written. (The RED commit carries no-op scaffolds so the tests fail on assertions rather than on a missing module; they are replaced in GREEN.)

## Verification

- `uv run pytest tests/test_feedback_router.py tests/test_feedback_repository.py tests/test_feedback_ask.py`: 40 passed.
- `ruff format`, `ruff check`, `ty check app/ tests/ scripts/`, `check_function_size.py app/ --fail-over-depth 4`: clean.
- Frontend: `npm run lint`, `npm run build`, `npm run knip` exit 0; `npm test -- --run` 5164 passed.
- Acceptance greps: `FeedbackSource = Literal[...]`, `source=data.source`, both `set_tag` lines, `class TestFeedbackSource`, the three store exports, `source="milestone_ask"` in the host, `<FeedbackAskModalHost />` count = 2, no `playActive && <FeedbackAskModalHost`: all pass.

## Known Stubs

None.

## Threat Flags

None. T-234-15 mitigated: Pydantic Literal rejects unknown sources (422, no row) and `ck_feedback_source` backs it in the DB; the `feedback_source` tag is therefore one of two literals.

## Self-Check: PASSED

Created/modified files exist and commits baa3bb899, da5c657b5, 36b16b0d5 are ancestors of HEAD.
