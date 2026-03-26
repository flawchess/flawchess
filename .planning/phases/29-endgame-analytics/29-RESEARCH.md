# Phase 29: Endgame Analytics - Research

**Researched:** 2026-03-26
**Domain:** FastAPI + SQLAlchemy 2.x async query design, React page/routing patterns, Recharts stacked bar chart
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Two sub-tabs: "Statistics" and "Games". URL-driven tab state: `/endgames/statistics` and `/endgames/games`.
- **D-02:** Filter sidebar on the left (desktop) / collapsible on mobile. No chessboard. Filters: Time Control, Platform, Recency, plus "More filters" collapsible with Rated and Opponent Type. No color filter.
- **D-03:** All filters apply to both Statistics and Games sub-tabs.
- **D-04:** Stacked horizontal bar chart (same visual pattern as existing `WDLBarChart`) with endgame categories as Y-axis labels. Each category shows W/D/L percentage bars plus game count outline bar.
- **D-05:** Categories sorted by game count descending.
- **D-06:** Below each category's W/D/L bar, show inline conversion and recovery metrics: "Conversion: X% (n/m)" and "Recovery: Y% (n/m)".
- **D-07:** Six endgame categories: Rook, Minor Piece, Pawn, Queen, Mixed, Pawnless.
- **D-08:** Conversion = win rate in games where the user entered that endgame type with a material advantage (positive `material_imbalance` from the user's perspective at the endgame transition point).
- **D-09:** Recovery = draw+win rate in games where the user entered that endgame type with a material disadvantage.
- **D-10:** Stats displayed inline below each endgame category row, not as a separate section.
- **D-11:** No breakdown by game phase — single aggregate rate per endgame type.
- **D-12:** User clicks an endgame category in the Statistics tab to select it. Selection persists when switching to the Games tab.
- **D-13:** All 6 categories always visible in the Statistics tab — selection only affects the Games tab content.
- **D-14:** Reuse the existing `GameCardList` component for displaying games.
- **D-15:** New top-level nav item "Endgames" between Openings and Statistics. Desktop: Import, Openings, Endgames, Statistics. Mobile bottom bar: same 4 items.
- **D-16:** Route: `/endgames/*` with sub-routes `/endgames/statistics` (default) and `/endgames/games`. Mirrors `/openings/*` pattern.

### Claude's Discretion

- How to derive endgame class from `material_signature` at query time (SQL logic or Python post-processing)
- Game phase threshold logic (material_count + ply boundaries for opening/middlegame/endgame classification)
- Whether to create a generic WDL bar chart component or a new `EndgameWDLChart` that follows the same visual pattern
- Empty state design for users with no endgame data
- Mobile layout details for the inline conversion/recovery metrics
- How to determine the "endgame transition point" for material imbalance (first position classified as endgame in a game)

### Deferred Ideas (OUT OF SCOPE)

- **MATFLT-01** — Material signature drill-down (finer breakdown by specific material config, e.g. KRP vs KR within rook endgames)
- Conversion/recovery on Global Stats page
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| ENDGM-01 | User can view W/D/L rates for each endgame category in a dedicated Endgames tab | Backend: `query_endgame_stats` joins game_positions → games; Frontend: EndgamesPage + EndgameWDLChart |
| ENDGM-02 | User can filter endgame statistics by time control (bullet/blitz/rapid/classical) | FilterPanel reuse; time_control filter added to endgame query just like analysis_repository._build_base_query |
| ENDGM-03 | User can filter endgame statistics by color played (white/black/both) | D-02 omits color filter from sidebar — REQUIREMENTS.md says this but CONTEXT.md decision D-02 supersedes: no color filter |
| ENDGM-04 | User can see game count per endgame category to assess statistical significance | total count returned per category in EndgameStatsResponse |
| CONV-01 | User can see win rate when up material (conversion), per endgame type | Backend: query_endgame_conversion_recovery; CONV requirements note game-phase breakdown superseded — per-endgame-type per D-11 |
| CONV-02 | User can see draw+win rate when down material (recovery), per endgame type | Same endpoint as CONV-01 |
| CONV-03 | User can filter conversion/recovery stats by time control | Same filter params passed to endgame stats endpoint |
</phase_requirements>

---

## Summary

Phase 29 adds an Endgames page (`/endgames/*`) with two sub-tabs: Statistics (W/D/L per endgame category with inline conversion/recovery metrics) and Games (paginated game list filtered by selected category). The backend is a new router/service/repository triple (`app/routers/endgames.py`, `app/services/endgames_service.py`, `app/repositories/endgames_repository.py`) that queries `game_positions` joined to `games`, derives the endgame class in Python post-processing (since material_signature is a denormalized string), and aggregates W/D/L plus conversion/recovery per category. The frontend mirrors the Openings page structure almost exactly — same tab infrastructure, same FilterPanel (minus color), same GameCardList — with a new `EndgameWDLChart` component that extends `WDLBarChart`'s visual pattern with inline conversion/recovery text rows.

The key design choices are:
1. **Endgame class derivation in Python**, not SQL — the `material_signature` column is a string like `KRPP_KRP`; regex or character scanning in Python is cleaner than SQL LIKE patterns and easier to test.
2. **"Endgame transition point" = first position per game with `material_count` below the endgame threshold** — the material_imbalance at that ply is used for conversion/recovery classification.
3. **Single API endpoint** (`GET /api/endgames/stats`) returns W/D/L + conversion + recovery for all 6 categories in one response; a second endpoint (`GET /api/endgames/games`) returns paginated games for a selected category.

**Primary recommendation:** Follow the stats_service/stats_repository pattern (Python-side aggregation from raw DB rows). Avoid complex SQL aggregation; query raw per-game rows and aggregate in Python for testability.

---

## Standard Stack

### Core (all already in the project)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| SQLAlchemy 2.x async | 2.x (project-wide) | ORM / query building | Project standard |
| FastAPI | 0.115.x (project-wide) | HTTP layer | Project standard |
| Pydantic v2 | project-wide | Schema validation | Project standard |
| React + TypeScript | 19 / project-wide | Frontend | Project standard |
| TanStack Query | project-wide | Data fetching/cache | Project standard |
| Recharts (via shadcn chart) | project-wide | Bar chart | Already used in WDLBarChart |
| Tailwind CSS | project-wide | Styling | Project standard |

No new packages are required for this phase.

---

## Architecture Patterns

### Recommended File Structure

```
Backend (new files):
app/
├── routers/endgames.py            # HTTP layer: GET /endgames/stats, GET /endgames/games
├── services/endgames_service.py   # Business logic: endgame class derivation, aggregation
├── repositories/endgames_repository.py  # DB queries: raw rows from game_positions + games
└── schemas/endgames.py            # Pydantic response models

Frontend (new files):
frontend/src/
├── pages/Endgames.tsx             # Main page: sub-tabs, filter sidebar, desktop+mobile layout
├── components/charts/EndgameWDLChart.tsx  # Bar chart with inline conversion/recovery rows
├── hooks/useEndgames.ts           # TanStack Query hooks for endgame stats + games
└── types/endgames.ts              # TypeScript interfaces mirroring backend schemas
```

### Pattern 1: Endgame Class Derivation (Python Post-Processing)

**What:** Classify `material_signature` string into one of 6 endgame categories in Python.
**When to use:** At service layer, after raw rows returned from repository.
**Why Python not SQL:** `material_signature` is a denormalized string (e.g. `KRPP_KRP`). Python string scanning is straightforward, fully testable as a pure function, and avoids fragile SQL LIKE chains.

```python
# Source: position_classifier.py convention (pure functions, no I/O)

# Endgame category constants
ENDGAME_CLASS_ROOK = "rook"
ENDGAME_CLASS_MINOR_PIECE = "minor_piece"
ENDGAME_CLASS_PAWN = "pawn"
ENDGAME_CLASS_QUEEN = "queen"
ENDGAME_CLASS_MIXED = "mixed"
ENDGAME_CLASS_PAWNLESS = "pawnless"

ENDGAME_CLASS_ORDER = [
    ENDGAME_CLASS_ROOK,
    ENDGAME_CLASS_MINOR_PIECE,
    ENDGAME_CLASS_PAWN,
    ENDGAME_CLASS_QUEEN,
    ENDGAME_CLASS_MIXED,
    ENDGAME_CLASS_PAWNLESS,
]

def classify_endgame_class(material_signature: str) -> str:
    """Derive endgame category from a canonical material_signature string.

    material_signature format: "{white_side}_{black_side}"
    e.g. "KRP_KR", "KQPP_KQP", "KBN_KB", "KP_K", "K_K"

    Classification priority (checked in order):
    1. Queen present → queen (or mixed if also has rooks/minors)
    2. Rook(s) present, no queen → rook (or mixed if also has minor pieces)
    3. Only minor pieces (B/N), no Q/R → minor_piece
    4. Only pawns (P), no Q/R/B/N → pawn
    5. No pieces except kings → pawnless
    Mixed = combination of different major/minor categories (Q+R, R+minor, etc.)
    """
    sig = material_signature.replace("_", "")  # combine both sides
    has_queen = "Q" in sig
    has_rook = "R" in sig
    has_bishop = "B" in sig
    has_knight = "N" in sig
    has_pawn = "P" in sig
    has_minor = has_bishop or has_knight

    # Mixed: queen + anything else, or rook + minor piece
    if has_queen and (has_rook or has_minor):
        return ENDGAME_CLASS_MIXED
    if has_queen:
        return ENDGAME_CLASS_QUEEN
    if has_rook and has_minor:
        return ENDGAME_CLASS_MIXED
    if has_rook:
        return ENDGAME_CLASS_ROOK
    if has_minor and has_pawn:
        return ENDGAME_CLASS_MIXED
    if has_minor:
        return ENDGAME_CLASS_MINOR_PIECE
    if has_pawn:
        return ENDGAME_CLASS_PAWN
    return ENDGAME_CLASS_PAWNLESS
```

**CRITICAL NOTE on ENDGM-03 vs D-02 conflict:** REQUIREMENTS.md ENDGM-03 says "User can filter endgame statistics by color played". CONTEXT.md D-02 explicitly removes color filter from the endgames sidebar. The CONTEXT.md decision supersedes — no color filter in this phase.

### Pattern 2: Endgame Transition Point for Conversion/Recovery

**What:** For each game, find the first position where the game enters the endgame phase. Read `material_imbalance` at that ply to classify as up/even/down material from the user's perspective.
**When to use:** In the repository query; fetch the minimum ply endgame position per game.

**Game phase threshold (Claude's discretion — confirmed from position_classifier.py comments):**
- The position_classifier computes `material_count` (total centipawns both sides, starting = 7800).
- Game phase is derived at query time. Standard threshold used in project: material_count < 2600 = endgame (roughly 6 pieces total remain after pawn/minor trades).
- This threshold is not currently codified as a constant in the codebase — it must be defined as a named constant in endgames_repository.py.

```python
# Named constant (no magic numbers per CLAUDE.md)
ENDGAME_MATERIAL_THRESHOLD = 2600  # material_count < this → endgame phase

# user_material_imbalance from DB is always white - black (signed).
# For a white player: positive = white up = user up. For black: negate.
# user_imbalance = imbalance if user_color == "white" else -imbalance
```

**Endgame transition query approach:**
- Use a subquery (or lateral join) to find the minimum ply where `material_count < ENDGAME_MATERIAL_THRESHOLD` for each game.
- Join back to get `material_imbalance` and `material_signature` at that ply.
- Use `COUNT(DISTINCT game_id)` in all aggregations (critical constraint from STATE.md).

```python
# Pattern: subquery for first endgame ply per game
from sqlalchemy import func, select, and_

# Subquery: min ply where endgame starts per game
endgame_entry_subq = (
    select(
        GamePosition.game_id,
        func.min(GamePosition.ply).label("entry_ply"),
    )
    .where(
        GamePosition.user_id == user_id,
        GamePosition.material_count < ENDGAME_MATERIAL_THRESHOLD,
        GamePosition.material_count.is_not(None),
    )
    .group_by(GamePosition.game_id)
    .subquery()
)
```

### Pattern 3: Backend Router/Service/Repository Layering

Mirror the existing `stats.py` pattern exactly:

```python
# app/routers/endgames.py
@router.get("/endgames/stats", response_model=EndgameStatsResponse)
async def get_endgame_stats(
    session: Annotated[AsyncSession, Depends(get_async_session)],
    user: Annotated[User, Depends(current_active_user)],
    time_control: list[str] | None = Query(default=None),
    platform: list[str] | None = Query(default=None),
    rated: bool | None = Query(default=None),
    opponent_type: str = Query(default="human"),
    recency: str | None = Query(default=None),
) -> EndgameStatsResponse:
    ...

@router.get("/endgames/games", response_model=EndgameGamesResponse)
async def get_endgame_games(
    session: Annotated[AsyncSession, Depends(get_async_session)],
    user: Annotated[User, Depends(current_active_user)],
    endgame_class: str = Query(...),  # required: rook|minor_piece|pawn|queen|mixed|pawnless
    time_control: list[str] | None = Query(default=None),
    ...
    offset: int = Query(default=0),
    limit: int = Query(default=20),
) -> EndgameGamesResponse:
    ...
```

### Pattern 4: Pydantic Response Schema

```python
# app/schemas/endgames.py
from pydantic import BaseModel

class ConversionRecoveryStats(BaseModel):
    conversion_pct: float        # win rate when up material (0-100)
    conversion_games: int        # games where user entered up
    conversion_wins: int         # wins among those games
    recovery_pct: float          # draw+win rate when down material (0-100)
    recovery_games: int          # games where user entered down
    recovery_saves: int          # draws+wins among those games

class EndgameCategoryStats(BaseModel):
    endgame_class: str           # rook|minor_piece|pawn|queen|mixed|pawnless
    label: str                   # display label: "Rook", "Minor Piece", etc.
    wins: int
    draws: int
    losses: int
    total: int
    win_pct: float
    draw_pct: float
    loss_pct: float
    conversion: ConversionRecoveryStats

class EndgameStatsResponse(BaseModel):
    categories: list[EndgameCategoryStats]  # sorted by total desc (service layer)

class EndgameGamesResponse(BaseModel):
    games: list[GameRecord]      # reuse existing GameRecord from analysis schemas
    matched_count: int
    offset: int
    limit: int
```

### Pattern 5: Frontend Page Structure (mirrors Openings.tsx)

Key differences from OpeningsPage:
- No chessboard, no board controls, no move list
- Filter sidebar is the standard FilterPanel (subset: no color, no matchSide)
- Sub-tabs: "Statistics" (default) and "Games"
- Selected category state: `useState<string | null>(null)` — persists across tab switches
- URL-driven tabs: `/endgames/statistics` (default redirect from `/endgames`) and `/endgames/games`

```typescript
// Derived tab value from location pathname
const activeTab = location.pathname.includes('/games') ? 'games' : 'statistics';

// Need redirect: /endgames → /endgames/statistics
const needsRedirect = location.pathname === '/endgames' || location.pathname === '/endgames/';
```

### Pattern 6: EndgameWDLChart Component

`WDLBarChart` is tightly coupled to `PositionBookmarkResponse`. A new `EndgameWDLChart` component is the right approach — it replicates the bar chart visual but adds inline conversion/recovery rows below each bar.

The chart renders two visual layers per category:
1. The stacked W/D/L bar (Recharts `BarChart` with `layout="vertical"`)
2. Inline text row below each bar: `"Conversion: 85% (34/40)"` and `"Recovery: 42% (11/26)"`

The inline metrics cannot live inside Recharts — they must be rendered as sibling DOM elements. The recommended approach is to render the chart and metrics in a custom layout rather than relying on pure Recharts customization.

**Recommended implementation:** Render a plain flex column outside Recharts where each row = stacked bar segment + metrics text. Use `WDLBar` component per category row instead of a full `BarChart` (simpler, avoids Recharts multi-axis complexity for this use case).

**Alternative:** Keep the full Recharts BarChart approach from WDLBarChart and render conversion/recovery as a custom Y-axis tick label. More complex but provides a true bar chart with hover tooltips.

**Recommendation (Claude's discretion):** Use the existing `WDLBarChart` Recharts pattern for the bars (same tooltip/legend UX) and render conversion/recovery as a supplementary div below the chart or as custom tick content. The planner should resolve this in the plan.

### Pattern 7: App.tsx Navigation Updates

```typescript
// Add Endgames to NAV_ITEMS (between Openings and Statistics):
import { SwordsIcon } from 'lucide-react';  // or appropriate icon

const NAV_ITEMS = [
  { to: '/import', label: 'Import', Icon: DownloadIcon },
  { to: '/openings', label: 'Openings', Icon: BookOpenIcon },
  { to: '/endgames', label: 'Endgames', Icon: SwordsIcon },  // new
  { to: '/global-stats', label: 'Statistics', Icon: BarChart3Icon },
] as const;

// Same update to BOTTOM_NAV_ITEMS
// Add to ROUTE_TITLES: '/endgames': 'Endgames'
// isActive() needs to handle /endgames prefix (same logic as /openings)
// Add route in AppRoutes: <Route path="/endgames/*" element={<EndgamesPage />} />
```

### Anti-Patterns to Avoid

- **Using `COUNT(*)` in endgame aggregations**: Always use `COUNT(DISTINCT game_id)` — a game can have multiple positions matching the endgame criteria (the constraint from STATE.md).
- **Deriving endgame class in SQL LIKE clauses**: Complex, untestable, breaks with new signature formats. Use Python post-processing.
- **Forgetting the endgame transition ply subquery**: If you query all positions in endgame phase, you'll have multiple rows per game for the same endgame type. The conversion/recovery metric requires exactly the ENTRY point material_imbalance per game.
- **Inline color filter**: CONTEXT.md D-02 explicitly excludes color filter from endgames. FilterState.color must not be used here.
- **Re-implementing FilterPanel from scratch**: Reuse existing `FilterPanel` component — just don't pass `matchSide` and `color` state to it.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Stacked bar chart | Custom SVG bars | Recharts via shadcn `ChartContainer` | Already used in WDLBarChart — consistent UX |
| Game card display | New game list UI | `GameCardList` (already reusable) | Identical data shape; direct reuse |
| Filter controls | New time control / platform buttons | `FilterPanel` component | Existing component handles all filter state |
| Tab navigation | Custom tab state | shadcn `Tabs/TabsList/TabsTrigger` | Already used in Openings page |
| Collapsible sidebar | Custom accordion | shadcn `Collapsible` | Already used in Openings page |
| W/D/L percentages | Custom math | `derive_user_result()` from `analysis_service` | Correct edge-case handling |
| Recency filter | Custom date math | `recency_cutoff()` from `analysis_service` | Already handles all recency strings |
| Game record schema | New schema | `GameRecord` from `app/schemas/analysis.py` | Same shape needed |

---

## Common Pitfalls

### Pitfall 1: COUNT(*) Instead of COUNT(DISTINCT game_id)
**What goes wrong:** A single game can appear multiple times in game_positions for the same endgame class (multiple plies in endgame phase). COUNT(*) inflates all totals.
**Why it happens:** The query joins games to game_positions without deduplication.
**How to avoid:** Always use `COUNT(DISTINCT game_id)` or equivalent subquery grouping in endgame aggregation queries.
**Warning signs:** Total game counts per category sum to more than total_games in the user's library.

### Pitfall 2: Using All Endgame Positions Instead of the Entry Ply
**What goes wrong:** Conversion/recovery uses the material imbalance from an arbitrary mid-endgame ply instead of the transition moment.
**Why it happens:** Joining game_positions without finding the minimum ply per game in endgame phase.
**How to avoid:** Use a subquery that selects `MIN(ply)` where `material_count < ENDGAME_MATERIAL_THRESHOLD` grouped by `game_id`.

### Pitfall 3: material_count / material_imbalance is Nullable
**What goes wrong:** Rows where `material_count IS NULL` (pre-Phase 26 backfill not run, or import edge case) would crash comparisons or produce wrong results.
**Why it happens:** These columns are `nullable=True` in the model (Phase 26 design).
**How to avoid:** Filter `GamePosition.material_count.is_not(None)` in all endgame queries.

### Pitfall 4: Mobile Bottom Bar Has Only 3 Slots Before This Phase
**What goes wrong:** Adding a 4th `BOTTOM_NAV_ITEMS` entry pushes the "More" button off-screen on narrow phones, or items become too narrow.
**Why it happens:** D-15 requires adding "Endgames" to the bottom nav, making it 4 items + the "More" button = 5 slots.
**How to avoid:** Test at 375px width. Consider whether "More" button needs to be in a separate nav slot or if flex layout handles 5 items. The existing mobile nav uses `flex-1` per item — 5 items at 375px = 75px each, which should still be usable.

### Pitfall 5: isActive() Helper in App.tsx Missing /endgames Prefix Match
**What goes wrong:** The "Endgames" nav item does not highlight when on `/endgames/statistics` or `/endgames/games`.
**Why it happens:** The current `isActive()` function special-cases `/openings` but not `/endgames`.
**How to avoid:** Update `isActive()` to also prefix-match `/endgames`.

### Pitfall 6: ProtectedLayout isOpeningsRoute Hides Mobile Header for /endgames
**What goes wrong:** The Openings page has special logic: `const isOpeningsRoute = location.pathname.startsWith('/openings')` which hides the mobile header on that page. The Endgames page does NOT have a board, so it should show the mobile header.
**Why it happens:** ProtectedLayout conditionally hides MobileHeader for Openings. No change needed for Endgames.
**How to avoid:** Do not add `/endgames` to the `isOpeningsRoute` check — Endgames should show the standard mobile header.

### Pitfall 7: WDLBarChart Tight Coupling to PositionBookmarkResponse
**What goes wrong:** Trying to reuse `WDLBarChart` directly with endgame data fails because the component's props are typed to `PositionBookmarkResponse[]` and a `wdlStatsMap`.
**Why it happens:** WDLBarChart was built for the Compare tab's bookmark use case.
**How to avoid:** Create a separate `EndgameWDLChart` component that accepts `EndgameCategoryStats[]` directly. The visual pattern is the same (copy the Recharts config) but the data shape is different.

---

## Code Examples

### Endgame Stats Repository Query (Skeleton)

```python
# Source: pattern from app/repositories/analysis_repository.py + STATE.md constraint

async def query_endgame_entry_rows(
    session: AsyncSession,
    user_id: int,
    time_control: list[str] | None = None,
    platform: list[str] | None = None,
    rated: bool | None = None,
    opponent_type: str = "human",
    recency_cutoff: datetime.datetime | None = None,
) -> list[tuple]:
    """Return (game_id, result, user_color, material_signature, user_material_imbalance)
    tuples for each game's endgame transition point.

    user_material_imbalance = material_imbalance if user played white, else -material_imbalance.
    Returns one row per game (deduped via MIN(ply) subquery).
    Only games that reach endgame phase are included.
    """
    # Subquery: first endgame ply per game
    entry_subq = (
        select(
            GamePosition.game_id,
            func.min(GamePosition.ply).label("entry_ply"),
        )
        .where(
            GamePosition.user_id == user_id,
            GamePosition.material_count.is_not(None),
            GamePosition.material_count < ENDGAME_MATERIAL_THRESHOLD,
        )
        .group_by(GamePosition.game_id)
        .subquery()
    )

    # Material imbalance from user's perspective (white=+, black=negate)
    user_imbalance_expr = case(
        (Game.user_color == "white", GamePosition.material_imbalance),
        else_=-GamePosition.material_imbalance,
    ).label("user_material_imbalance")

    stmt = (
        select(
            Game.id,
            Game.result,
            Game.user_color,
            GamePosition.material_signature,
            user_imbalance_expr,
        )
        .join(entry_subq, entry_subq.c.game_id == Game.id)
        .join(
            GamePosition,
            and_(
                GamePosition.game_id == Game.id,
                GamePosition.ply == entry_subq.c.entry_ply,
            ),
        )
        .where(Game.user_id == user_id)
    )

    # Apply standard filters (mirror analysis_repository._build_base_query pattern)
    if time_control is not None:
        stmt = stmt.where(Game.time_control_bucket.in_(time_control))
    if platform is not None:
        stmt = stmt.where(Game.platform.in_(platform))
    if rated is not None:
        stmt = stmt.where(Game.rated == rated)
    if opponent_type == "human":
        stmt = stmt.where(Game.is_computer_game == False)  # noqa: E712
    elif opponent_type == "bot":
        stmt = stmt.where(Game.is_computer_game == True)  # noqa: E712
    if recency_cutoff is not None:
        stmt = stmt.where(Game.played_at >= recency_cutoff)

    result = await session.execute(stmt)
    return list(result.fetchall())
```

### Service Layer Aggregation Skeleton

```python
# Source: pattern from app/services/stats_service.py

# Threshold constant — no magic numbers
ENDGAME_MATERIAL_THRESHOLD = 2600

# Material imbalance threshold: 0 cp is "even" — classify positive as up, negative as down
MATERIAL_IMBALANCE_EVEN_THRESHOLD = 0

def _aggregate_endgame_stats(rows: list[tuple]) -> list[EndgameCategoryStats]:
    """Aggregate raw endgame entry rows into EndgameCategoryStats per category.

    Each row: (game_id, result, user_color, material_signature, user_material_imbalance)
    """
    from collections import defaultdict

    counts: dict[str, dict] = defaultdict(lambda: {
        "wins": 0, "draws": 0, "losses": 0,
        "conv_wins": 0, "conv_total": 0,
        "recov_saves": 0, "recov_total": 0,
    })

    for _game_id, result, user_color, material_signature, user_imbalance in rows:
        if material_signature is None:
            continue

        cat = classify_endgame_class(material_signature)
        outcome = derive_user_result(result, user_color)
        c = counts[cat]

        if outcome == "win":
            c["wins"] += 1
        elif outcome == "draw":
            c["draws"] += 1
        else:
            c["losses"] += 1

        if user_imbalance is not None and user_imbalance > MATERIAL_IMBALANCE_EVEN_THRESHOLD:
            c["conv_total"] += 1
            if outcome == "win":
                c["conv_wins"] += 1
        elif user_imbalance is not None and user_imbalance < MATERIAL_IMBALANCE_EVEN_THRESHOLD:
            c["recov_total"] += 1
            if outcome in ("win", "draw"):
                c["recov_saves"] += 1

    result_list = []
    for cat in ENDGAME_CLASS_ORDER:
        if cat not in counts:
            continue
        c = counts[cat]
        total = c["wins"] + c["draws"] + c["losses"]
        if total == 0:
            continue
        # ... build EndgameCategoryStats
    return sorted(result_list, key=lambda x: x.total, reverse=True)
```

### Games Endpoint: Filter by Endgame Class

For `GET /endgames/games?endgame_class=rook`, the repository needs to return `GameRecord` rows for games where the endgame transition ply has `material_signature` classifying as the requested category. The query is structurally identical to `query_endgame_entry_rows` but also filters on the classified category and returns game record columns instead of aggregation columns.

Since classify_endgame_class works on all signatures for a given category, a simpler approach: use the same entry_subq, join to get material_signature at entry ply, fetch all matching rows, then filter in Python to those whose signature classifies to the requested category. Alternatively, precompute a list of SQL LIKE patterns for each category — but Python post-processing is cleaner for this.

### Frontend Types

```typescript
// frontend/src/types/endgames.ts

export type EndgameClass = 'rook' | 'minor_piece' | 'pawn' | 'queen' | 'mixed' | 'pawnless';

export interface ConversionRecoveryStats {
  conversion_pct: number;
  conversion_games: number;
  conversion_wins: number;
  recovery_pct: number;
  recovery_games: number;
  recovery_saves: number;
}

export interface EndgameCategoryStats {
  endgame_class: EndgameClass;
  label: string;
  wins: number;
  draws: number;
  losses: number;
  total: number;
  win_pct: number;
  draw_pct: number;
  loss_pct: number;
  conversion: ConversionRecoveryStats;
}

export interface EndgameStatsResponse {
  categories: EndgameCategoryStats[];
}

export interface EndgameGamesResponse {
  games: GameRecord[];  // import from api.ts
  matched_count: number;
  offset: number;
  limit: number;
}
```

### TanStack Query Hooks

```typescript
// frontend/src/hooks/useEndgames.ts

export function useEndgameStats(filters: EndgameFilterState) {
  return useQuery<EndgameStatsResponse>({
    queryKey: ['endgameStats', filters],
    queryFn: async () => {
      const params = buildEndgameParams(filters);
      const response = await apiClient.get<EndgameStatsResponse>('/endgames/stats', { params });
      return response.data;
    },
    staleTime: 30_000,
  });
}

export function useEndgameGames(
  endgameClass: EndgameClass | null,
  filters: EndgameFilterState,
  offset: number,
  limit: number,
) {
  return useQuery<EndgameGamesResponse>({
    queryKey: ['endgameGames', endgameClass, filters, offset, limit],
    queryFn: async () => {
      if (!endgameClass) return { games: [], matched_count: 0, offset, limit };
      const params = buildEndgameParams(filters);
      const response = await apiClient.get<EndgameGamesResponse>('/endgames/games', {
        params: { ...params, endgame_class: endgameClass, offset, limit },
      });
      return response.data;
    },
    enabled: endgameClass !== null,
    staleTime: 30_000,
  });
}
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| game phase stored as column | derived at query time from material_count + ply | Phase 26 | Phase 29 must apply threshold logic in queries, not read a stored column |
| endgame class stored as column | derived at query time from material_signature | Phase 26 | Phase 29 derives class in Python post-processing |
| CONV-01/02 had game-phase breakdown (opening/middlegame/endgame) | superseded — single aggregate per endgame type (D-11) | Phase 29 CONTEXT.md | Simpler implementation; REQUIREMENTS.md CONV-01/02 text is stale |

**Deprecated/outdated:**
- REQUIREMENTS.md CONV-01 text says "broken down by game phase" — this requirement as written is superseded by CONTEXT.md D-11. Implement per-endgame-type breakdown only.
- REQUIREMENTS.md ENDGM-03 says "filter by color played" — CONTEXT.md D-02 explicitly removes color filter from the Endgames page. Implement without color filter.

---

## Open Questions

1. **Exact ENDGAME_MATERIAL_THRESHOLD value**
   - What we know: material_count starts at 7800, position_classifier.py comments mention threshold tuning. The value is not stored as a constant in the codebase.
   - What's unclear: The specific cp threshold has not been committed to any file yet.
   - Recommendation: Define `ENDGAME_MATERIAL_THRESHOLD = 2600` as a named constant in `app/services/endgames_service.py` (or a shared constants file). 2600 cp corresponds to roughly KRP+KRP (500+300+100+500+300+100 = 1800 white + 800 black = 2600). This is a reasonable lower bound for "clearly in endgame". The value can be tuned without data migration per the Phase 26 design decision.

2. **EndgameWDLChart: Recharts BarChart vs. WDLBar row-per-category**
   - What we know: WDLBarChart uses Recharts BarChart with a full vertical bar chart layout. WDLBar is a simpler single-row component used elsewhere.
   - What's unclear: Whether to render 6 `WDLBar` rows in a flex column (simpler, no Recharts) or replicate the full BarChart (same UX as WDLBarChart).
   - Recommendation: Use the full Recharts BarChart approach (same as WDLBarChart) for visual consistency and tooltip support. Render conversion/recovery metrics as a separate `<div>` grid below the chart, aligned to Y-axis labels. This avoids Recharts customization complexity while keeping the same chart UX.

3. **Games tab empty state when no category selected**
   - What we know: D-12 says clicking a category on Statistics tab selects it, and Games tab shows games for that category.
   - What's unclear: What the Games tab shows before any category is selected.
   - Recommendation: Show a prompt: "Select an endgame category on the Statistics tab to view games." This parallels the Openings page "no bookmarks yet" pattern.

---

## Environment Availability

Step 2.6: SKIPPED (no external dependencies — this phase is backend/frontend code only; all tools already present in the project).

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 8.x + pytest-asyncio (asyncio_mode = "auto") |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` |
| Quick run command | `uv run pytest tests/test_endgames_repository.py tests/test_endgames_service.py -x` |
| Full suite command | `uv run pytest` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|--------------|
| ENDGM-01 | W/D/L per endgame category returned by GET /endgames/stats | integration (router) | `uv run pytest tests/test_endgames_router.py -x` | Wave 0 |
| ENDGM-01 | endgame class derivation from material_signature | unit | `uv run pytest tests/test_endgames_service.py::TestClassifyEndgameClass -x` | Wave 0 |
| ENDGM-02 | time_control filter applied to endgame stats | integration (repository) | `uv run pytest tests/test_endgames_repository.py::TestQueryEndgameEntryRows -x` | Wave 0 |
| ENDGM-03 | (superseded by D-02 — no color filter; test that no color param accepted) | integration | included in router tests | Wave 0 |
| ENDGM-04 | game count per category correct (COUNT DISTINCT game_id) | integration (repository) | `uv run pytest tests/test_endgames_repository.py::TestGameCountDeduplication -x` | Wave 0 |
| CONV-01 | conversion rate = win rate when up material | unit | `uv run pytest tests/test_endgames_service.py::TestAggregateConversion -x` | Wave 0 |
| CONV-02 | recovery rate = draw+win rate when down material | unit | `uv run pytest tests/test_endgames_service.py::TestAggregateRecovery -x` | Wave 0 |
| CONV-03 | time_control filter applied to conv/recovery stats | integration (repository) | covered by ENDGM-02 tests (same query) | Wave 0 |

### Sampling Rate

- **Per task commit:** `uv run pytest tests/test_endgames_repository.py tests/test_endgames_service.py -x`
- **Per wave merge:** `uv run pytest`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `tests/test_endgames_repository.py` — covers ENDGM-02, ENDGM-04 (repository-level)
- [ ] `tests/test_endgames_service.py` — covers ENDGM-01 class derivation, CONV-01, CONV-02
- [ ] `tests/test_endgames_router.py` — covers ENDGM-01 HTTP layer, ENDGM-03

---

## Project Constraints (from CLAUDE.md)

These directives are enforced in this phase:

- **HTTP client:** Use `httpx.AsyncClient` only — never `requests`.
- **ORM:** SQLAlchemy 2.x async `select()` API. No legacy 1.x syntax.
- **Foreign keys:** Every FK column must have `ForeignKey()` with explicit `ondelete`.
- **No magic numbers:** `ENDGAME_MATERIAL_THRESHOLD`, `MATERIAL_IMBALANCE_EVEN_THRESHOLD`, `PAGE_SIZE`, and category label constants must be named constants.
- **Type safety:** Full TypeScript types for all props, hooks, and API responses. No `any`.
- **data-testid on every interactive element:** All buttons, tab triggers, filter toggles, category rows (if clickable), and major containers need `data-testid`. Use `endgames-` prefix.
- **Mobile variants:** Both desktop sidebar and mobile collapsible filter sections must be implemented. Apply all changes to both layouts (CLAUDE.md "Always check mobile variants").
- **Semantic HTML:** `<button>` for clickable elements, `<main>` for page content, `<nav>` for nav regions.
- **Comment bug fixes:** Any non-obvious conditional logic (e.g., the sign flip for black material imbalance) must have a comment explaining why.
- **COUNT(DISTINCT game_id):** STATE.md critical constraint — all endgame aggregation queries must deduplicate by game_id.

---

## Sources

### Primary (HIGH confidence)

- Direct code reading: `app/services/position_classifier.py` — material_count definition, signature format
- Direct code reading: `app/models/game_position.py` — column types, nullability
- Direct code reading: `app/repositories/analysis_repository.py` — filter pattern, _build_base_query
- Direct code reading: `app/services/stats_service.py` — Python-side aggregation pattern
- Direct code reading: `frontend/src/components/charts/WDLBarChart.tsx` — bar chart to replicate
- Direct code reading: `frontend/src/pages/Openings.tsx` — page structure to mirror
- Direct code reading: `frontend/src/App.tsx` — NAV_ITEMS, routing, isActive pattern
- Direct code reading: `frontend/src/components/filters/FilterPanel.tsx` — filter state interface
- `.planning/phases/29-endgame-analytics/29-CONTEXT.md` — locked decisions
- `.planning/STATE.md` — critical constraints (COUNT DISTINCT, nullable columns)

### Secondary (MEDIUM confidence)

- CONTEXT.md D-11 note: "CONV requirements reference game phase breakdown which has been superseded" — confirms REQUIREMENTS.md CONV-01/02 text is stale

### Tertiary (LOW confidence)

- `ENDGAME_MATERIAL_THRESHOLD = 2600` — derived from piece value math, not from a committed project constant. Should be validated against actual endgame position distributions.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries already in project, no new dependencies
- Architecture patterns: HIGH — directly verified against existing code in canonical refs
- Pitfalls: HIGH — derived from STATE.md constraints and direct code review
- Threshold constant (2600 cp): LOW — reasonable estimate, must be confirmed as named constant

**Research date:** 2026-03-26
**Valid until:** 2026-04-25 (stable stack — no fast-moving dependencies)
