# Requirements: FlawChess

**Defined:** 2026-03-31
**Core Value:** Users can determine their success rate for any opening position they specify, filtering by their own pieces only, regardless of how platforms categorize the opening.

## v1.7 Requirements

Requirements for the consolidation, tooling & refactoring milestone. Each maps to roadmap phases.

### Tooling & Type Safety

- [x] **TOOL-01**: Backend static type checking with astral `ty` integrated into CI/CD pipeline
- [x] **TOOL-02**: Backend type safety review — replace untyped dicts with TypedDicts/Pydantic models, add missing type hints
- [x] **TOOL-03**: Evaluate and optionally integrate knip.dev (or similar) for frontend dead export detection
- [ ] **TOOL-04**: Add test coverage analysis and reporting (maybe)

### Code Quality

- [ ] **QUAL-01**: Review and improve naming across codebase (API endpoints, routes, variables)
- [ ] **QUAL-02**: Identify and eliminate code duplication (DRY principle)
- [ ] **QUAL-03**: Identify and remove dead code across backend and frontend

### Backend Optimization

- [ ] **BOPT-01**: Identify and refactor inefficient DB queries (replace row-level processing with aggregations)
- [ ] **BOPT-02**: Optimize game_positions column types (BIGINT/DOUBLE → SmallInteger/REAL)
- [ ] **BOPT-03**: Ensure consistent Pydantic response models across all API endpoints

### Frontend Cleanup

- [ ] **FCLN-01**: Refactor button brand colors from theme.ts constants to CSS variables

## Future Requirements

- **Bitboard storage for partial-position queries** — 12 BIGINT bitboard columns on game_positions (v2+)
- **Human-like engine analysis** — engine eval filtered by human move plausibility at target Elo (v2+)
- **Material configuration filter for endgames** — deferred to future milestone

## Out of Scope

| Feature | Reason |
|---------|--------|
| New user-facing features | This milestone is consolidation only — no new functionality |
| Database schema changes beyond column type optimization | Minimize migration risk during refactoring |
| Frontend framework/library upgrades | Dependency updates are not in scope for this milestone |
| Duplicate mobile Openings layout refactor | Potentially complex; defer to future milestone |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| TOOL-01 | Phase 40 | Complete |
| TOOL-02 | Phase 40 | Complete |
| TOOL-03 | Phase 41 | Complete |
| TOOL-04 | Phase 43 | Pending |
| QUAL-01 | Phase 41 | Pending |
| QUAL-02 | Phase 41 | Pending |
| QUAL-03 | Phase 41 | Pending |
| BOPT-01 | Phase 42 | Pending |
| BOPT-02 | Phase 42 | Pending |
| BOPT-03 | Phase 42 | Pending |
| FCLN-01 | Phase 43 | Pending |

**Coverage:**
- v1.7 requirements: 11 total
- Mapped to phases: 11
- Unmapped: 0 ✓

---
*Requirements defined: 2026-03-31*
*Last updated: 2026-03-31 after roadmap creation*
