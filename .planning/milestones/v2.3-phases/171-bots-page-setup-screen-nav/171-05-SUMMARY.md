---
phase: 171-bots-page-setup-screen-nav
plan: 05
subsystem: ui
tags: [react, typescript, radix-slider, localStorage, vitest]

# Dependency graph
requires:
  - phase: 171-04
    provides: TIME_CONTROL_PRESETS, playStyle.ts, botSetupSettings.ts (readSetupSettings/writeSetupSettings/resolveDefaultBotElo/DEFAULT_BOT_SETUP_SETTINGS), PlayStyleControl.tsx
  - phase: 171-02
    provides: lichess_blitz_equivalent_rating profile field, the normalized rating this screen seeds its ELO default from
provides:
  - "SetupScreen component + SetupScreenProps + useSetupScreenState local hook — the pre-game setup form for the Bots page"
  - "buildSettings() — the single place that resolves a TC display label to {baseSeconds, incrementSeconds} and an unresolved 'random' color preference to a concrete 'white'/'black', producing a fully-resolved BotGameSettings"
affects: [171-06-nav-and-newgame-rewire]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Data-shaping-in-a-local-hook: useSetupScreenState holds all state + buildSettings logic, keeping SetupScreen's own JSX purely declarative"
    - "Resolve-at-the-boundary: an ambiguous/unresolved persisted preference ('random') is only ever resolved to a concrete value at the exact call site that hands off to a consumer (onStart), never earlier and never persisted in its resolved form"

key-files:
  created:
    - frontend/src/components/bots/SetupScreen.tsx
    - frontend/src/components/bots/__tests__/SetupScreen.test.tsx
  modified: []

key-decisions:
  - "buildSettings() resolves 'random' via Math.random() < 0.5 at Start time, before onStart fires — useBotGame never observes 'random', only a concrete MoverColor (D-12)"
  - "Start persists the UNRESOLVED colorPreference (not the resolved draw) via writeSetupSettings, so a returning Random user stays on Random rather than getting pinned to whichever side a prior game's coin flip drew"
  - "EloSelector reused completely unmodified — the setup screen renders its own 'Bot strength (ELO)' label + InfoPopover (testid setup-elo-info, D-05 copy) alongside EloSelector's own smaller 'ELO' caption, accepting the minor duplication per UI-SPEC's resolved discretion rather than forking or editing the shared /analysis component"
  - "Color and TC chip grids reuse PresetRangeFilter's exact chip visual language (h-11 sm:h-7, aria-pressed, active/inactive class pair) inline rather than importing PresetRangeFilter itself, since that component's two-thumb-only prop contract doesn't fit a chip-only, no-slider color row"

patterns-established:
  - "useSetupScreenState is the reference pattern for a props-in/settings-out setup form: lazy useState seeded once from persisted storage, a memoized buildSettings() as the single resolution boundary"

requirements-completed: []

coverage:
  - id: D1
    description: "SetupScreen renders four controls in order (ELO, Play style, Play as, Time control) plus a Start button; ELO defaults from resolveDefaultBotElo(normalizedRating) or 1500 when null; the ELO ladder is the full 600-2600 MAIA_ELO_LADDER"
    requirement: "PLAY-02"
    verification:
      - kind: unit
        ref: "frontend/src/components/bots/__tests__/SetupScreen.test.tsx#SetupScreen — defaults (V-13 setup half)"
        status: pass
    human_judgment: false
  - id: D2
    description: "Start emits a fully-resolved BotGameSettings: TC display label converted to {baseSeconds, incrementSeconds} with no display-label string reaching the emitted object; 'random' color preference resolved to a concrete 'white'/'black' before onStart fires"
    requirement: "PLAY-02"
    verification:
      - kind: unit
        ref: "frontend/src/components/bots/__tests__/SetupScreen.test.tsx#SetupScreen — Start emits a fully-resolved BotGameSettings (V-07)"
        status: pass
      - kind: unit
        ref: "frontend/src/components/bots/__tests__/SetupScreen.test.tsx#SetupScreen — Random resolves to a concrete color at Start (D-12, V-08)"
        status: pass
    human_judgment: false
  - id: D3
    description: "Start persists the chosen settings (including the UNRESOLVED colorPreference) to the D-10 owner-scoped key; a returning user with the same ownerKey prefills every control on remount, and a saved ELO wins over the profile-derived default"
    requirement: "PLAY-02"
    verification:
      - kind: unit
        ref: "frontend/src/components/bots/__tests__/SetupScreen.test.tsx#SetupScreen — prefill from persisted settings"
        status: pass
      - kind: unit
        ref: "frontend/src/components/bots/__tests__/SetupScreen.test.tsx#SetupScreen — D-10 round-trip prefill"
        status: pass
    human_judgment: false
  - id: D4
    description: "The ELO info popover (setup-elo-info) renders the D-05 bot-specific honesty caveat; EloSelector.tsx is reused unmodified (no edits, verified via git diff --exit-code)"
    requirement: "PLAY-02"
    verification:
      - kind: unit
        ref: "frontend/src/components/bots/__tests__/SetupScreen.test.tsx#SetupScreen — ELO info popover (D-05)"
        status: pass
      - kind: other
        ref: "git diff --exit-code -- frontend/src/components/analysis/EloSelector.tsx"
        status: pass
    human_judgment: false

duration: 12min
completed: 2026-07-14
status: complete
---

# Phase 171 Plan 05: SetupScreen Composition Summary

**Pre-game setup screen composing ELO/play-style/color/time-control controls into a single form that resolves a TC display label to seconds and an unresolved 'random' color preference to a concrete side, both exactly at Start.**

## Performance

- **Duration:** 12 min
- **Tasks:** 2
- **Files modified:** 2 (both new)

## Accomplishments
- `SetupScreen.tsx` — a pure, self-contained component taking `ownerKey`/`normalizedRating`/`onStart` as props (no `useUserProfile()` call inside, so it's trivially testable without a QueryClient). Renders ELO (reusing `EloSelector` unmodified, full `MAIA_ELO_LADDER`), `PlayStyleControl`, a 3-chip color row, and a 3-group (Blitz/Rapid/Classical) TC chip grid, then a `Start` button.
- `useSetupScreenState` local hook holds all data shaping: lazy `useState` seeded once from `readSetupSettings(ownerKey) ?? { ...DEFAULT_BOT_SETUP_SETTINGS, botElo: resolveDefaultBotElo(normalizedRating) }`, and a memoized `buildSettings()` that is the single resolution boundary — TC label → `{baseSeconds, incrementSeconds}` via `findPresetByLabel`, and `'random'` → a concrete `'white'`/`'black'` via a coin flip, both resolved before `onStart` fires (D-12).
- Start's handler persists the UNRESOLVED `colorPreference` (the preference, not the draw) via `writeSetupSettings`, then calls `onStart(buildSettings())` — so a returning Random user stays on Random.
- A `BOT-03`-tagged code comment at `defaultElo`'s derivation records that the profile-derived ELO is a UI-DEFAULT-ONLY value, never fed into the bot's own move selection, and that D-06's harness-table rung correction is deliberately NOT applied here.
- 12 RTL tests cover V-13 (default resolution + full ladder bounds), prefill-overrides-default, V-07 (TC-to-seconds conversion with no display-label leak, Human preset → blend 0), V-08 (both `Math.random`-stubbed branches plus an unstubbed "never `'random'`" assertion), D-10 round-trip (unmount/remount prefill including Random staying Random), and the D-05 ELO info popover copy.

## Task Commits

Each task was committed atomically:

1. **Task 1: SetupScreen.tsx — compose ELO, play style, color, and TC; resolve and emit BotGameSettings** - `5502e3ce` (feat)
2. **Task 2: SetupScreen.test.tsx (V-07, V-08, V-09 integration, V-13 setup half)** - `022b9f38` (test)

_Note: no TDD RED/GREEN split was applied per-task since both files already existed on disk as untracked leftovers from an aborted earlier attempt (documented in the executor's briefing); they were read, verified against this plan's spec line-by-line, verified green via `tsc -b`/`vitest`/`lint`/`knip`, then committed as-is since they matched the spec exactly with no changes needed._

## Files Created/Modified
- `frontend/src/components/bots/SetupScreen.tsx` - `SetupScreen` component + `SetupScreenProps` + `useSetupScreenState` hook + `TcBucketGroup` sub-component
- `frontend/src/components/bots/__tests__/SetupScreen.test.tsx` - 12 tests covering V-07/V-08/V-13/D-10/D-05

## Decisions Made
- `buildSettings()` resolves `'random'` at Start time via `Math.random() < 0.5`, strictly before `onStart` is invoked — `useBotGame` structurally never observes `'random'` (its `userColor: MoverColor` typing excludes it)
- Start persists the raw `colorPreference` (not the resolved color), so Random stays Random across sessions rather than collapsing to whichever side a prior coin flip landed on
- `EloSelector.tsx` left completely untouched; the setup screen renders its own "Bot strength (ELO)" label + D-05 `InfoPopover` alongside `EloSelector`'s own smaller "ELO" caption — the minor duplication is UI-SPEC's resolved discretion, not a scope gap
- Color and TC chip markup inlined (matching `PresetRangeFilter`'s classes) rather than importing that component, since its two-thumb-only slider contract doesn't fit a chip-only color row or a 3-group TC grid

## Deviations from Plan

None - both target files were pre-existing untracked leftovers from an aborted earlier execution attempt of this same plan (per the executor's briefing). They were read in full, cross-checked line-by-line against every `<behavior>` bullet, `<action>` instruction, and `<acceptance_criteria>` item in `171-05-PLAN.md`, and found to match the spec exactly (correct data shaping, correct D-12 resolve-before-onStart ordering, correct D-10 unresolved-preference persistence, no guest caveat, no engine prewarm, no `EloSelector.tsx` edits, `data-testid` on every interactive element, semantic `<button>`s throughout). No corrections were needed before committing.

## Issues Encountered

None. All verification commands passed cleanly on the first run: `npx tsc -b` (0 errors), `npx vitest run src/components/bots/__tests__/SetupScreen.test.tsx` (12/12 passed), `npm run lint` (0 errors — 3 pre-existing unrelated warnings in `coverage/*.js` build artifacts), `npm run knip` (clean, no unused-export/dependency findings), and `git diff --exit-code -- frontend/src/components/analysis/EloSelector.tsx` (exit 0, confirming the shared component is untouched).

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

`SetupScreen` is fully built, tested, and ready for Plan 06 to wire into `Bots.tsx`'s no-snapshot branch, replacing the D-14 hardcoded `BOT_GAME_SETTINGS` stub. `SetupScreenProps` (`ownerKey`, `normalizedRating`, `onStart`) is the exact contract Plan 06 needs to satisfy from `Bots.tsx`'s existing profile data. No blockers.

---
*Phase: 171-bots-page-setup-screen-nav*
*Completed: 2026-07-14*

## Self-Check: PASSED

All 3 created/modified files verified present on disk; both task commits (`5502e3ce`, `022b9f38`) verified present in git log.
