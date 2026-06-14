# Requirements — Milestone v1.26 Full-Game Eval Pipeline

Sourced from SEED-012 (server-first v1 amendment, decisions D-1..D-8) and the
Q-008 spike findings (`.planning/spikes/`, spikes 001–003). All throughput
numbers referenced below are measured on prod, not estimated.

## v1.26 Requirements

### Eval Pipeline (EVAL)

- [x] **EVAL-01**: Every ply of a queued game gets `eval_cp`/`eval_mate` persisted in `game_positions` (terminal game-over positions excluded). No book-skip: the ply≤20 dedup (EVAL-03) makes the heavily-shared opening region cheap, eval charts get no opening gap, and the collector needs no openings-table dependency. Cost ceiling if dedup never hits: ~+26% vs the book-skip plan (~6.3k games/day floor)
- [x] **EVAL-02**: Full-game analysis searches at the Lichess-parity budget — 1,000,000 nodes, NNUE, multiPV=1, Hash=32MB, Threads=1 per worker (the existing depth-15 entry-ply convention is replaced for games analyzed by this pipeline)
- [x] **EVAL-03**: Before each engine call on plies ≤ 20, an indexed `full_hash` lookup reuses any existing server eval instead of recomputing
- [x] **EVAL-04**: `best_move` (PV[0], UCI) is persisted for *every* evaluated position (enables an engine-best-move step-through display and "better move you missed"); the *full* engine PV (UCI, ~12-ply cap) is persisted only at the position *after* each flawed move — the refutation line SEED-039's tactic-motif classifier consumes, so the future tagger needs no second engine pass. Opening-region `best_move` rides the ply≤20 `full_hash` dedup transplant. Pre-117-analyzed games (engine + lichess) are backfilled demand-driven on re-touch, not mass re-enqueued. (Amended 2026-06-13 — D-117-01/02/12)
- [x] **EVAL-05**: Each game carries a full-analysis completion marker distinct from the existing entry-ply `evals_completed_at` semantics, so coverage stats and gates can tell the two apart
- [x] **EVAL-06**: When the background drain finishes a game's full analysis, the game flows through `classify_game_flaws` automatically — `game_flaws` rows and summary counts appear without user action. Import itself stays fast: the hot import lane and its quick entry-ply eval pass are untouched; full evals and flaws arrive progressively after import

### Priority Queue (QUEUE)

- [x] **QUEUE-01**: Analysis work drains from a tiered priority queue: explicit user requests > automatic recent windows > idle backlog
- [x] **QUEUE-02**: Within a tier, users are served round-robin (one game each, cycle); within a user, games are ordered time-control-weighted (classical > rapid > blitz > bullet) then most-recent-first (amended 2026-06-13 — D-117-04)
- [x] **QUEUE-03**: A tier-1 explicit request fans one game's positions across the entire worker pool (~10s wall-clock per game, measured)
- [ ] **QUEUE-04**: Import completion and user activity automatically enqueue the user's ~200 most recent unanalyzed games (tier 2)
- [x] **QUEUE-05**: Idle workers drain the backlog (tier 3) so cores never sit idle; full-DB coverage accrues over time
- [x] **QUEUE-06**: Workers interact with the queue through a lease/report contract (claim job → post evals), so a future browser/external worker is an additive change (SEED-012 D-8)
- [x] **QUEUE-07**: Worker pool memory is explicitly bounded and accounted against the backend container's 4g limit before `STOCKFISH_POOL_SIZE` is raised; the drain coexists with the import-time eval pass without competing during active imports
- [x] **QUEUE-08**: Guest accounts (`users.is_guest`) are excluded from all analysis tiers (automatic, explicit, backlog) — full-game analysis requires a real account; guest-facing UX presents account promotion as the unlock. Rationale: inactive-guest games are cleanup candidates, so analyzing them is wasted compute

### Demand UX (EVUX)

- [ ] **EVUX-01**: User can trigger "analyze more games" explicitly and see progress (reusing the import-job mental model)
- [ ] **EVUX-02**: User can see their analysis coverage (% of games analyzed / N of M) on eval-dependent surfaces, with a CTA when coverage is low
- [ ] **EVUX-03**: User sees in-flight analysis state (queued/analyzing) for their games without refreshing blindly

### Eval Convention Fix (EVALFIX) — Phase 117.1 (INSERTED, SEED-044)

- [x] **EVALFIX-01**: `game_positions.eval_cp`/`eval_mate` store the eval of the position AFTER the move at every row, for both engine-drained and lichess `%eval` games — a single post-move convention with no per-source branch in `classify_game_flaws`. (Root cause: the engine drain stored the pre-push position's eval = eval BEFORE the move, while the classifier assumed post-move — off-by-one for every chess.com game.)
- [x] **EVALFIX-02**: The drain evaluates the terminal position so the last move of every game has an "after" eval and is flaw-assessable (no unassessable game-ending blunders); `best_move`/`pv` remain keyed to the decision ply (the move-played row), not shifted
- [x] **EVALFIX-03**: The opening-region dedup transplant (`eval_drain._fetch_dedup_evals`/`_resolve_full_eval`) recovers a position's eval correctly under post-move storage via a one-ply shift on the donor read; the `best_move` transplant is unchanged; the `eval_drain.py:182-191` convention comment is rewritten to document post-move + the shift
- [x] **EVALFIX-04**: A migration NULLs `eval_cp`/`eval_mate`/`best_move`/`pv` and clears `full_evals_completed_at`/`full_pv_completed_at` for engine games (`lichess_evals_at IS NULL`), deletes their `game_flaws`, and TRUNCATEs the `eval_jobs` queue/lease table (clean slate — clears stale leases/jobs so games re-enqueue cleanly under the new convention); the background drain re-materializes everything
- [x] **EVALFIX-05**: Regression fixtures (engine games 1420780, 1073118; lichess game 640092) produce coherent mistake/blunder detection through the unified post-move path; flaw-PV coverage is re-verified after re-eval (the off-by-one is the suspected cause of the ~32% flaw-PV coverage TODO)

## Future Requirements (deferred)

- Browser WASM workers leasing from the same queue (SEED-012 client path, phase 2 of D-8)
- Tactic-motif classification over the captured PVs (SEED-039 — consumes EVAL-04's output)
- Standalone native worker for power users / free external compute (Oracle ARM etc.)

## Out of Scope

- **Tactic motif classifier (SEED-039)** — separate milestone; v1.26 only captures the PVs it needs
- **Train drills (SEED-037)** — depends on the best-move endpoint (SEED-036 remainder) and coach-settled loop design
- **Client-side analysis** — deferred per SEED-012 D-1; the D-8 queue shape keeps it additive
- **Eval validation / trust model** — SEED-012 non-goal #4 stands (server is the only writer in v1)
- **Cloud eval APIs (lichess cloud-eval, chessdb.cn)** — calibration risk for marginal coverage; ruled out during the 2026-06-12 explore session

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| EVAL-01 | Phase 116 | Complete |
| EVAL-02 | Phase 116 | Complete |
| EVAL-03 | Phase 116 | Complete |
| EVAL-04 | Phase 117 | Complete |
| EVAL-05 | Phase 116 | Complete |
| EVAL-06 | Phase 117 | Complete |
| QUEUE-01 | Phase 117 | Complete |
| QUEUE-02 | Phase 117 | Complete |
| QUEUE-03 | Phase 117 | Complete |
| QUEUE-04 | Phase 118 | Pending |
| QUEUE-05 | Phase 117 | Complete |
| QUEUE-06 | Phase 117 | Complete |
| QUEUE-07 | Phase 116 | Complete |
| QUEUE-08 | Phase 117 | Complete |
| EVALFIX-01 | Phase 117.1 | Complete |
| EVALFIX-02 | Phase 117.1 | Complete |
| EVALFIX-03 | Phase 117.1 | Complete |
| EVALFIX-04 | Phase 117.1 | Complete |
| EVALFIX-05 | Phase 117.1 | Complete |
| EVUX-01 | Phase 118 | Pending |
| EVUX-02 | Phase 118 | Pending |
| EVUX-03 | Phase 118 | Pending |
