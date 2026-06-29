---
phase: "138"
plan: "01"
subsystem: frontend-test
status: complete
tags: [test, wave-0, analysis, vitest, jsdom]
dependency_graph:
  requires: []
  provides: [138-01-test-scaffold]
  affects: [138-02-analysis-page-and-route]
tech_stack:
  added: []
  patterns: [vitest-jsdom-page-harness, vi.mock-hook-state, MemoryRouter-initialEntries]
key_files:
  created:
    - frontend/src/pages/__tests__/Analysis.test.tsx
  modified: []
decisions:
  - useAnalysisBoard not mocked so ?fen= seeding is genuinely exercised
  - engineState mutable object pattern (copied from Endgames.readinessGate.test.tsx)
metrics:
  duration: "1min"
  completed: "2026-06-26"
  tasks_completed: 1
  files_changed: 1
---

# Phase 138 Plan 01: Page Test Scaffold Summary

**One-liner:** Wave-0 failing Vitest jsdom harness for the Analysis page, mocking useStockfishEngine and asserting ROUTE-01/ROUTE-02/D-06 behaviors (RED until Plan 02 ships Analysis.tsx).

## Tasks Completed

| # | Task | Commit | Files |
|---|------|--------|-------|
| 1 | Create the failing Analysis page test harness (mocked engine) | aee65e2d | frontend/src/pages/__tests__/Analysis.test.tsx |

## What Was Built

Created `frontend/src/pages/__tests__/Analysis.test.tsx` — the Wave-0 RED test scaffold for the `/analysis` page. The file:

- Follows the `Endgames.readinessGate.test.tsx` harness pattern verbatim: `// @vitest-environment jsdom` pragma, mutable mock-state object reset per test, `vi.mock` shape, jsdom shims (`matchMedia`, `ResizeObserverStub`, `window.scrollTo`), `afterEach` cleanup + state reset, late page import after mocks, `MemoryRouter initialEntries` render helper.
- Mocks `useStockfishEngine` returning a fixed `StockfishEngineState` so `isReady`/`pvLines` are deterministic per test. Does NOT mock `useAnalysisBoard` (pure in-memory, must run for real so `?fen=` seeding is genuinely exercised).
- Default-imports the page as `import AnalysisPage from '../Analysis'` (default export required by `React.lazy` — Pitfall 1 from RESEARCH).
- Defines 5 test cases covering: shell renders (ROUTE-01), valid `?fen=` seeds the board (ROUTE-02), malformed `?fen=` degrades without throwing (security), engine-loading chrome while `isReady=false` + board stays present (D-06/SC#3), engine ready hides the loading chrome (D-06).

## Verification

Running `cd frontend && npm test -- --run src/pages/__tests__/Analysis.test.tsx` yields:

```
FAIL  src/pages/__tests__/Analysis.test.tsx
Error: Failed to resolve import "../Analysis" from "src/pages/__tests__/Analysis.test.tsx". Does the file exist?
```

This is the expected Wave-0 RED state. The failure is `Cannot find module '../Analysis'` — not a harness syntax error. Plan 02 creates `Analysis.tsx` and turns all 5 cases green.

Note on `npx tsc -b`: the TypeScript build also errors on the missing `../Analysis` import in Wave-0. This is acceptable and resolves when Plan 02 lands the default-exported page.

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None. This plan creates test code only; no stubs exist.

## Threat Flags

None — test-only plan with no runtime trust boundary.

## Self-Check: PASSED

- [x] `frontend/src/pages/__tests__/Analysis.test.tsx` exists
- [x] Commit `aee65e2d` present in git log
- [x] Test is RED for the correct reason (unresolved module, not harness syntax error)
- [x] 5 test cases present
- [x] `vi.mock('@/hooks/useStockfishEngine'` present
- [x] `import AnalysisPage from '../Analysis'` present
- [x] No `vi.mock('@/hooks/useAnalysisBoard'` in the file
- [x] jsdom shims present (matchMedia, ResizeObserver, scrollTo)
