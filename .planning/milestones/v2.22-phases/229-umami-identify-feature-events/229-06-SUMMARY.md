---
phase: 229-umami-identify-feature-events
plan: 06
subsystem: analytics
status: complete
tags: [frontend, analytics, umami, endgames, library, openings]

requires: [229-02]
provides:
  - "panel-open on endgame per-TC accordions (endgame-type-tc, endgame-metrics-tc, time-pressure-tc), expand only"
  - "toggle on endgame ELO timeline and flaw trend legends (elo-timeline-legend, flaw-trend-legend) with on/off"
  - "panel-open on show-more expanders (opening-insights-more, opening-stats-more, tactic-motifs-more, move-stats-expand), expand only"
  - "action analyze on FlawCard and both LibraryGameCard Links; action chip-cycle on LibraryGameCard"
affects: [229-08]

actuals:
  tokens: 18000
  tasks: 2
  commits: 2
plan_head_before: 72a7089c36a24c42712f83bd125145c925284fb0
plan_head_after: c221b74241c955091e011a61eb686707d8ab6f15

tech-stack:
  added: []
  patterns:
    - "Accordion onValueChange goes through a named handler that tracks only when the next array contains a value absent from the current one (an item was opened)"
    - "Expanders gate trackFeature on the pre-toggle state (expanded false / collapsed true) so collapse is silent"
    - "Internal Analyze Links track in onClick; no data-umami-event on a react-router Link"

key-files:
  created: []
  modified:
    - frontend/src/components/charts/EndgameTypeBreakdownSection.tsx
    - frontend/src/components/charts/EndgameMetricsByTcSection.tsx
    - frontend/src/components/charts/EndgameTimePressureSection.tsx
    - frontend/src/components/charts/EndgameEloTimelineSection.tsx
    - frontend/src/components/library/FlawTrendChart.tsx
    - frontend/src/components/insights/OpeningInsightsBlock.tsx
    - frontend/src/components/stats/OpeningStatsSection.tsx
    - frontend/src/components/library/TacticMotifGroup.tsx
    - frontend/src/components/library/MoveStats.tsx
    - frontend/src/components/results/LibraryGameCard.tsx
    - frontend/src/components/library/FlawCard.tsx
    - frontend/src/components/charts/__tests__/EndgameTypeBreakdownSection.test.tsx
    - frontend/src/components/charts/__tests__/EndgameEloTimelineSection.test.tsx
    - frontend/src/components/results/__tests__/LibraryGameCard.test.tsx

key-decisions:
  - "chip-cycle fires after the no-plies early return in handleActivate, so only activations that actually cycle are counted; MoveStats cell clicks share that handler and also count as chip-cycle"
  - "The two sibling accordion sections (metrics-by-TC, time-pressure) reuse the type-breakdown pattern verbatim and are covered by the existing suites as regression rather than new cases, as the plan specified"

requirements-completed: [D-03, D-04, D-12]

coverage:
  - id: C1
    description: "Expanding an endgame per-TC accordion item fires one id-free panel-open; render and collapse are silent"
    verification:
      - kind: unit
        ref: "frontend/src/components/charts/__tests__/EndgameTypeBreakdownSection.test.tsx#panel-open tracking"
        status: pass
    human_judgment: false
  - id: C2
    description: "Legend clicks fire toggle with off when hiding and on when showing; no combo key in the payload"
    verification:
      - kind: unit
        ref: "frontend/src/components/charts/__tests__/EndgameEloTimelineSection.test.tsx#legend toggle tracking"
        status: pass
    human_judgment: false
  - id: C3
    description: "LibraryGameCard Analyze, chip activation and move-stats expand fire typed actions; no game id in any payload"
    verification:
      - kind: unit
        ref: "frontend/src/components/results/__tests__/LibraryGameCard.test.tsx#feature-event tracking"
        status: pass
    human_judgment: false
  - id: C4
    description: "Expanders (opening insights, opening stats, tactic motifs) and FlawCard Analyze are wired"
    verification:
      - kind: build
        ref: "npm run build (tsc -b) plus acceptance greps"
        status: pass
    human_judgment: true

duration: 12min
completed: 2026-10-03
---

# Phase 229 Plan 06: Chart and table view controls Summary

Endgame per-TC accordions, chart legends, show-more expanders, the library game card chip cycle and both Analyze actions now report typed, identifier-free Umami feature events.

## What was built

- **Accordions (3 sections):** `onValueChange` now routes through `handleExpandedChange`, which sends `panel-open` (`endgame-type-tc` / `endgame-metrics-tc` / `time-pressure-tc`) only when the next array holds a TC that was not open. No TC value in the payload.
- **Legends:** `EndgameEloTimelineSection` and `FlawTrendChart` send `toggle` (`elo-timeline-legend` / `flaw-trend-legend`) with `onOff(isHidden)`: a hidden series becoming visible is `on`. No combo or series key.
- **Expanders:** `OpeningInsightsBlock`, `OpeningStatsSection`, `TacticMotifGroup` send `panel-open` only when `expanded` is false; `MoveStats` only when `collapsed` is true.
- **Cards:** `LibraryGameCard` sends `action` `chip-cycle` from `handleActivate` and `action` `analyze` from both Analyze Links; `FlawCard` sends `analyze` from its Link. All via `onClick`, never `data-umami-event`.

## Verification

- Targeted suites: 4 chart suites (57 tests) and 4 card/insight suites (75 tests) pass; wider run over charts, library, results, insights and stats: 39 files, 616 tests pass.
- `npm run lint` clean; `npm run build` (tsc -b + vite) clean.
- Acceptance greps all return the expected counts for the new strings (see deviation note on two counts).

### Mutation checks

- Accordion gate changed to `if (next.length >= 0)`: type-breakdown test failed (`expected "vi.fn()" to be called 1 times, but got 2 times`). Reverted.
- chip-cycle `trackFeature` line commented out: `activating a tag chip sends one id-free action chip-cycle` failed. Reverted.

## Deviations from Plan

None in behavior. Two acceptance greps in the plan assumed a count of 1 but pre-existing testids contain the same substring: `grep -c "endgame-metrics-tc"` prints 3 in `EndgameMetricsByTcSection.tsx` (existing `endgame-metrics-tc-section*` testids) and `grep -c "flaw-trend-legend"` prints 2 in `FlawTrendChart.tsx` (existing `flaw-trend-legend-${s.key}` testid). Exactly one `trackFeature` target occurrence exists in each. `npm ci` was run once in the fresh worktree's `frontend/`; no package was added.

## Known Stubs

None.

## Threat Flags

None. T-229-18 mitigated: targets are registry literals, and the LibraryGameCard tests serialize every track call and assert the game id is absent.

## Notes

- knip will flag registry exports until all wave-3 plans land; Plan 08 owns the knip gate (not run here).

## Self-Check: PASSED

- Commits `319bba011` and `c221b7424` exist on the worktree branch.
- All modified files exist.
