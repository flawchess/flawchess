---
phase: 185-bots-roster-transpose-win-stars
reviewed: 2026-07-22T00:00:00Z
depth: standard
files_reviewed: 20
files_reviewed_list:
  - alembic/versions/20260722_160246_411a8de89c4b_add_persona_id_to_games.py
  - app/models/game.py
  - app/repositories/game_repository.py
  - app/routers/bots.py
  - app/schemas/bots.py
  - app/services/store_bot_game_service.py
  - frontend/src/api/client.ts
  - frontend/src/components/bots/PersonaCard.tsx
  - frontend/src/components/bots/PersonaGrid.tsx
  - frontend/src/components/bots/__tests__/PersonaCard.test.tsx
  - frontend/src/components/bots/__tests__/PersonaGrid.test.tsx
  - frontend/src/hooks/__tests__/useStoreBotGame.test.ts
  - frontend/src/hooks/useBotPersonaWins.ts
  - frontend/src/hooks/useStoreBotGame.ts
  - frontend/src/lib/personas/personaRegistry.ts
  - frontend/src/lib/theme.ts
  - frontend/src/pages/Bots.tsx
  - frontend/src/types/bots.ts
  - tests/repositories/test_game_repository_persona_wins.py
  - tests/routers/test_bots.py
  - tests/schemas/test_bots.py
findings:
  critical: 1
  warning: 3
  info: 1
  total: 5
status: fixed
fixes:
  CR-01: fixed
  WR-01: fixed
  WR-02: fixed
  WR-03: fixed
  IN-01: acknowledged
---

# Phase 185: Code Review Report

**Reviewed:** 2026-07-22
**Depth:** standard
**Files Reviewed:** 20
**Status:** fixed (CR-01, WR-01, WR-02, WR-03 fixed; IN-01 acknowledged, no fix)

## Summary

Phase 185 adds a nullable `games.persona_id` column, a `GET /bots/persona-wins`
endpoint, and transposes the Bots `PersonaGrid` into a rung-major layout with a
win-stars row on each `PersonaCard`. The backend plumbing (migration, schema,
repository, router, service) is careful and well-documented, and the new SQL
correctly reuses the project's canonical `win_cond` (verbatim match against
`stats_repository.query_results_by_time_control`, avoiding the "third
divergent copy" the code comments warn about). Idempotency (D-11), auth
scoping, and PGN-size/length bounds are all handled correctly, and the test
suites (schema, repository, router, and three frontend suites) are thorough
for the paths they cover.

However, the feature's primary user-visible payoff — the win stars on
`PersonaCard` updating after a persona game — has a cache-invalidation gap
that means it will not update in the most common navigation flow (finish
game → "New game" → back to the roster) for up to 5 minutes. There is also a
docstring/behavior mismatch in `count_wins_by_persona`, a small validation
gap on `persona_id`, and dead code introduced by a hook that duplicates
`botsApi.getPersonaWins` instead of calling it (invisible to knip, mirroring
a pitfall already called out elsewhere in this same file for `newGame`).

## Critical Issues

### CR-01: Win-star counts never refresh after a persona game finishes (stale 5-minute cache, no invalidation) — FIXED (commit 50de6676)

**Fix applied:** `BOT_PERSONA_WINS_QUERY_KEY` exported from `useBotPersonaWins.ts`;
invalidated from both `Bots.tsx`'s finish-time store `onSuccess` and
`useStoreBotGame.ts`'s `useDrainPendingStore` (only when at least one entry
actually stored). Covered by a new test in `Bots.test.tsx` (finish-time path)
and two new tests in `useStoreBotGame.test.ts` (drain path, positive +
negative). Mutation-verified: reverting either invalidation call fails its
respective test.

**File:** `frontend/src/hooks/useBotPersonaWins.ts:17-26`, `frontend/src/pages/Bots.tsx:508-527`, `frontend/src/hooks/useStoreBotGame.ts`

**Issue:** `useBotPersonaWins()` is called exactly once, at `BotsPage`'s top
level (`Bots.tsx:526`), with `staleTime: 300_000` (5 minutes) and no
`refetchOnMount`/`refetchInterval` override. `BotsPage` itself never unmounts
across the setup → game → result → "New game" cycle — only the inner
`BotsGame` component remounts (via its `key={boot.nonce}`) — so the
`useBotPersonaWins` query instance persists across a finished game.

Nowhere in the codebase is `queryClient.invalidateQueries({ queryKey:
['botPersonaWins'] })` called:
- `useStoreBotGame.ts`'s `useStoreBotGame()`/`useDrainPendingStore()` mutations
  have no `onSuccess`/`onSettled` invalidation of this key.
- `BotsGame`'s finish-time store effect (`Bots.tsx:260-284`) only calls
  `removePendingStore` on success — it never touches the query cache.

Net effect: a user who plays a persona (e.g. "Diesel the Bull"), wins, and
clicks "New Game" to return to the roster will see the *same* star count they
saw before the game — the just-earned win is invisible until the 5-minute
`staleTime` window lapses or the whole page is hard-reloaded (which resets
the in-memory `QueryClient` and forces a real refetch). This defeats the
phase's stated purpose ("per-persona win tracking to display in Persona
Grid") for the normal in-session flow, which is exactly the flow a user takes
after finishing a game.

**Fix:** Invalidate `['botPersonaWins']` when the finish-time store mutation
succeeds (the same place `removePendingStore` already fires), e.g. in
`Bots.tsx`'s `BotsGame` effect:

```ts
// Bots.tsx, inside the D-21 finish-time store effect
import { useQueryClient } from '@tanstack/react-query';
// ...
const queryClient = useQueryClient();
store.mutate(
  toStoreRequest({ gameUuid: game.gameUuid, pgn: game.pgn, settings, enqueuedAt: Date.now() }),
  {
    onSuccess: () => {
      removePendingStore(ownerKey, game.gameUuid);
      void queryClient.invalidateQueries({ queryKey: ['botPersonaWins'] });
    },
  },
);
```

Also consider invalidating from `useDrainPendingStore`'s per-entry success
path (`useStoreBotGame.ts`), since a queued/offline game that drains
successfully on a later `/bots` mount should also refresh the stars shown on
that same mount.

## Warnings

### WR-01: `count_wins_by_persona` docstring contradicts its own SQL — zero-win personas are NOT absent, they appear as `0` — FIXED (commit fbc32416)

**Fix applied:** added `.having(win_count > 0)` to the query so the returned
dict now matches the documented contract (zero-win personas are absent, not
present as `0`). Extended `test_game_repository_persona_wins.py` with a
persona-with-only-losses case. Mutation-verified: removing the `HAVING`
fails the new test.

**File:** `app/repositories/game_repository.py:282-316`

**Issue:** The docstring states: *"Personas with zero wins for this user are
simply absent from the dict (not present as 0)."* The actual query groups by
every `persona_id` matching the `WHERE` clause (`persona_id IS NOT NULL AND
platform = 'flawchess'`), independent of whether any of those games were won:

```python
result = await session.execute(
    select(Game.persona_id, func.count().filter(win_cond).label("wins"))
    .where(
        Game.user_id == user_id,
        Game.persona_id.is_not(None),
        Game.platform == "flawchess",
    )
    .group_by(Game.persona_id)
)
return {row[0]: row[1] for row in result.all()}
```

A user who has played (and lost/drawn) 3 games against `attacker-1200` but
never won one still produces a group row `("attacker-1200", 0)`, so the
returned dict contains `{"attacker-1200": 0}` — not an absent key. The
committed test suite (`tests/repositories/test_game_repository_persona_wins.py`)
never exercises this exact scenario (every test either has ≥1 win per persona
present in the dict, or zero rows at all), so the mismatch is currently
invisible to CI. It's harmless today only because `PersonaCard` treats `0`
and `undefined` identically — but any future consumer that trusts the
docstring's "absent means never played" contract (e.g. a future "personas
you haven't beaten yet" feature) will silently misbehave.

**Fix:** Either correct the docstring to describe the actual behavior, or
make the behavior match the docstring with a `HAVING` clause:

```python
.group_by(Game.persona_id)
.having(func.count().filter(win_cond) > 0)
```

### WR-02: `useBotPersonaWins` duplicates `botsApi.getPersonaWins` instead of calling it — dead code invisible to knip — FIXED (commit f81812eb)

**Fix applied:** `queryFn` now calls `botsApi.getPersonaWins()` instead of
re-implementing the `apiClient.get` call inline — exactly one implementation
of the endpoint call remains.

**File:** `frontend/src/hooks/useBotPersonaWins.ts:20-22`, `frontend/src/api/client.ts:231-236`

**Issue:** `app/api/client.ts` defines `botsApi.getPersonaWins` for exactly
this call site:

```ts
export const botsApi = {
  storeGame: (data: StoreBotGameRequest) => ...,
  getPersonaWins: () =>
    apiClient.get<PersonaWinsResponse>('/bots/persona-wins').then(r => r.data),
};
```

But `useBotPersonaWins.ts`'s `queryFn` bypasses it and re-implements the same
call inline:

```ts
queryFn: async () => {
  const res = await apiClient.get<PersonaWinsResponse>('/bots/persona-wins');
  return res.data;
},
```

`grep` confirms `botsApi.getPersonaWins` has zero callers anywhere in
`frontend/src`. Because it's an object-literal property (not a bare module
export), `npm run knip` will not flag it as dead — this is the exact same
pitfall `Bots.tsx`'s own code comments call out for `useBotGame`'s `newGame`
property ("knip cannot see it... nothing enforces its removal"). The result
is a maintenance trap: two implementations of the same endpoint call that can
silently diverge (e.g. if one gets an error-handling change and the other
doesn't).

**Fix:** Use the existing API function instead of duplicating it:

```ts
queryFn: () => botsApi.getPersonaWins(),
```

or remove `botsApi.getPersonaWins` if the inline call is preferred, so there
is exactly one implementation.

### WR-03: `persona_id` lacks `min_length=1` — an empty string bypasses the None-means-no-persona contract — FIXED (commit bb988fe5)

**Fix applied:** `Field(default=None, min_length=1, max_length=_MAX_PERSONA_ID_LENGTH)`
now rejects `""` with a 422. Added `test_persona_id_empty_string_rejected` to
`tests/schemas/test_bots.py`. Mutation-verified: removing `min_length=1`
fails the new test.

**File:** `app/schemas/bots.py:50-52`

**Issue:**

```python
persona_id: str | None = Field(default=None, max_length=_MAX_PERSONA_ID_LENGTH)
```

Only `max_length` is bounded. A client can submit `"persona_id": ""`, which
passes Pydantic validation (it's a `str`, not `None`) and is then persisted
by `store_bot_game_service.py`'s `if request.persona_id is not None:` guard
(an empty string is not `None`, so it's written). `count_wins_by_persona`'s
`Game.persona_id.is_not(None)` filter then includes it, producing a spurious
`""` key in the `GET /bots/persona-wins` response — a phantom entry that
serves no persona (the frontend's `personaForId`/registry lookups just
silently `undefined` on it today, but it's needless response pollution and
an easy state to reach by an empty-string form field or a client bug).

**Fix:**

```python
persona_id: str | None = Field(default=None, min_length=1, max_length=_MAX_PERSONA_ID_LENGTH)
```

## Info

### IN-01: `games.persona_id` has no DB-level constraint tying it to the known persona roster — ACKNOWLEDGED, no fix applied

Acknowledged by design per the review's own assessment (reasonable given the
roster's frontend-only, milestone-evolving nature and low blast radius). No
CHECK constraint added.

**File:** `app/models/game.py:182-187`

**Issue:** CLAUDE.md's Database Design Rules recommend `TEXT + CHECK` (or a
lookup table + FK) for low-cardinality domain columns. `persona_id` is
exactly such a column (24 known values today), but ships with no `CHECK`
constraint and no FK — any string up to 30 characters is accepted. This is
explicitly acknowledged in the code's own comments ("the persona roster is a
frontend-only, milestone-evolving TS module... not a DB-tracked entity" /
"low blast radius"), and is a reasonable call given the roster changes every
milestone and lives only in the frontend. Flagging for visibility rather than
as an actionable defect — no fix required unless the roster's blast radius
changes (e.g. if `persona_id` starts driving server-side logic beyond a
display key).

---

_Reviewed: 2026-07-22_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
