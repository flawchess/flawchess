---
phase: 230-weekly-train-leaderboards
plan: 04
subsystem: api
tags: [backend, frontend, settings, privacy, leaderboard, tanstack-query, react]

requires:
  - phase: 230-weekly-train-leaderboards (plan 01)
    provides: users.leaderboard_hidden column and the server-side visibility rules on both boards
  - phase: 230-weekly-train-leaderboards (plan 03)
    provides: TRAIN_LEADERBOARD_QUERY_KEY, the landing card the mutation re-ranks
provides:
  - "GET/PUT /api/users/me/profile carry leaderboard_hidden (None on PUT = unchanged, non-boolean = 422)"
  - "useSetLeaderboardHidden mutation and USER_PROFILE_QUERY_KEY in hooks/useUserProfile.ts"
  - "LeaderboardPrivacyCard: server-persisted 'Hide me from leaderboards' switch in the settings overlay, after Reset, hidden for guests"
  - "Privacy page line disclosing the leaderboard use of usernames and the opt-out"
affects: [230-05, settings, privacy, train-leaderboard]

actuals:
  tokens: 7900
  tasks: 2
  commits: 3
plan_head_before: ac2fa82918d163681fa411890933ae1be72b6c22
plan_head_after: 96e724d2abdd934648aa1e5f6f219510b4d2dcd7

tech-stack:
  added: []
  patterns:
    - "Profile mutation writes the PUT response straight into the ['userProfile'] cache (setQueryData) and invalidates the dependent leaderboard prefix, so the switch reads the server's answer and the board re-ranks without a reload"
    - "Switch shows mutation.variables while a save is in flight and the stored value otherwise, so a rejected PUT falls back with no extra state"
    - "Server-state settings card rendered outside isAtDefaults/resetAllSettings, which stay localStorage-only"

key-files:
  created:
    - frontend/src/components/settings/LeaderboardPrivacyCard.tsx
    - frontend/src/components/settings/__tests__/LeaderboardPrivacyCard.test.tsx
  modified:
    - app/schemas/users.py
    - app/routers/users.py
    - tests/test_users_router.py
    - tests/routers/test_train_leaderboard.py
    - frontend/src/types/users.ts
    - frontend/src/hooks/useUserProfile.ts
    - frontend/src/components/settings/SettingsPanel.tsx
    - frontend/src/components/settings/__tests__/SettingsPanel.test.tsx
    - frontend/src/components/settings/__tests__/SettingsDialogButton.test.tsx
    - frontend/src/components/settings/__tests__/SettingsSheetButton.test.tsx
    - frontend/src/App.test.tsx
    - frontend/src/pages/__tests__/Bots.test.tsx
    - frontend/src/pages/Privacy.tsx

key-decisions:
  - "No repository change: user_repository.update_profile already drops None and applies an explicit False, so the new bool | None field gets the right omit-vs-false semantics for free"
  - "The toggle sends no Umami event (database-landing write per frontend/CLAUDE.md, RESEARCH A4)"
  - "The card renders null for guests and while the profile is loading; only a profile error renders the Privacy card shell with the load-error line"

patterns-established:
  - "Suites that render the real SettingsPanel without a QueryClientProvider each mock LeaderboardPrivacyCard (five suites now: SettingsPanel, SettingsDialogButton, SettingsSheetButton, App, Bots)"

requirements-completed: [D-06, D-13, D-16]

coverage:
  - id: D1
    description: "GET /users/me/profile exposes leaderboard_hidden (default false); PUT persists true/false, an omitted or null field leaves it unchanged, a non-boolean is a 422"
    requirement: "D-16"
    verification:
      - kind: unit
        ref: "tests/test_users_router.py#TestProfileLeaderboardHidden"
        status: pass
    human_judgment: false
  - id: D2
    description: "After a user hides, other viewers' boards no longer contain them and rank without them, the user keeps a private 'hidden' row, un-hiding restores the public row"
    requirement: "D-13"
    verification:
      - kind: unit
        ref: "tests/routers/test_train_leaderboard.py#test_profile_opt_out_hides_user_from_other_viewers"
        status: pass
    human_judgment: false
  - id: D3
    description: "Settings overlay has a Privacy card with the switch; it reads useUserProfile().data, writes through the profile PUT, adopts the response and invalidates the boards; guests see nothing; errors and pending states are visible; no analytics event"
    requirement: "D-16"
    verification:
      - kind: unit
        ref: "frontend/src/components/settings/__tests__/LeaderboardPrivacyCard.test.tsx"
        status: pass
    human_judgment: false
  - id: D4
    description: "The Privacy card sits after Reset, is not part of isAtDefaults, and Reset never changes it"
    requirement: "D-16"
    verification:
      - kind: unit
        ref: "frontend/src/components/settings/__tests__/SettingsPanel.test.tsx#places the Privacy section after the Reset button (server state, outside Reset)"
        status: pass
      - kind: unit
        ref: "frontend/src/components/settings/__tests__/LeaderboardPrivacyCard.test.tsx#keeps the hidden choice when Reset to defaults runs and sends no PUT"
        status: pass
    human_judgment: false
  - id: D5
    description: "The Privacy page discloses that the lichess (else chess.com) username appears next to weekly Train results on boards other users see, that guests never appear, that missing usernames show as Anonymous, and how to hide"
    requirement: "D-16"
    verification:
      - kind: command
        ref: "grep -c 'leaderboards that other FlawChess users can see' frontend/src/pages/Privacy.tsx"
        status: pass
    human_judgment: true
    rationale: "Wording adequacy of a legal-adjacent disclosure is a judgment the owner makes; the presence of the line is asserted by grep only"

duration: 7min
completed: 2026-10-04
status: complete
---

# Phase 230 Plan 04: Leaderboard Opt-out Summary

**A registered user can hide themselves from the weekly Train leaderboards: `leaderboard_hidden` rides the profile GET/PUT, a "Hide me from leaderboards" switch sits in a Privacy card after Reset in the settings overlay, and the Privacy page states the new use of usernames and the way out.**

## Performance

- **Duration:** 7 min
- **Started:** 2026-10-04T02:44:00Z
- **Completed:** 2026-10-04T02:51:00Z
- **Tasks:** 2 (1 tracer, 1 TDD)
- **Files modified:** 15 (2 created, 13 modified)

## Accomplishments

- `UserProfileResponse.leaderboard_hidden: bool` and `UserProfileUpdate.leaderboard_hidden: bool | None`; router passes it in both GET and PUT. The existing repository `None` filtering gives omit-leaves-unchanged and explicit-false-unhides with no repository edit. `beta_enabled` stays out of the update schema (the BETA-01 mass-assignment test still passes).
- `useSetLeaderboardHidden` PUTs `{ leaderboard_hidden }`, writes the returned profile into `['userProfile']` and invalidates `['train', 'leaderboard']`; `USER_PROFILE_QUERY_KEY` replaces the inline literal inside `useUserProfile` only.
- `LeaderboardPrivacyCard`: switch + visible label + helper line; shows the requested state while saving and falls back to the stored value on rejection; renders nothing for guests/loading; `LoadError` card shell on a profile error; `settings-leaderboard-hidden-error` on a failed save. `lib/engineSettings.ts` was not edited, so Reset and `isAtDefaults` stay localStorage-only.
- End-to-end router test drives the real PUT: another viewer loses the row and moves up a rank, the hider keeps exactly one `hidden` row, un-hiding restores the public row.
- Privacy page: one list item under "What we collect", "Last updated: October 2026".

## Task Commits

1. **Task 1 (tracer): hide-me switch persisted through the profile PUT** - `f2da465f9` (feat)
2. **Task 2 tests: opt-out end to end, card edge states, panel placement** - `6b07395d0` (test)
3. **Task 2: Privacy page disclosure** - `96e724d2a` (feat)

**Plan metadata:** committed separately (docs: complete plan)

## Decisions Made

- No repository change; the existing `None`-dropping `update_profile` already has the needed semantics.
- No Umami event on the toggle (DB-known write).
- Guests: card hidden, nothing to opt out of; a guest PUT is harmless (T-230-14, accepted).

## TDD Gate Compliance

Task 2 is flagged `tdd="true"`, but every behavior in its list was already delivered by the Task 1 tracer (the card was written with the pending, guest, load-error, save-error and Reset-safe branches from the start, and the backend visibility came from Plan 01). The RED step therefore could not fail: the `test(230-04)` commit `6b07395d0` is characterization coverage that passed on first run, followed by `feat(230-04)` `96e724d2a` for the only net-new production code (the Privacy copy). `gsd_run check tdd-red-evidence` was not run.

To compensate, mutation checks on the card (each reverted afterwards, 7/7 green restored): removing `disabled={mutation.isPending}` failed `disables the switch and shows the requested state while the PUT is pending`; removing the `is_guest` guard failed `renders nothing for a guest profile`; replacing the in-flight `mutation.variables` with the stored value failed the same pending test.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Bots.test.tsx also renders the real SettingsPanel without a QueryClient**
- **Found during:** Task 2 (full vitest run after the panel placement tests)
- **Issue:** `src/pages/__tests__/Bots.test.tsx` "mobile settings sheet" test crashed: the real card calls `useQueryClient`, and the file's `useUserProfile` mock factory lacks `useSetLeaderboardHidden`. The plan's mock list named four suites and missed this fifth one.
- **Fix:** Added the same `vi.mock('@/components/settings/LeaderboardPrivacyCard', ...)` returning null.
- **Files modified:** frontend/src/pages/__tests__/Bots.test.tsx
- **Verification:** full frontend suite 296 files / 4867 tests pass
- **Commit:** 6b07395d0

**Total deviations:** 1 auto-fixed (1 blocking). **Impact:** test-only, no production change.

## Issues Encountered

None.

## Known Stubs

None.

## Threat Flags

None. The only new surface is one bool field on an existing authenticated, self-scoped route (T-230-11 mitigated by tests); no package installs.

## Verification Results

- `uv run pytest tests/routers/test_train_leaderboard.py tests/test_users_router.py -x`: 39 passed (5 `leaderboard` cases in `TestProfileLeaderboardHidden`, `-k opt_out` 1 passed)
- `uv run ruff format/check`, `uv run ty check app/ tests/ scripts/`, `check_function_size.py app/ --fail-over-depth 4`: clean
- `npx vitest run` (whole frontend): 296 files, 4867 tests passed; `npm run lint`, `npm run build`, `npm run knip`: clean (one pre-existing knip config hint)
- Acceptance greps: `leaderboard_hidden` x3 in schemas, `leaderboard_hidden=` x2 in router, card mock present in all four named suites, 0 `trackEvent|trackFeature` in the card, `TRAIN_LEADERBOARD_QUERY_KEY` x2 in the hook, Privacy phrase x1, "October 2026" x1, error testid x1; card suite 7 tests

## Next Phase Readiness

- Plan 05 can rely on a hidden viewer's private row and on `['train','leaderboard']` being invalidated when the flag flips.
- Browser confirmation of the Settings Privacy card (desktop dialog and mobile sheet) is not done here; the visual check belongs to Plan 05's human-check run.

---
*Phase: 230-weekly-train-leaderboards*
*Completed: 2026-10-04*

## Self-Check: PASSED

Both created files exist on disk; commits f2da465f9, 6b07395d0 and 96e724d2a are present; acceptance criteria for both tasks re-run green.
