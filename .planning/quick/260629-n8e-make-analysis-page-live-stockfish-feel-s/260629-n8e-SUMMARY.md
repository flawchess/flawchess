---
phase: quick-260629-n8e
plan: "01"
subsystem: frontend/analysis
tags: [stockfish, ux, performance, debounce, uci]
status: complete

dependency_graph:
  requires: []
  provides: [live-first-paint-eval, adaptive-debounce]
  affects: [frontend/src/hooks/useStockfishEngine.ts]

tech_stack:
  added: []
  patterns: [adaptive-debounce, live-streaming-pv, extract-shared-helper]

key_files:
  modified:
    - frontend/src/hooks/useStockfishEngine.ts
    - frontend/src/hooks/__tests__/useStockfishEngine.test.ts

decisions:
  - "Adaptive debounce: fire immediately when sinceLast > RAPID_STEP_DEBOUNCE_MS (settled), debounce when rapid (coalesce arrow-key steps)"
  - "Relaxed bound gate: accept lowerbound/upperbound info lines for live painting; eval bounces briefly then settles (lichess-style, user-accepted)"
  - "Fake timer init { now: 0 } in tests so Date.now() is deterministic for debounce path testing"

metrics:
  duration: "~15 minutes"
  completed: "2026-06-29T15:14:43Z"
  tasks_completed: 2
  tasks_total: 2
  files_changed: 2
---

# Phase quick-260629-n8e Plan 01: Live Stockfish Feel Summary

One-liner: Adaptive immediate-fire debounce + relaxed UCI bound gate for sub-100ms first-paint and live eval sharpening in the analysis page engine.

## What Was Built

### Task 1: Adaptive debounce + relaxed-bound live streaming (useStockfishEngine.ts)

**A. Adaptive debounce** (replaces flat `DEBOUNCE_MS = 150`):

Renamed to `RAPID_STEP_DEBOUNCE_MS = 150`. Added `lastFenChangeAtRef = useRef(0)`. The FEN-change effect now computes `sinceLast = Date.now() - lastFenChangeAtRef.current`:
- `sinceLast > RAPID_STEP_DEBOUNCE_MS` (settled move, or first mount in real time where `Date.now() >> 0`): calls `setDebouncedFen(fen)` immediately, no timer.
- Rapid succession: schedules the existing debounce timer so arrow-key auto-repeat coalesces.

**B. Relaxed bound + live snapshot commit**:

Extracted the white-POV normalization + setPvLines/setEvalCp/setEvalMate/setDepth logic into a `commitPvSnapshot()` function inside the worker effect (closure over refs/setters). The info handler now:
1. Guards: `if (stateRef.current !== 'thinking' || stopPendingRef.current) return;`
2. Accepts all bounds (removes `bound === 'exact'` gate)
3. Updates pvMapRef and calls `commitPvSnapshot()` for live first-paint

The bestmove non-stale branch calls `commitPvSnapshot()` then sets `stateRef='idle'` and `setIsAnalyzing(false)`. The stop-pending discard branch is unchanged.

### Task 2: Updated unit tests (useStockfishEngine.test.ts)

- **`beforeEach`**: switched to `vi.useFakeTimers({ now: 0 })` so `Date.now()` is deterministic (starts at 0, advances with fake clock).
- **New "settled first move" test**: advances fake time to 200ms before rendering, then asserts go is sent during `driveInit` (no timer advance needed after).
- **New "rapid coalescing" test**: renders at fake time 0 (debounce path), advances to 140ms (just before first timer fires), rerenders to new FEN (cleanup cancels first timer, second timer set at 290ms), advances 300ms, asserts only one go for the final FEN.
- **Inverted lowerbound/upperbound tests**: now assert `evalCp` IS set after the info line (live painting).
- **Strengthened exact info line test**: split into two assertions — `evalCp` set BEFORE bestmove, and still correct with `isAnalyzing=false` after bestmove.
- **Stop-pending test**: updated comments to reflect that info lines now commit immediately; timer behavior note added for the immediate-fire path.

## Verification

Full frontend gate passed:
- `npm run lint`: clean
- `npm test -- --run`: 1231 tests, 104 test files, all passed
- `npx tsc -b`: zero errors

## Deviations from Plan

None. Plan executed exactly as written.

The one non-obvious implementation detail: Vitest's `vi.useFakeTimers()` initializes `Date.now()` at the current real Unix timestamp (not 0). This caused the adaptive debounce to always take the immediate path in tests (real time >> 0), making the coalescing test fail. Fix: `vi.useFakeTimers({ now: 0 })` resets the fake clock to epoch 0 for deterministic behavior.

## Known Stubs

None.

## Threat Flags

None. Frontend-only change to an analysis hook; no new network endpoints or auth paths.

## Self-Check

Verified:
- `frontend/src/hooks/useStockfishEngine.ts` exists and contains `RAPID_STEP_DEBOUNCE_MS`, `commitPvSnapshot`, and the stale guard
- `frontend/src/hooks/__tests__/useStockfishEngine.test.ts` exists with 14 tests
- Commit `94aadd5f` exists

## Self-Check: PASSED
