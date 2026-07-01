---
gsd_state_version: 1.0
milestone: v1.30
milestone_name: Forcing-Line Tactic Gate
current_phase: 146
current_phase_name: offload-live-submit-forcing-line-continuation-eval-to-the-re
status: planning
stopped_at: Phase 147 context gathered
last_updated: "2026-07-01T18:09:34.293Z"
last_activity: 2026-07-01
last_activity_desc: "Completed quick task 260701-lw4: replace tier-4 blob-backfill top-50 recency window with a two-stage ES weighted lottery"
progress:
  total_phases: 7
  completed_phases: 4
  total_plans: 19
  completed_plans: 17
  percent: 57
---

# Project State: FlawChess

## Current Position

Phase: 146 (offload-live-submit-forcing-line-continuation-eval-to-the-re) — EXECUTING
Last activity: 2026-07-01 — Completed quick task 260701-lw4: replace tier-4 blob-backfill top-50 recency window with a two-stage ES weighted lottery

Phase 145 (corpus-backfill-rollout) — COMPLETE (code). Plans 01–05 + the autonomous part of
plan 06 are merged to main (`875bc164`) and released to production in v1.30 (PR #229,
`61107f47`). The remaining plan-06 `[HUMAN-VERIFY]` prod backfill *drain* (fleet drain → D-08
retag sweep → SC3 after-snapshot) is intentionally deferred: it is gated on the upgraded
remote-worker fleet deploy, which IS the deliverable of Phase 146 (D-04). So 145's rollout
completes through 146 — not a 145 gap.

## Project Reference

See: .planning/PROJECT.md (updated 2026-06-29 after v1.29 milestone close)
Core value: Position-precise WDL across openings + endgames + time pressure on top of users' actual chess.com / lichess games, with personalized LLM commentary and an auto-generated opening-strengths/weaknesses report.
Current focus: v1.30 Forcing-Line Tactic Gate — 5 phases (141–145) blocking on JSONB schema (141) before engine pass (142), offline re-tagger (143), A/B validation (144), and corpus backfill + rollout (145). Hard sequential dependency chain; no parallelization.

## Milestone Progress

Twenty-nine milestones complete (v1.0–v1.29). v1.29 Live-Engine Analysis Page shipped 2026-06-29 — 5 phases (136–140), 14 plans; released to production via PR #227 (`e3f652ab`). Live in-browser single-thread WASM Stockfish (`useStockfishEngine`), branching analysis board (`useAnalysisBoard`), lazy-loaded `/analysis` route, tactic mode subsuming + deleting the Phase 135 TacticLineExplorer, and a full-game board behind a unified `Analyze` entry with inline tactic-chip PV sidelines. No backend schema or new endpoints (D-4). Archived to milestones/v1.29-ROADMAP.md, phases to milestones/v1.29-phases/, tagged v1.29.

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

- Phase 146 added: Offload live-submit forcing-line continuation eval to the remote worker (SEED-071)
- Phase 147 added: Persist only forcing-line-gated tactic tags — suppress ungated remote-submit tags (A) + upgraded-worker atomic eval+blob pipeline (B) (SEED-074; scope confirmed as A+B together)

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
- [Phase ?]: goToRoot sets currentNodeId=null without clearing nodes/mainLine for D-5 re-seed landing at decision position
- [Phase ?]: TacticModeOverlay exports buildRootArrows/buildPvArrow as named exports so Analysis.tsx drives ChessBoard arrows without file indirection (Phase 139)
- [Phase ?]: ESLint analysis/** override added for co-exported arrow helpers alongside component (mirrors ui/** and filters/** pattern)
- [Phase 139-02]: FlawCard/LibraryGameCard Explore repointed to /analysis tactic URL params (D-01, no modal/location.state); D-02 Analyze position button added via ?fen= free-play (desktop + mobile)
- [Phase ?]: deferred=True on allowed_pv_lines/missed_pv_lines is the D-02 structural leak guard; no repository rewrites needed (D-02b)
- [Phase ?]: list[Any] | None type for PV-line blobs (D-05: blob is a list-of-dicts; write-once, no MutableList)
- [Phase 141]: Mate-priority hierarchy (D-01) implemented in forcing_line_gate.py: only-best-is-mate forced; both-mates shorter-distance; mate-in-1 never suppressed; fall through to win-prob margin
- [Phase 141]: ONLY_MOVE_WIN_PROB_MARGIN=0.35, ALREADY_WINNING_CP_THRESHOLD=300, STILL_WINNING_FLOOR_CP=200 as named constants (D-07..D-09); final margin committed in Phase 144
- [Phase 141]: PvNode uses eval_mate_to_expected_score for perspective-safe mate checking (T-141-04 guard)
- [Phase ?]: D-02: New _analyse_multipv2 method required for list[InfoDict] return type (MPV-01)
- [Phase ?]: Pitfall 3: second_uci str sentinel is '' for single-legal-move positions (never None, PvNode.su: str)
- [Phase ?]: whole-game per-ply pass switched to evaluate_nodes_multipv2 (D-01 MPV-02)
- [Phase ?]: engine_result_map kept as 4-tuple; second_best_map carries 3-tuple second-best per ply (no blast radius on existing callers)
- [Phase ?]: _fill_engine_game_flaw_second_best mirrors SEED-056 for dedup-transplanted flaw plies (D-05 MPV-02)
- [Phase ?]: additive schema extension
- [Phase ?]: NULL blobs for old workers; Phase 145 backfills
- [Phase ?]: Phase 143-01 gate parameterization
- [Phase ?]: D-02 implemented: _classify_tactic_gated wrapper routes live classify through forcing-line gate (SC4 single classify path)
- [Phase ?]: flaw_pv_blobs threaded from drain into classify before _run_multipv2_pass writes to DB (Pitfall 4 avoided)
- [Phase ?]: Ungated arm wires _detect_tactic_for_flaw directly, not margin=0, to get the genuine pre-gate baseline
- [Phase ?]: Both arms replay identical stored JSONB blobs, isolating gate effect from eval_cp cross-machine variance (VALID-01)
- [Phase ?]: D-06 sentinel: [] skips gate in _classify_tactic_gated (D-06 supersedes Phase-143 Pitfall-2); SHIP-02: blob_map threaded into _classify_and_fill_oracle in _apply_submit
- [Phase ?]: D-04 isolation enforced
- [Phase ?]: T-145-09: foreign token injection blocked — per-token validation against re-derived lease returns 422
- [Phase ?]: D-03: double-submit idempotent — blobs_written=0 when no NULL-blob flaws remain (early exit before token validation)
- [Phase ?]: D-06 sentinel write: [] blob written for un-fillable flaw lines so they stop matching the IS NULL predicate
- [Phase ?]: D-07 rolling retag: only 8 tactic columns updated via bulk_update_tactic_tags after blob write (no severity reclassification)
- [Phase ?]: blob_map={} unconditional in _apply_submit (Phase 146 D-03)
- [Phase ?]: _claim_tier4_blob is a two-stage Efraimidis-Spirakis weighted lottery (user by last_activity, then game by full_evals_completed_at, no tc_multiplier) — floor terms give the whole corpus non-zero draw mass so old analyzed games drain, fresh stays dominant (supersedes the TIER4_RECENCY_WINDOW top-50 window from Phase 146 D-01; quick 260701-lw4)
- [Phase ?]: _eval_flaw_blob_positions maps r[0]/r[1]/r[4]/r[5]/r[6]; r[2]/r[3] excluded; token echoed (D-04a)
- [Phase ?]: HTTP_TIMEOUT_S=30.0 — SEED-071 stopgap removed; full-ply pass reduced to MultiPV-1

### Pending Todos

None yet.

### Blockers/Concerns

None at planning start.

### Quick Tasks Completed

| # | Description | Date | Commit | Directory |
|---|-------------|------|--------|-----------|
| 260627-dny | Phase 139 tactic overlay UAT: remove StoredPV/engine toggle, eval bar perspective+position, live eval number, remove old eval badge | 2026-06-27 | 46067dff | [260627-dny-phase-139-tactic-overlay-uat-remove-stor](./quick/260627-dny-phase-139-tactic-overlay-uat-remove-stor/) |
| 260627-jqk | Phase 140 UAT: motif+depth move-list chips, fix tactic-chip PV sideline, precomputed best-move blue arrow + eval bar (engine = grey 2nd line), board tactic overlay without loaded PV, remove overlay chrome above engine lines | 2026-06-27 | 0efa9448 | [260627-jqk-uat-phase-140-tactic-badges-best-move-ar](./quick/260627-jqk-uat-phase-140-tactic-badges-best-move-ar/) |
| 260627-l2z | Phase 140 UAT round 2: remove legacy tactic mode (?flaw_ply=), clear stale engine arrows on position change, PV-sideline depth overlay arrow, color depth-0 resolving sideline move, flip board+chart for black-player games | 2026-06-27 | 634b343f | [260627-l2z-phase-140-uat-polish-round-2-remove-tact](./quick/260627-l2z-phase-140-uat-polish-round-2-remove-tact/) |
| 260627-mt8 | Phase 140 UAT round 3: engine info line (toggle + SF 18, Depth d), blue/grey eval badges on single-line PV rows, remove board-control engine toggle + best-line depth badge, fixed-height engine loading container, narrower move list bottom-aligned with eval slider, eval-chart slider syncs on move/sideline (fork-point) navigation | 2026-06-27 | c145d3de | [260627-mt8-more-uat-feedback-for-phase-140-analysis](./quick/260627-mt8-more-uat-feedback-for-phase-140-analysis/) |
| 260627-r9g | Phase 140 UAT round 4: move list −25px + subtle zebra rows (sideline inherits fork-row band), engine info/lines in a fixed-height charcoal Card with skeleton loaders, severity flaw arrows → blunder/mistake/inaccuracy (`!?`) corner glyphs, severity-colored last-move overlay (red/orange/yellow/green), depth labels moved top-left + smaller; same board changes mirrored onto the games-card MiniBoard | 2026-06-27 | da3e77c3 | [260627-r9g-more-uat-feedback-for-phase-140-analysis](./quick/260627-r9g-more-uat-feedback-for-phase-140-analysis/) |
| 260627-thl | Phase 140 UAT round 5: desktop move list −25px via flex-margin (controls stay bottom-aligned), best-move blue arrow uses next-ply best_move so it matches the live grey 2nd-best (fixed on analysis board + games-card MiniBoard; FlawCard correct), blunder/mistake glyphs in move list even when a tactic chip is present, forward button steps into the open flaw sideline, miniboard tooltip on engine-move hover | 2026-06-27 | c5389b1d | [260627-thl-more-uat-feedback-for-phase-140-analysis](./quick/260627-thl-more-uat-feedback-for-phase-140-analysis/) |
| 260627-w8k | Phase 140 UAT round 6: miniboard hover tooltip (no border, rounded corners, green played-move overlay), eval-slider↔board-controls bottom alignment fixed via absolute-inset scroller (browser-verified, no magic px), move-list tactic badges on a line below the move, live blunder/mistake/inaccuracy classification of freely-played moves via the live engine (glyph + square overlay), missed tactics shown one ply earlier (blue arrow + depth) on board/minimap/eval-tooltip/move-list | 2026-06-27 | e116912c | [260627-w8k-phase-140-uat-round-6-miniboard-border-h](./quick/260627-w8k-phase-140-uat-round-6-miniboard-border-h/) |
| 260628-1t5 | Phase 140 UAT round 6 follow-up: reverted the missed-tactic ply-1 shift (cfaa7856 + e116912c), drew the should-have-played move as a NEW violet arrow at the flaw ply on board + miniboard (empirically index-parity tested vs FlawCard), recolored both tactic families into opposite free zones of the board palette for distinctness (missed → magenta hue 330, allowed → teal hue 200; ~130° apart, magenta ~70° off the blue best-move arrow) across chips/arrows/depth-numbers/eval-tooltip, dropped the allowed +1 depth offset on navigable surfaces via an `anchored` flag (FlawCard + filter predicate keep it), surfaced the live free-move blunder/mistake glyph in the move list (desktop + mobile) | 2026-06-28 | 4343c576 | [260628-1t5-phase-140-uat-revert-missed-tactic-ply-1](./quick/260628-1t5-phase-140-uat-revert-missed-tactic-ply-1/) |
| 260628-cjp | Mobile `/analysis` takeover: back-button header (no logo) + suppressed shell bottom nav; the page owns an in-flow board-controls footer (Reset/Back/Forward/Flip); the two Stockfish PV lines moved above the board without the info-card header; a Moves \| Eval-chart 2-tab view (Moves default, vertical move list) fills all space between board and footer; single-tree-per-breakpoint (`useIsMobile` 640px) so the board mounts once; desktop layout unchanged | 2026-06-28 | 8a0b93c1 | [260628-cjp-improve-the-mobile-version-of-the-analys](./quick/260628-cjp-improve-the-mobile-version-of-the-analys/) |
| 260628-dgv | Mobile `/analysis` takeover UAT: EngineLines `compact` mode (text-xs single-row PV lines, flex-nowrap+overflow-x, shared `min-h-[44px]` across loading/analyzing/rendered) removes the vertical layout jump when lines arrive (text-xs is a user-approved exception to the text-sm floor, scoped to this engine surface; desktop keeps text-sm); BoardControls `flat` prop drops the rounded charcoal pill so the mobile board-controls footer reads like the main nav bar (desktop + Openings keep the pill); browser nav/URL-bar hiding left as-is (no reliable cross-browser JS API — PWA install is the only path) | 2026-06-28 | c215a4ac | [260628-dgv-analysis-mobile-uat-tweaks](./quick/260628-dgv-analysis-mobile-uat-tweaks/) |
| 260628-ojq | Phase 140 UAT: tactic-colored arrows. A board arrow/sideline move belonging to a missed/allowed tactic now carries that tactic's color (missed → teal, allowed → crimson — a vivid pink-red set apart from the blunder by higher saturation + a magenta-ward hue; orientation hues swapped in theme.ts after the initial pass, after interim wine-red, purple/violet, and burgundy tries), matching the chips. FlawCard played-move arrow teal (allowed) + best-move arrow magenta (missed), gated on the same orientation+motif as the chip; LibraryGameCard following-best (opponent response) arrow teal for allowed tactics (missed unchanged — already the violet should-have arrow); Analysis sideline colors every move from the fork up to the depth-0 resolving move (was only the resolving move) and `buildPvArrow` countdown arrows in the orientation color until depth 0 (neutral payoff color past the punchline) | 2026-06-28 | 71aa4df6 | [260628-ojq-uat-feedback-phase-140-tactic-colored-ar](./quick/260628-ojq-uat-feedback-phase-140-tactic-colored-ar/) |
| 260628-pu2 | Phase 140 UAT: analysis board. (1) On an allowed-tactic flaw the following-best (opponent response) arrow now reads in the allowed crimson, matching the game-card miniboard (was plain blue). (2) Display-depth 0 is treated as the payoff move — no number, neutral color (the tactic is over by then); dead `isFlawLeadIn` arrow branch dropped. (3) Allowed PV sidelines now start AT the flaw position (fork at `mainLine[ply]`, drop the prepended flaw move) instead of one ply before, which also fixes the depth counter that was counting one level too low (now ends at 1 on the punchline like missed). New `forkPlyForOrientation` helper; missed lines unchanged | 2026-06-28 | 582df240 | [260628-pu2-uat-phase-140-analysis-board-allowed-col](./quick/260628-pu2-uat-phase-140-analysis-board-allowed-col/) |
| 260628-qta | Phase 140 UAT: analysis board ply / scroll. (1) Game mode keys on `game_id` alone (was `game_id` AND `ply`), so `/analysis?game_id=X` with no ply loads the game at ply 0 instead of free play. (2) The game card's Analyze button omits the `ply` param when the slider rests on the game's end position (opens at ply 0); a scrubbed-back slider still deep-links to that move (`buildGameAnalysisUrl` ply now optional). (3) The desktop move list aligns the initial-ply move to the TOP of the scroller on first open (was bottom via `block:'nearest'`), held until `currentNodeId` reaches the initial-ply node past the `loadMainLine` last-node transient | 2026-06-28 | aac82a37 | [260628-qta-phase-140-analysis-ply-scroll-uat](./quick/260628-qta-phase-140-analysis-ply-scroll-uat/) |
| 260628-shc | Phase 140 UAT: analysis board engine lines. (1) Each of the two Stockfish PV lines gets a right-pinned `ChevronDown` (shown only when the line is longer than `MAX_PLIES`=5) that toggles between the first 5 plies and the full PV; per-row expand state survives streaming depth updates (stable `lineIndex` key); the desktop engine `CardBody` changed `h-[78px] overflow-y-auto` → `min-h-[78px]` so the card grows to fit an expanded line instead of scrolling. (2) Clicking a line move now grafts the WHOLE sideline up to that move from the current anchor: `EngineLines.onMoveClick` signature `(from,to)` → `(uciMoves[])` passing `moves.slice(0,i+1)`; new `useAnalysisBoard.playUciLine` replays the UCI prefix from `currentNodeId` in one setState (reuses matching children, no duplicate branches) and lands on the last move — fixing the old `onMoveClick={makeMove}` that played only the single clicked move and skipped the moves before it | 2026-06-28 | 75156d60 | [260628-shc-phase-140-analysis-board-uat-chevron-to-](./quick/260628-shc-phase-140-analysis-board-uat-chevron-to-/) |
| 260628-r5v | Phase 140 UAT: analysis board. (1) Blunder/mistake icons now persist on every explored sideline move (was current-move-only): Analysis.tsx persists each freely-played node's live classification in `liveFlawByNode` (node-id keyed, FIFO-capped, stale-id/deleted-node guards, cleared on Reset) and merges it into `moveListMarkers`; VariationTree paints the severity glyph on any variation/free node, not just `isCurrent` (desktop + mobile). Also caches the per-node grading so stepping back re-shows the icon without re-running the engine (eval value already FEN-cached in `engineEvalByFen`). (2) Desktop engine lines `text-sm`→`text-xs` to match the compact mobile lines (user-approved exception to the text-sm floor, scoped to the engine surface); the `compact` split is now purely row layout | 2026-06-28 | 21a5d670 | [260628-r5v-uat-keep-blunder-mistake-icons-on-sideli](./quick/260628-r5v-uat-keep-blunder-mistake-icons-on-sideli/) |
| 260628-pcb | Desktop analysis board: player name + ELO (in parens) above and below the board (ordered by `boardFlipped`), each with their remaining clock at the current position (lucide `Clock` icon + m:ss) on the right. New `PlayerBar` component + 8 unit tests; clocks derived from `eval_series` per ply (even=White/odd=Black, latest ≤ current ply), hidden when a game has no `%clk`. Validated against the live `/api/library/games` response + dev DB (ply 69 → White 0:24 / Black 1:32). Follow-up: invisible top spacer in the right column (`lg:-mb-2`) aligns the Stockfish card top with the board top. Desktop only; mobile takeover unchanged | 2026-06-28 | 7f461121 | [260628-pcb-analysis-board-player-names-elo-clock](./quick/260628-pcb-analysis-board-player-names-elo-clock/) |
| 260628-u7d | Eval-chart flaw tooltip now shows the OPPONENT's tactic motif (missed:/allowed: + depth) on hollow-square markers, matching the user's own filled markers, on both the games card and `/analysis` (shared `EvalChart`). Backend-only, zero frontend changes: opponent tactic data already exists in `game_flaws` (Phase 113 emits both movers) and was withheld only by `player_only_gate` at read time. New ungated `fetch_page_game_flaws_both_colors` + `mover_is_white_at_ply` ply-parity helper feed ONLY the per-ply `tactic_by_ply` map; severity counts, curated chips, the Games-tab EXISTS filter, and stats stay player-gated (landmine guard test asserts blunder/mistake counts unchanged). Full backend suite green (2918 passed) | 2026-06-28 | 7fd6c91c | [260628-u7d-show-opponent-tactic-motif-in-eval-chart](./quick/260628-u7d-show-opponent-tactic-motif-in-eval-chart/) |
| 260629-n8e | `/analysis` live Stockfish feels snappier: first engine line now paints sub-100ms and sharpens in place (lichess-style) instead of waiting ~0.5–1s. Two changes in `useStockfishEngine.ts`: (1) adaptive first-paint debounce — `DEBOUNCE_MS`→`RAPID_STEP_DEBOUNCE_MS=150` + `lastFenChangeAtRef`; a settled move (or first mount) fires `setDebouncedFen` immediately, only rapid-succession FEN changes (held arrow-key stepping) fall back to the timer. (2) Relaxed the `bound==='exact'` gate AND added a live `commitPvSnapshot()` on every passing `info` line (the UI previously only painted at `bestmove`, so relaxing the bound alone did nothing) — eval now bounces for ~200–300ms then settles, by design. Stale-search / stop-pending discard guard preserved (info handler gated on `stateRef!=='thinking' \|\| stopPendingRef`). MultiPV 2, movetime 1500/nodes 2M, warm worker, tab-hide pause all unchanged. Multithreading explicitly NOT touched (D-3). All 1231 frontend tests + lint + tsc green | 2026-06-29 | 94aadd5f | [260629-n8e-make-analysis-page-live-stockfish-feel-s](./quick/260629-n8e-make-analysis-page-live-stockfish-feel-s/) |
| 260629-pq8 | Fix installed-PWA stale layout: SW precached index.html and served it cache-first, so an installed Android PWA launched a many-deploys-old shell (e.g. missing Library nav) until a manual reload. `vite.config.ts`: `globIgnores` adds `**/*.html` (drops index.html from the precache) + a `NetworkFirst` navigation route into an `html-shell` cache (online → always-fresh shell → current hashed assets; offline → last cached shell); `/api/` `NetworkOnly` kept first + `navigateFallback: null` so OAuth callback is unaffected. `main.tsx`: debounced `reg.update()` now also fires on `visibilitychange`/`focus` (the events that fire when Android resumes a frozen PWA), not just the hourly interval. Caddy already correct. Verified `dist/sw.js` has no `*.html` precache entries; lint + 1237 tests + build green | 2026-06-29 | 8c3400dc | [260629-pq8-fix-unreliable-pwa-cache-busting-stale-a](./quick/260629-pq8-fix-unreliable-pwa-cache-busting-stale-a/) |
| 260630-jsr | Fix Bug B in the forcing-line gate: make `apply_forcing_line_filter` depth-aware. It required EVERY solver node in the full stored PV line to be a unique only-move, so a tactic that already fired and won material at the firing node was rejected whenever the winning conversion had several near-equal follow-ups (the still-winning floor never truncates a flatly-winning line). Added a `firing_depth` param (the detector's tactic depth) so only solver nodes up to and including the firing node must be forced; the conversion tail is exempt. `firing_depth=None` preserves the legacy whole-line check (all existing gate tests unchanged); `_classify_tactic_gated` passes the detected depth; guard rejects a firing node lost to floor truncation. Diagnosed via UAT report case 27 (game 681358 ply 16, allowed fork ...e5 forking Bf4+Nd4): now survives. FORK/allowed suppression 97.6%→83.1%, HANGING_PIECE 96.5%→65.3%, no motif flooded to 0%. Follows the Bug A pre-flaw-eval fix (dc0077b7). 193+32 backend tests + ruff + ty green | 2026-06-30 | cd1d1a57 | [260630-jsr-fix-bug-b-in-the-forcing-line-gate-make-](./quick/260630-jsr-fix-bug-b-in-the-forcing-line-gate-make-/) |
| 260701-93s | SEED-072: stop serving tier-4 flaw-blob (gating backfill) games through the idle `/lease` path. Phase 145 wired tier-4 into `claim_eval_job(scope="idle")` as a fallthrough; Phase 146 removed the inline server walk that filled blobs on `/submit` (`_apply_submit` forces `blob_map={}`) but left the routing, so `/lease?scope=idle` never 204'd (always a ~3.3M NULL-blob backlog) and remote workers full-ply re-evaluated already-complete games (~5:1 submit:completion), never reaching their dedicated rung-4 `/flaw-blob-lease` → gating backfill starved. Deleted the tier-4 fallthrough from the idle scope so an empty tier-3 returns None → 204; workers then drain tier-4 via `/flaw-blob-lease` (→ `_claim_tier4_blob` → MultiPV-2 → `/flaw-blob-submit`, the only post-146 blob-writing path). Bundled `scope=None` keeps tier-4 (its sole consumer, the in-process server-pool drain, writes blobs via the MultiPV-2 pass, not `/submit`). New `test_idle_scope_returns_none_when_tier3_empty`; ruff + ty + eval-queue/worker/drain suites green | 2026-07-01 | e85164c5 | [260701-93s-remove-tier-4-blob-fallthrough-from-idle](./quick/260701-93s-remove-tier-4-blob-fallthrough-from-idle/) |
| 260701-lw4 | Replaced the tier-4 blob-backfill top-50 recency window (`TIER4_RECENCY_WINDOW`, a hard cutoff giving game #51+ zero draw probability) with a two-stage Efraimidis-Spirakis weighted lottery in `_claim_tier4_blob`, mirroring `_claim_tier3_derived`: stage 1 picks a non-guest user weighted by `last_activity` recency + floor, stage 2 picks that user's game weighted by `full_evals_completed_at` recency + floor (no `tc_multiplier` — blobs aren't TC-sensitive). The floor terms give every pending-blob game across the whole corpus non-zero mass so the old analyzed backlog (e.g. user 28's ~5k games) drains instead of being permanently dead-last behind freshly-analyzed games, while recency weighting keeps fresh dominant. Table-less/idempotent preserved (no eval_jobs row, no locking); all ES params bound via `sa.text` dict (QUEUE-08). Four tunable `TIER4_*` constants seeded from tier-3. New `test_claim_tier4_blob_anti_starvation_and_recency_preference` (old game aged 400d + floor monkeypatched to land P(old)≈0.19; finally-cleanup on all non-guest rows). Fairness/ordering fix, not throughput. ruff + ty + eval-queue suite green | 2026-07-01 | 9ac007ea | [260701-lw4-replace-tier-4-blob-backfill-top-50-rece](./quick/260701-lw4-replace-tier-4-blob-backfill-top-50-rece/) |

## Deferred Items

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

Last session: 2026-07-01T18:09:34.277Z
Stopped at: Phase 147 context gathered
Resume file: .planning/phases/147-persist-only-forcing-line-gated-tactic-tags-suppress-ungated/147-CONTEXT.md

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
| Phase 139 P01 | 45min | 3 tasks | 7 files |
| Phase 139 P02 | 20min | 2 tasks | 3 files |
| Phase 139 P03 | 5min | 1 tasks | 4 files |
| Phase 140 P01 | 30 | 3 tasks | 6 files |
| Phase 140-full-game-analysis-board P02 | 45min | 2 tasks | 4 files |
| Phase 140-full-game-analysis-board P03 | 15 | 2 tasks | 3 files |
| Phase 141 P01 | 15min | 3 tasks | 3 files |
| Phase 141 P02 | 25min | 2 tasks | 2 files |
| Phase 142 P01 | 301 | 2 tasks | 2 files |
| Phase 142 P02 | 5400 | 3 tasks | 2 files |
| Phase 142 P03 | 3600 | 3 tasks | 4 files |
| Phase 142 P04 | 900 | 2 tasks | 2 files |
| Phase Phase 143 PP01 | 15min | 2 tasks | 2 files |
| Phase 143 P02 | 20min | 2 tasks | 3 files |
| Phase 143 P03 | 10min | 3 tasks | 4 files |
| Phase 144-user-28-a-b-validation P01 | 45 | 2 tasks | 3 files |
| Phase 145 P01 | 7min | 3 tasks | 5 files |
| Phase 145 P02 | 16min | 2 tasks | 3 files |
| Phase 145 P03 | 15min | 3 tasks | 5 files |
| Phase 145-corpus-backfill-rollout P04 | 30 minutes | 2 tasks | 3 files |
| Phase 145 P05 | 60 | 2 tasks | 3 files |
| Phase 146 P02 | 8 | - tasks | - files |
