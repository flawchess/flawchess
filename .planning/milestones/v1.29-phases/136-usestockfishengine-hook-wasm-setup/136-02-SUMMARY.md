---
phase: 136-usestockfishengine-hook-wasm-setup
plan: "02"
subsystem: frontend/hooks
status: complete
tags: [engine, uci, stockfish, wasm, hook, tdd]
dependency_graph:
  requires: ["136-01"]
  provides: ["useStockfishEngine", "uciParser", "ENGINE-01", "ENGINE-02", "ENGINE-03", "ENGINE-04", "ENGINE-05"]
  affects: ["frontend/hooks", "frontend/tests"]
tech_stack:
  added: []
  patterns:
    - "UCI state machine (idle|thinking|stopping) with stopPendingRef two-layer guard"
    - "Inline debounce starting null (not useDebounce) for consistent 150ms delay on all analyses"
    - "ref-for-latest-value via render-phase useEffect sync (pattern from useTacticLine)"
    - "Worker mock via vi.fn(function(){return mock}) — regular function required for new compatibility"
    - "Real-WASM integration test via initEngine('lite-single') Promise form in @vitest-environment node"
key_files:
  created:
    - frontend/src/hooks/uciParser.ts
    - frontend/src/hooks/useStockfishEngine.ts
    - frontend/src/hooks/__tests__/uciParser.test.ts
    - frontend/src/hooks/__tests__/useStockfishEngine.test.ts
    - frontend/src/hooks/__tests__/useStockfishEngine.integration.test.ts
  modified:
    - frontend/knip.json
decisions:
  - "Inline debounce (useState null + setTimeout) instead of useDebounce — preserves 150ms on initial analysis; useDebounce initializes with current value immediately (no delay)"
  - "analyzeRef.current NOT updated during render (ESLint react-hooks/refs) — analyze is stable useCallback([]), so the ref only needs initialization"
  - "score mate accepted in evalLine assertion — mate-in-1 FEN never produces score cp lines"
  - "stockfish removed from knip ignoreDependencies — integration test's dynamic import() is detected by knip"
metrics:
  duration: "~15 minutes"
  completed: "2026-06-26"
  tasks_completed: 3
  tasks_total: 3
  files_created: 5
  files_modified: 1
---

# Phase 136 Plan 02: useStockfishEngine Hook + UCI Parser Summary

**One-liner:** UCI state machine hook with 150ms debounce, stopPendingRef two-layer stale-eval guard, tab-hide pause, and real-WASM integration test proving FEN→bestmove end-to-end.

## What Was Built

### Task 1: Pure UCI Parser + Unit Tests (TDD)

`frontend/src/hooks/uciParser.ts` — pure module (no React, no Worker) exporting:
- `parseInfoLine(line)` → `ParsedInfoLine | null`
- `parseBestmove(line)` → `string | null`
- Types: `PvLine`, `ParsedInfoLine`, `UCIScoreBound`

`frontend/src/hooks/__tests__/uciParser.test.ts` — 13 tests covering:
- lowerbound / upperbound → `bound !== 'exact'` (Pitfall 5)
- `score mate 0` (terminal), `score mate 1` (winning), `score mate -3` (losing)
- Interleaved MultiPV lines parsed independently
- `bestmove (none)` → null

### Task 2: useStockfishEngine Hook + Mock-Worker Unit Tests (TDD)

`frontend/src/hooks/useStockfishEngine.ts` — the primary deliverable:
- Constants: `ENGINE_PATH`, `MOVETIME_MS=1500`, `MAX_NODES=2000000`, `DEBOUNCE_MS=150`, `MULTIPV=2`
- Classic Worker (`new Worker(ENGINE_PATH)` — no `{type:'module'}`)
- UCI init sequence: uci → uciok → setoption MultiPV 2 → isready → readyok → `isReady=true`
- Inline debounce (starts null, fires after 150ms) for consistent delay
- Two-layer stale guard: Layer A = debounce; Layer B = `stopPendingRef`
- pvMap (keyed by multipv) committed to pvLines only on non-stale bestmove
- Exact-only eval commit (Pitfall 5)
- Tab-hide pause: stop on hidden, auto re-go on visible (D-04)
- Unmount cleanup: stop + terminate (Pitfall 4)

`frontend/src/hooks/__tests__/useStockfishEngine.test.ts` — 13 tests:
- Classic Worker assertion (no module option)
- UCI init sequence + isReady transition
- Debounce: no go at 100ms; go at 200ms
- Search command: `movetime 1500 nodes 2000000`
- lowerbound/upperbound NOT committed; exact IS committed
- Stop-pending discard: rapid FEN changes keep pvLines empty until final result
- Visibility hidden: stop sent, worker not terminated
- Unmount: stop + terminate

### Task 3: Real-WASM Integration Test

`frontend/src/hooks/__tests__/useStockfishEngine.integration.test.ts`:
- `// @vitest-environment node`; `import('stockfish')` dynamically
- `await initEngine('lite-single')` (Promise form — ready after uciok/readyok)
- `engine.listener = (line) => {...}` confirmed as the output API (A2 resolved)
- Mate-in-1 FEN → asserts `bestmove h5f7` + info line with `score mate` + `pv`
- Passes in ~250ms (WASM boots fast in Node.js v24)

## Confirmed API Details (Open Question 1 / Assumption A2)

The `engine.listener` property name was confirmed against the installed
`node_modules/stockfish/bin/stockfish-18-lite-single.js`:

```javascript
f.print=function(e){f.listener?f.listener(e):console.log(e)}
```

Where `f` is the Emscripten module object passed via `initEngine`. Setting
`engine.listener = (line: string) => {...}` is the correct output API.

**File location deviation:** RESEARCH.md said files are in `node_modules/stockfish/src/`
but v18.0.8 ships them in `node_modules/stockfish/bin/`. The `index.js` checks `bin/`
first, so no code changes were needed — `initEngine('lite-single')` resolves correctly.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Inline debounce instead of useDebounce for consistent 150ms delay**
- **Found during:** Task 2 GREEN phase (test "does not send go before 150ms" failed)
- **Issue:** `useDebounce(fen, 150)` initializes its state with the current value immediately (via `useState(value)`), so the initial analysis would bypass the 150ms delay when `isReady` was added to the effect deps
- **Fix:** Replaced with `useState<string | null>(null)` + `useEffect(() => { setTimeout(() => setDebouncedFen(fen), DEBOUNCE_MS) }, [fen])` — starts null, delays consistently
- **Files modified:** `frontend/src/hooks/useStockfishEngine.ts`
- **Impact:** `useDebounce` is no longer imported; inline debounce is slightly more code but correct

**2. [Rule 1 - Bug] Worker mock must use regular function (not arrow) for `new` compatibility**
- **Found during:** Task 2 GREEN phase (all 13 tests failed with "not a constructor")
- **Issue:** `vi.fn().mockImplementation(() => mockWorker)` uses an arrow function, which cannot be a constructor (arrow functions cannot be called with `new`)
- **Fix:** Changed to `vi.fn(function () { return mockWorker; })` — regular function that, when called with `new`, returns the pre-created mockWorker object (JS spec: constructor returning object overrides `this`)
- **Files modified:** `frontend/src/hooks/__tests__/useStockfishEngine.test.ts`

**3. [Rule 2 - Missing] Remove analyzeRef render-phase update (ESLint react-hooks/refs)**
- **Found during:** Task 2 lint check
- **Issue:** `analyzeRef.current = analyze` in the component body triggers ESLint `react-hooks/refs: Cannot update ref during render`
- **Fix:** Removed the render-phase update. Since `analyze` is `useCallback([])` (stable, never changes), `analyzeRef.current` is initialized once and never needs updating
- **Files modified:** `frontend/src/hooks/useStockfishEngine.ts`

**4. [Rule 1 - Bug] Integration test: `score cp` assertion fails for mate-in-1 FEN**
- **Found during:** Task 3 first test run
- **Issue:** For a mate-in-1 position, Stockfish reports `score mate 1`, not `score cp`. The assertion `l.includes('score cp')` always failed
- **Fix:** Changed assertion to accept either: `l.includes('score cp') || l.includes('score mate')`
- **Files modified:** `frontend/src/hooks/__tests__/useStockfishEngine.integration.test.ts`

**5. [Rule 2 - Missing] Remove stockfish from knip ignoreDependencies**
- **Found during:** Task 3 post-test knip run
- **Issue:** Knip reported "Configuration hints: Remove stockfish from ignoreDependencies" after the integration test was written — knip now detects `import('stockfish')` as a valid usage
- **Fix:** Removed `"stockfish"` from `ignoreDependencies` in `knip.json`
- **Files modified:** `frontend/knip.json`

## Verified Success Criteria

- ROADMAP SC#1: hook returns `evalCp`, `evalMate`, `pvLines` (top 2 lines), bestmove (`pvLines[0].moves[0]`), `depth` — data contract proven by mock-Worker + integration tests
- ROADMAP SC#2: debounced 150ms re-analysis capped at `go movetime 1500 nodes 2000000` — asserted in mock-Worker tests
- ROADMAP SC#3: `enabled` input + `isReady`/`isAnalyzing` states exposed — mock-Worker tests cover
- ENGINE-01..05: each mapped to a hook-data deliverable and covered by tests
- T-136-03 (Worker lifecycle): per-mount Worker, unmount terminates — tested
- T-136-04 (stop/bestmove/go race): two-layer guard tested (stale discard)

## Integration Test — CI Status

The integration test runs in ~250ms in Node.js v24. It is NOT gated with `it.skipIf(CI)` because it is reliable and fast. The 10s timeout provides ample buffer.

## Stubs

None — this plan ships no user-visible UI and no stub data. The hook returns real data from engine analysis.

## Self-Check: PASSED

All 5 created files exist on disk. All 6 task commits (2× TDD RED, 2× TDD GREEN, 1× integration, 1× chore) are verified in git log.
