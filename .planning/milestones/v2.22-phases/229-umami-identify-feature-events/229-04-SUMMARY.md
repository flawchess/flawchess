---
phase: 229-umami-identify-feature-events
plan: 04
subsystem: analytics
status: complete
tags: [frontend, analytics, umami, filters, openings]

requires: [229-02]
provides:
  - "filter-change events for every D-12 group 2 filter control (played-as, recency, time control, platform, pasted, opponent type, rated, opponent strength, piece filter, flaw severity/tag, tactic family/orientation/depth, gem, great, reset, apply) and the Openings color toggle"
  - "PresetRangeFilter optional slider.onValueCommit passthrough"
  - "panel-open bookmark-suggestions, action analyze / bookmark-load, toggle bookmark-chart"
affects: [229-08]

actuals:
  tokens: 24000
  tasks: 3
  commits: 3
plan_head_before: 72a7089c36a24c42712f83bd125145c925284fb0
plan_head_after: bbe496ee28779b37bf076eedc5b5b6e70fd20bad

tech-stack:
  added: []
  patterns:
    - "Each handler tracks its own typed value after its guard and state write; FilterPanel.update(partial) is never diffed"
    - "Slider filters report once on Radix onValueCommit (drag end), as the matching preset or 'custom'"
    - "Shared FilterActions footer tracks reset/apply once for all 17 footers"

key-files:
  created:
    - frontend/src/components/filters/__tests__/FilterPanel.tracking.test.tsx
    - frontend/src/components/position-bookmarks/__tests__/PositionBookmarkCard.tracking.test.tsx
  modified:
    - frontend/src/components/filters/FilterPanel.tsx
    - frontend/src/components/filters/FilterActions.tsx
    - frontend/src/components/filters/FlawFilterControl.tsx
    - frontend/src/components/filters/PresetRangeFilter.tsx
    - frontend/src/components/filters/OpponentStrengthFilter.tsx
    - frontend/src/components/filters/TacticDepthFilter.tsx
    - frontend/src/components/filters/__tests__/FlawFilterControl.test.tsx
    - frontend/src/pages/openings/OpeningsFilterFields.tsx
    - frontend/src/pages/Openings.tsx
    - frontend/src/components/position-bookmarks/PositionBookmarkCard.tsx

key-decisions:
  - "PresetRangeFilter stays presentational: it only forwards slider.onValueCommit and contains no tracking call or analytics import; its two callers (OpponentStrengthFilter, TacticDepthFilter) track"
  - "Custom date range is reported only as value 'custom', and on desktop only when the committed range differs from the existing one, so a popover dismissed with no edit is silent (T-229-13)"
  - "Gem/great closures bail when their handler prop is absent, so the Best Moves section rendered with only one handler never reports the other button"
  - "Slider commit tests use real Radix pointer drags in jsdom (stubbed getBoundingClientRect and pointer capture) with stateful wrappers, because Radix only commits when the controlled value moved"

requirements-completed: [D-03, D-04, D-12]

coverage:
  - id: C1
    description: "Each user change of a D-12 group 2 filter fires exactly one filter-change with the target and new value; render and Radix re-tap fire nothing"
    verification:
      - kind: unit
        ref: "frontend/src/components/filters/__tests__/FilterPanel.tracking.test.tsx"
        status: pass
      - kind: unit
        ref: "frontend/src/components/filters/__tests__/FlawFilterControl.test.tsx#filter-change tracking (Phase 229)"
        status: pass
    human_judgment: false
  - id: C2
    description: "Slider filters fire once on drag end, never per drag step, and never leak the Elo gap or depth bounds"
    verification:
      - kind: unit
        ref: "frontend/src/components/filters/__tests__/FlawFilterControl.test.tsx#slider commit (Pitfall 2)"
        status: pass
    human_judgment: false
  - id: C3
    description: "Reset and Apply in the shared footer and the lone Reset button report filter-change reset / apply"
    verification:
      - kind: unit
        ref: "frontend/src/components/filters/__tests__/FilterPanel.tracking.test.tsx"
        status: pass
    human_judgment: false
  - id: C4
    description: "Bookmark chart toggle and load report fixed, id-free events; match-side change stays untracked"
    verification:
      - kind: unit
        ref: "frontend/src/components/position-bookmarks/__tests__/PositionBookmarkCard.tracking.test.tsx"
        status: pass
    human_judgment: false
  - id: C5
    description: "Openings color toggle (desktop and mobile), bookmark suggestions open and Analyze position are wired"
    verification:
      - kind: build
        ref: "npm run build (tsc -b) plus acceptance greps: target 'color' x2, 'bookmark-suggestions' x1, 'analyze' x1 in Openings.tsx"
        status: pass
    human_judgment: true

duration: 25min
completed: 2026-10-03
---

# Phase 229 Plan 04: Filter-change and Openings leaf events Summary

Every filter control in D-12 group 2 plus the Openings color toggle, bookmark suggestions, Analyze position and the bookmark card now report typed events through `trackFeature`, with sliders firing once per drag.

## What was built

- `FilterPanel.tsx`: played-as, recency (preset and custom commit on desktop popover and mobile drawer Apply), time-control, platform, Pasted, opponent type, rated and the lone Reset button each call `trackFeature('filter-change', ...)` inside their handler after the guard. Platform toggling was split into `applyPlatformToggle` (existing logic untouched) plus a thin tracked `togglePlatform`. No `useEffect` was added (count stays 3).
- `FilterActions.tsx`: `handleReset` / `handleApply` wrappers track `reset` / `apply`, covering all 17 footers (LibraryFilterPanel needs no change).
- `OpeningsFilterFields.tsx`: piece filter tracks `piece-filter` inside its existing `if (!v) return` guard.
- `FlawFilterControl.tsx`: severity, flaw tag, tactic family, orientation (after the deselect guard) and gem/great (reporting the NEW state via `onOff(!hasGem)` / `onOff(!hasGreat)`).
- `PresetRangeFilter.tsx`: optional `slider.onValueCommit` typed and forwarded to the Slider. `OpponentStrengthFilter` and `TacticDepthFilter`: `handlePreset` tracks the preset; new `handleSliderCommit` tracks `derivePreset(...) ?? 'custom'`; `handleSliderChange` stays untracked.
- `Openings.tsx`: both color toggles (desktop `onToggleColor`, mobile `onTogglePlayedAs`) track `color` with the new `Color`; one `openSuggestions` callback replaces the three inline closures and tracks `panel-open bookmark-suggestions`; `handleAnalyzePosition` tracks `action analyze` before `navigate` (so the derived page is still openings).
- `PositionBookmarkCard.tsx`: `handleChartToggle` tracks `toggle bookmark-chart` (`onOff(!chartEnabled)`), `handleLoad` tracks `action bookmark-load`. No bookmark id in any payload; `onMatchSideChange` untracked.

## Verification

- `npx vitest run src/components/filters/ src/components/position-bookmarks/ src/pages/openings/ src/pages/`: 23 files, 340 tests pass.
- `npm run lint` clean; `npm run build` (tsc -b + vite) clean after each task.
- Mutation check (Pitfall 2): temporarily made `OpponentStrengthFilter`'s `onValueChange` also call `handleSliderCommit`. The slider test failed red (`expected "vi.fn()" to not be called at all, but actually been called 2 times`). Reverted; green again.
- Pre-edit grep: the only `vi.mock('@/lib/analytics'` suites are SettingsPanel, EngineReadyGate and ImportAskActions; none render a component touched here, so no factory needed the partial-real form.
- Tracer gate (Task 1): the click path to `window.umami.track` was proven by the test suite (real analytics module) before expansion; passed, expanded.

## Deviations from Plan

None - plan executed exactly as written. Test-implementation notes:
- The slider commit is tested with real Radix pointer events (not a thin PresetRangeFilter render). The first attempt failed because a `vi.fn()` `onChange` never moves the controlled value and Radix commits only when the value changed; stateful wrappers fixed it. The depth slider defaults to the full range, so the drag uses clientX 100 to move the low thumb.
- `PositionBookmarkCard` renders its button row in both the mobile and desktop layouts, so its test uses `getAllByTestId(...)[0]`. It also needs `TooltipProvider` and a `QueryClientProvider` (mutation hooks).
- `npm ci` was run once in the fresh worktree's `frontend/` (no package added).

## Known Stubs

None.

## Threat Flags

None. T-229-13 (custom range only as `'custom'`), T-229-14 (bookmark id absent, asserted by test) and T-229-15 (commit-only sliders, asserted by test) are all mitigated and tested.

## Notes for Plan 08

- knip: `FilterChangeProps` targets `endgame-type` is not consumed here (Endgames plan owns it). This plan consumed `onOff`, `RatedFilterValue` and the `filter-change`, `toggle`, `panel-open`, `action` events.
- `FlawFilterControl` flaw-tag and tactic-family tracking fire on every click, including when a parent supplies no `onTacticFamiliesChange` (the section is only rendered by callers that pass it).

## Self-Check: PASSED

- Commits `5602944c8` (Task 1), `53292b962` (Task 2), `bbe496ee2` (Task 3) exist on the worktree branch.
- All files listed in key-files exist.
