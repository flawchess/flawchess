# Roadmap: Chessalytics

## Milestones

- ✅ **v1.0 Initial Platform** — Phases 1-10 (shipped 2026-03-15)
- ✅ **v1.1 Opening Explorer & UI Restructuring** — Phases 11-16 (shipped 2026-03-20)
- 🚧 **v1.2 Mobile & PWA** — Phases 17-19 (in progress)

## Phases

<details>
<summary>✅ v1.0 Initial Platform (Phases 1-10) — SHIPPED 2026-03-15</summary>

- [x] Phase 1: Data Foundation (2/2 plans) — completed 2026-03-11
- [x] Phase 2: Import Pipeline (4/4 plans) — completed 2026-03-12
- [x] Phase 3: Analysis API (2/2 plans) — completed 2026-03-12
- [x] Phase 4: Frontend and Auth (3/3 plans) — completed 2026-03-12
- [x] Phase 5: Position Bookmarks (5/5 plans) — completed 2026-03-13
- [x] Phase 6: Browser Automation Optimization (2/2 plans) — completed 2026-03-13
- [x] Phase 7: Game Statistics and Charts (3/3 plans) — completed 2026-03-14
- [x] Phase 8: Games and Bookmark Tab Rework (3/3 plans) — completed 2026-03-14
- [x] Phase 9: Game Cards, Username Import, Pagination (8/8 plans) — completed 2026-03-15
- [x] Phase 10: Auto-Generate Position Bookmarks (4/4 plans) — completed 2026-03-15

</details>

<details>
<summary>✅ v1.1 Opening Explorer & UI Restructuring (Phases 11-16) — SHIPPED 2026-03-20</summary>

- [x] Phase 11: Schema and Import Pipeline (1/1 plan) — completed 2026-03-16
- [x] Phase 12: Backend Next-Moves Endpoint (2/2 plans) — completed 2026-03-16
- [x] Phase 13: Frontend Move Explorer Component (2/2 plans) — completed 2026-03-16
- [x] Phase 14: UI Restructuring (3/3 plans) — completed 2026-03-17
- [x] Phase 15: Enhanced Game Import Data (3/3 plans) — completed 2026-03-18
- [x] Phase 16: Game Card UI Improvements (3/3 plans) — completed 2026-03-18

</details>

### 🚧 v1.2 Mobile & PWA (In Progress)

**Milestone Goal:** Make the application work great on smartphones as an installable PWA, with mobile-optimized navigation and dev workflow for phone testing.

- [x] **Phase 17: PWA Foundation + Dev Workflow** - Installable PWA with service worker, custom icons, and phone testing workflow (completed 2026-03-20)
- [x] **Phase 18: Mobile Navigation** - Bottom navigation bar with direct tabs and "More" drawer for mobile viewports with safe-area support (completed 2026-03-20)
- [ ] **Phase 19: Mobile UX Polish + Install Prompt** - Touch targets, overflow fixes, iOS/Android install prompts, mobile chessboard

## Phase Details

### Phase 17: PWA Foundation + Dev Workflow
**Goal**: App is installable as a PWA with correct service worker caching and a usable phone testing setup
**Depends on**: Phase 16
**Requirements**: PWA-01, PWA-02, PWA-03, DEV-01, DEV-02
**Success Criteria** (what must be TRUE):
  1. User can install the app from Android Chrome via "Add to Home Screen" and it opens in standalone mode (no browser chrome)
  2. Repeat visits on mobile load static assets from service worker cache without network requests
  3. API routes (analysis, games, imports) are never served from cache — network tab shows no ServiceWorker source for API calls
  4. App shows chess-themed icons (not Vite default) in the home screen shortcut and browser tab
  5. Developer can expose the Vite dev server over HTTPS to a phone on a different network using a documented one-command tunnel
**Plans:** 1/1 plans complete
Plans:
- [ ] 17-01-PLAN.md — PWA setup with icons, manifest, service worker, and dev workflow scripts

### Phase 18: Mobile Navigation
**Goal**: Users on mobile viewports navigate the full app through a bottom navigation bar with direct tabs and a "More" drawer
**Depends on**: Phase 17
**Requirements**: NAV-01, NAV-02, NAV-03
**Success Criteria** (what must be TRUE):
  1. At viewport widths below 640px the horizontal nav bar is hidden and a bottom navigation bar with 3 tabs + More button is visible
  2. Tapping "More" opens a bottom sheet drawer containing all nav links and a logout button
  3. Tapping any nav link in the drawer navigates to that route and closes the drawer
  4. On notched iPhones in standalone PWA mode the header and content do not overlap the notch or Dynamic Island
**Plans:** 1/1 plans complete
Plans:
- [ ] 18-01-PLAN.md — Mobile bottom bar, More drawer, mobile header, safe-area insets

### Phase 19: Mobile UX Polish + Install Prompt
**Goal**: All app interactions work correctly on mobile touch devices with in-app install prompts for iOS and Android
**Depends on**: Phase 18
**Requirements**: UX-01, UX-02, UX-03, UX-04, PWA-04, PWA-05
**Success Criteria** (what must be TRUE):
  1. No page displays a horizontal scrollbar at 375px viewport width (iPhone SE baseline)
  2. All buttons, filters, and controls have tap targets of at least 44x44px on mobile
  3. Moving chess pieces via click-to-click works correctly on iOS Safari and Android Chrome
  4. The Openings page sidebar (board + filters) and main content area are both usable on mobile without excessive scrolling
  5. Android Chrome users see an in-app install prompt after interacting with the app; iOS Safari users see a dismissible banner with "Share > Add to Home Screen" instructions
**Plans:** 3 plans
Plans:
- [ ] 19-01-PLAN.md — Chessboard touch fix and Openings sticky mobile layout
- [ ] 19-02-PLAN.md — 44px touch targets and horizontal overflow fixes
- [ ] 19-03-PLAN.md — PWA install prompts for Android and iOS

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Data Foundation | v1.0 | 2/2 | Complete | 2026-03-11 |
| 2. Import Pipeline | v1.0 | 4/4 | Complete | 2026-03-12 |
| 3. Analysis API | v1.0 | 2/2 | Complete | 2026-03-12 |
| 4. Frontend and Auth | v1.0 | 3/3 | Complete | 2026-03-12 |
| 5. Position Bookmarks | v1.0 | 5/5 | Complete | 2026-03-13 |
| 6. Browser Automation | v1.0 | 2/2 | Complete | 2026-03-13 |
| 7. Game Statistics | v1.0 | 3/3 | Complete | 2026-03-14 |
| 8. Bookmark Tab Rework | v1.0 | 3/3 | Complete | 2026-03-14 |
| 9. Game Cards & Import | v1.0 | 8/8 | Complete | 2026-03-15 |
| 10. Auto Bookmarks | v1.0 | 4/4 | Complete | 2026-03-15 |
| 11. Schema & Pipeline | v1.1 | 1/1 | Complete | 2026-03-16 |
| 12. Next-Moves API | v1.1 | 2/2 | Complete | 2026-03-16 |
| 13. Move Explorer UI | v1.1 | 2/2 | Complete | 2026-03-16 |
| 14. UI Restructuring | v1.1 | 3/3 | Complete | 2026-03-17 |
| 15. Enhanced Import | v1.1 | 3/3 | Complete | 2026-03-18 |
| 16. Game Card UI | v1.1 | 3/3 | Complete | 2026-03-18 |
| 17. PWA Foundation + Dev Workflow | v1.2 | 1/1 | Complete | 2026-03-20 |
| 18. Mobile Navigation | v1.2 | 1/1 | Complete | 2026-03-20 |
| 19. Mobile UX Polish + Install Prompt | v1.2 | 0/3 | Not started | - |

---
*Created: 2026-03-11*
*v1.0 shipped: 2026-03-15*
*v1.1 shipped: 2026-03-20*
*v1.2 roadmap added: 2026-03-20*
