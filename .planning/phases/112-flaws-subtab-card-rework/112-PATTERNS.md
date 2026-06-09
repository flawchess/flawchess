# Phase 112: Flaws Subtab Card Rework - Pattern Map

**Mapped:** 2026-06-09
**Files analyzed:** 13 (new/modified files)
**Analogs found:** 13 / 13

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `frontend/src/components/library/FlawCard.tsx` | component | request-response | `frontend/src/components/results/LibraryGameCard.tsx` | exact |
| `frontend/src/pages/library/FlawsTab.tsx` | component | request-response | self (modify — replace FlawRow + list with FlawCard + grid) | self |
| `frontend/src/hooks/useLibrary.ts` | hook | request-response | self (extend — add `useLibraryGame`) | self |
| `frontend/src/api/client.ts` | utility | request-response | self (extend — add `libraryApi.getGame`) | self |
| `frontend/src/lib/formatFlawEval.ts` (or inline in FlawCard) | utility | transform | `frontend/src/components/library/EvalChart.tsx` (formatEval, line 303) | role-match |
| `app/routers/library.py` | route | request-response | self (extend — `GET /flaws` route, lines 144-190) | self |
| `app/schemas/library.py` | model | CRUD | self (modify `FlawListItem`, lines 107-133) | self |
| `app/repositories/library_repository.py` | repository | CRUD | self (modify `query_flaws`, lines 192-295) | self |
| `app/services/library_service.py` | service | CRUD | self (extend — add `get_library_game`, analog: `get_library_games`) | self |
| `app/repositories/game_flaws_repository.py` | repository | CRUD | self (modify `flaw_record_to_row`, lines 100-115) | self |
| `app/models/game_flaw.py` | model | CRUD | self (modify — drop 3 columns, lines 59-61) | self |
| `alembic/versions/20260609_drop_game_flaws_display_cols.py` | migration | batch | `alembic/versions/20260607_alter_game_flaws_impact_cols.py` | exact |
| Tests (backend + frontend) | test | — | `tests/test_library_repository.py`, `FlawCard.test.tsx` (new) | role-match |

---

## Pattern Assignments

### `frontend/src/components/library/FlawCard.tsx` (component, request-response)

**Analog:** `frontend/src/components/results/LibraryGameCard.tsx`

**Imports pattern** (lines 1-24 of LibraryGameCard.tsx):
```tsx
import { useState } from 'react';
import { Chess } from 'chess.js';
import { BookOpen, Calendar, Clock, Equal, ExternalLink, Minus, Plus } from 'lucide-react';
import { cn } from '@/lib/utils';
import { SEV_BLUNDER, SEV_MISTAKE, SEV_INACCURACY } from '@/lib/theme';
import { Card, CardHeader } from '@/components/ui/card';
import { Tooltip } from '@/components/ui/tooltip';
import { PlatformIcon } from '@/components/icons/PlatformIcon';
import { LazyMiniBoard } from '@/components/board/LazyMiniBoard';
import { SeverityBadge } from '@/components/library/SeverityBadge';
import { TagChip, TagLegend } from '@/components/library/TagChip';
import { Dialog, DialogContent, DialogTitle } from '@/components/ui/dialog';
import { LoadError } from '@/components/ui/load-error';
import { LibraryGameCard } from '@/components/results/LibraryGameCard';
import { flawPlyUrl, supportsPlyDeepLink } from '@/lib/platformLinks';
import { sanToSquares } from '@/lib/sanToSquares';
import { formatSignedEvalPawns } from '@/lib/clockFormat';
import { useLibraryGame } from '@/hooks/useLibrary';
import type { FlawListItem } from '@/types/library';
```

**Board size constant** (line 34):
```tsx
const DESKTOP_BOARD_SIZE = 132;  // copy this exact constant
```

**CardHeader pattern** (lines 280-293) — exact template:
```tsx
const header = (
  <CardHeader as="h4" size="compact" className="rounded-t-md">
    <span className="hidden sm:block truncate text-foreground min-w-0">
      ■ {whiteName} {whiteRating}
      <span className="mx-1.5 text-muted-foreground font-normal">vs</span>□ {blackName}{' '}
      {blackRating}
    </span>
    <div className="flex sm:hidden min-w-0 flex-1 flex-col text-foreground">
      <span className="truncate">■ {whiteName} {whiteRating}</span>
      <span className="truncate">□ {blackName} {blackRating}</span>
    </div>
    {platformIconAndLink}
  </CardHeader>
);
```
For `FlawCard`: `platformIconAndLink` uses `flawPlyUrl` (exact-ply deep-link, D-12) instead of `gamePlatformUrl`.

**Platform link pattern** (lines 253-272) — adapt for flaw:
```tsx
// In LibraryGameCard: gamePlatformUrl(...) — in FlawCard: flawPlyUrl(...)
const flawUrl = flawPlyUrl(flaw.platform, flaw.platform_url, flaw.ply, flaw.user_color);
const platformIconAndLink = (
  <span className="ml-auto shrink-0 flex items-center gap-1.5 text-muted-foreground">
    <PlatformIcon platform={flaw.platform} className="h-4 w-4" />
    {flawUrl ? (
      <Tooltip content="Open at this move on platform">
        <a
          href={flawUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="text-brand-brown-light hover:text-brand-brown-highlight transition-colors"
          aria-label="Open at this move on platform"
          data-testid={`flaw-card-platform-link-${flaw.game_id}-${flaw.ply}`}
        >
          <ExternalLink className="h-4 w-4" />
        </a>
      </Tooltip>
    ) : null}
  </span>
);
```

**Result indicator pattern** (lines 73-83 + 236-248):
```tsx
const RESULT_ICONS: Record<UserResult, LucideIcon> = { win: Plus, draw: Equal, loss: Minus };
const BORDER_COLORS: Record<UserResult, string> = {
  win: WDL_BORDER_WIN,
  draw: WDL_BORDER_DRAW,
  loss: WDL_BORDER_LOSS,
};
// Usage:
const ResultIcon = RESULT_ICONS[flaw.user_result];
const resultIndicator = (
  <span className={cn('inline-flex items-center justify-center rounded border h-3.5 w-3.5 shrink-0', RESULT_CLASSES[flaw.user_result])} aria-label={flaw.user_result}>
    <ResultIcon className="h-2.5 w-2.5" strokeWidth={3} />
  </span>
);
```

**Metadata block pattern** (lines 305-350):
```tsx
// Desktop: wrap row (termination · date · TC)
const desktopMetadata = (
  <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-sm text-muted-foreground">
    {terminationItem}
    {dateItem}
    {timeControlItem}
  </div>
);
// Mobile: vertical stack
const mobileMetadata = (
  <div className="flex flex-col gap-1 text-sm text-muted-foreground">
    {dateItem}
    {timeControlItem}
    {terminationItem}
  </div>
);
```

**Helper functions to copy verbatim** (lines 98-131):
- `formatDate(dateStr: string | null): string` (lines 98-109)
- `formatTimeControl(tcStr: string): string` (lines 114-131)

**Card body layout pattern** — use `overflowVisible` and `accentColor` (the analog `LibraryGameCard` uses these via the `Card` component):
```tsx
<Card as="article" accentColor={severityColor} overflowVisible
      data-testid={`flaw-card-${flaw.game_id}-${flaw.ply}`}>
  {header}
  <div className="flex gap-3 items-start p-3">
    <LazyMiniBoard fen={flaw.fen} flipped={flipped} size={DESKTOP_BOARD_SIZE}
      arrows={moveSquares ? [{ from: moveSquares.from, to: moveSquares.to, color: SEV_BLUNDER }] : undefined} />
    <div className="flex flex-col gap-1.5 min-w-0 flex-1">
      {/* content stack */}
    </div>
  </div>
</Card>
```

**Move-arrow computation pattern** (FlawsTab.tsx lines 57-60):
```tsx
const sideToMove = flaw.user_color === 'black' ? 'b' : 'w';
const moveSquares = flaw.move_san
  ? sanToSquares(`${flaw.fen} ${sideToMove} - - 0 1`, flaw.move_san)
  : null;
```

---

### `frontend/src/components/library/FlawCard.tsx` — Eval swing formatter (inline or extracted)

**Analog:** `frontend/src/components/library/EvalChart.tsx` lines 303-315

**Source function** (EvalChart.tsx line 303):
```typescript
/** White-perspective eval string for a ply — mate takes priority over cp. */
function formatEval(point: EvalPoint | undefined): string {
  if (point?.eval_mate != null) {
    return `Eval: Mate in ${point.eval_mate}#`;
  }
  if (point?.eval_cp != null) {
    const cpValue = point.eval_cp / 100;
    const sign = cpValue >= 0 ? '+' : '';
    return `Eval: ${sign}${cpValue.toFixed(1)}`;
  }
  return 'Eval: —';
}
```

**Extracted form for FlawCard** (strip prefix, add user-POV negation, use `formatSignedEvalPawns` from `lib/clockFormat.ts` line 41):
```typescript
// formatSignedEvalPawns from clockFormat.ts line 41:
// export function formatSignedEvalPawns(value: number): string {
//   const sign = value >= 0 ? '+' : '';
//   return `${sign}${value.toFixed(1)}`;
// }

function formatFlawEvalPart(evalCp: number | null, evalMate: number | null): string {
  if (evalMate !== null) return `#${evalMate}`;         // e.g. "#3" or "#-3"
  if (evalCp !== null) return formatSignedEvalPawns(evalCp / 100);  // e.g. "+4.7"
  return '—';
}

function applyUserPov(evalCp: number | null, evalMate: number | null, userColor: string) {
  if (userColor !== 'black') return { evalCp, evalMate };
  return {
    evalCp: evalCp !== null ? -evalCp : null,
    evalMate: evalMate !== null ? -evalMate : null,
  };
}

// Usage in FlawCard:
const { evalCp: beforeCp, evalMate: beforeMate } = applyUserPov(
  flaw.eval_cp_before, flaw.eval_mate_before, flaw.user_color
);
const { evalCp: afterCp, evalMate: afterMate } = applyUserPov(
  flaw.eval_cp_after, flaw.eval_mate_after, flaw.user_color
);
const evalSwing = `${formatFlawEvalPart(beforeCp, beforeMate)} → ${formatFlawEvalPart(afterCp, afterMate)}`;
```

**EvalChart also has a `formatMoveLabel`** (line 296-301) that matches the inline formula needed for FlawCard:
```typescript
// EvalChart.tsx line 297-300 — same parity rule (even ply = white):
function formatMoveLabel(ply: number, san: string | null): string {
  if (!san) return `Ply ${ply}`;
  const moveNumber = Math.floor(ply / 2) + 1;
  return ply % 2 === 0 ? `${moveNumber}.${san}` : `${moveNumber}...${san}`;
}
// Copy this exactly as formatFlawMove in FlawCard.tsx
```

---

### `frontend/src/pages/library/FlawsTab.tsx` (component, modify)

**Current list block to replace** (lines 414-419):
```tsx
{matchedCount > 0 && (
  <div className="flex flex-col gap-3">
    {flaws.map((flaw) => (
      <FlawRow key={`${flaw.game_id}-${flaw.ply}`} flaw={flaw} />
    ))}
  </div>
)}
```

**Replacement pattern** (D-01 grid):
```tsx
{matchedCount > 0 && (
  <div className="grid grid-cols-1 lg:grid-cols-2 gap-4" data-testid="flaw-grid">
    {flaws.map((flaw) => (
      <FlawCard key={`${flaw.game_id}-${flaw.ply}`} flaw={flaw} />
    ))}
  </div>
)}
```

Remove the `FlawRow` function (lines 48-141) entirely. Remove the `MINI_BOARD_SIZE = 80` constant (line 41). Import `FlawCard` instead of the inline components (`LazyMiniBoard`, `SeverityBadge`, `TagChip`) that move into `FlawCard.tsx`.

---

### `frontend/src/hooks/useLibrary.ts` (hook, extend)

**Analog:** `useLibraryFlaws` (lines 89-102) — exact template:
```typescript
export function useLibraryFlaws(
  filters: FilterState,
  flawFilter: FlawFilterState,
  offset: number,
  limit: number,
) {
  const params = buildLibraryParams(filters, flawFilter.severity, flawFilter.tags);
  return useQuery({
    queryKey: ['library-flaws', params, offset, limit],
    queryFn: () => libraryApi.getFlaws({ ...params, offset, limit }),
    staleTime: LIBRARY_STALE_TIME,
    refetchOnWindowFocus: false,
  });
}
```

**New hook to add**:
```typescript
export function useLibraryGame(gameId: number | null) {
  return useQuery({
    queryKey: ['library-game', gameId],
    queryFn: () => libraryApi.getGame(gameId!),
    enabled: gameId !== null,
    staleTime: LIBRARY_STALE_TIME,
    refetchOnWindowFocus: false,
  });
}
```

---

### `frontend/src/api/client.ts` (utility, extend)

**Analog:** `libraryApi.getFlaws` (lines 267-end of libraryApi block):
```typescript
getFlaws: (params: {
  time_control?: string[] | null;
  // ... filter params ...
  severity?: ('blunder' | 'mistake')[];
  tag?: string[];
  offset?: number;
  limit?: number;
}) =>
  apiClient.get<LibraryFlawsResponse>('/library/flaws', {
    params: { ...buildFilterParams(params), ..., offset, limit },
  }).then(r => r.data),
```

**New method to add to `libraryApi`**:
```typescript
getGame: (gameId: number) =>
  apiClient.get<GameFlawCard>(`/library/games/${gameId}`).then(r => r.data),
```
Also add `GameFlawCard` to the import from `@/types/library`.

---

### `app/routers/library.py` (route, extend)

**Analog:** `get_library_flaws` route (lines 144-190) — exact structural pattern:
```python
@router.get("/flaws", response_model=LibraryFlawsResponse)
async def get_library_flaws(
    session: Annotated[AsyncSession, Depends(get_async_session)],
    user: Annotated[User, Depends(current_active_user)],
    # ... Query params ...
) -> LibraryFlawsResponse:
    """..."""
    if from_date is not None and to_date is not None and from_date > to_date:
        raise HTTPException(status_code=422, detail="from_date must be <= to_date")
    return await library_service.get_library_flaws(session, user_id=user.id, ...)
```

**New route to add**:
```python
@router.get("/games/{game_id}", response_model=GameFlawCard)
async def get_library_game(
    game_id: int,
    session: Annotated[AsyncSession, Depends(get_async_session)],
    user: Annotated[User, Depends(current_active_user)],
) -> GameFlawCard:
    """Return a single GameFlawCard by game_id (Phase 112, D-10).

    Used by the FlawCard modal ("View game") to load the full analyzed game
    card. User-scoped — game_id validated against user.id in the service layer
    (IDOR: returns 404 if game does not belong to this user, per T-108-10).
    """
    card = await library_service.get_library_game(session, user_id=user.id, game_id=game_id)
    if card is None:
        raise HTTPException(status_code=404, detail="Game not found")
    return card
```

Also add `GameFlawCard` to the import from `app.schemas.library`.

---

### `app/schemas/library.py` (model, modify)

**Current `FlawListItem`** (lines 107-133):
- Remove: `move_san: str | None` (line 119), `es_before: float` (line 122), `es_after: float` (line 123)
- Add after `fen: str`:
```python
move_san: str | None  # from game_positions join (Phase 112, D-08)
eval_cp_before: int | None  # game_positions at ply-1, white-POV
eval_mate_before: int | None
eval_cp_after: int | None   # game_positions at ply, white-POV
eval_mate_after: int | None
white_rating: int | None    # from games join (D-03)
black_rating: int | None
```

**Pattern for optional nullable fields** (follow existing `GameFlawCard` style, lines 79-104):
```python
white_rating: int | None
black_rating: int | None
```

---

### `app/repositories/library_repository.py` (repository, modify)

**Current `query_flaws` join base** (lines 232-240):
```python
base_stmt = (
    select(GameFlaw, Game)
    .join(Game, Game.id == GameFlaw.game_id)
    .where(
        GameFlaw.user_id == user_id,
        *flaw_clauses,
    )
)
```

**New base with two `game_positions` aliases** (RESEARCH.md Pattern 6 + SQLAlchemy 2.x `aliased` pattern):
```python
from sqlalchemy.orm import aliased

PositionAt = aliased(GamePosition)     # ply = N: move_san + eval_after
PositionBefore = aliased(GamePosition) # ply = N-1: eval_before

base_stmt = (
    select(GameFlaw, Game, PositionAt, PositionBefore)
    .join(Game, Game.id == GameFlaw.game_id)
    .outerjoin(
        PositionAt,
        (PositionAt.game_id == GameFlaw.game_id)
        & (PositionAt.user_id == GameFlaw.user_id)
        & (PositionAt.ply == GameFlaw.ply),
    )
    .outerjoin(
        PositionBefore,
        (PositionBefore.game_id == GameFlaw.game_id)
        & (PositionBefore.user_id == GameFlaw.user_id)
        & (PositionBefore.ply == GameFlaw.ply - 1),
    )
    .where(
        GameFlaw.user_id == user_id,
        *flaw_clauses,
    )
)
```

**Current `FlawListItem` constructor block** (lines 274-294):
```python
items: list[FlawListItem] = [
    FlawListItem(
        game_id=flaw.game_id,
        ply=flaw.ply,
        fen=flaw.fen,
        move_san=flaw.move_san,          # REMOVE — now from pos_at
        severity=_SEVERITY_INT_TO_TAG[flaw.severity],
        tags=_reconstruct_tags(flaw),
        es_before=flaw.es_before,        # REMOVE
        es_after=flaw.es_after,          # REMOVE
        user_result=derive_user_result(game.result, game.user_color),
        played_at=game.played_at,
        time_control_bucket=game.time_control_bucket,
        platform=game.platform,
        platform_url=game.platform_url,
        white_username=game.white_username,
        black_username=game.black_username,
        user_color=game.user_color,
    )
    for flaw, game in rows
]
```

**Replacement constructor** (iterate `(flaw, game, pos_at, pos_before)` instead):
```python
items: list[FlawListItem] = [
    FlawListItem(
        game_id=flaw.game_id,
        ply=flaw.ply,
        fen=flaw.fen,
        move_san=pos_at.move_san if pos_at else None,
        severity=_SEVERITY_INT_TO_TAG[flaw.severity],
        tags=_reconstruct_tags(flaw),
        eval_cp_before=pos_before.eval_cp if pos_before else None,
        eval_mate_before=pos_before.eval_mate if pos_before else None,
        eval_cp_after=pos_at.eval_cp if pos_at else None,
        eval_mate_after=pos_at.eval_mate if pos_at else None,
        white_rating=game.white_rating,
        black_rating=game.black_rating,
        user_result=derive_user_result(game.result, game.user_color),
        played_at=game.played_at,
        time_control_bucket=game.time_control_bucket,
        platform=game.platform,
        platform_url=game.platform_url,
        white_username=game.white_username,
        black_username=game.black_username,
        user_color=game.user_color,
    )
    for flaw, game, pos_at, pos_before in rows
]
```

---

### `app/services/library_service.py` (service, extend)

**Analog:** `_build_card` function (lines 294-390) — the card builder to reuse verbatim for the single-game endpoint. Also `get_library_games` (lines 393+) as structural analog for `get_library_game`.

**`_build_card` signature** (line 294):
```python
def _build_card(
    game: Game,
    flaw_rows: list[GameFlaw],
    is_analyzed: bool,
    positions: list[GamePosition],
) -> GameFlawCard:
```

**New service function**:
```python
async def get_library_game(
    session: AsyncSession,
    user_id: int,
    game_id: int,
) -> GameFlawCard | None:
    """Fetch a single game's full GameFlawCard for the "View game" modal (D-10, Phase 112).

    Reuses _build_card with the same three batch queries as get_library_games,
    scoped to one game_id. Returns None (-> 404) if game_id does not belong to
    user_id (IDOR guard — T-108-10).

    Sequential queries — no asyncio.gather on one session (CLAUDE.md).
    """
    game = await session.get(Game, game_id)
    if game is None or game.user_id != user_id:
        return None
    is_analyzed = game_id in await library_repository.fetch_page_analyzed_set(
        session, user_id, [game_id]
    )
    flaw_rows = (await library_repository.fetch_page_game_flaws(session, user_id, [game_id])).get(game_id, [])
    positions: list[GamePosition] = []
    if is_analyzed:
        positions = (await library_repository.fetch_page_eval_positions(session, user_id, [game_id])).get(game_id, [])
    return _build_card(game, flaw_rows, is_analyzed, positions)
```

---

### `app/repositories/game_flaws_repository.py` (repository, modify)

**Current write path** (lines 111-113):
```python
"es_before": flaw["es_before"],
"es_after": flaw["es_after"],
"move_san": flaw["move_san"],
```

**Action:** remove these 3 lines. The `FlawRecord` TypedDict in `flaws_service.py` retains `es_before`/`es_after`/`move_san` (they are internal classifier fields). Only stop persisting them to the DB.

---

### `app/models/game_flaw.py` (model, modify)

**Current columns to drop** (lines 59-61):
```python
es_before: Mapped[float] = mapped_column(Float, nullable=False)
es_after: Mapped[float] = mapped_column(Float, nullable=False)
move_san: Mapped[Optional[str]] = mapped_column(String, nullable=True)
```

**Keep** (line 62-65):
```python
fen: Mapped[str] = mapped_column(String, nullable=False)  # board_fen() BEFORE the flawed move
```

Also remove `Float` from the SQLAlchemy imports (line 11) if it becomes unused after removing the two Float columns. Update the module docstring to reflect the schema change.

---

### `alembic/versions/20260609_drop_game_flaws_display_cols.py` (migration)

**Analog:** `alembic/versions/20260607_alter_game_flaws_impact_cols.py` — exact structural pattern:
```python
# revision identifiers
revision: str = "..."
down_revision: str = "20260608_rename_lucky_escape_to_lucky"  # most recent migration
branch_labels: str | None = None
depends_on: str | None = None
```

**Pattern** (drop-only, no backfill, no server_default gymnastics — dev-only):
```python
import sqlalchemy as sa
from alembic import op

def upgrade() -> None:
    op.drop_column("game_flaws", "es_before")
    op.drop_column("game_flaws", "es_after")
    op.drop_column("game_flaws", "move_san")

def downgrade() -> None:
    # Re-add as nullable so existing rows don't break on rollback.
    op.add_column("game_flaws", sa.Column("move_san", sa.String(), nullable=True))
    op.add_column("game_flaws", sa.Column("es_after", sa.Float(), nullable=True))
    op.add_column("game_flaws", sa.Column("es_before", sa.Float(), nullable=True))
```

Rule: literal column types only — no import of live app constants (per `20260607` migration comment).

---

## Shared Patterns

### Authentication / User Scoping
**Source:** `app/routers/library.py` lines 52-54
**Apply to:** new `GET /games/{game_id}` route
```python
session: Annotated[AsyncSession, Depends(get_async_session)],
user: Annotated[User, Depends(current_active_user)],
```
IDOR guard: always `game.user_id == user.id` check in service, return `None` (→ 404) not 403.

### No `asyncio.gather` on single session
**Source:** CLAUDE.md critical constraint
**Apply to:** `get_library_game` service function
Three batch queries run sequentially: `fetch_page_analyzed_set`, then `fetch_page_game_flaws`, then `fetch_page_eval_positions`.

### Error handling — `isError` mandatory branch
**Source:** CLAUDE.md frontend rules
**Apply to:** Dialog modal body in `FlawCard`
```tsx
{isLoading && <div className="flex justify-center p-8"><Spinner /></div>}
{isError && <LoadError resource="game" variant="centered" />}
{data && <LibraryGameCard game={data} />}
```
Never let `isError` fall through to empty state.

### Theme constants — never hard-code semantic colors
**Source:** `frontend/src/lib/theme.ts`, enforced by CLAUDE.md
**Apply to:** `FlawCard` severity accent color, tag chip colors, result indicator colors
```typescript
import { SEV_BLUNDER, SEV_MISTAKE, SEV_INACCURACY, WDL_BORDER_WIN, WDL_BORDER_LOSS, WDL_BORDER_DRAW } from '@/lib/theme';
```

### `data-testid` + semantic HTML
**Source:** CLAUDE.md browser-automation rules
**Apply to:** all new interactive elements in `FlawCard`
| Element | `data-testid` |
|---------|--------------|
| Card root | `flaw-card-{game_id}-{ply}` |
| Grid container | `flaw-grid` |
| Platform link | `flaw-card-platform-link-{game_id}-{ply}` |
| "View game" button | `flaw-card-view-game-{game_id}-{ply}` |
| Modal DialogContent | `flaw-game-modal` |

### TanStack Query `staleTime` + `refetchOnWindowFocus`
**Source:** `useLibrary.ts` lines 10-11 + all `useQuery` calls
**Apply to:** `useLibraryGame` hook
```typescript
const LIBRARY_STALE_TIME = 5 * 60 * 1000;
// all library hooks use: staleTime: LIBRARY_STALE_TIME, refetchOnWindowFocus: false
```

### `text-sm` floor + `text-xs` exception
**Source:** CLAUDE.md frontend rules
**Apply to:** all text in `FlawCard`
`text-sm` minimum everywhere. `text-xs` only for TagChip definition popover bodies and TagLegend popover body (hover/tap-activated, Radix popover surfaces).

---

## No Analog Found

No files in this phase lack a codebase analog. All patterns are well-established in the project.

---

## Metadata

**Analog search scope:** `frontend/src/components/`, `frontend/src/hooks/`, `frontend/src/api/`, `app/routers/`, `app/schemas/`, `app/repositories/`, `app/services/`, `app/models/`, `alembic/versions/`
**Files scanned:** 13 primary analog files read
**Pattern extraction date:** 2026-06-09
