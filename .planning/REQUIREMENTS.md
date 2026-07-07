# Requirements: FlawChess — v2.0 FlawChess Engine

**Defined:** 2026-07-05
**Core Value:** Where Stockfish says "what is objectively best," the FlawChess Engine says "what is practically best *for you*" — the strongest line a player at your rating could realistically find and follow against an opponent defending like a real human at their level. Surfaced on the `/analysis` board in both free analysis and game review, client-side, with no server load.

## Milestone v2.0 Requirements

Committed scope for this milestone (MVP1 core, per SEED-082). Each maps to a roadmap phase.

### Search Core (ENGINE)

- [x] **ENGINE-01**: A user can request a practical-play analysis of any position and receive a ranked list of candidate root moves scored by *expected practical score* (not objective evaluation).
- [x] **ENGINE-02**: Node expansion draws candidate moves from the Maia policy top-k (opponent replies truncated at ~90% cumulative probability, renormalized) graded by a Stockfish shallow evaluation — the Phase 151 per-node primitive.
- [x] **ENGINE-03**: The search values non-root nodes as a Maia-prior-weighted expectation over expanded children, and the root as a max over candidates (the custom expectimax-in-MCTS backup rule).
- [x] **ENGINE-04**: The search applies the opponent's ELO at opponent-to-move nodes and the player's own ELO at the player's own future nodes (asymmetric self+opponent rating), keyed on actual side-to-move.
- [x] **ENGINE-05**: Leaf positions (explicit depth ~6–10 plies) are converted to expected score via the lichess eval→win% sigmoid.
- [x] **ENGINE-06**: The search core is exposed behind a stable `position + budget → ranked root lines` interface, so a depth-limited expectimax is a drop-in fallback behind the same contract.
- [x] **ENGINE-07**: The search produces identical output for identical inputs under a fixed node budget (deterministic: no Dirichlet noise, canonical tie-breaking).

### Parallel Grading & Providers (POOL)

- [x] **POOL-01**: Stockfish child/leaf grading runs across a pool of 2–4 single-threaded Stockfish.wasm workers in parallel, with no SharedArrayBuffer and no site-wide COOP/COEP.
- [x] **POOL-02**: A node-evaluation priority queue schedules grading work toward the currently-best root lines.
- [x] **POOL-03**: Maia move-probability distributions are provided per node (with a per-side ELO parameter) from a dedicated Maia worker, reusing the v1.32 client-side inference.
- [x] **POOL-04**: The Stockfish pool size adapts to the device so the page stays responsive and stays within the browser (mobile Safari) memory ceiling, and does not run concurrently with the standalone eval bar on the same position. (Code-complete: Plan 01 delivered workerPool.ts's adaptive sizing + lazy spawn/abort surface; Plan 02 delivered maiaQueue.ts's own isolated lazy-spawn/terminate lifecycle. SC4's real-device mobile-memory-ceiling UAT and the actual eval-bar mutual-exclusion wiring remain deferred to Phase 155, which is the first phase with a UI to drive them — tracked in 154-VALIDATION.md.)

### Anytime Display (DISPLAY)

- [x] **DISPLAY-01**: The engine emits results anytime — quick top-n lines appear immediately and refine live as the search accumulates visits. (Partial: Plan 02 delivered `useFlawChessEngine`'s onSnapshot throttle + abort/stopAll guard, fully unit-tested. DISPLAY-01 is shared across Plans 02/04's frontmatter and only closes when Plan 04 actually surfaces the hook on the `/analysis` page.)
- [x] **DISPLAY-02**: Each candidate line displays its modal path (the player's chosen moves plus the opponent's most-likely replies).
- [x] **DISPLAY-03**: Each ranked move displays the objective-vs-practical score pair (the objective Stockfish evaluation alongside the practical-for-you score). (Complete: Plan 01 delivered the `expectedScoreToWhitePovCp` inverse-sigmoid conversion function; Plan 03's `FlawChessEngineLines` card renders the visible two-number score-pair badge, closing DISPLAY-03.)
- [x] **DISPLAY-04**: The engine surfaces on the free-analysis `/analysis` board (arbitrary position + free play).

### Board Arrows (ARROW)

- [x] **ARROW-01**: A new FlawChess Engine top-2 arrow layer renders the engine's best practical moves on the board, refining live with the search.
- [x] **ARROW-02**: The FlawChess Engine, Stockfish top-2, and (in game review) played-move arrow layers are each individually toggleable.
- [x] **ARROW-03**: The existing played-move arrow (game review) and Stockfish top-2 arrow are reused; there is no dedicated Maia arrow layer (Maia moves stay reachable by hovering the Moves-by-Rating chart / prose).
- [x] **ARROW-04**: Engine output is always framed as the "best **practical** move for you," never "best move" unqualified; disagreement with Stockfish reads as intentional.

### Game Review Integration (REVIEW)

- [x] **REVIEW-01**: The engine runs on the game-review board (whole game via `?game_id&ply`) as well as in free analysis (satisfied incidentally by the shared `Analysis.tsx`; Phase 157 confirms end-to-end parity there). Confirmed via live human UAT 2026-07-07.
- [x] **REVIEW-02**: The FlawChess Engine card surfaces a prose agreement verdict — whether its top **practical** move agrees or diverges from Stockfish's top **objective** move, citing both evals, with the named moves hoverable (arrow + popover) and click-to-play. Reframed 2026-07-07 from "what you played vs practical best" (that game-review-only comparison is now SEED-086).

## Future Requirements

Acknowledged, deferred by design to a later milestone (not in this roadmap).

### Advanced surfacing (TRAP)

- **TRAP-01**: Dedicated trap-finder / "best practical try" surfacing (the swindle ranking is emergent in MVP1's search; this adds explicit UI for it).
- **TRAP-02**: Branch-point display ("if instead …Qxb2, which ~30% of opponents play, then…").

### Calibration & performance (CAL / PERF)

- **CAL-01**: Per-ELO-bucket leaf sigmoids fit from the benchmark DB, replacing the single rating-agnostic lichess curve (a clean isolated swap behind ENGINE-05).
- **CAL-02**: Time-pressure conditioning — clock→temperature and clock→ELO-offset curves calibrated from imported `%clk`/`clk`, applied as per-side node parameters (possibly the most defensible genuine novelty axis).
- **PERF-01**: SharedArrayBuffer-multithreaded root grading (requires COOP/COEP cross-origin isolation — deployment blast radius beyond the engine).
- **CAL-03**: Adopt Maia-2 dual-skill attention as the asymmetric self+opponent rating model in place of independent per-rating Maia-1 queries.

## Out of Scope

Explicitly excluded this milestone. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| Server-side search / browser↔server search loop | Latency-miserable; the engine is client-side everything, reusing the v1.32 Maia + v1.29 Stockfish.wasm workers, zero server load |
| App-level Zobrist / transposition cache | Positions diverge too fast to pay off; Stockfish.wasm's internal TT gives partial reuse for free (SEED-082) |
| Persisting analysis to the DB | Analysis state stays ephemeral in the URL, consistent with v1.29 D-4 (no schema, no new endpoints) |
| Dedicated Maia arrow layer | Redundant with the existing Moves-by-Rating chart / prose hover; dropped from the seed's original 4-layer draft |
| Presenting output as "best move" unqualified / claiming a novel engine | Polecat + vala-bot ship the core practical-play concept already; framing is "a practical-play analysis engine built on Stockfish and Maia," the asymmetric self+opponent rating is the only unclaimed hook |
| Feeding search results back to "sharpen" the Maia prior | MCTS degrades Maia move accuracy when it reshapes Maia's own prediction; Maia's static policy is used as fixed expectimax weights, never re-searched |

## Traceability

Which phases cover which requirements. Populated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| ENGINE-01 | Phase 153 | Complete |
| ENGINE-02 | Phase 153 | Complete |
| ENGINE-03 | Phase 153 | Complete |
| ENGINE-04 | Phase 153 | Complete |
| ENGINE-05 | Phase 153 | Complete |
| ENGINE-06 | Phase 153 | Complete |
| ENGINE-07 | Phase 153 | Complete |
| POOL-01 | Phase 154 | Complete |
| POOL-02 | Phase 154 | Complete |
| POOL-03 | Phase 154 | Complete |
| POOL-04 | Phase 154 | Complete (SC4 real-device UAT deferred to Phase 155) |
| DISPLAY-01 | Phase 155 | Complete |
| DISPLAY-02 | Phase 155 | Complete |
| DISPLAY-03 | Phase 155 | Complete |
| DISPLAY-04 | Phase 155 | Complete |
| ARROW-01 | Phase 156 | Complete |
| ARROW-02 | Phase 156 | Complete |
| ARROW-03 | Phase 156 | Complete |
| ARROW-04 | Phase 156 | Complete |
| REVIEW-01 | Phase 157 | Pending |
| REVIEW-02 | Phase 157 | Complete |

**Coverage:**

- Milestone v2.0 requirements: 21 total (corrected — the "19" figure recorded at requirements-definition time was a miscount; ENGINE-01..07 [7] + POOL-01..04 [4] + DISPLAY-01..04 [4] + ARROW-01..04 [4] + REVIEW-01..02 [2] = 21)
- Mapped to phases: 21/21
- Unmapped: 0

---
*Requirements defined: 2026-07-05*
*Last updated: 2026-07-05 after roadmap creation (Phases 153-157)*
