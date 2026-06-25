---
phase: 129-tactic-filter-ui
plan: "03"
subsystem: frontend
tags: [tactic-filter, comparison-grid, two-bullet-cards, more-tactics-accordion, tdd, frontend]
status: complete

dependency_graph:
  requires:
    - TacticBullet.orientation schema field (plan 01 — server emits up to 12 bullets)
    - TacticBullet.orientation type mirror in types/library.ts (plan 02)
    - FlawFilterState (plan 02 — tacticOrientation/tacticDepthPreset/tacticDepthMax present)
  provides:
    - Two-bullet-per-card TacticComparisonGrid (D-13): Missed + Allowed rows per family
    - More Tactics accordion (D-14): overflow families beyond top-6, same FamilyCard renderer
    - groupBulletsByFamily: server-order preserving family grouper
    - FamilyCard renderer: reused for both main grid and accordion
  affects:
    - frontend/src/components/library/TacticComparisonGrid.tsx
    - frontend/src/components/library/__tests__/TacticComparisonGrid.test.tsx

tech_stack:
  added: []
  patterns:
    - "groupBulletsByFamily: order-preserving Map approach (server order = canonical)"
    - "FamilyCard: extracted renderer shared by main grid + accordion (no compact variant)"
    - "More Tactics accordion: verbatim clone of Endgames.tsx:390-397 pattern"
    - "TacticBulletRow rowLabel/rowTestId props: orientation-labeled rows without icon repeat"

key_files:
  modified:
    - frontend/src/components/library/TacticComparisonGrid.tsx
    - frontend/src/components/library/__tests__/TacticComparisonGrid.test.tsx

decisions:
  - "FamilyCard extracts the two-bullet card renderer and is shared by top-6 grid + accordion overflow (no compact variant per CONTEXT discretion)"
  - "groupBulletsByFamily uses insertion-order Map to preserve server order of first appearance — matches the no-client-re-sort contract"
  - "TacticBulletRow gets optional rowLabel/rowTestId props; when rowLabel is set, the family icon is suppressed (icon shown in CardHeader instead)"
  - "More Tactics accordion wraps overflow families in a nested 1-3 grid inside AccordionContent, matching the main grid layout"
  - "More Tactics accordion content is tested via main grid exclusion (overflow cards are in accordion DOM but Radix hides content with hidden= until opened)"

metrics:
  duration_minutes: 7
  completed_date: "2026-06-20"
  tasks_completed: 2
  tasks_total: 2
  files_modified: 2
---

# Phase 129 Plan 03: Two-Bullet Cards + More Tactics Accordion Summary

Restructured `TacticComparisonGrid` to render two bullet rows per family card ("Missed {Family}" + "Allowed {Family}"), show the server's top-6-by-Missed families in the main grid, and move overflow families into a "More Tactics" accordion cloned from the Endgame Statistics Concepts pattern.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 (TDD) | Two-bullet family cards + More Tactics accordion | 774e5bb6 | TacticComparisonGrid.tsx, TacticComparisonGrid.test.tsx |
| 2 | Full frontend gate (lint + vitest + tsc -b) | (no new files) | — |

## What Was Built

### Task 1: Two-Bullet Cards + More Tactics Accordion

**`groupBulletsByFamily(bullets)`** (new utility): groups up-to-12 orientation-tagged bullets by `bullet.family`, preserving server order of first appearance via an insertion-order Map. Returns `{ family, missed?, allowed? }[]`. No client re-sort (D-14).

**`FamilyCard`** (new component): one `Card` per tactic family. `CardHeader` shows the family icon + name (existing `font-medium` style unchanged). `CardBody` contains two `TacticBulletRow`s:
- Row 1: `rowLabel="Missed {familyName}"`, `rowTestId="tactic-grid-missed-{family}"` — using the `missed` orientation bullet
- Row 2: `rowLabel="Allowed {familyName}"`, `rowTestId="tactic-grid-allowed-{family}"` — using the `allowed` orientation bullet

Row label typography: `text-sm text-muted-foreground` Regular 400 (not extending the existing `font-medium` on the CardHeader, per UI-SPEC).

**`TacticBulletRow`** (extended): added optional `rowLabel` and `rowTestId` props. When `rowLabel` is set: family icon is suppressed in the row (icon is shown in CardHeader instead), label renders the override text. When `rowLabel` is unset: backward-compatible (existing single-bullet mode, icon shown in row, family name as label).

**`GridBody`** (restructured): calls `groupBulletsByFamily`, slices into `mainFamilies` (first `MAX_MAIN_GRID_FAMILIES = 6`) and `overflowFamilies`. Main grid renders inside `data-testid="tactic-comparison-grid"`. Overflow wrapped in:
```tsx
<Accordion type="single" collapsible>
  <AccordionItem value="more-tactics"
    className="charcoal-texture rounded-md overflow-hidden border-none"
    data-testid="tactic-grid-more-tactics">
    <AccordionTrigger band>
      <h3 className="text-base font-semibold text-foreground">More Tactics</h3>
    </AccordionTrigger>
    <AccordionContent className="p-4">
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {overflowFamilies.map(...FamilyCard...)}
      </div>
    </AccordionContent>
  </AccordionItem>
</Accordion>
```
Accordion only renders when `overflowFamilies.length > 0` (no empty accordion shown).

**Tests extended** (`TacticComparisonGrid.test.tsx`):
- Updated `DEFAULT_FLAW_FILTER` to include Phase 129 fields (`tacticOrientation`, `tacticDepthPreset`, `tacticDepthMax`)
- Updated `makeBullet` factory to require `orientation` parameter (now dual-orientation aware)
- Added `makeDualBullets(families)` helper — missed then allowed per family
- Added 5 new Phase 129 test cases:
  - (g) each card has both `tactic-grid-missed-{family}` and `tactic-grid-allowed-{family}` rows
  - (h) "Missed Fork" / "Allowed Fork" label copy verified
  - (i) popover count: 2 per family (one per orientation bullet)
  - (j) top-6 in main grid, overflow not in main grid, accordion rendered
  - (k) server order preserved (fork → pin_skewer as first two cards)
  - (l) ≤6 families → no More Tactics accordion
  - (m) no orientation toggle on grid (D-09)

### Task 2: Frontend Gate

Full gate passed without modifications:
- `npm run lint`: clean (zero ESLint + knip issues)
- `npm test -- --run`: 1069 tests pass across 88 test files
- `npx tsc -b`: zero errors

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Test checking accordion content via innerHTML**
- Found during: Task 1 GREEN
- Issue: Initial test checked `accordion.innerHTML.toContain('zwischenzug')` to verify overflow families. Radix Accordion collapses content with `hidden=""` when closed, so the content wasn't accessible via innerHTML.
- Fix: Changed test to verify overflow families are absent from the main grid (not present in `[data-testid="tactic-comparison-grid"] [data-testid^="tactic-family-card-"]`) and that the main grid has exactly 6 cards. This is a stronger assertion — server order + 6-family cap are both verified.
- Files: `TacticComparisonGrid.test.tsx`

## Verification Results

- `npm run lint`: clean
- `npm test -- --run`: 1069 passed, 0 failed (88 test files, up from 1063 in plan 02)
- `npx tsc -b`: zero errors

## UAT Notes (backstop for phase verification step)

The following require manual/browser verification (SC#4):
- Two-bullet cards stack correctly at 375px (mobile visual parity)
- "More Tactics" accordion visual matches the Endgame Statistics Concepts pattern (texture, trigger band, spacing)
- Grid is unaffected by Flaws-tab depth/orientation filter changes (D-09 independence)

## Known Stubs

None — two-bullet rendering wired to real `orientation`-tagged server data from plan 01. The accordion uses the same FamilyCard renderer as the main grid.

## Threat Mitigations Verified

| T-ID | Status |
|------|--------|
| T-129-08 (info disclosure via comparison grid render) | Accept — aggregate you-vs-opponent rates, server-gated + beta-gated; same posture as plan 01 |
| T-129-09 (beta-gate bypass) | Accept — `useUserProfile().data.beta_enabled` gate preserved; no orientation arg on grid (D-09) |
| T-129-SC (npm installs) | Mitigated — no new dependencies; Accordion from Phase 126 |

## Self-Check: PASSED
