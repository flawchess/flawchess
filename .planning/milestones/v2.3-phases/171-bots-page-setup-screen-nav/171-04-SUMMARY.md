---
phase: 171-bots-page-setup-screen-nav
plan: 04
subsystem: ui
tags: [react, typescript, localStorage, radix-slider, vitest]

requires:
  - phase: 170-localstorage-resume
    provides: botGameSnapshot.ts / botPendingStore.ts owner-scoped localStorage shape to mirror
  - phase: 166-bot-move-selection
    provides: selectBotMove's blend regime dispatch (justifies the 0.05 slider floor)
provides:
  - TIME_CONTROL_PRESETS (9-entry lichess TC label -> {baseSeconds, incrementSeconds} table)
  - playStyle.ts constants + deriveActivePlayStylePreset/formatPlayStyleSummary
  - botSetupSettings.ts (third owner-scoped localStorage key + resolveDefaultBotElo)
  - PlayStyleControl.tsx (single-thumb preset+slider component)
affects: [171-05-setup-screen, 171-06-nav-and-newgame-rewire]

tech-stack:
  added: []
  patterns:
    - "Sibling-not-wrapper component pattern: PlayStyleControl copies PresetRangeFilter's shell but has its own single-thumb slider contract, never importing from filters/"
    - "Third owner-scoped localStorage key mirroring botGameSnapshot.ts's SSR-guard -> try/catch -> JSON.parse -> shape-validator -> Sentry-once-on-corruption shape"

key-files:
  created:
    - frontend/src/lib/botTimeControlPresets.ts
    - frontend/src/lib/playStyle.ts
    - frontend/src/lib/botSetupSettings.ts
    - frontend/src/components/bots/PlayStyleControl.tsx
    - frontend/src/lib/__tests__/botTimeControlPresets.test.ts
    - frontend/src/lib/__tests__/playStyle.test.ts
    - frontend/src/lib/__tests__/botSetupSettings.test.ts
    - frontend/src/components/bots/__tests__/PlayStyleControl.test.tsx
  modified: []

key-decisions:
  - "resolveDefaultBotElo snaps a mid-rung rating to the nearest 100-Elo rung via Math.round((clamped-min)/step)*step+min — pinned so 1650 -> 1700 (round-half-up, matching Math.round's native behavior)"
  - "DEFAULT_BOT_SETUP_SETTINGS.colorPreference defaults to 'random' — no explicit guidance in CONTEXT.md/UI-SPEC.md, chosen as the neutral no-preference default consistent with D-12's 'Random resolves at Start' framing"
  - "formatPlayStyleSummary's numeric form uses blend.toFixed(2) (e.g. '0.50') per UI-SPEC.md's exact example string"

patterns-established:
  - "PlayStyleControl.tsx is the reference sibling-component pattern for any future single-thumb control that visually matches PresetRangeFilter without widening its two-thumb-only prop contract"

requirements-completed: [PLAY-02]

coverage:
  - id: D1
    description: "9-entry lichess TC preset table (blitz 3+0/3+2/5+0/5+3, rapid 10+0/10+5/15+10, classical 30+0/30+20; no bullet) converting label -> {baseSeconds, incrementSeconds}, with the 30+0 -> backend-rapid-bucket quirk documented inline"
    requirement: "PLAY-02"
    verification:
      - kind: unit
        ref: "frontend/src/lib/__tests__/botTimeControlPresets.test.ts"
        status: pass
    human_judgment: false
  - id: D2
    description: "Play-style pure derivations: HUMAN_BLEND/ENGINE_BLEND, PLAY_STYLE_MIN/MAX/STEP/DEFAULT_BLEND, deriveActivePlayStylePreset, formatPlayStyleSummary — slider floor (0.05) pinned strictly above HUMAN_BLEND (0)"
    requirement: "PLAY-02"
    verification:
      - kind: unit
        ref: "frontend/src/lib/__tests__/playStyle.test.ts"
        status: pass
    human_judgment: false
  - id: D3
    description: "botSetupSettings.ts — third owner-scoped localStorage key (flawchess_bot_setup_settings:), distinct from botGameSnapshot's and botPendingStore's, with corruption recovery and resolveDefaultBotElo"
    requirement: "PLAY-02"
    verification:
      - kind: unit
        ref: "frontend/src/lib/__tests__/botSetupSettings.test.ts"
        status: pass
    human_judgment: false
  - id: D4
    description: "PlayStyleControl.tsx — single-thumb Human/Engine preset + slider control whose slider provably cannot reach blend 0 (aria-valuemin=0.05)"
    requirement: "PLAY-02"
    verification:
      - kind: unit
        ref: "frontend/src/components/bots/__tests__/PlayStyleControl.test.tsx"
        status: pass
    human_judgment: false

duration: 25min
completed: 2026-07-14
status: complete
---

# Phase 171 Plan 04: Setup-Screen Primitives (Time-Control Presets, Play-Style Control, Settings Persistence) Summary

**Three pure lib modules (9-preset TC table, play-style derivations, third owner-scoped localStorage key) plus a single-thumb PlayStyleControl whose slider provably cannot reach blend 0.**

## Performance

- **Duration:** 25 min
- **Tasks:** 3
- **Files modified:** 8 (4 new lib/component files, 4 new test files)

## Accomplishments
- `botTimeControlPresets.ts` — the 9-entry lichess TC preset table (label -> `{baseSeconds, incrementSeconds}`), with the accepted `30+0` -> backend `rapid`-bucket quirk documented directly at the row and cross-referenced against `app/services/normalization.py`'s frozen boundary rule.
- `playStyle.ts` — `HUMAN_BLEND`/`ENGINE_BLEND`/`PLAY_STYLE_MIN`/`MAX`/`STEP`/`DEFAULT_BLEND` plus `deriveActivePlayStylePreset` and `formatPlayStyleSummary`, with `PLAY_STYLE_MIN (0.05) > HUMAN_BLEND (0)` pinned as a standalone assertion — the constant-level proof that the slider cannot reach the Human regime by dragging.
- `botSetupSettings.ts` — a third, physically separate owner-scoped localStorage key (`flawchess_bot_setup_settings:`), verbatim-mirroring `botGameSnapshot.ts`'s guard/parse/validate/Sentry-once shape, plus `resolveDefaultBotElo` (clamp + snap to the `MAIA_ELO_LADDER`, BOT-03/D-06 invariants documented in the doc comment).
- `PlayStyleControl.tsx` — a single-thumb sibling of `PresetRangeFilter` (not a prop variant, not a wrapper) with Human/Engine presets and a slider floored at 0.05; Human-active state dims the slider and parks its thumb at the floor.

## Task Commits

Each task was committed atomically:

1. **Task 1: botTimeControlPresets.ts + playStyle.ts** - `6303baab` (feat)
2. **Task 2: botSetupSettings.ts** - `3ed59adf` (feat)
3. **Task 3: PlayStyleControl.tsx** - `28d8e9e6` (feat)

**Plan metadata:** (this commit, docs: complete plan)

## Files Created/Modified
- `frontend/src/lib/botTimeControlPresets.ts` - 9-entry TC preset table + `findPresetByLabel`
- `frontend/src/lib/playStyle.ts` - play-style constants + `deriveActivePlayStylePreset`/`formatPlayStyleSummary`
- `frontend/src/lib/botSetupSettings.ts` - third owner-scoped settings key + `resolveDefaultBotElo` + `DEFAULT_BOT_SETUP_SETTINGS`
- `frontend/src/components/bots/PlayStyleControl.tsx` - single-thumb play-style control
- `frontend/src/lib/__tests__/botTimeControlPresets.test.ts` - 6 tests
- `frontend/src/lib/__tests__/playStyle.test.ts` - 10 tests
- `frontend/src/lib/__tests__/botSetupSettings.test.ts` - 15 tests
- `frontend/src/components/bots/__tests__/PlayStyleControl.test.tsx` - 11 tests

## Decisions Made
- `resolveDefaultBotElo(1650)` snaps to `1700` (`Math.round` of the half-rung case rounds up) — pinned in the test as the plan explicitly allowed either direction.
- `DEFAULT_BOT_SETUP_SETTINGS.colorPreference` defaults to `'random'` (no explicit spec guidance; chosen as the neutral no-preference default, pinned in the test).
- `formatPlayStyleSummary`'s numeric form uses `blend.toFixed(2)` matching UI-SPEC.md's `"0.50 — blends style with 50% search"` example exactly.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

All four primitives (`TIME_CONTROL_PRESETS`, `playStyle.ts`'s derivations, `botSetupSettings.ts`'s round-trip + `resolveDefaultBotElo`, and `PlayStyleControl.tsx`) are ready for Plan 05's `SetupScreen.tsx` composition. `PresetRangeFilter.tsx` and `app/services/normalization.py` are both untouched (verified via `git diff --exit-code`), so no unplanned surface was introduced. No blockers for the remaining setup-screen wiring (color picker, TC picker, ELO reuse) or nav wiring in Plans 05/06.

---
*Phase: 171-bots-page-setup-screen-nav*
*Completed: 2026-07-14*

## Self-Check: PASSED
