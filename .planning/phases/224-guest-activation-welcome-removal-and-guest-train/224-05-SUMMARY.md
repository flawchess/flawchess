---
phase: 224-guest-activation-welcome-removal-and-guest-train
plan: 05
subsystem: train
tags: [fastapi, sqlalchemy, guest-accounts, pytest, guest-lifecycle]

# Dependency graph
requires:
  - phase: 224-01
    provides: "Train open to every zero-game account (guest gate removed), enabling a guest to accumulate real drill_sessions/drill_solves/train_settings rows"
provides:
  - "_purge_guest deletes a guest's drill_sessions (cascading drill_solves) and train_settings alongside the games cascade (D-08)"
  - "A rewritten test proving the purge deletes Train rows, including a game_id-IS-NULL filler solve the games cascade cannot reach"
  - "An integration test proving promotion preserves a guest's Train session, solves, settings and streak"
  - "train_reminder_repository's guest-exclusion docstring states the filter is load-bearing, not defence in depth"
affects: [224-06-signup-ask]

# Actuals (#2632)
actuals:
  tokens: 5296
  tasks: 3
  commits: 3

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Guest purge deletes Train state by targeting the parent drill_sessions row only, relying on session_id ON DELETE CASCADE to reach every drill_solves row (including rows a games-scoped cascade cannot reach, e.g. game_id IS NULL fillers)"

key-files:
  created: []
  modified:
    - app/services/guest_cleanup_service.py
    - tests/test_guest_cleanup_service.py
    - tests/test_guest_auth.py
    - app/repositories/train_reminder_repository.py

key-decisions:
  - "Deleting drill_sessions alone is sufficient and correct: drill_solves.session_id is ON DELETE CASCADE, so no separate DrillSolve delete statement was added (kept the plan's explicit prohibition)"
  - "The purge test's filler solve uses source=SHARP_FILLER with game_id=None and a sharp_puzzle_id, matching the real shape of a warm-up-only session's unreachable-by-games-cascade row"
  - "The promotion-preservation test verifies the guest's real internal user id via the drill_sessions row it created (the profile response has no id field), rather than decoding the JWT"
  - "Per explicit project_notes override, the full backend suite (uv run pytest -n auto -x) named in the plan's verification block was NOT run this session; only tests/test_guest_cleanup_service.py, tests/test_guest_auth.py, ty, ruff, and the function-size gate were run (see Deviations)"

requirements-completed: [GUESTACT-06, GUESTACT-10, GUESTACT-16]

coverage:
  - id: D1
    description: "The 30-day guest purge deletes drill_sessions, drill_solves (via cascade) and train_settings alongside the games, proven by a rewritten test including a game_id-IS-NULL filler solve"
    requirement: "GUESTACT-10"
    verification:
      - kind: integration
        ref: "tests/test_guest_cleanup_service.py#TestPurgeGuestDrillCascade::test_purge_guest_cascades_drill_rows"
        status: pass
    human_judgment: false
  - id: D2
    description: "Promoting a guest in place preserves its drill_sessions, drill_solves, train_settings and streak"
    requirement: "GUESTACT-06"
    verification:
      - kind: integration
        ref: "tests/test_guest_auth.py#TestGuestPromotion::test_train_state_preserved_after_promotion"
        status: pass
    human_judgment: false
  - id: D3
    description: "The reminder fan-out's User.is_guest.is_(False) filter is unchanged and its docstring states the invariant that actually holds post-Phase-224"
    requirement: "GUESTACT-16"
    verification:
      - kind: other
        ref: "grep -q 'is_guest.is_(False)' app/repositories/train_reminder_repository.py && grep -q 'Phase 224' app/repositories/train_reminder_repository.py"
        status: pass
      - kind: other
        ref: "git diff -- app/repositories/train_reminder_repository.py (docstring-only hunk)"
        status: pass
    human_judgment: false

duration: 35 min
completed: 2026-09-17
status: complete
---

# Phase 224 Plan 5: Guest Lifecycle — Purge Deletes Train State, Promotion Preserves It Summary

**`_purge_guest` now deletes a purged guest's `drill_sessions`/`drill_solves`/`train_settings` alongside their games (D-08), while `promote_guest_with_password` continues to preserve all three unchanged, both proven by inverted/new tests, and the reminder fan-out's guest-exclusion docstring now states that its filter is load-bearing rather than defence-in-depth.**

## Performance

- **Duration:** 35 min
- **Started:** 2026-09-17T21:20:00Z
- **Completed:** 2026-09-17T21:55:49Z
- **Tasks:** 3
- **Files modified:** 4

## Accomplishments

- `app/services/guest_cleanup_service.py`: added `delete(DrillSession)` and `delete(TrainSettings)` statements inside `_purge_guest`'s existing transaction (after the derived-stats deletes, before the backfill-cursor reset), replaced the superseded Phase 189 "Train tables need no handling" comment with the Phase 224 D-08 rule, and updated the module docstring to state Train rows do NOT survive the purge as of Phase 224
- `tests/test_guest_cleanup_service.py`: rewrote `test_purge_guest_cascades_drill_rows` to seed a second `drill_solves` row with `game_id=None`/`source=SHARP_FILLER` (the row the games cascade structurally cannot reach) and a `train_settings` row, then flipped every post-purge assertion from "survives" to "deleted" (`drill_sessions`, `drill_solves`, `train_settings`, `drill_items` all `== 0`)
- `tests/test_guest_auth.py`: added `test_train_state_preserved_after_promotion` to `TestGuestPromotion` — composes a Train session as a guest over HTTP, solves every puzzle to a streak of 1, promotes via `/auth/guest/promote/email`, and asserts (both over HTTP and via a direct DB read) that the same user id, `drill_sessions` row, all `drill_solves` rows, and the `train_settings` row all survive, and the streak reported by `/train/progress` is unchanged
- `app/repositories/train_reminder_repository.py`: rewrote the "Guest exclusion (REMIND-07)" docstring paragraph to state that `User.is_guest.is_(False)` is now load-bearing (guests can reach `PUT /train/settings` as of Phase 224) rather than defence-in-depth against an already-403ing route; no SQL, filter, or function signature changed

## Task Commits

Each task was committed atomically:

1. **Task 1: The purge takes the guest's Train rows with the games (D-08)** - `76b5cdac8` (feat)
2. **Task 2: Rewrite the purge test to prove the new rule, including the unreachable filler solve** - `6fcae5065` (test)
3. **Task 3: Prove promotion preserves Train state, and retire the stale gate docstring** - `24e2bff99` (test)

**Plan metadata:** committed alongside this SUMMARY (see final commit below)

## Files Created/Modified

- `app/services/guest_cleanup_service.py` - two new deletes in `_purge_guest`, superseded comment replaced, module docstring updated
- `tests/test_guest_cleanup_service.py` - `test_purge_guest_cascades_drill_rows` inverted to prove D-08, including the `game_id IS NULL` filler-solve seed
- `tests/test_guest_auth.py` - new `test_train_state_preserved_after_promotion` in `TestGuestPromotion`
- `app/repositories/train_reminder_repository.py` - "Guest exclusion" docstring paragraph rewritten (no code change)

## Decisions Made

- No separate `delete(DrillSolve)` statement was added — `drill_solves.session_id` is `ON DELETE CASCADE` to `drill_sessions`, so deleting the session is sufficient and one fewer statement, exactly as the plan's prohibition required.
- The promotion test reads the guest's real internal `user_id` off the `drill_sessions` row it just created (via a direct DB query through `test_engine`) rather than trying to extract an `id` field from `GET /users/me/profile` (that schema has no `id` field) or decoding the JWT — simpler and it doubles as part of the "same row" proof.
- The filler solve in the rewritten purge test uses `source=DrillSource.SHARP_FILLER` with `game_id=None` and a `sharp_puzzle_id`, matching the real on-disk shape of an unreachable-by-games-cascade row (rather than an arbitrary NULL-`game_id` row of a different `source`).

## Deviations from Plan

### Auto-fixed Issues

None — plan executed exactly as written, with the one explicitly instructed scope reduction below (not a deviation rule, an operator instruction).

### Explicit Scope Reduction (operator instruction, not a Rule 1-4 deviation)

**Full backend suite not run this session.** The plan's `<verification>` block and Task 3's `<verify>` both name `uv run pytest -n auto -x` as a gate. The orchestrator's `project_notes` for this dispatch explicitly instructed: "Do NOT run the full backend suite (`uv run pytest -n auto`) ... Run only the relevant test files." Per that instruction, only `tests/test_guest_cleanup_service.py` and `tests/test_guest_auth.py` were run (39 passed combined), alongside `uv run ty check`, `uv run ruff check .`, `uv run ruff format --check`, and `uv run python scripts/check_function_size.py` — all green. The full-suite run named in the plan's own verification section was not executed. An attempt to record this in `.planning/WINDOWS.md` via `gsd_run query windows.append --kind unrun-verify` failed with a pre-existing ledger-table/JSON mismatch unrelated to this plan (row id 8); per the ledger's documented best-effort contract this was not retried or hand-fixed (out of this plan's scope).

---

**Total deviations:** 0 auto-fixed. One explicitly instructed scope reduction (full-suite run skipped per operator override).
**Impact on plan:** No scope creep, no unauthorized shortcuts — the reduction was directed by the dispatch's own project_notes, not a judgment call made during execution. The two directly-relevant test files are green and the standard gate (ty/ruff/function-size) is clean; the full-suite run remains outstanding for whoever next runs it (e.g. at the pre-merge gate per CLAUDE.md, which mandates `uv run pytest -n auto -x` before any squash-merge to `main` regardless of what ran during phase execution).

## Issues Encountered

- Ruff's initial format pass required renaming one comment string (`delete(DrillSolve)` -> "DrillSolve-targeting delete statement") because the literal substring `delete(DrillSolve)` inside an explanatory comment tripped Task 1's own acceptance-criteria grep (`! grep -q 'delete(DrillSolve)' ...`), which does not distinguish code from comments. Resolved by rewording the comment; no functional change.
- `gsd_run query windows.append` (attempted to log the skipped full-suite run to the cross-phase defect ledger) failed with a pre-existing `WINDOWS.md` table/JSON disagreement at row id 8, unrelated to this plan's changes. Per the ledger's best-effort contract this was not fixed (out of scope) — documented above instead.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- D-08 (purge deletes Train state) and the promotion-preservation invariant (ROADMAP SC 4/SC 8) are both implemented and proven by tests.
- `train_reminder_repository`'s guest-exclusion docstring is accurate post-Phase-224.
- No new abuse guard was added (D-09 respected — only test/service/docstring changes, no rate-limiter or quota code touched).
- Outstanding: the full backend suite (`uv run pytest -n auto -x`) has not been run against these changes this session — must run before any squash-merge to `main` per CLAUDE.md's mandatory pre-merge gate.
- Ready for the remaining plan(s) in this phase (e.g. 224-06 signup-ask), and for the phase-level verification/UAT pass.

---
*Phase: 224-guest-activation-welcome-removal-and-guest-train*
*Completed: 2026-09-17*

## Self-Check: PASSED

- `app/services/guest_cleanup_service.py` exists (FOUND)
- `tests/test_guest_cleanup_service.py` exists (FOUND)
- `tests/test_guest_auth.py` exists (FOUND)
- `app/repositories/train_reminder_repository.py` exists (FOUND)
- Commit `76b5cdac8` present in `git log` (FOUND)
- Commit `6fcae5065` present in `git log` (FOUND)
- Commit `24e2bff99` present in `git log` (FOUND)
- `uv run pytest tests/test_guest_cleanup_service.py tests/test_guest_auth.py -x -q` -> 39 passed
- `uv run pytest tests/test_guest_auth.py -k rate_limit -x -q` -> 1 passed (D-09 backstop coverage still selects and passes)
- `uv run ty check app/ tests/ scripts/` -> All checks passed
- `uv run ruff check .` -> All checks passed
- `uv run ruff format --check app/ tests/ scripts/` -> 468 files already formatted
- `uv run python scripts/check_function_size.py app/ --fail-over-depth 4 --fail-over-loc 200` -> OK, no breaches
- All plan `<acceptance_criteria>` re-verified: PASS for every criterion across Tasks 1-3
