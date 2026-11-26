---
phase: 255-feature-discovery-dot-route
fixed_at: 2026-11-15T22:07:29Z
review_path: .planning/phases/255-feature-discovery-dot-route/255-REVIEW.md
iteration: 1
findings_in_scope: 4
fixed: 4
skipped: 0
status: all_fixed
---

# Phase 255: Code Review Fix Report

**Fixed at:** 2026-11-15T22:07:29Z
**Source review:** .planning/phases/255-feature-discovery-dot-route/255-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 4 (WR-01 to WR-04; the Info findings IN-01 to IN-05 were out of scope and are untouched)
- Fixed: 4
- Skipped: 0

WR-01, WR-02 and WR-03 are logic fixes. Their tests prove the cases below, but the design choices
listed under "Decisions for the owner" need a human look before the phase moves on.

## Fixed Issues

### WR-01: A failed `done` POST is never retried in the session

**Status:** fixed: requires human verification
**Files modified:** `frontend/src/components/feature-route/FeatureRouteRecorder.tsx`, `frontend/src/components/feature-route/__tests__/FeatureRouteRecorder.test.tsx`
**Commit:** a571af85c
**Applied fix:** The sent-key set became a map of key to send time. A key blocks its request for
`ROUTE_WRITE_RESEND_COOLDOWN_MS` (10 s) and then expires, so a write that failed is sent again the
next time the effect plans it (a later visit or a profile change). It is not retried at once.

This differs from the review's sketch (return the mutation promise and delete the key in `.catch`).
The expiry needs no change to the hook's return type or to the click handlers, and it is the same
mechanism that fixes WR-03.

**Regression test:** `(h) a failed done POST is retried on a later visit, not at once`.
- Before the fix: failed at `expect(postCount(doneBots)).toBe(2)`, received 1 (the review's repro).
- Mutation, cooldown set to 0: fails at the "revisit right after the failure" assertion, expected 1, received 2. So the test pins both halves (retry later, no immediate resend).
- Mutation, keys never expire (`if (sentAt != null) continue`): fails.

### WR-02: A route write cancels an in-flight profile refetch and marks the cache fresh

**Status:** fixed: requires human verification
**Files modified:** `frontend/src/hooks/useRecordFeatureRoute.ts`, `frontend/src/components/feature-route/__tests__/FeatureRouteRecorder.test.tsx`
**Commit:** de1f2eaea
**Applied fix:** `onMutate` records, per QueryClient (a module-level `WeakSet`, shared by the three
hook instances), that a profile refetch is owed when the profile is being fetched or is stale.
`onSettled` invalidates the profile once the last queued route write has settled, on success and on
failure. The cancel and the optimistic patch are unchanged.

Two differences from the review's sketch: the flag is per client instead of one module boolean (no
leak between clients or tests), and a profile that is stale but not yet fetching also counts. Without
that second part the patch still marked an already stale profile fresh for another 5 minutes.

**Regression tests** (all failed before the fix):
- `(i) repeats a profile refetch (invalidate) that the write cancelled`: the review's repro, game count stayed 0.
- `(i) ... (refetch)`: same with a fetch on a profile that still counts as fresh.
- `(j) refetches a profile that was already stale instead of marking it fresh`.
- `(k) waits for the last queued write before it refetches`.

Mutations, each restored afterwards:

| Mutation | Tests that fail |
|----------|-----------------|
| Remove the `isFetching` check | (i) refetch |
| Remove the `isStale` check | (j) |
| Remove the `invalidateQueries` call | (i) invalidate, (i) refetch, (j) |
| Remove the last-write guard in `onSettled` | (k) |

### WR-03: The stamp-signature reset defeats the sent-key guard

**Status:** fixed: requires human verification
**Files modified:** `frontend/src/components/feature-route/FeatureRouteRecorder.tsx`, `frontend/src/components/feature-route/__tests__/FeatureRouteRecorder.test.tsx`
**Commit:** 674854515
**Applied fix:** The signature-driven forget is removed (`currentSignature`, `signatureRef`). No state
change clears a key any more: each request (action plus step) is sent at most once per cooldown,
whatever the server answers. The docstring now describes exactly that, including that there is no
timer and a resend needs a new effect run.

This differs from the review's sketch (keep the forget, add a cap of 3 sends per key). A cap would
also have stopped the legitimate re-stamp after the third delete-all-games in one session, and would
have counted WR-01 retries against the same cap. With expiring keys the forget is not needed: the
re-stamp after delete-all-games works because the old key has expired.

**Regression tests:**
- `(l) a current stamp the server does not confirm is not re-POSTed at network speed`: a server that answers every write after 30 ms with the unchanged state. Before the fix: expected 1, received 151 `current:train` POSTs. Mutation, cooldown set to 0: received 152.
- `(m) a stamp removed by delete-all-games is set again on unlock in the same session (D-23)`: guards the locked decision. It passed before the fix (the forget did the job) and passes after (expiry does). Mutation, keys never expire: fails.

### WR-04: Recorder test (d) cannot fail on "posts nothing"

**Status:** fixed
**Files modified:** `frontend/src/components/feature-route/__tests__/FeatureRouteRecorder.test.tsx`
**Commit:** d925e7fb4
**Applied fix:** Test (d) now waits for the loaded profile to render (the probe shows a profile
field), flushes pending effects and writes, then asserts. It runs on `/library/games` instead of
`/library/import`: there an empty route would show the dot on the Import subtab and stamp `import`,
so the "no dot" half can fail too (on `/library/import` it could not).

**Mutation evidence:**
- Old test, with the recorder and the write hook treating a loaded `feature_route: null` as an empty route (the review's mutation): 14 of 14 passed, confirming the finding.
- New test, same mutation: (d) fails on `expect(apiPost).not.toHaveBeenCalled()`, 1 call.
- New test, read hook (`useRouteDotPlacement`) falling back to an empty route: (d) fails, expected `none`, received `subtab:library-import`.
- All mutated sources were restored from copies; the committed diff for this finding touches the test file only.

## Decisions for the owner

1. **Cooldown value.** `ROUTE_WRITE_RESEND_COOLDOWN_MS = 10_000` is my choice. It bounds any POST
   loop to one request per key per 10 s, and only when something re-runs the effect.
2. **Retry is trigger-based, not timed.** After a failed `done`, the write goes out again on the
   first effect run 10 s or more later (navigation or a profile change). A user who returns to the
   page within 10 s and stays there is not retried until the next visit. A timer would close that
   gap at the cost of periodic resends against a server that keeps refusing.
3. **D-23 re-stamp, one narrow change.** If a step is stamped, all games are deleted, and a
   re-import unlocks the nav again within 10 s of that stamp, the re-stamp waits for the next effect
   run after the cooldown. The dot shows in the meantime; only the 3-day clock starts later. Before
   this fix the re-stamp was immediate. D-23 itself (no stamp, skip or dot while the first unresolved
   step is locked) is unchanged and still covered by test (g).
4. **One extra profile GET** after a route write when the profile was stale or being fetched.
5. **Not changed:** the 255-04 summary still says a no-op keeps the sent keys. The review flagged
   that sentence; planning documents were outside this fix.

## Verification

All gates ran in the main checkout on `gsd/phase-255-feature-discovery-dot-route` (no worktree, as
instructed by the orchestrator), from `frontend/`, after the last fix commit:

| Gate | Result |
|------|--------|
| `npm run lint` | exit 0, no output |
| `npm run build` (`tsc -b` + vite) | exit 0 |
| `npm test -- --run` | `Test Files  367 passed (367)`, `Tests  6453 passed (6453)` |
| `npm run knip` | exit 0, two configuration hints that were already there, no findings |

The recorder test file went from 7 to 14 tests. No backend file was touched. `.planning/state.json`
and the untracked `reports/` files were not staged.

---

_Fixed: 2026-11-15T22:07:29Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
