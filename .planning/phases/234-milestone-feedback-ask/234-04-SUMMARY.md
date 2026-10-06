---
phase: 234-milestone-feedback-ask
plan: 04
subsystem: frontend
tags: [feedback-ask, hilda, train-landing, bots-roster, changelog]
requires:
  - "FeedbackAskBubble, feedbackAskDays (plan 02)"
  - "app-level 'Sure!' modal host (plan 03)"
provides:
  - "Hilda's ask on the Train landing (after the intro, phones included)"
  - "Hilda's ask on the Bots roster welcome bubble"
  - "CHANGELOG [Unreleased] bullet"
affects:
  - "phase 234 verification (browser UAT legs pending)"
tech-stack:
  added: []
  patterns:
    - "Page reads useUserProfile once and prop-drills feedbackAskDays; leaf components stay provider-less in tests"
key-files:
  created: []
  modified:
    - frontend/src/pages/Train.tsx
    - frontend/src/components/train/TrainStartScreen.tsx
    - frontend/src/components/train/__tests__/TrainStartScreen.test.tsx
    - frontend/src/components/bots/PersonaGrid.tsx
    - frontend/src/components/bots/__tests__/PersonaGrid.test.tsx
    - frontend/src/pages/Bots.tsx
    - CHANGELOG.md
key-decisions:
  - "TrainStartScreen gets a required feedbackAskDays prop, so tsc catches a missing wire-up; PersonaGrid's is optional like winsByPersona"
  - "Existing TrainStartScreen test fixtures got feedbackAskDays: null (the required prop would otherwise break tsc -b); no assertions changed"
requirements-completed: [FBASK-08, FBASK-09]
duration: ~20 min
completed: 2026-10-06
status: complete
actuals:
  tokens: 6500
  tasks: 3
  commits: 4
plan_head_before: 646abc54ea51b33c920e97bbd0ad30c2e183b4c4
plan_head_after: 0232a17ace841372b21b06094e922377f24d94dc
---

# Phase 234 Plan 04: Hilda ask on Train landing and Bots roster Summary

Hilda's milestone feedback ask now also appears on the Train landing (replacing the daily host once the intro is done, visible on phones, outranking the reminder and import asks) and on the Bots roster welcome bubble, reusing plan 02's `FeedbackAskBubble`; CHANGELOG announces the ask and the full pre-merge gate is green.

## Accomplishments

- **Tracer (Task 1):** `Train.tsx` passes `feedbackAskDays(profile)` to `TrainStartScreen`; `TrainHeader` computes `askDays = introDone ? feedbackAskDays : null` (D-04: Tank's intro wins, and requiring loaded settings avoids counting a view on a render that flips to Tank). While the ask shows, the whole host bubble is replaced (SEED-191 #10, so it outranks the reminder-install and import asks) and `max-sm:hidden` is dropped (SEED-191 #3). Five new tests cover intro done, reminder outranked, intro not done, inactive, and the completed landing.
- **Task 2 (TDD):** `BotWelcomeCard` early-returns `FeedbackAskBubble surface="bots"` (large avatar) while `feedbackAskDays != null`; the greeting and `bots-intro-info` popover return when null or omitted. `PersonaGrid` still calls no query hook (acceptance grep empty). RED commit `5691adac9` (active-ask test failed, the two inactive variants passed as expected) precedes GREEN `5c5fb34b4`.
- **Task 3:** CHANGELOG `[Unreleased]` -> Added bullet (CHANGELOG-OK printed). Full pre-merge gate green with plans 01-04 applied.
- The score screen (`TrainScoreScreen.tsx`) and solve screen are untouched (empty diff for the plan's commits).

## Task Commits

| Task | Commit | Description |
| ---- | ------ | ----------- |
| 1 (tracer) | 7706d4dde | Hilda's ask on the Train landing |
| 2 RED | 5691adac9 | Failing tests for the Bots roster ask |
| 2 GREEN | 5c5fb34b4 | Bots roster ask branch, Bots.tsx wiring |
| 3 | 0232a17ac | CHANGELOG bullet |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Pre-existing TrainStartScreen test fixtures needed the new required prop**
- **Found during:** Task 1
- **Issue:** The plan says pre-existing tests stay untouched because they omit the prop, but `feedbackAskDays` is a required prop and `tsc -b` type-checks the test files, so the `renderScreen` helper and the refetch test's explicit props object would fail the build.
- **Fix:** Added `feedbackAskDays={null}` to `renderScreen` (before the `{...props}` spread, so overrides still win) and `feedbackAskDays: null` to the refetch test's props. No assertion changed.
- **Files modified:** `frontend/src/components/train/__tests__/TrainStartScreen.test.tsx`
- **Commit:** 7706d4dde

**Total deviations:** 1 auto-fixed (1 blocking). **Impact:** none on behavior.

## Verification

- `npx vitest run` on TrainStartScreen (53 tests), PersonaGrid and Bots page tests (58): green.
- Pre-merge gate, run once in foreground: `ruff format` (521 files unchanged), `ruff check` clean, `ty check app/ tests/ scripts/` clean, `ty check analysis/` clean, `check_function_size.py` no breaches (1142 functions), `pytest -n auto -x` 5254 passed / 19 skipped; frontend `npm run lint`, `npm run build`, `npm test -- --run` (312 files / 5172 tests), `npm run knip` all exit 0. The gate modified no files, so no style commit.
- Acceptance greps: both `feedbackAskDays={feedbackAskDays(profile)}` wire-ups, `surface="train-landing"`, `surface="bots"`, two `feedbackAskDays: number | null` in TrainStartScreen, PersonaGrid query-hook grep empty.

## Manual UAT (pending, for /gsd-verify-work, run by the orchestrator in the browser)

Setup: registered dev user without feedback rows, 4 prior `user_activity` days (current_date - 1..4), `users.prompt_state = '{}'`, Train intro completed.

1. Import -> Train -> Bots on one day: Hilda on all three with "for 5 days now"; `prompt_state->'feedback_v1'->>'views'` is 1 afterwards.
2. Phone width (375px) on the Train landing: Hilda visible above the streak card.
3. Start an import, click "Sure!" while the 3s poll runs: modal and typed draft persist after Hilda disappears; submit stores `feedback.source = 'milestone_ask'`.
4. "Maybe later" on a fresh state: Hilda vanishes at once on the current page and stays gone on the other two.

## Known Stubs

None.

## Threat Flags

None. Both surfaces read only `feedbackAskDays(profile)` (server-decided `feedback_ask.active`), so T-234-13 holds: no client-side eligibility.

## Self-Check: PASSED

Modified files exist, commits 7706d4dde, 5691adac9, 5c5fb34b4, 0232a17ac are ancestors of HEAD.
