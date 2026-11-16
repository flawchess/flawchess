---
phase: 255-feature-discovery-dot-route
reviewed: 2026-11-15T21:47:05Z
depth: standard
files_reviewed: 35
files_reviewed_list:
  - alembic/versions/20261115_180000_c3f8e2a6d255_phase_255_feature_route_seed.py
  - app/repositories/feature_route_repository.py
  - app/repositories/game_repository.py
  - app/routers/users.py
  - app/schemas/feature_route.py
  - app/schemas/users.py
  - app/services/feature_route_service.py
  - tests/test_feature_route.py
  - tests/test_migration_255_feature_route_seed.py
  - frontend/src/App.tsx
  - frontend/src/lib/featureRoute.ts
  - frontend/src/lib/retiredLocalStorage.ts
  - frontend/src/lib/theme.ts
  - frontend/src/hooks/useFeatureRoute.ts
  - frontend/src/hooks/useRecordFeatureRoute.ts
  - frontend/src/components/feature-route/FeatureRouteRecorder.tsx
  - frontend/src/components/feature-route/RouteDot.tsx
  - frontend/src/components/openings/stats/OpeningColorSwitch.tsx
  - frontend/src/components/train/TrainStartScreen.tsx
  - frontend/src/components/train/TrainSubnav.tsx
  - frontend/src/pages/Openings.tsx
  - frontend/src/pages/Train.tsx
  - frontend/src/pages/library/LibraryPage.tsx
  - frontend/src/pages/openings/OpeningsDesktopSidebar.tsx
  - frontend/src/pages/openings/OpeningsMobileBoardPanel.tsx
  - frontend/src/pages/openings/useSidebarState.ts
  - frontend/src/types/users.ts
  - frontend/src/App.test.tsx
  - frontend/src/components/feature-route/__tests__/FeatureRouteRecorder.test.tsx
  - frontend/src/components/train/__tests__/TrainStartScreen.test.tsx
  - frontend/src/lib/__tests__/featureRoute.test.ts
  - frontend/src/lib/__tests__/retiredLocalStorage.test.ts
  - frontend/src/pages/__tests__/Openings.render.test.tsx
  - frontend/src/pages/__tests__/Train.subnav.test.tsx
  - frontend/src/pages/library/__tests__/LibraryPage.reroute.test.tsx
findings:
  critical: 0
  warning: 4
  info: 5
  total: 9
  necessity: 0
status: issues_found
---

# Phase 255: Code Review Report

**Reviewed:** 2026-11-15T21:47:05Z
**Depth:** standard
**Files Reviewed:** 35
**Status:** issues_found

## Summary

Reviewed the backend route state (seed migration, guarded SQL transitions, service, router), the
frontend arbiter, recorder, write hook and every dot render site, plus the tests as evidence.

The backend is sound. I found no defect in the four SQL transitions, the SKIP guard, the
delete-all-games hook or the seed migration. All four Warnings are in the frontend write path
(`FeatureRouteRecorder` and `useRecordFeatureRoute`) and in one recorder test. No Critical findings.

How the findings were checked:

- Backend: `uv run pytest tests/test_feature_route.py tests/test_migration_255_feature_route_seed.py`
  gives 27 passed. Alembic has one head (`c3f8e2a6d255`).
- Frontend: WR-01, WR-02, WR-03 and WR-04 were each reproduced by running vitest in a scratch copy
  of `frontend/src` outside the repository (probe tests and mutations). No repository file was
  changed. Three other suspicions were dropped after the same check: recorder tests (c), (e) and
  (g) do fail when their guard is removed.

Not checked: production `users` row count (relevant to claim 4), and real-device behaviour. The
suggested fixes below are sketches and were not run.
The necessity reference was read; no necessity findings. `.claude/skills/` holds only operational
skills (benchmarks, db-report, deploy, parallel-worktree, tactic-tagger-report), none with review rules.

### Verdict on the nine claims

| # | Claim | Verdict | Evidence |
|---|-------|---------|----------|
| 1 | Guarded SQL transitions are atomic, touch only `feature_route`, handle `{}` / absent / corrupt | Holds | One `UPDATE ... RETURNING` per transition, `prompt_state \|\| jsonb_build_object(key, ...)` replaces only that key (`feature_route_repository.py:43-114`). Absent key and absent `steps` are covered by `coalesce` (`:46-48`, `:67`, `:85-87`). `prompt_state` cannot be NULL (`app/models/user.py:129-131`). A corrupt value makes the returned object fail validation and the service rolls back (`feature_route_service.py:116-122`, test `tests/test_feature_route.py:583-609`). Two caveats: atomicity under concurrency rests on Postgres READ COMMITTED semantics, not on the test (IN-05); a hand-corrupted non-integer `current.since_days` would make the SKIP cast raise a 500 (`feature_route_repository.py:95-97`), which the shipped client cannot reach because the profile returns `null` for such a row. |
| 2 | SKIP enforces `since_days + 3` server-side, only for the stored `current`; impersonation never writes | Holds | Guard at `feature_route_repository.py:92-97`; active days are counted server-side (`feature_route_service.py:53-63`, `:86-89`); impersonation returns before any write (`feature_route_service.py:106-107`, `app/routers/users.py:275-285`). Tests `tests/test_feature_route.py:339-371`, `:399-421`, `:482-506`. CURRENT accepts any unresolved step, see IN-02. |
| 3 | `delete_all_games_for_user` clears `current` in the caller's transaction, never writes `feature_route: null`, never touches rows without the key | Holds | Same session, no commit (`app/repositories/game_repository.py:321-323`); guard `current IS NOT NULL` (`feature_route_repository.py:107-114`). Tests `tests/test_feature_route.py:627-700`. The guest purge and the reimport script inherit it. |
| 4 | Seed migration marks every existing user done without a dot, idempotent, correct downgrade, safe on a large table, keeps other keys | Holds, one open point | `c3f8e2a6d255:51-60` (seed, `WHERE ... IS NULL` guard, `\|\|` merge), `:70-71` (downgrade). It is one UPDATE over the whole table inside the migration transaction, with no batching. That is fine for a small `users` table (non-key update, so no FK lock conflict; the subquery runs once). I did not check the production row count. |
| 5 | Arbiter: at most one dot, D-23 pause, expiry, no off-by-one | Holds | `frontend/src/lib/featureRoute.ts:166-176` (first unresolved step, locked gives no candidate), `:189-193` (`activeDays - since_days >= 3`, same rule as the SQL), `:201-210` (one placement), `:276-293` (no stamp, skip or advance while locked). A step stamped on active day N shows on N, N+1, N+2 and is skipped on N+3 on both sides. |
| 6 | Recorder: no storms or loops, no duplicate POSTs, sane on failure, re-stamps after delete-all | Partly fails | Normal flow is correct (one POST per request across re-renders and route changes; re-stamp after delete-all works because `Import.tsx:394` invalidates the profile). Failure and race paths are not: WR-01, WR-02, WR-03. |
| 7 | Stale `current` after the last step | Harmless | See IN-01. |
| 8 | testids, no hand-written dot markup, no `useUserFlag` leftovers | Holds | `RouteDot` requires `testid` (`RouteDot.tsx:14-19`) and every call site passes one. The remaining `animate-ping` spans are the brown filter-modified dots, not route dots (`Openings.tsx:530`, `Endgames.tsx:152`, `OpeningsDesktopSidebar.tsx:81`, `FilterModifiedDot.tsx:60`). No code imports `useUserFlag`; only comments mention it (IN-04). |
| 9 | Sentry rules | Holds | `feature_route_service.py:30-34`, `:48-50`, `:116-122` capture with a constant message and the user id in context. The router has no `except`. |

## Narrative Findings (AI reviewer)

## Warnings

### WR-01: A failed `done` POST is never retried in the session, so the dot can come back and stay

**File:** `frontend/src/components/feature-route/FeatureRouteRecorder.tsx:35-46`, `frontend/src/hooks/useRecordFeatureRoute.ts:51-65`
**Issue:** The recorder adds `done:<step>` to `sentRef` before the POST and never removes `done:` keys (`:38`). The mutation has no `onError`, so a failed POST (network blip, 5xx) leaves the optimistic "done" in the cache and the key in the ref. When the profile next refetches (5 minute stale time, window focus, any invalidation), the server state returns with the step unresolved and the dot moves back to that step. Visiting the page again plans `done:<step>`, finds the key and sends nothing. The dot then stays on a page the user has opened (against D-15) until a full reload or the 3-active-day skip.

Reproduced: server holds `bots` unresolved, first `done:bots` POST rejects, profile is invalidated, user opens `/bots` again with a working server. Result: `done:bots` POST count stays 1 and the placement after leaving is still `nav:/bots`.

`current` self-heals (its key is forgotten when the stamp signature changes). `skip` has the same weakness as `done` when no next candidate exists.
**Fix:** Forget the key when its request fails, without invalidating the profile in the error path (that would retry at failure speed). Per-call `mutate` callbacks only fire for the latest call on an observer, and the recorder can send two requests in one effect, so use the promise:

```ts
// useRecordFeatureRoute.ts: return the promise so each call can observe its own failure
return useCallback(
  (request: FeatureRouteActionRequest): Promise<unknown> | null => {
    if (state == null || impersonated || !isRouteWriteNeeded(state, request)) return null;
    return mutateAsync(request);
  },
  [state, impersonated, mutateAsync],
);

// FeatureRouteRecorder.tsx
sentRef.current.add(key);
// Bug fix: a failed write must be retried on the next visit or profile refetch.
// The global MutationCache.onError already reports it.
record(request)?.catch(() => sentRef.current.delete(key));
```

The click handlers in `Openings.tsx` and `Train.tsx` need a `?.catch(() => {})` on the returned promise so a failure is not an unhandled rejection.

### WR-02: Every route write cancels an in-flight profile refetch and marks the cache fresh, dropping the refetched profile

**File:** `frontend/src/hooks/useRecordFeatureRoute.ts:51-63`
**Issue:** `onMutate` calls `cancelQueries` on the profile key, then `setQueryData` patches `feature_route`. `setQueryData` resets `isInvalidated` and `dataUpdatedAt`, and nothing re-invalidates afterwards. A profile refetch that was in flight is therefore discarded and the cache counts as fresh for another 5 minutes.

Reproduced: profile shows 0 games, the profile is invalidated (slow GET in flight, as after `handleJobDone` at `App.tsx:948`), the user opens `/bots` so the recorder posts `done:bots`, then the GET resolves with 42 games. Result: the page still shows 0, `fetchStatus` is idle, `isInvalidated` is false, and no further GET is sent.

The existing feedback-ask hook uses the same pattern, but only on a click. Here the writes are effect-driven and fire on exactly the events that also refetch the profile: navigation with a stale profile (refetch on mount plus a first-visit `done`), and the nav unlock at the end of an import (`current` stamp while a second job's invalidation is in flight). The effect is stale game counts and a nav that stays locked or half-updated for up to 5 minutes. The window is short, so the probability per event is low.
**Fix:** Remember that a fetch was dropped and re-invalidate once the last route write settles. The flag must be shared by the three hook instances (recorder, Openings, Train), so keep it at module level:

```ts
/** True while a profile refetch cancelled by a route write still has to be repeated. */
let droppedProfileRefetch = false;

// onMutate, before cancelQueries:
if (queryClient.isFetching({ queryKey: USER_PROFILE_QUERY_KEY }) > 0) droppedProfileRefetch = true;

// onSettled:
if (droppedProfileRefetch && queryClient.isMutating({ mutationKey: FEATURE_ROUTE_MUTATION_KEY }) === 1) {
  droppedProfileRefetch = false;
  void queryClient.invalidateQueries({ queryKey: USER_PROFILE_QUERY_KEY });
}
```

### WR-03: The stamp-signature reset defeats the sent-key guard, so an unconfirmed `current` loops POSTs at network speed

**File:** `frontend/src/components/feature-route/FeatureRouteRecorder.tsx:35-40` (docstring claim at `:16-17`)
**Issue:** The docstring says the sent-key ref stops a server no-op from looping, and the 255-04 summary says a no-op that leaves the stamp unchanged keeps the keys. That is not what the code does. The recorder's own optimistic patch changes the stamp signature, which deletes the `current:<step>` key it has just added. When the response then lacks the stamp, the signature changes back, the keys are cleared again and the same request is sent again.

Reproduced with a stubbed server that answers every `current` with an unchanged state after 30 ms: 46 `current:train` POSTs in 1.5 seconds, unbounded. With an instant response there is one POST, because the optimistic and the server state land in one render, which is why the existing tests do not see it.

I found no path in today's backend that answers a `current` this way (impersonation is guarded on both sides, a resolved step comes back as resolved, a corrupt state comes back as `null`). So this is a latent request storm whose only protection is server behaviour, and the documented protection does not exist for `current` and `skip` keys.
**Fix:** Keep the signature-driven forget (the re-stamp after delete-all-games needs it) and add a per-key send cap that the forget does not reset:

```ts
/** A request is sent at most this often per session, whatever the server answers. */
const MAX_SENDS_PER_KEY = 3;
const sendCountRef = useRef<Map<string, number>>(new Map());

// in the loop, after the sentRef.has(key) check:
const sends = sendCountRef.current.get(key) ?? 0;
if (sends >= MAX_SENDS_PER_KEY) continue;
sendCountRef.current.set(key, sends + 1);
sentRef.current.add(key);
record(request);
```

Correct the docstring, and add a recorder test with a delayed POST mock that returns the unchanged state and asserts a bounded call count.

### WR-04: Recorder test (d) cannot fail on "posts nothing"

**File:** `frontend/src/components/feature-route/__tests__/FeatureRouteRecorder.test.tsx:150-157`
**Issue:** The test waits only for the profile GET to be called, then asserts the placement is `none` and that no POST was made. Both are also true before the profile has loaded, and the assertions run before the profile reaches the recorder. Mutation check: with the recorder and the write hook changed to treat a loaded profile's `feature_route: null` as an empty route (`profile == null ? null : (profile.feature_route ?? { steps: {}, current: null })`), all 7 tests still pass. The fail-closed write guard for a corrupt state is covered at the lib level (`featureRoute.test.ts:95-98`) and for click handlers (`Openings.render.test.tsx`, "posts nothing for a profile without feature_route"), but the recorder wiring this test is named for is not covered.

Tests (c), (e) and (g) use similar waits and were checked the same way: they do fail when their guard is removed, so they are fine.
**Fix:** Wait for a signal that depends on the loaded profile, flush, then assert:

```tsx
// Probe: render a marker once the profile is in
const { data } = useUserProfile();
{data != null && <span data-testid="route-probe-loaded" />}

// test (d)
await screen.findByTestId('route-probe-loaded');
await act(async () => { await new Promise((resolve) => setTimeout(resolve, 0)); });
expect(screen.getByTestId('route-probe').textContent).toBe('none');
expect(apiPost).not.toHaveBeenCalled();
```

## Info

### IN-01: `feature_route.current` is never cleared when its step resolves (claim 7)

**File:** `app/repositories/feature_route_repository.py:43-59`, `app/schemas/feature_route.py:55-61`
**Issue:** `_DONE_SQL` and `_SKIP_SQL` resolve a step but leave `current` pointing at it. `current` is only replaced by the next stamp, so it stays stale after the last step and whenever the next step is locked. This is harmless for the route: SKIP requires the step to be unresolved (`:94`), the client only reads `current` when its step equals the first unresolved step (`featureRoute.ts:189-193`), and a step appended later (D-12) gets a fresh stamp because `current.step` differs (`:72-74`). `with_dot` stays correct too. Two consequences worth knowing: the `FeatureRouteCurrent` docstring ("the step the dot currently sits on") is not true for stored data, and any Postgres query that measures where the dot is must also require the step to be absent from `steps`.
**Fix:** Either document this on `FeatureRouteCurrent`, or drop `current` in the DONE and SKIP statements when it names the resolved step (compute `with_dot` from the old value first).

### IN-02: CURRENT trusts the client's candidate, so clients with different registries re-stamp each other

**File:** `app/repositories/feature_route_repository.py:64-77`
**Issue:** The server stamps any unresolved step and does not check that it is the first unresolved one. Two clients that disagree on the candidate (a stale cached build next to a new build after a step is added, D-12) overwrite each other's stamp on every profile refetch. Each overwrite resets `since_days`, so the step would not expire while both are in use. Bounded by the refetch cadence and limited to the user's own row.
**Fix:** Accept as is, or have the server reject a `current` for a step that is not the first unresolved one in the `FeatureRouteStepId` order.

### IN-03: Dead code in the service: `_CorruptRouteStateError` is never raised

**File:** `app/services/feature_route_service.py:26-34`, `:49`, `:120`
**Issue:** `_capture_corrupt_state` builds and returns a `_CorruptRouteStateError`, and both callers discard the return value. The class was copied from `feedback_ask_service`, where it is raised.
**Fix:** Make `_capture_corrupt_state` return `None` and delete the class.

### IN-04: Stale comments and docstrings

**File:** `frontend/src/lib/botGameSnapshot.ts:17,23,38`, `frontend/src/lib/sounds.ts:41,45,198`, `frontend/src/lib/retiredLocalStorage.ts:27`, `app/routers/users.py:278`
**Issue:** Comments in `botGameSnapshot.ts` and `sounds.ts` point at `useUserFlag.ts`, which this phase deleted. The `retiredLocalStorage.ts` comment gives the old key as `user_flag:<email>:<name>`; the real format was `user_flag:<name>:<email>` (the prefix match removes both). The router docstring says the endpoint records a step as done, but it also handles `current` and `skip`.
**Fix:** Reword the comments so they do not name a deleted file, correct the key format, and describe all three actions in the docstring.

### IN-05: Two backend tests are weaker than their names

**File:** `tests/test_feature_route.py:555-579`, `tests/test_migration_255_feature_route_seed.py:164-182`
**Issue:** `test_concurrent_posts_are_idempotent` sends the same request twice. A read-modify-write implementation would pass it too, so it does not test lost updates. `test_upgrade_is_idempotent` would pass without the migration's `WHERE` guard, because re-seeding writes the same value on the same day; the guard is proven only by the `_USER_HAS_ROUTE` assertion in the first migration test.
**Fix:** Add a concurrent pair with two different steps (`done import` and `done train`) and assert both are stored. For the migration, re-run over a row whose stored route differs from the seed, or fold the case into the first test.

---

_Reviewed: 2026-11-15T21:47:05Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
