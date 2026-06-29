# Phase 136: `useStockfishEngine` Hook + WASM Setup - Context

**Gathered:** 2026-06-26
**Status:** Ready for planning

<domain>
## Phase Boundary

Build `useStockfishEngine` — a React hook wrapping a single-thread WASM Stockfish in a Web Worker — plus the platform hardening required to ship it safely. The hook exposes a UCI state machine (`uci`/`uciok`/`setoption`/`isready`/`readyok`/analyze loop), debounced re-analysis on position change, MultiPV state, a stop-pending guard for stale `bestmove`, and the `go movetime 1500` search cap. It returns engine output (`evalCp`/`evalMate`, `pvLines`, `depth`, `isAnalyzing`, `isReady`) as plain data.

**This phase ships NO user-visible page or display components.** EvalBar / EngineLines / VariationTree are Phase 137; the `/analysis` route and page shell are Phase 138. Phase 136 is the engine hook + WASM build wiring + PLAT hardening only.

In scope: `stockfish` npm install, engine binaries vendored to `public/engine/`, `vite.config.ts` wiring (`optimizeDeps.exclude`, PWA `*.wasm` handling), the hook itself, UCI parser + headless-worker tests, no-COOP/COEP CI guard, tab-hide pause.

Out of scope: any rendered UI surface, `/analysis` route, branching move tree (`useAnalysisBoard`), tactic mode, entry points. Any modification to `useChessGame.ts`.
</domain>

<decisions>
## Implementation Decisions

### Verification surface (no UI in 136)
- **D-01:** Phase 136 ships **tests only, no user-visible UI.** Deliverables: `useStockfishEngine.ts`, Vitest UCI-parser unit tests, and **one** headless Worker integration test that drives a single fixed FEN through the real engine and asserts a sane `evalCp`/`pvLines`/`bestmove` come back. No route, no dev harness, no temporary toggle on existing boards.
- **D-02:** Human-in-the-loop / on-device (iOS Safari, low-end Android) eyeball verification is **deferred to Phase 138** when the `/analysis` page first renders engine output. Do not build a throwaway harness to pull that verification earlier.
- **RESEARCH FLAG (must resolve in planning):** A *true* headless Worker integration test that boots the real WASM is non-trivial under Vitest — `Worker` is not native in node. The planner/researcher must pick the mechanism: `@vitest/web-worker`, a `node:worker_threads` + stockfish-node harness, or the stockfish package's node entry point. If a real-worker harness proves flaky/infeasible in CI, the acceptable fallback is: UCI parser unit tests (full coverage of lowerbound/upperbound, `mate 0`, interleaved MultiPV) + a worker test gated to run locally, OR a `npm run build && npx serve dist` smoke step. The intent (D-01) is one real end-to-end FEN→eval assertion; the exact harness is the planner's call.

### Engine file delivery
- **D-03:** Commit the two engine files (`stockfish-18-lite-single.js` + `stockfish-18-lite-single.wasm`, ~7 MB total) directly into `public/engine/` and check them into git. No `vite-plugin-static-copy`, no extra dev dependency. Rationale: dead-simple, fully reproducible offline builds, served verbatim, no build-time copy magic. Accepted cost: a ~7 MB binary blob in git history.
- Files are served verbatim from `public/engine/`; Worker instantiated via `new Worker('/engine/stockfish-18-lite-single.js')`. `optimizeDeps: { exclude: ['stockfish'] }` still required in `vite.config.ts` even though we vendor manually (guards against any future import of the npm package through the bundler).

### Tab-hide pause (PLAT-02)
- **D-04:** On `visibilitychange → hidden`, send `stop` to the engine but keep the Worker alive (no terminate). On `visibilitychange → visible`, **automatically re-`go`** on the current position so the user returns to a live, updating eval. Worker is reused — no re-init cost. (Chosen over "stay idle until next user interaction".)

### Locked upstream — DO NOT re-litigate (from v1.29 research + ROADMAP success criteria + D-1..D-5)
- Build: `stockfish` v18, `stockfish-18-lite-single.{js,wasm}` (~7 MB, single-thread NNUE). NOT the full single-thread build (HCE-only, weaker, exceeds iOS Cache limit).
- Search cap: `go movetime 1500` is the **primary** bound (ROADMAP SC#2 locked 1500ms — overrides STACK.md's exploratory 3000ms figure). `go nodes 2000000` permitted only as a secondary safety valve.
- MultiPV = 2 (top 1–2 lines). Debounce = 150ms. Stop-pending flag mandatory (the `bestmove` that always follows `stop` must be discarded — Pitfall 3 two-layer guard: debounce + `stopPendingRef`).
- **No `SharedArrayBuffer` / COOP / COEP headers anywhere** (Pitfall 8, D-3). CI `curl -I` guard must assert their absence on every page; `window.crossOriginIsolated === false`. This protects Google OAuth popup + iOS Safari.
- PWA service worker must NOT precache `*.wasm` (Workbox `globPatterns`/`globIgnores` audit — Pitfall 2, iOS ~50 MB Cache API limit). Serve wasm with long-lived immutable `Cache-Control`.
- No backend work: no schema, no migration, no new endpoints (D-4).

### Claude's Discretion
- UCI state-machine internal representation (`idle | thinking | stopping` enum naming), MultiPV map keying, exact debounce/stop wiring, and the secondary `go nodes` valve are the planner's/executor's call within the locked bounds above.
- Tab-hide pause implementation detail (whether resume reuses the last `go` params verbatim or recomputes) is discretionary, as long as D-04's auto-resume behavior holds.
</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### v1.29 milestone research (read all four — Phase 136 is the highest-novel-risk phase)
- `.planning/research/SUMMARY.md` — executive summary; "Phase 1: `useStockfishEngine` Hook + WASM Setup" section and "Open Questions" list
- `.planning/research/STACK.md` — build choice, Vite wiring (`optimizeDeps.exclude`, `public/engine/`), `vite-plugin-static-copy` vs commit tradeoff, search-cap discussion, version-compat notes
- `.planning/research/PITFALLS.md` — all 10 pitfalls; Phase 136 owns 1 (esbuild WASM URL break), 2 (iOS 50 MB Cache), 3 (stale-eval race), 4–8 (incl. COOP/COEP)
- `.planning/research/ARCHITECTURE.md` — `useStockfishEngine` hook contract, FEN-per-node context, component boundaries

### Requirements & roadmap
- `.planning/REQUIREMENTS.md` — ENGINE-01..05, PLAT-01/02 (this phase's requirements); D-1..D-5 locked decisions; anti-features table
- `.planning/ROADMAP.md` § "Phase 136" — 5 success criteria (the acceptance bar)

### Prior-art in the codebase (read before writing the hook)
- `frontend/vite.config.ts` — existing VitePWA / Workbox config to amend (currently `globPatterns` is default; `runtimeCaching` allowlists `/api/`); the `*.wasm` audit happens here
- `frontend/src/hooks/useChessGame.ts` — the hook NOT to modify; reference only for conventions
- `frontend/src/hooks/useDebounce.ts` — existing debounce utility (reuse vs inline is planner's call)
- `frontend/src/hooks/useTacticLine.ts` — Phase 135 hook; context for the eventual subsume (Phase 139), not touched here
</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `frontend/src/hooks/useDebounce.ts` — existing debounce; candidate for the 150ms re-analysis debounce (planner decides reuse vs hook-local).
- VitePWA + Workbox already configured in `vite.config.ts` with an allowlist `runtimeCaching` for `/api/` and `navigateFallback: null` — the `*.wasm` exclusion plugs into this existing structure rather than introducing PWA config from scratch.
- `frontend/public/` already serves verbatim static assets (icons, og-image, openings.tsv) — `public/engine/` follows the established pattern.

### Established Patterns
- Hooks live in `frontend/src/hooks/`, tests in `frontend/src/hooks/__tests__/`. `useStockfishEngine.ts` + its tests follow this layout.
- No existing Web Worker usage in the app (the "Worker" grep hits are service-worker / unrelated). This is the first real `new Worker(...)` — no prior worker-lifecycle pattern to match; establish a clean one.
- `noUncheckedIndexedAccess`, knip dead-export detection, and `text-sm` floor all apply (CLAUDE.md Frontend rules). UCI parsing reads array tokens — narrow every indexed access.

### Integration Points
- `vite.config.ts`: add `optimizeDeps: { exclude: ['stockfish'] }`; audit/confirm Workbox does not glob `*.wasm`.
- CI: a new `curl -I` step asserting no `Cross-Origin-Opener-Policy` / `Cross-Origin-Embedder-Policy` headers and `application/wasm` MIME on the engine asset. Wire into the existing GitHub Actions frontend job.
- `package.json`: `stockfish` v18 added as a dependency (even though binaries are committed, the package pins the version we vendored from and documents provenance). Confirm GPLv3 acknowledgement in README (Worker boundary keeps GPL non-infective).
</code_context>

<specifics>
## Specific Ideas

- The one headless integration test should assert on a **known FEN with an unambiguous best move** (e.g. a simple mate-in-1 or a clearly winning capture) so the assertion is deterministic across machines despite eval-value non-determinism (see memory: Stockfish eval_cp is not reproducible across hardware — assert on `bestmove` / sign of eval, not an exact centipawn value).
- Engine version provenance: vendor the exact files from `stockfish` v18.0.8; record the version + source pointer in README per GPLv3.
</specifics>

<deferred>
## Deferred Ideas

- **On-device (iOS Safari / low-end Android) manual verification** — intentionally deferred to Phase 138 when the `/analysis` page first renders engine output (D-02). Not lost; it's the verification gate for 138.
- **Real-device `movetime` calibration** — the 1500ms cap is locked for v1; empirical re-tuning against budget Android hardware is a Phase 138/UAT smoke check (SUMMARY open question #1), not a 136 decision.
- **`go nodes` desktop mode / adjustable strength** — secondary valve only in 136; any user-facing strength/depth control is out of v1.29 scope.
- Multi-thread WASM engine (ENGINE-V2-01, D-3) — explicitly deferred to v2; reopens COOP/COEP + OAuth + iOS analysis.

### Reviewed Todos (not folded)
None — no pending todos matched this phase.
</deferred>

---

*Phase: 136-usestockfishengine-hook-wasm-setup*
*Context gathered: 2026-06-26*
