---
phase: 251-blunder-check-schedule-streak-and-leaderboards-seed-261108-d
plan: 08
subsystem: ui
tags: [train, blunder-check, level-step, launch-notice, react]

requires:
  - phase: 251-07
    provides: BlunderCheckTab drill host (compose on mount, onExit)
  - phase: 251-13
    provides: TrainStreakCard launcher rows, analytics targets, optional blunderCheckLevel on the settings save
  - phase: 251-06
    provides: modes.blunder_check.needs_level, blunder_check_notice, POST /train/blunder-check-notice/dismiss
provides:
  - "BlunderCheckLevelStep: one-time Beginner / Intermediate / Advanced screen (labels only)"
  - "Host level gate: waits for progress, shows the step while needs_level, saves the level, composes after the save"
  - "Launch notice on the streak card with optimistic dismissal"
  - "trainApi.dismissBlunderCheckNotice, useDismissBlunderCheckNotice, LAUNCH_NOTICE_TINT_CLASS"
affects: [251-09, 251-10]

plan_head_before: ab521061d24f2330e240e64781f05c1748626b3f
plan_head_after: 7b153172c4342abb2e138b3cf800a05edf75cfdb

actuals:
  tokens: 9300
  tasks: 2
  commits: 3

tech-stack:
  added: []
  patterns:
    - "Host-side gate hook (useLevelGate): progress + settings reads, mutate-level onSuccess sets a local flag that releases the compose effect"
    - "Optimistic mutation on the shared progress query key (setQueryData on mutate, invalidate on settle)"

key-files:
  created:
    - frontend/src/components/train/blunder-check/BlunderCheckLevelStep.tsx
    - frontend/src/components/train/blunder-check/__tests__/BlunderCheckLevelStep.test.tsx
  modified:
    - frontend/src/components/train/blunder-check/BlunderCheckTab.tsx
    - frontend/src/components/train/blunder-check/__tests__/BlunderCheckTab.test.tsx
    - frontend/src/components/train/TrainStreakCard.tsx
    - frontend/src/components/train/__tests__/TrainStreakCard.test.tsx
    - frontend/src/api/client.ts
    - frontend/src/hooks/useTrainProgress.ts
    - frontend/src/lib/theme.ts

key-decisions:
  - "The compose after a level save runs from the existing compose-on-mount effect, released by a levelSaved flag set in the save's onSuccess; one compose path, the startInFlight guard stays the only de-dup"
  - "The option-change event is sent inside the save's onSuccess (not on the tap), so a failed save that is retried records one event, matching 'a settings row overwritten in place' semantics"
  - "A failed progress load in the host shows the compose LoadError with Back instead of composing blind, since composing could skip a needed level step"
  - "The level step's Start is disabled while the settings GET is pending, because the PUT is a full replace of the schedule fields"
  - "The launch notice is a brand-brown tint (LAUNCH_NOTICE_TINT_CLASS in theme.ts), not the amber warning tone"

requirements-completed: []

coverage:
  - id: D1
    description: "A no-rated-games, no-level user sees one level step on first Start; the level is saved before the first compose; later starts go straight to the drill"
    verification:
      - kind: unit
        ref: "frontend/src/components/train/blunder-check/__tests__/BlunderCheckTab.test.tsx (level step (D-20), no level step when none is needed)"
        status: pass
      - kind: unit
        ref: "frontend/src/components/train/blunder-check/__tests__/BlunderCheckLevelStep.test.tsx (5 tests)"
        status: pass
    human_judgment: false
  - id: D2
    description: "Level picker shows labels only, never Elo numbers"
    verification:
      - kind: unit
        ref: "BlunderCheckLevelStep.test.tsx#shows the three level labels and no Elo numbers (D-17)"
        status: pass
    human_judgment: false
  - id: D3
    description: "Streak card shows the D-21 notice while the server flag is true, hides it on dismiss (optimistic), tells the server, refreshes progress; absent when the flag is false"
    verification:
      - kind: unit
        ref: "frontend/src/components/train/__tests__/TrainStreakCard.test.tsx (blunder-check launch notice, 4 tests)"
        status: pass
    human_judgment: false
  - id: D4
    description: "Visual look and spacing of the level step and the notice on desktop and phone"
    verification: []
    human_judgment: true
    rationale: "No test judges layout, the tint against the dark theme, or the dismiss target size"

duration: 45min
completed: 2026-11-18
status: complete
---

# Phase 251 Plan 08: Level step and launch notice Summary

**Blunder check now asks a no-rated-games user (guests included) for a Beginner / Intermediate / Advanced level once, saves it through PUT /train/settings, and only then composes the first session; the streak card shows the D-21 "streak now includes blunder check" notice with an optimistic dismiss.**

## Accomplishments

- `BlunderCheckLevelStep`: three `ToggleChipButton`s (`aria-pressed`, testids `btn-blunder-check-level-beginner|intermediate|advanced`), Intermediate preselected, the plan's copy, primary Start (`btn-blunder-check-level-start`, disabled while saving, also the retry after an inline error) and a secondary Back (`btn-blunder-check-level-back`). No digits anywhere (asserted).
- `BlunderCheckTab`: new `useLevelGate` hook reads `useTrainProgress()` and `useTrainSettings()`. The compose-on-mount effect now waits for the progress response and for no pending level. While `needs_level` is true and the level is unsaved the idle phase renders the level step; its confirm calls `unlockAudio()` in the tap, saves the stored schedule values plus `blunderCheckLevel` through `useTrainSettings().save`, and on success sends `option-change` `train-blunder-check-level` and releases the compose. A failed save shows the inline error and does not compose; a failed progress load shows the compose LoadError with Back.
- `TrainStreakCard`: `BlunderCheckNotice` (`train-blunder-check-notice`, D-21 copy, `text-sm`, `LAUNCH_NOTICE_TINT_CLASS`) rendered full width above the launcher rows while `blunder_check_notice` is true; ghost icon Dismiss (`aria-label="Dismiss"`, `btn-train-blunder-check-notice-dismiss`) sends the `train-blunder-check-notice-dismiss` action event and fires `useDismissBlunderCheckNotice`.
- `trainApi.dismissBlunderCheckNotice` (POST, 204) and `useDismissBlunderCheckNotice` (sets the cached `blunder_check_notice` to false on mutate, invalidates the progress query on settle; no Sentry call, the global MutationCache captures errors).

## Task Commits

1. **Task 1 (tracer): level step, host gate** - `bad638ab9` (feat)
2. **Task 2 RED** - `5951a20a2` (test); **GREEN** - `7b153172c` (feat)

Tracer gate: the tracer's automated verify (the two test files, build) passed before the commit and again inside the full suite and final build, so expansion proceeded.

## TDD Gate Compliance

- **RED** (`5951a20a2`): `shows the D-21 sentence above the launcher rows...` failed with `Unable to find an element by: [data-testid="train-blunder-check-notice"]`; the dismiss and invalidate tests failed with `Unable to find ... btn-train-blunder-check-notice-dismiss`. These are the planned assertions, no collection or fixture faults. The "flag false shows no notice" test passed immediately (regression guard for the absent case). `gsd_run check tdd-red-evidence` was not run (plan type is `execute`; vitest output inspected directly). The Task 1 tests were also run red first (6 new host tests failed on the planned assertions, the level-step file failed on its missing import), then committed together with the implementation as the tracer.
- **GREEN** (`7b153172c`): TrainStreakCard 45 tests pass; full suite 372 files / 6564 tests.
- No REFACTOR commit.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] D-19 "no analytics import" scan updated**
- **Found during:** Task 1
- **Issue:** The plan has the host (`BlunderCheckTab.tsx`) send `trackFeature`, which the Phase 249 D-19 scan in `BlunderCheckTab.test.tsx` forbids for every blunder-check source except the end screen (plan 251-05 already carved out that one). The host test itself also now mocks the analytics module, which the same directory scan would flag.
- **Fix:** The scan keeps its rule and the Umami-attribute check, and exempts `BlunderCheckTab.tsx` (alongside the end screen) plus files under `__tests__`.
- **Files modified:** `frontend/src/components/train/blunder-check/__tests__/BlunderCheckTab.test.tsx`
- **Commit:** `bad638ab9`

**2. [Rule 2 - Missing critical] Host tests now mock the progress and settings endpoints**
- **Issue:** The host reads `GET /train/progress` and `GET /train/settings` before composing, so every pre-existing host test needed a resolved progress (needs_level false) and settings response or compose would never start.
- **Fix:** Default `getProgress` / `getSettings` / `updateSettings` mocks in `beforeEach`; no existing assertion changed.
- **Commit:** `bad638ab9`

**3. [Judgment inside plan latitude] Event sent on save success, compose released by effect**
- The plan says to send the event from the confirm handler and to compose in the save's onSuccess. The event is sent inside the save's onSuccess (a failed-then-retried save records one event), and the compose is triggered by the existing mount effect once onSuccess sets `levelSaved`, keeping a single compose path guarded by `startInFlight`. Observable order (PUT before compose) is asserted.

**Total deviations:** 2 auto-fixed (1 blocking, 1 missing critical), 1 judgment note. **Impact:** no scope creep.

## Issues Encountered

None. From `frontend/`: `npm run lint`, `npm run build` (`tsc -b` + vite), `npx vitest run` (372 files, 6564 tests) and `npm run knip` (exit 0, two pre-existing configuration hints) pass. `tsconfig.app.json` excludes test files, so the build does not type-check them.

## Known Stubs

None.

## Threat Flags

None. T-251-24: the client only ever sends one of the three `BlunderCheckLevel` literals; server validation is plan 04. T-251-25: dismissal is optimistic and the mutation is a single idempotent call. T-251-SC: no packages installed.

## Next Phase Readiness

Plans 251-09 and 251-10 are unaffected. Note for 251-09: the level can be changed later "in the Blunder Check settings" (the level step's own copy promises it), so the settings surface should expose the level picker.

## Self-Check: PASSED

- Created files exist: `BlunderCheckLevelStep.tsx`, `BlunderCheckLevelStep.test.tsx`, this SUMMARY.
- Commits `bad638ab9`, `5951a20a2`, `7b153172c` are ancestors of HEAD.
- Acceptance greps: `export function BlunderCheckLevelStep` in `BlunderCheckLevelStep.tsx` (1), the D-21 copy in `TrainStreakCard.tsx` (1), `dismissBlunderCheckNotice` in `client.ts` (1).

---
*Phase: 251-blunder-check-schedule-streak-and-leaderboards-seed-261108-d*
*Completed: 2026-11-18*
