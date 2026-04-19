---
phase: 57-endgame-elo-timeline-chart
plan: 02
subsystem: frontend
tags: [endgame, elo, frontend, timeline, recharts, chart, react]

# Dependency graph
requires:
  - phase: 57-endgame-elo-timeline-chart
    plan: 01
    provides: /api/endgames/overview extended with endgame_elo_timeline field (EndgameEloTimelineResponse with combos[] + timeline_window)
provides:
  - EloComboKey (TS literal union, 8 keys)
  - EndgameEloTimelinePoint / EndgameEloTimelineCombo / EndgameEloTimelineResponse TS mirrors
  - EndgameOverviewResponse.endgame_elo_timeline field on the TS interface
  - ELO_COMBO_COLORS record (8 combos x {bright, dark} oklch strings)
  - niceEloAxis(values) utility with 6 vitest cases
  - EndgameEloTimelineSection component (paired-line Recharts chart, combo-level legend toggle, locked info popover, tooltip, empty + error + loading branches)
  - Endgame ELO h2 container on the Endgames -> Stats tab (shared section; Phase 56 breakdown table will join here)
affects: [56 endgame-elo-breakdown (will reuse the new Endgame ELO h2 container), future chart components that want niceEloAxis or ELO_COMBO_COLORS]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Custom <ChartLegend content={...}/> legend renderer with per-item <button> + data-testid, because Recharts does not propagate custom props to <Line> SVG"
    - "flatMap-not-Fragment pattern inside Recharts chart children (Recharts 2.15.x React.Children traversal is unreliable across Fragment wrappers)"
    - "Component-level error / loading / empty / chart branches owned by the section so CLAUDE.md's isError rule can surface LOCKED copy without depending on page-level error-branch placement"
    - "Type-only import `import type { EloComboKey } from '@/types/endgames'` in theme.ts — no runtime cycle; bundler verified via npm run build"
    - "Stable COMBO_LABELS + FALLBACK_COMBO_COLOR pattern to satisfy noUncheckedIndexedAccess without littering the component with `as EloComboKey` casts"

key-files:
  created:
    - frontend/src/components/charts/EndgameEloTimelineSection.tsx
  modified:
    - frontend/src/types/endgames.ts
    - frontend/src/lib/theme.ts
    - frontend/src/lib/utils.ts
    - frontend/src/lib/utils.test.ts
    - frontend/src/pages/Endgames.tsx

key-decisions:
  - "Lines emitted via flatMap rather than a per-combo <React.Fragment> so Recharts 2.15.x's React.Children traversal reliably discovers every <Line> instance for scale computation"
  - "Custom legend renderer owns the endgame-elo-legend-{combo_key} testid on <button> elements (one per combo, not per line) — Recharts strips data-testid from <Line> SVG output"
  - "legendType=\"none\" on the dark (Actual ELO) Line is retained defensively so a future ChartLegendContent swap cannot reintroduce a 16-entry default legend"
  - "Component-owned isError branch renders the locked `endgame-elo-timeline-error` copy so CLAUDE.md's isError rule is satisfied regardless of the page-level error branch placement (the two paths do not conflict: page-level catches whole-response failure; component-level catches the sub-payload failure surface)"
  - "Animate-pulse skeleton at h-72 during isLoading keeps layout stable when data arrives; matches the MoveExplorer skeleton style in the codebase"

patterns-established:
  - "Pattern 1: EndgameEloTimelineSection props contract — accepts `data | undefined`, `isLoading`, `isError` so the component owns all 4 display branches; future sections whose empty/error UI needs to live inside the component can copy this shape"
  - "Pattern 2: flatMap-not-Fragment inside Recharts chart children — enshrined as an executor rule in the plan and followed in code; document for any future multi-line combo chart"
  - "Pattern 3: Custom legend via `<ChartLegend content={customDOM} />` with per-item testid on <button> elements — reusable for any multi-series chart that needs browser-automation hooks on the legend surface"

requirements-completed: [ELO-05]

# Metrics
duration: 6min
completed: 2026-04-18
---

# Phase 57 Plan 02: Endgame ELO — Frontend Timeline Chart Summary

**Frontend rendering of the Plan 01 `endgame_elo_timeline` field: paired-line Recharts chart per (platform, time_control) combo with combo-level legend toggle, locked info popover, and component-owned loading/error/empty branches inside a new `Endgame ELO` h2 container on the Endgames → Stats tab.**

## Performance

- **Duration:** ~6 min (2 atomic task commits + gate runs)
- **Started:** 2026-04-18T17:36:xxZ (approx)
- **Completed:** 2026-04-18T17:42:34Z
- **Tasks:** 2 executed + 1 checkpoint auto-approved (auto mode)
- **Files created:** 1
- **Files modified:** 5

## Accomplishments

- Closed ELO-05 SC-1 (paired lines per combo), SC-2 (filter-responsive via shared `useEndgameOverview`), and SC-3 (cold-start empty state keeps info popover visible) at the frontend layer.
- Extended the TypeScript response contract to mirror the Plan 01 Pydantic schema (`EloComboKey`, `EndgameEloTimelinePoint`, `EndgameEloTimelineCombo`, `EndgameEloTimelineResponse`) and added the `endgame_elo_timeline` field to `EndgameOverviewResponse`.
- Added `ELO_COMBO_COLORS` to `frontend/src/lib/theme.ts` with the 8 locked oklch pairs from 57-UI-SPEC.md (bright Endgame ELO + dark Actual ELO per combo — two tones instead of an opacity modifier so hue reading stays clean on the dark charcoal surface).
- Promoted the inline tick algorithm from `RatingChart.tsx` into `niceEloAxis(values)` in `frontend/src/lib/utils.ts` with step candidates `[50, 100, 200, 500]` per UI-SPEC §Axes. Added 6 vitest cases covering empty, all-equal, small/medium/large ranges, and non-aligned values.
- Built `EndgameEloTimelineSection` (~320 lines) implementing paired-line chart with combo-level legend toggle, 4-paragraph LOCKED info popover, tooltip with per-combo gap + games-in-window, and 4 display branches (error / loading / empty / chart).
- Wired the new section into `frontend/src/pages/Endgames.tsx` under a new `Endgame ELO` h2 block positioned AFTER `Endgame Type Breakdown`. The section is emitted unconditionally within the `statsData.categories.length > 0` branch and owns its own error/loading/empty swaps internally.

## Task Commits

1. **Task 1: Add Endgame ELO timeline TS types, ELO_COMBO_COLORS, niceEloAxis helper** — `97152f5` (feat)
2. **Task 2: Add EndgameEloTimelineSection component + wire into Endgames page** — `f24c20b` (feat)
3. **Task 3: Human-verify checkpoint** — auto-approved under auto mode; automated gates (lint, tsc --noEmit, knip, npm run build, full vitest suite 83/83) all green, acceptance-criteria grep checks all satisfied. Live visual smoke to be run by user post-merge.

## Files Created/Modified

- `frontend/src/components/charts/EndgameEloTimelineSection.tsx` — NEW. Component with loading skeleton, error UI (LOCKED copy + `endgame-elo-timeline-error` testid), empty state (LOCKED copy + `endgame-elo-timeline-empty` testid + info popover remains visible), and chart branch. Uses `flatMap` to emit 2N `<Line>` elements as direct children of `<LineChart>` so Recharts discovers them; custom legend renderer carries the `endgame-elo-legend-{combo_key}` testid on one `<button>` per combo; tooltip filters hidden combos and shows per-combo endgame/actual/gap/games-in-window blocks.
- `frontend/src/types/endgames.ts` — appended `EloComboKey` literal union (8 keys), `EndgameEloTimelinePoint`, `EndgameEloTimelineCombo`, `EndgameEloTimelineResponse`; added `endgame_elo_timeline: EndgameEloTimelineResponse` field on `EndgameOverviewResponse`.
- `frontend/src/lib/theme.ts` — added `ELO_COMBO_COLORS: Record<EloComboKey, {bright, dark}>` with all 8 locked oklch pairs verbatim from UI-SPEC.
- `frontend/src/lib/utils.ts` — added `niceEloAxis(values: number[])` helper lifted from `RatingChart.tsx:54-106` with the UI-SPEC step set.
- `frontend/src/lib/utils.test.ts` — added a `describe('niceEloAxis')` block with 6 test cases (empty → auto fallback, all-equal → ±50 expansion, small/medium/large ranges, non-aligned values). Full `utils.test.ts` now 17/17 green.
- `frontend/src/pages/Endgames.tsx` — added `EndgameEloTimelineSection` import, `eloTimelineData = overviewData?.endgame_elo_timeline` destructure, and the new `Endgame ELO` h2 block + `data-testid="endgame-elo-timeline-section"` card wrapper after the Endgame Type Breakdown section.

## Verification Gates

All commands exited 0:

```bash
cd frontend
npm run lint         # 0 errors, 3 warnings (all in coverage/, pre-existing, out of scope)
npx tsc --noEmit     # 0 errors (noUncheckedIndexedAccess enforced)
npm test -- --run src/lib/utils.test.ts   # 17/17 pass
npm test             # 83/83 pass across 6 test files
npm run knip         # zero unused exports / unused deps
npm run build        # production build succeeds, prerenders 2 pages
```

Acceptance-criteria grep checks (all satisfied):

- `export function EndgameEloTimelineSection` → 1 match
- `ELO_COMBO_COLORS` refs → 2 (import + `getComboColors` lookup)
- `niceEloAxis` refs → 2 (import + useMemo call)
- `data-testid="endgame-elo-timeline-section"` in Endgames.tsx → 1
- `data-testid="endgame-elo-timeline-chart"` → 1
- `endgame-elo-timeline-info` → 1 (passed as `testId` prop to InfoPopover which renders `data-testid` on the trigger span — same pattern used by every sibling section)
- `data-testid="endgame-elo-timeline-empty"` → 1
- `data-testid="endgame-elo-timeline-error"` → 1
- `Failed to load Endgame ELO timeline` → 1 (LOCKED error heading)
- `endgame-elo-legend-` template literal → present on `<button>` elements
- `flatMap` → used for `<Line>` emission inside `<LineChart>` children
- Zero `<React.Fragment>` / `<></>` inside chart children (only match is the explanatory comment)
- LOCKED empty-state copy: `Not enough endgame games yet for a timeline.` + `Import more games or loosen the recency filter.` → both present
- `strokeWidth={2}` + `strokeDasharray="4 2"` → present for bright / dark lines respectively
- Only oklch literal in the component is `FALLBACK_COMBO_COLOR` (all other colors routed through `ELO_COMBO_COLORS`)

## Decisions Made

- **Component owns its own display branches.** The component accepts `data | undefined`, `isLoading`, `isError` and renders the appropriate UI internally — rather than the page wrapping it in `{showEloTimeline && <Section data={data} />}`. This makes the locked `endgame-elo-timeline-error` testid reachable and satisfies CLAUDE.md's `isError` rule structurally, irrespective of where the parent's error branch lives. The page-level error branch (lines 323-329 of `Endgames.tsx`) still handles the case where the whole overview response fails before any child renders — the two paths do not conflict.
- **flatMap over Fragment.** A `data.combos.flatMap((combo) => [<Line .../>, <Line .../>])` keeps every `<Line>` as a direct child of `<LineChart>`. Recharts 2.15.x's `React.Children.forEach` traversal is historically unreliable across Fragment wrappers (`<>` ... `</>` inside a `.map()`), and the plan called this out explicitly as a forbidden anti-pattern.
- **Custom legend for per-combo testid.** Recharts strips custom props (including `data-testid`) when rendering `<Line>` as SVG. To honor the locked `endgame-elo-legend-{combo_key}` testid, the legend is a fully custom DOM via `<ChartLegend content={renderLegend()} />` emitting one `<button>` per combo. The button handles the click-to-toggle and owns the testid.
- **Heading + info popover live inside the loading / empty branches.** Users with sparse data (cold start, narrow recency filter) still see the section heading and can open the info popover to read why they see no chart. This covers Pitfall 4 from 57-RESEARCH.md.
- **Type-only import of `EloComboKey` into `theme.ts`.** `import type { EloComboKey } from '@/types/endgames'` is bundler-hinted to not pull the full endgames module into the theme bundle. Verified via `npm run build` — no runtime cycle, no bundle-size regression.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] ESLint `no-unused-vars` on renamed `_payload` tooltip parameter**
- **Found during:** Task 2 lint gate (`npm run lint`)
- **Issue:** The plan's `<action>` pseudo-code destructured `{active, payload, label}` from the Recharts tooltip content prop, and I preserved `payload` as `_payload` (underscore prefix) signaling "intentionally unused". ESLint's `@typescript-eslint/no-unused-vars` rule in this codebase does NOT exempt the underscore-prefix convention, so it reported an error: `'_payload' is defined but never used`.
- **Fix:** Dropped the `payload` destructure entirely since the tooltip reads data from `chartData` (the already-shaped merged rows) keyed by the `label` x-axis value, not from `payload`. Changed the tooltip content signature from `({ active, payload: _payload, label }) => ...` to `({ active, label }) => ...`.
- **Files modified:** `frontend/src/components/charts/EndgameEloTimelineSection.tsx` (single line)
- **Verification:** `npm run lint` re-run, zero errors.
- **Committed in:** `f24c20b` (part of Task 2 commit — not a separate commit because the fix was caught at the Task 2 gate before the commit landed)

**Total deviations:** 1 auto-fixed (Rule 1, trivial lint config vs underscore-prefix convention). No other deviations from 57-UI-SPEC.md, 57-PATTERNS.md, or the plan's `<action>` blocks — all LOCKED copy, palette values, line styles, and testids applied verbatim.

## TDD Gate Compliance

This plan's frontmatter declares `type: execute` (not `type: tdd`), and the tasks were marked `tdd="true"` but executed as "tests-first for niceEloAxis" rather than separate RED/GREEN commits (the utility has a straightforward input-output contract and is covered by 6 cases in `utils.test.ts` committed alongside the implementation). The chart component has no unit tests in this plan — per the plan's `<verify>` block the gate is lint + tsc + knip + build + the human-verify checkpoint, not a component-level vitest. This is consistent with every other `charts/*Section.tsx` in the codebase, which rely on the integration tests in Plan 01 + manual visual verification for the rendering surface.

## Auth Gates

None. Phase 57 Plan 02 is a read-only rendering pass; the API endpoint is the existing `/api/endgames/overview` with the shared `current_active_user` dependency.

## Known Stubs

None. The component is wired end-to-end: it consumes the real `overviewData.endgame_elo_timeline` field returned by the Plan 01 backend, renders every LOCKED testid and copy string, and never falls through to placeholder text.

## Threat Flags

None. No new network endpoints, no new auth paths, no file access, no schema changes. The threat model's Rule-2 mitigation (T-57-09) for `ELO_COMBO_COLORS[combo_key as EloComboKey] ?? FALLBACK_COMBO_COLOR` is implemented verbatim in `getComboColors()`.

## Issues Encountered

- The `Edit` tool produced repeated `READ-BEFORE-EDIT REMINDER` system messages even though the files had been read within the session. All edits applied successfully regardless. No workaround needed beyond ignoring the false-positive reminders.
- Early in the session, several tool calls inside a large parallel batch were cancelled mid-flight due to a filesystem-lookup error on a non-existent directory, which invalidated the batch. The next iteration used sequential calls with explicit paths and completed cleanly.

## Self-Check: PASSED

**Files created/modified verified:**
- `.planning/phases/57-endgame-elo-timeline-chart/57-02-SUMMARY.md` — FOUND (this file, written last)
- `frontend/src/components/charts/EndgameEloTimelineSection.tsx` — FOUND
- `frontend/src/types/endgames.ts` — FOUND (EloComboKey + 3 interfaces + 1 field extension)
- `frontend/src/lib/theme.ts` — FOUND (ELO_COMBO_COLORS)
- `frontend/src/lib/utils.ts` — FOUND (niceEloAxis)
- `frontend/src/lib/utils.test.ts` — FOUND (6 new cases; 17/17 total pass)
- `frontend/src/pages/Endgames.tsx` — FOUND (import + destructure + h2 block + section usage)

**Commits verified in `git log`:**
- `97152f5` — feat(57-02): add Endgame ELO timeline TS types, ELO_COMBO_COLORS, niceEloAxis helper ✓
- `f24c20b` — feat(57-02): add EndgameEloTimelineSection component + wire into Endgames page ✓

**Verification commands all green:**
- `cd frontend && npm run lint` — zero errors
- `cd frontend && npx tsc --noEmit` — zero errors
- `cd frontend && npm test -- --run src/lib/utils.test.ts` — 17/17 pass
- `cd frontend && npm test` — 83/83 pass
- `cd frontend && npm run knip` — zero unused exports / zero unused dependencies
- `cd frontend && npm run build` — production build succeeds, prerendering complete

## Next Phase Readiness

- **Phase 56 (Endgame ELO — Backend + Breakdown Table):** can reuse the `Endgame ELO` h2 container introduced here. When Phase 56 ships, it will insert a new breakdown-table card between the h2 and the `<EndgameEloTimelineSection />` card, keeping both subsections under one section heading.
- **Phase 58 (Opening Risk & Drawishness):** no direct dependency on this plan.
- **No blockers.** ELO-05 is closed (frontend surface complete); the Phase 56 dedup opportunity for `_endgame_skill_from_bucket_rows` on the backend is still open per Plan 01's TODO marker.

---
*Phase: 57-endgame-elo-timeline-chart*
*Plan: 02*
*Completed: 2026-04-18*
