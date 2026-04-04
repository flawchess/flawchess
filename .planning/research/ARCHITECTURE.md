# Architecture Research

**Domain:** Advanced chess analytics integration — ELO-adjusted metrics, opening risk, refined endgame stats
**Researched:** 2026-04-04
**Confidence:** HIGH — based on direct codebase inspection of all affected modules (v1.7, shipped 2026-04-03)

## Standard Architecture

The existing architecture is strict 3-layer: routers (HTTP only) → services (business logic) → repositories (SQL only). No SQL in services, no business logic in routers. All new features follow this layering.

### System Overview

```
┌──────────────────────────────────────────────────────────────────┐
│                     HTTP Layer (FastAPI Routers)                   │
│  routers/endgames.py                 routers/openings.py          │
│  GET /performance  (MODIFY)          POST /next-moves  (MODIFY)   │
│  GET /elo-timeline (NEW)                                           │
├──────────────────────────────────────────────────────────────────┤
│                     Business Logic (Services)                      │
│  endgame_service.py                  openings_service.py          │
│  · get_endgame_performance (MODIFY)  · get_next_moves (MODIFY)   │
│  · get_elo_skill_timeline  (NEW)     · _wdl_entropy    (NEW)      │
│  · _normalize_rating       (NEW)                                   │
│  · _compute_elo_adjusted_skill (NEW)                               │
├──────────────────────────────────────────────────────────────────┤
│                     Data Access (Repositories)                     │
│  endgame_repository.py               openings_repository.py       │
│  · query_endgame_entry_rows (KEEP)   · query_next_moves (KEEP)   │
│  · query_elo_skill_rows    (NEW)                                   │
├──────────────────────────────────────────────────────────────────┤
│                     Database (PostgreSQL)                          │
│  games table                         game_positions table          │
│  · white_rating / black_rating  ←── KEY for ELO (already stored) │
│  · platform                          · endgame_class (SmallInt)   │
│  · result / user_color               · material_imbalance         │
│  NO MIGRATIONS NEEDED for core ELO feature                        │
└──────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities (v1.8)

| Component | Responsibility | v1.8 Status |
|-----------|----------------|-------------|
| `routers/endgames.py` | HTTP endpoints for endgame analytics | MODIFY — add GET /elo-timeline |
| `routers/openings.py` | HTTP endpoints for opening analytics | MODIFY — augment next-moves response |
| `endgame_service.py` | ELO normalization, adjusted score, rolling series | MODIFY + NEW functions |
| `openings_service.py` | WDL entropy computation, risk scoring | MODIFY — add per-move risk inline |
| `endgame_repository.py` | SQL queries for endgame data with rating columns | NEW query function |
| `schemas/endgames.py` | Pydantic response models | MODIFY — extend existing + new timeline response |
| `schemas/openings.py` | Pydantic response models | MODIFY — add risk field to NextMoveEntry |
| `frontend/src/types/endgames.ts` | TypeScript mirrors of backend schemas | MODIFY |
| `frontend/src/api/client.ts` | Axios API calls | MODIFY — add getEloSkillTimeline |
| `frontend/src/hooks/useEndgames.ts` | TanStack Query hooks | MODIFY — add useEloSkillTimeline |
| `EndgamePerformanceSection.tsx` | Gauge display (conversion/recovery/endgame skill) | MODIFY — show adjusted value in gauge |
| `EloSkillTimelineChart.tsx` | Single-line rolling ELO-adjusted score timeline | NEW component |
| `EndgameGauge.tsx` | SVG gauge — already generic | NO CHANGE |
| `WDLChartRow.tsx` | Shared WDL bar chart — already generic | NO CHANGE |
| `lib/theme.ts` | Gauge zone color constants | NO CHANGE |
| `repositories/query_utils.py` | `apply_game_filters()` shared filter utility | NO CHANGE |

## Recommended Project Structure

No new directories. All new code extends existing modules following established conventions.

```
app/
├── routers/
│   └── endgames.py          # MODIFY: add GET /elo-timeline endpoint
├── services/
│   └── endgame_service.py   # MODIFY: add _normalize_rating(), _compute_elo_adjusted_skill(),
│                            #         get_elo_skill_timeline(); modify get_endgame_performance()
├── repositories/
│   └── endgame_repository.py  # MODIFY: add query_elo_skill_rows()
└── schemas/
    └── endgames.py           # MODIFY: add elo_adjusted_skill to EndgamePerformanceResponse;
                              #         add EloSkillTimelinePoint, EloSkillTimelineResponse

frontend/src/
├── components/charts/
│   └── EloSkillTimelineChart.tsx   # NEW: single-line rolling chart for ELO-adjusted score
├── hooks/
│   └── useEndgames.ts              # MODIFY: add useEloSkillTimeline()
├── types/
│   └── endgames.ts                 # MODIFY: EndgamePerformanceResponse + new timeline types
└── api/
    └── client.ts                   # MODIFY: add endgameApi.getEloSkillTimeline()
```

For opening risk (independent track):

```
app/
├── services/
│   └── openings_service.py   # MODIFY: add _wdl_entropy(), call it in get_next_moves()
└── schemas/
    └── openings.py           # MODIFY: add risk: float to NextMoveEntry

frontend/src/
├── components/move-explorer/  # MODIFY: show risk badge per move row
└── types/
    └── (openings type file)   # MODIFY: add risk to NextMoveEntry interface
```

### Structure Rationale

- **No new top-level files for ELO:** The ELO adjustment is a new metric within the existing endgame analytics domain. Fragmenting it into new files would scatter closely related logic.
- **New file for EloSkillTimelineChart:** The ELO timeline is a distinct chart type (single-line vs. existing multi-series charts). Conditionalizing `EndgameConvRecovTimelineChart` would add excessive branching.
- **No migration for core ELO feature:** `games.white_rating`, `games.black_rating`, and `games.platform` are already stored. The rating normalization is pure Python.

## Architectural Patterns

### Pattern 1: ELO Normalization as Pure Python Service Functions

**What:** Rating normalization and adjustment live entirely in `endgame_service.py` as named pure functions with module-level constants. No SQL arithmetic.

**When to use:** When the formula has conditional logic and will likely be tuned. The tapering offset for lichess ratings uses `max(0, ...)` and conditional branching that reads naturally in Python but awkwardly in SQL CASE expressions.

**Trade-offs:** Slightly more data fetched from DB (two extra integer columns per row) vs. computing in SQL. Negligible at the row counts involved. Python testing of the formula is straightforward; SQL-side GREATEST() expressions are not.

**Example:**
```python
# Module-level named constants (no magic numbers per project conventions)
_LICHESS_BASE_OFFSET = 350
_LICHESS_TAPER_PER_POINT = 0.3
_LICHESS_TAPER_START = 1400
_REFERENCE_RATING = 1500  # chess.com blitz equivalent; fixed for cross-player comparison

def _normalize_rating(rating: int, platform: str) -> float:
    """Convert platform rating to chess.com-equivalent for cross-platform comparison."""
    if platform == "lichess":
        offset = max(0.0, _LICHESS_BASE_OFFSET - (rating - _LICHESS_TAPER_START) * _LICHESS_TAPER_PER_POINT)
        return float(rating) - offset
    return float(rating)

def _compute_elo_adjusted_skill(raw_skill: float, avg_normalized_opponent_rating: float) -> float:
    """Adjust raw endgame skill by opponent strength relative to reference rating."""
    if avg_normalized_opponent_rating <= 0:
        return 0.0
    return raw_skill * avg_normalized_opponent_rating / _REFERENCE_RATING
```

### Pattern 2: New query_elo_skill_rows() Alongside Existing query_endgame_entry_rows()

**What:** Add `query_elo_skill_rows()` to `endgame_repository.py` with the same span subquery structure as `query_endgame_entry_rows()` but selecting additional columns: `Game.white_rating`, `Game.black_rating`, `Game.platform`.

**When to use:** When you need the same join/filter structure but a different SELECT list and return type. Do not modify the existing function — callers unpack columns positionally and adding columns would break them.

**Trade-offs:** Some duplication in the subquery builder. If duplication grows, extract `_build_endgame_span_subq(user_id)` as a private helper shared by both. For now, two independent functions are clearer than a combined one with an `include_ratings` flag.

**Example sketch:**
```python
async def query_elo_skill_rows(
    session: AsyncSession,
    user_id: int,
    time_control: Sequence[str] | None,
    platform: Sequence[str] | None,
    rated: bool | None,
    opponent_type: str,
    recency_cutoff: datetime.datetime | None,
) -> list[Row[Any]]:
    """Return endgame entry rows with rating data for ELO-adjusted skill computation.

    Returns rows of: (game_id, endgame_class, result, user_color,
                      user_material_imbalance, white_rating, black_rating, platform)
    Same span_subq as query_endgame_entry_rows; adds rating/platform columns.
    """
    # ... same span_subq construction ...
    stmt = (
        select(
            Game.id.label("game_id"),
            span_subq.c.endgame_class,
            Game.result,
            Game.user_color,
            (span_subq.c.entry_imbalance * color_sign).label("user_material_imbalance"),
            Game.white_rating,
            Game.black_rating,
            Game.platform,
        )
        .join(span_subq, Game.id == span_subq.c.game_id)
        .where(Game.user_id == user_id)
    )
    stmt = apply_game_filters(stmt, time_control, platform, rated, opponent_type, recency_cutoff)
    result = await session.execute(stmt)
    return list(result.fetchall())
```

### Pattern 3: Opening Risk as WDL Entropy on Existing NextMoveEntry Rows

**What:** Risk per candidate move is the normalized Shannon entropy of the WDL distribution. It is computed inline in `get_next_moves()` from the existing WDL counts — no extra SQL query.

**When to use:** When the metric derives entirely from data already fetched. Entropy adds O(1) Python arithmetic per move row.

**Trade-offs:** Adds one new `risk: float` field to `NextMoveEntry`. Backend callers must not have hardcoded column counts. Frontend renders a risk badge per move row.

**Example computation:**
```python
import math

def _wdl_entropy(wins: int, draws: int, losses: int) -> float:
    """Normalized Shannon entropy of WDL distribution over 3 outcomes.

    0.0 = one outcome dominates (predictable position).
    1.0 = all three outcomes equally likely (maximally uncertain).
    """
    total = wins + draws + losses
    if total == 0:
        return 0.0
    entropy = 0.0
    for count in (wins, draws, losses):
        p = count / total
        if p > 0:
            entropy -= p * math.log2(p)
    return round(entropy / math.log2(3), 4)  # normalize to [0, 1]
```

Entropy is preferred over raw variance: it handles the 3-outcome WDL space correctly, is bounded [0, 1], and correctly scores a position with 33%/33%/33% as maximally uncertain (1.0) vs. a position with 100% wins as maximally certain (0.0).

### Pattern 4: Extend EndgamePerformanceResponse, Not New Endpoint

**What:** `elo_adjusted_skill: float` is added to the existing `EndgamePerformanceResponse` rather than a new `/endgames/elo-skill` endpoint. The ELO-adjusted skill gauge replaces or augments the existing `endgame_skill` gauge in `EndgamePerformanceSection`.

**When to use:** When the new metric semantically belongs with existing response data. The performance endpoint already computes `endgame_skill`; the adjusted version is just a refinement of it.

**Trade-offs:** `get_endgame_performance()` now runs two repository queries sequentially (existing `query_endgame_entry_rows` + new `query_elo_skill_rows`). Both query the same covering index and rows are not large. The alternative — a dedicated endpoint — doubles frontend loading state management for one screen section.

**Decision:** Add `elo_adjusted_skill: float` to `EndgamePerformanceResponse`. The timeline (`GET /endgames/elo-timeline`) is necessarily separate because it needs its own `window` parameter.

## Data Flow

### ELO-Adjusted Endgame Skill

```
User adjusts filters on Endgames page
    ↓
useEndgamePerformance(filters) [EXISTING hook — unchanged]
    ↓
endgameApi.getPerformance(params) — GET /api/endgames/performance
    ↓
endgame_service.get_endgame_performance() [MODIFY]
    ├── query_endgame_entry_rows()     [EXISTING — unchanged]
    └── query_elo_skill_rows()         [NEW — same filters, adds rating columns]
        ↓
    _normalize_rating(rating, platform) per opponent rating  [NEW]
    avg_normalized_opponent_rating = mean of normalized ratings
    _compute_elo_adjusted_skill(raw_skill, avg_rating)       [NEW]
        ↓
EndgamePerformanceResponse [MODIFY: adds elo_adjusted_skill: float]
    ↓
EndgamePerformanceSection.tsx [MODIFY: Endgame Skill gauge shows adjusted value]
```

### ELO Skill Timeline

```
Endgames stats tab mounts
    ↓
useEloSkillTimeline(filters) [NEW hook]
    ↓
endgameApi.getEloSkillTimeline(params) — GET /api/endgames/elo-timeline [NEW endpoint]
    ↓
endgame_service.get_elo_skill_timeline() [NEW function]
    └── query_elo_skill_rows(recency_cutoff=None) [pre-fill pattern — same as conv/recov timeline]
        ↓
    _compute_elo_skill_rolling_series(rows, window) [NEW — mirrors _compute_conv_recov_rolling_series]
    Filter output points to recency cutoff (same pattern as existing timeline functions)
        ↓
EloSkillTimelineResponse { series: [EloSkillTimelinePoint], window: int }
    ↓
EloSkillTimelineChart.tsx [NEW component — single line, same Recharts pattern]
    ↓
Endgames.tsx statisticsContent [MODIFY: render EloSkillTimelineChart below existing charts]
```

### Opening Risk (Independent Track)

```
User navigates move explorer to a position
    ↓
useNextMoves(position, filters) [EXISTING hook — unchanged]
    ↓
openingsApi.getNextMoves(params) — POST /api/openings/next-moves
    ↓
openings_service.get_next_moves() [MODIFY]
    └── query_next_moves() [EXISTING — already returns wins/draws/losses per move]
        ↓
    _wdl_entropy(wins, draws, losses) called per move [NEW — O(1) per row]
        ↓
NextMoveEntry [MODIFY: add risk: float field]
    ↓
MoveExplorer component [MODIFY: render risk badge or colored indicator per move row]
```

### Key Data Facts

1. **Opponent rating source:** `games.white_rating` when `user_color == "black"`, else `games.black_rating`. Both are already stored. No migration needed.
2. **Games without ratings:** Some unrated games have NULL ratings. Filter these out when computing `avg_normalized_opponent_rating`. If no rated games exist, return `elo_adjusted_skill = 0.0`.
3. **Opening risk is zero-migration, zero-new-query:** Entropy computed from WDL counts already fetched by `query_next_moves()`. No DB changes.
4. **Filter propagation:** All new endpoints accept the same standard filter parameters as existing endgame endpoints. `apply_game_filters()` from `query_utils.py` handles all of them without modification.
5. **Rolling window pre-fill:** `get_elo_skill_timeline()` must follow the same pattern as `get_conv_recov_timeline()` — fetch all games (no recency filter), compute the full rolling series, then filter output points to the recency window. This prevents cold-start artifacts when filtering to recent games.
6. **Cache keys:** New TanStack Query hooks use keys like `['eloSkillTimeline', params, window]` following the exact pattern of `['endgameConvRecovTimeline', params, window]`.

## Scaling Considerations

| Scale | Architecture Adjustments |
|-------|--------------------------|
| Current (hundreds to low thousands of games/user) | Python-side aggregation after SQL fetch is fast; sequential queries per endpoint is the established pattern |
| 10k+ games/user | `query_elo_skill_rows()` uses the same covering index (`ix_gp_user_endgame_game`) as `query_endgame_entry_rows()` — performance will be similar. Adding two integer columns to SELECT does not change the index scan plan. |
| Opening risk at any scale | Zero scaling concern. Entropy is O(1) per move entry computed from pre-aggregated WDL counts. |

### Scaling Priorities

1. **First bottleneck (ELO feature):** Running `query_endgame_entry_rows()` AND `query_elo_skill_rows()` in `get_endgame_performance()` doubles the heavy endgame queries. Acceptable initially. If profiling reveals it as a bottleneck, merge into a single query by adding rating columns to `query_endgame_entry_rows()` — but only after confirming no callers break (all unpack positionally). Use a refactor phase rather than doing it speculatively.
2. **ELO timeline pre-fill:** Fetching all games (no recency filter) for the rolling window pre-fill is the same trade-off already made by `get_conv_recov_timeline()` and `get_endgame_timeline()`. Acceptable. If a user has 50k+ games this may be slow — but that's a future problem for all timeline endpoints equally.

## Anti-Patterns

### Anti-Pattern 1: Rating Normalization in SQL

**What people do:** Compute `GREATEST(0, 350 - (rating - 1400) * 0.3)` as a SQL expression.

**Why it's wrong:** The tapering formula is likely to be tuned after observing real data. SQL CASE/GREATEST expressions are harder to unit-test than Python functions and harder to read. Named Python constants (`_LICHESS_BASE_OFFSET = 350`) make the formula self-documenting in a way SQL cannot.

**Do this instead:** Fetch raw ratings from SQL. Normalize in Python with named constants at the top of `endgame_service.py`. Write a unit test for `_normalize_rating()`.

### Anti-Pattern 2: Separate /endgames/elo-skill Endpoint for the Current Score Value

**What people do:** Create a dedicated `GET /endgames/elo-skill` endpoint returning just the adjusted score, keeping `GET /endgames/performance` for everything else.

**Why it's wrong:** Frontend now needs two concurrent queries and two loading states for a single screen section. The `/performance` endpoint already fetches the same row set. Two nearly identical heavy DB queries fire for one page section.

**Do this instead:** Add `elo_adjusted_skill: float` to `EndgamePerformanceResponse`. The frontend `useEndgamePerformance()` hook already exists — the adjusted value arrives in the same response with no extra HTTP round-trip.

### Anti-Pattern 3: Standard Deviation for Opening Risk

**What people do:** Compute variance or standard deviation of per-game win rates to quantify "inconsistency."

**Why it's wrong:** Per-game outcomes are categorical (win/draw/loss), not a continuous distribution. Variance of Bernoulli outcomes recovers `p*(1-p)` which peaks at 50% win rate — this conflates "you win half your games" with "this opening is risky." It also ignores draws entirely, treating them as losses. The 3-outcome WDL space needs a measure designed for categorical distributions.

**Do this instead:** Use normalized Shannon entropy over (wins, draws, losses). Peaks at 0.333/0.333/0.333, is 0 when one outcome dominates completely, and is bounded [0, 1] regardless of game count.

### Anti-Pattern 4: Modifying query_endgame_entry_rows Signature

**What people do:** Add `include_ratings: bool = False` to the existing function and conditionally expand the SELECT inside it to return rating columns when True.

**Why it's wrong:** `query_endgame_entry_rows` has callers in `get_endgame_stats`, `get_endgame_performance`, and `get_endgame_timeline`. All unpack result rows positionally: `for game_id, endgame_class_int, result, user_color, user_material_imbalance in rows`. Conditionally changing the column count silently corrupts these unpackings in a way that ty/mypy may not catch (rows are `list[Row[Any]]`).

**Do this instead:** Add a separate `query_elo_skill_rows()` function with a documented return signature. If the span subquery becomes duplicated enough to warrant refactoring, extract `_build_endgame_span_subq()` as a private helper — but only after both functions are written and tested.

### Anti-Pattern 5: Opening Risk as a Separate Aggregation Endpoint

**What people do:** Create `GET /openings/position-risk?full_hash=X` that re-runs the WDL aggregation query just to return an entropy value.

**Why it's wrong:** The next-moves endpoint already computes per-move WDL counts via `query_next_moves()`. A separate endpoint re-runs the same SQL for no benefit. Users need risk visible per move in the move explorer — not as a separate screen.

**Do this instead:** Compute `_wdl_entropy(wins, draws, losses)` inline in `get_next_moves()` and attach as `risk: float` to each `NextMoveEntry`. Zero extra SQL. Position-level risk can be computed from `position_stats: WDLStats` already in `NextMovesResponse` using the same function.

### Anti-Pattern 6: asyncio.gather for Sequential Repository Calls

**What people do:** `await asyncio.gather(query_endgame_entry_rows(...), query_elo_skill_rows(...))` to run both queries "concurrently."

**Why it's wrong:** The project codebase explicitly documents this constraint in multiple places: "AsyncSession is not safe for concurrent use from multiple coroutines, and a single session uses one DB connection so there's no concurrency benefit from asyncio.gather here." The comment appears in `endgame_service.py`, `endgame_repository.py`, and CLAUDE.md.

**Do this instead:** Execute `query_endgame_entry_rows()` then `query_elo_skill_rows()` sequentially, exactly as the existing `get_endgame_performance()` already does for its multiple repository calls.

## Integration Points

### New vs. Modified (Explicit)

#### New (pure additions)

| File | What is New |
|------|-------------|
| `app/repositories/endgame_repository.py` | `query_elo_skill_rows()` function |
| `app/services/endgame_service.py` | `_normalize_rating()`, `_compute_avg_opponent_rating()`, `_compute_elo_adjusted_skill()`, `get_elo_skill_timeline()`, `_compute_elo_skill_rolling_series()` |
| `app/schemas/endgames.py` | `EloSkillTimelinePoint`, `EloSkillTimelineResponse` classes |
| `frontend/src/components/charts/EloSkillTimelineChart.tsx` | Single-line rolling chart for ELO-adjusted score |
| `frontend/src/hooks/useEndgames.ts` | `useEloSkillTimeline()` export |
| `app/routers/endgames.py` | `GET /elo-timeline` endpoint |

#### Modified (existing files changed)

| File | What Changes |
|------|-------------|
| `app/services/endgame_service.py` | `get_endgame_performance()` calls `query_elo_skill_rows()` and computes `elo_adjusted_skill` |
| `app/schemas/endgames.py` | `EndgamePerformanceResponse` gains `elo_adjusted_skill: float` field |
| `frontend/src/types/endgames.ts` | `EndgamePerformanceResponse` interface gains `elo_adjusted_skill: number` |
| `frontend/src/api/client.ts` | `endgameApi` gains `getEloSkillTimeline()` method |
| `frontend/src/pages/Endgames.tsx` | `statisticsContent` renders `EloSkillTimelineChart`; add `useEloSkillTimeline` data |
| `frontend/src/components/charts/EndgamePerformanceSection.tsx` | Endgame Skill gauge shows `elo_adjusted_skill` value (adjusted) with tooltip or label explaining adjustment |

For opening risk (if pursued this milestone):

| File | What Changes |
|------|-------------|
| `app/services/openings_service.py` | Add `_wdl_entropy()` pure function; call it in `get_next_moves()` per move |
| `app/schemas/openings.py` | `NextMoveEntry` gains `risk: float` field |
| Frontend types (openings) | `NextMoveEntry` interface gains `risk: number` |
| Move explorer component | Risk indicator badge rendered per move row |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| `endgame_repository.py` → `endgame_service.py` | `list[Row[Any]]` tuples, positional columns | Document column order clearly in docstring — no named columns in Row |
| `endgame_service.py` → `routers/endgames.py` | Pydantic response models | `elo_adjusted_skill` is `float`, always present (0.0 when no rated games) |
| `openings_service.py` → `routers/openings.py` | `NextMovesResponse` with `NextMoveEntry` | `risk: float` added to existing model — non-breaking addition |
| Frontend hooks → API client | TypeScript interfaces mirror backend Pydantic schemas | Keep `endgames.ts` in sync with `schemas/endgames.py` after any schema change |
| `EndgamePerformanceSection.tsx` → `EndgameGauge.tsx` | `value: number`, `zones: GaugeZone[]` props | Gauge is already fully generic — existing `ENDGAME_SKILL_ZONES` constant applies unchanged |

## Suggested Build Order

Dependencies flow top to bottom within each track. Tracks can be interleaved but not parallelized within a session.

### Track A: ELO-Adjusted Endgame Skill

**Step A1: Backend (service + repository + schema)**
- Add `_normalize_rating`, `_compute_avg_opponent_rating`, `_compute_elo_adjusted_skill` to `endgame_service.py`
- Add `query_elo_skill_rows()` to `endgame_repository.py`
- Modify `get_endgame_performance()` to call it and compute `elo_adjusted_skill`
- Add `elo_adjusted_skill: float` to `EndgamePerformanceResponse` in `schemas/endgames.py`
- Write unit tests for `_normalize_rating` and `_compute_elo_adjusted_skill`
- Smoke test: `GET /api/endgames/performance` returns the new field

**Step A2: Frontend gauge**
- Add `elo_adjusted_skill: number` to `EndgamePerformanceResponse` TS interface
- Modify `EndgamePerformanceSection.tsx` — show adjusted value in Endgame Skill gauge
- Optionally add `InfoPopover` explaining raw vs. adjusted

**Step A3: ELO timeline endpoint**
- Add `_compute_elo_skill_rolling_series()` and `get_elo_skill_timeline()` to `endgame_service.py`
- Add `EloSkillTimelinePoint`, `EloSkillTimelineResponse` to `schemas/endgames.py`
- Add `GET /endgames/elo-timeline` to `routers/endgames.py`

**Step A4: Frontend timeline chart**
- Add `useEloSkillTimeline()` hook to `useEndgames.ts`
- Add `endgameApi.getEloSkillTimeline()` to `api/client.ts`
- Create `EloSkillTimelineChart.tsx` component
- Wire into `Endgames.tsx` stats tab

### Track B: Opening Risk (independent, can be done after or alongside Track A)

**Step B1: Backend**
- Add `_wdl_entropy()` pure function to `openings_service.py`
- Modify `get_next_moves()` to compute and attach `risk` per move
- Add `risk: float` to `NextMoveEntry` in `schemas/openings.py`

**Step B2: Frontend**
- Add `risk: number` to `NextMoveEntry` TS interface
- Modify move explorer component to display risk badge per move row

## Sources

- Direct inspection of `app/routers/endgames.py` — confirmed endpoint signatures, all use Query params pattern
- Direct inspection of `app/services/endgame_service.py` — confirmed `_compute_rolling_series`, `_compute_conv_recov_rolling_series`, `_ENDGAME_SKILL_CONVERSION_WEIGHT/_RECOVERY_WEIGHT`, sequential query pattern documented inline
- Direct inspection of `app/repositories/endgame_repository.py` — confirmed `query_endgame_entry_rows` return shape, covering index `ix_gp_user_endgame_game`, AsyncSession sequential constraint
- Direct inspection of `app/models/game.py` — confirmed `white_rating: Mapped[int | None]`, `black_rating: Mapped[int | None]`, `platform: Mapped[str]` all present; no migration needed
- Direct inspection of `app/schemas/endgames.py` and `app/schemas/openings.py` — confirmed extension points
- Direct inspection of `app/repositories/query_utils.py` — confirmed `apply_game_filters()` handles all standard filters; no changes needed
- Direct inspection of `frontend/src/components/charts/EndgamePerformanceSection.tsx`, `EndgameGauge.tsx` — confirmed gauge is fully generic (accepts `value`, `zones` props); `ENDGAME_SKILL_ZONES` already defined
- Direct inspection of `frontend/src/hooks/useEndgames.ts` — confirmed `ENDGAME_STALE_TIME = 5 * 60 * 1000` pattern for new hooks
- Backlog item 999.5 in `.planning/ROADMAP.md` — ELO normalization formula, reference rating 1500, adjustment formula: `adjusted = raw × avg_normalized_opponent_rating / 1500`

---
*Architecture research for: FlawChess v1.8 Advanced Analytics*
*Researched: 2026-04-04*
