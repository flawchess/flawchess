---
phase: quick-261123-9cw
plan: 01
subsystem: frontend/analysis
tags: [settings, analysis-board, jump-button, localStorage]
status: complete
requires: []
provides:
  - computeFastForwardStops helper
  - useJumpOwnMovesOnly / setJumpOwnMovesOnly preference store
affects: [frontend/src/pages/Analysis.tsx, frontend/src/components/settings/SettingsPanel.tsx]
tech-stack:
  added: []
  patterns: [useSyncExternalStore flat-key setting with session override fallback]
key-files:
  created:
    - frontend/src/lib/fastForwardStops.ts
    - frontend/src/lib/__tests__/fastForwardStops.test.ts
  modified:
    - frontend/src/lib/engineSettings.ts
    - frontend/src/lib/__tests__/engineSettings.test.ts
    - frontend/src/pages/Analysis.tsx
    - frontend/src/components/settings/SettingsPanel.tsx
    - frontend/src/components/settings/__tests__/SettingsPanel.test.tsx
    - CHANGELOG.md
key-decisions:
  - "Preference lives in localStorage (flawchess_settings_jump_own_moves), default off, covered by Reset"
  - "Unknown user color falls back to both-sides stops instead of an empty set"
metrics:
  tasks: 2
  commits: 2
  plan_head_before: 7b012d8b6258b3b6471602ac533d69091f7f2b5e
  plan_head_after: 344df62cfd78b6f5c6632d8e05fbd0198f196b31
actuals:
  tasks: 2
  commits: 2
commits: 2
plan_head_before: 7b012d8b6258b3b6471602ac533d69091f7f2b5e
plan_head_after: 344df62cfd78b6f5c6632d8e05fbd0198f196b31
completed: 2026-11-23
---

# Quick 261123-9cw: Jump button own-moves setting Summary

A "Jump button" switch in the settings panel makes the analysis board's Jump stop only at the user's own blunders, mistakes, gem and great moves (default off, both sides as before).

## What changed

- `computeFastForwardStops` (new, pure): collects blunder/mistake and gem/great plies; with the setting on and a white/black user color, filters via `isUserPly`. Unknown color keeps both sides.
- `engineSettings.ts`: `useJumpOwnMovesOnly`, `setJumpOwnMovesOnly`, `JUMP_OWN_MOVES_STORAGE_KEY`; only exact `'1'` reads on; in-memory override when storage writes fail; `resetAllSettings` clears it; `SettingId` gained `'jumpOwnMoves'`.
- `Analysis.tsx`: stop-set memo now calls the helper; unused `isRareMoveTier` import removed. `useFastForward` untouched; highlight display untouched.
- `SettingsPanel.tsx`: new `settings-section-jump` card with `settings-jump-own-moves-switch`, legacy `settings-change` event (`jumpOwnMoves`, on/off), included in `isAtDefaults`.
- CHANGELOG bullet under Unreleased / Added.

## Verification

Frontend lint, `npm run build` (tsc -b), full vitest suite (6844 passed) and knip (config hints only) all green. New tests cover both-sides default, white/black filtering, unknown-color fallback, null inputs, storage tamper/throw cases, Reset and the panel switch/event.

## Deviations from Plan

None - plan executed as written. Minor placement: `useJumpOwnMovesOnly()` is called directly above the stop-set memo in Analysis.tsx instead of next to `useEngineToggles()` (same component, unconditional hook call).

## Known Stubs

None.

## Self-Check: PASSED

Created files exist; commits f0aa49e43 and 344df62cf are on main.
