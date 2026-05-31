---
phase: 98-per-tc-collapsible-endgame-type-cards
plan: "02"
subsystem: endgame-analytics
tags: [frontend, react, accordion, per-tc, endgame-type-breakdown, conv-recov-gauges]

dependency_graph:
  requires:
    - 98-01 (PER_CLASS_TC_GAUGE_ZONES in endgameZones.ts, categories_by_tc on EndgameStatsResponse)
  provides:
    - computePrimaryTc shared util in frontend/src/lib/primaryTc.ts
    - Restored 5-element EndgameTypeCard tile with Conv/Recov gauges banded per-(class x TC)
    - EndgameTypeTcCard accordion item (full-bleed header + both-axes divider 4-tile grid)
    - EndgameTypeBreakdownSection rewritten as controlled accordion orchestrator
    - Endgames.tsx wired to categories_by_tc and filterKey
  affects:
    - frontend/src/components/charts/EndgameTypeCard.tsx (restored gauges, tc prop)
    - frontend/src/components/charts/EndgameTypeBreakdownSection.tsx (3-col grid -> accordion)
    - frontend/src/pages/Endgames.tsx (new props to section)
    - CHANGELOG.md ([Unreleased] entry)

tech_stack:
  added: []
  patterns:
    - computePrimaryTc argmax (games x NOMINAL_DURATION) for primary-TC heuristic (D-09/D-10/D-11)
    - Controlled Radix Accordion (value + onValueChange) with useEffect filterKey reset (D-12)
    - Both-axes divider grammar via per-cell conditional border classes (D-08, Pitfall 4)
    - Per-(class x TC) gauge band lookup from generated PER_CLASS_TC_GAUGE_ZONES (D-04)
    - Outer guard component + inner hook component to satisfy React rules of hooks

key_files:
  created:
    - frontend/src/lib/primaryTc.ts
    - frontend/src/lib/__tests__/primaryTc.test.ts
    - frontend/src/components/charts/EndgameTypeTcCard.tsx
  modified:
    - frontend/src/components/charts/EndgameTypeCard.tsx (restored gauges, tc prop, PER_CLASS_TC_GAUGE_ZONES)
    - frontend/src/components/charts/__tests__/EndgameTypeCard.test.tsx (tc prop, gauge assertions)
    - frontend/src/components/charts/EndgameTypeBreakdownSection.tsx (full rewrite as accordion orchestrator)
    - frontend/src/components/charts/__tests__/EndgameTypeBreakdownSection.test.tsx (full rewrite)
    - frontend/src/pages/Endgames.tsx (new props: categoriesByTc, filterKey)
    - CHANGELOG.md ([Unreleased] entry)

decisions:
  - "computePrimaryTc placed in frontend/src/lib/ (not charts/) so ELO Timeline can consume it later (D-11)"
  - "EndgameTypeBreakdownSection split into outer guard + inner hook component to keep React hooks unconditional"
  - "filterKey = JSON.stringify(appliedFilters) — stable serialization, changes on any filter mutation (D-12)"
  - "AccordionContent className='p-0' with inner grid carrying p-4 — preserves full-bleed header (RESEARCH §7)"
  - "tileDividerClasses() function: per-cell conditional border classes, not divide-x/divide-y (D-08, Pitfall 4)"

metrics:
  duration: ~60 minutes
  completed_date: "2026-05-30"
  tasks_completed: 3
  tasks_total: 3
  files_modified: 8
  files_created: 3
---

# Phase 98 Plan 02: Frontend Per-TC Collapsible Endgame Type Cards Summary

One-liner: Replaced the 3-column grid of 5 per-type EndgameTypeCards with full-width vertically-stacked collapsible per-TC accordion cards, each holding a divider-separated 4-tile grid (rook/minor_piece/pawn/queen), with Conversion+Recovery gauges restored and banded against the correct per-(class x TC) IQR from Plan 98-01.

## Tasks Completed

| Task | Name | Commit | Key Files |
|------|------|--------|-----------|
| 1 | Add primaryTc util + restore EndgameTypeCard 5-element tile | f7beb8ce | primaryTc.ts, primaryTc.test.ts, EndgameTypeCard.tsx, EndgameTypeCard.test.tsx |
| 2 | Create EndgameTypeTcCard accordion item | 5f1db345 | EndgameTypeTcCard.tsx |
| 3 | Rewrite EndgameTypeBreakdownSection + wire Endgames.tsx + tests + CHANGELOG | 2a4299d7, 01beceb2 | EndgameTypeBreakdownSection.tsx, EndgameTypeBreakdownSection.test.tsx, Endgames.tsx, CHANGELOG.md |

## What Was Built

**Task 1: computePrimaryTc shared util + EndgameTypeCard restore**

Created `frontend/src/lib/primaryTc.ts` with:
- `NOMINAL_DURATION: Record<TC, number>` = `{ bullet: 60, blitz: 180, rapid: 600, classical: 900 }` (D-10)
- `computePrimaryTc(categoriesByTc, minGames)` = argmax of `tcTotal x NOMINAL_DURATION[tc]` over TCs passing `minGames` floor (D-09)
- 10 unit tests: argmax picks time-weighted TC, respects floor, returns null when empty

Restored `EndgameTypeCard.tsx` 5-element anatomy:
- Added `tc: 'bullet'|'blitz'|'rapid'|'classical'` prop (D-04)
- Replaced `PER_CLASS_GAUGE_ZONES` with `PER_CLASS_TC_GAUGE_ZONES[class][tc]` for Conv/Recov zones
- Score Gap `neutralMin/Max` now from `classBands.achievable_score_gap` (per-(class x TC))
- Restored `EndgameGauge` import, `PER_TYPE_GAUGE_SIZE=130`, gauge row JSX with `data-testid`s
- Empty-class shell now also renders opacity-50 gauges (D-02 full anatomy)
- Updated tests: added `tc` prop to fixtures, added `-conv-gauge`/`-recov-gauge` testid assertions

**Task 2: EndgameTypeTcCard accordion item**

Created `frontend/src/components/charts/EndgameTypeTcCard.tsx`:
- `AccordionItem` with `value={tc}`, `className="charcoal-texture rounded-md overflow-hidden border-none"` (suppresses default inter-item border)
- `AccordionTrigger` IS the full-bleed header: `bg-black/20 border-b border-border/40`, `TimeControlIcon`, TC label, Games: X% count with Swords icon
- `data-testid={type-breakdown-tc-${tc}-trigger}` + `aria-label` for keyboard accessibility (SC-2)
- `AccordionContent className="p-0"` (no px-4, full-bleed header preserved)
- `grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4` with `tileDividerClasses(i)` per-cell borders (D-07/D-08)
- Both-axes divider grammar: mobile top borders on i>0; tablet sm:border-r on left col + sm:border-t on bottom row; desktop xl:border-r on non-last columns; all resets via sm:border-t-0/xl:border-t-0/xl:border-r-0
- Fixed TILE_ORDER: rook/minor_piece/pawn/queen; Mixed excluded (SC-3)
- Each tile passed tc prop for per-(class x TC) band lookup

**Task 3: EndgameTypeBreakdownSection rewrite + Endgames.tsx wiring**

Rewrote `EndgameTypeBreakdownSection.tsx` as controlled accordion orchestrator:
- New props: `categoriesByTc?: Record<TC, EndgameCategoryStats[]>`, `filterKey?: string`, `onCategorySelect`
- Outer guard component returns `null` when `categoriesByTc` is undefined (Pitfall 6 back-compat)
- Inner component (separate to satisfy React hooks rules): computes eligibleTcs, grandTotal, primary TC
- `useState(() => computePrimaryTc(...) ?? '')` initializes expanded TC (D-09)
- `useEffect` on `filterKey` resets accordion to recomputed primary (D-12)
- Empty state `data-testid="endgame-type-breakdown-empty"` when no eligible TC (SC-7)
- `<Accordion type="single" collapsible value={expandedTc} onValueChange={setExpandedTc} className="flex flex-col gap-2 mt-2">`

Updated `Endgames.tsx`:
- `categoriesByTc={statsData.categories_by_tc}` (new optional field from Plan 98-01)
- `filterKey={JSON.stringify(appliedFilters)}` (stable serialized filter state for D-12 reset)

Rewrote `EndgameTypeBreakdownSection.test.tsx`: 10 tests covering per-TC accordion items, primary TC default-expand, 4 tiles per TC (no Mixed), floor suppression, filter-change reset, null guard, empty state, sub-question copy.

Added `CHANGELOG.md` `[Unreleased]` entries:
- `### Added`: Conv/Recov gauges restored per-(class x TC) banded
- `### Changed`: Endgame Type Breakdown restructured into collapsible per-TC accordion cards

## Verification Results

- `cd frontend && node_modules/.bin/vitest run` — 731 tests passed (62 test files)
- `cd frontend && node_modules/.bin/tsc --noEmit` — no errors
- `cd frontend && node_modules/.bin/eslint src/` — no issues
- `cd frontend && node_modules/.bin/knip` — no dead exports

## Deviations from Plan

None. Plan executed exactly as written with one minor addition: split `EndgameTypeBreakdownSection` into an outer guard component and an inner component, to satisfy React's rules of hooks (hooks cannot be called after a conditional return). This is a standard React pattern and does not affect external behavior.

## Known Stubs

None. All components are fully wired to real data from `categories_by_tc`. The section returns `null` when `categoriesByTc` is undefined (back-compat only, not a UI stub).

## Threat Surface Scan

No new network endpoints, auth paths, or schema changes. All rendered data comes from the already-authorized `categories_by_tc` field on `EndgameStatsResponse` (scoped to the authenticated user server-side per Plan 98-01 T-98-04).

## Self-Check: PASSED

- `frontend/src/lib/primaryTc.ts` exists: FOUND
- `frontend/src/lib/__tests__/primaryTc.test.ts` exists: FOUND
- `frontend/src/components/charts/EndgameTypeTcCard.tsx` exists: FOUND
- `frontend/src/components/charts/EndgameTypeCard.tsx` contains PER_CLASS_TC_GAUGE_ZONES: FOUND
- `frontend/src/components/charts/EndgameTypeBreakdownSection.tsx` does not contain lg:grid-cols-3: CONFIRMED CLEAN
- `frontend/src/pages/Endgames.tsx` passes categories_by_tc and filterKey: FOUND
- `CHANGELOG.md` contains Phase 98 [Unreleased] entries: FOUND
- Commit f7beb8ce exists: FOUND
- Commit 5f1db345 exists: FOUND
- Commit 2a4299d7 exists: FOUND
- Commit 01beceb2 exists: FOUND
- All 731 frontend tests pass: CONFIRMED
