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
- ✅ **v1.12 Benchmark DB Infrastructure & Ingestion Pipeline** — Phase 69 (shipped 2026-04-26) — see [milestones/v1.12-ROADMAP.md](milestones/v1.12-ROADMAP.md)
- ✅ **v1.13 Opening Insights** — Phases 70, 71, 71.1 (shipped 2026-04-27; Phases 72-74 descoped) — see [milestones/v1.13-ROADMAP.md](milestones/v1.13-ROADMAP.md)
- ✅ **v1.14 Score-Based Opening Insights** — Phases 75, 76, 77 (shipped 2026-04-29; INSIGHT-UI-04 descoped) — see [milestones/v1.14-ROADMAP.md](milestones/v1.14-ROADMAP.md)
- 🚧 **v1.15 Eval-Based Endgame Classification** — Phases 78-79 (in progress, opened 2026-05-02) — Stockfish eval cutover for endgame conv/recov classification, plus position-phase classifier (opening/middlegame/endgame) and middlegame eval
- 📦 **v1.16 Stockfish Eval Analyses** — Phase 80+ (planned, opened 2026-05-03) — Downstream consumers of the v1.15 Stockfish evals (endgame span-entry + middlegame-entry `eval_cp`/`eval_mate`). First phase: opening-stats columns for middlegame-entry eval and clock diff. More phases TBD.

## Phases

<details open>
<summary>🚧 v1.15 Eval-Based Endgame Classification (Phases 78-79) — IN PROGRESS (opened 2026-05-02)</summary>

- 🚧 Phase 78: Stockfish-Eval Cutover for Endgame Classification (6/6 plans, code complete; operational backfill + VAL-01 + deploy + VAL-02 deferred to post-phase-79 combined run) — ENG-01..03, FILL-01..04, IMP-01..02, REFAC-01..05, VAL-01..02
- 🚧 Phase 79: Position-phase classifier and middlegame eval (3/4 plans) — CLASS-01..02, SCHEMA-01..02, PHASE-IMP-01..02, PHASE-FILL-01..03, PHASE-VAL-01..03, PHASE-INV-01

### Phase 78: Stockfish-Eval Cutover for Endgame Classification
**Goal**: Replace the material-imbalance + 4-ply persistence proxy for endgame conv/recov classification with Stockfish eval (depth 15) populated into the existing `eval_cp` / `eval_mate` columns on `game_positions`. Backfill historical span-entry positions across benchmark + prod, eval new span-entry positions during import going forward, refactor endgame queries to threshold on eval, and remove the proxy entirely (hard cutover).
**Depends on**: v1.14 shipped (Phase 77)
**Requirements**: ENG-01, ENG-02, ENG-03, FILL-01, FILL-02, FILL-03, FILL-04, IMP-01, IMP-02, REFAC-01, REFAC-02, REFAC-03, REFAC-04, REFAC-05, VAL-01, VAL-02
**Success Criteria** (what must be TRUE):
  1. The backend Docker image ships a pinned Stockfish binary, and a single shared engine wrapper module exposes a depth-15 evaluation API consumed by both the backfill script and the import path.
  2. After the benchmark backfill completes, every endgame span-entry row in the benchmark DB has either `eval_cp` or `eval_mate` populated; the prod backfill achieves the same coverage on prod span-entry rows (existing lichess `%eval` annotations preserved, never overwritten).
  3. New game imports populate `eval_cp` / `eval_mate` on per-class span-entry rows where the lichess `%eval` annotation did not already do so, adding well under 1 second to the typical-game import path.
  4. `app/repositories/endgame_repository.py` queries (`query_endgame_entry_rows`, `query_endgame_bucket_rows`, `query_endgame_elo_timeline_rows`) classify conv/parity/recov by thresholding `eval_cp` (±100 cp after color-sign flip) and `eval_mate` directly at the span-entry row — no contiguity-checked persistence lookup remains.
  5. `_MATERIAL_ADVANTAGE_THRESHOLD`, `PERSISTENCE_PLIES`, and the `array_agg(... ORDER BY ply)[PERSISTENCE_PLIES + 1]` contiguity case-expression no longer appear anywhere in the codebase; the `material_imbalance` column is retained for other consumers; `ix_gp_user_endgame_game` has been migrated via Alembic so the rewritten queries stay index-only.
  6. Re-running the `/conv-recov-validation` skill on the benchmark DB post-backfill produces ~100% agreement on the populated subset by construction, and the live-UI endgame gauges for representative test users show only the expected accuracy-driven shifts (operator smoke check).
**Plans**: 6 plans
  - [ ] 78-01-PLAN.md — Stockfish in backend Docker image (ENG-01)
  - [x] 78-02-PLAN.md — Engine wrapper module + lifespan integration (ENG-02, ENG-03)
  - [ ] 78-03-PLAN.md — Backfill script (FILL-01, FILL-02 relaxed, FILL-03)
  - [ ] 78-04-PLAN.md — Import-path integration (IMP-01, IMP-02)
  - [x] 78-05-PLAN.md — Endgame repository + service refactor + index migration (REFAC-01..05)
  - [ ] 78-06-PLAN.md — Operator-driven cutover execution (FILL-03, FILL-04, VAL-01, VAL-02)

### Phase 79: Position-phase classifier and middlegame eval

**Goal:** Add a per-position `phase` SmallInteger column (0=opening, 1=middlegame, 2=endgame) to `game_positions` via a Python port of lichess Divider.scala using existing `piece_count`, `backrank_sparse`, `mixedness` inputs. Extend Phase 78's import-time eval pass and `scripts/backfill_eval.py` so the middlegame entry position (MIN(ply) of phase=1 rows per game) is also evaluated with Stockfish at depth 15, populated into the existing `eval_cp` / `eval_mate` columns. Run the combined Phase 78 + Phase 79 backfill against benchmark first, then prod, then merge 78+79 to main and deploy. Folds in Phase 78's deferred operational steps (FILL-03, FILL-04, VAL-01, VAL-02).
**Requirements**: CLASS-01, CLASS-02, SCHEMA-01, SCHEMA-02, PHASE-IMP-01, PHASE-IMP-02, PHASE-FILL-01, PHASE-FILL-02, PHASE-FILL-03, PHASE-VAL-01, PHASE-VAL-02, PHASE-VAL-03, PHASE-INV-01
**Depends on:** Phase 78 (engine wrapper, backfill script, import-path integration)
**Plans:** 4 plans
**Context:** Adds a `phase` SmallInteger column (0=opening, 1=middlegame, 2=endgame) to `game_positions`, computed via a port of [lichess Divider.scala](https://github.com/lichess-org/scalachess/blob/master/core/src/main/scala/Divider.scala) using existing `piece_count`, `backrank_sparse`, `mixedness` inputs. Extends import path and backfill script to also evaluate the middlegame entry position with Stockfish (depth 15). Then runs the combined endgame + middlegame backfill on benchmark + prod (folds in phase 78's deferred operational steps), validates ≥99% agreement, merges 78+79 to main, and deploys.

Plans:
- [x] 79-01-PLAN.md — Schema migration + Divider classifier port + parity test fixture (SCHEMA-01, CLASS-01, CLASS-02, PHASE-VAL-01)
- [x] 79-02-PLAN.md — Import-path integration: phase column writes + middlegame entry import-time eval (SCHEMA-02, PHASE-IMP-01, PHASE-IMP-02)
- [x] 79-03-PLAN.md — Backfill script extension: phase UPDATE pass + middlegame entry eval pass (PHASE-FILL-01, PHASE-FILL-02)
- [ ] 79-04-PLAN.md — Operator-driven cutover: dev smoke + benchmark backfill + VAL-01 + prod backfill + combined PR merge + deploy + UI smoke check (PHASE-FILL-03, PHASE-VAL-02, PHASE-VAL-03, PHASE-INV-01)

</details>

<details>
<summary>📦 v1.16 Stockfish Eval Analyses (Phase 80+) — PLANNED (opened 2026-05-03)</summary>

Downstream consumers of the v1.15 Stockfish evals (endgame span-entry + middlegame-entry `eval_cp` / `eval_mate` on `game_positions`). Additional phases will be added as new analyses are scoped from `.planning/notes/phase-aware-analytics-ideas.md` and other brainstorms.

- [ ] Phase 80: Opening stats: middlegame-entry eval and clock-diff columns (0 plans) — not planned yet

### Phase 80: Opening stats: middlegame-entry eval and clock-diff columns

**Goal:** Extend the Openings → Stats subtab tables (bookmarked openings + most-played openings) with three new columns that consume the Phase 79 middlegame-entry Stockfish evals: (1) **Avg eval at middlegame entry ± std**, oriented from the user's POV (positive = user better, regardless of color); (2) **Eval significance** via a one-sample t-test of mean eval vs 0, surfaced with low/medium/high confidence buckets analogous to the opening insights cards; (3) **Avg clock diff at middlegame entry**, analogous to the existing "Avg clock diff" column in *Time Pressure at Endgame Entry*. Together these answer "does this opening leave me better off in position and on the clock when the real fight starts?" Both tables (bookmarked + most-played) get the same new columns; both desktop and mobile layouts updated.
**Requirements**: TBD (defined during /gsd-spec-phase 80 or /gsd-discuss-phase 80)
**Depends on:** v1.15 shipped (Phase 79 — needs `phase` SmallInteger column populated and middlegame-entry positions Stockfish-evaluated on benchmark + prod)
**Plans:** 0 plans
**Context:** Sources opening-stats data from positions where `phase = 1` AND it is `MIN(ply)` per game (the middlegame-entry row already populated by Phase 79). Eval is signed user-perspective via the existing color-flip helper used by endgame conv/recov queries. T-test confidence reuses the **10-game minimum threshold** from opening insights (matches `compute_confidence_bucket` in `app/services/opening_insights/`). Avg clock diff at middlegame entry mirrors the SQL pattern from "Avg clock diff at endgame entry" in `app/repositories/endgame_repository.py` — read user clock and opponent clock at the middlegame-entry row, average the diff. Source brainstorm: `.planning/notes/phase-aware-analytics-ideas.md` (Active focus section).

Plans:
- [ ] TBD (run `/gsd-plan-phase 80` to break down)

</details>

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
- [~] Phase 67: Validation & Beta Rollout — descoped, replaced by public rollout for all users (commit c91478e)
- [x] Phase 68: Endgame Score Timeline (dual-line + shaded gap) (4/4 plans) — completed 2026-04-24

See [milestones/v1.11-ROADMAP.md](milestones/v1.11-ROADMAP.md) for full details.

</details>

<details>
<summary>✅ v1.12 Benchmark DB Infrastructure & Ingestion Pipeline (Phase 69) — SHIPPED 2026-04-26</summary>

- [x] Phase 69: Benchmark DB Infrastructure & Ingestion Pipeline (6/6 plans) — completed 2026-04-26 via PR #65 — INFRA-01..03, INGEST-01..06

See [milestones/v1.12-ROADMAP.md](milestones/v1.12-ROADMAP.md) for full details.

</details>

<details>
<summary>✅ v1.13 Opening Insights (Phases 70, 71, 71.1) — SHIPPED 2026-04-27</summary>

- [x] Phase 70: Backend opening insights service (5/5 plans) — completed 2026-04-26 via PR #66 — INSIGHT-CORE-01..09
- [x] Phase 71: Frontend Stats subtab — `OpeningInsightsBlock` (6/6 plans) — completed 2026-04-27 via PR #67 — INSIGHT-STATS-01..06
- [x] Phase 71.1: Openings subnav layout refactor — match Endgames pattern (3/3 plans, INSERTED) — completed 2026-04-27 via PR #68
- [~] Phase 72: Frontend Moves subtab — inline weakness/strength bullets — descoped 2026-04-27 (covered by MoveExplorer row tint via `getArrowColor`)
- [~] Phase 73: Meta-recommendation aggregate finding (stretch) — descoped 2026-04-27 (per-finding cards in Phase 71 already deliver actionable signal)
- [~] Phase 74: Bookmark-card weakness badge (stretch) — descoped 2026-04-27 (alert-fatigue concern with existing nav notification dots)

See [milestones/v1.13-ROADMAP.md](milestones/v1.13-ROADMAP.md) for full details.

</details>

<details>
<summary>✅ v1.14 Score-Based Opening Insights (Phases 75, 76, 77) — SHIPPED 2026-04-29</summary>

- [x] Phase 75: Backend — score metric and confidence annotation (4/4 plans) — completed 2026-04-28 (PR #69)
- [x] Phase 76: Frontend — score-based coloring, confidence badges, label reframe (8/8 plans) — completed 2026-04-28 (PR #70; inline confidence-mute hotfix PR #71)
- [x] Phase 77: Troll-opening watermark on Insights findings (4/4 plans) — completed 2026-04-28 (PR #72)

See [milestones/v1.14-ROADMAP.md](milestones/v1.14-ROADMAP.md) for full details.

</details>

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1-10. v1.0 phases | v1.0 | 36/36 | Complete | 2024-03-15 |
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
| 69. Benchmark DB Infra & Ingestion | v1.12 | 6/6 | Complete (follow-on phases → SEED-006) | 2026-04-26 |
| 70-71.1. v1.13 phases | v1.13 | 14/14 | Complete (Phases 72/73/74 descoped) | 2026-04-27 |
| 75-77. v1.14 phases | v1.14 | 16/16 | Complete (INSIGHT-UI-04 descoped) | 2026-04-29 |
| 78. Eval-based endgame classification | v1.15 | 2/6 | In Progress|  |

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

