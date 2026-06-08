---
phase: 110-flaw-tag-taxonomy-overhaul-rename-impact-family-rebuild-tool
plan: 05
subsystem: ui
tags: [react, typescript, radix-ui, tailwind, flaw-tags, taxonomy]

# Dependency graph
requires:
  - phase: 110-04
    provides: Generated flawThresholds.ts with threshold scalars for TAG_DEFINITIONS interpolation

provides:
  - FlawTag/TempoTag frontend unions with renamed canonical members (reversed/squandered/hasty/unrushed)
  - TagDistribution rate fields renamed to reversed_rate/squandered_rate
  - FAM_TEMPO_HASTY/FAM_TEMPO_UNRUSHED theme constants (renamed from IMPATIENT/CONSIDERED)
  - ACTIVE_FILTER_RING_CLASS theme constant for D-05 ring emphasis
  - TAG_DEFINITIONS rebuilt with thresholds from @/generated/flawThresholds (no hard-coded %)
  - TAG_LABELS with renamed canonical keys (still consumed by FlawFilterControl)
  - TagChip restored as Radix Popover trigger with bold {tag} heading + definition
  - D-05 active-filter ring on TagChip (internal store subscription, no prop drilling)
  - Navigation removed from TagChip (D-06)
  - FlawStatsBand impact cell removed (D-02); FlawTagDistribution uses renamed fields
  - All cascade consumers updated (FlawFilterControl, FlawTagDistribution, tests)

affects:
  - 110-06 (backend tests/verification will reference new tag names)
  - 110-07 (final lint/test/knip gate)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Store-internal ring subscription: TagChip reads useFlawFilterStore internally so both call sites get the ring without prop drilling"
    - "Threshold interpolation: TAG_DEFINITIONS uses pct()/secs() helpers with constants from @/generated/flawThresholds — no hard-coded numeric literals in definition prose"
    - "D-07 heading convention: TagChip popover bold heading is raw {tag} lowercase-with-dash string, not TAG_LABELS[tag]"

key-files:
  created: []
  modified:
    - frontend/src/types/library.ts
    - frontend/src/lib/theme.ts
    - frontend/src/lib/tagDefinitions.ts
    - frontend/src/components/library/TagChip.tsx
    - frontend/src/components/library/__tests__/TagChip.test.tsx
    - frontend/src/components/library/FlawTagDistribution.tsx
    - frontend/src/components/library/FlawStatsBand.tsx
    - frontend/src/components/library/FlawStatsPanel.tsx
    - frontend/src/components/filters/FlawFilterControl.tsx
    - frontend/src/components/filters/__tests__/FlawFilterControl.test.tsx
    - frontend/src/pages/library/__tests__/FlawsTab.test.tsx
    - frontend/src/pages/library/__tests__/GamesTab.test.tsx
    - frontend/src/api/__tests__/client.test.ts

key-decisions:
  - "ACTIVE_FILTER_RING_CLASS exported as a Tailwind class string (ring-2 ring-offset-1) from theme.ts; ring color applied via CSS custom property --tw-ring-color set to the family color inline — keeps family-color-ring without adding per-family ring constants"
  - "D-02 impact cell removal from FlawStatsBand was a compile-cascade consequence of dropping result_changing_rate from TagDistribution — fixed as Rule 1 (compile blocker)"
  - "Pre-existing EvalChart.tsx tsc error (recharts TooltipPayload readonly vs mutable array) is out-of-scope; logged in deferred items"

patterns-established:
  - "Popover heading = raw {tag} string, not human-readable label (D-07): the filter-control buttons use TAG_LABELS; the chip tooltip uses the canonical tag identifier"
  - "Store subscription inside leaf components (not prop drilling): TagChip subscribes to useFlawFilterStore for ring state so the Games and Flaws call sites need no changes"

requirements-completed: [SC-1, SC-5, SC-6]

# Metrics
duration: 14min
completed: 2026-06-07
---

# Phase 110 Plan 05: Tag-chip surface rebuild — Radix popover + active-filter ring + taxonomy renames

**Frontend FlawTag/TempoTag unions renamed (reversed/squandered/hasty/unrushed), TAG_DEFINITIONS rebuilt with interpolated thresholds, TagChip restored as Radix popover with store-internal active-filter ring, D-06 navigation removed**

## Performance

- **Duration:** 14 min
- **Started:** 2026-06-07T21:00:21Z
- **Completed:** 2026-06-07T21:14:21Z
- **Tasks:** 3
- **Files modified:** 13

## Accomplishments

- Renamed FlawTag union members (while-ahead->reversed, result-changing->squandered, impatient->hasty, considered->unrushed) and TempoTag; TagDistribution drops while_ahead_rate/result_changing_rate in favour of reversed_rate/squandered_rate
- TAG_DEFINITIONS rebuilt from flaw-tag-definitions.md with all thresholds interpolated from @/generated/flawThresholds — zero hard-coded 70%/85%/60%/30% string literals
- TagChip restored as Radix PopoverPrimitive trigger: bold {tag} heading + one-sentence definition; hover-open on desktop, tap-toggle on mobile; navigation removed (D-06)
- Active-filter ring (D-05): TagChip subscribes to useFlawFilterStore internally; ring applies on both LibraryGameCard and FlawsTab without prop drilling

## Task Commits

Each task was committed atomically:

1. **Task 1: Update frontend types + theme constants** - `e81093cd` (feat)
2. **Task 2: Rebuild tagDefinitions.ts TAG_DEFINITIONS + rename TAG_LABELS keys** - `70967d0a` (feat)
3. **Task 3: Restore TagChip Radix Popover + active-filter ring; rewrite TagChip test** - `b8df7df9` (feat)

## Files Created/Modified

- `frontend/src/types/library.ts` - FlawTag/TempoTag union renames; TagDistribution rate field renames
- `frontend/src/lib/theme.ts` - FAM_TEMPO_HASTY/UNRUSHED renamed; ACTIVE_FILTER_RING_CLASS added (D-05)
- `frontend/src/lib/tagDefinitions.ts` - TAG_DEFINITIONS rebuilt with interpolated thresholds; TAG_LABELS renamed keys
- `frontend/src/components/library/TagChip.tsx` - Restored Radix Popover (8c5ebc81) + ring + navigation removed
- `frontend/src/components/library/__tests__/TagChip.test.tsx` - Rewritten: popover + ring assertions, no navigation
- `frontend/src/components/library/FlawTagDistribution.tsx` - Cascade rename: hasty/unrushed stacked bar; reversed_rate/squandered_rate sub-column
- `frontend/src/components/library/FlawStatsBand.tsx` - D-02: impact cell removed; result_changing_rate prop dropped
- `frontend/src/components/library/FlawStatsPanel.tsx` - Removed result_changing_rate prop pass to FlawStatsBand
- `frontend/src/components/filters/FlawFilterControl.tsx` - TIMING_TAGS/IMPACT_TAGS/TAG_ICONS updated to new tag names
- `frontend/src/components/filters/__tests__/FlawFilterControl.test.tsx` - Tag testids updated (reversed/squandered/hasty/unrushed)
- `frontend/src/pages/library/__tests__/FlawsTab.test.tsx` - result-changing->reversed in mock flaw data + deep-link test
- `frontend/src/pages/library/__tests__/GamesTab.test.tsx` - result-changing->reversed in mock filter state
- `frontend/src/api/__tests__/client.test.ts` - result-changing->reversed in tag filter test

## Decisions Made

- ACTIVE_FILTER_RING_CLASS is a Tailwind class string combining ring-width + offset; the ring color is set via CSS custom property `--tw-ring-color` in the inline style (matching the family color), rather than adding per-family ring color constants to theme.ts. This keeps one constant in theme.ts instead of three.
- D-02 (FlawStatsBand impact cell removal) was applied as part of Task 1 cascade because removing `result_changing_rate` from `TagDistribution` caused a compile error in FlawStatsBand via Rule 1.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Cascade compile errors in FlawTagDistribution, FlawStatsBand, FlawFilterControl, and test files**
- **Found during:** Task 1 (types/theme update)
- **Issue:** Renaming FlawTag/TempoTag union members caused compile errors in all consumers using the old literal strings or old rate field names
- **Fix:** Updated all consumers to use renamed tag names, rate fields, and theme constants; applied D-02 (remove impact cell from FlawStatsBand) as part of the cascade
- **Files modified:** FlawTagDistribution.tsx, FlawStatsBand.tsx, FlawStatsPanel.tsx, FlawFilterControl.tsx, and 5 test files
- **Committed in:** e81093cd (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 Rule 1 compile-cascade)
**Impact on plan:** All auto-fixes necessary for type correctness. No scope creep — all changes were direct consequences of the planned union rename.

## Issues Encountered

- Pre-existing `EvalChart.tsx` tsc error (recharts TooltipPayload readonly vs mutable array) surfaces when running `npx tsc -p tsconfig.app.json --noEmit` directly. This error exists in the original codebase before our changes (confirmed via git stash check). It is out-of-scope for this plan. Logged in deferred items.
- The `npx tsc --noEmit` via project references exits 0 (uses build cache); direct `npx tsc -p tsconfig.app.json --noEmit` reveals the pre-existing EvalChart error. All files touched by this plan are type-clean.

## Known Stubs

None — all changes are wired to real data. TAG_DEFINITIONS thresholds are interpolated from the generated constants.

## Threat Flags

No new threat surface. TagChip definition prose and filter store are client-only static constants; no network, auth, or data exposure introduced.

## Next Phase Readiness

- Frontend type surface is now grep-clean for deprecated tag/rate names (SC-1 partial)
- TagChip popover with canonical definitions and thresholds is production-ready (SC-5)
- Active-filter ring on both Games and Flaws cards (SC-6 chip side)
- Plan 110-06 (backend test updates, FlawsTab URL-sync) can proceed
- Plan 110-07 (full lint/test/knip gate) is the final integration gate

## Self-Check: PASSED

All key files verified present. All task commits verified in git log.

---
*Phase: 110-flaw-tag-taxonomy-overhaul-rename-impact-family-rebuild-tool*
*Completed: 2026-06-07*
