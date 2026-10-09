---
phase: 233-train-puzzle-timing-telemetry
plan: 03
subsystem: ui
tags: [react, typescript, telemetry, keepalive, visibility-api, pagehide, vitest]

requires:
  - phase: 233-train-puzzle-timing-telemetry
    provides: "plan 01 server route POST /train/sessions/{id}/solves/{position}/review (204, ReviewTelemetry body, merge per key)"
  - phase: 233-train-puzzle-timing-telemetry
    provides: "plan 02 useTrainPuzzleTelemetry (think part), visibleStopwatch, trainTelemetry constants"
provides:
  - "Review-time telemetry: visible-only, 30-min-capped review_ms plus review_hidden_ms, flushed on Next (exit 'next') through trainApi.recordReview"
  - "postReviewKeepalive: fetch keepalive with Bearer header, the transport of every non-Next flush (exit 'pagehide' = left the reveal without pressing Next)"
  - "One non-Next flush helper fed by visibilitychange-hidden, window pagehide and a StrictMode-safe deferred unmount"
  - "Analyze round trip keeps ONE review timer: reveal cache carries reviewTelemetry, updated by an update-only mirror"
affects: [233-04, 233-05]

actuals:
  tokens: 12800
  tasks: 3
  commits: 3
plan_head_before: b3697d5b2dc76b2f670aa4775c1f0d582c76d99e
plan_head_after: b50de61f85234634dd15b7968416345eab4b21a3

tech-stack:
  added: []
  patterns:
    - "Single funnel for all non-Next exits: one internal helper, one transport, so guard and dedupe rules hold for every trigger"
    - "Microtask-deferred unmount flush guarded by an aliveRef, so React StrictMode's simulated unmount sends nothing"
    - "Update-only cache mirror: never creates an entry, so a late write cannot resurrect a reveal the loop cleared"

key-files:
  created: []
  modified:
    - frontend/src/types/train.ts
    - frontend/src/lib/trainTelemetry.ts
    - frontend/src/lib/trainRevealCache.ts
    - frontend/src/api/client.ts
    - frontend/src/hooks/useTrainPuzzleTelemetry.ts
    - frontend/src/components/train/TrainSolveScreen.tsx
    - frontend/src/api/__tests__/client.test.ts
    - frontend/src/hooks/__tests__/useTrainPuzzleTelemetry.test.ts
    - frontend/src/lib/__tests__/trainRevealCache.test.ts
    - frontend/src/components/train/__tests__/TrainSolveScreen.test.tsx
    - frontend/src/components/train/__tests__/TrainSolveScreen.restoredGameArrow.test.tsx
    - frontend/src/pages/__tests__/Train.solveLoop.test.tsx

key-decisions:
  - "ReviewExit stays the closed set 'next' | 'pagehide'; 'pagehide' means left the reveal without pressing Next (route change, unmount, Analyze, tab hidden, unload). No third value"
  - "Only the Next flush sets the Next-flushed guard; a non-Next flush never does, so a returning user's Next still overwrites per key with larger cumulative totals"
  - "At most one non-Next flush per hidden span (hidden-span marker cleared on visible); a later span or unmount flushes again with updated totals"
  - "postReviewKeepalive swallows network rejections and 4xx, reports only 5xx to Sentry with a constant message and the status in context; Next-path errors are left to the global MutationCache handler"
  - "API_BASE_URL and AUTH_TOKEN_STORAGE_KEY are module constants in client.ts (not exported, knip) shared by axios and the keepalive fetch"

patterns-established:
  - "StrictMode hook tests need RTL configure({ reactStrictMode: true }): StrictMode nested inside a wrapper component never double-invokes effects, so a nested wrapper silently stops covering the simulated unmount"

requirements-completed: [D-03, D-04, D-06, D-07]

coverage:
  - id: C1
    description: "Next on a reveal sends exactly one review flush for that puzzle (exit next, visible-only review_ms, review_hidden_ms) before the loop advances"
    requirement: "D-03"
    verification:
      - kind: integration
        ref: "frontend/src/pages/__tests__/Train.solveLoop.test.tsx#Next does not fetch the reveal for the next, unattempted puzzle (FLAWCHESS-64)"
        status: pass
      - kind: integration
        ref: "frontend/src/components/train/__tests__/TrainSolveScreen.test.tsx#telemetry: Next flushes the review once with exit next for this position"
        status: pass
      - kind: unit
        ref: "frontend/src/hooks/__tests__/useTrainPuzzleTelemetry.test.ts#review: *"
        status: pass
    human_judgment: false
  - id: C2
    description: "Only visible time counts in review_ms, hidden span lands in review_hidden_ms, both capped at 30 min"
    requirement: "D-04"
    verification:
      - kind: unit
        ref: "frontend/src/hooks/__tests__/useTrainPuzzleTelemetry.test.ts#review: no timer before the verdict, then visible time minus the hidden span is sent on Next"
        status: pass
    human_judgment: false
  - id: C3
    description: "Every non-Next exit (unmount, page hidden, pagehide) sends one authenticated keepalive flush; Next-flushed puzzles never re-flush; StrictMode double-invoke sends nothing"
    requirement: "D-03"
    verification:
      - kind: unit
        ref: "frontend/src/hooks/__tests__/useTrainPuzzleTelemetry.test.ts#exit: *"
        status: pass
      - kind: integration
        ref: "frontend/src/components/train/__tests__/TrainSolveScreen.test.tsx#telemetry: leaving an open reveal (unmount) sends one keepalive flush with exit pagehide for this position"
        status: pass
      - kind: integration
        ref: "frontend/src/components/train/__tests__/TrainSolveScreen.test.tsx#telemetry: Next then unmount sends no keepalive flush"
        status: pass
    human_judgment: false
  - id: C4
    description: "Keepalive transport carries the Bearer token same-origin, never goes through the axios 401 interceptor, and reports only 5xx"
    requirement: "D-06"
    verification:
      - kind: unit
        ref: "frontend/src/api/__tests__/client.test.ts#postReviewKeepalive"
        status: pass
      - kind: command
        ref: "UNLOAD-TRANSPORT-OK gate (no beacon call in frontend/src, no unload/beforeunload listener in the hook)"
        status: pass
    human_judgment: false
  - id: C5
    description: "exit is set on every flush: 'next' on Next, 'pagehide' on every other exit"
    requirement: "D-07"
    verification:
      - kind: unit
        ref: "frontend/src/hooks/__tests__/useTrainPuzzleTelemetry.test.ts#exit: hidden, visible, then Next still sends the larger Next flush"
        status: pass
    human_judgment: false
  - id: C6
    description: "Analyze round trip continues ONE review timer from exactly the flushed totals; the reveal cache holds what the row received"
    requirement: "D-03"
    verification:
      - kind: unit
        ref: "frontend/src/hooks/__tests__/useTrainPuzzleTelemetry.test.ts#analyze: *"
        status: pass
      - kind: unit
        ref: "frontend/src/lib/__tests__/trainRevealCache.test.ts#updateTrainRevealCacheReview"
        status: pass
      - kind: integration
        ref: "frontend/src/components/train/__tests__/TrainSolveScreen.test.tsx#telemetry: Analyze saves the review snapshot into the reveal cache"
        status: pass
    human_judgment: false
  - id: C7
    description: "Real tab close, tab switch, in-app navigation and Analyze-then-close landing a flush in drill_solves.telemetry (jsdom cannot unload or background a page)"
    requirement: "D-03"
    verification: []
    human_judgment: true
    rationale: "Manual-only per the plan's verification block (VALIDATION.md): a dev build must be driven through close-tab, switch-tab-and-return, nav-link-away, Analyze-then-close and the drill_solves.telemetry row inspected after each"

duration: 25min
completed: 2026-10-05
status: complete
---

# Phase 233 Plan 03: Review-time telemetry and abandon-safe flushes Summary

**Visible-only, capped review_ms and review_hidden_ms flushed on Next through the mutation path and on every other exit (unmount, tab hidden, pagehide) through one Bearer-authenticated keepalive fetch, with one review timer carried across the Analyze round trip.**

## Performance

- **Duration:** ~25 min
- **Completed:** 2026-10-05
- **Tasks:** 3 (1 tracer, 2 auto/tdd)
- **Files:** 12 modified, 0 created

## Accomplishments

- Task 1 (tracer): `useTrainPuzzleTelemetry` gained a review stopwatch that starts when the verdict lands; `handleNextFromReveal` calls `flushReviewOnNext()` first, which sends `{v, exit: 'next', review_ms, review_hidden_ms}` through `useMutation(trainApi.recordReview)` and sets the Next-flushed guard. `ReviewExit`/`ReviewTelemetry` types, `buildReviewTelemetry` and `trainApi.recordReview` added.
- Task 2: `postReviewKeepalive` (fetch `keepalive: true`, Bearer from localStorage, same-origin `/api` URL, 5xx-only Sentry capture) is called from exactly one place, the internal `flushReviewNonNext` helper, which is fed by the `visibilitychange`-hidden branch, a `window` `pagehide` listener and a microtask-deferred unmount flush guarded by `aliveRef`. All three listeners live in the one mount effect.
- Task 3: `CachedTrainReveal.reviewTelemetry?` plus `updateTrainRevealCacheReview` (update-only). The Analyze click stores `snapshotReviewForAnalyze()` without stopping the timer; every non-Next flush mirrors the same snapshot it sent into a matching cache entry; a restored reveal seeds the stopwatch from it when `isUsableReviewSnapshot` accepts the numbers.
- Full frontend suite green (308 files, 5110 tests), plus lint, `tsc -b` build and knip.

## Mutation proofs

- m1 (non-Next flush sets the Next-flushed guard): 3 tests failed ("exit: hidden, visible, then Next ...", "exit: a second hidden span ...", "review: no timer before the verdict ..."); reverted.
- m2 (delete the Next-guard early return in `flushReviewNonNext`): "exit: Next then unmount sends nothing ..." failed; reverted.
- m3 (drop the `aliveRef` check in the unmount microtask): "exit: StrictMode double effect sends nothing ..." failed; reverted. See Deviations: this one first passed because the test did not really run under StrictMode.
- m4 (delete the hidden-span marker check): "exit: hidden then pagehide in the same hidden span sends one flush" failed; reverted.
- Mirror (delete the `updateTrainRevealCacheReview` call): "analyze: unmount mirrors the flushed snapshot into the reveal cache" and "analyze: a hidden-tab flush also mirrors its snapshot" failed; reverted.

## Task Commits

1. **Task 1 (tracer): flush review time on Next via recordReview** - `c578bad61` (feat)
2. **Task 2: keepalive review flush for every non-Next exit** - `85b0a3369` (feat)
3. **Task 3: keep one review timer across the Analyze round trip** - `b50de61f8` (feat)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] StrictMode hook tests did not exercise the simulated unmount**
- **Found during:** Task 2, mutation proof m3 (the mutation did not turn "exit: StrictMode" red)
- **Issue:** a wrapper component that nests `<StrictMode>` (needed to also provide the QueryClientProvider) never triggers React's double-invoke, because it only applies when StrictMode is the outermost element of the mount. Both the new StrictMode test and plan 02's "think: a first mount under React StrictMode" test (which I had switched from `wrapper: StrictMode` to the nested wrapper) were silently vacuous.
- **Fix:** `renderHookStrict` helper using RTL `configure({ reactStrictMode: true })` around the render; both StrictMode tests use it. m3 then failed as expected.
- **Files modified:** frontend/src/hooks/__tests__/useTrainPuzzleTelemetry.test.ts
- **Commit:** 85b0a3369

**2. [Rule 3 - Blocking] RTL does not auto-clean hooks in this suite**
- **Found during:** Task 2 (hooks left mounted by earlier tests received later tests' `pagehide`/visibility events)
- **Fix:** explicit `cleanup()` plus a microtask flush in the hook test file's `afterEach`.
- **Files modified:** frontend/src/hooks/__tests__/useTrainPuzzleTelemetry.test.ts
- **Commit:** 85b0a3369

**3. [Rule 3 - Blocking] `useMutation().mutate` runs `mutationFn` in a microtask**
- **Found during:** Task 1 tests (synchronous `toHaveBeenCalled` assertions saw zero calls)
- **Fix:** hook tests flush with `await act(async () => {})` (Vitest fake timers do not fake microtasks); the screen test uses `waitFor`. A per-test `QueryClient` replaces one built inside the wrapper, which would be recreated every render.
- **Commit:** c578bad61

**Total deviations:** 3 auto-fixed (1 bug in test coverage, 2 blocking test-harness issues). **Impact:** none on production code; all within the plan's files.

## Known Stubs

None.

## Threat Flags

None beyond the plan's `<threat_model>`. The only new network surface is the keepalive POST to the route shipped in plan 01, same-origin with the existing Bearer token (T-233-11 to T-233-14 mitigations implemented as specified; T-233-20 accepted).

## Accepted residuals (from the plan, unchanged)

- A page killed with no `visibilitychange`-hidden and no `pagehide` (crash, never-hidden kill) sends no flush; the row keeps its solve patch without `review_*` keys.
- A dropped keepalive request is not retried; a late non-Next flush could land after the Next flush (T-233-20).
- A modifier-click on Analyze (new tab) is not an exit.
- Manual-only check still open (coverage C7): close tab / switch tab and return / nav link away / Analyze then close, inspecting `drill_solves.telemetry` on a dev build.

## Self-Check: PASSED

- All 12 modified files exist; commits `c578bad61`, `85b0a3369`, `b50de61f8` are ancestors of HEAD; `commits:` measured from the plan ledger (3).
- Verification: the six touched test files green (174 tests), full `npm test -- --run` green (5110), `npm run lint`, `npm run build`, `npm run knip` exit 0; EXIT-PATHS-OK (9 `it('exit: ...` tests, one `postReviewKeepalive(` call site in the hook) and UNLOAD-TRANSPORT-OK printed; `isCachedTrainReveal` does not mention `reviewTelemetry`.
