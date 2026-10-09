---
phase: 228-settings-page
plan: 01
subsystem: ui
tags: [react, localStorage, useSyncExternalStore, settings, navigation, vaul-drawer]

requires:
  - phase: 223-bot-voice
    provides: useMuted/setMuted store and the flawchess_bot_sound_muted key (reused unchanged)
provides:
  - lib/engineSettings.ts typed localStorage store for FC/SF line and arrow counts, plus resetAllSettings
  - SettingsPanel (Sound, FlawChess engine, Stockfish, Reset) used by /settings and both sheets
  - SettingsSheetButton (cogwheel plus bottom Drawer with the full panel)
  - /settings route inside ProtectedLayout and every entry point (desktop cogwheel, More drawer row, mobile /analysis sheet, mobile bot-game sheet)
affects: [228-02, 228-03, engine cards, useAnalysisEngineLines, useAnalysisBoardArrows, useStockfishEngine, useTrainFreePlay]

actuals:
  tokens: 8600
  tasks: 3
  commits: 3

tech-stack:
  added: []
  patterns:
    - "Per-key primitive useSyncExternalStore store (one flat localStorage key per setting) so every getSnapshot is a stable primitive"
    - "Tamper-safe reads: integer in range or default, never clamp"
    - "One SettingsPanel, two containers (page and bottom Drawer)"

key-files:
  created:
    - frontend/src/lib/engineSettings.ts
    - frontend/src/components/settings/SettingsPanel.tsx
    - frontend/src/components/settings/SettingsSheetButton.tsx
    - frontend/src/pages/Settings.tsx
    - frontend/src/lib/__tests__/engineSettings.test.ts
    - frontend/src/components/settings/__tests__/SettingsPanel.test.tsx
    - frontend/src/components/settings/__tests__/SettingsSheetButton.test.tsx
  modified:
    - frontend/src/App.tsx
    - frontend/src/App.test.tsx
    - frontend/src/components/bots/BotGameMobileLayout.tsx
    - frontend/src/pages/__tests__/Bots.test.tsx

key-decisions:
  - "Four new keys flawchess_settings_{fc,sf}_{lines,arrows}; sound keeps flawchess_bot_sound_muted untouched (lib/sounds.ts has zero diff)"
  - "Invalid or tampered stored values fall back to the default (no clamping); setCountSetting refuses invalid writes"
  - "Reset fires a single settings-reset event, not one per changed setting"
  - "Bot-game cogwheel sits at the far end of the existing top row (ml-auto), so the row height and vertical budget are unchanged"
  - "SettingId is used to type the sound event payload in SettingsPanel so the exported type is not dead for knip"

patterns-established:
  - "Settings entry points: header cogwheel as a ghost icon Link outside NAV_ITEMS; drawer row with a non-drawer-nav- testid; in-place sheet where navigation is costly"

requirements-completed: [D-01, D-02, D-03, D-04, D-05, D-06, D-07, D-08, D-09, D-10]

coverage:
  - id: D1
    description: "Settings store: defaults, round trip with subscriber re-render, tamper-safe reads, invalid writes refused, reset"
    verification:
      - kind: unit
        ref: "frontend/src/lib/__tests__/engineSettings.test.ts"
        status: pass
    human_judgment: false
  - id: D2
    description: "SettingsPanel: three ordered sections, 1-5 / 0-3 ToggleGroups, sound Switch with legacy mute key, Umami once per real change, Reset"
    verification:
      - kind: unit
        ref: "frontend/src/components/settings/__tests__/SettingsPanel.test.tsx"
        status: pass
    human_judgment: false
  - id: D3
    description: "Desktop header cogwheel reaches /settings, stays out of NAV_ITEMS; mobile header title reads Settings"
    verification:
      - kind: unit
        ref: "frontend/src/App.test.tsx#228 settings page entry"
        status: pass
    human_judgment: false
  - id: D4
    description: "Mobile More-drawer row, mobile /analysis sheet and mobile bot-game sheet open the full panel without navigating"
    verification:
      - kind: unit
        ref: "frontend/src/components/settings/__tests__/SettingsSheetButton.test.tsx, App.test.tsx, pages/__tests__/Bots.test.tsx"
        status: pass
    human_judgment: false

duration: 12min
completed: 2026-10-03
status: complete
plan_head_before: 2883983b06ca4167e17a23df685feaccd1a4b9fc
plan_head_after: 6f21d168905925c5ac211f478fd8ceab96428a21
---

# Phase 228 Plan 01: Settings Store, Panel, Page and Entry Points Summary

**A guest-usable /settings page and in-place mobile sheets backed by a tamper-safe useSyncExternalStore localStorage store, giving sound its off switch and persisting per-engine line/arrow counts for Plans 02 and 03.**

## Performance

- **Duration:** about 12 min
- **Tasks:** 3 of 3
- **Files:** 7 created, 4 modified

## Accomplishments

- `lib/engineSettings.ts`: one flat key per count (FC/SF lines 1-5 default 2, arrows 0-3 default 1); reads accept only in-range integers, otherwise the default; `resetAllSettings` also unmutes sound via `setMuted(false)`.
- `SettingsPanel`: Sound switch (legacy `'1'` mute key still reads as off), FlawChess and Stockfish sections with Lines and Arrows ToggleGroups, helper copy, a `brand-outline` Reset button disabled at defaults. Umami `settings-change {setting, value}` fires once per real change (re-tap guard on Radix `''`), `settings-reset` once on Reset.
- Entry points: desktop `nav-settings` cogwheel left of Logout (not in NAV_ITEMS), `drawer-settings` row above the divider, `btn-analysis-settings` and `btn-bots-settings` open the same full-panel sheet in place; `/settings` sits in ProtectedLayout without ImportRequiredRoute and `ROUTE_TITLES` titles it.
- The tracer (Task 1) ran end to end in `App.test.tsx`: header link, route, panel, sound key write, SF lines persistence. Mutation check: removing the `next === ''` guard made two panel tests fail.

## Task Commits

1. **Task 1 (tracer): store, panel, page, header cogwheel** - `041b69e8e`
2. **Task 2: store and panel contract tests** - `7d07cc90d`
3. **Task 3: mobile entry points and sheet** - `6f21d1689`

## Deviations from Plan

None to the plan's behavior. Two small adjustments, no scope change:

- **[Rule 3 - Blocking] knip flagged `SettingId` as an unused exported type.** Used it to type the sound event's `setting` value in `SettingsPanel` instead of dropping the plan-listed export. Commit `6f21d1689`.
- The plan's acceptance grep `grep -rn "drawer-nav-settings" frontend/src` must print nothing, so the negative test asserts no `drawer-nav-*` testid contains "settings" via a DOM scan rather than a literal id.

## Verification

From `frontend/`: `npm run lint` clean, `npm run build` (tsc -b + vite) clean, `npm run knip` clean, `npm test -- --run` 285 files / 4602 tests passed. Plan acceptance greps pass; `lib/sounds.ts` and `BotGameMobileBar.tsx` have zero diff; nothing under `components/analysis` references `SettingsSheetButton` (D-05).

## Known Stubs

None.

## Threat Flags

None. T-228-01 (tampered localStorage) mitigated and tested; T-228-02 payload is `{setting, value}` only.

## Notes for Plans 02 and 03

- Consume `useEngineDisplaySettings()` and the `LineCount`/`ArrowCount` types; replace `MAX_LINES`/`ARROW_COUNT` constants with the settings.
- Not changed here (per plan): no cross-tab `storage` listener; desktop cogwheel navigates away from `/analysis` and drops an unsaved free-play tree (D-01 locked; RESEARCH Open Question 1).

## Self-Check: PASSED

All created files exist and commits `041b69e8e`, `7d07cc90d`, `6f21d1689` are in `git log`.
