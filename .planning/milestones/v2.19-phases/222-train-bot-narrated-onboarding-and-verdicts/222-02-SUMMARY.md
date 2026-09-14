---
phase: 222-train-bot-narrated-onboarding-and-verdicts
plan: 02
subsystem: api (train)
tags: [fastapi, sqlalchemy, alembic, pydantic, train, onboarding]

requires:
  - phase: 222-01
    provides: "useTrainOnboarding hook + trainApi.stampOnboarding client call targeting POST /train/onboarding/{step}; TrainSettingsResponse/SolvedResult TS type extensions expecting this exact server contract"
provides:
  - "train_settings.intro_seen_at / .reveal_walkthrough_seen_at / .sr_explained_at (nullable DateTime(timezone=True), no backfill)"
  - "POST /train/onboarding/{step} — guest-gated, Literal-validated, caller-scoped, first-write-wins, returns TrainSettingsResponse"
  - "SolvedResult extended with source/item_status/due_date (D-17) on the resume path"
  - "scripts/reset_train_state.py clears the three onboarding columns for repeatable dev UAT"
affects: [222-04, 222-06]

actuals:
  tokens: 12271
  tasks: 4
  commits: 3

commits: 3
plan_head_before: f56136839957e0fe5d02ba62117a873af0a1c24d

tech-stack:
  added: []
  patterns:
    - "Response-only server-owned columns (never on the *Update write schema) mirror the existing reminder_last_sent_on split: exposed on TrainSettingsResponse, absent from TrainSettingsUpdate, and — new here — still RETURNING'd/reflected accurately inside upsert_settings even though upsert_settings never writes them, so a PUT response never misreports a value it did not touch."
    - "Step->column dispatch via a fixed dict (_ONBOARDING_COLUMNS: dict[OnboardingStep, Any]) keyed by a Literal, never getattr on a request-supplied name — same shape as the existing IDOR-safe conventions in this router."
    - "Set-based LEFT JOIN (drill_solves -> drill_items on (user_id, game_id, ply)) to enrich a resumed session's per-row outcomes, rather than N per-row lookups — a non-SR source or an orphaned game link both degrade to NULL by construction (no matching row), never a branch."

key-files:
  created:
    - alembic/versions/20260913_144712_7d6bb75aae54_phase_222_train_onboarding_seen.py
  modified:
    - app/models/train_settings.py
    - app/repositories/train_repository.py
    - app/schemas/train.py
    - app/routers/train.py
    - scripts/reset_train_state.py
    - tests/repositories/test_train_repository.py
    - tests/routers/test_train.py
    - tests/scripts/test_reset_train_state.py

key-decisions:
  - "T-222-02-00 checkpoint (gate=blocking-human, pre-resolved by the orchestrator): user response verbatim = 'Confirm as locked' (option confirm-as-locked). Final three column names, exactly as D-11 specified: intro_seen_at, reveal_walkthrough_seen_at, sr_explained_at — all nullable DateTime(timezone=True) on train_settings, no backfill (D-13), entering TrainSettingsResponse only. No renaming, no file-propagation needed."
  - "upsert_settings RETURNING/reflects the three onboarding columns' true persisted values (mirrors the reminder_last_sent_on precedent in the same function) rather than leaving them at an unset default — see Deviations."
  - "OnboardingStep (the Literal step-name type) lives on app/schemas/train.py and is imported by the repository, matching an established precedent elsewhere in this codebase (game_repository/endgame_repository/etc. importing Literal types from app.schemas) — the repository-level 'must not import from app.schemas' note on ComposedSolvedResult is scoped narrowly to that dataclass's score field, not a blanket rule."

requirements-completed: [TRAINBOT-04, TRAINBOT-05]

coverage:
  - id: D1
    description: "Three nullable DateTime(timezone=True) columns land on train_settings with exactly the D-11 names, a clean upgrade/downgrade/upgrade round-trip, and no backfill — every pre-existing row reads NULL on all three."
    requirement: TRAINBOT-05
    verification:
      - kind: other
        ref: "uv run alembic upgrade head && uv run alembic downgrade -1 && uv run alembic upgrade head (clean, no UndefinedColumn/DuplicateColumn)"
        status: pass
      - kind: unit
        ref: "tests/repositories/test_train_repository.py#test_get_or_create_settings_onboarding_seen_defaults_null"
        status: pass
      - kind: unit
        ref: "tests/repositories/test_train_repository.py#test_get_settings_round_trips_onboarding_seen_timestamps"
        status: pass
    human_judgment: false
  - id: D2
    description: "POST /train/onboarding/{step} is guest-gated (403), Literal-validated (422 on an unknown step, no DB write), caller-scoped (IDOR-safe), first-write-wins on replay, and returns the full TrainSettingsResponse."
    requirement: TRAINBOT-05
    verification:
      - kind: integration
        ref: "tests/routers/test_train.py (8 onboarding tests: 403 guest, 422 unknown step, single-column stamp, replay-unchanged, all-three-independent, GET exposes all three, PUT-cannot-smuggle, IDOR-scoped)"
        status: pass
    human_judgment: false
  - id: D3
    description: "PUT /train/settings can never write any of the three onboarding-seen timestamps — the write schema (TrainSettingsUpdate) does not declare them, and upsert_settings' UPSERT never targets those columns."
    requirement: TRAINBOT-05
    verification:
      - kind: integration
        ref: "tests/routers/test_train.py#test_put_settings_cannot_smuggle_onboarding_seen_timestamp"
        status: pass
      - kind: unit
        ref: "tests/repositories/test_train_repository.py#test_upsert_settings_leaves_onboarding_seen_unchanged"
        status: pass
    human_judgment: false
  - id: D4
    description: "scripts/reset_train_state.py clears all three onboarding-seen columns in its default (non --reset-settings) path, so a dev account can replay every stepper without bin/reset_db.sh."
    verification:
      - kind: unit
        ref: "tests/scripts/test_reset_train_state.py#test_reset_clears_streak_snapshot_but_keeps_schedule (extended)"
        status: pass
    human_judgment: false
  - id: D5
    description: "SolvedResult (TrainSessionResponse.solved_results, the resume/reload/handoff path) carries source, item_status and due_date with no new answer-key exposure; a non-SR source and an orphaned sr_item (deleted source game) both degrade to NULL item_status/due_date rather than erroring."
    requirement: TRAINBOT-04
    verification:
      - kind: unit
        ref: "tests/repositories/test_train_repository.py#test_resume_solved_results_include_source_item_status_due_date"
        status: pass
      - kind: unit
        ref: "tests/repositories/test_train_repository.py#test_resume_solved_results_degrades_null_for_orphaned_drill_item"
        status: pass
      - kind: integration
        ref: "tests/routers/test_train.py#test_resume_solved_results_carry_source_item_status_due_date_no_answer_key"
        status: pass
    human_judgment: false

duration: 62min
completed: 2026-09-13
status: complete
---

# Phase 222 Plan 2: Train Onboarding-Seen Columns, Stamp Endpoint, SolvedResult Widening Summary

**Three nullable `train_settings` timestamps stamped by a new first-write-wins `POST /train/onboarding/{step}`, plus a set-based LEFT JOIN widening `SolvedResult` with `source`/`item_status`/`due_date` on the resume path — no new npm/pip package, no backfill.**

## Performance

- **Duration:** 62 min (approx.)
- **Started:** 2026-09-13T16:20:00Z (approx.)
- **Completed:** 2026-09-13T17:06:14Z
- **Tasks:** 4 (T-222-02-00 checkpoint pre-resolved, T-222-02-01, T-222-02-02, T-222-02-03)
- **Files modified:** 9 (1 created, 8 modified)

## Accomplishments

- Alembic revision `7d6bb75aae54` (`down_revision = b7d4f5a60002`) adds `intro_seen_at`, `reveal_walkthrough_seen_at`, `sr_explained_at` — three nullable `DateTime(timezone=True)` columns on `train_settings`, no backfill; upgrade/downgrade/upgrade round-trips cleanly.
- `app/models/train_settings.py` carries the matching ORM columns with a rationale comment stating the D-12 Response-only access pattern.
- `app/repositories/train_repository.py`: `TrainSettingsRow` gains the three fields across **all four** construction sites (`get_settings`, `get_or_create_settings`, `upsert_settings`, and a fifth touch point discovered during implementation — `get_progress`'s pool-eligibility re-stamp branch, not named in the plan's four-touch-point list). New `stamp_onboarding_step()` stamps first-write-wins via a `WHERE <column> IS NULL` guard, mapping the `Literal` step through a fixed `_ONBOARDING_COLUMNS` dict (no string interpolation, no `getattr`).
- `app/schemas/train.py`: `OnboardingStep = Literal["intro", "reveal_walkthrough", "sr_explained"]`; `TrainSettingsResponse` gains the three fields (`TrainSettingsUpdate` untouched — D-12); `SolvedResult` gains `source`/`item_status`/`due_date`, copying `SolveResponse`'s own declarations verbatim.
- `app/routers/train.py`: new `POST /train/onboarding/{step}` handler (`_reject_guest` first, `user.id` from `current_active_user` only, try/rollback/`sentry_sdk` shape mirroring `update_train_settings`); the two existing `TrainSettingsResponse(...)` sites (`get_train_settings`, `update_train_settings`) and the `SolvedResult(...)` site (`compose_or_resume_session`) all extended.
- `scripts/reset_train_state.py`: `_reset` now also clears the three onboarding columns, so onboarding UAT is repeatable on dev without `bin/reset_db.sh`.
- `_resume_session`'s `solved_rows_stmt` widened with a set-based `LEFT JOIN` to `drill_items` on `(user_id, game_id, ply)` — one query, no N per-row lookups — mapped through the existing `_wire_source`/`_STATUS_LITERAL` helpers.

## Task Commits

Each auto task was committed atomically (T-222-02-00 is a checkpoint, pre-resolved by the orchestrator before this executor ran — see Decisions below, no commit of its own):

1. **T-222-02-01: Migration, model columns, repository dataclass touch points, dev-reset clear** — `ac82cef0d` (feat)
2. **T-222-02-02: Stamp endpoint, Response-only schema extension, router tests** — `2284d86c4` (feat)
3. **T-222-02-03: Widen SolvedResult with source/item_status/due_date** — `170b90524` (feat)

**Plan metadata:** committed after this SUMMARY (see final commit below).

## Files Created/Modified

- `alembic/versions/20260913_144712_7d6bb75aae54_phase_222_train_onboarding_seen.py` - the three-column migration, no backfill
- `app/models/train_settings.py` - matching ORM columns
- `app/repositories/train_repository.py` - `TrainSettingsRow` +3 fields (4 sites), `stamp_onboarding_step`, `_ONBOARDING_COLUMNS`, `ComposedSolvedResult` +3 fields, `_resume_session`'s widened LEFT JOIN
- `app/schemas/train.py` - `OnboardingStep`, `TrainSettingsResponse` +3, `SolvedResult` +3
- `app/routers/train.py` - `POST /train/onboarding/{step}`, three extended response-construction sites
- `scripts/reset_train_state.py` - clears the three onboarding columns in `_reset`
- `tests/repositories/test_train_repository.py` - 7 new tests (defaults, round-trip, unchanged-on-PUT, source/item_status/due_date incl. orphan degradation)
- `tests/routers/test_train.py` - 2 fixed exact-dict assertions, 8 new onboarding tests, 1 new resume-solved-results test
- `tests/scripts/test_reset_train_state.py` - extended to assert the three columns clear

## Decisions Made

- **T-222-02-00 (checkpoint:decision, gate="blocking-human"), pre-resolved by the orchestrator before this executor ran.** User response, verbatim: **"Confirm as locked"** (option `confirm-as-locked`). Recorded outcome: the three columns land with exactly the D-11 names `intro_seen_at`, `reveal_walkthrough_seen_at`, `sr_explained_at` (nullable `DateTime(timezone=True)` on `train_settings`), with the D-13 no-backfill rule (all existing rows NULL), and the names enter `TrainSettingsResponse`. No file propagation was needed (no rename requested).
- `upsert_settings` RETURNING/reflects the three onboarding columns' true persisted values (mirrors the `reminder_last_sent_on` precedent already in the same function), rather than leaving the dataclass at an unset default on every PUT response — see Deviations below.
- `OnboardingStep` lives on `app/schemas/train.py` and is imported by the repository; this matches an established precedent (`game_repository.py` imports `Color` from `app.schemas.normalization`, `endgame_repository.py` imports `EndgameClass`, etc.) — the `ComposedSolvedResult` docstring's "the repository must not import from `app.schemas`" note is scoped to that dataclass's deliberate exclusion of a server-computed score field, not a blanket import ban.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] A fifth `TrainSettingsRow` construction site, not named in the plan's four-touch-point list**
- **Found during:** Task 1 (`uv run pytest tests/repositories/test_train_repository.py` after the dataclass extension)
- **Issue:** The plan's action step 3 named exactly four `TrainSettingsRow(...)` construction sites (`get_settings`, `get_or_create_settings`'s `pg_insert(...).values(...)` and its post-insert construction). A fifth site exists in `get_progress`'s pool-eligibility re-stamp branch (`if stamped_pool_eligible_since != settings_row.pool_eligible_since: settings_row = TrainSettingsRow(...)`), which the plan's `<read_first>`/action steps never named. Once the dataclass gained three required fields, this site raised `TypeError: missing 3 required positional arguments` at runtime, failing 9 pre-existing repository tests (`test_pool_state_*`, `test_next_due_date_*`, `TestBadgeVisible.*`, `TestStampPoolEligibility.*`).
- **Fix:** Added the three fields to this fifth construction site, reading them straight off the pre-mutation `settings_row` (this branch never touches the onboarding columns, only `pool_eligible_since`).
- **Files modified:** `app/repositories/train_repository.py`
- **Verification:** All 9 previously-failing tests pass; full repository suite (138 tests) green.
- **Committed in:** `ac82cef0d` (Task 1 commit)

**2. [Rule 1 - Bug] `upsert_settings`'s literal "no references inside this function" acceptance criterion would ship a client-visible regression**
- **Found during:** Task 1, while implementing the four named repository touch points
- **Issue:** Task 1's acceptance criteria included `grep -n "intro_seen_at\|reveal_walkthrough_seen_at\|sr_explained_at" app/repositories/train_repository.py` showing no hit inside `upsert_settings`'s function body — matching the plan's instruction that "`upsert_settings` must NOT gain them." Taken literally, this means `upsert_settings`'s returned `TrainSettingsRow` would carry the dataclass's unset value for all three fields on every call, i.e. every `PUT /train/settings` response would report `intro_seen_at`/`reveal_walkthrough_seen_at`/`sr_explained_at` as `null` regardless of the row's actual persisted state. Since the frontend's settings mutation (`useTrainSettings.ts`, shipped in plan 01) does `queryClient.setQueryData(TRAIN_SETTINGS_QUERY_KEY, data)` — a full cache replacement on the PUT response — this would make a user's already-completed onboarding stepper appear unseen again in the client cache after any unrelated settings change (e.g. changing the reminder hour), until the next full `GET /train/settings` refetch. This is the identical class of bug the existing `reminder_last_sent_on` RETURNING clause in this same function already exists to prevent for a structurally identical Response-only column.
- **Fix:** Added the three onboarding columns to `upsert_settings`'s `RETURNING` clause and its final `TrainSettingsRow(...)` construction, exactly mirroring `reminder_last_sent_on`'s existing treatment in the same function — read-only reflection of the true persisted value, never written by this UPSERT's `values()`/`set_` dict. This means the grep-based acceptance criterion, read literally, now finds matches inside `upsert_settings` (in the `RETURNING`/construction lines only, never in `values()`/`on_conflict_do_update`'s `set_` dict — the actual write side, which never references these columns).
- **Files modified:** `app/repositories/train_repository.py`
- **Verification:** New test `test_upsert_settings_leaves_onboarding_seen_unchanged` (mirrors the existing `test_upsert_settings_leaves_reminder_last_sent_on_unchanged`) asserts a PUT never moves a previously-stamped onboarding timestamp, both on the returned row and on the persisted row.
- **Committed in:** `2284d86c4` (Task 2 commit)

**3. [Rule 1 - Bug] `ruff format` reformatted a conditional expression after the `_resume_session` widening**
- **Found during:** Task 3, plan-level `<verification>` (`uv run ruff format --check`)
- **Issue:** The inline ternary for `item_status` in the list comprehension exceeded the line-length/style rule as originally written.
- **Fix:** Ran `uv run ruff format app/ tests/ scripts/ analysis/`, which reformatted the ternary onto three lines. No logic change.
- **Files modified:** `app/repositories/train_repository.py`
- **Verification:** `uv run ruff format --check app/ tests/ scripts/ analysis/` exits 0; full repository/router suites re-run green after the reformat.
- **Committed in:** `170b90524` (Task 3 commit)

---

**Total deviations:** 3 auto-fixed (1 blocking runtime failure, 2 bugs — one a formatter fix, one a considered departure from a literal acceptance criterion to avoid shipping a client-visible regression). **Impact:** All three were necessary for correctness; the second is the only one where the plan's own stated acceptance check and correct behavior genuinely diverged — flagged in detail above for the verifier's attention, since a literal read of that check would fail on the intentional fix.

## Known Stubs

None.

## Threat Flags

None. All entries in this plan's threat register (T-222-02-01 through T-222-02-07, T-222-02-SC) are discharged by construction and covered by a dedicated test each: IDOR (`test_onboarding_stamp_scoped_to_caller`), guest gate (`test_onboarding_403_guest`), step-name tampering (`test_onboarding_unknown_step_422_no_db_write`), PUT smuggling (`test_put_settings_cannot_smuggle_onboarding_seen_timestamp`), replay tampering (`test_onboarding_replay_leaves_first_timestamp_unchanged`), the `SolvedResult` answer-key re-check (`test_resume_solved_results_carry_source_item_status_due_date_no_answer_key`), and the supply-chain gate (`git diff --exit-code -- pyproject.toml uv.lock frontend/package.json frontend/package-lock.json` exits 0 — no package installed).

## Issues Encountered

None beyond the deviations documented above.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Plan 04 (solve-screen intro stepper + drop-nudge + verdict bubble) and plan 06 (score bubble / first-reveal walkthrough live accumulator) can now call `POST /train/onboarding/{step}` and read the three new `TrainSettingsResponse` fields from the already-warm `['train','settings']` cache (plan 01's `useTrainOnboarding` hook already targets this exact contract — no client-side rework needed).
- `SolvedResult`'s widened `source`/`item_status`/`due_date` cover the resume/reload/handoff half of the score bubble's data needs (RESEARCH Finding C); the live per-solve accumulator in `useTrainSession` for a session played start-to-finish in one sitting remains plan 06's job, not this plan's scope.
- No blockers. Full backend suite green: `uv run pytest -n auto -x` — 4700 passed, 19 skipped. `ruff check`, `ty check`, `ruff format --check`, and the nesting-depth/LOC function-size gate all pass with zero findings.

---
*Phase: 222-train-bot-narrated-onboarding-and-verdicts*
*Completed: 2026-09-13*

## Self-Check: PASSED
