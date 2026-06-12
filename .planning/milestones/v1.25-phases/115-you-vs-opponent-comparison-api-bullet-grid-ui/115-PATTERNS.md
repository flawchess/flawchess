# Phase 115: You-vs-Opponent Comparison API + Bullet-Grid UI — Pattern Map

**Mapped:** 2026-06-11
**Files analyzed:** 11 new/modified files
**Analogs found:** 11 / 11

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `app/services/flaw_delta_zones.py` | registry / config | transform | `app/services/endgame_zones.py` | exact |
| `app/schemas/library.py` (extend) | model / schema | request-response | `app/schemas/library.py` `FlawStatsResponse` block | exact |
| `app/repositories/library_repository.py` (extend) | repository | CRUD / batch | `fetch_stats_aggregates` + `_filtered_games_base` in same file | exact |
| `app/services/library_service.py` (extend) | service | request-response | `get_flaw_stats` in same file | exact |
| `app/routers/library.py` (extend) | router / controller | request-response | `get_flaw_stats` route in same file | exact |
| `frontend/src/components/charts/MiniBulletChart.tsx` (modify) | component | transform | self (add `invertColors` prop) | exact |
| `frontend/src/components/library/FlawComparisonGrid.tsx` (new) | component | request-response | `FlawStatsPanel.tsx` zone structure + existing `MiniBulletChart` callers | role-match |
| `frontend/src/components/popovers/FlawBulletPopover.tsx` (new) | component | event-driven | `MetricStatPopover.tsx` | exact |
| `frontend/src/hooks/useLibrary.ts` (extend) | hook | request-response | `useLibraryFlawStats` in same file | exact |
| `frontend/src/components/library/FlawStatsPanel.tsx` (modify) | component | request-response | self (remove NormToggle, replace Zone 3) | exact |
| `frontend/src/components/library/FlawTagDistribution.tsx` (delete) | — | — | — | — |

---

## Pattern Assignments

---

### `app/services/flaw_delta_zones.py` (registry, transform)

**Analog:** `app/services/endgame_zones.py`

**Module docstring pattern** (lines 1–11 of endgame_zones.py):
```python
"""Flaw-delta zone registry: authoritative backend source for per-bullet zone constants.

Backend is the single source of truth per Phase 115 D-07. The endpoint embeds
zone_lo / zone_hi / domain in every FlawBullet response so the frontend renders
exactly what the registry stores. No TS codegen — the frontend does not commit
these constants locally.

This module is pure Python with no DB or I/O. All functions are synchronous
and side-effect free.
"""
```

**Frozen dataclass pattern** (endgame_zones.py lines 148–162):
```python
from dataclasses import dataclass

@dataclass(frozen=True)
class FlawDeltaZoneSpec:
    """Zone bounds and axis domain for one flaw-delta bullet.

    zone_lo: Q1 in pp (verbatim from §5 pooled benchmark).
    zone_hi: Q3 in pp (verbatim from §5 pooled benchmark).
    domain: axis half-width in pp (hand-set from p05/p95 per D-04).

    Sign convention (D-08): negative delta = fewer flaws than opponent = good.
    The MiniBulletChart invertColors mode handles color inversion; the registry
    stores raw Q1/Q3 values with no sign flip.
    """
    zone_lo: float
    zone_hi: float
    domain: float
```

**Registry dict pattern** (endgame_zones.py `ZONE_REGISTRY` / `PER_CLASS_GAUGE_ZONES`):
```python
from collections.abc import Mapping

FLAW_DELTA_ZONES: Mapping[str, FlawDeltaZoneSpec] = {
    # Severity family
    "flaw_rate":      FlawDeltaZoneSpec(zone_lo=-0.5, zone_hi=+0.4, domain=2.0),
    "mistake":        FlawDeltaZoneSpec(zone_lo=-0.2, zone_hi=+0.2, domain=1.0),
    "blunder":        FlawDeltaZoneSpec(zone_lo=-0.3, zone_hi=+0.2, domain=1.4),
    # Tempo family
    "low_clock":      FlawDeltaZoneSpec(zone_lo=-0.1, zone_hi=+0.0, domain=0.5),
    "hasty":          FlawDeltaZoneSpec(zone_lo=-0.3, zone_hi=+0.2, domain=1.2),
    "unrushed":       FlawDeltaZoneSpec(zone_lo=-0.4, zone_hi=+0.4, domain=1.7),
    # Phase family
    "opening":        FlawDeltaZoneSpec(zone_lo=-0.1, zone_hi=+0.1, domain=0.8),
    "middlegame":     FlawDeltaZoneSpec(zone_lo=-0.3, zone_hi=+0.2, domain=1.3),
    "endgame_phase":  FlawDeltaZoneSpec(zone_lo=-0.1, zone_hi=+0.1, domain=0.5),
    # Opportunity family
    "miss":           FlawDeltaZoneSpec(zone_lo=-0.1, zone_hi=+0.1, domain=0.5),
    "lucky":          FlawDeltaZoneSpec(zone_lo=-0.1, zone_hi=+0.1, domain=0.5),
    # Impact family
    "reversed":       FlawDeltaZoneSpec(zone_lo=+0.0, zone_hi=+0.0, domain=0.3),
    "squandered":     FlawDeltaZoneSpec(zone_lo=-0.1, zone_hi=+0.1, domain=0.4),
    # Combo family
    "hasty_miss":     FlawDeltaZoneSpec(zone_lo=-0.1, zone_hi=+0.1, domain=0.4),
    "low_clock_miss": FlawDeltaZoneSpec(zone_lo=+0.0, zone_hi=+0.0, domain=0.2),
}
```

**No `assign_zone` helper needed** — the frontend renders what the API sends; no backend zone classification for this surface.

---

### `app/schemas/library.py` (extend — add `FlawBullet` + `FlawComparisonResponse`)

**Analog:** `app/schemas/library.py` lines 254–269 (`FlawStatsResponse`)

**Existing model shape to mirror** (lines 190–269):
```python
from pydantic import BaseModel

class FlawBullet(BaseModel):
    """Per-bullet data for one of the 15 flaw-delta metrics (Phase 115, FLAWCMP-01/03)."""
    tag: str                    # registry key, e.g. "flaw_rate", "hasty_miss"
    delta: float | None         # mean per-game delta (pp); None = both sides zero events
    ci_low: float | None        # 95% CI lower bound (pp)
    ci_high: float | None       # 95% CI upper bound (pp)
    player_events: int          # total player-side tag events across analyzed games
    opp_events: int             # total opponent-side tag events across analyzed games
    zone_lo: float              # Q1 from FLAW_DELTA_ZONES registry
    zone_hi: float              # Q3 from FLAW_DELTA_ZONES registry
    domain: float               # axis half-width from registry (D-04)
    has_zone: bool = True       # False for future zoneless bullets (FLAWUI-04)

class FlawComparisonResponse(BaseModel):
    """Response for GET /api/library/flaw-comparison (Phase 115, FLAWCMP-01/03).

    bullets: always 15 entries ordered by family (severity → tempo → phase →
             opportunity → impact → combos) when below_gate=False; empty list
             when below_gate=True.
    analyzed_n: analyzed game count after the current filter set.
    analyzed_gate: minimum required (constant = FLAW_COMPARISON_GATE = 20).
    below_gate: True when analyzed_n < analyzed_gate — frontend shows CTA (D-10).
    """
    bullets: list[FlawBullet]
    analyzed_n: int
    analyzed_gate: int = 20     # exposed so frontend can render "X of 20" without hardcoding
    below_gate: bool
```

---

### `app/repositories/library_repository.py` (extend — add `fetch_flaw_comparison`)

**Analog:** `fetch_stats_aggregates` (lines 474–560) and `fetch_stats_trend` (lines 563–644) in same file.

**Imports to add** (mirrors existing imports at file top):
```python
from sqlalchemy import ARRAY, Float, Select, Subquery, case, exists, func, or_, select, true
# is_opponent_expr is already imported as: from app.repositories.query_utils import apply_game_filters, player_only_gate
# Add: is_opponent_expr
from app.repositories.query_utils import apply_game_filters, is_opponent_expr, player_only_gate
```

**Per-game LEFT JOIN pattern** (synthesized from `fetch_stats_trend` lines 606–644 + RESEARCH SQL shape):
```python
async def fetch_flaw_comparison(
    session: AsyncSession,
    user_id: int,
    analyzed_game_ids_subq: Subquery,
    *,
    time_control: Sequence[str] | None,
    platform: Sequence[str] | None,
    rated: bool | None,
    opponent_type: str,
    from_date: datetime.date | None,
    to_date: datetime.date | None,
    flaw_severity: Sequence[str] | None,
    opponent_gap_min: int | None,
    opponent_gap_max: int | None,
    color: str | None,
) -> list[Any]:
    """Per-game player/opp counts for all 15 metrics over the analyzed+filtered set.

    LEFT JOIN anchor: analyzed+filtered games list → LEFT JOIN game_flaws so games
    with zero flaws contribute a zero-delta row (§5 all-analyzed-games basis).
    Returns one row per (game_id, user_moves) with 30 COUNT columns (15 player +
    15 opp). Python aggregates mean + CI per metric.

    Pitfall: games with ply_count IS NULL or ply_count = 0 must be excluded
    (dividing by zero user_moves). Filter at the anchor level.
    Pitfall: use is_opponent_expr from query_utils — never inline ply % 2 math.
    """
    base_filtered_subq = _filtered_games_base(
        user_id,
        time_control=time_control,
        platform=platform,
        rated=rated,
        opponent_type=opponent_type,
        from_date=from_date,
        to_date=to_date,
        flaw_severity=flaw_severity,
        opponent_gap_min=opponent_gap_min,
        opponent_gap_max=opponent_gap_max,
        color=color,
    ).subquery("filtered_fc")

    # Anchor: analyzed+filtered games with valid ply_count (D-04 denominator safety)
    anchor_subq = (
        select(
            Game.id.label("game_id"),
            Game.user_color,
            case(
                (Game.user_color == "white", func.floor(Game.ply_count / 2.0)),
                else_=func.ceil(Game.ply_count / 2.0),
            ).label("user_moves"),
        )
        .where(
            Game.user_id == user_id,
            Game.id.in_(select(base_filtered_subq.c.id)),
            Game.id.in_(select(analyzed_game_ids_subq.c.game_id)),
            Game.ply_count.isnot(None),
            Game.ply_count > 0,
        )
        .subquery("anchor")
    )

    # LEFT JOIN game_flaws — one FILTER pair per metric
    # player side: NOT is_opponent_expr; opponent side: is_opponent_expr
    stmt = (
        select(
            anchor_subq.c.game_id,
            anchor_subq.c.user_moves,
            # severity family
            func.count(GameFlaw.ply).filter(
                ~is_opponent_expr(GameFlaw.ply, anchor_subq.c.user_color),
                GameFlaw.severity.in_([_SEVERITY_INT["mistake"], _SEVERITY_INT["blunder"]]),
            ).label("player_flaw_count"),
            func.count(GameFlaw.ply).filter(
                is_opponent_expr(GameFlaw.ply, anchor_subq.c.user_color),
                GameFlaw.severity.in_([_SEVERITY_INT["mistake"], _SEVERITY_INT["blunder"]]),
            ).label("opp_flaw_count"),
            # ... (one pair per remaining 14 metrics)
        )
        .outerjoin(GameFlaw, (GameFlaw.game_id == anchor_subq.c.game_id) & (GameFlaw.user_id == user_id))
        .group_by(anchor_subq.c.game_id, anchor_subq.c.user_moves, anchor_subq.c.user_color)
    )
    rows = (await session.execute(stmt)).all()
    return list(rows)
```

**COUNT FILTER pattern** (from `fetch_stats_aggregates` lines 526–537):
```python
# Single-scan COUNT(*) FILTER idiom — used for aggregated counts
func.count().filter(GameFlaw.severity == _SEVERITY_INT["mistake"])
func.count().filter(GameFlaw.tempo == _TEMPO_INT["low-clock"])
func.count().filter(GameFlaw.is_miss.is_(True))

# Per-game LEFT JOIN variant uses func.count(GameFlaw.ply) not func.count()
# because NULL ply (from LEFT JOIN on absent rows) must not be counted.
func.count(GameFlaw.ply).filter(
    ~is_opponent_expr(GameFlaw.ply, anchor_subq.c.user_color),
    GameFlaw.severity.in_([_SEVERITY_INT["mistake"], _SEVERITY_INT["blunder"]]),
)
```

---

### `app/services/library_service.py` (extend — add `get_flaw_comparison` + CI helper)

**Analog:** `get_flaw_stats` (lines 665–756 in same file)

**Imports to add:**
```python
import math
from app.services.flaw_delta_zones import FLAW_DELTA_ZONES
from app.schemas.library import FlawBullet, FlawComparisonResponse
```

**CI helper — no new file needed** (RESEARCH CI method, `eval_confidence.py` pattern):
```python
def _compute_mean_ci(
    values: list[float],
    z: float = 1.96,
) -> tuple[float, float, float]:
    """Return (mean, ci_low, ci_high) for a list of per-game deltas.

    Returns (0.0, 0.0, 0.0) when values is empty.
    Returns (mean, mean, mean) when n == 1 (undefined variance).
    Normal/t approximation — adequate at N >= 20 per RESEARCH §CI Method.
    """
    n = len(values)
    if n == 0:
        return 0.0, 0.0, 0.0
    mean = sum(values) / n
    if n == 1:
        return mean, mean, mean
    variance = sum((v - mean) ** 2 for v in values) / (n - 1)
    se = math.sqrt(variance / n)
    half = z * se
    return mean, mean - half, mean + half
```

**Service function pattern** (mirrors `get_flaw_stats` lines 665–756):
```python
# Named constant — no magic number in service body (CLAUDE.md no-magic-numbers rule)
FLAW_COMPARISON_GATE: int = 20  # matches §5 cohort inclusion basis (D-09)

async def get_flaw_comparison(
    session: AsyncSession,
    user_id: int,
    *,
    time_control: list[str] | None,
    platform: list[str] | None,
    rated: bool | None,
    opponent_type: str,
    from_date: datetime.date | None,
    to_date: datetime.date | None,
    flaw_severity: list[str] | None,
    opponent_gap_min: int | None = None,
    opponent_gap_max: int | None = None,
    color: str | None = None,
) -> FlawComparisonResponse:
    try:
        total_n, analyzed_n = await library_repository.count_filtered_and_analyzed(
            session, user_id=user_id, **_filter_kwargs
        )
        if analyzed_n < FLAW_COMPARISON_GATE:
            return FlawComparisonResponse(bullets=[], analyzed_n=analyzed_n, below_gate=True)

        analyzed_subq = library_repository._analyzed_game_ids_subquery(user_id)
        rows = await library_repository.fetch_flaw_comparison(
            session, user_id, analyzed_subq, **_filter_kwargs
        )
        bullets = _compute_bullets(rows)
        return FlawComparisonResponse(bullets=bullets, analyzed_n=analyzed_n, below_gate=False)

    except Exception as exc:
        sentry_sdk.set_context("flaw_comparison", {"user_id": user_id})
        sentry_sdk.capture_exception(exc)
        raise
```

**`_compute_bullets` private helper** — iterates rows once, builds per-metric lists of per-game deltas, calls `_compute_mean_ci`, assembles 15 `FlawBullet` objects in family order. Zero-event bullet: when both `player_events == 0` and `opp_events == 0`, set `delta=None`, `ci_low=None`, `ci_high=None`.

---

### `app/routers/library.py` (extend — add `GET /flaw-comparison`)

**Analog:** `get_flaw_stats` route (lines 125–165 in same file)

**Router convention** — prefix is already `"/library"`, add a relative path:
```python
@router.get("/flaw-comparison", response_model=FlawComparisonResponse)
async def get_flaw_comparison(
    session: Annotated[AsyncSession, Depends(get_async_session)],
    user: Annotated[User, Depends(current_active_user)],
    severity: list[SeverityFilter] | None = Query(default=None),
    time_control: list[str] | None = Query(default=None),
    platform: list[str] | None = Query(default=None),
    from_date: datetime.date | None = Query(default=None),
    to_date: datetime.date | None = Query(default=None),
    rated: bool | None = Query(default=None),
    opponent_type: str = Query(default="human"),
    opponent_gap_min: int | None = Query(default=None),
    opponent_gap_max: int | None = Query(default=None),
    color: str | None = Query(default=None),
) -> FlawComparisonResponse:
    """Return the 15-bullet you-vs-opponent comparison for the filtered analyzed set (Phase 115).

    user_id is taken exclusively from the authenticated user — never from a
    request parameter (IDOR prevention, T-108-10 pattern).
    """
    if from_date is not None and to_date is not None and from_date > to_date:
        raise HTTPException(status_code=422, detail="from_date must be <= to_date")
    return await library_service.get_flaw_comparison(
        session,
        user_id=user.id,
        time_control=time_control,
        platform=platform,
        rated=rated,
        opponent_type=opponent_type,
        from_date=from_date,
        to_date=to_date,
        flaw_severity=list(severity) if severity else None,
        opponent_gap_min=opponent_gap_min,
        opponent_gap_max=opponent_gap_max,
        color=color,
    )
```

---

### `frontend/src/components/charts/MiniBulletChart.tsx` (modify — add `invertColors` prop)

**Analog:** self (lines 37–255)

**Props interface extension** (add after `barColor` field, line 82):
```typescript
interface MiniBulletChartProps {
  // ... all existing props unchanged ...
  barColor?: 'zone' | 'neutral';
  /**
   * When true, inverts zone color semantics: values LEFT of the neutral band
   * paint ZONE_SUCCESS (fewer flaws = good); values RIGHT paint ZONE_DANGER.
   * Used for flaw-delta bullets where negative delta = better performance (D-08).
   * Default false — preserves all existing callers unchanged.
   */
  invertColors?: boolean;
}
```

**Existing color logic** (lines 127–133) — REPLACE with:
```typescript
// invertColors: negative delta (left of zone) = good → ZONE_SUCCESS left, ZONE_DANGER right
const positiveColor = invertColors ? ZONE_DANGER : ZONE_SUCCESS;
const negativeColor = invertColors ? ZONE_SUCCESS : ZONE_DANGER;

let fillColor: string;
if (value >= absNeutralMax) {
  fillColor = positiveColor;
} else if (value >= absNeutralMin) {
  fillColor = ZONE_NEUTRAL;
} else {
  fillColor = negativeColor;
}
```

**Background zone order** (lines 157–182) — same inversion applies to the three zone divs:
```typescript
{/* Background zones: left | neutral | right */}
<div className="h-full" style={{ width: `${neutralMinPct}%`, backgroundColor: invertColors ? ZONE_SUCCESS : ZONE_DANGER, opacity: ZONE_OPACITY }} />
<div className="h-full" style={{ width: `${neutralMaxPct - neutralMinPct}%`, backgroundColor: ZONE_NEUTRAL, opacity: ZONE_OPACITY }} />
<div className="h-full" style={{ width: `${100 - neutralMaxPct}%`, backgroundColor: invertColors ? ZONE_DANGER : ZONE_SUCCESS, opacity: ZONE_OPACITY }} />
```

**Destructure addition** (line 103):
```typescript
export function MiniBulletChart({
  // ... existing props ...
  barColor = 'zone',
  invertColors = false,
}: MiniBulletChartProps) {
```

---

### `frontend/src/components/library/FlawComparisonGrid.tsx` (new)

**Analog:** `FlawStatsPanel.tsx` zone structure + `MiniBulletChart` caller patterns

**Imports pattern** (from MiniBulletChart callers in endgame sections):
```typescript
import { MiniBulletChart } from '@/components/charts/MiniBulletChart';
import { FlawBulletPopover } from '@/components/popovers/FlawBulletPopover';
import type { FlawComparisonResponse, FlawBullet } from '@/types/library';
```

**Grid layout** (D-03: 3-col desktop, 1-col mobile; D-01: family headers span full width):
```typescript
// Grid container
<div data-testid="flaw-comparison-grid" className="grid grid-cols-1 lg:grid-cols-3 gap-2">
  {/* Family section header — spans full width */}
  <h4 className="col-span-1 lg:col-span-3 text-sm font-medium text-muted-foreground mt-2">
    Severity
  </h4>
  {/* Bullet rows inside the same grid */}
  {severityBullets.map((bullet) => (
    <FlawBulletRow key={bullet.tag} bullet={bullet} />
  ))}
  {/* ... repeat for tempo, phase, opportunity, impact, combos */}
</div>
```

**Below-gate CTA state** (D-10 — rendered instead of the grid):
```typescript
if (data.below_gate) {
  return (
    <div data-testid="flaw-comparison-gate-cta" className="text-sm text-muted-foreground py-4">
      {/* current analyzed count vs 20 needed + lichess server analysis guidance */}
    </div>
  );
}
```

**Bullet row states** (D-11):
- Normal: `<MiniBulletChart value={bullet.delta} neutralMin={bullet.zone_lo} neutralMax={bullet.zone_hi} domain={bullet.domain} ciLow={bullet.ci_low} ciHigh={bullet.ci_high} invertColors center={0} />`
- Zero-event (`player_events === 0 && opp_events === 0`): muted placeholder text, row does not reflow
- `data-testid` pattern: `data-testid={`flaw-bullet-row-${bullet.tag}`}`

**Loading/error chain pattern** — copy from `FlawStatsPanel.tsx` (the `isLoading / isError / data` ternary chain):
```typescript
// Always handle isError branch per CLAUDE.md frontend rules
if (isLoading) return <LoadingSkeleton />;
if (isError) return <ErrorMessage message="Failed to load comparison. Something went wrong. Please try again in a moment." />;
if (!data) return null;
```

---

### `frontend/src/components/popovers/FlawBulletPopover.tsx` (new)

**Analog:** `MetricStatPopover.tsx` (lines 1–96) — exact structural copy

**Structural pattern** (copy MetricStatPopover shell, substituting HelpCircle trigger for Search):
```typescript
import { HelpCircle } from 'lucide-react';
import { Popover as PopoverPrimitive } from 'radix-ui';
import { cn } from '@/lib/utils';

const HOVER_OPEN_DELAY_MS = 100;  // same constant as MetricStatPopover

export interface FlawBulletPopoverProps {
  tag: string;          // bullet key, used to select content
  testId: string;
  ariaLabel: string;
  triggerClassName?: string;
}
```

**Trigger pattern** (lines 59–73 of MetricStatPopover.tsx — use HelpCircle not Search):
```typescript
<span
  role="button"
  tabIndex={0}
  className={cn(
    'inline-flex items-center text-brand-brown-light/70 hover:text-brand-brown focus:outline-none cursor-pointer',
    triggerClassName,
  )}
  aria-label={ariaLabel}
  data-testid={testId}
  onMouseEnter={handleMouseEnter}
  onMouseLeave={handleMouseLeave}
>
  <HelpCircle className="h-4 w-4" />
</span>
```

**Content pattern** (lines 75–95 of MetricStatPopover.tsx — identical Portal + Content structure):
```typescript
<PopoverPrimitive.Portal>
  <PopoverPrimitive.Content
    side="top"
    sideOffset={4}
    className={cn(
      'z-50 max-w-xs rounded-md border-0 outline-none bg-foreground px-3 py-1.5 text-xs text-background',
      'data-[state=open]:animate-in data-[state=open]:fade-in-0 data-[state=open]:zoom-in-95',
      // ... same animation classes
    )}
  >
    {/* Per-bullet content: definition + sign convention line + optional caveats */}
    {/* text-xs allowed per CLAUDE.md exception for hover-activated info tooltips */}
  </PopoverPrimitive.Content>
</PopoverPrimitive.Portal>
```

**Required popover content per D-15:**
- Definition paragraph (from `flaw-tag-definitions.md`)
- Sign convention line: "Negative = fewer flaws than opponents = better."
- Tempo-interaction caveat for `low_clock`, `hasty`, `unrushed`, `low_clock_miss`, `hasty_miss`
- Exposure caveat for `squandered`, `lucky` (114 D-03: reads partly as how often the situation arose)
- Severity-basis caveat (D-13): "Zone was computed on M+B basis; under a severity filter your delta reflects that filter's scope."
- Filter line (D-14): generic wording like "Filters change your point estimate; the typical zone may not follow your filters."

---

### `frontend/src/hooks/useLibrary.ts` (extend — add `useLibraryFlawComparison`)

**Analog:** `useLibraryFlawStats` (lines 83–94 in same file) — exact structural copy

```typescript
/**
 * Fetch the 15-bullet flaw comparison for the current filter + flaw filter.
 *
 * Query key: ['library-flaw-comparison', params]
 * Independent of ['library-flaw-stats', params] — separate endpoint, separate type.
 */
export function useLibraryFlawComparison(
  filters: FilterState,
  flawFilter: FlawFilterState,
) {
  const params = buildLibraryParams(filters, flawFilter.severity, flawFilter.tags);
  return useQuery({
    queryKey: ['library-flaw-comparison', params],
    queryFn: () => libraryApi.getFlawComparison(params),
    staleTime: LIBRARY_STALE_TIME,
    refetchOnWindowFocus: false,
  });
}
```

**API client addition** — add `getFlawComparison(params)` to `libraryApi` in `frontend/src/api/client.ts`, mirroring `getFlawStats`.

---

### `frontend/src/components/library/FlawStatsPanel.tsx` (modify)

**Analog:** self — surgical modifications only

**What to change:**
1. Remove `NormToggle` import and JSX (D-02). Remove the `normMode` state and the `per_game` rendering path.
2. Remove `FlawTagDistribution` import and JSX (Zone 3).
3. Import `FlawComparisonGrid` and `useLibraryFlawComparison`.
4. Replace Zone 3 JSX with `<FlawComparisonGrid />` passing the comparison query result.
5. `FlawStatsBand` — remove any `normMode` prop; fix to `per_100_moves` (D-02).

**Loading/error state extension** — the existing `isLoading / isError / data` ternary chain in the panel stays for Zones 1–2. Zone 3 (`FlawComparisonGrid`) handles its own loading/error state internally using `useLibraryFlawComparison`.

---

### `frontend/src/components/library/FlawTagDistribution.tsx` + `__tests__/` (delete)

**Pre-deletion check:** Grep confirms `FlawTagDistribution` is only imported by `FlawStatsPanel.tsx` (RESEARCH A3). Safe to delete both the component file and its test file. Knip will fail CI if the export remains — deletion is the correct action (not export removal), because the file itself is dead.

---

## Shared Patterns

### Authentication / IDOR guard
**Source:** `app/routers/library.py` lines 55–103 (existing routes)
**Apply to:** `GET /flaw-comparison` endpoint
```python
# user_id always from authenticated session — never from request params
user: Annotated[User, Depends(current_active_user)]
# ...
user_id=user.id,  # not from query params
```

### Sentry error capture
**Source:** `app/services/library_service.py` lines 753–756 (`get_flaw_stats`)
**Apply to:** `get_flaw_comparison` service function
```python
except Exception as exc:
    sentry_sdk.set_context("flaw_comparison", {"user_id": user_id})
    sentry_sdk.capture_exception(exc)
    raise
```

### Filter kwargs forwarding
**Source:** `app/services/library_service.py` lines 715–726 (`_filter_kwargs` dict)
**Apply to:** `get_flaw_comparison` service function — same 9-key dict passed to both `count_filtered_and_analyzed` and `fetch_flaw_comparison`.

### `is_opponent_expr` usage
**Source:** `app/repositories/query_utils.py` lines 23–51
**Apply to:** `fetch_flaw_comparison` repository function — every COUNT FILTER split must use `is_opponent_expr(GameFlaw.ply, anchor_subq.c.user_color)` and `~is_opponent_expr(...)`. Never inline `ply % 2` math.

### `_analyzed_game_ids_subquery` reuse
**Source:** `app/repositories/library_repository.py` lines 815–835
**Apply to:** `get_flaw_comparison` — call `library_repository._analyzed_game_ids_subquery(user_id)` identical to `get_flaw_stats` line 713. This subquery is the §5 all-analyzed-games basis gate.

### `data-testid` + ARIA naming convention
**Source:** CLAUDE.md §Browser Automation Rules
**Apply to:** `FlawComparisonGrid`, `FlawBulletPopover`, and all bullet rows
```
data-testid="flaw-comparison-grid"
data-testid="flaw-comparison-gate-cta"
data-testid="flaw-bullet-row-{tag}"          # e.g. flaw-bullet-row-flaw_rate
data-testid="flaw-bullet-popover-{tag}"      # e.g. flaw-bullet-popover-hasty
data-testid="flaw-comparison-loading"        # loading skeleton
aria-label="Flaw comparison: {label}"        # accessible label per bullet
```

### Theme color constants
**Source:** `frontend/src/lib/theme.ts` (ZONE_SUCCESS, ZONE_DANGER, ZONE_NEUTRAL, BULLET_BAR_NEUTRAL)
**Apply to:** `MiniBulletChart.tsx` `invertColors` logic — use the same imported constants; no new raw hex values.

### `text-sm` floor
**Source:** CLAUDE.md §Frontend / No `text-xs`
**Apply to:** All new component UI text (labels, family headers, CTA copy).
**Exception:** `FlawBulletPopover` content may use `text-xs` (CLAUDE.md: hover/tap-activated info tooltips are the single intentional exception).

---

## No Analog Found

All 11 files have analogs. No entries in this section.

---

## Metadata

**Analog search scope:** `app/services/`, `app/repositories/`, `app/schemas/`, `app/routers/`, `frontend/src/components/`, `frontend/src/hooks/`
**Files scanned:** 10 source files read directly
**Pattern extraction date:** 2026-06-11
