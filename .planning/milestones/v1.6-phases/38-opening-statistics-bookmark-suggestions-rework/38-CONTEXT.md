# Phase 38: Opening Statistics & Bookmark Suggestions Rework - Context

**Gathered:** 2026-03-29
**Status:** Ready for planning
**Source:** User requirements (conversation)

<domain>
## Phase Boundary

This phase reworks the Opening Statistics subtab when there are no bookmarks, refactors bookmark suggestions to use most-played openings data from Phase 37, and redesigns the bookmark card layout. No backend schema changes expected — leverages existing most-played openings endpoint.

</domain>

<decisions>
## Implementation Decisions

### Section Reordering
- Reorder the Opening Statistics sections to:
  1. Results by Opening
  2. Win Rate Over Time
  3. Most Played Openings as White (renamed from "White: Most Played Openings", with white color circle)
  4. Most Played Openings as Black (renamed from "Black: Most Played Openings", with black color circle)

### Default Chart Data (No Bookmarks)
- If the user has NO position bookmarks, use the top 3 white and top 3 black most-played openings as data for "Results by Opening" and "Win Rate Over Time" charts
- Each opening uses its corresponding "Played as" filter (white openings use played-as-white, black openings use played-as-black) with "Piece filter: Both" and all default "more filters" settings
- Since most-played openings data is already fetched, do NOT create extra API requests — reuse the existing fetched data
- Most Played Openings data must be fetched BEFORE rendering "Results by Opening" and "Win Rate Over Time" charts (since those charts depend on it when no bookmarks exist)
- If the user has at least one position bookmark, use ONLY bookmarks for "Results by Opening" and "Win Rate Over Time" charts

### Bookmark Suggestions Rework
- Fetch top 10 most-played openings for white and black for bookmark suggestions
- Suggest only the top 5 for each color
- If a most-played opening is already bookmarked, skip it and suggest the next one from the list
- If all 10 most-played positions (for a color) are already bookmarked, display a message suggesting the user create custom position bookmarks on the board and experiment with the Piece filter
- Remove ALL obsolete bookmark suggestion code

### Bookmark Card: Chart Enable Toggle
- Add a toggle to each bookmark card to enable/disable including that bookmark in "Results by Opening" and "Win Rate Over Time" charts
- Default: enabled

### Bookmark Card Layout Redesign
- Make the minimap slightly bigger
- Move load and delete buttons to a new row below the Piece filter (gains horizontal space)
- New button row layout: chart-enable toggle on left, load button in middle, delete button on right

### Position Bookmarks Popover
- Update the explanation text in the Position Bookmarks popover
- Add explanation of the Piece filter (not what it does functionally, just that its state can be updated here)
- Add explanation of the chart-enable toggle

### Claude's Discretion
- How to implement the chart-enable toggle state (localStorage, API field, or bookmark model extension)
- Exact sizing of the bigger minimap
- Transition/animation details for toggle
- Loading state handling while most-played openings fetch is in progress

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Opening Statistics Components
- `frontend/src/pages/Openings/Statistics/` — Opening Statistics subtab components
- `frontend/src/pages/Openings/Statistics/MostPlayedOpenings.tsx` — Most Played Openings component (Phase 37)
- `frontend/src/pages/Openings/Statistics/ResultsByOpening.tsx` — Results by Opening chart
- `frontend/src/pages/Openings/Statistics/WinRateOverTime.tsx` — Win Rate Over Time chart

### Bookmark Components
- `frontend/src/pages/Openings/Bookmarks/` — Bookmark-related components
- `frontend/src/components/` — Shared components

### API / Hooks
- `frontend/src/api/` — API client and hooks
- `app/routers/` — Backend routers
- `app/services/` — Backend services
- `app/repositories/` — Backend repositories

### Theme
- `frontend/src/lib/theme.ts` — Theme constants

</canonical_refs>

<specifics>
## Specific Ideas

- The "Played as" filter context for default chart openings: white openings get played-as-white, black openings get played-as-black
- Piece filter for default chart openings: "Both"
- More filters for default chart openings: default settings
- Bookmark suggestion fallback message should mention creating custom bookmarks on the board and experimenting with the Piece filter

</specifics>

<deferred>
## Deferred Ideas

None — requirements cover phase scope

</deferred>

---

*Phase: 38-opening-statistics-bookmark-suggestions-rework*
*Context gathered: 2026-03-29 from user requirements*
