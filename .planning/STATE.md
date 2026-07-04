---
gsd_state_version: 1.0
milestone: v1.31
milestone_name: Pipeline Consolidation
current_phase: 999.1
current_phase_name: BACKLOG
status: v1.31 Pipeline Consolidation complete — archived + tagged v1.31; merged to main, prod deploy pending
stopped_at: v1.31 milestone closed
last_updated: "2026-07-04T20:00:00.000Z"
last_activity: 2026-07-04
progress:
  total_phases: 3
  completed_phases: 3
  total_plans: 14
  completed_plans: 14
  percent: 100
---

# Project State: FlawChess

## Current Position

Milestone: v1.31 Pipeline Consolidation — **COMPLETE** (Phases 148, 149, 150; tagged v1.31; archived to milestones/)
Phase: none active — planning next milestone
Status: v1.31 complete and merged to `main`; **prod deploy pending** (`bin/deploy.sh` — last prod release was #242)
Last activity: 2026-07-04

## Project Reference

See: .planning/PROJECT.md (updated 2026-07-04 after v1.31 milestone close)
Core value: Position-precise WDL across openings + endgames + time pressure on top of users' actual chess.com / lichess games, with personalized LLM commentary and an auto-generated opening-strengths/weaknesses report.
Current focus: v1.31 complete. Next: deploy v1.31 to production (`bin/deploy.sh` / `/deploy`), then `/gsd-new-milestone` (leading candidate: SEED-081 Maia-3 human-move enrichment).

## Milestone Progress

Thirty milestones complete (v1.0–v1.30). v1.30 Forcing-Line Tactic Gate shipped 2026-06-30 — 7 phases (141–147), 25 plans; released across PRs #229/#230/#231/#234. An engine-free `forcing_line_gate` module over persisted MultiPV=2 blobs (`allowed_pv_lines`/`missed_pv_lines` JSONB on `game_flaws`) gates the v1.28 tactic tags to real forced tactics; `retag_flaws.py` makes every threshold change a seconds-fast engine-free re-derivation; the continuation eval + blob backfill run on the remote fleet via an atomic `/atomic-lease`/`/atomic-submit` pipeline (Phases 146/147, SEED-071/074). Known gap: the local in-process drain re-mints ~9/3.36M ungated cp tags (self-heals via tier-4, not rollback-class). Archived to milestones/v1.30-ROADMAP.md + v1.30-REQUIREMENTS.md, tagged v1.30.

v1.29 Live-Engine Analysis Page shipped 2026-06-29 — 5 phases (136–140), 14 plans; released to production via PR #227 (`e3f652ab`). Live in-browser single-thread WASM Stockfish (`useStockfishEngine`), branching analysis board (`useAnalysisBoard`), lazy-loaded `/analysis` route, tactic mode subsuming + deleting the Phase 135 TacticLineExplorer, and a full-game board behind a unified `Analyze` entry with inline tactic-chip PV sidelines. No backend schema or new endpoints (D-4). Archived to milestones/v1.29-ROADMAP.md, phases to milestones/v1.29-phases/, tagged v1.29.

## Key Context

- Stack: FastAPI + React/TS/Vite 8 + PostgreSQL + python-chess
- ORM: SQLAlchemy 2.x async + Alembic
- Auth: FastAPI-Users 15.0.5 (Bearer JWT, Google SSO, guest sessions)
- Core algorithm: Zobrist hashes (white_hash, black_hash, full_hash) precomputed at import
- Deployment: Docker Compose on Hetzner CPX42, 8 vCPUs, 16 GB RAM + 4 GB swap
- v1.29 WASM engine: stockfish-18-lite-single.{js,wasm} (~7 MB), vendored to public/engine/, loaded via plain new Worker('/engine/stockfish-18-lite-single.js') — no Vite bundler processing
- v1.29 D-3 locked: single-thread WASM only; no COOP/COEP headers site-wide; multi-thread explicitly deferred (D-3)
- v1.29 D-4 locked: no schema, no migration, no new backend endpoints; analysis state lives in the URL
- v1.29 D-5 locked: stored PVs (Phase 135 tactic-lines endpoint) are the initial mainline; live engine takes over on deviation

## Accumulated Context

### Roadmap Evolution

- v1.31 Pipeline Consolidation closed 2026-07-04 (Phases 148, 149, 150; tag v1.31). Execution decisions + quick-task log archived to `milestones/v1.31-ROADMAP.md`, PROJECT.md Key Decisions, and git. Reset for the next milestone.

### Decisions

(Cleared at v1.31 close — full log in `.planning/PROJECT.md` Key Decisions + the milestone archives.)

### Pending Todos

None active.

### Blockers/Concerns

- v1.31 is complete on `main` but **not yet deployed to production** — deploy is the next step (`bin/deploy.sh` / `/deploy`).

## Deferred Items

Items acknowledged and deferred at **v1.31 milestone close on 2026-07-04** (user chose "Acknowledge & proceed" on the 31-item pre-close audit):

| Category | Item | Disposition |
|----------|------|-------------|
| debug | `entry-submit-n-plus-1` (fixed_awaiting_deploy), `insights-diskfull-shm` (awaiting_human_verify) | Carried — unrelated infra sessions, not v1.31-scoped (carried since v1.29) |
| quick_task | 19 incomplete (unknown/missing status, 260531–260616) | Resolved in fact — shipped across prior milestones; false-positive pattern (`project_stale_gsd_sdk_audit_bug`) |
| todos | 2 pending (bitboard partial-position storage; WR01-PT33 invalid Tailwind score-axis label) | Carried — long-range / cosmetic, not milestone-scoped |
| seeds | 8 dormant (SEED-037/042/067/069/077/078/081 + closed-in-fact SEED-080) | SEED-080 implemented as this milestone → moved to `seeds/closed/` at close; remainder future/v2 (SEED-081 Maia-3 is the leading next-milestone candidate) |
| known-gap | Local in-process drain re-mints ~9/3.36M ungated cp tags | Carried from v1.30 — self-heals via tier-4, not rollback-class; untouched by v1.31 (consolidation preserved behavior exactly); `project_local_drain_ungated_tactic_tags` |
| deploy | v1.31 not yet deployed to production | Intentional — milestone closed on `main`; deploy is the explicit next step (`bin/deploy.sh`) |

Items acknowledged and deferred at **v1.30 milestone close on 2026-07-02** (user signed off "mark all as resolved and proceed"):

| Category | Item | Disposition |
|----------|------|-------------|
| verification | Phase 146 `146-VERIFICATION.md` (human_needed) | Resolved at close — Phase 146 shipped to prod (#230) + follow-on fix #231, soaked live; verification human-signed-off |
| uat | Phase 142 `142-UAT.md` (passed, 0 pending scenarios) | Resolved — false positive (status already `passed`) |
| verification | Phase 147-06 atomic gated-write e2e (HUMAN-UAT-pending) | Carried — dev DB has no queued eval_jobs (`EVAL_AUTO_DRAIN_ENABLED=false`); automated dry-run confirmed `/atomic-lease` wiring; verify on live prod drain |
| known-gap | Phase 147 strict-zero invariant broken (local in-process drain re-mints ~9/3.36M ungated cp tags) | Carried — self-heals via tier-4, not rollback-class; tracked in `project_local_drain_ungated_tactic_tags` |
| debug | `entry-submit-n-plus-1` (fixed_awaiting_deploy), `insights-diskfull-shm` (awaiting_human_verify) | Carried — unrelated infra sessions, not v1.30-scoped (carried since v1.29) |
| quick_task | 19 incomplete (unknown/missing status, 260531–260616) | Resolved in fact — shipped across prior milestones; false-positive pattern (`project_stale_gsd_sdk_audit_bug`) |
| todos | 5 pending (bitboard storage, phase-70 amendments, benchmark items) | Carried — long-range, not milestone-scoped |
| seeds | 9 dormant (SEED-037/042/063/067/069 + closed-in-fact SEED-070/071/073/074) | Carried — SEED-070/071/073/074 implemented as v1.30 (move to closed/ on next housekeeping); remainder future/v2 |

Items acknowledged and deferred at **v1.29 milestone close on 2026-06-29** (user signed off "mark all as resolved and proceed"):

| Category | Item | Disposition |
|----------|------|-------------|
| verification | Phase 136 / 138 / 140 `VERIFICATION.md` (human_needed) | Resolved — human-signed-off at close; feature shipped to prod (#227) and exercised live (incl. 2 Sentry crash fixes against the running page) |
| uat | Phase 138 `138-UAT.md` — 4 deferred scenarios | Resolved — human-signed-off at close; `/analysis` route + entry points live and in daily use |
| debug | `entry-submit-n-plus-1` (fixed_awaiting_deploy), `insights-diskfull-shm` (awaiting_human_verify) | Carried — unrelated infra sessions, not v1.29-scoped |
| quick_task | 19 incomplete (unknown/missing status, 260531–260616) | Resolved in fact — shipped across prior milestones; false-positive pattern (project_stale_gsd_sdk_audit_bug) |
| todos | 5 pending (bitboard storage, phase-70 amendments, benchmark items) | Carried — long-range, not milestone-scoped |
| seeds | 9 dormant (SEED-012/037/039/042/063/066/067/068/069) | Carried — SEED-066 implemented as v1.29 (move to closed/ on next housekeeping); SEED-068 (double-go on visible-during-stopping) effectively addressed by the FLAWCHESS-7V stopping-state guard; remainder future/v2 |

## Session Continuity

Last session: 2026-07-04 — v1.31 milestone close
Stopped at: v1.31 archived + tagged; prod deploy pending
Resume: deploy v1.31 (`bin/deploy.sh` / `/deploy`), then `/gsd-new-milestone`

## Performance Metrics

(Cleared at v1.31 close — per-plan timings archived with the milestone.)
