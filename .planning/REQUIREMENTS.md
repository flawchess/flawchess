# Requirements: FlawChess

**Defined:** 2026-03-28
**Core Value:** Users can determine their success rate for any opening position they specify, filtering by their own pieces only, regardless of how platforms categorize the opening.

## v1.6 Requirements

Requirements for v1.6 — UI Polish & Improvements.

### Theme

- [ ] **THEME-01**: User sees all visual constants (container colors, spacing, chart styles) centralized in theme.ts and CSS variables
- [ ] **THEME-02**: User sees content containers with charcoal background and subtle SVG feTurbulence noise texture, visually distinct from page background
- [ ] **THEME-03**: User sees filter buttons in sidebar spaced horizontally across full available width
- [ ] **THEME-04**: User sees consistent WDL chart styling (unified corners and rendering) across all chart types (custom and Recharts-based)
- [ ] **THEME-05**: User sees clear visual highlighting on the active subtab

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
| THEME-01 | Phase 34 | Pending |
| THEME-02 | Phase 34 | Pending |
| THEME-03 | Phase 34 | Pending |
| THEME-04 | Phase 34 | Pending |
| THEME-05 | Phase 34 | Pending |

**Coverage:**
- v1.6 requirements: 5 total
- Mapped to phases: 5
- Unmapped: 0 ✓

---
*Requirements defined: 2026-03-28*
*Last updated: 2026-03-28 after roadmap creation*
