---
phase: 229-umami-identify-feature-events
plan: 05
subsystem: analytics
status: complete
tags: [frontend, analytics, umami, analysis-board]

requires:
  - phase: 229-02
    provides: "trackFeature, onOff, isAnalysisTabId and the typed FeatureEventMap registry"
provides:
  - "Analysis board feature events: tab-switch, toggle engine-*, option-change elo/temperature, board-tool flip/paste-open/paste-load/line-expand/line-delete/elo-reset, action chip-cycle"
affects: [229-08]

actuals:
  tokens: 7500
  tasks: 2
  commits: 2
plan_head_before: 72a7089c36a24c42712f83bd125145c925284fb0
plan_head_after: 09f8a7905c0246dbdfa7354854b1d7ab7a0a4cb6

tech-stack:
  added: []
  patterns:
    - "Sliders track in onValueCommit only; Radix fires it once per drag and only when the value changed"
    - "Engine on/off switches report through three tracked handlers in Analysis.tsx; the raw useState setters stay private"

key-files:
  created:
    - frontend/src/components/analysis/__tests__/AnalysisTabs.tracking.test.tsx
  modified:
    - frontend/src/components/analysis/AnalysisTabs.tsx
    - frontend/src/pages/Analysis.tsx
    - frontend/src/components/analysis/EloSelector.tsx
    - frontend/src/components/analysis/TemperatureSelector.tsx
    - frontend/src/pages/__tests__/Analysis.test.tsx
    - frontend/src/components/board/BoardControls.tsx
    - frontend/src/components/bots/BotGameMobileBar.tsx
    - frontend/src/components/analysis/PasteModal.tsx
    - frontend/src/components/analysis/EngineLines.tsx
    - frontend/src/components/analysis/FlawChessEngineLines.tsx
    - frontend/src/components/analysis/VariationTree.tsx
    - frontend/src/components/analysis/AnalysisTagsPanel.tsx
    - frontend/src/components/board/__tests__/BoardControls.test.tsx

key-decisions:
  - "Swapped all four setter pass-through sites in Analysis.tsx for the tracked handlers: every receiver (EngineToggleHeader onCheckedChange in FlawChessCard and StockfishCard, MaiaHumanPanel Switch, MaiaCard onToggleEnabled) only calls the prop from a user Switch, so no auto-enable path is mis-reported"
  - "EloSelector gained a snapToLadder helper (nearest rung) used by both onChange and the commit event; for the uniform default ladder it is identical to the previous pass-through, and it guarantees the tracked value is always a MAIA_ELO_LADDER rung"
  - "chip-cycle is tracked in AnalysisTagsPanel.handleActivate after the cycle navigates, so it also covers motif chips and Move Stats cells that route through the same handler (target only, no tag or ply)"

requirements-completed: [D-02, D-03, D-06, D-12]

coverage:
  - id: C1
    description: "Tab switches fire tab-switch with the tab id; render fires nothing"
    verification:
      - kind: unit
        ref: "frontend/src/components/analysis/__tests__/AnalysisTabs.tracking.test.tsx#AnalysisTabs tab-switch tracking (D-02)"
        status: pass
    human_judgment: false
  - id: C2
    description: "Engine toggles fire toggle engine-* with on/off; FlawChess verified through the full Analysis page"
    verification:
      - kind: unit
        ref: "frontend/src/pages/__tests__/Analysis.test.tsx#Analysis page: engine toggle tracking"
        status: pass
    human_judgment: false
  - id: C3
    description: "ELO and temperature sliders fire once per drag on commit (never on change alone), ELO value is a ladder rung, temperature is a 3-value bucket; ELO reset fires elo-reset; bots page is attributed via page"
    verification:
      - kind: unit
        ref: "frontend/src/components/analysis/__tests__/AnalysisTabs.tracking.test.tsx#EloSelector tracking (Pitfall 2)"
        status: pass
      - kind: unit
        ref: "frontend/src/components/analysis/__tests__/AnalysisTabs.tracking.test.tsx#TemperatureSelector tracking"
        status: pass
    human_judgment: false
  - id: C4
    description: "Flip tracked on BoardControls; back/forward/reset/fast-forward untracked (D-06)"
    verification:
      - kind: unit
        ref: "frontend/src/components/board/__tests__/BoardControls.test.tsx#BoardControls tracking"
        status: pass
    human_judgment: false
  - id: C5
    description: "paste-load, line-expand (expand only), line-delete, chip-cycle, bot-bar flip send fixed targets only; btn-paste-analyze untracked and no pasted text in any payload"
    verification:
      - kind: other
        ref: "grep acceptance checks plus existing suites for PasteModal, EngineLines, FlawChessEngineLines, VariationTree, AnalysisTagsPanel, BotGameMobileBar (all green); FeatureEventMap cannot express free text"
        status: pass
    human_judgment: true

duration: 22min
completed: 2026-10-03
---

# Phase 229 Plan 05: Analysis board feature events Summary

The analysis board now reports its discrete feature usage (tabs, engine switches, ELO and play-style sliders, flip, paste, line expand/delete, tag chip cycle) through the typed `trackFeature` registry, while move stepping stays silent.

## What was built

- `AnalysisTabs.tsx`: uncontrolled Radix `Tabs` gets `onValueChange` firing `tab-switch` (guarded by `isAnalysisTabId`; Radix never fires it on mount). The shared `MoveListHeaderContent` paste button fires `board-tool paste-open` once for desktop and mobile.
- `Analysis.tsx`: `handleStockfishToggle`, `handleMaiaToggle`, `handleFlawChessToggle` wrap the three setters and replace them at the four pass-through sites.
- `EloSelector.tsx`: `onValueCommit` fires `option-change elo` with the snapped ladder rung; the reset button fires `board-tool elo-reset`. `TemperatureSelector.tsx`: `onValueCommit` fires `option-change temperature` with `lower | default | higher` via a module-private `temperatureBucket` (never the float).
- `BoardControls.tsx` and `BotGameMobileBar.tsx`: flip fires `board-tool flip`. `PasteModal.tsx`: Load submit fires `paste-load`; Analyze full game stays untracked. `EngineLines.tsx` / `FlawChessEngineLines.tsx`: `line-expand` on expand only. `VariationTree.tsx`: both delete handlers fire `line-delete`. `AnalysisTagsPanel.tsx`: `chip-cycle`.

## Test approach

- Slider tests use the real Radix primitive. Keyboard arrows prove one event per commit; a pointer-down/pointer-up drag (stubbed pointer capture and track rect) proves the commit-only contract (`onChange` fired, tracker untouched until pointer-up). Radix only fires `onValueCommit` when the value changed since drag start, so drag tests use stateful wrappers (a fixed controlled `value` never commits).
- Tab tests trigger Radix tabs with `mouseDown`.
- Analysis page test uses a `window.umami` stub, the real analytics module and `history.pushState('/analysis')`; none of the touched suites mock `@/lib/analytics`, so no factory needed the partial-real spread.

## Verification

- `npm run lint` clean, `npm run build` (tsc -b + vite) clean.
- `npx vitest run src/components/analysis/ src/components/board/ src/components/bots/ src/pages/__tests__/Analysis.test.tsx`: 33 files, 518 tests pass.
- All acceptance greps match (tab-switch 1, paste-open 1, engine-* 3, onValueCommit in both selectors, elo-reset 1, flip 1 per file, paste-load 1, line-expand 1 per file, line-delete 2, chip-cycle 1).
- knip not run (deferred to Plan 08 per the plan).

## Deviations from Plan

None - plan executed exactly as written. Note for the record: the `snapToLadder` helper is new behavior for `onChange` (nearest rung instead of raw pass-through); identical for the uniform Maia ladder and the existing EloSelector suite passes unchanged.

## Known Stubs

None.

## Threat Flags

None. Every payload is a fixed literal from the registry; pasted PGN/FEN text, SAN moves, tag names and game ids are not expressible in `FeatureEventMap` (T-229-16); sliders fire on commit with a ladder rung or 3-value bucket (T-229-17).

## Self-Check: PASSED

- FOUND: frontend/src/components/analysis/__tests__/AnalysisTabs.tracking.test.tsx
- FOUND commits: e945ffba0, 09f8a7905
