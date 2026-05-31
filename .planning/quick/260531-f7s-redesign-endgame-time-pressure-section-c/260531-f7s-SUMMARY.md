---
status: complete
phase: quick-260531-f7s
plan: "01"
subsystem: frontend
tags: [refactor, accordion, time-pressure, endgame]
tech-stack:
  added: []
  patterns: [controlled-accordion, flex-col-lg-flex-row, AccordionItem-AccordionTrigger-AccordionContent]
key-files:
  modified:
    - frontend/src/components/charts/EndgameTimePressureSection.tsx
    - frontend/src/components/charts/EndgameTimePressureCard.tsx
    - frontend/src/pages/Endgames.tsx
    - frontend/src/components/charts/__tests__/EndgameTimePressureSection.test.tsx
    - frontend/src/components/charts/__tests__/EndgameTimePressureCard.test.tsx
decisions:
  - "Reused EndgameMetricsByTcSection/Card accordion + divider pattern verbatim"
  - "Card body is left: Score Gap chart (lg:basis-2/3), right: Clock Gap + Net flag (lg:basis-1/3)"
  - "Vertical separator (w-px) on desktop, horizontal (border-t block lg:hidden) on mobile"
  - "Primary TC seeded via computePrimaryTc; filterKey prop resets on filter change"
  - "null-return for card.total < MIN_GAMES_PER_TC_CARD preserved inside AccordionItem"
metrics:
  duration: "~25min"
  completed: "2026-05-31"
  tasks_completed: 3
  files_modified: 5
---

# Quick Task 260531-f7s: Redesign Endgame Time Pressure Section Summary

One-liner: Converted EndgameTimePressureSection from a dynamic 2x2 grid to a controlled Accordion with primary-TC auto-expand and a 2-column AccordionItem body (Score Gap chart left, gauges right) matching the EndgameMetricsByTcSection sibling.

## Tasks Completed

| # | Task | Commit | Files |
|---|------|--------|-------|
| 1 | Convert EndgameTimePressureSection to Accordion | 81c6c9a1 | EndgameTimePressureSection.tsx, Endgames.tsx |
| 2 | Convert EndgameTimePressureCard to AccordionItem with 2-column body | c4ca3e78 | EndgameTimePressureCard.tsx |
| 3 | Update tests for accordion + 2-column layout; run all gates | 0b84877a | __tests__/EndgameTimePressureSection.test.tsx, __tests__/EndgameTimePressureCard.test.tsx |

## What Changed

**EndgameTimePressureSection.tsx**: Deleted the four `GRID_*` constants and the IIFE `gridClass` ternary. Added `useState`, `useEffect`, `Accordion`, `computePrimaryTc`, and `MIN_GAMES_PER_TC_CARD`. Added `filterKey?: string` prop. Seeds `expandedTcs` from `computePrimaryTc`; resets on `filterKey` change. Renders cards inside `<Accordion type="multiple" value={expandedTcs} onValueChange={setExpandedTcs} className="flex flex-col gap-4 mt-2">`.

**EndgameTimePressureCard.tsx**: Replaced outer `<div>` with `<AccordionItem value={card.tc} ... className="charcoal-texture rounded-md overflow-hidden border-none">`. Replaced `<h3>` header band with `<AccordionTrigger>` containing the TC icon, name, and game count (collapsed header only). Wrapped body in `<AccordionContent className="p-0">` with `<div className="flex flex-col lg:flex-row p-4">`. Left column (lg:basis-2/3): Score Gap by Remaining Time chart. Right column (lg:basis-1/3): Clock Gap header + bullet + Net flag rate. Vertical/horizontal divider pair between columns mirrors the sibling card exactly.

**Endgames.tsx**: Added `filterKey={JSON.stringify(appliedFilters)}` to the `<EndgameTimePressureSection>` call site, matching the `EndgameMetricsByTcSection` wiring at line 625.

## Deviations from Plan

None. Plan executed exactly as written.

## Known Stubs

None. All data flows through the existing API response fields unchanged.

## Threat Flags

None. Pure frontend layout refactor with no new API surface, auth paths, or schema changes.

## Gate Results

```
lint:  PASS (eslint ., 0 warnings)
tests: PASS (744/744 tests, 63 test files)
tsc:   PASS (0 errors)
knip:  PASS (0 dead exports — GRID_* constants were module-local)
```

## Self-Check

- [x] EndgameTimePressureSection.tsx modified with Accordion pattern
- [x] EndgameTimePressureCard.tsx modified with AccordionItem + 2-column body
- [x] Endgames.tsx filterKey wired
- [x] Tests updated and passing
- [x] Commits exist: 81c6c9a1, c4ca3e78, 0b84877a

## Self-Check: PASSED
