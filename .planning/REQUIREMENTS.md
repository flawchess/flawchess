# Requirements: FlawChess

**Defined:** 2026-03-28
**Core Value:** Users can determine their success rate for any opening position they specify, filtering by their own pieces only, regardless of how platforms categorize the opening.

## v1.6 Requirements

Requirements for v1.6 — UI Polish & Improvements.

### Theme

- [x] **THEME-01**: User sees all visual constants (container colors, spacing, chart styles) centralized in theme.ts and CSS variables
- [x] **THEME-02**: User sees content containers with charcoal background and subtle SVG feTurbulence noise texture, visually distinct from page background
- [x] **THEME-03**: User sees filter buttons in sidebar spaced horizontally across full available width
- [x] **THEME-04**: User sees consistent WDL chart styling (unified corners and rendering) across all chart types (custom and Recharts-based)
- [x] **THEME-05**: User sees clear visual highlighting on the active subtab

### WDL Chart Refactoring

- [ ] **WDL-01**: A shared WDL chart component exists with configurable title, games link, and optional game count bar
- [ ] **WDL-02**: All WDL charts across the app (Results by Time Control, Results by Color, Results by Opening, endgame type charts) use the shared component — except the moves list in the Moves tab
- [ ] **WDL-03**: No unused WDL-related constants, CSS classes, or Recharts bar chart code remains
- [ ] **WDL-04**: Visual appearance of all WDL charts matches the current endgame type WDL charts (glass overlay, inline legend, game count bars)

## Future Requirements

### Pawn Structure Analysis

- **PAWN-01**: System computes pawn structure hash for grouping similar structures (e.g., Carlsbad, isolated d-pawn)

### Tactical Features

- **TACT-01**: System detects per-position tactical flags (passed pawn, opposite-colored bishops, open file)

### Material Config Filter

- **MATFLT-01**: User can filter endgame stats by specific material signature (e.g., KRP vs KR)

## Out of Scope

| Feature | Reason |
|---------|--------|
| Dark/light mode toggle | Not requested for v1.6; current dark theme is the only mode |
| Fine borders on containers | Explicitly excluded — charcoal background with texture only |
| Image-based background textures | Use lightweight SVG feTurbulence instead of asset files |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| THEME-01 | Phase 34 | Complete |
| THEME-02 | Phase 34 | Complete |
| THEME-03 | Phase 34 | Complete |
| THEME-04 | Phase 34 | Complete |
| THEME-05 | Phase 34 | Complete |
| WDL-01 | Phase 35 | Not started |
| WDL-02 | Phase 35 | Not started |
| WDL-03 | Phase 35 | Not started |
| WDL-04 | Phase 35 | Not started |

**Coverage:**
- v1.6 requirements: 9 total
- Mapped to phases: 9
- Unmapped: 0 ✓

---
*Requirements defined: 2026-03-28*
*Last updated: 2026-03-28 after Phase 35 planning*
