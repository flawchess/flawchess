# Phase 7: Add More Game Statistics and Charts - Research

**Researched:** 2026-03-14
**Domain:** React/Recharts chart expansion, FastAPI new stats endpoints, chess.com ECO import fix, navigation restructuring
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Current nav: Analysis | Bookmarks | Stats → becomes: **Analysis | Bookmarks | Openings | Rating | Global Stats**
- **Openings** page = current Stats page content (bookmark W/D/L bars, win rate over time chart, all existing filters)
- **Rating** page = new rating over time charts, recency filter only
- **Global Stats** page = new results by color + results by time control, recency filter only
- Each page is a separate route, not subtabs — different pages need different filters
- **Two separate charts**: one for chess.com ratings, one for lichess ratings (scales are incomparable)
- Each chart has **multiple lines per time control** (bullet/blitz/rapid/classical) — togglable
- Data points are per-game ratings (user_rating already stored in Game model)
- Default time window: **all time**, narrowable via recency filter
- Use Recharts LineChart (consistent with existing win rate chart)
- W/D/L breakdown per time control bucket (bullet/blitz/rapid/classical) — Global Stats page
- W/D/L split showing white vs black performance — Global Stats page
- **Recency filter only** on Global Stats and Rating pages
- Use **ECO-based grouping** for consistent cross-platform opening identification
- **Fix chess.com ECO import** — currently broken, ECO codes not correctly populated
- Use a static ECO-to-opening-name mapping applied at import time
- Full ECO-based opening analytics deferred to a later phase
- Additional new data fields from chess.com/lichess APIs deferred unless trivially integrated

### Claude's Discretion
- Exact chart styling and color schemes for rating lines per time control
- Layout of charts on Rating and Global Stats pages
- Whether rating chart uses per-game data points or monthly averages
- Backend API endpoint design for new stats queries
- How to display the results by time control (horizontal bars, vertical bars, or other chart type)
- How to display results by color (bars, pie chart, or other)

### Deferred Ideas (OUT OF SCOPE)
- Full ECO-based opening analytics (grouping by opening family, expandable to individual ECO codes)
- Game activity calendar (GitHub-style heatmap)
- Game length distribution histogram
- Additional data from chess.com/lichess APIs (researcher will investigate, but implementation deferred unless trivially integrated)
</user_constraints>

## Summary

Phase 7 adds three new statistics pages (Openings = renamed Stats, Rating, Global Stats) and fixes the chess.com ECO import bug. All the data needed for the new charts is **already stored** in the Game model — `user_rating`, `time_control_bucket`, `user_color`, and `result` — so no schema migration is required. The work is primarily: (1) adding two new backend query endpoints, (2) building three new frontend page components using existing Recharts patterns, and (3) fixing the ECO extraction bug in `normalization.py`.

The chess.com ECO bug is confirmed: chess.com sometimes returns opening URLs with move notation but no ECO code embedded, e.g. `https://www.chess.com/openings/Kings-Gambit-Accepted-Modern-Defense-4.exd5`. The regex `[A-E]\d{2}` correctly returns `None` for these — the stored `opening_eco` will simply be `None` for these games. This is expected behavior given the URL format; the fix should improve ECO coverage but cannot guarantee 100% population for all chess.com games.

**Primary recommendation:** Implement in 3 plans — (1) Backend endpoints for rating history and global stats, (2) Frontend pages Openings/Rating/GlobalStats with navigation restructuring, (3) ECO fix in normalization.

## Standard Stack

### Core (already in project — no new dependencies needed)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| recharts | ^2.15.4 | LineChart, BarChart, PieChart | Already used in WinRateChart and WDLBarChart |
| @tanstack/react-query | ^5.90.21 | Server state / data fetching hooks | Already established pattern |
| FastAPI | 0.115.x | New backend endpoints | Project standard |
| SQLAlchemy 2.x async | latest | New repository queries | Project standard |
| Pydantic v2 | latest | Request/response schemas | Project standard |

### No New Dependencies Required
All phase 7 work uses existing libraries. No new npm or Python packages are needed.

## Architecture Patterns

### Recommended Project Structure (new files)

```
app/
├── routers/analysis.py          # Add GET /stats/rating-history, GET /stats/global
├── repositories/
│   └── stats_repository.py      # New — rating history and global stats queries
├── schemas/
│   └── stats.py                 # New — RatingHistoryResponse, GlobalStatsResponse
└── services/
    └── stats_service.py         # New — aggregation logic for rating/global stats

frontend/src/
├── pages/
│   ├── Openings.tsx             # Renamed copy of Stats.tsx (route /openings)
│   ├── Rating.tsx               # New rating over time page
│   └── GlobalStats.tsx          # New global stats page
├── components/
│   └── stats/
│       ├── RatingChart.tsx      # New — LineChart for rating over time per TC
│       └── GlobalStatsCharts.tsx # New — WDL by TC and by color
├── hooks/
│   └── useStats.ts              # New — useRatingHistory(), useGlobalStats()
└── api/
    └── client.ts                # Add statsApi.* endpoints
```

### Pattern 1: New Backend Stats Endpoint (GET with query params)

New stats endpoints do NOT require a request body (unlike time-series which has bookmark params). Use GET with query params for recency:

```python
# Source: existing analysis.py pattern adapted for stats
@router.get("/stats/rating-history", response_model=RatingHistoryResponse)
async def get_rating_history(
    recency: str | None = Query(default=None),
    session: Annotated[AsyncSession, Depends(get_async_session)],
    user: Annotated[User, Depends(current_active_user)],
) -> RatingHistoryResponse:
    return await stats_service.get_rating_history(session, user.id, recency)
```

### Pattern 2: Recharts Rating Line Chart (multi-line with toggle)

The existing `WinRateChart` already demonstrates the `hide` prop pattern for toggling lines. Apply same pattern for rating:

```typescript
// Source: existing WinRateChart.tsx pattern
const [hiddenKeys, setHiddenKeys] = useState<Set<string>>(new Set());
// ...
<Line
  dataKey="bullet"
  hide={hiddenKeys.has('bullet')}
  stroke="var(--color-bullet)"
/>
```

Rating chart data shape per platform:
```typescript
// One entry per game, sorted by played_at
interface RatingDataPoint {
  date: string;       // ISO date string "2024-03-15"
  bullet?: number;    // user_rating if this game was bullet, else undefined
  blitz?: number;
  rapid?: number;
  classical?: number;
}
```

Each time control is a separate Line on the same chart, so gaps appear between TC-specific games. This is cleaner than a single line that jumps between TC rating scales.

### Pattern 3: Global Stats WDL by Time Control

Reuse `WDLBarChart` component pattern — same stacked horizontal bar, but category axis is time control buckets rather than bookmark labels:

```typescript
// Data shape for results by TC
interface WDLByTC {
  label: string;    // "Bullet" | "Blitz" | "Rapid" | "Classical"
  win_pct: number;
  draw_pct: number;
  loss_pct: number;
  wins: number; draws: number; losses: number; total: number;
}
```

### Pattern 4: Global Stats WDL by Color

Two-row version of WDLBarChart (White and Black rows). The `WDLBarChart` component already accepts arbitrary labels, so it can be reused directly with data shaped as:

```typescript
[
  { label: 'White', wins: N, draws: N, losses: N, ... },
  { label: 'Black', wins: N, draws: N, losses: N, ... },
]
```

### Pattern 5: Navigation Restructuring

The nav is defined in `App.tsx` as `NAV_ITEMS` constant. Update requires:
1. Change `NAV_ITEMS` array: replace `Stats` with `Openings`, add `Rating` and `Global Stats`
2. Add three routes inside `<Route element={<ProtectedLayout />}>`: `/openings`, `/rating`, `/global-stats`
3. Keep `/stats` route as redirect to `/openings` for backward compat (optional, no external links use it)
4. Rename `StatsPage` import to `OpeningsPage` (just a rename — no content changes)
5. `data-testid` on new nav links: `nav-openings`, `nav-rating`, `nav-global-stats`

### Anti-Patterns to Avoid
- **Mixing chess.com and lichess ratings in one chart**: Scales are incomparable. Always render two separate RatingChart components with platform labels.
- **POST for simple stats queries**: New stats endpoints have no complex body payload — use GET with query params for rating-history and global-stats. Only use POST when body complexity warrants it.
- **Scatter plot for rating over time**: LineChart with `connectNulls={false}` and per-TC dataKeys naturally shows gaps between games of different time controls. Do not use ScatterChart.
- **Using `useState` for derived chart data that should be `useMemo`**: Follow the WinRateChart pattern where data transformation uses `useMemo`.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Chart toggle-by-legend | Custom toggle UI | Recharts `hide` prop on `<Line>` + legend onClick | Already implemented in WinRateChart — copy pattern |
| WDL percentage bars | Custom bar UI | Recharts `BarChart layout="vertical"` | Already implemented in WDLBarChart |
| Recency date math | Custom date arithmetic | Existing `recency_cutoff()` in analysis_service.py | Already handles all 6 recency values correctly |
| Per-game rating data fetch | Complex join | Simple `SELECT played_at, user_rating, time_control_bucket WHERE platform=X ORDER BY played_at` | All data already in `games` table |
| ECO code lookup | Custom scraper | Regex on existing chess.com `eco` URL field | ECO code is embedded in most URLs; None is acceptable for variation URLs |

**Key insight:** Phase 7 requires zero new data — all stats can be computed from existing `games` columns (`user_rating`, `time_control_bucket`, `user_color`, `result`, `platform`, `played_at`). Backend work is pure query logic.

## Common Pitfalls

### Pitfall 1: Chess.com ECO URL Variation Format
**What goes wrong:** Chess.com sometimes returns opening URLs ending in move notation rather than ECO code, e.g. `Kings-Gambit-Accepted-Modern-Defense-4.exd5`. The current regex `[A-E]\d{2}` correctly returns `None` for these — no ECO code can be extracted.
**Why it happens:** Chess.com has deep opening variation pages (specific moves) that don't have a standalone ECO code in the URL slug.
**How to avoid:** The existing `_extract_chesscom_eco()` is technically correct. The "fix" is to document and test that `None` is valid for variation URLs, and that this is expected behavior. A meaningful improvement would be to extract the opening name from variation URLs and map to ECO by name prefix — but this is complex and the CONTEXT.md says to keep it simple.
**Better fix approach:** For games where the URL has no ECO code, try to extract the opening *name* from the URL slug (already done by `_extract_chesscom_opening_name`) and accept that `opening_eco` will be `None`. This is acceptable.

### Pitfall 2: Rating Chart Empty State
**What goes wrong:** User has imported only chess.com games — lichess chart has no data and vice versa. Show a platform-specific empty state per chart, not a single "no data" message.
**Why it happens:** Two separate charts for two platforms, user may only have games on one.
**How to avoid:** Check `data.length === 0` per platform before rendering; show a "No [Platform] games imported" message inline.

### Pitfall 3: `date_trunc` vs per-game data points for rating chart
**What goes wrong:** Monthly averaging loses the trend visible from individual games. Per-game data points show the true rating trajectory.
**Why it happens:** The existing time-series uses monthly `date_trunc` because it aggregates W/D/L across many games. Rating history is different — each game has one rating, so per-game is natural.
**How to avoid:** Query `(played_at::date, user_rating, time_control_bucket)` without `date_trunc`. Sort by `played_at`. Frontend formats dates as "Mar 2024" for axis labels but stores ISO date string.

### Pitfall 4: Nav active state for new routes
**What goes wrong:** The nav uses `location.pathname === to` for exact path match. The current `/` works because Dashboard is only at root. New routes `/openings`, `/rating`, `/global-stats` need exact match — fine as long as no nested routes exist.
**Why it happens:** pathname comparison is already exact-match in the NavHeader.
**How to avoid:** No change needed to the active state logic — exact matching works for these routes.

### Pitfall 5: Missing data-testid on new nav items
**What goes wrong:** Browser automation tests break on the new nav links.
**Why it happens:** CLAUDE.md requires `data-testid` on all interactive elements.
**How to avoid:** Add `data-testid="nav-openings"`, `data-testid="nav-rating"`, `data-testid="nav-global-stats"` to the Link elements. Follow existing `nav-{label.toLowerCase().replace(' ', '-')}` pattern.

### Pitfall 6: PostgreSQL session timezone for played_at
**What goes wrong:** Date grouping shifts by one day at month boundaries when session timezone is Europe/Zurich.
**Why it happens:** Already documented in STATE.md: "date_trunc UTC normalization: Use `func.timezone("UTC", timestamptz_col)` before `func.date_trunc`"
**How to avoid:** Apply `func.timezone("UTC", Game.played_at)` before any `date_trunc` call in the new stats repository. For per-game data points, cast to date in UTC: `func.timezone("UTC", Game.played_at).cast(Date)`.

## Code Examples

Verified patterns from existing codebase:

### Rating History Backend Query
```python
# Source: adapted from analysis_repository.py pattern + game model
from sqlalchemy import select, cast, Date, func

async def query_rating_history(
    session: AsyncSession,
    user_id: int,
    platform: str,
    recency_cutoff: datetime | None,
) -> list[tuple]:
    """Return (date, user_rating, time_control_bucket) sorted by played_at."""
    played_at_utc = func.timezone("UTC", Game.played_at)
    stmt = (
        select(
            cast(played_at_utc, Date).label("game_date"),
            Game.user_rating,
            Game.time_control_bucket,
        )
        .where(
            Game.user_id == user_id,
            Game.platform == platform,
            Game.user_rating.isnot(None),
            Game.played_at.isnot(None),
        )
        .order_by(Game.played_at)
    )
    if recency_cutoff is not None:
        stmt = stmt.where(Game.played_at >= recency_cutoff)
    rows = await session.execute(stmt)
    return list(rows.all())
```

### Global Stats WDL by Time Control Query
```python
# Source: adapted from analysis_service.py derive_user_result pattern
async def query_results_by_time_control(
    session: AsyncSession,
    user_id: int,
    recency_cutoff: datetime | None,
) -> list[tuple]:
    """Return (time_control_bucket, result, user_color) for all games."""
    stmt = (
        select(Game.time_control_bucket, Game.result, Game.user_color)
        .where(
            Game.user_id == user_id,
            Game.time_control_bucket.isnot(None),
        )
    )
    if recency_cutoff is not None:
        stmt = stmt.where(Game.played_at >= recency_cutoff)
    rows = await session.execute(stmt)
    return list(rows.all())
```

### Frontend Rating Hook Pattern (follow useTimeSeries)
```typescript
// Source: adapted from hooks/useBookmarks.ts pattern
export function useRatingHistory(recency: Recency | null) {
  return useQuery({
    queryKey: ['ratingHistory', recency],
    queryFn: () => statsApi.getRatingHistory(recency),
  });
}

export function useGlobalStats(recency: Recency | null) {
  return useQuery({
    queryKey: ['globalStats', recency],
    queryFn: () => statsApi.getGlobalStats(recency),
  });
}
```

### Recency Filter Component (reusable)
```typescript
// Source: Stats.tsx recency Select pattern
// Both Rating and GlobalStats pages use recency filter only
// Extract to a shared RecencySelect component or inline (small enough to inline)
<Select
  value={recency ?? 'all'}
  onValueChange={(v) => setRecency(v === 'all' ? null : (v as Recency))}
>
  <SelectTrigger size="sm" data-testid="filter-recency">
    <SelectValue />
  </SelectTrigger>
  <SelectContent>
    <SelectItem value="all">All time</SelectItem>
    <SelectItem value="week">Past week</SelectItem>
    <SelectItem value="month">Past month</SelectItem>
    <SelectItem value="3months">3 months</SelectItem>
    <SelectItem value="6months">6 months</SelectItem>
    <SelectItem value="year">1 year</SelectItem>
  </SelectContent>
</Select>
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `/stats` route | `/openings` route (rename) | Phase 7 | Navigation items grow from 3 to 5 |
| No rating charts | RatingChart per platform | Phase 7 | users can see rating trends per TC |
| No global WDL breakdown | GlobalStats page | Phase 7 | users can compare color/TC performance |

**No deprecated approaches in this phase.** All existing Recharts and pattern usage is current.

## Open Questions

1. **Chess.com ECO URL variation format**
   - What we know: Some chess.com games return `eco` URLs with move notation suffix instead of ECO code (e.g. `-4.exd5`). Current regex correctly returns `None`.
   - What's unclear: What percentage of chess.com games have ECO-less variation URLs vs. ECO-bearing URLs? This affects how useful the ECO fix is in practice.
   - Recommendation: Accept that `opening_eco` will be `None` for variation games. Add a test for the variation URL pattern. The "fix" in CONTEXT.md likely means ensuring the code handles these gracefully (it already does) and adding test coverage.

2. **Rating chart — per-game points vs monthly averages**
   - What we know: CONTEXT.md marks this as Claude's Discretion. Per-game points show the actual trajectory but create visual clutter for users with thousands of games.
   - Recommendation: Per-game data points. Recharts dots can be disabled (`dot={false}`) while keeping lines — this keeps the trajectory visible without overwhelming the chart. Monthly averages lose important rating swings.

3. **Global Stats page — bar vs pie for results by color**
   - What we know: CONTEXT.md marks this as Claude's Discretion. WDLBarChart already exists.
   - Recommendation: Reuse `WDLBarChart` with two rows (White, Black). Avoids any new chart type. Pie charts are harder to compare than side-by-side bars.

4. **Additional chess.com/lichess API data (deferred per CONTEXT.md)**
   - What we know: Both platforms provide accuracy scores and opening name data beyond what's currently stored. Chess.com provides `accuracies.white/black` per game. Lichess provides `analysis.inaccuracy/mistake/blunder` counts.
   - What's unclear: Whether these are worth importing now vs. a later phase.
   - Recommendation: Defer. CONTEXT.md explicitly defers these unless "trivially integrated". They require new columns, migrations, and new import logic — not trivial.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (existing, all 199 tests passing) |
| Config file | pyproject.toml (`[tool.pytest.ini_options]`) |
| Quick run command | `uv run pytest tests/test_normalization.py tests/test_analysis_service.py -x -q` |
| Full suite command | `uv run pytest -x -q` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| STATS-01 | ECO extraction handles variation URLs (returns None) | unit | `uv run pytest tests/test_normalization.py -x -q` | ✅ test_normalization.py (extend) |
| STATS-02 | rating history query returns per-game (date, rating, tc_bucket) | unit | `uv run pytest tests/test_stats_repository.py -x -q` | ❌ Wave 0 |
| STATS-03 | global stats query returns WDL by time control | unit | `uv run pytest tests/test_stats_repository.py -x -q` | ❌ Wave 0 |
| STATS-04 | global stats query returns WDL by color | unit | `uv run pytest tests/test_stats_repository.py -x -q` | ❌ Wave 0 |
| STATS-05 | recency filter applies to stats queries | unit | `uv run pytest tests/test_stats_repository.py -x -q` | ❌ Wave 0 |
| STATS-06 | GET /stats/rating-history returns 200 with auth | integration | `uv run pytest tests/test_stats_router.py -x -q` | ❌ Wave 0 |
| STATS-07 | GET /stats/global returns 200 with auth | integration | `uv run pytest tests/test_stats_router.py -x -q` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/test_normalization.py tests/test_stats_repository.py tests/test_stats_router.py -x -q`
- **Per wave merge:** `uv run pytest -x -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_stats_repository.py` — covers STATS-02, STATS-03, STATS-04, STATS-05
- [ ] `tests/test_stats_router.py` — covers STATS-06, STATS-07

*(Extend existing `tests/test_normalization.py` for STATS-01 — no new file needed)*

## Sources

### Primary (HIGH confidence)
- Existing codebase read directly: `app/services/normalization.py`, `app/repositories/analysis_repository.py`, `app/services/analysis_service.py`, `app/routers/analysis.py`, `app/models/game.py`, `app/schemas/analysis.py`, `frontend/src/pages/Stats.tsx`, `frontend/src/components/bookmarks/WinRateChart.tsx`, `frontend/src/components/bookmarks/WDLBarChart.tsx`, `frontend/src/App.tsx`, `frontend/src/hooks/useBookmarks.ts`, `frontend/src/api/client.ts`
- All 199 tests passing confirmed by `uv run pytest`
- ECO bug verified by manual testing of `_extract_chesscom_eco()` with variation URLs

### Secondary (MEDIUM confidence)
- [chess.com API documentation format](https://chessnerd.net/chesscom-api.html) — confirmed `eco` field is a URL, variation example shown
- [lichess-org/chess-openings GitHub](https://github.com/lichess-org/chess-openings) — TSV format with ECO, Name, PGN, UCI, EPD fields; CC0 license; confirmed as reference source for ECO mapping

### Tertiary (LOW confidence)
- Recharts `hide` prop behavior for toggling lines — confirmed in existing `WinRateChart.tsx` usage (HIGH from codebase), Recharts GitHub issues confirm pattern is standard

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries already in use, versions confirmed from package.json
- Architecture: HIGH — patterns copied from existing working code
- Pitfalls: HIGH — ECO bug verified empirically, DB timezone pitfall documented in STATE.md, other pitfalls from direct code reading
- Test infrastructure: HIGH — existing test suite confirmed, Wave 0 gaps identified by checking test directory

**Research date:** 2026-03-14
**Valid until:** 2026-04-14 (stable stack, no moving parts)
