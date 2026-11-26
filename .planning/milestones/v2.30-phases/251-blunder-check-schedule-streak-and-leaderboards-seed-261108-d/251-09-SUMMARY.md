---
phase: 251-blunder-check-schedule-streak-and-leaderboards-seed-261108-d
plan: 09
subsystem: ui
tags: [train, settings, slider, react, draft, level-picker]

requires:
  - phase: 251-13
    provides: TrainStreakCard onTurnOn / launcher rows, analytics targets and value lists, optional blunder-check fields on the settings save
  - phase: 251-08
    provides: BlunderCheckLevel type use, level-step copy that promises a later change in settings
  - phase: 251-07
    provides: copy for How it works (removed Phase 249 start-screen text)
  - phase: 251-04
    provides: PUT /train/settings contract (0/0 rejected, absent blunder-check keys keep stored values)
provides:
  - "useTrainSettingsDraft: one shared settings draft with the debounced save and indicator"
  - "TrainModeSettings: collapsed per-mode rows (pitch, How it works, level picker, 0-to-Off size slider)"
  - "TrainScheduleSettings reduced to days and reminders, taking the shared draft"
  - "Turn on from the Today card, desktop two-column landing grid"
affects: [251-10]

plan_head_before: 2dbf5114a6601cc4d649eb9aa8401c5190ba5e85
plan_head_after: e0fdccb2fd8ee019889323459cdc4fea6a368b4e

actuals:
  tokens: 17000
  tasks: 2
  commits: 3

tech-stack:
  added: []
  patterns:
    - "One settings draft owned by the page component, passed to every writer (rows, schedule, Turn on); update() accepts a patch or a function of the latest draft"
    - "Draft refuses a patch that would set both session sizes to 0, on top of the slider floor"

key-files:
  created:
    - frontend/src/hooks/useTrainSettingsDraft.ts
    - frontend/src/components/train/TrainModeSettings.tsx
    - frontend/src/components/train/__tests__/TrainModeSettings.test.tsx
  modified:
    - frontend/src/components/train/TrainScheduleSettings.tsx
    - frontend/src/components/train/TrainStartScreen.tsx
    - frontend/src/components/train/useTrainReminderSlot.tsx
    - frontend/src/components/train/__tests__/TrainScheduleSettings.test.tsx
    - frontend/src/components/train/__tests__/TrainStartScreen.test.tsx

key-decisions:
  - "TrainStartScreen owns the single draft above its early returns, so a pending save survives the loading state and a tab switch (previously the schedule card's own mount)"
  - "update(patch) also takes a function of the latest draft, so the weekday XOR toggle stays race-free exactly as the old functional setDraft"
  - "onSaved is held in a ref inside the hook, so a parent re-render with a new callback identity cannot re-fire an in-flight save"
  - "Level change compares against the STORED level (not the displayed one): while none is stored, tapping Intermediate saves it, which is how a user confirms the default"
  - "The save indicator stays in the schedule card header (always open); mode rows do not duplicate it, since the testids are unique"
  - "Empty landing now also renders the settings column (rows + schedule) beside the card, not only when puzzles are off, so Blunder Check settings stay reachable"

requirements-completed: []

coverage:
  - id: D1
    description: "Per-mode collapsed rows with 0-to-Off sliders (puzzles 0..30, blunder check 0..18, step 3); a size edit and a days edit in one burst send one PUT"
    verification:
      - kind: unit
        ref: "frontend/src/components/train/__tests__/TrainModeSettings.test.tsx (tracer cases, Off at 0, slider grids drift guard)"
        status: pass
    human_judgment: false
  - id: D2
    description: "D-05 clamp: the last active mode's slider stops at 3 with the break hint; the UI never sends both sizes at 0"
    verification:
      - kind: unit
        ref: "frontend/src/components/train/__tests__/TrainModeSettings.test.tsx#Off at 0 and the never-both-off clamp"
        status: pass
    human_judgment: false
  - id: D3
    description: "How it works open until first_session_done (per mode), collapsed afterwards, user-toggleable"
    verification:
      - kind: unit
        ref: "frontend/src/components/train/__tests__/TrainModeSettings.test.tsx#How it works (D-10)"
        status: pass
    human_judgment: false
  - id: D4
    description: "Level picker only without rated games, stored level preselected (Intermediate when none), one option-change event per change"
    verification:
      - kind: unit
        ref: "frontend/src/components/train/__tests__/TrainModeSettings.test.tsx#level picker (D-17)"
        status: pass
    human_judgment: false
  - id: D5
    description: "Turn on in an off launcher row sets that mode to 6 through the shared draft (one PUT, rides with a days edit) and sends the action event"
    verification:
      - kind: unit
        ref: "frontend/src/components/train/__tests__/TrainStartScreen.test.tsx#mode settings rows, Turn on and the two-column layout"
        status: pass
    human_judgment: false
  - id: D6
    description: "Landing grid: one column on phones, Today card left and settings column right from lg"
    verification:
      - kind: unit
        ref: "TrainStartScreen.test.tsx#lays the landing out as a grid (class-level assertion only)"
        status: pass
    human_judgment: true
    rationale: "A class assertion cannot judge the real two-column look, row spacing or the Today card height against the settings column on a desktop and a phone"

duration: 75min
completed: 2026-11-19
status: complete
---

# Phase 251 Plan 09: Per-mode settings rows Summary

**Session size moves out of the schedule card into one collapsed settings row per mode (0-to-Off sliders, last-active-mode clamp with a break hint, auto-collapsing How it works, level picker for users without rated games), every settings writer including Turn on now edits one shared draft, and the landing is a two-column grid from lg.**

## Performance

- **Duration:** about 75 min
- **Tasks:** 2 (1 tracer, 1 TDD)
- **Files:** 8 (3 created, 5 modified)
- **Commits:** 3 measured from `plan_head_before`

## Accomplishments

- `useTrainSettingsDraft({ onSaved })`: seeded-once draft (weekday mask, both sizes, level, reminder fields), 600 ms debounced save that skips no-op drafts, saved/error indicator, `update(patch | fn)`, and a guard that drops a patch which would set both sizes to 0 (T-251-27 alongside the 422 and the DB CHECK).
- `TrainModeSettings`: two `Card` rows (`train-mode-settings-{puzzles|blunder-check}`, trigger `btn-train-mode-settings-*`), collapsed by default with an "N per session" / "Off" summary. Open state shows the pitch, How it works (`train-mode-how-*`, trigger `btn-train-mode-how-*`), the level picker for Blunder Check when `has_rated_games` is false (`btn-train-level-*`) and the slider (`filter-puzzles-per-session`, `filter-blunder-check-per-session`) with "Off" at 0 and the D-05 hint (`train-mode-break-hint-*`). Slider commits track through `useDebouncedTrackFeature`, the level change and Turn on send their registered events.
- `TrainScheduleSettings` keeps the days chips, next-session line, reminders and phone/QR block; the puzzles slider and the draft machinery moved out (`PuzzlesPerSessionControl` is gone).
- `TrainStartScreen` owns the one draft, passes it to both settings components, wires `onTurnOn` (sets the mode to `DEFAULT_MODE_SIZE` 6 and sends `train-mode-turn-on-*`) and renders `train-landing-grid` (`grid-cols-1`, `lg:grid-cols-2`, container widened to `lg:max-w-4xl`).

## Task Commits

1. **Task 1 (tracer): size sliders save through one shared draft** - `66a2ba063` (feat)
2. **Task 2 RED** - `3da15a912` (test); **GREEN** - `e0fdccb2f` (feat)

Tracer gate: the tracer's automated verify (the three test files, build) passed before its commit; auto-mode and `end-of-phase` rules then applied, so the verify was re-run as part of Task 2 and the full suite and expansion proceeded (`Tracer verified end-to-end — expanding`).

## TDD Gate Compliance

- **RED** (`3da15a912`): 14 new cases failed on the planned assertions: slider minimum `expected 3 to be +0` and `expected '3' to be '0'`, missing `train-mode-break-hint-*`, `btn-train-mode-how-*`, `btn-train-level-*`, `btn-train-launcher-turn-on-*` and `train-landing-grid` testids, the blunder-check burst tracking `'0'`. No collection, import or fixture faults. Two cases passed immediately and are regression guards (collapsed summary "N per session", Home on the last active slider never saves 0, the latter already held because of the tracer's min 3 and the draft guard). `gsd_run check tdd-red-evidence` was not run (plan type is `execute`; vitest output inspected directly).
- **GREEN** (`e0fdccb2f`): train and pages suites 58 files / 1253 tests, then the full suite 373 files / 6584 tests.
- No REFACTOR commit.

## Decisions Made

See key-decisions. The retry-day copy uses two named constants (`PUZZLE_CORRECT_RETRY_DAYS` 10, `PUZZLE_FAIL_RETRY_DAYS` 4) mirroring `app/services/train_scheduler.py`, since the frontend had none. The blunder-check maximum stays 18 (the plan's A2): I did not read 251-03-SUMMARY.md for a "compose too slow or short" note, so that check is left to the orchestrator.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Tests that reached into the removed slider updated**
- **Found during:** Task 1
- **Issue:** `TrainScheduleSettings.test.tsx` rendered the component standalone and asserted the puzzles slider and the old debounce export; `TrainStartScreen.test.tsx` imported `TRAIN_SETTINGS_SAVE_DEBOUNCE_MS` from the schedule file and its `useTrainSettings` mock lacked the blunder-check fields.
- **Fix:** Schedule tests render through a small harness that owns the draft (as `TrainStartScreen` does); the three slider tests and the slider-burst Umami test moved to `TrainModeSettings.test.tsx`; the debounce constants now come from the hook; the start-screen mock carries `blunder_check_per_session` / `blunder_check_level`. No assertion on days or reminders changed.
- **Files modified:** `TrainScheduleSettings.test.tsx`, `TrainStartScreen.test.tsx`
- **Committed in:** `66a2ba063`

**2. [Rule 2 - Missing critical] Hook-level both-off guard and `onSaved` ref**
- **Issue:** The plan clamps at the slider only; a Turn on or future writer could still build a 0/0 draft, and an `onSaved` callback with a changing identity re-ran the save effect while a save was in flight.
- **Fix:** `update` drops a patch yielding two zero sizes; `onSaved` is read through a ref.
- **Committed in:** `66a2ba063`

**3. [Judgment inside plan latitude] Empty landing shows the settings column**
- The empty state used to render the schedule card only when puzzles were off. It now always renders the grid with the Today card and the settings column, so Blunder Check settings and Turn on stay reachable; the empty-state body (`TrainEmptyBody`) follows below when puzzles are not off.

---

**Total deviations:** 2 auto-fixed (1 blocking, 1 missing critical), 1 judgment note. **Impact:** no scope creep; the existing days and reminder tests kept their assertions.

## Pre-existing tests changed

- `TrainScheduleSettings.test.tsx`: harness render, slider cases moved to `TrainModeSettings.test.tsx`, drift guard imports the slider constants from `TrainModeSettings` (it now sees `PUZZLES_PER_SESSION_MIN = 0` so the `'0'` prepend branch is dormant).
- `TrainStartScreen.test.tsx`: debounce import path, settings mock fields (see deviation 1).

## Issues Encountered

None. From `frontend/`: `npm run lint`, `npm run build` (`tsc -b` + vite), `npx vitest run` (373 files, 6584 tests) and `npm run knip` (exit 0, two pre-existing configuration hints) pass. `tsconfig.app.json` excludes test files, so the build does not type-check them.

## Known Stubs

None.

## Threat Flags

None. T-251-26: one draft instance, tests assert a size edit plus a days edit and a Turn on plus a days edit each produce one PUT carrying both. T-251-27: slider floor, draft guard, plus the server 422 and DB CHECK. T-251-SC: no packages installed.

## Next Phase Readiness

Plan 251-10 is unaffected. The level picker fulfils the 251-08 copy promise ("can be changed later in the Blunder Check settings"). A visual check of the two-column desktop layout and the row spacing on a phone is left to UAT.

## Self-Check: PASSED

- Created files exist: `useTrainSettingsDraft.ts`, `TrainModeSettings.tsx`, `TrainModeSettings.test.tsx`, this SUMMARY.
- Commits `66a2ba063`, `3da15a912`, `e0fdccb2f` are ancestors of HEAD.
- Acceptance greps: `export function useTrainSettingsDraft` in the hook (1), `useTrainSettingsDraft` in `TrainStartScreen.tsx` (single owner), `filter-blunder-check-per-session` in `TrainModeSettings.tsx` (1), `PuzzlesPerSessionControl` in `TrainScheduleSettings.tsx` (0), `train-landing-grid` in `TrainStartScreen.tsx` (2).

---
*Phase: 251-blunder-check-schedule-streak-and-leaderboards-seed-261108-d*
*Completed: 2026-11-19*
