# Phase 7: Add More Game Statistics and Charts - Context

**Gathered:** 2026-03-14
**Status:** Ready for planning

<domain>
## Phase Boundary

Extend the application with three new statistics pages (Openings, Rating, Global Stats) and fix chess.com ECO import. The existing Stats page is renamed to "Openings" and two new pages are added. All analyses must work for games imported from both chess.com and lichess — no platform-exclusive stats.

</domain>

<decisions>
## Implementation Decisions

### Navigation restructuring
- Current nav: Analysis | Bookmarks | Stats → becomes: **Analysis | Bookmarks | Openings | Rating | Global Stats**
- **Openings** page = current Stats page content (bookmark W/D/L bars, win rate over time chart, all existing filters)
- **Rating** page = new rating over time charts, recency filter only
- **Global Stats** page = new results by color + results by time control, recency filter only
- Each page is a separate route, not subtabs — different pages need different filters

### Rating over time charts
- **Two separate charts**: one for chess.com ratings, one for lichess ratings (scales are incomparable)
- Each chart has **multiple lines per time control** (bullet/blitz/rapid/classical) — togglable
- Data points are per-game ratings (user_rating already stored in Game model)
- Default time window: **all time**, narrowable via recency filter
- Use Recharts LineChart (consistent with existing win rate chart)

### Results by time control (Global Stats page)
- W/D/L breakdown per time control bucket (bullet/blitz/rapid/classical)
- Shows where user performs best across all their games
- Recency filter available

### Results by color (Global Stats page)
- W/D/L split showing white vs black performance
- Global across all games
- Recency filter available

### Opening categorization
- Use **ECO-based grouping** for consistent cross-platform opening identification
- **Fix chess.com ECO import** — currently broken, ECO codes not correctly populated
- Use a static ECO-to-opening-name mapping (e.g., from lichess chess-openings database) applied at import time for consistent naming
- Full ECO-based opening analytics deferred to a later phase — for now, bookmarked positions serve as the opening analysis mechanism

### Global Stats page filters
- **Recency filter only** (week/month/3months/6months/year/all time)
- No other filters for now — keeps the page simple
- More filters can be added in future phases

### Research needed: additional API data
- Researcher should investigate what additional game data is available from chess.com and lichess APIs beyond what's currently imported
- Focus on data available on **both platforms** or that can be meaningfully integrated
- Any new data fields should be captured at import time (new columns on Game model + migration)

### Claude's Discretion
- Exact chart styling and color schemes for rating lines per time control
- Layout of charts on Rating and Global Stats pages
- Whether rating chart uses per-game data points or monthly averages
- Backend API endpoint design for new stats queries
- How to display the results by time control (horizontal bars, vertical bars, or other chart type)
- How to display results by color (bars, pie chart, or other)

</decisions>

<specifics>
## Specific Ideas

- chess.com and lichess ELO ratings are on very different scales and must never be mixed in the same chart
- The Openings page is simply a rename of the current Stats page — no content changes
- Global Stats page is designed to be extensible — more stats will be added in future phases that require no filters
- Rating page is also extensible — more rating-related analyses can be added later

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `WinRateChart` (`components/bookmarks/WinRateChart.tsx`): Recharts LineChart pattern — reuse for rating over time
- `WDLBarChart` (`components/bookmarks/WDLBarChart.tsx`): Recharts horizontal bar pattern — reuse for results by TC and color
- `WDLBar` (`components/results/WDLBar.tsx`): Stacked W/D/L bar — potential reuse for compact stats
- Existing Stats page filters (time control, platform, rated, opponent, recency) — Openings page keeps these as-is
- TanStack Query hooks pattern (`useBookmarks`, `useTimeSeries`) — follow for new data fetching

### Established Patterns
- Recharts for all charts (Phase 5 decision)
- shadcn/ui dark theme — all new UI must match
- Backend routers/services/repositories layering
- `user_rating` and `opponent_rating` already stored per game — no new import data needed for rating charts
- `time_control_bucket` already stored — no new import data for results by TC
- `user_color` already stored — no new import data for results by color

### Integration Points
- Nav header: add Openings, Rating, Global Stats routes (modify `ProtectedLayout` or nav component)
- `App.tsx`: add new routes for /openings, /rating, /global-stats
- Current `/stats` route renamed to `/openings`
- Backend: new endpoints for rating history and global stats queries
- `normalization.py`: fix `_extract_chesscom_eco()` for reliable ECO codes
- Migration needed if adding new columns for additional API data

</code_context>

<deferred>
## Deferred Ideas

- Full ECO-based opening analytics (grouping by opening family, expandable to individual ECO codes) — future phase
- Game activity calendar (GitHub-style heatmap) — future phase
- Game length distribution histogram — future phase
- Additional data from chess.com/lichess APIs — researcher will investigate what's available, but implementation of new data fields deferred unless trivially integrated

</deferred>

---

*Phase: 07-add-more-game-statistics-and-charts-by-replicating-the-most-popular-analyses-from-chess-com-and-lichess-insights*
*Context gathered: 2026-03-14*
