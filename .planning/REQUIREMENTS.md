# Requirements: Chessalytics

**Defined:** 2026-03-20
**Core Value:** Users can determine their success rate for any opening position they specify, filtering by their own pieces only, regardless of how platforms categorize the opening.

## v1.2 Requirements

Requirements for Mobile & PWA milestone. Each maps to roadmap phases.

### PWA

- [x] **PWA-01**: App has a web manifest with name, icons, theme color, and display:standalone
- [x] **PWA-02**: Service worker precaches static assets for fast repeat loads (NetworkOnly for API routes)
- [x] **PWA-03**: App has custom chess-themed icons (192px + 512px PNG) replacing default Vite favicon
- [ ] **PWA-04**: User sees an in-app install prompt on Chromium browsers after engagement
- [ ] **PWA-05**: iOS users see manual "Add to Home Screen" instructions since beforeinstallprompt is unavailable

### Mobile Navigation

- [x] **NAV-01**: User sees a hamburger menu on mobile screens that opens a slide-in drawer with all nav links and logout
- [x] **NAV-02**: Drawer closes on link tap and highlights the active route
- [x] **NAV-03**: App content respects safe-area insets on notched iPhones in standalone PWA mode

### Mobile UX

- [ ] **UX-01**: All interactive elements (buttons, filters, controls) meet 44x44px minimum touch target
- [ ] **UX-02**: No page shows horizontal scroll at 375px viewport width
- [ ] **UX-03**: Chessboard drag-and-drop and click-to-click moves work correctly on mobile devices
- [ ] **UX-04**: Sidebar (chessboard + filters) and main content (Moves/Games/Statistics) are both usable on mobile without excessive scrolling

### Dev Workflow

- [x] **DEV-01**: npm script exposes Vite dev server on LAN for same-network phone testing
- [x] **DEV-02**: Documented one-command Cloudflare Tunnel setup for HTTPS phone testing

## Future Requirements

Deferred to future release. Tracked but not in current roadmap.

### PWA Enhancements

- **PWA-F01**: TanStack Query persistence adapter for faster re-renders on slow mobile connections
- **PWA-F02**: Push notifications for import completion

### Mobile UX Enhancements

- **UX-F01**: Bottom navigation bar (revisit if hamburger proves insufficient)

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| Offline API data caching | Chess data is user-specific + authenticated; caching risks stale analysis; import requires network anyway |
| Background sync for imports | Web Background Sync API has limited support; server-side jobs persist; user refreshes to resume |
| Swipe-to-navigate between tabs | Conflicts with chessboard drag-and-drop touch gestures |
| Tablet-specific layouts | Phone-first; tablet gets free improvements from responsive work; optimize later if needed |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| PWA-01 | Phase 17 | Complete |
| PWA-02 | Phase 17 | Complete |
| PWA-03 | Phase 17 | Complete |
| PWA-04 | Phase 19 | Pending |
| PWA-05 | Phase 19 | Pending |
| NAV-01 | Phase 18 | Complete |
| NAV-02 | Phase 18 | Complete |
| NAV-03 | Phase 18 | Complete |
| UX-01 | Phase 19 | Pending |
| UX-02 | Phase 19 | Pending |
| UX-03 | Phase 19 | Pending |
| UX-04 | Phase 19 | Pending |
| DEV-01 | Phase 17 | Complete |
| DEV-02 | Phase 17 | Complete |

**Coverage:**
- v1.2 requirements: 14 total
- Mapped to phases: 14
- Unmapped: 0 ✓

---
*Requirements defined: 2026-03-20*
*Last updated: 2026-03-20 after roadmap creation*
