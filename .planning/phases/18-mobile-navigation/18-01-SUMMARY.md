---
phase: 18-mobile-navigation
plan: "01"
subsystem: ui
tags: [react, tailwind, shadcn, vaul, mobile, pwa, navigation, drawer]

# Dependency graph
requires:
  - phase: 17-pwa-foundation
    provides: Vite PWA setup and dev workflow (Cloudflare Tunnel) that this builds on top of
provides:
  - Mobile bottom navigation bar (MobileBottomBar) with 3 direct tabs + More button
  - Slide-up More drawer (MobileMoreDrawer) with all nav links, user email, and logout
  - Simplified mobile header (MobileHeader) with brand + current page title
  - Safe-area CSS utilities via tailwindcss-safe-area (pb-safe, pt-safe)
  - shadcn Drawer component backed by vaul
affects: [19-mobile-ux-polish]

# Tech tracking
tech-stack:
  added:
    - vaul (via shadcn drawer generator — bottom-sheet drawer primitive)
    - tailwindcss-safe-area (pb-safe/pt-safe utilities for notched iPhones)
  patterns:
    - All mobile nav components co-located in App.tsx alongside NavHeader (existing pattern)
    - Tailwind breakpoint classes (sm:hidden / hidden sm:block) for responsive switching — NO useEffect + window.innerWidth
    - DrawerClose asChild wrapping Link for auto-dismiss on navigation
    - pb-16 sm:pb-0 on main content to clear fixed bottom bar

key-files:
  created:
    - frontend/src/components/ui/drawer.tsx
  modified:
    - frontend/src/App.tsx
    - frontend/src/index.css
    - frontend/package.json
    - frontend/package-lock.json

key-decisions:
  - "vaul (via shadcn) chosen for bottom drawer — handles scroll lock, backdrop, iOS momentum scrolling without manual DOM manipulation"
  - "tailwindcss-safe-area plugin for pb-safe/pt-safe — avoids hardcoded pixel values for notch/home-indicator clearance"
  - "All mobile components in App.tsx (not separate files) — consistent with existing NavHeader co-location pattern"
  - "Pure Tailwind breakpoints for show/hide — no JS-based responsive detection to avoid hydration mismatches"

patterns-established:
  - "Responsive mobile/desktop switching: use Tailwind sm: prefix only — never useEffect + window.innerWidth"
  - "Bottom bar z-40, vaul drawer z-50 — fixed stacking order convention"
  - "pb-16 sm:pb-0 on <main> required whenever fixed bottom bar is present"

requirements-completed: [NAV-01, NAV-02, NAV-03]

# Metrics
duration: 30min
completed: 2026-03-20
---

# Phase 18 Plan 01: Mobile Navigation Summary

**Bottom-bar navigation with vaul drawer — MobileBottomBar (4 tabs), MobileHeader, MobileMoreDrawer with email + logout, safe-area insets for iOS notch**

## Performance

- **Duration:** ~30 min
- **Started:** 2026-03-20T15:10:00Z
- **Completed:** 2026-03-20T15:42:37Z
- **Tasks:** 3 (2 auto + 1 human-verify)
- **Files modified:** 5

## Accomplishments
- shadcn Drawer component (vaul-backed) generated and tailwindcss-safe-area installed
- Three mobile nav components added to App.tsx: MobileHeader, MobileBottomBar, MobileMoreDrawer
- Desktop NavHeader unchanged — hidden on mobile via `hidden sm:block`, shown at >=640px
- All required data-testid attributes present for browser automation compatibility
- User visually verified mobile and desktop layouts at the checkpoint

## Task Commits

Each task was committed atomically:

1. **Task 1: Install dependencies and add shadcn drawer + safe-area CSS** - `a368db7` (chore)
2. **Task 2: Create mobile navigation components and wire into ProtectedLayout** - `1eb65c2` (feat)
3. **Task 3: Visual verification of mobile and desktop navigation** - human-verify checkpoint (no code changes)

## Files Created/Modified
- `frontend/src/components/ui/drawer.tsx` - shadcn Drawer component backed by vaul primitive
- `frontend/src/App.tsx` - MobileHeader, MobileBottomBar, MobileMoreDrawer components + modified ProtectedLayout
- `frontend/src/index.css` - Added `@import "tailwindcss-safe-area"` for pb-safe/pt-safe utilities
- `frontend/package.json` - Added vaul and tailwindcss-safe-area dependencies
- `frontend/package-lock.json` - Lockfile updated

## Decisions Made
- vaul chosen (via shadcn) for the bottom drawer — it handles scroll lock, backdrop dismiss, and iOS momentum scrolling without manual DOM manipulation
- tailwindcss-safe-area plugin used for `pb-safe`/`pt-safe` — avoids hardcoded pixel offsets that break across device generations
- All three mobile components co-located in App.tsx, consistent with the existing NavHeader pattern (no new files for components that belong to the layout)
- Pure Tailwind breakpoints (`sm:hidden`, `hidden sm:block`) for responsive switching — no JS-based detection to avoid race conditions and hydration mismatches

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Mobile navigation is complete and visually verified
- Phase 19 (Mobile UX Polish + Install Prompt) can build directly on this foundation
- Known open concern: react-chessboard touch drag on Android Chrome is unverified — click-to-move is confirmed fallback (tracked from Phase 17)

---
*Phase: 18-mobile-navigation*
*Completed: 2026-03-20*
