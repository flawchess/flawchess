---
phase: 238-endgame-stats-percentile-first
plan: 03
subsystem: ui
tags: [react, typescript, tanstack-query, percentiles, endgames, radix-popover, useSyncExternalStore]

requires:
  - phase: 238-01
    provides: GET /api/endgames/ranked-stats payload (RankedTcStats, RankedMetricOut, rank status matrix, popover CI/p statistics)
provides:
  - "Ranked payload TS mirror, endgameApi.getRankedStats and useEndgameRankedStats (queryKey ['endgameOverview','ranked'])"
  - "useEndgameStatsTc: shared synced TC store with D-12 default, D-13 localStorage restore, D-14 TC list"
  - "TcSwitch, PercentileBar (+ RankStatusLine status slots), RankedMetricPopover, RankedMetricRow, rankedMetrics vocabulary module"
  - "OverallSection (two per-TC cards, ranked timelines), ComparedToPeersCard (D-00g), D-10 empty state"
  - "EndgameStatsTab extracted from EndgamesPage, owning the insights state, concepts accordion and the transitional overview sections"
affects: [238-05, 238-06, 238-07]

plan_head_before: 9b1a2fd4f4e7e7a5c13b55378cdf761487a82384
plan_head_after: 7b2ccfae8144e75d726e5c073653494514c95566
actuals:
  tokens: 29000
  tasks: 3
  commits: 5

tech-stack:
  added: []
  patterns:
    - "Module store + useSyncExternalStore holding only the user's choice; effective TC derived during render so restore/fallback never write state or fire analytics"
    - "Merged Radix hover popover shell with status-aware body; status copy owned by one RankStatusLine component reused by the bar slot and the popover"
    - "Test lookups via queryByTestId + expect (one-line failure message) so TAP RED evidence stays classifiable"

key-files:
  created:
    - frontend/src/hooks/useEndgameStatsTc.ts
    - frontend/src/hooks/__tests__/useEndgameStatsTc.test.ts
    - frontend/src/components/endgames/EndgameStatsTab.tsx
    - frontend/src/components/endgames/EndgameStatsTab.test.tsx
    - frontend/src/components/endgames/stats/rankedMetrics.ts
    - frontend/src/components/endgames/stats/rankedFixtures.ts
    - frontend/src/components/endgames/stats/TcSwitch.tsx
    - frontend/src/components/endgames/stats/PercentileBar.tsx
    - frontend/src/components/endgames/stats/PercentileBar.test.tsx
    - frontend/src/components/endgames/stats/RankedMetricPopover.tsx
    - frontend/src/components/endgames/stats/RankedMetricPopover.test.tsx
    - frontend/src/components/endgames/stats/RankedMetricRow.tsx
    - frontend/src/components/endgames/stats/OverallSection.tsx
    - frontend/src/components/endgames/stats/ComparedToPeersCard.tsx
    - frontend/src/components/endgames/stats/ComparedToPeersCard.test.tsx
  modified:
    - frontend/src/types/endgames.ts
    - frontend/src/api/client.ts
    - frontend/src/hooks/useEndgames.ts
    - frontend/src/lib/analytics.ts
    - frontend/src/lib/theme.ts
    - frontend/src/pages/Endgames.tsx
    - frontend/src/pages/__tests__/Endgames.readinessGate.test.tsx
    - frontend/src/pages/__tests__/Endgames.overallPerformance.test.tsx

key-decisions:
  - "TC store keeps only the user's choice (null until clicked); selectedTc = stored if in payload else pickDefaultTc(tcs), derived in render, so no effect writes and no analytics on restore"
  - "A failed localStorage write still keeps the choice in memory for the session (an ignored click would make the switch feel broken)"
  - "RankStatusLine is exported from PercentileBar.tsx and reused by the popover, so the below-floor/pending/not-ranked copy lives in one file"
  - "Peer-card rows and the Overall rows share RankedMetricPopover with testid ranked-metric-{slug}-tc-{tc}; popoverTargetFromTestId collapses the TC, giving one analytics row per metric"
  - "Rates render as whole percents like every gap (plan said plain percent); CI bounds are one-decimal, signed for gaps and plain for rates"
  - "EndgameStatsTab takes appliedFilters/setAppliedFilters and the overview as transitional props (insights cache is still filter-keyed until 238-07; Metrics/Time Pressure/Type still read the overview until 238-05)"

patterns-established:
  - "Stats-tab components never import the filter store; only the transitional Tab receives filter props"
  - "Section anchors: SECTION_ID_* constants in rankedMetrics.ts, ids on the section roots; peer rows scrollIntoView then trackFeature('action', endgame-peer-row) from the click handler only"

requirements-completed: [D-00a, D-00c, D-00g, D-00h, D-00i, D-01, D-03, D-08, D-09, D-10, D-11, D-12, D-13, D-14]

coverage:
  - id: D1
    description: "Stats tab reads GET /api/endgames/ranked-stats without any filter argument and renders the Overall section per TC (two cards with the unchanged timelines on the selected TC's ranked series)"
    requirement: "D-01"
    verification:
      - kind: unit
        ref: "frontend/src/components/endgames/EndgameStatsTab.test.tsx#calls the ranked hook without any filter argument"
        status: pass
      - kind: unit
        ref: "frontend/src/components/endgames/EndgameStatsTab.test.tsx#feeds the timelines from the selected TC (D-03)"
        status: pass
      - kind: integration
        ref: "frontend/src/pages/__tests__/Endgames.overallPerformance.test.tsx"
        status: pass
    human_judgment: false
  - id: D2
    description: "One synced TC switch per section with D-12 default, D-13 localStorage restore (never breaks rendering) and the D-14 TC list"
    requirement: "D-12"
    verification:
      - kind: unit
        ref: "frontend/src/hooks/__tests__/useEndgameStatsTc.test.ts"
        status: pass
      - kind: unit
        ref: "frontend/src/components/endgames/EndgameStatsTab.test.tsx#switching TC in one section switches every section (D-00h)"
        status: pass
    human_judgment: false
  - id: D3
    description: "Percentile bar with 25-75 band, median tick, banded dot, uncolored value, no icon; below-floor / pending / not-ranked slots without a dot"
    requirement: "D-00a"
    verification:
      - kind: unit
        ref: "frontend/src/components/endgames/stats/PercentileBar.test.tsx"
        status: pass
      - kind: unit
        ref: "frontend/src/components/endgames/stats/RankedMetricPopover.test.tsx#RankedMetricRow status slots (D-09, D-11)"
        status: pass
    human_judgment: false
  - id: D4
    description: "Merged popover: WHAT + sign, percentile statement, four disclosures (three anchor branches), greyed n / 95% CI / p footer below a separator"
    requirement: "D-00c"
    verification:
      - kind: unit
        ref: "frontend/src/components/endgames/stats/RankedMetricPopover.test.tsx"
        status: pass
    human_judgment: true
    rationale: "Copy tone and the greyed footer contrast on the light popover surface need a visual pass; no test asserts readability"
  - id: D5
    description: "Compared-to-peers dot plot: 11 ranked metrics in three groups, non-ranked rows omitted, hidden for an unranked TC, row link fires one action event"
    requirement: "D-00g"
    verification:
      - kind: unit
        ref: "frontend/src/components/endgames/stats/ComparedToPeersCard.test.tsx"
        status: pass
    human_judgment: true
    rationale: "Desktop grid and mobile stacking (bar on its own line below sm) are layout choices verified only by eye"
  - id: D6
    description: "Empty ranked sample shows one empty state naming rated games, human opponents, opponents within 100 Elo and the last 36 months, linking to the Games tab"
    requirement: "D-10"
    verification:
      - kind: unit
        ref: "frontend/src/components/endgames/EndgameStatsTab.test.tsx#shows exactly one empty state that names what qualifies and links to the Games tab"
        status: pass
    human_judgment: false

duration: 21min
completed: 2026-10-11
status: complete
---

# Phase 238 Plan 03: Frontend ranked foundation Summary

**Percentile-first Stats tab foundation: synced persisted TC switch, percentile bar with honest status slots, one merged popover per metric, the per-TC Overall section on ranked data, the compared-to-peers dot plot and the D-10 empty state, with the Stats tab extracted from EndgamesPage into EndgameStatsTab.**

## Performance

- **Duration:** about 21 min
- **Started:** 2026-10-11T12:45Z (approx)
- **Completed:** 2026-10-11T13:06Z
- **Tasks:** 3 (1 tracer, 2 TDD)
- **Files:** 23 touched (15 created, 8 modified)

## Accomplishments

- `GET /endgames/ranked-stats` is wired end to end (types, `endgameApi.getRankedStats`, `useEndgameRankedStats` under the `['endgameOverview']` prefix so the import-completion invalidations keep working, Tier-2 `enabled` gate, no filter argument).
- `useEndgameStatsTc` is a module store (`useSyncExternalStore`) shared by every section's `TcSwitch`. `pickDefaultTc` implements D-12 (most ranked games among at-or-above-anchor-floor TCs, ties to the faster TC). A stored choice is validated against the TC union and the payload list; a throwing `localStorage` read or write never breaks rendering. Analytics fire only from the switch click.
- `PercentileBar`: track, 25-75 band, median tick, dot red below 25 / blue 25-75 / green above 75, ordinal in the dot color, no icon. Cells without a percentile show their slot line instead: "Not enough games to rank yet (18 of 30)", "Analyzing your games, this fills in once evaluations finish", "Not ranked yet". There is no drift or updating state (D-08).
- `RankedMetricPopover`: WHAT + sign, "Better than X% of ~{anchor}-rated {tc} players." (X clamped 1..99), four disclosures with the three anchor-composition branches, then a separator and a greyed `n = ... · 95% CI ... · p = ...` footer. Stats vocabulary lives only in the footer.
- `OverallSection`: two cards (score with vs. without an endgame + Endgame Score Gap; entry eval to expected to actual + Eval Score Gap) for the selected TC, then the Score Gap over Time and ELO timelines fed from that TC's ranked series, then the narration slot.
- `ComparedToPeersCard`: every ranked metric of the selected TC on one 0-100 axis in three groups, each row an in-page link (scrollIntoView + `trackFeature('action', endgame-peer-row)`); hidden when the TC has no ranked metric.
- `EndgameStatsTab` now owns the insights mutation/cache/cached-query state, the import-completion cache clear, `SectionInsightSlot`, the concepts accordion and the transitional Metrics / Time Pressure / Type sections; `EndgamesPage` lost those branches (538 lines, was 1117).

## Task Commits

1. **Task 1 (tracer): ranked Endgame Score Gap card end-to-end** - `b959ede65` (feat)
2. **Task 2 RED: failing popover / status-slot tests** - `31432335c` (test)
3. **Task 2 GREEN: popover, status slots, entry-advantage card** - `e4b3cde7f` (feat)
4. **Task 3 RED: failing peers-card / timeline / empty-state tests** - `2da6c4427` (test)
5. **Task 3 GREEN: peers card, ranked timelines, empty state** - `7b2ccfae8` (feat)

**Plan metadata:** committed separately (docs: complete plan).

## TDD Gate Compliance

- **Tracer gate (Task 1):** `<verify>` (PercentileBar + TC hook + page tests, then `npm run build`) re-run green before expanding; "Tracer verified end-to-end, expanding".
- **Task 2 RED:** 14 of 15 tests failed in `RankedMetricPopover.test.tsx` against render-nothing scaffolds (`RankedMetricPopover` returned only its children, `RankedMetricRow` returned null). `gsd-tools check tdd-red-evidence` returned `RED_EVIDENCE_OK` for the target "orders WHAT, percentile sentence, four disclosures, separator, footer" (TAP, `NO_COLOR=1`). Semantic assessment: the target failed on the `element ranked-metric-score-gap-tc-rapid present` expectation because the scaffold renders no trigger, which is the planned reason. One vacuous pass (the no-drift-state test) is expected against an empty scaffold. GREEN made all 15 pass.
- **Task 3 RED:** 7 of 10 tests failed (peers card scaffold renders nothing, timelines still read the filtered overview, empty state had no testid). `RED_EVIDENCE_OK` for the target "switching TC in one section switches every section (D-00h)"; semantic assessment: the peers-card switch is absent, the intended reason. The default-TC, filter-free-hook and below-floor-hidden tests held already (Task 1 / scaffold). GREEN made all pass.
- **Evidence handling:** testing-library `getBy*` errors print a multi-line DOM dump that the TAP classifier rejects as non-TAP data, so the tests look elements up with `queryByTestId` + `expect(el, 'element X present').not.toBeNull()` (one-line message). The evidence files were scratch and are not committed.
- **Mutation check (GREEN):** dropping the `status === 'ranked'` filter in `ComparedToPeersCard` failed "omits rows whose metric is not ranked" and "is not rendered when no metric ... is ranked"; reverted.
- No REFACTOR commit was needed.

## Files Created/Modified

See `key-files`. The ranked contract mirrors `app/schemas/endgames.py` 1:1 in `frontend/src/types/endgames.ts`; `lib/theme.ts` gained `PERCENTILE_TRACK`, `PERCENTILE_TYPICAL_BAND`, `PERCENTILE_MEDIAN_TICK`; `lib/analytics.ts` gained `'endgame-stats-tc'` (option-change, value `TimeControlBucket`) and `'endgame-peer-row'` (action).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Extra test-helper module `rankedFixtures.ts`**
- **Found during:** Task 1
- **Issue:** the hook test, popover test, peers test, tab test and page tests all need ranked-payload fixtures; the plan's file list has no shared home for them.
- **Fix:** `frontend/src/components/endgames/stats/rankedFixtures.ts` (imported only by tests, type-checked by `tsc -b`, reachable for knip).
- **Commit:** `b959ede65`

**2. [Rule 3 - Blocking] Dead tail empty-state helpers removed from `Endgames.tsx`**
- **Found during:** Task 1
- **Issue:** `EndgamesTailEmptyState` / `shouldShowEndgamesNoHumanRatedGames` only served the old Stats body; once the Stats tab moved out they were unused (eslint/`noUnusedLocals`). Their `useGameCountValue` call and imports went with them, and the readiness-gate test dropped its `useGameCount` mock.
- **Fix:** deleted them; the D-10 empty state replaces them for the Stats tab (the Games tab never used them).
- **Commit:** `b959ede65`

**3. [Rule 2 - Missing critical] Section anchor ids on the transitional headings**
- **Found during:** Task 3
- **Issue:** peer-row links to `endgame-section-metrics` / `endgame-section-time-pressure` would be dead until plan 238-05 builds those sections.
- **Fix:** `id` + `scroll-mt-16` on the existing "Endgame Metrics" and "Time Pressure" `h2`s (238-05 moves the ids onto its section roots).
- **Commit:** `7b2ccfae8`

**4. [Rule 2 - Missing critical] Inline `LoadError` for an overview error**
- **Found during:** Task 1 (the old page showed a centered LoadError on `overviewError`)
- **Fix:** the Tab renders `<LoadError variant="inline" resource="endgame data" />` in place of the transitional sections when the overview query fails, and a centered "endgame stats" LoadError when the ranked query fails (frontend/CLAUDE.md `isError` rule).
- **Commit:** `b959ede65`, `7b2ccfae8`

### Execution notes (no impact on scope)

- The D-10 empty state was written in Task 1 (the Tab needs the `tcs.length === 0` branch to render at all); Task 3 added its testid and the tests.
- `METRIC_SECTION_ID` / `PEER_GROUPS` were held back to Task 3 so Task 2's knip gate stays green (they were unused until the peers card).
- Rate values render as whole percents (the plan said "plain percent"); CI bounds use one decimal.
- The plan's overrun fallback (split at the primitives seam) was not needed.

**Total deviations:** 4 small auto-fixes (2 Rule 3, 2 Rule 2). **Impact:** none on the contract plans 238-05/06/07 build on.

## Authentication Gates

None.

## Issues Encountered

- Desktop and mobile layouts each mount `statisticsContent`, so `EndgameStatsTab` (and its insights state) is mounted twice, as before for the DOM but now with separate mutation state per instance. A generated report shows in the visible layout; after a breakpoint resize the other instance only picks it up through the cached-report query. Harmless in practice, and plan 238-07 collapses the insights state to one filter-free report.
- The concepts accordion copy still describes percentile badges and cross-TC weighted chips, and the ELO timeline's own empty state still says "loosen the recency filter"; plan 238-05 rewrites the accordion, and the ELO component was left untouched per D-00i.
- Verification: `npm run lint`, `npm run build`, `npm run knip` clean; full `npm test` 328 files / 5535 tests passing.

## Known Stubs

None. The transitional sections (Metrics, Time Pressure, Type) intentionally still read the filtered overview until plan 238-05; that is the planned seam, not a stub.

## Threat Flags

None. The only new surface is the existing authenticated `GET /endgames/ranked-stats` and a user-writable `localStorage` key, both in the plan's threat model (T-238-07 validated against the TC union and payload list with try/catch; T-238-08 analytics send only the enumerated `TimeControlBucket` and fixed action target).

## Next Phase Readiness

Ready for 238-05 (Metrics / Time Pressure / Type sections on the ranked payload, filter-free Tab, concepts copy) and 238-07 (filter-free insights). 238-06 must still delete the unmounted Overall components (`EndgameOverallPerformanceSection`, `EndgameOverallCard`, `EndgameOverallEntryCard`, their tests) and sweep the retired-name comments (e.g. `types/endgames.ts` line ~395 PercentileChip comment).

## Self-Check: PASSED

- Created files exist (EndgameStatsTab, hook, store test, all `stats/` modules and tests)
- Commits `b959ede65`, `31432335c`, `e4b3cde7f`, `2da6c4427`, `7b2ccfae8` are ancestors of HEAD
- Acceptance greps: ranked queryKey, `'endgame-stats-tc'`, `'endgame-peer-row'`, zero `trackFeature` in the TC hook, zero `useFilterStore` in `components/endgames`, no retired-component names in new code, "36 months" in the empty-state copy
