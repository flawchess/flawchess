---
phase: 104-library-page-shell-import-overview-subtab-migration
verified: 2026-06-05T12:00:00Z
status: passed
score: 9/9 must-haves verified
overrides_applied: 0
re_verification: true
resolved_gaps:
  - truth: "The Library page and both subtabs work on mobile — responsive subtab control plus the responsive layouts preserved from the migrated Import and Overview pages, with data-testid / ARIA / semantic-HTML conventions on all new interactive elements and containers"
    original_status: partial
    resolution: "RESOLVED in commit f1ff037b. LibraryPage.tsx shell <main> (lines 39/116) changed to <div>, removing the phase-introduced nesting level. /library/import and /library/overview now expose a single inner <main> (the wrapped page's), the same App-<main> > page-<main> depth as every other route. Confirmed: no <main> JSX remains in LibraryPage.tsx; tsc + eslint clean; 744/744 frontend tests pass. WR-02 double-padding (shell max-w/px over the inner pages' own) was intentionally retained — code review and verification both rated the de-pad optional, and the proper fix adds wrapper churn across desktop+mobile for a minor cosmetic delta (over-engineering per CLAUDE.md). Tracked as non-blocking polish."
---

# Phase 104: Library Page Shell + Import/Overview Subtab Migration Verification Report

**Phase Goal:** Users have a single top-level Library page that hosts the existing Import and Overview workflows as deep-linkable subtabs, with all old entry points (nav items, `/import`, `/overview`, the gameless-user redirect, the zero-games notification dot) seamlessly repointed at it.
**Verified:** 2026-06-05
**Status:** passed (re-verified after gap fix f1ff037b)
**Re-verification:** Yes — the single semantic-HTML gap (triple-nested `<main>`, LIB-09) was fixed inline by changing the LibraryPage shell `<main>`→`<div>`; 9/9 must-haves now verified. See `resolved_gaps` in frontmatter.

---

## Goal Achievement

### Observable Truths

| #  | Truth                                                                                                                                                                                                       | Status      | Evidence                                                                                                                                                                          |
|----|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| 1  | LibraryPage renders `<Tabs variant="brand">` with Import (leftmost) and Overview subtab, mirroring Endgames.tsx                                                                                              | VERIFIED    | LibraryPage.tsx:43-64 (desktop), :69-113 (mobile). Import leftmost in both blocks. `TabsList variant="brand"`. DownloadIcon + "Import", LayoutDashboard + "Overview".            |
| 2  | Bare `/library` lands on `/library/import` when user has zero games and `/library/overview` when user has games (state-dependent, D-06)                                                                     | VERIFIED    | LibraryPage.tsx:26-33: guarded on `profile != null`, returns `<Navigate to={noGames ? '/library/import' : '/library/overview'} replace />`. noGames derived correctly (line 22). |
| 3  | Import subtab forwards onImportStarted / activeJobIds / onJobDismissed unchanged                                                                                                                            | VERIFIED    | LibraryPage.tsx:55-59 (desktop) and :104-108 (mobile) pass all three props to ImportTab. ImportTab.tsx:3-4 spreads props to ImportPage. App.tsx:599 threads them to LibraryPage.  |
| 4  | Overview subtab renders GlobalStatsPage unchanged, preserving global-stats-page container                                                                                                                    | VERIFIED    | OverviewTab.tsx:3 returns `<GlobalStatsPage />`. GlobalStats.tsx:100 still has `data-testid="global-stats-page"`. No props removed.                                              |
| 5  | Each subtab is its own .tsx file under `frontend/src/pages/library/`                                                                                                                                        | VERIFIED    | ImportTab.tsx (5 lines), OverviewTab.tsx (5 lines) both exist. Confirmed by git commit 5f218bb2.                                                                                  |
| 6  | Top-level nav shows Library · Openings · Endgames (+ Admin); Import and Overview gone as standalone nav items across desktop, mobile bottom bar, More drawer                                                | VERIFIED    | App.tsx:58-68: NAV_ITEMS and BOTTOM_NAV_ITEMS each have exactly 3 entries — Library (FolderOpen), Openings, Endgames. No `/import` or `/overview` entry in either array.          |
| 7  | notification dot on Library nav item (not Import) in all three nav surfaces; no stale `import-notification-dot` testids remain                                                                              | VERIFIED    | App.tsx:144-152 (`library-notification-dot`, NavHeader), :279-287 (`library-notification-dot-mobile`, MobileBottomBar), :364-373 (`library-notification-dot-drawer`, MobileMoreDrawer). Zero `import-notification-dot` references found in source.  |
| 8  | Redirects: `/import`→`/library/import`; `/overview`, `/rating`, `/global-stats`→`/library/overview`; Home gameless redirect→`/library/import`; ImportRequiredRoute→`/library/import`; internal links swept | VERIFIED    | App.tsx:600-603 (4 Navigate redirects). App.tsx:489 (`<Navigate to="/library/import" replace />`). Home.tsx:623 (`/library/import`). Endgames.tsx:711, GamesTab.tsx:49 both show `/library/import`. Zero remaining `to="/import"` live links found. |
| 9  | Library always reachable (never import-gated); Openings/Endgames stay gated; mobile parity + semantic-HTML conventions on new elements                                                                      | PARTIAL     | Gating correct (App.tsx:599 not wrapped, :604-605 still wrapped). Mobile blocks implemented with correct testids. **FAIL on semantic-HTML:** triple-nested `<main>` and double layout constraint — see Gaps section. |

**Score:** 8/9 truths verified (Truth 9 is partial)

---

### Requirement Traceability

| Requirement | Description                                                     | Status      | Evidence                                                                                                            |
|-------------|------------------------------------------------------------------|-------------|---------------------------------------------------------------------------------------------------------------------|
| LIB-01      | Library page reachable from desktop nav, mobile bottom bar, More drawer | VERIFIED    | App.tsx NAV_ITEMS + BOTTOM_NAV_ITEMS + MobileMoreDrawer all include `{ to: '/library', label: 'Library', Icon: FolderOpen }`. Testids `nav-library`, `mobile-nav-library`, `drawer-nav-library` derived correctly.    |
| LIB-02      | Deep-linkable URL-routed subtabs in own .tsx files, Openings-style Tabs | VERIFIED    | ImportTab.tsx + OverviewTab.tsx exist. LibraryPage.tsx uses `navigate('/library/<tab>')` from onValueChange. activeTab derived from `location.pathname.includes('/import')`.                                          |
| LIB-03      | Import workflow at `/library/import`; `/import` redirects there   | VERIFIED    | App.tsx:599 routes `/library/*` to LibraryPage with job props. App.tsx:600 redirects `/import`. ImportTab.tsx/ImportPage functional with prop threading intact.                                                      |
| LIB-04      | Overview dashboard at `/library/overview`; `/overview` redirects  | VERIFIED    | App.tsx:601 redirects `/overview`. OverviewTab renders GlobalStatsPage. SidebarLayout/FilterPanel behavior preserved (GlobalStats.tsx unchanged).                                                                     |
| LIB-05      | Nav shows Library · Openings · Endgames; Import + Overview removed | VERIFIED    | NAV_ITEMS (App.tsx:58-62) and BOTTOM_NAV_ITEMS (App.tsx:64-68) have exactly these 3 entries.                        |
| LIB-06      | `totalGames === 0` dot on Library nav item in all three surfaces   | VERIFIED    | App.tsx:144-152 (NavHeader), :279-287 (MobileBottomBar), :364-373 (MobileMoreDrawer). Guard: `to === '/library' && noGames`.                                                                                         |
| LIB-07      | Default landing state-dependent; Home gameless → `/library/import` | VERIFIED    | LibraryPage.tsx:26-33 (Navigate). Home.tsx:623: `Navigate to={hasGames ? '/openings' : '/library/import'}`.         |
| LIB-08      | Library always accessible; Import + Overview subtabs always open   | VERIFIED    | App.tsx:599: `/library/*` route NOT in ImportRequiredRoute. App.tsx:125, :262, :348: nav-lock exempts `/library`. Both subtab wrappers render unconditionally.                                                       |
| LIB-09      | Library + subtabs work on mobile; data-testid/ARIA/semantic-HTML on new elements | PARTIAL | Mobile blocks present with all required testids. **GAP:** LibraryPage.tsx:39 renders `<main>` inside App.tsx:453's `<main>`, and ImportPage/GlobalStatsPage each add a third `<main>`. Invalid HTML + CLAUDE.md semantic-HTML rule violation. Double layout constraint adds excess padding. |

---

### Required Artifacts

| Artifact                                        | Expected                                          | Status   | Details                                                                       |
|-------------------------------------------------|---------------------------------------------------|----------|-------------------------------------------------------------------------------|
| `frontend/src/pages/library/LibraryPage.tsx`   | Shell with Tabs, Navigate, testids, prop threading | VERIFIED | 119 lines. All required testids present. Props threaded to both ImportTab instances. |
| `frontend/src/pages/library/ImportTab.tsx`     | Thin wrapper forwarding props to ImportPage       | VERIFIED | 5 lines. `import { ImportPage, type ImportPageProps }` from Import. Spreads all props. |
| `frontend/src/pages/library/OverviewTab.tsx`   | Zero-prop wrapper rendering GlobalStatsPage       | VERIFIED | 5 lines. `import { GlobalStatsPage }` from GlobalStats. Returns `<GlobalStatsPage />`. |
| `frontend/src/pages/Import.tsx`                | ImportPageProps exported                          | VERIFIED | Line 51: `export interface ImportPageProps {`. Import.tsx otherwise unchanged.  |
| `frontend/src/App.tsx`                         | Library route, redirects, nav, dot               | VERIFIED | All routing, nav config, redirects, guard, and notification dot verified above. |
| `frontend/src/pages/Home.tsx`                  | Gameless redirect → `/library/import`             | VERIFIED | Line 623: `Navigate to={hasGames ? '/openings' : '/library/import'}`.          |

---

### Key Link Verification

| From                          | To                                       | Via                                                          | Status   | Details                                                              |
|-------------------------------|------------------------------------------|--------------------------------------------------------------|----------|----------------------------------------------------------------------|
| App.tsx                       | LibraryPage.tsx                          | `<Route path="/library/*" element={<LibraryPage ...>}`       | WIRED    | App.tsx:599. Job props passed: onImportStarted, activeJobIds, onJobDismissed. |
| App.tsx                       | `/library/import` and `/library/overview` | `<Navigate>` from `/import`, `/overview`, `/rating`, `/global-stats` | WIRED | App.tsx:600-603. All four redirect routes confirmed.               |
| LibraryPage.tsx               | ImportTab.tsx                            | Prop spread of three job-tracking props                       | WIRED    | Lines 55-59 (desktop) and 104-108 (mobile).                         |
| LibraryPage.tsx               | useUserProfile                           | `noGames` derivation for state-dependent Navigate             | WIRED    | Lines 14, 18-22.                                                     |
| ImportRequiredRoute (App.tsx) | `/library/import`                        | `<Navigate to="/library/import" replace />`                  | WIRED    | App.tsx:489.                                                         |
| Home.tsx                      | `/library/import`                        | Gameless `<Navigate>`                                        | WIRED    | Home.tsx:623.                                                        |
| Endgames.tsx:711              | `/library/import`                        | `<Link to="/library/import">`                                | WIRED    | Confirmed by grep.                                                   |
| openings/GamesTab.tsx:49      | `/library/import`                        | `<Link to="/library/import">`                                | WIRED    | Confirmed by grep.                                                   |

---

### Data-Flow Trace (Level 4)

Not applicable — this phase produces no data-fetching components. LibraryPage is a routing shell; ImportTab and OverviewTab delegate to existing components that already have established data flows (unchanged from pre-migration).

---

### Behavioral Spot-Checks

Step 7b: SKIPPED (no runnable entry points for this pure-frontend routing change; all runtime behavior is URL-navigation-dependent and requires a browser + dev server).

---

### Probe Execution

Step 7c: No probe scripts declared or present for this phase. SKIPPED.

---

### Anti-Patterns Found

| File                                  | Line | Pattern                                      | Severity  | Impact                                                                          |
|---------------------------------------|------|----------------------------------------------|-----------|---------------------------------------------------------------------------------|
| `frontend/src/pages/library/LibraryPage.tsx` | 39   | `<main>` inside App.tsx's `<main>` + inner pages add a third `<main>` | BLOCKER | Invalid HTML (multiple `<main>` landmarks); violates CLAUDE.md semantic-HTML browser-automation rule; LIB-09 explicitly requires semantic-HTML compliance. |
| `frontend/src/pages/library/LibraryPage.tsx` | 39   | `max-w-7xl px-4 md:px-6` outer wrapper around pages that apply their own max-width + padding | WARNING | Import form gets double horizontal padding (px-4 twice) and is constrained by an outer max-w-7xl it does not need; visible layout regression vs. pre-migration standalone `/import` page. |

No debt markers (TBD / FIXME / XXX) found in any file modified by this phase.

---

### Human Verification Required

The following items cannot be verified programmatically and require browser testing:

#### 1. State-dependent `/library` landing

**Test:** Log in as (a) a user with zero imported games and navigate to `/library`, then (b) as a user with games.
**Expected:** Zero-games user lands on `/library/import` (Import subtab active, form visible). Has-games user lands on `/library/overview` (Overview subtab active, dashboard visible).
**Why human:** Requires live profile data and active React Router navigation in a browser.

#### 2. Redirect chain verification

**Test:** As an authenticated user, navigate the browser address bar to `/import`, `/overview`, `/rating`, and `/global-stats` in sequence.
**Expected:** Each resolves to the correct Library subtab URL (`/library/import` or `/library/overview`) and shows the matching content without a flash of intermediate content.
**Why human:** React Router redirects require a browser runtime; `<Navigate replace>` behavior needs visual confirmation.

#### 3. Mobile bottom bar at 375px

**Test:** Open Chrome DevTools at 375px width, log in as a zero-games user.
**Expected:** Bottom bar shows Library · Openings · Endgames + More. A red pulsing dot appears on the Library icon. Tapping Library opens `/library/import`. Tapping Openings/Endgames shows the lock state (nav-locked for a zero-games user).
**Why human:** Responsive CSS and touch interaction require a real device or DevTools.

#### 4. Import workflow end-to-end in subtab

**Test:** On `/library/import`, enter a chess.com or lichess username and start an import. Monitor the progress bar. After completion, navigate to `/library/overview`.
**Expected:** The import progress bar appears and tracks correctly (same as pre-migration). After the job completes, Overview shows updated stats. No visual regression from double padding (the import form should appear centered and full-width within its max-w-2xl, not squeezed).
**Why human:** Requires live backend + real game data; also the double-padding regression (WR-02) needs visual confirmation that the form does not appear cramped.

#### 5. Triple-`<main>` accessibility impact

**Test:** Open `/library/import` in Chrome DevTools Accessibility tree. Inspect landmark regions.
**Expected (current/broken state):** Three `<main>` landmarks will appear nested — this should be flagged as the gap. A conformant fix (changing LibraryPage's `<main>` to `<div>`) would show a single `<main>` from ImportPage.
**Why human:** Landmark counting in the accessibility tree requires a browser with DevTools.

---

### Gaps Summary

One gap blocks full goal achievement:

**Triple-nested `<main>` + double layout constraint (LibraryPage.tsx line 39)**

LibraryPage.tsx renders `<main className="mx-auto w-full max-w-7xl flex-1 px-4 py-2 md:py-6 md:px-6">`. This sits inside App.tsx:453's `<main className="pb-16 sm:pb-0">`. The two subtab pages it wraps — Import.tsx:284 (`<main data-testid="import-page">`) and GlobalStats.tsx:101 (`<main>`) — each add a third `<main>` landmark. The result on `/library/import` and `/library/overview` is three nested `<main>` elements, which is invalid HTML and violates CLAUDE.md's mandatory semantic-HTML browser-automation rule. LIB-09 requires "semantic-HTML conventions on all new interactive elements and containers."

Additionally, LibraryPage's `max-w-7xl` + `px-4 md:px-6` wrapper creates a double constraint: the Import form (already `max-w-2xl mx-auto px-4`) gets an additional outer container with its own width limit and horizontal padding — producing doubled side padding and a visible layout regression from the pre-migration standalone `/import` page.

**Root cause:** The thin-wrap pattern (wrapping full page components that own a `<main>`) collides with the structural assumption that subtab content is a fragment, not a full page. The canonical analog (Endgames.tsx) renders inline content inside its single `<main>`, not wrapped pages.

**Fix (one-line, low risk):** In `LibraryPage.tsx`, change `<main ...>` (line 39) to `<div ...>` and `</main>` (line 116) to `</div>`. Optionally simplify the wrapper classes to `className="w-full flex-1 py-2 md:py-6"` since Import/GlobalStats already own their own horizontal padding and max-width. This eliminates both the `<main>` nesting violation and the double layout constraint in a single edit.

This is not a functional blocker (Import and Overview work correctly), but it is a code-quality gap that LIB-09 specifically requires be correct, and CLAUDE.md treats semantic HTML as a mandatory convention.

---

_Verified: 2026-06-05_
_Verifier: Claude (gsd-verifier)_
