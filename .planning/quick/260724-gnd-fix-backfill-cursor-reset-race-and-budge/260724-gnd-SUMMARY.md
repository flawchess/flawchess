---
phase: quick-260724-gnd
plan: 01
subsystem: api
tags: [import-pipeline, backfill, chess.com, lichess, sqlalchemy, pytest]

requires:
  - phase: 186
    provides: TC/game-cap import filters (forward + backward pass, per-platform backfill cursors)
provides:
  - Shared _import_scope_expanded (repository-owned) consumed by both the PATCH endpoint and run_import
  - run_import end-of-run cursor reset when a mid-run PATCH expanded scope (UAT-186-RACE)
  - Anchor-aware _admit_backward_game admitting post-anchor games uncapped (UAT-186-BUDGET)
affects: [import-service, users-router, user-import-settings-repository]

tech-stack:
  added: []
  patterns:
    - "Shared predicate functions live in the repository module, not the router, when both a router and a background service need the same scope-comparison logic"
    - "Post-condition re-check pattern: reload state after a long-running background pass and re-apply a side effect if a concurrent mutation invalidated the pass's job-start snapshot"

key-files:
  created: []
  modified:
    - app/repositories/user_import_settings_repository.py
    - app/routers/users.py
    - app/services/import_service.py
    - tests/test_import_service.py

key-decisions:
  - "_import_scope_expanded moved verbatim into user_import_settings_repository.py (near ImportSettingsRow) rather than duplicated, per the plan's must-haves truth (exactly ONE implementation)"
  - "_reset_cursors_if_scope_expanded_mid_run uses get_settings (read-only), not get_or_create_settings, for the end-of-run reload -- a settings row must already exist once a job has run, and create-on-touch semantics don't belong in a background re-check"
  - "Test fixture fix: _make_normalized_game's default played_at moved from 2024-01-01 to 2015-06-15 (pre-anchor) since the new anchor-aware budget check made every pre-existing backward-pass test's default post-anchor, which silently defeated cap assertions and hung the lichess cursor test's while loop"
  - "Autouse test fixture _default_import_settings_noop_backward extended to also default-mock get_settings (not just get_or_create_settings) so the new end-of-run reload doesn't fall through to a real query against the generic mocked session and read a spuriously truthy MagicMock row"

requirements-completed: [UAT-186-RACE, UAT-186-BUDGET]

coverage:
  - id: D1
    description: "run_import re-checks scope expansion after the backward pass's own final cursor flush and resets cursors again if a mid-run PATCH expanded scope"
    requirement: "UAT-186-RACE"
    verification:
      - kind: unit
        ref: "tests/test_import_service.py::TestResetCursorsIfScopeExpandedMidRun (5 tests: TC-on, cap-raise, no-op, narrowing, reload-None)"
        status: pass
      - kind: integration
        ref: "tests/test_import_service.py::TestRunImportEndOfRunScopeReset (2 tests: mid-run widening resets, no mid-run change is a no-op)"
        status: pass
    human_judgment: false
  - id: D2
    description: "_admit_backward_game admits post-anchor games (played_at >= users.created_at) uncapped, mirroring the forward pass's uncapped post-anchor semantics"
    requirement: "UAT-186-BUDGET"
    verification:
      - kind: unit
        ref: "tests/test_import_service.py::TestAdmitBackwardGame (post-anchor at-cap admitted uncapped, post-anchor==anchor uncapped, pre-anchor under-cap still counts, pre-anchor at-cap still rejected)"
        status: pass
    human_judgment: false
  - id: D3
    description: "_import_scope_expanded has exactly ONE implementation, shared by the PATCH endpoint and run_import"
    verification:
      - kind: unit
        ref: "tests/test_users_router.py::TestPatchImportSettingsCursorReset (pre-existing, unaffected by the move — proves the shared function still drives the PATCH path correctly)"
        status: pass
    human_judgment: false

duration: 32min
completed: 2026-07-24
status: complete
---

# Quick 260724-gnd: Fix backfill cursor-reset race and post-anchor budget accounting Summary

**Fixed a cursor-reset race where a mid-run import-settings PATCH's cursor reset got clobbered by the running job's own cursor writes, plus made the backward-pass backlog budget uncapped for post-account-creation games (mirroring the forward pass), consolidating the scope-expansion predicate into one shared implementation.**

## Performance

- **Duration:** ~32 min
- **Started:** 2026-07-24T12:02:00+02:00 (approx, pre-dispatch)
- **Completed:** 2026-07-24T12:34:22+02:00
- **Tasks:** 2 (source fix + regression tests)
- **Files modified:** 4 (`import_service.py`, `users.py`, `user_import_settings_repository.py`, `test_import_service.py`)

## Accomplishments

- **Shared `_import_scope_expanded`**: moved from `app/routers/users.py` into `app/repositories/user_import_settings_repository.py` (next to `ImportSettingsRow`). `users.py` now imports it instead of redefining it; `import_service.py` calls it via the already-imported `user_import_settings_repository` module. Exactly one implementation, per the plan's must-have truth.
- **RACE fix (UAT-186-RACE)**: `run_import` now reloads the current settings row (read-only, via `get_settings`) after the backward pass's own final cursor flush and — if it expanded scope vs. the job-start snapshot — resets the backfill cursors again. This reset is the last write in the job, so it always wins over the job's own incremental cursor persistence, closing the window where a concurrent scope-expanding PATCH's reset got silently clobbered.
- **BUDGET fix (UAT-186-BUDGET)**: `_admit_backward_game` gained an `anchor: datetime` parameter (threaded from `_run_backward_pass`'s `created_at` through both `_run_chesscom_backward_pass` and `_run_lichess_backward_pass`). A game with `played_at >= anchor` is now admitted without incrementing `live_counts`, matching the forward pass's uncapped post-anchor semantics — so a TC enabled after the account's first sync gets its post-creation games backfilled uncapped via the backward walk instead of them eating the pre-anchor backlog budget.
- **Regression tests**: extended `TestAdmitBackwardGame` with 4 new cases (post-anchor at-cap admitted uncapped, `played_at == anchor` counts as post-anchor, pre-anchor under-cap still counts, pre-anchor at-cap still rejected); added `TestResetCursorsIfScopeExpandedMidRun` (unit, 5 cases covering the `_import_scope_expanded` truth table through the new helper) and `TestRunImportEndOfRunScopeReset` (integration, 2 cases wiring the fix through the real `run_import`).
- **Test-fixture bug fix** (discovered while running the new tests): the pre-existing `_make_normalized_game`'s default `played_at` (2024-01-01) was *after* the tests' fixed account-creation anchor (`_TEST_USER_CREATED_AT`, 2020-01-01). Once the anchor-aware budget bypass shipped, every pre-existing `TestBackwardPass` test's default game became "post-anchor," silently defeating their cap assertions and hanging the lichess-cursor test's `while not should_stop()` loop forever (live_counts never advanced). Fixed by moving the default to 2015-06-15 (pre-anchor) and moving the one test with an explicit `played_at` override to a pre-anchor `base_ms`.

## Task Commits

1. **Task 1: Fix both bugs — shared scope predicate + end-of-run reset + anchor-aware budget** - `21580838` (fix)
2. **Task 2: Regression tests for both fixes** - `10e341c1` (test)

**Plan metadata:** commit pending (this SUMMARY + STATE.md, made by the orchestrator per the docs-commit step)

## Files Created/Modified

- `app/repositories/user_import_settings_repository.py` - Houses the shared `_import_scope_expanded` predicate (moved from `users.py`); exported via `__all__`.
- `app/routers/users.py` - Imports `_import_scope_expanded` instead of defining it; dropped the now-unused `ImportSettingsRow` import.
- `app/services/import_service.py` - New `_reset_cursors_if_scope_expanded_mid_run` helper called at the end of `run_import`; `_admit_backward_game` (+ both backward-pass platform functions + `_run_backward_pass`'s dispatch calls) thread an `anchor: datetime` parameter.
- `tests/test_import_service.py` - Extended `TestAdmitBackwardGame`; new `TestResetCursorsIfScopeExpandedMidRun` and `TestRunImportEndOfRunScopeReset` classes; fixed `_make_normalized_game`'s default `played_at` and one explicit override; extended the autouse settings-mocking fixture to also default `get_settings`; updated `TestRunImportSessionPerBatch.test_one_session_per_batch`'s expected session count (7 → 8, for the new mandatory end-of-run reload session).

## Decisions Made

- `_import_scope_expanded` moved verbatim (not reimplemented) to guarantee byte-identical PATCH-endpoint behavior — proven by the pre-existing `TestPatchImportSettingsCursorReset` real-DB tests passing unchanged.
- The end-of-run reload uses `get_settings` (returns `None` if missing) rather than `get_or_create_settings` — a background re-check has no business create-on-touch semantics; a missing row is treated as a no-op.
- Extended (rather than duplicated) the existing autouse settings-mocking fixture, keeping the "tests exercising this feature patch it themselves" convention consistent for both `get_or_create_settings` and `get_settings`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Pre-existing backward-pass test fixtures broke (and one hung) once the anchor-aware budget fix shipped**
- **Found during:** Task 2, initial full-suite run after adding the anchor param
- **Issue:** `_make_normalized_game`'s default `played_at` (2024-01-01) sat *after* the tests' fixed anchor `_TEST_USER_CREATED_AT` (2020-01-01). Every backward-pass test relying on the default suddenly classified its games as "post-anchor" (uncapped), defeating `TestBackwardPass`'s cap assertions and hanging `test_first_sync_backlog_bounded_not_full_history`'s `while not should_stop()` loop forever (its explicit `played_at` override, `base_ms = 1_700_000_000_000` ≈ 2023-11-14, was also post-anchor).
- **Fix:** Moved the default `played_at` to 2015-06-15 (pre-anchor) and the explicit `base_ms` override to `1_262_304_000_000` (2010-01-01), both well before the anchor. No test assertions reference `played_at` values directly, so this was a safe global change (verified via grep before applying).
- **Files modified:** `tests/test_import_service.py`
- **Verification:** Full `tests/test_import_service.py` suite passes (96/96, no hangs).
- **Committed in:** `10e341c1` (Task 2 commit)

**2. [Rule 1 - Bug] `TestRunImportSessionPerBatch.test_one_session_per_batch` session-count mismatch caused by an un-mocked `get_settings` reload**
- **Found during:** Task 2, full-suite run
- **Issue:** The new end-of-run reload calls `user_import_settings_repository.get_settings`, which the existing autouse fixture only defaulted for `get_or_create_settings`. Left unmocked, `get_settings` fell through to the real function against the test's generic mocked session, whose unconfigured `scalar_one_or_none()` returns a truthy `MagicMock`-backed row. Compared against the real all-`False` job-start snapshot, `_import_scope_expanded` read every field as "just turned on" and fired a spurious `reset_backfill_cursors` call — 2 extra `async_session_maker()` opens (7 → 9) in a test asserting an exact session count.
- **Fix:** Extended the autouse `_default_import_settings_noop_backward` fixture to also default-mock `get_settings` to the same no-op settings row, keeping the reload a true no-op unless a test explicitly overrides it. Updated the affected test's expected count (7 → 8, for the new mandatory reload session that always opens regardless of its return value).
- **Files modified:** `tests/test_import_service.py`
- **Verification:** `TestRunImportSessionPerBatch::test_one_session_per_batch` passes; full suite green.
- **Committed in:** `10e341c1` (Task 2 commit)

---

**Total deviations:** 2 auto-fixed (both Rule 1 — bugs surfaced by the current task's own change, confined to the touched test file)
**Impact on plan:** Both fixes were necessary to make the new regression tests reliable and to keep pre-existing tests green; no scope creep beyond the test file the plan already listed in `files_modified`.

## Mutation-Check Proof

Per `feedback_mutation_test_gap_closures` (never accept symbol-presence as proof):

- **BUDGET fix**: temporarily removed the post-anchor `if played_at is not None and played_at >= anchor: return True` branch from `_admit_backward_game`. `test_post_anchor_game_admitted_without_counting_even_at_cap` and `test_post_anchor_exactly_at_anchor_is_uncapped` both failed (`assert False`). Restored the branch; both pass again.
- **RACE fix**: temporarily commented out the `await _reset_cursors_if_scope_expanded_mid_run(job.user_id, settings)` call in `run_import`. `TestRunImportEndOfRunScopeReset::test_mid_run_patch_widening_scope_resets_cursors_after_backward_pass` failed ("Expected mock to have been awaited once. Awaited 0 times."), while the no-op baseline test correctly still passed. Restored the call; both pass again.

`git diff` confirmed clean (no stray edits) after each restore.

## Issues Encountered

None beyond the two auto-fixed test-fixture issues documented above (both surfaced and resolved during Task 2's own verification loop, before final commit).

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Both UAT-186 bugs (cursor-reset race, post-anchor budget mischarging) are fixed and regression-tested; no follow-up work identified.
- Full targeted verification green: `uv run ty check app/ tests/` (zero errors), `uv run ruff format --check` + `uv run ruff check` clean, full `tests/test_import_service.py` (96/96) and `tests/test_users_router.py` (22/22) / `tests/test_imports_router.py` (18/18) all green.
- Not run as part of this quick task (per constraints): the full backend suite (`uv run pytest -n auto`) and frontend lint/tests — deferred to the later pre-merge gate.

---
*Phase: quick-260724-gnd*
*Completed: 2026-07-24*

## Self-Check: PASSED

All claimed files found on disk; both commit hashes (`21580838`, `10e341c1`) verified present in `git log --oneline --all`.
