---
phase: 240-train-first-session-onboarding-load
plan: 02
subsystem: api
tags: [train, composition, onboarding, sqlalchemy]

requires:
  - phase: 240-train-first-session-onboarding-load
    provides: "plan 01 (same repository and test files; no functional dependency)"
provides:
  - "First-ever Train session opens on a sharp puzzle (answer-key type) and holds a several puzzle (soft or herring) at index 1 or 2"
  - "_order_first_ever_session composition stage between _assemble_session_items and _materialize_session_rows"
affects: [240-04, train-frontend]

actuals:
  tokens: 40000
  tasks: 2
  commits: 1
plan_head_before: 0f0b32358a576306d621b0333a2b0e72e08f4ae9
plan_head_after: 86cc15de3fae91b85effdb9b57a22823d0f16dc5

tech-stack:
  added: []
  patterns:
    - "Pure ordering helper + thin async stage + spy-backed wiring test (delegating monkeypatch recorder)"

key-files:
  created: []
  modified:
    - app/repositories/train_repository.py
    - tests/repositories/test_train_repository.py

key-decisions:
  - "Types are computed after assembly, only for a first-ever composition, with one PK-scoped query for the SR items' live blobs; herrings and sharp fillers need no query"
  - "Slot 0 uses pop-and-insert (keeps the shuffled order of the rest); the several puzzle uses a seeded swap into index 1 or 2"
  - "Seed f\"{user_id}:{today}:first-session\" is distinct from the D-09 seed"

patterns-established:
  - "First-ever gate = no drill_sessions row of any status, evaluated after _resolve_existing_session so a discarded untouched-and-resized first session no longer counts"

requirements-completed: [D-13, D-14, D-15]

coverage:
  - id: D13
    description: "Reorder applies to the first-ever session only; any earlier drill_sessions row (expired, completed) gets the plain D-09 shuffle; a resized first session is recomposed with the reorder"
    requirement: "D-13"
    verification:
      - kind: integration
        ref: "tests/repositories/test_train_repository.py#test_first_session_gate_blocks_an_expired_earlier_session"
        status: pass
      - kind: integration
        ref: "tests/repositories/test_train_repository.py#test_first_session_gate_blocks_an_earlier_completed_session"
        status: pass
      - kind: integration
        ref: "tests/repositories/test_train_repository.py#test_first_session_resized_untouched_session_is_recomposed_with_the_reorder"
        status: pass
      - kind: integration
        ref: "tests/repositories/test_train_repository.py#test_first_session_order_is_reproducible_for_the_same_user_and_day"
        status: pass
    human_judgment: false
  - id: D14
    description: "Sharp means the verdict's own answer_key_for type (live blob for SR items, sharp fillers sharp, herrings herring)"
    requirement: "D-14"
    verification:
      - kind: integration
        ref: "tests/repositories/test_train_repository.py#test_first_session_opens_on_sharp_and_several_in_slot_1_or_2"
        status: pass
      - kind: integration
        ref: "tests/repositories/test_train_repository.py#test_first_session_slot_0_is_the_sharp_filler_when_sr_items_are_all_soft"
        status: pass
    human_judgment: false
  - id: D15
    description: "A several puzzle sits at index 1 or 2 when the set holds one; degenerate sizes and sessions without sharp/several never raise or reorder needlessly"
    requirement: "D-15"
    verification:
      - kind: unit
        ref: "tests/repositories/test_train_repository.py#test_first_session_order_swaps_a_several_into_slot_1_or_2"
        status: pass
      - kind: unit
        ref: "tests/repositories/test_train_repository.py#test_first_session_order_two_puzzles_put_the_sharp_first"
        status: pass
      - kind: integration
        ref: "tests/repositories/test_train_repository.py#test_first_session_without_sharp_or_several_slots_keeps_the_shuffled_order"
        status: pass
    human_judgment: false

duration: 20min
completed: 2026-10-15
status: complete
---

# Phase 240 Plan 02: First-Ever Session Ordering Summary

**The first-ever Train session now opens on a sharp puzzle and carries a "several" puzzle at puzzle 2 or 3, decided after the D-09 shuffle and before materialization using the verdict's own `answer_key_for` type.**

## Accomplishments

- `_first_session_order` (pure, depth <= 2): moves the first sharp puzzle to slot 0 (pop and insert), then swaps the first several puzzle into a seeded choice of slots 1 or 2 when neither already holds one; slots clamp to the list length so sessions of 1 or 2 puzzles are safe.
- `_is_first_ever_session`: `EXISTS` on `drill_sessions` for the user, any status.
- `_composition_puzzle_types`: one `user_id`-scoped query for the SR items' live `missed_pv_lines`, then `answer_key_for(...).puzzle_type` per puzzle (missing blob classifies as soft, same as the verdict).
- `_order_first_ever_session` is called in `compose_and_materialize_session` right after `_assemble_session_items`, before the empty-session return and `_materialize_session_rows`. Seed suffix `first-session` keeps it independent from the D-09 draw.

## Task Commits

1. **Task 1 + Task 2 (combined)** - `86cc15de3` (feat)

## Mutation check (gate proof)

With the `_is_first_ever_session` check removed from `_order_first_ever_session`, `-k first_session` failed:
- `test_first_session_gate_blocks_an_expired_earlier_session`
- `test_first_session_gate_blocks_an_earlier_completed_session`

The check was restored (file byte-identical to the committed version), and all 18 `first_session` tests pass again.

## Positional tests fixed in Task 2

None. The full backend suite (`uv run pytest -n auto -x`: 5488 passed, 19 skipped) passed with no edits to tests/routers/test_train.py, tests/test_guest_auth.py or tests/test_imports_router.py; no existing test depended on a fresh user's first-session puzzle position.

## Deviations from Plan

- **Task commit granularity:** the Task 2 tests live in the same file and were written alongside the tracer, so Task 1 and Task 2 were committed together in one commit (`86cc15de3`). Task 2 changed no app/ file beyond Task 1 and needed no suite-wide fixes, so there is no separate Task 2 commit.
- **Reproducibility test:** the plan implied recomposing the same fresh state; recomposition after deleting the session row is not stable (padding already created `drill_items`, which changes the candidate order before the D-09 shuffle). The test instead runs `_order_first_ever_session` twice on one `_assemble_session_items` result, which isolates the new stage's determinism. Several first-session integration cases use sharp fillers (via `_install_sharp_fixture`) where a sharp puzzle must be present at every session size, since the SR pick of a specific sharp item depends on slot arithmetic.

## Verification

- `uv run pytest tests/repositories/test_train_repository.py -k first_session`: 18 passed.
- `uv run pytest -n auto -x`: 5488 passed, 19 skipped.
- `uv run ty check app/ tests/ scripts/`, `uv run ruff check .`, `uv run python scripts/check_function_size.py app/ --fail-over-depth 4`: clean.

## Known Stubs

None.

## Threat Flags

None. T-240-06 mitigated by the mutation-proven gate; T-240-07 mitigated by `GameFlaw.user_id == user_id` in the blob query.

## Self-Check: PASSED

- FOUND commit 86cc15de3 (ancestor of HEAD)
- FOUND `_order_first_ever_session(` definition and one call site in app/repositories/train_repository.py
