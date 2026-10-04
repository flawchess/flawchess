---
phase: 230-weekly-train-leaderboards
plan: 03
subsystem: ui
tags: [frontend, train, leaderboard, tanstack-query, umami, react]

requires:
  - phase: 230-weekly-train-leaderboards (plan 01)
    provides: GET /api/train/leaderboard wire contract (both boards, seconds_remaining, rank_without_session key)
provides:
  - "TrainLeaderboardCard: one tabbed 'This week' card (Points | Accuracy) on the Train landing, in the D-08 position"
  - "useTrainLeaderboard hook (landing + score-screen variants) and trainApi.getLeaderboard"
  - "lib/trainLeaderboard.ts: tab storage, countdown math/format, row and hint copy (pure, React-free)"
  - "Umami tab-switch targets leaderboard-points / leaderboard-accuracy"
  - "SignupAskSource 'train-leaderboard'; TrainDevClock leaderboard invalidation"
affects: [230-04, 230-05, train-leaderboard, medals]

actuals:
  tokens: 12600
  tasks: 3
  commits: 5
plan_head_before: a0b4de344f2ad59ca1713ecd4001ae6c736a8dba
plan_head_after: 72517c88d75a3f97c44e97d8d184be776ee88ddb

tech-stack:
  added: []
  patterns:
    - "One useQuery with options computed from an optional sessionId (landing vs score-screen variant), because rules-of-hooks forbids calling two hooks conditionally"
    - "Countdown = server seconds_remaining minus time since dataUpdatedAt; the clock is read only inside the setInterval callback (react-hooks purity)"
    - "Per-week_end ref guards the deadline invalidation so a skewed client clock cannot loop refetches"
    - "Module-level Record maps a board kind to its Umami target, so nothing user-derived is ever sent"

key-files:
  created:
    - frontend/src/hooks/useTrainLeaderboard.ts
    - frontend/src/lib/trainLeaderboard.ts
    - frontend/src/lib/__tests__/trainLeaderboard.test.ts
    - frontend/src/components/train/TrainLeaderboardCard.tsx
    - frontend/src/components/train/__tests__/TrainLeaderboardCard.test.tsx
  modified:
    - frontend/src/types/train.ts
    - frontend/src/api/client.ts
    - frontend/src/components/train/TrainStartScreen.tsx
    - frontend/src/components/train/__tests__/TrainStartScreen.test.tsx
    - frontend/src/components/train/SignupAskActions.tsx
    - frontend/src/components/train/TrainDevClock.tsx
    - frontend/src/lib/analytics.ts
    - frontend/src/lib/__tests__/analytics.test.ts
    - frontend/src/pages/__tests__/Train.solveLoop.test.tsx

key-decisions:
  - "useTrainLeaderboard is a single useQuery whose key, staleTime, refetchOnMount and enabled derive from options.sessionId (undefined = landing), not two conditionally-called hooks"
  - "The countdown never sets state on mount: until the first 60 s tick the fetch time stands in for 'now', which keeps the react-hooks set-state-in-effect rule satisfied and shows the server value exactly"
  - "Hidden and guest labelling keys off the row's own visibility field, not the board viewer, so the private would-be row renders correctly wherever the server places it"

patterns-established:
  - "Leaderboard card tests spy on apiClient.get (real axios instance) so client, hook and card are covered together; TrainStartScreen tests stub the card to keep the QueryClient-free suite intact"

requirements-completed: [D-02, D-03, D-04, D-07, D-08, D-09, D-10, D-13, D-14, D-15, D-19]

coverage:
  - id: D1
    description: "The Train landing shows one 'This week' card with Points and Accuracy tabs, rows with rank/name/value/puzzle count, viewer highlight and gap marker, fed by GET /train/leaderboard"
    requirement: "D-04"
    verification:
      - kind: unit
        ref: "frontend/src/components/train/__tests__/TrainLeaderboardCard.test.tsx#renders rows in server order with shared ranks, name, value and puzzle count"
        status: pass
      - kind: unit
        ref: "frontend/src/components/train/__tests__/TrainLeaderboardCard.test.tsx#renders a hidden gap marker before a gap_before row"
        status: pass
    human_judgment: false
  - id: D2
    description: "The card sits after TrainStreakCard and before TrainStatsCard on the completed, fresh and exhausted landing states"
    requirement: "D-08"
    verification:
      - kind: unit
        ref: "frontend/src/components/train/__tests__/TrainStartScreen.test.tsx#Phase 230 D-08: weekly leaderboard card position"
        status: pass
    human_judgment: false
  - id: D3
    description: "Selected tab persists in localStorage under flawchess_train_leaderboard_tab; first visit, unknown value or throwing storage fall back to Points"
    requirement: "D-09"
    verification:
      - kind: unit
        ref: "frontend/src/lib/__tests__/trainLeaderboard.test.ts#readLeaderboardTab / writeLeaderboardTab"
        status: pass
      - kind: unit
        ref: "frontend/src/components/train/__tests__/TrainLeaderboardCard.test.tsx#remembers the tab across a remount via localStorage"
        status: pass
    human_judgment: false
  - id: D4
    description: "Accuracy tab helper line, tentative marker, 'N more puzzles to qualify' from the server count, and the specific not-on-this-board line for a viewer with no Accuracy entry; no copy frames the board as ability"
    requirement: "D-19"
    verification:
      - kind: unit
        ref: "frontend/src/components/train/__tests__/TrainLeaderboardCard.test.tsx#D-19: a viewer with Points entries but no Accuracy entry gets the not-entered line"
        status: pass
      - kind: unit
        ref: "frontend/src/components/train/__tests__/TrainLeaderboardCard.test.tsx#never frames the board as ability"
        status: pass
    human_judgment: false
  - id: D5
    description: "Hand tab switches send tab-switch with a leaderboard target; mount, restore and re-tap send nothing"
    requirement: "D-09"
    verification:
      - kind: unit
        ref: "frontend/src/components/train/__tests__/TrainLeaderboardCard.test.tsx#TrainLeaderboardCard Umami tab-switch (Phase 229 registry)"
        status: pass
      - kind: unit
        ref: "frontend/src/lib/__tests__/analytics.test.ts#trackFeature sends the %s tab-switch target with page train (Phase 230)"
        status: pass
    human_judgment: false
  - id: D6
    description: "Countdown derived from the server remainder, ticking every 60 s, invalidating the query once per week_end at zero; dev-clock changes invalidate the leaderboard"
    requirement: "D-02"
    verification:
      - kind: unit
        ref: "frontend/src/components/train/__tests__/TrainLeaderboardCard.test.tsx#invalidates the leaderboard query exactly once at the deadline, without looping"
        status: pass
      - kind: unit
        ref: "frontend/src/lib/__tests__/trainLeaderboard.test.ts#remainingSeconds"
        status: pass
    human_judgment: false
  - id: D7
    description: "Hidden viewer row labelled 'Hidden from others', guest ghost row 'You (guest)' plus the claim-your-spot nudge with the shared sign-up pair (source train-leaderboard), Anonymous names render as sent"
    requirement: "D-14"
    verification:
      - kind: unit
        ref: "frontend/src/components/train/__tests__/TrainLeaderboardCard.test.tsx#guest: shows the claim-your-spot nudge with the shared sign-up pair (train-leaderboard source)"
        status: pass
      - kind: unit
        ref: "frontend/src/components/train/__tests__/TrainLeaderboardCard.test.tsx#a hidden viewer row shows the name plus \"Hidden from others\""
        status: pass
    human_judgment: false
  - id: D8
    description: "Layout at 375 px and desktop reads well (row density, header countdown, tab touch targets)"
    requirement: "D-07"
    verification: []
    human_judgment: true
    rationale: "Visual adequacy has no assertion; the plan assigns browser confirmation to Plan 05 Task 3's human-check, run by Claude"

duration: 7min
completed: 2026-10-04
status: complete
---

# Phase 230 Plan 03: Weekly Leaderboard Card on the Train Landing Summary

**One tabbed "This week" card (Points | Accuracy, remembered tab, server-driven countdown, viewer hints, hidden/guest rows, guest sign-up nudge) fed by GET /train/leaderboard through a typed client, a single TanStack query and a React-free lib, inserted after the streak card on every landing state that has one.**

## Performance

- **Duration:** 7 min
- **Started:** 2026-10-04T02:36:26Z
- **Completed:** 2026-10-04T02:43:16Z
- **Tasks:** 3 (1 tracer, 2 TDD)
- **Files modified:** 14 (5 created, 9 modified)

## Accomplishments

- The Train landing now shows the weekly competition: top rows with shared ranks, the viewer row highlighted (`data-viewer`, `aria-current`), a gap marker before the viewer's neighbours, and a one-line hint (pass target on Points, qualifier count or not-on-this-board line on Accuracy, enter hint when absent).
- The card is in the D-08 position in three branches (completed, fresh/resume/warmup, exhausted empty state), with `isGuest` threaded through a new `TrainEmptyBody` prop.
- The tab survives remounts via `flawchess_train_leaderboard_tab`; every storage failure and any foreign value falls back to Points. Umami sees only hand switches (`leaderboard-points` / `leaderboard-accuracy`); restore and re-tap send nothing.
- The countdown never does client week math: server `seconds_remaining` minus time since fetch, a 60 s tick, and one invalidation per `week_end` at zero so the board rolls over at the Monday reset.
- Backend contract mirrored exactly (`rank_without_session` is typed but unused here; Plan 05 reads it through the same hook's score-screen variant).

## Task Commits

1. **Task 1 (tracer): Points board and guest nudge end to end** - `53d5e0bf1` (feat)
2. **Task 2 RED: failing tests for tabs, hints, tab-switch** - `2a8436a1e` (test)
3. **Task 2 GREEN: tabs, remembered tab, viewer hints, tab-switch event** - `baedc7515` (feat)
4. **Task 3 RED: failing tests for countdown, rollover, private row labels** - `92fdf8e94` (test)
5. **Task 3 GREEN: countdown, rollover, row labels, dev-clock refresh** - `72517c88d` (feat)

**Plan metadata:** committed separately (docs: complete plan)

## Files Created/Modified

- `frontend/src/hooks/useTrainLeaderboard.ts` - one query, landing vs score-screen variant by `sessionId`
- `frontend/src/lib/trainLeaderboard.ts` - tab storage, countdown math/format, copy constants, `viewerHint`
- `frontend/src/components/train/TrainLeaderboardCard.tsx` - the card plus small module-level subcomponents and the countdown hook
- `frontend/src/types/train.ts`, `frontend/src/api/client.ts` - wire types and `trainApi.getLeaderboard`
- `frontend/src/components/train/TrainStartScreen.tsx` - card inserted in three branches, `TrainEmptyBody` gets `isGuest`
- `frontend/src/components/train/SignupAskActions.tsx` - `train-leaderboard` source
- `frontend/src/components/train/TrainDevClock.tsx` - invalidates the leaderboard query on offset change
- `frontend/src/lib/analytics.ts` - `LEADERBOARD_TAB_IDS`, widened `tab-switch` target (event name count stays 9)
- Tests: card, lib, analytics registry, TrainStartScreen (card stubbed, D-08 order tests), Train.solveLoop (`getLeaderboard` mock)

## Decisions Made

- Single `useQuery` with options derived from `sessionId`, not two hooks behind a condition (rules-of-hooks).
- No state set on mount for the countdown: the fetch time stands in for "now" until the first tick, which also satisfies the `set-state-in-effect` lint rule.
- Private row labelling reads `row.visibility`, so it is correct wherever the server places the viewer's would-be row.

## TDD Gate Compliance

Tasks 2 and 3 followed RED then GREEN: `test(230-03)` commits `2a8436a1e` and `92fdf8e94` precede `feat(230-03)` commits `baedc7515` and `72517c88d`. RED runs failed on missing implementation (`parseLeaderboardTab is not a function`, `remainingSeconds is not a function`, missing countdown testid, missing 'Hidden from others' / 'You (guest)' text, `LEADERBOARD_TAB_IDS` not iterable); a few characterization cases (for example the Anonymous name test) passed immediately against Task 1 code. `gsd_run check tdd-red-evidence` was not run (no evidence record persisted).

Mutation check (re-tap guard): with both the Radix `''` guard and the `next === tab` guard removed from `handleTabChange`, `re-tapping the active tab sends nothing` failed (`expected "vi.fn()" to not be called at all, but actually been called 1 times`, 1 failed / 19 passed); guards restored, 20 passed.

## Deviations from Plan

None - plan executed exactly as written.

The tracer feedback gate ran as automated-only verify (vitest on the five files, lint, build) with no checkpoint, per the end-of-phase default. Plan-level note: the `refetchOnMount: 'always'` acceptance grep matches the hook's docstring; the code line is a ternary (`isLanding ? 'always' : true`) because one query serves both variants.

## Issues Encountered

None.

## Known Stubs

None. The card never reads `rank_without_session` (Plan 05 does); that is scope, not a stub.

## Threat Flags

None. No new network surface beyond the planned GET; names render as React text only (T-230-08), the Umami target comes from a fixed Record (T-230-09), and the stored tab is validated against two literals (T-230-10). No `dangerouslySetInnerHTML`, no polling interval, no package installs.

## Verification Results

- `npx vitest run src/components/train src/lib src/pages/__tests__/Train.solveLoop.test.tsx`: 134 files, 2612 tests passed
- `npm run lint`: clean; `npm run build` (tsc -b + vite): clean; `npm run knip`: clean (one pre-existing configuration hint)
- Acceptance greps: 3 card insertions, `getLeaderboard` x1, `'train-leaderboard'` source present, no `text-xs`, component-only export, 0 occurrences of "skill" in card and lib, `COUNTDOWN_TICK_MS` used in the card, `TRAIN_LEADERBOARD_QUERY_KEY` x2 in TrainDevClock, no `refetchInterval`
- Analytics registry test "defines exactly 9 well-formed event names" passes unchanged

## Next Phase Readiness

- Plan 05 can call `useTrainLeaderboard({ sessionId })` on the score screen; the landing card never touches `rank_without_session`.
- Browser confirmation at 375 px and desktop remains for Plan 05 Task 3's human-check.

---
*Phase: 230-weekly-train-leaderboards*
*Completed: 2026-10-04*

## Self-Check: PASSED

All 5 created files exist on disk; commits 53d5e0bf1, 2a8436a1e, baedc7515, 92fdf8e94 and 72517c88d are present; acceptance criteria for all three tasks re-run green.
