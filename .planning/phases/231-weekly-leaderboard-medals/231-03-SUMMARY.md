---
phase: 231-weekly-leaderboard-medals
plan: 03
subsystem: frontend
tags: [frontend, react, train, leaderboard, medals]

requires:
  - phase: 231-weekly-leaderboard-medals
    provides: "Plan 01 wire shape: LeaderboardBoard.last_week and LeaderboardRow.medals on GET /train/leaderboard"
provides:
  - "Wire types MedalKind, LeaderboardMedals, LeaderboardPodiumEntry, LeaderboardLastWeek (mirror of app/schemas/train.py)"
  - "MEDAL_GOLD / MEDAL_SILVER / MEDAL_BRONZE / MEDAL_COLORS theme constants"
  - "MedalIcon, MedalTally, LastWeekPodium presentational components plus lib/trainMedals.ts copy helpers"
  - "TrainLeaderboardCardView, a prop-driven card with no fetching (the seam Plan 05's admin demo renders)"
affects: [231-04, 231-05]

actuals:
  tokens: 9500  # chars/4 over the realized diff (729 inserted lines, estimate)
  tasks: 2
  commits: 3
plan_head_before: a566a84e32460af4378f7bff77d06a302c035244
plan_head_after: 35dfeec384aae6aaee806a43a00cfeec19872a49

tech-stack:
  added: []
  patterns:
    - "Prop-driven *View component plus thin fetching container, so a demo renders production markup from fixtures"
    - "Medal colours only via theme.ts MEDAL_COLORS; MedalIcon is the single place that tints a lucide Medal"

key-files:
  created:
    - frontend/src/lib/trainMedals.ts
    - frontend/src/components/train/medals/MedalIcon.tsx
    - frontend/src/components/train/medals/MedalTally.tsx
    - frontend/src/components/train/medals/LastWeekPodium.tsx
    - frontend/src/components/train/medals/__tests__/MedalTally.test.tsx
    - frontend/src/components/train/medals/__tests__/LastWeekPodium.test.tsx
    - frontend/src/lib/__tests__/trainMedals.test.ts
  modified:
    - frontend/src/types/train.ts
    - frontend/src/lib/theme.ts
    - frontend/src/components/train/TrainLeaderboardCard.tsx
    - frontend/src/components/train/__tests__/TrainLeaderboardCard.test.tsx
    - frontend/src/components/train/__tests__/TrainScoreRankLines.test.tsx
    - frontend/src/lib/__tests__/trainLeaderboard.test.ts
    - frontend/src/pages/__tests__/Train.solveLoop.test.tsx

key-decisions:
  - "MedalTally items are inline-flex spans with a text-sm count; the whole tally is role=img with an aria-label such as '3 gold, 1 silver Points medals'"
  - "LeaderboardHint now returns a fragment: the existing hint paragraph unchanged, plus a separate last-week finish paragraph (mt-1 under a hint, mt-2 when alone)"
  - "Test-only exports (TrainLeaderboardCardView etc.) are tolerated by knip because vitest files are entries; Plan 05 adds the production consumer"

patterns-established:
  - "Fixtures that build LeaderboardBoard inline must carry last_week (runtime-only drift: test files are outside tsc, and LastWeekPodium dereferences it)"

requirements-completed: []

coverage:
  - id: D1
    description: "Each tab starts with a 'Last week:' podium of every server-sent entry (tinted Medal plus name, wraps), nothing when last_week is null or the podium is empty, names as React text only"
    verification:
      - kind: unit
        ref: "frontend/src/components/train/__tests__/TrainLeaderboardCard.test.tsx 'TrainLeaderboardCard last-week podium (Phase 231, D-07..D-09)'; medals/__tests__/LastWeekPodium.test.tsx"
        status: pass
    human_judgment: false
  - id: D2
    description: "Every row shows its owner's non-zero lifetime medals for that tab's board in gold/silver/bronze order inside the wrapping name block, with an aria-label; zero medals render nothing"
    verification:
      - kind: unit
        ref: "frontend/src/components/train/__tests__/TrainLeaderboardCard.test.tsx 'lifetime medal tally'; medals/__tests__/MedalTally.test.tsx; lib/__tests__/trainMedals.test.ts"
        status: pass
    human_judgment: false
  - id: D3
    description: "'You finished #N last week' appears as a separate line below this week's hint (or alone), only when viewer_final_rank is a number"
    verification:
      - kind: unit
        ref: "frontend/src/components/train/__tests__/TrainLeaderboardCard.test.tsx 'last-week finish line (Phase 231, D-03)'"
        status: pass
    human_judgment: false
  - id: D4
    description: "TrainLeaderboardCardView renders the whole card from props with no fetching; the container and its call sites are unchanged"
    verification:
      - kind: unit
        ref: "frontend/src/components/train/__tests__/TrainLeaderboardCard.test.tsx 'TrainLeaderboardCardView (Phase 231 seam)' (apiClient.get never called, no QueryClientProvider)"
        status: pass
    human_judgment: false
  - id: D5
    description: "Medal colour values and the 375 px wrap look right on the dark card"
    verification:
      - kind: manual
        ref: "UAT through the Plan 05 admin demo (colours tuned there)"
        status: unrun
    human_judgment: true

duration: 22min
completed: 2026-10-04
status: complete
---

# Phase 231 Plan 03: Medals on the live board Summary

**The live Train leaderboard now shows last week's podium at the top of each tab, a lifetime medal tally in every row's name block, and "You finished #N last week" under the hint, all rendered through a new prop-driven `TrainLeaderboardCardView` that the admin demo can reuse.**

## Performance

- **Duration:** about 22 min (start time not recorded, estimated from the Plan 01 closing commit)
- **Tasks:** 2 (1 tracer, 1 TDD)
- **Files:** 7 created, 7 modified

## Accomplishments

- Wire types mirrored by hand from `app/schemas/train.py`; `LeaderboardRow.medals` and `LeaderboardBoard.last_week` are required fields, so `tsc -b` flags any new fixture that omits them.
- `MEDAL_GOLD/SILVER/BRONZE` and `MEDAL_COLORS` in `theme.ts`; `MedalIcon` is the only place a lucide `Medal` is tinted (no colour literals in the components).
- `LastWeekPodium` (D-07/D-08/D-09), `MedalTally` and the `trainMedals.ts` helpers (`tallyEntries`, `tallyAriaLabel`, `lastWeekFinishCopy`, labels).
- `TrainLeaderboardCard` split: `TrainLeaderboardCardView` takes `data, isPending, isError, remaining, tab, onTabChange, isGuest` and does no fetching; `TrainLeaderboardCard` keeps `useTrainLeaderboard`, the countdown, tab state and the Umami `tab-switch`.
- Before the first deadline (`last_week: null`, zero medals) the card renders as in Phase 230; all pre-existing card tests pass unchanged apart from the fixture additions.

## Task Commits

1. **Task 1 (tracer): types, theme, podium, card seam, fixtures, podium tests** - `240df604a` (feat)
2. **Task 2 RED: tally, copy helper, finish-line and podium component tests** - `2fea258b0` (test)
3. **Task 2 GREEN: `MedalTally`, tally/finish helpers, hint-area finish line** - `35dfeec38` (feat)

## Verification

- `npx vitest run` on the four fixture files plus the new medals tests: green. Full suite `npm test -- --run`: 300 files, 4933 tests passed.
- `npm run lint`, `npm run build` (tsc -b + vite), `npm run knip`: clean (knip's only output is the pre-existing `.css` configuration hint).
- Acceptance greps: no `text-xs` and no `oklch` / hex literals in the three medal components; `train-leaderboard-last-week-finish` appears once in the card.
- Tracer gate: Task 1's verify (tests, lint, build, knip) passed before Task 2 began.
- Spec-less probe fallback skipped: the phase has no requirement IDs to probe (as recorded in Plan 01).

## TDD Gate Compliance

Task 1 is `type="tracer"` (not TDD): one feat commit with its tests. Task 2 follows RED then GREEN. RED `2fea258b0` failed as intended: 14 tests, namely the `tallyEntries` / `tallyAriaLabel` / `BOARD_LABEL` / `lastWeekFinishCopy` unit tests (not exported yet), the card tally and finish-line tests (testids absent), and `MedalTally.test.tsx` (module missing). The `LastWeekPodium` component tests passed at RED by design: that component shipped in Task 1 and the tests pin it. GREEN is `35dfeec38`; no refactor commit was needed. The `gsd_run check tdd-red-evidence` record was not produced (the failing assertions above are the evidence), the same as Plan 01.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Inline LeaderboardBoard literals in TrainLeaderboardCard.test.tsx lacked `last_week`**
- **Found during:** Task 1 verification (21 tests threw `Cannot read properties of undefined (reading 'podium')`)
- **Issue:** the plan listed only `EMPTY_BOARD` and `makeRow` as fixture drift, but about a dozen tests build board literals inline (`{ rows, viewer, pass_target }`), which reach `LastWeekPodium` with `last_week: undefined`.
- **Fix:** added `last_week: null` to each inline literal in that file. The component keeps the strict `| null` contract rather than tolerating `undefined`.
- **Files modified:** `frontend/src/components/train/__tests__/TrainLeaderboardCard.test.tsx`
- **Commit:** `240df604a`

**Total deviations:** 1 auto-fixed (test fixtures only). No production deviation.

## Auth Gates

None.

## Known Stubs

None. `row.medals` is real wire data; it is all-zero until Plan 02 fills the lifetime counts server-side (documented in Plan 01), and the tally then renders nothing.

## Threat Flags

None beyond the plan's threat model. T-231-14 is mitigated and tested: a podium name `<b>x</b>` renders as literal text with no `<b>` element. Row names were already React text children.

## Notes for Plans 04 and 05

- `TrainLeaderboardCardView` and `TrainLeaderboardCardViewProps` are exported; today their only importer is the test file (knip counts vitest files as entries). Plan 05's admin demo is the production consumer.
- `MedalIcon` is exported for the Plan 04 dialog.
- Medal colour values are first guesses, to be tuned in UAT via the admin demo (a 375 px wrap check belongs there too).

## Self-Check: PASSED

All created files exist on disk; commits `240df604a`, `2fea258b0`, `35dfeec38` exist; `commits: 3` measured from `git rev-list --count a566a84e3..HEAD` (the ledger base equals the dispatch base).
