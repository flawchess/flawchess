# Phase 36: Most Played Openings - Research

**Researched:** 2026-03-28
**Domain:** FastAPI aggregation endpoint + React WDL chart integration
**Confidence:** HIGH

## Summary

Phase 36 adds a "Most Played Openings" section to the top of the Opening Statistics subtab. It
shows the user's top 5 most played openings by game count, separated by color (White / Black), as
WDL charts — the same `WDLChartRow` component already used in the "Results by Opening" section.

The data source is the `games` table, which already stores `opening_eco` (String(10)) and
`opening_name` (String(200)) on every imported game. A simple GROUP BY aggregation query on those
two columns, filtered by `user_color` and grouped by `(opening_eco, opening_name)`, produces the
top-N openings with WDL counts in one SQL pass. No new database columns or migrations are needed.

The feature slots cleanly into the existing `stats_repository` / `stats_service` / `stats_router`
stack. A new endpoint `GET /stats/most-played-openings` accepts the same filter parameters
(`recency`, `platform`) already wired in `stats_service`. On the frontend, a new `useQuery` call
fetches the data and renders it above the existing "Results by Opening" section in
`statisticsContent` inside `Openings.tsx`. The `WDLChartRow` component is already the correct
shape; the response payload maps directly onto `WDLRowData`.

**Primary recommendation:** Add a single new GET endpoint, a repository function with GROUP BY
aggregation, a Pydantic response schema, and render the result in `Openings.tsx` using the shared
`WDLChartRow`. No new components, no migrations.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| MPO-01 | "Most Played Openings: White" and "Most Played Openings: Black" sections appear at the top of the Opening Statistics subtab in a shared charcoal container | `statisticsContent` in `Openings.tsx` — prepend above existing charcoal blocks; use `charcoal-texture rounded-md p-4` |
| MPO-02 | Each section lists the top 5 openings by game count, based on `opening_eco`/`opening_name` from the games table | Single GROUP BY query on `games`; ORDER BY COUNT(*) DESC LIMIT 5 per color |
| MPO-03 | Openings with fewer than 10 games are excluded; if no openings meet the threshold, an explanatory message is shown | Filter `HAVING COUNT(*) >= MIN_GAMES_THRESHOLD` in repository; empty list triggers no-data message in UI |
| MPO-04 | Openings are displayed as WDL charts (same component as "Results by Opening") with ECO code in parentheses in the title | `WDLChartRow` with `label` prop = `"Opening Name (ECO)"` |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| SQLAlchemy 2.x async | 2.x (project-wide) | GROUP BY aggregation query | Already project ORM; `func.count()`, `case()`, `.group_by()`, `.having()`, `.order_by()` |
| FastAPI | 0.115.x (project-wide) | New GET endpoint | Already project framework |
| Pydantic v2 | v2 (project-wide) | Response schema | Project-wide validation standard |
| TanStack Query | project-wide | Frontend data fetching | `useQuery` already used for all stats |
| WDLChartRow | Phase 35 output | WDL bar chart rendering | Shared component, satisfies `WDLRowData` |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `derive_user_result` (analysis_service) | internal | Map `result` + `user_color` to win/draw/loss | Import for aggregation logic in stats_service |

**No new installations required.** All dependencies are already present.

## Architecture Patterns

### Backend pattern: stats_repository + stats_service + stats_router

The existing stats stack follows this exact three-layer split:

```
stats_repository.py   — raw SQL query returning list[tuple]
stats_service.py      — aggregation + WDLByCategory construction
stats_router.py       — HTTP GET endpoint, delegates to service
schemas/stats.py      — Pydantic response models
```

Add one function to each layer. Reuse `WDLByCategory` as the item schema (it has `label`, `wins`,
`draws`, `losses`, `total`, `win_pct`, `draw_pct`, `loss_pct` — exactly what the UI needs).

### Repository query pattern

```python
# Source: existing analysis_repository._build_base_query + stats_repository patterns
from sqlalchemy import case, func, select
from app.models.game import Game
from app.services.analysis_service import derive_user_result  # NOT used in SQL — used post-fetch

# Pure SQL aggregation — faster than fetching all rows and aggregating in Python
stmt = (
    select(
        Game.opening_eco,
        Game.opening_name,
        func.count().label("game_count"),
        func.sum(case((Game.result == "1-0", case((Game.user_color == "white", 1), else_=0)),
                      else_=case((Game.result == "0-1", case((Game.user_color == "black", 1), else_=0)),
                                 else_=0))).label("wins"),
        # ... draws, losses
    )
    .where(
        Game.user_id == user_id,
        Game.user_color == color,
        Game.opening_eco.is_not(None),
        Game.opening_name.is_not(None),
    )
    .group_by(Game.opening_eco, Game.opening_name)
    .having(func.count() >= min_games)
    .order_by(func.count().desc())
    .limit(limit)
)
```

**Alternative aggregation approach** (simpler, avoids complex SQL CASE): fetch
`(opening_eco, opening_name, result, user_color)` rows in one query (no GROUP BY), then aggregate
in Python using the existing `_aggregate_wdl` helper from `stats_service`. This matches the
established pattern for `by_time_control` and `by_color` in `get_global_stats`.

**Recommendation: use the Python aggregation approach** — it is consistent with the existing
codebase style, avoids SQL CASE complexity, and performance is fine for the top-5 use case (not
millions of rows returned, just filtered game results).

### Recommended Project Structure additions

```
app/
├── repositories/stats_repository.py    # add query_top_openings_by_color()
├── services/stats_service.py           # add get_most_played_openings()
├── routers/stats.py                    # add GET /stats/most-played-openings
└── schemas/stats.py                    # add MostPlayedOpeningsResponse

frontend/src/
├── api/client.ts                       # add statsApi.getMostPlayedOpenings()
├── hooks/useStats.ts                   # add useMostPlayedOpenings()
├── types/stats.ts                      # add MostPlayedOpeningsResponse type
└── pages/Openings.tsx                  # add section at top of statisticsContent
```

### Frontend rendering pattern

The `statisticsContent` block in `Openings.tsx` currently starts with the bookmarks check and
the "Results by Opening" charcoal block. The Most Played Openings sections go **before** these
existing blocks, still inside the `flex flex-col gap-4` wrapper.

Both White and Black sections share a single `charcoal-texture rounded-md p-4` container (per
success criterion 1: "shared charcoal container").

```tsx
// Pattern: single charcoal container, two subsections
<div className="charcoal-texture rounded-md p-4" data-testid="most-played-openings">
  <h2 className="text-lg font-medium mb-3">Most Played Openings</h2>
  <div className="space-y-6">
    {/* White section */}
    <div>
      <h3 className="text-base font-medium mb-2">White</h3>
      {whiteOpenings.length === 0
        ? <p className="text-sm text-muted-foreground">...</p>
        : <div className="space-y-2">
            {whiteOpenings.map(o => (
              <WDLChartRow
                key={`${o.opening_eco}-${o.label}`}
                data={o}
                label={o.label}
                maxTotal={maxTotalWhite}
                testId={`mpo-white-${o.opening_eco}`}
              />
            ))}
          </div>
      }
    </div>
    {/* Black section */}
    ...
  </div>
</div>
```

Label format: `"King's Indian Defense (E97)"` — opening name first, ECO code in parentheses.

### Anti-Patterns to Avoid
- **Separate charcoal containers for White/Black:** success criterion says "shared container"
- **Custom WDL rendering:** always delegate to `WDLChartRow`, never inline bar markup
- **Filtering by `color` from FilterPanel:** the Openings page `FilterPanel` `color` field is for
  board-side analysis, not this feature. The Most Played Openings feature ignores the board filters
  entirely — it always shows both colors. No color filter prop should be wired.
- **Hard-coding `10` as the minimum games threshold:** extract to a named constant
  `MIN_GAMES_FOR_OPENING = 10` (same value as `MIN_GAMES_FOR_RELIABLE_STATS` in `theme.ts`, but
  a separate backend constant to keep concerns separated — the frontend constant controls dimming,
  the backend constant controls exclusion).
- **Nullable opening_eco/opening_name rows:** both columns are nullable in the `Game` model.
  Always filter `Game.opening_eco.is_not(None), Game.opening_name.is_not(None)` in the repository
  query, otherwise NULL-grouped rows pollute the top-5.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| WDL bar rendering | Custom bar markup | `WDLChartRow` | Phase 35 built this exactly for this use case |
| WDL aggregation | Custom win/draw/loss counting | `_aggregate_wdl` from stats_service or derive_user_result | Established pattern, tested |
| Filter wiring | Custom query param parsing | `recency_cutoff()` from analysis_service | Used by all other stats endpoints |

## Common Pitfalls

### Pitfall 1: NULL opening_eco / opening_name
**What goes wrong:** Games imported before the opening lookup was wired, or games where the
platform didn't provide an opening, have NULL in both columns. A GROUP BY without filtering NULLs
returns a NULL bucket that counts as a "top opening" and breaks the display.
**Why it happens:** `opening_eco` and `opening_name` are both `Mapped[str | None]` (nullable).
**How to avoid:** Always `.where(Game.opening_eco.is_not(None), Game.opening_name.is_not(None))`
before the GROUP BY.
**Warning signs:** A WDL row labeled "None" or empty string appearing in top results.

### Pitfall 2: opening_eco + opening_name cardinality mismatch
**What goes wrong:** The same ECO code (e.g. "E60") can cover multiple openings (King's Indian
main line vs. side variations), and the same opening name might theoretically appear under
different ECO codes. Grouping by both columns is correct — GROUP BY just `opening_eco` would
collapse distinct variations into one bucket.
**Why it happens:** Chess opening taxonomy is hierarchical; ECO codes are not unique to one name.
**How to avoid:** Always `GROUP BY Game.opening_eco, Game.opening_name` (both columns).

### Pitfall 3: Forgetting mobile variant of statisticsContent
**What goes wrong:** The Statistics tab content is rendered in two places in `Openings.tsx`:
once in the desktop two-column layout (lines ~619) and once in the mobile single-column layout
(lines ~834). The `statisticsContent` variable is defined once and referenced in both, so a
single change propagates. But if the variable is ever split, the mobile variant would be missed.
**Why it happens:** CLAUDE.md explicitly calls this out: "always check mobile variants."
**How to avoid:** Verify both `<TabsContent value="compare">` occurrences reference the same
`statisticsContent` variable. In the current architecture, a single variable is shared — no
duplication needed.

### Pitfall 4: Applying Openings FilterPanel filters to this feature
**What goes wrong:** The Statistics tab shares the `debouncedFilters` state with the board
explorer (time controls, platform, color, recency, etc.). If those filters are wired to the
Most Played Openings query, the feature becomes less discoverable and confusing (e.g. showing
"top 5 blitz openings" when the user is exploring rapid positions).
**Why it happens:** Easy to accidentally pass `debouncedFilters` to the new hook call.
**How to avoid:** The phase description says this feature shows top 5 based purely on game count
from the games table. Do NOT pass time_control, platform, or recency filters from FilterPanel.
The endpoint should accept no filters beyond auth (or optionally recency/platform for consistency
— but this must be an explicit product decision, not an accidental wire-up).

**Clarification needed:** The phase description does not explicitly say whether the existing
FilterPanel's recency/platform filters should affect the Most Played Openings section. Given that
the "Results by Opening" section (bookmarks WDL) is also unfiltered by those panel filters, the
safe default is: **no filters** — show all-time top 5 for the authenticated user. Flag this
for confirmation if the user has different expectations.

### Pitfall 5: Missing data-testid attributes
**What goes wrong:** CLAUDE.md requires `data-testid` on every interactive element and major
layout container.
**How to avoid:** Add `data-testid="most-played-openings"` on the outer container,
`data-testid="mpo-white-section"` / `data-testid="mpo-black-section"` on subsections,
and `data-testid={`mpo-white-${opening_eco}`}` / `data-testid={`mpo-black-${opening_eco}`}` on
each `WDLChartRow`.

## Code Examples

### Repository function (Python aggregation approach)

```python
# Source: stats_repository.py (new function, following existing query style)
async def query_top_openings_by_color(
    session: AsyncSession,
    user_id: int,
    color: str,  # "white" | "black"
    min_games: int,
    limit: int,
) -> list[tuple]:
    """Return (opening_eco, opening_name, result, user_color) rows for games
    with the top N opening_eco/opening_name combos by count (>= min_games).

    Returns raw rows for Python-side aggregation consistent with
    query_results_by_time_control / query_results_by_color patterns.
    """
    # Subquery: find top-N (eco, name) pairs by game count, min threshold
    top_stmt = (
        select(
            Game.opening_eco,
            Game.opening_name,
            func.count().label("game_count"),
        )
        .where(
            Game.user_id == user_id,
            Game.user_color == color,
            Game.opening_eco.is_not(None),
            Game.opening_name.is_not(None),
        )
        .group_by(Game.opening_eco, Game.opening_name)
        .having(func.count() >= min_games)
        .order_by(func.count().desc())
        .limit(limit)
        .subquery()
    )

    # Main query: fetch result rows for those top openings
    stmt = (
        select(
            Game.opening_eco,
            Game.opening_name,
            Game.result,
            Game.user_color,
        )
        .join(
            top_stmt,
            (Game.opening_eco == top_stmt.c.opening_eco)
            & (Game.opening_name == top_stmt.c.opening_name),
        )
        .where(
            Game.user_id == user_id,
            Game.user_color == color,
        )
    )

    result = await session.execute(stmt)
    return list(result.fetchall())
```

### Service function

```python
# Source: stats_service.py (new function, following get_global_stats pattern)
MIN_GAMES_FOR_OPENING = 10
TOP_OPENINGS_LIMIT = 5

async def get_most_played_openings(
    session: AsyncSession,
    user_id: int,
) -> MostPlayedOpeningsResponse:
    white_rows = await query_top_openings_by_color(
        session, user_id, color="white",
        min_games=MIN_GAMES_FOR_OPENING, limit=TOP_OPENINGS_LIMIT
    )
    black_rows = await query_top_openings_by_color(
        session, user_id, color="black",
        min_games=MIN_GAMES_FOR_OPENING, limit=TOP_OPENINGS_LIMIT
    )
    # Aggregate with existing helper
    white = _aggregate_top_openings(white_rows)
    black = _aggregate_top_openings(black_rows)
    return MostPlayedOpeningsResponse(white=white, black=black)
```

### Pydantic schema

```python
# Source: schemas/stats.py (new model)
class OpeningWDL(BaseModel):
    """WDL stats for a single opening, with ECO and display label."""
    opening_eco: str
    opening_name: str
    label: str          # "Opening Name (ECO)" — precomputed for UI
    wins: int
    draws: int
    losses: int
    total: int
    win_pct: float
    draw_pct: float
    loss_pct: float

class MostPlayedOpeningsResponse(BaseModel):
    white: list[OpeningWDL]
    black: list[OpeningWDL]
```

### Frontend type

```typescript
// types/stats.ts (addition)
export interface OpeningWDL {
  opening_eco: string;
  opening_name: string;
  label: string;
  wins: number;
  draws: number;
  losses: number;
  total: number;
  win_pct: number;
  draw_pct: number;
  loss_pct: number;
}

export interface MostPlayedOpeningsResponse {
  white: OpeningWDL[];
  black: OpeningWDL[];
}
```

`OpeningWDL` structurally satisfies `WDLRowData` (duck typing, consistent with Phase 35 decisions).

## State of the Art

| Old Approach | Current Approach | Impact |
|--------------|------------------|--------|
| Inline WDL bar markup per chart type | Shared `WDLChartRow` (Phase 35) | New charts must use `WDLChartRow`, not custom markup |
| Direct color constants in components | Centralized `theme.ts` | New components import from `theme.ts` |

## Open Questions

1. **Should FilterPanel (recency/platform) affect Most Played Openings?**
   - What we know: "Results by Opening" (bookmark WDL) is unfiltered by the panel
   - What's unclear: Whether users expect filtered or all-time top 5
   - Recommendation: Default to no filters (all-time, all platforms) for consistency with the
     bookmark section. If the user wants filters, it can be added as a follow-up.

## Environment Availability

Step 2.6: SKIPPED — this phase is code/config changes only; no new external tools, databases, or
CLI utilities are required beyond the existing Docker PostgreSQL dev environment.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest + pytest-asyncio |
| Config file | `pyproject.toml` (project root) |
| Quick run command | `uv run pytest tests/test_stats_repository.py tests/test_stats_router.py -x` |
| Full suite command | `uv run pytest` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| MPO-02 | `query_top_openings_by_color` returns top 5 by game count | unit | `uv run pytest tests/test_stats_repository.py -x -k top_openings` | ❌ Wave 0 |
| MPO-03 | Openings with < 10 games excluded from results | unit | `uv run pytest tests/test_stats_repository.py -x -k min_games` | ❌ Wave 0 |
| MPO-03 | Empty list returned when no opening meets threshold | unit | `uv run pytest tests/test_stats_repository.py -x -k no_openings` | ❌ Wave 0 |
| MPO-01/04 | `GET /stats/most-played-openings` returns 200 with correct structure | integration | `uv run pytest tests/test_stats_router.py -x -k most_played` | ❌ Wave 0 |
| MPO-01/04 | `GET /stats/most-played-openings` returns 401 without auth | integration | `uv run pytest tests/test_stats_router.py -x -k most_played` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/test_stats_repository.py tests/test_stats_router.py -x`
- **Per wave merge:** `uv run pytest`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_stats_repository.py` — add `TestQueryTopOpeningsByColor` class (new test class in existing file)
- [ ] `tests/test_stats_router.py` — add `TestGetMostPlayedOpenings` class (new test class in existing file)

No new test files needed — extend existing stats test files.

## Project Constraints (from CLAUDE.md)

- **No magic numbers:** `MIN_GAMES_FOR_OPENING = 10` and `TOP_OPENINGS_LIMIT = 5` must be named constants in `stats_service.py` (backend) and mirrored as named constants in the frontend component.
- **Theme constants in theme.ts:** No new color values needed — `WDLChartRow` reads from `theme.ts` internally.
- **Type safety:** `OpeningWDL` must be an explicit TypeScript interface; no `any`. Use `Literal["white", "black"]` for the color parameter in the backend function signature.
- **data-testid on all interactive/layout elements:** containers and each `WDLChartRow` row must have `data-testid`.
- **Always check mobile variants:** `statisticsContent` is shared between desktop and mobile tabs — one variable, referenced twice. No duplication needed, but verify both `<TabsContent value="compare">` blocks reference it.
- **SQLAlchemy 2.x async:** use `select()` API, not legacy 1.x style.
- **No SQLite:** PostgreSQL only (Docker dev environment).
- **httpx.AsyncClient only:** no `requests` library.
- **Pydantic v2 throughout:** `BaseModel` with v2 semantics.
- **Foreign key constraints mandatory:** no bare integer columns as implicit references — not applicable for this read-only feature.
- **API responses never expose internal hashes:** not applicable (no hashes in this feature).

## Sources

### Primary (HIGH confidence)
- Direct codebase inspection: `app/models/game.py` — `opening_eco` (String(10), nullable), `opening_name` (String(200), nullable) confirmed
- Direct codebase inspection: `app/repositories/stats_repository.py` — Python aggregation pattern confirmed
- Direct codebase inspection: `app/services/stats_service.py` — `_aggregate_wdl` helper pattern confirmed
- Direct codebase inspection: `frontend/src/components/charts/WDLChartRow.tsx` — `WDLRowData` interface, `label` prop, `maxTotal` prop confirmed
- Direct codebase inspection: `frontend/src/pages/Openings.tsx` — `statisticsContent` structure, charcoal-texture pattern, mobile/desktop tab rendering confirmed
- Direct codebase inspection: `frontend/src/lib/theme.ts` — `MIN_GAMES_FOR_RELIABLE_STATS = 10` confirmed

### Secondary (MEDIUM confidence)
- Phase 35 STATE.md notes: `WDLRowData` uses structural duck-typing — `WDLStats`, `WDLByCategory`, `EndgameWDLSummary` all satisfy the interface without explicit `implements`
- Phase 35 STATE.md notes: `WDLChartRow` default `barHeight` is `h-5`

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries are project-wide, no new dependencies
- Architecture: HIGH — repository/service/router pattern is established and directly inspected
- Pitfalls: HIGH — NULL column behavior and mobile variant concerns verified from codebase
- Frontend integration: HIGH — `WDLChartRow` props and `statisticsContent` structure directly inspected

**Research date:** 2026-03-28
**Valid until:** 2026-04-28 (stable codebase, no fast-moving external dependencies)
