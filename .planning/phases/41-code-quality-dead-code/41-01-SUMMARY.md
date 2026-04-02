---
phase: 41-code-quality-dead-code
plan: 01
subsystem: infra
tags: [knip, dead-code, ci, frontend, vitest, vite, typescript]

# Dependency graph
requires: []
provides:
  - Knip installed and configured for frontend dead export detection
  - CI pipeline enforces frontend build, test, and knip on every PR
affects: [41-02, 41-03, 41-04]

# Tech tracking
tech-stack:
  added: [knip@6]
  patterns: [dead export detection via knip in CI, frontend CI gates (build + test + knip)]

key-files:
  created:
    - frontend/knip.json
  modified:
    - frontend/package.json
    - frontend/package-lock.json
    - .github/workflows/ci.yml

key-decisions:
  - "Minimal knip.json config — Vite and Vitest plugins auto-activate from devDependencies, no explicit plugin config needed"
  - "Entry points: src/main.tsx + src/prerender.tsx (SSR prerender entry)"
  - "CI step ordering: eslint -> build -> test -> knip — type errors caught before test failures, dead code last"

patterns-established:
  - "CI: all frontend checks run in working-directory: frontend after npm ci"
  - "Knip: exit 1 (issues found) does not block plan completion — Plan 03 will clean up reported issues"

requirements-completed: [TOOL-03]

# Metrics
duration: 7min
completed: 2026-04-02
---

# Phase 41 Plan 01: Knip Installation and CI Hardening Summary

**Knip@6 installed and configured for dead export detection, with frontend build/test/knip steps added to GitHub Actions CI pipeline**

## Performance

- **Duration:** ~7 min
- **Started:** 2026-04-02T19:45:00Z
- **Completed:** 2026-04-02T19:52:43Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments

- Installed knip@6 as devDependency with `knip` script in package.json
- Created `frontend/knip.json` with entry points `src/main.tsx` and `src/prerender.tsx`
- Added three CI steps to `.github/workflows/ci.yml`: type check + build, vitest tests, and knip dead code check
- Confirmed knip runs and reports 7 unused files, 26 unused exports, and 3 unused types — input for Plan 03 cleanup

## Task Commits

1. **Task 1: Install Knip and create configuration** - `cdfed5f` (chore)
2. **Task 2: Add frontend build, test, and knip steps to CI** - `3784689` (feat)

**Plan metadata:** (docs commit follows)

## Files Created/Modified

- `frontend/knip.json` - Knip configuration with entry points and project glob
- `frontend/package.json` - Added `knip` devDependency and `"knip": "knip"` script
- `frontend/package-lock.json` - Updated after knip installation (20 new packages)
- `.github/workflows/ci.yml` - Three new frontend CI steps added after eslint step

## Decisions Made

- Minimal knip.json with no explicit plugin config — Vite/Vitest plugins auto-activate from devDependencies (per research D-03)
- CI step ordering: eslint -> build -> test -> knip. Build first catches TypeScript errors, tests second, dead code detection last as non-blocking (exit 1 is valid while dead code exists)
- Did NOT add `ignoreExportsUsedInFile: true` yet — Plan 03 will determine what's genuinely dead vs. false positives

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None - knip installed cleanly, CI file updated without conflicts.

## Knip Report Summary (input for Plan 03)

Knip found the following on first run:
- **7 unused files**: `ImportModal.tsx`, `ImportProgress.tsx`, `GameTable.tsx`, `WDLBar.tsx`, `table.tsx`, `tooltip.tsx`, `Dashboard.tsx`
- **6 unused dependencies**: `@fontsource-variable/geist`, `clsx`, `shadcn`, `tailwind-merge`, `tailwindcss-safe-area`, `tw-animate-css`
- **1 unused devDependency**: `tailwindcss`
- **2 unlisted dependencies**: `@dnd-kit/utilities`, `@dnd-kit/core` (used but not in package.json)
- **26 unused exports** and **3 unused exported types** (mostly shadcn UI component re-exports)
- **1 configuration hint**: `src/main.tsx` listed as entry in knip.json but also auto-detected as entry (redundant)

Plan 03 will triage and address these findings.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Plan 02 (research/planning) can proceed independently
- Plan 03 (dead code cleanup) can now use `npm run knip` to identify and verify removal of dead exports
- CI will block PRs that introduce new dead exports once Plan 03 cleans up existing findings

---
*Phase: 41-code-quality-dead-code*
*Completed: 2026-04-02*
