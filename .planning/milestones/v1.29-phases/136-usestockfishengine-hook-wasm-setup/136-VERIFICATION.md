---
phase: 136-usestockfishengine-hook-wasm-setup
verified: 2026-06-26T12:40:00Z
status: human_needed
score: 13/14
behavior_unverified: 1
overrides_applied: 0
behavior_unverified_items:
  - truth: "On tab hidden the hook sends stop and keeps the Worker alive; on visible it auto re-go on the current FEN (D-04)"
    test: "Trigger visibilitychange to hidden (while engine is analyzing), then trigger visibilitychange to visible. Verify that the engine resumes analysis of the current position."
    expected: "After the tab becomes visible, analyze() is called for currentFenRef.current and the engine sends position fen + go within a reasonable delay. pvLines and evalCp are eventually updated from the new analysis."
    why_human: "The mock-Worker test only exercises the hidden-stop path (stop sent, worker not terminated). The visible-to-re-go state transition is not covered. Additionally, when the tab becomes visible while stateRef is 'stopping' (not 'thinking'), analyze() bypasses the stop-pending check and sends go immediately — then when the stale bestmove arrives it tries to re-analyze again, creating a potential double-analyze ordering issue that no test exercises."
human_verification:
  - test: "Tab visible auto re-go after hidden pause"
    expected: "With the engine active (isReady=true, isAnalyzing=true on a real board position), hide the browser tab. Verify the engine stops (isAnalyzing goes false). Make the tab visible again. Verify the engine re-starts analysis of the current position (isAnalyzing goes true and pvLines/evalCp are eventually updated)."
    why_human: "The visible-to-re-go state transition is coded (analyzeRef.current(current) in the visibility handler) but no unit or integration test exercises this path. The potential race between the direct visible-handler analyze call and the stale-bestmove-discard's re-analyze (both firing analyze when stopping→visible) needs a real browser to observe."
---

# Phase 136: useStockfishEngine Hook + WASM Setup Verification Report

**Phase Goal:** Users can rely on a live in-browser engine that evaluates positions correctly and efficiently without breaking the existing site (no COOP/COEP headers, iOS-safe PWA, tab-hide pause). Note: rendering/UI is deferred to phases 137/138 — this phase delivers the hook data contract + platform hardening only.
**Verified:** 2026-06-26T12:40:00Z
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Source | Truth | Status | Evidence |
|---|--------|-------|--------|----------|
| 1 | P01-T1 | No COOP/COEP headers on any page (window.crossOriginIsolated stays false), protecting Google OAuth + iOS Safari | VERIFIED | CI step at line 130 in ci.yml curl-checks for Cross-Origin-Opener-Policy/Cross-Origin-Embedder-Policy on the vite preview page; fails build if found; SUMMARY confirms local verify showed no headers |
| 2 | P01-T2 | Engine WASM asset served as Content-Type application/wasm | VERIFIED | CI step (same step) asserts `content-type.*application/wasm` on /engine/stockfish-18-lite-single.wasm; SUMMARY A3 verified locally with vite preview + curl -I |
| 3 | P01-T3 | PWA service worker manifest does NOT precache *.wasm (iOS Cache-API safe) | VERIFIED | `globIgnores: ['**/*.wasm']` present in the `workbox` block in `frontend/vite.config.ts` lines 96-97; SUMMARY confirms dist/sw.js has no precache entry for the wasm |
| 4 | P01-T4 | Vendored stockfish-18-lite-single.{js,wasm} (~7 MB) load verbatim from /engine/ and are committed to git | VERIFIED | Both files exist: `frontend/public/engine/stockfish-18-lite-single.js` (21429 bytes) and `frontend/public/engine/stockfish-18-lite-single.wasm` (7295411 bytes); `git ls-files --error-unmatch` confirms both are tracked |
| 5 | P01-T5 | CI fails if a future change adds COOP/COEP headers or breaks the WASM MIME type | VERIFIED | CI step "No COOP/COEP header guard + WASM MIME check" in `.github/workflows/ci.yml` lines 130-160; uses `FAIL=1` + `exit $FAIL` pattern; positioned after vitest and before knip |
| 6 | P02-T1 | Given a position FEN, engine reaches readyok (isReady false→true) and returns deterministic bestmove for mate-in-1 FEN | VERIFIED | Integration test `useStockfishEngine.integration.test.ts` boots real WASM (stockfish@18.0.8 initEngine), sends Scholar's-mate pre-mate FEN, asserts `bestmove h5f7`; passes in ~250ms |
| 7 | P02-T2 | Hook exposes evalCp/evalMate, pvLines (top 1-2 lines, MultiPV=2), bestmove (pvLines[0].moves[0]), and depth as plain data | VERIFIED | `StockfishEngineState` interface in `useStockfishEngine.ts` lines 50-63 exports all required fields; mock-Worker test "exact info line + bestmove commits evalCp to state" exercises end-to-end data flow |
| 8 | P02-T3 | Hook re-analyzes debounced 150ms on FEN change, bounded by go movetime 1500 nodes 2000000 (ENGINE-05) | VERIFIED | Mock-Worker tests: "does not send go before 150ms" (advanceTimersByTime 100) and "sends position + go after debounce delay" (advanceTimersByTime 200) both pass; "search command contains movetime 1500 and nodes 2000000" asserts the exact go string; constants MOVETIME_MS=1500, MAX_NODES=2000000, DEBOUNCE_MS=150 defined at top of hook |
| 9 | P02-T4 | Hook exposes isReady/isAnalyzing and an enabled control input; engine can be toggled off/on (ENGINE-04) | VERIFIED | `UseStockfishEngineOptions.enabled` exists; when false the worker effect returns early without creating a Worker; `StockfishEngineState.isReady/isAnalyzing` both in the return; mock-Worker test "sends isready...transitions isReady false→true on readyok" passes |
| 10 | P02-T5 | lowerbound/upperbound info lines never update the committed eval; only bound=exact does (Pitfall 5) | VERIFIED | `useStockfishEngine.ts` line 212: `if (parsed !== null && parsed.bound === 'exact')` gates pvMap updates; mock-Worker tests "lowerbound info line does NOT update evalCp" and "upperbound info line does NOT update evalCp" both pass; uciParser unit tests also confirm bound parsing |
| 11 | P02-T6 | score mate 0 and score mate -N (losing) parse correctly; interleaved MultiPV lines key independently (Pitfall 7) | VERIFIED | `uciParser.test.ts`: "score mate 0 (terminal — already checkmate) returns scoreMate=0", "score mate -3 (losing) returns scoreMate=-3", "interleaved multipv lines: both parsed independently with their own pv moves" — all 13 uciParser tests pass |
| 12 | P02-T7 | bestmove following a stop is discarded via two-layer guard (debounce + stopPendingRef); rapid FEN changes show only final position | VERIFIED | Mock-Worker test "stop-pending bestmove is discarded — rapid FEN changes show only final result" passes; simulates FEN change while thinking, sends stale bestmove, asserts pvLines remains empty; `stopPendingRef` and Layer B discard logic in hook lines 224-236 |
| 13 | P02-T8 | On tab hidden: hook sends stop and keeps Worker alive; on visible: auto re-go on current FEN (D-04) | PRESENT_BEHAVIOR_UNVERIFIED | Hidden-stop path: mock-Worker test "visibility hidden sends stop without terminating the Worker" passes — stop count increases, terminated stays false. Visible-re-go path: coded in `handleVisibility` (lines 296-302, `analyzeRef.current(current)`), but no test exercises the hidden→visible state transition. Ordering invariant unverified: when state is 'stopping' on visible, analyze() sends go immediately, then the stale bestmove discard's re-analyze also fires — potential double-analyze race is not tested. |
| 14 | P02-T9 | On unmount the Worker is stopped and terminated (no leak, Pitfall 4) | VERIFIED | Mock-Worker test "unmount sends stop and terminates the Worker (no leak)" passes; worker effect cleanup (lines 265-270) sends stop + terminate + nulls ref |

**Score:** 13/14 truths verified (1 present, behavior-unverified)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `frontend/public/engine/stockfish-18-lite-single.js` | Emscripten JS glue for single-thread Stockfish 18 lite (vendored) | VERIFIED | 21429 bytes, git-tracked |
| `frontend/public/engine/stockfish-18-lite-single.wasm` | WASM binary (~7 MB) single-thread NNUE Stockfish 18 lite | VERIFIED | 7295411 bytes (7.0 MB), git-tracked |
| `frontend/vite.config.ts` | `optimizeDeps.exclude=['stockfish']` + `workbox.globIgnores=['**/*.wasm']` | VERIFIED | Both present: `exclude: ['stockfish']` (line 45), `globIgnores: ['**/*.wasm']` (line 96); existing plugin order unchanged |
| `.github/workflows/ci.yml` | No-COOP/COEP header guard + application/wasm MIME check step | VERIFIED | Lines 130-160; positioned correctly after vitest (line 127), before knip (line 162) |
| `frontend/package.json` | `"stockfish": "18.0.8"` exact pin (no caret) | VERIFIED | Line 39: `"stockfish": "18.0.8"` — no caret |
| `README.md` | GPLv3 provenance note for vendored engine binaries | VERIFIED | Lines 55-60 contain package name, vendored files, GPL-3.0 license, source URL, Worker process boundary GPL-isolation note |
| `frontend/src/hooks/uciParser.ts` | Pure UCI parser: parseInfoLine + parseBestmove; exports PvLine, ParsedInfoLine, UCIScoreBound; min 40 lines | VERIFIED | 149 lines; all three types exported; parseInfoLine and parseBestmove exported; no React/Worker dependency |
| `frontend/src/hooks/useStockfishEngine.ts` | React hook: Worker lifecycle + UCI state machine + debounce + stop-pending guard + tab-hide pause; returns StockfishEngineState; min 80 lines | VERIFIED | 313 lines; all required functionality present; exports UseStockfishEngineOptions, StockfishEngineState, useStockfishEngine |
| `frontend/src/hooks/__tests__/uciParser.test.ts` | Unit tests: lowerbound/upperbound, mate 0, mate -N, interleaved MultiPV, bestmove parse | VERIFIED | 13 tests passing; all edge cases covered |
| `frontend/src/hooks/__tests__/useStockfishEngine.test.ts` | jsdom mock-Worker tests: stop-pending discard, debounce, isReady/isAnalyzing transitions, visibility pause | VERIFIED | 13 tests passing; all behavioral scenarios covered (except visible-re-go — see PRESENT_BEHAVIOR_UNVERIFIED) |
| `frontend/src/hooks/__tests__/useStockfishEngine.integration.test.ts` | node-env real-WASM test: initEngine('lite-single') FEN→bestmove mate-in-1 | VERIFIED | 1 test passing in ~250ms; asserts `bestmove h5f7` + score/pv flow |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `frontend/vite.config.ts` | `frontend/public/engine/stockfish-18-lite-single.wasm` | `workbox.globIgnores` excludes wasm from SW precache manifest | VERIFIED | `globIgnores: ['**/*.wasm']` at line 96 |
| `.github/workflows/ci.yml` | `frontend/dist` (vite preview) | curl -I asserts no COOP/COEP + application/wasm MIME | VERIFIED | Lines 138-156 curl the page and wasm asset; FAIL=1 on violation |
| `frontend/src/hooks/useStockfishEngine.ts` | `frontend/public/engine/stockfish-18-lite-single.js` | `new Worker('/engine/stockfish-18-lite-single.js')` classic Worker | VERIFIED | `ENGINE_PATH = '/engine/stockfish-18-lite-single.js'` (line 24), `new Worker(ENGINE_PATH)` (line 189); no `{ type: 'module' }` |
| `frontend/src/hooks/useStockfishEngine.ts` | `frontend/src/hooks/uciParser.ts` | `import { parseInfoLine }` to parse worker.onmessage lines | VERIFIED | Line 18: `import { parseInfoLine } from './uciParser'`; used in handleLine line 209 |
| `frontend/src/hooks/__tests__/useStockfishEngine.integration.test.ts` | stockfish (npm) | `dynamic import('stockfish')` → initEngine('lite-single') | VERIFIED | Line 35: `const { default: initEngine } = (await import('stockfish'))` |

### Data-Flow Trace (Level 4)

Not applicable. The primary deliverables are a React hook and a pure parser — neither renders UI or fetches data from an API. The hook produces real engine data from the WASM Worker (confirmed via integration test: real Stockfish output reaches the lines array and bestmoveLine).

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| uciParser unit tests (13 tests) | `cd frontend && npm test -- --run src/hooks/__tests__/uciParser.test.ts` | 13/13 passed in 207ms | PASS |
| useStockfishEngine mock-Worker tests (13 tests) | `cd frontend && npm test -- --run src/hooks/__tests__/useStockfishEngine.test.ts` | 13/13 passed in 874ms | PASS |
| Real-WASM integration test (1 test) | `cd frontend && npm test -- --run src/hooks/__tests__/useStockfishEngine.integration.test.ts` | 1/1 passed in 430ms (WASM boots in ~250ms in Node v24) | PASS |
| Engine binaries git-tracked | `git ls-files --error-unmatch frontend/public/engine/stockfish-18-lite-single.{js,wasm}` | Both files tracked | PASS |
| Stockfish exact pin in package.json | grep `"stockfish": "18.0.8"` | Found at line 39, no caret | PASS |
| stockfish NOT in knip ignoreDependencies | cat `frontend/knip.json` | stockfish absent from ignoreDependencies (removed after Plan 02's integration test added dynamic import) | PASS |
| No source module imports stockfish | `grep -rEl "from 'stockfish'" frontend/src` excluding `__tests__` | No results — only the integration test dynamically imports it | PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| ENGINE-01 | Plan 02 | User sees live eval bar + numeric centipawn/mate | SATISFIED (data contract) | `evalCp: number | null` and `evalMate: number | null` in StockfishEngineState; rendering deferred to Phase 137/138 per plan scope |
| ENGINE-02 | Plan 02 | User sees top 1-2 candidate lines as SAN sequences with depth | SATISFIED (data contract) | `pvLines: PvLine[]` with MultiPV=2 and `depth` in StockfishEngineState; each PvLine has moves[] array and evalCp/evalMate |
| ENGINE-03 | Plan 02 | User sees engine best move as arrow on board | SATISFIED (data contract) | `pvLines[0].moves[0]` is the UCI best-move string; arrow rendering deferred to Phase 137/138 |
| ENGINE-04 | Plan 02 | User can toggle engine on/off; board stays interactive while WASM initializes | SATISFIED (data contract) | `enabled` input + `isReady`/`isAnalyzing` state outputs; when enabled=false no Worker created; toggle UI deferred to Phase 138 |
| ENGINE-05 | Plan 02 | Engine re-analyzes automatically (debounced), bounded by movetime/node cap | SATISFIED | DEBOUNCE_MS=150, `go movetime ${MOVETIME_MS} nodes ${MAX_NODES}` = 1500ms/2000000 nodes; tested by mock-Worker suite |
| PLAT-01 | Plan 01 | No site-wide COOP/COEP headers; absence CI-guarded | SATISFIED | CI step in ci.yml lines 130-160 asserts no COOP/COEP; fails build if either header present |
| PLAT-02 | Plan 01 | Engine WASM loads efficiently on mobile; iOS Cache-API-limit safe; engine pauses when tab hidden | SATISFIED (partial: tab-pause behavior unverified) | Lite ~7 MB build vendored; `globIgnores: ['**/*.wasm']` keeps it out of SW precache; tab-hide-stop implemented; visible-re-go path not test-verified (see human verification) |

**Note on REQUIREMENTS.md:** PLAT-01 and PLAT-02 checkboxes remain `[ ]` (unchecked) in REQUIREMENTS.md; only ENGINE-01..05 have `[x]`. The traceability table also still shows them as "Pending". Both are actually implemented. This is a documentation inconsistency — the SUMMARY.md frontmatter correctly records `requirements-completed: [PLAT-01, PLAT-02]`.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| No files with TBD/FIXME/XXX markers | — | — | — | None |
| No placeholder/stub implementations found | — | — | — | None |

No unreferenced debt markers. No empty return bodies in the hook or parser. Named constants used throughout (`ENGINE_PATH`, `MOVETIME_MS`, `MAX_NODES`, `DEBOUNCE_MS`, `MULTIPV`) — no magic numbers.

### Human Verification Required

#### 1. Tab Visible Auto Re-Go After Hidden Pause

**Test:** With the engine active (navigate to a page using `useStockfishEngine`, wait for `isReady=true` and `isAnalyzing=true`), switch to another tab or minimize the browser (triggering `visibilityState='hidden'`). Wait 1-2 seconds. Switch back to the FlawChess tab (triggering `visibilityState='visible'`).

**Expected:** After hiding, the engine stops analyzing (isAnalyzing becomes false). After becoming visible, the engine re-starts analysis of the current position (isAnalyzing becomes true within 150ms, and pvLines/evalCp are updated with new engine output).

**Why human:** The `visible → re-go` state transition in `handleVisibility` (useStockfishEngine.ts lines 296-302) calls `analyzeRef.current(current)` directly. No unit or integration test exercises this path. There is also an ordering concern: if the tab becomes visible while `stateRef.current === 'stopping'` (stop was just sent for the hidden event), `analyze()` sends `position fen + go` immediately without checking the stopping state. When the stale bestmove subsequently arrives it also triggers `analyzeRef.current(current)` (line 233) — this double-invocation of `analyze` when state is `'thinking'` causes a second `stop → stopPendingRef=true → return` cycle. Whether this produces visible behavior issues (stale-eval jitter, missed re-analysis) requires real browser observation.

### Gaps Summary

No gaps. All must-have truths are either VERIFIED by tests or PRESENT with code clearly implementing the behavior. The single human-verification item is the visible-re-go state transition, which is coded but not exercised by any test.

**REQUIREMENTS.md documentation gap (non-blocking):** Update PLAT-01 and PLAT-02 checkboxes in REQUIREMENTS.md from `[ ]` to `[x]` and update their traceability table status from "Pending" to "Complete". This is cosmetic cleanup and does not block phase advancement.

---

## Acknowledged Gaps

During `/gsd-verify-work 136` (2026-06-26), the single human-verification item ("Tab visible
auto re-go after hidden pause") could not be tested manually: this phase ships
`useStockfishEngine` as data-only, with rendering deferred to Phases 137/138, so no board UI
exists to exercise the tab-hide/visible path against.

While reviewing the code, the verifier's suspected ordering concern was **confirmed as a real
double-go bug** (visible event fired during the `'stopping'` window → two `go` commands with no
intervening `stop`). The user **explicitly chose to defer the fix to Phases 137/138** (when the
UI is wired and the path becomes observable) and to accept the hook as-is for this phase.

- Item: visible→re-go double-go bug (`useStockfishEngine.ts` `analyze()` lacks a `'stopping'`
  guard). Severity: minor. Disposition: **accepted, deferred to 137/138.**
- Captured as `.planning/seeds/SEED-068-stockfish-visible-during-stopping-double-go.md`
  (dormant; `trigger_when` = wiring the hook into a real board UI in 137/138). The seed records
  the exact bug, the one-line fix, and a deterministic no-browser mock-Worker test.
- UAT item recorded as `skipped` (with reason) in `136-UAT.md`; phase advancement proceeds with
  this gap consciously acknowledged.

_Verified: 2026-06-26T12:40:00Z_
_Verifier: Claude (gsd-verifier)_
_Acknowledged gap recorded: 2026-06-26 (verify-work)_
