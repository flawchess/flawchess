# Roadmap: FlawChess

## Milestones

- ✅ **v1.0 Initial Platform** — Phases 1-10 (shipped 2024-03-15)
- ✅ **v1.1 Opening Explorer & UI Restructuring** — Phases 11-16 (shipped 2024-03-20)
- ✅ **v1.2 Mobile & PWA** — Phases 17-19 (shipped 2024-03-21)
- ✅ **v1.3 Project Launch** — Phases 20-23 (shipped 2026-03-22)
- ✅ **v1.4 Improvements** — Phase 24 (shipped 2026-03-22)
- ✅ **v1.5 Game Statistics & Endgame Analysis** — Phases 26-33 (shipped 2026-03-28)
- ✅ **v1.6 UI Polish & Improvements** — Phases 34-39 (shipped 2026-03-30)
- ✅ **v1.7 Consolidation, Tooling & Refactoring** — Phases 40-43 (shipped 2026-04-03)
- ✅ **v1.8 Guest Access** — Phases 44-47 (shipped 2026-04-06)
- ✅ **v1.9 UI/UX Restructuring** — Phases 49-51 (shipped 2026-04-10) — see [milestones/v1.9-ROADMAP.md](milestones/v1.9-ROADMAP.md)
- ✅ **v1.10 Advanced Analytics** — Phases 48, 52-55, 57, 57.1, 59-62 (shipped 2026-04-19) — see [milestones/v1.10-ROADMAP.md](milestones/v1.10-ROADMAP.md)
- ✅ **v1.11 LLM-first Endgame Insights** — Phases 63-68 (shipped 2026-04-24) — see [milestones/v1.11-ROADMAP.md](milestones/v1.11-ROADMAP.md)
- ✅ **v1.12 Benchmark DB Infrastructure & Ingestion Pipeline** — Phase 69 (shipped 2026-04-26). The applied-analytics work originally scoped under v1.12 (classifier validation at scale, rating-stratified offsets, Parity validation, `/benchmarks` skill upgrade & zone recalibration) was deferred to a future milestone — see [seeds/SEED-006](seeds/SEED-006-benchmark-population-zone-recalibration.md). Full archive: [milestones/v1.12-ROADMAP.md](milestones/v1.12-ROADMAP.md)
- 🚧 **v1.13 Opening Insights** — Phases 70-74 (planning, opened 2026-04-26) — see [milestones/v1.13-ROADMAP.md](milestones/v1.13-ROADMAP.md)

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

<details>
<summary>✅ v1.7 Consolidation, Tooling & Refactoring (Phases 40-43) — SHIPPED 2026-04-03</summary>

- [x] Phase 40: Static Type Checking (2/2 plans) — completed 2026-04-01
- [x] Phase 41: Code Quality & Dead Code (4/4 plans) — completed 2026-04-02
- [x] Phase 41.1: Import Speed Optimization (2/2 plans) — completed 2026-04-03
- [x] Phase 42: Backend Optimization (2/2 plans) — completed 2026-04-03
- [x] Phase 43: Frontend Cleanup (1/1 plan) — completed 2026-04-03

</details>

<details>
<summary>✅ v1.8 Guest Access (Phases 44-47) — SHIPPED 2026-04-06</summary>

- [x] Phase 44: Guest Session Foundation — completed 2026-04-06
- [x] Phase 45: Guest Frontend — completed 2026-04-06
- [x] Phase 46: Email/Password Promotion — completed 2026-04-06
- [x] Phase 47: Google SSO Promotion — completed 2026-04-06

</details>

<details>
<summary>✅ v1.9 UI/UX Restructuring (Phases 49-51) — SHIPPED 2026-04-10</summary>

- [x] Phase 49: Openings Desktop Sidebar (1/1 plan) — completed 2026-04-09
- [x] Phase 50: Mobile Layout Restructuring (2/2 plans) — completed 2026-04-10
- [x] Phase 51: Stats Subtab, Homepage & Global Stats (4/4 plans) — completed 2026-04-10

See [milestones/v1.9-ROADMAP.md](milestones/v1.9-ROADMAP.md) for full details.

</details>

<details>
<summary>✅ v1.10 Advanced Analytics (Phases 48, 52-55, 57, 57.1, 59-62) — SHIPPED 2026-04-19</summary>

- [x] Phase 48: Conversion & Recovery Persistence Filter (2/2 plans) — completed 2026-04-07
- [x] Phase 52: Endgame Tab Performance (3/3 plans) — completed 2026-04-11
- [x] Phase 53: Endgame Score Gap & Material Breakdown (2/2 plans) — completed 2026-04-12
- [x] Phase 54: Time Pressure — Clock Stats Table (2/2 plans) — completed 2026-04-12
- [x] Phase 55: Time Pressure — Performance Chart (2/2 plans) — completed 2026-04-12
- [~] Phase 56: Endgame ELO Backend + Breakdown Table — cancelled, subsumed by Phase 57
- [x] Phase 57: Endgame ELO Timeline Chart (2/2 plans) — completed 2026-04-18
- [x] Phase 57.1: Endgame ELO Timeline Anchor Change + Volume Bars (2/2 plans, INSERTED) — completed 2026-04-18
- [→] Phase 58: Opening Risk & Drawishness — moved to backlog as Phase 999.6
- [x] Phase 59: Fix Endgame Conv/Parity/Recov per-game stats (3/3 plans) — completed 2026-04-13
- [x] Phase 60: Opponent-based Baseline for Endgame Conv/Recov (2/2 plans) — completed 2026-04-14
- [x] Phase 61: Test Suite Hardening & DB Reset (3/3 plans) — completed 2026-04-16
- [x] Phase 62: Admin User Impersonation (5/5 plans) — completed 2026-04-17

See [milestones/v1.10-ROADMAP.md](milestones/v1.10-ROADMAP.md) for full details.

</details>

<details>
<summary>✅ v1.11 LLM-first Endgame Insights (Phases 63-68) — SHIPPED 2026-04-24</summary>

- [x] Phase 63: Findings Pipeline & Zone Wiring (5/5 plans) — completed 2026-04-20
- [x] Phase 64: `llm_logs` Table & Async Repo (3/3 plans) — completed 2026-04-20
- [x] Phase 65: LLM Endpoint with pydantic-ai Agent (6/6 plans) — completed 2026-04-21
- [x] Phase 66: Frontend EndgameInsightsBlock & Beta Flag (5/5 plans) — completed 2026-04-22
- [~] Phase 67: Validation & Beta Rollout — **descoped**, replaced by public rollout for all users (commit c91478e)
- [x] Phase 68: Endgame Score Timeline (dual-line + shaded gap) (4/4 plans) — completed 2026-04-24

See [milestones/v1.11-ROADMAP.md](milestones/v1.11-ROADMAP.md) for full details.

</details>

<details>
<summary>✅ v1.12 Benchmark DB Infrastructure & Ingestion Pipeline (Phase 69) — SHIPPED 2026-04-26</summary>

- [x] Phase 69: Benchmark DB Infrastructure & Ingestion Pipeline (6/6 plans) — completed 2026-04-26 via PR #65 — INFRA-01..03, INGEST-01..06

**Scope-down (2026-04-26):** v1.12 was originally planned to include four follow-on applied-analytics phases (classifier validation at scale, rating-stratified offsets, Parity validation, `/benchmarks` skill upgrade & zone recalibration). They were moved to a future milestone seeded at [seeds/SEED-006](seeds/SEED-006-benchmark-population-zone-recalibration.md) with no phase numbers retained. The full benchmark ingest is operational work (days of wall-clock time), not a milestone gate; treating it as one was blocking unrelated work like v1.13 opening insights. Pipeline correctness is the v1.12 deliverable; populating the DB is ops. The phase-number range 70-74 was subsequently allocated to v1.13.

See [milestones/v1.12-ROADMAP.md](milestones/v1.12-ROADMAP.md) for full details.

</details>

<details open>
<summary>🚧 v1.13 Opening Insights (Phases 70-74) — IN PLANNING (opened 2026-04-26)</summary>

- [ ] Phase 70: Backend opening insights service — INSIGHT-CORE-01..09
- [ ] Phase 71: Frontend Stats subtab — `OpeningInsightsBlock` — INSIGHT-STATS-01..06
- [ ] Phase 72: Frontend Moves subtab — inline weakness/strength bullets — INSIGHT-MOVES-01..03
- [ ] Phase 73 (stretch): Meta-recommendation aggregate finding — INSIGHT-META-01
- [ ] Phase 74 (stretch): Bookmark-card weakness badge — INSIGHT-BADGE-01

See [milestones/v1.13-ROADMAP.md](milestones/v1.13-ROADMAP.md) for full details.

</details>

## Phase Details (v1.13 active)

### Phase 70: Backend opening insights service
**Goal**: A user-scoped `opening_insights_service` produces ranked, deduplicated, structured `OpeningInsightFinding` payloads for every (entry_position, candidate_move) pair that classifies as a weakness or strength against the user's filtered game history.
**Depends on**: PRE-01 fix landed (top-10 parity bug); reuses existing `query_top_openings_sql_wdl`, `apply_game_filters`, and `game_positions` Zobrist-hash schema. No new schema or migration.
**Requirements**: INSIGHT-CORE-01, INSIGHT-CORE-02, INSIGHT-CORE-03, INSIGHT-CORE-04, INSIGHT-CORE-05, INSIGHT-CORE-06, INSIGHT-CORE-07, INSIGHT-CORE-08, INSIGHT-CORE-09
**Success Criteria** (what must be TRUE):
  1. `POST /api/insights/openings` (or equivalent) returns a structured `OpeningInsightFinding[]` payload for an authenticated user under their active filter set; equivalent filter states return equivalent rankings.
  2. The scan input is exactly `top-10 most-played openings per color ∪ user bookmarks`, with the configurable min-games-per-entry floor enforced; scanning recurses **only** to the immediate next ply (no deep recursion).
  3. Each (entry_position, candidate_move) pair with n ≥ 10 games is classified `weakness` (loss_rate ≥ 0.55), `strength` (score ≥ 0.60), or dropped as neutral; findings are deduplicated by Zobrist hash with deepest-opening attribution.
  4. Findings are ranked by frequency × severity (formula resolved in Phase 70 `/gsd-discuss-phase`) and capped at the configurable display ceiling (default top 5 weaknesses + top 3 strengths).
  5. Latency budget — typical user (≤ ~2k games) sees on-the-fly responses without precompute; service-layer caching is added only if heavy users (10k+) breach the budget.
**Plans**: 5 plans
  - [x] 70-01-PLAN.md — Pydantic schemas (Request/Finding/Response) + Wave 0 test scaffolding
  - [x] 70-02-PLAN.md — Alembic CONCURRENTLY migration adding ix_gp_user_game_ply + GamePosition.__table_args__
  - [x] 70-03-PLAN.md — Repository: query_opening_transitions (LAG CTE) + query_openings_by_hashes
  - [x] 70-04-PLAN.md — Service: compute_insights() classify/attribute/dedupe/rank/cap pipeline
  - [x] 70-05-PLAN.md — Router POST /openings + REQUIREMENTS/ROADMAP/CHANGELOG amendments per D-15/D-16/D-17

### Phase 71: Frontend Stats subtab — `OpeningInsightsBlock`
**Goal**: Users see ranked weakness and strength bullets on Openings → Stats subtab, with deep-links that navigate to Openings → Moves pre-loaded at the entry FEN with the candidate move highlighted.
**Depends on**: Phase 70
**Requirements**: INSIGHT-STATS-01, INSIGHT-STATS-02, INSIGHT-STATS-03, INSIGHT-STATS-04, INSIGHT-STATS-05, INSIGHT-STATS-06
**Success Criteria** (what must be TRUE):
  1. Authenticated user with at least one qualifying finding sees an `OpeningInsightsBlock` on Openings → Stats subtab with templated bullets like "You lose 62% as Black after 1.e4 c5 2.Nf3 d6 3.d4 cxd4 4.Nxd4 (n=18) → [open in Move Explorer]" using the existing red/green semantic theme colors.
  2. Clicking a finding's deep-link navigates to Openings → Moves with the chessboard pre-loaded at the entry FEN and the candidate move visibly highlighted.
  3. When the active filter set yields no findings, the block renders a clear empty-state message naming the threshold and the min-games floor.
  4. Changing filters (color, time_control, recency, opponent_type/strength, rated) refreshes the block; loading and error states match v1.11 EndgameInsightsBlock conventions.
  5. Block renders cleanly inside the mobile drawer / single-column layout — verified at 375px width, no horizontal scroll, ≥ 44px touch targets, semantic HTML + `data-testid` per CLAUDE.md frontend rules.
**Plans**: 6 plans
  - [x] 71-01-PLAN.md — Phase 70 contract amendment: add entry_san_sequence to OpeningInsightFinding
  - [x] 71-02-PLAN.md — Extract LazyMiniBoard from GameCard into shared module
  - [x] 71-03-PLAN.md — Types, openingInsights helpers (trim, severity-color, threshold copy), useOpeningInsights hook
  - [x] 71-04-PLAN.md — OpeningFindingCard component (per-finding card with severity border, dual layout, prose)
  - [x] 71-05-PLAN.md — OpeningInsightsBlock component (outer block, 4 sections, loading/error/empty/populated states)
  - [ ] 71-06-PLAN.md — Stats tab integration + handleOpenFinding deep-link wiring + manual UAT
**UI hint**: yes

### Phase 71.1: Openings subnav layout refactor — match Endgames pattern (INSERTED)

**Goal:** Refactor `frontend/src/pages/Openings.tsx` so its subnav and mobile shape match the Endgames page pattern. Desktop subnav lifts to span the full right side of `SidebarLayout` (board column + main content). Mobile gets a sticky subnav with a filter button, the chevron-fold sticky board is removed, the board becomes non-sticky on Moves + Games, and is hidden entirely on Stats + Insights — all per the locked decisions in 71.1-CONTEXT.md.
**Depends on:** Phase 71
**Requirements**: N/A (frontend layout refactor — decisions live in `71.1-CONTEXT.md`, not `REQUIREMENTS.md`)
**Success Criteria** (what must be TRUE):
  1. Desktop (≥ 1024px): subnav spans the full width of `(board column + main content)` above both. Right-of-board settings column visible only on Moves + Games. Board column visible on all 4 subtabs. Left sidebar strip + slide-out panel unchanged.
  2. Mobile (< 1024px): sticky subnav at top with 4 subtabs + filter button on the right edge. Filter drawer opens from this new button. Chevron fold + grid-rows collapse animation removed. Board, controls, moves field non-sticky and scroll with the page on Moves + Games. Stats + Insights hide the board, controls, and moves field entirely. Subtab switching resets scroll to top.
  3. No horizontal scroll at 375px viewport. Tabs + filter button have ≥ 44px touch targets. All interactive elements have `data-testid` per CLAUDE.md frontend rules; mobile and desktop changes are applied symmetrically per "always apply changes to mobile too".
  4. `npm run knip` in `frontend/` reports no new dead exports — chevron/fold cleanup is complete.
  5. Phase 71 plans (`OpeningInsightsBlock`, deep-links, etc.) still render correctly inside the new layout — no Phase 71 regression.
**Plans:** 3/3 plans complete
  - [x] 71.1-01-PLAN.md — Desktop subnav lift: wrap SidebarLayout in Tabs, render TabsList above board column + main content (D-01, D-04, D-13)
  - [x] 71.1-02-PLAN.md — Mobile rework: sticky subnav with filter button, non-sticky board conditional on Moves/Games, chevron-fold removed (D-05..D-11, D-13)
  - [x] 71.1-03-PLAN.md — Cleanup: delete chevron-fold dead state, run knip/lint/build/test gates, manual UAT at 375px (D-12)
**UI hint**: yes

### Phase 72: Frontend Moves subtab — inline weakness/strength bullets
**Goal**: When the user is viewing a position on Openings → Moves that has at least one classified candidate-move finding, an inline bullet appears next to the existing red/green candidate-move arrow for that finding, scoped to the currently displayed position only.
**Depends on**: Phase 70
**Requirements**: INSIGHT-MOVES-01, INSIGHT-MOVES-02, INSIGHT-MOVES-03
**Success Criteria** (what must be TRUE):
  1. On Openings → Moves, when the displayed position matches a Phase-70 finding's `entry_fen`, a templated bullet renders inline next to the existing red/green candidate-move arrow for that finding's `candidate_move_san`.
  2. Bullets are scoped to the currently displayed position only — no full-scan list and no deep-link affordance.
  3. The same `OpeningInsightFinding` payload powers both this view and the Stats block; no second backend route or schema is introduced.
**Plans**: TBD
**UI hint**: yes

### Phase 73 (stretch): Meta-recommendation aggregate finding
**Goal**: Above the per-finding list on the Stats subtab, render a single templated aggregate sentence summarizing the user's repertoire-level pattern (e.g. "You have weaknesses across 8 different openings — consider narrowing your repertoire").
**Depends on**: Phase 70, Phase 71. Stretch — deferrable without affecting core delivery.
**Requirements**: INSIGHT-META-01
**Success Criteria** (what must be TRUE):
  1. When the findings list contains weaknesses spanning multiple openings, the aggregate sentence appears above the per-finding bullets and reflects the active filter set.
  2. The rule(s) that generate the sentence are pure templated logic over the findings list — no LLM call, no second backend round trip.
  3. When findings are absent or below the meta-rule threshold, the aggregate sentence is suppressed.
**Plans**: TBD
**UI hint**: yes

### Phase 74 (stretch): Bookmark-card weakness badge
**Goal**: A small visual indicator (red dot + count chip) appears on bookmark cards whose bookmarked opening surfaces ≥ 1 Phase-70 weakness finding under the active filter set, on both desktop bookmarks panel and mobile bookmarks drawer.
**Depends on**: Phase 70. Stretch — deferrable without affecting core delivery.
**Requirements**: INSIGHT-BADGE-01
**Success Criteria** (what must be TRUE):
  1. A bookmark card whose `entry_fen` matches at least one weakness finding shows a red dot + count chip badge; cards with no findings render unchanged.
  2. The badge is present in both the desktop bookmarks panel (`PositionBookmarkCard`) and the mobile bookmarks drawer — applied consistently per CLAUDE.md "always apply changes to mobile too" rule.
  3. The badge updates when filters change — same data source as the Stats block, so badge state stays consistent with the bullet list.
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
| 11-16. v1.1 phases | v1.1 | 14/14 | Complete | 2024-03-18 |
| 17-19. v1.2 phases | v1.2 | 5/5 | Complete | 2024-03-21 |
| 20-23. v1.3 phases | v1.3 | 10/10 | Complete | 2026-03-22 |
| 24. Web Analytics | v1.4 | 2/2 | Complete | 2026-03-22 |
| 26-33. v1.5 phases | v1.5 | 18/19 | Complete (28-03 deferred) | 2026-03-28 |
| 34-39. v1.6 phases | v1.6 | 11/11 | Complete | 2026-03-30 |
| 40-43. v1.7 phases | v1.7 | 11/11 | Complete | 2026-04-03 |
| 44-47. v1.8 phases | v1.8 | N/A | Complete | 2026-04-06 |
| 49-51. v1.9 phases | v1.9 | 7/7 | Complete | 2026-04-10 |
| 48, 52-62. v1.10 phases | v1.10 | 28/28 | Complete | 2026-04-19 |
| 63-68. v1.11 phases | v1.11 | 23/23 | Complete (Phase 67 descoped) | 2026-04-24 |
| 69. Benchmark DB Infra & Ingestion Pipeline | v1.12 | 6/6 | Complete (follow-on phases deferred to SEED-006) | 2026-04-26 |
| 70. Backend opening insights service | v1.13 | 5/5 | Complete   | 2026-04-26 |
| 71. `OpeningInsightsBlock` (Stats subtab) | v1.13 | 5/6 | In Progress|  |
| 72. Inline bullets (Moves subtab) | v1.13 | 0/0 | Not started | — |
| 73. Meta-recommendation (stretch) | v1.13 | 0/0 | Not started | — |
| 74. Bookmark-card weakness badge (stretch) | v1.13 | 0/0 | Not started | — |

## Backlog

### Phase 999.1: Password Reset (BACKLOG)

**Goal:** Users can recover account access when they forget their password — request reset link, receive email, set new password
**Requirements:** TBD
**Plans:** 5/6 plans executed

Plans:
- [ ] TBD (promote with /gsd:review-backlog when ready)

### Phase 999.5: Hybrid Stockfish Eval for Conversion/Recovery (BACKLOG)

**Goal:** Use Stockfish eval (`eval_cp`) as the advantage/disadvantage signal for conversion/recovery classification when available, falling back to material imbalance + 4-ply persistence for games without eval. Stockfish eval is the gold standard (no persistence filter needed since eval handles transient trades natively). Currently only ~15% of Lichess games have eval data and chess.com has 0%, but this improves automatically as more games get server-analyzed. Validated in `docs/endgame-conversion-recovery-analysis.md`: persistence closes 50-70% of the gap to Stockfish for pawn/mixed endgames, but a hybrid approach would eliminate the remaining 5-8pp offset for eval-available games.
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

### Phase 999.6: Opening Risk & Drawishness (BACKLOG)

**Goal:** Risk and drawishness metrics per position in the move explorer.
**Requirements:** TBD
**Plans:** 0 plans
**Context:** Moved from v1.10 Advanced Analytics — v1.10 is an endgame-focused milestone and opening risk metrics are a better fit for the upcoming Opening Insights milestone (discovering weaknesses in most-played opening lines). Re-evaluate scope at that time.

Plans:
- [ ] TBD (promote with /gsd-review-backlog when ready)

