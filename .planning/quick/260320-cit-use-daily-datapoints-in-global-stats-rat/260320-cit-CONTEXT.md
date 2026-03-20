# Quick Task 260320-cit: Use daily datapoints in global stats rating charts - Context

**Gathered:** 2026-03-20
**Status:** Ready for planning

<domain>
## Task Boundary

Change the rating chart from always-monthly grouping to adaptive granularity based on data date range. Frontend-only change in RatingChart.tsx.

</domain>

<decisions>
## Implementation Decisions

### Granularity thresholds
- < 1 year data span → group by day (YYYY-MM-DD), last rating per day per time control
- < 3 years data span → group by week, last rating per week per time control
- >= 3 years data span → group by month (YYYY-MM), current behavior preserved

### Aggregation layer
- Frontend-only change — no backend/API modifications
- Backend already sends per-game data sorted chronologically; frontend just changes grouping key

### X-axis label formatting
- Smart auto-thin: Recharts handles label density automatically
- Daily: "Mar 15" format
- Weekly: "Mar 10" format
- Monthly: "Mar '26" format (unchanged from current)

### Claude's Discretion
- Week key computation method (ISO week or simple 7-day bucketing)
- Exact Recharts tick/interval configuration for auto-thinning

</decisions>

<specifics>
## Specific Ideas

- Keep "last rating per bucket per time control" logic identical, just change the bucket key
- No backend optimization needed at current scale — can be addressed later if payload size becomes an issue

</specifics>
