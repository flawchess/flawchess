---
phase: 138-analysis-route-page-shell-entry-points
plan: 01
type: execute
wave: 0
depends_on: []
files_modified:
  - frontend/src/pages/__tests__/Analysis.test.tsx
autonomous: true
requirements: [ROUTE-01, ROUTE-02]

must_haves:
  truths:
    - "A jsdom test harness exists that mounts the lazy Analysis page with useStockfishEngine mocked (jsdom has no real Worker)"
    - "The harness encodes the phase's observable behaviors as assertions: page renders, ?fen= seeds the board, malformed ?fen= degrades to start, engine-loading chrome shows while !isReady, board stays interactive"
  artifacts:
    - path: "frontend/src/pages/__tests__/Analysis.test.tsx"
      provides: "Wave-0 failing test scaffold for the Analysis page (RED until Plan 02 ships Analysis.tsx)"
      contains: "vi.mock('@/hooks/useStockfishEngine'"
  key_links:
    - from: "frontend/src/pages/__tests__/Analysis.test.tsx"
      to: "frontend/src/pages/Analysis.tsx"
      via: "default import of the page under test (Pitfall 1 — default export required)"
      pattern: "import AnalysisPage from '../Analysis'"
---

<objective>
Create the Wave-0 failing test scaffold for the `/analysis` page (`frontend/src/pages/__tests__/Analysis.test.tsx`) BEFORE the page exists, so Plan 02's implementation is verified test-first. The scaffold mocks `useStockfishEngine` (jsdom cannot construct the classic-worker engine file — VALIDATION.md jsdom note) and asserts the contract testids and behaviors the page must satisfy.

Purpose: Nyquist sampling — Plan 02 (page) and the ROUTE-01/ROUTE-02/D-06 behaviors must have an automated red→green signal that lands ahead of the implementation.
Output: One new test file, RED (fails because `../Analysis` does not yet resolve). Plan 02 turns it green.
</objective>

<execution_context>
@$HOME/.claude/gsd-core/workflows/execute-plan.md
@$HOME/.claude/gsd-core/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/138-analysis-route-page-shell-entry-points/138-RESEARCH.md
@.planning/phases/138-analysis-route-page-shell-entry-points/138-PATTERNS.md
@.planning/phases/138-analysis-route-page-shell-entry-points/138-VALIDATION.md
</context>

<artifacts_produced>
NEW symbols/files created by this plan (use to exclude newly-created symbols from drift verification):
- `frontend/src/pages/__tests__/Analysis.test.tsx` — new Vitest jsdom test file. References (does not create) the not-yet-existing default export `Analysis` from `frontend/src/pages/Analysis.tsx` (created in Plan 02) and the testids `analysis-page`, `analysis-board`, `analysis-eval-bar`, `analysis-engine-loading`.
</artifacts_produced>

<tasks>

<task type="auto">
  <name>Task 1: Create the failing Analysis page test harness (mocked engine)</name>
  <files>frontend/src/pages/__tests__/Analysis.test.tsx</files>
  <read_first>
    - `frontend/src/pages/__tests__/Endgames.readinessGate.test.tsx` (lines 1-206) — the canonical full-page render harness this file copies: `// @vitest-environment jsdom` pragma + imports (1-14); mutable mock-state object reset per test (17-33); `vi.mock` shape (31-67); jsdom shims `matchMedia`/`ResizeObserverStub`/`window.scrollTo` (130-155); `afterEach` cleanup + state reset (157-165); late page import after mocks (167); render helper with `MemoryRouter initialEntries` (170-178); `getByTestId` assertion style (183-206).
    - `.planning/phases/138-analysis-route-page-shell-entry-points/138-RESEARCH.md` §"Exact Composition Contract" (the verified `StockfishEngineState` shape: `evalCp`, `evalMate`, `pvLines`, `depth`, `isAnalyzing`, `isReady`) and §"Validation Architecture" → "jsdom note" (must mock `useStockfishEngine`).
    - `.planning/phases/138-analysis-route-page-shell-entry-points/138-PATTERNS.md` §"frontend/src/pages/__tests__/Analysis.test.tsx (test)" (the full harness mapping, lines 212-268) and §"jsdom shims".
    - `.planning/phases/138-analysis-route-page-shell-entry-points/138-UI-SPEC.md` §"Interaction & Accessibility Contract" (the authoritative testid list: `analysis-page`, `analysis-board`, `analysis-eval-bar`, `analysis-engine-loading`).
  </read_first>
  <action>
    Create `Analysis.test.tsx` following the `Endgames.readinessGate.test.tsx` harness verbatim for structure. Begin with the `// @vitest-environment jsdom` pragma. Declare a mutable `engineState` object holding a full `StockfishEngineState` with safe defaults (`evalCp: null`, `evalMate: null`, `pvLines: []`, `depth: 0`, `isAnalyzing: false`, `isReady: false`) and `vi.mock('@/hooks/useStockfishEngine')` returning `useStockfishEngine: () => ({ ...engineState })` so each test can drive `isReady`/`pvLines` deterministically. Do NOT mock `useAnalysisBoard` — it is pure in-memory and must run for real so `?fen=` seeding is genuinely exercised. Copy the `matchMedia`, `ResizeObserverStub`, and `window.scrollTo` jsdom shims verbatim (react-chessboard needs them). Reset `engineState` to defaults and `cleanup()` in `afterEach`.

    Default-import the page as `import AnalysisPage from '../Analysis'` (Pitfall 1: the page is a default export; named import would break). Place this import after the `vi.mock` calls (mirrors the analog's late import). Provide a `renderAnalysis(initialPath = '/analysis')` helper that wraps `<AnalysisPage />` in `<MemoryRouter initialEntries={[initialPath]}>` and `<TooltipProvider>` (add `QueryClientProvider` only if a child throws for missing query context — the page itself does no data fetch).

    Write these test cases (they are RED now because `../Analysis` does not yet exist — that is the expected Wave-0 state; Plan 02 makes them green):
    1. Shell renders: `renderAnalysis()` then assert `getByTestId('analysis-page')`, `getByTestId('analysis-board')`, and `getByTestId('analysis-eval-bar')` are present.
    2. Valid `?fen=` seeds the root: render with `/analysis?fen=` plus an `encodeURIComponent` of a non-start FEN (e.g. a known mid-opening FEN), then assert the rendered board reflects that position rather than the standard start (assert via a square/piece signal exposed by the board, or via a testid the page derives from `board.position`; keep the assertion resilient — presence of the seeded position, not exact DOM internals).
    3. Malformed `?fen=` degrades to start without throwing: render with `/analysis?fen=not-a-valid-fen`; assert the render does NOT throw and `analysis-page` is present (the security FEN-guard in Plan 02 falls back to the standard start position).
    4. Engine-loading chrome (D-06 / SC#3): with `engineState.isReady = false`, render and assert `getByTestId('analysis-engine-loading')` shows the "Loading engine…" copy, AND `analysis-board` is still present (board stays interactive while the engine loads — it must never be gated on `isReady`).
    5. Engine ready hides the loading chrome: set `engineState.isReady = true`, render, assert `queryByTestId('analysis-engine-loading')` is null.

    Use `text-sm`-floor-agnostic assertions (assert on testids/roles/copy, not class names) except where a test specifically guards a class. Do not assert on engine internals (debounce, UCI) — those are Phase 136's tests.
  </action>
  <acceptance_criteria>
    - `frontend/src/pages/__tests__/Analysis.test.tsx` exists and contains `vi.mock('@/hooks/useStockfishEngine'` and `import AnalysisPage from '../Analysis'` (default import).
    - The file defines at least the 5 cases above, including a malformed-FEN case asserting no throw and an `isReady:false` case asserting `analysis-engine-loading` is shown while `analysis-board` is present.
    - `useAnalysisBoard` is NOT mocked (grep: no `vi.mock('@/hooks/useAnalysisBoard'` in the file).
    - jsdom shims (`matchMedia`, `ResizeObserver`, `scrollTo`) are present.
    - Running the file is RED for the right reason only: failure is `Cannot find module '../Analysis'` / unresolved default export, NOT a harness syntax error.
  </acceptance_criteria>
  <verify>
    <automated>cd frontend && npm test -- --run src/pages/__tests__/Analysis.test.tsx; echo "EXPECTED RED in Wave 0 — failure must be unresolved '../Analysis', not a harness error"</automated>
  </verify>
  <done>The scaffold compiles as a test module, collects under Vitest, and fails only because `frontend/src/pages/Analysis.tsx` does not exist yet. Plan 02 Task 1 turns all cases green.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| (none — test-only) | This plan adds test code only; it introduces no runtime trust boundary, no input parsing in shipped code, and no network/DOM-injection surface. |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-138-T1 | Tampering | Test scaffold encodes the FEN-guard expectation | accept | The malformed-`?fen=` case here is the *specification* of the Plan-02 mitigation for T-138-01; no runtime risk in this plan. |
| T-138-SC | Tampering | npm/pip/cargo installs | accept (N/A) | No package installs this phase — verified RESEARCH.md §"Package Legitimacy Audit" (zero new packages). No legitimacy checkpoint required. |
</threat_model>

<verification>
- `npm test -- --run src/pages/__tests__/Analysis.test.tsx` collects the file (RED expected in Wave 0).
- `npx tsc -b` does not regress on the new test file (test may reference the not-yet-existing default export; if `tsc` errors on the missing module, that is acceptable Wave-0 state and resolves when Plan 02 lands — note it in the SUMMARY).
</verification>

<success_criteria>
- The failing test scaffold exists and is the authoritative red→green gate for ROUTE-01, ROUTE-02, and D-06 (engine-loading-while-interactive).
</success_criteria>

<output>
Create `.planning/phases/138-analysis-route-page-shell-entry-points/138-01-SUMMARY.md` when done.
</output>
