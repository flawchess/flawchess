---
phase: 118-demand-ux-auto-enqueue
plan: "03"
subsystem: frontend-demand-ux
tags: [eval-queue, demand-ux, frontend, react, tanstack-query, guest-promo, tdd]
dependency_graph:
  requires:
    - phase: 118-01
      provides: [enqueue_tier2_window, EvalCoverageResponse-extended, count_is_analyzed_games, count_in_flight_evals]
    - phase: 118-02
      provides: [POST /imports/eval/tier1/{game_id}, POST /imports/eval/tier2, GET /imports/eval-coverage (extended)]
  provides:
    - useEvalCoverage extended (analyzedCount, inFlightCount, isError, in-flight polling)
    - useTier1Enqueue + useTier2Enqueue mutations with cache invalidation
    - NoAnalysisState per-game branching (guest/analyze/in-flight/null)
    - NoEngineAnalysisFlawsState real CTAs (guest/in-flight/analyze bulk)
    - FlawDenominatorPill in-flight badge + Analyze-more CTA + guest sign-up
    - LOW_COVERAGE_THRESHOLD constant (0.8) replacing 'coming soon' copy
  affects: [Library/FlawsTab, Library/GamesTab/LibraryGameCard, GlobalStats/FlawDenominatorPill, analysisCoverageCopy]
tech_stack:
  added: []
  patterns: [TanStack useMutation onSuccess invalidateQueries, localized in-flight state, LOW_COVERAGE_THRESHOLD gate, CLAUDE.md isError branch on every useEvalCoverage surface]
key_files:
  created:
    - frontend/src/hooks/useEnqueueGame.ts
    - frontend/src/components/library/__tests__/NoAnalysisState.test.tsx
  modified:
    - frontend/src/types/api.ts
    - frontend/src/hooks/useEvalCoverage.ts
    - frontend/src/hooks/__tests__/useEvalCoverage.test.tsx
    - frontend/src/components/library/analysisCoverageCopy.tsx
    - frontend/src/components/library/FlawStatsPanel.tsx
    - frontend/src/components/library/NoEngineAnalysisFlawsState.tsx
    - frontend/src/components/library/NoAnalysisState.tsx
    - frontend/src/components/results/LibraryGameCard.tsx
    - frontend/src/pages/GlobalStats.tsx
    - frontend/src/pages/library/FlawsTab.tsx
    - frontend/src/components/library/__tests__/FlawCard.test.tsx
decisions:
  - "LOW_COVERAGE_THRESHOLD = 0.8 (named constant for <80% CTA gate, D-118-09)"
  - "isInFlight in LibraryGameCard is local state, not driven by aggregate inFlightCount (D-118-11)"
  - "onInFlightChange callback pattern: tier-1 onSuccess sets parent card's local state"
  - "useNavigate in NoAnalysisState uses react-router-dom navigate() not window.location.href"
  - "isCoverageError prop on FlawDenominatorPill: isError from useEvalCoverage rendered explicitly (T-118-13)"
  - "FlawCard.test.tsx: added mocks for useUserProfile/useEnqueueGame/useNavigate to fix LibraryGameCard rendering in test"
metrics:
  duration: "~18 minutes"
  completed: "2026-06-14T08:41:34Z"
  tasks_completed: 3
  files_changed: 12
---

# Phase 118 Plan 03: Demand UX Frontend Summary

Extended useEvalCoverage hook and types, new useTier1/Tier2Enqueue mutations, repurposed analysisCoverageCopy, wired four Library flaw surfaces with real coverage badges, in-flight states, low-coverage CTAs, guest promotion, and per-game analyze buttons.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Extend types + useEvalCoverage + useEnqueueGame (TDD) | 01f505d3 | api.ts, useEvalCoverage.ts, useEnqueueGame.ts, useEvalCoverage.test.tsx |
| 2 | Coverage copy + FlawStatsPanel/FlawComparisonGrid/NoEngineAnalysisFlawsState | 7954b094 | analysisCoverageCopy.tsx, FlawStatsPanel.tsx, NoEngineAnalysisFlawsState.tsx, NoAnalysisState.tsx, LibraryGameCard.tsx, GlobalStats.tsx, FlawsTab.tsx, FlawCard.test.tsx |
| 3 | NoAnalysisState test suite | 2a2fa627 | NoAnalysisState.test.tsx |

## Key Deliverables

### Types (frontend/src/types/api.ts)
- `EvalCoverageResponse` extended with `analyzed_count: number` and `in_flight_count: number`
- New `EnqueueTier1Response { status: 'enqueued' | 'skipped_guest' | 'already_queued'; game_id: number }`
- New `EnqueueTier2Response { status: 'enqueued' | 'in_flight' | 'nothing_to_enqueue' | 'skipped_guest'; enqueued_count: number }`

### useEvalCoverage extension (D-118-12)
- `refetchInterval` guard extended: keeps polling when `in_flight_count > 0` even at 100% pct_complete
- Returns `analyzedCount`, `inFlightCount`, `isError` in addition to existing fields
- Backward-compatible: existing Endgames/Openings/GlobalStats consumers unaffected

### useEnqueueGame.ts (new file)
- `useTier1Enqueue(gameId)`: POSTs `/imports/eval/tier1/${gameId}`, invalidates `['imports','eval-coverage']` on success
- `useTier2Enqueue()`: POSTs `/imports/eval/tier2`, same cache invalidation

### analysisCoverageCopy.tsx (repurposed)
- Removed `ANALYSIS_COVERAGE_PARAGRAPHS` and `ANALYSIS_COVERAGE_COPY` (no "coming soon" copy)
- Exports `LOW_COVERAGE_THRESHOLD = 0.8` (D-118-09 named constant)
- Exports `ANALYSIS_COVERAGE_INFO_COPY` string for real popover body

### FlawDenominatorPill (FlawStatsPanel.tsx)
- New props: `inFlightCount`, `isGuest`, `isCoverageError`
- Shows "· N in progress" text when `inFlightCount > 0`
- Shows "Analyze more" (brand-outline CTA, `data-testid="btn-analyze-more-pill"`) when below threshold and idle, for non-guests
- Shows "Sign up to unlock full-game analysis" link (`data-testid="btn-signup-for-analysis-pill"`) for guests
- `isCoverageError=true` renders explicit "Failed to load analysis status…" (T-118-13)

### NoEngineAnalysisFlawsState (rebuilt)
- Props: `isGuest`, `inFlightCount`, `analyzedCount`, `totalCount`
- Guest: "Sign up to unlock full-game analysis" + brand-outline link (`data-testid="btn-signup-for-analysis-flaws"`)
- Non-guest in-flight: "Analyzing your games…" + "N of M analyzed" progress text, no button
- Non-guest idle: "Analyze your games" + primary tier-2 button (`data-testid="btn-analyze-more"`)

### NoAnalysisState (rebuilt with branching)
- Props: `gameId`, `isGuest`, `isAnalyzed`, `isInFlight?`, `onInFlightChange?`
- `isGuest`: "Sign up to unlock analysis" (`data-testid="btn-signup-for-analysis"`)
- `!isAnalyzed && !isInFlight`: "Analyze this game" tier-1 button (`data-testid="btn-analyze-game-{gameId}"`)
- `!isAnalyzed && isInFlight`: pulsing "Analyzing…" span (`data-testid="analyzing-{gameId}"`)
- `isAnalyzed`: returns null (lichess-eval and FlawChess-analyzed games show nothing)

### LibraryGameCard wiring
- Added `useUserProfile()` call for `isGuest` derivation
- Added local `isInFlight` state (localized — D-118-11: only clicked card shows pulse)
- Both `NoAnalysisState` call sites (desktop col-3/mobile flaw block + desktop col-2 missing-series fallback) receive full props

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] FlawCard.test.tsx broke when LibraryGameCard gained new hooks**
- **Found during:** Task 2 (full test suite run)
- **Issue:** `FlawCard.test.tsx` renders `LibraryGameCard` in a test without `QueryClientProvider` or Router context. When `LibraryGameCard` gained `useUserProfile()` (via `QueryClient`) and when `NoAnalysisState` (rendered for analyzed-but-missing-series fallback) gained `useNavigate()` and `useTier1Enqueue()`, the test failed with "No QueryClient set" and "useNavigate() may be used only in the context of a Router".
- **Fix:** Added `vi.mock` for `useUserProfile`, `useEnqueueGame`, and `react-router-dom#useNavigate` in `FlawCard.test.tsx`.
- **Files modified:** `frontend/src/components/library/__tests__/FlawCard.test.tsx`
- **Commit:** 7954b094

**2. [Rule 1 - Bug] useEvalCoverage "stops polling" test broke with in_flight_count guard**
- **Found during:** Task 1 GREEN phase
- **Issue:** The refetchInterval stop condition `data.in_flight_count === 0` compared to `undefined` (old mock responses don't include `in_flight_count`), evaluating to `false` and allowing polling to continue.
- **Fix:** Changed to `(data.in_flight_count ?? 0) === 0` for backward-compat with old mock shapes.
- **Files modified:** `frontend/src/hooks/useEvalCoverage.ts`
- **Commit:** 01f505d3

**3. [Rule 2 - Missing] onInFlightChange callback for localized in-flight state**
- **Found during:** Task 2/3 implementation
- **Issue:** `NoAnalysisState` needed a callback to set the parent card's local in-flight state on tier-1 mutation success (D-118-11: localized, not global inFlightCount).
- **Fix:** Added `onInFlightChange?: (inFlight: boolean) => void` prop to `NoAnalysisState`; called in tier-1 mutation's `onSuccess` handler.
- **Files modified:** `NoAnalysisState.tsx`, `LibraryGameCard.tsx`
- **Commit:** 7954b094

## Tests Added

**useEvalCoverage.test.tsx** (4 new tests):
- `returns analyzedCount and inFlightCount from the response`
- `defaults analyzedCount and inFlightCount to 0 when fields are absent`
- `keeps polling when pct_complete=100 but in_flight_count > 0`
- `stops polling when pct_complete=100 AND in_flight_count=0 AND total_count>0`

**NoAnalysisState.test.tsx** (6 new tests, new file):
- Guest: renders `btn-signup-for-analysis` CTA
- Guest: does not render analyze button
- Not-analyzed idle: renders `btn-analyze-game-{gameId}`
- Not-analyzed idle: clicking fires tier-1 mutation
- Not-analyzed in-flight: renders `analyzing-{gameId}` pulse span
- Analyzed: returns null

**Total: 10 new tests. Suite: 915 passed (all 79 test files pass).**

## Known Stubs

None. All coverage counts, mutation endpoints, and branching logic are fully wired.

## Threat Flags

None. All surfaces introduced by this plan were already in the plan's threat model (T-118-11 through T-118-13).

## Self-Check: PASSED

### Files verified:
- `frontend/src/hooks/useEnqueueGame.ts` contains `useTier1Enqueue` and `useTier2Enqueue`
- `frontend/src/hooks/useEvalCoverage.ts` returns `analyzedCount`, `inFlightCount`, `isError`
- `frontend/src/types/api.ts` contains `analyzed_count`, `in_flight_count`, `EnqueueTier1Response`, `EnqueueTier2Response`
- `frontend/src/components/library/analysisCoverageCopy.tsx` contains `LOW_COVERAGE_THRESHOLD` and 0 instances of "coming soon"
- `frontend/src/components/library/FlawStatsPanel.tsx` contains `btn-analyze-more-pill` and `btn-signup-for-analysis-pill`
- `frontend/src/components/library/NoEngineAnalysisFlawsState.tsx` contains `btn-signup-for-analysis-flaws`, `btn-analyze-more`
- `frontend/src/components/library/NoAnalysisState.tsx` contains `btn-signup-for-analysis`, `btn-analyze-game-`, `analyzing-`
- `frontend/src/components/library/__tests__/NoAnalysisState.test.tsx` exists with 6 tests

### Commits verified:
- 01f505d3: Task 1 (types + hooks + TDD tests)
- 7954b094: Task 2 (coverage copy + surfaces)
- 2a2fa627: Task 3 (NoAnalysisState tests)

### Build: PASSED (npm run build succeeds)
### Lint: PASSED (npm run lint clean)
### Knip: PASSED (npm run knip clean)
### Tests: 915/915 passed

## UAT fixes (post-checkpoint)

Three issues found during human visual UAT (Task 4 checkpoint). All fixed atomically
with `fix(118-03):` prefix commits.

### Issue 1 + 2 (combined): Coverage badge missing from Library subtabs

**Root cause:** The `FlawDenominatorPill` built in the plan renders on the GlobalStats
/ Stats tab, not in the Library Games or Flaws subtabs where the user was looking. The
two match-count rows (`{matchedCount} of {total} games` in `LibraryGameCardList` and
`{matchedCount} flaws matched` in `FlawsTab`) had no coverage indicator at all.

**Fix:** Created `frontend/src/components/library/EvalCoverageBadge.tsx`:
- Driven by `useEvalCoverage()` — shows "N of M analyzed" with "· K in progress" when
  in-flight; merged "Analyze more" CTA (brand-outline) when coverage is below
  `LOW_COVERAGE_THRESHOLD` and idle; guest branch shows "Sign up to analyze" link to
  `/login?tab=register`; mandatory `isError` branch per CLAUDE.md
- Wired into `LibraryGameCardList` (Games subtab) and `FlawsTab` (Flaws subtab): each
  match-count `<p>` is now inside a `flex items-center justify-between gap-3` row so
  the count stays left and the badge sits right. Applied to the shared `mainContent`
  block in FlawsTab (consumed by both desktop SidebarLayout and mobile stacked layout).
- `LibraryGameCardList` gained an `isGuest: boolean` prop; `GamesTab` derives it from
  `useUserProfile` and passes it through.
- D-118-08 scope guard honoured: Stats/Endgames/Openings coverage surfaces untouched.
- **Commit:** a1e679f8

### Issue 3: Per-game button stuck "Analyzing…" + button label too long

**Root cause (stuck state):** `useTier1Enqueue.onSuccess` only invalidated
`['imports', 'eval-coverage']`, never the games list query
`['library-games', ...]`. So `game.analysis_state` never refreshed from
`no_engine_analysis` to `analyzed` after the eval completed, and the card's local
`isInFlight` state (set in `LibraryGameCard`) was never cleared. The card stayed
"Analyzing…" until a full page reload.

**Fix:**
1. `useEnqueueGame.ts`: `useTier1Enqueue.onSuccess` now also invalidates
   `['library-games']` (prefix-match, all param variants) so the games list refetches
   immediately after the tier-1 mutation.
2. `useEvalCoverage.ts`: export `EVAL_COVERAGE_POLL_INTERVAL_MS` (was private) so
   callers can reuse the same constant without introducing new magic numbers.
3. `useLibrary.ts`: `useLibraryGames` gains an optional `refetchIntervalMs` param;
   when > 0, the query re-polls at that interval.
4. `GamesTab.tsx`: calls `useEvalCoverage()` for `inFlightCount` and passes
   `EVAL_COVERAGE_POLL_INTERVAL_MS` to `useLibraryGames` while in-flight (0 otherwise).
   Cards now flip from "Analyzing…" to the analyzed view within ~3 s, no page reload.
5. `LibraryGameCard.tsx`: added a `useEffect` that calls `setIsInFlight(false)` when
   `isAnalyzed && isInFlight` — clears the local in-flight state as soon as the
   query refetch delivers the updated `analysis_state`.
6. `NoAnalysisState.tsx`: button label shortened from "Analyze this game" to "Analyze"
   (keeps Cpu icon and existing testid/aria-label).
- **Commit:** ba2fd576

### New tests

`EvalCoverageBadge.test.tsx` (5 tests, new file):
- Analyzed/total count renders in the badge
- In-flight: "· K in progress" visible, CTA hidden
- Low-coverage non-guest: "Analyze more" btn-analyze-more present
- Low-coverage guest: sign-up CTA (btn-analyze-more with "Sign up" aria-label)
- High-coverage: CTA hidden (90% ≥ 80% threshold)

**Total after UAT fixes: 920 tests passed (80 test files).**

### Gate results

- `npm run lint`: PASSED
- `npm run knip`: PASSED (EvalCoverageBadge and EVAL_COVERAGE_POLL_INTERVAL_MS both consumed)
- `npm test -- --run`: 920/920 passed

### Issue 4: EvalCoverageBadge had no InfoPopover tooltip on Games/Flaws subtabs

**Root cause:** Two parallel coverage-badge components existed: `FlawDenominatorPill`
(prop-driven, had `InfoPopover` with `ANALYSIS_COVERAGE_INFO_COPY`) on the Stats tab,
and `EvalCoverageBadge` (hook-driven, no tooltip) on Games + Flaws subtabs. The
explanatory tooltip was silently missing on two of the three surfaces.

**Fix (commit 0f91e4f2):** Consolidated into one canonical `EvalCoverageBadge` that is
prop-driven and includes the `InfoPopover` tooltip. `FlawDenominatorPill` removed.
`GlobalStats.tsx` switched to `EvalCoverageBadge` passing flaw-stats probe values;
`GamesTab.tsx` / `LibraryGameCardList.tsx` / `FlawsTab.tsx` updated to supply the full
coverage-prop set from `useEvalCoverage()`. Test suite updated to prop-driven interface
with a new InfoPopover test: 921/921 passed; lint + knip clean.

### Issue 5: Per-game "Analyzing…" still stuck (residual race) + remove front-run button

Two items from a later UAT round.

**5a — Stuck "Analyzing…" pill (residual race Issue 3 missed).** Issue 3's fix
invalidated `['library-games']` on tier-1 *enqueue success* (click time), which is
too early — the game is not analyzed yet at click. The real gap: the games-list
poll is gated on `inFlightCount > 0` (`GamesTab.tsx`), so it stops the instant the
last eval job completes. When a single tier-1 job is the only in-flight job, its
completion can land *after* the previous poll, and there is no guaranteed final
refetch once `inFlightCount` hits 0 — so `analysis_state` never flips to `analyzed`,
the local `isInFlight` never clears, and the pill shows "Analyzing…" indefinitely.
(Confirmed backend-clean: `_classify_and_fill_oracle` writes `white_blunders` and the
`eval_jobs` completion in the same transaction/commit in `eval_drain.py`, so there is
no backend lag between job-completed and `is_analyzed`.)

Fix: in `GamesTab.tsx` and `FlawsTab.tsx`, watch the `inFlightCount` `>0 → 0`
transition (via a `useRef` of the previous value) and invalidate the list queries
once on that edge — `['library-games']` on Games; `['library-flaws']` /
`['library-flaw-stats']` / `['library-flaw-comparison']` on Flaws (the flaw views
don't poll at all, so they were also stale until reload). `eval-coverage` self-polls,
so the transition is always observed even after the list query stops polling.

**5b — Remove the bulk "Analyze more" front-run button (both surfaces + endpoint).**
Decision: front-running is a no-op for speed — throughput is server-fixed (one shared
Stockfish pool) and D-118-06 already disabled the button while draining. Active users
are already prioritized at every tier (tier-1 > tier-2 auto-window > tier-3 ordered by
`last_activity DESC`), and import-completion + the hourly `last_activity` bump already
keep the tier-2 window topped up automatically. The button added nothing but
redundancy. The per-game "Analyze this game" (tier-1) button stays — that is the one
meaningful immediate control.

Removed: `useTier2Enqueue` hook, `EnqueueTier2Response` type (frontend + backend
schema), `POST /imports/eval/tier2` endpoint, `count_tier2_in_flight` repo helper, and
their tests (`test_imports_tier2_enqueue.py` deleted). `EvalCoverageBadge` keeps only
the guest sign-up CTA (guests are excluded from the queue, so it is their only path —
testid renamed `btn-analyze-more` → `btn-coverage-signup`). `NoEngineAnalysisFlawsState`
non-guest idle branch replaced with a passive explainer + "Go to Games" link.
`enqueue_tier2_window` is retained (still called by the activity middleware and import
completion). Tooltip copy (`ANALYSIS_COVERAGE_INFO_COPY`) rewritten to explain
automatic background analysis and activity-based prioritization.

Gates: ruff + ty clean; affected backend tests pass (32); tsc + eslint + knip clean;
affected frontend tests pass (52).

### Issue 6: Remove the tier-2 auto-enqueue entirely; add a live background-progress counter

Follow-on decision after Issue 5. The tier-2 auto-enqueue (`enqueue_tier2_window`,
fired on the hourly `last_activity` bump and on import completion) is redundant as a
*scheduler*: the tier-3 idle drain already orders the whole backlog by
`users.last_activity DESC`, so a single active user's recent games are analyzed first
either way, and tier-3 covers the entire backlog rather than a 200-game window. The
only thing tier-2 uniquely provided was the `eval_jobs` rows that drove the badge's
"N in progress" live signal — and even that only covered a post-import burst of ≤200
games before freezing.

**Removed (mechanism only):** `enqueue_tier2_window` + `TIER2_AUTO_WINDOW_SIZE`, its two
fire-and-forget callers (`LastActivityMiddleware`, `_complete_import_job`), and the
`TestTier2AutoWindow` / `TestImportCompletionTrigger` suites. The `last_activity` write
stays (it's the tier-3 priority key). `import asyncio` dropped from the middleware where
now unused.

**Retained (per explicit user direction — "we might need it later"):** the tier *system*
itself — `TIER_AUTO_WINDOW` constant, the `eval_jobs.tier` column, the generic
SKIP-LOCKED claim path that can pick any tier, and `Game.needs_engine_full_evals`. The
tier-2 lane is left dormant for a future phase that may let users either analyze only
their own games or opt in to help drain the global tier-3 backlog. Docstrings/comments
in `eval_queue_service.py`, `eval_jobs.py` (left implicitly via system retention),
`game.py`, `config.py`, `last_activity.py`, and `import_service.py` updated to record
this.

**Live counter (replaces tier-2's progress signal, done better):** `useEvalCoverage`
gains a `trackFullAnalysis` option. When set (Games + Flaws tabs only), the badge keeps
polling while full analysis is incomplete (`analyzed_count < total_count`), so the
"N of M analyzed" count ticks up live as the background tier-3 drain works through the
*whole* backlog — not just a 200-game window. A stall backstop (5 consecutive fetches
with no new analysis, tracked via `dataUpdatedAt` so re-renders don't false-count) stops
the poll for permanently-stuck games (e.g. an engine outage). Readiness-gate consumers
(Endgames / Openings / Import) pass nothing and keep the original stop-at-entry-ply
behavior, so they don't poll for the full-analysis backlog. The game/flaw *card lists*
remain lazy during background drain (they refresh on navigation and on the tier-1
in-flight→0 transition from Issue 5); only the cheap count badge polls live.

Gates: ruff + ty clean; full backend suite 2606 passed; tsc + eslint + knip clean; full
frontend suite 924 passed (+3 new `useEvalCoverage` trackFullAnalysis tests).
