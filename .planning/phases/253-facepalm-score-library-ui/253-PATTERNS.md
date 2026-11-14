# Phase 253: Facepalm Score in the Library UI - Pattern Map

**Mapped:** 2026-11-14
**Files analyzed:** 20 (3 new, 17 modified, plus test fixtures)
**Analogs found:** 20 / 20 (all analogs are git-tracked source)

The phase is a clone of the tactic depth filter plus a SeverityBadge extension. Every new piece has a direct
in-repo template; RESEARCH.md Patterns 1-4 give the target shapes. This file pins the exact source excerpts.

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `app/repositories/library_repository.py` (constants, `facepalm_range_active`, `_facepalm_clause`, params on `build_flaw_filter_clauses` / `flaw_exists_from_table` / `query_flaws` / `query_filtered_games`, `_build_flaw_item`) | repository | CRUD (read filter) | same file: `_TACTIC_DEPTH_FULL_MIN/MAX` (77-79), `_tactic_controls_active` (292-314), `build_flaw_filter_clauses` (585-690) | exact |
| `app/repositories/query_utils.py` (`apply_game_filters` gate) | utility (shared filter) | CRUD | same function, tactic gate lines 395-425 | exact |
| `app/routers/library.py` (2 endpoints) | router | request-response | `min_tactic_depth`/`max_tactic_depth` params lines 73-74 and ~321-322 | exact |
| `app/services/library_service.py` (`get_library_games`, `get_library_flaws`) | service | request-response passthrough | tactic depth kwargs at 931-932/990-991 and 1276-1277/1327-1328 | exact |
| `app/schemas/library.py` (`FlawListItem` ~172) | schema | transform | existing optional fields on `FlawListItem` | exact |
| `frontend/src/lib/facepalm.ts` (new) | utility | transform | `frontend/src/lib/tacticDepth.ts` | exact |
| `frontend/src/components/filters/FacepalmFilter.tsx` (new) | component | event-driven | `frontend/src/components/filters/TacticDepthFilter.tsx` | exact |
| `frontend/src/components/filters/PresetRangeFilter.tsx` (add `hint?`) | component | presentational | itself (lines 23-55 props, 113-126 slider block) | exact |
| `frontend/src/components/filters/FlawFilterControl.tsx` | component | event-driven | its Gem/Great section (~552-588) and TacticDepthFilter mount (~590-597) | exact |
| `frontend/src/hooks/useFlawFilterStore.ts` | store | state | `tacticDepthMin/Max` (5, 31-36, 52-53, 81-82) | exact |
| `frontend/src/hooks/useLibrary.ts` | hook | request-response | `depthParam` in `useLibraryGames` (161-169) and `useLibraryFlaws` (~337) | exact |
| `frontend/src/api/client.ts` | API client | request-response | `min_tactic_depth` in `getGames` (502, 524) and `getFlaws` (615, 635) | exact |
| `frontend/src/types/library.ts` (`FlawListItem` ~239) | type | — | sibling nullable fields | exact |
| `frontend/src/lib/analytics.ts` | config (registry) | — | `'tactic-depth'` in `FILTER_TARGETS` (428-446) / `FilterChangeProps` (469-484) | exact |
| `frontend/src/components/library/SeverityBadge.tsx` | component | presentational | itself | exact |
| `frontend/src/components/library/FacepalmBadgePopover.tsx` (new) | component | event-driven (popover) | `frontend/src/components/ui/metric-info-popover.tsx` + pointer guard from `ui/tooltip.tsx` (38-60) + grace close from `library/TagChip.tsx` | role-match |
| `frontend/src/components/library/FlawCard.tsx` (`tagsRow` 350-355) | component | presentational | itself | exact |
| `frontend/src/pages/library/GamesTab.tsx`, `FlawsTab.tsx` (2 sites each) | page | event-driven | existing `tacticDepth` / `onTacticDepthChange` props at each `FlawFilterControl` site | exact |
| Tests: `tests/test_library_repository.py`, `tests/repositories/test_library_repository.py`, `tests/test_query_utils.py`, `tests/test_library_router.py`, `frontend/src/lib/__tests__/facepalm.test.ts` (new), SeverityBadge / FlawFilterControl / useFlawFilterStore / FlawCard / FlawsTab tests | test | — | `test_depth_filter_narrows_games_without_family` (tests/test_library_repository.py:428), `frontend/src/lib/__tests__/tacticDepth.test.ts` | exact |

## Pattern Assignments

### `app/repositories/library_repository.py` (repository, CRUD)

**Constants analog** (lines 75-79):
```python
# Domain constants for the tactic depth range.
# These mirror DEPTH_MIN / DEPTH_MAX in frontend/src/lib/tacticDepth.ts and are
# used by _tactic_controls_active to detect the "full-range = no depth filter" state.
_TACTIC_DEPTH_FULL_MIN: int = 0
_TACTIC_DEPTH_FULL_MAX: int = 11
```
Add `_FACEPALM_PCT_FULL_MIN = 0`, `_FACEPALM_PCT_FULL_MAX = 100`, `_FACEPALM_PCT_SCALE = 100.0` with a "mirrors frontend/src/lib/facepalm.ts" comment.

**Activity predicate analog** (lines 292-314, `_tactic_controls_active`):
```python
    min_active = min_tactic_depth is not None and min_tactic_depth != _TACTIC_DEPTH_FULL_MIN
    max_active = max_tactic_depth is not None and max_tactic_depth != _TACTIC_DEPTH_FULL_MAX
    depth_active = min_active or max_active
```
`facepalm_range_active(min_pct, max_pct)` is public (no underscore) because `query_utils.py` lazy-imports it. Use RESEARCH.md Pattern 1 code verbatim for it and `_facepalm_clause` (compare REAL column against Python float thresholds; never `floor()`/`* 100` in SQL).

**Clause append analog** (end of `build_flaw_filter_clauses`, ~680-688):
```python
    tactic_clause = _build_tactic_clause(
        tactic_families, orientation, min_tactic_depth, max_tactic_depth, decided_lost
    )
    if tactic_clause is not None:
        clauses.append(tactic_clause)

    return clauses
```
Add `facepalm_clause = _facepalm_clause(min_facepalm_pct, max_facepalm_pct)` + append, separate from the tactic clause (not gated by `decided_lost`). New params go at the END of the signature (after `decided_lost`) or keyword-only; existing callers (`flaw_exists_from_table` ~741, `query_flaws` ~1110) pass positionally (Pitfall 2). Document them in the Args docstring in the same style as `min_tactic_depth / max_tactic_depth`.

**Item builder:** `_build_flaw_item` (~908): add `facepalm_score=flaw.facepalm_score`.

---

### `app/repositories/query_utils.py` (shared filter utility)

**Analog** (lines 399-425):
```python
    tactic_active = _tactic_controls_active(
        resolved_families, orientation, min_tactic_depth, max_tactic_depth
    )
    if flaw_severity or flaw_tags or tactic_active:
        if user_id is None:
            # Message intentionally omits variable values to preserve Sentry grouping
            raise ValueError("flaw/tactic filter requires user_id for EXISTS scoping")
        ...
        exists_pred = flaw_exists_from_table(
            user_id=user_id,
            severity=severities,
            tags=tag_list,
            tactic_families=families_seq,
            orientation=orientation,
            min_tactic_depth=min_tactic_depth,
            max_tactic_depth=max_tactic_depth,
        )
        stmt = stmt.where(exists_pred)
```
Add `facepalm_active = facepalm_range_active(...)` (lazy import, same place `_tactic_controls_active` is imported), OR it into the gate (Pitfall 1), forward both kwargs. Keep the ValueError message unchanged.

---

### `app/routers/library.py` (router, request-response)

**Analog** (lines 73-74, repeat at ~321-322; forwards at 116-117 and 362-363):
```python
    min_tactic_depth: int | None = Query(default=None, ge=0, le=11),
    max_tactic_depth: int | None = Query(default=None, ge=0, le=11),
```
Add `min_facepalm_pct` / `max_facepalm_pct` with `ge=0, le=100` (consider module constants for 0/100). Only the two list endpoints; not stats/comparison/coverage.

### `app/services/library_service.py` (service passthrough)
Copy how `min_tactic_depth`/`max_tactic_depth` are declared and forwarded in `get_library_games` (931-932 / 990-991) and `get_library_flaws` (1276-1277 / 1327-1328). Do not touch `library_service.py:520/540` (`tactic_slot_visible`).

### `app/schemas/library.py`
`FlawListItem`: `facepalm_score: float | None = None` (raw 0..1).

---

### `frontend/src/lib/facepalm.ts` (new, utility)

**Analog:** `frontend/src/lib/tacticDepth.ts`. Copy structure: header doc comment, `// ─── Named constants` block, `DEFAULT_PRESET as const`, `Preset` union type, `Value` interface, `PRESET_RANGES` / `PRESET_LABELS` / `PRESET_ORDER`, `DEFAULT_..._VALUE`, then `derivePreset`, `presetToRange`, `sliderToRange`, `formatSummary`, `toQueryParams`.

```ts
export const PRESET_RANGES: Record<TacticDepthPreset, TacticDepthValue> = {
  low: { min: 0, max: 1 },
  medium: { min: 0, max: 5 },
  high: { min: DEPTH_MIN, max: DEPTH_MAX },
};
export const PRESET_ORDER: TacticDepthPreset[] = ['low', 'medium', 'high'];
export const DEFAULT_TACTIC_DEPTH_VALUE: TacticDepthValue = PRESET_RANGES[DEPTH_DEFAULT_PRESET];

export function derivePreset(min: number, max: number): TacticDepthPreset | null {
  for (const preset of PRESET_ORDER) {
    const r = PRESET_RANGES[preset];
    if (r.min === min && r.max === max) return preset;
  }
  return null;
}

export function sliderToRange(lo: number, hi: number): TacticDepthValue {
  return {
    min: Math.max(DEPTH_MIN, Math.min(lo, hi)),
    max: Math.min(DEPTH_MAX, Math.max(lo, hi)),
  };
}

export function formatDepthSummary(value: TacticDepthValue): string {
  const lo = toDisplayDepth(value.min);
  const hi = toDisplayDepth(value.max);
  const range = value.min === value.max ? `${lo}` : `${lo}-${hi}`;
  const preset = derivePreset(value.min, value.max);
  return preset ? `${PRESET_LABELS[preset]}: ${range}` : range;
}
```
Deltas: presets `all|low|mid|high`, default `all`; summary upper bound via `displayUpper(hi)` (25 -> 29, 100 -> 100), giving `Low: 0-29%`; `facepalmToQueryParams` returns `{}` at default (unlike `depthToQueryParams`, which always sends); add `toFacepalmPct` (floor) and `isFacepalmNarrowed`. See RESEARCH.md Pattern 2 sketch. Knip: only export what is imported.

---

### `frontend/src/components/filters/FacepalmFilter.tsx` (new, component)

**Analog:** `frontend/src/components/filters/TacticDepthFilter.tsx` (full file). Copy verbatim structure:
```tsx
const PRESETS: PresetOption[] = PRESET_ORDER.map((preset) => ({ key: preset, label: PRESET_LABELS[preset] }));

export function TacticDepthFilter({ value, onChange }: TacticDepthFilterProps) {
  const activePreset = derivePreset(value.min, value.max);
  const trackCommit = useDebouncedTrackFeature('filter-change');
  const handleSliderChange = useCallback((values: number[]) => { ... onChange(sliderToRange(lo, hi)); }, [onChange]);
  const handleSliderCommit = useCallback((values: number[]) => {
      ...
      trackCommit({ target: 'tactic-depth', value: derivePreset(range.min, range.max) ?? 'custom' });
    }, [trackCommit]);
  const handlePreset = useCallback((preset: string) => {
      const next = preset as TacticDepthPreset;
      onChange(presetToRange(next));
      if (next !== activePreset) {
        trackFeature('filter-change', { target: 'tactic-depth', value: next });
      }
    }, [onChange, activePreset]);
  const isSummaryActive = activePreset !== DEPTH_DEFAULT_PRESET;

  return (
    <PresetRangeFilter
      label="Tactic Depth"
      testIdPrefix="filter-tactic-depth"
      infoAriaLabel="Tactic depth filter info"
      infoChildren={<p>...</p>}
      presets={PRESETS}
      gridClassName="grid-cols-3"
      ...
      slider={{ min: DEPTH_MIN, max: DEPTH_MAX, step: DEPTH_STEP, minStepsBetweenThumbs: 0,
        value: [value.min, value.max], onValueChange: handleSliderChange,
        onValueCommit: handleSliderCommit, thumbLabels: ['Minimum tactic depth', 'Maximum tactic depth'] }}
    />
  );
}
```
Deltas: `label="Facepalm"`, `testIdPrefix="filter-facepalm"`, `gridClassName="grid-cols-4"`, target `'facepalm'`, D-19 copy as two `<p>`, `hint={narrowed ? 'Mistakes are excluded' : undefined}`.

### `frontend/src/components/filters/PresetRangeFilter.tsx` (add hint slot)
Props interface lines 23-55; slider block lines ~113-126 (`<div className="px-1.5"><Slider .../></div>` is the last child of the root `<div data-testid={testIdPrefix}>`). Add optional `hint?: string` to the interface and destructure, render after the slider div:
`{hint && <p className="mt-1 text-sm text-muted-foreground" data-testid={`${testIdPrefix}-hint`}>{hint}</p>}`. Existing callers unaffected.

### `frontend/src/components/filters/FlawFilterControl.tsx`
Insert between the severity block's closing `</div>` (~549) and the `{/* ── Gem / Great toggles` comment (~552). Gate on the opt-in handler like Gem/Great (`{onFacepalmChange && (...)}`), not on `showTactics` (comment at ~557-560 explains why). Mount style mirrors:
```tsx
      {showTactics && (
        <TacticDepthFilter
          value={tacticDepth}
          onChange={onTacticDepthChange ?? (() => undefined)}
        />
      )}
```
Add `facepalm?: FacepalmValue` / `onFacepalmChange?` props with doc comments matching the `tacticDepth` prop docs (~70-90), and update the section-order doc comment (~454).

### `frontend/src/hooks/useFlawFilterStore.ts`
Mirror lines 5, 31-36 (field docs), 52-53 (defaults), 81-82:
```ts
    (filter.tacticDepthMin ?? DEFAULT_TACTIC_DEPTH_VALUE.min) !== DEFAULT_TACTIC_DEPTH_VALUE.min ||
    (filter.tacticDepthMax ?? DEFAULT_TACTIC_DEPTH_VALUE.max) !== DEFAULT_TACTIC_DEPTH_VALUE.max ||
```
Add `facepalmMin` / `facepalmMax` with the same `??` guard (Pitfall 7).

### `frontend/src/hooks/useLibrary.ts`
Analog (161-169):
```ts
  const depthParam = depthToQueryParams(flawFilter.tacticDepthMin, flawFilter.tacticDepthMax);
    queryKey: ['library-games', params, tacticFamily, tacticOrientation, depthParam, offset, limit],
        ...depthParam,
```
Add `facepalmParam = facepalmToQueryParams({min: flawFilter.facepalmMin ?? ..., max: ...})` in both `useLibraryGames` and `useLibraryFlaws`, in queryKey and spread.

### `frontend/src/api/client.ts`
Analog (`getGames` 502-503 / 524-525, `getFlaws` 615-616 / 635-636):
```ts
    min_tactic_depth?: number;
    max_tactic_depth?: number;
        ...(params.min_tactic_depth != null ? { min_tactic_depth: params.min_tactic_depth } : {}),
        ...(params.max_tactic_depth != null ? { max_tactic_depth: params.max_tactic_depth } : {}),
```

### `frontend/src/lib/analytics.ts`
Add `'facepalm'` next to `'tactic-depth'` in `FILTER_TARGETS` and `| { target: 'facepalm'; value: FacepalmPreset | 'custom' }` in `FilterChangeProps`, mirroring the tactic-depth union member.

---

### `frontend/src/components/library/SeverityBadge.tsx` (component)

Current render body (keep as the unscored path byte-identical):
```tsx
  const interactive = Boolean(onHover || onActivate);
  return (
    <span
      role={onActivate ? 'button' : undefined}
      ...
      className={cn(
        'inline-flex items-center gap-1 rounded-full border px-2 py-0.5 whitespace-nowrap',
        interactive && 'transition-all hover:-translate-y-px',
        ...
      )}
      style={{ color: SEV_COLORS[severity], backgroundColor: highlighted ? HIGHLIGHT_BG(...) : SEV_BG_COLORS[severity], ... }}
      aria-label={showCount ? `${count} ${severity}s` : SEVERITY_LABELS_SINGULAR[severity]}
      data-testid={`severity-${severity}-${gameId}`}
      ...
    >
      {showCount && <span className="text-base font-bold">{count}</span>}
      <span className="text-sm font-bold">
        {showCount ? SEVERITY_LABELS[severity] : SEVERITY_LABELS_SINGULAR[severity]}
      </span>
    </span>
  );
```
Add optional `facepalmScore?: number | null` and `ply?: number` props (JSDoc in the same style as `onActivate`). When `severity === 'blunder' && facepalmScore != null`: treat as `interactive` (lift + highlight), append `<TreePalm className="h-3.5 w-3.5" aria-hidden />` and `{pct}%` inside the `text-sm font-bold` content, and wrap the span in `FacepalmBadgePopover`. Keep inner `data-testid={`severity-blunder-${gameId}`}`. Highlight state (`HIGHLIGHT_BG`) is the existing hover treatment to reuse. Do not touch `TrainPuzzleCard` (second call site).

### `frontend/src/components/library/FacepalmBadgePopover.tsx` (new)

**Primary analog:** `frontend/src/components/ui/metric-info-popover.tsx` (full file): `useTrackedPopoverOpen(testId)`, `HOVER_OPEN_DELAY_MS = 100`, unmount timer cleanup, `PopoverPrimitive.Root open/onOpenChange`, `Trigger asChild`, `Portal` + `Content side="top" sideOffset={4}` with content `onMouseEnter` clearing the timer and identical Content classes:
```tsx
          className={cn(
            'z-50 max-w-xs rounded-md border-0 outline-none bg-foreground px-3 py-1.5 text-xs text-background',
            'data-[state=open]:animate-in data-[state=open]:fade-in-0 data-[state=open]:zoom-in-95',
            'data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=closed]:zoom-out-95',
            'data-[side=bottom]:slide-in-from-top-2 data-[side=left]:slide-in-from-right-2',
            'data-[side=right]:slide-in-from-left-2 data-[side=top]:slide-in-from-bottom-2',
          )}
```
**Pointer-type guard analog:** `frontend/src/components/ui/tooltip.tsx` 38-60:
```tsx
  const lastPointerType = React.useRef<string>("")
  const trackPointer = (e: React.PointerEvent) => { lastPointerType.current = e.pointerType }
  const handleOpenChange = (next: boolean) => {
    if (next && lastPointerType.current && lastPointerType.current !== "mouse") { return }
    setOpen(next)
  }
```
(Here: use it only to restrict hover-open to mouse; tap must still open via the Radix click toggle.)
**Grace close + `onCloseAutoFocus` prevent:** `frontend/src/components/library/TagChip.tsx` (80ms grace, comment on lingering focus ring).
Deltas per RESEARCH.md Pattern 4: real `<button type="button">` trigger, focus-open only when not preceded by pointerdown, `onOpenAutoFocus`/`onCloseAutoFocus` preventDefault, testId `facepalm-badge-${gameId}-${ply}` (numeric only), aria-label `Blunder, Facepalm N%`, body `<p className="font-bold">Facepalm {pct}%</p>` + D-18 copy.

### `frontend/src/components/library/FlawCard.tsx`
`tagsRow` (350-355): add `facepalmScore={flaw.facepalm_score}` and `ply={flaw.ply}` to the existing `<SeverityBadge severity count={1} gameId showCount={false} />`. `tagsRow` renders twice (mobile/desktop), tests need `getAllByTestId` (Pitfall 6).

### `GamesTab.tsx` / `FlawsTab.tsx`
At each of the two `FlawFilterControl` sites per file (~353/~536 and ~336/~557), pass `facepalm` + `onFacepalmChange` exactly the way `tacticDepth` / `onTacticDepthChange` are passed there (pending filter object update).

## Shared Patterns

### Full range = no clause / no param
Source: `_tactic_controls_active` (library_repository.py 292-314) and `isFlawFilterNonDefault` (useFlawFilterStore.ts 81-82). Apply to backend predicate, query params, filter dot.

### Single shared flaw predicate
Source: `build_flaw_filter_clauses` -> used by `query_flaws` and `flaw_exists_from_table` -> `apply_game_filters`. Apply: score clause added once there; no per-endpoint clause; not in stats/comparison/count functions.

### Sentry-safe errors
Source: query_utils.py `raise ValueError("flaw/tactic filter requires user_id for EXISTS scoping")`. No variables in messages.

### Umami
`useDebouncedTrackFeature('filter-change')` for slider commit, `trackFeature` on preset change only, `useTrackedPopoverOpen(testId)` for the badge popover; values are preset keys or `'custom'`; testIds numeric-only beyond the static prefix.

### Theme / testids
Colors only from `@/lib/theme` (`SEV_BLUNDER*` already in SeverityBadge); `data-testid` on every interactive element; `text-sm` floor except popover bodies (`text-xs` allowed, per metric-info-popover header comment).

## No Analog Found

| File | Role | Data Flow | Reason |
|---|---|---|---|
| (keyboard-focus-open part of `FacepalmBadgePopover`) | component | event-driven | No existing popover opens on keyboard focus; use RESEARCH.md Pattern 4 items 3-5 |

## Metadata

**Analog search scope:** `app/repositories`, `app/routers`, `app/services`, `app/schemas`, `frontend/src/{lib,components/filters,components/library,components/ui,hooks,api}`
**Files scanned:** ~15 read directly, remainder verified via RESEARCH.md line references and grep
**Pattern extraction date:** 2026-11-14
