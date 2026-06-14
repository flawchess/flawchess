---
phase: quick-260614-vy4
plan: "01"
subsystem: frontend
tags: [welcome, guest, onboarding, routing, localStorage]
dependency_graph:
  requires: []
  provides: [welcome-page, welcome-dismissal-flag, guest-routing-gate]
  affects: [Home.tsx, App.tsx]
tech_stack:
  added: []
  patterns: [localStorage flag, React Navigate gate, ProtectedLayout route]
key_files:
  created:
    - frontend/src/pages/Welcome.tsx
    - frontend/src/lib/welcomeDismissal.ts
    - frontend/src/pages/__tests__/Welcome.test.tsx
  modified:
    - frontend/src/App.tsx
    - frontend/src/pages/Home.tsx
decisions:
  - WelcomePage placed under ProtectedLayout (requires guest token) matching existing auth flow; not a public route
  - Routing gate lives in Home.tsx (single entry point for authenticated landing), not in LibraryPage
  - node_modules symlink created in worktree frontend to enable lint/test in worktree context (worktrees share source but not node_modules)
metrics:
  duration: ~15 minutes
  completed: "2026-06-14"
---

# Phase quick-260614-vy4 Plan 01: Guest Welcome Page Summary

**One-liner:** New `/welcome` route with honest guest-vs-signup value-split table, localStorage dismissal flag, and guest routing gate in Home.tsx; zero backend changes.

## Tasks Completed

| Task | Description | Commit | Files |
|------|-------------|--------|-------|
| 1 | Welcome page component + dismissal-flag helper | 4bfc66a2 | Welcome.tsx, welcomeDismissal.ts |
| 2 | Wire /welcome route + guest routing gate | b4dc7807 | App.tsx, Home.tsx |
| 3 | Tests for dismissal gate + Welcome render | d0cf7b2e | Welcome.test.tsx |

## What Was Built

`frontend/src/lib/welcomeDismissal.ts` exports `isWelcomeDismissed()` and `setWelcomeDismissed(dismissed)` backed by `localStorage` key `welcome_dismissed`. Guards against SSR environments.

`frontend/src/pages/Welcome.tsx` renders a `<main data-testid="welcome-page">` with:
- Intro paragraphs explaining guest capabilities
- A responsive `<table>` with 6 value-split rows (3 shared, 3 sign-up only), using `Check`/`X` lucide icons colored with `WDL_WIN`/`WDL_LOSS` from `@/lib/theme`
- Soft rationale note with no hard deadline language ("may eventually be cleared")
- "Don't show this again" checkbox (`data-testid="welcome-checkbox-dont-show"`)
- Primary `Button variant="default"` Proceed CTA (`data-testid="welcome-btn-proceed"`) navigating to `/library/import`
- Secondary `Button variant="brand-outline"` Sign up CTA (`data-testid="welcome-btn-signup"`) using `logoutForPromotion()` + `window.location.href` matching the existing Import.tsx promotion pattern

`frontend/src/App.tsx`: Added `<Route path="/welcome" element={<WelcomePage />} />` inside `<ProtectedLayout>` (requires auth token; not behind `ImportRequiredRoute` which would defeat the purpose).

`frontend/src/pages/Home.tsx`: Updated the authenticated routing gate to redirect first-time guests (0 games, `is_guest: true`, `!isWelcomeDismissed()`) to `/welcome`. All other users continue to `/library/games` or `/library/import` as before.

`frontend/src/pages/__tests__/Welcome.test.tsx`: 8 tests covering localStorage round-trip, page render testids, Stockfish differentiator copy, and Proceed behavior with/without the dismissal checkbox.

## Verification

- `npm run lint`: clean
- `npx tsc --noEmit`: zero errors
- `npx knip`: no unused exports or dead deps
- `npm test -- --run`: 932 tests across 81 files, all passed

## Deviations from Plan

**Worktree node_modules symlink (Rule 3 - blocking issue)**
- **Found during:** Task 1 verification
- **Issue:** The worktree's `frontend/` directory has no `node_modules`; ESLint config uses ES module imports that fail when `eslint` binary is invoked outside the directory containing `node_modules`.
- **Fix:** Created a symlink `frontend/node_modules -> /home/aimfeld/.../flawchess/frontend/node_modules` inside the worktree so that `npm run lint`, `npx tsc`, `npx knip`, and `npm test` all resolve packages correctly.
- **Impact:** Symlink is gitignored by the frontend `.gitignore` (`/node_modules`), so it does not pollute the commit.

## Known Stubs

None. All value-split rows are static content with no data-fetching; the table is fully wired with accurate copy per SEED-047.

## Self-Check: PASSED
