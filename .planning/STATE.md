---
gsd_state_version: 1.0
milestone: v1.29
milestone_name: Live-Engine Analysis Page
current_phase: 138
current_phase_name: analysis-route-page-shell-entry-points
status: verifying
stopped_at: Phase 138 executed (3/3 plans); UAT deferred to Phase 139 (combined /analysis surface test)
last_updated: "2026-06-26T19:32:00Z"
last_activity: 2026-06-26
last_activity_desc: Phase 138 executed + reviewed; 4 UAT items deferred to Phase 139
progress:
  total_phases: 8
  completed_phases: 3
  total_plans: 8
  completed_plans: 8
  percent: 38
---

# Project State: FlawChess

## Current Position

Phase: 138 (analysis-route-page-shell-entry-points) — PENDING UAT (deferred to Phase 139)
Plan: 3 of 3
Status: Executed + code-reviewed (CR-01/WR-01 fixed); 4 browser/device UAT items deferred to a combined pass after Phase 139. Close with /gsd-verify-work 138.
Last activity: 2026-06-26 — Phase 138 executed; UAT deferred to Phase 139

Progress: [░░░░░░░░░░] 0%

## Project Reference

See: .planning/PROJECT.md (updated 2026-06-26 for v1.29 milestone kickoff)
Core value: Position-precise WDL across openings + endgames + time pressure on top of users' actual chess.com / lichess games, with personalized LLM commentary and an auto-generated opening-strengths/weaknesses report.
Current focus: v1.29 Live-Engine Analysis Page — standalone /analysis board with in-browser single-thread WASM Stockfish, branching move tree, and tactic-mode overlay subsuming Phase 135 TacticLineExplorer.

## Milestone Progress

Twenty-eight milestones complete (v1.0–v1.28). v1.28 Tactic Tagging shipped 2026-06-25 — 14 phases (123.1, 124–135 incl. 128.1; 130 superseded by 131–134), 45 plans. Tactic-motif detector (cook.py-faithful), missed-vs-allowed dual orientation, you-vs-opponent comparison, tactic filter UI (de-beta'd, homepage hero), Tactic Line Explorer (SEED-065). Archived to milestones/v1.28-ROADMAP.md, tagged v1.28. Phase 135's TacticLineExplorer is the direct predecessor to v1.29 Phase 139 (subsume without regression).

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

### Decisions

- D-3: Single-thread WASM only; no SharedArrayBuffer/COOP+COEP site-wide (breaks Google OAuth + iOS Safari)
- D-4: Ephemeral, no schema — analysis state in URL; backend untouched except existing tactic-lines endpoint
- D-5: Stored PVs seed the initial mainline; live engine supplements on deviation
- useAnalysisBoard must NOT modify useChessGame.ts (independent hook, different contract)
- vite.config.ts must have optimizeDeps: { exclude: ['stockfish'] } to prevent WASM path break (Pitfall 1)
- Phase 139 regression gate required BEFORE deleting TacticLineExplorer.tsx
- [Phase ?]: Inline debounce (useState null + setTimeout) vs useDebounce — starts null to preserve 150ms delay on all analyses
- [Phase ?]: analyzeRef stable (useCallback []) — no render-phase update needed per react-hooks/refs rule
- [Phase ?]: useAnalysisBoard: FEN-per-node branching tree; functional setState updaters for navigation; stateRef for makeMove synchronous read
- [Phase 138]: Destructure useAnalysisBoard return to avoid react-hooks/refs v7 false-positive in JSX
- [Phase 138]: AnalysisRoute wrapper reads useSearchParams and keys AnalysisPage by fen for remount on re-entry
- [Phase 138]: Single EvalBar render to avoid duplicate testid failure in jsdom tests

### Pending Todos

None yet.

### Blockers/Concerns

None at planning start.

## Deferred Items

Items acknowledged and deferred at **v1.28 milestone close on 2026-06-25**:

| Category | Item | Disposition |
|----------|------|-------------|
| uat | Phase 135 `135-UAT.md` — RESOLVED: passed 2/2 | Resolved — user manually verified on prod 2026-06-25 |
| uat | Phase 126 `126-UAT.md` (passed, 0 pending) | Not a gap — frontmatter artifact |
| debug | `entry-submit-n-plus-1` (fixed_awaiting_deploy), `insights-diskfull-shm` (awaiting_human_verify) | Carried — unrelated infra sessions |
| quick_task | 19 incomplete (unknown/missing status) | Resolved in fact — shipped; false-positive pattern (project_stale_gsd_sdk_audit_bug) |
| todos | 5 pending (bitboard storage, phase-70 amendments, benchmark items) | Carried — long-range, not v1.29-scoped |
| seeds | SEED-012, SEED-037, SEED-039, SEED-042, SEED-063 | Carried — future/v2; SEED-037/039 next-milestone candidates |

## Session Continuity

Last session: 2026-06-26T17:12:53.494Z
Stopped at: Phase 138 planned (3 plans, checker-verified)
Resume file: .planning/phases/138-analysis-route-page-shell-entry-points/138-02-analysis-page-and-route-PLAN.md

## Performance Metrics

| Phase | Plan | Duration | Notes |
|-------|------|----------|-------|
| Phase 136 P02 | 15m | 3 tasks | 6 files |
| Phase 137 P01 | 4min | 2 tasks | 2 files |
| Phase 137 P01 | 4min | 2 tasks | 2 files |
| Phase Phase 137 P02 P7min | 2 tasks | 6 files tasks | - files |
| Phase 137 P02 | 9min | 2 tasks | 6 files |
| Phase Phase 137 P03 P13min | 2 tasks | 2 tasks | 2 files |
| Phase 138 P01 | 1min | 1 tasks | 1 files |
| Phase Phase 138 PP03 | 3min | 2 tasks | 3 files |
| Phase 138 P02 | 7min | 2 tasks | 2 files |
