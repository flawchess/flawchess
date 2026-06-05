# Phase 104: Library Page Shell + Import & Overview Subtab Migration - Pattern Map

**Mapped:** 2026-06-05
**Files analyzed:** 9 (3 new, 6 modified)
**Analogs found:** 9 / 9 (all in-repo; pure frontend restructure)

> All line numbers below were re-verified against the current working tree. The
> CONTEXT.md / UI-SPEC.md references had drifted in several places (App.tsx
> NAV_ITEMS, ImportRequiredRoute, route block, the `to !== '/import'` exemptions,
> Import.tsx container) — **use the line numbers in THIS file**, not the ones in
> 104-CONTEXT.md / 104-UI-SPEC.md.

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `frontend/src/pages/library/LibraryPage.tsx` (NEW) | page-shell / route | request-response (URL-routed tabs) | `frontend/src/pages/Endgames.tsx` | exact (2-subtab Tabs page) |
| `frontend/src/pages/library/ImportTab.tsx` (NEW) | subtab wrapper | request-response (forwards props) | `frontend/src/pages/openings/GamesTab.tsx` | role-match (subtab split) |
| `frontend/src/pages/library/OverviewTab.tsx` (NEW) | subtab wrapper | request-response | `frontend/src/pages/openings/GamesTab.tsx` | role-match (subtab split) |
| `frontend/src/App.tsx` (MOD) | router / nav config | request-response | self (in-file patterns) | exact |
| `frontend/src/pages/Import.tsx` (MOD) | page (becomes subtab content) | request-response + polling | self (interface preserved) | n/a (no structural change) |
| `frontend/src/pages/GlobalStats.tsx` (MOD) | page (becomes subtab content) | CRUD (read aggregates) | self (interface preserved) | n/a (no structural change) |
| `frontend/src/pages/Home.tsx` (MOD) | redirect | request-response | self (line 623) | exact |
| `frontend/src/pages/Endgames.tsx` (MOD) | internal link sweep | — | self (line 711) | exact |
| `frontend/src/pages/openings/GamesTab.tsx` (MOD) | internal link sweep | — | self (line 49) | exact |

**Key structural finding:** `Endgames.tsx` is the single closest analog for
`LibraryPage.tsx` — it is the only existing page with **exactly two**
URL-routed `<Tabs variant="brand">` subtabs. Copy its shell wholesale and strip
the sidebar/filter machinery (Library's subtabs own their own filters).

**Key threading finding (D-14):** No existing page component receives props from
`App.tsx`. `OpeningsPage`, `EndgamesPage`, and `GlobalStatsPage` are all
zero-prop (`pages/Openings.tsx:111`, `pages/Endgames.tsx:88`,
`pages/GlobalStats.tsx:16`). `ImportPage` is the *only* component that takes
App-level props, and it is currently rendered **directly by a route**
(`App.tsx:589`). Threading App → LibraryPage → ImportTab → ImportPage is
**net-new** — there is no in-repo precedent to copy. See Shared Patterns §
"Prop Threading" for the exact mechanism.

---

## Pattern Assignments

### `frontend/src/pages/library/LibraryPage.tsx` (NEW — page-shell, request-response)

**Primary analog:** `frontend/src/pages/Endgames.tsx` (2-subtab `<Tabs variant="brand">` page).
**Secondary analog:** `frontend/src/pages/Openings.tsx` (page-level `<Navigate>` resolution).

**Active-tab-from-pathname derivation** — copy `Endgames.tsx:98`, invert the two values:
```tsx
// Endgames.tsx:98 (analog)
const activeTab = location.pathname.includes('/games') ? 'games' : 'stats';
// Library: Import is leftmost/default-on-/import, Overview otherwise
const activeTab = location.pathname.includes('/import') ? 'import' : 'overview';
```

**State-dependent page-level redirect** — combine `Openings.tsx:682-684` (the
`<Navigate ... replace />` early-return pattern) with the `noGames` source from
`App.tsx:101-102`. Note the analog is a *static* target; Library is *state-dependent* (D-06):
```tsx
// Openings.tsx:682-684 (analog — static target)
if (needsRedirect) {
  return <Navigate to="/openings/explorer" replace />;
}
// Library (D-06 — state-dependent). `noGames` derived like App.tsx:101-102:
//   const totalGames = profile != null ? profile.chess_com_game_count + profile.lichess_game_count : 0;
//   const noGames = profile != null && totalGames === 0;
if (location.pathname === '/library' || location.pathname === '/library/') {
  return <Navigate to={noGames ? '/library/import' : '/library/overview'} replace />;
}
```

**Profile / totalGames source** — copy verbatim from `App.tsx:101-102` (the
canonical `noGames` derivation used by every nav surface):
```tsx
// App.tsx:101-102
const totalGames = profile != null ? profile.chess_com_game_count + profile.lichess_game_count : 0;
const noGames = profile != null && totalGames === 0;
```
Source hook: `useUserProfile()` (imported in App.tsx:22; same import path `@/hooks/useUserProfile`).

**Desktop tab block** — copy `Endgames.tsx:840-871`, drop the `SidebarLayout`
wrapper and the `InfoPopover` slot (D-04: no popovers on Library triggers),
swap icons/labels (D-03: `DownloadIcon`+"Import", `LayoutDashboard`+"Overview"):
```tsx
// Endgames.tsx:840-864 (analog — strip InfoPopover + SidebarLayout for Library)
<Tabs value={activeTab} onValueChange={(val) => navigate(`/endgames/${val}`)}>
  <TabsList variant="brand" className="w-full" data-testid="endgames-tabs">
    <TabsTrigger value="stats" data-testid="tab-stats" className="flex-1">
      <BarChart2Icon className="mr-1.5 h-4 w-4" />
      Stats
      {/* InfoPopover slot here — OMIT for Library (D-04) */}
    </TabsTrigger>
    <TabsTrigger value="games" data-testid="tab-games" className="flex-1">
      <SwordsIcon className="mr-1.5 h-4 w-4" />
      Games
    </TabsTrigger>
  </TabsList>
  <TabsContent value="stats" className="mt-4">{statisticsContent}</TabsContent>
  <TabsContent value="games" className="mt-4">{gamesContent}</TabsContent>
</Tabs>
```
Library desktop `onValueChange` → `navigate(`/library/${val}`)`. Test ids:
`library-tabs`, `tab-import`, `tab-overview`.

**Sticky mobile subnav** — copy `Endgames.tsx:877-903` but **drop the filter
button** (Endgames.tsx:904-927) entirely; Library's subtabs manage their own
filters (UI-SPEC "Layout Patterns" note). Keep the `window.scrollTo` on switch:
```tsx
// Endgames.tsx:877-903 (analog — REMOVE the Tooltip/filter Button at 904-927)
<Tabs value={activeTab} onValueChange={(val) => { navigate(`/endgames/${val}`); window.scrollTo({ top: 0 }); }}>
  <div className="sticky top-0 z-20 flex items-center gap-2 h-[52px] bg-white/20 backdrop-blur-md rounded-md px-1 py-1"
       data-testid="endgames-mobile-control-row">
    <TabsList variant="brand" className="flex-1 !h-full !p-0" data-testid="endgames-tabs-mobile">
      <TabsTrigger value="stats" className="flex-1" data-testid="tab-stats-mobile"> ... </TabsTrigger>
      <TabsTrigger value="games" className="flex-1" data-testid="tab-games-mobile"> ... </TabsTrigger>
    </TabsList>
  </div>
  <TabsContent value="stats" className="mt-4"> ... </TabsContent>
  <TabsContent value="games" className="mt-4"> ... </TabsContent>
</Tabs>
```
Library mobile test ids: `library-tabs-mobile`, `library-mobile-control-row`,
`tab-import-mobile`, `tab-overview-mobile`.

**Page container** — copy `Endgames.tsx:813-815` (the outer wrapper + `<main>`),
rename test id `endgames-page` → `library-page`:
```tsx
// Endgames.tsx:813-815 (analog)
<div data-testid="endgames-page" className="flex min-h-0 flex-1 flex-col bg-background">
  <main className="mx-auto w-full max-w-7xl flex-1 px-4 py-2 md:py-6 md:px-6">
```

**Hooks/imports** — copy the `react-router-dom` import shape from `Endgames.tsx:2`
(`useNavigate, useLocation, Navigate`) and the Tabs import from `Endgames.tsx:16`
(`import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs'`).
`DownloadIcon` / `LayoutDashboard` come from `lucide-react` (already imported in App.tsx:13).

> **Do NOT copy** Endgames' `SidebarLayout`, `FilterPanel`, `useFilterStore`,
> insights-cache, modified-dot, or `useReadiness` tier-gating machinery
> (`Endgames.tsx:103-356`, `801-803`, `817-838`, `904-951`). Library is not
> tier-gated (D-08) and owns no filters at the shell level.

---

### `frontend/src/pages/library/ImportTab.tsx` (NEW — subtab wrapper, request-response)

**Analog:** `frontend/src/pages/openings/GamesTab.tsx` (the per-subtab `.tsx`
split convention — a focused props interface + a default-exported function component).

**Recommended approach (UI-SPEC "File Structure" — thin-wrap, not move):**
`ImportTab` re-declares the same three props as `ImportPageProps` and renders
`<ImportPage {...props} />`. This preserves `ImportPage`'s `import-page` test id
and its entire job-tracking workflow with a near-zero diff to `Import.tsx`.

**Props-interface pattern** — mirror `GamesTab.tsx:9-20` (typed prop object,
destructured in the signature) and reuse `ImportPageProps` from `Import.tsx:51-55`:
```tsx
// Import.tsx:51-55 (the interface ImportTab must forward)
interface ImportPageProps {
  onImportStarted: (jobId: string) => void;
  activeJobIds: string[];
  onJobDismissed: (jobId: string) => void;
}
```
```tsx
// GamesTab.tsx:9-33 (analog: subtab props interface + destructured signature)
type GamesTabProps = { gamesQuery: ...; hasNoGames: boolean; /* ... */ };
export function GamesTab({ gamesQuery, hasNoGames, /* ... */ }: GamesTabProps) {
```
ImportTab signature: `export function ImportTab(props: ImportTabProps)` where
`ImportTabProps` = the same three fields, forwarded as `<ImportPage {...props} />`.
Consider exporting `ImportPageProps` from `Import.tsx` (currently un-exported,
`Import.tsx:51`) so `ImportTab` imports the type instead of re-declaring it.

---

### `frontend/src/pages/library/OverviewTab.tsx` (NEW — subtab wrapper, request-response)

**Analog:** `frontend/src/pages/openings/GamesTab.tsx` (subtab split convention).

`GlobalStatsPage` takes **no props** (`GlobalStats.tsx:16`), so `OverviewTab` is
a zero-prop thin wrapper: `export function OverviewTab() { return <GlobalStatsPage />; }`.
This preserves the `global-stats-page` test id (`GlobalStats.tsx:100`) and the
intact `SidebarLayout` + `FilterPanel` + `RatingChart` + `GlobalStatsCharts`
behavior (`GlobalStats.tsx:99-101`, sidebar block at `103+`). No structural
change to `GlobalStats.tsx` itself.

---

### `frontend/src/App.tsx` (MOD — router / nav config, request-response)

This file holds the bulk of the migration. All references below re-verified.

**`NAV_ITEMS` / `BOTTOM_NAV_ITEMS`** (`App.tsx:59-71`) — replace the `/import` +
`/overview` entries with a single `/library` entry (D-05, D-11). `FolderOpen`
must be added to the lucide import at `App.tsx:13`:
```tsx
// App.tsx:59-64 (current — to be replaced)
const NAV_ITEMS = [
  { to: '/import', label: 'Import', Icon: DownloadIcon },
  { to: '/openings', label: 'Openings', Icon: BookOpenIcon },
  { to: '/endgames', label: 'Endgames', Icon: TrophyIcon },
  { to: '/overview', label: 'Overview', Icon: LayoutDashboard },
] as const;
// Target (D-01/D-11): { to: '/library', label: 'Library', Icon: FolderOpen } leftmost,
// then Openings, Endgames. Drop the standalone Import and Overview entries.
// Apply identically to BOTTOM_NAV_ITEMS (App.tsx:66-71).
```

**`ROUTE_TITLES`** (`App.tsx:79-85`) — add `/library`, remove `/import` +
`/overview`. `MobileHeader` (`App.tsx:207-209`) already resolves the title via
`startsWith`, so `/library/import` and `/library/overview` will both show "Library":
```tsx
// App.tsx:79-85 (current)
const ROUTE_TITLES: Record<string, string> = {
  '/import': 'Import',
  '/openings': 'Openings',
  '/endgames': 'Endgames',
  '/overview': 'Overview',
  '/admin': 'Admin',
};
// Target: '/library': 'Library' (drop '/import', '/overview').
```

**`isActive` helper** (`App.tsx:89-93`) — add a `/library` prefix branch so
`/library/import` and `/library/overview` highlight the Library nav item:
```tsx
// App.tsx:89-93 (current)
function isActive(to: string, pathname: string): boolean {
  if (to === '/openings') return pathname.startsWith('/openings');
  if (to === '/endgames') return pathname.startsWith('/endgames');
  return pathname === to;
}
// Add: if (to === '/library') return pathname.startsWith('/library');
```

**Nav-lock exemption** — three identical sites, each currently exempts `/import`.
Change `'/import'` → `'/library'` (D-09). These are the corrected line numbers:
```tsx
// NavHeader        App.tsx:128 — const locked = to !== '/import' && to !== '/admin' && !navUnlocked;
// MobileBottomBar  App.tsx:264 — const locked = to !== '/import' && !navUnlocked;
// MobileMoreDrawer App.tsx:348 — const locked = to !== '/import' && to !== '/admin' && !navUnlocked;
```

**Notification dot (MOVE)** — the `totalGames === 0` red dot currently lives on
the `/import` nav item in all three surfaces. Repoint the `to === '/import'`
guard to `to === '/library'` and rename the test ids (D-10). The corrected sites:
```tsx
// NavHeader        App.tsx:147-155  (testid import-notification-dot        → library-notification-dot)
// MobileBottomBar  App.tsx:281-289  (testid import-notification-dot-mobile → library-notification-dot-mobile)
// MobileMoreDrawer — NOTE: the current More-drawer markup (App.tsx:347-367) renders NO notification dot.
//                    Adding one (testid library-notification-dot-drawer) is net-new; copy the dot span
//                    from App.tsx:147-154 and gate on `to === '/library' && noGames`.
```
The dot markup to copy (from `App.tsx:147-154`):
```tsx
{to === '/import' && noGames && (
  <span className="absolute top-0.5 right-0.5 flex h-2.5 w-2.5" data-testid="import-notification-dot">
    <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-red-500 opacity-75" />
    <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-red-500" />
  </span>
)}
```
Note: `MobileMoreDrawer` (`App.tsx:326-335`) already computes `totalGames` but
**not** `noGames` — add `const noGames = profile != null && totalGames === 0;`
if you render the drawer dot.

**Routes block** (`App.tsx:588-596`) — repoint to the Library shell + add
redirects. `ImportPage` props move from the route onto `LibraryPage` (D-14):
```tsx
// App.tsx:588-596 (current)
<Route element={<ProtectedLayout />}>
  <Route path="/import" element={<ImportPage onImportStarted={handleImportStarted} activeJobIds={activeJobIds} onJobDismissed={handleJobDismissed} />} />
  <Route path="/openings/*" element={<ImportRequiredRoute><OpeningsPage /></ImportRequiredRoute>} />
  <Route path="/endgames/*" element={<ImportRequiredRoute><EndgamesPage /></ImportRequiredRoute>} />
  <Route path="/rating" element={<Navigate to="/overview" replace />} />
  <Route path="/global-stats" element={<Navigate to="/overview" replace />} />
  <Route path="/overview" element={<ImportRequiredRoute><GlobalStatsPage /></ImportRequiredRoute>} />
  <Route path="/admin" element={<SuperuserRoute><AdminPage /></SuperuserRoute>} />
</Route>
```
Target shape (D-06/D-08/D-12):
```tsx
// /library is a wildcard, NOT wrapped in ImportRequiredRoute (D-08), and carries the job props (D-14):
<Route path="/library/*" element={<LibraryPage onImportStarted={handleImportStarted} activeJobIds={activeJobIds} onJobDismissed={handleJobDismissed} />} />
// Old-route redirects (D-12) — repoint aliases directly to the new target, not via /overview:
<Route path="/import"       element={<Navigate to="/library/import" replace />} />
<Route path="/overview"     element={<Navigate to="/library/overview" replace />} />
<Route path="/rating"       element={<Navigate to="/library/overview" replace />} />
<Route path="/global-stats" element={<Navigate to="/library/overview" replace />} />
```
> The `<Navigate to="/library" replace />` for the bare `/library` path is
> handled **inside** `LibraryPage` (state-dependent, D-06), not in the route
> table — mirrors how Openings/Endgames resolve their default subtab in-component.

**`ImportRequiredRoute` redirect target** (`App.tsx:479`) — `<Navigate to="/import" replace />`
→ `<Navigate to="/library/import" replace />` (D-13):
```tsx
// App.tsx:478-480 (current)
if (shouldRedirect) {
  return <Navigate to="/import" replace />;
}
```

**Import cleanup** — `ImportPage` is no longer rendered directly by App; it is
imported by `ImportTab`. Remove the now-unused `ImportPage` import at `App.tsx:25`
**only if** App no longer references it (knip in CI will flag a dead import — see
CLAUDE.md "Knip runs in CI"). `GlobalStatsPage` import at `App.tsx:29` likewise
moves to `OverviewTab`. Verify with `npm run knip` before merge.

---

### `frontend/src/pages/Import.tsx` (MOD — interface preserved)

No structural change required. Keep `ImportPageProps` (`Import.tsx:51-55`),
`export function ImportPage(...)` (`Import.tsx:174`), and the `import-page`
container test id (`Import.tsx:284`). **Recommended diff:** add `export` to the
`ImportPageProps` interface (`Import.tsx:51`) so `ImportTab` can import the type
rather than duplicate it. Everything else stays intact (LIB-03 behavioral parity).

---

### `frontend/src/pages/GlobalStats.tsx` (MOD — interface preserved)

No change required. `GlobalStatsPage` (`GlobalStats.tsx:16`) is already zero-prop
and self-contained (its `global-stats-page` container at `GlobalStats.tsx:100`,
`SidebarLayout`/`FilterPanel` at `103+`). `OverviewTab` wraps it as-is.

---

### `frontend/src/pages/Home.tsx` (MOD — redirect)

**Single-line change** at `Home.tsx:623` (D-05/D-13): gameless target `/import`
→ `/library/import`; has-games target stays `/openings` (explicitly unchanged, D-05):
```tsx
// Home.tsx:621-623 (current)
const hasGames =
  (profile?.chess_com_game_count ?? 0) + (profile?.lichess_game_count ?? 0) > 0;
return <Navigate to={hasGames ? '/openings' : '/import'} replace />;
// Target: <Navigate to={hasGames ? '/openings' : '/library/import'} replace />;
```

---

### `frontend/src/pages/Endgames.tsx` & `frontend/src/pages/openings/GamesTab.tsx` (MOD — link sweep)

**Single-line `<Link>` href change** each (D-13), `/import` → `/library/import`:
```tsx
// Endgames.tsx:711           <Link to="/import">Import Games</Link>
// openings/GamesTab.tsx:49   <Link to="/import">Import Games</Link>
```

---

## Shared Patterns

### Notification Dot
**Source:** `App.tsx:147-154` (desktop, h-2.5) and `App.tsx:282-288` (mobile, h-2).
**Apply to:** Library nav item in NavHeader, MobileBottomBar, and (net-new) MobileMoreDrawer.
Identical pulsing `bg-red-500` markup; only the `to ===` guard and `data-testid`
change. The `noGames` condition source is `App.tsx:101-102` (already present in
NavHeader and MobileBottomBar; **must be added** to MobileMoreDrawer at `App.tsx:330`).

### Nav-lock / `isActive` derivation
**Source:** `App.tsx:89-93` (isActive), `App.tsx:128/264/348` (lock exemption).
**Apply to:** all three nav surfaces uniformly. The derived test-id convention
(`nav-${label.toLowerCase()}`, `mobile-nav-${...}`, `drawer-nav-${...}` at
`App.tsx:133/269/353`) auto-produces `nav-library` / `mobile-nav-library` /
`drawer-nav-library` once the label is "Library" — no manual test-id needed for
the nav items themselves.

### Page-level `<Navigate>` default-subtab resolution
**Source:** `Openings.tsx:682-684`, `Endgames.tsx:805-807`.
**Apply to:** `LibraryPage` — but state-dependent (D-06), gated on `noGames`
rather than a static target.

### Prop Threading (D-14) — NET-NEW, no in-repo precedent
**Owner:** `App.tsx` (`AppRoutes`) owns `activeJobIds` / `handleImportStarted` /
`handleJobDismissed` (`App.tsx:505`, `539-541`, `564-571`) and the
`ImportJobWatcher` fan-out (`App.tsx:600-602`). This state stays in App.
**Chain:** `App.tsx` (route element) → `LibraryPage` (declares + forwards the 3
props) → `ImportTab` (declares + forwards) → `ImportPage` (existing
`ImportPageProps`, `Import.tsx:51-55`). `OverviewTab` receives nothing.
**Mechanism (planner's call, per D-14):** simplest is plain prop drilling through
two thin wrappers — `LibraryPage` adds a 3-field props interface identical to
`ImportPageProps`, spreads them onto `<ImportTab {...jobProps} />`, which spreads
onto `<ImportPage {...jobProps} />`. No context provider is warranted for a
2-hop, 3-field forward (CLAUDE.md: "Don't invent context dataclasses … pass the
args directly"). **Constraint:** identical runtime behavior — the full Import
workflow (progress bars, job restore, completion invalidation) must be unchanged.

### Tabs component
**Source:** `@/components/ui/tabs` — `<Tabs variant="brand">` / `<TabsList variant="brand">`
/ `<TabsTrigger>` / `<TabsContent>`, imported identically in
`Endgames.tsx:16` and `Openings.tsx:23`. Reuse verbatim; no new component (UI-SPEC Registry Safety).

---

## No Analog Found

| Concern | Reason | Planner guidance |
|---------|--------|-----------------|
| App → page-component → subtab prop threading | No existing page receives App-level props; `OpeningsPage`/`EndgamesPage`/`GlobalStatsPage` are all zero-prop. `ImportPage` is the only prop-taking component and is route-rendered directly. | Net-new prop drilling (Shared Patterns § Prop Threading). Follow `GamesTab.tsx:9-33` for the *shape* of the subtab props interface, but the App→shell hop has no precedent — keep it plain drilling. |
| MobileMoreDrawer notification dot | The current drawer markup (`App.tsx:347-367`) renders no dot at all. | Net-new: copy dot span from `App.tsx:147-154`, add `noGames` derivation at `App.tsx:330`, gate on `to === '/library' && noGames`, testid `library-notification-dot-drawer`. |

---

## Metadata

**Analog search scope:** `frontend/src/pages/` (Openings, Endgames, GlobalStats,
Import, Home), `frontend/src/pages/openings/*Tab.tsx`, `frontend/src/App.tsx`,
`frontend/src/components/ui/tabs.tsx`.
**Files scanned:** 9 read + 3 grep sweeps for line-number verification.
**Pattern extraction date:** 2026-06-05
</content>
</invoke>
