# Phase 246: Train Subnav Split, Today / Leaderboard / Archive (SEED-261106-gw8) - Research

**Researched:** 2026-11-06
**Domain:** React route/layout split of a stateful page, one read-only FastAPI list endpoint, SQL aggregate sort
**Confidence:** HIGH for code behaviour (read from source, replayed on the dev DB). MEDIUM for query cost at prod scale (dev has 135 `drill_solves` rows, see Prod checks).

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

#### Carried forward from SEED-261106-gw8 (locked, not re-discussed)
- **D-01:** Tabs and URLs as above. `/train` must keep working for reminders, PWA and nav. Archive keeps its name; statistics get a separate fourth Stats tab later. Desktop and mobile follow the `TabsList variant="brand"` pattern.
- **D-02:** Today holds the streak card with Start button and a new rank line, plus the full schedule card. The collapsible and its collapsed summary are removed. The completed state's "Next session" line stays.
- **D-03:** Leaderboard holds the existing `TrainLeaderboardCard`.
- **D-04:** Archive has a Mastered / Parked toggle with counts and the existing explainer popovers, replacing `TrainStatsCard`. 20 per page via the existing `Pagination`, newest first, list and page in the URL so browser back from Analysis returns to the same spot. No filters in v1.
- **D-05:** New small `TrainPuzzleCard` on `LazyMiniBoard`, not `FlawCard`. Horizontal, board left, details and buttons right. One column on phones, two on desktop. Pre-mistake position with no arrows on both lists.
- **D-06:** Hide the subnav during solve, score and restored-reveal views. `TrainMedalDialogHost` moves to the layout. `POST /train/sessions` and the grading engine must not run on Leaderboard or Archive.

#### Archive card details
- **D-07:** Beside the board, above Analyze: game details (opponent and rating, game date, time control) plus a status line, for example `Mastered Oct 3, 2026` or `Parked Oct 3, 2026 · 4 misses`. The date is the latest solve date for that puzzle (see D-13) and the miss count is `drill_items.fail_count`.
- **D-08:** No originally played move on the card, as text or otherwise. No motif or severity either: all would hint at the answer on a later Retry, and Analyze shows them anyway.
- **D-09:** An empty Mastered or Parked list shows per-list explainer copy based on the existing explainers, plus a link to Today. Example: "No mastered puzzles yet. Solve a puzzle correctly twice in a row to master it." The copy for an empty Parked list should read as good news, not a dead end. Zero-game accounts get the same empty state, no import button.

#### Streak card additions
- **D-10:** The rank line uses the Points board only and reads `#4 this week`, linking to `/train/leaderboard`. Accuracy is excluded because it stays tentative and unranked until 20 puzzles.
- **D-11:** With no Points rank this week, the same spot shows a link reading `See this week's leaderboard`. Guests and opted-out players get the same rank line they see on their own board view. Planning must confirm `viewer.rank` is populated for hidden and guest rows; if it isn't, they get this link instead.
- **D-12:** `Points today: 5/9` is a muted text line in the streak card's details column, under the week caption and rank line, on the completed state only. `TrainStatsCard` is deleted.

#### Archive data
- **D-13:** Sort by latest `drill_solves.solved_at` per puzzle, newest first. Verified: `_advance_drill_item` (`app/repositories/train_repository.py:3092`) is the only status writer in `app/`, and new items are inserted ACTIVE. Status therefore only changes on a solve.
- **D-14:** Keep puzzles whose `game_flaws` row was evicted: `LEFT JOIN` to `game_flaws`, with `mastered_count` and `parked_count` unchanged, so the list always matches the toggle counts. This matches the anchoring rule in `app/models/drill_item.py`. The user did not select this area, so this is a default rather than a discussed choice. Nothing on the card needs the flaw row, since the FEN comes from `games.pgn` via `fen_and_last_move_at_ply`. Later Retry needs a rule for these puzzles (see Deferred Ideas).

#### Tab width and visibility
- **D-15:** Tabs span `max-w-7xl` on every tab, matching Library, where the narrow Import form already sits under wide tabs. Today and Leaderboard stay in a centered `max-w-2xl` column; Archive uses the full width. Tabs must not change size or position when switching.
- **D-16:** Tabs always show on the landing, including during Tank's first-visit intro and in the no-games state. The only hidden states are those in D-06. Accepted cost: Start moves down about 40px on a phone.

### Claude's Discretion
Defaults the user saw and accepted at the end of the discussion, or left unasked:
- Mobile tabs are non-sticky, like Library.
- Mastered is the default list.
- The list lives in the URL path, for example `/train/archive/parked?page=2`, with `/train/archive` resolving to Mastered. The pageview therefore covers it and no Umami event is needed.
- How Retry's space is reserved. No visible placeholder.
- Whether the card shows the arriving move highlight (not an arrow, and not a spoiler) and whether the board itself is clickable.
- Rank line loading and error states, which must not flash the D-11 fallback link before the query resolves.

### Deferred Ideas (OUT OF SCOPE)
- **Retry on evicted puzzles (SEED-261106-q92):** D-14 keeps puzzles with no `game_flaws` row in the Archive, but the solve path skips them as unservable. Retry must hide or disable the button on those cards, so the list endpoint may want to expose that fact when Retry ships.
- **Tactic motif filter and Stats tab:** already recorded in SEED-261106-gw8 as later work.

Out of scope from the phase boundary: Retry (SEED-261106-q92), the Stats tab, archive filters. Never list active puzzles with an Analyze button, because seeing the solution before the next review defeats spaced repetition.
</user_constraints>

<phase_requirements>
## Phase Requirements

There is no REQUIREMENTS.md for this phase (IDs are TBD). The coverage contract is D-01 through D-16.

| ID | Description | Research Support |
|----|-------------|------------------|
| D-01 | Three URL-routed tabs, `/train` stays valid | Q6, Pattern 2 |
| D-02 | Today: streak, rank line, full schedule card | Q7, Pitfall 8 |
| D-03 | Leaderboard tab holds the existing card | Q8 |
| D-04 | Archive toggle, 20 per page, URL state | Pattern 4, Pitfall 7 |
| D-05 | `TrainPuzzleCard` on `LazyMiniBoard` | Q1, Pattern 5 |
| D-06 | Immersive hide, medal host in layout, no session/engine off Today | Q3, Q4, Pattern 1 |
| D-07 / D-08 | Card fields, no spoilers | Pattern 3 (response shape excludes them) |
| D-09 | Per-list empty states | Pattern 4 |
| D-10 / D-11 | Rank line and fallback | Q5, Pattern 6 |
| D-12 | Points today line, `TrainStatsCard` deleted | Q7, Pattern 6 |
| D-13 | Sort by latest solve | Q2 |
| D-14 | Evicted puzzles stay listed | Q2 |
| D-15 / D-16 | Tab geometry and visibility | Pattern 2, Pitfall 3 |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

Root `CLAUDE.md`:
- Routers are HTTP only; SQL lives in repositories. `APIRouter(prefix="/train")` with relative paths, so the route is `@router.get("/archive")`.
- Never bare `str` for a fixed set: `Literal["mastered", "parked"]` in the schema and parameters.
- No magic numbers: `ARCHIVE_PAGE_SIZE`, query bounds as named constants.
- Explicit return annotations; `ty` zero errors; `Sequence[...]` for parameters taking literal lists.
- Sentry: `capture_exception` in non-trivial `except` blocks in routers, no variables in messages, `set_context` for data.
- Never `asyncio.gather` on one `AsyncSession`: list then count, sequentially.
- API responses never expose internal hashes.
- Nesting depth <= 4 (gated). About 100 logic lines per function and cognitive complexity <= 15 are soft.
- Pre-merge gate before the squash-merge. CHANGELOG bullet under `[Unreleased]`.
- GSD scope: no unplanned features.

`frontend/CLAUDE.md`:
- `data-testid` on every interactive element and major container, kebab-case and component-prefixed.
- `text-sm` is the floor. `text-xs` only inside hover/tap info popovers.
- Primary is `variant="default"`, secondary is `variant="brand-outline"`. Analyze on the card is `brand-outline`, as on `FlawCard`.
- Every `useQuery` loading/data/empty chain needs an `isError` branch ("Failed to load [X]. Something went wrong. Please try again in a moment."), never falling through to the empty state.
- No duplicate Sentry capture around `useQuery`; the global `QueryCache.onError` handles it.
- URL-routed tabs need no Umami event. Never put `data-umami-event` on an internal `<Link>`; use `trackFeature` in `onClick`. Register targets in `FeatureEventMap` first.
- Knip gates CI: remove exports with the feature. `npm run build` is the only type check. No Prettier.
- `noUncheckedIndexedAccess` is on. Theme colours live in `theme.ts`.

Memory rules that apply: never re-add per-file test timeouts, hoist `await import` out of test bodies into `beforeAll`; prove gap fixes by reverting them.

## Summary

The split is mostly a state-ownership problem, not a routing one. `TrainPage` owns session state, loop flags, and the grading Worker, and `/train/*` already routes every sub-path to it. Move all of that into one hook owned by the page itself (which becomes the layout), add a latch so nothing session-related starts until Today is first visited, and derive `immersive` in the same place. The layout then knows the immersive state synchronously from first paint, with no context or callback, which removes the restored-reveal flash and gives the medal host its hold-back for free.

Three things in the seed were wrong or incomplete. The seed's `buildGameAnalysisUrl(game_id, ply)` lands one half-move past the position the card shows, because `?ply=N` is an index into `mainLine` where `mainLine[N]` is the position after move N has been played. `TrainSolveScreen`'s `ply - 1` is correct. Second, "no migration" holds only because of table size: no index on `drill_solves` can serve a user-scoped read, so the list query is a sequential scan. That scan costs less than the page's PGN parsing until the table reaches roughly 300k rows, and `POST /train/sessions` already does the same scan on every compose, so the recommendation is no migration unless the prod check says otherwise. Third, browser Back during the solve loop now lands on a sibling tab instead of leaving the page, which the current state machine does not handle.

The leaderboard data already supports the rank line for all viewers, and `TrainLeaderboardCard` needs no new states.

**Primary recommendation:** Keep `pages/Train.tsx` as the single route element. Extract its state into `useTrainLoop({ isToday, canTrain })` with a one-way `todayVisited` latch, render a nav-only `TrainSubnav` plus plain-div panels, and link Analyze through one shared helper that applies `ply - 1`.

## Planning Questions Resolved

### Q1. Analyze ply: use `ply - 1`, the seed is off by one

**Recommendation:** Add `buildTrainPuzzleAnalysisUrl(gameId, ply)` to `lib/analysisUrl.ts` returning `buildGameAnalysisUrl(gameId, ply > 0 ? ply - 1 : null)`, and use it in both `TrainSolveScreen.tsx:947` and the new card.

Evidence chain:

1. **`drill_items.ply = P` means the position after P half-moves, with the user to move and the flawed move still unplayed.** `fen_and_last_move_at_ply` replays `moves[:ply]` and returns `moves[ply - 1]` as the arriving move [VERIFIED: app/services/train_pool.py:1525-1532]. Replayed on dev rows, `moves[ply]` equals `game_positions.move_san` at that ply and `board_fen()` equals `game_flaws.fen`, for all 6 sampled items including all 3 mastered ones (for example game 820337, ply 28: side to move white, `user_color` white, `moves[28]` = `Qe3`, arriving move `c6d4`) [VERIFIED: dev DB replay this session].
2. **`?ply=N` navigates to `mainLine[N]`** [VERIFIED: frontend/src/hooks/analysis/useAnalysisRouteSeeding.ts:218,237].
3. **`mainLine[i]` is the node after move i has been played, with no root entry.** `loadMainLine` pushes one node per SAN, carrying `chess.fen()` after that move, starting at id 0. The root is `currentNodeId: null`, not an entry in `mainLine` [VERIFIED: frontend/src/hooks/useAnalysisBoard.ts:429-447, 474].

So:

| URL | Node | Board shown |
|-----|------|-------------|
| `?ply=P-1` | `mainLine[P-1]` | after P half-moves: the card's position, the arriving move last |
| `?ply=P` | `mainLine[P]` | after the flawed move has been played |

This matches `forkPlyForOrientation`'s docstring, verbatim: "Missed lines fork at the pre-flaw DECISION board (flawPly-1)" and "Allowed lines fork at the FLAW position itself (flawPly)" [VERIFIED: frontend/src/lib/analysisTactics.ts:45-46]. `FlawCard` passes `flaw.ply` deliberately (it also auto-opens a tactic line through `initialTactic`). At `P-1` the marker lookup finds no user flaw, since `tacticOrientationAtPly` requires `m.is_user` and `P-1` is the opponent's move, so no line auto-opens and the board stays on the card's position.

Edge: `ply === 0` gives `null`, and `initialPly ?? 0` lands on `mainLine[0]`, one half-move past the root. This is existing behaviour, there are 0 such rows in dev, and it is left alone. Prod check P6 counts them.

**FEN derivation:** `fen_and_last_move_at_ply(game.pgn, item.ply)` gives the full FEN and the arriving UCI. `game_flaws.fen` is piece placement only and D-14 allows it to be missing, so do not use it.

**Existing Train shape:** `TrainPuzzle` carries `game_id`, `ply`, `fen`, `side_to_move`, `last_move_uci` [VERIFIED: app/routers/train.py:103-111]. The archive item reuses those names.

### Q2. Sort query: sequential scan on `drill_solves`, no migration unless the prod check exceeds the threshold

**The query that ships:** see Pattern 3. It groups solves once for the user and joins the result to the page of items.

**Do not use the correlated form.** A per-item `(SELECT max(solved_at) FROM drill_solves ...)` runs one full scan per item (the dev plan shows `Seq Scan on drill_solves` inside `SubPlan 1`, `loops=3`). That is items × table rows, and it would be the worst plan available on a parked-heavy user.

**Indexes on `drill_solves`**, read from `pg_indexes`:
- `drill_solves_pkey (session_id, "position")`
- `ix_drill_solves_solved_at (solved_at) WHERE (solved_at IS NOT NULL)`
- `uq_drill_solves_session_puzzle (session_id, game_id, ply)`

None has a `user_id` or `game_id` prefix. With `enable_seqscan = off` the only alternative the planner finds is a bitmap scan of the entire `ix_drill_solves_solved_at` with `Filter: ((user_id = 28) AND (source = 0))`, which still visits every solved row [VERIFIED: dev EXPLAIN this session].

**Measured on dev:** 135 rows, 88 kB heap, grouped form executes in 0.15 ms. The plan shows `Seq Scan on drill_solves ... Rows Removed by Filter: 107`. The dev DB is too small to show a realistic plan, so treat these as shapes, not timings.

**Cost estimate:** the correlated plan's per-loop scan took 0.026 ms for 135 rows, about 0.2 µs per row when cached. That extrapolates to about 20 ms at 100k rows [ASSUMED: linear extrapolation, cached pages]. PGN parsing costs 28 to 71 ms per page (below), so the scan stays the smaller cost until roughly 300k rows.

**Not a new class of cost.** `POST /train/sessions` already runs user-scoped reads on `drill_solves` with no usable index: `app/services/sharp_filler.py:127` (`DrillSolve.user_id == user_id, DrillSolve.source == DrillSource.SHARP_FILLER`) and the herring no-repeat `exists` at `app/services/train_pool.py:1342`.

**Decision rule, settled by prod check P1 and P2:** no migration unless `drill_solves` has 300k rows or more, or the P2 execution time exceeds 50 ms. If the rule fires, add the additive index below. Keep the code otherwise identical.

```python
# app/models/drill_solve.py, __table_args__. Only if P1/P2 cross the threshold.
Index(
    "ix_drill_solves_user_sr_puzzle",
    "user_id", "game_id", "ply", "solved_at",
    # source 0 = DrillSource.SR_ITEM
    postgresql_where=text("solved_at IS NOT NULL AND source = 0"),
)
```

Migration precedent for a concurrent build: `alembic/versions/20260426_201533_80e22b38993a_add_gp_user_game_ply_index.py` (`op.get_context().autocommit_block()`, `postgresql_concurrently=True`).

**Nullable `solved_at` on a mastered item:** should be impossible, and the query tolerates it anyway.
- `solved_at` is set in the claim UPDATE (`"solved_at": now_utc`) [VERIFIED: app/repositories/train_repository.py:3571] and `_advance_drill_item` runs after a successful claim for an SR row (`:3629`). `_advance_drill_item`'s `update(DrillItem)` (`:3128`) is the only status write in `app/`, `scripts/` and `alembic/versions/`; the Phase 244 `UPDATE drill_items` only sets `due_date` on ACTIVE rows. This confirms D-13.
- Solve rows can only vanish with their session. `delete(DrillSession)` appears once, at `:1596`, in `_discard_if_untouched_and_resized`, which acts on sessions with zero solved rows. `scripts/reset_train_state.py` deletes solves and items together.
- Dev shows 0 mastered items without a solved row.
- Still use `LEFT JOIN` + `NULLS LAST` and type the field `datetime | None`, so a surprise row keeps the list equal to the count. The status line then reads `Mastered` with no date. Prod check P4 confirms.

**`SET NULL` on `drill_solves.game_id`:** no effect. `drill_items.game_id` is `ON DELETE CASCADE` [VERIFIED: app/models/drill_item.py:80-82], so deleting a game removes the item in the same statement. An item therefore always has a `games` row, and the inner join to `games` cannot drop rows. A nulled solve row simply matches no item. `app/routers/imports.py:505-506` documents the same cascade.

**Filter `source = SR_ITEM`.** Only SR solves move the status, and a herring row can reference a game the user owns. `SR_ITEM = 0`, `RED_HERRING = 1`, `SHARP_FILLER = 2` [VERIFIED: app/models/drill_solve.py:91-93].

**`game_flaws` join:** a `LEFT JOIN` with no selected column is removed by the planner, because the join key is the table's primary key. The dev plan for it is a bare `Seq Scan on drill_items di` [VERIFIED: dev EXPLAIN this session]. D-14's outcome is therefore met by simply not joining. **Recommendation: omit the join in v1 and pin the behaviour with a test** (an item with no `game_flaws` row still appears, and `total` matches). Add the join when Retry needs to expose servability. This differs from D-14's letter, not its outcome, and D-14 is marked as a default.

**N+1:** none. One statement selects columns only (no `Game` entity, so no lazy loading). The sort runs on a subquery before `games` is joined, so `pgn` is read only for the 20 rows on the page.

**PGN parse cost, measured on dev with `fen_and_last_move_at_ply`:**

| Sample (n=200) | Avg PGN bytes | Median ms | p95 ms | Max ms | 20 cards at median |
|----------------|---------------|-----------|--------|--------|--------------------|
| Random flaws | 3,337 | 1.41 | 2.70 | 78.6 | 28 ms |
| Longest PGNs | 8,442 | 3.56 | 6.75 | 47.6 | 71 ms |

Run it inline in the repository, as `load_session_puzzles` does at `:1464`. No cache. It returns `None` on an unparseable PGN or a ply past the end, and the list must not drop that row (see Pitfall 5).

### Q3. Session and engine placement: layout-level latch

**Recommendation:** hooks stay in the page (now the layout), gated by a one-way `todayVisited` state.

| Concern | Hooks on the Today route | Layout latch (chosen) |
|---------|--------------------------|-----------------------|
| Deep link to Leaderboard or Archive | No POST, no Worker | No POST, no Worker |
| Today → tab → Today | New POST, Worker terminate and respawn, UCI handshake | Nothing |
| "Loading…" flash on return | Yes: `isLoading && session === null` [VERIFIED: TrainStartScreen.tsx:145] | No |
| Layout learns immersive state | Needs a lifted callback or context, flashes on first paint | Direct, synchronous |
| iOS | Repeated Stockfish spawns against a budget of about 3 wasm reservations per page, which Stockfish consumes one of [per project memory, measured 2026-09-06 on an iPhone 14 Pro]. Whether a terminated Worker's reservation is released promptly is unmeasured [ASSUMED] | One Worker per visit |
| After leaving `/train/*` | Unmounts | Unmounts, same as today |
| Today → tab: Worker stays loaded but idle | n/a | Accepted. It only searches when `startGrading` is called, from the solve screen |

D-06 holds under the latch: no POST and no engine load on a visit that never touched Today, and no new POST or search while on those tabs after it has. The StrictMode warning at `Train.tsx:94-107` forbids a ref latch around `startSession()`. The latch here is React state that feeds the effect's dependencies, so the double-invoke recovery the comment relies on still works.

Three call sites re-fire `startSession`: mount, `onSettingsSaved`, `returnToLanding`. All remain reachable only from Today.

### Q4. Layout and loop state: `useTrainLoop` owned by the page, `immersive` derived there

**Owner:** `pages/Train.tsx`, via a new `hooks/useTrainLoop.ts`, which absorbs everything `TrainPage` holds today except rendering.

**State shape** (the pure function is exported so the first-paint rule is unit-testable):

```ts
export function resolveTrainImmersive(input: {
  isToday: boolean;
  showLoop: boolean;
  showScoreScreen: boolean;
  restoredReveal: CachedTrainReveal | null;
  session: TrainSessionResponse | null;
  isSessionError: boolean;
}): boolean {
  if (!input.isToday) return false;
  if (input.showLoop || input.showScoreScreen) return true;
  // Bug-prone spot: restoredActive is false until the session loads, so a cached
  // reveal must count from first paint or the subnav flashes on Analyze -> back.
  // The cache is read in a useState initializer, so this is true on the first render.
  if (input.restoredReveal === null || input.isSessionError) return false;
  return input.session === null || input.session.session_id === input.restoredReveal.sessionId;
}
```

Why each clause matters:
- `session === null` is the first-paint case. A stale cache from another session flips to `false` in the same render that delivers the mismatching session, before the clearing effect at `Train.tsx:115-120` runs.
- `isSessionError` stops an error screen from losing its tabs.
- `!isToday` means a cached reveal cannot hide the subnav on an Archive deep link, where no session will ever arrive to validate it.

**Medal dialog:** `{profile != null && !immersive && <TrainMedalDialogHost isGuest={isGuest} />}` in the layout. This keeps `TrainStartScreen`'s promise: the host unmounts for the loop, the score screen, and a pending restored reveal. It remounts on return, as it does today (the landing already remounted after Done). Between tab switches it stays mounted, so `closed` survives and the dialog does not reopen. Delete the three `<TrainMedalDialogHost>` lines in `TrainStartScreen` (`:407, :417, :451`) and update both docstrings.

A behaviour change to accept: the host now also renders while Today's session is loading or errored, because it no longer lives in those landing branches. The dialog is modal and independent of session data, so this is harmless, and it is required anyway for a deep link to Leaderboard.

**Dev clock:** keep it on the Today panel only. Its handler calls `returnToLanding`, which fires `startSession`.

### Q5. Rank line data: `viewer.rank` is populated for hidden and guest viewers

On the Points board a viewer's rank is always an integer when they have solved at least one puzzle this week, regardless of visibility. `viewer` is `null` otherwise. D-11's "same rank line" applies; no fallback branch is needed for hidden or guest.

- `fetch_week_aggregates` includes all users with a solve in the window, selecting `User.is_guest` and `User.leaderboard_hidden` rather than filtering on them (`app/repositories/train_leaderboard_repository.py:63-103`).
- `_rank_board`: `combined = [e for e in entries if e.is_public or e.key == viewer_id]` [VERIFIED: app/services/train_leaderboard.py:453]. The viewer always joins the ranking.
- `_entry_for("points", ...)` always passes `tentative=False` (`:219-220`), so `_tiered_order` gives every Points entry a numeric rank (`:272-275`).
- `ViewerStanding(rank=ranks[viewer_index], ...)` is set whenever `viewer_index is not None` (`:535-546`).
- `LeaderboardVisibility = Literal["public", "hidden", "guest"]` [VERIFIED: app/schemas/train.py:843]. A hidden or guest rank is computed among visible users plus themselves ("A hidden viewer sees a private would-be row, a guest viewer a ghost row, each ranked among the visible users", `train_leaderboard.py:22-23`), matching what their own board shows.
- A viewer with 0 points this week still gets a rank. Show it; the board shows it too.

**Frontend read:** `data.points.viewer?.rank` from `useTrainLeaderboard()` with no arguments, the landing variant. It shares the key `['train', 'leaderboard']` with `TrainLeaderboardCard`, so no extra request is introduced: the landing already fetched this. Use `refetchOnMount: 'always'` as is.

### Q6. Routing integration: nothing in `App.tsx` needs changing except the Suspense copy

| Item | Finding | Action |
|------|---------|--------|
| Route | `path="/train/*"` already catches sub-paths (`App.tsx:1085`) | None |
| Nav active state | `if (to === '/train') return pathname.startsWith('/train');` [VERIFIED: App.tsx:178]. `App.test.tsx:613` already pins `/train/anything` as active | None |
| Mobile title | `Object.entries(ROUTE_TITLES).find(([path]) => location.pathname.startsWith(path))` [VERIFIED: App.tsx:384-386], with `'/train': 'Train'` (`:137`) | None |
| Import gate | `/train` is in `IMPORT_EXEMPT_ROUTES` and matched on the nav item's `to` (`:168`) | None |
| Nav badge, first-visit flag | Keyed on `startsWith('/train')` (`:711, :764`) | None |
| Reminders and PWA | `frontend/public/push-sw.js:39` falls back to `/train`; `useReminderResurface.ts:165` navigates to `/train`; `TrainInstallQr.tsx:37` is `/train?src=handoff`. All land on Today, and the route parser reads only the pathname | None |
| Install banner | `InstallPromptBanner.tsx:24` suppresses on `startsWith('/train')`, now also on sub-tabs | None |
| Umami pageviews | The tag has `data-exclude-hash` and `data-before-send`, no `data-exclude-search`, and `umamiBeforeSend` strips only `token` [VERIFIED: frontend/index.html:45-48, lib/analytics.ts:65]. So `/train/archive/parked?page=2` is recorded whole, and pagination and the list need no event. `currentPage()` uses the first segment only, so `trackFeature` still labels these `train` | None |
| Mobile Analysis back | `btn-analysis-back` calls `navigate(-1)` (`App.tsx:438`), so the phone's in-app Back returns to the exact list URL | None |
| Suspense fallback | "Loading your training session…" (`App.tsx:1090`) is wrong for Leaderboard and Archive deep links | Change to `Loading…`, keep `train-loading` |
| Unknown sub-paths | Today, `/train/anything` renders Train | `<Navigate to="/train" replace />` |

**Route parsing:** a pure `parseTrainRoute(pathname)` in `lib/trainRoute.ts`, tolerating a trailing slash, returning `{ tab: 'today' } | { tab: 'leaderboard' } | { tab: 'archive', list: 'mastered' | 'parked' } | null`. Follow LibraryPage's path-derived tab but with exact segments rather than `includes`.

**Mastered URL:** `/train/archive` renders Mastered with no redirect, and the toggle's Mastered side links there. A redirect would record two pageviews and add a history step for no benefit.

### Q7. Tests that break

| File | What breaks | Action |
|------|-------------|--------|
| `frontend/src/components/train/__tests__/TrainStatsCard.test.tsx` | Component deleted | Delete; move popover coverage to the Archive tab test |
| `frontend/src/components/train/__tests__/TrainStartScreen.test.tsx` | `train-stats-today-score` (`:399, :413`), toggle clicks (`:311, :506`), card order with leaderboard and stats (`:464, :469, :816-842`), medal host block (`:846-879`), mocks (`:13-16, :176, :183-185`), the "open schedule card" test (`:295`) | Rewrite against the new order; medal assertions move to the page test |
| `frontend/src/components/train/__tests__/TrainScheduleSettings.test.tsx` | `openCard`-style helper (`:181`), collapsed-summary tests (`:931-953`), toggle (`:1050`), any `weekdaySummary` import | Delete summary tests, drop the helper's click |
| `frontend/src/pages/__tests__/Train.solveLoop.test.tsx` | `<MemoryRouter>` with the default entry `/` (`:296`), which `parseTrainRoute` will not treat as Today; `train-stats-today-score` (`:589-590`), comment at `:175-180` | `initialEntries={['/train']}`; assert the new `train-points-today` line |
| `frontend/src/components/train/__tests__/TrainStreakCard.test.tsx` | The card now calls `useTrainLeaderboard` and needs a router for `Link`. `trainApi` mock only stubs `getProgress` (`:15-24`) | Add `getLeaderboard` to the mock and wrap in `MemoryRouter` |
| `frontend/src/lib/__tests__/analytics.test.ts` | Only if it enumerates `PANEL_TARGETS` (`:281` covers `panel-open`) | Check when removing `'train-schedule'` |
| `frontend/src/vitest.setup.ts:22` | Comment naming TrainStartScreen and the Train page, still accurate | None |

Not breaking, but touch: `TrainMedalDialogHost.test.tsx` (host logic unchanged, docstring only), `TrainLeaderboardCard.test.tsx` (unchanged), `TrainSolveScreen.test.tsx:2165, :2272, :2284` (unchanged if the helper returns the same URLs; these pin Q1). `App.test.tsx` is unaffected.

**Source removals for knip and the build:** in `TrainScheduleSettings.tsx`, `weekdaySummary`, `MIN_WEEKDAY_RANGE`, `ALL_WEEKDAYS_MASK`, `scheduleSummary`, the `open` state, the shell's collapsible branch, `ChevronDown`, likely `cn`, and the module docstring's last paragraph. In `analytics.ts`, remove `'train-schedule'` from `PANEL_TARGETS` [VERIFIED: lib/analytics.ts:383] (CONTEXT lists the event as going with the collapsible; this is a removal, not a rename). Keep `formatReminderHour`, which the Select still uses. Also remove the "snapped the schedule card shut" rationale at `TrainStartScreen.tsx:140-144` but keep its logic, because the old session still has to render during a re-fetch.

### Q8. `TrainLeaderboardCard` states: all present, nothing to add

| State | Where | Copy or testid |
|-------|-------|----------------|
| Loading | `:392-398` | `train-leaderboard-loading` |
| Error | `:399-401` | `LoadError`, `train-leaderboard-error` |
| Empty board | `:265-268` | `train-leaderboard-empty`: `No one has trained yet this week. Be the first.` / `No accuracy entries yet this week.` |
| Viewer not on board | `LeaderboardHint`, `trainLeaderboard.ts:114-128` | `Solve a puzzle to enter this week's board.` |
| Guest CTA | `:277-286, :406` | `train-leaderboard-guest-cta` |

A zero-game guest on `/train/leaderboard` therefore gets a complete page. The seed's "needs its own empty state" is already satisfied for Leaderboard; only Archive needs one (D-09). The tab supplies `isGuest` from the layout's profile and a `max-w-2xl` wrapper. Update the docstring's "on the Train landing". `TrainStartScreen.tsx:352, :432, :475` lose the card, including the `exhausted` branch.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Tab and list state | Browser (URL) | — | URL is the source of truth, for back navigation and pageviews |
| Immersive and latch state | Browser (`useTrainLoop`) | — | Derived from local loop state; never persisted |
| Reveal restore | Browser (sessionStorage) | — | Existing per-tab cache, unchanged |
| Archive list, sort, pagination | API + Database | — | Latest-solve aggregate needs SQL; never sort on the client |
| FEN reconstruction | API | — | `python-chess` replay, one implementation |
| Ownership scoping | API | — | `current_active_user.id`, never client-supplied |
| Rank line | API (exists) | Browser (display) | Rank is computed server-side; the client only reads it |
| Analyze deep link | Browser | — | URL construction only |

## Standard Stack

No new dependencies.

| Library | Version | Purpose | Note |
|---------|---------|---------|------|
| react-router | 8.5.1 | `useLocation`, `useNavigate`, `useSearchParams`, `Navigate`, `Link` | [VERIFIED: frontend/node_modules/react-router/package.json]. `FlawsTab` uses `useSearchParams` already |
| @tanstack/react-query | 5.105.0 | `useQuery`, `keepPreviousData` | [VERIFIED: package.json; `keepPreviousData` exported by query-core's index.d.ts]. No existing hook in `hooks/` uses it |
| radix-ui tabs | 1.2.1 | `Tabs`, `TabsList`, `TabsTrigger` via `components/ui/tabs` | [VERIFIED: installed package.json] |
| date-fns | existing | `format(parseISO(x), 'MMM d, yyyy')` | As the "Next session" line, `TrainScheduleSettings.tsx:670` |
| python-chess | existing | PGN replay | Through `fen_and_last_move_at_ply` only |

**Do not use:** `FlawCard` (arrows, severity, tags), `formatDate` from `FlawCard` for the status line (locale-dependent, and D-07 specifies the `MMM d, yyyy` format).

## Package Legitimacy Audit

No external packages are installed in this phase, so no audit applies. **Packages removed due to [SLOP] verdict:** none. **Packages flagged as suspicious [SUS]:** none.

## Architecture Patterns

### System Architecture Diagram

```
Nav / reminder / PWA / browser back
              |
              v
   /train/* (App.tsx, lazy) --> pages/Train.tsx  (the only route element)
              |
              v
     parseTrainRoute(pathname) ---- null ---> <Navigate to="/train" replace/>
              |
              v
     useTrainLoop({isToday, canTrain})
        |  todayVisited latch: false until first Today render, then stays true
        |  (latch && canTrain) --> POST /train/sessions, grading Worker
        v
     resolveTrainImmersive(...) ---- true ---> [ loop / score / restored reveal ]
              |                                  full-width wrapper, no subnav, no medals
              | false
              v
     TrainSubnav + TrainMedalDialogHost
              |
     +--------+---------------------+--------------------------+
     v                              v                          v
  Today panel                  Leaderboard                  Archive
  (mounted once visited,       (mounted when active)        (mounted when active)
   CSS-hidden when inactive)        |                          |
     |                              v                          v
     |                      GET /train/leaderboard      URL list + ?page
     |                                                         |
     +--> rank line reads the same query key                   v
                                                  GET /train/archive?list&limit&offset
                                                               |
                                      drill_items + grouped drill_solves (sort, page)
                                                               |
                                                     join games, PGN replay per row
                                                               |
                                                               v
                                           TrainPuzzleCard --> Analyze /analysis?game_id&ply=P-1
```

### Recommended Project Structure

```
frontend/src/
├── pages/Train.tsx                        # layout; default export stays for React.lazy
├── hooks/useTrainLoop.ts                  # NEW: session, engine, loop flags, latch, immersive
├── hooks/useTrainArchive.ts               # NEW: GET /train/archive
├── lib/trainRoute.ts                      # NEW: parseTrainRoute, buildArchivePath
├── lib/analysisUrl.ts                     # add buildTrainPuzzleAnalysisUrl
├── components/train/TrainSubnav.tsx       # NEW: nav-only Tabs + TabsList
├── components/train/TrainArchiveTab.tsx   # NEW: toggle, list, pagination, empty states
├── components/train/TrainPuzzleCard.tsx   # NEW
├── components/train/TrainStreakCard.tsx   # rank line, optional pointsToday prop
├── components/train/TrainScheduleSettings.tsx  # collapsible removed
├── components/train/TrainStartScreen.tsx  # leaderboard, stats, medal host removed
└── components/train/TrainStatsCard.tsx    # DELETED; explainers move to TrainArchiveTab
app/
├── routers/train.py                       # GET /archive
├── schemas/train.py                       # TrainArchiveItem, TrainArchiveResponse
└── repositories/train_repository.py       # list_archive_items, beside _count_drill_items_by_status
```

### Pattern 1: Latch and render gates

**What:** one-way state, set during render so the effect sees it on the first pass.

```ts
// hooks/useTrainLoop.ts (sketch)
const [todayVisited, setTodayVisited] = useState(isToday);
if (isToday && !todayVisited) setTodayVisited(true);   // adjust during render, no extra frame

const trainSession = useTrainSession();
const gradingEngine = useTrainGradingEngine({ enabled: canTrain && todayVisited });

const { startSession } = trainSession;
useEffect(() => {
  // State, not a ref latch: see the StrictMode comment moved here from Train.tsx.
  if (!canTrain || !todayVisited) return;
  startSession();
}, [canTrain, todayVisited, startSession]);
```

Render gates in the page: loop, score and restored screens render only when `isToday`. The landing renders once `todayVisited`, wrapped in `<div className={isToday ? undefined : 'hidden'}>`.

**Why keep the landing mounted but hidden:** `TrainScheduleSettings` debounces saves by `TRAIN_SETTINGS_SAVE_DEBOUNCE_MS = 600` and only calls `onSaved` from a mutate-level callback, so an edit followed by a quick tab switch would otherwise lose the save, or save without re-fetching the session. This also keeps the streak card from replaying and avoids skeleton flashes. It is free of extra requests: hidden observers refetch only on focus, like any mounted query.

### Pattern 2: Nav-only subnav, plain panels

`Tabs` wraps only `TabsList`. Panels are plain divs, not `TabsContent`.

```tsx
<Tabs value={tab} onValueChange={(val) => { navigate(TRAIN_TAB_PATHS[val]); window.scrollTo({ top: 0 }); }}>
  <TabsList variant="brand" className="w-full max-md:!h-10 max-md:!p-0" data-testid="train-tabs">
    <TabsTrigger value="today" className="flex-1" data-testid="tab-train-today">…</TabsTrigger>
    <TabsTrigger value="leaderboard" className="flex-1" data-testid="tab-train-leaderboard">…</TabsTrigger>
    <TabsTrigger value="archive" className="flex-1" data-testid="tab-train-archive">…</TabsTrigger>
  </TabsList>
</Tabs>
```

Use one responsive `TabsList`, not Library's separate desktop and mobile copies. Library renders `TabsContent` in both branches, so each tab's content is mounted twice, which would double the session effect and the medal dialog here. The trade-off is a dangling `aria-controls` from Radix triggers, which is harmless.

**Wrapper:**
- Not immersive: `mx-auto w-full max-w-7xl px-4 py-2 md:px-6 md:py-6`, as `LibraryPage.tsx:54`.
- Immersive: the existing `trainPageClass(showLoop, restoredActive)`. `TrainSolveScreen` is a two-column layout that needs the full page width.
- Same element, class swap only, so nothing remounts.
- Today and Leaderboard: `mx-auto max-w-2xl`. Reduce `LANDING_CONTAINER_CLASS`'s top padding so the first card sits close under the tabs.

### Pattern 3: Backend list

```python
# app/repositories/train_repository.py
@dataclass(frozen=True)
class ArchiveItemRow:
    game_id: int
    ply: int
    fen: str | None            # None only for an unreplayable PGN; keeps list == count
    last_move_uci: str | None
    user_color: Literal["white", "black"]
    last_solved_at: datetime.datetime | None
    fail_count: int
    white_username: str | None
    black_username: str | None
    white_rating: int | None
    black_rating: int | None
    played_at: datetime.datetime | None
    time_control_bucket: str | None
    time_control_str: str | None


async def list_archive_items(
    session: AsyncSession, *, user_id: int, status: DrillStatus, limit: int, offset: int
) -> list[ArchiveItemRow]:
    # One grouped scan for this user. Never a correlated per-item subquery: with no
    # user/game index on drill_solves that is one full scan per item.
    last_solve = (
        select(
            DrillSolve.game_id,
            DrillSolve.ply,
            func.max(DrillSolve.solved_at).label("last_solved_at"),
        )
        .where(
            DrillSolve.user_id == user_id,
            DrillSolve.source == DrillSource.SR_ITEM,
            DrillSolve.solved_at.is_not(None),
        )
        .group_by(DrillSolve.game_id, DrillSolve.ply)
        .subquery()
    )
    # Sort and page before joining games, so pgn is read for the page's rows only.
    page = (
        select(DrillItem.game_id, DrillItem.ply, DrillItem.fail_count, last_solve.c.last_solved_at)
        .outerjoin(
            last_solve,
            and_(last_solve.c.game_id == DrillItem.game_id, last_solve.c.ply == DrillItem.ply),
        )
        .where(DrillItem.user_id == user_id, DrillItem.status == status)
        .order_by(
            last_solve.c.last_solved_at.desc().nulls_last(),
            DrillItem.game_id.desc(),
            DrillItem.ply.desc(),
        )
        .limit(limit)
        .offset(offset)
        .subquery()
    )
    # select the page's columns plus Game.pgn, Game.user_color, usernames, ratings,
    # played_at, time_control_*; join Game on id == page.c.game_id; repeat the ORDER BY.
```

The tiebreak (`game_id`, `ply`) makes page boundaries stable. `DrillStatus` values: `ACTIVE = 0`, `MASTERED = 1`, `PARKED = 2` [VERIFIED: app/models/drill_item.py:53-55]. The `Game` columns named here were exercised by the EXPLAIN query this session; `user_color` and `pgn` are `nullable=False` in the model.

```python
# app/routers/train.py
ARCHIVE_PAGE_SIZE_MAX: Final = 50
_ARCHIVE_OFFSET_MAX: Final = 2**31 - 1   # bound it so asyncpg cannot overflow into a 500

@router.get("/archive", response_model=TrainArchiveResponse)
async def get_train_archive(
    session: Annotated[AsyncSession, Depends(get_async_session)],
    user: Annotated[User, Depends(current_active_user)],
    list_: Annotated[Literal["mastered", "parked"], Query(alias="list")] = "mastered",
    limit: Annotated[int, Query(ge=1, le=ARCHIVE_PAGE_SIZE_MAX)] = 20,
    offset: Annotated[int, Query(ge=0, le=_ARCHIVE_OFFSET_MAX)] = 0,
) -> TrainArchiveResponse: ...
```

Response: `{ items: TrainArchiveItem[], total: int }`, with `total` from `_count_drill_items_by_status`, the same function behind the toggle counts [VERIFIED: train_repository.py:557-572]. Run list then count sequentially. Mirror the fields into `frontend/src/types/train.ts`.

**Fields deliberately absent (D-08):** `played_move`, `best_move`, severity, motif, `move_san`.

### Pattern 4: Archive tab

- **Page param:** `Math.max(1, parsed)` with non-integer → 1. Changing page calls `setSearchParams({ page: String(n) })` (a push, so Back steps through pages), then `window.scrollTo({ top: 0 })` as `FlawsTab.tsx:445-448`.
- **Over-range page:** when `total > 0 && items.length === 0`, replace to the last page.
- **Query:** key `['train', 'archive', list, page]`, `refetchOnMount: 'always'`, `placeholderData: keepPreviousData`. The prefix sits under `['train']` but is not the progress key, so nothing already invalidates it, which is why `refetchOnMount` is needed: a solve changes membership.
- **Toggle:** `ToggleGroup` like `LeaderboardTabs`, with `onValueChange` navigating to the list path (no `page` param). Guard the empty string Radix sends on re-tap, as `TrainLeaderboardCard.tsx:421`. No Umami event.
- **Counts:** from `useTrainProgress()`; label without a number while pending or errored, never `0`.
- **Popovers:** `InfoPopover` as a **sibling** of each `ToggleGroupItem`, not inside. Its trigger is a `span role="button"` so nesting would be valid HTML, but a click would bubble and switch the list. Keep `testId="train-mastered-info"` and `"train-parked-info"`, so the `popover-open` history continues. Move `MASTERED_EXPLAINER` and `PARKED_EXPLAINER` verbatim [VERIFIED: TrainStatsCard.tsx:39-41].
- **Chain:** error → `LoadError`; first load → skeleton grid; `total === 0` → per-list `EmptyState` with a `Link` to `/train`; otherwise grid `grid grid-cols-1 lg:grid-cols-2 gap-4` (`FlawsTab.tsx:427`) and `Pagination` when `total > PAGE_SIZE`.
- **Parked empty copy (draft, owner-visible):** "Nothing parked. Puzzles you keep missing get set aside here so they stop resurfacing." Reads as good news per D-09, built from the existing explainer. Mastered uses D-09's example.

### Pattern 5: `TrainPuzzleCard`

- `LazyMiniBoard` with `flipped={item.user_color === 'black'}`, no `arrows`.
- **Arriving-move highlight: include it.** `lastMove` from `uciToSquares(item.last_move_uci)`; the solve screen shows the same move on this position, it reads better, and it says nothing about the answer. D-08 does not forbid it.
- **Board not clickable.** Analyze is the single action, and a clickable board would need rework for Retry.
- Size via `useMiniBoardSize` with constants of its own. `FlawCard`'s are 200 desktop and 132 mobile (per CONTEXT).
- Opponent derivation: same as `FlawCard.tsx:186-196`, `'?'` for a null name, rating only when present. Time control and date tolerate null.
- `fen === null`: render the muted board-sized slot with no board. Analyze still works.
- **Analyze:** `Button asChild variant="brand-outline"` with `Link to={buildTrainPuzzleAnalysisUrl(item.game_id, item.ply)}`, `data-testid="btn-train-puzzle-analyze"`, `onClick={() => trackFeature('action', { target: 'analyze' })}`, as `FlawCard.tsx:205-208`. `'analyze'` is already an `ACTION_TARGETS` member [VERIFIED: lib/analytics.ts:398].
- **Retry space:** the action row is `flex gap-2` with Analyze `flex-1`, like `FlawCard`'s `buttonRow`. A second button drops in later with no placeholder.
- `data-testid={`train-puzzle-card-${game_id}-${ply}`}` (numeric only).
- **Status line:** `Mastered Oct 3, 2026`; `Parked Oct 3, 2026 · 4 misses` with `1 miss` singular. Null date: `Mastered`. Parse `last_solved_at` with `parseISO`, which formats in the viewer's local zone. Use the same-format helper the rest of the card uses.

### Pattern 6: Streak card additions

Render order in the details column: heading, week caption, rank line, `Points today`, freezes. Put the rank line in its own small component so the card's body doesn't grow.

```tsx
function TrainRankLine(): ReactElement {
  const { data, isPending, isError } = useTrainLeaderboard();
  // Reserve the row while pending so the fallback link never flashes and nothing shifts.
  if (isPending) return <span className="invisible text-sm" aria-hidden="true">&nbsp;</span>;
  const rank = isError ? null : (data?.points.viewer?.rank ?? null);
  return (
    <Link to="/train/leaderboard" className="text-sm …" data-testid="train-rank-line">
      {rank !== null ? `#${rank} this week` : "See this week's leaderboard"}
    </Link>
  );
}
```

- On a query error the link still works and the Leaderboard tab shows its own `LoadError`; the global `QueryCache` handles Sentry.
- **Points today:** add `pointsToday?: { total: number; max: number }` to `TrainStreakCard`, passed only from the `completed` branch using `state.score` and `state.totalPoints`. Text `Points today: 5/9`, `text-sm text-muted-foreground`, `data-testid="train-points-today"`.
- **Rank-link event (optional):** the pageview cannot separate the link from the tab. `nav-click` currently accepts `NAV_SOURCES = ['more-drawer']` [VERIFIED: lib/analytics.ts:419]. To answer the seed's "may be a motivator" question, add `'train-rank-line'` and call `trackFeature('nav-click', { target: 'train', value: 'train-rank-line' })` in `onClick`. Recommended, because a new feature ships with its event and the URL does not carry this fact.

### Anti-Patterns to Avoid

- **Session hooks under a nested Today route.** Respawns the Worker and re-POSTs on each return, and hides state from the layout.
- **`TabsContent` around the session screens.** It applies `flex-1 text-sm` (`components/ui/tabs.tsx`), which would shrink every inheriting text on the solve screen and landing. `Tabs`' root also adds `flex gap-2`.
- **Library's duplicated desktop and mobile `TabsContent`.** Double-mounts the session and medal hosts.
- **`restoredActive` as the immersive test.** False until the session loads. Use `resolveTrainImmersive`.
- **An inner join to `game_flaws`.** Breaks list-equals-count under lazy eviction.
- **Listing active items.** Status filter must be mastered or parked only; the schema's `Literal` enforces it.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Position from PGN | A new replay | `fen_and_last_move_at_ply` | Handles custom starts, malformed PGN, ply past end |
| Pagination row | A new control | `components/results/Pagination.tsx` | Renders nothing at one page, handles truncation |
| Lazy board | Direct `MiniBoard` | `LazyMiniBoard` | IntersectionObserver with a 200px margin; a page has 20 boards |
| Status counts | A new count query | `_count_drill_items_by_status` | Same source as the toggle, so they can't disagree |
| Date format | `toLocaleDateString` | `format(parseISO(x), 'MMM d, yyyy')` | D-07's format, already used by "Next session" |
| Board-size resolve | `vw` CSS | `useMiniBoardSize` | Board geometry needs a concrete pixel size |

**Key insight:** this phase's risk is moved state, not new code. Every helper the Archive needs already exists.

## Common Pitfalls

### Pitfall 1: Browser Back during the solve loop now lands on a sibling tab
**What goes wrong:** Archive → Today → Start → phone Back gives `/train/archive` while `hasEnteredLoop` is still true. Before, Back unmounted the whole page and a return resumed from the landing. Under a layout, the loop state survives, and Forward or Today would re-mount the solve screen on a stale verdict or score.
**How to avoid:** in `useTrainLoop`, when `!isToday` and `hasEnteredLoop || showScoreScreen`, clear both flags and set `sessionStale`. When `isToday && sessionStale`, call `resetSolve()` and `startSession()`, then clear it. The re-read is load-bearing (`Train.tsx:150-155`: `solved_count` is the compose-time value). It must wait until Today is active again, because D-06 forbids a POST on Archive. Keep `restoredReveal` as is.
**Warning signs:** a test that navigates away mid-loop and sees the solve screen, the mobile header missing (`useMarkPlayActive`), or a POST while on Archive.

### Pitfall 2: "No puzzles available yet" flash on the session-less first render
**What goes wrong:** the mutation is idle on the first commit, before the effect fires: `isLoading` false, `session` null, so `resolveLandingState` returns `empty`. It already exists at page mount, but the latch makes it reachable on every first Today click.
**How to avoid:** pass `isLoading={trainSession.isSessionPending || (trainSession.session === null && !trainSession.isSessionError)}` to `TrainStartScreen`.
**Warning signs:** `train-empty-*` or the generic empty title appearing before `train-session-loading`.

### Pitfall 3: Tabs shifting between tabs (D-15)
**What goes wrong:** a list of different height can bring a page scrollbar in or out and move the centered wrapper. A loading state of a different height does the same.
**How to avoid:** skeletons with card-like height, plus an in-browser check at desktop width. `index.css` has no `scrollbar-gutter` rule (grep returned nothing), and Library has the same exposure. Flag it if the shift is visible rather than adding global CSS unasked.

### Pitfall 4: Immersive flash for a stale reveal cache
**What goes wrong:** with a cache from an older session, the subnav is hidden on first paint and reappears once the session arrives. This is accepted: stale caches are rare, the window is one request long, and the alternative is a flash for the common case.

### Pitfall 5: Dropping a row on a failed replay
**What goes wrong:** copying `load_session_puzzles`' `continue` on a `None` FEN makes the list shorter than the count, and page math drifts.
**How to avoid:** keep the row with `fen=None`. Test with a corrupted PGN.

### Pitfall 6: Medal dialog reopening or appearing mid-session
**What goes wrong:** mounting the host unconditionally in the layout shows it over the solve screen. Keying it to the tab reopens it on every switch.
**How to avoid:** condition only on `!immersive`, at a stable position in the tree. Test: session running → no dialog; deep link to Leaderboard → dialog; switch tabs after dismissing → no reopen.

### Pitfall 7: Browser back and scroll position
**What goes wrong:** back from Analysis restores the URL and data (the query cache keeps the page for the default gc time), but the scroll position depends on the browser's automatic restoration finding the document tall enough at popstate. The app has no `ScrollRestoration`.
**How to avoid:** cached data renders on the first commit, so this should work [ASSUMED]. `LazyMiniBoard` boxes have fixed sizes, so offsets hold before boards paint. Check in UAT; the locked requirement is same tab and page, so a scroll miss is a polish finding, not a blocker.

### Pitfall 8: QR code now renders on every desktop landing
**What goes wrong:** with the collapsible gone, `TrainInstallQr` mounts on all desktop landings, which lazy-loads `qrcode.react`, and the card is much taller on desktop. No analytics fire on mount (`TrainInstallQr.tsx` has no effects or tracking calls per grep). This is a consequence of D-02, not a bug.
**How to avoid:** nothing to do; expect a new chunk request on desktop.

### Pitfall 9: Flaky test from dynamic import in a test body
**What goes wrong:** project memory records `await import` inside a test body as a timeout cause. `Train.solveLoop.test.tsx:291` has that shape.
**How to avoid:** new page tests import in `beforeAll`.

## Code Examples

### Shared Analyze helper

```ts
// frontend/src/lib/analysisUrl.ts
/**
 * /analysis deep link landing on a Train puzzle's own position. `drill_items.ply` is the
 * position after P half-moves, while `?ply=N` opens mainLine[N], the position after move N
 * has been played. So P-1 shows the puzzle's board, and P would show it after the mistake.
 */
export function buildTrainPuzzleAnalysisUrl(gameId: number, ply: number): string {
  return buildGameAnalysisUrl(gameId, ply > 0 ? ply - 1 : null);
}
```

### Route parser

```ts
// frontend/src/lib/trainRoute.ts
export type ArchiveList = 'mastered' | 'parked';
export type TrainRoute =
  | { tab: 'today' }
  | { tab: 'leaderboard' }
  | { tab: 'archive'; list: ArchiveList };

export function parseTrainRoute(pathname: string): TrainRoute | null {
  const path = pathname.replace(/\/+$/, '');
  if (path === '/train') return { tab: 'today' };
  if (path === '/train/leaderboard') return { tab: 'leaderboard' };
  if (path === '/train/archive') return { tab: 'archive', list: 'mastered' };
  if (path === '/train/archive/parked') return { tab: 'archive', list: 'parked' };
  return null;
}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `TrainStatsCard` count tiles | Browsable Archive with counts in the toggle | This phase | Tile testids `train-stats-*` go away; popover testids stay |
| Collapsed schedule card | Full card on Today | This phase | `panel-open` `train-schedule` stops firing |
| Medal host in landing branches | Medal host in layout | This phase | Deep links to Leaderboard get medals |

**Deprecated/outdated:**
- Seed line "`buildGameAnalysisUrl(game_id, ply)`": off by one, see Q1.
- Seed line "No migration expected": true only conditionally, see Q2.
- Seed and CONTEXT trap "use a thin layout with those hooks moved to the Today route": superseded by the latch, as CONTEXT's own finding anticipated.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Seq scan cost scales linearly, about 20 ms at 100k rows when cached | Q2 | The threshold is off. P2 measures the real number, so this resolves itself |
| A2 | A terminated Worker's wasm reservation is not reliably released at once on iOS | Q3 | Only weakens one argument for the latch; the POST and flash arguments stand |
| A3 | Browser scroll restoration works on back from Analysis with cached data | Pitfall 7 | Polish only; URL and page are still correct |
| A4 | Prod `drill_solves` is below 300k rows | Q2 | Add the index; the migration is written out in Q2 |
| A5 | The draft Parked empty copy is acceptable | Pattern 4 | Copy tweak |
| A6 | Omitting the `game_flaws` join is acceptable against D-14's wording | Q2 | Add a no-op join that the planner removes anyway |

## Open Questions

1. **Does the index ship?** Settled by P1 and P2 below. Everything else is independent of the answer.
2. **Should a Today tab return re-read the session after hours away?** The session is not refreshed on a tab switch, and a day rollover with the app left open behaves as it does today with the page left open. Recommendation: no change. Flagging only because tabs make long-lived layouts more likely.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| PostgreSQL dev container | Backend tests, EXPLAIN | ✓ | postgres:18.6-alpine, healthy | — |
| Node | Frontend build and tests | ✓ | v24.19.0 | — |
| uv | Backend | ✓ | 0.10.9 | — |
| Prod DB read access | P1 to P6 | Orchestrator only | — | Default to no migration, flag in the plan |

**Missing dependencies with no fallback:** none.

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest with pytest-xdist; Vitest with Testing Library |
| Config file | existing (`pyproject.toml`, `frontend/vite.config.ts` test block) |
| Quick run command | `uv run pytest tests/routers/test_train.py -k archive -x` and `cd frontend && npx vitest run src/pages/__tests__/Train.subnav.test.tsx` |
| Full suite command | Pre-merge gate in `CLAUDE.md` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| D-01 | `parseTrainRoute` covers all paths, trailing slash, unknown → null | unit | `npx vitest run src/lib/__tests__/trainRoute.test.ts` | ❌ Wave 0 |
| D-01 | `/train/foo` redirects to `/train` | component | `npx vitest run src/pages/__tests__/Train.subnav.test.tsx` | ❌ Wave 0 |
| D-02 | Schedule controls render with no toggle click; Next session line stays | component | `npx vitest run src/components/train/__tests__/TrainScheduleSettings.test.tsx` | ✅ update |
| D-03 | Leaderboard tab renders the card; absent from Today | component | `Train.subnav.test.tsx` | ❌ Wave 0 |
| D-04 | Toggle, URL page, 20 per page, Back restores page | component | `npx vitest run src/components/train/__tests__/TrainArchiveTab.test.tsx` | ❌ Wave 0 |
| D-05 / D-08 | No arrows; no move, motif or severity in DOM or response keys | component + router | `TrainPuzzleCard.test.tsx`; `pytest tests/routers/test_train.py -k archive` (exact key set) | ❌ Wave 0 |
| D-05 / Q1 | Analyze href uses `ply - 1`; solve screen unchanged | unit | `npx vitest run src/lib/analysisUrl.test.ts` and `TrainSolveScreen.test.tsx` | ✅ extend |
| D-06 | Deep link to Leaderboard or Archive: 0 POSTs, no Worker constructed | component | `Train.subnav.test.tsx` | ❌ Wave 0 |
| D-06 | Today → tab → Today: exactly 1 POST and 1 Worker | component | same | ❌ Wave 0 |
| D-06 | Cached reveal: no `train-tabs` on first paint, before the session resolves | component | same, using `saveTrainRevealCache` and a held promise | ❌ Wave 0 |
| D-06 | `resolveTrainImmersive` truth table | unit | `useTrainLoop.test.ts` | ❌ Wave 0 |
| D-06 | Medal host: absent mid-session, present on Leaderboard deep link, no reopen on switch | component | `Train.subnav.test.tsx` | ❌ Wave 0 |
| Pitfall 1 | Back out of loop: solve screen gone, 0 POST on Archive, 1 POST and Resume on return | component | same | ❌ Wave 0 |
| D-07 / D-13 | Sort newest first, tiebreak stable, filler and herring solves ignored, latest of several | integration | `pytest tests/repositories/test_train_repository.py -k archive` | ❌ add |
| D-14 | Item with no `game_flaws` row listed; `total` equals progress count | integration | same | ❌ add |
| Pitfall 5 | Corrupt PGN keeps row with `fen` null | integration | same | ❌ add |
| Security | Other user's items absent; bad `list` is 422; offset and limit bounds are 422; 401 without token | router | `pytest tests/routers/test_train.py -k archive` | ❌ add |
| D-09 | Per-list empty copy and Today link; error branch does not show empty copy | component | `TrainArchiveTab.test.tsx` | ❌ Wave 0 |
| D-10 / D-11 | Rank text; fallback when `viewer` null; no fallback while pending | component | `TrainStreakCard.test.tsx` | ✅ extend |
| D-11 | Hidden and guest viewers carry a numeric Points rank | router | `pytest tests/routers/test_train_leaderboard.py -k "hidden or guest"` | ✅ extend (assert `viewer.rank`) |
| D-12 | Points line on completed only; `TrainStatsCard` gone | component | `TrainStartScreen.test.tsx` | ✅ update |
| D-15 / D-16 | Tabs present in intro, no-games, empty states | component | `Train.subnav.test.tsx` | ❌ Wave 0 |
| D-15 / D-05 | Tab geometry, card layout at 375px and desktop, Analyze lands on the card's board, Back restores page | manual, browser | In-browser UAT, agent-run | manual-only: real layout and navigation |

**Prove the invariants by reverting them** (project rule): the latch, `ply - 1`, the `isToday` gate on loop screens, and the first-paint clause must each fail a test when reverted.

### Sampling Rate

- **Per task commit:** the quick commands for the touched area
- **Per wave merge:** `uv run pytest tests/routers/test_train.py tests/repositories/test_train_repository.py tests/routers/test_train_leaderboard.py -x` and `cd frontend && npm test -- --run && npm run build && npm run knip`
- **Phase gate:** full pre-merge gate green before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `frontend/src/lib/__tests__/trainRoute.test.ts`
- [ ] `frontend/src/hooks/__tests__/useTrainLoop.test.ts`
- [ ] `frontend/src/pages/__tests__/Train.subnav.test.tsx` (fake Worker and `trainApi` mock from `Train.solveLoop.test.tsx`, shared helper or copy; import in `beforeAll`)
- [ ] `frontend/src/components/train/__tests__/TrainArchiveTab.test.tsx`
- [ ] `frontend/src/components/train/__tests__/TrainPuzzleCard.test.tsx` (mock `IntersectionObserver` or `LazyMiniBoard`)
- [ ] Archive cases in `tests/routers/test_train.py` and `tests/repositories/test_train_repository.py`

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | yes | `current_active_user` (FastAPI-Users), as every Train route |
| V3 Session Management | no | Unchanged |
| V4 Access Control | yes | `user_id` from the token only, in both the items and solves predicates; guests allowed like other `/train` routes |
| V5 Input Validation | yes | Pydantic/FastAPI `Literal` list, bounded `limit` and `offset` |
| V6 Cryptography | no | None |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| IDOR via client-supplied user | Elevation | No user parameter exists; scope both subqueries by `current_active_user.id` |
| Scoping only one side of the join | Information disclosure | `drill_solves` subquery is filtered by `user_id` too; a test seeds another user's solve on the same game and ply shape |
| Opening a stranger's game via Analyze | Information disclosure | Only `drill_items` rows are listed, which are the user's own flaws (seed; dev check found 0 rows where `games.user_id <> drill_items.user_id`; P5 confirms in prod) |
| Integer overflow into a 500 | Denial of service | Bounded `offset`, as `_SESSION_ID_MAX` at `app/routers/train.py:69` |
| XSS through usernames | Tampering | React text children only |
| Spoiling an active puzzle | Business logic | `Literal` admits mastered and parked only |
| Unbounded PGN work | Denial of service | `limit` capped at `ARCHIVE_PAGE_SIZE_MAX` |

## Prod checks for the orchestrator

**Status (2026-11-06, during execution): RUN against prod, all pass, no migration.** P1: 19,493 rows (11,353 SR solved, 8.5 MB heap), below 300k. P2, user 28 (largest list), one run: 3.6 ms execution with a seq scan on `drill_solves`, below 50 ms. P3: largest list is 170 mastered (user 28), about 9 pages. P4: 0. P5: 0. P6: 0 evicted archive items, 0 ply-0 items. A4 holds, and T-246-07 is confirmed safe in prod. These checks were NOT run at planning time (the tunnel was down then), and the plans were written on the no-migration fallback.

All read-only. P1 and P2 decide the migration; the rest confirm assumptions without changing the plan unless noted. Replace `28` with another heavy user if P3 shows one.

```sql
-- P1: table size. Migration if n_solves >= 300000.
SELECT count(*) AS n_solves,
       count(*) FILTER (WHERE solved_at IS NOT NULL AND source = 0) AS n_sr_solved,
       pg_size_pretty(pg_relation_size('drill_solves')) AS heap
FROM drill_solves;

-- P2: real plan and time. Migration if execution time exceeds 50 ms on a warm repeat.
EXPLAIN (ANALYZE, BUFFERS)
SELECT di.game_id, di.ply, di.fail_count, ls.last_solved_at
FROM drill_items di
LEFT JOIN (
  SELECT game_id, ply, max(solved_at) AS last_solved_at
  FROM drill_solves
  WHERE user_id = 28 AND source = 0 AND solved_at IS NOT NULL
  GROUP BY game_id, ply
) ls ON ls.game_id = di.game_id AND ls.ply = di.ply
WHERE di.user_id = 28 AND di.status = 1
ORDER BY ls.last_solved_at DESC NULLS LAST, di.game_id DESC, di.ply DESC
LIMIT 20;

-- P3: largest archive lists (page count, and the worst user for P2).
SELECT user_id, status, count(*) AS n
FROM drill_items WHERE status IN (1, 2)
GROUP BY 1, 2 ORDER BY n DESC LIMIT 10;

-- P4: expect 0. Mastered or parked with no SR solved row (the null-date branch).
SELECT di.status, count(*) AS n_without_solved_row
FROM drill_items di
WHERE di.status IN (1, 2)
  AND NOT EXISTS (
    SELECT 1 FROM drill_solves s
    WHERE s.user_id = di.user_id AND s.game_id = di.game_id AND s.ply = di.ply
      AND s.source = 0 AND s.solved_at IS NOT NULL)
GROUP BY 1;

-- P5: expect 0. Items pointing at another user's game (Analyze ownership).
SELECT count(*) AS foreign_items
FROM drill_items di JOIN games g ON g.id = di.game_id
WHERE g.user_id <> di.user_id;

-- P6: informational. Evicted archive items (D-14) and ply-0 items (Q1 edge).
SELECT count(*) FILTER (WHERE gf.ply IS NULL AND di.status IN (1, 2)) AS evicted_archive_items,
       count(*) FILTER (WHERE di.ply = 0) AS ply_zero_items
FROM drill_items di
LEFT JOIN game_flaws gf ON gf.user_id = di.user_id AND gf.game_id = di.game_id AND gf.ply = di.ply;
```

If P4 or P5 is non-zero, the null-date branch or the ownership claim needs another look before planning continues. P5 non-zero would make Analyze unsafe and should block.

## Sources

### Primary (HIGH confidence)
- Repository source, read this session: `frontend/src/pages/Train.tsx`, `TrainStartScreen.tsx`, `TrainStatsCard.tsx`, `TrainStreakCard.tsx`, `TrainScheduleSettings.tsx`, `TrainLeaderboardCard.tsx`, `TrainSolveScreen.tsx`, `useTrainSession.ts`, `useTrainGradingEngine.ts`, `useTrainLeaderboard.ts`, `useAnalysisBoard.ts`, `useAnalysisRouteSeeding.ts`, `analysisTactics.ts`, `analysisUrl.ts`, `trainRevealCache.ts`, `LibraryPage.tsx`, `FlawsTab.tsx`, `Pagination.tsx`, `LazyMiniBoard.tsx`, `analytics.ts`, `App.tsx`, `index.html`
- Repository source, backend: `app/models/drill_item.py`, `drill_solve.py`, `app/services/train_pool.py`, `train_leaderboard.py`, `app/repositories/train_repository.py`, `train_leaderboard_repository.py`, `app/routers/train.py`, `app/schemas/train.py`
- Dev DB, read-only: `pg_indexes`, EXPLAIN ANALYZE of four query shapes, PGN replay of `drill_items`, timing of `fen_and_last_move_at_ply` on 400 rows
- Installed package manifests: react-router 8.5.1, @tanstack/react-query 5.105.0, @radix-ui/react-tabs 1.2.1

### Secondary (MEDIUM confidence)
- Project memory: iOS wasm reservation budget (measured 2026-09-06), frontend test flake causes

### Tertiary (LOW confidence)
- Linear extrapolation of scan cost to prod size (A1), pending P2

No external documentation was needed: every library behaviour relied on here is already in use in the repository, so the research-plan seam was not exercised.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH, no new dependencies
- Architecture: HIGH, follows from the existing state machine; latch behaviour needs the listed tests
- Ply and rank findings: HIGH, read from source and replayed on data
- Query cost: MEDIUM, dev is too small; P1 and P2 settle it
- Pitfalls: HIGH for 1, 2, 5, 6 (traced in code); MEDIUM for 3 and 7 (need a browser)

**Research date:** 2026-11-06
**Valid until:** 2026-12-06, or sooner if `TrainPage` or `useTrainSession` changes

## RESEARCH COMPLETE
