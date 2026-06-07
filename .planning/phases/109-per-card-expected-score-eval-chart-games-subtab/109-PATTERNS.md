# Phase 109: Per-Card Expected-Score Eval Chart (Games subtab) - Pattern Map

**Mapped:** 2026-06-07
**Files analyzed:** 9 new/modified files
**Analogs found:** 9 / 9

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `app/schemas/library.py` | model | request-response | `app/schemas/library.py` (self — extend in place) | exact |
| `app/repositories/library_repository.py` | repository | CRUD | `fetch_page_game_flaws` in same file (lines 298-322) | exact |
| `app/services/library_service.py` | service | transform | `_build_card` in same file (lines 94-159) | exact |
| `app/routers/library.py` | router | request-response | same file — no route change | exact |
| `frontend/src/types/library.ts` | model | — | same file — extend `GameFlawCard` (lines 51-74) | exact |
| `frontend/src/lib/theme.ts` | config | — | same file — existing `SEV_*` constants (lines 27-29) | exact |
| `frontend/src/components/library/EvalChart.tsx` (NEW) | component | event-driven | `FlawTrendChart.tsx` + `EndgameClockDiffOverTimeChart.tsx` | role-match |
| `frontend/src/components/results/LibraryGameCard.tsx` | component | request-response | same file — existing desktop/mobile layout (lines 265-307) | exact |
| `tests/services/test_eval_chart_service.py` (NEW) | test | — | `tests/services/test_flaws_service.py` | exact |

---

## Pattern Assignments

### `app/schemas/library.py` — extend `GameFlawCard`, add three new Pydantic models

**Analog:** same file, `GameFlawCard` class (lines 26-55) and `FlawListItem` (lines 58-84).

**Imports pattern** (lines 1-24): no new imports needed — `FlawSeverity` and `FlawTag` are already imported from `app.services.flaws_service`.

**Existing `GameFlawCard` tail to extend** (lines 50-55):
```python
    severity_counts: SeverityCounts | None
    chips: list[FlawTag]
    analysis_state: Literal["analyzed", "no_engine_analysis"]
    # Phase 109 additions — null for unanalyzed games:
    eval_series: list[EvalPoint] | None = None
    flaw_markers: list[FlawMarker] | None = None
    phase_transitions: PhaseTransitions | None = None
```

**New Pydantic models to add** (after existing `FlawListItem`, before `LibraryFlawsResponse`):
```python
class EvalPoint(BaseModel):
    """One ply's white-perspective ES datapoint for the eval chart line."""
    ply: int
    es: float | None        # white-perspective ES in (0,1); null = missing eval
    eval_cp: int | None     # raw cp for tooltip display
    eval_mate: int | None   # signed, white-perspective (positive = White has mate)


class FlawMarker(BaseModel):
    """One flaw dot for the eval chart (both colors, B/M/I)."""
    ply: int
    severity: FlawSeverity
    tags: list[FlawTag]  # empty for inaccuracies (D-03)
    is_user: bool        # True = filled dot (player), False = hollow dot (opponent)


class PhaseTransitions(BaseModel):
    """First ply of middlegame and endgame phases (D-06)."""
    middlegame_ply: int | None  # None = middlegame never reached
    endgame_ply: int | None     # None = endgame never reached
```

**Docstring style:** follow the block-comment pattern at lines 1-16 — module docstring explains the phase that introduced each addition.

---

### `app/repositories/library_repository.py` — add `fetch_page_eval_positions`

**Analog:** `fetch_page_game_flaws` (lines 298-322) — identical pattern: batch IN query, group in Python, return `dict[int, list[...]]`.

**Exact analog to copy structure from** (lines 298-322):
```python
async def fetch_page_game_flaws(
    session: AsyncSession,
    user_id: int,
    game_ids: Sequence[int],
) -> dict[int, list[GameFlaw]]:
    """Batch-load all game_flaws rows for a page of games, grouped by game_id."""
    if not game_ids:
        return {}
    stmt = select(GameFlaw).where(
        GameFlaw.user_id == user_id,
        GameFlaw.game_id.in_(game_ids),
    )
    rows = list((await session.execute(stmt)).scalars().all())
    result: dict[int, list[GameFlaw]] = {gid: [] for gid in game_ids}
    for row in rows:
        result[row.game_id].append(row)
    return result
```

**New function — same pattern, `GamePosition` instead of `GameFlaw`:**
```python
async def fetch_page_eval_positions(
    session: AsyncSession,
    user_id: int,
    analyzed_game_ids: Sequence[int],
) -> dict[int, list[GamePosition]]:
    """Batch-load GamePosition rows for analyzed games on a page, grouped by game_id.

    Only called for games in analyzed_set (unanalyzed games get no positions).
    Selects full ORM objects so _run_all_moves_pass and _build_tags can consume
    them unchanged. Ordered by game_id, ply ASC for sequential grouping.
    User-scoped via GamePosition.user_id (IDOR mitigation — same pattern as
    fetch_page_game_flaws / T-108-08).
    """
    if not analyzed_game_ids:
        return {}
    stmt = (
        select(GamePosition)
        .where(
            GamePosition.user_id == user_id,
            GamePosition.game_id.in_(analyzed_game_ids),
        )
        .order_by(GamePosition.game_id, GamePosition.ply)
    )
    rows = list((await session.execute(stmt)).scalars().all())
    result: dict[int, list[GamePosition]] = {gid: [] for gid in analyzed_game_ids}
    for row in rows:
        result[row.game_id].append(row)
    return result
```

**Imports:** `GamePosition` is already imported at line 26; `Sequence` at line 17.

---

### `app/services/library_service.py` — add `_build_eval_series`, `_build_opponent_tags`, extend `_build_card`

**Analog:** `_build_card` (lines 94-159) — the pattern for a private builder that receives pre-fetched data, does no DB access, returns a schema object.

**Import additions** (follow lines 29-52 import block style):
```python
from app.models.game_position import GamePosition
from app.schemas.library import EvalPoint, FlawMarker, PhaseTransitions
from app.services.eval_utils import (
    eval_cp_to_expected_score,
    eval_mate_to_expected_score,
)
from app.services.flaws_service import (
    # already imported: FlawSeverity, FlawTag, SeverityCounts
    _MoveEntry,
    _build_tags,
    _run_all_moves_pass,
)
```

**`_build_card` signature extension** (lines 94-98 → extend parameter list):
```python
def _build_card(
    game: Game,
    flaw_rows: list[GameFlaw],
    is_analyzed: bool,
    positions: list[GamePosition],   # NEW — empty list for unanalyzed games
) -> GameFlawCard:
```

**Inside `_build_card` — add eval series branch** (after `analysis_state = "analyzed"` at line 136):
```python
        eval_series, flaw_markers, phase_transitions = (
            _build_eval_series(game, positions) if positions else (None, None, None)
        )
```

**`_build_eval_series` helper** (new private function, co-located with `_build_card`):
```python
_USER_FRAMED_TAGS: frozenset[FlawTag] = frozenset({"miss", "lucky-escape"})


def _build_eval_series(
    game: Game,
    positions: list[GamePosition],
) -> tuple[list[EvalPoint], list[FlawMarker], PhaseTransitions]:
    """Compute white-perspective ES line, flaw markers, and phase transitions.

    Line perspective: white-perspective (eval_cp_to_expected_score(..., "white")).
    Detection perspective: mover-POV drops via _run_all_moves_pass (D-01/D-04).
    No DB access — positions are pre-fetched by get_library_games.
    """
    all_moves = _run_all_moves_pass(positions)
    eval_series: list[EvalPoint] = []
    flaw_markers: list[FlawMarker] = []
    middlegame_ply: int | None = None
    endgame_ply: int | None = None

    # Increment for _build_tags tempo computation — mirror flaws_service pattern.
    increment = game.increment_seconds or 0.0

    for pos in positions:
        # White-perspective ES for the chart line (D-04).
        if pos.eval_mate is not None:
            es: float | None = eval_mate_to_expected_score(pos.eval_mate, "white")
        elif pos.eval_cp is not None:
            es = eval_cp_to_expected_score(pos.eval_cp, "white")
        else:
            es = None
        eval_series.append(
            EvalPoint(ply=pos.ply, es=round(es, 3) if es is not None else None,
                      eval_cp=pos.eval_cp, eval_mate=pos.eval_mate)
        )

        # Phase transitions — first ply where phase==1 or phase==2 (D-06).
        if pos.phase == 1 and middlegame_ply is None:
            middlegame_ply = pos.ply
        elif pos.phase == 2 and endgame_ply is None:
            endgame_ply = pos.ply

        # Flaw markers from the mover-POV kernel dict (both colors, D-01/D-02).
        entry = all_moves.get(pos.ply)
        if entry is None:
            continue
        mover_color, severity, es_before, es_after = entry
        if severity is None:
            continue
        is_user = mover_color == game.user_color
        tags: list[FlawTag]
        if severity in ("mistake", "blunder"):
            if is_user:
                tags = _build_tags(
                    pos.ply, severity, es_before, es_after,
                    positions, all_moves,
                    derive_user_result(game.result, game.user_color),
                    increment, game.base_time_seconds,
                )
            else:
                tags = _build_opponent_tags(
                    pos.ply, severity, es_before, es_after,
                    positions, all_moves, game, increment,
                )
        else:
            tags = []  # inaccuracy — no tags (D-03)
        flaw_markers.append(FlawMarker(
            ply=pos.ply, severity=severity, tags=tags, is_user=is_user,
        ))

    return (
        eval_series,
        flaw_markers,
        PhaseTransitions(middlegame_ply=middlegame_ply, endgame_ply=endgame_ply),
    )


def _build_opponent_tags(
    n: int,
    severity: FlawSeverity,
    es_before: float,
    es_after: float,
    positions: list[GamePosition],
    all_moves: dict[int, _MoveEntry],
    game: Game,
    increment: float,
) -> list[FlawTag]:
    """Tags for an opponent flaw dot — mover-framed only (D-03 resolution).

    Flips user_result to opponent's perspective so while-ahead / result-changing
    are mover-relative. Strips 'miss' and 'lucky-escape' which are user-framed
    and meaningless/misleading from the opponent's perspective.
    """
    opponent_color: Literal["white", "black"] = (
        "black" if game.user_color == "white" else "white"
    )
    opponent_result = derive_user_result(game.result, opponent_color)
    raw_tags = _build_tags(
        n, severity, es_before, es_after,
        positions, all_moves, opponent_result, increment, game.base_time_seconds,
    )
    return [t for t in raw_tags if t not in _USER_FRAMED_TAGS]
```

**`get_library_games` pipeline injection** (lines 217-234 — add step between `analyzed_set` fetch and card construction):
```python
        # D-02/D-10: batch-load positions for analyzed games only (no N+1).
        analyzed_game_ids = [gid for gid in page_game_ids if gid in analyzed_set]
        page_positions = await library_repository.fetch_page_eval_positions(
            session, user_id, analyzed_game_ids
        )

        cards = [
            _build_card(
                game,
                page_flaws.get(game.id, []),
                game.id in analyzed_set,
                page_positions.get(game.id, []),  # NEW
            )
            for game in games
        ]
```

**Error handling pattern** (lines 235-238 — unchanged; the Sentry capture at `get_library_games` top level covers the new code):
```python
    except Exception as exc:  # noqa: BLE001
        sentry_sdk.set_context("library_games", {"user_id": user_id})
        sentry_sdk.capture_exception(exc)
        raise
```

---

### `app/routers/library.py` — no route change

**Analog:** `GET /games` at lines 50-60. No change to the route signature. The `response_model=LibraryGamesResponse` propagates new `GameFlawCard` fields automatically via Pydantic.

**Router declaration** (line 26 — copy style for reference):
```python
router = APIRouter(prefix="/library", tags=["library"])
```

**Route signature** (lines 50-60 — unchanged):
```python
@router.get("/games", response_model=LibraryGamesResponse)
async def get_library_games(
    session: Annotated[AsyncSession, Depends(get_async_session)],
    user: Annotated[User, Depends(current_active_user)],
    ...
```

---

### `frontend/src/types/library.ts` — extend `GameFlawCard`, add three interfaces

**Analog:** existing `GameFlawCard` interface (lines 51-74) — follow the Literal union typing convention and JSDoc comment style.

**Extend `GameFlawCard` tail** (after line 73, `analysis_state: AnalysisState;`):
```typescript
  // Phase 109 additions — null for unanalyzed games (analysis_state === 'no_engine_analysis'):
  eval_series: EvalPoint[] | null;
  flaw_markers: FlawMarker[] | null;
  phase_transitions: PhaseTransitions | null;
```

**New interfaces to add** (after `GameFlawCard`, before `LibraryGamesResponse`):
```typescript
/** One ply's white-perspective ES datapoint (mirrors backend EvalPoint). */
export interface EvalPoint {
  ply: number;
  es: number | null;       // white-perspective ES in (0,1); null = missing eval
  eval_cp: number | null;  // raw cp for tooltip
  eval_mate: number | null; // signed, white-perspective
}

/**
 * One flaw dot for the eval chart (both colors, B/M/I).
 * is_user=true → filled circle (player); is_user=false → hollow circle (opponent).
 */
export interface FlawMarker {
  ply: number;
  severity: FlawSeverity;
  tags: FlawTag[];    // empty for inaccuracies
  is_user: boolean;
}

/** First ply of middlegame and endgame phases (at most two phase lines). */
export interface PhaseTransitions {
  middlegame_ply: number | null;
  endgame_ply: number | null;
}
```

---

### `frontend/src/lib/theme.ts` — add five `EVAL_CHART_*` constants

**Analog:** `SEV_BLUNDER` / `SEV_MISTAKE` / `SEV_INACCURACY` block (lines 27-29) — same oklch color format, same `export const` style.

**Add after the existing `SEV_*` block** (after line 29):
```typescript
// Eval chart area fill and line colors (Phase 109 — EvalChart.tsx).
// White-ahead region (top half of chart), black-ahead region (bottom half).
export const EVAL_CHART_AREA_WHITE_AHEAD = 'oklch(0.70 0 0 / 0.35)';
export const EVAL_CHART_AREA_BLACK_AHEAD = 'oklch(0.28 0 0 / 0.45)';
export const EVAL_CHART_LINE = 'oklch(0.82 0 0)';
export const EVAL_CHART_MIDLINE = 'oklch(0.55 0 0)';
export const EVAL_CHART_PHASE_LINE = 'oklch(0.55 0 0 / 0.60)';
```

---

### `frontend/src/components/library/EvalChart.tsx` (NEW)

**Analogs:**
1. `FlawTrendChart.tsx` — recharts-in-card pattern: `useId` for gradient ID, `ChartContainer config={{}}`, `isAnimationActive={false}`, `ChartTooltip` with custom content render prop, `linearGradient` in `<defs>`, no `CartesianGrid`.
2. `EndgameClockDiffOverTimeChart.tsx` (lines 290-320) — custom `dot` render prop on `<Line>`, `connectNulls={false}`, `ComposedChart`.

**Imports pattern** (copy from FlawTrendChart.tsx lines 1-5, extended):
```tsx
import { useId } from 'react';
import { Area, ComposedChart, Line, ReferenceLine, XAxis, YAxis } from 'recharts';
import { ChartContainer, ChartTooltip } from '@/components/ui/chart';
import {
  EVAL_CHART_AREA_BLACK_AHEAD,
  EVAL_CHART_AREA_WHITE_AHEAD,
  EVAL_CHART_LINE,
  EVAL_CHART_MIDLINE,
  EVAL_CHART_PHASE_LINE,
  SEV_BLUNDER,
  SEV_INACCURACY,
  SEV_MISTAKE,
} from '@/lib/theme';
import type { EvalPoint, FlawMarker, FlawSeverity, PhaseTransitions } from '@/types/library';
```

**Props interface** (follow `FlawTrendChartProps` shape from FlawTrendChart.tsx lines 9-13):
```tsx
interface EvalChartProps {
  evalSeries: EvalPoint[];
  flawMarkers: FlawMarker[];
  phaseTransitions: PhaseTransitions;
  userColor: 'white' | 'black';
  /** 'h-24' (desktop default) or 'h-20' (mobile). */
  heightClass?: string;
}
```

**Gradient ID pattern** (FlawTrendChart.tsx lines 31-33 — copy verbatim, change prefix):
```tsx
const rawId = useId();
const gradientId = `eval-gradient-${rawId.replace(/[^a-zA-Z0-9]/g, '_')}`;
```

**Two-region gradient** (hardcoded 50% hard stop — no analog exists, but follows `<defs>` pattern from FlawTrendChart.tsx lines 64-68):
```tsx
<defs>
  <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
    <stop offset="0%"   stopColor={EVAL_CHART_AREA_WHITE_AHEAD} />
    <stop offset="50%"  stopColor={EVAL_CHART_AREA_WHITE_AHEAD} />
    <stop offset="50%"  stopColor={EVAL_CHART_AREA_BLACK_AHEAD} />
    <stop offset="100%" stopColor={EVAL_CHART_AREA_BLACK_AHEAD} />
  </linearGradient>
</defs>
```

**Custom dot render prop** (EndgameClockDiffOverTimeChart.tsx lines 300-319 — copy structure, add hollow/filled logic):
```tsx
const severityColor = (sev: FlawSeverity): string => {
  if (sev === 'blunder') return SEV_BLUNDER;
  if (sev === 'mistake') return SEV_MISTAKE;
  return SEV_INACCURACY;
};

// Build a ply-keyed lookup for O(1) access inside the dot render prop.
const markerMap = new Map(flawMarkers.map((m) => [m.ply, m]));

const customDotRenderer = (props: {
  cx?: number;
  cy?: number;
  payload?: EvalPoint;
}) => {
  const { cx, cy, payload } = props;
  if (!payload || !Number.isFinite(cx) || !Number.isFinite(cy)) {
    // Return empty <g> not null — avoids React key warning (Pitfall 7).
    return <g key={`nodot-${String(payload?.ply ?? cx)}`} />;
  }
  const marker = markerMap.get(payload.ply);
  if (!marker || payload.es == null) return <g key={`nodot-${payload.ply}`} />;
  const color = severityColor(marker.severity);
  const r = marker.severity === 'inaccuracy' ? 2 : 2.5;
  if (marker.is_user) {
    return <circle key={`dot-${payload.ply}`} cx={cx} cy={cy} r={r} fill={color} />;
  }
  // Hollow circle for opponent — fill="none" lets area shading show through (Pitfall 6).
  return (
    <circle
      key={`dot-${payload.ply}`} cx={cx} cy={cy} r={r}
      fill="none" stroke={color} strokeWidth={1.5}
    />
  );
};
```

**ComposedChart structure** (EndgameScoreOverTimeChart.tsx lines 276-310 as template; FlawTrendChart.tsx lines 58-105 for ChartContainer/margin):
```tsx
<ChartContainer config={{}} className={`w-full ${heightClass ?? 'h-24'}`}>
  <ComposedChart data={evalSeries} margin={{ top: 4, right: 4, left: 4, bottom: 4 }}>
    <defs>...</defs>
    <XAxis dataKey="ply" hide />
    <YAxis hide domain={[0, 1]} />
    {/* Area fill — two-region gradient */}
    <Area
      type="monotone" dataKey="es"
      stroke={EVAL_CHART_LINE} strokeWidth={1.5}
      fill={`url(#${gradientId})`}
      dot={false} activeDot={false}
      connectNulls={false}
      isAnimationActive={false}
    />
    {/* 50% midline */}
    <ReferenceLine y={0.5} stroke={EVAL_CHART_MIDLINE} strokeWidth={1} strokeDasharray="3 3" />
    {/* Phase transitions — at most two lines (D-06) */}
    {phaseTransitions.middlegame_ply != null && (
      <ReferenceLine x={phaseTransitions.middlegame_ply} stroke={EVAL_CHART_PHASE_LINE} strokeWidth={1} />
    )}
    {phaseTransitions.endgame_ply != null && (
      <ReferenceLine x={phaseTransitions.endgame_ply} stroke={EVAL_CHART_PHASE_LINE} strokeWidth={1} />
    )}
    {/* Invisible line overlay — renders flaw dots via custom dot prop */}
    <Line
      type="monotone" dataKey="es"
      stroke="none" dot={customDotRenderer} activeDot={false}
      connectNulls={false} isAnimationActive={false}
    />
    <ChartTooltip content={({ active, payload }) => {
      if (!active || !payload?.length) return null;
      const point = payload[0]?.payload as EvalPoint | undefined;
      if (!point) return null;
      const marker = point.ply != null ? markerMap.get(point.ply) : undefined;
      const evalStr = point.eval_mate != null
        ? `M${point.eval_mate > 0 ? '+' : ''}${point.eval_mate}`
        : point.eval_cp != null ? `${(point.eval_cp / 100).toFixed(2)}` : '—';
      return (
        <div className="rounded-lg border border-border/50 bg-background px-3 py-2 text-sm shadow-xl space-y-1">
          <div className="text-muted-foreground">Ply {point.ply} · {evalStr}</div>
          {marker && (
            <div style={{ color: severityColor(marker.severity) }}>
              {marker.is_user ? 'You' : 'Opponent'} · {marker.severity.charAt(0).toUpperCase() + marker.severity.slice(1)}
              {marker.tags.length > 0 && (
                <span className="text-muted-foreground"> · {marker.tags.join(', ')}</span>
              )}
            </div>
          )}
        </div>
      );
    }} />
  </ComposedChart>
</ChartContainer>
```

**ARIA / data-testid** (follow FlawTrendChart.tsx lines 37-40):
```tsx
<div
  data-testid={`eval-chart-${gameId}`}
  aria-label="Expected score chart for this game"
>
```

---

### `frontend/src/components/results/LibraryGameCard.tsx` — three-thirds grid restructure

**Analog:** same file, lines 265-307 — the existing mobile and desktop body sections.

**Desktop body restructure** (lines 285-307 — change `hidden sm:flex` to CSS grid):
```tsx
{/* Desktop body: 3 equal columns — board+info / eval chart / flaw column */}
<div className="hidden sm:grid sm:grid-cols-3 sm:gap-3 sm:items-start">
  {/* Col 1: mini board + info */}
  <div className="flex gap-3 items-start">
    {game.result_fen && (
      <LazyMiniBoard fen={game.result_fen} flipped={game.user_color === 'black'} size={DESKTOP_BOARD_SIZE} />
    )}
    <div className="min-w-0 flex-1 flex flex-col gap-2">
      {openingLine}
      {desktopMetadata}
    </div>
  </div>
  {/* Col 2: eval chart (analyzed only) */}
  <div className="flex items-center justify-center">
    {game.analysis_state === 'analyzed' && game.eval_series && game.flaw_markers && game.phase_transitions
      ? <EvalChart evalSeries={game.eval_series} flawMarkers={game.flaw_markers}
                   phaseTransitions={game.phase_transitions}
                   userColor={game.user_color as 'white' | 'black'}
                   gameId={game.game_id} />
      : <NoAnalysisState gameId={game.game_id} />
    }
  </div>
  {/* Col 3: flaw column */}
  <div className="flex flex-col gap-2">
    {flawContent}
  </div>
</div>
```

**Mobile body addition** (lines 265-283 — insert eval chart between board+info and flawContent):
```tsx
<div className="flex flex-col gap-2 sm:hidden">
  <div className="flex gap-3 items-start">
    {game.result_fen && (
      <LazyMiniBoard fen={game.result_fen} flipped={game.user_color === 'black'} size={MOBILE_BOARD_SIZE} />
    )}
    <div className="flex-1 min-w-0 flex flex-col gap-1">
      {openingLine}
      {mobileMetadata}
    </div>
  </div>
  {/* Eval chart — full-width, analyzed games only */}
  {game.analysis_state === 'analyzed' && game.eval_series && game.flaw_markers && game.phase_transitions && (
    <EvalChart evalSeries={game.eval_series} flawMarkers={game.flaw_markers}
               phaseTransitions={game.phase_transitions}
               userColor={game.user_color as 'white' | 'black'}
               gameId={game.game_id} heightClass="h-20" />
  )}
  <div className="flex flex-col gap-2">
    {flawContent}
  </div>
</div>
```

---

### `tests/services/test_eval_chart_service.py` (NEW)

**Analog:** `tests/services/test_flaws_service.py` — the `_make_pos` / `_make_game` fixture helpers (lines 38-91) are the exact pattern to copy.

**File header and imports** (copy lines 1-35 style):
```python
"""Unit tests for the Phase 109 eval chart builder (_build_eval_series).

No DB required — all tests construct GamePosition / Game objects in memory
using the _make_pos / _make_game helpers from the flaws_service test pattern.

Sign convention: eval_cp / eval_mate are white-perspective (Stockfish).
"""

import pytest

from app.models.game import Game
from app.models.game_position import GamePosition
from app.services.library_service import _build_eval_series
from app.services.flaws_service import (
    BLUNDER_DROP,
    INACCURACY_DROP,
    MISTAKE_DROP,
)
```

**`_make_pos` fixture helper** (copy verbatim from test_flaws_service.py lines 38-70 — identical structure, same ORM instantiation pattern):
```python
def _make_pos(
    ply: int,
    eval_cp: int | None = None,
    eval_mate: int | None = None,
    clock_seconds: float | None = None,
    phase: int = 1,
    move_san: str | None = None,
) -> GamePosition:
    """Build a GamePosition with eval/clock fields for pure unit testing (no DB flush)."""
    pos = GamePosition()
    pos.ply = ply
    pos.eval_cp = eval_cp
    pos.eval_mate = eval_mate
    pos.clock_seconds = clock_seconds
    pos.phase = phase
    pos.move_san = move_san
    pos.full_hash = 0
    pos.white_hash = 0
    pos.black_hash = 0
    pos.material_count = 1000
    pos.material_signature = "KP_KP"
    pos.material_imbalance = 0
    pos.has_opposite_color_bishops = False
    pos.piece_count = 2
    pos.backrank_sparse = False
    pos.mixedness = 100
    pos.endgame_class = None
    return pos
```

**`_make_game` fixture helper** (copy from test_flaws_service.py lines 73-91):
```python
def _make_game(
    user_color: str = "white",
    result: str = "1-0",
    base_time_seconds: int | None = 600,
    increment_seconds: float | None = 0.0,
) -> Game:
    game = Game()
    game.pgn = "1. e4 e5 *"
    game.user_color = user_color
    game.result = result
    game.base_time_seconds = base_time_seconds
    game.increment_seconds = increment_seconds
    return game
```

**Test class structure** (follow `class TestConstants` / `class TestClassifySeverity` pattern from test_flaws_service.py lines 102+):
```python
class TestEvalSeries:
    def test_white_perspective_line_positive_cp(self) -> None: ...
    def test_null_eval_produces_null_es(self) -> None: ...
    def test_mate_hard_1_0_for_chart_line(self) -> None: ...

class TestFlawMarkers:
    def test_both_color_detection(self) -> None: ...
    def test_is_user_flag_player(self) -> None: ...
    def test_is_user_flag_opponent(self) -> None: ...
    def test_inaccuracy_has_empty_tags(self) -> None: ...
    def test_opponent_tags_strip_user_framed(self) -> None: ...

class TestPhaseTransitions:
    def test_no_ply_0_line(self) -> None: ...
    def test_middlegame_first_ply(self) -> None: ...
    def test_endgame_first_ply(self) -> None: ...
    def test_at_most_two_transitions(self) -> None: ...
```

---

## Shared Patterns

### Auth guard
**Source:** `app/routers/library.py` lines 50-53
**Apply to:** `library.py` router (already applied — `current_active_user` dependency on `GET /games`, no change needed).
```python
@router.get("/games", response_model=LibraryGamesResponse)
async def get_library_games(
    session: Annotated[AsyncSession, Depends(get_async_session)],
    user: Annotated[User, Depends(current_active_user)],
```

### IDOR guard (user_id scoping in batch queries)
**Source:** `fetch_page_game_flaws` (library_repository.py lines 314-316)
**Apply to:** `fetch_page_eval_positions` — same `WHERE user_id == user_id` clause.
```python
stmt = select(GameFlaw).where(
    GameFlaw.user_id == user_id,
    GameFlaw.game_id.in_(game_ids),
)
```

### Sentry error capture
**Source:** `get_library_games` (library_service.py lines 235-238)
**Apply to:** No additional capture needed — new builder code runs inside the existing `try/except` block.
```python
    except Exception as exc:
        sentry_sdk.set_context("library_games", {"user_id": user_id})
        sentry_sdk.capture_exception(exc)
        raise
```

### `isAnimationActive={false}` + no CartesianGrid
**Source:** `FlawTrendChart.tsx` line 102; `EndgameScoreOverTimeChart.tsx` lines 284, 295, 303
**Apply to:** All recharts data series in `EvalChart.tsx` — Area, Line, any Bar.

### `useId()` for SVG gradient IDs
**Source:** `FlawTrendChart.tsx` lines 31-33
**Apply to:** `EvalChart.tsx` gradient `id` attribute — prevents collisions when 20 cards render simultaneously.
```tsx
const rawId = useId();
const gradientId = `eval-gradient-${rawId.replace(/[^a-zA-Z0-9]/g, '_')}`;
```

### `noUncheckedIndexedAccess` — narrow before use
**Source:** CLAUDE.md §Frontend Code Style; `EndgameClockDiffOverTimeChart.tsx` line 303-309 (payload narrowing)
**Apply to:** Every `payload?` access in `EvalChart.tsx` dot render prop and tooltip content.
```tsx
const point = payload[0]?.payload as EvalPoint | undefined;
if (!point) return null;
```

### Empty `<g>` instead of `null` in dot render prop
**Source:** `EndgameClockDiffOverTimeChart.tsx` line 307
**Apply to:** `EvalChart.tsx` custom dot renderer for plies without a flaw marker.
```tsx
return <g key={`nodot-${String(payload?.ply ?? cx)}`} />;
```

### `connectNulls={false}`
**Source:** `EndgameScoreOverTimeChart.tsx` lines 284, 295, 303
**Apply to:** `<Area>` and the flaw-dot `<Line>` overlay in `EvalChart.tsx` — breaks the line at plies with null eval.

### Theme constants only — no hex literals in components
**Source:** CLAUDE.md §Frontend; `FlawTrendChart.tsx` (all colors via imports from `@/lib/theme`)
**Apply to:** `EvalChart.tsx` — import all color values from `theme.ts`, no inline oklch/hex strings.

---

## No Analog Found

All 9 files have a close analog. No entries.

---

## Metadata

**Analog search scope:** `app/services/`, `app/repositories/`, `app/schemas/`, `app/routers/`, `frontend/src/components/library/`, `frontend/src/components/charts/`, `frontend/src/types/`, `frontend/src/lib/`, `tests/services/`
**Files read:** 12 source files (all analogs read directly)
**Pattern extraction date:** 2026-06-07
