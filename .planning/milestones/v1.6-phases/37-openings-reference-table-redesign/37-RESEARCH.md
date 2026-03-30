# Phase 37: Openings Reference Table & Most Played Openings Redesign - Research

**Researched:** 2026-03-28
**Domain:** PostgreSQL seeding + SQLAlchemy model + SQL-side WDL aggregation + React table with popover
**Confidence:** HIGH

## Summary

Phase 37 has three connected work streams. First, a new `openings` PostgreSQL table is seeded from
`app/data/openings.tsv` (~3641 rows). Each row stores ECO code, name, PGN, ply count (computed via
`board.ply()` in python-chess), and FEN (computed via `board.board_fen()`). A deduplicated DB view
`openings_dedup` collapses the 204 duplicate `(eco, name)` pairs — keeping one representative FEN
and PGN per pair — for use in JOIN queries against the `games` table.

Second, the `GET /stats/most-played-openings` endpoint (Phase 36, fully implemented) is redesigned.
It gains filter parameters (recency, time_control, platform, rated, opponent_type), increases the
result limit from 5 to 10, and moves WDL computation from Python-side aggregation (join + fetch all
rows) to SQL-side aggregation using `func.count().filter(...)` — a single GROUP BY query per color.
The response schema gains new fields per opening: `fen` (from `openings_dedup`) and `pgn`.

Third, the Most Played Openings section in `Openings.tsx` is redesigned: the existing `WDLChartRow`
component is replaced with a dedicated `MostPlayedOpeningsTable` component that renders a
three-column layout (ECO+name+PGN / game count with folder icon / mini WDL bar). Row hover/tap
shows a `MinimapPopover` using `Chessboard` from `react-chessboard` with a static position.

**Primary recommendation:** Implement in four distinct waves: (1) DB model + seed script + migration
+ dedup view, (2) redesigned backend endpoint with SQL-side WDL + filter params, (3) updated
frontend API client + hook + types, (4) new `MostPlayedOpeningsTable` + `MinimapPopover` components
replacing the old `WDLChartRow` usage in `statisticsContent`.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| ORT-01 | `openings` table contains all ~3641 rows from TSV with correct `ply_count` and `fen` via python-chess | New `Opening` SQLAlchemy model + Alembic migration + seed script using `chess.pgn.read_game` |
| ORT-02 | Deduplicated view returns one row per `(eco, name)` pair | `CREATE VIEW openings_dedup AS ... DISTINCT ON (eco, name)` — defined in migration |
| ORT-03 | Endpoint returns top 10 openings per color with SQL-side WDL stats, filtered by recency/time_control/platform/rated/opponent_type, excluding openings below ply threshold | Updated `query_top_openings_sql_wdl()` in `stats_repository.py` using `func.count().filter()` + JOIN to `openings_dedup` |
| ORT-04 | Frontend renders dedicated table with ECO/name/PGN, game count link, mini WDL bar | New `MostPlayedOpeningsTable` component — replaces `WDLChartRow` rows in `statisticsContent` |
| ORT-05 | Hovering/tapping a row shows a minimap popover of the opening position | `MinimapPopover` component wrapping Radix `Popover` + `Chessboard` from `react-chessboard` |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

- **No magic numbers:** `TOP_OPENINGS_LIMIT = 10`, `MIN_PLY_WHITE = 1`, `MIN_PLY_BLACK = 2`,
  `MIN_GAMES_FOR_OPENING = 10` must be named constants. Mirror relevant ones in the frontend component.
- **Theme constants in theme.ts:** Any new color values must go in `theme.ts`. The mini WDL bar
  reuses existing `WDL_WIN`, `WDL_DRAW`, `WDL_LOSS`, `GLASS_OVERLAY` constants.
- **Type safety:** New TypeScript interfaces must be explicit. Use `Literal["white", "black"]` in
  Python function signatures for color parameters.
- **data-testid on all interactive/layout elements:** Table container, each row, the minimap
  trigger, and the popover must have `data-testid`.
- **Always check mobile variants:** `statisticsContent` is referenced in both desktop and mobile
  `<TabsContent>` blocks in `Openings.tsx`. The variable is shared (defined once) — changes
  propagate automatically, but verify before shipping.
- **SQLAlchemy 2.x async:** `select()` API only; no legacy 1.x patterns.
- **No SQLite:** PostgreSQL only.
- **Pydantic v2 throughout.**
- **Foreign key constraints mandatory:** The `openings` table is standalone (no FK to other tables),
  but must have appropriate indexed columns for JOIN performance.
- **API responses never expose internal hashes.**
- **Semantic HTML + ARIA:** Minimap trigger must have `aria-label`. Table rows that are clickable
  must use semantic elements or role attributes.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| SQLAlchemy 2.x async | project-wide | New `Opening` model, `openings_dedup` view, updated query | Project ORM |
| Alembic | project-wide | Migration to create `openings` table + `openings_dedup` view | Project migration tool |
| python-chess | >=1.10.0 | Compute `ply_count` and `fen` from PGN during seeding | Project chess logic library |
| FastAPI | 0.115.x | Updated endpoint with new filter params | Project framework |
| Pydantic v2 | project-wide | Updated response schema with `fen`/`pgn` fields | Project validation |
| TanStack Query | project-wide | Updated `useMostPlayedOpenings` hook with filter params | Project data fetching |
| react-chessboard | 5.x | Static board render in minimap popover | Already project dependency |
| radix-ui Popover | 1.4.3 | Minimap popover trigger/content | Already used via `InfoPopover` |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `func.count().filter()` | SQLAlchemy 2.x | SQL-side WDL aggregation | Replaces Python-side `_aggregate_top_openings` |
| `DISTINCT ON (eco, name)` | PostgreSQL | Deduplicated view | One row per opening name in JOIN |
| lucide-react | project-wide | `FolderOpen` or `ExternalLink` icon for games link | Consistent with existing icon usage |

**No new npm packages or Python packages required.** All dependencies are already installed.

## Architecture Patterns

### Backend: New `Opening` SQLAlchemy Model

```python
# app/models/opening.py — NEW FILE
from sqlalchemy import Index, SmallInteger, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Opening(Base):
    __tablename__ = "openings"
    __table_args__ = (
        UniqueConstraint("eco", "name", "pgn", name="uq_openings_eco_name_pgn"),
        Index("ix_openings_eco_name", "eco", "name"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    eco: Mapped[str] = mapped_column(String(10), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    pgn: Mapped[str] = mapped_column(Text, nullable=False)
    ply_count: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    fen: Mapped[str] = mapped_column(String(100), nullable=False)
```

**Rationale for UniqueConstraint on `(eco, name, pgn)`:** All 3641 rows are kept (including 204
duplicate `(eco, name)` pairs with different PGN/transpositions). The triple uniqueness constraint
prevents duplicate inserts during repeated seed runs.

### Backend: Seed Script

```
scripts/seed_openings.py   — NEW: one-shot idempotent seeding from TSV
```

The seed script reads `app/data/openings.tsv`, computes `ply_count` and `fen` via python-chess for
each row, and bulk-inserts with `INSERT INTO openings ... ON CONFLICT DO NOTHING`. This is safe to
run multiple times.

```python
# Source: python-chess docs — chess.pgn.read_game, board.board_fen(), board.ply()
import chess.pgn, io

def pgn_to_fen_and_ply(pgn_str: str) -> tuple[str, int]:
    game = chess.pgn.read_game(io.StringIO(pgn_str))
    board = game.board()
    for move in game.mainline_moves():
        board.push(move)
    return board.board_fen(), board.ply()
```

**PGN parse failure handling:** Wrap each row in a try/except. On error, log and skip — don't abort
the entire seed. The TSV is the lichess openings database (high quality), so failures should be
rare, but the constraint is documented in CLAUDE.md: "wrap per-game in try/except."

### Backend: Alembic Migration

The migration does two things:
1. Creates the `openings` table (Alembic autogenerate after adding `Opening` to `alembic/env.py`).
2. Creates the `openings_dedup` view with a raw SQL `execute()` call.

```python
# In the migration upgrade():
op.execute("""
    CREATE VIEW openings_dedup AS
    SELECT DISTINCT ON (eco, name)
        id, eco, name, pgn, ply_count, fen
    FROM openings
    ORDER BY eco, name, id
""")
```

**DISTINCT ON ordering:** `ORDER BY eco, name, id` picks the lowest `id` (first-inserted row) as
the representative per `(eco, name)` pair. This is deterministic given a fixed seed order.

```python
# In the migration downgrade():
op.execute("DROP VIEW IF EXISTS openings_dedup")
```

### Backend: SQL-side WDL Aggregation

The redesigned repository function performs a single JOIN+GROUP BY query instead of the current
subquery + full row fetch approach. This is fundamentally more efficient (no Python iteration over
individual game rows) and required by ORT-03.

```python
# Source: SQLAlchemy 2.x docs — func.count().filter() verified above
from sqlalchemy import func, or_, and_, select
from app.models.game import Game
# Note: openings_dedup is a DB view — use text() or reflect with Table()

async def query_top_openings_sql_wdl(
    session: AsyncSession,
    user_id: int,
    color: Literal["white", "black"],
    min_games: int,
    limit: int,
    min_ply: int,
    recency_cutoff: datetime.datetime | None = None,
    time_control: list[str] | None = None,
    platform: list[str] | None = None,
    rated: bool | None = None,
    opponent_type: str = "human",
) -> list[tuple]:
    """Return WDL aggregates per (eco, name) with filter support.

    Joins games to openings_dedup to get fen and pgn.
    Filters by min_ply from openings_dedup.ply_count.
    Returns (eco, name, pgn, fen, total, wins, draws, losses) tuples.
    """
    white_win = and_(Game.result == "1-0", Game.user_color == "white")
    black_win = and_(Game.result == "0-1", Game.user_color == "black")
    win_cond = or_(white_win, black_win)
    draw_cond = Game.result == "1/2-1/2"

    # openings_dedup as a reflected table (or use text subquery)
    ...
```

**Implementation note on `openings_dedup` access:** Since SQLAlchemy ORM models map to tables, not
views, the `openings_dedup` view must be accessed via `text()`-based subquery or by reflecting it.
The cleanest approach is to define a `Table()` object for the view:

```python
from sqlalchemy import Table, Column, String, SmallInteger, MetaData
_openings_dedup = Table(
    "openings_dedup",
    MetaData(),
    Column("id", primary_key=True),
    Column("eco", String(10)),
    Column("name", String(200)),
    Column("pgn", Text),
    Column("ply_count", SmallInteger),
    Column("fen", String(100)),
)
```

This avoids ORM mapping complexity while still getting type-checked column access.

### Backend: Updated Response Schema

```python
# app/schemas/stats.py — updated OpeningWDL
class OpeningWDL(BaseModel):
    opening_eco: str
    opening_name: str
    label: str          # "Opening Name (ECO)" — precomputed for UI
    pgn: str            # NEW: PGN move sequence for display
    fen: str            # NEW: position FEN for minimap popover
    wins: int
    draws: int
    losses: int
    total: int
    win_pct: float
    draw_pct: float
    loss_pct: float
```

**Backward compatibility note:** Adding `pgn` and `fen` fields to `OpeningWDL` breaks the existing
`GET /stats/most-played-openings` response. Since Phase 36 was just implemented and Phase 37
replaces the endpoint behavior, this is expected — the frontend is also being redesigned.

### Backend: Updated Service + Router

```python
# stats_service.py — updated constants
TOP_OPENINGS_LIMIT = 10  # was 5 in Phase 36
MIN_PLY_WHITE = 1         # NEW: white needs at least 1 ply
MIN_PLY_BLACK = 2         # NEW: black needs at least 2 plies

# stats_router.py — new filter params
@router.get("/stats/most-played-openings", response_model=MostPlayedOpeningsResponse)
async def get_most_played_openings(
    session: ...,
    user: ...,
    recency: str | None = Query(default=None),
    time_control: list[str] | None = Query(default=None),
    platform: list[str] | None = Query(default=None),
    rated: bool | None = Query(default=None),
    opponent_type: str = Query(default="human"),
) -> MostPlayedOpeningsResponse:
    ...
```

**Color and matchSide are NOT filter params** — the response already splits by color (white/black),
so no color param is needed. matchSide is for board hash analysis, not this feature.

### Frontend: Updated Hook

```typescript
// hooks/useStats.ts — updated useMostPlayedOpenings
export function useMostPlayedOpenings(filters: MostPlayedFilters) {
  const { recency, timeControls, platforms, rated, opponentType } = filters;
  const normalizedRecency = recency === 'all' ? null : recency;
  const platform = ...; // flatten array to string if single
  return useQuery({
    queryKey: ['mostPlayedOpenings', normalizedRecency, timeControls, platforms, rated, opponentType],
    queryFn: () => statsApi.getMostPlayedOpenings({ ... }),
  });
}
```

The hook takes a subset of `FilterState` (not the full board-explorer filter). **Color and
matchSide are excluded** per the design decision.

### Frontend: New `MostPlayedOpeningsTable` Component

New file: `frontend/src/components/stats/MostPlayedOpeningsTable.tsx`

Three-column table per row:
- Column 1: ECO code + opening name (break after colon if present in name) + PGN moves on next line(s)
- Column 2: game count number + `FolderOpen` (or `ExternalLink`) icon as link to `/openings/games`
- Column 3: mini WDL bar (reuse the WDL bar segment markup from `WDLChartRow`, not the full row component)

**Name formatting:** Split on `: ` and insert a line break if colon is found. Example:
`"Ruy Lopez: Morphy Defense"` → `Ruy Lopez:` / `Morphy Defense`.

**PGN display:** Render the PGN string as-is below the name in `text-xs text-muted-foreground`.
Truncate long PGN strings to fit column width on mobile (or wrap naturally).

### Frontend: `MinimapPopover` Component

New file: `frontend/src/components/stats/MinimapPopover.tsx`

Wraps Radix `Popover` from `radix-ui` (same import pattern as `InfoPopover` — `import { Popover as
PopoverPrimitive } from "radix-ui"`). Trigger is the opening name cell (the row itself acts as
hover trigger). On hover/tap, renders a static `Chessboard` at a small fixed size (e.g. 180px).

```tsx
import { Popover as PopoverPrimitive } from "radix-ui";
import { Chessboard } from "react-chessboard";

// Minimal static board — no drag/drop, no arrows
<Chessboard
  id="minimap-board"
  position={fen}
  boardWidth={180}
  arePiecesDraggable={false}
  customDarkSquareStyle={{ backgroundColor: BOARD_DARK_SQUARE }}
  customLightSquareStyle={{ backgroundColor: BOARD_LIGHT_SQUARE }}
/>
```

**react-chessboard static rendering:** `arePiecesDraggable={false}` and no `onPieceDrop` prop
disables interaction. `boardWidth` prop sets fixed pixel size.

**Mobile support:** Popover trigger on mobile should open on tap (click), not just hover. Use
`onClick` toggle for mobile compatibility (same approach as `InfoPopover` which uses `onMouseEnter`
+ `onOpenChange`).

### Recommended Project Structure Changes

```
app/
├── models/opening.py               # NEW: Opening SQLAlchemy model
├── repositories/stats_repository.py # MODIFIED: new query function
├── services/stats_service.py        # MODIFIED: SQL WDL, new constants, filter params
├── routers/stats.py                 # MODIFIED: new query params
└── schemas/stats.py                 # MODIFIED: pgn/fen fields on OpeningWDL

scripts/
└── seed_openings.py                 # NEW: idempotent seed script

alembic/versions/
└── XXXXXX_create_openings_table.py  # NEW: table + view + alembic/env.py import

frontend/src/
├── components/stats/               # NEW directory
│   ├── MostPlayedOpeningsTable.tsx # NEW: dedicated table component
│   └── MinimapPopover.tsx          # NEW: hover/tap popover with static board
├── types/stats.ts                  # MODIFIED: pgn/fen fields on OpeningWDL
├── api/client.ts                   # MODIFIED: getMostPlayedOpenings with filter params
├── hooks/useStats.ts               # MODIFIED: useMostPlayedOpenings with filter params
└── pages/Openings.tsx              # MODIFIED: wire filters, replace WDLChartRow with new table
```

### Anti-Patterns to Avoid

- **Full-scan seed:** Don't INSERT + DELETE on every restart. Use `ON CONFLICT DO NOTHING` to make
  seeding idempotent.
- **ORM model for the view:** Don't map `openings_dedup` as a SQLAlchemy ORM class — it's a view,
  and autogenerate will try to drop/recreate it. Use `Table()` with `MetaData()` (not
  `Base.metadata`) so it's invisible to Alembic autogenerate.
- **Python-side WDL aggregation:** Phase 37 mandates SQL-side aggregation. Do not retain the old
  `_aggregate_top_openings` path for the new query. Keep the function in case it's used elsewhere
  but don't call it from the redesigned service function.
- **Passing color filter to the endpoint:** Color is not a filter here — the response has separate
  `white` and `black` lists. The `color` filter in `FilterPanel` is for the board hash explorer
  feature, not for Most Played Openings.
- **Using `board.fen()` instead of `board.board_fen()`:** CLAUDE.md is explicit: use
  `board.board_fen()` (piece placement only). `board.fen()` includes castling/en passant which
  would mismatch existing FEN comparisons in the codebase.
- **Hard-coding popover width/board size:** Extract `MINIMAP_BOARD_SIZE = 180` as a named constant.
- **Forgetting `data-testid="chessboard"` and `id="chessboard"` on the minimap board:** CLAUDE.md
  requires `data-testid="chessboard"`. For the minimap, use a unique id like `"minimap-board"` to
  avoid conflicting with the main board's `id="chessboard"`.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| WDL bar rendering | Custom bar markup | Reuse WDL bar segment CSS from `WDLChartRow` (extract or copy inline) | Consistent visual output, existing tested pattern |
| Chess position display | Custom SVG/canvas rendering | `Chessboard` from `react-chessboard` with `arePiecesDraggable={false}` | Already project dependency, handles piece rendering |
| Popover behavior | Custom CSS hover/focus management | `Popover` from `radix-ui` | Already used in `InfoPopover`, handles Portal, z-index, animation |
| FEN computation | Manual board state parsing | `chess.pgn.read_game` + `board.board_fen()` | python-chess handles all edge cases (castling, en passant, en passant ignored per CLAUDE.md) |
| Idempotent seeding | Manual SELECT + conditional INSERT | `INSERT ... ON CONFLICT DO NOTHING` with `UniqueConstraint` | Single-pass, safe for repeated runs |

## Common Pitfalls

### Pitfall 1: Alembic Autogenerate Detecting the View

**What goes wrong:** If `openings_dedup` Table is added to `Base.metadata`, Alembic autogenerate
will try to CREATE TABLE for the view on every run (or error when it detects a mismatch).
**Why it happens:** Alembic treats any table in `Base.metadata` as a managed table.
**How to avoid:** Define the `_openings_dedup` Table with a standalone `MetaData()` instance, NOT
`Base.metadata`. The view DDL goes in a handwritten `op.execute()` in the migration.
**Warning signs:** `alembic revision --autogenerate` adds unexpected CREATE TABLE statements.

### Pitfall 2: `board.fen()` vs `board.board_fen()`

**What goes wrong:** The FEN stored in `openings.fen` includes castling rights and en passant
targets if `board.fen()` is used. The FEN is only used for minimap display in Phase 37, so this
won't cause position-matching bugs today — but storing the wrong FEN format is inconsistent with
the codebase convention and would cause issues if the column is ever used for matching.
**Why it happens:** Confusion between the two python-chess methods.
**How to avoid:** Always use `board.board_fen()` per CLAUDE.md. Document in the seed script.

### Pitfall 3: DISTINCT ON Ordering in `openings_dedup`

**What goes wrong:** Without an explicit `ORDER BY eco, name, id`, PostgreSQL's `DISTINCT ON`
behavior is non-deterministic (it picks an arbitrary row per group on repeated runs).
**Why it happens:** `DISTINCT ON (cols)` requires the first `ORDER BY` columns to match the
DISTINCT columns.
**How to avoid:** Always `ORDER BY eco, name, id` in the view definition.

### Pitfall 4: NULL opening_eco / opening_name in Games Join

**What goes wrong:** Games with NULL `opening_eco` or `opening_name` cannot join to
`openings_dedup`. If not filtered, they produce NULL values in the result set.
**Why it happens:** `Game.opening_eco` and `Game.opening_name` are nullable (CLAUDE.md note about
NULL columns was documented in Phase 36 research).
**How to avoid:** Add `.where(Game.opening_eco.is_not(None), Game.opening_name.is_not(None))` to
the updated repository query.

### Pitfall 5: `func.count().filter()` Precedence

**What goes wrong:** `func.count().filter(A & B | C)` may not parse as intended due to Python
operator precedence — `&` binds tighter than `|`, but wrapping with `and_()` / `or_()` is clearer.
**Why it happens:** SQLAlchemy's column operators `&`, `|`, `~` have precedence issues.
**How to avoid:** Always use explicit `and_()` / `or_()` imports from `sqlalchemy` for compound
conditions. Verified pattern in Pitfall verification above:
```python
win_cond = or_(
    and_(Game.result == "1-0", Game.user_color == "white"),
    and_(Game.result == "0-1", Game.user_color == "black"),
)
wins_col = func.count().filter(win_cond).label("wins")
```

### Pitfall 6: Seed Script Import Path

**What goes wrong:** `scripts/seed_openings.py` imports from `app.*` but the `scripts/` package
must be importable. Phase 27 added `scripts/__init__.py` for this purpose.
**Why it happens:** Python package resolution when running scripts from the repo root.
**How to avoid:** Verify `scripts/__init__.py` exists (it does — added in Phase 27). Run seed
script with `uv run python -m scripts.seed_openings` to use module mode.

### Pitfall 7: Popover Z-Index / Portal Stacking

**What goes wrong:** The minimap popover appears behind other page elements (sticky filter bar,
modal dialogs) because the z-index is insufficient.
**Why it happens:** Radix `PopoverContent` uses z-50 by default, which conflicts with other z-50
elements.
**How to avoid:** Use `PopoverPrimitive.Portal` (same as `InfoPopover`) to portal the content to
`document.body`. This ensures correct stacking context. Use `z-[100]` or similar if conflicts arise.

### Pitfall 8: Mobile Missing Hover Trigger

**What goes wrong:** On mobile/touch devices, `onMouseEnter`/`onMouseLeave` events don't fire.
The minimap popover never opens.
**Why it happens:** Touch devices don't have hover. The existing `InfoPopover` handles this via
`onOpenChange` (which fires on click/tap).
**How to avoid:** Use `onOpenChange` as the primary toggle, or combine hover + click: set `open`
state on `onMouseEnter` and toggle on click. The simplest pattern: let Radix manage open state
via `onOpenChange` (uncontrolled). On mobile, a tap opens the popover; a tap outside closes it.
For desktop, add `onMouseEnter`/`onMouseLeave` to the trigger for hover behavior.

## Code Examples

### python-chess FEN + ply computation (verified)

```python
# Source: verified via uv run python3, 2026-03-28
import chess
import chess.pgn
import io

def pgn_to_fen_and_ply(pgn_str: str) -> tuple[str, int]:
    """Compute piece-placement FEN and ply count from a PGN move sequence.

    Uses board.board_fen() (not board.fen()) per project convention.
    """
    game = chess.pgn.read_game(io.StringIO(pgn_str))
    if game is None:
        raise ValueError(f"Failed to parse PGN: {pgn_str!r}")
    board = game.board()
    for move in game.mainline_moves():
        board.push(move)
    return board.board_fen(), board.ply()
```

### SQL-side WDL aggregate (verified SQLAlchemy 2.x)

```python
# Source: verified via uv run python3 with SQLAlchemy 2.x, 2026-03-28
from sqlalchemy import and_, func, or_

win_cond = or_(
    and_(Game.result == "1-0", Game.user_color == "white"),
    and_(Game.result == "0-1", Game.user_color == "black"),
)
draw_cond = Game.result == "1/2-1/2"
loss_cond = or_(
    and_(Game.result == "0-1", Game.user_color == "white"),
    and_(Game.result == "1-0", Game.user_color == "black"),
)

stmt = (
    select(
        Game.opening_eco,
        Game.opening_name,
        func.count().label("total"),
        func.count().filter(win_cond).label("wins"),
        func.count().filter(draw_cond).label("draws"),
        func.count().filter(loss_cond).label("losses"),
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
# Generates: count(*) FILTER (WHERE result='1-0' AND user_color='white' OR ...)
```

### Alembic migration for view (pattern)

```python
# In migration upgrade():
op.execute("""
    CREATE VIEW openings_dedup AS
    SELECT DISTINCT ON (eco, name)
        id, eco, name, pgn, ply_count, fen
    FROM openings
    ORDER BY eco, name, id
""")

# In migration downgrade():
op.execute("DROP VIEW IF EXISTS openings_dedup")
op.drop_table("openings")
```

### MinimapPopover trigger pattern

```tsx
// Source: info-popover.tsx pattern adapted for row hover, 2026-03-28
import { Popover as PopoverPrimitive } from "radix-ui";
import { Chessboard } from "react-chessboard";
import { BOARD_DARK_SQUARE, BOARD_LIGHT_SQUARE } from "@/lib/theme";

const MINIMAP_BOARD_SIZE = 180;

export function MinimapPopover({ fen, children, testId }: MinimapPopoverProps) {
  const [open, setOpen] = useState(false);
  const hoverTimeout = useRef<ReturnType<typeof setTimeout> | null>(null);

  const handleMouseEnter = () => {
    hoverTimeout.current = setTimeout(() => setOpen(true), 150);
  };
  const handleMouseLeave = () => {
    if (hoverTimeout.current) clearTimeout(hoverTimeout.current);
    setOpen(false);
  };

  return (
    <PopoverPrimitive.Root open={open} onOpenChange={setOpen}>
      <PopoverPrimitive.Trigger asChild>
        <div
          onMouseEnter={handleMouseEnter}
          onMouseLeave={handleMouseLeave}
          data-testid={testId}
        >
          {children}
        </div>
      </PopoverPrimitive.Trigger>
      <PopoverPrimitive.Portal>
        <PopoverPrimitive.Content
          side="right"
          sideOffset={8}
          onMouseEnter={() => { if (hoverTimeout.current) clearTimeout(hoverTimeout.current); }}
          onMouseLeave={handleMouseLeave}
          className="z-50 rounded-md shadow-lg overflow-hidden"
          data-testid={`${testId}-popover`}
        >
          <Chessboard
            id="minimap-board"
            position={fen}
            boardWidth={MINIMAP_BOARD_SIZE}
            arePiecesDraggable={false}
            customDarkSquareStyle={{ backgroundColor: BOARD_DARK_SQUARE }}
            customLightSquareStyle={{ backgroundColor: BOARD_LIGHT_SQUARE }}
          />
        </PopoverPrimitive.Content>
      </PopoverPrimitive.Portal>
    </PopoverPrimitive.Root>
  );
}
```

### `openings_dedup` Table object for non-ORM access

```python
# In stats_repository.py — table object for view access
from sqlalchemy import Column, MetaData, SmallInteger, String, Table, Text

_openings_dedup = Table(
    "openings_dedup",
    MetaData(),  # NOT Base.metadata — keeps it invisible to Alembic autogenerate
    Column("id"),
    Column("eco", String(10)),
    Column("name", String(200)),
    Column("pgn", Text),
    Column("ply_count", SmallInteger),
    Column("fen", String(100)),
)
```

## TSV Dataset Facts (verified)

| Fact | Value | Source |
|------|-------|--------|
| Total rows | 3641 | `wc -l openings.tsv` minus header |
| Unique `(eco, name)` pairs | 3301 | Python analysis |
| Duplicate `(eco, name)` pairs | 340 (204 unique pairs with 2+ PGNs) | Python analysis |
| Max PGN ply count | 22 | `1. e4 e5 2. Nf3 Nc6 ... 11. Rxe5 c6` |
| TSV columns | eco, name, pgn | Header row verified |
| TSV path | `app/data/openings.tsv` | Direct inspection |

## Filter Parameters: Mapping to Backend

| Frontend FilterState field | Backend param | Included? | Notes |
|---------------------------|---------------|-----------|-------|
| `recency` | `recency` | YES | Via `recency_cutoff()` helper |
| `timeControls` | `time_control` | YES | Array param |
| `platforms` | `platform` | YES | Array param |
| `rated` | `rated` | YES | `bool | None` |
| `opponentType` | `opponent_type` | YES | Default `"human"` |
| `color` | — | IGNORED | Response already splits by color |
| `matchSide` | — | IGNORED | Board hash feature only |

## State of the Art

| Old Approach | Current Approach | Impact |
|--------------|------------------|--------|
| Python-side WDL aggregation (fetch rows + iterate) | SQL-side `COUNT(*) FILTER (WHERE ...)` | Single DB round-trip, no Python loop over game rows |
| Top 5 openings, no filters | Top 10 openings, full filter support | More useful, consistent with other stats endpoints |
| `WDLChartRow` for each opening | Dedicated `MostPlayedOpeningsTable` with ECO/name/PGN columns | Better information density, adds PGN display |
| No position preview | `MinimapPopover` on hover/tap | Quick position reference without navigating away |
| No openings DB table (TSV only in memory via trie) | `openings` table + `openings_dedup` view | Enables SQL JOINs for richer aggregation |

## Open Questions

1. **Minimap popover position on mobile**
   - What we know: On mobile, the popover `side="right"` may go off-screen.
   - What's unclear: Whether Radix auto-flips the side when space is insufficient.
   - Recommendation: Use `side="top"` with `align="start"` as fallback, or test on a narrow
     viewport. Radix's collision detection should handle this automatically via `avoidCollisions`.

2. **Game count link: navigate to games tab or filter by opening?**
   - What we know: The games tab shows position-filtered games (using hash). The design says
     "game count link with folder icon to open games" — but no mechanism exists to filter by
     opening name in the games tab (analysis endpoint uses hash, not eco/name).
   - What's unclear: Whether "open games" means navigate to `/openings/games` (unfiltered) or
     provide a filtered view.
   - Recommendation: For Phase 37, link to `/openings/games` (navigate to games tab) as the
     simplest correct interpretation. A filtered game list by opening name would require a new
     backend endpoint. Flag this if the user expects filtered games.

3. **WHERE to wire `useMostPlayedOpenings` filter params in `Openings.tsx`**
   - What we know: `Openings.tsx` already has `debouncedFilters` (full `FilterState`).
   - What's unclear: Whether a separate filter state is needed, or whether the existing
     `debouncedFilters` is passed directly (minus `color` and `matchSide`).
   - Recommendation: Pass `debouncedFilters` directly, extracting only the relevant fields
     (recency, timeControls, platforms, rated, opponentType). No separate state needed.

## Environment Availability

Step 2.6: SKIPPED — all dependencies (Python libraries, npm packages, PostgreSQL) are already
available in the project environment. No new external services or tools are required.

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
| ORT-01 | Seed script inserts ~3641 rows with correct `ply_count` and `fen` | unit | `uv run pytest tests/test_seed_openings.py -x` | ❌ Wave 0 |
| ORT-01 | Seed script is idempotent (safe to run twice) | unit | `uv run pytest tests/test_seed_openings.py -x -k idempotent` | ❌ Wave 0 |
| ORT-02 | `openings_dedup` view returns one row per `(eco, name)` | integration | `uv run pytest tests/test_seed_openings.py -x -k dedup_view` | ❌ Wave 0 |
| ORT-03 | `query_top_openings_sql_wdl` returns top 10 with correct WDL counts | unit | `uv run pytest tests/test_stats_repository.py -x -k sql_wdl` | ❌ Wave 0 |
| ORT-03 | Filter params (recency/time_control/platform/rated/opponent_type) affect results | unit | `uv run pytest tests/test_stats_repository.py -x -k sql_wdl_filters` | ❌ Wave 0 |
| ORT-03 | Ply threshold (min_ply) excludes short openings | unit | `uv run pytest tests/test_stats_repository.py -x -k ply_threshold` | ❌ Wave 0 |
| ORT-03 | `GET /stats/most-played-openings` returns 200 with `pgn` and `fen` fields | integration | `uv run pytest tests/test_stats_router.py -x -k most_played_openings` | ✅ (extend) |
| ORT-03 | `GET /stats/most-played-openings` accepts filter params | integration | `uv run pytest tests/test_stats_router.py -x -k most_played_openings` | ✅ (extend) |

**Note on ORT-04 and ORT-05:** These are pure frontend requirements. They are validated via visual
inspection and browser automation testing (data-testid presence), not pytest. Mark as manual-only.

| Req ID | Behavior | Test Type | Notes |
|--------|----------|-----------|-------|
| ORT-04 | Table renders ECO/name/PGN, game count link, mini WDL bar | manual + browser | Verify `data-testid="mpo-table"` in DOM |
| ORT-05 | Hover/tap shows minimap popover with correct position | manual + browser | Verify `data-testid="minimap-popover"` in DOM |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/test_stats_repository.py tests/test_stats_router.py -x`
- **Per wave merge:** `uv run pytest`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_seed_openings.py` — new test file covering ORT-01, ORT-02
- [ ] `tests/test_stats_repository.py` — add `TestQueryTopOpeningsSqlWDL` class for ORT-03 (replace/extend `TestQueryTopOpeningsByColor`)
- [ ] `tests/test_stats_router.py` — extend `TestGetMostPlayedOpenings` for ORT-03 (new params, `pgn`/`fen` fields)

The existing `TestQueryTopOpeningsByColor` in `test_stats_repository.py` tests the Phase 36 Python-
aggregation approach. Phase 37 replaces this with SQL-side aggregation — the old tests should be
updated to the new function signature, not kept alongside.

## Sources

### Primary (HIGH confidence)
- Direct codebase inspection: `app/data/openings.tsv` — 3641 rows, columns: eco/name/pgn, confirmed
- Direct codebase inspection: `app/services/opening_lookup.py` — TSV loading pattern confirmed
- Direct codebase inspection: `app/models/game.py` — `opening_eco` (String(10)), `opening_name` (String(200)) nullable confirmed
- Direct codebase inspection: `app/repositories/stats_repository.py` — Phase 36 `query_top_openings_by_color` confirmed implemented
- Direct codebase inspection: `app/services/stats_service.py` — `TOP_OPENINGS_LIMIT = 5`, `_aggregate_top_openings` confirmed
- Direct codebase inspection: `app/routers/stats.py` — endpoint confirmed with no filter params
- Direct codebase inspection: `app/repositories/endgame_repository.py` — `_apply_game_filters` filter pattern (time_control/platform/rated/opponent_type) confirmed
- Direct codebase inspection: `frontend/src/components/ui/info-popover.tsx` — Radix Popover usage pattern confirmed
- Direct codebase inspection: `frontend/src/components/board/ChessBoard.tsx` — `react-chessboard` import pattern confirmed
- Direct codebase inspection: `frontend/node_modules/radix-ui/dist/index.d.ts` — `Popover` export from `radix-ui` confirmed
- Verified: `func.count().filter()` SQLAlchemy 2.x syntax compiles to `COUNT(*) FILTER (WHERE ...)`
- Verified: `board.board_fen()` + `board.ply()` produce correct output for TSV PGN strings

### Secondary (MEDIUM confidence)
- `DISTINCT ON` PostgreSQL behavior: deterministic only with explicit `ORDER BY` matching DISTINCT columns (standard PostgreSQL docs behavior)
- Alembic autogenerate exclusion for views: using standalone `MetaData()` instance is the documented approach to exclude objects from autogenerate

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries already in project, verified imports
- Architecture: HIGH — patterns directly confirmed from codebase inspection
- Pitfalls: HIGH — multiple pitfalls verified by direct inspection (NULL columns, board_fen vs fen, alembic view issue)
- SQL-side WDL: HIGH — `func.count().filter()` syntax verified via SQLAlchemy 2.x compilation
- Frontend minimap: HIGH — react-chessboard and radix-ui Popover both confirmed available

**Research date:** 2026-03-28
**Valid until:** 2026-04-28 (stable dependencies, no fast-moving external APIs)
