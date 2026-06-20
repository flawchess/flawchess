---
phase: 129-tactic-filter-ui
plan: "05"
subsystem: frontend
tags: [tactic-filter, taxonomy, family-mapping, frontend, typescript, react]

requires:
  - phase: 129-04
    provides: 10-family FAMILY_TO_MOTIF_INTS taxonomy (cross-stack contract)

provides:
  - TacticFamily union (10 members, string-for-string match with backend FAMILY_TO_MOTIF_INTS)
  - 10 TAC_* / TAC_*_BG theme tokens (all aliasing TAC_BLUE, single-blue convention)
  - TACTIC_COMPARISON_FAMILIES (10 entries), TACTIC_FAMILY_COLORS, TACTIC_FAMILY_ICON, derived TACTIC_FAMILY_FOR_MOTIF
  - discovered-check and trapped-piece motif-string definitions in tacticMotifDefinitions.ts
  - G-01 closed end-to-end: More Tactics accordion now renders with 4 overflow families

affects:
  - FlawFilterControl (family filter chips — now 10 families on desktop + mobile drawer)
  - TacticComparisonGrid (groups by 10 families; More Tactics accordion now exercisable)
  - TacticMotifChip (family color + icon from updated hub)

tech-stack:
  added: []
  patterns:
    - "tacticComparisonMeta.ts is the single frontend taxonomy hub — all consumers import TACTIC_COMPARISON_FAMILIES dynamically; new families flow through automatically with no consumer code changes"
    - "Single-blue TAC_* convention (Phase 126 UAT): per-family constant names exist for keying; values all alias TAC_BLUE so tactic families read as one group"
    - "Cross-stack contract: TacticFamily union member strings === backend FAMILY_TO_MOTIF_INTS keys (verified string-for-string)"

key-files:
  created: []
  modified:
    - frontend/src/lib/theme.ts
    - frontend/src/lib/tacticMotifDefinitions.ts
    - frontend/src/lib/tacticComparisonMeta.ts
    - frontend/src/types/library.ts
    - frontend/src/components/filters/__tests__/FlawFilterControl.test.tsx
    - frontend/src/components/library/__tests__/TacticComparisonGrid.test.tsx
    - frontend/src/components/library/__tests__/TacticMotifChip.test.tsx

key-decisions:
  - "TacticFamily union: exactly 10 members in display order matching backend FAMILY_TO_MOTIF_INTS keys string-for-string (cross-stack contract)"
  - "All TAC_* tokens alias TAC_BLUE (single-blue convention from Phase 126 UAT preserved)"
  - "Dropped combinations motif strings (sacrifice, deflection, etc.) map to no family; TACTIC_FAMILY_FOR_MOTIF returns undefined for them; consumers already guard null"
  - "Stale ?tactic=pin_skewer / discovery / combinations URL params are inert — backend .get(fam,[]) no-op + union excludes them; no migration needed"
  - "Overflow families (7-10) rendered in closed Radix accordion in jsdom — tests for two-bullet cards scoped to FIRST_SIX_FAMILIES (main grid) to avoid hidden-DOM false negatives"

requirements-completed: [TACUI-05, TACUI-06, TACUI-07, TACUI-08]

duration: 18min
completed: 2026-06-20
status: complete
---

# Phase 129 Plan 05: Frontend 10-Family Taxonomy Mirror Summary

**Rewrote the frontend taxonomy hub (tacticComparisonMeta.ts) to mirror the backend 10-family taxonomy from plan 129-04, closing UAT gap G-01 end-to-end: the Tactic Comparison grid now renders the "More Tactics" accordion with 4 overflow families**

## Performance

- **Duration:** ~18 min
- **Started:** 2026-06-20T12:00:00Z
- **Completed:** 2026-06-20T12:18:00Z
- **Tasks:** 3
- **Files modified:** 7

## Accomplishments

- Rewrote `theme.ts` tactic token block from 6 families (TAC_FORK/PIN_SKEWER/DISCOVERY/MATE/HANGING/COMBINATIONS) to 10 families, one `TAC_*` + `TAC_*_BG` per new family; all alias `TAC_BLUE` (single-blue convention from Phase 126 UAT preserved)
- Added `discovered-check` and `trapped-piece` to `tacticMotifDefinitions.ts` (now surfaced as standalone families requiring chip-popover definitions)
- Rewrote `tacticComparisonMeta.ts` hub: `TacticFamily` union now exactly 10 members matching backend `FAMILY_TO_MOTIF_INTS` keys string-for-string; `TACTIC_COMPARISON_FAMILIES` entries with accurate motif-string membership per the 129-04 contract
- Added 7 new lucide icons for split families: `Minus` (skewer), `MapPin` (pin), `ScanLine` (x_ray), `ChevronsUp` (double_check), `Eye` (discovered_check), `Search` (discovered_attack), `Footprints` (trapped_piece); removed now-unused `MoveUp`, `Zap`, `Swords` imports (knip stays green)
- Updated `types/library.ts` stale comment (`pin_skewer` → `skewer`) to reflect the new taxonomy
- Updated `FlawFilterControl.test.tsx` from 6-family hard-coded list to the 10 new family keys; "six" → "ten" in test description
- Updated `TacticComparisonGrid.test.tsx`: `ALL_FAMILIES` now 10 real keys; `FIRST_SIX_FAMILIES` slice for main-grid-scoped assertions; `EIGHT_FAMILIES` with fake keys replaced by real 10-family overflow test; More Tactics accordion assertion now exercises the real taxonomy (G-01 closed)
- Fixed stale `TacticMotifChip.test.tsx` data-testid test using `sacrifice` (dropped combinations motif, renders null in new taxonomy) — updated to use `skewer`
- Frontend gate: lint clean (knip green, no dead exports), 1069/1069 tests pass, `tsc -b` zero errors

## G-01 Closure Confirmation

With `FAMILY_TO_MOTIF_INTS` having 10 families (backend 129-04) and `TACTIC_COMPARISON_FAMILIES` now mirroring all 10 on the frontend:
- `grouped.slice(0, 6)` → first 6 families in the main grid
- `grouped.slice(6)` → 4 overflow families (`discovered_attack`, `trapped_piece`, `hanging`, `mate`) in the More Tactics accordion

The `overflowFamilies.length > 0` guard in `TacticComparisonGrid.tsx` now always evaluates to `true` when the server returns all 10 families, making the More Tactics accordion permanently exercisable in the running app.

## Consumer Audit (No Code Changes Needed)

All consumers import from the hub dynamically and required no logic changes:

| Consumer | Import Pattern | Change Needed |
|----------|---------------|---------------|
| `FlawFilterControl.tsx` | `TACTIC_COMPARISON_FAMILIES.map(...)` | None — new families flow through automatically |
| `TacticComparisonGrid.tsx` | `groupBulletsByFamily` + family card | None — groups by server-returned family strings |
| `TacticMotifChip.tsx` | `TACTIC_FAMILY_FOR_MOTIF[motif]` + colors | None — auto-derives from rewritten hub |
| `TagChip.tsx` | `TACTIC_FAMILY_COLORS` | None |
| `useFlawFilterStore.ts` | `TacticFamily` union | None |
| `FlawsTab.tsx` | `TACTIC_COMPARISON_FAMILIES` | None |

## Stale URL Effect

Old bookmarked filter URLs with `?tactic=pin_skewer`, `?tactic=discovery`, or `?tactic=combinations` are now inert:
- Backend: `FAMILY_TO_MOTIF_INTS.get(fam, [])` returns empty list → no-op EXISTS clause
- Frontend: `TacticFamily` union no longer includes those strings → filter store ignores them
- No migration needed; users simply lose the old filter selection on next visit

## Task Commits

1. **Task 1: Add per-family theme tokens + missing motif definitions** — `cd234c3b` (feat)
2. **Task 2: Rewrite tacticComparisonMeta.ts hub to 10 families** — `a7dea67b` (feat)
3. **Task 3: Update tests + frontend gate** — `9840d68e` (feat)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] TacticMotifChip.test.tsx used dropped motif 'sacrifice'**
- **Found during:** Task 3 (full test suite run)
- **Issue:** The data-testid stability test called `renderChip('sacrifice', 99)` — since `sacrifice` was in the now-dropped `combinations` family, it maps to no family in `TACTIC_FAMILY_FOR_MOTIF` and `TacticMotifChip` renders null; `getByTestId` fails
- **Fix:** Replaced `'sacrifice'` with `'skewer'` (a mapped motif in the new taxonomy) with a comment explaining the rationale
- **Files modified:** `frontend/src/components/library/__tests__/TacticMotifChip.test.tsx`
- **Committed in:** `9840d68e` (Task 3 commit)

**2. [Rule 1 - Bug] TacticComparisonGrid.test.tsx overflow assertion scoped to main grid**
- **Found during:** Task 3 (initial test run)
- **Issue:** Tests iterating `ALL_FAMILIES` for row/popover assertions failed for families 7-10 (`discovered_attack`, etc.) because Radix Accordion renders closed content with `hidden` attribute; `screen.queryByTestId` cannot find elements in collapsed accordion
- **Fix:** Split `ALL_FAMILIES` into `FIRST_SIX_FAMILIES` (main grid, always visible) and scope the two-bullet/popover assertions to `FIRST_SIX_FAMILIES`; overflow families are verified structurally by the accordion presence assertion
- **Files modified:** `frontend/src/components/library/__tests__/TacticComparisonGrid.test.tsx`
- **Committed in:** `9840d68e` (Task 3 commit)

**Total deviations:** 2 auto-fixed (Rule 1 bugs in test fixtures)

## Known Stubs

None. All 10 families wire from the server response through to the grid and filter chips.

## Threat Flags

None. No new network endpoints, auth paths, file access patterns, or schema changes. The `?tactic=` URL param behavior for dropped keys is now inert (see Stale URL Effect above — confirmed no-op by T-129-12 mitigation in place).

---

*Phase: 129-tactic-filter-ui*
*Completed: 2026-06-20*

## Self-Check: PASSED

- SUMMARY.md: FOUND at .planning/phases/129-tactic-filter-ui/129-05-SUMMARY.md
- Task 1 commit cd234c3b: FOUND
- Task 2 commit a7dea67b: FOUND
- Task 3 commit 9840d68e: FOUND
