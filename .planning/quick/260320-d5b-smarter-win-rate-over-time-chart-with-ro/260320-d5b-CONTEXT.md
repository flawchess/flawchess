# Quick Task 260320-d5b: Smarter win rate over time chart with rolling windows - Context

**Gathered:** 2026-03-20
**Status:** Ready for planning

<domain>
## Task Boundary

Replace monthly-bucketed win rate chart with rolling last-N-games window. Affects backend service/repository (return per-game data chronologically), backend schema (new response shape), and frontend chart component (rolling computation or pre-computed display).

</domain>

<decisions>
## Implementation Decisions

### Smoothing method
- Rolling last-N-games window (game-count-based, not time-based)
- Each datapoint shows win rate over the trailing N games through that position
- X-axis remains time-based (game date), Y-axis is win rate percentage

### Window size
- N = 20 games trailing window
- Extract as named constant (e.g., ROLLING_WINDOW_SIZE = 20)

### Sparse data handling
- Show partial windows from game 1 onwards
- Tooltip should indicate window fullness (e.g., "5/20 games" vs "20/20 games")
- No minimum threshold to show the line — start immediately

### Claude's Discretion
- Whether to compute rolling window in backend service vs frontend
- Exact datapoint density (one per game vs thinned for performance)
- X-axis tick formatting for game-date based axis

</decisions>

<specifics>
## Specific Ideas

- Backend repository needs to return per-game results chronologically (not DATE_TRUNC monthly)
- Service computes rolling window and returns pre-aggregated points
- Frontend WinRateChart.tsx consumes new response shape
- TimeSeriesPoint schema changes: month field → date field, add window_size field
- Keep existing filters (time_control, platform, rated, opponent_type, recency) working

</specifics>
