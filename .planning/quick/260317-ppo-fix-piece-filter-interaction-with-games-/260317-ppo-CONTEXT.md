# Quick Task 260317-ppo: Fix piece filter interaction with games and moves tables - Context

**Gathered:** 2026-03-17
**Status:** Ready for planning

<domain>
## Task Boundary

Fix the Piece filter (Mine/Opponent/Both) interaction across the three sub-tabs (Moves, Games, Statistics) on the Openings page. Two problems: (1) the Piece filter is shown as active on tabs where it has no effect, confusing users; (2) selecting "Mine" on the Games tab returns empty results when it should return more games (less restrictive filter).

</domain>

<decisions>
## Implementation Decisions

### Filter applicability per tab
- **Moves tab**: "Played as" (color) stays enabled. "Piece filter" gets disabled (greyed out) — Moves always uses full_hash.
- **Games tab**: Both "Played as" and "Piece filter" remain enabled — both are applicable.
- **Statistics tab**: Both "Played as" and "Piece filter" get disabled (greyed out) — Statistics shows bookmark data with their own stored filters.

### Disabled filter style
- Greyed out (visually dimmed) with a tooltip on hover explaining "Not applicable for this tab"
- Filters remain visible but non-interactive when disabled

### Scope
- Fix both: UX changes (disable inapplicable filters) AND the empty-results bug when using "Mine" filter on Games tab
- Single task, not split across multiple PRs

### Claude's Discretion
- Exact tooltip wording
- Implementation approach for greying out (CSS opacity, pointer-events, or Tailwind disabled utilities)

</decisions>

<specifics>
## Specific Ideas

- The "Mine" piece filter on Games tab queries white_hash/black_hash but returns empty — likely a hash computation or hash column selection bug to investigate
- Current Moves tab ignores piece filter silently — disabling it makes this explicit to the user

</specifics>
