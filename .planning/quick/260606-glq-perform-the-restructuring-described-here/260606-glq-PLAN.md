---
phase: quick-260606-glq
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - frontend/src/pages/library/LibraryPage.tsx
  - frontend/src/pages/library/OverviewTab.tsx
  - frontend/src/pages/library/StatsTab.tsx
  - frontend/src/pages/library/GamesTab.tsx
  - frontend/src/pages/GlobalStats.tsx
  - frontend/src/App.tsx
  - frontend/src/components/library/FlawStatsPanel.tsx
autonomous: true
requirements: []
must_haves:
  truths:
    - "Library tab labeled 'Stats' (not 'Overview'); route is /library/stats"
    - "Stats tab renders rating + WDL charts AND the FlawStatsPanel below them"
    - "Stats tab filter panel exposes the FULL filter set (time control, color, opponent, recency, platform)"
    - "Games subtab is filter panel + game list only — no FlawStatsPanel"
    - "severityFilter drives only useLibraryGames in the Games tab"
    - "FlawStatsPanel on the Stats tab is fed an empty severity argument and the shared global filters"
    - "Returning users with games land on /openings (not the Library)"
  artifacts:
    - path: "frontend/src/pages/library/StatsTab.tsx"
      provides: "Renamed Stats-tab wrapper composing global stats + FlawStatsPanel"
    - path: "frontend/src/pages/GlobalStats.tsx"
      provides: "Full-filter-set Stats content + mounted FlawStatsPanel"
    - path: "frontend/src/pages/library/GamesTab.tsx"
      provides: "Lean filtered browser (no stats panel)"
  key_links:
    - from: "GlobalStats.tsx"
      to: "useLibraryFlawStats"
      via: "shared useFilterStore filters + empty severity arg"
      pattern: "useLibraryFlawStats\\("
    - from: "GamesTab.tsx"
      to: "useLibraryGames"
      via: "severityFilter wired to games query only"
      pattern: "useLibraryGames\\("
---

<objective>
Restructure the Library page per the locked spec at `.planning/notes/library-stats-tab-restructure.md`:
rename the `Overview` subtab to `Stats`, move `FlawStatsPanel` out of the Games subtab into
the Stats tab (alongside the rating + WDL charts), widen the Stats-tab filter set from
`['platform','recency']` to the full set, and reduce the Games subtab to a lean filtered
browser. Also re-point the returning-user landing to `/openings` (decision 7).

Purpose: the Games subtab should be a fast browsable game list, and the flaw stats belong
with the other stats — matching the Openings (`/openings/stats`) and Endgames
(`/endgames/stats`) precedent.

Output: renamed `Stats` subtab + route, full-filter Stats content with FlawStatsPanel
mounted, severity filter scoped to the Games list only, returning-user redirect to Openings.

SCOPE GUARDRAILS (from the spec):
- The spec's decisions 1-7 are LOCKED. Do not re-litigate them. Translate the "Concrete
  change checklist" into the tasks below; do not redesign.
- OUT OF SCOPE: any FlawStatsPanel content/visual improvement, and any unrelated phase-107
  UAT bug. Land the structural move only.
- This intentionally edits files phase 107 just created (GamesTab.tsx, LibraryPage.tsx) on
  the current phase-107 branch — that is in-scope.
- Verification must run against the existing dev DB / build. Do NOT gate on `bin/reset_db.sh`.

IMPLEMENTER'S-CALL DEFAULTS (low stakes, "Open detail" in the spec — confirm at UAT):
- Vertical order on the Stats tab: rating + WDL charts FIRST, FlawStatsPanel BELOW.
- Within-Library default subtab (direct `/library` nav): default to `Stats`.
</objective>

<execution_context>
@$HOME/.claude/gsd-core/workflows/execute-plan.md
</execution_context>

<context>
@.planning/notes/library-stats-tab-restructure.md
@./CLAUDE.md
@frontend/src/pages/library/LibraryPage.tsx
@frontend/src/pages/library/OverviewTab.tsx
@frontend/src/pages/library/GamesTab.tsx
@frontend/src/pages/GlobalStats.tsx
@frontend/src/hooks/useLibrary.ts
@frontend/src/components/library/FlawStatsPanel.tsx

Key facts confirmed by reading the code:
- `useLibraryFlawStats(filters, severity)` requires a severity arg. The Stats-tab call site
  must pass `[]` (empty array) — `buildLibraryParams` already omits severity from wire params
  when the array is empty, so an empty arg means "no severity filter" (decision 5).
- `useLibraryFlawStats` has exactly ONE caller today: `GamesTab.tsx:171`. After this change
  its only caller is the Stats content (GlobalStats / StatsTab). No other consumer depends on
  the severity argument, so the signature can stay as-is and simply receive `[]`.
- `OverviewTab.tsx` is a 5-line wrapper around `<GlobalStatsPage />`. Rename it to `StatsTab`.
- The within-Library redirect that decision 7 revisits lives in `LibraryPage.tsx:32`
  (`noGames ? '/library/import' : '/library/games'`, flipped by commit `51537b63`). There is
  NO separate app-level post-login redirect to the Library to change — re-pointing returning
  users to Openings means changing this Navigate so a returning user with games is NOT routed
  into `/library/games` by default but to `/openings`.
- `App.tsx:601-603` redirect legacy `/overview`, `/rating`, `/global-stats` → `/library/overview`.
  These must point at `/library/stats` after the rename.
- No frontend test references `tab-overview`, `OverviewTab`, or `/library/overview` (grep
  confirmed), so the rename is low-risk for the test suite. Still run the full frontend suite.
</context>

<tasks>

<task type="auto">
  <name>Task 1: Rename Overview → Stats (tabs, route, redirects, default landing)</name>
  <files>
    frontend/src/pages/library/LibraryPage.tsx,
    frontend/src/pages/library/OverviewTab.tsx → frontend/src/pages/library/StatsTab.tsx,
    frontend/src/App.tsx
  </files>
  <action>
    Implements spec decisions 1 and 7 + the LibraryPage.tsx / App.tsx checklist items.

    1. Rename the file `frontend/src/pages/library/OverviewTab.tsx` to
       `frontend/src/pages/library/StatsTab.tsx` and rename the exported component
       `OverviewTab` → `StatsTab` (keep it a thin wrapper around `<GlobalStatsPage />` for now;
       Task 2 adds the FlawStatsPanel). Use `git mv` so history is preserved.

    2. In `LibraryPage.tsx`:
       - Update the import from `OverviewTab` to `StatsTab`.
       - Rename the tab value/label `overview` → `stats` in BOTH the desktop block
         (`TabsTrigger`/`TabsContent` ~lines 59-77) and the mobile block (~lines 110-137).
         Tab label text "Overview" → "Stats". Keep the `LayoutDashboard` icon.
       - Update `data-testid="tab-overview"` → `tab-stats` and
         `data-testid="tab-overview-mobile"` → `tab-stats-mobile`.
       - Update `activeTab` derivation (~lines 36-40) so `/library/stats` resolves to `'stats'`,
         and make `'stats'` the fallback default (replace the trailing `'overview'` default).
       - Update the within-Library redirect (line 32): returning user WITH games →
         `/openings`; no games → `/library/import` (unchanged). Net result:
         `noGames ? '/library/import' : '/openings'`. (Decision 7 — small, reversible.)
         Add a brief inline comment noting this revisits commit 51537b63 and is intentionally
         reversible.

    3. In `App.tsx`, update the three legacy redirect routes (~lines 601-603) from
       `/library/overview` → `/library/stats` for `/overview`, `/rating`, `/global-stats`.

    Do NOT touch the Games subtab or GlobalStats content in this task.
  </action>
  <verify>
    <automated>cd frontend && grep -rn "library/overview\|tab-overview\|OverviewTab\|value=\"overview\"" src --include="*.tsx" --include="*.ts" | grep -v '^#' | wc -l   # expect 0</automated>
    <automated>cd frontend && npx tsc --noEmit && npm run lint</automated>
  </verify>
  <done>
    - `StatsTab.tsx` exists (renamed via git mv); no file/symbol named `OverviewTab` remains.
    - Both desktop and mobile tabs read "Stats" with `tab-stats` / `tab-stats-mobile` testids
      and value `stats`; `/library/stats` is the active + default tab.
    - Legacy `/overview`, `/rating`, `/global-stats` redirect to `/library/stats`.
    - Returning user with games lands on `/openings`; gameless user still lands on
      `/library/import`.
    - tsc + lint clean; zero remaining `overview` references in the grep above.
  </done>
</task>

<task type="auto">
  <name>Task 2: Stats tab — full filter set + mount FlawStatsPanel below charts</name>
  <files>
    frontend/src/pages/GlobalStats.tsx,
    frontend/src/pages/library/StatsTab.tsx
  </files>
  <action>
    Implements spec decisions 2, 3, 4 + the GlobalStats.tsx checklist items.

    1. In `GlobalStats.tsx`, change BOTH `FilterPanel` usages from
       `visibleFilters={['platform', 'recency']}` to the full set. Pass the full set
       explicitly — `visibleFilters={['timeControl', 'color', 'opponent', 'recency', 'platform']}`
       — matching `FilterField` / `ALL_FILTERS` in `FilterPanel.tsx`. Apply to the desktop
       usage (~line 121) AND the mobile drawer usage (~line 175) per CLAUDE.md mobile parity.
       (If `ALL_FILTERS` is exported, omitting the prop to use the default is also acceptable;
       prefer whichever reads cleaner, but the result MUST expose all five fields.)
       Drop the now-stale comments at ~line 17 and ~lines 42-44 that claim "GlobalStats only
       uses recency + platforms" / "GlobalStats's own UI only exposes platform + recency".
       Decision 4 ("accept the collapse") means no special handling for single-TC/color
       filtering — the existing breakdown charts collapsing to one slice is the desired behavior.

    2. Mount `FlawStatsPanel` on the Stats tab BELOW the rating + WDL charts (implementer's-call
       default). Wire it to the shared global `filters` from `useFilterStore` (already present
       in GlobalStats as `filters`) and an EMPTY severity argument:
       `useLibraryFlawStats(filters, [])` (decision 5 — severity must NOT reach the stats).
       Place the panel inside the `content` block after `<GlobalStatsCharts ... />`, rendering
       it in both the desktop and mobile column (the shared `content` variable already renders
       in both, so a single placement covers both layouts — verify it does). Pass the hook's
       `data` / `isLoading` / `isError` to `FlawStatsPanel`'s `stats` / `isLoading` / `isError`
       props exactly as GamesTab did. Add the `useLibraryFlawStats` import.

       NOTE on file choice: mount the panel + hook call directly in `GlobalStats.tsx` (where
       `filters` and the existing `content` JSX live) rather than in the `StatsTab.tsx` wrapper,
       to avoid prop-threading the filter store. `StatsTab.tsx` stays a thin wrapper.

    3. OUT OF SCOPE reminder: do not change FlawStatsPanel's internal content or styling.
  </action>
  <verify>
    <automated>cd frontend && grep -n "useLibraryFlawStats(filters, \[\])" src/pages/GlobalStats.tsx   # expect 1 match, empty severity</automated>
    <automated>cd frontend && grep -c "visibleFilters={\['platform', 'recency'\]}" src/pages/GlobalStats.tsx   # expect 0</automated>
    <automated>cd frontend && npx tsc --noEmit && npm run lint</automated>
  </verify>
  <done>
    - Both Stats-tab FilterPanel usages (desktop + mobile) expose the full filter set; no
      `['platform', 'recency']` restriction and no stale "recency + platforms only" comments
      remain.
    - `FlawStatsPanel` renders on the Stats tab below the rating + WDL charts, fed
      `useLibraryFlawStats(filters, [])` (empty severity) and the shared global filters.
    - tsc + lint clean.
  </done>
</task>

<task type="auto">
  <name>Task 3: Strip FlawStatsPanel from Games tab + verify build/tests</name>
  <files>
    frontend/src/pages/library/GamesTab.tsx,
    frontend/src/components/library/FlawStatsPanel.tsx
  </files>
  <action>
    Implements spec decisions 5, 6 + the GamesTab.tsx / FlawStatsPanel checklist items.

    1. In `GamesTab.tsx`:
       - Remove the `<FlawStatsPanel .../>` render block (~lines 214-219) from `mainContent`.
       - Remove the `useLibraryFlawStats` call (~lines 167-171) and the `statsData` /
         `statsLoading` / `statsError` destructured vars.
       - Remove the `FlawStatsPanel` import and the `useLibraryFlawStats` named import (keep
         `useLibraryGames`).
       - KEEP `severityFilter` local state (~line 57) and its handlers; it stays wired to
         `useLibraryGames` ONLY (~line 165) and to the `LibraryFilterPanel`'s
         `severityFilter`/`onSeverityChange` props (decision 5). Do NOT move severity into
         FilterState.
       - Update the component docstring (~lines 25-45) to drop the "Composes FlawStatsPanel"
         and dual-query language — the tab is now filter panel + game list only.
       - The `isModified` dot logic already incorporates `severityFilter` — leave it; severity
         still legitimately modifies the Games list.

    2. In `FlawStatsPanel.tsx`, update the stale comment at ~line 117 that says
       "Data-fetching (useLibraryFlawStats) lives in GamesTab (Plan 07)" to point at the Stats
       tab / GlobalStats instead. (Comment-only; no behavior change.)

    3. Full local gate (CLAUDE.md Pre-PR checklist, frontend portion — this is a
       frontend-only change so the backend gate is not required, but run it if any shared file
       was touched, which it was not):
       - `cd frontend && npm run lint && npm run knip && npx tsc --noEmit && npm test -- --run`
       knip matters here: removing the GamesTab FlawStatsPanel import must not leave a dead
       export, and `useLibraryFlawStats` must still be imported (now by GlobalStats).
  </action>
  <verify>
    <automated>cd frontend && grep -n "FlawStatsPanel\|useLibraryFlawStats" src/pages/library/GamesTab.tsx | grep -v '^#' | wc -l   # expect 0</automated>
    <automated>cd frontend && npm run lint && npm run knip && npx tsc --noEmit</automated>
    <automated>cd frontend && npm test -- --run</automated>
  </verify>
  <done>
    - GamesTab no longer imports, calls, or renders FlawStatsPanel / useLibraryFlawStats; it is
      filter panel + LibraryGameCardList only.
    - severityFilter remains wired to useLibraryGames only and to the LibraryFilterPanel.
    - knip reports no dead exports / unused deps; `useLibraryFlawStats` still has a live caller
      (GlobalStats).
    - Frontend lint, knip, tsc, and full test suite all pass.
  </done>
</task>

</tasks>

<verification>
- Manual (UAT, against existing dev DB — `bin/run_local.sh`): open `/library`, confirm it
  redirects appropriately (gameless → Import; with games → Openings). Navigate to
  `/library/stats`: tab reads "Stats", shows rating + WDL charts with the full filter panel
  (TC / color / opponent / recency / platform), and FlawStatsPanel below the charts. Apply a
  single time control and confirm the WDL breakdown collapses to that slice AND the
  FlawStatsPanel updates (decision 4 "accept the collapse"). Navigate to `/library/games`:
  filter panel (incl. severity blunder/mistake toggle) + game list only, no stats panel; the
  severity toggle filters the list but does not exist on the Stats tab.
- Automated: each task's `<automated>` checks above; full frontend suite green in Task 3.
</verification>

<success_criteria>
- Library `Overview` subtab renamed to `Stats` end to end (label, value, route, testids,
  legacy redirects, default tab).
- FlawStatsPanel removed from the Games subtab and mounted on the Stats tab below the
  rating + WDL charts, fed shared global filters and an empty severity arg.
- Stats tab exposes the full filter set on both desktop and mobile.
- Games subtab is a lean filtered browser; severity scoped to the game list only.
- Returning users with games land on `/openings`.
- No scope creep: no FlawStatsPanel content/visual changes, no unrelated phase-107 UAT fixes.
- Frontend lint + knip + tsc + tests all pass.
</success_criteria>

<output>
Create `.planning/quick/260606-glq-perform-the-restructuring-described-here/260606-glq-SUMMARY.md` when done.
</output>
