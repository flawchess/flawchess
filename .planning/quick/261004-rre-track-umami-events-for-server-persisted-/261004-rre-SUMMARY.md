---
phase: quick-261004-rre
plan: 01
subsystem: frontend-analytics
tags: [umami, analytics, trackFeature, settings, reminders]
status: complete
requirements: ["QUICK-261004-rre"]
key-files:
  modified:
    - frontend/src/lib/analytics.ts
    - frontend/src/lib/__tests__/analytics.test.ts
    - frontend/src/components/train/TrainReminderResurfaceBanner.tsx
    - frontend/src/components/train/__tests__/TrainReminderResurfaceBanner.test.tsx
    - frontend/src/components/train/TrainReminderButton.tsx
    - frontend/src/components/train/__tests__/TrainReminderButton.test.tsx
    - frontend/src/components/train/TrainScheduleSettings.tsx
    - frontend/src/components/train/__tests__/TrainScheduleSettings.test.tsx
    - frontend/src/components/filters/ImportFilterCard.tsx
    - frontend/src/components/filters/__tests__/ImportFilterCard.test.tsx
    - frontend/src/components/settings/LeaderboardPrivacyCard.tsx
    - frontend/src/components/settings/__tests__/LeaderboardPrivacyCard.test.tsx
    - frontend/CLAUDE.md
commits: 4
plan_head_before: 2e752f228ed6db29fc9961251635eb36de5e8902
plan_head_after: 738cee6b1106775a10c69357b96643c327fad535
actuals:
  tokens: 45000
  tasks: 3
  commits: 4
---

# Phase quick-261004-rre Plan 01: Umami events for server-persisted settings Summary

Typed Umami events for settings rows that are overwritten in place (import filters, train schedule, reminder opt-in funnel, leaderboard privacy), all through the `trackFeature` registry with no new event names (FEATURE_EVENT_NAMES stays at 9).

## What was built

- **Registry (`analytics.ts`)**: `reminder-enable` action with a discriminated `ActionProps` (`source`: score-screen | resurface-banner | train-settings; `outcome`: derived from `DeviceSubscribeResult['status']` plus `install-instructions`); toggle targets `import-tc-*`, `train-day-*`, `train-reminder`; option targets `import-cap`, `train-puzzles-per-session`, `train-reminder-hour` with enumerated value arrays; `enumeratedValue()` narrowing helper (off-grid numbers send nothing).
- **Reminder funnel**: one `reminder-enable` event per press on the resurface banner, the score-screen "Remind me" (outcome from the subscribe result), the iOS "Get reminders" tap (`install-instructions`, counted even before settings load), and the Train-settings reminder switch.
- **Train schedule**: weekday chips (`toggleTarget` per chip, new state), puzzles slider (debounced `onValueCommit`, one event per burst), reminder switch (requested state), reminder hour.
- **Import filters**: TC toggles (new state) and backlog cap; the no-op last-TC click and the Radix empty re-tap send nothing.
- **Leaderboard privacy**: legacy `settings-change` event (`leaderboard-hidden`, on/off), same shape as SettingsPanel's sound switch.
- **frontend/CLAUDE.md**: skip rule now distinguishes row-creating writes (un-evented) from settings rows overwritten in place (evented).

## Verification

- Full gate green from `frontend/`: `npm run lint`, `npm run build` (tsc -b + vite), `npm test -- --run` (305 files, 5050 tests), `npm run knip`.
- Mutation proofs (call removed, tests went red, call restored): banner `reminder-enable` (5 failing), score-screen `handleClick` `reminder-enable` (2 failing), weekday toggle (2 failing), import-cap `option-change` (1 failing), leaderboard `settings-change` (2 failing).
- Drift guard test pins `TRAIN_PUZZLES_PER_SESSION_VALUES` to `PUZZLES_PER_SESSION_MIN/MAX/STEP` and `REMINDER_HOUR_VALUES` to `REMINDER_HOUR_OPTIONS`.

## Commits

- 733f50917 feat(analytics): register settings tracking targets and track reminder opt-in on the resurface banner
- 1f3cd0693 feat(analytics): track score-screen reminder opt-in and train schedule settings
- b280877d5 feat(analytics): track import filter and leaderboard privacy settings
- 738cee6b1 docs(frontend): event in-place settings rows, keep row-creating writes un-evented

## Deviations from Plan

None - plan executed as written. Two small implementation notes:
- `IMPORT_TC_TOGGLE_TARGETS` is module-private (only consumed in-file by `TOGGLE_TARGETS`) so knip stays clean; the `import-tc-${tc}` template literal narrows against the registry without a cast, so no Record fallback was needed.
- The CLAUDE.md edit is a plan deliverable and was committed as its own `docs(frontend)` commit; SUMMARY/STATE/PLAN were not committed.

## Known Stubs

None.

## Threat Flags

None. All new props are string-literal unions (T-rre-01); the legacy `settings-change` call sends only a constant id and on/off (T-rre-02); everything routes through `trackFeature`'s D-14 exclusion (T-rre-03).

## Self-Check: PASSED

All four commits found on `main`; all modified files present; working tree clean apart from the untracked quick-task directory.
