# Phase 175: Board & Filter — Gem/Great Consumption - Pattern Map

**Mapped:** 2026-07-16
**Files analyzed:** 15 (new + modified)
**Analogs found:** 15 / 15

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|--------------------|------|-----------|-----------------|----------------|
| `app/services/best_move_candidates.py` (add `best_move_tier_sql`, `_es_sql`) | service | transform | `app/services/canonical_slice_sql.py:704-708` (sigmoid) + `classify_best_move` (same file, lines ~126-157) | role-match (Python→SQL twin of a sibling function) |
| `app/repositories/library_repository.py` (add `fetch_page_best_moves`) | repository | batch/CRUD | `fetch_page_eval_positions` (same file, ~1163-1194) | exact |
| `app/repositories/library_repository.py` (add `best_move_exists_from_table`) | repository | CRUD (correlated EXISTS) | `flaw_exists_from_table` (same file, 677-751) | exact |
| `app/repositories/query_utils.py` (`apply_game_filters` extend `has_gem`/`has_great`) | repository | request-response | existing `flaw_severity`/`tactic_families` params in the same function | exact |
| `app/services/library_service.py` (`_build_eval_series` extend) | service | transform | same function's existing per-position loop (assembles `EvalPoint`) | exact |
| `app/schemas/library.py` (`EvalPoint` extend) | model (Pydantic schema) | request-response | same file's existing `EvalPoint`/`FlawMarker` fields | exact |
| `app/routers/library.py` (`GET /library/games` add `has_gem`/`has_great`) | route | request-response | existing `rated: bool \| None` Query param, same endpoint | exact |
| `frontend/src/lib/theme.ts` (add `GREAT_ACCENT`) | config | — | `MAIA_ACCENT` (line 74) | exact |
| `frontend/src/lib/greatGlyph.ts` (new) | utility | transform | `frontend/src/lib/gemGlyph.ts` | exact |
| `frontend/src/components/icons/GreatMoveIcon.tsx` (new) | component | — | `frontend/src/components/icons/GemIcon.tsx` | exact |
| `frontend/src/lib/gemMove.ts` (add `classifyGreat`, `GREAT_MAIA_MAX_PROB`) | utility | transform | `classifyGem`/`GEM_MAIA_MAX_PROB` (same file, lines 35-56) | exact |
| `frontend/src/components/board/boardMarkers.tsx` (`SquareMarker.great` branch) | component | request-response (render) | `marker.book` branch (lines 143-158), which itself mirrors `marker.gem` (126-141) | exact |
| `frontend/src/components/analysis/GemMoveBadge.tsx` → new `GreatMoveBadge.tsx` (or extend) | component | request-response (render) | `GemMoveBadge.tsx` itself | exact |
| `frontend/src/components/analysis/UnifiedMovePopover.tsx` (add `isGreat` prop) | component | request-response (render) | same file's existing `isGem` prop | exact |
| `frontend/src/components/analysis/VariationTree.tsx` (add `great*` fields) | component | request-response (render) | same file's existing gem fields / `resolveMarkerIcon` | exact |
| `frontend/src/lib/moveQuality.ts` (add `'great'` to `MoveQuality`) | utility | transform | existing `'gem'` case in `colorForQuality`/`bucketKeyForQuality` (lines ~191-192, 212) | exact |
| `frontend/src/types/library.ts` (`EvalPoint` extend) | model (TS interface) | request-response | same file's existing `EvalPoint` (104-118) | exact |
| `frontend/src/hooks/useGemSweep.ts` (demote to fallback-only + WR-06 fix) | hook | event-driven | itself (no better analog; this is a modification, not new) | n/a (modify in place) |
| `frontend/src/pages/Analysis.tsx` (gate `gemC1`/`gemGrading`/sweep on "no stored row"; switch mainline reads to `EvalPoint.best_move_tier`) | component | event-driven + request-response | itself (modification) | n/a (modify in place) |
| `frontend/src/hooks/useFlawFilterStore.ts` (`FlawFilterState.hasGem`/`hasGreat`) | store | request-response | existing `severity`/`tacticFamilies` fields (lines 9-45) | exact |
| `frontend/src/components/filters/FlawFilterControl.tsx` (new "Best Moves" toggle section) | component | request-response | existing `SeverityFilterButton` + `handleSeverityToggle` pattern (lines 215-244, 388-393) | exact |
| `frontend/src/hooks/useLibrary.ts` (`buildLibraryParams` add `has_gem`/`has_great`) | hook | request-response | existing `severity`/`rated` param threading | role-match |
| `frontend/src/api/client.ts` (`libraryApi.getGames` add params) | service (API client) | request-response | existing `rated`/`severity` query-param wiring | role-match |

## Pattern Assignments

### `app/services/best_move_candidates.py` — `best_move_tier_sql` + `_es_sql` (service, transform)

**Analog:** `classify_best_move` (same file, ~126-157) for the math; `app/services/canonical_slice_sql.py:704-708` for the raw-SQL sigmoid precedent.

**Existing constants to import, never re-declare** (`best_move_candidates.py:34-36`):
```python
GEM_MAIA_MAX_PROB: float = 0.20
GREAT_MAIA_MAX_PROB: float = 0.50
```

**Core pattern — RESEARCH.md's exact recommended construction** (net-new but fully precedented; use verbatim as starting point):
```python
from sqlalchemy import case, func, literal
from sqlalchemy.sql.elements import ColumnElement

from app.services.eval_utils import LICHESS_K
from app.services.flaws_service import MATE_CP_EQUIVALENT, MISTAKE_DROP


def _es_sql(cp_col: Any, mate_col: Any, user_color_col: Any) -> ColumnElement[float | None]:
    """SQL twin of _eval_to_expected_score's Option-B mate mapping + Lichess sigmoid."""
    sign = case((user_color_col == "white", 1.0), else_=-1.0)
    mate_cp_equiv = case((mate_col > 0, float(MATE_CP_EQUIVALENT)), else_=-float(MATE_CP_EQUIVALENT))
    return case(
        (mate_col.isnot(None), 1.0 / (1.0 + func.exp(-LICHESS_K * sign * mate_cp_equiv))),
        (cp_col.isnot(None), 1.0 / (1.0 + func.exp(-LICHESS_K * sign * cp_col))),
        else_=literal(None),
    )


def best_move_tier_sql(
    maia_prob_col: Any,
    best_cp_col: Any, best_mate_col: Any,
    second_cp_col: Any, second_mate_col: Any,
    user_color_col: Any,
) -> ColumnElement[str | None]:
    """SQL twin of classify_best_move. Must stay consistent — see docstring
    discipline used for is_decided_lost / decided_lost_sql elsewhere."""
    best_es = _es_sql(best_cp_col, best_mate_col, user_color_col)
    second_es = _es_sql(second_cp_col, second_mate_col, user_color_col)
    return case(
        (best_es.is_(None), literal(None)),
        (second_es.is_(None), literal(None)),
        ((best_es - second_es) < MISTAKE_DROP, literal(None)),
        (maia_prob_col <= GEM_MAIA_MAX_PROB, literal("gem")),
        (maia_prob_col <= GREAT_MAIA_MAX_PROB, literal("great")),
        else_=literal(None),
    )
```
**Sigmoid raw-SQL precedent** (do NOT copy this style — it hardcodes the literal `0.00368208` instead of importing `LICHESS_K`; cited only to show the pattern is tolerated in this codebase):
`app/services/canonical_slice_sql.py:704-708, 800-801, 816-817`.

**Naming-consistency pattern to imitate:** `decided_lost_sql` / `is_decided_lost` (Python + SQL twin pair) — find and copy the cross-reference-comment discipline those two use for keeping in sync.

---

### `app/repositories/library_repository.py` — `fetch_page_best_moves` (repository, batch)

**Analog:** `fetch_page_eval_positions` (same file, lines 1163-1194).

**Core pattern** (from RESEARCH.md Pattern 1, verified against the analog's batching shape):
```python
async def fetch_page_best_moves(
    session: AsyncSession,
    game_ids: Sequence[int],
) -> dict[int, dict[int, GameBestMove]]:
    """Batch-load GameBestMove rows for the given games, grouped by game_id then ply.
    No user_id scoping — game_best_moves has no user_id column; IDOR is not a
    concern because callers already scope game_ids to the authenticated user's
    own games before calling this (mirrors fetch_page_eval_positions)."""
    if not game_ids:
        return {}
    stmt = select(GameBestMove).where(GameBestMove.game_id.in_(game_ids))
    rows = list((await session.execute(stmt)).scalars().all())
    result: dict[int, dict[int, GameBestMove]] = {gid: {} for gid in game_ids}
    for row in rows:
        result[row.game_id][row.ply] = row
    return result
```

---

### `app/repositories/library_repository.py` — `best_move_exists_from_table` (repository, CRUD/EXISTS)

**Analog:** `flaw_exists_from_table` (same file, lines 677-751) — read in full above.

**Imports pattern** (from the analog): `from sqlalchemy import exists, select, true`, `from sqlalchemy.sql.elements import ColumnElement`.

**Auth/scoping pattern to copy exactly** (lines 744-749 of the analog):
```python
return exists(
    select(GameFlaw.ply)
    .where(
        GameFlaw.game_id == Game.id,
        GameFlaw.user_id == user_id,
        player_only_gate(GameFlaw.ply, Game.user_color),  # D-04 player gate
        *clauses,
    )
)
```

**Twin for `game_best_moves`** (no `user_id` column on this table — RESEARCH.md's V4 access-control note: IDOR safety comes ENTIRELY from `Game.id` correlation to an already user-scoped outer query, not from a `user_id` column here):
```python
def best_move_exists_from_table(tiers: Sequence[Literal["gem", "great"]]) -> ColumnElement[bool]:
    if not tiers:
        return true()
    tier_expr = best_move_tier_sql(
        GameBestMove.maia_prob,
        GameBestMove.best_cp, GameBestMove.best_mate,
        GameBestMove.second_cp, GameBestMove.second_mate,
        Game.user_color,
    )
    return exists(
        select(GameBestMove.ply)
        .where(
            GameBestMove.game_id == Game.id,
            player_only_gate(GameBestMove.ply, Game.user_color),  # D-04 user-scoping
            tier_expr.in_(tiers),
        )
    )
```
**No-filter sentinel:** copy `flaw_exists_from_table`'s `if not clauses: return true()` — matches "no filter = match all games."

---

### `app/repositories/query_utils.py` — `apply_game_filters` extension (repository, request-response)

**Analog:** the function's own existing `flaw_severity: Sequence[str] | None = None` and `tactic_families` kwargs (lines 106-108) plus their downstream use inside the function body.

**Signature addition pattern** (mirror the existing kwarg style exactly — keyword-only, `Sequence[...] | None = None` default):
```python
has_gem: bool | None = None,
has_great: bool | None = None,
```
Build a `tiers: list[Literal["gem", "great"]]` list from the two booleans before calling `best_move_exists_from_table(tiers)`, then `stmt = stmt.where(best_move_exists_from_table(tiers))` alongside the existing flaw/tactic composition — never a parallel filter path (D-05a, CLAUDE.md "Shared Query Filters").

**Ply-parity helper already available, reuse verbatim:** `player_only_gate(ply_col, user_color_col)` (lines 74-91, same file) — do not re-derive `ply % 2` anywhere new.

---

### `app/schemas/library.py` — `EvalPoint` extension (model, request-response)

**Analog:** the schema's own existing fields (lines 32-46).

**Exact snippet to add** (from RESEARCH.md Code Examples, verified consistent with CONTEXT D-03/D-03a and Pitfall 3/5 semantics):
```python
best_move_tier: Literal["gem", "great"] | None = None
maia_prob: float | None = None
```
Both fields null unless a stored row classifies as gem/great (never populate `maia_prob` for a "neither" ply — Pitfall 5).

---

### `app/services/library_service.py` — `_build_eval_series` extension (service, transform)

**Analog:** the function's own existing per-position loop (assembles other `EvalPoint` fields from `GamePosition` rows) plus `classify_best_move`/`mover_color_for_ply` imports already exported from `best_move_candidates.py`.

**Core pattern** (RESEARCH.md Pattern 2, use verbatim):
```python
from app.services.best_move_candidates import classify_best_move, mover_color_for_ply

best_row = best_moves_by_ply.get(pos.ply)
best_move_tier: Literal["gem", "great"] | None = None
maia_prob_out: float | None = None
if best_row is not None:
    tier = classify_best_move(
        best_row.maia_prob,
        best_row.best_cp, best_row.best_mate,
        best_row.second_cp, best_row.second_mate,
        mover_color_for_ply(pos.ply),
    )
    if tier != "neither":
        best_move_tier = tier
        maia_prob_out = best_row.maia_prob  # only set alongside a real tier (Pitfall 5)
```

---

### `app/routers/library.py` — `has_gem`/`has_great` Query params (route, request-response)

**Analog:** the existing `rated: bool | None = Query(default=None)` param on the same `GET /library/games` endpoint.

**Pattern:**
```python
has_gem: bool | None = Query(default=None),
has_great: bool | None = Query(default=None),
```
Thread straight through to `library_service.get_library_games(..., has_gem=has_gem, has_great=has_great, ...)` — no transformation at the router layer (router stays thin, per CLAUDE.md "Router Convention").

---

### Frontend: `frontend/src/lib/theme.ts` — `GREAT_ACCENT` (config)

**Analog** (line 74):
```typescript
export const MAIA_ACCENT = 'oklch(0.58 0.20 290)'; // violet
```
Add a sibling constant using the same `oklch(...)` format, blue hue, next to `MAIA_ACCENT`. Never hard-code the hex/oklch value elsewhere (theme.ts rule, CLAUDE.md Frontend section).

---

### Frontend: `frontend/src/lib/greatGlyph.ts` (new) — mirrors `gemGlyph.ts` verbatim

**Analog** (full file, `frontend/src/lib/gemGlyph.ts`):
```typescript
import { MAIA_ACCENT } from '@/lib/theme';

export const GEM_GLYPH: { color: string } = {
  color: MAIA_ACCENT,
};
```
**New file:**
```typescript
import { GREAT_ACCENT } from '@/lib/theme';

export const GREAT_GLYPH: { color: string } = {
  color: GREAT_ACCENT,
};
```
Keep the same "one record, two consumers" docstring rationale (plain module, not the icon component file, for react-refresh's component-only-export rule).

---

### Frontend: `frontend/src/components/icons/GreatMoveIcon.tsx` (new) — mirrors `GemIcon.tsx`

**Analog** (full file, `frontend/src/components/icons/GemIcon.tsx`, reproduced above in full). Key structure to clone:
- `GemIconProps` shape (`className?`, `style?`, `'aria-hidden'?`) — copy identically as `GreatMoveIconProps`.
- `<svg viewBox="0 0 24 24">` wrapper, `<title>` for a11y (`<title>Great move</title>`), `<circle fill={GREAT_GLYPH.color}>`.
- D-02 says the inner glyph is a custom SVG (blue circle + white "!"), NOT a lucide icon this time (unlike `Gem` from lucide-react) — draw the exclamation mark as inline SVG paths (`<line>`/`<circle>` for the dot, or a `<text>` element), since chess.com's "Great Move" glyph has no direct lucide equivalent. Keep the same `stroke="#fff"` white-on-color convention the Gem icon uses.

---

### Frontend: `frontend/src/lib/gemMove.ts` — add `classifyGreat` + `GREAT_MAIA_MAX_PROB` (utility, transform)

**Analog:** `classifyGem` + `GEM_MAIA_MAX_PROB` (same file, lines 35-56, reproduced above in full).

**Pattern to clone** — a great move requires the SAME C2 (only-good-move) gate as gem, but the probability falls in `(GEM_MAIA_MAX_PROB, GREAT_MAIA_MAX_PROB]` rather than `<= GEM_MAIA_MAX_PROB`:
```typescript
// Cross-reference: mirrors app/services/best_move_candidates.py's
// GREAT_MAIA_MAX_PROB = 0.50. Fallback-only (D-03c) — the stored path never
// calls this. If the backend constant changes, update here too (Pitfall 4).
export const GREAT_MAIA_MAX_PROB = 0.5;

export function classifyGreat(params: {
  maiaProbability: number | null;
  playedIsBest: boolean;
  bestEs: number | null;
  secondBestEs: number | null;
}): boolean {
  const { maiaProbability, playedIsBest, bestEs, secondBestEs } = params;
  if (maiaProbability === null) return false;
  if (maiaProbability <= GEM_MAIA_MAX_PROB || maiaProbability > GREAT_MAIA_MAX_PROB) return false;
  if (!playedIsBest || bestEs === null || secondBestEs === null) return false;
  return bestEs - secondBestEs >= MISTAKE_DROP;
}
```
Add the same cross-reference comment to `GEM_MAIA_MAX_PROB` retroactively if not already present (Pitfall 4 — discoverability via grep for a future retune).

---

### Frontend: `frontend/src/components/board/boardMarkers.tsx` — `SquareMarker.great` branch

**Analog:** `marker.book` branch (lines 143-158), itself cloned from `marker.gem` (126-141) — both reproduced above in full.

**Interface addition:**
```typescript
export interface SquareMarker {
  square: string;
  severity?: FlawSeverity;
  gem?: boolean;
  great?: boolean;  // NEW — mirrors `book`'s addition exactly, mutually exclusive by construction
  book?: boolean;
  label?: string;
  labelColor?: string;
}
```

**Render branch** (copy `marker.book`'s shape, swap the icon/glyph):
```typescript
if (marker.great) {
  // Same ratio as gem/book — reused verbatim (UI-SPEC: no new geometry constant).
  const iconSize = 2 * r * GEM_ICON_DIAMETER_RATIO;
  return (
    <g>
      <circle cx={cx} cy={cy} r={r} fill={GREAT_GLYPH.color} stroke={MARKER_STROKE} strokeWidth={1} />
      {/* GreatMoveIcon-equivalent inline SVG: white "!" on the circle, matching
          GreatMoveIcon.tsx's markup so the two never drift */}
    </g>
  );
}
```
Order matters: place the `great` branch before or after `gem`/`book` consistently (existing order is `gem` → `book` → severity fallback) — insert `great` in the same tier, e.g. immediately after `gem`.

---

### Frontend: `frontend/src/components/analysis/GemMoveBadge.tsx` → `GreatMoveBadge.tsx` (or add `tier` prop)

**Analog:** `GemMoveBadge.tsx` (full file — read separately if extending inline vs. cloning as sibling; not re-read here since the icon/glyph pattern above already establishes the shape). Recommend a `tier: 'gem' | 'great'` prop on the existing component rather than a full duplicate file, to avoid drift between two badge components — but CONTEXT.md's canonical refs list it as a sibling file target, so either approach satisfies D-02b as long as both surfaces render.

---

### Frontend: `frontend/src/components/analysis/UnifiedMovePopover.tsx` — add `isGreat` prop

**Analog:** the file's existing `isGem` prop (same pattern: boolean prop gating a badge + popover copy line). Mirror the existing `isGem`-gated JSX block, swapping in `GreatMoveIcon`/`GREAT_GLYPH` and per D-02 popover copy (Claude's Discretion — keep in the copy-minimalism style per project memory: WHAT + sign convention only, no jargon).

---

### Frontend: `frontend/src/components/analysis/VariationTree.tsx` — add `great*` fields

**Analog:** the file's existing gem fields on `MoveNode` and `resolveMarkerIcon`'s gem branch — mirror the `SquareMarker.great` addition pattern from `boardMarkers.tsx` above (same mutually-exclusive shape).

---

### Frontend: `frontend/src/lib/moveQuality.ts` — add `'great'` to `MoveQuality` union

**Analog:** existing `'gem'` case in `colorForQuality`/`bucketKeyForQuality` (lines ~191-192, 212 per RESEARCH.md A1). Add a parallel case returning `GREAT_ACCENT` instead of `MAIA_ACCENT`.

---

### Frontend: `frontend/src/types/library.ts` — `EvalPoint` extension (model, request-response)

**Analog:** the interface's own existing fields (lines 104-118).

```typescript
best_move_tier: 'gem' | 'great' | null;
maia_prob: number | null;
```
Must mirror the backend Pydantic schema exactly (CLAUDE.md "Type safety" — no `any`, discriminated literal union not bare `string`).

---

### Frontend: `frontend/src/hooks/useFlawFilterStore.ts` — `FlawFilterState.hasGem`/`hasGreat`

**Analog:** existing `severity`/`tacticFamilies` fields (lines 9-45, reproduced above in the RESEARCH excerpt).

```typescript
export interface FlawFilterState {
  severity: ('blunder' | 'mistake')[];
  tags: FlawTag[];
  tacticFamilies: TacticFamily[];
  tacticOrientation: TacticOrientation;
  tacticDepthMin: number;
  tacticDepthMax: number;
  hasGem: boolean;   // NEW (FILT-01, D-05) — independent boolean, default false
  hasGreat: boolean; // NEW
}

export const DEFAULT_FLAW_FILTER: FlawFilterState = {
  severity: [], tags: [], tacticFamilies: [], tacticOrientation: 'either',
  tacticDepthMin: DEFAULT_TACTIC_DEPTH_VALUE.min, tacticDepthMax: DEFAULT_TACTIC_DEPTH_VALUE.max,
  hasGem: false, hasGreat: false,
};
```
Also gate `isFlawFilterNonDefault`: `filter.hasGem || filter.hasGreat || <existing checks>`.

---

### Frontend: `frontend/src/components/filters/FlawFilterControl.tsx` — new "Best Moves" toggle section (component)

**IMPORTANT CORRECTION (per RESEARCH.md):** the mirror target is `FlawFilterControl.tsx`, **NOT** `FilterPanel.tsx`/`MobileFilterDrawer.tsx` as CONTEXT.md's canonical refs literally state — `FilterPanel.tsx` has zero flaw/tactic code (game-metadata-only: time control, platform, rated, recency, opponent), and `MobileFilterDrawer.tsx` is generic drawer chrome with no filter content. `GamesTab.tsx` renders `FlawFilterControl` directly on both desktop (lines 325-349) and mobile (lines 503-527), independent of `LibraryFilterPanel`.

**Analog:** `SeverityFilterButton` + `handleSeverityToggle` (lines 215-244, 388-393).

```typescript
// Props addition
export interface FlawFilterControlProps {
  severity: ('blunder' | 'mistake')[];
  // ... existing props ...
  hasGem?: boolean;
  hasGreat?: boolean;
  onHasGemToggle?: () => void;
  onHasGreatToggle?: () => void;
}

// Toggle button — mirrors SeverityFilterButton's shape (rounded-full pill,
// colored when selected, glyph icon inline, data-testid + aria-label per
// CLAUDE.md Browser Automation Rules)
function BestMoveFilterButton({ label, icon, selected, onToggle, testId }: {...}) {
  return (
    <button
      type="button"
      data-testid={testId}
      aria-pressed={selected}
      aria-label={`Filter by ${label}`}
      onClick={onToggle}
      className={cn(/* selected ? colored : neutral, mirrors SeverityFilterButton */)}
    >
      {icon}
      {label}
    </button>
  );
}
```
Use `data-testid="filter-has-gem"` / `data-testid="filter-has-great"` (per Browser Automation Rules naming convention `filter-{name}`).

---

### Frontend: `frontend/src/hooks/useLibrary.ts` + `frontend/src/api/client.ts` — param threading

**Analog:** existing `severity`/`rated` query-param wiring in `buildLibraryParams` and `libraryApi.getGames`. Add `has_gem`/`has_great` as optional boolean params, following the exact same conditional-inclusion-in-URLSearchParams pattern already used for `rated`.

## Shared Patterns

### Ply-parity user-scoping (backend)
**Source:** `app/repositories/query_utils.py:74-91` (`player_only_gate` / `is_opponent_expr`)
**Apply to:** `best_move_exists_from_table` (new), and confirm `_build_eval_series`'s `mover_color_for_ply` (from `best_move_candidates.py`) agrees with the same parity convention — never re-derive `ply % 2` anywhere new (CLAUDE.md-documented history of an off-by-one bug here).

### Single authoritative classifier, SQL twin discipline
**Source:** `app/services/best_move_candidates.py`'s `classify_best_move`
**Apply to:** Both the board (`_build_eval_series` calls it directly in Python) and the filter (`best_move_tier_sql` is its SQL mirror). Any future threshold retune changes ONE module; comment cross-reference required in the SQL twin's docstring (same discipline as `decided_lost_sql`/`is_decided_lost`).

### "One record, two consumers" glyph pattern
**Source:** `frontend/src/lib/gemGlyph.ts` / `bookGlyph.ts`
**Apply to:** New `frontend/src/lib/greatGlyph.ts` — single color source consumed by both `GreatMoveIcon.tsx` and `boardMarkers.tsx`'s inline SVG, so they never drift.

### Additive mutually-exclusive marker field
**Source:** `frontend/src/components/board/boardMarkers.tsx`'s `SquareMarker.book` (added in Phase 172, itself mirroring `gem`)
**Apply to:** New `SquareMarker.great` field — same shape, same "mutually exclusive by construction, no runtime assertion" contract.

### Batched per-page repository read (no N+1)
**Source:** `fetch_page_eval_positions` (`app/repositories/library_repository.py:1163-1194`)
**Apply to:** New `fetch_page_best_moves` — identical `dict[int, dict[int, Row]]` grouping shape, called once per page from `get_library_game`/`get_library_games`.

### Correlated EXISTS filter composed via `apply_game_filters`
**Source:** `flaw_exists_from_table` (`app/repositories/library_repository.py:677-751`) + its wiring into `apply_game_filters` (`app/repositories/query_utils.py:94-`)
**Apply to:** New `best_move_exists_from_table`, wired the same way — never a parallel filter path (CLAUDE.md "Shared Query Filters": `apply_game_filters()` is the single implementation).

### Router param passthrough, thin router
**Source:** existing `rated: bool | None = Query(default=None)` on `GET /library/games`
**Apply to:** New `has_gem`/`has_great` Query params — no logic in the router, straight passthrough to the service layer.

## No Analog Found

None — every file in this phase has a direct, strong sibling analog already in the codebase (this phase is explicitly a "clone gem → great, clone flaw-filter → gem/great-filter" consumption phase per RESEARCH.md's Summary).

## Metadata

**Analog search scope:** `app/services/`, `app/repositories/`, `app/schemas/`, `app/routers/` (backend); `frontend/src/lib/`, `frontend/src/components/icons/`, `frontend/src/components/board/`, `frontend/src/components/analysis/`, `frontend/src/components/filters/`, `frontend/src/hooks/`, `frontend/src/types/`, `frontend/src/pages/` (frontend).
**Files scanned:** ~15 direct reads (analogs) + CONTEXT.md/RESEARCH.md's own extensive file:line citations, cross-checked against direct reads of `GemIcon.tsx`, `gemGlyph.ts`, `theme.ts`, `gemMove.ts`, `boardMarkers.tsx`, `FlawFilterControl.tsx`, `query_utils.py`, `library_repository.py` (`flaw_exists_from_table`), `best_move_candidates.py`.
**Pattern extraction date:** 2026-07-16
