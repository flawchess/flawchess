# Phase 129: Tactic Filter UI - Pattern Map

**Mapped:** 2026-06-20
**Files analyzed:** 13 (4 new, 9 modified)
**Analogs found:** 13 / 13 (every new/modified file has an in-repo twin)

> This phase is an **extension/clone** phase. Every new surface has an existing twin; the
> risk is divergence (re-implementing instead of cloning), not novelty. Excerpts below are
> the exact patterns to copy. Line numbers are verified against current source (2026-06-20).

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `frontend/src/lib/tacticDepth.ts` (NEW) | utility (filter-state lib) | transform | `frontend/src/lib/opponentStrength.ts` | exact (single-handle variant) |
| `frontend/src/components/filters/TacticDepthFilter.tsx` (NEW) | component (filter control) | request-response | `frontend/src/components/filters/OpponentStrengthFilter.tsx` | exact (single-handle variant) |
| `frontend/src/lib/__tests__/tacticDepth.test.ts` (NEW) | test | transform | `frontend/src/lib/__tests__/opponentStrength.test.ts` (if present) / existing lib tests | role-match |
| `frontend/src/hooks/useFlawFilterStore.ts` (MOD) | store | event-driven | self (extend in place) | exact |
| `frontend/src/components/filters/FlawFilterControl.tsx` (MOD) | component | request-response | "Played as" block in `FilterPanel.tsx:265-286` | exact (toggle clone) |
| `frontend/src/components/library/TacticMotifChip.tsx` (MOD) | component | transform | self (add `orientation` prop) | exact |
| `frontend/src/components/library/FlawCard.tsx` (MOD) | component | transform | self (dual-chip branch) | exact |
| `frontend/src/components/library/TacticComparisonGrid.tsx` (MOD) | component | request-response | self + `Endgames.tsx:390-397` accordion | exact |
| `frontend/src/types/library.ts` (MOD) | model (types) | transform | self (mirror backend schema) | exact |
| `app/repositories/query_utils.py` (MOD) | repository (filter) | CRUD/query | self (`:208-238` tactic clause) | exact |
| `app/repositories/library_repository.py` (MOD) | repository (filter+read) | CRUD/query | self (`:157-250`, `:122-135`) | exact |
| `app/schemas/library.py` (MOD) | model (schema) | request-response | self (`TacticBullet` `:362-382`) | exact |
| `app/services/library_service.py` + `app/routers/library.py` (MOD) | service + route | request-response | self (`_compute_tactic_bullets` `:1245-1327`) | exact |

---

## Shared Patterns

### Tactic-column resolver (closed-enum, never string interpolation)
**Source:** `app/repositories/library_repository.py:122-135`
**Apply to:** both filter sites + comparison fetch. T-128-05: never interpolate caller input into SQL.

The current resolver returns a `(motif_col, conf_col)` pair for one orientation:
```python
def _tactic_cols(orientation: TacticOrientation) -> tuple[Any, Any]:
    if orientation == "missed":
        return GameFlaw.missed_tactic_motif, GameFlaw.missed_tactic_confidence
    return GameFlaw.allowed_tactic_motif, GameFlaw.allowed_tactic_confidence
```
**Target (D-05/D-08):** RESEARCH recommends a sibling
`_tactic_orientation_pairs(orientation) -> list[tuple[motif_col, conf_col, depth_col]]`
returning **1 pair** for `missed`/`allowed` and **2 pairs** for `"either"`, so all three SQL
sites (`apply_game_filters`, `build_flaw_filter_clauses`, `fetch_tactic_comparison`) share one
helper. Add the depth column (`GameFlaw.missed_tactic_depth` / `allowed_tactic_depth`) to the
returned tuple so the depth clause uses the same resolver. Widen `TacticOrientation`
(`library_repository.py:49`) to `Literal["either", "missed", "allowed"]` — this single alias is
imported by `query_utils` (lazy) and `library_service`, so all three layers update at once.

### Orientation type alias (single source of truth)
**Source:** `app/repositories/library_repository.py:49`
```python
TacticOrientation = Literal["missed", "allowed"]
```
**Apply to:** widen to `Literal["either", "missed", "allowed"]`. Keep default `"allowed"` on
existing callers; Flaws/comparison callers pass `"either"` when the toggle is Either. Mirror the
same 3-value union in `frontend/src/types/library.ts` and `useFlawFilterStore.ts`.

### Confidence gate constant (reuse unchanged for both orientations)
**Source:** `app/repositories/library_repository.py:58`
```python
_TACTIC_CHIP_CONFIDENCE_MIN: int = 70  # 0-100 scale matching tactic_confidence column
```
**Apply to:** both orientations + the depth filter (D-08). Do NOT introduce a new threshold.
Note the **intentional asymmetry** (Pitfall 3): `build_flaw_filter_clauses` (Flaws list) gates on
confidence; `apply_game_filters` (Games EXISTS) does NOT. Preserve it unless deliberately fixing.

### Mate exemption set (reuse, do NOT add a new constant)
**Source:** `FAMILY_TO_MOTIF_INTS["mate"]` (`library_repository.py:85-95`)
**Apply to:** depth clause at every site. Depth bound is OR'd with the mate-membership escape so
mates always pass regardless of the slider (D-04):
```python
(depth_col <= max_tactic_depth) | motif_col.in_(FAMILY_TO_MOTIF_INTS["mate"])
```

### Beta gate (frontend render-time only)
**Source:** `FlawCard.tsx:278` / `TacticComparisonGrid.tsx` — `useUserProfile().data.beta_enabled`
**Apply to:** every new tactic UI surface, desktop AND mobile. Do NOT switch to
`useAuth().user.beta_enabled` (always null — project memory `frontend_beta_gating_source`).

### Theme tokens only (no new color)
**Source:** `frontend/src/lib/theme.ts` (`TAC_*` family colors added Phase 126)
**Apply to:** all new controls. D-10: the `missed:`/`allowed:` prefix is **text only** — chip color
stays the family color, no new orientation token.

### tsc -b at the shared-type boundary
**Apply to:** `types/library.ts` + `api/client.ts` changes. `npm run lint`/`npm test` strip types
(esbuild) and will NOT catch drift. Run `npx tsc -b` before integrating (project memory
`frontend_run_tsc_build`).

---

## Pattern Assignments

### `frontend/src/lib/tacticDepth.ts` (NEW — utility, transform)

**Analog:** `frontend/src/lib/opponentStrength.ts` (full file is the template; collapse the
two-bound range to a single `maxMoves: number | null`).

**Constants idiom** (`opponentStrength.ts:6-34`) — named constants + preset record + label record
+ order array:
```typescript
export const SLIDER_MIN = -200;
export const SLIDER_MAX = 200;
export const SLIDER_STEP = 50;
export const PRESET_RANGES: Record<OpponentStrengthPreset, OpponentStrengthRange> = { ... };
export const PRESET_LABELS: Record<OpponentStrengthPreset, string> = { ... };
export const PRESET_ORDER: OpponentStrengthPreset[] = ['any', 'stronger', 'similar', 'weaker'];
```
Mirror with the UI-SPEC constants (no magic numbers): `DEPTH_SLIDER_MIN=1`, `DEPTH_SLIDER_MAX=10`,
`DEPTH_SLIDER_STEP=1`, `DEPTH_PRESET_BEGINNER_MAX=2`, `DEPTH_PRESET_INTERMEDIATE_MAX=6`,
`DEPTH_PRESET_ADVANCED_MAX=null`, `DEPTH_DEFAULT_PRESET='intermediate'`.

**`derivePreset` idiom** (`opponentStrength.ts:40-46`) — match value to a preset or return null:
```typescript
export function derivePreset(range: OpponentStrengthRange): OpponentStrengthPreset | null {
  for (const preset of PRESET_ORDER) {
    const r = PRESET_RANGES[preset];
    if (r.min === range.min && r.max === range.max) return preset;
  }
  return null;
}
```
Single-handle version: `derivePreset(maxMoves: number | null)` returns `'advanced'` when
`maxMoves === null`, else matches `BEGINNER_MAX`/`INTERMEDIATE_MAX`, else `null` (custom).

**Slider <-> value conversion** (`opponentStrength.ts:57-69`) — extreme endpoint maps to `null`:
```typescript
export function sliderToRange(lo: number, hi: number): OpponentStrengthRange {
  return { min: lo <= SLIDER_MIN ? null : lo, max: hi >= SLIDER_MAX ? null : hi };
}
export function rangeToSlider(range: OpponentStrengthRange): [number, number] {
  return [range.min ?? SLIDER_MIN, range.max ?? SLIDER_MAX];
}
```
Single-handle: `sliderToMax(v)` returns `null` when `v >= DEPTH_SLIDER_MAX` (= Advanced/no cap),
else `v`; `maxToSlider(maxMoves)` returns `maxMoves ?? DEPTH_SLIDER_MAX`.

**Summary formatter** (`opponentStrength.ts:87-94`) — preset name when one matches, else custom:
```typescript
export function formatRangeSummary(range: OpponentStrengthRange): string {
  const preset = derivePreset(range);
  if (preset) return PRESET_LABELS[preset];
  ...
}
```
Use the UI-SPEC Copywriting Contract strings: "Beginner (1 move)", "Intermediate (≤ 3 moves deep)",
"Advanced (all)", "Custom (≤ N moves)".

**Query-param builder** (`opponentStrength.ts:101-108`) — omit the param when unbounded:
```typescript
export function rangeToQueryParams(range): { opponent_gap_min?: number; opponent_gap_max?: number } {
  const params = {};
  if (range.min !== null) params.opponent_gap_min = range.min;
  if (range.max !== null) params.opponent_gap_max = range.max;
  return params;
}
```
Mirror as `depthToQueryParam(maxMoves) -> { max_tactic_depth?: number }` — omit when `null`
(Advanced = no cap). **A1 (locked in planning): the API param is in half-moves** (matches the
SmallInteger column 1:1); convert to "moves deep" labels in the frontend only.

---

### `frontend/src/components/filters/TacticDepthFilter.tsx` (NEW — component, request-response)

**Analog:** `frontend/src/components/filters/OpponentStrengthFilter.tsx` (full file).

**Imports + props** (`OpponentStrengthFilter.tsx:1-22`):
```typescript
import { useCallback } from 'react';
import { Slider } from '@/components/ui/slider';
import { InfoPopover } from '@/components/ui/info-popover';
import { cn } from '@/lib/utils';
// ... + named imports from '@/lib/opponentStrength'
interface OpponentStrengthFilterProps {
  value: OpponentStrengthRange;
  onChange: (next: OpponentStrengthRange) => void;
}
```

**Label + InfoPopover + summary header** (`OpponentStrengthFilter.tsx:45-90`):
```tsx
<div className="mb-1 flex items-center justify-between gap-2">
  <p className="text-sm text-muted-foreground">
    <span className="inline-flex items-center gap-1">
      Opponent Strength
      <InfoPopover ariaLabel="..." testId="filter-opponent-strength-info" side="bottom">
        {/* popover body */}
      </InfoPopover>
    </span>
  </p>
  <span
    className={cn('text-sm tabular-nums',
      activePreset && activePreset !== 'any' ? 'font-medium text-toggle-active' : 'text-muted-foreground')}
    data-testid="filter-opponent-strength-summary"
  >
    {formatRangeSummary(value)}
  </span>
</div>
```
Replace label with "Tactic Difficulty", testIds with `filter-tactic-depth-*`, and add the mate-exempt
sentence to the popover ("Forced mates always show, regardless of difficulty" — D-04). Summary goes
`text-toggle-active` when preset !== Intermediate (the depth-filter "non-default" rule, D-02).

**Preset chip grid** (`OpponentStrengthFilter.tsx:92-114`) — `aria-pressed`, `h-11 sm:h-7`, active class:
```tsx
<div className="mb-3 grid grid-cols-4 gap-1" data-testid="filter-opponent-strength-presets">
  {PRESET_ORDER.map((preset) => {
    const isActive = activePreset === preset;
    return (
      <button type="button" onClick={() => handlePreset(preset)}
        data-testid={`filter-opponent-strength-preset-${preset}`} aria-pressed={isActive}
        className={cn('rounded border h-11 sm:h-7 text-sm transition-colors',
          isActive
            ? 'border-toggle-active bg-toggle-active text-toggle-active-foreground'
            : 'border-border bg-inactive-bg text-muted-foreground pointer-fine:hover:bg-inactive-bg-hover pointer-fine:hover:text-foreground')}>
        {PRESET_LABELS[preset]}
      </button>
    );
  })}
</div>
```
**Change `grid-cols-4` → `grid-cols-3`** (Beginner/Intermediate/Advanced — UI-SPEC Spacing exception).

**Slider block** (`OpponentStrengthFilter.tsx:116-133`):
```tsx
<div className="px-1.5">
  <Slider min={SLIDER_MIN} max={SLIDER_MAX} step={SLIDER_STEP} minStepsBetweenThumbs={1}
    value={[sliderLo, sliderHi]} onValueChange={handleSliderChange}
    thumbLabels={['Minimum opponent Elo gap', 'Maximum opponent Elo gap']}
    data-testid="filter-opponent-strength-slider" />
  <div className="mt-1 flex justify-between text-sm tabular-nums text-muted-foreground">
    <span>≤−{Math.abs(SLIDER_MIN)}</span><span>0</span><span>≥+{SLIDER_MAX}</span>
  </div>
</div>
```
Single-handle: `value={[sliderValue]}`, single `thumbLabels={['Maximum tactic depth in moves']}`,
drop `minStepsBetweenThumbs`, ticks show `1` / `DEPTH_SLIDER_MAX`. `handleSliderChange` reads
`values[0]` only.

---

### `frontend/src/hooks/useFlawFilterStore.ts` (MOD — store, event-driven)

**Analog:** self. The module-level `useSyncExternalStore` pattern (`:48-88`) is unchanged — only the
state shape + default + non-default predicate grow.

**State shape** (`:7-22`) — add three fields:
```typescript
export interface FlawFilterState {
  severity: ('blunder' | 'mistake')[];
  tags: FlawTag[];
  tacticFamilies: TacticFamily[];
  // NEW (129):
  // tacticOrientation: 'either' | 'missed' | 'allowed';  default 'either'
  // tacticDepthPreset: TacticDepthPreset;                 default 'intermediate'
  // tacticDepthMax: number | null;                        default DEPTH_PRESET_INTERMEDIATE_MAX (6)
}
```

**Default** (`:24-28`):
```typescript
export const DEFAULT_FLAW_FILTER: FlawFilterState = {
  severity: [], tags: [], tacticFamilies: [],
  // tacticOrientation: 'either', tacticDepthPreset: 'intermediate', tacticDepthMax: DEPTH_PRESET_INTERMEDIATE_MAX,
};
```

**Non-default predicate** (`:38-46`) — CRITICAL (Pitfall 5): the depth filter is **always on**
(D-02), so "non-default" means *not Intermediate* / *not Either*, NOT *set*:
```typescript
export function isFlawFilterNonDefault(filter: FlawFilterState): boolean {
  return (
    filter.tags.length > 0 ||
    filter.severity.length === 1 ||
    (filter.tacticFamilies?.length ?? 0) > 0
    // NEW: || filter.tacticOrientation !== 'either' || filter.tacticDepthPreset !== 'intermediate'
  );
}
```
Note the existing optional-chaining defensiveness (`?.length ?? 0`) against partial persisted state —
new fields should default-guard the same way (`filter.tacticOrientation ?? 'either'`).

---

### `frontend/src/components/filters/FlawFilterControl.tsx` (MOD — component, request-response)

**Analog:** "Played as" block in `FilterPanel.tsx:265-286` (orientation toggle) + the new
`TacticDepthFilter` (depth section). Both new sections go above the Tactic Motif section, gated on the
existing `showTacticFilter` prop (renders automatically in the mobile drawer — no separate path).

**Orientation ToggleGroup** — clone `FilterPanel.tsx:266-286` verbatim with `either/missed/allowed`:
```tsx
<div>
  <p className="mb-1 text-sm text-muted-foreground">Played as</p>
  <ToggleGroup type="single" value={filters.playedAs}
    onValueChange={(v) => { if (!v) return; update({ playedAs: v as FilterState['playedAs'] }); }}
    variant="outline" size="sm" data-testid="filter-played-as" className="w-full">
    <ToggleGroupItem value="either" data-testid="filter-played-as-either" className="min-h-11 sm:min-h-0 flex-1 text-sm">Either</ToggleGroupItem>
    <ToggleGroupItem value="white" ...>White</ToggleGroupItem>
    <ToggleGroupItem value="black" ...>Black</ToggleGroupItem>
  </ToggleGroup>
</div>
```
The **`if (!v) return;` guard** is the deselect-prevention the interaction contract requires (D-06).
Relabel to "Orientation", values `either/missed/allowed`, testIds `filter-tactic-orientation-*`.

---

### `frontend/src/components/library/TacticMotifChip.tsx` (MOD — component, transform)

**Analog:** self. Add an optional `orientation?: 'missed' | 'allowed'` prop; label/aria/testid gain a
prefix. **LANDMINE (Pitfall 1):** do NOT re-add a per-chip definition popover — Phase 126 UAT removed
it; D-12 narration lives in the shared `<TagLegend>`. No new Popover/Radix import in this file.

**Current label/aria/testid** (`:91-92, 124`):
```tsx
aria-label={`Tactic: ${motif} — ${definition}`}
data-testid={`chip-tactic-${motif}-${flawId}`}
// ...
<Icon className="h-3 w-3 shrink-0" />
{motif}
```
**Target (D-10):** when `orientation` set →
label `` `${orientation}: ${motif}` ``,
aria-label `` `Tactic: ${orientation} ${motif} — ${definition}` `` (space, not colon, in aria),
testid `` `chip-tactic-${orientation}-${motif}-${flawId}` ``. The `text-xs font-bold` chip styling
(`:80`) is the documented exception — keep it; the prefix inherits it.

---

### `frontend/src/components/library/FlawCard.tsx` (MOD — component, transform)

**Analog:** self (`:278-298`). Today renders ONE chip and feeds `[flaw.allowed_tactic_motif]` to
`TagLegend`. Beta source `useUserProfile().data` is already correct.

**Target (D-11):** branch on `flawFilter.tacticOrientation` (threaded as a prop from `FlawsTab`,
keeping the card pure — A6): Missed → missed chip only; Allowed → allowed chip only; Either → both
when both non-null, one when one. Pass `orientation` to each chip AND prefix the orientation onto the
`TagLegend` motif list so the legend explains "missed: fork" / "allowed: fork". Apply to BOTH the
list-row card and the single-game card path (D-12 mobile parity — confirm the single-game render site
reuses `TacticMotifChip` the same way; Open Question 3).

---

### `frontend/src/components/library/TacticComparisonGrid.tsx` (MOD — component, request-response)

**Analog:** self (`TacticBulletRow` `:189-248`, `GridBody` `:261-280`) + `Endgames.tsx:390-397`
accordion. Self-fetch via `useTacticComparison` (no orientation — grid always shows both, D-09).

**Reuse `TacticBulletRow`** (`:189-248`) per bullet unchanged — it already renders label + delta +
popover + `MiniBulletChart` + zero-event placeholder. For two-bullets-per-card (D-13), render two
rows per family card with labels "Missed {Family}" / "Allowed {Family}"
(`text-sm text-muted-foreground` per UI-SPEC; do NOT extend the `font-medium` on the family label —
new rows are Regular 400). Group the (now ~12) bullets by `bullet.family`.

**Card structure** (`GridBody` `:261-280`) — one `Card` per family, but two `TacticBulletRow`s in the
body:
```tsx
<div data-testid="tactic-comparison-grid" className="grid grid-cols-1 lg:grid-cols-3 gap-4">
  {data.bullets.map((bullet) => (
    <Card key={bullet.family} data-testid={`tactic-family-card-${bullet.family}`}>
      <CardHeader>{familyName}</CardHeader>
      <CardBody className="space-y-3"><TacticBulletRow bullet={bullet} /></CardBody>
    </Card>
  ))}
</div>
```

**More Tactics accordion (D-14)** — clone `Endgames.tsx:390-397` exactly:
```tsx
<Accordion type="single" collapsible>
  <AccordionItem value="concepts" className="charcoal-texture rounded-md overflow-hidden border-none"
    data-testid="endgame-concepts-trigger">
    <AccordionTrigger band>
      <span className="flex items-center gap-2 flex-1">
        <h3 className="text-base font-semibold text-foreground">Endgame Statistics Concepts</h3>
      </span>
    </AccordionTrigger>
    <AccordionContent className="... p-4"> ... </AccordionContent>
  </AccordionItem>
</Accordion>
```
Relabel to "More Tactics", testid `tactic-grid-more-tactics`, and render the overflow families with
the **same `FamilyCard` renderer** as the top-6 (no compact variant — CONTEXT discretion). Top-6
selection is server-side by Missed rate; the grid renders server order (no client re-sort, matching
the existing `GridBody` comment `:256-260`).

---

### `frontend/src/types/library.ts` (MOD — model, transform) — SHARED-TYPE BOUNDARY

**Analog:** self. `FlawListItem`/`FlawMarker` already expose both `allowed_*`/`missed_*` motif fields;
`TacticBullet`/`TacticComparisonResponse` mirror the backend. **Target:** mirror the locked backend
schema choice — RESEARCH recommends **option A: add `orientation: 'missed' | 'allowed'` to
`TacticBullet`** and return up to 12 bullets. Add the 3-value `tacticOrientation` union and the depth
filter types. **Run `npx tsc -b` after editing** (lint/test do not type-check).

---

### `app/repositories/query_utils.py` (MOD — repository, query) — Games-EXISTS filter site

**Analog:** self (`:208-238`). Current tactic clause resolves one column pair and adds a correlated
EXISTS (no confidence gate here — intentional, Pitfall 3):
```python
motif_col, _conf_col = _tactic_cols(orientation)
tactic_exists = _exists(
    _select(_GameFlaw.ply).where(
        _GameFlaw.game_id == Game.id,
        _GameFlaw.user_id == user_id,
        motif_col.in_(motif_ints),
    )
)
stmt = stmt.where(tactic_exists)
```
**Target (D-05/D-08):** widen `orientation` to 3 values; add `max_tactic_depth: int | None = None`
kwarg; for `"either"` build `or_(missed_pred, allowed_pred)` where each branch is
`motif_col.in_(ints) & ((depth_col <= max_tactic_depth) | motif_col.in_(FAMILY_TO_MOTIF_INTS["mate"]))`.
Resolve all pairs via the shared `_tactic_orientation_pairs` helper. Keep the correlated-EXISTS shape.

---

### `app/repositories/library_repository.py` (MOD — repository, query) — Flaws-list filter site + read

**Analog:** self (`build_flaw_filter_clauses` `:157-250`, tactic clause `:244-248`). This site DOES
gate confidence:
```python
if tactic_families:
    motif_ints = [m for fam in tactic_families for m in FAMILY_TO_MOTIF_INTS.get(fam, [])]
    if motif_ints:
        motif_col, conf_col = _tactic_cols(orientation)
        clauses.append(motif_col.in_(motif_ints) & (conf_col >= _TACTIC_CHIP_CONFIDENCE_MIN))
```
**Target:** widen `orientation`; thread `max_tactic_depth` from `query_flaws` (`:378` signature has
`orientation` but no depth param) into the clause; for `"either"` build the OR-across-both-column-sets
clause with the depth+mate escape on each branch, preserving the `conf_col >= _TACTIC_CHIP_CONFIDENCE_MIN`
gate. **Read path** (`:519-547`, `FlawListItem` rows) likely needs NO change — both motif fields come
back; client (`FlawCard`) decides which chip(s) to render (D-11 client-side, A4).

---

### `app/schemas/library.py` (MOD — model, request-response)

**Analog:** self (`TacticBullet` `:362-382`, `TacticComparisonResponse` `:385-398`). **Target
(option A):** add `orientation: Literal["missed", "allowed"]` to `TacticBullet`; the response returns
up to 12 bullets (6 families × 2). Minimal churn — reuses the entire existing CI machinery. The
frontend groups by `family`.

---

### `app/services/library_service.py` + `app/routers/library.py` (MOD — service + route)

**Analog:** self. `_compute_tactic_bullets` (`:1245-1327`) computes per-family deltas/CI for ONE
orientation, ranks via `_sort_key`, caps at 6:
```python
def _sort_key(b: TacticBullet) -> tuple[int, float, int]:
    is_sig = b.ci_low is not None and b.ci_high is not None and (b.ci_low > 0 or b.ci_high < 0)
    abs_delta = abs(b.delta) if b.delta is not None else 0.0
    volume = max(b.you_events, b.opp_events)
    return (0 if is_sig else 1, -abs_delta, -volume)
bullets.sort(key=_sort_key)
return bullets[:6]
```
**Target (D-13/D-14, A3):** call the per-game fetch **twice** (once `"missed"`, once `"allowed"`),
run `_compute_tactic_bullets` per orientation, tag each bullet with its `orientation`. **Ranking
changes to top-6 families by Missed `you_rate` descending** (was: largest significant gap); align the
tie-break/volume fallback with `_sort_key` (Claude's discretion). Emit BOTH orientation bullets for
each selected family. Router needs NO new query param (grid always shows both, D-09); keep existing
game-metadata params. The service already early-gates on `analyzed_n < TACTIC_COMPARISON_GATE` before
the expensive query — both fetches are post-gate (acceptable cost).

---

## Query-threading note (TanStack — Pitfall 4)

**Source:** `api/client.ts:332-344` (`getFlaws` params) + `useLibrary.ts` `useLibraryFlaws` key.
`getFlaws` spreads filter params and conditionally includes `tactic_family`:
```typescript
...(params.tactic_family && params.tactic_family.length > 0 ? { tactic_family: params.tactic_family } : {}),
```
**Target:** add `tactic_orientation` + `max_tactic_depth` to the `getFlaws` params AND to the
`useLibraryFlaws` query key (append to the key array or fold into the params object) — otherwise
changing orientation/depth serves stale data. The comparison hook does NOT take orientation.

---

## No Analog Found

None. Every new/modified file has a direct in-repo twin (clone target or self-extension).

---

## Metadata

**Analog search scope:** `frontend/src/lib/`, `frontend/src/components/filters/`,
`frontend/src/components/library/`, `frontend/src/hooks/`, `frontend/src/api/`,
`frontend/src/types/`, `frontend/src/pages/`, `app/repositories/`, `app/schemas/`,
`app/services/`, `app/routers/`.
**Files read this session:** `opponentStrength.ts`, `OpponentStrengthFilter.tsx`,
`useFlawFilterStore.ts`, `TacticMotifChip.tsx`, `query_utils.py` (tactic clause),
`library_repository.py` (`_tactic_cols`, `build_flaw_filter_clauses`, alias, gate),
`FilterPanel.tsx` ("Played as"), `Endgames.tsx` (accordion), `schemas/library.py` (`TacticBullet`),
`library_service.py` (`_compute_tactic_bullets`), `TacticComparisonGrid.tsx`, `api/client.ts`
(`getFlaws`). Line numbers cross-checked against 129-RESEARCH.md (all VERIFIED).
**Pattern extraction date:** 2026-06-20
