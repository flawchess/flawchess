---
gsd_state_version: 1.0
milestone: v2.5
milestone_name: Move Statistics
current_phase: 179
status: not-started
stopped_at: Phase 178 complete; v2.5 milestone opened, Phase 179 registered (needs planning)
last_updated: "2026-07-18T09:42:31.000Z"
last_activity: 2026-07-18
last_activity_desc: Opened v2.5 Move Statistics milestone (Phases 178–179); registered Phase 179 (SEED-112)
progress:
  total_phases: 2
  completed_phases: 1
  total_plans: 4
  completed_plans: 4
current_phase_name: two-sided-move-stats-component
---

# Project State: FlawChess

## Current Position

Milestone: **v2.5 Move Statistics — IN PROGRESS** (phases 178–179). Phase 178 (lichess-compatible accuracy & ACPL computed columns, SEED-110) is complete, 4/4 plans. Phase 179 (two-sided Move Stats component, SEED-112) is registered but **not yet planned** — next action is `/gsd-discuss-phase 179` then `/gsd-plan-phase 179`.
Phase: 179 (registered, not started)
Status: v2.5 opened; Phase 178 complete, Phase 179 needs planning
Last activity: 2026-07-18 — Opened v2.5 milestone and registered Phase 179 (SEED-112)

Prior milestone: v2.4 Backend Gem & Great Detection — CLOSED 2026-07-17 (phases 174–176, 14 plans; Phase 177 folded in as a post-close addendum 2026-07-18, 5 plans → 174–177, 19 plans).

## Project Reference

See: .planning/PROJECT.md (updated 2026-07-14 after Phase 170)
Core value: Position-precise WDL across openings + endgames + time pressure on top of users' actual chess.com / lichess games, with personalized LLM commentary and an auto-generated opening-strengths/weaknesses report.
Current focus: **v2.4 Backend Gem & Great Detection is closed (2026-07-17)** — gem/great move detection now runs in the backend full-game analysis pass as stored first-class `game_best_moves` rows (Maia-3 at eval-apply), powering the analysis board + eval chart + a Library "has gem"/"has great" filter, with an opportunistic tier-4b corpus backfill lottery (ships OFF behind `BEST_MOVE_BACKFILL_ENABLED`). All three phases (174, 175, 176) are shipped and squash-merged to `main` behind the full pre-merge gate. **Deploy pending** — v2.4 is on `main` but not yet on `production`; next action is `bin/deploy.sh`. Prior milestone v2.3 (Bot Play) closed 2026-07-15 and shipped to production via #255 (bundled with v2.1). Prior milestone v2.2 (Analysis ELO Calibration & Deep-links) closed 2026-07-11 and is live in production via #253/#254.

## Milestone Progress

Thirty-seven milestones complete (v1.0–v2.4). **v2.5 Move Statistics is now in progress.**

v2.5 Move Statistics — IN PROGRESS (opened 2026-07-18), phases 178–179. Theme: a uniform, cross-platform move-quality story surfaced in one shared UI component. **Phase 178 (complete, 4/4 plans, SEED-110)** repurposes the canonical `games` accuracy/ACPL columns (`white_accuracy`/`black_accuracy`/`white_acpl`/`black_acpl`) to hold values computed with lichess's exact formulas from the per-ply `game_positions` evals, preserving the original platform-provided numbers in new `*_imported` columns for validation; one shared `accuracy_acpl.py` compute path runs both at the live hook (`_classify_and_fill_oracle`) and in `scripts/backfill_accuracy_acpl.py`, gated on a complete per-ply eval sequence (holes → NULL); `inaccuracies`/`mistakes`/`blunders` untouched (D-04). **Phase 179 (registered, not yet planned, SEED-112)** will replace the badge rows on the Library game card and analysis board tags panel with a single shared two-sided **Move Stats** component (accuracy strip with player-color-coded cells + a 7-category Gem/Great/Best/Good/Inaccuracy/Mistake/Blunder per-player count table), split into a backend/API surfacing task (both-color accuracy + per-side per-category counts onto `GameFlawCard` and the analysis payload; NO new engine scoring — deliberately shows the opponent's positive tiers on this surface) and a frontend redesign extracting the shared component with per-cell (category × side) cycling and a still-user-scoped global filter. Depends on Phase 178.

v2.4 Backend Gem & Great Detection closed 2026-07-17 — 3 phases (174, 175, 176), 14 plans, plus a post-close addendum Phase 177 (SEED-111, 5 plans) folded into the milestone 2026-07-18 (worker-side MultiPV-2 gem-candidate offload; shipped to production via #261, not in the `v2.4` git tag). Gem/great move detection moved off the brittle client-side sweep into the backend full-game analysis pass as stored first-class `game_best_moves` rows (peers to `game_flaws`). Phase 174 (spike-gated) ports the client's 12-plane board→tensor encoding to Python, runs Maia-3 (`onnxruntime`, isolated `maia-inference` uv group) at eval-apply pinned to the mover's lichess-blitz-equivalent rating (clamped [600, 2600]), and stores a candidate row (`maia_prob` + best/second eval as floats, never a boolean) for each out-of-book played==best ply clearing `INACCURACY_DROP` (0.05) — so Gem (`≤0.20`) / Great (`(0.20, 0.50]`) thresholds retune with zero re-analysis; two SEED-109 gap-closure plans retired the lichess-eval special-case lane + backfilled the existing lichess-eval games. Phase 175 has the analysis board + eval chart + move-cycling badges + Library "has gem"/"has great" filter read the stored rows directly (client `useGemSweep` demoted to a free-play-only fallback; SEED-107 closed as superseded). Phase 176 added a backend-only tier-4b ES-weighted backfill lottery (`_claim_tier4_bestmove`) with a Maia-absence guardrail, gated behind `BEST_MOVE_BACKFILL_ENABLED` (default off). Also bundled: a CI fix installing the `maia-inference` group so `ty` resolves the onnxruntime/numpy imports. Archived to milestones/v2.4-ROADMAP.md, phases to milestones/v2.4-phases/, CHANGELOG promoted, tagged v2.4. **Deploy pending** via `bin/deploy.sh`; the tier-4b backfill flag stays OFF (D-05) and is flipped on in prod as a separately observed step post-deploy.

v2.3 Bot Play closed 2026-07-15 — 9 phases (166, 167, 168, 168.5, 169, 169.5, 170, 171, 172), 46 plans. A new top-level `/bots` page lets users and guests play a full clocked game against a calibrated FlawChess bot: a pure provider-agnostic `selectBotMove` sample↔argmax blend (166) shared by the app and a headless Node calibration harness (168, spike-gated, `onnxruntime-node`) that measures real strength across a coarse (ELO × play-style) grid; per-move search budget + confidence early-stop so moves land in seconds (168.5, SEED-096/095); dual Fischer clocks on a wall-clock delta model with fair pause/flag and bot pacing (169); a Maia-policy-weighted ECO opening book for near-instant early moves (169.5, PLAY-11); localStorage resume with the clock paused while away and exactly-once storage (170); the Bots page + setup screen + nav tying it together (171); and finished games persisted as analyzable `platform='flawchess'` Library games (167). Phase 172 (SEED-106) added a background gem sweep + opening-book markers on `/analysis` (rung pinned to the mover's rating, `GEM_MAIA_MAX_PROB` 0.10→0.20, `opening_ply_count` on-read, precedence severity > gem > book). Also bundled: quicks 260714-pnk/qaj/rj5 and 260715-als. Archived to milestones/v2.3-ROADMAP.md, phases to milestones/v2.3-phases/, CHANGELOG promoted, tagged v2.3, SEED-091 closed. **Deploy pending** via `bin/deploy.sh` (ships v2.1 + v2.3 together).

v2.2 Analysis ELO Calibration & Deep-links closed 2026-07-11 — 2 phases (164, 165), 6 plans. Phase 164 (SEED-093) seats each player's analysis-board Maia ELO at their Lichess-blitz-equivalent rating (Maia-3's training scale) via a backend `normalize_to_lichess_blitz` converter (incl. chess.com `classical` → `rapid`), two nullable `*_lichess_blitz` `GameFlawCard` fields computed on-read, and a frontend `deriveRawDefault` read-with-raw-fallback; slider info popover + inline reset. Phase 165 (SEED-094) restored an additive `?fen=<fen>` analysis deep-link (precedence game_id > fen > line) and added a headless Node gem-ELO calibration harness (onnxruntime-web Maia 6 rungs + Stockfish WASM C2 + stratified CSV → TSV in `reports/data/`, importing the real `classifyGem`/`evalToExpectedScore`/`MISTAKE_DROP`); gem generosity relaxed to Maia ≤10%. Archived to milestones/v2.2-ROADMAP.md, phases to milestones/v2.2-phases/, CHANGELOG promoted, tagged v2.2, GH release created. **Deployed to production** — released incrementally as single-phase releases #253 (164) and #254 (165); bundled into v2.2 retroactively at close.

v2.1 Analysis Eval Reconciliation & Gem Moves closed 2026-07-10 — 2 phases (162, 163), 7 plans, both frontend-only on `/analysis`. Phase 162 (SEED-090) flipped `buildEvalLookup` to grading-first precedence and introduced a single canonical `resolveReconciledBest`/`reconciledBestUci` that the board arrow, agreement verdict, eval bar, and Best/Good labels all consume, so a "Good" move can never show a higher eval than "Best". Phase 163 (SEED-092) added violet gem badges (lucide `Gem`, `MAIA_ACCENT`) for the rare move that is the engine's clearly-only good move AND hard to find at the player's rating (Maia prob ≤ `GEM_MAIA_MAX_PROB` 0.03 AND expected-score gap ≥ `MISTAKE_DROP`), surfaced on board, move list, moves-by-rating chart, and popover via a new `'gem'` `MoveQuality` bucket. No backend, no schema, no new deps. Archived to milestones/v2.1-ROADMAP.md, phases to milestones/v2.1-phases/, CHANGELOG promoted, tagged v2.1. **Not yet deployed to production** — deploy pending via `bin/deploy.sh`.

v2.0 FlawChess Engine shipped 2026-07-09 — 9 phases (153–161), 24 plans, ~51 tasks, ~69 commits over 5 days. A client-side practical-play analysis engine on `/analysis` (free analysis + game review), zero server load, no persistence, no new deps: a worker-free deterministic search core (Maia-prior-weighted expectimax backup + asymmetric self+opponent ELO, proven against fabricated providers in Phase 153 before any WASM/ONNX; depth-limited expectimax fallback on the same interface) → device-adaptive 2–4 Stockfish.wasm grading pool + dedicated Maia policy worker (154) → `useFlawChessEngine` anytime lines with objective-vs-practical score pairs (155) → amber engine board arrow (156) → aligned/safe/sharp agreement verdict, click-to-play spans (157) → one UCI-keyed lookup reconciling every displayed Stockfish eval (158, SEED-087) → ELO-scaled findability ranking + play-style temperature slider (159, SEED-085) → ad-hoc `/analysis` polish via quick/fast (160) → `100dvh` viewport-locked layout (161, SEED-088). Framing held: never "best move" unqualified. Live-browser UAT for 155/157/161 confirmed at close. Archived to milestones/v2.0-ROADMAP.md + v2.0-REQUIREMENTS.md, phases to milestones/v2.0-phases/, tagged v2.0. **Deployed to production** across releases #247 (phases 153–160), #248, #249 (viewport layout / 161).

v1.32 Maia-3 Human-Move Enrichment shipped 2026-07-05 — 2 phases (151, 151.1), 10 plans. Client-side Maia-3 (`maia3_simplified.onnx` via onnxruntime-web in a lazy Web Worker) on `/analysis`: a per-ELO "Moves by Rating" chart + a Maia WDL eval bar (LEFT; Stockfish RIGHT), live per navigation, zero server round-trip, nothing persisted. Phase 151.1 (SEED-083) recolored chart lines by Stockfish move quality and swapped the top-6 cap for the Maia ≥0.95-mass ∪ {SF-best} set via a second isolated grading worker. Repo relicensed MIT → AGPL-3.0. Phase 152 (Flaw Overlay, Pillars A+B) demoted to SEED-084; MAIA-06 latency measurement accepted as override. No schema/migration; one read-only `current_rating` backend field. Archived to milestones/v1.32-ROADMAP.md + v1.32-REQUIREMENTS.md, phases to milestones/v1.32-phases/, tagged v1.32. **Deployed to production.**

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

- Phase 178 added 2026-07-18: Lichess-compatible accuracy & ACPL computed columns (SEED-110) — compute per-game accuracy + ACPL for every analyzed game with one uniform lichess formula (confirmed from scalachess/lila source: `-0.00368208` sigmoid, `103.1668100711649·exp(...)` per-move accuracy with the `+1` uncertainty bonus, windowed-stddev-weighted `(weightedMean+harmonicMean)/2` aggregation seeded at 15cp, ±1000 cp ceiling) into four NEW `games` columns, leaving the existing chess.com-accuracy / lichess-acpl columns untouched as a comparison/validation signal. Per-ply eval comes from whatever analyzed the game (`game_positions.eval_cp`), so the uniform formula reproduces lichess's own accuracy for lichess games (validation surface) and gives our-Stockfish-through-lichess-formula for chess.com/self-analyzed games. Single Python path shared by the live hook (full-eval completion) and a `scripts/backfill_*.py`; complete-sequence gate (eval holes → leave NULL, since the sliding volatility window silently distorts on a hole). Placed after Phase 177 in the v2.4 milestone; `phase.add` numbered 178 sequentially. Open plan-time questions in the seed: exact live-hook seam, `eval_cp` sign + post-move-shift mapping, terminal-ply/0–1-move handling, column names+migration (SMALLINT acpl / REAL accuracy), ~718k-game backfill batching.
- Phase 177 added 2026-07-17: Worker-side MultiPV-2 gem-candidate searches, protocol v2 (SEED-111) — move the gem-candidate runner-up (MultiPV-2, 1M-node) searches off the prod server's Stockfish pool onto the workers (targeted re-search after the MultiPV-1 pass; submit schema v2 gated at the atomic lease; instrumented server fallback), so atomic-submit apply becomes pure Maia + classify + DB writes and tier-4b backfill throughput scales near-linearly with the fleet (measured 2026-07-17: server pool ~92% pinned, fleet engines ~32% idle, ~550 games/h). Standalone post-v2.4 phase (same pattern as Phase 173); numbered and placed manually — mature-ROADMAP `phase.add` misnumbers/misplaces (known behavior, see Phase 164/172 entries).
- v2.4 Backend Gem & Great Detection roadmap created 2026-07-16 — 3 phases (174–176) in 2 dependency waves (A={174}, B={175,176}), continuing absolute numbering from Phase 173 (the v2.3 post-close anchor-calibration addendum). All 11 requirements (GEMS-01..07, BOARD-01/02, FILT-01, BACK-01) mapped 1:1, no orphans. Keystone Phase 174 (backend Maia inference + best-move storage, spike-gated on a Python encoding-parity check mirroring Phase 168's Maia-in-Node feasibility gate) gates everything else; Phases 175 (board + Library-filter frontend consumption) and 176 (opportunistic corpus backfill) depend only on 174, not on each other. UI hint on Phase 175.
- Phase 172 added 2026-07-14: Background Gem Sweep on Analysis (SEED-106) — resolve gems for the whole mainline in the background (free `played === best_move` + out-of-book prefilter → Maia C1 → Stockfish parent grade), pin the gem rung to the mover's own seeded rating instead of the ELO slider, raise `GEM_MAIA_MAX_PROB` 0.10 → 0.20, and add `opening_ply_count` (computed on-read, no migration) for book markers with precedence `severity > gem > book`. Added to the **v2.3 Bot Play** milestone by explicit user choice even though it is an `/analysis` feature, not bot play — Adrian chose "extend v2.3" over closing the milestone first (2026-07-14); revisit the boundary at milestone close. User amendment at add time: SEED-106 D3 extended so the sweep triggers on analysis *becoming* ready (bot games analyzed in the background on the live-updating analysis board), not only on mount-time readiness. `gsd-tools phase.add` numbered it 172 correctly but appended the section to the end of the file after the archived `<details>` history — moved into the active milestone by hand (the known mature-ROADMAP behavior).
- v2.3 Bot Play roadmap created 2026-07-11 — 6 phases (166–171) in 3 dependency waves (A={166,167}, B={168,169}, C={170,171}), continuing absolute numbering from v2.2's Phase 165. All 26 requirements (BOT/PLAY/STORE/RESUME/CAL) mapped 1:1, no orphans. Keystone Phase 166 (`selectBotMove` two-regime sample↔argmax blend) is imported by both the play loop and the calibration harness; Phase 167 (backend store-on-finish) is fully independent. Phase 166 (slider→temperature/threshold curve + regime discontinuity) and Phase 168 (Maia-in-Node feasibility spike + `onnxruntime-node` version) flagged for plan-time research/spike. UI hints on Phases 169 (clocked board) and 171 (Bots page/setup).
- Phase 165 added: Gem-move ELO calibration harness + restore `?fen=` analysis deep-link (from SEED-094) — headless Node harness measuring raw Maia prob per ELO rung over ~3000 Kaggle "brilliant" moves (empirical basis for Phase 163 D-08's ELO-scaled iso-rarity ceiling), plus an additive `?fen=` analysis deep-link so the TSV positions are clickable. gsd-tools phase.add numbered it 165 sequentially (164 is the only phase left in `.planning/phases/`).
- Phase 164 added: Maia ELO Lichess-blitz normalization (from SEED-093) — normalize player ratings to Lichess-blitz for the analysis-board Maia ELO slider default. Numbered manually 164 (gsd-tools phase.add proposed 1 because completed phases are archived out of `.planning/phases/`; project uses absolute numbering).
- v2.0 FlawChess Engine closed 2026-07-09 (Phases 153–161; tag v2.0). Grew beyond its planned 153–159 scope to include Phase 160 (ad-hoc `/analysis` UI polish, artifact-free quick/fast bucket) and Phase 161 (SEED-088 viewport-locked layout); ROADMAP header lagged at "153–159" until close, corrected to 153–161. Live-browser UAT for 155/157/161 confirmed at close. Roadmap + requirements archived to `milestones/v2.0-ROADMAP.md` + `v2.0-REQUIREMENTS.md`, phases to `milestones/v2.0-phases/`. Reset for the next milestone.
- v1.31 Pipeline Consolidation closed 2026-07-04 (Phases 148, 149, 150; tag v1.31). Execution decisions + quick-task log archived to `milestones/v1.31-ROADMAP.md`, PROJECT.md Key Decisions, and git. Reset for the next milestone.
- Phase 151.1 inserted after Phase 151: Stockfish-graded Maia moves on the Moves-by-Rating chart (from SEED-083)
- Phase 158 added: FlawChess Engine displayed-eval provenance reconciliation (SEED-087, amended with third Maia-card provenance chain + shared-fallback design)
- Phase 159 added: FlawChess Engine policy temperature + root-move findability (SEED-085, Threads A + B committed)
- Phase 160 added: Analysis page layout and card/element UI polish — ad-hoc improvements via /gsd-quick and /gsd-fast, no preplanning
- Phase 161 added: Analysis page viewport-locked responsive layout (SEED-088) — fix small-laptop bottom cutoff via 100dvh lock, height-bound board, fluid grid, Tags relocation
- Phase 162 added: Grading-run-authoritative eval reconciliation — precedence flip (SEED-090, preferred over SEED-089's unified pass; frontend-only, grading run becomes authoritative for all displayed per-move evals)
- Phase 163 added: Gem moves — Maia-findability move badges on /analysis (SEED-092; escalated from a /gsd-quick request 2026-07-10 — sized as phase-scale: ~10+ files, new detection module, open tunables)
- Phase 169.5 inserted: Bot Opening Book — inserted 2026-07-13 after a /gsd-explore session on slow bot first moves. Maia-policy-weighted ECO book (frontend/public/openings.tsv) for the early plies; no search, no backend, no re-calibration (the harness already starts from book FENs). New requirement PLAY-11.
- Phase 173 added: Anchor ladder self-calibration (SEED-101) — round-robin maia/SF anchors, fit internal rating scale; unblocks SEED-102

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
- [Phase 153]: MoveGrade re-exported from moveQuality.ts in types.ts (single import surface), not redeclared
- [Phase 153]: leafExpectedScore wraps liveFlaw.ts's evalToExpectedScore verbatim; mate-near-certainty test thresholds set to 0.95/0.05 matching actual sigmoid output
- [Phase 153-02]: backupExpectation's empty-array case is a natural consequence of the totalPrior===0 guard, tested explicitly alongside the plan-specified totalPrior===0 case
- [Phase 153-03]: selectChild() throws on empty children array (Rule 2 precondition validation) rather than returning a sentinel - no sensible default UCI move exists
- [Phase 153-03]: D-01 root/non-root split test uses ONE shared children fixture (rootExplorationPrior tied, plain prior differs) proving the SAME object selects differently by isRoot flag alone
- [Phase 153]: [Phase 153-04]: extraRootMoves unioned with the truncated Maia top-k AFTER truncateAndRenormalize (not before) to satisfy D-05's floor-boost rationale
- [Phase 153]: [Phase 153-04]: Visit-count increments deferred from selection/dispatch time to apply time - isPending alone prevents same-round re-picks; eager bumping broke ENGINE-07 snapshot-sequence determinism at concurrency=2
- [Phase 153]: [Phase 153-04]: Added selectPath root-pending guard (Rule 1 bug fix) - child-level pending filter never protected the walk's own starting node
- [Phase 153-05]: fallbackExpectimax reuses backup.ts/leafScore.ts/select.ts, ignores budget.concurrency entirely (purely sequential walk), and matches mctsSearch's visits/modalPath semantics for output-shape parity
- [Phase 153-05]: knip passed unchanged with no knip.json edit needed — the anticipated engine-export-consumed-only-by-tests caveat did not trip knip's vitest-plugin entry-point detection
- [Phase 154-01]: grade() uses priority=0/depth=0 internally since the frozen 2-arg EngineProviders.grade signature has no priority channel; the priority queue's ordering logic itself is fully built and unit-tested per POOL-02, ready for a future caller
- [Phase 154-01]: pool.grade's third signal?: AbortSignal param is an ADDITIONAL optional parameter, keeping it structurally assignable to EngineProviders['grade'] per TypeScript's trailing-optional-param assignability rule
- [Phase 154-01]: Reverted requirements.mark-complete's POOL-04 checkbox flip: POOL-04 is shared across Plans 01/02 (frontmatter) — 154-01 only partially delivers it (Stockfish-pool adaptive sizing + lazy spawn/abort surface); left [ ] Pending with a partial-delivery note; Plan 02 will actually close it
- [Phase 154-02]: requestPolicy pipeline (dedup/cache/FIFO/SAN-UCI) committed as Task 1 without terminate()/Sentry/graceful-degradation, then Task 2 layered worker lifecycle + error forwarding on top
- [Phase 154-02]: same-fen batching collapses ANY pending requests sharing a FEN into one analyze call with the deduped ELO set, beyond the literal two-same-ELO-requests example
- [Phase 154-02]: worker error / construction failure both resolve affected policy() promises to {} rather than reject, mirroring workerPool.ts's resolve-empty-on-failure precedent
- [Phase 154-02]: POOL-04 marked complete; SC4 real-device UAT and eval-bar mutual-exclusion wiring remain deferred to Phase 155 per CONTEXT.md D-03, tracked in 154-VALIDATION.md
- [Phase 154-03]: Used a dedicated PoolWorkerSlot.dead boolean rather than inferring pool failure from isReady, to avoid a false-positive drain during normal not-yet-ready startup — isReady is also false during normal init before uciok/readyok, so an inference-based all-failed check would incorrectly drain valid pending requests
- [Phase 154-03]: WR-02 fixed as a documentation-only correction: priority/depth stay 0 under the frozen 2-arg grade() contract until Phase 155 supplies a real caller — No caller exists yet in Phase 154 to supply real priority values; the ordering machinery itself is already correct and unit-tested
- [Phase 154]: [Phase 154-04]: Task 1 committed as a standalone inline fix (no shared helper) so its commit is self-contained; Task 2 extracted settleAllAndDropWorker() and layered the onerror handler on top, per plan's explicit permission to factor shared logic in Task 2
- [Phase 155-01]: expectedScoreToWhitePovCp special-cases es<=0/es>=1 to +/-MATE_CP_EQUIVALENT*sign (mirroring evalToExpectedScore's mate-before-sigmoid convention) instead of a literal log-odds inverse — avoids Infinity/NaN blow-up on a genuine forced-mate subtree (Pitfall 2)
- [Phase 155-01]: Switch's checked-track fill defaults to bg-primary but is caller-overridable via className, not a single hardcoded accent baked into the primitive — each engine card (Stockfish/Maia/FlawChess) needs its own switch tint (D-03)
- [Phase 155-01]: Reverted requirements.mark-complete's DISPLAY-03 checkbox flip — DISPLAY-03 is shared across Plans 01/03 (frontmatter) — 155-01 alone only delivers the expectedScoreToWhitePovCp conversion function; left [ ] Pending with a partial-delivery note; Plan 03 (the visible score-pair badge) actually closes it
- [Phase 155-02]: budget.elo = { w: elo, b: elo } — both colors share the single on-page ELO in free analysis (D-07/Open Question 2); true self/opponent asymmetry deferred to Phase 157
- [Phase 155-02]: lastCommitAtRef reset to 0 at the start of every fresh mctsSearch call, not just on hook mount, so the D-09 first-paint guarantee holds on every FEN navigation
- [Phase 155-02]: abortControllerRef.abort() + pool.stopAll() called unconditionally at the top of the search-trigger effect (including the first search, where stopAll is a harmless no-op) — matches 155-RESEARCH.md Pattern 2 literally
- [Phase 155-02]: Reverted requirements.mark-complete's DISPLAY-01 checkbox flip: DISPLAY-01 is shared across Plans 02/04 (frontmatter) — 155-02 alone only delivers the hook's throttle/abort mechanics; left [ ] Pending with a partial-delivery note; Plan 04 (surfacing on /analysis) actually closes it
- [Phase 155-03]: Exported replayPvLine/formatScore from EngineLines.tsx (additive only) and gave EngineLinesSkeleton a rows?: 2|3 prop rather than duplicating logic or writing a second skeleton
- [Phase 155-03]: FlawChessEngineLines has no compact prop - card placement/mobile-tab wiring is Plan 04's job per this plan's Out-of-Scope section
- [Phase 155-03]: DISPLAY-02 and DISPLAY-03 marked fully complete - DISPLAY-02 was never shared with another plan, and DISPLAY-03's Plan 01/03 split closes here per REQUIREMENTS.md's own note
- [Phase 155-04]: Combined Task 1+2 into one commit — topLine/flawChessEngine's mount is inert until Task 2 consumes it, so a Task-1-only commit would fail its own tsc --noEmit gate under noUnusedLocals
- [Phase 155-04]: Expanded files_modified to include MaiaHumanPanel.tsx — the Maia card header lives there, not in Analysis.tsx; added optional enabled/onToggleEnabled props, no-op when omitted (preserves the locked 151.1 compact-drops-header test)
- [Phase 155-04]: FlawChess card wrapper uses testid analysis-flawchess-panel (not analysis-flawchess-card, already used by FlawChessEngineLines.tsx's own root div) to avoid a duplicate-testid collision
- [Phase 155-04]: engineLoading gained a && !flawChessEnabled guard (Rule 1 bug fix) — without it the Stockfish card's loading skeleton spins forever once FlawChess suppresses the standalone search (both default ON)
- [Phase 155-04]: No isError/FlawChess-unavailable state wired — the frozen Plan 02 hook exposes no error field (worker/pool failures resolve to empty results internally); documented as a known gap rather than fabricated
- [Phase 157-01]: D-04 aligned check is UCI-string equality before the drop split, not derived from drop === 0
- [Phase 157-01]: SHARP_DROP_THRESHOLD is the imported BLUNDER_DROP alias -- no bare 0.15 literal
- [Phase 157-01]: FlawChess-side FlawChessVerdictMove always sets evalMate: null (Pitfall 4 -- RankedLine has no mate field)
- [Phase 157-02]: ProseSpan extracted (not duplicated) into a shared content-agnostic hover/click-to-play shell
- [Phase 157-02]: Main verdict sentence cites each pick's objective eval (not practicalScore-derived) to stay consistent with the win%-drop tier split; the D-10 popover separately shows the practical-converted number
- [Phase 157-02]: Aligned tier renders a single shared ProseSpan (FlawChess pick's own span/popover) rather than a distinct combined-role type
- [Phase 158-01]: Chosen grading budget: movetime=4000ms, no depth clause (pure movetime cap) — measured via headless WASM sweep to reach depth parity with the free run and agree within noise on shared candidates
- [Phase 158-01]: Rule 1 bug fix — go-command clause order: searchmoves must be LAST (trailing movetime was silently swallowed as an illegal move token, so the old 2500ms cap never actually limited search time)
- [Phase 158-01]: Free-run MULTIPV left at 2 unchanged — widening it only costs search depth with no meaningful union-coverage benefit
- [Phase 158-02]: buildEvalLookup takes exactly 3 params (pvLines, gradeMapBySan, baseFen) — no pool-grade parameter, structurally excluding a shallow MCTS pool eval from ever surfacing through this lookup
- [Phase 158-03]: Task 1+2 combined into one commit — interleaved memo chain (unionSans/gradingEnabled -> evalLookup -> reconciledRankedLines -> qualityBySan -> engineTopLines), mirrors 155-04 precedent
- [Phase 158-03]: qualityBySan's reconciled grade map is keyed by grading.gradeMap's own SAN set (not a fresh union) — preserves identical classification coverage, only the resolved values are reconciled
- [Phase 159-01]: P_REF_ANCHORS starting hypothesis taken verbatim from RESEARCH.md; flagged as assumption pending live UAT validation (159-04)
- [Phase 159-01]: buildRankedLines pairs each RankedLine with a sort-only rankScore via a parallel array (not spread-and-omit) to keep eslint no-unused-vars clean
- [Phase 159-02]: rawProbBySan and shownSans made REQUIRED props on FlawChessAgreementVerdictProps (not optional) - Analysis.tsx always has this data; all 11 pre-existing component tests updated with the two new props
- [Phase 159-02]: D-11 fallback wording is tier-nearlySameEval-aware (4 total safe-tier variants: gate x nearlySameEval), not a single flat fallback string
- [Phase 159-03]: ROOT_CANDIDATE_HARD_CAP set to 15 (D-07/Pitfall 6 discretion) - generous at T~1, bounded at T=2.0 against the 400-node budget
- [Phase 159-03]: sideMatchesMover and applyRootCandidateHardCap placed in treeCommon.ts (shared cross-runner file) rather than inlined per-runner, structurally preventing Pitfall 3 divergence
- [Phase 159-03]: Opponent-untouched (D-05) test proven via the exact candidateUcis recorded at grade() call time (2 kept at T=1 raw vs 4 at T=2 flattened on the same distribution shape), not via output inference
- [Phase 159-04]: TEMPERATURE_DEFAULT imported directly from DEFAULT_POLICY_TEMPERATURE rather than declared as a matching literal - makes the Pitfall 7/T-159-08 invariant (slider center === search no-op value) structural, not just test-covered
- [Phase 159-04]: TemperatureSelector rendered exactly once, inside the pre-existing shared eloSelector JSX const (already rendered in both the mobile humanTab and desktop human column) - mobile/desktop parity via one render site, not two
- [Phase 159-04]: policyTemperature defaulted (?? DEFAULT_POLICY_TEMPERATURE) at useFlawChessEngine's own SearchBudget-construction call site, not inside a helper - keeps the no-op short-circuit visible at the orchestrator layer per 159-03's established Pitfall 1 discipline
- [Phase 162-01]: Kept the exact !lookup.has(uci) insertion-order-wins guard on both loops in buildEvalLookup — only reordered which loop runs first (grading loop before free-run loop)
- [Phase 162-01]: resolveReconciledBest co-located in engineEvalLookup.ts (not moveQuality.ts), reusing evalToExpectedScore/MoverColor from @/lib/liveFlaw verbatim
- [Phase 162-02]: freeRunCommitted declared as plain const (not useMemo) — cheap boolean, no memoization overhead
- [Phase 162-02]: reconciledBestUci iterates grading.gradeMap.keys() directly (Pitfall 3 keyspace), not the broader unionSans
- [Phase 162-02]: D-03 mirror-image test verified via MaiaMoveQualityBar's positionVerdict prose (escape/bad roles), not the recharts-based MovesByRatingChart, to avoid adding ResponsiveContainer mock machinery Analysis.test.tsx doesn't already carry
- [Phase 162-03]: Tasks 1+2 combined into one commit — interleaved reconciled memo chain (reconciledStockfishLine beside reconciledBestEval), mirrors 155-04/158-03 precedent
- [Phase 162-03]: D-12 arrow test verified via scoped Element.prototype.clientWidth spy + SVG path-string diff, not geometry decoding — jsdom's default 0 clientWidth degenerates ArrowOverlay paths to NaN
- [Phase 163-01]: classifyGem takes no ply/color argument by construction — satisfies D-02/D-04 structurally, not just via test coverage
- [Phase 163-01]: Free-lunch guard 1 (saturation) test uses +1000/+600 cp instead of the plan's illustrative +800/+400 — the real LICHESS_K sigmoid only compresses the ES gap below MISTAKE_DROP at higher cp magnitudes
- [Phase 163-01]: bucketKeyForQuality('gem') coverage verified via bucketMovesByQuality (its only real caller) rather than exporting the previously-private bucketKeyForQuality function
- [Phase 163-02]: GEM_ICON_DIAMETER_RATIO (0.8) added as a named constant for the gem icon's size relative to the badge circle diameter, not a new geometry/position constant
- [Phase 163-02]: SquareMarkerBadge restructured so cx/cy/r are computed once up front, then branches gem vs. guarded severity lookup, to avoid indexing SEVERITY_GLYPH with an undefined key now that severity is optional
- [Phase 163-03]: Pitfall-5 audit recorded inline via commit message -- colorForQuality's switch is the only quality-string branch in MovesByRatingChart.tsx; stroke emphasis keys off SAN identity not quality
- [Phase 163-03]: isGem threaded through ProseMoveSpan as a required boolean prop computed by the parent (renderMove), not read from qualityBySan inside the child
- [Phase 163-03]: Gem copy row in UnifiedMovePopover uses colSpan={2} -- a single declarative sentence, not a label+value pair like the source rows
- [Phase 163-04]: Task 1+2 combined into one commit (interleaved memo chain) - Task 1's per-FEN caches are unread until Task 2's gemCandidate memo consumes them
- [Phase 163-04]: moveListMarkers gem fold has no mainLineSet exclusion - gemActive covers mainline AND free variations (D-05), and moveListMarkers is VariationTree's only data source
- [Phase 163-04]: Rule 1 fix - boardSquareMarkers reads the LIVE gemCandidate memo (not the sticky gemByNode cache) so an ELO-slider change can hide an already-shown board badge, mirroring liveFlaw (live)/liveFlawByNode (sticky) split
- [Phase 164-01]: Leftmost-tie-wins via bisect_left's exact-match branch resolves the classical column's 1935 tie to anchor 1500 (zero-width guard is defensive, not the branch actually exercised)
- [Phase 164-01]: chess.com Daily represented via is_correspondence=True (no distinct source_tc literal exists) since TimeControlBucket has no 'daily' member
- [Phase 164-01]: lichess+blitz excluded from the six convertible out-of-range combos - unconditional identity with no range check
- [Phase 164-02]: cast(Platform, game.platform) / cast(TimeControlBucket, game.time_control_bucket) narrows the DB's plain str columns to normalize_to_lichess_blitz's Literal params, mirroring endgame_service.py's existing cast(TimeControlBucket, tc_str) precedent
- [Phase 164-02]: _seed_db_game extended with optional white_rating/black_rating/time_control_str/time_control_bucket params (defaults unchanged) instead of a parallel seeding helper
- [Phase 164-03]: Both new *_lichess_blitz fields kept optional (?: number | null) on both TS types (Pitfall 5) so existing fixtures compile and a missing value falls back to raw via ??
- [Phase 164-03]: Updated useMaiaEloDefault.ts's top-of-file doc comment to describe the normalized-rating-first D-07 rule, kept in sync as part of Task 1
- [Phase 165-01]: Grade Stockfish C2 over ALL legal root moves (not the frontend's display-union) for an honest playedIsBest in calibration
- [Phase 165-01]: Apply expensive FEN/SAN validation lazily only to reservoir-slot candidates during stratified sampling, not all ~22M CSV rows
- [Phase 165-01]: Dedupe quantile strata edges to avoid degenerate empty strata from tied score values undercounting --n
- [Phase 165]: ?fen= restored additively alongside ?line= (not a revert) per SEED-094/D-06 for arbitrary mid-game snapshot loading
- [Phase 165]: Precedence game_id > fen > line enforced via rootFenSeed === null guard on shared hasLoadedMainLine ref (T-165-04)
- [Phase 166-01]: TAU_EPSILON = 1e-9 short-circuit kept as a cheap defense alongside sampleRankedLines's max-subtraction stability trick (RESEARCH Open Question 1)
- [Phase 166-01]: BotSettings/BotMoveDeps co-located in selectBotMove.ts, not types.ts (RESEARCH Open Question 2) — a Phase-166-owned contract layered on the frozen Phase 153 core, not a modification to it
- [Phase 167]: Platform Literal extended only in app/schemas/normalization.py (D-17); left unrelated inline filter Literals untouched per RESEARCH Pitfall 4
- [Phase 167]: bot_elo bounded 600-2600 (BOTX-01 range) via Pydantic Field ge/le
- [Phase 167]: Autogenerate correctly emitted CheckConstraint + ondelete=CASCADE for bot_game_settings on first attempt, no hand-editing needed
- [Phase 167-02]: D-02 implemented as a module constant (DEFAULT_EXCLUDED_PLATFORMS) + platform-None else-branch in apply_game_filters, excluding flawchess from every default analytics population
- [Phase 167-02]: D-03 implemented as a local variable at the get_library_games call site, not a new apply_game_filters parameter, keeping the exclusion centralized
- [Phase 167]: 167-03: normalize_flawchess_game takes an explicit user_id param (required NormalizedGame field, not in the plan's prose signature)
- [Phase 167]: 167-03: tc_str is fed directly into parse_time_control in the existing seconds-based format; flagged for Phase 169/171 if the wire tc_preset value is ever a minutes-based label
- [Phase 167]: 167-03: PGN [Termination "..."] header takes precedence over board-state derivation for termination
- [Phase 168]: Refactored (not duplicated) Maia/Stockfish bring-up out of gem-elo-calibration.mjs into scripts/lib/node-engine-providers.mjs, re-imported unchanged
- [Phase 168]: nodeGrade built from workerPool.ts's sendGo/handleLine pattern (UCI-keyed, searchmoves-restricted, depth-carrying), not gem-elo's SAN-keyed gradePosition
- [Phase 168]: Opening book (33 entries) generated by replaying SAN lines through chess.js, guaranteeing legality
- [Phase 168]: Stockfish pool (workerPool.ts slot-queue analog) parallelizes grade() across N processes: blend=1 full-budget move 190s (1 proc) -> 92s (4 procs), 2.07x speedup — CAL-03 spike found grade() serialization on a single shared Stockfish process was the throughput bottleneck, not Maia/ONNX
- [Phase 168]: TSV row granularity is per (bot-cell x anchor) cell, streamed durably as soon as each cell's games-per-cell games finish — Reconciles D-04's literal per-cell row schema with WR-01/D-06's incremental-durability requirement
- [Phase 168]: D-09 determinism check is probabilistic, not a hard guarantee, on a loaded machine — root-caused to a pre-existing D-10 adjudication-eval fragility, confirmed via A/B test against untouched Plan 02 code, not a Plan 03 regression — Movetime-only adjudication eval with no depth ceiling is inherently sensitive to real wall-clock timing, cascading into subsequent grade() hash state; redesigning D-10 is out of this plan's scope
- [Phase 168.5-01]: Phase 169 SC1 amended to D-04 pacing sentence (fixed shipped budget, randomized reveal delay, fraction-of-remaining synthetic clock debit, bot never flags)
- [Phase 168.5-01]: SEED-091 clock/fixed-strength fork resolved as fixed strength + synthetic bot clock (D-01), original deferred prose annotated not deleted
- [Phase 168.5-02]: ADJUDICATION_TARGET_DEPTH finalized at 10 (measured mean 18ms/max 57ms per call) - no need to lower to 8
- [Phase 168.5-02]: GRADING_WATCHDOG_TIMEOUT_MS=60000 / ADJUDICATION_WATCHDOG_TIMEOUT_MS=20000 confirmed generous (~33x/~350x margin over worst observed latency)
- [Phase 168.5-02]: ENGINE_RETRY_ATTEMPTS=2 (3 total attempts), gated strictly to the waitFor timeout error message pattern, never a bare catch-all
- [Phase 168.5-03]: Stop-rule check reads root.children's .value directly (== practicalScore) in the existing canonical apply-order loop — never buildRankedLines' findability-sorted rankScore (Pattern 2)
- [Phase 168.5-03]: buildSnapshot's new stopReason param defaults to null so untouched fallbackExpectimax.ts callers keep compiling unchanged, rather than making it a required arg
- [Phase 168.5-03]: All FLAWCHESS_BOT_* values shipped as PROVISIONAL placeholders per RESEARCH.md Pattern 1; Plan 04 locks final numbers from harness measurement
- [Phase 168.5]: FLAWCHESS_BOT_MAX_NODES=50/_MAX_PLIES=8/_CONCURRENCY=4/_STOP_RULE(marginThreshold=0.05,epsilonThreshold=0.02,stabilityWindow=3,minNodes=8) locked from real-engine measurement — validated the Plan 03 provisional values without change (median ~5.4s, worst-case ~12.7s)
- [Phase 168.5]: calibration-harness.mjs playGame's SearchBudget now carries stopRule + PINNED FLAWCHESS_BOT_CONCURRENCY (not pool.size) — app==harness determinism no longer silently tracks --stockfish-procs
- [Phase 168.5-05]: D-15 dynamic-cutoff traversal resolved as bracket-and-expand (split in-window anchors at the bot-cell's own rating, walk each side outward) rather than a single whole-window ascending pass -- the literal ascending-only reading makes the skip-weaker half vacuous
- [Phase 168.5-05]: ANCHOR_ELO_WINDOW=400, DYNAMIC_CUTOFF_SCORE_EPS=0.05 set from Claude's Discretion, bracketing every D-14 default bot ELO against at least one Maia rung each side
- [Phase 168.5-05]: SC5 determinism check now proves the SHIPPED FLAWCHESS_BOT_* budget (50 nodes/8 plies/stop-rule/concurrency=4) -- passed, byte-identical 29-ply blend=1 game
- [Phase 168.5-05]: D-17 bounded pilot via the real harness pipeline confirms the pacing band (median 3.32s, p95 16.72s) under measured CPU contention from a concurrent background sweep; full ~24h re-calibration sweep handed to the operator per D-16, not launched in-phase
- [Phase 169-01]: chessClock constants set to CONTEXT.md suggested defaults verbatim (REVEAL_DELAY 500-1500ms, SYNTHETIC_DEBIT_DIVISOR=20, SYNTHETIC_INCREMENT_SHARE=0.9, NEVER_FLAG_FLOOR_MS=1000, LOW_TIME_THRESHOLD_MS=10000) — No deviation needed; CONTEXT.md's Claude's-discretion defaults already tuned for plausible 5+0 blitz pacing
- [Phase 169-01]: Reverted requirements.mark-complete's PLAY-03/04/05 checkbox flip — PLAY-03/04/05 are shared across Plans 01/04/05 (frontmatter) — 169-01 alone only delivers the chessClock math primitives; left [ ] Pending with a partial-delivery note; Plan 04 (useBotGame) actually closes them
- [Phase 169-02]: Reused MoverColor from @/lib/liveFlaw for winner/userColor instead of a duplicate type; finalizeBotPgn additionally sets a [TimeControl] PGN header from tcStr for fidelity even though the backend receives tc_str as a separate param, not parsed from the header
- [Phase 169-02]: Reverted requirements.mark-complete's PLAY-06/07/09 checkbox flip: shared across Plans 02/04 (frontmatter; PLAY-07 also Plan 05, PLAY-09 also Plan 06) — 169-02 alone only delivers the pure board-detection/draw-gate/PGN-builder logic; left [ ] Pending with a partial-delivery note; Plans 04/05/06 actually close them
- [Phase 169-03]: Vendored lila sfx directory (Enigmahack, AGPLv3+) instead of the non-free 'standard' set D-08 originally named (RESEARCH Pitfall 1 correction)
- [Phase 169-03]: Checkmate.mp3 reconstructed as a byte-copy of Check.mp3 since raw.githubusercontent.com serves lila's own symlink as literal target-path text, not resolved binary content
- [Phase 169-03]: SoundEvent's single 'game-end' member maps to Checkmate.mp3; Victory/Defeat/Draw remain vendored but unused by sounds.ts today for a future finer-grained surface
- [Phase 169-04]: D-01 draw-accept score refreshed via best-effort non-blocking pool.grade() after each bot move — selectBotMove exposes no snapshot/practicalScore, only the resolved UCI; defaults to neutral 0.5 which correctly falls through the endgame gate before any bot move resolves
- [Phase 169-04]: commitMove(move, mover, debitMs) shared by user and bot move paths — caller supplies raw elapsed time or the D-05 reconciled never-flag debit; end-conditions test coverage is checkmate+threefold+flag-on-time since stalemate/fifty-move/insufficient-material are already exhaustively fixture-tested in Plan 02's botGameEnd.test.ts
- [Phase 169]: CLOCK_LOW_TIME_URGENT set to the exact shadcn --destructive oklch value rather than a new hand-picked red, for consistency with other destructive surfaces
- [Phase 169]: HorizontalMoveList.tsx extended with an optional activeItemClassName override (default unchanged) so MoveListPanel's brand-brown live-ply highlight doesn't require duplicating the shared shell or touching existing callers
- [Phase 169]: GameControls' resign trigger Button is a sibling of <Dialog>, not nested inside it -- mirrors the existing FeedbackButton/FeedbackModal controlled open/onOpenChange split since dialog.tsx has no DialogTrigger export
- [Phase 169-06]: GameResultStrip replaces GameControls in the panel (not shown alongside it) once the dialog is dismissed, per the UI-SPEC's 'replacing the normal in-game controls area' wording
- [Phase 169-06]: Bots.tsx renders a single mounted tree via a matchMedia isDesktop flag (mirroring Analysis.tsx's useIsMobile precedent) instead of two CSS-hidden trees, since ClockDisplay/MoveListPanel/GameControls carry fixed non-parameterizable data-testids
- [Phase 169-06]: D-14 stub settings (botElo 1500, blend 0.5, lichess 5+3, userColor white) start the game immediately on route load; PLAY-09's REQUIREMENTS.md traceability row updated to Complete (mark-complete reported the checkbox already set)
- [Phase 169-08]: D-16 deadline constants tuned by feel (BOT_MOVES_TO_GO=30, BOT_THINK_INCREMENT_SHARE=0.7, min/max band 800-15000ms, BOT_MOVE_OVERHEAD_MS=300) against the 168.5-04 measured search cost (median ~5.4s, worst-case ~12.7s) -- a full 5+3 clock yields a ~12.1s deadline
- [Phase 169-08]: createDeadlineSearch uses an inner AbortController isolated from the caller's outer signal so a deadline cut and a cancel can never be confused -- the two-signal design, not a reason tag
- [Phase 169-08]: Reverted requirements.mark-complete for PLAY-04/PLAY-05 -- shared with Plan 09 (frontmatter), which also owns the REQUIREMENTS.md/168.5-CONTEXT.md/botBudget.ts doc amendments per its own Task 3; this plan delivers only the honest-clock math + deadline-search wrapper
- [Phase 169-09]: resetTurnAnchor() re-baselines pausedAtRef alongside turnStartedAtRef whenever the anchor resets (commitMove, newGame) -- the single fix point for WR-02's future-dated-anchor bug
- [Phase 169-09]: commitMove computes wasLive from viewedPlyRef/liveGamePlyRef (both refs kept fresh outside the render cycle) rather than closing over moveHistory/viewedPly state, which would be permanently stale since commitMove's deps don't include either
- [Phase 169-09]: Test G (WR-03) captures a real stale closure (result.current.offerDraw taken before checkmate) rather than trying to win a React effect-flush race -- deterministic and mirrors the bug report's actual mechanism; wouldBotAcceptDraw forced true via a test-only override since Fool's-mate never satisfies the real endgame gate
- [Phase 169-09]: 168.5-CONTEXT.md D-01/D-02/D-04 get SUPERSEDED annotations appended (original text preserved) rather than rewritten, so the historical record stays intact and future verifiers don't re-fail the phase on stale prose
- [Phase 169-10]: computeChargeableElapsedMs delegates to the existing computeElapsedMs primitive with pausedAtMs ?? nowMs as the effective now, rather than duplicating the subtraction
- [Phase 169-10]: flagIfOutOfTime sets the flagged mover's clock to 0 directly before calling finalizeGame, called BEFORE chess.move() in both attemptMove and runBotTurn, replacing the 100ms tick as the sole flag detector
- [Phase 169.5-01]: OpeningLookup interface bundles fullLineMap + prefixSet as buildLookup()'s single cached return shape, keeping fetch/parse shared between both query directions
- [Phase 169.5-01]: loadOpeningPrefixSet() does not swallow fetch errors (unlike preloadOpenings()) — the future book caller (plan 04) decides how to react to a rejected promise
- [Phase 169.5-01]: Did not run requirements.mark-complete for PLAY-11 — shared across all 4 plans in this phase (frontmatter); 169.5-01 alone only delivers the candidate-generation half (prefix set + corpus-parity guard); left [ ] Pending with a partial-delivery note
- [Phase ?]: D-08 RESOLVED: botGameSnapshot persists chess.pgn() (not SAN+clk-array); a clean version mismatch is a silent hard drop while corruption removes the key and captures to Sentry exactly once
- [Phase ?]: Did not run requirements.mark-complete for RESUME-01/RESUME-02 — shared across all 5 plans in Phase 170 (frontmatter); 170-01 alone only delivers the persistence primitives (snapshot module, pending-store queue, clock-fold rule), not the resume UI/seam/store-client that fulfills the requirements. Left [ ] Pending with this partial-delivery note (mirrors 169.5-01's PLAY-11 precedent).
- [Phase 170-localstorage-resume]: tc_preset reuses toBackendTcStr verbatim (base-seconds) — no separate lichess display-preset derivation (D-14 corrected)
- [Phase 170-localstorage-resume]: useDrainPendingStore uses its own retry-less useMutation instead of reusing useStoreBotGame() — a 401's unconditional-retry predicate would hang mutateAsync forever inside the drain loop
- [Phase 170-03]: gameUuid and the resume->board replay cache modeled as useState, not useRef as the plan literally specified — react-hooks/refs (react-hooks 7.1.1) forbids reading ref.current during render; useState gives byte-identical external behavior
- [Phase 170-03]: Task 1 (resume seam) and Task 2 (live gate) committed together — the refs/state block and return statement are physically interleaved by both tasks; matches project precedent (Phase 155-04)
- [Phase 170-03]: Left RESUME-01 checkbox unmarked (Pending) — shared across Plans 01/03/04/05 (frontmatter); 170-03 alone only delivers the hook resume seam + live gate, not the localStorage write path or the resume-gate UI; Plans 04/05 will actually close it
- [Phase 170]: Plan 170-04 split Task 1/Task 2 into two atomic commits (orthogonal call sites), verified byte-identical to a combined diff
- [Phase 170]: Reverted requirements.mark-complete's RESUME-01 checkbox flip: RESUME-01 is shared across Plans 04/05 (frontmatter) — 170-04 alone delivers the persistence half (snapshot on every move, fold on hide); the SC1 'Resume game?' prompt is Plan 05's job; left [ ] Pending with a partial-delivery note; Plan 05 actually closes it
- [Phase 170-05]: Date.now() moved into a lazy useState initializer in ResumeGate.tsx to satisfy react-hooks/purity; test assertions use .toBeNull()/.not.toBeNull() (no jest-dom in this project) instead of toBeInTheDocument()
- [Phase 170-UAT]: ClockDisplay slimmed to roughly the analysis board's PlayerBar proportions (p-4 → px-2 py-1.5, text-xl → text-lg digits) after UAT test 7 flagged the clock strips as too tall on mobile. The card surface was deliberately KEPT rather than going fully borderless like PlayerBar — the active-side fill and the low-time ring need something to paint on, which a live game needs and an analysis board does not.
- [Phase 171-01]: SEED-100 resolved via fix (b) document+pin, not fix (a) racing the deadline (rejected per RESEARCH.md D-03)
- [Phase 171-01]: Mutation target refined to disable only the return statement inside the blend<=0 block (not the whole block) so the RED failure lands on the search-count assertion the acceptance criteria names, not the policy-count assertion
- [Phase 171-02]: _lichess_blitz_equivalent_rating() reads only the blitz TC bucket -- rapid/classical-only anchor users correctly get None (D-07 deliberate semantic)
- [Phase 171-02]: MaiaEloProfile.lichess_blitz_equivalent_rating added as required (non-optional); current_rating kept on both TS types for other consumers, not deleted
- [Phase 171]: Exported NavHeader/MobileBottomBar/MobileMoreDrawer/MobileHeader from App.tsx (additive) so App.test.tsx can render each nav surface directly, since App() owns its own BrowserRouter/AuthProvider/QueryClientProvider stack
- [Phase 171-04]: resolveDefaultBotElo snaps a mid-rung rating via Math.round((clamped-min)/step)*step+min — pinned so 1650 -> 1700 — Plan explicitly allowed either rounding direction for the ambiguous half-rung case; Math.round's native round-half-up behavior was accepted rather than a custom rounding rule.
- [Phase 171-04]: DEFAULT_BOT_SETUP_SETTINGS.colorPreference defaults to 'random' — No explicit spec guidance in CONTEXT.md/UI-SPEC.md for the default color preference; chosen as the neutral no-preference default consistent with D-12's "Random resolves at Start" framing.
- [Phase 171-06]: Fixed a stale BOT_GAME_SETTINGS doc-comment reference in SetupScreen.tsx (a Plan 05 leftover, not in this plan's files_modified) to satisfy this plan's own explicit whole-frontend grep gate
- [Phase 171-06]: handleDiscard() now also resets startedSettings to null in addition to clearing the snapshot and bumping nonce, falling through to setup (D-13) rather than auto-starting
- [Phase 171-06]: game.newGame left fully in place on the hook (untouched useBotGame.ts); documented at the BotsGame call site that it is no longer reached from the UI (D-11) — npm run knip is the arbiter, ran clean
- [Phase 171-07]: Link color uses text-brand-brown-light hover:text-brand-brown-highlight (established FlawCard/GameCard convention), not a literal theme.ts export -- no such link-color token exists there
- [Phase 171-07]: Store-FAILURE test asserts call count strictly increases (not a hardcoded '2') -- shouldRetryStore's real MAX_STORE_RETRIES=2 bounded retry makes one failed finish-time attempt cost 3 real HTTP calls before a remount's drain adds one more
- [Phase 171-08]: buildAnalysisLineUrl's orientation arg is optional (2nd param) so the existing Openings.tsx:570 caller compiles unchanged with zero edits
- [Phase 171-08]: No new exported type alias for the orientation union; inline 'white' | 'black' keeps knip's dead-export surface at zero
- [Phase 171-08]: Square-order assertion pinned empirically (unflipped: a8 precedes a1 in DOM order) rather than assumed
- [Phase 171-09]: fenAtPly renamed to replayToPly and returns { fen, lastMove } from ONE replay pass, not a second useMemo -- avoids double-replaying moveHistory on every render
- [Phase 171-09]: lastMove derives from viewedPly, never the live tail, so scrubbing the move list moves the highlight with it (lichess/chess.com behavior); pinned by a dedicated anti-stale-highlight test
- [Phase 171]: [Phase 171-10]: Kept Task 1 (clearance) and Task 2 (density) as independently revertable commits per the plan's explicit instruction
- [Phase 171]: [Phase 171-10]: Slider 40px override scoped via [&_[data-slot=slider]]:min-h-10 descendant selector on SetupScreen's root rather than editing the shared ui/slider.tsx primitive's min-h-11 (app-wide 44px contract stays untouched)
- [Phase 171]: [Phase 171-10]: Could not independently browser-verify the slider override's computed height in this execution environment (no browser tooling available); applied on CSS-specificity grounds, final confirmation deferred to the plan's mandatory real-device human-check
- [Phase 172-01]: Computed opening_ply_count unconditionally in _build_card (list-mode cards too) — negligible cost against the already-loaded trie, avoids forking the card-construction contract
- [Phase 172-01]: find_opening_ply_count does not call _normalize_pgn_to_san_sequence — caller already has tokenized SAN, keeping find_opening's PGN-taking signature and callers untouched
- [Phase 172-02]: GEM_MAIA_MAX_PROB set to exactly 0.2 (D-07), doc-comment records Phase 165 TSV ratios (ratios transfer, absolute frequencies do not)
- [Phase 172-02]: Export-in-place chosen for deriveRawDefault/clampToLadderBounds (D-01) over extracting to a shared module — minimal diff, matches PATTERNS.md analog
- [Phase 172-02]: selectSweepCandidates uses strict best_move equality (no es-loss band) — fails safe on backend/live-engine disagreement per D-04
- [Phase 172-03]: BOOK_MARKER_COLOR = oklch(0.60 0.04 250) added verbatim per UI-SPEC — no deviation
- [Phase 172-03]: MoveListMarker required NO new branch — book falls through the existing plain-icon path severity already uses (confirmed: single resolveMarkerIcon call site covers both desktop and mobile render paths)
- [Phase 172-04]: Dedicated worker instances chosen over workerPool.ts priority-queue migration (structural fix for D-05 starvation)
- [Phase 172-04]: SWEEP_GRADING_MOVETIME_MS set to 1000ms, deliberately smaller than the live grading path's 4000ms cap
- [Phase 172-04]: Sweep yields only at the dispatch gate (never aborts in-flight sweep work on cursor change) - dedicated workers make this safe
- [Phase 172-04]: Two-layer liveBusy gate (scheduler decision + idle-callback ref re-check) covers the schedule-to-execution race
- [Phase 172-05]: sweepArmedForGame implemented via useState (armedGameId), not a ref — this project's react-hooks/refs ESLint rule forbids reading ref.current during render — reads evalChartReady directly for the same-render transition; armedGameId is only sticky protection against a later flicker
- [Phase 172-05]: needParentGemGrade's double-work-avoidance extension uses a companion sweepResolvedPlies useState synced by an effect declared AFTER useGemSweep, not a ref — avoids both the react-hooks/refs lint rule and a circular dependency (needParentGemGrade also feeds the sweep's own liveBusy input)
- [Phase 172-05]: Actual hook call order is [primary grading, sweep's grading, live gemGrading] and [live maia, sweep's maia] per commit, not [primary, gemGrading, sweep] as first assumed — useGemSweep had to be wired in before parentGemCandidateSans/gemGrading since needParentGemGrade (which both depend on) must exist before it can be passed to the sweep as liveBusy
- [Phase 173-01]: sf8/sf10 documented [ASSUMED] labels/ordering-only (never a Bradley-Terry fit input) directly in the SF_SKILL_ELO doc comment, per D-09/Pitfall 3
- [Phase 173-01]: playTwoMoverGame's own maxPlies param (game-level PLY_CAP cutoff) kept distinct from playGame's maxPlies param (SearchBudget tree-depth cap) — the thin wrapper never forwards the latter into the former, preserving the pre-extraction PLY_CAP default
- [Phase 173-01]: playGame's onPly wrapper remaps playTwoMoverGame's color-keyed mover ('white'/'black') back to the bot-relative 'bot'/'anchor' label via (p.mover === 'white') === botIsWhite, keeping the pre-extraction onPly payload byte-identical
- [Phase 173-03]: fit_bradley_terry returns ratings already on the 400*log10(pi) scale (not raw strengths) so apply_scale_fix operates uniformly on rating dicts
- [Phase 173-03]: apply_scale_fix assigns the pin anchor's rating directly to value (not via addition) so the D-05 exact-1500.0 pin holds regardless of floating-point rounding
- [Phase 173-03]: compute_residuals returns a ResidualRow TypedDict instead of dict[str, object] — ty could not statically verify tuple-unpacking row['pair'] on a plain object-valued dict
- [Phase 173-03]: bootstrap_ci's pinned anchor (maia1500) collapses to a zero-width CI by construction across every resample — documented as expected behavior in test_bootstrap, not a bug
- [Phase 173-02]: Global gameIndex is a single run-wide counter (not per-pair-local) shared across probe+measure and all pairs, mirroring the bot harness's --resume convention
- [Phase 173-02]: D-04 re-targeting applies to every dropped cross-family pair on every round (not only when it's the sole surviving link), bounded by MAX_RETARGET_ROUNDS=3
- [Phase 173-02]: Measure-pass extension computes gamesPerMeasure - stats.games (stats.games already includes probe games) — resolves 173-RESEARCH.md Open Question 1 by reusing rather than discarding already-played data
- [Phase 173-02]: isCrossFamilyPair exported from calibration-anchor-schedule.mjs (shared by checkConnectivity and the orchestrator's retarget logic) rather than duplicated
- [Phase ?]: [Phase 173-04]: Band-relaxing connectivity rescue (rescueConnectivity/bandDistance, commit a2f96e81, user-approved) fixes D-04 re-target dead-end when a pair's only informative link has no weaker same-family anchor
- [Phase 174]: 174-01: Maia parity D-02 gate PASSED — PARITY_EPSILON=0.010 derived from measured max drift 0.003844; phase proceeds to Wave 2
- [Phase 174]: 174-01: encoding module kept numpy-free (stdlib+python-chess) so encoding tests run in the default no-group suite while onnxruntime/numpy stay isolated in the maia-inference uv group
- [Phase ?]: 174-02: backend Dockerfile installs the maia-inference uv group (--group), worker image stays lean (GEMS-06); isolation asserted by tests/test_dependency_isolation.py
- [Phase ?]: 174-03: game_best_moves keyed on (game_id, ply) — no user_id (candidacy is position-scoped); raw cp stored, tier decided query-time
- [Phase ?]: 174-04: Maia ONNX session is an eager singleton (Stockfish-mirrored) with a D-03a ImportError no-op guard + SHA-256 model-pin cross-check; lean/worker images boot without onnxruntime.
- [Phase ?]: 174-04: Gem/Great/neither classification is a pure function of stored (maia_prob, cp margin) + module constants (GEM_MAIA_MAX_PROB=0.20, GREAT_MAIA_MAX_PROB=0.50) — retune reclassifies the corpus with zero re-analysis (GEMS-07).
- [Phase ?]: 174-05: best-move candidate builder runs off-session in each eval-apply lane (session-closed-then-gather) and rows persist in apply_full_eval's shared write commit (GEMS-03, T-174-12)
- [Phase ?]: 174-05: remote-worker lane (Pitfall 1, MultiPV-1) uses a targeted backend-owned evaluate_nodes_multipv2 fallback for played==best plies lacking second-best — worker protocol untouched
- [Phase ?]: 174-05: measured Maia RSS ~235 MiB, projected backend ~2743/4096 MiB — fits 4GB budget alongside 6-worker Stockfish pool; prod backend-Maia enablement stays human-gated (D-03b)
- [Phase ?]: 174-06: Bypassed the SEED-076 lease-redundancy filter entirely for lichess-eval games in _build_lease_positions (Rule 1 fix) — its premise (already-eval'd row = already resolved by a prior worker) is false for lichess games, whose %evals come from import; left unfixed the lease collapsed to ply 0 only, defeating Task 2's own acceptance criteria
- [Phase ?]: 174-06: _contiguous_san_prefix rebuilt around the deepest target's board.move_stack + its own move_san (not a ply-0-anchored walk over the caller's targets list) — fixes CR-01 book-depth collapse on a sparse targets list
- [Phase ?]: [Phase 174-07]: Broadened the existing residual PV-backfill fallback (full_evals_completed_at IS NULL -> full_pv_completed_at IS NULL) rather than adding a new lottery rung; kept precedence and ES key unchanged
- [Phase ?]: [Phase 174-07]: Dropped the superseded ix_games_pv_backfill_pending in the same migration that adds ix_games_lichess_pv_backfill_pending, since its predicate no longer matches any query after the broadening
- [Phase ?]: Moved TIER_BESTMOVE_BACKFILL constant addition from Task 4 to Task 3 (Rule 3 auto-fix) to unblock Task 3 verify tests without a forward dependency on Task 4's lottery rung
- [Phase ?]: [Phase 177-01]: worker_schema_version defaults to 1 on /atomic-lease (un-updated binary compatibility, Pitfall 4)
- [Phase ?]: [Phase 177-01]: _build_best_move_candidates's source param defaults to 'drain-local' so the out-of-scope eval_drain.py call site keeps working unchanged
- [Phase ?]: [Phase 177-01]: second_best tamper guard checks only in-range ply, not candidate membership -- a non-candidate ply is silently dropped at the map lookup, mirroring the blob-node precedent (S-02)
- [Phase ?]: [Phase 177-02]: _build_bestmove_lease_positions applies only the availability (None-guard) half of the inaccuracy gate at lease time -- the runner-up eval doesn't exist until the worker computes it; the full margin gate + Maia scoring runs once, authoritatively, at submit time via the reused _build_best_move_candidates
- [Phase ?]: [Phase 177-02]: /bestmove-submit's tamper guard is structural-range-only (422 on out-of-range ply); candidate-membership rejection is achieved for free by _build_best_move_candidates's own independent recompute (never reads second_best_map keys to decide candidacy)
- [Phase ?]: [Phase 177-02]: _apply_bestmove_submit lives in eval_apply.py (service layer) per the plan's explicit artifact placement, diverging from precedent (_apply_flaw_blob_submit/_apply_atomic_submit live in the router); still raises HTTPException directly for 404/422, matching established error-handling style
- [Phase ?]: [Phase 177-03]: _tier4b_minimal_drain_tick inlines the reconstruction + write sequence rather than calling _apply_bestmove_submit verbatim, so it can pass source='drain-local' into _build_best_move_candidates (D-06), and preserves the Phase 176 D-01 maia_available guardrail the new tier branch would otherwise bypass (Rule 2 auto-fix, caught by the plan's own pre-existing test)
- [Phase ?]: Phase 177 Plan 04: split Task 1/Task 2 into two atomic commits despite overlapping code in _run_cycle, by temporarily reverting/reapplying Task 2's additions rather than merging commits
- [Phase ?]: Phase 177 Plan 04: engine-failure detection for the targeted second-best search checks r[0] is None and r[1] is None (both eval_cp/eval_mate absent) as the unique failure signature
- [Phase 178-01]: Copy-then-null implemented as two sequential UPDATE statements (not a single multi-column UPDATE with subselects) for auditability; both run in upgrade() in the correct order
- [Phase 178-01]: Migration docstring rephrased to avoid the literal substrings `inaccuracies`/`mistakes`/`blunders` so the D-04 guardrail grep passes even against comments, not just code
- [Phase ?]: [Phase 178-02]: Corrected the RESEARCH.md/PLAN.md game-296343 fixture array (dropped one of five consecutive zeros at plies 9-13); re-verified against dev DB game_positions directly
- [Phase ?]: [Phase 178-02]: Checkmate final-move NULL eval resolved via the +/-CP_CEILING mate-delivered convention (uniform per-move loop, no skip-branch)
- [Phase ?]: [Phase 178-04]: --dry-run still streams and computes (pure Python, no engine calls), only skipping the write, giving a real processed/filled/skipped_none summary
- [Phase ?]: [Phase 178-04]: a compute None result (interior hole) is not written as an explicit NULL UPDATE — the candidate query is already gated on white_accuracy IS NULL, so skipping the write keeps each batch's write session lean
- [Phase ?]: [Phase 178-04]: --limit caps streamed position rows (not games), mirroring backfill_best_move_pv.py; confirmed on dev that a limit landing mid-game harmlessly trips that one game's Complete-Sequence Gate
- [Phase ?]: [Phase 178-04]: validation script's delta stats computed in Python (not SQL percentile_cont) — per-signal row counts are thousands, not the ~718k backfill scale, so a plain fetch + Python percentile is simpler and fast enough

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
| 260708-qrr | Unified move-hover popover (FlawChess/practical gold, Stockfish/objective blue, Maia/human violet — icon-led, whole-line color, omit unavailable) shared by both analysis cards' dotted moves | 2026-07-08 | a339346a | [260708-qrr-unified-move-popover-on-dotted-moves](./quick/260708-qrr-unified-move-popover-on-dotted-moves/) |
| 260709-j3k | Checkmate on a free move line no longer reads as a blunder — terminal eval derived from the rules so the bar fills to 0%/100% and the mating move reads green | 2026-07-09 | ce8d19b5 | [260709-j3k-analysis-board-a-free-move-line-ending-i](./quick/260709-j3k-analysis-board-a-free-move-line-ending-i/) |
| 260709-k9r | FlawChess Engine card surfaces forced mates — thread evalMate through RankedLine/search/reconciliation so a mate line shows #-4 (not …) and the agreement verdict narrates instead of the stale "Turn on Stockfish" prompt | 2026-07-09 | 0b02c4f9 | [260709-k9r-fix-flawchess-engine-card-mate-eval-and-](./quick/260709-k9r-fix-flawchess-engine-card-mate-eval-and-/) |
| 260709-o72 | Maia/FlawChess card prose now reflects player standing (Option B: "{standing} — {difficulty}"); player-POV eval chips (−M4 = "You're being mated" not white-POV), standing bands (winning/better/level/worse/losing/mate), decisive+safe collapse to "longest resistance"; FlawChess "safer" → "more reliable" | 2026-07-09 | ca301bee | [260709-o72-fix-maia-flawchess-card-prose-to-reflect](./quick/260709-o72-fix-maia-flawchess-card-prose-to-reflect/) |
| 260710-e2p | Maia "Moves by Rating" tooltip pins the FlawChess Engine's OWN top pick (reconciledRankedLines[0]) instead of Stockfish's objective best mislabeled "FlawChess"; drops row when FC engine off; removed the "(played)" tag from tooltip rows | 2026-07-10 | 9b409161 | [260710-e2p-show-flawchess-engine-top-pick-in-maia-c](./quick/260710-e2p-show-flawchess-engine-top-pick-in-maia-c/) |
| 260710-k7n | FlawChess Engine promoted to homepage hero (FEATURES[0]: "Your Best Practical Move" + ChessKnight + 3 bullets, Game/Tactic Analysis to #2); README leads Features with the engine and intro rewritten to headline it (dropped Zobrist-hash + AI-narrated-insights) | 2026-07-10 | c039196b | [260710-k7n-engine-hero-homepage](./quick/260710-k7n-engine-hero-homepage/) |
| 260710-wub | Openings "Analyze position" moved from full-width button to a compact Search-icon button in the sidebar strip (desktop) / settings column under bookmarks (mobile), shown on Moves + Games subtabs; fixed the sideline × delete not working in Analysis `?fen=` free-play mode (onDeleteLine was gated on isGameMode) | 2026-07-10 | 27d0507d | [260710-wub-openings-move-analyze-button-to-sidebar-](./quick/260710-wub-openings-move-analyze-button-to-sidebar-/) |
| 260710-x3d | Openings analyze passes the opening's moves to the analysis board as a `?line=` UCI param (cursor at end, navigable back to move 1), replacing the `?fen=` snapshot; new buildAnalysisLineUrl/parseAnalysisLineParam helpers; game mode kept (user-confirmed) | 2026-07-10 | edce3687 | [260710-x3d-implement-opening-moves-main-line-in-ana](./quick/260710-x3d-implement-opening-moves-main-line-in-ana/) |
| 260712-r4s | Calibration harness `--resume <prior.tsv>` (SEED-097): skips already-swept `(elo,blend,anchor)` cells, fast-forwards the global gameIndex, appends remaining cells → finished map byte-identical to an uninterrupted run; refuses on games-per-cell/seed/budget/grid mismatch or a truncated prior file | 2026-07-12 | b13a1d98 | [260712-r4s-calibration-harness-resume-flag](./quick/260712-r4s-calibration-harness-resume-flag/) |
| 260714-f2b | Default Opponent Type filter changed from Human to Both (DEFAULT_FILTERS + useStats/useOpeningInsights fallbacks); computer games now included by default across Stats, Openings, Endgames, Library | 2026-07-14 | 912e8c3e | — |
| 260714-pnk | Bot games show the player's real platform username instead of "You" (lichess → chess.com → "You"), on the /bots clock caption and in the stored `games` row; one resolver per stack (`resolve_player_username` / `resolvePlayerName`) | 2026-07-14 | 355b52d5 | [260714-pnk-show-player-s-platform-username-instead-](./quick/260714-pnk-show-player-s-platform-username-instead-/) |
| 260714-qaj | Stored bot games get a full lichess-comparable PGN header block, stamped server-side post-insert (`bot_game_pgn.stamp_bot_game_headers`): Event/Site deep link/Date/Round/White/Black/GameId/UTCDate/UTCTime/Elo/Title/Variant/ECO/Opening + non-standard RatingSource + PlayStyleBlend; player Elo is the Lichess-equivalent anchor, omitted (never "?") when the user has no anchor | 2026-07-14 | e4509e9b | [260714-qaj-enrich-bot-game-pgn-metadata-headers](./quick/260714-qaj-enrich-bot-game-pgn-metadata-headers/) |
| 260714-rj5 | "Analyze this game" after a bot game enqueues a tier-1 eval job and opens the analysis board in game mode; the board renders the move list immediately, shows the Pending…/Analyzing… pill in the eval chart's slot, and swaps in the eval chart + flaw icons + tactic badges in place when the job lands (no remount, so the move cursor and variation tree survive). Unanalyzed single-game cards now carry `moves` + `phase_transitions`, which also fixes the empty-board dead end for unanalyzed imported games. Retires the Phase 169 D-20/D-21 "never gated" invariant | 2026-07-14 | 1f27190c | [260714-rj5-bot-game-tier-1-analysis-with-live-updat](./quick/260714-rj5-bot-game-tier-1-analysis-with-live-updat/) |
| 260715-als | WR-04 (Phase 172 deferred review finding): a book ply carrying an inaccuracy-severity flaw rendered no variation-tree marker at all — the move list's resolveMarkerIcon draws no glyph for inaccuracy, and the book fold was suppressed by any non-null severity. Fixed by deferring only to entries that draw a move-list icon (blunder/mistake/gem); board `!?` surface untouched. Page-level RED→GREEN test | 2026-07-15 | 6d9c12b8 | [260715-als-fix-wr-04-inaccuracy-severity-book-ply-r](./quick/260715-als-fix-wr-04-inaccuracy-severity-book-ply-r/) |
| 260715-r9c | /bots layout: BoardControls bar (reset/back/forward/flip) below the board, wired to the hook's view-only `viewedPly` cursor; flip is a manual local toggle. Single-column constrains the stack to the board's max width (clock strips always match the board) and HIDES the move list; two-column desktop (breakpoint lowered 1024→800) is two rows with a small gap so the flex-filled move list bottom aligns with the board bottom, board controls + Resign/Draw beneath. Split GamePanel → move-list + controls; MoveListPanel gained `fillHeight`. Layout-only, all 2228 FE tests green | 2026-07-15 | 4b8c1878 | [260715-r9c-improve-bot-game-layout-with-board-contr](./quick/260715-r9c-improve-bot-game-layout-with-board-contr/) |
| 260717-agv | Analysis game-view by url (`/analysis?game_id=X`) accessible to any logged-in user, not just the owner. Relaxed `GET /library/games/{game_id}` + tactic-line expansion from an owner IDOR guard to logged-in-only: scope `get_library_game` queries to `owner_id = game.user_id` and `fetch_tactic_lines` by globally-unique `game_id`, keep `current_active_user` as the auth gate. Contained to Analysis.tsx (list endpoint stays owner-scoped). Flipped 3 cross-user IDOR tests to 200; 121 backend tests pass. Intentional: game_ids are enumerable, so any logged-in user can view any game (scouting/sharing) | 2026-07-17 | 4b9d3da2 | [260717-agv-analysis-game-view-any-logged-in-user](./quick/260717-agv-analysis-game-view-any-logged-in-user/) |
| 260717-gmg | Guard gem/great badges against best_cp vs imported-eval divergence: on lichess-eval games the eval graph preserves lichess's `%eval` while `best_cp`/`best_move` come from our own Stockfish, so a shallow overrating of a sharp line produced spurious badges (game 640125, 55.Qc6+: our −0.82 vs lichess −2.46). Query-time, directional, expected-score guard in `classify_best_move` + SQL twin `best_move_tier_sql` (new `BEST_MOVE_DIVERGENCE_MAX_ES = 0.10`), wired through the board and the Library has-gem/great filter (LEFT-join the candidate ply's `game_positions` row, fail-open). Retroactive (zero re-analysis), no-op for engine games. 12 new tests; full backend suite 3439 passed | 2026-07-17 | aa599bcd | [260717-gmg-gem-great-divergence-guard-lichess-eval](./quick/260717-gmg-gem-great-divergence-guard-lichess-eval/) |
| 260717-lr9 | Preset-only 3-tier play-style control on the Bots setup screen: replaced the play-style slider + Human/Engine chips with three preset buttons — Human (blend 0), Light (0.05, new default), Deep (0.5). Names describe calculation depth, not a rating (engine not ELO-calibrated yet). playStyle.ts drops the slider constants + transitional `ENGINE_PRESET_BLEND`, adds `LIGHT_BLEND`/`DEEP_BLEND`/`BLEND_MAX` (validation ceiling kept at 1 so legacy blend=1 blobs still validate); `deriveActivePlayStylePreset` 3-way; default flips to Light. Also tightened adjacent setup copy (play-style popover, EloSelector tooltip). Full FE gate green: knip/tsc/eslint + 2298 tests | 2026-07-17 | c6b4c7a4 | [260717-lr9-preset-only-3-tier-play-style-control-hu](./quick/260717-lr9-preset-only-3-tier-play-style-control-hu/) |
| 260717-rbn | Best + Good query-time move tiers alongside gem/great, surfaced as green corner glyphs (white star = best, white thumbs-up = good) on the analysis board (both players) and the library card mini-board (user-scoped). `EvalPoint.best_move_tier` widened to gem/great/best/good/null: `best` = played UCI == stored `game_positions.best_move` (Move-object replay, not SAN==UCI string compare); `good` = sub-inaccuracy severity (reuses `_run_all_moves_pass` flaws_service conventions) and not best/gem/great; book plies excluded via `opening_ply_count`; precedence gem>great>best>good. No DB/engine/backfill impact. New `bestGlyph.ts`/`goodGlyph.ts` (theme constants) + boardMarkers branches. 7 new backend tests (suite 3482), FE tsc/knip green | 2026-07-17 | fda1ae24 | [260717-rbn-add-best-good-move-tiers-to-analysis-boa](./quick/260717-rbn-add-best-good-move-tiers-to-analysis-boa/) |

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

**Stopped at:** Completed 178-04-PLAN.md

**Last session:** 2026-07-18T09:27:41.610Z

**Resume file:**

None

## Performance Metrics

(Cleared at v1.31 close — per-plan timings archived with the milestone.)
**Per-Plan Metrics:**

| Plan | Duration | Tasks | Files |
|------|----------|-------|-------|
| Phase 173-anchor-ladder-self-calibration-seed-101 P03 | 20min | 2 tasks | 2 files |
| Phase 173 P02 | 13min | 2 tasks | 3 files |
| Phase 173 P04 | 25min | 2 tasks | 5 files |
| Phase 174 P01 | 14 min | 2 tasks | 8 files |
| Phase 174 P02 | 8min | 2 tasks | 2 files |
| Phase 174 P03 | 8min | 2 tasks | 4 files |
| Phase 174 P04 | 20min | 2 tasks | 5 files |
| Phase 174 P05 | 45min | 2 tasks | 5 files |
| Phase 174 P06 | ~50min | 3 tasks | 7 files |
| Phase 174 P07 | 35min | 2 tasks | 5 files |
| Phase 176 P01 | 20min | 4 tasks | 8 files |
| Phase 177 P01 | 14min | 3 tasks | 5 files |
| Phase 177 P02 | 31min | 3 tasks | 6 files |
| Phase 177 P03 | 16min | 1 tasks | 2 files |
| Phase 177 P04 | 25min | 2 tasks | 2 files |
| Phase 178 P01 | 15min | 3 tasks | 3 files |
| Phase 178 P02 | 12min | 2 tasks | 2 files |
| Phase 178 P03 | 15min | 2 tasks | 2 files |
| Phase 178 P04 | 12min | 3 tasks | 3 files |

## Performance Metrics

| Phase | Plan | Duration | Notes |
|-------|------|----------|-------|
| Phase 151 P01 | 16min | 3 tasks | 8 files |
| Phase 151 P02 | 20min | 2 tasks | 4 files |
| Phase 151 P03 | 20min | 2 tasks | 6 files |
| Phase 151 P04 | 45min | 3 tasks | 10 files |
| Phase 151 P05 | 20min | 3 tasks | 7 files |
| Phase 151 P06 | 30min | 4 tasks | 7 files |
| Phase 153 P01 | 12min | 2 tasks | 4 files |
| Phase 153 P02 | 8min | 2 tasks | 2 files |
| Phase 153 P03 | 15min | 2 tasks | 2 files |
| Phase 153 P04 | 35min | 3 tasks | 2 files |
| Phase 153 P05 | 20min | 2 tasks | 2 files |
| Phase 154 P01 | 15min | 3 tasks | 2 files |
| Phase 154 P02 | 25min | 2 tasks | 2 files |
| Phase 154 P03 | 25min | 3 tasks | 2 files |
| Phase 154 P04 | 20min | 2 tasks | 2 files |
| Phase 155 P01 | 15min | 3 tasks | 6 files |
| Phase 155 P02 | 10min | 2 tasks | 2 files |
| Phase 155 P03 | 13min | 2 tasks | 3 files |
| Phase 155 P04 | 55min | 3 tasks | 3 files |
| Phase 156 P01 | 15min | 2 tasks | 5 files |
| Phase 157 P01 | 15min | 2 tasks | 2 files |
| Phase 157 P02 | 40min | 3 tasks | 5 files |
| Phase 158 P01 | 23min | 2 tasks | 2 files |
| Phase 158 P02 | 20min | 1 tasks | 2 files |
| Phase 158 P03 | 40min | 3 tasks | 3 files |
| Phase 159 P01 | 12min | 2 tasks | 7 files |
| Phase 159 P02 | 14min | 2 tasks | 5 files |
| Phase 159 P03 | 16min | 2 tasks | 9 files |
| Phase 159 P04 | 20min | 2 tasks | 4 files |
| Phase 162 P01 | 12min | 2 tasks | 2 files |
| Phase 162 P02 | 20min | 2 tasks | 2 files |
| Phase 162 P03 | 22min | 2 tasks | 3 files |
| Phase 163 P01 | 10min | 2 tasks | 4 files |
| Phase 163 P02 | 15min | - tasks | - files |
| Phase 163 P03 | 12min | 2 tasks | 3 files |
| Phase 163 P04 | 55min | 3 tasks | 3 files |
| Phase 164 P01 | 20min | 2 tasks | 2 files |
| Phase 164 P02 | 25min | 2 tasks | 3 files |
| Phase 164 P03 | 15min | 2 tasks | 3 files |
| Phase 165 P01 | 17min | 2 tasks | 3 files |
| Phase 165 P02 | 35min | 3 tasks | 3 files |
| Phase 166 P01 | 25min | 3 tasks | 4 files |
| Phase 167 P01 | 25min | 2 tasks | 8 files |
| Phase 167 P02 | 25min | 2 tasks | 4 files |
| Phase 167 P03 | 20min | 3 tasks | 8 files |
| Phase 168 P01 | 40min | 3 tasks | 7 files |
| Phase 168 P03 | 95min | 3 tasks | 6 files |
| Phase 168.5 P01 | 2min | 2 tasks | 2 files |
| Phase 168.5 P02 | 35min | 3 tasks | 2 files |
| Phase 168.5 P03 | 20min | 4 tasks | 6 files |
| Phase 168.5 P04 | 45min | 2 tasks | 2 files |
| Phase 168.5 P05 | 45min | 3 tasks | 4 files |
| Phase 169 P01 | 6min | 2 tasks | 2 files |
| Phase 169 P02 | 20min | 3 tasks | 7 files |
| Phase 169 P03 | 20min | 2 tasks | 11 files |
| Phase 169 P04 | 23min | 3 tasks | 2 files |
| Phase 169 P05 | 10min | 3 tasks | 5 files |
| Phase 169 P06 | 22min | 3 tasks | 4 files |
| Phase 169 P08 | 20min | 2 tasks | 4 files |
| Phase 169 P09 | 55min | 3 tasks | 7 files |
| Phase 169 P10 | 25min | 3 tasks | 5 files |
| Phase 169.5 P01 | 25min | 2 tasks | 2 files |
| Phase 170 P01 | 35min | 3 tasks | 6 files |
| Phase 170-localstorage-resume P02 | 40min | 2 tasks | 4 files |
| Phase 170 P03 | 45min | 2 tasks | 2 files |
| Phase 170 P04 | 40min | 2 tasks | 2 files |
| Phase 170 P05 | 20min | 2 tasks | 3 files |
| Phase 171 P01 | 20min | 2 tasks | 2 files |
| Phase 171 P02 | 6min | 3 tasks | 6 files |
| Phase 171 P03 | 25min | 2 tasks | 2 files |
| Phase 171 P04 | 25min | 3 tasks | 8 files |
| Phase 171 P05 | 12min | 2 tasks | 2 files |
| Phase 171 P06 | 20min | 2 tasks | 3 files |
| Phase 171 P07 | 55m | 3 tasks | 6 files |
| Phase 171 P08 | 7min | 2 tasks | 6 files |
| Phase 171 P09 | 8min | 2 tasks | 4 files |
| Phase 171 P10 | 7min | 2 tasks | 4 files |
| Phase 172 P01 | 20min | 3 tasks | 6 files |
| Phase 172 P02 | 25min | 3 tasks | 6 files |
| Phase 172 P03 | 20min | 3 tasks | 7 files |
| Phase 172 P04 | 50min | 3 tasks | 4 files |
| Phase 172 P05 | ~2h | 3 tasks | 2 files |
| Phase 173 P01 | ~20min | 2 tasks | 5 files |

## Operator Next Steps

- Start the next milestone with /gsd-new-milestone
