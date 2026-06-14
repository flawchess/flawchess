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
- ✅ **v1.15 Eval-Based Endgame Classification** — Phases 78, 79 (shipped 2026-05-03; VAL-01 / PHASE-VAL-01 rescinded) — see [milestones/v1.15-ROADMAP.md](milestones/v1.15-ROADMAP.md)
- ✅ **v1.16 Stockfish Eval Analyses** — Phases 80, 80.1, 81, 82, 83 (shipped 2026-05-11) — see [milestones/v1.16-ROADMAP.md](milestones/v1.16-ROADMAP.md)
- ✅ **v1.17 Endgame Stats Card Redesign** — Phases 84-88.4 (shipped 2026-05-19; Phase 89 dropped, 87.3 superseded) — see [milestones/v1.17-ROADMAP.md](milestones/v1.17-ROADMAP.md)
- ✅ **v1.18 Import Pipeline Hardening** — Phases 90, 91, 92 (shipped 2026-05-22; PRs #130, #137, #138 + hotfix #139) — see [milestones/v1.18-ROADMAP.md](milestones/v1.18-ROADMAP.md)
- ✅ **v1.19 Endgame Percentiles** — Phases 93, 94, 94.1, 94.2, 94.3, 94.4 (shipped 2026-05-27; Phase 95 split out before milestone close) — see [milestones/v1.19-ROADMAP.md](milestones/v1.19-ROADMAP.md)
- ✅ **v1.20 Import Pipeline Hardening Follow-Up and Readiness** — Phases 95, 96 (shipped 2026-05-29) — see [milestones/v1.20-ROADMAP.md](milestones/v1.20-ROADMAP.md)
- ✅ **v1.21 Time-Control-Aware Endgame Metrics** — Phases 97, 98, 99, 99.1 (shipped 2026-05-31; PRs #160, #163/#164, #167, #168) — see [milestones/v1.21-ROADMAP.md](milestones/v1.21-ROADMAP.md)
- ✅ **v1.22 Maintenance — Test Isolation & Frontend Major Upgrades** — Phases 100, 101 (shipped 2026-05-31) — see [milestones/v1.22-ROADMAP.md](milestones/v1.22-ROADMAP.md)
- ✅ **v1.23 LLM Endgame-Insights Statistical-Reasoning Rework** — Phases 102, 103 (shipped 2026-06-03) — see [milestones/v1.23-ROADMAP.md](milestones/v1.23-ROADMAP.md)
- ✅ **v1.24 Library Page** — Phases 104–112 (shipped 2026-06-09) — see [milestones/v1.24-ROADMAP.md](milestones/v1.24-ROADMAP.md)
- ✅ **v1.25 Flaw-Stats Opponent Comparison** — Phases 113–115 (incl. 114.1) (shipped 2026-06-12) — see [milestones/v1.25-ROADMAP.md](milestones/v1.25-ROADMAP.md)
- **v1.26 Full-Game Eval Pipeline** — Phases 116–119 (in progress)

## Phases

### v1.26 Full-Game Eval Pipeline (Phases 116–119)

- [ ] **Phase 116: All-Ply Engine Core** - Search-budget upgrade + all-ply target collector + dedup + completion marker + memory bounds
  - **Plans:** 3 plans
  - Plans:
    - [x] 116-01-PLAN.md — Schema + engine API: full_evals_completed_at column, dedup index, verified backfill migration, evaluate_nodes() 1M-node call (EVAL-02, EVAL-05, EVAL-03)
    - [x] 116-02-PLAN.md — run_full_eval_drain coroutine: all-ply collector, ply≤20 dedup, preserve/overwrite write, completion marker, yield gate, lifespan wiring (EVAL-01, EVAL-03, EVAL-05, QUEUE-07)
    - [x] 116-03-PLAN.md — QUEUE-07 memory accounting: measure per-worker RSS at 1M nodes, document 4g budget, correct stale pool-size comments, gate pool→8 (QUEUE-07)
- [x] **Phase 117: Priority Queue + Flaw Integration** - Tiered priority queue replacing LIFO pick + round-robin fairness + tier-1 fan-out + idle drain + lease/report contract + PV capture + flaw flow-through + guest exclusion
  - **Plans:** 3 plans — EXECUTED + verified (14/14 must-haves). DEPLOYED to prod 2026-06-14 via release #190 (`e97bcf54`).
  - Plans:
    - [x] 117-01-PLAN.md — Migration + schema: best_move/pv columns, lichess_evals_at + full_pv_completed_at, eval_jobs queue/lease table, D-117-10 backfill (EVAL-04, EVAL-06, QUEUE-01, QUEUE-06)
    - [x] 117-02-PLAN.md — Tiered SKIP-LOCKED queue service: round-robin + TC-weighted pick, lease/report, tier-3 derived, guest exclusion, superuser tier-1 trigger (QUEUE-01/02/03/05/06/08)
    - [x] 117-03-PLAN.md — Drain integration: evaluate_nodes_with_pv, best_move threading + WR-02 repoint to lichess_evals_at, classify+oracle hook, queue-lease pick, tier-1 fan-out (EVAL-04, EVAL-06, QUEUE-03)
- [x] **Phase 117.1: Flaw-Eval Convention Fix (INSERTED, SEED-044)** - HIGH-priority off-by-one: engine drain stores `eval_cp` pre-move, classifier assumes post-move → wrong flaw stats for all chess.com (engine-evaluated) games. Standardize on post-move storage everywhere + dedup one-ply-shift rework + clean-slate re-eval
  - **Plans:** 2 plans — EXECUTED + full local gate green. DEPLOYED to prod 2026-06-14 via release #190 (`e97bcf54`).
  - Plans:
    - [x] 117.1-01-PLAN.md — Post-move write convention (`_post_move_eval` single shift site) + terminal eval donor + dedup one-ply self-join + classifier comment cleanup + drain/regression tests (EVALFIX-01/02/03/05)
    - [x] 117.1-02-PLAN.md — Clean-slate data migration: NULL engine eval/best_move/pv, clear markers, delete engine `game_flaws`, TRUNCATE `eval_jobs`; preserve all lichess data; no-op downgrade + migration test (EVALFIX-04/05)
- [x] **Phase 117.2: Wipe Eval-Only Engine Residue (INSERTED, SEED-044 follow-up)** - Data-only migration: NULLs `eval_cp`/`eval_mate`/`best_move`/`pv` for 3,497 engine games (3 users) carrying dense evals from a pre-Phase-117 eval-only pass with no `best_move`/flaw classification/`full_evals_completed_at` marker. They showed in the Library as analyzed-with-no-flaws (≥90%-coverage "analyzed" gate); the wipe drops them from the analyzed set until the tier-3 drain re-materializes them properly. Gated on `lichess_evals_at IS NULL` — lichess never touched.
  - **Plans:** 1 data migration (no PLAN.md; committed follow-up) — DEPLOYED to prod 2026-06-14 via release #191 (`8359935b`). Verified: residue 3497→0; lichess_total 39876 unchanged, lichess_flawed_no_marker 9655 unchanged (guards held).
- [ ] **Phase 118: Demand UX + Auto-Enqueue** - Automatic window enqueue on import/activity + explicit "analyze more" affordance + coverage indicators + in-flight status
- [ ] **Phase 119: Eval-drain coverage (SEED-045, SEED-046)** - Bounded-retry hole-filling (don't stamp full_evals_completed_at while non-terminal/non-mate holes remain; cap at MAX_EVAL_ATTEMPTS) + recency-weighted tier-3 lottery (replace winner-take-all last_activity ordering with Efraimidis–Spirakis user-weighted sampling + PV-backfill residual tier)

<details>
<summary>✅ v1.25 Flaw-Stats Opponent Comparison (Phases 113–115, incl. 114.1) — SHIPPED 2026-06-12</summary>

Reworked the Library flaw-stats surface from a self-only descriptive panel into an actionable you-vs-opponent comparison, in four phases: opponent-flaw materialization with a query-time player/opponent split (113), the benchmark §5 flaw-delta delta-IQR zones with Cohen's-d collapse verdicts (114), an inserted `move_count`→exact `ply_count` swap for an exact per-game denominator (114.1, SEED-041 §9), and the comparison surface — a unified per-100-moves paired-delta endpoint feeding a uniform 15-bullet `MiniBulletChart` grid (115). The SEED-040 count-rate/proportion family split was superseded by one unified estimator (FLAWCMP-02 voided); the `is_opponent` column was voided in favour of a query-time helper (FLAWX-03 voided). Deferred to v2: tactic-motif families (SEED-039) and coverage raising (SEED-012).

- [x] Phase 113: Opponent-Flaw Materialization (3/3 plans) — both-mover `game_flaws` + query-time `is_opponent_expr` split, reader gating, dev/benchmark backfill — completed 2026-06-10
- [x] Phase 114: Benchmark Flaw-Delta Zone Computation (1/1 plan) — §5 chapter, 15-metric Q1/Q3 + ELO/TC marginals + Cohen's-d verdicts — completed 2026-06-10
- [x] Phase 114.1: Replace `move_count` with exact `ply_count` (INSERTED, SEED-041 §9) (2/2 plans) — single migration + import-path + all readers; frontend cards + chapter5 §5 follow-on — completed 2026-06-10
- [x] Phase 115: You-vs-Opponent Comparison API + Bullet-Grid UI (2/2 plans) — unified per-100-moves paired-delta endpoint + family-grouped 15-bullet grid, tooltips, sample gate — completed 2026-06-11

See [milestones/v1.25-ROADMAP.md](milestones/v1.25-ROADMAP.md) for full details.

</details>

<details>
<summary>✅ v1.24 Library Page (Phases 104–112) — SHIPPED 2026-06-09</summary>

SEED-036's analysis half, built in nine phases: the Library shell + Import/Overview migration (104), the on-the-fly mistake-detection kernel (105), the Games-surface backend (106), the Games subtab UI (107), the Flaws subtab + `game_flaws` materialization + cross-tab Flaw filter (108), per-card expected-score eval charts (109), the flaw-tag taxonomy overhaul (110), a filter-UX polish pass (111), and the Flaws-card rework + single-game modal (112). The deferred SEED-036 surfaces (Analysis detail viewer, best-move endpoint) stay specified in `.planning/seeds/SEED-036-library-page-milestone.md`.

- [x] Phase 104: Library Page Shell + Import & Overview Subtab Migration (2/2 plans) — completed 2026-06-05
- [x] Phase 105: Mistake-Detection + Classification + Tagging Service on-the-fly (2/2 plans) — completed 2026-06-05
- [x] Phase 106: Games-Surface Backend — Mistake Filter, Per-Game Counts & Stats Aggregates (3/3 plans) — completed 2026-06-05
- [x] Phase 107: Games Subtab Frontend — Card Archive, Filters & Flaw-Stats Panel (7/7 plans) — completed 2026-06-06
- [x] Phase 108: Flaws Subtab — game_flaws Materialization, Per-Flaw Endpoint, Cross-Tab Flaw Filter & Miniboard List (8/8 plans) — completed 2026-06-06
- [x] Phase 109: Per-Card Expected-Score Eval Chart (Games subtab) (4/4 plans) — completed 2026-06-07
- [x] Phase 110: Flaw-Tag Taxonomy Overhaul — Rename, Impact-Family Rebuild, Tooltip Restore & Active-Filter Highlight (7/7 plans) — completed 2026-06-08
- [x] Phase 111: Library UI Polish — staged Apply-only filter model (shipped via direct commits; no plan artifacts) — completed 2026-06-09
- [x] Phase 112: Flaws Subtab Card Rework — 2-up Card grid + View-game modal (4/4 plans) — completed 2026-06-09

See [milestones/v1.24-ROADMAP.md](milestones/v1.24-ROADMAP.md) for full details.

</details>

*Earlier milestones below. v1.23 (Phases 102, 103) shipped 2026-06-03 — archived to [milestones/v1.23-ROADMAP.md](milestones/v1.23-ROADMAP.md); see the collapsed block. v1.22 (Phases 100, 101) shipped 2026-05-31 — archived to [milestones/v1.22-ROADMAP.md](milestones/v1.22-ROADMAP.md). v1.21 (Phases 97, 98, 99, 99.1) shipped 2026-05-31 — archived to [milestones/v1.21-ROADMAP.md](milestones/v1.21-ROADMAP.md).*

<details>
<summary>✅ v1.23 LLM Endgame-Insights Statistical-Reasoning Rework (Phases 102, 103) — SHIPPED 2026-06-03</summary>

- [x] Phase 102: Endgame LLM Statistical-Reasoning Rework (3/3 plans) — cohort-framed percentile annotations + time-pressure narration (Score Gap by Remaining Time / Clock Gap / Net Flag Rate) wired into the endgame-insights payload, prompt taught to reason over the v1.17–v1.21 metric set under the zone gate (p-values + CI bounds OUT), relaxed overview cap, vocabulary audit vs concepts accordion + tooltip popovers, `endgame_v35` → `endgame_v43`; HUMAN-UAT (LLM-07) signed off across short-history / sparse-section / full-history prod users — completed 2026-06-02 (LLM-01..07)
- [x] Phase 103: Endgame report LLM prompt refinements (unplanned follow-on) — three GM-feedback recommendation-quality fixes (decision-speed time-trouble advice, no fabricated mechanism, no named theoretical positions at any Elo), GM Noël Studer study link in the Recommendations card, prompt condensed ~35%, `endgame_v44` — completed 2026-06-03

See [milestones/v1.23-ROADMAP.md](milestones/v1.23-ROADMAP.md) for full details.

</details>

<details>
<summary>✅ v1.22 Maintenance — Test Isolation & Frontend Major Upgrades (Phases 100, 101) — SHIPPED 2026-05-31</summary>

- [x] Phase 100: Isolated Test DB Per Run (2/2 plans) — per-run/per-xdist-worker DB cloned from a migrated template; TRUNCATE retired; `pytest -n auto` green at 18.56s vs 40.29s serial (2.2x); concurrent-run isolation verified (SEED-031) — completed 2026-05-31
- [x] Phase 101: Frontend Major Dependency Upgrades (1/1 plan) — 11 frontend deps to latest major across 6 bisectable atomic clusters (lucide → Vite 8 → jsdom 29 → eslint 10 → TypeScript 6 → recharts 3); recharts 3 visual UAT (one regression fixed); peer-compat clean (SEED-032) — completed 2026-05-31

See [milestones/v1.22-ROADMAP.md](milestones/v1.22-ROADMAP.md) for full details.

</details>

<details>
<summary>✅ v1.21 Time-Control-Aware Endgame Metrics (Phases 97, 98, 99, 99.1) — SHIPPED 2026-05-31</summary>

- [x] Phase 97: Endgame Metrics by Time Control (4/4 plans, PR #160) — completed 2026-05-29
- [x] Phase 98: Per-TC Collapsible Endgame Type Cards (2/2 plans, PR #163; release #164) — completed 2026-05-30
- [x] Phase 99: Percentile Badges for Conversion, Parity, and Recovery (5/5 plans, PR #167) — completed 2026-05-30
- [x] Phase 99.1: Move Cohort CDF Out of Source into a DB Table (4/4 plans, PR #168; INSERTED) — completed 2026-05-31

See [milestones/v1.21-ROADMAP.md](milestones/v1.21-ROADMAP.md) for full details.

</details>

<details>
<summary>✅ v1.20 Import Pipeline Hardening Follow-Up and Readiness (Phases 95-96) — SHIPPED 2026-05-29</summary>

- [x] Phase 95: asyncpg COPY for `bulk_insert_positions` (2/2 plans, PRs #148/#149) — completed 2026-05-27
- [x] Phase 96: Import Readiness Gate (3/3 plans, PR #151) — completed 2026-05-28

See [milestones/v1.20-ROADMAP.md](milestones/v1.20-ROADMAP.md) for full details.

</details>

<details>
<summary>✅ v1.18 Import Pipeline Hardening (Phases 90-92) — SHIPPED 2026-05-22</summary>

- [x] Phase 90: Import Pipeline Memory Leak Fix + Resilience (3/3 plans, PR #130) — completed 2026-05-20
- [x] Phase 91: Two-lane import — defer Stockfish eval to in-process cold drain (8/8 plans, PR #137) — completed 2026-05-21
- [x] Phase 92: Custom date range filter (from/to dates replace closed Recency union) (6/6 plans, PR #138) — completed 2026-05-22

</details>

<details>
<summary>✅ v1.17 Endgame Stats Card Redesign (Phases 84-88.4) — SHIPPED 2026-05-19</summary>

- [x] Phase 84: Data plumbing — mirror-rate audit (1/1 plan, PR #95) — completed 2026-05-13
- [x] Phase 85: Section 1 — Games with vs without Endgame / 3-card composite (5/5 plans) — shipped 2026-05-14
- [x] Phase 85.1: Hypothesis tests + 95% CIs for Endgame Score Differences (4/4 plans; INSERTED) — shipped 2026-05-14
- [x] Phase 86: Section 2 — Endgame Metrics 4-card layout (5/5 plans) — shipped 2026-05-14
- [x] Phase 87: Section 3 — Per-type Endgame Type Breakdown cards (3/3 plans) — shipped 2026-05-15
- [x] Phase 87.1: Per-span ΔES metric for endgame types (4/4 plans, PR #97; INSERTED) — completed 2026-05-15
- [x] Phase 87.2: Section 2 — eval-based ΔES Score Gap bullets (4/4 plans, PR #98; INSERTED) — completed 2026-05-16
- [~] Phase 87.3: Endgame Skill v2 — Conv+Parity percentile composite (INSERTED) — **superseded** by Phase 87.4 (PR #102)
- [x] Phase 87.4: Drop Endgame Skill — Conversion ELO timeline (3/3 plans, PR #104; INSERTED) — completed 2026-05-16
- [x] Phase 87.5: Rebuild Endgame ELO on Endgame Score Gap (3/3 plans, PR #105; INSERTED) — completed 2026-05-17
- [x] Phase 87.6: Endgame ELO via logistic stretch around Actual ELO (3/3 plans, PR #106; INSERTED) — completed 2026-05-18
- [x] Phase 88: Time Pressure stats rework with hypothesis tests + CIs (15/15 plans, PR #107; INSERTED) — completed 2026-05-18
- [x] Phase 88.3: Endgame Stats viz refinements — inactivity-gap annotations + Overall Performance card (4/4 plans, PR #108; INSERTED) — completed 2026-05-18
- [x] Phase 88.4: Time Pressure card layout refactor (3/3 plans, PR #109; INSERTED) — completed 2026-05-19
- [→] Phase 89: Polish — popovers, gating decisions, automation rules, 375px parity — **dropped from scope** 2026-05-19 (not needed)

See [milestones/v1.17-ROADMAP.md](milestones/v1.17-ROADMAP.md) for full details.

</details>

<details>
<summary>✅ v1.16 Stockfish Eval Analyses (Phases 80, 80.1, 81, 82, 83) — SHIPPED 2026-05-11</summary>

- [x] Phase 80: Opening stats: middlegame-entry eval and clock-diff columns (6/6 plans) — completed 2026-05-05 (PR #80)
- [x] Phase 80.1: Include transpositions in Move Explorer and Opening Insights stats (4/4 plans) — completed 2026-05-07 (PR #82)
- [x] Phase 81: Endgame Start vs End — twin-tile section above the WDL table (5/5 plans) — completed 2026-05-09 (PR #85)
- [x] Phase 82: LLM prompt awareness of Endgame Start vs End metrics (4/4 plans) — completed 2026-05-10 (PR #86)
- [x] Phase 83: Stockfish-baseline predicted endgame score (5/5 plans) — completed 2026-05-11 (PR #88)

See [milestones/v1.16-ROADMAP.md](milestones/v1.16-ROADMAP.md) for full details.

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

<details>
<summary>✅ v1.15 Eval-Based Endgame Classification (Phases 78, 79) — SHIPPED 2026-05-03</summary>

- [x] Phase 78: Stockfish-Eval Cutover for Endgame Classification (6/6 plans) — completed 2026-05-03 (PR #78) — ENG-01..03, FILL-01..04, IMP-01..02, REFAC-01..05, VAL-02 (VAL-01 rescinded)
- [x] Phase 79: Position-phase classifier and middlegame eval (4/4 plans) — completed 2026-05-03 (PR #78) — CLASS-01..02, SCHEMA-01..02, PHASE-IMP-01..02, PHASE-FILL-01..03, PHASE-VAL-02..03, PHASE-INV-01 (PHASE-VAL-01 rescinded)

See [milestones/v1.15-ROADMAP.md](milestones/v1.15-ROADMAP.md) for full details.

</details>

## Phase Details

### Phase 116: All-Ply Engine Core

**Goal**: The eval drain analyzes every ply of queued games at Lichess-parity depth, storing results directly in `game_positions.eval_cp/eval_mate` with dedup and a distinct full-analysis completion marker, and the worker pool's memory footprint is explicitly bounded before the pool size is raised
**Depends on**: Nothing (extends existing `eval_drain.py` + `engine.py`)
**Requirements**: EVAL-01, EVAL-02, EVAL-03, EVAL-05, QUEUE-07
**Success Criteria** (what must be TRUE):

  1. A queued game's `game_positions` rows have `eval_cp`/`eval_mate` populated on every ply (terminal game-over positions excluded — no book-skip, so eval charts have no opening gap), and plies ≤ 20 skip the engine call when a matching `full_hash` already has a server eval (the dedup that makes the shared opening region cheap)
  2. The search budget is exactly 1,000,000 nodes, NNUE, multiPV=1 per worker call (Lichess fishnet parity), replacing the former depth-15 convention for games processed by this pipeline
  3. A game that completes full-ply analysis carries a completion marker that is distinct from `evals_completed_at` (the existing entry-ply marker), so coverage queries can report each tier independently
  4. The combined memory footprint of `STOCKFISH_POOL_SIZE` workers at the new budget, an active import, and Postgres fits inside the backend container's 4g limit with documented headroom

**Plans**: TBD

### Phase 117: Priority Queue + Flaw Integration

**Goal**: A tiered priority queue replaces the current LIFO id-DESC game pick, serving explicit requests first, then automatic windows, then idle backlog, with round-robin per-user fairness, tier-1 fan-out across the full worker pool, and newly analyzed games flowing automatically into `game_flaws`
**Depends on**: Phase 116
**Requirements**: EVAL-04, EVAL-06, QUEUE-01, QUEUE-02, QUEUE-03, QUEUE-05, QUEUE-06, QUEUE-08
**Success Criteria** (what must be TRUE):

  1. The drain selects the next game via a tiered pick: any tier-1 job takes precedence over tier-2, which takes precedence over the tier-3 idle backlog; within a tier, the next game comes from the user who has waited longest (round-robin); within a user, the most recent unanalyzed game goes first
  2. A tier-1 single-game request fans all of that game's positions across the entire worker pool and completes in approximately 10 seconds wall-clock on an otherwise-idle pool (Lichess game-review UX reference)
  3. Idle workers pick from the tier-3 backlog so no core sits unused when tier-1 and tier-2 queues are empty; full-DB coverage accrues over time
  4. Workers interact with the queue through a lease-then-report contract (claim job → evaluate positions → post evals), such that adding a second worker type (e.g. browser-based) requires no queue redesign
  5. The PV string is persisted in `game_positions` for plies adjacent to a flaw (so SEED-039 needs no second engine pass), and discarded for all other plies
  6. Once a game's positions are fully evaluated, `classify_game_flaws` runs automatically and `game_flaws` rows appear for that game without any user action (import itself stays fast — the hot lane and its quick entry-ply pass are untouched; full evals + flaws arrive progressively after import)
  7. Guest accounts (`users.is_guest`) are excluded from every tier — no guest game is ever enqueued or drained; full-game analysis requires a real account (inactive-guest games are cleanup candidates, so analyzing them wastes compute)

**Proposed amendment to Success Criterion #5** (2026-06-13, pending `/gsd-discuss-phase 117`): split PV persistence into two artifacts instead of one, so we get an "engine's best move per position" step-through display nearly for free.

  - **`best_move` (PV[0]) for *every* evaluated position** — enables showing the engine's preferred move when stepping through any game ply. It is a position property (keyed on the pre-move `full_hash`), so the existing opening-region dedup-transplant (`eval_drain._fetch_dedup_evals`, `ply ≤ DEDUP_MAX_PLY=20`, WR-02 gate) carries it for free alongside `eval_cp`; `ply > 20` stored per-row. Storage ≈ +80 MB (int2-encoded `from·64+to+promo`) to +240 MB (UCI text) on the 44.4M-row `game_positions` (~+1–4% of the 5.5 GB data; prod db-report 2026-06-12). **Zero extra engine compute** (PV falls out of the search that already produces `eval_cp`). Display-only → fetched by `game_id` (already indexed), no new index.
  - **Full PV string only for plies adjacent to a flaw** (the original #5 intent, for SEED-039 motif continuations). REJECT full-PV-for-all: ≈ 5 GB, roughly doubles `game_positions` data and bloats the import/replay bulk-fetch hot path (the heaviest query class per db-report).
  - Pipeline delta: capture `info["pv"][0]` from the existing search; thread `best_move` through `_fetch_dedup_evals` (return `(eval_cp, eval_mate, best_move)`) and the write path. Open sub-questions: int2 encoding vs UCI text; opening plies show book-region best moves too (no gap); top-1 only (MultiPV is a separate, more expensive search — out of scope).

**Plans**: 3 plans (3 waves)

- [x] 117-01-PLAN.md — Migration + schema: 4 nullable columns (best_move, pv, lichess_evals_at, full_pv_completed_at), eval_jobs queue/lease table + indexes, D-117-10 backfill, ORM models (wave 1)
- [x] 117-02-PLAN.md — Tiered priority queue service: SKIP-LOCKED claim (tier-1>2>3, round-robin, TC-weighted), lease/report contract, tier-3 derived pick, guest exclusion, tier-1 enqueue + superuser admin trigger (wave 2)
- [x] 117-03-PLAN.md — Drain integration: evaluate_nodes_with_pv (best_move + flaw PV, zero extra compute), WR-02 repoint to lichess_evals_at, classify_game_flaws hook + oracle counts, completion markers, queue lease wiring, tier-1 fan-out (wave 3)

### Phase 117.1: Flaw-Eval Convention Fix (INSERTED, SEED-044)

**Goal**: A single eval-storage convention (post-move) holds across all sources, so `classify_game_flaws` produces correct flaw stats for chess.com (engine-evaluated) games — not just lichess `%eval` games. Today the engine drain stores `eval_cp` as the eval of the pre-push position (eval BEFORE the move) while the classifier assumes eval AFTER the move; the result is missing or misattributed flaws for the majority of the dataset (every chess.com game). The fix canonicalizes storage to post-move, reworks the opening-region dedup transplant to recover position evals correctly under the new convention, and re-evaluates affected games from a clean slate.
**Depends on**: Phase 117
**Requirements**: EVALFIX-01, EVALFIX-02, EVALFIX-03, EVALFIX-04, EVALFIX-05
**Success Criteria** (what must be TRUE):

  1. `game_positions.eval_cp`/`eval_mate` store the eval of the position AFTER the move at every row, for both engine-drained and lichess games — one convention, no per-source branch in the classifier
  2. The drain evaluates the terminal position so the last move of every game has an "after" eval and is flaw-assessable; `best_move`/`pv` stay keyed to the decision ply (the move-played row)
  3. The opening-region dedup transplant recovers a position's eval correctly under post-move storage (one-ply shift on the donor read); `best_move` transplant is unchanged and the lines 182-191 convention comment is rewritten to document post-move
  4. A migration NULLs `eval_cp`/`eval_mate`/`best_move`/`pv` and clears `full_evals_completed_at`/`full_pv_completed_at` for engine games (`lichess_evals_at IS NULL`) and deletes their `game_flaws` — clean slate; the background drain re-materializes them under the new convention
  5. Regression fixtures (engine games 1420780, 1073118; lichess game 640092) all produce coherent mistake/blunder detection through the unified post-move path; flaw-PV coverage is re-verified after re-eval (the off-by-one is the suspected cause of the ~32% coverage TODO)

**Plans**: 2 plans

- [ ] 117.1-01-PLAN.md — Post-move write convention + terminal eval + dedup one-ply shift; classifier comment cleanup; drain/dedup tests + 3 regression fixtures (wave 1)
- [ ] 117.1-02-PLAN.md — Clean-slate data migration (NULL engine eval/flaw data, truncate eval_jobs, preserve lichess) + migration test (wave 1)

### Phase 118: Demand UX + Auto-Enqueue

**Goal**: Users' recent games are automatically queued for analysis on import completion and on activity, with a visible explicit "analyze more" affordance showing real-time progress, coverage indicators on eval-dependent surfaces, and live in-flight status — all without requiring the user to initiate or monitor analysis manually
**Depends on**: Phase 117
**Requirements**: QUEUE-04, EVUX-01, EVUX-02, EVUX-03
**Success Criteria** (what must be TRUE):

  1. After a game import completes (or on first activity), the user's most recent ~200 unanalyzed games are automatically enqueued at tier 2 without any user action, and Library flaw features light up progressively as analysis finishes
  2. A user can explicitly trigger "analyze more games" and see a progress indicator (games analyzed / games queued) that updates without a full page refresh — reusing the import-job mental model
  3. Eval-dependent surfaces (Library Flaw-Stats panel, comparison grid) display "based on N of M analyzed games" and a CTA to analyze more when coverage is below a useful threshold, rather than silently showing data over a small analyzed subset
  4. A user can see whether their games are currently queued or being analyzed (in-flight status) without refreshing the page blindly
  5. Guest users see account promotion presented as the unlock for full-game analysis (QUEUE-08's UX face) instead of analyze affordances that would silently do nothing

**Plans**: 3 plans
**Wave 1**

- [x] 118-01-PLAN.md — Backend foundation: enqueue_tier2_window + coverage/in-flight repo counts (is_analyzed fix) + EvalCoverageResponse extension + ix_eval_jobs_user_active migration + tier-3 ORDER BY refinement + the two auto-enqueue triggers

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 118-02-PLAN.md — API surface: POST /imports/eval/tier1/{game_id}, POST /imports/eval/tier2 (disabled-until-drained gate), extended GET /imports/eval-coverage

**Wave 3** *(blocked on Wave 2 completion)*

- [x] 118-03-PLAN.md — Frontend: useEvalCoverage + useEnqueueGame mutations, real "N of M analyzed" coverage copy + CTA, per-game/bulk analyze affordances, in-flight states, guest promotion across the Library flaw surfaces

**UI hint**: yes

### Phase 119: Eval-drain coverage: bounded-retry hole-filling + recency-weighted tier-3 lottery (SEED-045, SEED-046)

**Goal:** [To be planned]
**Requirements**: TBD
**Depends on:** Phase 118
**Plans:** 0 plans
**Scope (from seeds):**

  - **SEED-045 — bounded-retry hole-filling:** `eval_drain.py::_mark_full_evals_completed` stamps `full_evals_completed_at` unconditionally (D-116-07), so a game can be marked "fully analyzed" with genuine mid-game eval holes. Stop stamping while non-terminal, non-mate holes remain; re-pick up to `MAX_EVAL_ATTEMPTS` (~3) via a new `games.full_eval_attempts` SmallInteger; after the cap, stamp anyway + one aggregated Sentry event. Hole = `eval_cp IS NULL AND eval_mate IS NULL AND ply is not the terminal game-over ply`. Backfill decision for already-stamped-with-holes games (extend `scripts/backfill_eval.py` or a re-enqueue sweep).
  - **SEED-046 — recency-weighted tier-3 lottery:** replace `_claim_tier3_derived`'s winner-take-all `last_activity DESC` top key with an Efraimidis–Spirakis user-weighted lottery (`ORDER BY -ln(random()) / weight LIMIT 1` over distinct `needs_engine_full_evals` users; weight = `exp(-Δt/τ)` + floor), then pick that user's best game by the existing secondary order. PV-backfill-only games become a residual fallback tier. One partial-index migration; verify DISTINCT-users + ES pick stays sub-100ms at prod scale.
  - **Timing caveat:** SEED-046's own trigger asks to tune τ/floor against prod `last_activity` distributions *after* Phase 118 ships. Keep τ/floor as tunable constants and include a prod-tuning task rather than hardcoding.
  - **Additional UX requirement (not seed-derived):** the `EvalCoverageBadge` CPU icon (`frontend/src/components/library/EvalCoverageBadge.tsx:81`) must pulse (`animate-pulse`) while analysis is incomplete and go static at 100%, signalling progress is being made. NOTE the sibling surfaces already pulse (`EvalCoverageHeader.tsx:23`, `EvalCpuPlaceholder.tsx:22`) — this badge is the only one that doesn't, so the work is one conditional className + a test. **Design fork to resolve at discuss/plan:** pulse on `analyzedN < totalN` (literal "not all analyzed") vs only when `inFlightCount > 0` (jobs actually running for this user). The in-flight gate is more honest under SEED-046's lottery — a dormant backlog user usually has zero in-flight jobs, so pulsing-on-incomplete would falsely imply active progress.

Plans:

- [ ] TBD (run /gsd-plan-phase 119 to break down)

## Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1-10. v1.0 phases | 36/36 | Complete | 2024-03-15 |
| 11-16. v1.1 phases | 14/14 | Complete | 2024-03-18 |
| 17-19. v1.2 phases | 5/5 | Complete | 2024-03-21 |
| 20-23. v1.3 phases | 10/10 | Complete | 2026-03-22 |
| 24. Web Analytics | 2/2 | Complete | 2026-03-22 |
| 26-33. v1.5 phases | 18/19 | Complete (28-03 deferred) | 2026-03-28 |
| 34-39. v1.6 phases | 11/11 | Complete | 2026-03-30 |
| 40-43. v1.7 phases | 11/11 | Complete | 2026-04-03 |
| 44-47. v1.8 phases | N/A | Complete | 2026-04-06 |
| 49-51. v1.9 phases | 7/7 | Complete | 2026-04-10 |
| 48, 52-62. v1.10 phases | 28/28 | Complete | 2026-04-19 |
| 63-68. v1.11 phases | 23/23 | Complete (Phase 67 descoped) | 2026-04-24 |
| 69. Benchmark DB Infra & Ingestion | 6/6 | Complete (follow-on phases → SEED-006) | 2026-04-26 |
| 70-71.1. v1.13 phases | 14/14 | Complete (Phases 72/73/74 descoped) | 2026-04-27 |
| 75-77. v1.14 phases | 16/16 | Complete (INSIGHT-UI-04 descoped) | 2026-04-29 |
| 78-79. v1.15 phases | 10/10 | Complete (VAL-01 / PHASE-VAL-01 rescinded) | 2026-05-03 |
| 80-83. v1.16 phases | 24/24 | Complete | 2026-05-11 |
| 84-88.4. v1.17 phases | ~54/~54 | Complete (89 dropped, 87.3 superseded) | 2026-05-19 |
| 90-92. v1.18 phases | 17/17 | Complete | 2026-05-22 |
| 93. Global Percentile Benchmark Artifact | 2/2 | Complete | 2026-05-22 |
| 94. Backend & Frontend Percentile Annotations | 3/3 | Complete | 2026-05-23 |
| 95-96. v1.20 phases | 5/5 | Complete | 2026-05-29 |
| 97-99.1. v1.21 phases | 15/15 | Complete (99.1 INSERTED) | 2026-05-31 |
| 100-101. v1.22 phases | 3/3 | Complete | 2026-05-31 |
| 102-103. v1.23 phases | 3/3 | Complete (103 unplanned follow-on) | 2026-06-03 |
| 104-112. v1.24 phases | 37/37 | Complete (111 shipped direct, no plan artifacts) | 2026-06-09 |
| 113. Opponent-Flaw Materialization | 3/3 | Complete | 2026-06-10 |
| 114. Benchmark Flaw-Delta Zone Computation | 1/1 | Complete | 2026-06-10 |
| 114.1. Replace move_count with exact ply_count (INSERTED) | 2/2 | Complete | 2026-06-10 |
| 115. You-vs-Opponent Comparison API + Bullet-Grid UI | 2/2 | Complete | 2026-06-11 |
| 116. All-Ply Engine Core | 3/3 | Complete (deployed #190) | 2026-06-14 |
| 117. Priority Queue + Flaw Integration | 3/3 | Complete (deployed #190) | 2026-06-14 |
| 117.1. Flaw-Eval Convention Fix (INSERTED, SEED-044) | 2/2 | Complete (deployed #190) | 2026-06-14 |
| 117.2. Wipe Eval-Only Engine Residue (INSERTED, SEED-044) | 1/1 | Complete (deployed #191) | 2026-06-14 |
| 118. Demand UX + Auto-Enqueue | 3/3 | Complete (verified; not yet deployed) | 2026-06-14 |
| **119. Eval-drain coverage (SEED-045, SEED-046)** | **0/TBD** | **Not started** | **-** |

## Backlog

### Phase 999.1: Password Reset (BACKLOG)

**Goal:** Users can recover account access when they forget their password — request reset link, receive email, set new password
**Requirements:** TBD
**Plans:** 3/3 plans complete

Plans:

- [ ] TBD (promote with /gsd:review-backlog when ready)

### Phase 999.4: Position-Based Most Played Openings via game_positions (BACKLOG)

**Goal:** Redesign "Most Played Openings" to count how many games *passed through* each opening position (via `game_positions` Zobrist hash matching) instead of counting final opening name classifications from chess.com/lichess. Currently "1. e4" shows ~75 games (only games *classified* as "King's Pawn Game") while obscure specific lines rank higher. Position-based counting would show all ~2000+ games that played 1. e4, consistent with FlawChess's core Zobrist hash architecture. Requires JOIN from `openings` reference table to `game_positions` on FEN or precomputed hash, then `COUNT(DISTINCT game_id)`.
**Requirements:** TBD
**Plans:** 0 plans

Plans:

- [ ] TBD (promote with /gsd:review-backlog when ready)

### Phase 999.5: Hybrid Stockfish Eval for Conversion/Recovery (BACKLOG)

**Goal:** Use Stockfish eval (`eval_cp`) as the advantage/disadvantage signal for conversion/recovery classification when available, falling back to material imbalance + 4-ply persistence for games without eval. Stockfish eval is the gold standard (no persistence filter needed since eval handles transient trades natively). Currently only ~15% of Lichess games have eval data and chess.com has 0%, but this improves automatically as more games get server-analyzed. Validated in `docs/endgame-conversion-recovery-analysis.md`: persistence closes 50-70% of the gap to Stockfish for pawn/mixed endgames, but a hybrid approach would eliminate the remaining 5-8pp offset for eval-available games.
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

*Phase 999.7 (LLM Endgame-Insights Statistical-Reasoning Rework) promoted to active Phase 102 (v1.23) on 2026-06-01 via `/gsd-explore`; shipped 2026-06-03.*

*Phase 103 (Endgame report LLM prompt refinements) shipped 2026-06-03 as an unplanned follow-on under v1.23 — see the collapsed v1.23 block above and [milestones/v1.23-ROADMAP.md](milestones/v1.23-ROADMAP.md).*
