# Phase 104: Library Page Shell + Import & Overview Subtab Migration - Context

**Gathered:** 2026-06-05
**Status:** Ready for planning

<domain>
## Phase Boundary

A **pure frontend restructure + route migration**. Introduce `/library` as a new top-level nav destination that hosts the existing **Import** and **Overview** workflows as deep-linkable, URL-routed subtabs (`/library/import`, `/library/overview`), each its own `.tsx` mirroring the Openings page structure. Repoint every old entry point at the new structure: top-level nav drops to **Library · Openings · Endgames** (+ superuser Admin), the `totalGames === 0` notification dot moves to the Library nav item, `/import` and `/overview` redirect into the subtabs, and the bare `/library` route lands state-dependently (zero games → Import, has games → Overview).

**No backend endpoints. No schema changes. No new business logic.** This is the first slice of SEED-036; the Games subtab, Analysis viewer, mistake-detection backend, and best-move endpoint are **explicitly out of scope** and not roadmapped (they live in `.planning/seeds/SEED-036-library-page-milestone.md`).

</domain>

<decisions>
## Implementation Decisions

### Library nav identity
- **D-01:** The Library top-level nav item uses the lucide **`FolderOpen`** icon (user override of the recommended `Library` icon — reads as "a collection you open"). Applies to desktop nav, mobile bottom bar, and the mobile "More" drawer.

### Subtab presentation
- **D-02:** Two subtabs only, in order: **Import** (leftmost), **Overview**. Each is its own `.tsx` file under `frontend/src/pages/library/` mirroring the `frontend/src/pages/openings/*Tab.tsx` split.
- **D-03:** Subtab triggers reuse the **existing nav icons + plain text labels**: Import subtab = `Download` icon + "Import"; Overview subtab = `LayoutDashboard` icon + "Overview". Mirrors the Openings/Endgames icon+label `<TabsTrigger>` style for visual parity.
- **D-04:** **No `InfoPopover`** on the subtab triggers (unlike the Openings tabs). Import and Overview are self-explanatory pre-existing surfaces. Revisit only if the Games/Analysis subtabs (future phases) arrive needing explanation.

### Landing & routing behavior
- **D-05:** **Returning-user app landing stays `/openings`.** `Home.tsx`'s has-games redirect is NOT changed to point at Library/Overview (SEED-036's flagged open question resolved: keep current behavior; Library is reachable via the nav). Only the **gameless** redirect changes: `/import` → `/library/import`.
- **D-06:** Bare `/library` redirects state-dependently, mirroring the Openings page-level `<Navigate ... replace />` pattern: zero games → `/library/import`, has games → `/library/overview` (LIB-07).
- **D-07:** Subtab switching uses the Openings pattern exactly — `navigate('/library/<tab>')` from `<Tabs onValueChange>`, active tab derived from `location.pathname`, `/library/*` wildcard route. Deep-linkable (LIB-02).

### Gating
- **D-08:** The `/library` route is **always accessible** — NOT wrapped in `ImportRequiredRoute` (it hosts Import, so it can never be import-gated). Both Import and Overview subtabs are always open. No subtab-level gating exists in this phase (Games/Analysis, which the seed gates, are out of scope). Openings/Endgames stay route-gated exactly as today (LIB-08).
- **D-09:** The nav-lock exemption logic that currently special-cases `to !== '/import'` must be updated so **Library** is the always-unlocked top-level item (replacing the Import exemption) across `NavHeader`, `MobileBottomBar`, and `MobileMoreDrawer`.

### Notification dot
- **D-10:** The `totalGames === 0` red notification dot moves from the Import nav item to the **Library** nav item, in all three nav surfaces (LIB-06). Same `data-testid` convention; rename to a `library-notification-dot` test id.

### Mobile bottom bar (default — not explicitly discussed)
- **D-11:** `BOTTOM_NAV_ITEMS` becomes **Library · Openings · Endgames** + the existing "More" button (account/admin remain in the More drawer). Resolved via sensible default; user did not flag a different arrangement.

### Old-route redirects & internal links
- **D-12:** Add redirects `/import` → `/library/import` and `/overview` → `/library/overview` (LIB-03, LIB-04). The existing `/rating` and `/global-stats` → `/overview` aliases (`App.tsx:592-593`) must continue to resolve (chain through to `/library/overview` or be repointed directly).
- **D-13:** Sweep internal `<Link to="/import">` references to `/library/import` (`Endgames.tsx:711`, `pages/openings/GamesTab.tsx:49`) and the `ImportRequiredRoute` redirect target (`App.tsx:479`, currently `<Navigate to="/import">`).

### Import.tsx prop threading (planner detail)
- **D-14:** `Import.tsx` (`ImportPage`) takes App-level job-tracking props (`onImportStarted`, `activeJobIds`, `onJobDismissed`) wired from `App.tsx` state. When Import becomes a subtab rendered by the Library page, these props must thread App → Library page → Import subtab. Import progress/job state stays owned by `App.tsx` (no behavior change — the full Import workflow must remain intact, LIB-03). Mechanism is the planner's call; the constraint is identical runtime behavior.

### Claude's Discretion
- Exact file/component names under `frontend/src/pages/library/` (suggest `LibraryPage` + `ImportTab.tsx` / `OverviewTab.tsx`, mirroring `pages/openings/`).
- Whether `GlobalStats.tsx` is moved wholesale into the Overview subtab file or wrapped — preserve `GlobalStatsPage`'s behavior and its `global-stats-page` test id (or rename consistently); keep the SidebarLayout/drawer filter behavior intact.
- Desktop vs mobile subnav markup follows the Openings `<Tabs variant="brand">` + sticky mobile subnav pattern; reuse, don't reinvent.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Milestone vision & scope
- `.planning/seeds/SEED-036-library-page-milestone.md` — full Library milestone vision; **§"Page structure — DECIDED"** and the 2026-06-04 nav-refinement decision log are the authority for this phase. Note: Games/Analysis subtabs, mistake-detection, best-move endpoint are FUTURE phases, NOT this one.
- `.planning/ROADMAP.md` — Phase 104 block (Goal, 5 Success Criteria, LIB-01..09 mapping).
- `.planning/REQUIREMENTS.md` — LIB-01..09 requirement text (lines 14-22; status table 55-63).

### Patterns to mirror (frontend)
- `frontend/src/pages/Openings.tsx` — the canonical URL-routed `<Tabs variant="brand">` subtab pattern: active-tab-from-pathname derivation (~111-127), desktop tab block (~779-828), sticky mobile subnav (~880-928), page-level default-subtab `<Navigate ... replace />` (683, 687), `openings-page` container (691).
- `frontend/src/pages/Endgames.tsx` — same pattern with 2 subtabs (~840-871); closest structural analog to Library's 2-subtab shape.
- `frontend/src/pages/openings/*Tab.tsx` (`ExplorerTab`, `GamesTab`, `StatsTab`, `InsightsTab`) — the per-subtab `.tsx` split convention to copy.

### Files to modify / migrate
- `frontend/src/App.tsx` — routes (~578-596), `NAV_ITEMS`/`BOTTOM_NAV_ITEMS` (59-71), `ImportRequiredRoute` guard (462-482) + its `/import` redirect (479), `NavHeader` (97-200), `MobileBottomBar` (244-322), `MobileMoreDrawer` (326-384), notification-dot + nav-lock logic (101-164, 264-348), route-label map (80-83), existing `/rating` `/global-stats` aliases (592-593).
- `frontend/src/pages/Import.tsx` — `ImportPage` (493 lines), props `onImportStarted`/`activeJobIds`/`onJobDismissed`, container `import-page` (383). Migrates to `/library/import` subtab.
- `frontend/src/pages/GlobalStats.tsx` — `GlobalStatsPage` (185 lines, no props), container `global-stats-page` (100), uses `SidebarLayout`/`FilterPanel`/`RatingChart`/`GlobalStatsCharts`. Migrates to `/library/overview` subtab.
- `frontend/src/pages/Home.tsx` — gameless redirect (623): `/import` → `/library/import`; has-games stays `/openings` (D-05).
- `frontend/src/pages/Endgames.tsx` (711) and `frontend/src/pages/openings/GamesTab.tsx` (49) — `<Link to="/import">` → `/library/import`.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `<Tabs variant="brand">` / `<TabsList>` / `<TabsTrigger>` / `<TabsContent>` (Radix wrapper) — drives all existing subtab controls; reuse verbatim for Library.
- `useUserProfile()` → `chess_com_game_count + lichess_game_count` = `totalGames`; the single source for `noGames`, has-games landing, and the notification dot.
- `useReadiness()` → `tier1`; combined with totalGames gives `navUnlocked` for nav-lock logic.
- `SidebarLayout` + `FilterPanel` (used by GlobalStats) — keep intact when Overview becomes a subtab.

### Established Patterns
- Page-level default-subtab resolution is a `<Navigate to="/<page>/<defaultTab>" replace />` returned from the page component (Openings 683/687) — Library uses the state-dependent variant (D-06).
- Nav `data-testid` is derived: `nav-${label.toLowerCase()}`, `mobile-nav-${...}`, `drawer-nav-${...}`; tab triggers `tab-${name}` / `tab-${name}-mobile`. New code follows the same derivation → `nav-library`, `tab-import`, `tab-overview`.
- Nav-lock exemption is currently `to !== '/import' && to !== '/admin'`; becomes Library-exempt (D-09).

### Integration Points
- App-level import-job state (`activeJobIds`, handlers) is owned by `App.tsx` and passed into `ImportPage`; the Library page must forward these unchanged (D-14).
- The `ImportRequiredRoute` guard redirect target and `Home.tsx` gameless redirect are the two redirect seams that must point at `/library/import`.

</code_context>

<specifics>
## Specific Ideas

- Library nav icon: explicitly **`FolderOpen`** (lucide), chosen by the user over `Library`/`BookMarked`/`Archive`.
- "A library is a collection you stock (Import) then browse" — SEED-036's framing; informs the FolderOpen choice and the Import-leftmost ordering.

</specifics>

<deferred>
## Deferred Ideas

- **Games subtab** (filterable archive + eval-derived mistake-type filter + mistake-stats panel) — SEED-036 future phase. Out of scope here.
- **Analysis subtab** (full-width board, stepper, move list, eval/material timeline, on-demand best-move) — SEED-036 future phase.
- **Mistake-detection service + classification, best-move endpoint** — backend, SEED-036 future phases.
- **Subtab-level import gating** (Games/Analysis behind the import-required guard) — only relevant once those subtabs exist; this phase has no gated subtabs.
- **Subtab InfoPopovers** — deferred with the Games/Analysis subtabs that would actually need explaining (D-04).
- **Changing the returning-user landing to Library/Overview** — considered and rejected for now (D-05); keep `/openings`.

</deferred>

---

*Phase: 104-library-page-shell-import-overview-subtab-migration*
*Context gathered: 2026-06-05*
