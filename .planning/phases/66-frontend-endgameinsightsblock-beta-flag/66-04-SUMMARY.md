---
phase: 66-frontend-endgameinsightsblock-beta-flag
plan: 04
subsystem: frontend
tags: [frontend, integration, endgames-page, insights, react, tanstack-query]

# Dependency graph
requires:
  - phase: 66-frontend-endgameinsightsblock-beta-flag
    provides: "Plan 02 — useEndgameInsights mutation hook + EndgameInsightsResponse/SectionId types; Plan 03 — EndgameInsightsBlock self-gating top-card component with UseMutationResult-prop contract"
provides:
  - "frontend/src/pages/Endgames.tsx — top-level integration of useEndgameInsights + EndgameInsightsBlock mounted at top of statisticsContent"
  - "SectionInsightSlot — module-level helper rendering per-section insights (headline + 0-2 bullets) inside each H2 group; returns null when no matching section_id"
  - "4 data-testids for the automation harness: insights-section-overall, insights-section-metrics_elo, insights-section-time_pressure, insights-section-type_breakdown"
affects: [67 (validation & beta rollout — full UI surface now available for end-to-end admin-impersonation validation loop)]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Parent-owned mutation state + sibling slot subscription: Endgames.tsx holds the single useEndgameInsights mutation and the rendered/reportFilters snapshot; EndgameInsightsBlock + 4 SectionInsightSlot instances all observe the same state without a context provider."
    - "Ride-along H2 suppression: per-section insight slots are placed inside the same conditional branches as their matching H2 (showPerfSection, {scoreGapData && ...}, {(showClockPressure || showTimePressureChart) && ...}, statsData.categories.length > 0). A suppressed H2 automatically suppresses its slot — D-05 with zero extra guard logic."
    - "Silent mutation catch for mutateAsync: `catch {}` in handleGenerateInsights prevents unhandled-promise-rejection warnings; global MutationCache.onError in lib/queryClient.ts handles Sentry capture per CLAUDE.md §Frontend Rules."
    - "O(1) section lookup: build `Record<SectionId, {headline, bullets} | null>` once per render, each slot indexes by its own SectionId. No .find() scans in the render tree."

key-files:
  created: []
  modified:
    - frontend/src/pages/Endgames.tsx

key-decisions:
  - "SectionInsightSlot placed at module level (below EndgamesPage export) rather than nested inside the component. Matches the existing convention in this file — EndgamePerformanceSection, ScoreGapTimelineChart, EndgameScoreGapSection etc. are all external modules imported at the top; inlining a second component definition inside EndgamesPage would have been inconsistent."
  - "Slot A (overall) positioned AFTER the Accordion and BEFORE the first chart card. The Accordion is the 'Endgame statistics concepts' collapsible info panel, not a chart card. Plan explicitly specified this placement — insight reads naturally as introductory text above the quantitative charts."
  - "sectionBySection built unconditionally every render, populated only when `renderedInsights && !insightsMutation.isError`. Keeps the render path branch-free and the lookup O(1)."
  - "Unconditional `useEndgameInsights()` call at page level. Safe for non-beta users because (a) no network request fires until Generate is clicked, (b) EndgameInsightsBlock returns null for non-beta users, so the Generate button never renders, and (c) `renderedInsights` stays null so all 4 slots render null. Non-beta layout is byte-identical."

patterns-established:
  - "Parent-owned mutation state for components that need to drive sibling renders — one mutation call, one rendered snapshot, multiple observers (top card + per-section slots) without context."
  - "H2-ride-along slot suppression — anchoring per-section UI inside the same conditional as its matching H2 means suppression rules are expressed once (at the H2) and inherited by the slot."

requirements-completed: [INS-01, INS-02, INS-03]

# Metrics
duration: ~4min
completed: 2026-04-22
---

# Phase 66 Plan 04: Endgames.tsx — EndgameInsightsBlock + per-section slot integration

**Wired useEndgameInsights mutation + EndgameInsightsBlock into Endgames.tsx with parent-owned state, mounted the block at the top of statisticsContent, and added 4 SectionInsightSlot instances observing the same rendered report inside their matching H2 groups.**

## Performance

- **Duration:** ~4 min
- **Started:** 2026-04-22T05:43:26Z
- **Completed:** 2026-04-22T05:47:05Z
- **Tasks:** 1
- **Files modified:** 1

## Accomplishments

- Imported `EndgameInsightsBlock`, `useEndgameInsights`, and `EndgameInsightsResponse` / `SectionId` types into `Endgames.tsx`
- Added parent-owned mutation state at page level: `insightsMutation`, `renderedInsights`, `insightsReportFilters` — the single source of truth observed by both the top-card component and the 4 per-section slots
- `handleGenerateInsights` callback: calls `insightsMutation.mutateAsync(appliedFilters)`; on success captures the report + filter snapshot; on error leaves state unchanged (block reads `mutation.isError` directly). Silent `catch {}` — global `MutationCache.onError` in `lib/queryClient.ts` handles Sentry per CLAUDE.md §Frontend Rules
- Built `sectionBySection` O(1) lookup keyed by `SectionId`; populated only when `renderedInsights && !insightsMutation.isError`
- Mounted `<EndgameInsightsBlock ... />` at the top of `statisticsContent` above the `{overviewLoading ? ...}` ternary. Self-gating: returns null for non-beta users so the page layout is byte-identical for them
- Inserted 4 `<SectionInsightSlot ... />` instances inside their matching H2 groups:
  - Slot A (`overall`): after `</Accordion>`, before the first chart card in the Endgame Overall Performance H2 block (rides `showPerfSection`)
  - Slot B (`metrics_elo`): after `<h2>Endgame Metrics and ELO</h2>`, before the EndgameScoreGapSection card (rides `{scoreGapData && ...}`)
  - Slot C (`time_pressure`): after `<h2>Time Pressure</h2>`, before both nested subguards (rides `{(showClockPressure || showTimePressureChart) && ...}`)
  - Slot D (`type_breakdown`): after `<h2>Endgame Type Breakdown</h2>`, before the EndgameWDLChart card (rides `statsData.categories.length > 0`)
- Added module-level `SectionInsightSlot` helper: renders `data-testid="insights-section-{section_id}"` div with headline `<p>` + 0-2 bullet `<ul>`; returns null when `data` is null
- D-05 ("suppressed H2 drops its matching SectionInsight") satisfied by placement alone — each slot lives inside the same conditional branch as its H2, so any H2 suppression transitively suppresses the slot
- Zero `Sentry.captureException` calls added (only a comment reference to the global MutationCache handler)
- All verification gates pass: `npx tsc --noEmit` 0 errors, `npm run lint` 0 errors (3 pre-existing coverage warnings), `npm run knip` clean, `npm test` 97/97 pass, `npm run build` succeeds

## Task Commits

1. **Task 1: Add insights hook + state + handlers + SectionInsightSlot + 4 slots to Endgames.tsx** — `7a6f029` (feat)

_Note: The plan marks the task `tdd="true"`, but its `action` template contains no new test files and the `acceptance_criteria` requires only tsc/lint/knip + the existing full FE suite to pass. Plan 03 already ships 11 render tests for `EndgameInsightsBlock`; Plan 04's integration surface (mounting + slot insertion) is a thin wiring layer whose correctness is witnessed by the full-suite green + manual verification in Phase 67. No additional unit tests authored._

## Files Created/Modified

- `frontend/src/pages/Endgames.tsx` — MODIFIED. Added 3 new imports (EndgameInsightsBlock, useEndgameInsights, EndgameInsightsResponse/SectionId types), 3 pieces of parent-owned state (`insightsMutation`, `renderedInsights`, `insightsReportFilters`), `handleGenerateInsights` useCallback, `sectionBySection` O(1) lookup, 1 `<EndgameInsightsBlock />` mount point at top of `statisticsContent`, 4 `<SectionInsightSlot />` insertions inside matching H2 groups, and a module-level `SectionInsightSlot` helper component. +80 lines / -0 lines. No behavior change for non-beta users.

## Decisions Made

- **Module-level `SectionInsightSlot` helper.** Placed below the `EndgamesPage` export rather than nested inside. Matches the existing convention in this file — all sibling chart sections (`EndgamePerformanceSection`, `ScoreGapTimelineChart`, `EndgameScoreGapSection`, `EndgameClockPressureSection`, etc.) live in sibling modules imported at the top. A nested inline component would be inconsistent.
- **Slot A positioned after the Accordion, before the first chart card.** The Accordion is the "Endgame statistics concepts" collapsible info panel, not a chart card. Per plan, the slot goes above the first chart card — an initial placement before the Accordion was reverted in favor of the plan-specified location.
- **Unconditional `useEndgameInsights()` hook call at page level.** The hook sets up a TanStack Query mutation object but does NOT fire a network request until `mutateAsync` is called. Since `EndgameInsightsBlock` self-gates on `profile.beta_enabled`, non-beta users never see the Generate button, so `mutateAsync` never runs. The hook call is free for non-beta users.
- **Silent `catch {}` in `handleGenerateInsights`.** `mutateAsync` rejects on mutation failure. Without `catch`, Node/browser would log an unhandled-promise-rejection warning. The `catch` block is intentionally empty because (a) `mutation.isError` already drives the error UI, and (b) the global `MutationCache.onError` in `lib/queryClient.ts` has already captured to Sentry. Adding a local `Sentry.captureException` here would double-report.

## Deviations from Plan

None — plan executed exactly as written. One intra-task self-correction (Slot A was initially inserted before the Accordion, then moved to after the Accordion per the plan's explicit placement spec) but this happened inside Task 1 before the commit and is not a scope deviation.

## Issues Encountered

None.

## User Setup Required

None — no external services, environment variables, or database migrations introduced.

## Next Phase Readiness

- Phase 66 is now feature-complete. The full Endgame Insights UI surface is live on the Endgames.tsx `stats` tab for beta-flagged users:
  - Top-of-tab card: hero → skeleton → overview + Regenerate → error state machine
  - 4 inline per-section insight slots above each chart group
  - Outdated indicator when filters change after a successful generate
  - Stale banner when the 200-envelope reports `stale_rate_limited`
  - 429 rate-limit error with minute-rounded retry copy
- Phase 67 (validation & beta rollout) can now run:
  1. Flip `users.beta_enabled = true` for an admin-impersonation target via direct DB write (Plan 66-01 BE surface)
  2. Click through the 5 states on the live Endgames page via admin impersonation
  3. Exercise the full validation loop from `66-VALIDATION.md §Manual-Only Verifications`
- All 4 new `data-testid` selectors (`insights-section-{overall,metrics_elo,time_pressure,type_breakdown}`) join the 9 Plan 03 selectors (`insights-block`, `insights-overview`, `btn-generate-insights`, `btn-regenerate-insights`, `btn-insights-retry`, `insights-outdated-indicator`, `insights-stale-banner`, `insights-error`, `insights-skeleton`) — 13 total stable selectors for Phase 67 automation.
- Knip stays clean: Plan 02's `useEndgameInsights` hook and Plan 02's `EndgameInsightsResponse` / `SectionId` exports now have a production consumer. Plan 03's `EndgameInsightsBlock` has a production consumer.

## Self-Check: PASSED

**Files created (none) / modified (verified via `git diff --stat`):**
- MODIFIED: frontend/src/pages/Endgames.tsx (+80 / -0)

**Commit exists (verified via `git log`):**
- FOUND: 7a6f029 — feat(66-04): wire EndgameInsightsBlock + per-section slots into Endgames.tsx

**Verification commands passed:**
- `cd frontend && npx tsc --noEmit` — 0 errors
- `cd frontend && npm run lint` — 0 errors (3 pre-existing coverage/ warnings, unrelated)
- `cd frontend && npm run knip` — clean
- `cd frontend && npm test -- --run` — 97 tests across 8 files, all pass
- `cd frontend && npm run build` — production build succeeds
- All 11 plan grep acceptance criteria pass (imports, hook call, state setters, mount point, 4 sectionId slots, testid interpolation)
- `grep -c Sentry frontend/src/pages/Endgames.tsx` — 1 match (comment-only, not a `Sentry.captureException` call)

---
*Phase: 66-frontend-endgameinsightsblock-beta-flag*
*Completed: 2026-04-22*
