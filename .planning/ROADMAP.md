# Roadmap: FlawChess

## Milestones

- ✅ **v1.0 Initial Platform** — Phases 1-10 (shipped 2024-03-15)
- ✅ **v1.1 Opening Explorer & UI Restructuring** — Phases 11-16 (shipped 2024-03-20)
- ✅ **v1.2 Mobile & PWA** — Phases 17-19 (shipped 2024-03-21)
- ✅ **v1.3 Project Launch** — Phases 20-23 (shipped 2026-03-22)
- **v1.4 Improvements** — Phases 24-25
- **v1.5 Game Statistics & Endgame Analysis** — Phases 26-33

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

### v1.4 Improvements

- [x] Phase 24: Web Analytics (2/2 plans) — completed 2026-03-22
  - **Goal:** Add privacy-friendly, low-resource web analytics to track page visits, top routes, and referrer sources
  - **Requirements:** ANLY-01, ANLY-02, ANLY-03, ANLY-04, ANLY-05
  - **Plans:** 2 plans
    - [x] 24-01-PLAN.md — Add Umami service to Docker Compose, Caddy subdomain, and env vars
    - [x] 24-02-PLAN.md — Deploy Umami, add tracking script to frontend, verify end-to-end
  - **Success criteria:**
    1. Site owner can view a dashboard showing page visit counts and trends
    2. Top pages by visit count are visible
    3. Referrer sources are tracked and displayed
    4. No cookie consent banner is needed (privacy-friendly solution)
    5. Analytics adds negligible RAM/CPU overhead to the Hetzner VPS

- [ ] **Phase 25: Password Reset** — Add forgot-password / reset-password flow
- [x] **Phase 26: Position Classifier & Schema** — Compute game phase, material signature, imbalance, and endgame class per position with schema migration (completed 2026-03-23)
- [x] **Phase 27: Import Wiring & Backfill** — Wire classifier into live import pipeline and backfill all existing game_positions rows (completed 2026-03-24)
- [x] **Phase 28: Engine Analysis Import** — Import chess.com accuracy scores and lichess per-move evals during game import (completed 2026-03-25)
- [x] **Phase 29: Endgame Analytics** — Backend API + frontend Endgames tab delivering W/D/L by endgame category and material conversion/recovery stats (completed 2026-03-26)
- [ ] **Phase 33: Homepage, README & SEO Update** — Update homepage content, README, and SEO metadata to showcase new statistics features introduced in v1.5

## Phase Details

### Phase 25: Password Reset
**Goal**: Users can recover account access when they forget their password
**Depends on**: Phase 24
**Requirements**: TBD
**Success Criteria** (what must be TRUE):
  1. User can request a password reset link using their email address
  2. User receives a reset email and can set a new password via the link
  3. After resetting, user can log in with the new password
**Plans**: TBD

### Phase 26: Position Classifier & Schema
**Goal**: Every imported position carries computed game phase, material signature, material imbalance, and endgame class stored in the database
**Depends on**: Phase 25
**Requirements**: PMETA-01, PMETA-02, PMETA-03, PMETA-04
**Success Criteria** (what must be TRUE):
  1. Alembic migration adds seven nullable columns to game_positions (game_phase, material_signature, material_imbalance, endgame_class, has_bishop_pair_white, has_bishop_pair_black, has_opposite_color_bishops) and applies cleanly against the production schema
  2. position_classifier.py correctly classifies a sample position across all edge cases: early queen trade is not classified as endgame, symmetric material produces the same canonical signature regardless of which color the user played, endgame_class is NULL for non-endgame positions
  3. Unit tests cover all six endgame class categories and the phase boundary heuristic, and all tests pass
**Plans:** 2/2 plans complete
  - [x] 26-01-PLAN.md — TDD position classifier module (classify_position + unit tests)
  - [x] 26-02-PLAN.md — GamePosition model columns, Alembic migration, chunk_size update

### Phase 27: Import Wiring & Backfill
**Goal**: All newly imported games populate the seven metadata columns at import time, and all previously imported games have those columns filled without requiring users to re-import
**Depends on**: Phase 26
**Requirements**: PMETA-05
**Success Criteria** (what must be TRUE):
  1. A newly imported game shows non-null game_phase values on all its game_positions rows
  2. The backfill script completes against the production database without OOM error, using batch_size=10 and resuming correctly if interrupted
  3. After backfill, zero rows in game_positions have a NULL game_phase value
  4. A post-backfill VACUUM runs and dead tuple count drops to near zero
**Plans:** 2/2 plans complete
  - [x] 27-01-PLAN.md — Wire classify_position into import pipeline per-ply loop
  - [x] 27-02-PLAN.md — Standalone backfill script with resumability, VACUUM, and tests

### Phase 27.1: Optimize game_positions column types (INSERTED)

**Goal:** Optimize game_positions with piece_count, backrank_sparse, and mixedness columns for endgame classification — implemented via quick tasks 260326-jo8 (piece_count + Lichess endgame threshold) and 260326-k94 (backrank_sparse + mixedness per Lichess Divider.scala algorithm)
**Requirements**: N/A (implemented via quick tasks)
**Depends on:** Phase 27
**Status:** Complete (2026-03-26, via quick tasks — no formal plans)
**Plans:** 0 formal plans

### Phase 28: Engine Analysis Import
**Goal**: The system imports available engine analysis data (chess.com accuracy scores, lichess per-move evals) during game import, storing them for future display
**Depends on**: Phase 27
**Requirements**: ENGINE-01, ENGINE-02, ENGINE-03
**Success Criteria** (what must be TRUE):
  1. A lichess game that has prior computer analysis imports with per-move eval values populated in the database
  2. A chess.com game with an accuracy score imports with that score stored; a game without accuracy data imports without error and stores NULL
  3. A game with no analysis data on either platform imports cleanly with all engine fields NULL and no error logged
**Plans:** 2/3 plans complete (28-03 deferred — admin re-import script for backfilling existing games)
  - [x] 28-01-PLAN.md — Schema migration, model updates, normalization accuracy extraction, lichess evals param, chunk_size fix
  - [x] 28-02-PLAN.md — Wire eval extraction into _flush_batch import pipeline
  - [ ] 28-03-PLAN.md — Admin re-import script for backfilling existing games (deferred)

### Phase 28.1: Import lichess analysis metrics (INSERTED)

**Goal:** Import lichess per-player analysis metrics (ACPL, inaccuracy count, mistake count, blunder count) into the games table during normalization -- storage only, no display
**Depends on:** Phase 28
**Requirements**: LMETRIC-01, LMETRIC-02
**Success Criteria** (what must be TRUE):
  1. Lichess games with computer analysis import with all 8 analysis metric columns populated (ACPL + 3 move quality counts per color)
  2. Lichess games without analysis and all chess.com games import with all 8 columns as NULL
  3. Alembic migration adds 8 nullable SmallInteger columns to games table and applies cleanly
**Plans:** 1/1 plans complete

Plans:
- [x] 28.1-01-PLAN.md — Game model columns, Alembic migration, lichess normalizer extraction, tests

### Phase 29: Endgame Analytics
**Goal**: Users can view their endgame performance and material conversion/recovery statistics in a new Endgames tab with time control and color filters
**Depends on**: Phase 28
**Requirements**: ENDGM-01, ENDGM-02, ENDGM-03, ENDGM-04, CONV-01, CONV-02, CONV-03
**Success Criteria** (what must be TRUE):
  1. User can open the Endgames tab and see W/D/L rates broken down by endgame category (rook, minor piece, pawn, queen, mixed, pawnless), with game count per category
  2. User can filter endgame statistics by time control (bullet/blitz/rapid/classical) and color (white/black/both) and the displayed numbers update correctly
  3. User can see win rate when materially up and draw/win rate when materially down, each broken down by game phase (opening/middlegame/endgame)
  4. User can filter conversion/recovery stats by time control and the displayed numbers update correctly
  5. Users with no endgame data see a meaningful empty state rather than an error or blank page
  6. The Endgame tab layout is usable on mobile (375px width) with the same filter and stats structure as the desktop layout
**Plans**: 3 plans

- [x] 29-01-PLAN.md — Backend endgame repository, service, router, schemas, and tests (TDD)
- [x] 29-02-PLAN.md — Frontend Statistics sub-tab with EndgameWDLChart, filter sidebar, types and hooks
- [x] 29-03-PLAN.md — Frontend Games sub-tab with GameCardList, navigation wiring, and visual checkpoint

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
| 25. Password Reset | v1.4 | 0/0 | Not started | — |
| 26. Position Classifier & Schema | v1.5 | 2/2 | Complete    | 2026-03-23 |
| 27. Import Wiring & Backfill | v1.5 | 2/2 | Complete    | 2026-03-24 |
| 28. Engine Analysis Import | v1.5 | 2/3 | Complete (03 deferred) | 2026-03-25 |
| 28.1. Import lichess analysis metrics | v1.5 | 1/1 | Complete | 2026-03-26 |
| 29. Endgame Analytics | v1.5 | 3/3 | Complete | 2026-03-26 |
| 27.1. Optimize game_positions columns | v1.5 | N/A | Complete | 2026-03-26 |
| 31. Endgame classification redesign | v1.5 | 2/2 | Complete | 2026-03-26 |
| 32. Endgame Performance Charts | v1.5 | 3/3 | Complete | 2026-03-27 |
| 33. Homepage, README & SEO Update | v1.5 | 2/3 | In Progress|  |

### Phase 31: Endgame classification redesign: per-position instead of per-game

**Goal:** Redesign endgame analytics from per-game single-transition-point to per-position classification, storing endgame_class on game_positions and enabling multi-class-per-game counting with a 6-ply minimum threshold
**Requirements**: TBD
**Depends on:** Phase 29
**Status:** Complete (2026-03-26)
**Success Criteria** (what must be TRUE):
  1. Every endgame position (piece_count <= 6) has a non-NULL endgame_class SmallInteger value
  2. A game passing through multiple endgame classes counts in each category it spent >= 6 plies in
  3. Games with fewer than 6 plies in an endgame class are excluded from that category
  4. Conversion/recovery uses material_imbalance at the first ply of each endgame class span
  5. No frontend changes — same API response shape, same Endgames tab UI
**Plans:** 2/2 plans complete

Plans:
- [x] 31-01-PLAN.md — Schema migration (endgame_class column + backfill + index), IntEnum mapping, import pipeline wiring, chunk_size update
- [x] 31-02-PLAN.md — Repository + service redesign for per-position multi-class grouping, test updates

### Phase 32: Endgame Performance Charts

**Goal:** Add endgame performance comparison charts: endgame vs non-endgame WDL, endgame strength gauge, and rolling-window timeline charts for overall and per-endgame-type win rates
**Requirements**: PERF-01, PERF-02, PERF-03, PERF-04, PERF-05, PERF-06, PERF-07
**Depends on:** Phase 31
**Status:** Complete (2026-03-27)
**Success Criteria** (what must be TRUE):
  1. "Endgame Performance" section shows WDL chart for games reaching endgame and a separate WDL chart for games that don't
  2. Endgame strength gauge compares endgame win rate against non-endgame win rate
  3. Timeline chart shows rolling 50-game win rate for all endgame games
  4. Timeline chart shows rolling 50-game win rate broken down by endgame type
  5. All charts respect existing filters (time control, platform, recency, rated, opponent)
**Plans:** 3/3 plans complete

Plans:
- [x] 32-01-PLAN.md — Backend schemas, repository queries, service functions, router endpoints, and tests
- [x] 32-02-PLAN.md — Frontend performance section (WDL bars, gauges) and conversion/recovery bar chart
- [x] 32-03-PLAN.md — Frontend timeline charts and visual verification

### Phase 33: Homepage, README & SEO Update
**Goal**: Update homepage content, README, and SEO metadata to showcase the new statistics features (endgame analytics, engine analysis) introduced in milestone v1.5
**Depends on**: Phase 32
**Requirements**: SC-01, SC-02, SC-03, SC-04, SC-05
**Success Criteria** (what must be TRUE):
  1. Homepage highlights endgame analytics and engine analysis features
  2. README accurately describes the current feature set
  3. SEO metadata (title, description, OG tags) reflects the new capabilities
**Plans:** 2/3 plans executed

Plans:
- [x] 33-01-PLAN.md — Restructure homepage FEATURES array (6 to 5 sections), simplify layout, update hero and FAQ
- [x] 33-02-PLAN.md — Update SEO meta tags in index.html and README feature list
- [ ] 33-03-PLAN.md — Capture fresh screenshots and remove old screenshot files

## Backlog

### Phase 999.1: Python Static Type Checker in CI (BACKLOG)

**Goal:** Add a Python static type checker to the CI pipeline to catch type-level bugs (typos, bare `str` where `Literal` is needed, wrong function names) that ruff cannot detect. Evaluate [ty](https://docs.astral.sh/ty/) (from Astral, same team as ruff/uv) vs pyright vs mypy.
**Requirements:** TBD
**Plans:** 0 plans

Plans:
- [ ] TBD (promote with /gsd:review-backlog when ready)
