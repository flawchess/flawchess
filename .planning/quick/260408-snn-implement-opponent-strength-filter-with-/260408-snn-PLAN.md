---
phase: quick
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  # Backend
  - app/repositories/query_utils.py
  - app/schemas/openings.py
  - app/routers/endgames.py
  - app/routers/stats.py
  - app/services/openings_service.py
  - app/services/endgame_service.py
  - app/services/stats_service.py
  - app/repositories/openings_repository.py
  - app/repositories/endgame_repository.py
  - app/repositories/stats_repository.py
  # Frontend
  - frontend/src/types/api.ts
  - frontend/src/components/filters/FilterPanel.tsx
  - frontend/src/api/client.ts
  - frontend/src/hooks/useOpenings.ts
  - frontend/src/hooks/useNextMoves.ts
  - frontend/src/hooks/useEndgames.ts
  - frontend/src/hooks/useStats.ts
autonomous: true
must_haves:
  truths:
    - "User can select opponent strength filter (Any/Stronger/Similar/Weaker) on the Openings page"
    - "User can select opponent strength filter on the Endgames page"
    - "Selecting Stronger filters to games where opponent rating >= user rating + threshold"
    - "Selecting Similar filters to games where abs(opponent - user) < threshold"
    - "Selecting Weaker filters to games where opponent rating <= user rating - threshold"
    - "Filter defaults to Any (no filtering) and persists across page navigation"
  artifacts:
    - path: app/repositories/query_utils.py
      provides: "opponent_strength + elo_threshold SQL filter logic in apply_game_filters()"
    - path: frontend/src/components/filters/FilterPanel.tsx
      provides: "Opponent Strength toggle group above Rated filter"
  key_links:
    - from: frontend/src/components/filters/FilterPanel.tsx
      to: app/repositories/query_utils.py
      via: "FilterState.opponentStrength -> API param -> apply_game_filters()"
      pattern: "opponent_strength"
---

<objective>
Add an "Opponent Strength" filter with 4 options (Any, Stronger +100, Similar +/-100, Weaker -100) that works across Openings and Endgames tabs.

Purpose: Let users filter their game stats by relative opponent strength to find patterns (e.g., "I lose more with the London against stronger opponents").
Output: Working filter in both Openings and Endgames pages, backed by SQL filtering via `apply_game_filters()`.
</objective>

<execution_context>
@/home/aimfeld/.claude/get-shit-done/workflows/execute-plan.md
@/home/aimfeld/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@app/repositories/query_utils.py
@app/schemas/openings.py
@app/routers/endgames.py
@app/routers/stats.py
@app/services/openings_service.py
@app/services/endgame_service.py
@app/services/stats_service.py
@app/repositories/openings_repository.py
@app/repositories/endgame_repository.py
@app/repositories/stats_repository.py
@frontend/src/types/api.ts
@frontend/src/components/filters/FilterPanel.tsx
@frontend/src/api/client.ts
@frontend/src/hooks/useOpenings.ts
@frontend/src/hooks/useNextMoves.ts
@frontend/src/hooks/useEndgames.ts
@frontend/src/hooks/useStats.ts
@frontend/src/hooks/useFilterStore.ts

<interfaces>
<!-- Key types and contracts the executor needs. -->

From app/repositories/query_utils.py — the ONLY place filter SQL lives:
```python
def apply_game_filters(
    stmt: Any,
    time_control: Sequence[str] | None,
    platform: Sequence[str] | None,
    rated: bool | None,
    opponent_type: str,
    recency_cutoff: datetime.datetime | None,
    color: str | None = None,
) -> Any:
```

All callers (3 repos) pass these positionally. New params MUST be keyword-only to avoid breaking callers.

From app/models/game.py — rating columns available on Game:
```python
user_color: Mapped[str]      # "white" | "black"
white_rating: Mapped[int | None]
black_rating: Mapped[int | None]
```

From frontend FilterPanel — existing FilterState and FilterField types:
```typescript
export interface FilterState {
  matchSide: MatchSide;
  timeControls: TimeControl[] | null;
  platforms: Platform[] | null;
  rated: boolean | null;
  opponentType: OpponentType;
  recency: Recency | null;
  color: Color;
}

type FilterField = 'timeControl' | 'platform' | 'rated' | 'opponent' | 'recency';
const ALL_FILTERS: FilterField[] = ['timeControl', 'platform', 'rated', 'opponent', 'recency'];
```

From frontend client.ts — buildFilterParams maps filter state to query params:
```typescript
function buildFilterParams(params: {
  time_control?: string[] | null;
  platform?: string[] | null;
  recency?: string | null;
  rated?: boolean | null;
  opponent_type?: string;
  window?: number;
}): Record<string, string | string[] | number | boolean> { ... }
```

From frontend useEndgames.ts — buildEndgameParams extracts endgame-relevant filters:
```typescript
function buildEndgameParams(filters: FilterState) {
  return {
    time_control: filters.timeControls,
    platform: filters.platforms,
    recency: filters.recency,
    rated: filters.rated,
    opponent_type: filters.opponentType,
  };
}
```
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Backend — add opponent_strength filtering to apply_game_filters and thread through all layers</name>
  <files>
    app/repositories/query_utils.py
    app/schemas/openings.py
    app/repositories/openings_repository.py
    app/repositories/endgame_repository.py
    app/repositories/stats_repository.py
    app/services/openings_service.py
    app/services/endgame_service.py
    app/services/stats_service.py
    app/routers/endgames.py
    app/routers/stats.py
  </files>
  <action>
**1. `app/repositories/query_utils.py` — Add SQL filtering logic:**

Add two new **keyword-only** parameters to `apply_game_filters()`:
- `opponent_strength: str = "any"` — one of `"any"`, `"stronger"`, `"similar"`, `"weaker"`
- `elo_threshold: int = 100` — the rating difference threshold

The SQL logic uses CASE WHEN to derive user_rating and opponent_rating from `Game.white_rating`, `Game.black_rating`, and `Game.user_color`:

```python
if opponent_strength != "any":
    from sqlalchemy import case
    user_rating = case(
        (Game.user_color == "white", Game.white_rating),
        else_=Game.black_rating,
    )
    opp_rating = case(
        (Game.user_color == "white", Game.black_rating),
        else_=Game.white_rating,
    )
    # Exclude games with missing ratings
    stmt = stmt.where(Game.white_rating.isnot(None), Game.black_rating.isnot(None))
    if opponent_strength == "stronger":
        stmt = stmt.where(opp_rating >= user_rating + elo_threshold)
    elif opponent_strength == "similar":
        stmt = stmt.where(
            opp_rating > user_rating - elo_threshold,
            opp_rating < user_rating + elo_threshold,
        )
    elif opponent_strength == "weaker":
        stmt = stmt.where(opp_rating <= user_rating - elo_threshold)
```

Use the `Literal["any", "stronger", "similar", "weaker"]` type for `opponent_strength` parameter. Import `Literal` from `typing`. The `case` import from `sqlalchemy` should be at the top of the file (not inside the function).

Since these are keyword-only parameters with defaults, existing callers (all 3 repos, ~12 call sites) continue to work unchanged with zero modifications needed just for this function signature change. However, callers DO need updates to pass through the new params from their own callers (services/routers).

**2. `app/schemas/openings.py` — Add filter params to all request schemas:**

Add to `OpeningsRequest`, `NextMovesRequest`, and `TimeSeriesRequest`:
```python
opponent_strength: Literal["any", "stronger", "similar", "weaker"] = "any"
elo_threshold: int = 100
```

**3. Thread through repositories:**

Each repository function that calls `apply_game_filters()` needs the new keyword params. There are three repos:

- `app/repositories/openings_repository.py`: Functions `query_time_series`, `query_wdl_counts`, `query_next_moves`, and `query_positions` (there may be more — grep for `apply_game_filters` in this file). Add `opponent_strength: str = "any"` and `elo_threshold: int = 100` as keyword params to each function signature, and pass them through to `apply_game_filters(..., opponent_strength=opponent_strength, elo_threshold=elo_threshold)`.

- `app/repositories/endgame_repository.py`: Every function that calls `apply_game_filters` (~9 call sites). Same pattern — add keyword params and pass through.

- `app/repositories/stats_repository.py`: Same pattern for all functions calling `apply_game_filters`.

**4. Thread through services:**

- `app/services/openings_service.py`: Functions `analyze`, `get_time_series`, `get_next_moves`. These receive `OpeningsRequest`/`NextMovesRequest`/`TimeSeriesRequest` objects. Extract `request.opponent_strength` and `request.elo_threshold` and pass to repository calls.

- `app/services/endgame_service.py`: Functions `get_endgame_stats`, `get_endgame_games`, `get_endgame_performance`, `get_endgame_timeline`, `get_conv_recov_timeline`. Add `opponent_strength: str = "any"` and `elo_threshold: int = 100` as keyword params and pass through to repository calls.

- `app/services/stats_service.py`: Function `get_most_played_openings`. Same pattern.

**5. Thread through routers (endgames + stats only — openings uses request body):**

- `app/routers/endgames.py`: All 5 endpoints. Add query params:
  ```python
  opponent_strength: str = Query(default="any"),
  elo_threshold: int = Query(default=100),
  ```
  Pass through to service calls.

- `app/routers/stats.py`: `get_most_played_openings` endpoint. Same pattern.

Note: The openings router (`app/routers/openings.py`) does NOT need changes because it receives parameters via Pydantic request body (`OpeningsRequest`, etc.) which already gets the new fields from step 2.

**Type annotations:** Use `Literal["any", "stronger", "similar", "weaker"]` for `opponent_strength` everywhere in schemas and the `apply_game_filters` function. In services, routers, and repositories use `str` (consistent with existing `opponent_type: str` pattern in those layers). Ensure all new function signatures include return type annotations.
  </action>
  <verify>
    <automated>cd /home/aimfeld/Projects/Python/flawchess && uv run ruff check app/ && uv run ty check app/ tests/ && uv run pytest -x</automated>
  </verify>
  <done>
    - `apply_game_filters()` accepts `opponent_strength` and `elo_threshold` keyword args and applies correct SQL WHERE clauses
    - All 3 Pydantic request schemas include the new fields with defaults
    - All repository, service, and router layers thread the params through
    - All existing tests pass (no regressions from parameter threading)
    - ruff and ty checks pass with zero errors
  </done>
</task>

<task type="auto">
  <name>Task 2: Frontend — add Opponent Strength toggle group to FilterPanel and wire through API calls</name>
  <files>
    frontend/src/types/api.ts
    frontend/src/components/filters/FilterPanel.tsx
    frontend/src/api/client.ts
    frontend/src/hooks/useOpenings.ts
    frontend/src/hooks/useNextMoves.ts
    frontend/src/hooks/useEndgames.ts
    frontend/src/hooks/useStats.ts
  </files>
  <action>
**1. `frontend/src/types/api.ts` — Add type:**

```typescript
export type OpponentStrength = 'any' | 'stronger' | 'similar' | 'weaker';
```

**2. `frontend/src/components/filters/FilterPanel.tsx` — Add filter UI and state:**

Add to `FilterState`:
```typescript
opponentStrength: OpponentStrength;  // default "any"
```

Add to `DEFAULT_FILTERS`:
```typescript
opponentStrength: 'any',
```

Add `'opponentStrength'` to the `FilterField` type and `ALL_FILTERS` array. Place it between `'opponent'` (existing) and `'rated'` in the array so it renders above the Rated filter but below the Opponent filter.

Add a new ToggleGroup section in the JSX, placed ABOVE the Rated filter section and BELOW the Opponent section. Use the exact same pattern as the existing Rated and Opponent toggle groups (ToggleGroup with `type="single"`, `variant="outline"`, `size="sm"`):

```tsx
{/* Opponent Strength */}
{show('opponentStrength') && (
  <div>
    <p className="mb-1 text-xs text-muted-foreground">Opponent Strength</p>
    <ToggleGroup
      type="single"
      value={filters.opponentStrength}
      onValueChange={(v) => {
        if (!v) return;
        update({ opponentStrength: v as OpponentStrength });
      }}
      variant="outline"
      size="sm"
      data-testid="filter-opponent-strength"
      className="w-full"
    >
      <ToggleGroupItem value="any" data-testid="filter-opponent-strength-any" className="min-h-11 sm:min-h-0 flex-1">Any</ToggleGroupItem>
      <ToggleGroupItem value="stronger" data-testid="filter-opponent-strength-stronger" className="min-h-11 sm:min-h-0 flex-1 text-xs">+100</ToggleGroupItem>
      <ToggleGroupItem value="similar" data-testid="filter-opponent-strength-similar" className="min-h-11 sm:min-h-0 flex-1 text-xs">&plusmn;100</ToggleGroupItem>
      <ToggleGroupItem value="weaker" data-testid="filter-opponent-strength-weaker" className="min-h-11 sm:min-h-0 flex-1 text-xs">-100</ToggleGroupItem>
    </ToggleGroup>
  </div>
)}
```

Import `OpponentStrength` from `@/types/api`.

The labels are short: "Any", "+100", "±100", "-100". This keeps the 4-option toggle compact. (The section heading "Opponent Strength" provides context.)

**3. `frontend/src/api/client.ts` — Update `buildFilterParams`:**

Add `opponent_strength?: string` to the params type of `buildFilterParams`. Add to the function body:
```typescript
if (params.opponent_strength && params.opponent_strength !== 'any') {
  result.opponent_strength = params.opponent_strength;
}
```

Also update the `endgameApi` object: every method's params type should include `opponent_strength?: string`. Same for `statsApi.getMostPlayedOpenings`.

**4. `frontend/src/hooks/useOpenings.ts` — Pass opponent_strength:**

In the POST body, add:
```typescript
opponent_strength: params.filters.opponentStrength,
```

(The backend default is "any" so sending it always is fine and keeps the code simple.)

**5. `frontend/src/hooks/useNextMoves.ts` — Pass opponent_strength:**

Add to both the queryKey object and the POST body:
```typescript
opponent_strength: filters.opponentStrength,
```

**6. `frontend/src/hooks/useEndgames.ts` — Update `buildEndgameParams`:**

Add to the returned object:
```typescript
opponent_strength: filters.opponentStrength,
```

This flows through to all 5 endgame API calls via `buildFilterParams`.

**7. `frontend/src/hooks/useStats.ts` — Update `useMostPlayedOpenings`:**

Add `opponentStrength` to the filters type parameter and pass `opponent_strength: opponentStrength` to the `statsApi.getMostPlayedOpenings` call. Also add to the queryKey.

**Important:** The `elo_threshold` parameter is NOT sent from the frontend — it defaults to 100 on the backend. The frontend hardcodes the display labels (+100, +/-100, -100) matching this default. If the threshold needs to change later, it's a single backend constant change + frontend label update.
  </action>
  <verify>
    <automated>cd /home/aimfeld/Projects/Python/flawchess/frontend && npm run build && npm run lint && npm test</automated>
  </verify>
  <done>
    - "Opponent Strength" toggle group renders above "Rated" in FilterPanel with 4 options (Any, +100, +/-100, -100)
    - Default is "Any" (no filtering)
    - Filter state persists across Openings/Endgames navigation via useFilterStore
    - All API calls (openings positions, next-moves, endgame stats/games/performance/timeline/conv-recov, most-played-openings) include opponent_strength parameter
    - data-testid attributes present on all toggle items
    - npm build, lint, and tests pass
  </done>
</task>

<task type="checkpoint:human-verify" gate="blocking">
  <what-built>Opponent Strength filter (Any / +100 / +/-100 / -100) working across Openings and Endgames tabs</what-built>
  <how-to-verify>
    1. Start dev servers: `bin/run_local.sh`
    2. Navigate to the Openings page
    3. Verify "Opponent Strength" toggle group appears above the "Rated" filter with 4 options: Any, +100, +/-100, -100
    4. Default should be "Any" (highlighted)
    5. Select "Stronger (+100)" — game counts and WDL stats should change (likely fewer games)
    6. Select "Weaker (-100)" — stats should change again
    7. Select "Similar (+/-100)" — should show games against similarly-rated opponents
    8. Navigate to the Endgames tab — filter should persist and affect endgame stats
    9. On mobile viewport: verify the filter appears in the mobile drawer and is usable
    10. Reset to "Any" — all original data should return
  </how-to-verify>
  <resume-signal>Type "approved" or describe issues</resume-signal>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| client->API | opponent_strength and elo_threshold are user-controlled query/body params |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-quick-01 | T (Tampering) | opponent_strength param | mitigate | Pydantic Literal["any","stronger","similar","weaker"] validates on POST bodies; Query param validated by SQL logic (non-matching values produce no WHERE clause = "any" behavior). No injection risk — values are compared as column expressions, not interpolated. |
| T-quick-02 | T (Tampering) | elo_threshold param | accept | Integer type enforced by Pydantic. Extreme values (e.g. 99999) produce empty result sets, which is harmless. No business reason to constrain the range. |
| T-quick-03 | I (Info Disclosure) | Rating comparison | accept | Users only see their own game data (user_id filter always applied). The opponent strength filter reveals no new data — it just subsets existing visible games. |
</threat_model>

<verification>
```bash
# Backend
cd /home/aimfeld/Projects/Python/flawchess
uv run ruff check app/
uv run ty check app/ tests/
uv run pytest -x

# Frontend
cd frontend
npm run build
npm run lint
npm test
```
</verification>

<success_criteria>
- Opponent Strength filter (Any/Stronger/Similar/Weaker) visible in FilterPanel on both Openings and Endgames pages
- Filter applies correct SQL filtering based on rating difference using CASE WHEN on white_rating/black_rating/user_color
- Games with missing ratings are excluded when any non-"Any" option is selected
- Default "Any" produces identical results to pre-change behavior (no regression)
- Filter state persists across SPA navigation via useFilterStore
- All backend tests, linting, type checking pass
- All frontend build, lint, tests pass
</success_criteria>

<output>
After completion, create `.planning/quick/260408-snn-implement-opponent-strength-filter-with-/260408-snn-SUMMARY.md`
</output>
