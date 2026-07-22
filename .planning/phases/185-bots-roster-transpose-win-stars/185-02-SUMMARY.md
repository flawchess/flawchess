---
phase: 185-bots-roster-transpose-win-stars
plan: 02
subsystem: ui
tags: [react, typescript, vitest, bots, tailwind]

# Dependency graph
requires:
  - phase: 183-persona-registry-bots-page
    provides: PERSONA_REGISTRY (24-slot Record<PersonaId, Persona>), PersonaGrid/PersonaCard, STYLE_SECTION_ORDER, personasForSection
provides:
  - "Rung-major registry accessor (personasForRung, exported RUNGS) in personaRegistry.ts"
  - "Transposed PersonaGrid: single grid-cols-4 with an accent-colored header row + 6 rung rows (800->1800), rung-major DOM order"
  - "bots-persona-header-{style} testids replacing the removed bots-persona-section-{style} wrappers"
affects: [185-03-persona-win-stars]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Single flattened CSS grid (grid-cols-4) holding both a header row and N body rows via array flatMap, rather than nested per-row grid containers, so column alignment and gap spacing are guaranteed by one shared grid instead of coordinated separately across siblings"

key-files:
  created: []
  modified:
    - frontend/src/lib/personas/personaRegistry.ts
    - frontend/src/components/bots/PersonaGrid.tsx
    - frontend/src/components/bots/__tests__/PersonaGrid.test.tsx

key-decisions:
  - "Header row + 6 rung rows rendered as ONE grid-cols-4 container (header cells then RUNGS.flatMap(personasForRung) cards, all as direct grid children) rather than one grid div per row — guarantees header/body column alignment and uniform 8px row/column gaps without manually keeping two separate grids' gap values in sync"
  - "personasForRung added as a new exported function (not a manual Object.values sort) at the same abstraction level as the existing personasForSection, per Pitfall 1 in RESEARCH.md"
  - "DOM-order test rewritten (not patched) to RUNGS.flatMap(personasForRung) rung-major order; verified via an explicit revert-and-confirm-fail mutation check per Pitfall 2"

requirements-completed: []

coverage:
  - id: D1
    description: "personaRegistry.ts exports a rung-major accessor (personasForRung) and RUNGS, mirroring personasForSection's abstraction level"
    verification:
      - kind: unit
        ref: "frontend/src/lib/personas/__tests__/personaRegistry.test.ts (27 pre-existing tests, unaffected)"
        status: pass
      - kind: unit
        ref: "npx tsc -b (zero type errors from the new exports)"
        status: pass
    human_judgment: false
  - id: D2
    description: "PersonaGrid renders one header row of 4 accent-colored style-name cells (bots-persona-header-{style}) plus 6 rung rows of PersonaCards in rung-major DOM order, at grid-cols-4 with no breakpoint reflow, no row labels"
    verification:
      - kind: unit
        ref: "frontend/src/components/bots/__tests__/PersonaGrid.test.tsx#renders exactly 24 persona cards, in rung-major DOM order (rung 800 top -> 1800 bottom, 4 styles per row)"
        status: pass
      - kind: unit
        ref: "frontend/src/components/bots/__tests__/PersonaGrid.test.tsx#renders one header row of 4 style-name cells with the STYLE_ACCENT colors"
        status: pass
      - kind: other
        ref: "grep -c bots-persona-section PersonaGrid.tsx returns 0; grep grid-cols shows a single unconditional grid-cols-4 with no sm:grid-cols-* reflow"
        status: pass
    human_judgment: false
  - id: D3
    description: "No-row-labels legibility backstop: rung identity is readable from each card's own calibratedLabel without a row label"
    verification: []
    human_judgment: true
    rationale: "185-UI-SPEC.md flags this as a genuine visual-scan assumption (verification: backstop) — calibration offsets mean cards in a row are NOT byte-identical ELO text, so whether the row reads as one rung at a glance is a human visual judgment, not something a DOM assertion can prove."

duration: 8min
completed: 2026-07-22
status: complete
---

# Phase 185 Plan 02: Bots roster transpose Summary

**Transposed the Bots roster grid from 4 style `<section>` blocks into a single `grid-cols-4` container with an accent-colored header row and 6 rung-major body rows, backed by a new `personasForRung` registry accessor.**

## Performance

- **Duration:** 8 min
- **Started:** 2026-07-22T16:09:07Z
- **Completed:** 2026-07-22T16:13:59Z
- **Tasks:** 2 completed
- **Files modified:** 3

## Accomplishments
- `personaRegistry.ts` now exports `RUNGS` and a rung-major `personasForRung(rung)` accessor, mirroring `personasForSection`'s abstraction level so no component ever hand-sorts `PERSONA_REGISTRY` by rung.
- `PersonaGrid.tsx` renders one flattened `grid-cols-4` container: 4 accent-colored style-header cells (`bots-persona-header-{style}`), then all 24 `PersonaCard`s in rung-major order (rung 800 top -> 1800 bottom, 4 styles per row), with no row labels and no per-breakpoint column reflow.
- `PersonaGrid.test.tsx`'s DOM-order assertion was rewritten (not patched) to the new rung-major order, plus a new header-row assertion; a mutation check (temporarily reverting to style-major iteration) confirmed the rewritten test fails on the old layout, proving the assertion is load-bearing.

## Task Commits

Each task was committed atomically:

1. **Task 1: Add a rung-major registry accessor** - `6d4ddfed` (feat)
2. **Task 2: Transpose PersonaGrid to rung-rows x style-columns + rewrite DOM-order test** - `84155eef` (feat)

_No TDD tasks in this plan; both are `type="auto"`._

## Files Created/Modified
- `frontend/src/lib/personas/personaRegistry.ts` - exported `RUNGS` (was module-private) and added `personasForRung(rung)` returning the 4 personas at a rung in `STYLE_SECTION_ORDER` order
- `frontend/src/components/bots/PersonaGrid.tsx` - replaced the 4 per-style `<section>` blocks (`grid-cols-3 sm:grid-cols-6`, style-major) with one `grid-cols-4` container holding a header row + rung-major body rows
- `frontend/src/components/bots/__tests__/PersonaGrid.test.tsx` - rewrote the DOM-order test to rung-major expectations, added a header-row accent-color test, added a `normalizeColor` helper (jsdom oklch trailing-zero normalization, copied from the existing `EndgameOverallPerformanceSection.test.tsx` precedent)

## Decisions Made
- Rendered the header row and all 6 body rows as children of a **single** `grid-cols-4` div (header cells first, then `RUNGS.flatMap(personasForRung)` cards) rather than a separate grid div per row. This guarantees column alignment automatically (one shared grid template) and keeps row/column gaps uniform at 8px throughout, matching the UI-SPEC's "header-row-to-grid gap: 8px" requirement without needing to coordinate gap values across multiple sibling grid containers.
- Used the project's existing `normalizeColor` jsdom-oklch-rounding helper (copied verbatim from `EndgameOverallPerformanceSection.test.tsx`) rather than a raw string-equality check on `element.style.color`, since jsdom's CSSOM cosmetically rewrites oklch decimal precision on readback.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

The transposed `PersonaGrid` (single `grid-cols-4`, rung-major DOM order, header-row testids) is ready for Plan 03 (persona win-stars), which edits the same `PersonaGrid.tsx`/`PersonaCard.tsx` files to add the `winsByPersona` prop-drilled stars row on top of this layout. No blockers.

---
*Phase: 185-bots-roster-transpose-win-stars*
*Completed: 2026-07-22*

## Self-Check: PASSED

All 4 created/modified files found on disk; all 3 commit hashes (`6d4ddfed`, `84155eef`, `26e8d5b4`) found in git log.
