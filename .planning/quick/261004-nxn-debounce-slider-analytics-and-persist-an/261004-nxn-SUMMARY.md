---
phase: quick-261004-nxn
plan: 01
subsystem: frontend
tags: [analytics, umami, sliders, engine-settings, localStorage]
requires: []
provides:
  - useDebouncedTrackFeature (SLIDER_TRACK_DEBOUNCE_MS = 1000)
  - trackFeature optional pathname argument
  - useEngineToggles / setEngineToggle / ENGINE_TOGGLE_STORAGE_KEYS
affects:
  - frontend/src/components/analysis/TemperatureSelector.tsx
  - frontend/src/components/analysis/EloSelector.tsx
  - frontend/src/components/filters/TacticDepthFilter.tsx
  - frontend/src/components/filters/OpponentStrengthFilter.tsx
  - frontend/src/pages/Analysis.tsx
tech-stack:
  added: []
  patterns:
    - ref-only trailing debounce hook with flush on unmount
    - useSyncExternalStore boolean toggles with a session-override fallback on storage write failure
key-files:
  created:
    - frontend/src/hooks/useDebouncedTrackFeature.ts
    - frontend/src/hooks/__tests__/useDebouncedTrackFeature.test.ts
  modified:
    - frontend/src/lib/analytics.ts
    - frontend/src/lib/engineSettings.ts
    - frontend/src/lib/__tests__/engineSettings.test.ts
    - frontend/src/pages/Analysis.tsx
    - frontend/src/pages/__tests__/Analysis.test.tsx
    - frontend/src/components/analysis/TemperatureSelector.tsx
    - frontend/src/components/analysis/EloSelector.tsx
    - frontend/src/components/filters/TacticDepthFilter.tsx
    - frontend/src/components/filters/OpponentStrengthFilter.tsx
    - frontend/src/components/analysis/__tests__/AnalysisTabs.tracking.test.tsx
    - frontend/src/components/filters/__tests__/FlawFilterControl.test.tsx
    - frontend/CLAUDE.md
    - CHANGELOG.md
decisions:
  - Engine switches are not in the Settings panel and not reset by "Reset all settings".
  - No pagehide flush for a pending slider event.
  - Engine-ready gate opens at mount only when cache is cold AND all three engines are on.
metrics:
  tasks: 2
  files: 15
status: complete
actuals:
  tasks: 2
  commits: 2
plan_head_before: 84c11bc8dfa67e5918eea932beccfab7582af10f
plan_head_after: 8230265ef0d6a5b319569e94fbdf16a50cb0a8a4
completed: 2026-10-04
---

# Quick 261004-nxn: Slider analytics debounce and persisted engine switches Summary

One shared trailing-debounce hook now collapses slider commit bursts into a single Umami event, and the Stockfish, Maia and FlawChess switches persist in the existing engineSettings store.

## Tasks

| Task | Name | Commit |
| ---- | ---- | ------ |
| 1 | Debounced slider tracking hook wired into all four slider commit handlers | 1209a21ef |
| 2 | Persist the Stockfish / Maia / FlawChess switches in the engineSettings store | 8230265ef |

## What changed

**Task 1.** `useDebouncedTrackFeature(name, delayMs = SLIDER_TRACK_DEBOUNCE_MS)` keeps a pending record (props plus the pathname captured at call time) in refs, restarts a 1000 ms timer on every call, and flushes on unmount. `trackFeature` gained an optional third `pathname` argument (default `window.location.pathname`) used for both the D-14 exclusion and the page id, so a flush after navigation is attributed to the page where the slider was moved. TemperatureSelector, EloSelector, TacticDepthFilter and OpponentStrengthFilter route their `onValueCommit` through it; `onChange` / `onValueChange` stay synchronous. PresetRangeFilter is untouched. `frontend/CLAUDE.md` Sliders bullet updated.

**Task 2.** `engineSettings.ts` gained `useEngineToggles`, `setEngineToggle` and `ENGINE_TOGGLE_STORAGE_KEYS` (flat keys `flawchess_settings_engine_{stockfish,maia,flawchess}`, `'1'`/`'0'`, only exact `'0'` reads as off). If `localStorage.setItem` throws, the value is kept in a module-level session override (cleared by the next successful write). `Analysis.tsx` reads the three switches from the store above the gate initializer; the three handlers persist then track; hydration sends no event. CHANGELOG bullet added under Unreleased / Changed.

## Verification

- Targeted tests: all pass (hook, tracking, FlawFilterControl, selectors, analytics, engineSettings, Analysis: 103 tests).
- `npm run lint`, `npm run build` (tsc -b + vite), `npm run knip`: clean.
- Full `npm test -- --run`: 5010 passed, 1 failed. The failure is pre-existing and unrelated (see Deferred Issues).
- Mutation checks done for real:
  - Task 1: reverted TemperatureSelector to a direct `trackFeature` call; 3 new/updated tracking tests failed ("not called right after commit", held-key burst, keyboard step). Restored.
  - Task 2: restored `useState(true)` for flawChess and the old gate initializer; the persisted-off switch test and the engine-gate test both failed. Restored.

## Decisions (Claude's discretion)

- The switches are NOT added to the Settings panel UI and NOT reset by "Reset all settings" (`resetAllSettings` untouched, covered by a test): they are not panel settings, and a reset that silently re-enables heavy engines would surprise users. Persistence only.
- No pagehide flush: a slider event still pending when the tab is closed is lost. Acceptable for analytics (threat T-261004-nxn-04, accepted).
- The engine-ready gate now opens at mount only when the cache is cold AND all three engines are on. The gate is non-dismissible and only closes once every required asset has downloaded, but an asset only downloads while an engine that uses it is on, so a persisted-off engine plus missing seen flags (unsupported device, new asset id) could lock the user out. The all-on default keeps today's cold-start behavior exactly. Bug-fix comment is at the initializer site.
- Debounce is trailing, per component instance, 1000 ms.

## Audit findings (Task 2 step 3)

No defects found; no code changed beyond the plan.

- useStockfishEngine (worker-lifecycle effect line ~384), useMaiaEngine (lease effect ~601), useFlawChessEngine (provider lifecycle ~182, search effect ~338) and useStockfishGradingEngine (effect ~349) all start with `if (!enabled) return;`, so none spawns or warms a worker when `enabled` is false on the first render.
- useFastForward imports only `useAnalysisBoard` types and reads no engine state. The mobile tab default is `defaultValue="moves"` (AnalysisTabs.tsx ~803), engine-independent. The grading run is gated on `gradingEnabled = maiaEnabled || flawChessEnabled` with fen/enabled paired on the same condition. Downstream consumers (useGameOverlay, useAnalysisBoardArrows, useGemSweep, useAnalysisEngineLines, AnalysisTabs, AnalysisDesktopCards, MaiaHumanPanel, AnalysisPlayerBar, AnalysisBoardStage, FlawChessAgreementVerdict) receive the flags as props from Analysis.tsx, and the off states were already reachable mid-session before this change.
- useBotGame, useTrainFreePlay and useFastForward contain no references to the engine switches or the new store; left untouched.

## Deviations from Plan

None - plan executed as written. One test-harness extension: the Analysis.test.tsx `useFlawChessEngine` mock now also captures `enabled` in `flawChessCalls` (needed for the "latest flawChessCalls entry has enabled false" assertion the plan specifies).

## Deferred Issues

- `frontend/src/components/train/__tests__/TrainLeaderboardCard.test.tsx` ("clicking Accuracy shows % rows ...") fails on the committed baseline: it still expects the helper text to contain "Tactics puzzles don't count", but HEAD commit 84c11bc8d ("remove outdated caveat about tactics puzzle exclusion in accuracy helper") removed that copy. Not caused by this task; the test assertion needs updating in a separate change.

## Out-of-scope flags (not implemented)

- The focused slider thumb swallows ArrowLeft / ArrowRight, so keyboard board navigation stops working while a slider has focus.
- The `engine-gate-shown` and `pwa-install-offer-shown` events have no once-per-session dedupe.

## Known Stubs

None.

## Threat Flags

None. The deferred send only uses the captured pathname to derive the page id and D-14 exclusion; it is never sent.

## Self-Check: PASSED

- FOUND: frontend/src/hooks/useDebouncedTrackFeature.ts, frontend/src/hooks/__tests__/useDebouncedTrackFeature.test.ts
- FOUND commits: 1209a21ef, 8230265ef (both on main)
