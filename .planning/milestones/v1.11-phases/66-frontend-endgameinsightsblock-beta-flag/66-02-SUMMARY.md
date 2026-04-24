---
phase: 66-frontend-endgameinsightsblock-beta-flag
plan: 02
subsystem: frontend
tags: [frontend, types, hook, insights, tanstack-query, axios, testing-library]

# Dependency graph
requires:
  - phase: 65-llm-endpoint-with-pydantic-ai-agent
    provides: "POST /api/insights/endgame envelope shapes (EndgameInsightsResponse / InsightsErrorResponse) and Literal status/error unions (app/schemas/insights.py)"
  - phase: 66-frontend-endgameinsightsblock-beta-flag
    provides: "users.beta_enabled BE surface (Plan 01) wired into UserProfileResponse"
provides:
  - "frontend/src/types/insights.ts — Literal-typed API envelope (SectionId, InsightsStatus, InsightsError, SectionInsight, EndgameInsightsReport, EndgameInsightsResponse, InsightsErrorResponse, InsightsAxiosError)"
  - "UserProfile.beta_enabled: boolean as a required field on the FE type (mirrors NOT NULL DB column)"
  - "buildFilterParams exported from @/api/client (was module-private)"
  - "useEndgameInsights mutation hook (POST /insights/endgame, color appended, opponent_type intentionally omitted)"
  - "Unit test harness for React hooks: @testing-library/react@^16 + jsdom@^25 as devDeps; opt-in per-file via `// @vitest-environment jsdom`"
affects: [66-03 (EndgameInsightsBlock component consumes this hook + UserProfile.beta_enabled), 66-04 (integration wiring), 66-05 (FE test coverage)]

# Tech tracking
tech-stack:
  added: [@testing-library/react, jsdom]
  patterns:
    - "Hook file lives at src/hooks/useFoo.ts; matching unit test at src/hooks/__tests__/useFoo.test.tsx with file-level `// @vitest-environment jsdom` pragma"
    - "Module-level mock of @/api/client via vi.mock + importActual preserves non-mocked exports (buildFilterParams stays real while apiClient.post is mocked)"
    - "Reuse canonical filter serializer across hooks by exporting buildFilterParams (shared between useEndgames and useEndgameInsights)"

key-files:
  created:
    - frontend/src/types/insights.ts
    - frontend/src/hooks/useEndgameInsights.ts
    - frontend/src/hooks/__tests__/useEndgameInsights.test.tsx
  modified:
    - frontend/src/types/users.ts
    - frontend/src/api/client.ts
    - frontend/src/lib/impersonation.test.ts
    - frontend/package.json
    - frontend/package-lock.json

key-decisions:
  - "stale_filters typed as `unknown` (not `FilterContext | null`) on the FE envelope. BE sends either null or a FilterContext object; per Phase 65 D-13 the FE never reads this field, so `unknown` is the honest type and forces explicit narrowing if a future consumer wants to use it."
  - "opponent_type deliberately not forwarded to /insights/endgame — the insights router hardcodes `opponent_type=human` server-side (Phase 65). Passing it would 422. Enforced in two places: the hook implementation (inline comment) and the unit test (Pitfall 1 regression guard)."
  - "Hook test uses file-level `// @vitest-environment jsdom` pragma rather than a project-global vitest environment, because existing tests are pure (`vitest.config` has no `environment` set). Opt-in per file keeps non-DOM tests fast."
  - "jest-dom devDep dropped from install. Only @testing-library/react (renderHook, waitFor) is used; knip would flag jest-dom as unused otherwise (knip runs in CI per CLAUDE.md §Frontend)."
  - "Test file uses .tsx (not .test.ts per plan's first choice) because the QueryClientProvider wrapper contains JSX. Matches existing convention: `frontend/src/**/*.test.{ts,tsx}`."

patterns-established:
  - "FE type files mirror BE Pydantic schemas field-for-field with Literal unions matching verbatim — contract-drift-prevention pattern."
  - "Shared filter serializer across mutation + query hooks via named export, not copy-paste."

requirements-completed: [INS-01, INS-03, BETA-02]

# Metrics
duration: ~4min
completed: 2026-04-22
---

# Phase 66 Plan 02: Insights API types and useEndgameInsights hook

**TanStack Query v5 mutation hook for POST /insights/endgame with Literal-typed response envelope, UserProfile.beta_enabled required field, and shared buildFilterParams export — all three tasks green through tsc, lint, knip, and three-test vitest run.**

## Performance

- **Duration:** ~4 min
- **Started:** 2026-04-22T05:23:35Z
- **Completed:** 2026-04-22T05:27:42Z
- **Tasks:** 3
- **Files created:** 3
- **Files modified:** 5

## Accomplishments

- Shipped `frontend/src/types/insights.ts` with 8 exports (3 Literal unions, 4 interfaces, 1 AxiosError alias) — verbatim mirror of `app/schemas/insights.py` Phase 65 envelope
- Appended `beta_enabled: boolean` as a required field on `UserProfile` (no optional marker — the DB column is `NOT NULL` so the BE always sends a boolean)
- Exported `buildFilterParams` from `@/api/client` (was module-private) so the new hook reuses the canonical serializer instead of duplicating it
- Built `useEndgameInsights` as a `useMutation<EndgameInsightsResponse, InsightsAxiosError, FilterState>` that POSTs `null` body with query-param config, appending `color` and omitting `opponent_type` (Pitfall 1)
- Added three unit tests covering the POST shape, the Pitfall 1 regression guard (opponent_type not passed even when FilterState.opponentType='computer'), and AxiosError propagation on 429
- Added `@testing-library/react@^16.3` + `jsdom@^25.0` as devDependencies, wired via file-level pragma; project-global test environment unchanged
- Verification: `cd frontend && npx tsc --noEmit` clean, `npm run lint` 0 errors (3 pre-existing coverage warnings), `npm run knip` clean, `npm test` 86 tests across 7 files all pass, `npm run build` ships (~4.7s)

## Task Commits

1. **Task 1: Insights types + UserProfile.beta_enabled** — `0db27d4` (feat)
2. **Task 2: Export buildFilterParams + useEndgameInsights hook** — `7f3bae4` (feat)
3. **Task 3: Unit tests for useEndgameInsights** — `1b8bf46` (test)

## Files Created/Modified

- `frontend/src/types/insights.ts` — NEW. Literal-typed API envelope (`SectionId`, `InsightsStatus`, `InsightsError`, `SectionInsight`, `EndgameInsightsReport`, `EndgameInsightsResponse`, `InsightsErrorResponse`, `InsightsAxiosError`).
- `frontend/src/types/users.ts` — appended `beta_enabled: boolean` as final field of `UserProfile` with BETA-01 rationale comment.
- `frontend/src/api/client.ts` — changed `function buildFilterParams` → `export function buildFilterParams`. No logic change.
- `frontend/src/hooks/useEndgameInsights.ts` — NEW. `useMutation` wrapping `apiClient.post<EndgameInsightsResponse>('/insights/endgame', null, { params })`. Shared filter serialization via `buildFilterParams`; `color` appended; `opponent_type` deliberately omitted with inline justification.
- `frontend/src/hooks/__tests__/useEndgameInsights.test.tsx` — NEW. Three tests (POST shape, Pitfall 1 regression, AxiosError propagation) with module-level `@/api/client` mock and per-test `QueryClient`.
- `frontend/src/lib/impersonation.test.ts` — added `beta_enabled: false` to the `UserProfile` fixture (Rule 3 blocking fix: test file manually constructs the interface; new required field would have failed tsc in test compilation).
- `frontend/package.json` + `frontend/package-lock.json` — added `@testing-library/react@^16.3` and `jsdom@^25` as devDependencies.

## Decisions Made

- **`stale_filters: unknown` (not `FilterContext | null`):** The BE sends either null or a structured FilterContext; per Phase 65 D-13 the FE never reads this. Typing as `unknown` prevents accidental use without narrowing and avoids forcing a FilterContext FE type this plan doesn't need.
- **`opponent_type` enforced out in two places:** Hook code has an inline `// NOTE: opponent_type intentionally omitted` comment at the call site; unit test 2 asserts `params` has no `opponent_type` key even when `FilterState.opponentType='computer'`. Double-lock against regression because this is a silent 422 trap.
- **File-level jsdom pragma instead of global:** `vitest.config` has no `environment` set. Adding a global jsdom would slow down the 83 pure tests that don't need it. Per-file pragma keeps non-DOM tests fast.
- **Dropped `@testing-library/jest-dom`:** Only `renderHook` and `waitFor` from `@testing-library/react` are used. jest-dom would be flagged by knip in CI.
- **`.test.tsx` not `.test.ts`:** The QueryClientProvider wrapper contains JSX. Plan's acceptance criteria accepts either extension; chose `.tsx` because of the JSX literal.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Added `beta_enabled: false` to UserProfile fixture in `impersonation.test.ts`**
- **Found during:** Task 1 (adding required field to UserProfile interface)
- **Issue:** Making `beta_enabled` required on `UserProfile` broke `frontend/src/lib/impersonation.test.ts`, which constructs a `UserProfile` literal for test fixtures. Without the field, vitest's tsc-on-import would fail the test suite.
- **Fix:** Added `beta_enabled: false` to the `base` fixture.
- **Files modified:** `frontend/src/lib/impersonation.test.ts`
- **Verification:** `npm test -- src/lib/impersonation.test.ts` — 4/4 pass.
- **Committed in:** `0db27d4` (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (Rule 3 blocking)
**Impact on plan:** Necessary type-safety propagation. No scope creep — simply extends the plan's own Task 1 edit to the one place that manually constructs `UserProfile`.

## Issues Encountered

- **Plan's acceptance criterion "grep -q Sentry ... NO match" vs. plan's own action template.** The plan's Task 2 `<action>` block prescribes a docstring containing the phrase `handles Sentry` and `Do NOT add Sentry.captureException`. Acceptance criterion reads "`grep -q "Sentry" frontend/src/hooks/useEndgameInsights.ts` returns NO match". Taken literally these contradict. Resolved by preserving the plan-prescribed docstring (its whole purpose is to steer future contributors away from adding Sentry calls) while ensuring zero runtime `Sentry.*` calls — the intent of the criterion. Surface note only; behavior matches the plan.
- **`@testing-library/jest-dom` install flagged by knip as unused.** First install pulled in both packages; knip correctly flagged jest-dom. Dropped it (no matchers used) rather than adding a dummy import.

## User Setup Required

None — no external service configuration or environment variables introduced. Two new npm devDependencies (`@testing-library/react`, `jsdom`) ship via `package.json` + `package-lock.json`; standard `npm install` picks them up.

## Next Phase Readiness

- Plan 66-03 (EndgameInsightsBlock component) can import `useEndgameInsights` and the full envelope type surface directly: `import { useEndgameInsights } from '@/hooks/useEndgameInsights'` and `import type { SectionInsight, InsightsStatus, InsightsAxiosError } from '@/types/insights'`.
- Plan 66-03 can also gate the block on `profile.beta_enabled` — the field is present as a required `boolean` on `UserProfile` and wired end-to-end from the DB column via `UserProfileResponse`.
- Knip is clean; the `useEndgameInsights` export will satisfy knip once Plan 03 adds the first consumer (dead-export check deferred until then — this is expected for a pure plumbing wave).

## Self-Check: PASSED

**Files created (verified via `ls`):**
- FOUND: frontend/src/types/insights.ts
- FOUND: frontend/src/hooks/useEndgameInsights.ts
- FOUND: frontend/src/hooks/__tests__/useEndgameInsights.test.tsx

**Commits exist (verified via `git log`):**
- FOUND: 0db27d4 (Task 1 — feat: types + UserProfile.beta_enabled)
- FOUND: 7f3bae4 (Task 2 — feat: buildFilterParams export + hook)
- FOUND: 1b8bf46 (Task 3 — test: hook unit tests)

**Verification commands passed:**
- `cd frontend && npx tsc --noEmit` — 0 errors
- `cd frontend && npm run lint` — 0 errors
- `cd frontend && npm run knip` — clean
- `cd frontend && npm test` — 86 tests, 7 files, all pass
- `cd frontend && npm run build` — production build succeeds

---
*Phase: 66-frontend-endgameinsightsblock-beta-flag*
*Completed: 2026-04-22*
