# Requirements: FlawChess — v2.4 Backend Gem & Great Detection

**Defined:** 2026-07-16
**Core Value:** Position-precise WDL across openings + endgames + time pressure on top of users' actual chess.com / lichess games, with personalized LLM commentary and an auto-generated opening-strengths/weaknesses report.

**Milestone goal:** Move gem detection off the brittle client-side sweep (v2.3 Phase 172) into the backend full-game analysis pass, add a second "Great" tier, and make gems/greats stored first-class artifacts (peers to blunder/mistake/tactic tags) that power the analysis board and a game-level filter. Sourced from SEED-108 (design locked via /gsd-explore 2026-07-16, D-2 amended at kickoff to the `INACCURACY_DROP` row gate; supersedes SEED-107).

## v1 Requirements

Requirements for this milestone. Each maps to a roadmap phase.

### Backend Inference & Storage (GEMS)

- [x] **GEMS-01**: Every analyzed game stores candidate best-move rows in a new sibling table peer to `game_flaws` (neutral name, e.g. `game_best_moves`): `game_id` FK ondelete=CASCADE, `ply`, `maia_prob`, best/second eval (final column set at phase planning) — floats, never a gem/great boolean; natural-key unique on `(game_id, ply)`.
- [x] **GEMS-02**: A candidate row is stored only for out-of-book plies where the played move == Stockfish best AND `best_es − second_es ≥ INACCURACY_DROP` (0.05) — the amended D-2 gate ("the runner-up would have been at least an inaccuracy").
- [x] **GEMS-03**: The backend scores candidate plies with Maia-3 (`maia3_simplified.onnx` via onnxruntime, one-time session load) during eval-apply, where `second_best_map` already lands; remote workers stay pure Stockfish with no protocol change.
- [x] **GEMS-04**: The Python port of the 12-plane board→tensor encoding passes a fixture-based parity check against client Maia outputs (tolerance defined at phase planning).
- [x] **GEMS-05**: Maia inference uses the player's pinned lichess-blitz-equivalent rating at game time (the `pinnedEloForMover` rung, not the reactive slider), clamped to [600, 2600] — the frontend `MAIA_ELO_LADDER` bounds (Phase 174 D-04: the "1100–2000" band is Maia-3's validated draw-rate sub-band, not the clamp bounds).
- [x] **GEMS-06**: onnxruntime + numpy are isolated behind a uv extra/dependency group so the worker image stays lean.
- [x] **GEMS-07**: Gem (`maia_prob ≤ 0.20`) and Great (`(0.20, 0.50]`) classification happens at query time from stored floats + the C2 `MISTAKE_DROP` (0.10) margin — both tiers retunable with zero re-analysis; the 0.50 Great ceiling is a starting constant to calibrate against real per-game frequency.

### Analysis Board (BOARD)

- [x] **BOARD-01**: The analysis board shows gem/great markers from stored backend data for analyzed games (`EvalPoint` gains gem/great fields) — markers appear regardless of device or live-engine load.
- [x] **BOARD-02**: `useGemSweep.ts` is retired (or demoted to a free-play fallback for positions with no stored analysis); SEED-107 closes as superseded.

### Game Filter (FILT)

- [x] **FILT-01**: User can filter Library games by "has gem" / "has great" moves via the existing flaw/tactic game-filter machinery.

### Backfill (BACK)

- [ ] **BACK-01**: The existing analyzed corpus gains best-move rows opportunistically via the tier-4 lottery pattern (global + random, no deterministic sweep, no ETA); backfill lottery keying (reuse tier-4 blob lottery vs a parallel lottery on missing rows) decided at phase planning.

## Future Requirements

Deferred beyond this milestone. Tracked, not in this roadmap.

- **Gem/Great frequency calibration from live data** — re-check the 0.20 gem ceiling and calibrate the 0.50 Great ceiling once the pipeline produces real per-game frequencies (same playbook as Phase 172's 0.1 → 0.2 retune). Constants change only; enabled by GEMS-07.
- **Gem/great aggregate analytics** — per-user gem/great rate stats, trends, or comparison surfaces (only the game filter ships in v2.4).

## Out of Scope

Explicitly excluded from this milestone. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| Maia inference on the remote workers | Rejected by D-3 — workers stay pure Stockfish (no protocol change, no fleet coordination). Fallback only if backend RAM/CPU pressure materializes. |
| Chess.com-style hand-coded exclusion rules (trivial recaptures, forced sequences) | Rejected by D-1 — Maia probability already encodes trivialness; an obvious recapture scores 80–95% and falls out of the band with zero rule code. |
| Storing gem/great booleans or per-ELO probability curves | Rejected by D-4 — floats at the pinned rung only; classification is a query-time constants decision. |
| Ungated candidate rows (original D-2) | Amended at kickoff to the `INACCURACY_DROP` (0.05) row gate; loosening below 0.05 would need corpus re-analysis — accepted trade-off. |
| Deterministic backfill sweep with ETA / 100% guarantee | The tier-4 lottery pattern is opportunistic by design. |

## Traceability

Which phases cover which requirements. Filled during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| GEMS-01 | Phase 174 | Complete |
| GEMS-02 | Phase 174 | Complete |
| GEMS-03 | Phase 174 | Complete |
| GEMS-04 | Phase 174 | Complete |
| GEMS-05 | Phase 174 | Complete |
| GEMS-06 | Phase 174 | Complete |
| GEMS-07 | Phase 174 | Complete |
| BOARD-01 | Phase 175 | Done |
| BOARD-02 | Phase 175 | Done |
| FILT-01 | Phase 175 | Done |
| BACK-01 | Phase 176 | Pending |

---
*Requirements defined: 2026-07-16*
*Last updated: 2026-07-16 — roadmap created, Phases 174–176 (11/11 requirements mapped, no orphans)*
