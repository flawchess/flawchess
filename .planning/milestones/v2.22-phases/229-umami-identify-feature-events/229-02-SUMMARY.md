---
phase: 229-umami-identify-feature-events
plan: 02
subsystem: analytics
status: complete
tags: [frontend, analytics, umami, registry, popovers]

requires: [229-01]
provides:
  - "Typed feature-event registry (FeatureEventMap, 9 events) and trackFeature in lib/analytics.ts"
  - "popoverTargetFromTestId, currentPage, isTrackingExcludedPath, navDestinationOf, onOff, isAnalysisTabId and all const target arrays"
  - "hooks/useTrackedOpen.ts: useTrackedOpen (transition-fired) and useTrackedPopoverOpen (once per mount)"
  - "TimeControlPresetLabel union derived from TIME_CONTROL_PRESETS (as const satisfies)"
  - "popover-open event on InfoPopover plus the 7 popover shells (~70 instances)"
affects: [229-03, 229-04, 229-05, 229-06, 229-07, 229-08]

actuals:
  tokens: 28000
  tasks: 2
  commits: 2
plan_head_before: 27144be84a6b50745fe8492ce3e1d309fda58c84
plan_head_after: a09b7fe72c6e4d0f670cc9c645310247d910114d

tech-stack:
  added: []
  patterns:
    - "trackFeature is implemented via trackEvent so existing trackEvent spies and partial analytics mocks still see feature events"
    - "Tracking fires inside the setter on the open transition (ref-mirrored), never from an effect on a value and never inside a state updater (StrictMode double-invokes updaters)"

key-files:
  created:
    - frontend/src/hooks/useTrackedOpen.ts
    - frontend/src/hooks/__tests__/useTrackedOpen.test.tsx
  modified:
    - frontend/src/lib/analytics.ts
    - frontend/src/lib/__tests__/analytics.test.ts
    - frontend/src/lib/botTimeControlPresets.ts
    - frontend/src/components/ui/info-popover.tsx
    - frontend/src/components/popovers/MetricStatPopover.tsx
    - frontend/src/components/popovers/AchievableScorePopover.tsx
    - frontend/src/components/popovers/FlawBulletPopover.tsx
    - frontend/src/components/insights/BulletConfidencePopover.tsx
    - frontend/src/components/insights/ScoreConfidencePopover.tsx
    - frontend/src/components/charts/PercentileChip.tsx
    - frontend/src/components/charts/__tests__/PercentileChip.test.tsx
    - frontend/src/components/bots/PersonaEloDisclosurePopover.tsx
    - frontend/src/components/bots/__tests__/PersonaEloDisclosurePopover.test.tsx

key-decisions:
  - "Registry types for targets (ToggleTarget, PanelTarget, ActionTarget, NavDestination, ...) stay module-private; only the types the plan's export list names are exported, so knip stays clean until wave 3 consumers land"
  - "popoverTargetFromTestId rejects any slug that is not ^[a-z][a-z0-9-]*$ (e.g. an underscore in a testId) and sends nothing rather than a malformed target"

requirements-completed: [D-01, D-03, D-04, D-05, D-12, D-13, D-14, D-15]

coverage:
  - id: C1
    description: "Typed registry: 9 event names, enumerated targets/values, page derived from route, no collision with existing event names"
    verification:
      - kind: unit
        ref: "frontend/src/lib/__tests__/analytics.test.ts#feature-event registry"
        status: pass
      - kind: build
        ref: "npm run build (tsc -b)"
        status: pass
    human_judgment: false
  - id: C2
    description: "trackFeature sends nothing on /admin, /activity, /login, /auth/* (D-14) and never throws without a tracker"
    verification:
      - kind: unit
        ref: "frontend/src/lib/__tests__/analytics.test.ts#trackFeature sends nothing on %s"
        status: pass
    human_judgment: false
  - id: C3
    description: "Opening any explanation popover sends one id-free popover-open per mounted instance (hover and tap), nothing on render"
    verification:
      - kind: unit
        ref: "frontend/src/hooks/__tests__/useTrackedOpen.test.tsx"
        status: pass
      - kind: unit
        ref: "frontend/src/components/charts/__tests__/PercentileChip.test.tsx#popover-open tracking"
        status: pass
      - kind: unit
        ref: "frontend/src/components/bots/__tests__/PersonaEloDisclosurePopover.test.tsx#popover-open tracking"
        status: pass
    human_judgment: false
  - id: C4
    description: "popover-open target never carries a game id or list index (TagLegend, OpeningFindingCard shapes)"
    verification:
      - kind: unit
        ref: "frontend/src/lib/__tests__/analytics.test.ts#popoverTargetFromTestId"
        status: pass
    human_judgment: false

duration: 14min
completed: 2026-10-03
---

# Phase 229 Plan 02: Feature-event registry and popover-open Summary

One typed registry (9 events, enumerated targets) with `trackFeature`, proven end to end by a `popover-open` event on all ~70 explanation popovers via `useTrackedPopoverOpen`.

## What was built

- `lib/analytics.ts`: `FeatureEventMap` plus const target arrays (the D-15 inventory), `currentPage`, `isTrackingExcludedPath`, `trackFeature`, `popoverTargetFromTestId`, `navDestinationOf`, `onOff`, `isAnalysisTabId`. Value unions are type-imported from their source modules (`TimeControl`, `MatchSide`, `FlawTag`, `TacticFamily`, `EndgameClass`, `PlayStylePreset`, `TimeControlPresetLabel`, ...). `FEATURE_EVENT_NAMES` comes from a `Record<FeatureEventName, true>` so an unlisted event fails the build.
- `hooks/useTrackedOpen.ts`: `useTrackedOpen(onOpen, { once })` fires `onOpen` in a stable setter on false-to-true; `useTrackedPopoverOpen(testId)` wraps it with `once: true` and `popoverTargetFromTestId`.
- `botTimeControlPresets.ts`: `TIME_CONTROL_PRESETS` is `as const satisfies readonly TimeControlPreset[]`; `TimeControlPresetLabel` derived from it. `findPresetByLabel` and `DEFAULT_TC_PRESET_LABEL` unchanged and compile.
- `InfoPopover` plus `MetricStatPopover`, `AchievableScorePopover`, `FlawBulletPopover`, `BulletConfidencePopover`, `ScoreConfidencePopover`, `PercentileChip`, `PersonaEloDisclosurePopover` now use `useTrackedPopoverOpen`. `PersonaEloDisclosurePopover` hoists `PERSONA_ELO_DISCLOSURE_TESTID` so the hook argument and `data-testid` cannot drift.

## Verification

- `npx vitest run` over the full frontend suite: 289 files, 4714 tests pass.
- `npm run lint` clean; `npm run build` (tsc -b + vite) clean.
- Acceptance greps: 7 shells use `useTrackedPopoverOpen(`; no remaining `useState(false)` in `PercentileChip.tsx` or `PersonaEloDisclosurePopover.tsx`; `PERSONA_ELO_DISCLOSURE_TESTID` appears 3 times.
- The three suites that mock `@/lib/analytics` (SettingsPanel, EngineReadyGate, ImportAskActions) do not render an InfoPopover and pass unchanged, so no factory needed the partial-real spread form.

### Mutation check (raw testId as target)

Temporarily changed `useTrackedPopoverOpen` to pass the raw `testId` as the target. The `InfoPopover` test failed red as required:

```
FAIL  useTrackedOpen.test.tsx > InfoPopover popover-open tracking > sends nothing on render and one id-free event on open, none on reopen
expected "vi.fn()" to be called with arguments: [ 'popover-open', ... ]
-     "target": "tag-legend",
+     "target": "tag-legend-48213",
Tests  1 failed | 5 passed (6)
```

Reverted; the suite is green again.

## Deviations from Plan

None - plan executed exactly as written. Note: `npm ci` was run once in the fresh worktree's `frontend/` to restore the lockfile dependencies (no package added).

## Known Stubs

None.

## Threat Flags

None. All new surface is covered by T-229-07 to T-229-10; `popoverTargetFromTestId` and the registry unions are the mitigations and are tested.

## Notes for wave 3

- Several registry exports (`navDestinationOf`, `isAnalysisTabId`, `SidebarPanelId`, `onOff`, the target arrays, `FilterChangeProps`, `OptionChangeProps`, `PAGE_IDS`, ...) have no non-test consumer yet; `npm run knip` will flag them until plans 03-07 land. Plan 08 owns the knip gate.
- A testId containing an underscore or other non `[a-z0-9-]` character produces a null target and therefore no `popover-open` event (by design, T-229-08).

## Self-Check: PASSED

- Commits `a69aeb1c9` (registry + hook + InfoPopover) and `a09b7fe72` (7 shells) exist on the worktree branch.
- All files listed in key-files exist.
