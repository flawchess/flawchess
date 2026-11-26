---
phase: 258
reviewed: 2026-11-21T14:24:30Z
status: issues_found
depth: standard
files_reviewed: 27
files_reviewed_list:
  - app/repositories/library_repository.py
  - app/services/library_service.py
  - app/routers/library.py
  - app/schemas/library.py
  - frontend/src/lib/flawComparisonMeta.ts
  - frontend/src/components/library/stats/LibraryStatsSections.tsx
  - frontend/src/hooks/useLibraryStatsTc.ts
  - frontend/src/components/library/FlawTrendChart.tsx
  - frontend/src/components/library/stats/GapPopover.tsx
  - frontend/src/types/library.ts
  - tests/services/test_library_window.py
  - tests/services/test_library_service.py
  - tests/services/test_flaw_comparison.py
  - tests/services/test_tactic_comparison_service.py
  - tests/routers/test_library_tactic_comparison.py
  - tests/test_library_router.py
  - frontend/src/components/filters/__tests__/FilterPanel.defaults.test.ts
  - frontend/src/components/library/__tests__/FlawTrendChart.test.tsx
  - frontend/src/components/library/stats/__tests__/ContextTagCards.test.tsx
  - frontend/src/components/library/stats/__tests__/FacepalmCard.test.tsx
  - frontend/src/components/library/stats/__tests__/FlawTiles.test.tsx
  - frontend/src/components/library/stats/__tests__/GapPopover.test.tsx
  - frontend/src/components/library/stats/__tests__/LibraryStatsSections.test.tsx
  - frontend/src/components/library/stats/__tests__/flawStatsFixtures.ts
  - frontend/src/hooks/__tests__/useLibraryStatsTc.test.ts
  - frontend/src/lib/__tests__/flawComparisonMeta.test.ts
  - CHANGELOG.md
findings:
  critical: 0
  warning: 1
  info: 8
  total: 9
  necessity: 1
---

# Phase 258: Code Review Report

**Reviewed:** 2026-11-21T14:24:30Z
**Depth:** standard
**Files Reviewed:** 27
**Status:** issues_found

## Summary

Scope of the first review: `git diff main..HEAD` without `.planning/`, on branch
`gsd/phase-258-library-stats-recent-sample-snapshots` at `e387a6fa3`. Nothing was modified.

No blocker. The backend window is sound: every filter sits before the ranking, the three endpoints
build the window from the same call with the same arguments, and the rewritten facepalm query
returns the same rows as the old shape. One frontend defect is still worth fixing before the merge:
the default time control can land on a quiet one (claim 7 does not hold). The second defect of the
first review (WR-02, the quiet message stating something false when a sidebar filter emptied the
window) is resolved by plan 258-05; see "Re-review of 258-05" below.

Checks run for the first review, beyond reading the code:

- **Facepalm rewrite (claim 5):** a read-only script rebuilt the pre-`e387a6fa3` statement next to
  the current `fetch_facepalm_comparison` and compared the rows on the dev DB for users 28, 13 and
  14, each with three filter sets, on the lifetime set and on the windowed id set. All 18
  comparisons were row-for-row identical (up to 5,300 games, 57 to 342 games without a blunder per
  run).
- **Default TC (claim 7):** a scratch vitest probe outside the repo drove `useLibraryStatsTc`
  through "All time, 5 years, back to All time". Selected sequence: `rapid, null, blitz, blitz`,
  where the last `blitz` is the quiet TC.
- **Backend tests at HEAD:** the six touched backend test files plus
  `tests/test_library_repository.py`: 264 passed. `check_function_size.py app/ --fail-over-depth 4`:
  no breaches.

Not run: the full backend suite, the frontend suite, lint, build, knip, and any prod measurement.
The necessity rubric was read; one necessity finding (IN-07).

## Re-review of 258-05 (gap closure, incremental)

Scope: `git diff e461fbcf6..HEAD` on `flawComparisonMeta.ts`, `LibraryStatsSections.tsx` and their two
test files. Read-only; the frontend suite was not run in this pass (the new assertions were read
against the code, not executed).

**WR-02 is resolved.** Checked against the code, not the plan:

- `libraryNoRecentGamesText(tc, windowMonths, otherFiltersActive)` now builds its suffix through
  `samplePlaceText(false, otherFiltersActive)` (`flawComparisonMeta.ts:394`), the same helper the
  basis line uses (`:354`), so the wording of the qualifier cannot drift.
- `FlawStatsSection` computes `otherFiltersActive` once (`LibraryStatsSections.tsx:251`) and passes it
  to both the quiet message (`:279`) and `librarySampleBasisText` (`:302`), so the filter rule
  (`areFiltersEqual(filters, DEFAULT_FILTERS, BASIS_FILTER_FIELDS)`) is a single expression. The
  two lines cannot drift in the rule. The hooks above it are unaffected (the value is computed
  unconditionally, before any early return).
- The hardcoded `recencyFiltered = false` is correct. A quiet TC needs a TC on the switch with
  `total_n === 0`. The switch comes from `count_analyzed_by_tc(**filter_kwargs)` and the window from
  `fetch_recent_window_rows(**filter_kwargs)` with the same `from_date`/`to_date`
  (`library_service.py:1895-1912`, `1930-1950`). With an explicit date bound the window bound is
  dropped (`recent_window_start` returns `None`), so any TC with an analyzed game in the filters has
  that game in the window and the per-TC cap keeps the newest 1000: `total_n >= 1`. A quiet TC
  therefore cannot occur with a recency preset or a custom range. The code comment states this
  accurately. (Not pinned by a test, see IN-08.)
- Tests: both new tests fail without the fix. The component test asserts the exact two paragraphs
  with `playedAs: 'black'` (a `BASIS_FILTER_FIELDS` member), the unit test asserts the `true`
  variant; the default-filter component test still pins the unqualified sentence, so an
  always-on qualifier would also fail. The component test's data is a static mock, so it exercises
  the wording and the filter-state wiring, not the backend, which is what it claims.
- Copy: no em-dash in any added line (the diff contains none). The hint reads "Choose a longer
  period or a custom range under Recency to include older games." It is accurate (a longer preset,
  that is "5 years", or a custom range) and is correct also when a sidebar filter is the cause:
  a quiet TC means older matching games exist, so a wider period does bring them in.
- The updated `NO_RECENT_GAMES_HINT` JSDoc and the `libraryNoRecentGamesText` JSDoc match the code.
  The module header comment (`flawComparisonMeta.ts:10`) names the three symbols and needs no change.

No new Warning or Blocker from this diff. One Info (IN-08).

## Narrative Findings (AI reviewer)

## Warnings

### WR-01: The pinned default can select a quiet time control while a non-quiet one exists

**File:** `frontend/src/hooks/tcSelectionStore.ts:136-143`, with
`frontend/src/hooks/useLibraryStatsTc.ts:33-47`

**Issue:** `pickDefaultLibraryTc` avoids a quiet TC, but `useTcSelection` only calls it when the
pinned default is no longer in the payload (`pinnedOffered ? pinnedDefaultTc : pickDefault(tcs)`).
Since this phase a quiet TC stays in the payload (D-15), so a TC pinned under one filter set
survives as the default under another filter set where it is quiet. The store was written when
"offered" meant "has data"; that no longer holds. `tcSelectionStore.ts` is not in the phase diff,
the interaction is new with this phase.

**Failure scenario** (user who never clicked the TC switch, so nothing is stored):

1. Default filters. Blitz games are all older than 36 months (quiet), rapid has recent games.
   Default is rapid, pin = rapid.
2. Recency "5 years". New query key, empty list, the pin clears. Data arrives, blitz has the most
   analyzed games, pin = blitz.
3. Recency back to "All time" within the TanStack cache lifetime. The cached list is non-empty at
   once and still contains blitz, so the pin holds.

The page now opens on blitz: "No blitz games in the last 36 months." plus the timeline, with the
tiles, "You vs. your opponents" and "Tactic motifs" hidden, although rapid has a full snapshot.
Reproduced with a probe: selected sequence `["rapid", null, "blitz", "blitz"]`. The existing test
`defaults to the TC with recent games when another TC is quiet` only covers a fresh store.

**Fix:** let the store ask the tab whether a pin is still a valid default, and drop it when not:

```ts
// tcSelectionStore.ts
interface TcSelectionStoreOptions<T extends { tc: TimeControlBucket }> {
  storageKey: string;
  pickDefault: (tcs: readonly T[]) => TimeControlBucket | null;
  /** False drops a pinned default that is still offered (Library: it became a quiet TC). */
  isPinStillValid?: (pinned: T, tcs: readonly T[]) => boolean;
}

const pinnedEntry = tcs.find((t) => t.tc === pinnedDefaultTc);
const pinnedOffered =
  pinnedEntry !== undefined && (isPinStillValid?.(pinnedEntry, tcs) ?? true);
```

```ts
// useLibraryStatsTc.ts
isPinStillValid: (pinned, tcs) => !isQuietTc(pinned) || tcs.every(isQuietTc),
```

Add the three-step sequence above as a hook test. A stored user choice is unaffected (it is read
before the default).

## Resolved since the first review

### WR-02 (resolved by 258-05): The quiet message said "No {tc} games in the last 36 months" when a filter emptied the window

Fixed in `flawComparisonMeta.ts:383-398` and `LibraryStatsSections.tsx:251, 279`; see "Re-review of
258-05" for the verification. Not counted in the findings totals.

## Info

### IN-01: `count_analyzed_by_tc` keeps three parameters no caller passes

**File:** `app/repositories/library_repository.py:2032-2034`, `2052-2053`, `2088-2092`

**Issue:** `require_tactic_blobs`, `tactic_families` and `tactic_filter_orientation` had one
production caller, `get_tactic_comparison`, which now reads the window instead. The only remaining
callers (`library_service.py:1936`, `1942`, `tests/services/test_flaw_comparison.py:585`, `613`)
pass none of them. The `require_tactic_blobs` branch is unreachable, and the docstring still says
"only the tactic path sets it" and "the tactic keywords exist so the tactic comparison can reuse
this function unchanged".

**Fix:** remove the three parameters, the branch and the two docstring sentences. Small and inside
the phase's own blast radius, but unplanned: fold it into this phase or note a follow-up.

### IN-02: `games_cap` is returned and typed but never read

**File:** `app/schemas/library.py:545`, `app/services/library_service.py:2059`,
`frontend/src/types/library.ts:524`

**Issue:** No frontend code reads `games_cap` (only the type and the test fixture mention it). The
basis line prints `total_n`, which equals the cap when `cap_reached` is true. `window_months` is
read, `games_cap` is not.

**Fix:** drop the field, or keep it deliberately as API documentation and say so in the schema
docstring.

### IN-03: New repository and service signatures use bare `str` and `Mapping[str, Any]`

**File:** `app/repositories/library_repository.py:2108-2119`,
`app/services/library_service.py:1900`, `1930`, `2106`

**Issue:** CLAUDE.md asks for `Literal` on fixed value sets in service and repository parameters,
and TypedDicts for filter params. `fetch_recent_window_rows` takes `opponent_type: str`,
`color: str | None` and `Sequence[str]` for time control and platform, while
`fetch_facepalm_comparison` in the same file already uses `Literal[...]`, `Color` and
`TimeControlBucket`. `_fetch_recent_window` and `_fetch_flaw_comparison_inputs` take
`filter_kwargs: Mapping[str, Any]`. In `get_facepalm_comparison` the fetch call went from explicit
typed keyword arguments to `**_filter_kwargs` of `dict[str, Any]`, so ty no longer checks the
Literal parameters of `fetch_facepalm_comparison` at that call site. It mirrors the older sibling
`count_analyzed_by_tc`, so it is consistent with the neighbours, not with the rule.

**Fix:** a `LibraryFilterKwargs` TypedDict for the shared filter set, used by the three services
and `_fetch_recent_window`; `Literal`/`Color`/`TimeControlBucket` on `fetch_recent_window_rows`.

### IN-04: "Explicit recency" is decided in two places

**File:** `app/services/library_service.py:1851` and `2057`

**Issue:** `recent_window_start` decides whether the 36-month bound applies, and
`get_flaw_comparison` repeats `from_date is not None or to_date is not None` for
`recency_filtered`, the flag that names the bound in the basis line. If one changes (for example
the deferred "actively chosen All time" idea), the line names a bound the window did not use.

**Fix:** one helper, `has_explicit_recency(from_date, to_date)`, used by both.

### IN-05: New committed-seed tests seed outside the `try`, and one test asserts less than its name

**File:** `tests/test_library_router.py:372-382`, `419-428`;
`frontend/src/components/library/stats/__tests__/LibraryStatsSections.test.tsx:723`

**Issue:** In `test_window_follows_the_pinned_clock` and
`test_recency_filter_replaces_the_window_bound` the four analyzed non-guest games are committed in
a list comprehension before `try:`. If a later insert raises, the earlier games stay committed and
reach the global eval lottery. Low probability, but it is the leak the project's cleanup rule
exists for. Separately, `never changes the shared filter store: the message has no action` only
asserts `trackFeature` was called once; it never looks at the filter store. The neighbouring test
does assert the message contains no button, so the behaviour is covered, the name is not.

**Fix:** `game_ids: list[int] = []` before the `try`, append inside it. Rename the frontend test
or assert on the store.

### IN-06: Comments that no longer match the code

**File:** `frontend/src/types/library.ts:495`,
`frontend/src/components/library/stats/LibraryStatsSections.tsx:214-218`

**Issue:** The `TacticComparisonResponse` comment still says "one entry per time control with
analyzed games in the current filters"; it is now a TC with a tactic-ready game in the recent
window. The `facepalmRowsFor` comment says a TC missing from the facepalm response "only happens
while /facepalm-comparison is still behind a refetched /flaw-comparison"; a quiet TC is now absent
by design (harmless, the quiet branch returns before the tiles render).

**Fix:** update both comments.

### IN-07: Impossible-state guard: `played_at IS NOT NULL` never changes a production result

**File:** `app/repositories/library_repository.py:2156-2157`
**Category:** necessity

**Issue:** The predicate keeps a NULL-dated game from taking a cap slot (DESC sorts NULLs first).
No production call reaches that state. `recent_window_start` returns `None` only when `from_date`
or `to_date` is set (`library_service.py:1851-1853`); its only production caller,
`_fetch_recent_window`, passes the same dates into the filters, and `apply_game_filters` then adds
`played_at >= from_date` or `played_at < to_date + 1 day` (`query_utils.py:355-358`), both of
which reject NULL. Otherwise `played_at >= window_start` (`library_repository.py:2159-2160`)
rejects it. 258-02-SUMMARY (deviation 2) records the same: the predicate was untestable until a
test called the repository with `window_start=None` and no dates. Rated Info, not Warning: the
function documents `window_start=None` as a valid input, so the guard protects the function's own
contract even though no caller exercises it.

**Fix:** keep it and extend the comment ("only reachable when a caller passes no bound and no
date filter; no production caller does"), or drop it together with the extra test. A scope call.

### IN-08: The quiet message hardcodes "no recency filter" with no test pinning the invariant

**File:** `frontend/src/lib/flawComparisonMeta.ts:392-394`

**Issue:** `libraryNoRecentGamesText` passes `recencyFiltered = false` because a quiet TC cannot
occur with an explicit date bound. That holds today (verified in "Re-review of 258-05": the TC
switch and the window share the same `from_date`/`to_date`, and the window then has no lower bound),
and the comment says so. But the claim lives in the backend: no backend test asserts "a TC offered
under an explicit `from_date`/`to_date` always has `total_n >= 1`", and the frontend has no
fallback. If the offered-TC set and the window ever stop sharing the date filter (for example the
deferred "actively chosen All time" idea from IN-04), the message would say "in the last 36 months"
under a custom range. Low probability, wording-only consequence.

**Fix:** add one service test: with `from_date` set, every TC in the flaw-comparison payload has
`total_n >= 1`. Optionally take `recencyFiltered` from `comparison.data.recency_filtered` and fall
back to a period-neutral sentence when it is true.

## Claims

1. **Filters before the ranking, "analyzed" never a pre-rank predicate: holds.** The ranked
   subquery filters on `Game.id IN (filtered base)` in its `WHERE`
   (`library_repository.py:2148-2158`); the base is `_filtered_games_base`, which routes time
   control, platform, rated, opponent type, dates, colour, opponent gap, flaw severity and tactic
   families through `apply_game_filters` (`1798-1814`). `row_number()` is in the select list of
   that same subquery (`2170-2176`) and `rn <= cap` sits outside (`2187`). `analyzed` and
   `tactic_ready` are output columns (`2166-2169`). One caveat that is by design: a `severity`
   parameter is an EXISTS on `game_flaws`, which only analyzed games have, so it narrows the
   pre-rank set to analyzed games. The Stats tab never sends it (`DEFAULT_FLAW_FILTER.severity`
   is `[]`).

2. **Same window for all three endpoints: holds for every request the app sends.** All three go
   through `_fetch_recent_window` (`library_service.py:1895-1912`) with their `_filter_kwargs`.
   Flaw and facepalm pass the identical ten keys (`2038-2049`, `2106-2117`). Tactic adds
   `tactic_families` and `tactic_filter_orientation="either"` (`2301-2317`); with
   `tactic_families=None` that equals the repository defaults (`2118-2119`), and the Stats tab
   never sends `tactic_families` (`useLibrary.ts:262-266`). A direct API client that sends
   `tactic_families` gets a window ranked over the narrowed games, which is filter-first (D-11),
   not drift. Route defaults match across the three (`routers/library.py:233-243`, `287-297`,
   `331-342`). Residual, not worth code: each request reads its own `now_utc`, so a game exactly
   on the 36-month edge could be in one response and not the next.

3. **Month arithmetic and D-04: holds.** `months_before` (`1831-1840`) clamps the day to the
   target month's length and keeps `tzinfo` through `replace`; it works on naive values too.
   Tests pin Feb 29 2028 minus 36 months to Feb 28 2025, Jan 31 minus 2 months to Nov 30, and
   tzinfo identity. `dev_now_utc` is always aware and `played_at` is `TIMESTAMPTZ`
   (`models/base.py:10`). Any explicit bound returns `None` (`1851-1853`), so the 36 months is
   replaced, not intersected: a `from_date` five years back reaches five years
   (`test_recency_from_date`, `test_quiet_tc`). `to_date` alone gives the newest 1000 games up to
   that date with no lower bound, labelled "in the selected period", which is sensible.

4. **Clock only from `dev_now_utc`: holds.** `NowUtc` on the three routes
   (`routers/library.py:33`, `232`, `286`, `330`); the added lines under `app/` contain no
   `datetime.now`, `utcnow`, `func.now`, `NOW()` or `date.today`.

5. **Facepalm rewrite gives identical results: holds, verified on data.** `user_id` and
   `severity = blunder` are in the `ON` clause (`library_repository.py:2627-2634`), so a game
   without a blunder keeps one null-extended row. For that row `ply` is NULL, so every
   `COUNT(ply)` is 0. `s` is NULL too: the score always contains
   `played_coef * LN(maia_played_prob + offset)` (`facepalm_score.py:595-600`), and NULL
   propagates through the sum and the logistic, so `COUNT(s)` is 0. `is_opponent_expr` with a
   NULL ply falls to the `ELSE` arm and is true for one side, which is harmless because the
   counted column is NULL. Row-for-row equality with the old shape was confirmed on three dev
   accounts (see Summary).

6. **Zero-analyzed-window TC and quiet TC: holds, no crash and no contradictory numbers.**
   Window games but none analyzed (TC offered through older analyzed history): flaw gives
   `analyzed_n=0, total_n>0, below_gate=True` with zero-event bullets; facepalm lists the TC with
   three zero-event rows and `low_coverage=False`; tactic omits it. The page shows "..., 0
   analyzed." with the starting hint, gate slots in the tiles and in "You vs. your opponents", and
   "No tactic data for this time control yet." under Tactic motifs. Different wording, no
   conflicting number. Quiet TC: flaw gives `total_n=0`; facepalm and tactic omit it; all three
   sections branch on the flaw entry (`LibraryStatsSections.tsx:269`, `360`, `434-435`) and the
   hooks sit above the early returns. A quiet TC cannot occur with a recency filter set, because
   the date filter then bounds both the offered-TC count and the window. See WR-02 for the
   message wording.

7. **Default never a quiet TC: does not hold.** True for `pickDefaultLibraryTc` itself and for a
   fresh store; false once a pinned default from another filter set is still in the payload
   (WR-01, reproduced). A remembered user choice is respected (`tcSelectionStore.ts:143`, tested).

8. **Basis line text: holds.** All nine cap / recency / filter combinations, the singular
   "1 game", and the missing `sample_since` are pinned by tests and read correctly; `MMM yyyy`
   comes from `parseISO` of a date-only string, so no timezone shift across a month. The hint
   label "5 years" matches the select option (`FilterPanel.tsx:490`). No em-dash and no "pawns"
   in the new copy or the changelog bullet. Two notes: `cap_reached` is `len >= cap`, so exactly
   1000 games inside the 36 months reads "most recent 1,000 ... (since ...)" although nothing was
   cut (true statement, harmless); and the quiet message does not follow the filter-suffix rule
   (WR-02).

9. **No IDOR: holds.** `user_id` is `user.id` from `current_active_user` in all three routes.
   The id array is built from `fetch_recent_window_rows`, which filters `Game.user_id` in the base
   and again in the ranked predicates, and `_analyzed_game_ids_subquery` filters `user_id` once
   more. No request parameter feeds the array. Two-user isolation tests exist for the window and
   for each service.

10. **Test cleanup and clock: holds, and the known item is not a time bomb.** New service and
    window tests use `db_session` (rolled back) and pass a fixed `_NOW`. The two new committed
    router tests delete in `finally` (seeding sits before the `try`, IN-05). The tactic router
    tests and `TestTacticComparisonDualOrientation` pin `dev_now_utc`. The `/facepalm-comparison`
    router tests (`tests/test_library_router.py:465-538`) do run on the real clock, but they have
    no dated seeds: every one uses the module's empty `auth_headers` user and asserts 401, 422,
    200 or `{"tcs": []}`. Their result does not depend on the date, so nothing fires in 2029 or
    later. The January 2026 seeds named in 258-02-SUMMARY belong to `tactic_comparison_state`,
    whose test class is pinned.

**Also checked:** nesting depth (gate passes, no breach); router prefix convention (unchanged,
relative paths); magic numbers (constants imported from `canonical_slice_sql.py`, not redefined);
Sentry (no new `except` block, the three service handlers still capture). Dead code: IN-01, IN-02.
Bare `str`: IN-03.

---

_Reviewed: 2026-11-21T14:24:30Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
