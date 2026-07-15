---
phase: 171-bots-page-setup-screen-nav
plan: 03
subsystem: ui
tags: [react, react-router, nav, lucide-react, vitest, rtl]

requires:
  - phase: 169-clocked-board-game-loop
    provides: "the real, lazy-loaded /bots route (Phase 169 D-14) already wired into ProtectedLayout, unlinked from nav"
provides:
  - "A reachable, never-locked /bots nav entry in all three nav surfaces (desktop, mobile bottom bar, more-drawer)"
  - "The codebase's first App-level RTL test, guarding all three duplicated lock-rule expressions against a one-of-three patch"
affects: [nav, bots-page]

tech-stack:
  added: []
  patterns:
    - "Exporting App.tsx's internal nav components (NavHeader/MobileBottomBar/MobileMoreDrawer/MobileHeader) additively so they can be rendered directly in tests without needing App()'s own Router/AuthProvider/QueryClientProvider stack"

key-files:
  created:
    - frontend/src/App.test.tsx
  modified:
    - frontend/src/App.tsx

key-decisions:
  - "Exported NavHeader, MobileBottomBar, MobileMoreDrawer, and MobileHeader from App.tsx (additive, no behavior change) rather than rendering the full <App/> tree — App() owns its own BrowserRouter/AuthProvider/QueryClientProvider, which blocks both route control (MemoryRouter initialEntries) and hook mocking from the outside."
  - "Mocked @/hooks/useUserProfile, @/hooks/useReadiness, and @/hooks/useAuth directly (module-level mutable state, mirroring the Endgames.readinessGate.test.tsx precedent) instead of wrapping in a real QueryClientProvider."
  - "Left useUserFlag (notification-dot flags) unmocked — it reads real localStorage in jsdom, which is fine since this test asserts on lock/dim state and ordering, not on dot visibility."

patterns-established:
  - "First App-level nav RTL test: render individual exported nav components (not the full App tree) inside a MemoryRouter + TooltipProvider, with useUserProfile/useReadiness/useAuth mocked via a shared mutable state object driven by describe.each."

requirements-completed: [PLAY-01]

coverage:
  - id: D1
    description: "Bots is the second nav item in desktop NavHeader, mobile BOTTOM_NAV_ITEMS, and MobileMoreDrawer (via shared NAV_ITEMS), with the lucide Bot icon, a ROUTE_TITLES entry, and an isActive() prefix branch"
    requirement: PLAY-01
    verification:
      - kind: unit
        ref: "frontend/src/App.test.tsx#V-04: Bots renders in all three surfaces, second position (D-16)"
        status: pass
    human_judgment: false
  - id: D2
    description: "/bots is exempt from all three duplicated import-lock expressions (NavHeader, MobileBottomBar, MobileMoreDrawer) across zero-game, guest, and fully-imported navUnlocked states, with no notification dot"
    requirement: PLAY-01
    verification:
      - kind: unit
        ref: "frontend/src/App.test.tsx#nav lock state: $name > desktop/mobile/drawer /bots never aria-disabled or dimmed (describe.each over 3 states)"
        status: pass
      - kind: unit
        ref: "frontend/src/App.test.tsx#control assertion: existing lock behavior is genuinely exercised"
        status: pass
    human_judgment: false
  - id: D3
    description: "Navigating to /bots marks the Bots nav item active (desktop) and the mobile header title reads Bots"
    requirement: PLAY-01
    verification:
      - kind: unit
        ref: "frontend/src/App.test.tsx#V-06: /bots active state + mobile header title"
        status: pass
    human_judgment: false

duration: 25min
completed: 2026-07-14
status: complete
---

# Phase 171 Plan 03: Bots Nav Entry + First App-Level Nav Test Summary

**`/bots` is now a linked, second-position, never-locked nav item on desktop and mobile, backed by the codebase's first App-level RTL test with a verified mutation-check transcript.**

## Performance

- **Duration:** 25 min
- **Started:** 2026-07-14T09:47:54Z
- **Completed:** 2026-07-14T09:55:00Z
- **Tasks:** 2 completed
- **Files modified:** 2 (1 modified, 1 created)

## Accomplishments

- `/bots` is now reachable from all three nav surfaces (desktop `NavHeader`, mobile `BOTTOM_NAV_ITEMS`, and `MobileMoreDrawer` via the shared `NAV_ITEMS` array), positioned second (Library, Bots, Openings, Endgames — D-16).
- `/bots` is exempted from all three independently-duplicated import-lock expressions, so it never dims for a zero-game user, a guest, or a fully-imported user (D-17) — a deliberate exception to the "import unlocks the nav" pattern that governs Openings/Endgames.
- No notification dot was added for `/bots` (explicitly out of scope per the plan's prohibitions).
- `frontend/src/App.test.tsx` — the codebase's first App-level nav test — pins all of the above across three `navUnlocked` states via `describe.each`, with a control assertion proving Openings/Endgames genuinely lock in the zero-game state (so the `/bots` assertions aren't vacuous).
- A manual mutation-check (removing the `/bots` exemption from `MobileBottomBar`'s lock rule only, confirming RED, then restoring) proved the three-site coverage is real rather than a single-surface test wearing a `describe.each`.

## Task Commits

Each task was committed atomically:

1. **Task 1: Add /bots to all nav tables and exempt it from all three lock rules** - `b0ae381e` (feat)
2. **Task 2: Create App.test.tsx — the first nav-level RTL test (V-04, V-05, V-06)** - `f857d15a` (test)

**Plan metadata:** _pending_ (docs: complete plan — this commit)

## Files Created/Modified

- `frontend/src/App.tsx` - Added `Bot` icon import; inserted `/bots` as the second entry in `NAV_ITEMS` and `BOTTOM_NAV_ITEMS`; added `ROUTE_TITLES['/bots']` and an `isActive()` prefix branch; appended `&& to !== '/bots'` to all three `locked` expressions (`NavHeader`, `MobileBottomBar`, `MobileMoreDrawer`); exported `NavHeader`, `MobileHeader`, `MobileBottomBar`, `MobileMoreDrawer` (additive, for testability — see Deviations).
- `frontend/src/App.test.tsx` - NEW. First App-level RTL nav test: 16 test cases across `describe.each` over 3 `navUnlocked` states, a control assertion, an ordering assertion (V-04), and an active-state/mobile-header-title assertion (V-06).

## Decisions Made

- Exported `NavHeader`, `MobileBottomBar`, `MobileMoreDrawer`, and `MobileHeader` from `App.tsx` (additive, no behavior change) instead of rendering the full `<App />` tree, since `App()` owns its own `BrowserRouter`/`AuthProvider`/`QueryClientProvider` stack, making route control and hook mocking from the outside impractical. This was flagged as an open choice in the plan's `read_first` notes ("pick the LESS invasive option and state which in the SUMMARY").
- Mocked `@/hooks/useUserProfile`, `@/hooks/useReadiness`, and `@/hooks/useAuth` directly via `vi.mock` with a shared mutable state object (mirroring the `Endgames.readinessGate.test.tsx` precedent identified in the plan's `read_first`), rather than wrapping the render in a real `QueryClientProvider`.
- Left `useUserFlag` (the notification-dot flag hook) unmocked — it reads real `localStorage` in jsdom and defaults to `false`, which is safe since this test suite doesn't assert on dot visibility, only on lock/dim state and nav ordering.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing test infrastructure] Exported four previously-module-private components from App.tsx**

- **Found during:** Task 2
- **Issue:** The plan's `read_first` step explicitly flagged this as an open decision: "if they are module-private, either export them for the test or render the App shell and assert on the rendered nav; pick the LESS invasive option." Rendering the full `<App />` tree was evaluated and rejected — `App()` instantiates its own `BrowserRouter` (no `initialEntries` control), `AuthProvider` (real context requiring `token`/`logout` wiring), and `QueryClientProvider` (real network-backed queries), none of which are practical to intercept from an external test file.
- **Fix:** Added `export` to `NavHeader`, `MobileHeader`, `MobileBottomBar`, and `MobileMoreDrawer` function declarations. No behavior change — these are still rendered internally by `ProtectedLayout` exactly as before; the `export` keyword only makes them importable by `App.test.tsx`.
- **Files modified:** `frontend/src/App.tsx`
- **Verification:** `npx tsc -b`, `npm run lint`, and `npm run knip` all clean after the change — knip's `ignoreExportsUsedInFile: true` setting means these exports are not flagged as dead code since they're still used within `App.tsx` itself (by `ProtectedLayout`).
- **Committed in:** `f857d15a` (part of Task 2 commit)

---

**Total deviations:** 1 auto-fixed (Rule 2 — necessary test infrastructure, explicitly anticipated by the plan itself as an open decision to be resolved during execution).
**Impact on plan:** No scope creep — the plan's own `read_first` section named this exact fork and asked the executor to record the choice made. No behavior change to any nav component; the export is additive and required to make the plan's own mandated regression test (App.test.tsx) possible at all.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

`/bots` is fully linked and reachable for all user states (zero-game, guest, fully-imported), closing PLAY-01. This plan's regression test (`App.test.tsx`) now also guards the pre-existing Library/Openings/Endgames lock behavior against silent regression, since future nav changes will need to keep all `describe.each` states green.

No blockers for the remaining Phase 171 plans (setup screen, time-control/color pickers, ELO normalization, result-dialog store wiring).

## Self-Check: PASSED
