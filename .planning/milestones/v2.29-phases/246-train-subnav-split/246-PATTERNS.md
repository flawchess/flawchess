# Phase 246: Train Subnav Split, Today / Leaderboard / Archive - Pattern Map

**Mapped:** 2026-11-06
**Files analyzed:** 27 (11 new source/test groups, 16 modified or deleted)
**Analogs found:** 25 / 27 (the other 2 follow RESEARCH.md sketches, see No Analog Found)

All paths below are relative to the repo root. Frontend `@/` means `frontend/src/`.

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `app/repositories/train_repository.py` (add `list_archive_items`, `ArchiveItemRow`) | repository | CRUD read, paginated, PGN transform | same file: `_count_drill_items_by_status` :557, `load_session_puzzles` :1464 | exact |
| `app/routers/train.py` (add `GET /archive`) | route | request-response | same file: `get_train_leaderboard` :367 | exact |
| `app/schemas/train.py` (add `TrainArchiveItem`, `TrainArchiveResponse`) | schema | request-response | same file: `TrainPuzzle` :54 | exact |
| `frontend/src/types/train.ts` | types | transform | same file: `TrainPuzzle` :18 | exact |
| `frontend/src/api/client.ts` (add `trainApi.getArchive`) | API client | request-response | same file: `getLeaderboard` :343 | exact |
| `frontend/src/hooks/useTrainArchive.ts` (new) | hook | request-response | `frontend/src/hooks/useTrainLeaderboard.ts` | exact |
| `frontend/src/hooks/useTrainLoop.ts` (new) | hook | event-driven state | `frontend/src/pages/Train.tsx` :65-178 (moved code) | exact (extraction) |
| `frontend/src/pages/Train.tsx` | page/layout | event-driven | itself + `frontend/src/pages/library/LibraryPage.tsx` | exact |
| `frontend/src/components/train/TrainSubnav.tsx` (new) | component | URL-routed nav | `LibraryPage.tsx` :98-146 | role-match (single TabsList on purpose) |
| `frontend/src/lib/trainRoute.ts` (new) | utility | transform | `frontend/src/lib/analysisUrl.ts` (pure URL helpers) | role-match |
| `frontend/src/lib/analysisUrl.ts` (add `buildTrainPuzzleAnalysisUrl`) | utility | transform | same file: `buildGameAnalysisUrl` :111 | exact |
| `frontend/src/components/train/TrainArchiveTab.tsx` (new) | component | paginated list | `frontend/src/pages/library/FlawsTab.tsx` :377-455 | exact except URL-held page |
| `frontend/src/components/train/TrainPuzzleCard.tsx` (new) | component | display | `frontend/src/components/library/FlawCard.tsx` | role-match (layout only) |
| `frontend/src/components/train/TrainStreakCard.tsx` | component | request-response | itself; `TrainStatsCard.tsx` :93-101 for points copy | exact |
| `frontend/src/components/train/TrainStartScreen.tsx` | component | state chain | itself | removal |
| `frontend/src/components/train/TrainScheduleSettings.tsx` | component | form | itself | removal |
| `frontend/src/components/train/TrainLeaderboardCard.tsx` | component | request-response | itself | docstring only |
| `frontend/src/components/train/TrainSolveScreen.tsx` :947 | component | transform | itself | one-line swap to shared helper |
| `frontend/src/components/train/TrainStatsCard.tsx` + its test | component | n/a | n/a | DELETE (explainers move first) |
| `frontend/src/lib/analytics.ts` | config | event | same file: `PANEL_TARGETS` :383, `NAV_SOURCES` :419 | exact |
| `frontend/src/App.tsx` :1090 | route | n/a | itself | copy change |
| `tests/repositories/test_train_repository.py` | test | integration | same file | exact |
| `tests/routers/test_train.py`, `tests/routers/test_train_leaderboard.py` | test | router | same files (`_register_and_login` :247, `_seed_game_with_pgn` :377, `_seed_drill_item` :543 in `test_train.py`) | exact |
| `frontend/src/pages/__tests__/Train.subnav.test.tsx` (new), `Train.solveLoop.test.tsx` | test | component | `frontend/src/pages/__tests__/Train.solveLoop.test.tsx` | exact, with import hoisted |
| `frontend/src/components/train/__tests__/TrainPuzzleCard.test.tsx`, `TrainArchiveTab.test.tsx` (new) | test | component | `frontend/src/components/library/__tests__/FlawCard.test.tsx`, `TrainLeaderboardCard.test.tsx` | role-match |
| `frontend/src/lib/__tests__/trainRoute.test.ts` (new), `frontend/src/lib/analysisUrl.test.ts` | test | unit | `frontend/src/lib/analysisUrl.test.ts` | exact |
| `frontend/src/hooks/__tests__/useTrainLoop.test.ts` (new) | test | unit | none needed beyond pure-function tests | see No Analog Found |

Also updated, no new pattern: `TrainStartScreen.test.tsx`, `TrainScheduleSettings.test.tsx`, `TrainStreakCard.test.tsx`, `TrainMedalDialogHost.test.tsx` (docstring), per RESEARCH Q7.

## Pattern Assignments

### `app/repositories/train_repository.py` (repository, paginated read + PGN transform)

**Analog:** same file. All needed imports already exist (:14-69): `DrillItem, DrillStatus`, `DrillSolve, DrillSource`, `Game`, `fen_and_last_move_at_ply`. Confirm `and_` is in the `sqlalchemy` import block at :22-33.

**Frozen-dataclass + keyword-only signature + docstring style** (lines 557-572):
```python
async def _count_drill_items_by_status(
    session: AsyncSession, *, user_id: int, status: DrillStatus
) -> int:
    """Count a user's `drill_items` rows in a given status (mastered/parked counts).

    Args:
        session: AsyncSession.
        user_id: Authenticated user's internal PK (V4: never client-supplied).
        status: The `DrillStatus` to count.
    """
    stmt = (
        select(func.count())
        .select_from(DrillItem)
        .where(DrillItem.user_id == user_id, DrillItem.status == status)
    )
    return (await session.execute(stmt)).scalar_one()
```
This private helper is used for `total`. Either expose a thin public wrapper or return `(rows, total)` from a repository function, because the router calls repositories by module and should not reach for an underscore name.

**PGN replay, inline** (lines 1464-1467):
```python
result = fen_and_last_move_at_ply(game.pgn, solve.ply)
if result is None:
    continue  # never serve a puzzle whose FEN can't reconstruct
fen, last_move_uci = result
```
**DO NOT copy the `continue`.** Pitfall 5: keep the row with `fen=None, last_move_uci=None`, so the list length equals `total`.

**Query shape:** RESEARCH Pattern 3 verbatim (grouped `last_solve` subquery, `page` subquery sorted and limited before joining `Game`, tiebreak `game_id DESC, ply DESC`, `NULLS LAST`). Filter `DrillSolve.source == DrillSource.SR_ITEM`, and scope BOTH sides by `user_id`. Repeat the ORDER BY on the outer select. No correlated subquery.

**D-14 deviation to carry into the plan:** RESEARCH recommends no `game_flaws` join at all (same outcome as D-14's LEFT JOIN, since the planner eliminates it), pinned by a test.

---

### `app/routers/train.py` (route, request-response)

**Analog:** `get_train_leaderboard`, lines 367-407. Imports at :23-60 already include `Annotated, Final`, `Query`, `sentry_sdk`, `train_repository`, `current_active_user`, `get_async_session`. Add `Literal` to the typing import and the new schemas to the block at :35.

**Bounded-Query constant** (lines 67-69):
```python
# drill_sessions.id is int4; a larger session_id would raise in asyncpg and reach
# Sentry as a 500, so the Query bound turns it into a 422 before any SQL runs.
_SESSION_ID_MAX: Final = 2**31 - 1
```

**Handler signature and error handling** (lines 367-373, 400-407):
```python
@router.get("/leaderboard", response_model=TrainLeaderboardResponse)
async def get_train_leaderboard(
    session: Annotated[AsyncSession, Depends(get_async_session)],
    user: Annotated[User, Depends(current_active_user)],
    now_utc: NowUtc,
    session_id: Annotated[int | None, Query(ge=1, le=_SESSION_ID_MAX)] = None,
) -> TrainLeaderboardResponse:
    ...
    try:
        result = await get_weekly_leaderboard(...)
    except Exception:
        sentry_sdk.set_context("train", {"user_id": str(user_id), "session_id": str(session_id)})
        sentry_sdk.capture_exception()
        raise
    return TrainLeaderboardResponse.model_validate(result)
```
Read-only, so no `commit`/`rollback` (those appear on `/progress` at :327-334 because it writes). Copy `user_id = user.id` up front only if there is a reason; there is no finalizer here. No `now_utc` needed. Signature per RESEARCH Pattern 3: `list_` with `Query(alias="list")`, bounded `limit`, `offset`. Run list then count sequentially, never `gather`.

---

### `app/schemas/train.py` + `frontend/src/types/train.ts` (schema)

**Analog:** `TrainPuzzle` at `app/schemas/train.py:54`, field names `game_id`, `ply`, `fen`, `side_to_move`, `last_move_uci`. Long class docstrings explain what is forbidden and why: do the same, stating that `played_move`, `best_move`, severity, motif and `move_san` are excluded per D-08. `Literal` is already imported (:23).

Types from `app/models/game.py`: `user_color` non-null (:140), `time_control_str` :147, `time_control_bucket` :148, `played_at` :215 (nullable). Type `user_color` and `time_control_bucket` as `Literal`, not `str`. Mirror every field in `frontend/src/types/train.ts`, with `fen: string | null`.

---

### `frontend/src/api/client.ts` and `frontend/src/hooks/useTrainArchive.ts` (hook, request-response)

**API analog** (`client.ts` :343-347):
```ts
getLeaderboard: (sessionId?: number) =>
  apiClient
    .get<TrainLeaderboardResponse>('/train/leaderboard', {
      params: sessionId !== undefined ? { session_id: sessionId } : undefined,
    })
```

**Hook analog** (`useTrainLeaderboard.ts` :1-3, :34-46):
```ts
import { useQuery } from '@tanstack/react-query';
import { trainApi } from '@/api/client';
import type { TrainLeaderboardResponse } from '@/types/train';

export function useTrainLeaderboard(options?: UseTrainLeaderboardOptions) {
  ...
  return useQuery<TrainLeaderboardResponse>({
    queryKey: isLanding ? TRAIN_LEADERBOARD_QUERY_KEY : [...],
    queryFn: () => trainApi.getLeaderboard(sessionId ?? undefined),
    refetchOnMount: isLanding ? 'always' : true,
```
Add: key `['train', 'archive', list, page]`, `refetchOnMount: 'always'`, `placeholderData: keepPreviousData` (first use in `hooks/`). No Sentry here, the docstring at :30-32 states why.

---

### `frontend/src/hooks/useTrainLoop.ts` and `frontend/src/pages/Train.tsx` (hook + layout)

**Analog:** `Train.tsx` itself. Move, do not rewrite:

| Moves to `useTrainLoop` | Lines |
|-------------------------|-------|
| `useTrainSession`, `useTrainGradingEngine` | 65, 78 |
| `hasEnteredLoop`, `showScoreScreen`, `restoredReveal` state | 79-87 |
| `startSession` effect WITH its StrictMode comment | 89-110 |
| stale-reveal clearing effect | 112-120 |
| `restoredActive`, `showLoop` | 122-126 |
| `handleNext`, `handleRestoredNext`, `returnToLanding`, `handleDevClockChange` | 128-178 |

**Stays in the page:** `useUserProfile` and its derivations (:69-77), `trainPageClass` (:60-62), profile guard (:180-194), screen rendering (:202-259).

**Effect to gate** (lines 108-110):
```ts
if (!canTrain) return;
startSession();
}, [canTrain, startSession]);
```
Becomes `if (!canTrain || !todayVisited) return;`, with `todayVisited` as React state (RESEARCH Pattern 1). The comment at :94-107 forbids a ref latch, so keep it attached. `useTrainGradingEngine({ enabled: canTrain && todayVisited })`.

**Pure function:** `resolveTrainImmersive` from RESEARCH Q4, exported for tests. Do not use `restoredActive` (:122) as the immersive test: it is false until the session loads.

**Layout wrapper:** one element with class swap. Immersive keeps `trainPageClass`. Otherwise `mx-auto w-full max-w-7xl px-4 py-2 md:px-6 md:py-6` (`LibraryPage.tsx:54`). Keep `data-testid="train-page"`.

**Guards to add:** the redirect analog is `LibraryPage.tsx:28-37` (`<Navigate ... replace />`, used for `parseTrainRoute(...) === null`). Apply Pitfall 1 (`sessionStale`) and Pitfall 2 (`isLoading` also true while `session === null && !isSessionError`). The `TrainDevClock` gate at :209 additionally requires `isToday`. `canTrain` remains `profile != null`, and the profile-guard branch at :180 returns before the subnav, matching existing loading behaviour.

**Medal host:** `{!immersive && <TrainMedalDialogHost isGuest={isGuest} />}` at a stable tree position, after the guard so `profile` is non-null.

---

### `frontend/src/components/train/TrainSubnav.tsx` (component, URL-routed nav)

**Analog:** `LibraryPage.tsx`, imports :1-3, mobile handler and list :98-112:
```tsx
<Tabs
  value={activeTab}
  onValueChange={(val) => {
    navigate(`/library/${val}`);
    window.scrollTo({ top: 0 });
  }}
>
  <TabsList variant="brand" className="flex-1 !h-full !p-0" data-testid="library-tabs-mobile">
    <TabsTrigger value="import" className="flex-1" data-testid="tab-import-mobile">
      <DownloadIcon className="h-4 w-4" />
      Import
```
**Deliberate deviations (RESEARCH Pattern 2):** one responsive `TabsList` rather than Library's two copies; no `TabsContent`. Panels are plain divs, because `TabsContent` applies `flex-1 text-sm` and a duplicated copy double-mounts session and medal hosts. Icon sizing: `mr-1.5 h-4 w-4` as at :61. Testids `train-tabs`, `tab-train-today|leaderboard|archive`. Do not add a `tab-switch` event: URL-routed tabs need none.

---

### `frontend/src/lib/trainRoute.ts` and `frontend/src/lib/analysisUrl.ts` (utility)

**Style analog:** `analysisUrl.ts` is the module to imitate: docstring explaining the URL contract, named path constants (:32-37), pure tolerant parsers (:82-100, :156-159).

**Helper to wrap** (:111-114):
```ts
export function buildGameAnalysisUrl(gameId: number, ply?: number | null): string {
  if (ply == null) return `${ANALYSIS_PATH}?${GAME_ID_PARAM}=${gameId}`;
  return `${ANALYSIS_PATH}?${GAME_ID_PARAM}=${gameId}&${PLY_PARAM}=${ply}`;
}
```
Add `buildTrainPuzzleAnalysisUrl` and `parseTrainRoute` as in RESEARCH Code Examples.

**Existing call site to swap** (`TrainSolveScreen.tsx:947`):
```ts
? buildGameAnalysisUrl(puzzle.game_id, puzzle.ply > 0 ? puzzle.ply - 1 : null)
```
Do not copy `FlawCard`'s `buildGameAnalysisUrl(flaw.game_id, flaw.ply)` (:206): it passes the flaw ply on purpose and is off by one for this card. Knip: `buildGameAnalysisUrl` remains used by `FlawCard` and others.

---

### `frontend/src/components/train/TrainArchiveTab.tsx` (component, paginated list)

**Analog:** `FlawsTab.tsx`.

**Error, list and pagination chain** (:380-381, :426-450):
```tsx
{flawsError && <LoadError resource="flaws" />}
...
<div className="grid grid-cols-1 lg:grid-cols-2 gap-4" data-testid="flaw-grid">
  {flaws.map((flaw) => (<FlawCard key={`${flaw.game_id}-${flaw.ply}`} flaw={flaw} ... />))}
</div>
{matchedCount > PAGE_SIZE && (
  <div className="mt-6">
    <Pagination
      currentPage={Math.floor(offset / PAGE_SIZE) + 1}
      totalPages={Math.ceil(matchedCount / PAGE_SIZE)}
      onPageChange={(page) => {
        setOffset((page - 1) * PAGE_SIZE);
        window.scrollTo({ top: 0 });
      }}
    />
  </div>
)}
```
Difference: page lives in `useSearchParams` (already imported in `FlawsTab.tsx:3, :79`), not `setOffset`. `PAGE_SIZE = 20` as at :41. Page validation and over-range replace per RESEARCH Pattern 4.

**Toggle analog** (`TrainLeaderboardCard.tsx` :196-219, re-tap guard :418-421):
```tsx
<ToggleGroup type="single" value={tab} onValueChange={onChange} variant="outline" size="sm"
  className="mb-2 w-full" aria-label="Leaderboard" data-testid="train-leaderboard-tabs">
  <ToggleGroupItem value="points" data-testid="train-leaderboard-tab-points"
    className="min-h-11 flex-1 text-sm sm:min-h-0">
```
```ts
// Radix single-select emits '' when the active item is re-tapped
if (value === '') return;
```

**Explainers: move verbatim** (`TrainStatsCard.tsx` :33-41), keeping the comment that ties them to `train_scheduler` thresholds.

**Popover** (`TrainStatsCard.tsx` :57-59, testIds :106, :112):
```tsx
<InfoPopover ariaLabel={info.ariaLabel} testId={info.testId}>{info.body}</InfoPopover>
```
Keep `train-mastered-info` and `train-parked-info` (`popover-open` history), and render as a SIBLING of `ToggleGroupItem`, because a click inside would bubble and switch the list.

**Empty state** (`TrainStartScreen.tsx` :327-337):
```tsx
<EmptyState layout="page" title="..." subtitle="..."
  action={
    <Button variant="brand-outline" asChild className={TRAIN_CTA_BUTTON_CLASS}>
      <Link to="/library/import" data-testid="btn-train-import-games">Import games</Link>
    </Button>
  } />
```
Link goes to `/train`. D-09 copy; no import button. Counts come from `useTrainProgress()`; omit the number while pending or errored, never show `0`. Error: `LoadError` (`@/components/ui/load-error`), never falling through to empty.

---

### `frontend/src/components/train/TrainPuzzleCard.tsx` (component, display)

**Analog:** `FlawCard.tsx`, layout only. Do not import from it: it is a "standalone sibling" convention (:37, :53).

**Imports to reuse** (:1, :19-20, :23, :27, :31, :33-34): `Link`, `Card`, `Button`, `LazyMiniBoard`, `uciToSquares` (`@/lib/sanToSquares`), `useMiniBoardSize`, `trackFeature`, plus `format, parseISO` from `date-fns`.

**Sizes and flip** (:43-44, :108, :110):
```ts
const DESKTOP_BOARD_SIZE = 200;
const MOBILE_BOARD_SIZE = 132;
const mobileBoardSize = useMiniBoardSize(MOBILE_BOARD_SIZE);
const flipped = flaw.user_color === 'black';
```

**Opponent derivation** (:186-196): copy. Null names become `'?'`, rating in parentheses only when present.

**Analyze row** (:201-217), with `buildTrainPuzzleAnalysisUrl` and testid `btn-train-puzzle-analyze`:
```tsx
<div className="flex gap-2">
  <Button asChild variant="brand-outline" className="flex-1">
    <Link to={...} data-testid="btn-flaw-analyze" aria-label="Analyze game"
      // Internal Link: track in onClick, never data-umami-event (frontend/CLAUDE.md).
      onClick={() => trackFeature('action', { target: 'analyze' })}>
      <Search className="h-4 w-4 mr-1" />
      Analyze
```

**Body: separate mobile and desktop trees** (:410-416, :429-445): `sm:hidden` row and `hidden sm:flex gap-3 items-start p-3`, board left with `shrink-0`, right column `flex-1 min-w-0 flex flex-col gap-2`.

**Omit from FlawCard:** arrows, severity accent, chips, `TagLegend`, eval, clock, move notation, platform deep link (`platformPlyUrl` targets the flaw move), `formatDate` (locale-dependent; D-07 requires `MMM d, yyyy`).

**Add:** `lastMove={uciToSquares(item.last_move_uci) ?? undefined}` on `LazyMiniBoard` (prop exists, `LazyMiniBoard.tsx:13, :22`; confirm how `uciToSquares` treats null when wiring, FlawCard passes it a nullable value at :123). `fen === null` renders a muted board-sized slot. `data-testid` is `train-puzzle-card-${game_id}-${ply}`, as `FlawCard.tsx:404`.

**Date format** (`TrainScheduleSettings.tsx:670`):
```tsx
Next session: {format(parseISO(nextSessionDate), 'MMM d, yyyy')}
```

---

### `frontend/src/components/train/TrainStreakCard.tsx` (component)

**Analog:** itself. Insert after the week caption (lines 189-193):
```tsx
{data !== undefined && (
  <span className="text-sm text-muted-foreground" data-testid="train-this-week">
    {thisWeekCaption(data.current_week_completed, data.current_week_required)}
  </span>
)}
{details}
```
Props extend at :125-128 and destructure at :130. Rank line component per RESEARCH Pattern 6, reading `useTrainLeaderboard()` (same key as the Leaderboard tab, so requests dedupe while both are mounted). Render `pointsToday` above `{details}`, so order is caption, rank, points, freezes.

**Copy lineage** (`TrainStatsCard.tsx` :95-97) explains why the label must say "Points": a bare `0/9` reads as a puzzle count.

Note: the `no_material` empty body (`TrainStartScreen.tsx:324-341`) renders no streak card, so those users see no rank line. `exhausted` (:351) does, and passes no `pointsToday`.

---

### `frontend/src/components/train/TrainStartScreen.tsx` (removals)

- Imports :31, :32, :36.
- `TrainLeaderboardCard` at :352, :432, :475.
- `TrainStatsCard` at :433, :476.
- `TrainMedalDialogHost` at :407, :417, :451.
- `TrainEmptyBody`'s `isGuest` prop (:317-318, :409) becomes unused once :352 goes: remove it.
- Docstring :11-18 needs rewriting.
- :426 gains `pointsToday={{ total: state.score, max: state.totalPoints }}`.
- `LANDING_CONTAINER_CLASS` (:100-101): reduce top padding, and update its comment at :95-98.
- Comment at :140-144: drop "snapped the schedule card shut", keep the logic.
- Keep the ordered `resolveLandingState` chain unchanged.

---

### `frontend/src/components/train/TrainScheduleSettings.tsx` (removals)

Remove: `ChevronDown` (:72), `MIN_WEEKDAY_RANGE`/`ALL_WEEKDAYS_MASK` (:179-180), `weekdaySummary` (:184), `scheduleSummary` (:196), shell `open` prop and collapsible branch (:216, :254-290 region), `open` state (:514), toggle wiring and the `panel-open` event (:677-683). Keep `SaveIndicator`, `resolveScheduleCardVisibility`, `formatReminderHour`, and the Next-session line at :670. Check `isWeekdayBitSet` (:141) and `cn` for remaining uses before removing, with knip and the build as gates. `analytics.ts:383`: remove `'train-schedule'`.

---

### `frontend/src/lib/analytics.ts` (optional rank-link target)

`NAV_SOURCES` at :419: `['more-drawer'] as const`. Append `'train-rank-line'` if the plan adopts RESEARCH's recommendation, calling `trackFeature('nav-click', { target: 'train', value: 'train-rank-line' })` from `onClick`, never `data-umami-event` on a `Link`. Verify the props shape against the existing `nav-click` call in `App.tsx` when wiring.

---

### Tests

**Page test** (`Train.solveLoop.test.tsx` :291-300): reuse its `FakeWorker` and `trainApi` mock, but do NOT copy `await import('@/pages/Train')` in the render helper. Hoist it to `beforeAll` (Pitfall 9), and use `initialEntries`:
```tsx
const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
});
return render(
  <MemoryRouter initialEntries={['/train']}>
    <QueryClientProvider client={queryClient}>
      <TooltipProvider>
        <TrainPage />
```
The existing `Train.solveLoop.test.tsx:296` also needs `initialEntries={['/train']}`.

**Streak card test** (`TrainStreakCard.test.tsx` :15-24): add `getLeaderboard: vi.fn()` beside `getProgress`, and wrap in `MemoryRouter`.

**Backend:** seed helpers in `tests/routers/test_train.py`: `_register_and_login` :247, `_seed_game_with_pgn` :377, `_seed_drill_item` :543, `_seed_session` :572, `_delete_games` :406, `_delete_sessions` :415. Clean up every non-guest game insert in `finally`, because the tier-3 lottery is global and leaked games cause flakes elsewhere. Prove key invariants by reverting them (RESEARCH Validation).

## Shared Patterns

### Sentry (backend)
**Source:** `app/routers/train.py:403-406`. **Apply to:** `GET /archive`.
```python
except Exception:
    sentry_sdk.set_context("train", {"user_id": str(user_id), ...})
    sentry_sdk.capture_exception()
    raise
```

### Auth and ownership
**Source:** `app/routers/train.py:369-370`. **Apply to:** `GET /archive`. `Depends(current_active_user)`, with `user_id` passed keyword-only into the repository and no client-supplied user. Guests allowed.

### Query error branch (frontend)
**Source:** `TrainStatsCard.tsx:69-85`, `TrainStreakCard.tsx:142-151`. **Apply to:** `TrainArchiveTab`. Pending renders a `animate-pulse rounded-md bg-muted` skeleton, error renders `LoadError`. No Sentry calls in components, `QueryCache.onError` covers it.

### Internal link tracking
**Source:** `FlawCard.tsx:209-210`. **Apply to:** `TrainPuzzleCard`, rank line. `trackFeature` in `onClick`, never `data-umami-event` on a `Link`.

### Page width
**Source:** `LibraryPage.tsx:54` (`max-w-7xl`) and `TrainStartScreen.tsx:100-101` (`max-w-2xl`). **Apply to:** layout and Today/Leaderboard panels; Archive uses full width.

### Text floor
`text-sm` minimum in all new markup. FlawCard's icon sizes such as `h-3.5` are fine, and only info-popover bodies may use `text-xs`.

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `todayVisited` latch + `sessionStale` (inside `useTrainLoop.ts`) | hook logic | event-driven | No existing layout-level one-way render latch. Use RESEARCH Pattern 1 and Pitfall 1 |
| `frontend/src/hooks/__tests__/useTrainLoop.test.ts` | test | unit | Truth table for the new pure `resolveTrainImmersive`; write as a plain table test |

**Conditional migration:** only if prod checks P1/P2 cross the threshold, whose status is NOT RUN (default is no migration). Analog: `alembic/versions/20260426_201533_80e22b38993a_add_gp_user_game_ply_index.py` (`op.get_context().autocommit_block()`, `postgresql_concurrently=True`). Not read here; RESEARCH Q2 has the index definition.

## Metadata

**Analog search scope:** `frontend/src/{pages,components,hooks,lib,api,types}`, `app/{routers,schemas,repositories,models}`, `tests/`
**Files scanned:** 16 read or excerpted
**Pattern extraction date:** 2026-11-06
