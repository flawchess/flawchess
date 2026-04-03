# Roadmap: FlawChess

## Milestones

- ✅ **v1.0 Initial Platform** — Phases 1-10 (shipped 2024-03-15)
- ✅ **v1.1 Opening Explorer & UI Restructuring** — Phases 11-16 (shipped 2024-03-20)
- ✅ **v1.2 Mobile & PWA** — Phases 17-19 (shipped 2024-03-21)
- ✅ **v1.3 Project Launch** — Phases 20-23 (shipped 2026-03-22)
- ✅ **v1.4 Improvements** — Phase 24 (shipped 2026-03-22)
- ✅ **v1.5 Game Statistics & Endgame Analysis** — Phases 26-33 (shipped 2026-03-28)
- ✅ **v1.6 UI Polish & Improvements** — Phases 34-39 (shipped 2026-03-30)
- 🚧 **v1.7 Consolidation, Tooling & Refactoring** — Phases 40-43 (in progress)

## Phases

<details>
<summary>✅ v1.0 Initial Platform (Phases 1-10) — SHIPPED 2024-03-15</summary>

- [x] Phase 1: Data Foundation (2/2 plans) — completed 2024-03-11
- [x] Phase 2: Import Pipeline (4/4 plans) — completed 2024-03-12
- [x] Phase 3: Analysis API (2/2 plans) — completed 2024-03-12
- [x] Phase 4: Frontend and Auth (3/3 plans) — completed 2024-03-12
- [x] Phase 5: Position Bookmarks (5/5 plans) — completed 2024-03-13
- [x] Phase 6: Browser Automation Optimization (2/2 plans) — completed 2024-03-13
- [x] Phase 7: Game Statistics and Charts (3/3 plans) — completed 2024-03-14
- [x] Phase 8: Games and Bookmark Tab Rework (3/3 plans) — completed 2024-03-14
- [x] Phase 9: Game Cards, Username Import, Pagination (8/8 plans) — completed 2024-03-15
- [x] Phase 10: Auto-Generate Position Bookmarks (4/4 plans) — completed 2024-03-15

</details>

<details>
<summary>✅ v1.1 Opening Explorer & UI Restructuring (Phases 11-16) — SHIPPED 2024-03-20</summary>

- [x] Phase 11: Schema and Import Pipeline (1/1 plan) — completed 2024-03-16
- [x] Phase 12: Backend Next-Moves Endpoint (2/2 plans) — completed 2024-03-16
- [x] Phase 13: Frontend Move Explorer Component (2/2 plans) — completed 2024-03-16
- [x] Phase 14: UI Restructuring (3/3 plans) — completed 2024-03-17
- [x] Phase 15: Enhanced Game Import Data (3/3 plans) — completed 2024-03-18
- [x] Phase 16: Game Card UI Improvements (3/3 plans) — completed 2024-03-18

</details>

<details>
<summary>✅ v1.2 Mobile & PWA (Phases 17-19) — SHIPPED 2024-03-21</summary>

- [x] Phase 17: PWA Foundation + Dev Workflow (1/1 plan) — completed 2024-03-20
- [x] Phase 18: Mobile Navigation (1/1 plan) — completed 2024-03-20
- [x] Phase 19: Mobile UX Polish + Install Prompt (3/3 plans) — completed 2024-03-21

</details>

<details>
<summary>✅ v1.3 Project Launch (Phases 20-23) — SHIPPED 2026-03-22</summary>

- [x] Phase 20: Rename & Branding (2/2 plans) — completed 2026-03-21
- [x] Phase 21: Docker & Deployment (2/2 plans) — completed 2026-03-21
- [x] Phase 22: CI/CD & Monitoring (2/2 plans) — completed 2026-03-21
- [x] Phase 23: Launch Readiness (4/4 plans) — completed 2026-03-22

</details>

<details>
<summary>✅ v1.4 Improvements (Phase 24) — SHIPPED 2026-03-22</summary>

- [x] Phase 24: Web Analytics (2/2 plans) — completed 2026-03-22

</details>

<details>
<summary>✅ v1.5 Game Statistics & Endgame Analysis (Phases 26-33) — SHIPPED 2026-03-28</summary>

- [x] Phase 26: Position Classifier & Schema (2/2 plans) — completed 2026-03-23
- [x] Phase 27: Import Wiring & Backfill (2/2 plans) — completed 2026-03-24
- [x] Phase 27.1: Optimize game_positions columns (via quick tasks) — completed 2026-03-26
- [x] Phase 28: Engine Analysis Import (2/3 plans, 28-03 deferred) — completed 2026-03-25
- [x] Phase 28.1: Import lichess analysis metrics (1/1 plan) — completed 2026-03-26
- [x] Phase 29: Endgame Analytics (3/3 plans) — completed 2026-03-26
- [x] Phase 31: Endgame classification redesign (2/2 plans) — completed 2026-03-26
- [x] Phase 32: Endgame Performance Charts (3/3 plans) — completed 2026-03-27
- [x] Phase 33: Homepage, README & SEO Update (3/3 plans) — completed 2026-03-28

</details>

<details>
<summary>✅ v1.6 UI Polish & Improvements (Phases 34-39) — SHIPPED 2026-03-30</summary>

- [x] Phase 34: Theme Improvements (2/2 plans) — completed 2026-03-28
- [x] Phase 35: WDL Chart Refactoring (2/2 plans) — completed 2026-03-28
- [x] Phase 36: Most Played Openings (1/1 plan) — completed 2026-03-28
- [x] Phase 37: Openings Reference Table & Redesign (3/3 plans) — completed 2026-03-28
- [x] Phase 38: Opening Statistics & Bookmark Rework (2/2 plans) — completed 2026-03-29
- [x] Phase 39: Mobile Opening Explorer Sidebars (1/1 plan) — completed 2026-03-30

</details>

### v1.7 Consolidation, Tooling & Refactoring (In Progress)

**Milestone Goal:** Clean up and tighten the codebase for long-term maintainability and extendability — no new user-facing features.

- [x] **Phase 40: Static Type Checking** — Integrate `ty` into CI and fix type safety gaps in backend code (completed 2026-04-01)
- [x] **Phase 41: Code Quality & Dead Code** — Naming improvements, deduplication, dead code removal, frontend dead export detection (completed 2026-04-02)
- [x] **Phase 42: Backend Optimization** — DB query aggregation, column type optimization, API schema consistency (completed 2026-04-03)
- [ ] **Phase 43: Frontend Cleanup** — Refactor button brand colors to CSS variables; optional test coverage analysis

## Phase Details

### Phase 40: Static Type Checking
**Goal**: Backend type errors are caught at CI time, not at runtime
**Depends on**: Nothing (first phase of v1.7)
**Requirements**: TOOL-01, TOOL-02
**Success Criteria** (what must be TRUE):
  1. `ty` runs in CI pipeline and fails the build on type errors
  2. All backend functions have explicit type annotations on parameters and return values
  3. Untyped `dict` usage replaced with TypedDicts or Pydantic models where semantically meaningful
  4. `ty` passes clean (zero errors) on the backend codebase
**Plans**: 2 plans

Plans:
- [x] 40-01-PLAN.md — ty configuration, CI integration, and mechanical type error fixes (models, repositories, schemas, routers)
- [x] 40-02-PLAN.md — Service-layer TypedDicts/Pydantic models and test file type error fixes

### Phase 41: Code Quality & Dead Code
**Goal**: Codebase naming is clear, duplication is eliminated, and dead code is removed
**Depends on**: Phase 40
**Requirements**: TOOL-03, QUAL-01, QUAL-02, QUAL-03
**Success Criteria** (what must be TRUE):
  1. API endpoint paths, route names, and key variables follow a consistent, self-documenting naming convention
  2. Repeated logic is extracted into shared utilities or helpers — no significant copy-paste duplication remains
  3. Unreachable backend code and unused frontend exports are identified and removed
  4. knip.dev (or equivalent) report reviewed; actionable dead exports eliminated
**Plans**: 4 plans

Plans:
- [x] 41-01-PLAN.md — Install Knip, configure dead export detection, add frontend build/test/knip to CI
- [x] 41-02-PLAN.md — Backend router prefix consistency, shared apply_game_filters, frontend filter params dedup, dead code review
- [x] 41-03-PLAN.md — Run Knip report, review and remove confirmed dead frontend exports
- [x] 41-04-PLAN.md — Enable noUncheckedIndexedAccess in TypeScript, fix 56 type errors across 14 files

### Phase 41.1: Import Speed Optimization (INSERTED)

**Goal:** Import pipeline processes games at ~2x current throughput by eliminating triple PGN parsing, redundant DB round-trips, and per-game UPDATEs
**Requirements**: IMP-01, IMP-02, IMP-03, IMP-04, IMP-05
**Depends on:** Phase 41
**Success Criteria** (what must be TRUE):
  1. Each game's PGN is parsed exactly once during import (unified `process_game_pgn` function)
  2. `_flush_batch` does not SELECT Game.pgn from DB — uses in-memory platform_game_id lookup
  3. `move_count` and `result_fen` are updated via a single bulk CASE UPDATE per batch
  4. `_BATCH_SIZE` is 28 (reduced commit frequency by ~2.8x)
  5. All existing tests pass — zero regressions
**Plans**: 2 plans

Plans:
- [x] 41.1-01-PLAN.md — Unified process_game_pgn function with PlyData/GameProcessingResult TypedDicts, hashes_for_game thin wrapper
- [x] 41.1-02-PLAN.md — Refactor _flush_batch to use process_game_pgn, platform_game_id lookup, bulk CASE UPDATE, batch size 28

### Phase 42: Backend Optimization
**Goal**: Backend DB queries are efficient and all API responses use consistent Pydantic schemas
**Depends on**: Phase 40
**Requirements**: BOPT-01, BOPT-02, BOPT-03
**Success Criteria** (what must be TRUE):
  1. Identified row-level W/D/L counting loops replaced with SQL aggregations (COUNT().filter())
  2. `game_positions` column types verified as already optimal — no migration needed (BOPT-02 closed)
  3. All API endpoints return typed Pydantic response models — no bare `dict` or untyped returns
**Plans**: 2 plans

Plans:
- [x] 42-01-PLAN.md — SQL aggregation for openings W/D/L queries, column type verification (BOPT-01, BOPT-02)
- [x] 42-02-PLAN.md — Pydantic response models for 4 bare-dict endpoints (BOPT-03)

### Phase 43: Frontend Cleanup
**Goal**: Button brand colors are driven by CSS variables and the frontend has no hard-coded semantic color values
**Depends on**: Phase 41
**Requirements**: FCLN-01, TOOL-04
**Success Criteria** (what must be TRUE):
  1. Button brand color values are defined as CSS variables and imported consistently — no hard-coded hex/rgb values for brand buttons remain in components
  2. Brand color changes require editing only CSS variable definitions, not individual components
  3. (Optional) Test coverage report generated and baseline documented for future reference
**Plans**: TBD
**UI hint**: yes

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Data Foundation | v1.0 | 2/2 | Complete | 2024-03-11 |
| 2. Import Pipeline | v1.0 | 4/4 | Complete | 2024-03-12 |
| 3. Analysis API | v1.0 | 2/2 | Complete | 2024-03-12 |
| 4. Frontend and Auth | v1.0 | 3/3 | Complete | 2024-03-12 |
| 5. Position Bookmarks | v1.0 | 5/5 | Complete | 2024-03-13 |
| 6. Browser Automation | v1.0 | 2/2 | Complete | 2024-03-13 |
| 7. Game Statistics | v1.0 | 3/3 | Complete | 2024-03-14 |
| 8. Bookmark Tab Rework | v1.0 | 3/3 | Complete | 2024-03-14 |
| 9. Game Cards & Import | v1.0 | 8/8 | Complete | 2024-03-15 |
| 10. Auto Bookmarks | v1.0 | 4/4 | Complete | 2024-03-15 |
| 11. Schema & Pipeline | v1.1 | 1/1 | Complete | 2024-03-16 |
| 12. Next-Moves API | v1.1 | 2/2 | Complete | 2024-03-16 |
| 13. Move Explorer UI | v1.1 | 2/2 | Complete | 2024-03-16 |
| 14. UI Restructuring | v1.1 | 3/3 | Complete | 2024-03-17 |
| 15. Enhanced Import | v1.1 | 3/3 | Complete | 2024-03-18 |
| 16. Game Card UI | v1.1 | 3/3 | Complete | 2024-03-18 |
| 17. PWA Foundation + Dev Workflow | v1.2 | 1/1 | Complete | 2024-03-20 |
| 18. Mobile Navigation | v1.2 | 1/1 | Complete | 2024-03-20 |
| 19. Mobile UX Polish + Install Prompt | v1.2 | 3/3 | Complete | 2024-03-21 |
| 20. Rename & Branding | v1.3 | 2/2 | Complete | 2026-03-21 |
| 21. Docker & Deployment | v1.3 | 2/2 | Complete | 2026-03-21 |
| 22. CI/CD & Monitoring | v1.3 | 2/2 | Complete | 2026-03-21 |
| 23. Launch Readiness | v1.3 | 4/4 | Complete | 2026-03-22 |
| 24. Web Analytics | v1.4 | 2/2 | Complete | 2026-03-22 |
| 26. Position Classifier & Schema | v1.5 | 2/2 | Complete    | 2026-03-23 |
| 27. Import Wiring & Backfill | v1.5 | 2/2 | Complete    | 2026-03-24 |
| 28. Engine Analysis Import | v1.5 | 2/3 | Complete (03 deferred) | 2026-03-25 |
| 28.1. Import lichess analysis metrics | v1.5 | 1/1 | Complete | 2026-03-26 |
| 29. Endgame Analytics | v1.5 | 3/3 | Complete | 2026-03-26 |
| 27.1. Optimize game_positions columns | v1.5 | N/A | Complete | 2026-03-26 |
| 31. Endgame classification redesign | v1.5 | 2/2 | Complete | 2026-03-26 |
| 32. Endgame Performance Charts | v1.5 | 3/3 | Complete | 2026-03-27 |
| 33. Homepage, README & SEO Update | v1.5 | 3/3 | Complete | 2026-03-28 |
| 34. Theme Improvements | v1.6 | 2/2 | Complete    | 2026-03-28 |
| 35. WDL Chart Refactoring | v1.6 | 2/2 | Complete   | 2026-03-28 |
| 36. Most Played Openings | v1.6 | 1/1 | Complete    | 2026-03-28 |
| 37. Openings Reference Table & Redesign | v1.6 | 3/3 | Complete   | 2026-03-28 |
| 38. Opening Statistics & Bookmark Rework | v1.6 | 2/2 | Complete    | 2026-03-29 |
| 39. Mobile Opening Explorer Sidebars | v1.6 | 1/1 | Complete   | 2026-03-30 |
| 40. Static Type Checking | v1.7 | 2/2 | Complete    | 2026-04-01 |
| 41. Code Quality & Dead Code | v1.7 | 4/4 | Complete    | 2026-04-02 |
| 41.1. Import Speed Optimization | v1.7 | 2/2 | Complete    | 2026-04-03 |
| 42. Backend Optimization | v1.7 | 1/2 | Complete    | 2026-04-03 |
| 43. Frontend Cleanup | v1.7 | 0/TBD | Not started | - |

## Backlog

### Phase 999.1: Password Reset (BACKLOG)

**Goal:** Users can recover account access when they forget their password — request reset link, receive email, set new password
**Requirements:** TBD
**Plans:** 2/2 plans complete

Plans:
- [ ] TBD (promote with /gsd:review-backlog when ready)

### Phase 999.2: Python Static Type Checker in CI (BACKLOG)

**Goal:** Add a Python static type checker to the CI pipeline to catch type-level bugs (typos, bare `str` where `Literal` is needed, wrong function names) that ruff cannot detect. Evaluate [ty](https://docs.astral.sh/ty/) (from Astral, same team as ruff/uv) vs pyright vs mypy.
**Requirements:** TBD
**Plans:** 0 plans

Plans:
- [ ] TBD (promote with /gsd:review-backlog when ready)

### Phase 999.3: SQL-Side Aggregation for Remaining Python-Side DB Queries (BACKLOG)

**Goal:** Replace remaining Python-side row-by-row W/D/L counting with SQL GROUP BY + COUNT().filter() aggregation. High-impact targets: `analysis_service.analyze()` and `get_next_moves()` (N rows → 1), `endgame_service._aggregate_endgame_stats()` (K rows → 6). Lower priority: rolling-window functions that need chronological row data.
**Requirements:** TBD
**Plans:** 0 plans

Plans:
- [ ] TBD (promote with /gsd:review-backlog when ready)

### Phase 999.4: Position-Based Most Played Openings via game_positions (BACKLOG)

**Goal:** Redesign "Most Played Openings" to count how many games *passed through* each opening position (via `game_positions` Zobrist hash matching) instead of counting final opening name classifications from chess.com/lichess. Currently "1. e4" shows ~75 games (only games *classified* as "King's Pawn Game") while obscure specific lines rank higher. Position-based counting would show all ~2000+ games that played 1. e4, consistent with FlawChess's core Zobrist hash architecture. Requires JOIN from `openings` reference table to `game_positions` on FEN or precomputed hash, then `COUNT(DISTINCT game_id)`.
**Requirements:** TBD
**Plans:** 0 plans

Plans:
- [ ] TBD (promote with /gsd:review-backlog when ready)
