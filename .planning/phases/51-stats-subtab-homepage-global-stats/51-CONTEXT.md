# Phase 51: Stats Subtab, Homepage & Global Stats - Context

**Gathered:** 2026-04-10
**Status:** Ready for planning

<domain>
## Phase Boundary

Three independent frontend changes in v1.9 UI/UX Restructuring:

1. **Openings Stats subtab** — `Bookmarked Openings: Results` becomes a 2-column layout on larger desktops; `Most Played Openings as White/Black` on mobile is rebuilt to use the same `WDLChartRow` component the bookmarked section already uses (visual consistency).
2. **Public homepage** (`frontend/src/pages/Home.tsx`) — the centered single-column hero becomes a split hero on desktop: left column keeps the existing hero (title, subtitle, CTAs); right column statically previews the Interactive Opening Explorer feature (heading → image → bullets). The Opening Explorer feature section is removed from the alternating scroll-through sections below to avoid duplication. The callout pills row is removed entirely. Mobile hero is unchanged — HOME-01 is a desktop-fold problem only.
3. **Global Stats page** (`frontend/src/pages/GlobalStats.tsx`) — `Stats` is renamed to `Global Stats` across nav, mobile page title, and a new page `<h1>`. Two additional filters (`opponent_type`, `opponent_strength`) become functional on the page, which requires a narrow backend exception adding these two Query params to `/stats/global` and `/stats/rating-history`.

**Out of scope:** Carousel on the homepage (dropped — the split hero is static), backend changes to `/stats/global` or `/stats/rating-history` beyond `opponent_type` + `opponent_strength`, changes to the Openings desktop sidebar (Phase 49), changes to the Openings mobile layout (Phase 50), any changes to the alternating feature sections on the homepage other than dropping the Opening Explorer one, any changes to the mobile homepage layout.

</domain>

<decisions>
## Implementation Decisions

### Homepage — Desktop Hero Split (HOME-01)
- **D-01:** The desktop hero (`lg:` and above) becomes a 2-column split. **Left column:** existing hero content — title, subtitle, CTA buttons (Sign up / Use as Guest). **Right column:** static preview of the Interactive Opening Explorer feature — heading, screenshot, 3 bullets. No carousel. No auto-rotation (moot, since content is static).
- **D-02:** Right column content order: **heading → image → bullets** (top to bottom). The heading "Interactive Opening Explorer" anchors the top, the screenshot is the visual hook in the middle, the three bullets expand on it below.
- **D-03:** The Interactive Opening Explorer feature is **removed from the alternating feature sections below the hero**. The scroll-through now starts with Opening Comparison. Result: 4 alternating feature sections below the hero instead of 5. This prevents duplication.
- **D-04:** The callout pills row (`Free to use`, `Open source`, `Mobile app`, `Opening explorer`, `Progress tracking`, `Endgame stats`, `Cross-platform`) is **removed entirely** from the hero. Their content is already covered by CTAs and FAQ.
- **D-05:** The left column's mascot logo, title, subtitle, padding, and button sizes need to shrink to fit the narrower column while keeping all content above the 1280×720 fold. Exact sizing is Claude's discretion — the goal is "hero left column + Explorer right column both visible without scroll on 1280×720 desktop".

### Homepage — Mobile (HOME-01)
- **D-06:** The mobile hero (`<lg`) is **unchanged**. The existing centered single-column layout stays: mascot, title, subtitle, CTAs, then (after removing the pills per D-04) the alternating feature sections. HOME-01 is a desktop fold problem; mobile doesn't have a fold problem because the feature sections are already directly under the hero. No new mobile markup.
- **D-07:** Because mobile is unchanged, the Opening Explorer preview lives in the desktop-only right column markup (`hidden lg:block` or equivalent). The "no duplication" decision from D-03 applies to both viewports — the Opening Explorer feature section is removed from the alternating sections regardless of viewport, because mobile users now see the Explorer in its dedicated feature section further down the page (which is removed per D-03, so they see it first in the Opening Comparison section? — NO, see note below).

  **Mobile content note:** With D-03 removing the Opening Explorer feature section, mobile users lose their current first feature section entirely. This is acceptable because the mobile hero is directly above the remaining feature sections (no fold gap) and the mascot + tagline already communicates the product. If the planner determines this creates a discovery problem on mobile, they may keep the Opening Explorer feature section visible on mobile only (`lg:hidden`) and hide it on desktop (`hidden lg:*` on the right-column preview). Claude's discretion during implementation.

### Stats Subtab — Bookmarked Openings: Results 2-col (STAB-01)
- **D-08:** The 2-column layout for `Bookmarked Openings: Results` activates at the `lg` breakpoint (≥1024px). Below `lg` (tablets, small laptops), the section stays single-column. Reason: each `WDLChartRow` has a long opening name label + WDL bar + game count bar that needs breathing room, and the Openings page has a desktop sidebar strip on the left eating horizontal space (~60–300px depending on open/closed state).
- **D-09:** The 2-col flow is **top-to-bottom, left column first**: the first half of the rows (sorted by game count — the existing sort order) fills the left column top-to-bottom, the second half fills the right column top-to-bottom. Implementation: either CSS `columns-2` with `break-inside: avoid`, or a grid with explicit col placement calculated from row count. Claude's discretion on the exact technique.
- **D-10:** The `proportional maxTotal` argument currently passed to each `WDLChartRow` (`frontend/src/pages/Openings.tsx:703`) must be recomputed to span ALL rows across both columns, not per-column. The proportional game-count bar must stay comparable across the two columns.

### Stats Subtab — Most Played Openings mobile (STAB-02)
- **D-11:** On mobile (`<md`? or `<lg`? — see D-12), `Most Played Openings as White` and `Most Played Openings as Black` stop using the current `MostPlayedOpeningsTable` 3-col grid (name | games | MiniWDLBar) and instead render each row as a **`WDLChartRow`** — the same component used in `Bookmarked Openings: Results`. Each Most Played opening becomes a labeled WDLChartRow with its opening name as the label, the games count + FolderOpen link in the header (already supported by `WDLChartRow` via `onOpenGames` + `openGamesTestId`), and the stacked WDL bar below. Proportional `maxTotal` spans all rows in each color section.
- **D-12:** Mobile-only replacement — **desktop keeps the existing `MostPlayedOpeningsTable`** (compact 3-col grid). Only the mobile (`md:hidden` or equivalent) path switches to WDLChartRow. Desktop MostPlayedOpeningsTable is denser and already works well at the desktop width. The implementation may be a viewport branch inside the call site (`Openings.tsx` statisticsContent) or a `mobileMode` prop on `MostPlayedOpeningsTable` — Claude's discretion.
- **D-13:** The `INITIAL_VISIBLE_COUNT = 3` / "show N more" toggle behavior from `MostPlayedOpeningsTable` must be preserved on mobile — don't just render all 10 openings. If the component is branched by viewport, the mobile branch reimplements the collapse/expand. If `MostPlayedOpeningsTable` gets a mode prop, the collapse logic lifts to shared state.
- **D-14:** `MinimapPopover` hover minimaps currently wrap the name column in `MostPlayedOpeningsTable`. On mobile `WDLChartRow` there is no hover on touch devices, so the minimap popover becomes essentially dead on mobile. Claude's discretion whether to drop it on mobile or wire it to a tap (existing pattern on the Openings page: `MinimapPopover` already exists and handles tap on touch — confirm in implementation).

### Global Stats Rename (GSTA-01)
- **D-15:** `Stats` is renamed to `Global Stats` in four places: (a) `NAV_ITEMS` label in `frontend/src/App.tsx:52`, (b) `BOTTOM_NAV_ITEMS` label in `frontend/src/App.tsx:59`, (c) `ROUTE_TITLES['/global-stats']` in `frontend/src/App.tsx:66`, (d) a new top-level `<h1>Global Stats</h1>` added to `GlobalStats.tsx` at the top of the `main` content (currently the page has no h1 — section headings like "Chess.com Rating" carry the page).
- **D-16:** Data-testids that reference "stats" in a navigation context are renamed for consistency: `nav-stats` → `nav-global-stats`, `mobile-nav-stats` → `mobile-nav-global-stats`, `drawer-nav-stats` → `drawer-nav-global-stats`. The page-level `data-testid="global-stats-page"` stays (already correct). Any frontend/backend tests referencing the old testids must be updated in the same commit that renames them.
- **D-17:** The URL route `/global-stats` stays unchanged. No redirect needed. No browser tab title change (there's no `document.title` set for this route currently).

### Global Stats Additional Filters (GSTA-02)
- **D-18:** **Narrow backend exception.** `GET /stats/global` and `GET /stats/rating-history` gain two new query parameters: `opponent_type` (string, default `"human"`) and `opponent_strength` (`Literal["any", "stronger", "similar", "weaker"]`, default `"any"`). These mirror the exact parameters `/stats/most-played-openings` already accepts. No other filter params are added in this phase — `time_control` and `rated` are explicitly NOT added because they would add more risk than the phase warrants.
- **D-19:** `app/services/stats_service.py` (`get_global_stats` and `get_rating_history`) accept the two new params and pass them through the shared `apply_game_filters()` helper in `app/repositories/query_utils.py`. The helper already supports `opponent_type` and `opponent_strength` filtering — no new filter logic required, just wiring.
- **D-20:** `frontend/src/api/client.ts` `statsApi.getGlobalStats` and `statsApi.getRatingHistory` signatures gain `opponentType` and `opponentStrength` arguments. `useGlobalStats` and `useRatingHistory` in `frontend/src/hooks/useStats.ts` extract these from the shared `FilterState` and pass them through. The TanStack Query `queryKey` arrays must include the new args so the cache invalidates on filter change.
- **D-21:** `FilterPanel` on `GlobalStats.tsx` currently has `visibleFilters={['platform', 'recency']}` (both the desktop `SidebarLayout` panel and the mobile `Drawer`). Both change to `visibleFilters={['platform', 'recency', 'opponent', 'opponentStrength']}`. The `FilterPanel` already implements `opponent` and `opponentStrength` sections — no new UI needed. Order in the panel follows `FilterPanel`'s existing render order.
- **D-22:** **Scope exception rationale** — this is documented as an explicit narrow exception to the v1.9 "No backend API changes" rule (REQUIREMENTS.md Out of Scope table). The exception is bounded: only two new params, only on two endpoints, no new data models, no migrations, reuses existing `apply_game_filters`. The alternative (adding these filters without backend wiring) would show cosmetic filters that don't filter the data — worse UX than keeping them off.

### Claude's Discretion
- **Homepage left column sizing** — exact mascot logo size, title font size, padding reduction, button sizes in the desktop split hero (goal: both columns visible on 1280×720 without scroll)
- **Homepage right column image framing** — border/shadow/rounded styling on the Explorer screenshot (match existing feature section image styling or tighten for the hero)
- **Homepage column ratio** — `lg:grid-cols-[1fr_1fr]` (50/50) vs `lg:grid-cols-[2fr_3fr]` (left narrower, image larger) vs `lg:grid-cols-[3fr_2fr]` — pick what reads best; feature sections below use `2fr_3fr` / `3fr_2fr` as reference
- **Homepage mobile Opening Explorer fallback** — whether to keep the Opening Explorer feature section visible on mobile-only (`lg:hidden`) to compensate for its removal from the alternating sections on desktop, or drop it entirely on both viewports (see note under D-07)
- **Stats 2-col technique** — CSS `columns-2` with `break-inside: avoid` vs grid with explicit row placement calculated from `rows.length`
- **Stats 2-col empty-column handling** — with an odd row count, how the last row in the left column and the right column balance (one row imbalance is fine; larger imbalance needs a rule)
- **Most Played mobile branching technique** — viewport branch at the `Openings.tsx` call site vs a `mobileMode` prop on `MostPlayedOpeningsTable`
- **Most Played mobile MinimapPopover** — keep, drop, or wire to tap (existing touch pattern may already support this)
- **Global Stats h1 styling** — font size/weight/margin of the new page-level h1 to match the visual language of other pages that DO have h1s (none currently on the public auth page or the Openings page, so this may establish a new pattern)
- **Global Stats h1 placement relative to InfoPopover / filter button** — the h1 goes inside the `main` container but the exact position relative to the sticky mobile filter button may need tuning
- **New filter default values on Global Stats** — the `opponent_type` filter defaults to `'human'` in `DEFAULT_FILTERS` so rating charts start excluding bot games by default. This is a visible behavior change for the Global Stats page (today it doesn't filter opponent_type, meaning bot games are included in global stats). Flag whether this default change matches user expectation — it probably does, but call it out in the plan.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements & Scope
- `.planning/REQUIREMENTS.md` §"Stats Subtab Layout" — STAB-01, STAB-02 definitions
- `.planning/REQUIREMENTS.md` §"Homepage" — HOME-01 definition, including the `carousel, removing pills, or similar restructuring` language
- `.planning/REQUIREMENTS.md` §"Global Stats" — GSTA-01 (rename), GSTA-02 (more filters)
- `.planning/REQUIREMENTS.md` §"Out of Scope" — the "Backend API changes" rule that Phase 51 takes a narrow exception to (documented in D-18/D-22)
- `.planning/ROADMAP.md` §"Phase 51: Stats Subtab, Homepage & Global Stats" — 5 success criteria

### Prior Phase Context (v1.9)
- `.planning/phases/49-openings-desktop-sidebar/49-CONTEXT.md` — Phase 49 introduced `SidebarLayout` used by both Openings and Global Stats; the collapsed sidebar strip is always visible on desktop and affects how wide the 2-col `Bookmarked Openings: Results` section can be
- `.planning/phases/49-openings-desktop-sidebar/49-01-SUMMARY.md` — the `SidebarLayout` component implementation
- `.planning/phases/50-mobile-layout-restructuring/50-CONTEXT.md` — mobile sticky wrapper pattern (`bg-background/80 backdrop-blur-md`); Most Played mobile changes must not collide with the unified control row above the board

### Existing Code — Homepage (HOME-01 target)
- `frontend/src/pages/Home.tsx` — `HomePageContent` (line 97) is the main change target. Hero section at `hero-section` (line 117) uses `py-8 lg:py-24` + `h-28 lg:h-36` mascot + `mt-12` pills — all three push content below the 1280×720 fold. The `FEATURES` array (line 23) is where the Opening Explorer feature is defined and where it must be removed per D-03.
- `frontend/src/components/layout/PublicHeader.tsx` — public header shown above the hero, not modified

### Existing Code — Stats Subtab (STAB-01/02 targets)
- `frontend/src/pages/Openings.tsx` — `statisticsContent` variable (line 621). Contains the Bookmarked Openings: Results block (line 623) and the Most Played Openings sections (lines 722 white, 742 black). These are the primary change sites. Shared `wdlStatsMap` (line 251) feeds both blocks.
- `frontend/src/components/charts/WDLChartRow.tsx` — the row component reused for both STAB-01 (already used) and STAB-02 (new use). Accepts `label`, `maxTotal`, `onOpenGames`, `openGamesTestId`, `testId`. The `label` prop accepts `ReactNode`, so the existing color-chip-inline label pattern carries over.
- `frontend/src/components/stats/MostPlayedOpeningsTable.tsx` — the current Most Played table. Keep unchanged on desktop (D-12) or add a `mobileMode` prop branch (Claude's discretion).
- `frontend/src/components/stats/MinimapPopover.tsx` — hover/tap minimap popover used in current Most Played table. Relevant for D-14 decision on mobile.

### Existing Code — Global Stats (GSTA-01/02 targets)
- `frontend/src/pages/GlobalStats.tsx` — the page component. Lines 165–182 show the desktop `SidebarLayout` FilterPanel with `visibleFilters={['platform', 'recency']}`; line 216 shows the mobile drawer FilterPanel with the same visibleFilters. Both change per D-21.
- `frontend/src/App.tsx:52,59,66` — `NAV_ITEMS`, `BOTTOM_NAV_ITEMS`, `ROUTE_TITLES` — the rename targets from D-15.
- `frontend/src/components/filters/FilterPanel.tsx` — already implements `opponent` and `opponentStrength` filter sections. No new UI code needed for GSTA-02; just turn them on via `visibleFilters`.
- `frontend/src/hooks/useStats.ts` — `useGlobalStats` (line 15) and `useRatingHistory` (line 5). Both need to accept and pass through `opponent_type` and `opponent_strength`. Query keys must include the new args.
- `frontend/src/api/client.ts` around `statsApi.getGlobalStats` (line 118) and `statsApi.getRatingHistory` (line 114). Client signatures extend per D-20.
- `app/routers/stats.py` — `get_rating_history` (line 19) and `get_global_stats` (line 34) get two new `Query` params per D-18.
- `app/services/stats_service.py` — `get_rating_history` and `get_global_stats` service functions pass the new params through `apply_game_filters`.
- `app/repositories/query_utils.py` — `apply_game_filters()` already supports `opponent_type` and `opponent_strength` filtering per CLAUDE.md "Shared Query Filters" section — no changes needed to this file, just new call sites pass the new args.

### Existing Code — Do Not Modify
- `frontend/src/pages/Openings.tsx` desktop layout above the `statisticsContent` variable — Phase 49 locked this
- `frontend/src/pages/Openings.tsx` mobile unified control row — Phase 50 locked this
- `frontend/src/components/filters/FilterPanel.tsx` filter section implementations — only `visibleFilters` at call sites changes
- `app/repositories/query_utils.py` `apply_game_filters()` implementation — just called with new args

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **`WDLChartRow`** (`frontend/src/components/charts/WDLChartRow.tsx`) — exact component reused for STAB-01's 2-col layout and STAB-02's mobile Most Played conversion. Accepts a `label` prop of `ReactNode` (color chip + name), `onOpenGames` + `openGamesTestId` for the games-link interaction, and `maxTotal` for proportional game-count bars.
- **`apply_game_filters()`** (`app/repositories/query_utils.py`) — already implements `opponent_type` and `opponent_strength` filtering used by `/stats/most-played-openings`. GSTA-02 wires existing filter logic through two previously-ignoring endpoints.
- **`SidebarLayout`** (`frontend/src/components/layout/SidebarLayout.tsx`) — already used by `GlobalStats.tsx`. No changes to the layout component itself — only its `panels[0].content.visibleFilters` prop changes.
- **`FilterPanel`** opponent/opponentStrength sections — already rendered when `visibleFilters` includes `'opponent'` and `'opponentStrength'`. Zero new filter UI code required.
- **`DEFAULT_FILTERS`** (`FilterPanel.tsx:27`) — provides the default values for the shared filter state. `opponentType: 'human'`, `opponentStrength: 'any'`.
- **`useFilterStore`** hook — shared filter state across Openings, Endgames, and Global Stats. Already stores `opponentType` and `opponentStrength` — GlobalStats just isn't reading them yet. No new state management.

### Established Patterns
- **Desktop/mobile branching via `md:hidden` / `hidden md:*` / `lg:` breakpoints** — both Openings and GlobalStats use this pattern. STAB-01 uses `lg:` (not `md:`) per D-08; STAB-02 and HOME-01 use `md:` or `lg:` per Claude's discretion.
- **Charcoal texture containers** — `charcoal-texture rounded-md p-4` wraps each stats section. 2-col `Bookmarked Openings: Results` stays inside its current charcoal container; the container itself doesn't split — the content inside it does.
- **Shared `FilterState` type** — `opponentType` and `opponentStrength` are already in `FilterState` (`FilterPanel.tsx:15`). GSTA-02 reads existing state; no type changes.
- **Data-testid kebab-case component-prefix** — new testids follow `{component}-{element}` convention from CLAUDE.md (e.g., `nav-global-stats`, `mobile-nav-global-stats`).
- **`apply_game_filters` is the single source of truth** — per CLAUDE.md, all filter logic lives in `query_utils.py`. GSTA-02 does NOT introduce new filter logic; it wires existing helpers.
- **Shared backend endpoints return unfiltered data by default** — e.g., `/stats/global` currently counts all games including bot games. Adding `opponent_type='human'` as the default on the frontend hook is a visible behavior change — flag in the plan (D-from Claude's discretion).

### Integration Points
- **`useFilterStore` → `useGlobalStats` / `useRatingHistory` → `statsApi.getGlobalStats` / `getRatingHistory` → `/stats/global` / `/stats/rating-history` → `stats_service.get_global_stats` / `get_rating_history` → `apply_game_filters`** — full 6-hop stack needs `opponent_type` + `opponent_strength` wired through consistently per D-18/D-19/D-20/D-21.
- **`NAV_ITEMS` / `BOTTOM_NAV_ITEMS` / `ROUTE_TITLES` / `GlobalStats.tsx` new h1** — four sync points for the rename per D-15.
- **`statisticsContent` JSX in `Openings.tsx`** — single site that contains both the Bookmarked 2-col refactor (STAB-01) and the Most Played mobile branch (STAB-02).
- **`FEATURES` array in `Home.tsx:23`** — remove the `opening-explorer` entry (D-03). Leaves `opening-comparison`, `system-openings`, `endgame-analysis`, `cross-platform` — four alternating sections.
- **`hero-section` in `Home.tsx:117`** — restructure for the desktop split; wrap existing content in a left-column container, add a right-column container with the Opening Explorer preview. Shrink paddings and mascot on `lg`.

</code_context>

<specifics>
## Specific Ideas

- **User pivoted away from a carousel mid-discussion.** Original command arg said "we can have a carousel without auto-rotation, main feature is the interactive explorer". After seeing the questions framed around carousel variants, the user proposed a simpler direction: drop the carousel entirely, static split hero, Opening Explorer on the right (heading → image → bullets), alternating feature sections below stay unchanged (minus the now-duplicated Opening Explorer section). This context file reflects the pivoted direction, not the original carousel direction.
- **The UX expert's original proposal was a "split hero section"** — the carousel was a refinement that got dropped in favor of the simpler static version.
- **REQUIREMENTS.md HOME-01 says "via carousel, removing pills, or similar restructuring"** — the "or similar restructuring" clause covers the static split hero without needing a requirements amendment. Pills removal (D-04) is also explicitly listed as a valid option in the requirement text.
- **GSTA-02 requires a narrow backend exception to the v1.9 "No backend changes" out-of-scope rule.** User chose the minimum-change option: only `opponent_type` + `opponent_strength`, not `time_control` + `rated`. Rationale: opponent filters have the most analytical value (exclude bot games, compare against similar-strength humans). The exception must be explicitly documented in the plan and reflected in REQUIREMENTS.md if the out-of-scope table needs updating.
- **D-21 `opponent_type` default change is a visible behavior shift** on the Global Stats page: today the page includes bot games in rating and global WDL stats; after Phase 51 it defaults to `'human'` (excluding bots) because `DEFAULT_FILTERS.opponentType = 'human'`. This matches what users almost certainly want but should be called out in the PR description.
- **Stats subtab 2-col breakpoint chose `lg` not `md`** because the Openings page has a desktop sidebar strip on the left (from Phase 49) that eats horizontal space. At `md` (768px), the content width is ~400–500px — too tight for two `WDLChartRow`s side by side. `lg` (1024px) gives ~700–800px of usable content width.

</specifics>

<deferred>
## Deferred Ideas

- **Carousel on the homepage** — dropped mid-discussion in favor of the static split hero. If future work wants auto-rotation or multi-feature carousels, revisit then.
- **`time_control` and `rated` filters on Global Stats** — excluded from the GSTA-02 backend exception to keep the exception minimal. If users request these, a v1.10 backend pass can add them symmetrically across `/stats/global`, `/stats/rating-history`, and `/stats/most-played-openings` (the last already supports them).
- **URL route rename `/global-stats` → something else** — not in Phase 51. The route stays as `/global-stats`.
- **Browser tab title (`document.title`) for Global Stats** — not currently set for this route; not added in Phase 51.
- **Per-column proportional `maxTotal` for the 2-col Bookmarked Openings: Results** — explicitly NOT done. `maxTotal` spans all rows across both columns so bar lengths are comparable across the split (D-10).
- **Opening Explorer feature section on mobile-only** — may be kept on mobile via `lg:hidden` as a fallback per D-07 note; if the planner decides not to, this idea is deferred indefinitely.

</deferred>

---

*Phase: 51-stats-subtab-homepage-global-stats*
*Context gathered: 2026-04-10*
