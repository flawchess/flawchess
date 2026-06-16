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
- ✅ **v1.26 Full-Game Eval Pipeline** — Phases 116–120 (incl. 117.1, 117.2) (shipped 2026-06-14) — see [milestones/v1.26-ROADMAP.md](milestones/v1.26-ROADMAP.md)
- 🚧 **Active (post-v1.26, milestone TBD)** — shipped but not yet grouped into a named milestone: Phase 121 (Remote-worker tier-1 claiming, SEED-048, release #199), Phase 122 (In-app feedback button, SEED-049, release #202), Phase 123 (Remote-worker entry-ply fresh-import drain, SEED-051, release #203). No open phases.

## Phases

> 🚧 **Active work (post-v1.26, milestone TBD):** Phases 121–123 have **shipped to prod** (releases #199, #202 on 2026-06-15; #203 on 2026-06-16) but are not yet grouped into a named milestone. No open phases remain. Group the shipped phases at the next milestone close (per the standalone-then-regroup pattern, e.g. v1.20), or run `/gsd-new-milestone` to formalize one.

### Phase 121: Remote-worker tier-1 claiming (SEED-048) ✅ SHIPPED

**Status**: ✅ Implemented, tested, and live in prod — shipped 2026-06-15 (release #199). Soak confirmed no tier-1/tier-3 double-claim and correct `eval_jobs` stamping. Awaiting milestone grouping only.
**Goal**: A remote eval worker can claim tier-1 (single-game "analyze") requests, not just the tier-3 idle backlog — so when the server pool is mid-game on another job, a second (idle) machine can pick up a freshly-enqueued single-game analysis and shorten click-to-pickup latency. First-come-first-served: the server's in-process drain still usually wins tier-1 when it is idle (no network hop, no poll interval), so this deliberately targets the **server-busy overflow** case. Biasing tier-1 to the faster box and interruptible tier-3 are explicit deferred follow-ons.
**Depends on**: Phase 120 (remote eval worker lease/submit contract + headless CLI worker)
**Source**: SEED-048 (FCFS scope; decisions locked 2026-06-15 explore session) · **Plans**: 1 plan (complete)

Plans:

- [x] 121-01-PLAN.md — wire lease→claim_eval_job (tier-1/2/3), thread opaque job_id lease→submit with status='leased' stamp guard, drop worker idle_sleep 5s→1s

Scope (3 changes, no DB migration):

1. `POST /api/eval/remote/lease` calls `claim_eval_job` (tier-1 > tier-2 > tier-3, lease_expiry + SKIP LOCKED, stale-lease sweep) instead of `_claim_tier3_derived`; tier-3 still falls through as the derived path, unchanged.
2. Thread an opaque `job_id` through the lease→submit round-trip: the lease response carries the claimed `eval_jobs.id` (`None` for tier-3), submit echoes it, and the submit handler stamps `eval_jobs.status='completed', completed_at=now()` when present. Tier-3 keeps `job_id=None` and behaves exactly as today.
3. Drop the worker idle poll `idle_sleep` 5s → ~1s so an idle remote worker notices a freshly-enqueued tier-1 quickly (only the empty-queue/204 path sleeps; the busy path is already a tight loop).

Files: `app/routers/eval_remote.py` (lease/submit handlers), `app/services/eval_queue_service.py` (`claim_eval_job` already implements the tiered claim + lease sweep), `scripts/remote_eval_worker.py` (idle_sleep default + echo job token on submit), lease/submit Pydantic schemas (opaque job-token field). Prod soak passed: no tier-1/tier-3 double-claim observed, submit correctly stamps `eval_jobs`.

### Phase 122: In-app feedback button (SEED-049) ✅ SHIPPED

**Status**: ✅ Implemented, tested, and live in prod — shipped 2026-06-15 (release #202); all 5 human-gated UAT items confirmed on prod. Awaiting milestone grouping only.
**Goal**: A low-friction in-app feedback channel so users (guests included) can submit likes / dislikes / suggestions tied to the exact page they were on. A global floating button (bottom-right, auto-hides on scroll-down, yields to open drawers/modals, iOS safe-area aware) opens a modal with required freeform text + an optional coarse sentiment rating. Submissions persist to a new `feedback` table and also fire a Sentry signal (tagged with username / ELO bucket / platform) so feedback pings the team instead of rotting in a table nobody reads.
**Depends on**: none (standalone; can ship independently of Phase 121)
**Source**: SEED-049 (decisions locked 2026-06-15 explore session) · **Plans**: 2 plans (complete)
Plans:
**Wave 1**

- [x] 122-01-PLAN.md — Backend: feedback table + migration, schemas, rate-limit, repository, Sentry/ELO service, thin POST /api/feedback router

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 122-02-PLAN.md — Frontend: useScrollDirection + useOverlayOpen hooks, floating FeedbackButton, FeedbackModal (required text + optional 3-point sentiment), mount + bottom scroll padding

Scope (per [SEED-049](seeds/closed/SEED-049-in-app-feedback-button.md)):

1. **Backend**: new `app/models/feedback.py` + Alembic migration (`user_id` FK with `ondelete`, page URL, freeform text, optional sentiment, `created_at`); thin `routers/` endpoint → service → repository per the layering rules. Light per-user rate-limit + max text length as an abuse guard. Sentry capture via `sentry_sdk` with `source="feedback"` + username / ELO-bucket / platform tags (username/platform/ELO derived from the user record, not denormalized).
2. **Frontend**: global floating feedback button (auto-hide on scroll-down / show on scroll-up, yields to open overlays, `env(safe-area-inset-bottom)`, ≥44×44pt tap target, mini/secondary styling) + submit modal (required text, optional thumbs/3-point sentiment). Wire page URL from the router. Honor browser-automation rules (`data-testid`, `aria-label`, semantic `<button>`/`<form>`), theme colors from `theme.ts`, primary submit = `variant="default"`. Add bottom scroll padding to long containers.
3. **Optional de-risk**: a quick `/gsd-sketch` of the floating-button placement (mobile drawer-overlap is the real design risk) before planning.

### Phase 123: Remote-worker fan-out for entry-ply (import-time) eval on big first imports (SEED-051) ✅ SHIPPED

**Status**: ✅ Implemented, tested, and live in prod — shipped 2026-06-16 (release #203). UAT done, confirmed on a real 5,132-game first import (user 28): entry-ply drain split server-pool (2,573) / worker `ws80` (1,800) with identical 3.7 evals/game density, 100% `evals_completed_at` with zero stuck or expired-unstamped leases, and code-review BLOCKER CR-01 (zero-target lease livelock) verified fixed live (9 zero-target leased games stamped, not re-leased). Mixed-fleet backward compat holds: un-upgraded workers still drain full-ply under the `remote-worker` fallback and never touch entry-ply. Awaiting milestone grouping only.
**Goal**: Extend the headless remote eval worker pool (SEED-048 / Phase 120) — which today only drains full-ply tier-1/3 — to also drain **entry-ply** (import-time, depth-15) eval in parallel on **big first imports**, cutting first-import latency (time until a brand-new user sees flaws / phase-transition evals populate) by roughly the worker fan-out factor. The worker gains a second, higher-priority work type via a three-rung priority ladder: tier-1 single-game (top) > entry-ply fresh-import drain (new, batched depth-15) > tier-3 idle backlog (bottom), checked between full-ply games (no preemption, no reserved capacity). Incremental syncs stay server-pool-only via a runtime backlog-depth gate, so the lease/round-trip tax is only paid when it pays off.
**Depends on**: Phase 120 (remote worker lease/submit protocol + headless CLI) — ✅ live in prod (and Phase 121 tier-1 claiming shipped #199), so the dependency is satisfied; planning now gates only on big-first-import latency being a current priority
**Source**: SEED-051 (decisions D-1…D-5 locked 2026-06-16) · **Plans**: 3 plans (planned 2026-06-16)

Plans:

- [x] 123-01-PLAN.md — Foundation: lease columns migration + shared SKIP-LOCKED LIFO claim helper + tuning constants + D-01 server-side lease
- [x] 123-02-PLAN.md — Batched /entry-lease + /entry-submit endpoints, scope param, D-5 backlog gate, X-Worker-Id (operator-token auth)
- [x] 123-03-PLAN.md — Worker CLI: D-06 ladder + depth-15 entry-ply path + distinctive --worker-id

Scope (the delta is small — reuses the SEED-048 worker + SEED-044 storage convention):

1. **One nullable lease column on `games`** + migration (D-3) — `entry_eval_lease_expiry` (optionally `entry_eval_leased_by`); the queue stays the existing predicate `games.evals_completed_at IS NULL`, claimed via a `SKIP LOCKED` LIFO (id DESC) lease. No new table, no per-position storage.
2. **Batched entry-ply lease endpoint** — claim N fresh games, server derives target plies (reuse `_collect_eval_targets` / phase-transition selection), return a flat `{game_id, ply, fen}[]`. Worker stays a dumb Stockfish-over-HTTP node (D-2).
3. **Batched entry-ply submit endpoint** — accept `{game_id, ply, eval_cp, eval_mate}[]`, apply SEED-044 convention, classify flaws, stamp `evals_completed_at` per fully-covered game, clear the lease.
4. **Worker CLI: depth-15 mode** + the between-full-ply-games priority check (D-1).
5. **D-5 backlog-depth gate** — bounded existence probe (`… LIMIT 1 OFFSET 299`) at lease time; invite workers only when backlog ≥ threshold (starting knob: 300 games / 50-game batches); tail (≲300 games) falls back to the server pool for free.

Open/deferred (not v1): entry-ply lease TTL sizing; routing `run_eval_drain` through the same lease so the server pool can't double-evaluate leased games (v1 vs fast-follow TBD); backlog-gate threshold tuning against real server-pool throughput once live; macOS background-scheduling caveat (SEED-048) unchanged. See [seeds/SEED-051-remote-worker-entry-ply-fresh-import-drain.md](seeds/closed/SEED-051-remote-worker-entry-ply-fresh-import-drain.md).

<details>
<summary>✅ v1.26 Full-Game Eval Pipeline (Phases 116–120, incl. 117.1, 117.2) — SHIPPED 2026-06-14</summary>

Turned eval coverage from "endgame-entry plies only" into a full-game background analysis pipeline: every move evaluated by Stockfish at Lichess-parity strength (1M nodes/move), drained by a tiered priority queue (explicit > recent windows > idle backlog), results flowing automatically into the Library's flaw surfaces. Server-first v1 of SEED-012. Two correctness phases (117.1, 117.2) were inserted from SEED-044 for a pre/post-move eval off-by-one; Phase 119 (SEED-045/046) hardened drain coverage; Phase 120 (SEED-048) added an off-box headless eval worker.

- [x] Phase 116: All-Ply Engine Core (3/3 plans) — 1M-node all-ply drain + ply≤20 dedup + completion marker + memory bounds — completed 2026-06-14 (deployed #190)
- [x] Phase 117: Priority Queue + Flaw Integration (3/3 plans) — SKIP-LOCKED tiered queue + lease/report + tier-1 fan-out + best_move/PV + flaw flow-through + guest exclusion — completed 2026-06-14 (deployed #190)
- [x] Phase 117.1: Flaw-Eval Convention Fix (INSERTED, SEED-044) (2/2 plans) — post-move convention everywhere + dedup one-ply-shift + clean-slate re-eval — completed 2026-06-14 (deployed #190)
- [x] Phase 117.2: Wipe Eval-Only Engine Residue (INSERTED, SEED-044) (1/1 data migration) — NULLed 3,497 eval-only-residue engine games; lichess untouched — completed 2026-06-14 (deployed #191)
- [x] Phase 118: Demand UX + Auto-Enqueue (3/3 plans) — on-demand analyze affordances + coverage badges + in-flight status + guest promotion — completed 2026-06-14
- [x] Phase 119: Eval-drain coverage (SEED-045, SEED-046) (3/3 plans) — bounded-retry hole-filling + recency-weighted tier-3 lottery + lichess-leak fix + honest pulsing badge — completed 2026-06-14
- [x] Phase 120: Headless remote trusted-operator eval worker (SEED-048) (4/4 plans) — operator-token lease/submit endpoints + headless CLI worker + SF-version gate — completed 2026-06-14

See [milestones/v1.26-ROADMAP.md](milestones/v1.26-ROADMAP.md) for full details.

</details>

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
| 119. Eval-drain coverage (SEED-045, SEED-046) | 3/3 | Complete | 2026-06-14 |

## Backlog

### Phase 999.1: Password Reset (BACKLOG)

**Goal:** Users can recover account access when they forget their password — request reset link, receive email, set new password
**Requirements:** TBD
**Plans:** 1/1 plans complete

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
