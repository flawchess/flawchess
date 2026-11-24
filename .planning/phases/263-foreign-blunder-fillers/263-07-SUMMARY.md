---
phase: 263-foreign-blunder-fillers
plan: 07
subsystem: api
tags: [train, composition, eligibility, tests]

requires:
  - phase: 263-foreign-blunder-fillers
    provides: "263-01/03 foreign stage, real_foreign_draw fixture, seed helpers; 263-05/06 boards, activity, reveal"
provides:
  - "Composition without the lichess stage: the foreign stage is the only residual-shortfall filler (D-02)"
  - "No source 2 row is composed any more; solved source 2 rows are untouched (D-03)"
  - "Eligibility stamp after _materialize_session_rows (has_material=True), static-set term removed"
  - "tests/conftest.py foreign_filler_pool fixture (committed stranger pool for users without games)"
affects: [263-08, 263-09, 263-10]

actuals:
  tokens: 10000
  tasks: 2
  commits: 2

tech-stack:
  added: []
  patterns:
    - "Tests that need a filled session for a user without games request foreign_filler_pool (router level, committed, cleaned in finally) or seed strangers through db_session with _seed_foreign_blunders (repository level, rolled back, solver pinned to 2600)"

key-files:
  created: []
  modified:
    - app/repositories/train_repository.py
    - tests/conftest.py
    - tests/repositories/test_train_repository.py
    - tests/repositories/test_train_foreign.py
    - tests/routers/test_train.py
    - tests/routers/test_train_two_mode_streak.py
    - tests/routers/test_train_settings_two_modes.py
    - tests/test_guest_auth.py

key-decisions:
  - "Eligibility is stamped after a session row is written, not by a pre-composition probe (a TABLESAMPLE-based EXISTS would stamp nondeterministically); stamp-if-NULL makes the second call a no-op"
  - "The five flagged-session tests and the two warm-up router tests were kept and moved onto the foreign stage instead of deleted: a zero-SR session still composes, so their subject (is_warmup, guest warm-up streak) is alive until 263-09 retires the flag"

requirements-completed: [D-02, D-03]

duration: 16min
completed: 2026-11-23
status: complete
plan_head_before: 6a277cfcff272fa0d361233321e8f230e39af120
plan_head_after: 5981e591af2405d9a10ca74f2653343df82dafcd
commits: 2
---

# Phase 263 Plan 07: Foreign stage is the only filler Summary

**Composition no longer writes a lichess filler row: the foreign stage alone fills every residual shortfall, and a session with no own material stamps its streak floor once the session row exists.**

## Accomplishments

- Task 1 `096371ea2` (tests only, green on the old code): `foreign_filler_pool` fixture (one committed non-guest stranger, `FOREIGN_FILLER_POOL_GAMES = 8` qualifying blunders at raw 1500, deleted in `finally`); the streak and settings router suites request it instead of the lichess puzzle tuple; `test_train_repository.py` got `_seed_foreign_blunders` (pins `_USER_ID` to level 2600, seeds strangers at raw 2700 through the rolled-back session) and the composition, identity-column, answer-key, graded-parity and eligibility tests moved onto the foreign stage; `test_train.py` guest tests use the pool, and `test_solve_foreign_blunder_touches_no_drill_item` replaces the sharp-filler solve test.
- Task 2 `5981e591a`: deleted `_backfill_sharp_fillers` and its call, `_ReconstructedPuzzle.sharp_puzzle_id` (and the kwarg in `_materialize_session_rows`), the static-set term of the pre-composition stamp, and the sharp import block down to `SHARP_SET_BY_ID` (resume, classification and reveal still read it; 263-08 removes it). Added the post-materialize `_stamp_pool_eligibility(..., has_material=True)` with a fix-site comment. Docstrings that described the lichess stage were rewritten.

## Mutation check (reverted, tests restored green)

| Mutation | Result |
| --- | --- |
| post-materialize stamp `has_material=True` -> `False` | `TestStampPoolEligibility::test_foreign_only_session_stamps_pool_eligible_since` fails |

The first attempt did not fail: blunder check at its default size 6 already counts as material and stamps before composition, masking the new stamp. The test now switches blunder check off (`_set_blunder_check_size`), and the mutation fails it as expected. `test_empty_foreign_pool_composes_nothing_and_stamps_nothing` (new) covers the empty-pool case: no session, floor stays NULL.

## Test accounting

- Moved onto the foreign stage in `test_train_repository.py`: 16 tests (zero-SR and three-SR composition renamed to `test_zero_sr_material_composes_herrings_and_foreign_blunders` and `test_three_sr_candidates_compose_sr_herrings_and_foreign_blunders`; identity-column; answer-key; graded-parity; first-session resized; frozen-order; `test_foreign_only_session_stamps_pool_eligible_since` (renamed); the watermark-not-overwritten test; `test_sr_shortfall_backfills_with_herrings`, `test_blunder_heavy_game_contributes_exactly_one_pool_pick`, `test_cap_shortened_sr_side_fills_via_herring_backfill`; four is_warmup tests). The last three plus the is_warmup four were not in the plan list but asserted `SHARP_FILLER` counts or depended on the sharp fixture filling the session.
- Moved or rewritten in `test_train.py`: 4 (`test_session_response_exposes_is_warmup`, `test_guest_composes_session_200`, `test_guest_zero_game_warmup_end_to_end` use `foreign_filler_pool`; the sharp-filler solve test is rewritten as the foreign one). `tests/test_guest_auth.py::test_train_state_preserved_after_promotion` also uses the pool (found by the full suite).
- Suites relying on the pool fixture: `test_train_two_mode_streak.py` and `test_train_settings_two_modes.py` (11 tests).
- New: 1 (`test_empty_foreign_pool_composes_nothing_and_stamps_nothing`).
- Deleted: 2 (`test_no_sharp_puzzle_id_collides_within_one_session`, `test_first_session_slot_0_is_the_sharp_filler_when_sr_items_are_all_soft`; D-16 is covered by 263-03).
- Left for 263-08: `test_reveal_sharp_filler_reports_sharp_filler_source`, the `record_solve` sharp-filler tests, `_install_sharp_fixture` / `_TEST_SHARP_PUZZLES` in `test_train.py` (still used) and `test_train_repository.py` (now unused, definition only), and the `_empty_lichess_sharp_set` / `_default_empty_sharp_set` autouse patches.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Tests outside the plan's list depended on the lichess filler**
- **Found during:** Task 2 (full suite)
- **Issue:** three `test_train_repository.py` tests asserting `SHARP_FILLER == 7` and four is_warmup tests used the sharp fixture; `tests/test_guest_auth.py::test_train_state_preserved_after_promotion` composed from the real CSV and had no source of puzzles once the stage was gone.
- **Fix:** moved them onto the foreign stage (`_seed_foreign_blunders` / `foreign_filler_pool`); the guest-auth test got `@pytest.mark.usefixtures("foreign_filler_pool")`. The test_train_repository edits are in Task 1; the guest-auth edit and the two `_ReconstructedPuzzle(sharp_puzzle_id=None)` call sites in tests are in Task 2.
- **Files modified:** tests/test_guest_auth.py, tests/repositories/test_train_repository.py, tests/repositories/test_train_foreign.py
- **Commit:** 5981e591a

**2. [Rule 1 - Judgment] Kept instead of deleting five flagged-session tests and two router warm-up tests**
- The plan says to delete them (263-09 retires the flag). Their subject still composes via the foreign stage, so they were converted; 263-09 will retire or replace them with the `own_puzzle_count` equivalents.

## Known Stubs

None.

## Verification observed

- Task 1 suites on unchanged app code: 377 passed.
- After the last edit: `uv run pytest -n auto -q` full backend suite: 7098 passed, 9 skipped (was 7099 passed: 2 deleted, 1 added).
- Serial run of the rewritten files plus `test_train_foreign` (both files) and `test_guest_auth.py`: 411 passed.
- `ruff check .` clean, `ruff format --check app tests` clean, `ty check app/ tests/ scripts/` clean, `check_function_size.py app/ --fail-over-depth 4`: 1704 functions, no breaches.
- Acceptance greps: `foreign_filler_pool` present in conftest, `has_material=True` count 1, no `_backfill_sharp_fillers` / `sharp_filler_available` / `pick_sharp_fillers` in `app/repositories`, no `_sharp_fixture` / `_SHARP_PUZZLES` in the two streak/settings suites.

## Self-Check: PASSED

- 096371ea2 and 5981e591a are ancestors of HEAD; the files listed above exist.
