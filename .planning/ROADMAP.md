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
- 🚧 **v1.24 Library Page** — Phases 104, 105, 106 (in progress)

## Phases

### 🚧 v1.24 Library Page (Phases 104–106) — IN PROGRESS

SEED-036, built in stages. **Phase 104** introduced the **Library** page (top-level nav + URL-routed subtabs, with Import and Overview folded in) — a pure frontend restructure. **Phase 105** extends into the analysis backend: the on-the-fly mistake-detection + classification + tagging service the analysis surfaces consume. **Phase 106** builds the Games-surface backend on top of it — the boolean mistake-type filter, per-game counts/card-chips, and the stats-panel aggregates the Games subtab consumes. The remaining surfaces (Games subtab UI, Flaws subtab, Analysis detail viewer, best-move endpoint) stay specified in `.planning/seeds/SEED-036-library-page-milestone.md` and will be roadmapped as subsequent phases.

- [x] **Phase 104: Library Page Shell + Import & Overview Subtab Migration** — new `/library` route with deep-linkable `<Tabs variant="brand">` subtabs; migrate `/import` → `/library/import` and `/overview` → `/library/overview` (each its own tsx, with redirects); top-level nav drops to Library · Openings · Endgames (+ Admin); `totalGames === 0` dot moves to the Library nav item; state-dependent landing (zero games → Import, has games → Overview); subtab-level gating (Library + both subtabs always open); mobile parity + browser-automation conventions (LIB-01..09) (completed 2026-06-05)
- [x] **Phase 105: Mistake-Detection + Classification + Tagging Service (on-the-fly)** — server-side `mistakes` service derives every flaw in a Lichess-analyzed game on-the-fly from stored per-ply `eval_cp`/`eval_mate` — severity (Lichess-aligned 0.05/0.10/0.15 expected-score-drop thresholds) + eight attribution tags (miss, unpunished, from-winning, result-changing, time-pressure, hasty, knowledge-gap, phase) — emitting typed per-flaw objects for the Games/Flaws/Analysis surfaces and SEED-037 Train; no materialization, no schema change, no UI (LIBG-02, LIBG-06, LIBG-07) (completed 2026-06-05)
- [ ] **Phase 106: Games-Surface Backend — Mistake Filter, Per-Game Counts & Stats Aggregates (on-the-fly)** — two server-side endpoints the Games subtab consumes, both on-the-fly via a SQL window-scan + Python tagging that reuses Phase 105's kernel (no materialization, no schema change): (a) games-list — `apply_game_filters` extended with a boolean mistake-type `EXISTS` over the per-ply ES-drop (severity thresholds bound params), each game carrying B/M/I counts + aggregated/deduped card tag-chips; (b) stats-panel aggregates over the filtered analyzed-only set — per-severity counts/rates (normalized), tag distribution (tempo split, result-changing rate, phase histogram), trend-over-time, and the explicit `% analyzed` (≥90%-coverage) denominator with N (LIBG-08, LIBG-09)

#### Phase 104: Library Page Shell + Import & Overview Subtab Migration

**Goal**: Users have a single top-level **Library** page that hosts the existing Import and Overview workflows as deep-linkable subtabs, with all old entry points (nav items, `/import`, `/overview`, the gameless-user redirect, the zero-games notification dot) seamlessly repointed at it.
**Depends on**: Nothing new (builds on the existing Openings/Endgames URL-routed `<Tabs variant="brand">` subtab pattern and the existing Import.tsx / GlobalStats.tsx pages).
**Requirements**: LIB-01, LIB-02, LIB-03, LIB-04, LIB-05, LIB-06, LIB-07, LIB-08, LIB-09
**Success Criteria** (what must be TRUE):

  1. Top-level navigation shows **Library · Openings · Endgames** (plus superuser-only Admin); Import and Overview are gone as standalone nav items, and the `totalGames === 0` notification dot now appears on the **Library** nav item (LIB-01, LIB-05, LIB-06).
  2. Visiting the Library page lands the user on **Import** when they have zero imported games and on **Overview** when they have games; Home's gameless-user redirect sends them to `/library/import`. The Library page and both subtabs are always reachable (never import-gated) (LIB-07, LIB-08).
  3. Switching between the **Import** and **Overview** subtabs updates the URL to `/library/import` / `/library/overview` and those URLs are directly deep-linkable, using the same Openings-style `<Tabs variant="brand">` pattern, with each subtab implemented as its own `.tsx` file (LIB-02).
  4. Visiting the old `/import` URL redirects to `/library/import` with the full Import workflow intact, and visiting `/overview` redirects to `/library/overview` with the full Overview dashboard intact (LIB-03, LIB-04).
  5. The Library page, its subtab control, and both migrated subtabs render and function correctly on mobile, with `data-testid` / ARIA / semantic-HTML conventions present on all new interactive elements and containers (LIB-09).

**Plans**: 2 plansPlans:
**Wave 1**

- [x] 104-01-PLAN.md — Create the pages/library/ shell (LibraryPage) + Import/Overview subtab wrappers, mirroring the Endgames two-subtab Tabs pattern

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 104-02-PLAN.md — Rewire App.tsx nav/routes/redirects/notification-dot at the Library shell and sweep internal /import links to /library/import

**UI hint**: yes

#### Phase 105: Mistake-Detection + Classification + Tagging Service (on-the-fly)

**Goal**: A server-side `mistakes` service derives, on-the-fly from stored per-ply evals, every flaw in a Lichess-analyzed game — severity (inaccuracy / mistake / blunder) plus eight attribution tags — and returns typed per-flaw objects ready for the Games / Flaws / Analysis surfaces and SEED-037 Train to consume. No materialization, no schema change, no UI.
**Depends on**: Stored per-ply `eval_cp` / `eval_mate`, clocks, `phase`, `material_imbalance`, result + colors (Phases 28.1, 79, 80–83, 91); `app/services/eval_utils.py` (Lichess sigmoid + mate mapping). Independent of Phase 104.
**Requirements**: LIBG-02, LIBG-06, LIBG-07
**Success Criteria** (what must be TRUE):

  1. For a Lichess-analyzed game, the service returns the user's flaws with severity computed from the expected-score drop using the Lichess-aligned halved thresholds (inaccuracy ≥ 0.05, mistake ≥ 0.10, blunder ≥ 0.15 on the [0,1] ES scale), from the mover's perspective; derived per-game counts sanity-check *close* (not identical) to the game-level `white_/black_blunders/mistakes/inaccuracies` columns (LIBG-02).
  2. Each flaw carries its applicable attribution tags — `miss`, `unpunished`, `from-winning`, `result-changing`, `phase`, and exactly one tempo tag from {`time-pressure`, `hasty`, `knowledge-gap`} (derived from move-time + clock; initial thresholds documented and tunable) (LIBG-06).
  3. Detection is on-the-fly from stored evals with **no new columns / table / migration / reimport**; chess.com and unanalyzed-lichess games return an explicit "no engine analysis" result, never a false zero-flaw game (LIBG-02, LIBG-07).
  4. Mate evals are handled via Option B (±1000 cp-equivalent ES), not the hard 1.0/0.0 converter; cp↔mate transitions classify sensibly (LIBG-02).
  5. Each flaw is a typed structured object (ply, FEN, side, severity, tags, eval before/after) documented as the contract for Games / Flaws / Analysis / Train; unit tests cover each severity band, each tag, mate handling, and the no-analysis path (LIBG-07).

**Plans**: 2 plans

- [x] 105-01-PLAN.md — Core severity engine: types/constants, ES helper + mate Option B, coverage gate, FEN recompute, all-moves pass, severity-only `classify_game_mistakes` + Wave-0 test scaffold
- [x] 105-02-PLAN.md — Eight attribution tags wired into flaws, ply-ordered ownership-guarded repository read helper + DB test, oracle-closeness sanity test

**UI hint**: no

#### Phase 106: Games-Surface Backend — Mistake Filter, Per-Game Counts & Stats Aggregates (on-the-fly)

**Goal**: Two server-side endpoints the Games subtab consumes — a mistake-filtered game archive with per-game counts/card-chips, and a mistake-stats aggregate — both derived on-the-fly via a SQL window-scan + Python tagging that reuses Phase 105's `mistakes_service` kernel, with no materialization and no schema change.
**Depends on**: Phase 105 (`mistakes_service` per-game kernel + shared tag functions, `FlawRecord` contract); `app/repositories/query_utils.py::apply_game_filters()`; `app/services/eval_utils.py`; stored per-ply `eval_cp`/`eval_mate`, clocks, `phase`, `material_imbalance`, result + colors. Independent of any frontend work.
**Requirements**: LIBG-08, LIBG-09
**Success Criteria** (what must be TRUE):

  1. The game-archive query accepts a boolean mistake-type filter (game contains ≥1 of a selected severity), implemented as a single indexed `EXISTS` over the per-ply ES-drop with severity thresholds passed as bound parameters — no new column, no materialization, no backfill; benchmark the window-scan and add an index on `game_positions(game_id, ply)` only if measured necessary (LIBG-08).
  2. Each game returned by the archive endpoint carries its per-game B/M/I severity counts plus a curated, aggregated/deduped set of card tag-chips (game-level dedupe, one chip per tag type present, inaccuracy-level tags and `phase` excluded), reusing Phase 105's kernel; chess.com and unanalyzed-lichess games return an explicit "no engine analysis" state, never a false zero-flaw game (LIBG-08).
  3. A stats-panel aggregate endpoint computes, over the filtered analyzed-only set: per-severity counts and rates normalized per game and per 100 moves; the full tag distribution (tempo split, result-changing rate, phase histogram); and a trend-over-time series (mistake rate by recency window) (LIBG-09).
  4. The stats response states the explicit denominator — the `% analyzed` of the filtered set using the ≥90%-per-ply-coverage definition — and the analyzed-game N, so the panel never implies clean games where evals are simply absent (LIBG-09).
  5. The cross-game work is pushed into a SQL window-function query (`LAG`/`LEAD` over `game_positions ⋈ games`) that returns only flagged mistake+blunder rows enriched for tagging, with Python applying the 8 tags + tag-distribution stats over that reduced set; the severity-drop math is cross-checked against the Python kernel by a fixture test (LIBG-08, LIBG-09).

**Plans**: TBD (run `/gsd-plan-phase 106`)

**UI hint**: no

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
| 78-79. v1.15 phases | v1.15 | 10/10 | Complete (VAL-01 / PHASE-VAL-01 rescinded) | 2026-05-03 |
| 80-83. v1.16 phases | v1.16 | 24/24 | Complete | 2026-05-11 |
| 84-88.4. v1.17 phases | v1.17 | ~54/~54 | Complete (89 dropped, 87.3 superseded) | 2026-05-19 |
| 90-92. v1.18 phases | v1.18 | 17/17 | Complete | 2026-05-22 |
| 93. Global Percentile Benchmark Artifact | v1.19 | 2/2 | Complete    | 2026-05-22 |
| 94. Backend & Frontend Percentile Annotations | v1.19 | 3/3 | Complete   | 2026-05-23 |
| 95-96. v1.20 phases | v1.20 | 5/5 | Complete | 2026-05-29 |
| 97-99.1. v1.21 phases | v1.21 | 15/15 | Complete (99.1 INSERTED) | 2026-05-31 |
| 100-101. v1.22 phases | v1.22 | 3/3 | Complete | 2026-05-31 |
| 102-103. v1.23 phases | v1.23 | 3/3 | Complete (103 unplanned follow-on) | 2026-06-03 |
| 104. Library Page Shell + Import/Overview Migration | v1.24 | 2/2 | Complete    | 2026-06-05 |

## Backlog

### Phase 999.1: Password Reset (BACKLOG)

**Goal:** Users can recover account access when they forget their password — request reset link, receive email, set new password
**Requirements:** TBD
**Plans:** 2/2 plans complete

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
