---
phase: quick
plan: 260321-ftk
type: execute
wave: 1
depends_on: []
files_modified:
  - frontend/src/pages/Openings.tsx
  - frontend/src/App.tsx
  - frontend/src/pages/GlobalStats.tsx
autonomous: true
requirements: []
must_haves:
  truths:
    - "Openings sub-tab formerly named 'Statistics' now reads 'Compare'"
    - "Top-level nav tab formerly named 'Global Stats' now reads 'Statistics'"
    - "Desktop nav tabs show icons matching the mobile bottom nav icons"
  artifacts:
    - path: "frontend/src/pages/Openings.tsx"
      provides: "Renamed Statistics -> Compare tab labels"
    - path: "frontend/src/App.tsx"
      provides: "Renamed Global Stats -> Statistics in nav + route titles, icons on desktop nav"
    - path: "frontend/src/pages/GlobalStats.tsx"
      provides: "Renamed page heading to Statistics"
  key_links: []
---

<objective>
Rename the "Statistics" sub-tab in Openings to "Compare", rename the "Global Stats" top-level nav tab to "Statistics", and add icons to the desktop nav tabs matching the mobile bottom nav.

Purpose: Clearer naming -- the Openings sub-tab compares bookmarked positions while the top-level page shows overall statistics. Desktop nav gets visual parity with mobile bottom nav.
Output: Updated labels and desktop nav icons.
</objective>

<execution_context>
@/home/aimfeld/.claude/get-shit-done/workflows/execute-plan.md
@/home/aimfeld/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@frontend/src/App.tsx
@frontend/src/pages/Openings.tsx
@frontend/src/pages/GlobalStats.tsx
</context>

<tasks>

<task type="auto">
  <name>Task 1: Rename tabs and add desktop nav icons</name>
  <files>frontend/src/pages/Openings.tsx, frontend/src/App.tsx, frontend/src/pages/GlobalStats.tsx</files>
  <action>
**Openings.tsx -- rename Statistics sub-tab to Compare:**
- Line 147 comment: change "Statistics tab data" to "Compare tab data"
- Line 350 and 671: update help text references from "Statistics tab charts" to "Compare tab charts"
- Line 506-514 (desktop tabs): change the TabsTrigger with value="statistics" label from "Statistics" to "Compare". Update data-testid from "tab-statistics" to "tab-compare".
- Line 711 comment: change "Moves / Games / Statistics" to "Moves / Games / Compare"
- Line 716 (mobile tabs): change label from "Statistics" to "Compare". Update data-testid from "tab-statistics-mobile" to "tab-compare-mobile".
- Also update the TabsContent value attributes and the activeTab routing value from "statistics" to "compare" -- search for all occurrences of the string "statistics" as a tab value in the file and replace with "compare".
- Add lucide-react icon imports: `BarChartHorizontal` (for Compare tab), `ListTree` (for Moves tab), `Gamepad2` (for Games tab).
- On both desktop and mobile TabsTriggers, add an icon before the label text using `className="mr-1.5 h-4 w-4"` on the icon. Use: ListTree for Moves, Gamepad2 for Games, BarChartHorizontal for Compare.

**App.tsx -- rename Global Stats to Statistics and add desktop nav icons:**
- NAV_ITEMS (line 40-44): change label from "Global Stats" to "Statistics". Add Icon property to each item matching BOTTOM_NAV_ITEMS icons: DownloadIcon for Import, LayoutGridIcon for Openings, BarChart3Icon for Statistics.
- ROUTE_TITLES (line 52-56): change "Global Stats" to "Statistics".
- NavHeader component (line 78-91): update the desktop nav to render the Icon from NAV_ITEMS alongside the label. Add `<Icon className="mr-1.5 h-4 w-4" />` before the label text inside the Link. Update the NAV_ITEMS type to include Icon (match BOTTOM_NAV_ITEMS structure).
- The route path `/global-stats` stays unchanged (URL stability). Only labels change.
- Update data-testid generation: the label "Statistics" will produce `nav-statistics` which is fine.

**GlobalStats.tsx -- rename page heading:**
- Line 27: change h1 text from "Global Stats" to "Statistics".
  </action>
  <verify>
    <automated>cd /home/aimfeld/Projects/Python/chessalytics/frontend && npx tsc --noEmit 2>&1 | head -30 && npm run build 2>&1 | tail -5</automated>
  </verify>
  <done>
- Openings sub-tabs read "Moves", "Games", "Compare" (both desktop and mobile) with icons
- Top-level nav reads "Import", "Openings", "Statistics" (both desktop header and mobile bottom nav) with icons on both
- GlobalStats page heading reads "Statistics"
- All data-testid attributes updated to match new names
- TypeScript compiles, build succeeds
  </done>
</task>

</tasks>

<verification>
- `npm run build` succeeds
- Visual: desktop nav shows icons + labels for Import, Openings, Statistics
- Visual: Openings page tabs show icons + labels for Moves, Games, Compare
- Mobile bottom nav unchanged (already has icons)
- URL `/global-stats` still works (path not changed)
</verification>

<success_criteria>
All tab/nav labels renamed, desktop nav has icons matching mobile bottom nav, Openings sub-tabs have icons, build passes.
</success_criteria>

<output>
After completion, create `.planning/quick/260321-ftk-rename-statistics-sub-tab-to-compare-ren/260321-ftk-SUMMARY.md`
</output>
