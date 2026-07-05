---
gsd_state_version: 1.0
milestone: v2.0
milestone_name: FlawChess Engine
status: roadmap
last_updated: "2026-07-05T19:00:00.000Z"
last_activity: 2026-07-05
progress:
  total_phases: 5
  completed_phases: 0
  total_plans: 0
  completed_plans: 0
  percent: 0
---

# Project State: FlawChess

## Current Position

Phase: 153 Pure Search Core (Guardrail + Backup + MCTS + Fallback) (not started)
Plan: —
Status: Roadmap defined (5 phases); awaiting phase planning
Last activity: 2026-07-05 — Milestone v2.0 roadmap created

## Project Reference

See: .planning/PROJECT.md (updated 2026-07-04 after v1.31 milestone close)
Core value: Position-precise WDL across openings + endgames + time pressure on top of users' actual chess.com / lichess games, with personalized LLM commentary and an auto-generated opening-strengths/weaknesses report.
Current focus: v2.0 FlawChess Engine roadmap created (SEED-082) — 5 phases (153 pure search core; 154 real providers/worker pool; 155 React hook + anytime UI; 156 board arrows + toggles; 157 game-review overlay), all 21 v2.0 requirements mapped (REQUIREMENTS.md's own "19 total" placeholder was a miscount — corrected to 21 in the traceability table). Next: `/gsd-plan-phase 153`. Client-side-only, no backend/schema/migrations/new-deps — builds on the shipped, deployed v1.29 Stockfish.wasm + v1.32 Maia infra. v1.31 and v1.32 are both live in production.

## Milestone Progress

Thirty-two milestones complete (v1.0–v1.32).

v1.32 Maia-3 Human-Move Enrichment shipped 2026-07-05 — 2 phases (151, 151.1), 10 plans. Client-side Maia-3 (`maia3_simplified.onnx` via onnxruntime-web in a lazy Web Worker) on `/analysis`: a per-ELO "Moves by Rating" chart + a Maia WDL eval bar (LEFT; Stockfish RIGHT), live per navigation, zero server round-trip, nothing persisted. Phase 151.1 (SEED-083) recolored chart lines by Stockfish move quality and swapped the top-6 cap for the Maia ≥0.95-mass ∪ {SF-best} set via a second isolated grading worker. Repo relicensed MIT → AGPL-3.0. Phase 152 (Flaw Overlay, Pillars A+B) demoted to SEED-084; MAIA-06 latency measurement accepted as override. No schema/migration; one read-only `current_rating` backend field. Archived to milestones/v1.32-ROADMAP.md + v1.32-REQUIREMENTS.md, phases to milestones/v1.32-phases/, tagged v1.32. **Deployed to production.**

v1.31 Pipeline Consolidation completed 2026-07-04 — 3 phases (148, 149, 150), 14 plans. Server-side-only consolidation: retired the dead Gen-1 eval protocol and unified the copy-pasted eval write path (`apply_completion_decision()` 3→1, `_classify_with_overlay` 4→1, per-ply diff/upsert replacing delete-then-insert, `eval_apply.py`/`eval_entry.py` split), proven byte-identical. No behavior change. Archived, tagged v1.31. **Deployed to production.**

v1.30 Forcing-Line Tactic Gate shipped 2026-06-30 — 7 phases (141–147), 25 plans; released across PRs #229/#230/#231/#234. An engine-free `forcing_line_gate` module over persisted MultiPV=2 blobs (`allowed_pv_lines`/`missed_pv_lines` JSONB on `game_flaws`) gates the v1.28 tactic tags to real forced tactics; `retag_flaws.py` makes every threshold change a seconds-fast engine-free re-derivation; the continuation eval + blob backfill run on the remote fleet via an atomic `/atomic-lease`/`/atomic-submit` pipeline (Phases 146/147, SEED-071/074). Known gap: the local in-process drain re-mints ~9/3.36M ungated cp tags (self-heals via tier-4, not rollback-class). Archived to milestones/v1.30-ROADMAP.md + v1.30-REQUIREMENTS.md, tagged v1.30.

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
- Phase 151.1 inserted after Phase 151: Stockfish-graded Maia moves on the Moves-by-Rating chart (from SEED-083)

### Decisions

(Cleared at v1.31 close — full log in `.planning/PROJECT.md` Key Decisions + the milestone archives.)

- [Phase 151-02]: LICENSE: kept the exact FSF AGPL-3.0 boilerplate verbatim, only filled in the How-to-Apply appendix placeholders (FlawChess / 2026 / Adrian Imfeld)
- [Phase 151-02]: MaiaAttribution renders always-visible (not hover-gated like InfoPopover) so the AGPL offer-source links are present without interaction
- [Phase 151-03]: Insertion-ordered dict from get_current_rating_by_platform is the mechanism for picking the scalar current_rating (first key = platform of overall most-recent game, no second query needed)
- [Phase 151-03]: Tests placed in existing tests/test_game_repository.py + tests/test_users_router.py rather than plan's named tests/test_users.py (file doesn't exist; matches established repo/router test split)
- [Phase 151-03]: Reverted requirements.mark-complete's MAIA-04 checkbox flip: MAIA-04 is shared across Plans 03/04/06 (frontmatter), so 151-03 alone only partially delivers it (rating-at-game-time data source) — left [ ] Pending with a partial-delivery note; Plans 04/06 will actually close it
- [Phase 151-04]: Reconstructed the confirmed 4352-entry policy vocab as base(from*64+to,4096)+underpromotion lane(to,promo-piece)x4(256)=4352; best-effort, not verified vs CSSLab's literal index order - VALID-01 (Plan 06) must cross-check
- [Phase 151-04]: Corrected 151-MAIA-CONTRACT.md's WebGPU runtime assumption - v1.27.0 ort.webgpu.min.js requires the Asyncify wasm pair, not JSEP
- [Phase 151-04]: Kept onnxruntime-web in knip.json ignoreDependencies - worker consumes it via importScripts() in a plain public/ JS file, invisible to knip's src glob
- [Phase 151-05]: EvalBar whiteFraction override bypasses evalCp/evalMate/depth entirely (clamped 0..1) rather than partially blending, so one component serves both the Stockfish and Maia bars unambiguously
- [Phase 151-05]: MovesByRatingChart's custom tooltip is a factory function (not a TooltipContentProps<number,string>-typed component) to sidestep a recharts generic-variance TS error, mirroring ScoreChart.tsx's inline-lambda content prop
- [Phase 151-05]: EloSelector derives bounds/step from its ladder prop (default MAIA_ELO_LADDER) rather than hard-coding 1100-2000
- [Phase 151-06]: useMaiaEloDefault clamps the ELO default to the ladder [min,max] bounds only (no step-snapping); user pick wins permanently over late data loads (userOverrodeRef)
- [Phase 151-06]: useMaiaEngine mounted enabled:true (route-level React.lazy provides MAIA-02 laziness); desktop reworked into 3-column layout (Maia chart+selector left, both eval bars flanking board, engine panel right)
- [Phase 151-06]: VALID-01 APPROVED — calibration + policy-vocab move-label sanity check confirmed (closes 151-04 vocab-index risk); D-10 smallest model retained; MAIA-06 per-device latency left unmeasured, not fabricated

### Pending Todos

None active.

### Blockers/Concerns

- None active. (v1.31 and v1.32 are both deployed to production.)

### Quick Tasks Completed

| # | Description | Date | Commit | Directory |
|---|-------------|------|--------|-----------|
| 260705-bm3 | Phase 151 Maia UAT: card + header tooltip, 600–2600 range, adaptive y-axis, acknowledgement, remove legal box | 2026-07-05 | 7c0c547c | [260705-bm3-uat-feedback-phase-151-maia-card-acknowl](./quick/260705-bm3-uat-feedback-phase-151-maia-card-acknowl/) |
| 260705-dj5 | Phase 151 Maia UAT: fixed-size card + loading skeleton, wider chart with right-side move labels, horizontal grid lines | 2026-07-05 | 026e2edb | [260705-dj5-uat-feedback-phase-151-fixed-size-human-](./quick/260705-dj5-uat-feedback-phase-151-fixed-size-human-/) |
| 260705-kfg | Maia move-quality bar below Human Move Probability chart (hover-reveal move lists + severity-colored board arrows) | 2026-07-05 | 15b3a156 | [260705-kfg-maia-move-quality-bar-below-human-move-p](./quick/260705-kfg-maia-move-quality-bar-below-human-move-p/) |
| 260705-m3z | Prose position evaluation (safe/tricky/highly difficult verdict + interactive severity-colored move spans with board arrows and Maia %/eval tooltips) below the Maia move-quality bar | 2026-07-05 | b31a1f45 | [260705-m3z-prose-position-evaluation-below-the-maia](./quick/260705-m3z-prose-position-evaluation-below-the-maia/) |

## Deferred Items

Items acknowledged and deferred at **v1.32 milestone close on 2026-07-05** (acknowledged & proceed on the 31-item pre-close audit — all pre-existing standing backlog, no incomplete v1.32 work):

| Category | Item | Disposition |
|----------|------|-------------|
| debug | `entry-submit-n-plus-1` (fixed_awaiting_deploy), `insights-diskfull-shm` (awaiting_human_verify) | Carried — unrelated infra sessions, not v1.32-scoped (carried since v1.29) |
| quick_task | 19 incomplete (unknown/missing status, 260531–260616) | Resolved in fact — shipped across prior milestones; false-positive pattern (`project_stale_gsd_sdk_audit_bug`) |
| todos | 2 pending (bitboard partial-position storage; WR01-PT33 invalid Tailwind score-axis label) | Carried — long-range / cosmetic, not milestone-scoped |
| seeds | 8 dormant → now 8 active after housekeeping: SEED-081 (Maia-3 milestone) + SEED-083 (Stockfish-graded moves, shipped as Phase 151.1) moved to `seeds/closed/` at close; SEED-084 (Flaw Overlay, demoted from Phase 152) newly opened; remainder (SEED-037/042/067/069/077/078/082) future/v2 | Housekept + carried |
| known-gap | MAIA-06 per-device latency numbers never recorded | Accepted override — D-10 smallest-model choice rests on qualitative VALID-01 sign-off; no numeric board-response target was ever defined; Phase 151 verified `passed_with_override` |
| known-gap | Local in-process drain re-mints ~9/3.36M ungated cp tags | Carried from v1.30 — self-heals via tier-4, not rollback-class; `project_local_drain_ungated_tactic_tags` |
| deploy | v1.31 AND v1.32 not yet deployed to production (at v1.32 close) | Resolved — both since deployed to production |

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

**Last session:** 2026-07-05T08:32:35.940Z

**Resume file:** 

.planning/ROADMAP.md (v2.0 FlawChess Engine, Phases 153-157)
Stopped at: v2.0 roadmap created
Resume: `/gsd-plan-phase 153`

## Performance Metrics

(Cleared at v1.31 close — per-plan timings archived with the milestone.)

## Performance Metrics

| Phase | Plan | Duration | Notes |
|-------|------|----------|-------|
| Phase 151 P01 | 16min | 3 tasks | 8 files |
| Phase 151 P02 | 20min | 2 tasks | 4 files |
| Phase 151 P03 | 20min | 2 tasks | 6 files |
| Phase 151 P04 | 45min | 3 tasks | 10 files |
| Phase 151 P05 | 20min | 3 tasks | 7 files |
| Phase 151 P06 | 30min | 4 tasks | 7 files |

## Operator Next Steps

- Plan the first v2.0 phase with `/gsd-plan-phase 153`
