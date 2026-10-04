---
quick_id: 261004-dta
status: complete
commit: 13d2bc96e
---

# Quick 261004-dta: Train landing mobile cleanup — Summary

- `TrainHeader` wraps the host bubble in `train-landing-host`, which gets `max-sm:hidden`
  unless settings are loaded and `intro_seen_at` is null (Tank the Ox's intro). Desktop
  unchanged. Guest sign-up / import / install asks remain on the score screen.
- `TrainScheduleSettings` moved above `TrainLeaderboardCard` on the completed and
  start/resume landings (empty/exhausted landing has no schedule card, unchanged).
- Two new tests in `TrainStartScreen.test.tsx` (ordering, phone-hide gate).

Verified: `npm run lint`, `npm run build`, `npm run knip`, `vitest run src/components/train`
(558 passed). No browser UAT run.
