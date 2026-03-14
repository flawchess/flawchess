# Quick Task 9: Some fixes for phase 7 - Context

**Gathered:** 2026-03-14
**Status:** Ready for planning

<domain>
## Task Boundary

Fix two issues with phase 7 (Rating and Global Stats pages):
1. Global Stats page shows "No data available" due to a backend KeyError bug
2. Rating charts need adaptive y-axis scaling with round boundaries

</domain>

<decisions>
## Implementation Decisions

### Global Stats 500 error
- Root cause identified: `_aggregate_wdl()` in `stats_service.py` line 84 does `outcome + "s"` which produces `"losss"` (triple s) for losses, but the dict key is `"losses"`. This causes a `KeyError: 'losss'` crash.
- Fix: use a proper mapping dict instead of string concatenation.

### Y-axis scaling
- User wants round boundaries: Y-axis snaps to nearest 100 (e.g., 800-1200), giving clean tick marks while adapting to data range.
- Applies to both Chess.com and Lichess rating charts in `RatingChart.tsx`.

### Claude's Discretion
- Implementation approach for the outcome-to-key mapping fix

</decisions>

<specifics>
## Specific Ideas

- The `_aggregate_wdl` function should map outcomes to dict keys properly (e.g., `{"win": "wins", "draw": "draws", "loss": "losses"}`)
- YAxis domain should compute min/max from visible data, floor/ceil to nearest 100, with some padding

</specifics>
