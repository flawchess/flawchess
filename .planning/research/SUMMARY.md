# Project Research Summary

**Project:** FlawChess Engine (v2.0 milestone)
**Domain:** Client-side MCTS practical-play chess search (expectimax-inside-MCTS, Maia-weighted backup), integrating Stockfish + Maia into a mobile-first React/Vite analysis board
**Researched:** 2026-07-05
**Confidence:** HIGH (stack/architecture grounded in direct codebase reads and a locked design spec; features/pitfalls MEDIUM on browser-memory extrapolation and Maia-drift, HIGH on protocol facts already proven in Phase 151/151.1)

## Executive Summary

FlawChess Engine is a client-side chess search that ranks moves by *expected practical score* rather than pure objective evaluation — Stockfish supplies leaf quality, Maia supplies opponent-reply and self-execution probability, combined in an MCTS search with a deliberately non-textbook backup rule (Maia-prior-weighted expectation at non-root nodes, plain max at root, with the ELO used at each node depending asymmetrically on whose move it is). All four researchers converge on the same core verdict: **this ships as glue code over already-shipped infrastructure, not a new dependency.** No new npm packages are needed — the ~150-line MCTS core, the worker pool, and the priority queue are all hand-rolled extensions of patterns this codebase already has proven in `useStockfishGradingEngine.ts` and `useMaiaEngine.ts`. Reading the two closest prior-art systems (Polecat, vala-bot) directly — not just their marketing pages — confirmed the core concept (Maia-model + engine-eval expectimax that plays swindles) is not novel, but also confirmed the one thing FlawChess's design does that neither prior system does: model the *player's own* future execution probability at the *player's own* rating, not just the opponent's. That asymmetric self+opponent rating is the one legitimately unclaimed hook and the copy must never claim more than that.

The recommended approach is a strict separation between a pure, framework-agnostic, worker-free search core (`frontend/src/lib/engine/`, testable with fabricated `EngineProviders` and zero WASM/ONNX in the loop) and two thin adapter layers that touch real workers (`workerPool.ts` generalizing the Phase 151.1 Stockfish grading protocol to 2-4 parallel instances; `maiaQueue.ts` as a dedicated, separate Maia worker). This separation is what makes the two highest-risk pieces of logic — the custom backup rule and the ELO-at-node routing — unit-testable with hand-computed fixtures before a single worker exists, and what makes the SEED-mandated depth-limited-expectimax fallback a real, exercised escape hatch rather than an aspirational claim. Build order is five dependency-ordered phases: (A) pure search core + tests, (B) real worker-pool/Maia providers, (C) React hook + anytime UI in free analysis, (D) board arrows + toggles, (E) game-review overlay integration.

The two risks that matter most are orthogonal to each other and must both be addressed inside the relevant phase, not deferred: mobile Safari's memory ceiling (2-4 Stockfish WASM heaps + 1 Maia ONNX session + the existing eval bar can silently crash/reload the tab on iOS with no catchable exception — cap pool size adaptively and never run the new pool concurrently with the existing free-standing eval bar on the same position) and backup-rule/ELO-routing correctness (the custom Maia-weighted backup is one careless refactor away from silently degenerating into textbook visit-count-weighted MCTS, and ELO-at-node is one off-by-one from being fully inverted — both need golden-value negative-assertion unit tests, not integration tests, as the primary defense). Scope is deliberately narrow: MVP1 ships the modal-path line, the score pair, live-refining top-n lines, and a single new board-arrow layer on both surfaces — trap-finder UI, per-ELO sigmoids, time-pressure modeling, and SharedArrayBuffer multithreading are all explicitly deferred by design, and the arrow layer count was reduced from SEED-082's original 4 to 3 (no dedicated Maia arrow; Maia stays reachable via the existing Moves-by-Rating chart hover).

## Key Findings

### Recommended Stack

Zero new frontend dependencies. Every "which library" question resolves to "hand-roll it" because either no maintained library exists (no current MCTS npm package, none would fit the non-standard asymmetric backup rule even if maintained) or the workload is too small to justify one (a few hundred node evaluations per search doesn't need a priority-queue library — a plain array with linear max-scan suffices; `tinyqueue` is named only as a future option past ~1-2k pending nodes). The entire "new" surface is glue code over `stockfish@18.0.8` (lite-single WASM, already vendored) and `onnxruntime-web@1.27.0` (Maia-3, already vendored, already forced to `numThreads=1`).

**Core technologies:**
- `stockfish` 18.0.8 (lite-single WASM) — leaf-eval workhorse, pooled 2-4 instances, no version bump
- `onnxruntime-web` 1.27.0 — Maia-3 policy/WDL, single dedicated worker, already pinned single-threaded
- Hand-rolled MCTS core (`lib/engine/`) — ~150 lines, pure functions, `vitest`-testable with fabricated providers

**Explicitly rejected:** generic MCTS packages, priority-queue libraries at MVP1 scale, worker-RPC wrappers (Comlink/workerpool), SharedArrayBuffer multithreading (breaks the existing Google OAuth popup flow via COOP/COEP).

### Expected Features

**Must have (MVP1):** MCTS + custom Maia-weighted backup over the Phase 151 primitive; Stockfish.wasm worker pool (2-4); lichess eval→win% leaf sigmoid; modal-path line + objective-vs-practical score pair; live-refining top-n lines; FlawChess Engine top-2 board arrow, toggleable; works on both free analysis and game review, with the played-vs-practical-best comparison loop in game review (highest leverage-per-LOC item in the milestone).

**Should have ("Ambitious" tier, post-validation):** dedicated trap-finder/branch-point UI; per-ELO leaf sigmoids from the benchmark DB; SAB-multithreaded root grading.

**Defer (v2+):** time-pressure conditioning (clock→temperature/ELO-offset — flagged as possibly the most defensible genuinely-novel axis found); Maia-2 dual-skill-attention adoption.

### Architecture Approach

A nested `lib/engine/` subsystem holds the pure, worker-free search core behind a narrow `SearchRunner` guardrail interface (`position + budget + EngineProviders → ranked root lines`, incremental emission). The core never imports `Worker` directly — only an `EngineProviders` interface (`policy()`, `grade()`) — enabling fully deterministic tests against fabricated tables with zero real WASM/ONNX. `workerPool.ts` and `maiaQueue.ts` are the only files touching `postMessage`, each generalizing an already-shipped protocol rather than inventing one. `useFlawChessEngine.ts` is the sole React-aware file.

**Major components:** (1) `lib/engine/backup.ts` — the one genuinely novel piece, pure and fixture-tested; (2) `lib/engine/mctsSearch.ts`/`select.ts` + `fallbackExpectimax.ts` — orchestrator and the 1-day recovery path behind the identical interface; (3) `workerPool.ts` (2-4 Stockfish workers, priority queue) + `maiaQueue.ts` (dedicated Maia worker); (4) `useFlawChessEngine.ts` + `FlawChessEngineLines.tsx` + `Analysis.tsx` wiring.

Suggested build order: **A** pure search core with fake providers → **B** real providers (worker pool + Maia queue) → **C** React hook + anytime UI (free analysis only) → **D** board arrows + toggles → **E** game-review overlay integration.

### Critical Pitfalls

1. **Mobile Safari memory ceiling** — 2-4 Stockfish WASM heaps + 1 Maia ONNX session + the existing eval bar can silently crash/reload the tab on iOS. Cap pool size adaptively, never run concurrently with the existing eval bar, real-device profiling before ship.
2. **Backup rule silently degenerates into textbook MCTS** — negative golden-value unit tests asserting the result ≠ naive/visit-count-weighted average, plus explicit root-vs-non-root branch tests.
3. **Asymmetric ELO crossed at the node level** — derive "whose ELO" from actual side-to-move color, never depth parity; node-level oracle test covering both root colors.
4. **Non-determinism from worker-arrival order, not RNG** — canonical sort-by-move-key tie-breaks, stubbed-engine bit-identical repeated-run CI test.
5. **`multipv` reused as move identity** — the exact bug Phase 151.1 already fixed; reuse the shared `pv[0]`-keyed parsing utility and grep-audit every new call site.

## Implications for Roadmap

### Phase 1: Pure Search Core (guardrail + backup + MCTS + fallback, no workers)
**Rationale:** riskiest logic proven correct before WASM/ONNX exists. **Delivers:** `lib/engine/{types,guardrail,backup,select,mctsSearch,fallbackExpectimax}.ts`, fully unit-tested against fake providers. **Addresses:** MVP1 algorithmic core. **Avoids:** Pitfalls 3, 4, 5, 10.

### Phase 2: Real Providers (worker pool + Maia queue)
**Rationale:** mechanical generalization of already-shipped Phase 151.1 protocol, lowest-risk new-worker-code phase. **Delivers:** `workerPool.ts`, `maiaQueue.ts`, swapped in for fakes. **Uses:** `stockfish` 18.0.8, `onnxruntime-web` 1.27.0. **Implements:** Architecture Patterns 3 & 4. **Avoids:** Pitfall 1 (mobile memory — adaptive sizing lands here), Pitfall 6.

### Phase 3: React Hook + Anytime UI (free analysis only)
**Rationale:** first user-visible surface, arrows deferred. **Delivers:** `useFlawChessEngine.ts` + `FlawChessEngineLines.tsx`. **Addresses:** modal-path/score-pair, live-refining P1 items. **Avoids:** Pitfall 2 (main-thread jank), Pitfall 9 (anytime flicker).

### Phase 4: Board Arrows + Toggles (free analysis)
**Rationale:** depends on Phase 3's hook. **Delivers:** new `theme.ts` constants, `flawChessEngineArrows` useMemo, toggles. **Addresses:** headline visual (3-layer arrow system). **Avoids:** Pitfall 8 (disagreement looking broken).

### Phase 5: Game-Review Overlay Integration
**Rationale:** depends on Phase 4. **Delivers:** full locked v2.0 scope, both surfaces. **Addresses:** highest-leverage differentiator (played-vs-practical-best loop).

### Phase Ordering Rationale
Pure logic → workers → UI → free analysis → game review, each phase depending strictly on the prior phase's stable output. The one novel logic piece (backup rule) gets maximal upfront isolation so the fallback stays a real one-day swap. Mobile memory/pool sizing lands in Phase 2, not a later "polish" phase.

### Research Flags
Needs research: Phase 1 (backup-rule/ELO-oracle test-fixture design), Phase 2 (real-device memory profiling methodology).
Standard patterns (skip research-phase): Phases 3, 4, 5 (compose already-shipped, well-understood codebase patterns).

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | npm registry verified directly; codebase conventions cross-checked |
| Features | MEDIUM-HIGH | Polecat/vala-bot source read directly via WebFetch, some files partially retrievable |
| Architecture | HIGH | Grounded in direct reads of every relevant hook/component/page |
| Pitfalls | MEDIUM | HIGH on protocol facts (own postmortems); MEDIUM on browser-memory (third-party, not device-measured); LOW-MEDIUM on Maia-drift extrapolation |

**Overall confidence:** HIGH — hardest technical questions well-answered; residual uncertainty is empirical and correctly deferred to spike/UAT gates.

### Gaps to Address
- Real-device mobile memory ceiling unmeasured — needs an explicit iPhone + mid-tier-Android profiling pass in Phase 2 before committing to a default pool size.
- Opponent-ELO input in free analysis unresolved (symmetric default vs. a second ELO control) — flag as a Phase 3/4 scoping decision via `/gsd-discuss-phase` or `/gsd-ui-phase`.
- Arrow hue selection — one open high-saturation slot confirmed, final pick is a `/gsd-ui-phase` decision.
- Node-budget sizing across devices should be a tunable constant, revisited post-UAT.
- maiachess.com "played move arrow" precedent is LOW confidence — verify against the live UI before repeating the claim.

## Sources

### Primary (HIGH confidence)
npm registry (2026-07-05); FlawChess codebase (`useStockfishGradingEngine.ts`, `useMaiaEngine.ts`, `useStockfishEngine.ts`, `useAnalysisBoard.ts`, `Analysis.tsx`, `useGameOverlay.ts`, `moveQuality.ts`, `theme.ts`, `maia-worker.js`); `.planning/seeds/SEED-082-human-playable-line-engine.md`; `.planning/PROJECT.md` v2.0 section; Polecat and vala-bot repo source read directly.

### Secondary (MEDIUM confidence)
Maia KDD 2020, ALLIE (ICLR 2025), Maia-2 (NeurIPS 2024); Mobile Safari memory-ceiling third-party measurements; onnxruntime-web GitHub issues (#26858, #22086, #22776, #26827).

### Tertiary (LOW confidence)
maiachess.com marketing page (unconfirmed UI claim); player-specific Maia-2+MCTS (arXiv 2605.11893, background only).

---
*Research completed: 2026-07-05*
*Ready for roadmap: yes*
