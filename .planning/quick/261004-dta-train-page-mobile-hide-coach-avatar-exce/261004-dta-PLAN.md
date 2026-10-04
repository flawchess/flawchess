---
quick_id: 261004-dta
mode: quick
files_modified:
  - frontend/src/components/train/TrainStartScreen.tsx
  - frontend/src/components/train/__tests__/TrainStartScreen.test.tsx
---

# Quick 261004-dta: Train landing mobile cleanup

Executed inline (tiny frontend change, no subagents).

## Task 1: Hide the landing host bubble on phones, except Tank's intro

- `TrainHeader` (TrainStartScreen.tsx): wrap the bubble in a `max-sm:hidden` container
  unless the intro has not been completed yet (`settings.intro_seen_at == null` with
  settings loaded), in which case Tank the Ox introduces Train on every viewport.
- Rationale (user): the avatar + bubble eats too much vertical space on a phone; the
  install/sign-up/import asks are already on the session score screen.
- Desktop unchanged.

## Task 2: Schedule card above the leaderboard

- Completed and fresh/resume/warmup landings: render `TrainScheduleSettings` directly
  after `TrainStreakCard`, before `TrainLeaderboardCard` and `TrainStatsCard`.
- Update the module docstring (Phase 230 D-08 ordering note).

## Verify

- `npm run lint && npm run build && npm test -- --run src/components/train`
