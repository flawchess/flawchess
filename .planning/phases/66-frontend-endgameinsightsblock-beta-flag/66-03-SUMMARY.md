---
phase: 66-frontend-endgameinsightsblock-beta-flag
plan: 03
subsystem: frontend
tags: [frontend, component, insights, beta-gate, testing-library]

# Dependency graph
requires:
  - phase: 66-frontend-endgameinsightsblock-beta-flag
    provides: "Plan 01 — UserProfile.beta_enabled BE surface; Plan 02 — useEndgameInsights hook + envelope types + @testing-library/react + jsdom devDeps"
provides:
  - "frontend/src/components/insights/EndgameInsightsBlock.tsx — self-gating top-card component (beta gate + hero/skeleton/rendered/error state machine + outdated indicator + stale banner)"
  - "9 data-testids used by Cypress/automation harness: insights-block, insights-overview, btn-generate-insights, btn-regenerate-insights, btn-insights-retry, insights-outdated-indicator, insights-stale-banner, insights-error, insights-skeleton"
affects: [66-04 (Endgames.tsx integration mounts this component and owns the mutation + rendered state)]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Self-gating UX component: beta gate via useUserProfile() returns null for !profile?.beta_enabled. Parent mount site stays unconditional (no caller-side flag check)."
    - "Parent-owned mutation state pattern (lifted mutation): parent owns `mutation: UseMutationResult`, `rendered`, `reportFilters`, `onGenerate`; component reads isPending/isError/error and renders the 5-state machine. Enables per-section slot rendering in the same Endgames.tsx render tree."
    - "State machine in JSX via nested ternaries: isError → ErrorState; isPending && !hasRendered → SkeletonBlock; hasRendered → RenderedState; else → HeroState. Readable because each branch is a named component."
    - "Minute rounding utility `roundMinutes(s) = Math.max(1, Math.ceil(s/60))` — locked in UI-SPEC D-14 and tested for 0/45/60/61 second edge cases."
    - "Native DOM assertions (`element.textContent`, `queryByTestId`) instead of @testing-library/jest-dom matchers — jest-dom not installed project-wide (knip-unused per Plan 02 decision)."
    - "Explicit `afterEach(cleanup)` for RTL tests — Vitest 4 does not auto-unmount; without cleanup, rendered DOM from prior tests bleeds into subsequent `screen.getByTestId` queries."

key-files:
  created:
    - frontend/src/components/insights/EndgameInsightsBlock.tsx
    - frontend/src/components/insights/__tests__/EndgameInsightsBlock.test.tsx
  modified: []

key-decisions:
  - "String literal wrapper `{\"Couldn't generate insights.\"}` instead of JSX text with `&apos;` — acceptance criterion greps the source file for the verbatim phrase. JSX entity references would pass visually but fail the grep."
  - "Native DOM assertions over jest-dom matchers — Plan 02 intentionally dropped jest-dom (knip-unused). Using `element.textContent.toContain(...)` + `queryByTestId(...).toBeNull()` keeps the same test clarity without reintroducing the dependency."
  - "Explicit `afterEach(cleanup)` — Vitest 4 does not auto-cleanup RTL mounts. First test run showed DOM bleed between tests (4/11 failures). Added cleanup hook rather than globally enabling `globals: true` which would change config for all tests."
  - "Return type annotations omitted on components — matches codebase convention (MoveList, ChessBoard, GlobalStatsCharts all omit return types). Also sidesteps the React 19 / `@types/react` JSX.Element ambiguity under `verbatimModuleSyntax`."

patterns-established:
  - "Self-gating beta-feature components that return null when the feature flag is false — keeps Plan 04's mount site simple (`<EndgameInsightsBlock ... />` unconditional, no ternary at call site)."
  - "Parent-lifted mutation state for components that also need to drive sibling slot rendering — the same `mutation` + `rendered` state is observed by both the top-card component and Plan 04's inline `insights-section-*` slots."

requirements-completed: [INS-01, INS-02, INS-03, BETA-02]

# Metrics
duration: ~5min
completed: 2026-04-22
---

# Phase 66 Plan 03: EndgameInsightsBlock self-gating top-card component

**React component rendering the 5-state Insights UI (hero, skeleton, rendered with optional stale banner, rendered-pending with inline spinner, error) plus outdated indicator and 9 data-testids — self-gated via `useUserProfile().beta_enabled` and backed by 11 render tests covering beta gate, all states, BETA-02 overview-hide, 429 retry-min rounding, and filter-outdated detection.**

## Performance

- **Duration:** ~5 min
- **Started:** 2026-04-22T05:34:01Z
- **Completed:** 2026-04-22T05:38:25Z
- **Tasks:** 2
- **Files created:** 2
- **Files modified:** 0

## Accomplishments

- Shipped `frontend/src/components/insights/EndgameInsightsBlock.tsx` (239 lines) — self-gating top card with beta gate, hero/skeleton/rendered/error state machine, outdated indicator, stale banner, and inline pending spinner
- All 9 top-card `data-testid` attributes from UI-SPEC §Data-TestID Inventory present: `insights-block`, `insights-overview`, `btn-generate-insights`, `btn-regenerate-insights`, `btn-insights-retry`, `insights-outdated-indicator`, `insights-stale-banner`, `insights-error`, `insights-skeleton`
- All 9 locked copy strings rendered verbatim per UI-SPEC §Copywriting Contract (H2 "Insights", hero blurb, CTAs, outdated message, stale banner, error headline/body/retry-line, retry CTA)
- BETA-02 overview-hide honored: `rendered.report.overview === ''` hides the `<p data-testid="insights-overview">` while keeping the Regenerate row visible
- 429 retry-min rounding via `roundMinutes(s) = Math.max(1, Math.ceil(s/60))` — UI-SPEC D-14 formula used verbatim; rate-limited error response `retry_after_seconds=180` → "Try again in ~3 min."
- Primary buttons use `variant="default"` (Generate, Regenerate); retry CTA uses `variant="brand-outline"` per CLAUDE.md §Frontend UI rule
- 11 render tests covering beta gate (loading + false), all 5 states, BETA-02 overview-hide, stale banner fallback copy, outdated indicator, error-with-retry-min, and minute-rounding edge cases (0/45/60/61 sec → 1/1/1/2 min)
- Zero Sentry calls in the component (global `MutationCache.onError` in `queryClient.ts` handles reporting per CLAUDE.md §Frontend Rules)
- Full verification clean: `npx tsc --noEmit` 0 errors, `npm run lint` 0 errors, `npm run knip` clean, `npm test` 97/97 tests across 8 files, `npm run build` production build succeeds

## Task Commits

1. **Task 1: Create EndgameInsightsBlock.tsx with beta gate, hero, skeleton, overview, error states** — `eba78af` (feat)
2. **Task 2: Component render tests covering all 5 states** — `b4b11e5` (test)

## Files Created/Modified

- `frontend/src/components/insights/EndgameInsightsBlock.tsx` — NEW. Top-of-tab Insights component. Exports `EndgameInsightsBlock` and `EndgameInsightsBlockProps`. Props: `appliedFilters`, `rendered`, `reportFilters`, `mutation`, `onGenerate`. Beta gate reads `useUserProfile().data?.beta_enabled`; returns null during loading and when flag is false. Internal `roundMinutes` utility for UI-SPEC D-14 rounding. Private state components `HeroState`, `SkeletonBlock`, `RenderedState`, `ErrorState` encapsulate each branch of the state machine.
- `frontend/src/components/insights/__tests__/EndgameInsightsBlock.test.tsx` — NEW. 11 render tests with module-level `vi.mock('@/hooks/useUserProfile')`, `// @vitest-environment jsdom` pragma, and explicit `afterEach(cleanup)` to unmount RTL roots between tests.

## Decisions Made

- **String-literal wrapper for the one phrase with an apostrophe** (`{"Couldn't generate insights."}` in JSX): Acceptance criterion greps the source for the verbatim string `Couldn't generate insights.`. Using `&apos;` would render the apostrophe visually but the grep would fail. Wrapping the string in `{"..."}` passes both the grep and eslint's `react/no-unescaped-entities` rule without touching the user-visible output.
- **Native DOM assertions, not jest-dom:** Plan 02 explicitly dropped `@testing-library/jest-dom` to keep knip clean. Using `expect(el.textContent).toContain(...)` and `expect(screen.queryByTestId(...)).toBeNull()` is equally clear and avoids reintroducing the devDep.
- **Explicit `afterEach(cleanup)`:** Vitest 4 does NOT auto-cleanup RTL between tests (discovered after 4/11 initial failures showed stale DOM). Adding a file-local `afterEach(cleanup)` is the minimal fix; alternative would be setting `test.globals: true` in vitest config which affects all tests.
- **Parent-lifted mutation state (locked in plan):** Component receives `UseMutationResult` + `rendered` + `reportFilters` + `onGenerate` as props instead of calling `useEndgameInsights()` itself. Benefits: Plan 04 can observe the same state from its per-section `insights-section-*` slots without a context provider.
- **Stale-banner minutes always null (honest UI):** Phase 65's 200-envelope does not surface `retry_after_seconds` for `stale_rate_limited` responses. Rendered copy uses the "in a moment" fallback. If a future Phase 65 schema change adds the field, `staleMinutes` can be populated then.
- **Return types omitted on components:** Matches existing codebase convention. Also avoids React 19 `JSX.Element` compatibility churn.

## Deviations from Plan

None — plan executed exactly as written. One test-infrastructure fix needed during Task 2 (missing `afterEach(cleanup)` not mentioned in plan action template), but this is project-convention polish rather than a scope deviation: the plan's "action" template assumes vitest auto-cleanup and the quick fix kept all 11 specified tests green.

## Issues Encountered

- **Initial test run showed DOM bleed between tests.** Four tests (skeleton, overview-hidden, retry-min, minute-rounding) failed because RTL's `render()` mounts stack up in the same document without cleanup under Vitest 4. Fixed by adding `afterEach(cleanup)` to the test file. All 11 tests pass thereafter.

## User Setup Required

None — no external services, environment variables, or database migrations introduced.

## Next Phase Readiness

- Plan 66-04 (Endgames.tsx integration) can import the component directly: `import { EndgameInsightsBlock } from '@/components/insights/EndgameInsightsBlock'`.
- Plan 04 owns the mutation + rendered state. Recommended shape at the call site:
  ```tsx
  const insightsMutation = useEndgameInsights();
  const [rendered, setRendered] = useState<EndgameInsightsResponse | null>(null);
  const [reportFilters, setReportFilters] = useState<FilterState | null>(null);
  const handleGenerate = async () => {
    const resp = await insightsMutation.mutateAsync(appliedFilters);
    setRendered(resp);
    setReportFilters(appliedFilters);
  };

  <EndgameInsightsBlock
    appliedFilters={appliedFilters}
    rendered={rendered}
    reportFilters={reportFilters}
    mutation={insightsMutation}
    onGenerate={handleGenerate}
  />
  ```
- Plan 04's inline per-section slots (`insights-section-overall`, `insights-section-metrics_elo`, `insights-section-time_pressure`, `insights-section-type_breakdown`) observe the same `rendered` + `insightsMutation.isPending` values — no additional state plumbing required.
- Knip is still clean: the component + props export are consumed by the test file in Plan 03; Plan 04 will add the production consumer. No action needed.

## Self-Check: PASSED

**Files created (verified via `ls`):**
- FOUND: frontend/src/components/insights/EndgameInsightsBlock.tsx
- FOUND: frontend/src/components/insights/__tests__/EndgameInsightsBlock.test.tsx

**Commits exist (verified via `git log`):**
- FOUND: eba78af (Task 1 — feat: component with state machine + testids + locked copy)
- FOUND: b4b11e5 (Task 2 — test: 11 render tests for beta gate + all states + rounding)

**Verification commands passed:**
- `cd frontend && npx tsc --noEmit` — 0 errors
- `cd frontend && npm run lint` — 0 errors (3 pre-existing coverage warnings, not component-related)
- `cd frontend && npm run knip` — clean
- `cd frontend && npm test` — 97 tests across 8 files, all pass (11 new tests in EndgameInsightsBlock.test.tsx)
- `cd frontend && npm run build` — production build succeeds

---
*Phase: 66-frontend-endgameinsightsblock-beta-flag*
*Completed: 2026-04-22*
