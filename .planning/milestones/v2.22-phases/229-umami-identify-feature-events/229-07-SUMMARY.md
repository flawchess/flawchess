---
phase: 229-umami-identify-feature-events
plan: 07
subsystem: analytics
status: complete
tags: [frontend, analytics, umami, train, bots]

requires: [229-02]
provides:
  - "Train feature events: action train-solution, train-explore-exit, analyze, reminder-banner-dismiss; panel-open train-schedule"
  - "Bots feature events: option-change bot-tc, bot-color, play-style; action persona-open, custom-setup-open"
affects: [229-08]

actuals:
  tokens: 14000
  tasks: 2
  commits: 2
plan_head_before: 72a7089c36a24c42712f83bd125145c925284fb0
plan_head_after: ce10c6d2f344989fa03a8f614ea7f7ca4d5dd3c4

tech-stack:
  added: []
  patterns:
    - "Tracking fires inside the click handler after the existing behavior, guarded so re-picking the active choice sends nothing"

key-files:
  created: []
  modified:
    - frontend/src/components/train/TrainSolveScreen.tsx
    - frontend/src/components/train/TrainReveal.tsx
    - frontend/src/components/train/TrainScheduleSettings.tsx
    - frontend/src/components/train/TrainReminderResurfaceBanner.tsx
    - frontend/src/components/train/__tests__/TrainReveal.test.tsx
    - frontend/src/components/bots/SetupScreen.tsx
    - frontend/src/components/bots/PersonaDetailSurface.tsx
    - frontend/src/components/bots/PlayStyleControl.tsx
    - frontend/src/components/bots/PersonaCard.tsx
    - frontend/src/components/bots/PersonaGrid.tsx
    - frontend/src/components/bots/__tests__/PlayStyleControl.test.tsx
    - frontend/src/components/bots/__tests__/SetupScreen.test.tsx
    - frontend/src/components/bots/__tests__/PersonaCard.test.tsx

key-decisions:
  - "train-solve-retry left un-evented: retrySolve re-submits the solve payload to the backend (frontend/src/hooks/useTrainSession.ts:325-330, void solvePuzzle(lastSolvePayload)), so it is DB-known"
  - "reminder-banner-dismiss tracked: dismiss() only writes a per-device localStorage flag (frontend/src/hooks/useReminderResurface.ts:119-122), not a backend write"
  - "analyze tracked once, at the top of handleAnalyzeClick, because handleAnalyzeFromReveal calls through to it; tracking in both would double-count the reveal Analyze button"

requirements-completed: [D-03, D-04, D-12]

coverage:
  - id: C1
    description: "Train Solution, exploration exit, both Analyze buttons, schedule expand and reminder-banner dismiss send typed events; guesses, next, retry, session start stay un-evented"
    verification:
      - kind: unit
        ref: "frontend/src/components/train/__tests__/TrainReveal.test.tsx#TrainReveal feature events (Phase 229)"
        status: pass
    human_judgment: false
  - id: C2
    description: "Bot setup TC/color/play-style choices send option-change; re-picking the active choice sends nothing"
    verification:
      - kind: unit
        ref: "frontend/src/components/bots/__tests__/PlayStyleControl.test.tsx#PlayStyleControl feature events (Phase 229)"
        status: pass
      - kind: unit
        ref: "frontend/src/components/bots/__tests__/SetupScreen.test.tsx#SetupScreen feature events (Phase 229)"
        status: pass
    human_judgment: false
  - id: C3
    description: "persona-open carries no persona id or name"
    verification:
      - kind: unit
        ref: "frontend/src/components/bots/__tests__/PersonaCard.test.tsx#PersonaCard feature events (Phase 229)"
        status: pass
    human_judgment: false

duration: 12min
completed: 2026-10-03
---

# Phase 229 Plan 07: Train and Bots setup feature events Summary

Train reveal/exploration/analyze/schedule/banner actions and the Bots setup choices (TC, color, play style) plus persona and custom-setup opens now report typed Umami events; DB-known actions stay un-evented.

## What was built

- `TrainSolveScreen.tsx`: `btn-train-solution` fires `action train-solution` after `onShowSolution()`; `handleAnalyzeClick` fires `action analyze` (covers both Analyze buttons).
- `TrainReveal.tsx`: `btn-train-exploration-close` fires `action train-explore-exit` after `onExit?.()`.
- `TrainScheduleSettings.tsx`: the card toggle fires `panel-open train-schedule` only when the card is closed (expanding).
- `TrainReminderResurfaceBanner.tsx`: "Not now" fires `action reminder-banner-dismiss` after `dismiss()`.
- `SetupScreen.tsx` / `PersonaDetailSurface.tsx`: TC preset and color buttons fire `option-change` (`bot-tc` with the preset label, `bot-color` with white/black/random) unless the choice is already active.
- `PlayStyleControl.tsx`: preset buttons fire `option-change play-style` (human/light/deep) unless already active; one component serves both setup surfaces.
- `PersonaCard.tsx` fires `action persona-open` (no id/name); `PersonaGrid.tsx` Custom button fires `action custom-setup-open`.

## Tracked vs left out (DB-known evidence)

| Action | Decision | Evidence |
|---|---|---|
| train-solve-retry | NOT tracked (DB-known) | `useTrainSession.ts:325-330` `retrySolve` re-submits the identical payload via `solvePuzzle` (API mutation). A test asserts Retry sends nothing. |
| reminder-banner-dismiss | Tracked | `useReminderResurface.ts:119-122` `dismiss()` writes a localStorage flag only, no backend call. |
| guesses, Next, session start/resume, train_settings, push subscribe, bot game start/result | un-evented (D-03 DB-known) | untouched |

## Verification

- `npx vitest run src/components/train/ src/components/bots/ src/pages`: 46 files, 868 tests pass.
- `npm run lint` clean; `npm run build` (tsc -b + vite) clean.
- Mutation checks: removing the `train-explore-exit` call failed the new TrainReveal test; replacing the `activePreset !== preset.key` guard with `true` failed "re-picking the already-active preset sends nothing". Both reverted.
- No suite touched here mocks `@/lib/analytics` (the three mocking suites are SettingsPanel, EngineReadyGate, ImportAskActions; none render these components), so no factory needed the partial-real form.

## Deviations from Plan

**1. [Rule 1 - Bug] `target: 'analyze'` tracked once, not twice**
- **Found during:** Task 1
- **Issue:** The plan asked for `trackFeature('action', { target: 'analyze' })` at the top of both `handleAnalyzeFromReveal` and `handleAnalyzeClick`. `handleAnalyzeFromReveal` calls `handleAnalyzeClick`, so the reveal Analyze button would send two events per click.
- **Fix:** One call at the top of `handleAnalyzeClick` (before its cache-state early return). The acceptance grep `grep -c "target: 'analyze'"` therefore prints 1 instead of 2; both Analyze buttons (VerdictActions and TrainReveal) still count exactly once.
- **Files modified:** frontend/src/components/train/TrainSolveScreen.tsx
- **Commit:** 114a0777b

**2. [Rule 3 - Blocking] `onExit?.()` in TrainReveal**
- `onExit` is optional in the exploration subcomponent, so `onExit()` failed `tsc -b` (TS2722). Used optional call.

**3. Extra tests (scope: coverage of acceptance prohibitions)**
- Added bot-tc/bot-color cases to `SetupScreen.test.tsx` and a persona-open (no id/name) case to `PersonaCard.test.tsx`, not in the plan's files list, because the plan's "MUST NOT send persona ids" prohibition is marked `verification: test`.

`npm ci` was run once in `frontend/` of the fresh worktree (lockfile install, no package added).

## Known Stubs

None.

## Threat Flags

None. Targets are fixed literals from the registry (T-229-19); retry and banner dismissal were traced to their handlers (T-229-20).

## Self-Check: PASSED

- Commits `114a0777b` and `ce10c6d2f` exist on the worktree branch.
- All files listed in key-files exist.
