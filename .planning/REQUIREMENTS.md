# Requirements: FlawChess — v1.32 Maia-3 Human-Move Enrichment

**Defined:** 2026-07-04
**Core Value:** Position-precise WDL across openings + endgames + time pressure on top of users' actual chess.com / lichess games — now extended on the analysis board with a *human*-model second opinion: what a player at your rating would actually do, and how bad your flaws are in *practical* (not just objective) terms.

**Source:** SEED-081 (design locked in a 2026-07-04 `/gsd-explore` session; feasibility settled by spikes 004–006). Browser-only, client-side onnxruntime-web inference, **zero DB writes**.

## v1 Requirements

Requirements for this milestone. Each maps to a roadmap phase (151 or 152).

### Licensing (LIC)

- [x] **LIC-01**: FlawChess is relicensed from MIT to **AGPL-3.0** — `LICENSE` replaced, and README / package metadata / any license references updated to reflect AGPL.
- [x] **LIC-02**: The app shows a visible **attribution + offer-source notice** for Maia-3 (link to the CSSLab source repo + AGPL license text + the model artifact) and cites the Chessformer paper.

### Maia Serving (MAIA)

- [x] **MAIA-01**: The unmodified `maia3_simplified.onnx` is obtained, **version-pinned**, and loaded as a runtime data asset; its exact input encoding (board planes + how ELO is fed) and output tensor layout (policy 64×64 vs flat; WDL order) are confirmed against the reference client.
- [x] **MAIA-02**: onnxruntime-web runs the model in a **Web Worker**, **lazy-loaded only when the analysis board opens** — never in the initial app bundle.
- [x] **MAIA-03**: Our own glue (board→tensor encoding, ELO input, **legal-move masking**, softmax) produces a **normalized, deterministic per-legal-move probability distribution** for a given FEN + ELO. No AGPL inference/encoding JS is copied or bundled.
- [x] **MAIA-04**: A single forward pass (or an efficient ELO sweep) yields the **full per-ELO probability curve** across the rating ladder for every legal move, plus the position's **Maia WDL** value; the player's ELO is derived from **rating at game time** (`games.white_rating` / `games.black_rating`). *(Plan 03 delivered the "rating at game time" data source; Plan 04 delivered the per-ELO curve + WDL computation mechanism (`useMaiaEngine`'s batched ELO-ladder inference); Plan 06 wired the ELO-selector default from that data source into the hook's `selectedElo` input (`useMaiaEloDefault`) and consumed the curve in the analysis UI — COMPLETE.)*
- [x] **MAIA-05**: The inference cache is **ephemeral and board-session-scoped only** — no persistence of any kind (no DB, no localStorage of Maia artifacts).
- [~] **MAIA-06** (partial — latency deferred, accepted 2026-07-05): Model loads with **no unsupported-op errors** ✓, static download/artifact sizes recorded ✓, and the D-10 model-size decision was made (smallest `maia3_simplified.onnx` retained) on a qualitative "felt responsive" basis. **Deferred:** numeric per-device (desktop/phone) cold-load + per-position latency (WASM vs WebGPU; single call vs ELO sweep) were NOT recorded during the live pass — `151-MAIA-MEASUREMENTS.md` §2 marks those rows "NOT YET MEASURED". Gap disclosed by the executor and accepted at phase close; capturable as a follow-up on a real device.

### All-Position Surfaces (SURF)

- [x] **SURF-01**: For **every position** on the analysis board, a **"Moves by Rating" chart** (Recharts, `theme.ts` colors) renders one probability line per candidate move over the ELO ladder.
- [x] **SURF-02**: The chart marks the **player's ELO with a vertical "you are here" reference line** and visually emphasizes the **played move** and the **engine-best move**.
- [x] **SURF-03**: The chart's line set is capped at **top-N-by-peak probability** (default N ≈ 6), **always unioned with {played move, engine-best move}** even when they fall outside the top-N.
- [x] **SURF-04**: A **Maia WDL eval bar** renders on the **LEFT** of the board and the **Stockfish eval bar** on the **RIGHT**, both shown simultaneously for **all positions** (human-practical left, engine-objective right). *(Plan 05 delivered the mechanism — `EvalBar`'s `whiteFraction`/`testId` override so one component serves both bars; Plan 06 mounted both bars on the analysis board (`analysis-maia-eval-bar` LEFT, `analysis-eval-bar` RIGHT) for game mode and free play — COMPLETE.)*
- [x] **SURF-05**: The chart and Maia bar **re-compute live on every board navigation**, in-memory, with no server round-trip.

### Flaw Overlay (FLAW)

- [ ] **FLAW-01**: When the current move **is a flaw**, a **verdict banner** overlays the chart with the salience × trainability quadrant call ("Growth edge — drill this" / "Even masters fall for this" / "You rarely err here" / above-your-level).
- [ ] **FLAW-02**: The verdict derives **salience** = `P(blunder move | your ELO)` and **trainability** = `P(blunder | your ELO) − P(blunder | top ELO)` from the stored curve — an **endpoint** difference, robust to non-monotonic (hump/U) curve shapes, never a local slope.
- [ ] **FLAW-03**: The **Maia-WDL practical-severity reframe** is applied to the flaw — the human win% reframes how bad the flaw is relative to the objective Stockfish eval (Stockfish stays the objective source of truth; Maia adds the practical lens).
- [ ] **FLAW-04**: **Precision-first fallback** — where Maia's calibration is not trustworthy for the relevant ELO bucket, the verdict is **withheld** rather than shown wrong (consistent with the tactic-tag NULL-on-low-confidence stance).

### Validation Gate (VALID)

- [x] **VALID-01**: Maia's **calibration is validated by eyeballing live output** across representative positions before the feature is considered shippable — Maia-WDL ↔ Stockfish comparability (Q-014) and low/high-ELO calibration + platform-rating mapping (Q-015) answered live, since the ephemeral in-browser surface *is* the quality gate.

## v2 Requirements

Deferred to a future, persistence-gated milestone. Tracked, not in this roadmap.

### Aggregate Rollup — Pillar C (AGG)

- **AGG-01**: History-wide rollup of per-flaw salience/trainability across the user's games via `apply_game_filters()` to surface systematic level-relative weaknesses ("you commit high-trainability traps 2× the Maia baseline for your level").
- **AGG-02**: Persist the per-ELO curve + derived Maia signals (`game_flaws` schema + flaw-node backfill — a single deterministic Maia forward pass per flaw decision node).

### Human-Playable-Line Engine (HPL)

- **HPL-01**: SEED-082 — Maia-filtered Stockfish surfacing the strongest *human-plausible* line at a target ELO (depends on this milestone's Maia serving layer).

## Out of Scope

Explicitly excluded for this milestone.

| Feature | Reason |
|---------|--------|
| Any DB write / persistence of Maia signals | Locked browser-only design; ephemeral cache is the calibration quality gate; model size still being chosen, so a persisted artifact keyed to it is a migration liability |
| Pillar C aggregate weakness rollup | Impossible without persistence (can't aggregate values that only existed live); a separate future decision (AGG, v2) |
| `game_flaws` schema change / flaw-node backfill | Persistence-gated; not needed for the live browser feature |
| Server-side / remote-worker Maia inference | Resolved to client-side (spikes 004–006); the remote fleet is pull-based batch precompute, unfit for interactive latency. Server-side backend endpoint kept only as a documented fallback if client-side proves unviable |
| SEED-082 human-playable-line engine | Depends on this milestone's Maia infra; a later milestone |
| Maia model fine-tuning / modification | Any modification triggers AGPL §13 publish-source and forks the model into its own project; the model stays unmodified |

## Traceability

Provisional mapping (finalized by the roadmapper).

| Requirement | Phase | Status |
|-------------|-------|--------|
| LIC-01 | Phase 151 | Complete |
| LIC-02 | Phase 151 | Complete |
| MAIA-01 | Phase 151 | Complete |
| MAIA-02 | Phase 151 | Complete |
| MAIA-03 | Phase 151 | Complete |
| MAIA-04 | Phase 151 | Complete (Plan 03 data source + Plan 04 curve/WDL mechanism + Plan 06 UI wiring) |
| MAIA-05 | Phase 151 | Complete |
| MAIA-06 | Phase 151 | Partial (latency deferred, accepted) |
| SURF-01 | Phase 151 | Complete |
| SURF-02 | Phase 151 | Complete |
| SURF-03 | Phase 151 | Complete |
| SURF-04 | Phase 151 | Complete (Plan 05 EvalBar mechanism + Plan 06 both bars mounted LEFT/RIGHT) |
| SURF-05 | Phase 151 | Complete |
| VALID-01 | Phase 151 | Complete |
| FLAW-01 | Phase 152 | Pending |
| FLAW-02 | Phase 152 | Pending |
| FLAW-03 | Phase 152 | Pending |
| FLAW-04 | Phase 152 | Pending |

**Coverage:**

- v1 requirements: 18 total
- Mapped to phases: 18
- Unmapped: 0 ✓

---
*Requirements defined: 2026-07-04*
*Last updated: 2026-07-04 after initial definition (SEED-081, research skipped — feasibility settled by spikes 004–006)*
