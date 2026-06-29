---
phase: "138"
plan: "02"
subsystem: frontend
status: complete
tags: [react, routing, lazy-load, analysis-page, stockfish, green-wave]
dependency_graph:
  requires: [138-01-test-scaffold]
  provides: [138-02-analysis-page-and-route]
  affects: [138-03-openings-analyze-entry]
tech_stack:
  added: []
  patterns:
    - react-lazy-suspense-first-boundary
    - fen-guard-try-catch-fallback
    - useAnalysisBoard-destructure-pattern (avoids react-hooks/refs v7 false-positive)
    - route-wrapper-useSearchParams-key-remount
key_files:
  created:
    - frontend/src/pages/Analysis.tsx
  modified:
    - frontend/src/App.tsx
decisions:
  - Destructure useAnalysisBoard return value (not board.x in JSX) to satisfy react-hooks/refs v7 ESLint rule (TacticLineExplorer precedent)
  - AnalysisRoute wrapper component reads useSearchParams so ?fen= param is available for the key prop without polluting AppRoutes scope
  - Single EvalBar render (no desktop/mobile duplication) avoids duplicate data-testid="analysis-eval-bar" which would fail getByTestId
  - canGoForward=true (always-enabled) per RESEARCH Pitfall 4 guidance (hook no-ops with no child)
metrics:
  duration: "5min"
  completed: "2026-06-26"
  tasks_completed: 2
  files_changed: 2
---

# Phase 138 Plan 02: Analysis Page and Route Summary

**One-liner:** Default-exported Analysis page composing useAnalysisBoard + useStockfishEngine with FEN-guard, engine-loading chrome, and the app's first React.lazy + Suspense route boundary, turning Plan 01's Wave-0 scaffold GREEN.

## Tasks Completed

| # | Task | Commit | Files |
|---|------|--------|-------|
| 1 | Build Analysis page shell (default export, FEN-guard, engine-loading) | 98edbbce | frontend/src/pages/Analysis.tsx |
| 2 | Wire /analysis into router as first lazy + Suspense boundary | 2336c265 | frontend/src/App.tsx |

## What Was Built

### Task 1 — Analysis.tsx

Created `frontend/src/pages/Analysis.tsx` as a **default-exported** page component (required by `React.lazy`; all other pages in the codebase use named exports — this is the intentional divergence per RESEARCH Pitfall 1).

Key implementation details:

- **Security FEN-guard (T-138-01):** `try { new Chess(fenParam) } catch { guardedFen = undefined }` before `useAnalysisBoard`. Malformed `?fen=` degrades to the standard start position without throwing at render.
- **Hook wiring:** `useAnalysisBoard(guardedFen)` return is **destructured** (not accessed as `board.x` in JSX) to avoid the `react-hooks/refs` v7 false-positive that fires on hook-return property access inside JSX (same pattern as `TacticLineExplorer.tsx:289-291`).
- **Engine on by default (D-06):** `const [engineEnabled, setEngineEnabled] = useState(true)`. `useStockfishEngine({ fen: engineEnabled ? position : null, enabled: engineEnabled })` called unconditionally.
- **Engine-loading state (SC#3):** `engineLoading = engineEnabled && !engine.isReady`. When true, renders `<div data-testid="analysis-engine-loading">Loading engine…</div>` in the eval area. When false + enabled: renders `EngineLines`. When disabled: renders "Engine off".
- **Board stays interactive** during WASM init — board is never gated on `engine.isReady`.
- **containerRef div** wraps `ChessBoard` with `data-testid="analysis-board"`, `tabIndex={0}`, and `ref={containerRef}` for container-scoped ←/→ keyboard navigation (Pitfall 5).
- **Engine toggle** in `BoardControls.infoSlot` with `data-testid="btn-analysis-engine-toggle"`, `aria-label="Toggle engine"`, `aria-pressed={engineEnabled}`.
- **rootPly** derived from the guarded FEN: `(fullmove-1)*2 + (side==='b'?1:0)` for correct move-number labels in `EngineLines` (startPly) and `VariationTree` (rootPly).
- **Reset wiring:** `onReset={() => loadMainLine([], rootFen)}` — no `board.reset()` exists; empty SAN array clears tree to root (Pitfall 4).

### Task 2 — App.tsx

Three localized edits only (existing eager imports left unchanged):

1. **Lazy import:** `lazy, Suspense` merged into React import; `useSearchParams` added to react-router-dom import. `const AnalysisPage = lazy(() => import('./pages/Analysis'))` placed after all static imports — the app's **first** `React.lazy` boundary (D-07 / ROUTE-01).
2. **ROUTE_TITLES:** Added `'/analysis': 'Analysis'` for mobile header. NOT added to `NAV_ITEMS` or `BOTTOM_NAV_ITEMS` (D-05 — no nav item).
3. **Route registration:** New `AnalysisRoute` wrapper component reads `useSearchParams` (not in scope at `AppRoutes`), keys `AnalysisPage` by `params.get('fen') ?? 'start'` (Pitfall 2 — re-entry remount), and wraps in `<Suspense>` with `data-testid="analysis-loading"` fallback. Route is inside `ProtectedLayout`, NOT wrapped in `ImportRequiredRoute` (free-play valid for zero-game users, RESEARCH A2) or `SuperuserRoute`.

## Verification

```
Analysis page shell
  ✓ renders shell with required testids (ROUTE-01)
  ✓ seeds the board from a valid ?fen= param (ROUTE-02)
  ✓ degrades to start position on malformed ?fen= without throwing (security)
  ✓ shows engine-loading chrome while isReady=false, board stays present (D-06 / SC#3)
  ✓ hides the engine-loading chrome when isReady=true (D-06)

Test Files  1 passed (1)
Tests       5 passed (5)
```

`npx tsc -b`, `npm run lint`, `npm run knip` all clean.

**Manual UAT gate** (cannot be automated via jsdom — for `/gsd-verify-work`):
- SC#1: DevTools Network tab — no `stockfish-18-lite-single.js` / `.wasm` on `/library`, `/openings`, `/endgames`; engine fetch fires exactly once on `/analysis`.
- SC#3: On-device eyeball — "Loading engine…" in eval area while board + stepper + VariationTree + BoardControls are immediately interactive; engine eval appears within ~3s.
- SC#2: `/analysis?fen=<url-encoded FEN>` loads position; malformed `?fen=` silently shows start.
- SC#4 / PLAT-01: `window.crossOriginIsolated === false` on `/analysis`; full Google OAuth sign-in completes.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug / Rule 2 - Lint] Destructure useAnalysisBoard return value**
- **Found during:** Task 1 — `npm run lint` after initial implementation
- **Issue:** `react-hooks/refs` ESLint v7 false-positive: the rule fires on any property of a hook return object that contains a `Ref` type when accessed inline in JSX (e.g. `board.containerRef`, `board.position`, `board.makeMove` — all 12 properties flagged).
- **Fix:** Destructured the `useAnalysisBoard()` return at the component top (same pattern documented in `TacticLineExplorer.tsx:289-291`). Each property becomes a plain variable, no ref-access false-positive.
- **Files modified:** `frontend/src/pages/Analysis.tsx`
- **Commit:** 2336c265 (landed in same commit as Task 2 since Analysis.tsx was still staged)

## Known Stubs

None. Both the Analysis page and router wiring are fully implemented. EvalBar/EngineLines/VariationTree are wired to real data sources. The engine operates on the real (mocked-in-test) `useStockfishEngine` hook.

## Threat Flags

None. All trust boundaries from the plan's threat model are mitigated:
- T-138-01: FEN-guard implemented and asserted by automated test.
- T-138-02: Engine/SAN strings rendered as React children (auto-escaped) — inherited from Phase 137 components.
- T-138-03: No COOP/COEP headers added; no multi-thread engine build; PLAT-01 CI guard stays green.

## Self-Check: PASSED

- [x] `frontend/src/pages/Analysis.tsx` exists and contains `export default`
- [x] `frontend/src/App.tsx` contains `lazy(() => import('./pages/Analysis'))` and `Suspense`
- [x] Commit `98edbbce` present (Task 1)
- [x] Commit `2336c265` present (Task 2)
- [x] 5/5 Analysis.test.tsx cases pass (GREEN — Wave-0 scaffold complete)
- [x] `npx tsc -b` clean
- [x] `npm run lint` clean (0 errors)
- [x] `npm run knip` clean (no dead exports)
- [x] No `board.reset` reference (uses `loadMainLine([], rootFen)`)
- [x] `containerRef` on board wrapper div, not on ChessBoard container
- [x] `/analysis` not in NAV_ITEMS or BOTTOM_NAV_ITEMS
- [x] `/analysis` inside ProtectedLayout, NOT in ImportRequiredRoute or SuperuserRoute
- [x] `key={params.get('fen') ?? 'start'}` on AnalysisPage (Pitfall 2 remount)
