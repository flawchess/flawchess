# Phase 126: Comparison Stats + Frontend — Pattern Map

**Mapped:** 2026-06-18
**Files analyzed:** 13 new/modified files
**Analogs found:** 13 / 13

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `app/routers/library.py` (add endpoint) | router | request-response | same file `@router.get("/flaw-comparison")` line 172 | exact |
| `app/schemas/library.py` (add schema) | types/schema | request-response | same file `FlawComparisonResponse` / `FlawBullet` lines 285–326 | exact |
| `app/services/library_service.py` (add fn) | service | CRUD | same file `get_flaw_comparison` line 1084 | exact |
| `app/repositories/library_repository.py` (add fn) | repository | CRUD | same file `fetch_flaw_comparison` line 1039 | exact |
| `app/repositories/query_utils.py` (add filter arg) | utility | CRUD | same file `apply_game_filters` line 74 | exact |
| `frontend/src/lib/tacticComparisonMeta.ts` (new) | lib-constants | — | `frontend/src/lib/flawComparisonMeta.ts` | exact |
| `frontend/src/lib/tacticMotifDefinitions.ts` (new) | lib-constants | — | `frontend/src/lib/tagDefinitions.ts` | role-match |
| `frontend/src/lib/theme.ts` (add constants) | lib-constants | — | same file, existing `FAM_*` / `FAM_*_BG` block | exact |
| `frontend/src/api/client.ts` (add fn) | utility | request-response | same file `getFlawComparison` line 275 | exact |
| `frontend/src/hooks/useLibrary.ts` (add hook) | hook | request-response | same file `useLibraryFlawComparison` line 110 | exact |
| `frontend/src/components/library/TacticComparisonGrid.tsx` (new) | component | request-response | `FlawComparisonGrid.tsx` | exact |
| `frontend/src/components/library/TacticMotifChip.tsx` (new) | component | event-driven | `TagChip.tsx` | exact |
| `frontend/src/components/filters/FilterPanel.tsx` (modify) | component | event-driven | same file, `toggleTimeControl` / `isTimeControlActive` block | exact |

---

## Pattern Assignments

### `app/routers/library.py` — add `GET /tactic-comparison`

**Analog:** `app/routers/library.py` lines 172–208

**Imports pattern** (lines 14–30): already imported — `APIRouter`, `Depends`, `HTTPException`, `Query`, `Annotated`, `AsyncSession`, `get_async_session`, `User`, `current_active_user`, `library_service`.

Add to schema imports: `TacticComparisonResponse` (the new response model).

**Core endpoint pattern** (lines 172–208):
```python
@router.get("/tactic-comparison", response_model=TacticComparisonResponse)
async def get_tactic_comparison(
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
    tactic_families: list[str] | None = Query(default=None),
) -> TacticComparisonResponse:
    """Per-family tactic motif you-vs-opponent comparison (Phase 126).
    user_id taken from current_active_user only (IDOR prevention).
    """
    if from_date is not None and to_date is not None and from_date > to_date:
        raise HTTPException(status_code=422, detail="from_date must be <= to_date")
    return await library_service.get_tactic_comparison(
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
        tactic_families=tactic_families,
    )
```

---

### `app/schemas/library.py` — add `TacticBullet` + `TacticComparisonResponse`

**Analog:** `app/schemas/library.py` lines 285–326 (`FlawBullet` + `FlawComparisonResponse`)

**Core schema pattern** (lines 285–326):
```python
class TacticBullet(BaseModel):
    """Per-family data for one tactic-motif family row (Phase 126)."""
    family: str              # family key e.g. "fork", "pin_skewer"
    you_rate: float | None   # mean tactic allowances per game (player side); None = zero events
    opp_rate: float | None   # mean tactic allowances per game (opponent side); None = zero events
    delta: float | None      # you_rate - opp_rate; None = both sides zero events
    ci_low: float | None     # 95% CI lower bound on delta
    ci_high: float | None    # 95% CI upper bound on delta
    p_value: float | None    # two-sided p vs H0: delta == 0; None = zero events
    you_events: int          # raw event count (player side)
    opp_events: int          # raw event count (opponent side)
    zone_lo: float           # benchmark Q1 or 0.0 when unavailable
    zone_hi: float           # benchmark Q3 or 0.0 when unavailable
    has_zone: bool = False   # False until tactic benchmark pipeline ships


class TacticComparisonResponse(BaseModel):
    """Response for GET /api/library/tactic-comparison (Phase 126).

    bullets: ordered by rank (largest significant gap first, volume fallback),
             up to 6 family rows; empty list when below_gate=True.
    analyzed_n: analyzed game count after filters.
    analyzed_gate: minimum required (mirrors FLAW_COMPARISON_GATE).
    below_gate: True when analyzed_n < analyzed_gate.
    """
    bullets: list[TacticBullet]
    analyzed_n: int
    analyzed_gate: int
    below_gate: bool
```

---

### `app/services/library_service.py` — add `get_tactic_comparison`

**Analog:** `app/services/library_service.py` lines 1084–1156

**Key constants to add** (mirror `FLAW_COMPARISON_GATE` at line 957):
```python
# Mirror FLAW_COMPARISON_GATE = 20 — same minimum analyzed-game floor.
TACTIC_COMPARISON_GATE: int = 20

# Confidence threshold for chip display (D-09); must be a named constant.
MIN_TACTIC_CHIP_CONFIDENCE: int = 70  # percent (0–100 scale matching tactic_confidence column)
```

**Service pipeline pattern** (lines 1084–1156 as template):
```python
async def get_tactic_comparison(
    session: AsyncSession,
    user_id: int,
    *,
    time_control: Sequence[str] | None,
    platform: Sequence[str] | None,
    rated: bool | None,
    opponent_type: str,
    from_date: datetime.date | None,
    to_date: datetime.date | None,
    flaw_severity: Sequence[str] | None,
    opponent_gap_min: int | None = None,
    opponent_gap_max: int | None = None,
    color: str | None = None,
    tactic_families: Sequence[str] | None = None,
) -> TacticComparisonResponse:
    try:
        _filter_kwargs = dict(...)  # same pattern as get_flaw_comparison
        _total_n, analyzed_n = await library_repository.count_filtered_and_analyzed(
            session, user_id=user_id, **_filter_kwargs
        )
        if analyzed_n < TACTIC_COMPARISON_GATE:
            return TacticComparisonResponse(
                bullets=[], analyzed_n=analyzed_n,
                analyzed_gate=TACTIC_COMPARISON_GATE, below_gate=True,
            )
        analyzed_subq = library_repository._analyzed_game_ids_subquery(user_id)
        rows = await library_repository.fetch_tactic_comparison(
            session, user_id, analyzed_subq,
            tactic_families=tactic_families, **_filter_kwargs,
        )
        bullets = _compute_tactic_bullets(rows)
        return TacticComparisonResponse(
            bullets=bullets, analyzed_n=analyzed_n,
            analyzed_gate=TACTIC_COMPARISON_GATE, below_gate=False,
        )
    except Exception as exc:
        sentry_sdk.set_context("tactic_comparison", {"user_id": user_id})
        sentry_sdk.capture_exception(exc)
        raise
```

**CI computation** — use `_compute_mean_ci` (already in `library_service.py` at line 960) for delta CI. Sign convention: positive delta = you allow MORE than opponents = bad (matches `FlawBullet`).

**Ranking** — after computing bullets, sort by: largest `|delta|` where `ci_low > 0 or ci_high < 0` (significant gap) descending, then by `max(you_events, opp_events)` descending for non-significant rows. Return up to 6.

---

### `app/repositories/library_repository.py` — add `fetch_tactic_comparison`

**Analog:** `app/repositories/library_repository.py` lines 1039–end

**Core pattern** (lines 1039–1101 as template):
- Reuse `_filtered_games_base()` for the base filtered subquery
- Reuse `_analyzed_game_ids_subquery()` for analyzed game anchor
- LEFT JOIN `game_flaws` with `tactic_motif IS NOT NULL AND tactic_confidence >= :t`
- Use `is_opponent_expr(GameFlaw.ply, anchor_subq.c.user_color)` from `query_utils` — never inline `ply % 2` math
- `func.count(GameFlaw.ply)` (not `func.count()`) so NULL LEFT JOIN rows count as 0
- Group by family using `CASE WHEN tactic_motif IN (FORK_MOTIFS) THEN 'fork' ...` mapping

**`tactic_families` filter** in fetch function:
```python
# Apply family filter when provided: expand family keys to their motif int sets.
if tactic_families:
    motif_ints = [m for fam in tactic_families for m in FAMILY_TO_MOTIF_INTS[fam]]
    stmt = stmt.where(GameFlaw.tactic_motif.in_(motif_ints))
```

---

### `app/repositories/query_utils.py` — add `tactic_families` filter arg

**Analog:** `apply_game_filters` function lines 74–193. `flaw_tags` at line 88 shows how an optional list arg is added:

```python
def apply_game_filters(
    stmt: Any,
    time_control: Sequence[str] | None,
    ...
    flaw_tags: Sequence[str] | None = None,
    tactic_families: Sequence[str] | None = None,  # NEW — Phase 126 D-06
    user_id: int | None = None,
) -> Any:
```

When `tactic_families` is non-empty, add WHERE clause narrowing `game_flaws.tactic_motif` to the motif ints for the selected families (uses a lazy import of the motif→family mapping to avoid circular imports, mirroring the `flaw_exists_from_table` lazy import pattern at line 181).

---

### `frontend/src/lib/theme.ts` — add tactic family color constants

**Analog:** `theme.ts` lines 62–82 (`FAM_*` / `FAM_*_BG` block)

**Pattern** (copy the FAM_ export pair pattern):
```typescript
// Tactic motif family colors (Phase 126). Hues chosen to avoid collision
// with WDL semantic hues (25/145/260) and existing flaw-family hues (55/170/200/290/330/350).
export const TAC_FORK = 'oklch(0.72 0.18 40)';           // orange
export const TAC_FORK_BG = 'oklch(0.72 0.18 40 / 0.15)';
export const TAC_PIN_SKEWER = 'oklch(0.68 0.16 240)';    // indigo
export const TAC_PIN_SKEWER_BG = 'oklch(0.68 0.16 240 / 0.15)';
export const TAC_DISCOVERY = 'oklch(0.68 0.16 130)';     // lime
export const TAC_DISCOVERY_BG = 'oklch(0.68 0.16 130 / 0.15)';
export const TAC_MATE = 'oklch(0.62 0.20 10)';           // crimson
export const TAC_MATE_BG = 'oklch(0.62 0.20 10 / 0.15)';
export const TAC_HANGING = 'oklch(0.73 0.16 80)';        // gold
export const TAC_HANGING_BG = 'oklch(0.73 0.16 80 / 0.15)';
export const TAC_COMBINATIONS = 'oklch(0.68 0.16 300)';  // fuchsia
export const TAC_COMBINATIONS_BG = 'oklch(0.68 0.16 300 / 0.15)';
```

---

### `frontend/src/lib/tacticComparisonMeta.ts` (new file)

**Analog:** `frontend/src/lib/flawComparisonMeta.ts` (complete file)

**Import pattern** (lines 1–60 of analog):
```typescript
import type { ComponentType, CSSProperties } from 'react';
import { GitFork, Minus, Zap, Crown, AlertTriangle, Swords } from 'lucide-react';
import {
  TAC_FORK, TAC_FORK_BG, TAC_PIN_SKEWER, TAC_PIN_SKEWER_BG,
  TAC_DISCOVERY, TAC_DISCOVERY_BG, TAC_MATE, TAC_MATE_BG,
  TAC_HANGING, TAC_HANGING_BG, TAC_COMBINATIONS, TAC_COMBINATIONS_BG,
  ZONE_DANGER, ZONE_NEUTRAL, ZONE_SUCCESS,
} from '@/lib/theme';
import type { TacticBullet } from '@/types/library';
```

**Family type pattern** (lines 64–106 of analog):
```typescript
export type TacticFamily = 'fork' | 'pin_skewer' | 'discovery' | 'mate' | 'hanging' | 'combinations';

export interface TacticFamilyColors { color: string; bg: string; }

export const TACTIC_FAMILY_COLORS: Record<TacticFamily, TacticFamilyColors> = {
  fork:         { color: TAC_FORK,         bg: TAC_FORK_BG },
  pin_skewer:   { color: TAC_PIN_SKEWER,   bg: TAC_PIN_SKEWER_BG },
  discovery:    { color: TAC_DISCOVERY,    bg: TAC_DISCOVERY_BG },
  mate:         { color: TAC_MATE,         bg: TAC_MATE_BG },
  hanging:      { color: TAC_HANGING,      bg: TAC_HANGING_BG },
  combinations: { color: TAC_COMBINATIONS, bg: TAC_COMBINATIONS_BG },
};

export interface TacticFamilyDef { name: string; family: TacticFamily; motifs: string[]; }

export const TACTIC_COMPARISON_FAMILIES: TacticFamilyDef[] = [
  { name: 'Fork',           family: 'fork',         motifs: ['fork'] },
  { name: 'Pin / Skewer',   family: 'pin_skewer',   motifs: ['pin', 'skewer', 'x-ray'] },
  { name: 'Discovery',      family: 'discovery',    motifs: ['discovered-attack', 'double-check'] },
  { name: 'Mate patterns',  family: 'mate',         motifs: ['back-rank-mate', 'smothered-mate', 'anastasia-mate', 'hook-mate', 'arabian-mate', 'boden-mate', 'double-bishop-mate', 'dovetail-mate', 'mate'] },
  { name: 'Hanging piece',  family: 'hanging',      motifs: ['hanging-piece'] },
  { name: 'Combinations',   family: 'combinations', motifs: ['sacrifice', 'deflection', 'attraction', 'intermezzo', 'interference', 'self-interference', 'clearance', 'capturing-defender'] },
];
```

**Stat helpers** (lines 235–276 of analog — copy `isFlawDeltaSignificant` and `flawDeltaZoneColor` patterns verbatim, rename to `isTacticDeltaSignificant` and `tacticDeltaZoneColor`):
```typescript
// Tactic delta: positive = you allow MORE = bad → same invertColors=true convention as FlawBullet.
export function isTacticDeltaSignificant(bullet: TacticBullet): boolean {
  if (bullet.ci_low == null || bullet.ci_high == null) return false;
  return bullet.ci_low > 0 || bullet.ci_high < 0;
}

export function tacticDeltaZoneColor(delta: number, zoneLo: number, zoneHi: number): string {
  if (delta >= zoneHi) return ZONE_DANGER;
  if (delta >= zoneLo) return ZONE_NEUTRAL;
  return ZONE_SUCCESS;
}
```

---

### `frontend/src/lib/tacticMotifDefinitions.ts` (new file)

**Analog:** `frontend/src/lib/tagDefinitions.ts`

**Pattern:** Simple `Record<string, string>` export with one-sentence definitions per motif name.
```typescript
export const TACTIC_MOTIF_DEFINITIONS: Record<string, string> = {
  'fork': 'A single piece attacks two or more of the opponent\'s pieces simultaneously.',
  'pin': 'A piece is immobilized because moving it would expose a more valuable piece behind it.',
  // ... one entry per motif string
};
```

Used by `TacticMotifChip` popover body: `<strong>{motif}</strong>: {TACTIC_MOTIF_DEFINITIONS[motif]}`

---

### `frontend/src/api/client.ts` — add `getTacticComparison`

**Analog:** `libraryApi.getFlawComparison` lines 275–291

**Pattern:**
```typescript
getTacticComparison: (params: {
  time_control?: string[] | null;
  platform?: string[] | null;
  from_date?: string | null;
  to_date?: string | null;
  rated?: boolean | null;
  opponent_type?: string;
  opponent_strength?: OpponentStrengthRange;
  color?: string | null;
  severity?: ('blunder' | 'mistake')[];
  tactic_families?: string[];
}) =>
  apiClient.get<TacticComparisonResponse>('/library/tactic-comparison', {
    params: {
      ...buildFilterParams(params),
      ...(params.severity?.length ? { severity: params.severity } : {}),
      ...(params.tactic_families?.length ? { tactic_families: params.tactic_families } : {}),
    },
  }).then(r => r.data),
```

---

### `frontend/src/hooks/useLibrary.ts` — add `useTacticComparison`

**Analog:** `useLibraryFlawComparison` lines 110–121

**Pattern:**
```typescript
export function useTacticComparison(
  filters: FilterState,
  flawFilter: FlawFilterState,
  tacticFamilies: TacticFamily[],
) {
  const params = buildLibraryParams(filters, flawFilter.severity, flawFilter.tags);
  return useQuery({
    queryKey: ['library-tactic-comparison', params, tacticFamilies],
    queryFn: () => libraryApi.getTacticComparison({
      ...params,
      tactic_families: tacticFamilies.length > 0 ? tacticFamilies : undefined,
    }),
    staleTime: LIBRARY_STALE_TIME,
    refetchOnWindowFocus: false,
  });
}
```

`LIBRARY_STALE_TIME` and `buildLibraryParams` are already in the file — no new imports needed.

---

### `frontend/src/components/library/TacticComparisonGrid.tsx` (new)

**Analog:** `FlawComparisonGrid.tsx` (complete file — 219 lines)

**Structural diff from analog:**
- Import `TACTIC_COMPARISON_FAMILIES`, `TACTIC_FAMILY_COLORS`, `isTacticDeltaSignificant`, `tacticDeltaZoneColor` from `tacticComparisonMeta.ts` instead of `flawComparisonMeta.ts`
- Self-fetch via `useTacticComparison` instead of `useLibraryFlawComparison`
- Family card iterates `TACTIC_COMPARISON_FAMILIES` (6 families) instead of 6 flaw families
- `data-testid` names: `tactic-comparison-grid`, `tactic-comparison-loading`, `tactic-comparison-gate-cta`, `tactic-family-card-{familyKey}`, `tactic-family-header-{familyKey}`, `tactic-bullet-row-{familyKey}`, `tactic-bullet-popover-{familyKey}`
- Beta gate: wrap the top-level return: `if (!user.beta_enabled) return null;`
- Gate CTA copy (from UI-SPEC): `"{n} of {gate} analyzed games needed"` + Lichess server analysis explanation
- Benchmark zone degradation: when `!bullet.has_zone`, pass `neutralMin={0} neutralMax={0}` to `MiniBulletChart` — the band collapses, chart still shows delta bar and CI whiskers

**`TacticBulletRow` sub-component pattern** (mirrors `FlawBulletRow` lines 55–107):
```tsx
function TacticBulletRow({ bullet }: { bullet: TacticBullet }) {
  const family = bullet.family as TacticFamily;
  const familyDef = TACTIC_COMPARISON_FAMILIES.find(f => f.family === family);
  const { color } = TACTIC_FAMILY_COLORS[family];
  const isZeroEvent = bullet.delta === null;
  const numberColor =
    !isZeroEvent && bullet.delta !== null && isTacticDeltaSignificant(bullet)
      ? tacticDeltaZoneColor(bullet.delta, bullet.zone_lo, bullet.zone_hi)
      : undefined;

  return (
    <div className="flex flex-col gap-1" data-testid={`tactic-bullet-row-${bullet.family}`}>
      <div className="flex items-center gap-1.5">
        {/* family icon + label + signed delta + popover trigger */}
      </div>
      {isZeroEvent ? (
        <p className="text-sm text-muted-foreground/50 italic">No events in current filter</p>
      ) : (
        <MiniBulletChart
          value={bullet.delta ?? 0}
          neutralMin={bullet.has_zone ? bullet.zone_lo : 0}
          neutralMax={bullet.has_zone ? bullet.zone_hi : 0}
          center={0}
          ciLow={bullet.ci_low ?? undefined}
          ciHigh={bullet.ci_high ?? undefined}
          invertColors
          barColor="neutral"
        />
      )}
    </div>
  );
}
```

**Beta gate access pattern** — access user from `useAuth`:
```tsx
import { useAuth } from '@/hooks/useAuth';
// inside component:
const { user } = useAuth();
if (!user?.beta_enabled) return null;
```

---

### `frontend/src/components/library/TacticMotifChip.tsx` (new)

**Analog:** `TagChip.tsx` (complete file — 287 lines)

**Key differences from analog:**
- Props: `motif: string`, `flawId: number`, `confidence: number` (caller must gate on `confidence >= MIN_TACTIC_CHIP_CONFIDENCE` before rendering — or the chip gates internally via a const import)
- Family resolved via `TACTIC_FAMILY_FOR_MOTIF` lookup (derived from `TACTIC_COMPARISON_FAMILIES`) instead of `getTagFamily(tag)`
- Colors: `TACTIC_FAMILY_COLORS[family]` instead of `TAG_FAMILY_COLORS[getTagFamily(tag)]`
- Icon: `TACTIC_FAMILY_ICON[family]` (6-entry Record from `tacticComparisonMeta.ts`)
- Popover body: `<span className="font-bold">{motif}</span>: {TACTIC_MOTIF_DEFINITIONS[motif]}`
- `data-testid`: `chip-tactic-{motif}-{flawId}` (UI-SPEC §data-testid)
- `aria-label`: `Tactic: {motif} — {definition}`
- Popover `data-testid`: `tag-popover-tactic-{motif}-{flawId}`
- No `onHover` / `onActivate` / filter-ring subscription — purely informational (D-10)
- `useIsMobile` hook: copy exact pattern from `TagChip.tsx` lines 16–29 (same `SM_BREAKPOINT_PX = 640` + `matchMedia`)
- `HIGHLIGHT_BG` helper: copy exact pattern from `TagChip.tsx` line 36
- Hover/open timing: `scheduleOpen` 100ms delay, `scheduleClose` 80ms grace (lines 125–135)

**Chip span** (line 148–207 as template):
```tsx
<span
  className="inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-xs font-bold cursor-pointer transition-all hover:-translate-y-px"
  style={{ color, backgroundColor: highlighted ? HIGHLIGHT_BG(bg) : bg, borderColor: color }}
  role="button"
  tabIndex={0}
  aria-label={`Tactic: ${motif} — ${TACTIC_MOTIF_DEFINITIONS[motif] ?? motif}`}
  data-testid={`chip-tactic-${motif}-${flawId}`}
  onMouseEnter={() => { scheduleOpen(); setHighlighted(true); }}
  onMouseLeave={() => { scheduleClose(); setHighlighted(false); }}
  onFocus={() => setHighlighted(true)}
  onBlur={() => setHighlighted(false)}
  onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); setOpen(o => !o); } }}
>
  <Icon className="h-3 w-3 shrink-0" />
  {motif}
</span>
```

---

### `frontend/src/components/filters/FilterPanel.tsx` — add `TacticMotifFilter` section

**Analog:** Time Control multi-select toggle-group section (lines 228–237)

**FilterState extension** — add `tacticFamilies` field:
```typescript
export interface FilterState {
  // ... existing fields ...
  tacticFamilies: TacticFamily[] | null;  // null = all families (no filter)
}
```

**toggle/active helper pattern** (mirror `toggleTimeControl` / `isTimeControlActive` lines 228–242):
```typescript
const toggleTacticFamily = (fam: TacticFamily) => {
  const ALL = TACTIC_COMPARISON_FAMILIES.map(f => f.family);
  const current = filters.tacticFamilies ?? ALL;
  if (current.includes(fam)) {
    const next = current.filter(f => f !== fam);
    update({ tacticFamilies: next.length === ALL.length ? null : next.length === 0 ? [fam] : next });
  } else {
    const next = [...current, fam];
    update({ tacticFamilies: next.length === ALL.length ? null : next });
  }
};

const isTacticFamilyActive = (fam: TacticFamily): boolean => {
  if (filters.tacticFamilies === null) return true;
  return filters.tacticFamilies.includes(fam);
};
```

**Render section** (beta-gated, appended after existing filter sections):
```tsx
{user?.beta_enabled && visibleFilters.includes('tacticMotif') && (
  <div className="flex flex-col gap-2">
    <Label className="text-sm font-medium">Tactic motif</Label>
    <ToggleGroup type="multiple" className="flex flex-wrap gap-1">
      {TACTIC_COMPARISON_FAMILIES.map(({ family, name }) => {
        const { color, bg } = TACTIC_FAMILY_COLORS[family];
        return (
          <ToggleGroupItem
            key={family}
            value={family}
            data-testid={`filter-tactic-motif-${family}`}
            data-state={isTacticFamilyActive(family) ? 'on' : 'off'}
            onClick={() => toggleTacticFamily(family)}
            style={{ borderColor: color, color: isTacticFamilyActive(family) ? color : undefined,
                     backgroundColor: isTacticFamilyActive(family) ? bg : undefined }}
            className="text-sm rounded-full border px-2 py-0.5"
          >
            {name}
          </ToggleGroupItem>
        );
      })}
    </ToggleGroup>
  </div>
)}
```

Add `'tacticMotif'` to the `FilterField` union type and `ALL_FILTERS` array. Apply same section to both the desktop `FilterPanel` and the mobile drawer (CLAUDE.md mobile-parity rule — search for duplicated filter markup before considering complete).

---

## Shared Patterns

### Beta gate (`user?.beta_enabled`)
**Source:** `frontend/src/types/users.ts` line 19 (`beta_enabled: boolean`), `frontend/src/hooks/useAuth.ts` `useAuth()` returns `{ user: UserResponse | null, ... }`
**Apply to:** `TacticComparisonGrid`, `TacticMotifChip` (parent should gate), `FilterPanel` tactic section

Pattern:
```tsx
const { user } = useAuth();
if (!user?.beta_enabled) return null;
```

### `is_opponent_expr` player/opponent split
**Source:** `app/repositories/query_utils.py` lines 23–51
**Apply to:** `fetch_tactic_comparison` — never inline `ply % 2`; always import and call `is_opponent_expr(GameFlaw.ply, anchor_subq.c.user_color)`

### Sentry error capture
**Source:** `app/services/library_service.py` lines 1153–1156
**Apply to:** `get_tactic_comparison` service function
```python
except Exception as exc:
    sentry_sdk.set_context("tactic_comparison", {"user_id": user_id})
    sentry_sdk.capture_exception(exc)
    raise
```

### `LoadError` component (CLAUDE.md mandate)
**Source:** `FlawComparisonGrid.tsx` line 211
**Apply to:** `TacticComparisonGrid`
```tsx
if (isError) return <LoadError resource="tactic comparison" />;
```

### Date-validation guard in router
**Source:** `app/routers/library.py` lines 193–194
**Apply to:** `get_tactic_comparison` endpoint
```python
if from_date is not None and to_date is not None and from_date > to_date:
    raise HTTPException(status_code=422, detail="from_date must be <= to_date")
```

### `MiniBulletChart` with `invertColors=true barColor="neutral"`
**Source:** `FlawComparisonGrid.tsx` lines 93–104; `MiniBulletChart.tsx` lines 82–90
**Apply to:** `TacticBulletRow` inside `TacticComparisonGrid`
- Positive delta = more tactic allowances than opponents = bad → `invertColors` ensures left-of-zone = green (fewer = good)
- `barColor="neutral"` keeps the bar grey; zone bands carry the verdict color

---

## Family → Motif Int Mapping (backend)

The backend needs a constant mapping `FAMILY_TO_MOTIF_INTS` that translates family keys to lists of `tactic_motif` integer enum values. This mirrors the `_SEVERITY_INT` dict in `library_repository.py`. Read `app/models/game_flaw.py` for the actual `TacticMotifInt` enum values before implementing — the exact int assignments are at Claude's discretion (Phase 124 D-02). The family taxonomy from CONTEXT.md D-08 is the canonical grouping.

---

## No Analog Found

None — all files have strong analogs.

---

## Metadata

**Analog search scope:** `app/routers/`, `app/services/`, `app/repositories/`, `app/schemas/`, `frontend/src/components/library/`, `frontend/src/components/charts/`, `frontend/src/lib/`, `frontend/src/hooks/`, `frontend/src/api/`
**Files scanned:** 18 source files read directly; additional grep searches across the full codebase
**Pattern extraction date:** 2026-06-18
