# Roadmap: FlawChess

## Milestones

- ✅ **v1.0 Initial Platform** — Phases 1-10 (shipped 2024-03-15)
- ✅ **v1.1 Opening Explorer & UI Restructuring** — Phases 11-16 (shipped 2024-03-20)
- ✅ **v1.2 Mobile & PWA** — Phases 17-19 (shipped 2024-03-21)
- ✅ **v1.3 Project Launch** — Phases 20-23 (shipped 2026-03-22)
- **v1.4 Improvements** — Phases 24-25
- **v1.5 Game Statistics & Endgame Analysis** — Phases 26-29

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
- [ ] **Phase 26: Position Classifier & Schema** — Compute game phase, material signature, imbalance, and endgame class per position with schema migration
- [ ] **Phase 27: Import Wiring & Backfill** — Wire classifier into live import pipeline and backfill all existing game_positions rows
- [ ] **Phase 28: Endgame Analytics** — Backend API + frontend Endgames tab delivering W/D/L by endgame category and material conversion/recovery stats
- [ ] **Phase 29: Engine Analysis Import** — Import chess.com accuracy scores and lichess per-move evals during game import

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
**Plans:** 1/2 plans executed
  - [ ] 26-01-PLAN.md — TDD position classifier module (classify_position + unit tests)
  - [x] 26-02-PLAN.md — GamePosition model columns, Alembic migration, chunk_size update

### Phase 27: Import Wiring & Backfill
**Goal**: All newly imported games populate the four new columns at import time, and all previously imported games have those columns filled without requiring users to re-import
**Depends on**: Phase 26
**Requirements**: PMETA-05
**Success Criteria** (what must be TRUE):
  1. A newly imported game shows non-null game_phase values on all its game_positions rows
  2. The backfill script completes against the production database without OOM error, using batch_size=10 and resuming correctly if interrupted
  3. After backfill, zero rows in game_positions have a NULL game_phase value
  4. A post-backfill VACUUM runs and dead tuple count drops to near zero
**Plans**: TBD

### Phase 28: Endgame Analytics
**Goal**: Users can view their endgame performance and material conversion/recovery statistics in a new Endgames tab with time control and color filters
**Depends on**: Phase 27
**Requirements**: ENDGM-01, ENDGM-02, ENDGM-03, ENDGM-04, CONV-01, CONV-02, CONV-03
**Success Criteria** (what must be TRUE):
  1. User can open the Endgames tab and see W/D/L rates broken down by endgame category (rook, minor piece, pawn, queen, mixed, pawnless), with game count per category
  2. User can filter endgame statistics by time control (bullet/blitz/rapid/classical) and color (white/black/both) and the displayed numbers update correctly
  3. User can see win rate when materially up and draw/win rate when materially down, each broken down by game phase (opening/middlegame/endgame)
  4. User can filter conversion/recovery stats by time control and the displayed numbers update correctly
  5. Users with no endgame data see a meaningful empty state rather than an error or blank page
  6. The Endgame tab layout is usable on mobile (375px width) with the same filter and stats structure as the desktop layout
**Plans**: TBD
**UI hint**: yes

### Phase 29: Engine Analysis Import
**Goal**: The system imports available engine analysis data (chess.com accuracy scores, lichess per-move evals) during game import, storing them for future display
**Depends on**: Phase 27
**Requirements**: ENGINE-01, ENGINE-02, ENGINE-03
**Success Criteria** (what must be TRUE):
  1. A lichess game that has prior computer analysis imports with per-move eval values populated in the database
  2. A chess.com game with an accuracy score imports with that score stored; a game without accuracy data imports without error and stores NULL
  3. A game with no analysis data on either platform imports cleanly with all engine fields NULL and no error logged
**Plans**: TBD

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
| 26. Position Classifier & Schema | v1.5 | 1/2 | In Progress|  |
| 27. Import Wiring & Backfill | v1.5 | 0/0 | Not started | — |
| 28. Endgame Analytics | v1.5 | 0/0 | Not started | — |
| 29. Engine Analysis Import | v1.5 | 0/0 | Not started | — |
