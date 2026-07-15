---
phase: 170-localstorage-resume
plan: 02
subsystem: frontend-api
tags: [tanstack-query, axios, bots, store-once, resume]

# Dependency graph
requires:
  - phase: 170-localstorage-resume plan 01
    provides: botPendingStore.ts's PendingStoreEntry/listPendingStore/removePendingStore, the queue this plan drains
  - phase: 167-backend-store-on-finish
    provides: the shipped, idempotent POST /bots/games endpoint and its StoreBotGameRequest/StoreBotGameResponse schemas
provides:
  - botsApi.storeGame — the first frontend call site of POST /bots/games
  - useStoreBotGame — TanStack mutation with the D-13 per-status retry predicate (shouldRetryStore), for a future direct call site
  - useDrainPendingStore — the drain loop that decides, per HTTP outcome, whether a queued finished game survives to the next visit
  - toStoreRequest — the pure PendingStoreEntry -> StoreBotGameRequest mapper, the tc_preset invariant's single source of truth
affects: [170-03, 170-04, 170-05, resume-seam, store-once-drain, Bots.tsx-mount-drain]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Drain loop owns a retry-less useMutation of its own rather than reusing the general-purpose useStoreBotGame() — an unconditional-true retry predicate for 401 would hang mutateAsync forever within one for-loop iteration; the drain's real retry mechanism is the next /bots mount (D-13), not TanStack's in-flight retry"
    - "Pure extraction for direct testability: toStoreRequest and shouldRetryStore are both plain functions, unit-tested without mounting any hook"

key-files:
  created:
    - frontend/src/types/bots.ts
    - frontend/src/hooks/useStoreBotGame.ts
    - frontend/src/hooks/__tests__/useStoreBotGame.test.ts
  modified:
    - frontend/src/api/client.ts

key-decisions:
  - "tc_preset is toBackendTcStr(baseSeconds, incrementSeconds) — base-SECONDS, identical to the PGN's [TimeControl] header — per the 2026-07-13 RESEARCH correction to CONTEXT.md's original (inverted) D-14 text. No separate display-preset derivation exists anywhere in this plan's code."
  - "useDrainPendingStore does NOT reuse useStoreBotGame() internally. It constructs its own useMutation with no retry option (inherits the QueryClient default, which is 0/no-retry in both the test harness and the real app's queryClient.ts). shouldRetryStore returning true unconditionally for a 401 would otherwise retry forever within a single mutateAsync() call inside the drain's for-of loop, hanging the whole drain on the first 401 entry. useStoreBotGame() (with the predicate) remains exported for a future direct, user-triggered call site (e.g. a manual retry action)."
  - "Sentry.captureException is added nowhere in this file. The global MutationCache.onError (lib/queryClient.ts) already captures every TanStack mutation failure, including the drain's 422s, with tags: { source: 'tanstack-mutation' }. A dedicated 'mutation' test group renders useStoreBotGame() itself so knip recognizes it as a real (not dead) export, since nothing in this plan's production code calls it yet."

patterns-established:
  - "A queue-drain call site gets its OWN retry-less mutation; a general-purpose direct-action mutation keeps the retry predicate. Do not conflate the two — Plan 03/04's Bots.tsx mount-drain wiring should use useDrainPendingStore, not useStoreBotGame directly, for exactly this reason."

requirements-completed: [RESUME-02]

coverage:
  - id: D1
    description: "botsApi.storeGame POSTs to /bots/games with a StoreBotGameRequest whose six fields (game_uuid, pgn, user_color, bot_elo, play_style_blend, tc_preset) mirror app/schemas/bots.py's StoreBotGameRequest field-for-field, user_color as a closed 'white' | 'black' union (not a bare string)."
    requirement: "RESUME-02"
    verification:
      - kind: unit
        ref: "frontend/src/hooks/__tests__/useStoreBotGame.test.ts#mutation > useStoreBotGame calls botsApi.storeGame with the given request and resolves with its response"
        status: pass
    human_judgment: false
  - id: D2
    description: "tc_preset on the wire is toBackendTcStr(baseSeconds, incrementSeconds) (base-seconds, e.g. '300+3'), identical to the PGN's [TimeControl] header — never the lichess minutes-display preset."
    requirement: "RESUME-02"
    verification:
      - kind: unit
        ref: "frontend/src/hooks/__tests__/useStoreBotGame.test.ts#tc-preset (both tests) — REVERTED to a minutes-display preset, both went red, restored"
        status: pass
    human_judgment: false
  - id: D3
    description: "A queue entry is removed only on a confirmed 2xx (created:true or created:false both count as success) or a 422 (permanently-invalid PGN); it is kept on 401/5xx/network for the next visit. A mid-queue failure does not abort the rest of the drain, and an empty queue makes zero HTTP calls."
    requirement: "RESUME-02"
    verification:
      - kind: unit
        ref: "frontend/src/hooks/__tests__/useStoreBotGame.test.ts#drain (all 9 tests) — REVERTED to unconditional (finally-block) removal, the 401-keeps and 500-keeps tests (plus 4 others) went red, restored"
        status: pass
    human_judgment: false
  - id: D4
    description: "The drain never calls Sentry.captureException itself — the global MutationCache.onError already captures every mutation failure, including 422s."
    requirement: "RESUME-02"
    verification:
      - kind: unit
        ref: "frontend/src/hooks/__tests__/useStoreBotGame.test.ts#drain > never calls Sentry.captureException itself"
        status: pass
    human_judgment: false

duration: 40min
completed: 2026-07-13
status: complete
---

# Phase 170 Plan 02: StoreBotGame Client + Pending-Store Drain Loop Summary

**The frontend's first call site of the shipped `POST /bots/games` endpoint — `botsApi.storeGame`, `useStoreBotGame`, and a `useDrainPendingStore` loop that removes a queued finished game only on a confirmed 2xx or a permanently-invalid 422, keeping it on every retryable failure (401/5xx/network) for the next visit.**

## Performance

- **Duration:** ~40 min
- **Completed:** 2026-07-13
- **Tasks:** 2
- **Files modified:** 4 (1 modified, 3 created)

## Accomplishments
- `frontend/src/types/bots.ts`: `StoreBotGameRequest`/`StoreBotGameResponse` mirroring `app/schemas/bots.py` field-for-field, with `tc_preset`'s D-14-corrected base-seconds doc comment spelling out the mis-bucketing consequence of getting it wrong.
- `botsApi.storeGame` added inline to `frontend/src/api/client.ts`, copying `feedbackApi`'s exact grouped one-method shape.
- `frontend/src/hooks/useStoreBotGame.ts`: `toStoreRequest` (pure mapper), `shouldRetryStore` (pure D-13 retry predicate), `useStoreBotGame()` (the general-purpose mutation), and `useDrainPendingStore()` (the queue drain with its own retry-less mutation and the per-outcome remove/keep decision).
- 15 unit tests across `tc-preset`, `retry-predicate`, `drain`, and `mutation` groups, all passing; two REVERT PROOFs performed and confirmed.

## Task Commits

Each task was committed atomically:

1. **Task 1: StoreBotGame types + botsApi client** - `27d572a8` (feat)
2. **Task 2: useStoreBotGame mutation + the pending-store drain loop** - `12f19885` (feat)

**Plan metadata:** (this commit) — docs: complete plan

## Files Created/Modified
- `frontend/src/types/bots.ts` - new file: `StoreBotGameRequest`/`StoreBotGameResponse`, mirroring `app/schemas/bots.py`
- `frontend/src/api/client.ts` - added `botsApi` (one method: `storeGame`) inline, in its own `// ─── Bots API ───` section
- `frontend/src/hooks/useStoreBotGame.ts` - new file: `MAX_STORE_RETRIES`, `toStoreRequest`, `shouldRetryStore`, `useStoreBotGame`, `useDrainPendingStore`
- `frontend/src/hooks/__tests__/useStoreBotGame.test.ts` - new test file (15 tests: tc-preset, retry-predicate, drain, mutation)

## Decisions Made
- `tc_preset` reuses `toBackendTcStr(baseSeconds, incrementSeconds)` verbatim — no separate display-preset derivation function exists anywhere in this plan's code, per the RESEARCH-corrected D-14.
- `useDrainPendingStore` builds its own `useMutation({ mutationFn: botsApi.storeGame })` with no `retry` option, rather than calling `useStoreBotGame()` internally. This was a deviation from the plan's literal action text (which implied reusing `mutateAsync` from `useStoreBotGame()`), made because `shouldRetryStore` returning `true` unconditionally for a 401 makes a single `mutateAsync()` call retry forever with TanStack's default exponential backoff (capped at 30s per attempt, but never giving up) — inside the drain's `for...of` loop, this would hang the entire drain on the first 401 entry rather than settling and letting the `catch` branch decide "keep." The drain's real retry mechanism (per D-13 and RESEARCH.md's own closing paragraph: "the 'does this queue entry survive to the next page visit' decision belongs to the DRAIN LOOP, not to the mutation") is the next `/bots` mount, not an in-flight TanStack retry. `useStoreBotGame()` (with `shouldRetryStore` wired) is kept as the general-purpose export for a future direct call site.
- `shouldRetryStore` was extracted as a standalone exported function (rather than an inline arrow passed to `useMutation`'s `retry` option) so the plan's required "one separate test asserting the retry predicate itself returns `false` for 422 and `true` for 401" could be written as a plain function test, without needing to drive TanStack's actual retry timing.
- Added a `mutation` test group exercising `useStoreBotGame()` directly via `renderHook`. Without it, `useStoreBotGame` would be an unused export flagged by `knip` — this plan's scope doesn't yet wire either hook into `Bots.tsx` (that's Plan 03/04), so nothing in production code calls `useStoreBotGame()` yet, and a real test-file consumer was the correct way to keep it a legitimate exported artifact rather than dead code.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `useDrainPendingStore` given its own retry-less mutation instead of reusing `useStoreBotGame()`**
- **Found during:** Task 2, while writing the "keeps the entry on a 401" drain test
- **Issue:** The plan's action text describes `useDrainPendingStore` calling `mutateAsync` (implying reuse of `useStoreBotGame()`'s mutation, which carries `shouldRetryStore`). Because `shouldRetryStore` returns `true` unconditionally for a 401, wiring the drain through that mutation makes a single `await mutateAsync(...)` never settle for a persistently-401ing entry — TanStack keeps retrying with growing backoff indefinitely. Inside the drain's sequential `for...of` loop, this hangs the entire drain (and every subsequent queue entry) rather than letting the entry correctly settle into the "keep for next visit" branch.
- **Fix:** `useDrainPendingStore` constructs its own `useMutation<StoreBotGameResponse, Error, StoreBotGameRequest>({ mutationFn: botsApi.storeGame })` with no `retry` option, so it inherits the QueryClient's default (0/no-retry both in the test harness's `defaultOptions: { mutations: { retry: false } }` and the real app's `queryClient.ts`, which sets no `mutations` default at all — TanStack's own built-in default is 0). `useStoreBotGame()` remains exported, with `shouldRetryStore` wired, for a future direct call site.
- **Files modified:** `frontend/src/hooks/useStoreBotGame.ts`
- **Verification:** All 9 `drain` tests pass, including the 401-keeps and 500-keeps cases that would otherwise time out; REVERT PROOF 2 below confirms the removal-decision logic itself (not the mutation choice) is what's under test.
- **Committed in:** `12f19885` (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 bug fix — a genuine hang risk in the plan's literal reading, caught by writing the test before the implementation per TDD discipline)
**Impact on plan:** Necessary for correctness — an unfixed version would silently freeze the drain loop on the first logged-out visit with a pending game. No scope creep; `useStoreBotGame()` still exists exactly as the plan's artifact list requires.

## Issues Encountered
- Initial `toHaveBeenCalledWith(request)` assertion in the `mutation` test failed because TanStack Query's `mutationFn` receives a second internal context argument (`{ client, meta, mutationKey }`) beyond the variables — fixed by asserting on `mock.calls[0][0]` instead of the full call.
- The plan names the test file `useStoreBotGame.test.ts` (`.ts`, not `.tsx`); Vite's esbuild transform treats `.ts` files with the non-JSX `ts` loader, so the `QueryClientProvider` wrapper is built with `createElement` rather than JSX syntax.

## Revert Proofs

Per the plan's mutation-test discipline, each invariant below was ACTUALLY reverted, the named test(s) observed going red, and the mechanism restored + reconfirmed green.

1. **tc_preset base-seconds invariant** (`toStoreRequest`, `useStoreBotGame.ts`)
   - **Mechanism reverted:** changed `tc_preset: toBackendTcStr(entry.settings.baseSeconds, entry.settings.incrementSeconds)` to `` tc_preset: `${entry.settings.baseSeconds / 60}+${entry.settings.incrementSeconds}` `` (a minutes-display preset — the exact trap the corrected D-14 warns against).
   - **Tests that went red:** both `tc-preset` tests — `is base-seconds (toBackendTcStr output)...` (expected `'300+3'`, got `'5+3'`) and `maps every PendingStoreEntry field...` (expected `tc_preset: '300+3'`, got `'5+3'`).
   - **Restored and reconfirmed green:** yes (`npm test -- src/hooks/__tests__/useStoreBotGame.test.ts -t "tc-preset"` → 2 passed).

2. **Drain removal-on-exactly-two-outcomes invariant** (`useDrainPendingStore`'s try/catch, `useStoreBotGame.ts`)
   - **Mechanism reverted:** replaced the try/catch's conditional removal with `try { await mutateAsync(...); } finally { removePendingStore(ownerKey, entry.gameUuid); }` — unconditional removal on any outcome.
   - **Tests that went red:** 6 of 9 `drain` tests, including the two the plan specifically names — `keeps the entry on a 401 (logged out — retry once authenticated)` and `keeps the entry on a 500` (both now removed the entry when they should have kept it) — plus `removes the entry on a 422`, `keeps the entry on a network error`, the mid-queue-failure test, and the Sentry-zero-calls test (all failed with unhandled-rejection errors surfacing through the `finally` block rather than being caught).
   - **Restored and reconfirmed green:** yes (`npm test -- src/hooks/__tests__/useStoreBotGame.test.ts -t "drain"` → 9 passed; full file → 15 passed).

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- `botsApi.storeGame`, `useStoreBotGame`, `toStoreRequest`, and `useDrainPendingStore` are ready for Plan 03/04's `Bots.tsx` mount-effect wiring (D-13's "drain the queue on `/bots` mount, before the gate renders"). The mount effect should call `useDrainPendingStore(ownerKey).drain` — NOT `useStoreBotGame()` directly — per this plan's documented deviation.
- `StoreBotGameRequest`/`StoreBotGameResponse` are ready for Plan 03/04's `finalizeGame` enqueue path (Plan 01's `botPendingStore.ts` already accepts a `PendingStoreEntry` shaped for `toStoreRequest` to consume unchanged).
- No blockers. Full frontend suite (1972 tests across 154 files), `tsc -b`, `eslint`, and `knip` all green after this plan.

---
*Phase: 170-localstorage-resume*
*Completed: 2026-07-13*

## Self-Check: PASSED

All 4 files (types/bots.ts, hooks/useStoreBotGame.ts, hooks/__tests__/useStoreBotGame.test.ts,
170-02-SUMMARY.md) verified present on disk; both task commit hashes (`27d572a8`, `12f19885`)
verified present in git log.
