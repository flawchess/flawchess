---
phase: 43-frontend-cleanup
plan: 01
subsystem: ui
tags: [react, tailwind, css-variables, theme, refactor]

# Dependency graph
requires: []
provides:
  - .btn-brand CSS utility class in @layer components applying brand button styling via CSS vars
  - .glass-overlay CSS utility class for linear-gradient glass effect
  - PRIMARY_BUTTON_CLASS JS constant removed from theme.ts
  - All 3 brand button consumers (Home, Openings, PublicHeader) using pure CSS class
affects: [future-ui-work, theme-changes]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Brand button styling via CSS utility class .btn-brand in @layer components (not JS constant)"
    - "Changing brand colors requires only editing CSS variable in :root — zero JS/component edits"

key-files:
  created: []
  modified:
    - frontend/src/index.css
    - frontend/src/lib/theme.ts
    - frontend/src/pages/Home.tsx
    - frontend/src/pages/Openings.tsx
    - frontend/src/components/layout/PublicHeader.tsx

key-decisions:
  - "CSS utility class .btn-brand preferred over JS constant for purely stylistic concern — eliminates unnecessary import dependency in 3 files"
  - "GLASS_OVERLAY JS constant retained in theme.ts — still needed by WDL bar components for inline styles"
  - "tabs.tsx glass overlay remains as Tailwind arbitrary value — Tailwind variant prefixes cannot compose with arbitrary CSS classes"

patterns-established:
  - "Brand button pattern: className='btn-brand' (no imports, no JS constants, no cn() wrapper needed)"

requirements-completed:
  - FCLN-01

# Metrics
duration: 2min
completed: 2026-04-03
---

# Phase 43 Plan 01: Frontend Cleanup — Brand Button CSS Refactor Summary

**Replaced PRIMARY_BUTTON_CLASS JS constant with .btn-brand CSS utility class, eliminating JS-level styling indirection across 3 component files**

## Performance

- **Duration:** 2 min
- **Started:** 2026-04-03T12:31:22Z
- **Completed:** 2026-04-03T12:33:33Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments
- Added `.btn-brand` and `.glass-overlay` CSS utility classes to `@layer components` in index.css
- Removed `PRIMARY_BUTTON_CLASS` export from theme.ts (with its comment block) — brand button styling is now pure CSS
- Migrated all 3 consumers (Home.tsx, Openings.tsx, PublicHeader.tsx) to use `btn-brand` CSS class directly — no JS imports
- Build, tests, lint, and knip all pass with zero errors

## Task Commits

Each task was committed atomically:

1. **Task 1: Add CSS utility classes and remove PRIMARY_BUTTON_CLASS** - `4066b9f` (refactor)
2. **Task 2: Update all consumers to use CSS classes and verify build** - `d6f819e` (refactor)

**Plan metadata:** (docs commit below)

## Files Created/Modified
- `frontend/src/index.css` - Added `.btn-brand` and `.glass-overlay` in `@layer components`
- `frontend/src/lib/theme.ts` - Removed `PRIMARY_BUTTON_CLASS` constant and its 7-line comment block
- `frontend/src/pages/Home.tsx` - Removed import, replaced 2 `cn(PRIMARY_BUTTON_CLASS, ...)` with `cn('btn-brand', ...)`
- `frontend/src/pages/Openings.tsx` - Removed import, replaced 4 template literal usages with `className="flex-1 btn-brand"`
- `frontend/src/components/layout/PublicHeader.tsx` - Removed import, replaced `className={PRIMARY_BUTTON_CLASS}` with `className="btn-brand"`

## Decisions Made
- **CSS utility class over JS constant:** Moving brand button styling to CSS (@layer components) eliminates unnecessary JS import dependencies in 3 files. Styling concerns belong in CSS, not in a TS module that components must import.
- **GLASS_OVERLAY JS constant retained:** Used by WDL bar components for inline `backgroundImage` styles (not Tailwind className context) — JS access is required there. The new `.glass-overlay` CSS class is an additive utility for Tailwind className context.
- **tabs.tsx unchanged:** The Tailwind arbitrary value `bg-[image:linear-gradient(...)]` inside a `group-data-[variant=brand]/tabs-list:data-active:` variant prefix cannot be replaced with a custom CSS class — Tailwind variant prefixes only compose with Tailwind utilities, not arbitrary CSS classes.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Brand button refactor complete — brand color changes now require only editing `--brand-brown` and `--brand-brown-hover` CSS variables in `:root` in index.css
- No component or JS file edits needed for future brand color updates
- Phase 43 Plan 01 (only plan in phase) is complete

## Self-Check: PASSED

- `frontend/src/index.css` — contains `.btn-brand` and `.glass-overlay`
- `frontend/src/lib/theme.ts` — does NOT contain `PRIMARY_BUTTON_CLASS`
- `frontend/src/pages/Home.tsx` — contains `btn-brand` (2 occurrences)
- `frontend/src/pages/Openings.tsx` — contains `btn-brand` (4 occurrences)
- `frontend/src/components/layout/PublicHeader.tsx` — contains `btn-brand` (1 occurrence)
- Commits: `4066b9f` and `d6f819e` exist in git log

---
*Phase: 43-frontend-cleanup*
*Completed: 2026-04-03*
