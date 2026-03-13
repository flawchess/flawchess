# Phase 6: Optimize UI for Claude Chrome Extension Testing - Context

**Gathered:** 2026-03-13
**Status:** Ready for planning
**Source:** User-provided requirements (inline)

<domain>
## Phase Boundary

Audit the frontend and optimize the DOM for AI browser automation via the Claude Chrome extension. Ensure all interactive elements are accessible, semantically correct, and have stable selectors for automated testing.

</domain>

<decisions>
## Implementation Decisions

### Semantic HTML
- All interactive elements must use semantic HTML (`<button>`, `<a>`, `<nav>`) rather than generic `<div>` tags
- Review all primary UI components and forms for semantic correctness

### Data Test IDs
- Inject descriptive `data-testid` attributes into all clickable elements, inputs, and major layout containers
- The Claude Chrome agent needs stable selectors to target elements

### ARIA Labels and Roles
- All icon-only buttons and dynamic states must have accurate `aria-label`s and ARIA roles
- The agent relies on the accessibility tree for element identification

### Chess Board Interaction
- Moves on the board must be playable by clicking source and target squares (not just drag and drop)
- The board and each square must have `data-testid` attributes containing their coordinates

### CLAUDE.md Browser Automation Rules
- Add a "Browser Automation Rules" section to CLAUDE.md
- Strictly instruct that all future frontend code MUST include `data-testid` attributes
- Must adhere to WCAG semantic HTML
- Must include ARIA labels to maintain testing compatibility

### Claude's Discretion
- Specific `data-testid` naming conventions (e.g., kebab-case, component-prefixed)
- Implementation order within each task
- How to implement click-to-move on react-chessboard (library API specifics)

</decisions>

<specifics>
## Specific Ideas

- Use `data-testid` format that includes element purpose (e.g., `data-testid="btn-import-games"`, `data-testid="nav-stats"`)
- Board squares should include coordinates (e.g., `data-testid="square-e4"`)
- The board itself should have `data-testid="chessboard"`

</specifics>

<deferred>
## Deferred Ideas

None — user requirements cover phase scope

</deferred>

---

*Phase: 06-optimize-ui-for-claude-chrome-extension-testing*
*Context gathered: 2026-03-13 via user-provided requirements*
