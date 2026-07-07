# Phase 158: FlawChess Engine displayed-eval provenance reconciliation (SEED-087) - Context

**Gathered:** 2026-07-07
**Status:** Ready for planning
**Source:** Seed Express Path (.planning/seeds/SEED-087-flawchess-engine-eval-provenance-reconciliation.md, amended 2026-07-07)

<domain>
## Phase Boundary

Reconcile the Stockfish evals displayed across the three `/analysis` surfaces (Stockfish card + eval bar, FlawChess card + agreement verdict, Maia chart/quality bar) so any move shown on two or more surfaces renders the identical number. This is a **display/verdict overlay only**: the locked Phase 153 MCTS search core, its internal leaf grades, and the practical-score ranking (brown badges) are untouched.

Root cause (confirmed in code 2026-07-07): three independent Stockfish searches feed the displays —

1. `useStockfishEngine.ts` (free `go movetime 1500`, MultiPV=2) → SF card + eval bar. Deep, authoritative.
2. `workerPool.ts` MCTS grading pool (`go depth 14 searchmoves ... movetime 2500`, 8 MB hash) → `RankedLine.objectiveEvalCp`, the FC card's blue numbers. Shallow, capped.
3. `useStockfishGradingEngine.ts` (Phase 151.1; searchmoves MultiPV over `shownSans`, same depth-14/2500 ms constants) → `qualityBySan`, the Maia chart/quality-bar evals.

Observed (live UAT 2026-07-07): exd5 +1.3 (FC) vs +1.1 (Maia, SF); Bc5 +0.9 (FC, Maia) vs +0.8 (SF); 2100-ELO verdict graded FC pick Qc7 +2.8 above SF-best O-O +1.3, which is logically impossible with comparable evals.

</domain>

<decisions>
## Implementation Decisions

### Single source of truth + lookup precedence (LOCKED)
- The free SF MultiPV run (`useStockfishEngine`) is the authoritative eval source. Every displayed move on every surface resolves its eval by UCI lookup: **free run first, shared grading run second**.
- The MCTS pool's shallow grades (`objectiveEvalCp` from `workerPool.ts`) stop being a display source anywhere. They remain internal to the search.

### ONE shared fallback run, not per-card (LOCKED)
- `useStockfishGradingEngine` is promoted to the single shared fallback. Per-card fallbacks are rejected: most displayed FC moves are also in the Maia candidate set, so per-card grading would leave the FC and Maia cards disagreeing with each other.
- Its candidate set becomes `shownSans ∪ displayed FC moves`.
- Its budget is raised to analysis-grade depth: the depth-14 / 2500 ms cap is the proven skew source (the seed's O-O +1.4 ≈ +1.3 evidence shows `searchmoves` restriction itself does NOT skew evals; only the depth/hash cap did). The exact budget is chosen from a measured latency/depth trade on real positions (see Open Measurement below).

### Gating (LOCKED)
- The shared grading run must run when *either* consumer needs display evals: `maiaEnabled || flawChessEnabled` (today it is gated on `maiaEnabled` only). The candidate union reflects which consumers are active.

### Quality buckets classify from reconciled evals (LOCKED)
- `classifyMoveQuality` must classify from the same reconciled post-lookup evals it displays, so a move's number and severity color cannot disagree at bucket boundaries.
- This covers **every** consumer of the 5-bucket classification (best / good / inaccuracy / mistake / blunder), explicitly including the Maia Moves-by-Rating chart's **line and SAN-label colors** (user note 2026-07-07), the move-quality bar segments, and the position-difficulty verdict (`positionVerdict.ts`) — not just the quality bar. All category colorings on the Maia card derive from the unified evals this phase produces.

### Verdict consumes the lookup (LOCKED)
- The agreement verdict's FC-pick and SF-best evals both come from the lookup, making "FC pick grades higher than the objective best" impossible by construction.

### Scope fence (LOCKED)
- Do NOT touch the MCTS search internals, the backup rule, the practical-score ranking, or Phase 153's locked core.
- Explicitly out of scope (flagged, not folded in): whether shallow internal pool grades ever mis-*rank* the practical pick — a separate search-internal fidelity question.
- Configurable FC/SF line counts (`MAX_LINES`) are NOT a deliverable of this phase, but the reconciliation must be per-move (count-agnostic) so configurable counts fall out later for free.

### Open Measurement (Claude's Discretion on method, result feeds constants)
- The free run's MultiPV width trades against eval-bar depth (fixed time budget); the grading run's MultiPV = candidate-union size trades against its depth. Measure latency/depth on real positions before fixing the constants. Named constants, no bare thresholds (project rule).

### Claude's Discretion
- Where the lookup lives (a hook, a lib module, or Analysis.tsx-level memo) — pick the seam that keeps functions small and avoids threading context objects.
- How progressive refinement is handled while searches are still streaming (evals may update live; no layout jump per Phase 157 precedent).
- Test strategy, subject to project norms (vitest; pure lib functions preferred for the lookup/precedence logic).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Design source
- `.planning/seeds/SEED-087-flawchess-engine-eval-provenance-reconciliation.md` — the full amended design: three provenance chains, shared-fallback rationale, wiring details, breadcrumbs.

### Code touchpoints (from the seed's breadcrumbs)
- `frontend/src/hooks/useStockfishEngine.ts` — authoritative free run (`MULTIPV = 2`, `MOVETIME_MS = 1500`).
- `frontend/src/hooks/useStockfishGradingEngine.ts` — becomes the shared fallback (`GRADING_TARGET_DEPTH = 14`, `GRADING_MOVETIME_SAFETY_CAP_MS = 2500`).
- `frontend/src/lib/engine/workerPool.ts` — MCTS pool; its grades leave the display path.
- `frontend/src/pages/Analysis.tsx` — wires all three engines; `shownSans`, `grading` → `qualityBySan` (~lines 703-740); passes `engine.pvLines[0]` to the verdict.
- `frontend/src/lib/moveQuality.ts` — `classifyMoveQuality` / `selectCandidatesByMass`.
- `frontend/src/lib/flawChessVerdict.ts` — verdict classifier (`NEARLY_SAME_EVAL_CP` copy gate from e930cd91).
- `frontend/src/components/analysis/FlawChessEngineLines.tsx` — FC card (`MAX_LINES = 2`).
- `frontend/src/components/analysis/FlawChessAgreementVerdict.tsx` — verdict prose.
- `frontend/src/components/analysis/MaiaHumanPanel.tsx`, `MovesByRatingChart.tsx`, `MaiaMoveQualityBar.tsx` — Maia surfaces consuming `qualityBySan` / `engineTopLines`.

### Related prior work
- Phase 157 (`.planning/phases/157-flawchess-agreement-verdict-prose-hoverable-moves/`) — verdict component + e930cd91 copy-gate fix (symptom patch this phase replaces with the root fix).
- Phase 151.1 — built `useStockfishGradingEngine`; its "multipv is an eval rank, key by pv[0]" caveat applies to every new MultiPV consumer in this phase.

</canonical_refs>

<specifics>
## Specific Ideas

- Target architecture (from the amended seed):
  ```
  one free SF run @ MultiPV = N              ← source of truth (also drives the eval bar)
  one shared grading run (searchmoves over shownSans ∪ FC displayed moves, analysis-grade depth)
    ├─ SF card:   its top N_sf lines (free run by definition)
    ├─ FC card:   each displayed FC move → lookup: free run ▸ shared grading run
    ├─ Maia card: each shown candidate  → lookup: free run ▸ shared grading run
    └─ verdict:   FC pick eval + SF-best eval, both via the same lookup
  practical scores (brown badges): still the MCTS expectation — untouched
  ```
- Headless Stockfish WASM verification is available for measuring depth/latency without a browser: run the vendored `stockfish-18-lite-single.js` in Node (copy to a non-ESM dir as `.cjs`; auto-starts UCI on stdin/stdout). Illegal `searchmoves` entries are silently dropped; MultiPV index is an eval rank — map by `pv[0]`.
- Acceptance smoke: on a live position, a move present on all three surfaces (the exd5/Bc5 class) shows one number everywhere; the Qc7-class verdict impossibility can no longer occur.

</specifics>

<deferred>
## Deferred Ideas

- Search-internal grade fidelity (shallow pool grades mis-ranking the practical pick) — separate question, explicitly out of scope per the seed.
- Configurable FC/SF line counts (`MAX_LINES`) — falls out for free later; not this phase.
- SEED-085 root-findability (which move the engine selects) — orthogonal.
</deferred>

---

*Phase: 158-flawchess-engine-displayed-eval-provenance-reconciliation-se*
*Context gathered: 2026-07-07 via Seed Express Path (SEED-087)*
