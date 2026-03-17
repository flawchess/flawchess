# Quick Task 260317-qyx: Style action buttons with distinct color - Context

**Gathered:** 2026-03-17
**Status:** Ready for planning

<domain>
## Task Boundary

Restyle the action buttons (Bookmark, Suggest bookmarks) to distinguish them from filter controls, reorganize their placement, and add visual separators between sidebar sections.

</domain>

<decisions>
## Implementation Decisions

### Button color
- Use dark blue `#0a3d6b` background with white text for action buttons
- Matches the move arrow hover color — creates visual connection between board and actions

### Button layout
- Move BOTH buttons inside the "Position bookmarks" collapsible section
- "Bookmark" button on the top LEFT, "Suggest bookmarks" on the top RIGHT — side by side at the top of the collapsible
- Rename "Suggest bookmarks" to "Suggest" to fit the side-by-side layout

### Visual separators
- Add subtle horizontal dividers between sidebar sections (board controls, filters, bookmarks, more filters)

### Claude's Discretion
- Exact divider styling (border color, spacing)
- Whether to use inline style or a custom button variant for the dark blue color

</decisions>

<specifics>
## Specific Ideas

- The two buttons should be in a flex row at the top of the Position bookmarks collapsible
- Both buttons should be visually equal in weight (same size, same color)
- Dividers should be subtle — not heavy lines

</specifics>
