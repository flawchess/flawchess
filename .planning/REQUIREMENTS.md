# Requirements: FlawChess

**Defined:** 2026-04-09
**Core Value:** Users can determine their success rate for any opening position they specify, filtering by their own pieces only, regardless of how platforms categorize the opening.

## v1.9 Requirements

Requirements for UI/UX Restructuring milestone. Each maps to roadmap phases.

### Openings Desktop Layout

- [ ] **DESK-01**: User sees a collapsible sidebar on the left of the Openings page with filter and bookmark icons visible in collapsed state
- [ ] **DESK-02**: User can open the sidebar directly to Filters or Bookmarks by clicking the respective icon in the collapsed strip
- [ ] **DESK-03**: Only one panel (Filters or Bookmarks) is shown at a time in the sidebar; clicking the other icon switches panels
- [ ] **DESK-04**: Filter changes apply live while the sidebar is open (no deferred apply on desktop)
- [ ] **DESK-05**: Sidebar overlays the chessboard on smaller desktop screens where a 3-column push layout would be too tight

### Openings Mobile Layout

- [ ] **MMOB-01**: Subtab navigation (Moves/Games/Stats) is relocated from its current position (placement TBD — above board or bottom near main nav)

### Stats Subtab Layout

- [ ] **STAB-01**: "Bookmarked Openings: Results" uses a 2-column layout on desktop (matching "Most Played" style)
- [ ] **STAB-02**: "Most Played Openings as White/Black" uses a stacked layout on mobile (matching bookmarked style)

### Endgames & Games Mobile

- [ ] **EGAM-01**: Endgames and Games tab mobile layouts are adjusted consistent with Openings mobile layout changes

### Homepage

- [ ] **HOME-01**: Feature content is visible on desktop without scrolling (via carousel, removing pills, or similar restructuring)

### Global Stats

- [ ] **GSTA-01**: Stats page is relabeled to "Global Stats" in navigation and page header
- [ ] **GSTA-02**: More existing filters are enabled on the Global Stats page

## Future Requirements (v1.10)

Deferred to next milestone. Tracked but not in current roadmap.

### Advanced Analytics

- **ELO-01**: ELO-Adjusted Endgame Skill — opponent-strength-adjusted composite score with gauge + timeline
- **OPN-01**: Opening Risk and Drawishness metrics per position in the move explorer

## Out of Scope

| Feature | Reason |
|---------|--------|
| Backend API changes | This milestone is frontend layout restructuring only |
| New data models or migrations | No new data needed for layout changes |
| Deferred filter apply on desktop | User wants live filter updates on desktop |
| Simultaneous Filters + Bookmarks panels | One panel at a time by design |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| DESK-01 | TBD | Pending |
| DESK-02 | TBD | Pending |
| DESK-03 | TBD | Pending |
| DESK-04 | TBD | Pending |
| DESK-05 | TBD | Pending |
| MMOB-01 | TBD | Pending |
| STAB-01 | TBD | Pending |
| STAB-02 | TBD | Pending |
| EGAM-01 | TBD | Pending |
| HOME-01 | TBD | Pending |
| GSTA-01 | TBD | Pending |
| GSTA-02 | TBD | Pending |

**Coverage:**
- v1.9 requirements: 12 total
- Mapped to phases: 0
- Unmapped: 12 (pending roadmap creation)

---
*Requirements defined: 2026-04-09*
*Last updated: 2026-04-09 after initial definition*
