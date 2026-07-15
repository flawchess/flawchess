---
phase: 171-bots-page-setup-screen-nav
plan: 07
subsystem: ui
tags: [react, typescript, tanstack-query, localStorage, vitest, rtl]

# Dependency graph
requires:
  - phase: 171-06
    provides: "BotsPage's setup/game phase switch, BotsGame.settings/onNewGame props — the D-14 stub fully replaced"
  - phase: 170
    provides: "botPendingStore.ts (enqueuePendingStore/removePendingStore/listPendingStore) + useStoreBotGame.ts (useStoreBotGame/useDrainPendingStore/toStoreRequest/shouldRetryStore) — the localStorage durability queue and its drain loop, both consumed unchanged by this plan"
  - phase: 167
    provides: "POST /bots/games (idempotent on game_uuid) — the store endpoint this plan's finish-time mutation targets"
provides:
  - "A finish-time useStoreBotGame().mutate() effect in BotsGame, fired once per gameUuid on game.outcome transitioning null -> non-null"
  - "removePendingStore(ownerKey, gameUuid) called from the mutation's onSuccess — the double-POST dedupe fix for the next /bots mount's drain"
  - "storeSucceeded/isGuest threaded through BotsGame -> GamePanel/GameResultDialog -> GameResultStrip"
  - "GameResultDialog/GameResultStrip: a 'Saved to your Library' Link (react-router, /library/games) rendered only on storeSucceeded===true, plus a guest-only not-auto-analyzed caveat"
  - "BOT_GAME_SAVED_COPY / GUEST_NOT_AUTO_ANALYZED_COPY exported from GameResultDialog.tsx, imported by GameResultStrip.tsx for byte-identical copy on both surfaces"
affects: []

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Fire-once-per-gameUuid effect via a ref latch set BEFORE the async mutate() call (storedGameUuidRef), mirroring outcomeRef's first-wins shape in useBotGame.ts — prevents a re-render during the in-flight mutation from double-firing"
    - "Module-mocking botsApi (not the consuming hooks) in a page-level RTL test to exercise two hooks (useStoreBotGame + useDrainPendingStore) that share a network boundary and a localStorage queue, rather than stubbing either hook individually"

key-files:
  created:
    - frontend/src/components/bots/__tests__/GameResultDialog.test.tsx
    - frontend/src/components/bots/__tests__/GameResultStrip.test.tsx
  modified:
    - frontend/src/pages/Bots.tsx
    - frontend/src/components/bots/GameResultDialog.tsx
    - frontend/src/components/bots/GameResultStrip.tsx
    - frontend/src/pages/__tests__/Bots.test.tsx

key-decisions:
  - "GameResultStrip's outer container restructured from a single flex-wrap row to a flex-col wrapping two rows (the existing title+buttons row, then the new save-link row) — the row-vs-column split was implicit in the plan's 'below the button row' instruction but not spelled out; kept the original row's classes unchanged inside the new wrapper"
  - "Link color: text-brand-brown-light hover:text-brand-brown-highlight transition-colors (the established FlawCard.tsx/GameCard.tsx/LibraryGameCard.tsx link convention), not a literal 'theme.ts token' — no such link-color export exists in lib/theme.ts (that file holds chart/WDL/severity color constants, not Tailwind link classes). The CSS custom properties backing these Tailwind utilities DO live in index.css's :root block, which is the project's real color-token source for this class family; the acceptance grep for hardcoded hex/bg-[] still passes"
  - "Bots.test.tsx's beforeEach now defaults botsApi.storeGame to reject(500) — the D-13 mount-drain effect is no longer a no-op (Plan 06 stubbed useDrainPendingStore away entirely); an unconfigured mock resolving `undefined` would be silently treated as a 2xx by TanStack Query and would have made the pre-existing 'discard' test's seeded pending-store fixture vanish via the ordinary drain, unrelated to discard itself. Tests that DO care about the store override the mock explicitly"
  - "V-15/failure tests enqueue the pending-store entry via enqueuePendingStore INSIDE the same act() block as setOutcome/setPgn (mirroring finalizeGame's real atomicity), rather than pre-seeding localStorage before renderBots() — pre-seeding before the game starts let BotsPage's OWN initial mount-drain consume the entry before the game even finished, corrupting the call-count assertions the describe block exists to pin"
  - "Store-FAILURE test asserts the remount's drain call count strictly increases (not a hardcoded '2') — shouldRetryStore bounds a 500 at MAX_STORE_RETRIES=2 in-flight retries, so the finish-time attempt alone makes 3 real botsApi.storeGame calls before settling as failed (verified: `await waitFor(... toHaveBeenCalledTimes(3))`); a hardcoded '2' from the plan's simplified narrative would not hold against the real bounded-retry behavior already shipped in useStoreBotGame.ts"

requirements-completed: [PLAY-10]

coverage:
  - id: D1
    description: "A finished bot game POSTs to /bots/games immediately (while the user is still on the result screen), calling botsApi.storeGame exactly once per gameUuid — verified via a fire-once ref latch, not merely an effect-deps guard"
    requirement: "PLAY-10"
    verification:
      - kind: unit
        ref: "frontend/src/pages/__tests__/Bots.test.tsx#store on finish (D-21) > POSTs exactly once when outcome transitions null -> finished, with a matching game_uuid (V-14)"
        status: pass
    human_judgment: false
  - id: D2
    description: "REGRESSION CLOSED (V-15): a successful finish-time store removes the localStorage pending-store entry (onSuccess-only), so a subsequent /bots mount's drain makes zero additional POSTs for the same game — proven by an explicit RED-then-GREEN mutation transcript (see below), not by grep/symbol-presence"
    requirement: "PLAY-10"
    verification:
      - kind: unit
        ref: "frontend/src/pages/__tests__/Bots.test.tsx#store on finish (D-21) > finish -> store succeeds -> remount does NOT re-POST (V-15, the double-POST regression)"
        status: pass
    human_judgment: false
  - id: D3
    description: "A FAILED finish-time store (401/5xx/network) leaves the pending-store entry intact — the dedupe (onSuccess-only removal) does not cannibalize the offline/401-retry durability fallback; the next mount's drain still attempts it"
    requirement: "PLAY-10"
    verification:
      - kind: unit
        ref: "frontend/src/pages/__tests__/Bots.test.tsx#store on finish (D-21) > a FAILED finish-time store leaves the pending entry intact for the next mount to retry"
        status: pass
    human_judgment: false
  - id: D4
    description: "'Saved to your Library' link + guest not-auto-analyzed caveat render strictly gated on storeSucceeded===true (never idle/pending/error), mirrored identically on GameResultDialog and GameResultStrip"
    requirement: "PLAY-10"
    verification:
      - kind: unit
        ref: "frontend/src/components/bots/__tests__/GameResultDialog.test.tsx#GameResultDialog — Saved to Library + guest caveat (V-16)"
        status: pass
      - kind: unit
        ref: "frontend/src/components/bots/__tests__/GameResultStrip.test.tsx#GameResultStrip — Saved to Library + guest caveat (V-16)"
        status: pass
    human_judgment: false
  - id: D5
    description: "'Analyze this game' keeps its instant client-side buildAnalysisLineUrl behavior on both surfaces, never gated on the store's status (V-17)"
    requirement: "PLAY-10"
    verification:
      - kind: unit
        ref: "frontend/src/components/bots/__tests__/GameResultDialog.test.tsx#GameResultDialog — Analyze/New-game unaffected by the store (V-17)"
        status: pass
      - kind: unit
        ref: "frontend/src/components/bots/__tests__/GameResultStrip.test.tsx#GameResultStrip — Analyze/New-game unaffected by the store (V-17)"
        status: pass
      - kind: other
        ref: "git diff <base>..HEAD -- frontend/src/components/bots/GameResultDialog.tsx | grep -E '^[+-].*onAnalyze' (no output — the Analyze handler's wiring is byte-unchanged)"
        status: pass
    human_judgment: false

duration: 55min
completed: 2026-07-14
status: complete
---

# Phase 171 Plan 07: Store-on-Finish + Saved-to-Library Summary

**Closed the D-21 CONTEXT amendment: a finished bot game now POSTs to `/bots/games` the instant it ends (via a fire-once `useStoreBotGame().mutate()` effect keyed on `game.outcome`), and the confirmed save surfaces as a "Saved to your Library" link — plus a guest-only not-auto-analyzed caveat — on both `GameResultDialog` and `GameResultStrip`, with the resulting next-mount double-POST regression closed by an `onSuccess`-only `removePendingStore` call and pinned by an explicit RED-then-GREEN mutation proof.**

## Performance

- **Duration:** ~55 min
- **Completed:** 2026-07-14T12:33:29Z
- **Tasks:** 3 completed
- **Files modified:** 7 (4 modified, 2 new test files, this SUMMARY.md)

## Accomplishments

- `BotsGame` (`Bots.tsx`) gained a `useStoreBotGame()` instance and a `storedGameUuidRef` fire-once latch: the moment `game.outcome` transitions `null` -> a finished outcome (and `game.pgn` is non-null), it calls `store.mutate(toStoreRequest({...}), { onSuccess: () => removePendingStore(ownerKey, game.gameUuid) })` exactly once for that `gameUuid`. `finalizeGame`'s `enqueuePendingStore` call site (`useBotGame.ts`) and the `BotsPage`-level `useDrainPendingStore` mount effect are both byte-for-byte untouched (`git diff --exit-code` confirms).
- The double-POST regression D-21 explicitly warns about is closed structurally: `removePendingStore` fires ONLY inside the mutation's `onSuccess`, so a failed store (401/5xx/network) leaves the queue entry for the next mount's drain to retry, while a successful store empties the queue before that drain ever runs.
- `storeSucceeded`/`isGuest` are threaded from `BotsPage`'s single `useUserProfile()` call, through `BotsGame`, into both `GameResultDialog` and `GameResultStrip` (the latter via `GamePanelProps`).
- `GameResultDialog.tsx` exports `BOT_GAME_SAVED_COPY` ("Saved to your Library") and `GUEST_NOT_AUTO_ANALYZED_COPY` (the verbatim UI-SPEC guest string); `GameResultStrip.tsx` imports both so the two surfaces render byte-identical text. Both surfaces render the save link (a `react-router-dom` `Link` to `/library/games`, styled `text-brand-brown-light hover:text-brand-brown-highlight`) strictly gated on `storeSucceeded === true`, with the guest caveat as an additional gate on `isGuest === true`. "Analyze this game" / "New game" are completely unmodified.
- 3 test files (1 extended, 2 new), 25 new/updated assertions total, cover V-14 (fires once, matching `game_uuid`), V-15 (the load-bearing double-POST regression, proven via an explicit RED-then-GREEN mutation transcript below), the store-FAILURE durability case, and V-16/V-17 (render gating + Analyze-button independence) mirrored identically across the dialog and the strip.

## Task Commits

Each task was committed atomically:

1. **Task 1: Store the finished game on finish, and dedupe against the next mount's drain (D-21, V-14, V-15)** - `2d04fcaa` (feat)
2. **Task 2: "Saved to your Library" + the guest caveat on both result surfaces (D-20, SC4)** - `783f3cba` (feat)
3. **Task 3: Tests — no double-POST (V-15), store-fires-on-finish (V-14), render gating (V-16, V-17)** - `81bf37d0` (test)

_Note: no TDD RED/GREEN split at the task-commit level — Task 1 and Task 2's `<behavior>` specs were directly implementable against the already-shipped `useStoreBotGame`/`botPendingStore` contracts (mirroring Plan 06's own note on this). Task 3's own internal RED/GREEN discipline is the V-15 mutation proof documented below, which IS a real revert-and-confirm cycle, not a normal TDD test-first pass._

## Mutation proof (D-21 double-POST / V-15)

Per the plan's explicit instruction and project memory (`feedback_mutation_test_gap_closures`: never accept grep/symbol-presence as proof of a gap fix), the fix was proven by literally removing it and confirming the test goes RED, then restoring it and confirming GREEN.

**RED — `removePendingStore(ownerKey, game.gameUuid)` replaced with `() => {}` in `Bots.tsx`'s `onSuccess`:**

```
$ npx vitest run src/pages/__tests__/Bots.test.tsx -t "double-POST"

 FAIL  src/pages/__tests__/Bots.test.tsx > store on finish (D-21) > finish -> store succeeds -> remount does NOT re-POST (V-15, the double-POST regression)
AssertionError: expected 1 to be +0 // Object.is equality

 Test Files  1 failed (1)
      Tests  1 failed | 10 skipped (11)
```

The failing assertion is `expect(pendingEntryCount()).toBe(0)` (line ~470) — the queue entry never clears without the real `onSuccess` removal, so the test fails before even reaching the remount/re-POST check. That is itself sufficient proof the test is load-bearing: without the fix, the localStorage state the whole regression test depends on never reaches the state the test assumes, so the test cannot pass.

**GREEN — `removePendingStore(ownerKey, game.gameUuid)` restored:**

```
$ npx vitest run src/pages/__tests__/Bots.test.tsx -t "double-POST"

 Test Files  1 passed (1)
      Tests  1 passed | 10 skipped (11)
```

## Files Created/Modified

- `frontend/src/pages/Bots.tsx` - `BotsGame` gains `useStoreBotGame()` + the fire-once store-on-finish effect + `storedGameUuidRef`; `BotsGameProps`/`GamePanelProps` gain `isGuest`/`storeSucceeded`; `BotsPage` computes `isGuest` once and passes it to both `BotsGame` mounts
- `frontend/src/components/bots/GameResultDialog.tsx` - `storeSucceeded`/`isGuest` props; the "Saved to your Library" link + guest caveat row below `DialogFooter`; exports `BOT_GAME_SAVED_COPY`/`GUEST_NOT_AUTO_ANALYZED_COPY`
- `frontend/src/components/bots/GameResultStrip.tsx` - same props, same row below the button row; imports the shared copy consts; outer container restructured to `flex-col` to stack the new row beneath the existing title+buttons row
- `frontend/src/pages/__tests__/Bots.test.tsx` - `useStoreBotGame`/`useDrainPendingStore` are no longer mocked (real hooks against a mocked `botsApi.storeGame`); the fake `useBotGame` mock gains a settable `pgn`; new `describe('store on finish (D-21)')` block (4 tests: V-14 fire-once, pgn-null guard, V-15 regression, store-failure durability)
- `frontend/src/components/bots/__tests__/GameResultDialog.test.tsx` - NEW. V-16 render-gating (4 combinations) + V-17 Analyze/New-game independence (3 cases)
- `frontend/src/components/bots/__tests__/GameResultStrip.test.tsx` - NEW. Mirrors the dialog suite case-for-case

## Decisions Made

- Used the established `text-brand-brown-light hover:text-brand-brown-highlight transition-colors` link class (matching `FlawCard.tsx`/`GameCard.tsx`/`LibraryGameCard.tsx`) rather than a literal `theme.ts` export — no link-color token exists in `lib/theme.ts`; the CSS custom properties backing this Tailwind class family live in `index.css`, which is this project's actual color-token source for link styling
- Restructured `Bots.test.tsx`'s mocking strategy per the plan's own stated preference: real `useStoreBotGame`/`useDrainPendingStore` hooks against a module-mocked `botsApi.storeGame`, not a stubbed drain hook — required to prove the finish-time store and the mount-drain interact correctly through the same localStorage queue (the actual point of V-15)
- Adjusted the store-FAILURE test's exact call-count assertion from the plan's literal "becomes 2" to "strictly increases from the post-finish count" — `shouldRetryStore`'s real bounded-retry behavior (already shipped in `useStoreBotGame.ts`, `MAX_STORE_RETRIES=2`) makes a single failed finish-time attempt cost 3 real HTTP calls, not 1, before the remount's drain adds one more

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Removed an unnecessary `eslint-disable-next-line react-hooks/exhaustive-deps` comment, then re-added it once lint proved it necessary**
- **Found during:** Task 1 verification
- **Issue:** Initially added the comment defensively; `npx tsc -b`/`npm run lint` showed the deps array was already exhaustive without it, making the directive an unused-disable warning risk. Removed it, then `npm run lint` reported a genuine `react-hooks/exhaustive-deps` warning (wanting the whole `store` object in deps, which would defeat the "depend on `store.mutate`, not `store`" design), so it was re-added with rationale in the adjacent comment.
- **Fix:** Kept the `eslint-disable-next-line` immediately above the effect's deps array, matching the established convention already used in `Analysis.tsx`/`Openings.tsx`/`Endgames.tsx`.
- **Files modified:** `frontend/src/pages/Bots.tsx`
- **Verification:** `npm run lint` clean (0 errors, only pre-existing unrelated `coverage/` warnings).
- **Committed in:** `2d04fcaa` (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 — a lint-directive correction, no behavior change).
**Impact on plan:** No scope creep.

### Note on plan acceptance-criteria grep precision

Several of the plan's literal `grep -c`/`grep -rc` acceptance criteria count MATCHING LINES, not call sites, and don't account for pre-existing doc-comment references:
- `grep -c 'useDrainPendingStore' frontend/src/pages/Bots.tsx == 1` — the baseline (pre-Plan-07) file already had this at 2 (one `import` line, one call-site line); this is unaffected by this plan and was verified unchanged.
- `grep -c 'removePendingStore' frontend/src/pages/Bots.tsx == 1` — real count is 3 (1 import, 1 explanatory comment, 1 actual call inside `onSuccess`); manually verified the actual call site is singular and correctly placed inside `onSuccess`.
- `grep -rc 'enqueuePendingStore' frontend/src/ == 1 non-test call site` — a plain `grep -rn 'enqueuePendingStore'` returns several comment-line hits across `useBotGame.ts`/`botPendingStore.ts`; refining to `grep -rn 'enqueuePendingStore('` (matching the call/definition syntax) isolates exactly 2 hits — the one real call site (`useBotGame.ts:617`) and the function's own definition (`botPendingStore.ts:94`, not a "call site"). Confirmed structurally unchanged.

None of these represent an actual violation of the underlying invariants (verified manually above); documenting the discrepancy so a future grep-based audit isn't misled by the literal numbers.

## Issues Encountered

None beyond the mocking-strategy corrections already documented in "Decisions Made" — both were resolved within Task 3 before any commit, not after.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

This is the last plan in Phase 171. Full CLAUDE.md pre-merge gate run and green: `ruff format`/`ruff check --fix`/`ty check` clean, `pytest -n auto -x` 3252 passed/18 skipped, frontend `npm run lint`/`npm test -- --run` (2113 tests, 164 files) / `npx tsc -b` / `npm run knip` all clean. Phase 171 (and the v2.3 Bot Play milestone it closes) is ready for `/gsd-ship` or milestone-close review — no blockers.

---
*Phase: 171-bots-page-setup-screen-nav*
*Completed: 2026-07-14*

## Self-Check: PASSED

All 6 created/modified source+test files verified present on disk (`Bots.tsx`, `GameResultDialog.tsx`, `GameResultStrip.tsx`, `GameResultDialog.test.tsx`, `GameResultStrip.test.tsx`, `Bots.test.tsx`) plus this SUMMARY.md; all 3 task commits (`2d04fcaa`, `783f3cba`, `81bf37d0`) verified present in git log.
