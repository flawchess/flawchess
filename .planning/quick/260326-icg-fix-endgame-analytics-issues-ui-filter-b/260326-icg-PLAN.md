---
phase: quick
plan: 260326-icg
type: execute
wave: 1
depends_on: []
files_modified:
  - frontend/src/hooks/useDebounce.ts
  - frontend/src/pages/Endgames.tsx
  - frontend/src/hooks/useEndgames.ts
  - frontend/src/components/charts/EndgameWDLChart.tsx
  - frontend/src/types/endgames.ts
  - app/schemas/endgames.py
  - app/services/endgame_service.py
  - app/repositories/endgame_repository.py
autonomous: true
must_haves:
  truths:
    - "Clicking time control filters on the Endgames page causes statistics to update"
    - "Users see how many total games they have and what % reached an endgame"
    - "Categories with < 10 games show a visual low sample size warning"
    - "Info tooltip explains Q vs Q exclusion due to 1500cp threshold"
  artifacts:
    - path: "frontend/src/pages/Endgames.tsx"
      provides: "Filter state management and total games summary display"
    - path: "frontend/src/components/charts/EndgameWDLChart.tsx"
      provides: "Sample size warnings and updated info tooltip"
    - path: "app/schemas/endgames.py"
      provides: "total_games and endgame_games fields on EndgameStatsResponse"
  key_links:
    - from: "frontend/src/pages/Endgames.tsx"
      to: "useEndgameStats hook"
      via: "filter state -> debounce -> TanStack Query"
    - from: "app/services/endgame_service.py"
      to: "endgame_repository"
      via: "total game count query"
---

<objective>
Fix four endgame analytics issues from the sanity check report:
1. Debug and fix UI filter bug where time control changes don't update stats
2. Add total games context (X of Y games reached endgame)
3. Add sample size warnings for categories with fewer than 10 games
4. Add Q vs Q exclusion note to the info tooltip

Purpose: Improve data context and fix a filtering bug so endgame analytics are trustworthy and actionable.
Output: Working filter reactivity, total games summary line, low-sample warnings, updated tooltip.
</objective>

<execution_context>
@.planning/STATE.md
</execution_context>

<context>
@frontend/src/pages/Endgames.tsx
@frontend/src/hooks/useEndgames.ts
@frontend/src/hooks/useDebounce.ts
@frontend/src/components/filters/FilterPanel.tsx
@frontend/src/components/charts/EndgameWDLChart.tsx
@frontend/src/types/endgames.ts
@app/schemas/endgames.py
@app/services/endgame_service.py
@app/repositories/endgame_repository.py
@app/routers/endgames.py
@frontend/src/api/client.ts (lines 99-120, endgameApi section)

<interfaces>
From frontend/src/types/endgames.ts:
```typescript
export interface EndgameStatsResponse {
  categories: EndgameCategoryStats[];  // sorted by total desc
}
```

From app/schemas/endgames.py:
```python
class EndgameStatsResponse(BaseModel):
    categories: list[EndgameCategoryStats]
```

From frontend/src/hooks/useDebounce.ts:
```typescript
// WARNING: This hook compares value by reference (Object.is).
// For object values like FilterState, React's useEffect dependency
// check sees a new reference on every setState call, so debounce fires correctly.
// However, verify this is actually working at runtime.
export function useDebounce<T>(value: T, delay: number): T
```

From frontend/src/components/filters/FilterPanel.tsx:
```typescript
export interface FilterState {
  matchSide: MatchSide;
  timeControls: TimeControl[] | null; // null = all
  platforms: Platform[] | null;
  rated: boolean | null;
  opponentType: OpponentType;
  recency: Recency | null;
  color: Color;
}
```

From app/repositories/game_repository.py:
```python
async def count_games_for_user(session: AsyncSession, user_id: int) -> int:
    """Return total number of games imported by the given user."""
```
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Debug and fix filter reactivity bug + add total games context to backend</name>
  <files>
    frontend/src/hooks/useDebounce.ts
    frontend/src/pages/Endgames.tsx
    frontend/src/hooks/useEndgames.ts
    app/schemas/endgames.py
    app/services/endgame_service.py
    app/repositories/endgame_repository.py
    frontend/src/types/endgames.ts
    frontend/src/api/client.ts
  </files>
  <action>
    **Issue 1 — Filter bug debugging:**

    The code chain (FilterPanel -> Endgames.tsx -> useDebounce -> useEndgameStats -> endgameApi) looks correct on static analysis. The bug needs runtime debugging. Follow this sequence:

    1. Add temporary `console.log` statements at each stage to trace the data flow:
       - In `Endgames.tsx`: log `filters` and `debouncedFilters` on render
       - In `useEndgames.ts`: log the params object returned by `buildEndgameParams`
       - In `useDebounce.ts`: log when the timer fires and the new value

    2. Run `npm run dev` and test by clicking time control buttons on /endgames/statistics. Check the browser console output to identify where the chain breaks.

    3. Likely culprits to check:
       - `useDebounce` may not trigger re-render because `useEffect` dependency on object reference may behave unexpectedly with React's batching. Consider if the issue is that the debounced value updates but TanStack Query doesn't refetch because the serialized params look identical (null arrays vs omitted keys).
       - Check if `buildEndgameParams` returns `null` for `time_control` when all are selected AND when some are deselected — both might serialize to the same API params if the client strips null values.
       - Check if `apiClient.get` deduplicates requests that have identical URL params (axios/fetch may drop `null` params).

    4. Fix the root cause. If the issue turns out to be that `null` (all selected) and a subset array produce different query keys but the same HTTP request (because null params are omitted), the fix may be in `buildEndgameParams` to always send explicit arrays instead of null. Or it could be a deeper React/TanStack issue.

    5. Remove all temporary console.log statements after fixing.

    **Issue 2 — Total games context (backend):**

    1. In `app/schemas/endgames.py`, add two fields to `EndgameStatsResponse`:
       ```python
       total_games: int       # Total games matching current filters (not just endgame games)
       endgame_games: int     # Games that reached an endgame phase
       ```

    2. In `app/repositories/endgame_repository.py`, add a new function `count_filtered_games`:
       ```python
       async def count_filtered_games(
           session: AsyncSession,
           user_id: int,
           time_control: list[str] | None,
           platform: list[str] | None,
           rated: bool | None,
           opponent_type: str,
           recency_cutoff: datetime.datetime | None,
       ) -> int:
       ```
       This should count ALL games for the user matching the given filters (same filters as `_apply_game_filters` but just a COUNT query on Game). Use `select(func.count()).select_from(Game).where(Game.user_id == user_id)` then apply `_apply_game_filters`.

    3. In `app/services/endgame_service.py` `get_endgame_stats`, call the new `count_filtered_games` to get `total_games`. Compute `endgame_games` as the sum of all category totals (already computed from rows). Return both in the response.

    4. In `frontend/src/types/endgames.ts`, add `total_games: number` and `endgame_games: number` to `EndgameStatsResponse`.

    5. No changes needed to `frontend/src/api/client.ts` — the fields come back automatically in the JSON response.
  </action>
  <verify>
    Run backend tests: `cd /home/aimfeld/Projects/Python/flawchess && uv run pytest tests/ -x -q`
    Run frontend build: `cd /home/aimfeld/Projects/Python/flawchess/frontend && npm run build`
    Run frontend tests: `cd /home/aimfeld/Projects/Python/flawchess/frontend && npm test`
  </verify>
  <done>
    - Time control filter clicks cause the endgame statistics to re-fetch and display different data
    - EndgameStatsResponse includes total_games and endgame_games fields
    - Frontend type matches backend schema
  </done>
</task>

<task type="auto">
  <name>Task 2: Frontend total games summary, sample size warnings, and tooltip update</name>
  <files>
    frontend/src/pages/Endgames.tsx
    frontend/src/components/charts/EndgameWDLChart.tsx
  </files>
  <action>
    **Issue 2 — Frontend total games summary:**

    In `Endgames.tsx`, when `statsData` is available and has categories, display a summary line above the EndgameWDLChart showing:
    ```
    {endgame_games} of {total_games} games ({pct}%) reached an endgame phase
    ```
    Use `statsData.endgame_games` and `statsData.total_games`. Calculate percentage as `(endgame_games / total_games * 100).toFixed(1)`. Handle edge case where `total_games` is 0 (show "No games imported" instead). Style as `text-sm text-muted-foreground mb-2`. Add `data-testid="endgame-summary"` to the container element.

    Apply this in both the `statisticsContent` block (before `<EndgameWDLChart>`) — this is shared between desktop and mobile so it only needs to be added once.

    **Issue 4 — Sample size warnings in EndgameWDLChart:**

    In `EndgameWDLChart.tsx`:

    1. Add a named constant: `const MIN_GAMES_FOR_RELIABLE_STATS = 10;`

    2. For each category row, if `cat.total < MIN_GAMES_FOR_RELIABLE_STATS`, add a visual warning. After the game count span (line 94 area), add an inline warning indicator:
       ```tsx
       {cat.total < MIN_GAMES_FOR_RELIABLE_STATS && (
         <span className="text-xs text-amber-500 ml-1" title="Small sample size — percentages may be unreliable">
           (low sample)
         </span>
       )}
       ```
       Place this next to the "{cat.total} games" text. Also slightly dim the WDL bar for low-sample categories by adding `opacity-50` to the bar container div when `cat.total < MIN_GAMES_FOR_RELIABLE_STATS`.

    **Issue 5 — Q vs Q exclusion note in info tooltip:**

    In `EndgameWDLChart.tsx`, update the `InfoPopover` content (line 63 area) to add a note about the threshold. Append to the existing text:

    ```
    Note: Endgame phase is defined as positions where total material falls below 1500 centipawns
    (roughly a rook and pawns per side). This means queen-vs-queen positions are typically not
    classified as endgames unless significant material has been traded alongside.
    ```

    Keep the existing text before it unchanged.
  </action>
  <verify>
    Run frontend build: `cd /home/aimfeld/Projects/Python/flawchess/frontend && npm run build`
    Run frontend tests: `cd /home/aimfeld/Projects/Python/flawchess/frontend && npm test`
  </verify>
  <done>
    - Summary line "X of Y games (Z%) reached an endgame phase" appears above the chart
    - Categories with fewer than 10 games show "(low sample)" warning text and dimmed bar
    - Info tooltip mentions the 1500cp threshold and Q vs Q implications
    - All changes work on both desktop and mobile layouts
  </done>
</task>

</tasks>

<verification>
1. `uv run pytest tests/ -x -q` — backend tests pass
2. `npm run build` — frontend compiles without errors
3. `npm test` — frontend tests pass
4. Manual: visit /endgames/statistics, click time control filters, verify stats change
5. Manual: verify "X of Y games reached endgame" summary line appears
6. Manual: verify low-sample categories show "(low sample)" warning
7. Manual: click info icon, verify Q vs Q note appears in tooltip
</verification>

<success_criteria>
- Filter clicks on the Endgames page cause statistics to re-fetch and display correctly
- Total games summary line shows endgame reach rate with current filters
- Categories with < 10 games are visually flagged
- Info tooltip explains the 1500cp threshold and Q vs Q implications
- All tests pass, build succeeds
</success_criteria>

<output>
After completion, create `.planning/quick/260326-icg-fix-endgame-analytics-issues-ui-filter-b/260326-icg-SUMMARY.md`
</output>
