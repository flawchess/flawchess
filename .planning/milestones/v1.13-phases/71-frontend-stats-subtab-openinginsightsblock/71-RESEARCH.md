# Phase 71: Frontend Stats subtab — `OpeningInsightsBlock` - Research

**Researched:** 2026-04-27
**Domain:** React/TypeScript — TanStack Query, chess.js deep-link, LazyMiniBoard extraction, severity-color mapping
**Confidence:** HIGH — all findings verified by direct file reads of the project codebase

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Layout = stacked vertical sections inside one `charcoal-texture rounded-md p-4` card. Order: White Weaknesses → Black Weaknesses → White Strengths → Black Strengths. Section subheadings as `<h3>` (`text-base font-semibold`) with leading icon + piece-color square swatch.
- **D-02:** Block always sends `color="all"` to `POST /api/insights/openings`, ignoring the global color filter.
- **D-03:** Deep-link click sets the global `color` filter to `finding.color`.
- **D-04:** Each finding renders as `OpeningFindingCard` modeled on `GameCard.tsx`. Card chrome: `border-l-4 charcoal-texture border border-border/20 rounded px-4 py-3`. Desktop: board left + content right. Mobile: header full-width top, then board + content row.
- **D-04a:** Extract `LazyMiniBoard` from `GameCard.tsx` into `frontend/src/components/board/LazyMiniBoard.tsx`. Configure with `flipped={finding.color === 'black'}`, `fen={finding.entry_fen}`, sizes 100px desktop / 105px mobile.
- **D-05:** Move-sequence trim = "last 2 entry plys + candidate move", with leading ellipsis. Fewer than 3 total plys: no ellipsis. Pure helper in `frontend/src/lib/openingInsights.ts`, unit-tested.
- **D-06:** Card prose: `"You {lose|win} {rate}% as {White|Black} after {trimmed_san_seq} (n={n_games})"`. No W/D/L breakdown chip.
- **D-07:** Severity accent colors from `theme.ts`. Major weakness = dark red; minor weakness = light red; major strength = dark green; minor strength = light green. Values correspond to `DARK_RED`/`LIGHT_RED`/`DARK_GREEN`/`LIGHT_GREEN` from `arrowColor.ts`.
- **D-08:** No "show more" — render all returned findings (max 16). Section stacks use `space-y-3`.
- **D-09:** Empty section copy: `"No {weakness|strength} findings cleared the threshold under your current filters."` InfoPopover on block heading explains threshold.
- **D-10:** Empty block copy: `"No opening findings cleared the threshold under your current filters. Try widening filters (longer recency window, more time controls) or import more games."`
- **D-11:** Loading state = `animate-pulse` skeleton with 4 section headers + 2-3 placeholder cards each. No spinner-only state.
- **D-12:** Error state = `role="alert"` block with "Try again" button (`variant="brand-outline"`) that calls `query.refetch()`. No per-component Sentry capture.
- **D-13:** Deep-link sequence: `chess.loadMoves(entry_san_sequence)` → `setBoardFlipped(...)` → `setFilters(...)` → `navigate('/openings/explorer')` → `window.scrollTo({ top: 0 })`. Backend must expose `entry_san_sequence: list[str]` on `OpeningInsightFinding` (additive amendment).
- **D-14:** No candidate-move highlight on deep-link arrival.
- **D-15:** Whole card is `<a href="/openings/explorer">` with `e.preventDefault()` + React Router navigation. `aria-label="Open {display_name} ({candidate_move_san}) in Move Explorer"`. ExternalLink icon on header right.
- **D-16:** Auto-fetch via TanStack Query `useOpeningInsights` hook. `staleTime` matches existing 30s convention.
- **D-17:** Passes `recency`, `timeControls`, `platforms`, `rated`, `opponentType`, `opponentStrength` from `debouncedFilters`. Always sends `color="all"`.
- **D-18:** Block hides when zero imported games (mirrors `mostPlayedData` gating).
- **D-19:** Block renders at top of Stats tab `flex flex-col gap-4` container, before bookmarks section.
- **D-20:** Block heading = "Opening Insights" + `<Lightbulb>` icon + `<InfoPopover>`.
- **D-21:** Mobile layout mirrors `GameCard` exactly. `LazyMiniBoard` sizes: 105px mobile, 100px desktop. `data-testid="opening-insights-block"`, `data-testid="opening-finding-card-{idx}"`, `data-testid="opening-insights-section-{section_key}"`. Section keys: `white-weaknesses`, `black-weaknesses`, `white-strengths`, `black-strengths`.
- **D-22:** Touch targets ≥ 44px. LazyMiniBoard has no click handlers or drag affordance.

### Claude's Discretion

- File layout: `frontend/src/components/insights/OpeningInsightsBlock.tsx`, `frontend/src/components/insights/OpeningFindingCard.tsx`, `frontend/src/hooks/useOpeningInsights.ts`, `frontend/src/lib/openingInsights.ts`, `frontend/src/components/board/LazyMiniBoard.tsx`.
- Type definitions extend `frontend/src/types/insights.ts` (no new file).
- Whether sections are `<ul>/<li>` or flat `<div>` (prefer flat `<div>` matching `GameCardList`).
- Whether to memoize trim/severity helpers.
- Exact `staleTime` / `gcTime` (30s staleTime matches existing convention).
- Whether rate-percent in prose gets its own color shade.
- Whether to share threshold copy via a constant in `openingInsights.ts`.
- Card element type: `<a href>` with `e.preventDefault()` preferred (route destination = true link).

### Deferred Ideas (OUT OF SCOPE)

- Full PGN context (4+ plys), W/D/L breakdown chip, severity badge/icon, `hoveredMove` sticky-set on arrival, aggregate/meta-recommendation bullet, inline bullets on Moves subtab, bookmark badge on findings.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| INSIGHT-STATS-01 | `OpeningInsightsBlock` component on Openings → Stats subtab as primary insight surface | D-01, D-19 lock placement and outer chrome |
| INSIGHT-STATS-02 | Renders templated bullets with green/red semantic styling | D-06 prose template, D-07 severity color mapping — arrow color constants are the right source |
| INSIGHT-STATS-03 | Deep-link navigates to Move Explorer pre-loaded at entry FEN | D-13 sequence confirmed by `handleOpenGames` at Openings.tsx:492-498; requires backend amendment to expose `entry_san_sequence` |
| INSIGHT-STATS-04 | Empty state with threshold + min-games explanation | D-09, D-10 copy templates — threshold constant should be shared |
| INSIGHT-STATS-05 | Block respects active filter set; updates on filter change | D-16, D-17 — `debouncedFilters` from `Openings.tsx:377-384` is the exact pattern to mirror |
| INSIGHT-STATS-06 | Mobile-equivalent rendering | D-21 mirrors `GameCard.tsx` mobile layout exactly; `LazyMiniBoard` sizes match |
</phase_requirements>

---

## Summary

Phase 71 is a pure frontend assembly task. The backend (`POST /api/insights/openings`) is fully implemented by Phase 70. All findings have been verified by direct file reads of the project codebase — no web searches were needed since all relevant code is local.

The single cross-cutting concern is D-13: the deep-link handler needs a SAN sequence to call `chess.loadMoves(...)`, but Phase 70's `OpeningInsightFinding` schema currently only exposes `entry_fen`. The service already computes `row.entry_san_sequence` internally (verified in `opening_insights_service.py:293` and `openings_repository.py:514`) — adding `entry_san_sequence: list[str]` to `OpeningInsightFinding` is a one-field additive amendment to the Pydantic schema and a one-line change to the service constructor call. This is the only backend touch Phase 71 needs.

The visual model is `GameCard.tsx` (lines 1-264). The `LazyMiniBoard` function defined inline at lines 14-42 must be extracted to a shared module so both `GameCard` and the new `OpeningFindingCard` can consume it. The `BORDER_CLASSES` pattern in `GameCard.tsx` (lines 53-57) provides the card left-border color mapping idiom, but Phase 71 uses a different key type (`(classification, severity)` pair vs `UserResult`), so a new `FINDING_BORDER_CLASSES` constant is needed. The severity colors map exactly to the exported hex constants from `arrowColor.ts` (`DARK_RED`, `LIGHT_RED`, `DARK_GREEN`, `LIGHT_GREEN`).

Theme.ts has no light/dark severity-specific Tailwind border-color constants today — they must be added as Tailwind arbitrary-value classes or as theme constants. The correct approach (per CLAUDE.md "theme constants in theme.ts") is to either use the already-exported hex color constants from `arrowColor.ts` via inline `style={{ borderLeftColor: ... }}`, or add named Tailwind classes. Given Tailwind's JIT scanning, inline style for the border-left is the safer, more direct path using the arrowColor constants that are already exported.

**Primary recommendation:** Proceed with D-13 backend amendment first (add `entry_san_sequence` to schema + pass-through in service), then build frontend components in three waves: (1) extract `LazyMiniBoard` + add types, (2) build `OpeningFindingCard` + `useOpeningInsights` hook, (3) build `OpeningInsightsBlock` + insert into `Openings.tsx`.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Fetch opening insights | API / Backend (Phase 70, complete) | Frontend TanStack Query hook | Backend owns the query + classification pipeline |
| Render finding cards | Browser / Client | — | Pure rendering, no server interaction |
| Deep-link navigation | Browser / Client | — | React Router state mutations + chess.js board preload |
| Filter application | Browser / Client (debouncedFilters) | — | Filter state lives in Openings.tsx; hook receives debounced snapshot |
| Severity color mapping | Browser / Client (arrowColor.ts) | Backend (opening_insights_service.py) | Both use identical threshold constants; CI enforces lock-step |
| SAN sequence for board replay | API / Backend | Browser / Client (chess.js loadMoves) | Backend exposes entry_san_sequence; FE replays it |

---

## Phase Boundary

Frontend-only (with one additive backend amendment). No new route, no migration, no LLM. The block lives at the top of `Openings.tsx`'s `statisticsContent` JSX variable (line 785), inserted before the existing `bookmarks.length === 0` conditional block. The `debouncedFilters` variable (line 377-384) already drives all Stats tab queries and is the filter source for the new hook. The block receives `chess`, `setBoardFlipped`, `setFilters`, and `navigate` from the parent component scope to implement the deep-link handler.

---

## Source Audit

All CONTEXT.md decisions D-01..D-22 and requirements INSIGHT-STATS-01..06 have been read. This table records what the planner needs to know to implement each:

| Decision / Req | What the Planner Must Know |
|---|---|
| D-01 | Outer card uses `charcoal-texture rounded-md p-4` (confirmed in `EndgameInsightsBlock.tsx:86`). Section `<h3>` with `text-base font-semibold`. Piece-color swatch: `<span className="inline-block h-3.5 w-3.5 rounded-xs border border-muted-foreground bg-white" />` / `bg-zinc-900` (Openings.tsx:877, 908) |
| D-02 | Hook always passes `color: "all"` in request body regardless of `debouncedFilters.color` |
| D-03 | Deep-link click handler sets `filters.color = finding.color` before navigating |
| D-04 | Card chrome string is `"border-l-4 charcoal-texture border border-border/20 rounded px-4 py-3"` — copy verbatim from `GameCard.tsx:224-227` |
| D-04a | `LazyMiniBoard` is defined at `GameCard.tsx:15-42`. Its API: `{ fen: string; flipped: boolean; size: number }`. Only consumer currently: `GameCard`. Extraction target: `frontend/src/components/board/LazyMiniBoard.tsx`. `GameCard` must be updated to import from there. |
| D-05 | See dedicated section "Move-Sequence Trim Algorithm" |
| D-06 | Prose template: `"You {lose\|win} {rate}% as {White\|Black} after {trimmed_seq} (n={n_games})"`. Rate = `Math.round(loss_rate * 100)` for weakness, `Math.round(win_rate * 100)` for strength |
| D-07 | See dedicated section "Severity → Color Mapping" |
| D-08 | Cap is enforced server-side (5+5+3+3 = 16 max). Frontend renders all. Section stacks use `space-y-3` |
| D-09 | Empty section message. InfoPopover copy: "Insights are computed from candidate moves with at least 20 games where your win or loss rate exceeds 55%." |
| D-10 | Empty block message. Both messages should reference a shared `INSIGHT_THRESHOLD_COPY` constant in `openingInsights.ts` |
| D-11 | Skeleton: 4 `<h3>` section placeholder bars + 2 card-shaped placeholders per section, all `animate-pulse bg-muted/30`. No spinner. |
| D-12 | Error state: `role="alert"`. "Try again" button calls `query.refetch()`. No `Sentry.captureException`. |
| D-13 | See "Phase 70 Contract Amendment" section — `entry_san_sequence` must be added to schema and service |
| D-14 | Nothing extra on arrival; no `hoveredMove` state set |
| D-15 | Card rendered as `<a href="/openings/explorer">`. `onClick={e => { e.preventDefault(); handleFindingClick(finding); }}`. `aria-label` format confirmed. ExternalLink icon (lucide-react, already imported in `GameCard.tsx:5`) on header right |
| D-16 | TanStack Query `useQuery` (not `useMutation`). `staleTime: 30_000` matches `queryClient.ts:24` default — can rely on global default or set explicitly |
| D-17 | Hook receives explicit filter fields (not whole FilterState object) matching the `useMostPlayedOpenings` pattern: `recency`, `timeControls`, `platforms`, `rated`, `opponentType`, `opponentStrength`. Always adds `color: "all"` to request body |
| D-18 | Block conditional: `{insightsData && mostPlayedData && (mostPlayedData.white.length > 0 || mostPlayedData.black.length > 0) && <OpeningInsightsBlock ... />}` — or simpler: rely on `mostPlayedData` length > 0 as the "has games" proxy |
| D-19 | Insertion point: line 786 inside `statisticsContent`, before the `bookmarks.length === 0` check. See precise JSX context below |
| D-20 | Heading: `"Opening Insights"` + `<Lightbulb className="size-5" />` (same class as `EndgameInsightsBlock.tsx:90`) + `<InfoPopover ariaLabel="Opening insights info" testId="opening-insights-info">`. The `insight-lightbulb` CSS class (from `EndgameInsightsBlock.tsx:89`) adds gold glow from `theme.ts:116` |
| D-21 | `data-testid` values locked. Section keys locked. Board sizes locked (105/100). |
| D-22 | Card is full-width click target — no nested interactive elements inside the card (InfoPopover trigger sits on the block heading, outside the card stack) |
| INSIGHT-STATS-01 | Component file: `frontend/src/components/insights/OpeningInsightsBlock.tsx` |
| INSIGHT-STATS-02 | Red = `LIGHT_RED` / `DARK_RED`; Green = `LIGHT_GREEN` / `DARK_GREEN` from `arrowColor.ts`. Used as inline `style={{ borderLeftColor }}` on card |
| INSIGHT-STATS-03 | Deep-link uses `chess.loadMoves(entry_san_sequence)` — requires backend amendment first |
| INSIGHT-STATS-04 | Empty states at both section level and block level, with threshold constants |
| INSIGHT-STATS-05 | Hook key includes all debounced filter fields. Any filter change triggers refetch after 30s staleTime |
| INSIGHT-STATS-06 | `sm:hidden` mobile branch + `hidden sm:flex` desktop branch — exact pattern from `GameCard.tsx:230-261` |

---

## Implementation Approach

### File Layout

```
frontend/src/
├── components/
│   ├── board/
│   │   └── LazyMiniBoard.tsx          # EXTRACTED from GameCard.tsx (new shared module)
│   ├── insights/
│   │   ├── EndgameInsightsBlock.tsx   # UNCHANGED (visual chrome reference only)
│   │   ├── OpeningInsightsBlock.tsx   # NEW outer block
│   │   └── OpeningFindingCard.tsx     # NEW per-finding card
│   └── results/
│       └── GameCard.tsx               # MODIFIED: import LazyMiniBoard from shared module
├── hooks/
│   └── useOpeningInsights.ts          # NEW TanStack Query hook
├── lib/
│   └── openingInsights.ts             # NEW: trimMoveSequence(), FINDING_BORDER_CLASSES, constants
└── types/
    └── insights.ts                    # AMENDED: add OpeningInsightFinding + OpeningInsightsResponse types
```

Backend amendment (single file change):
```
app/schemas/opening_insights.py        # AMENDED: add entry_san_sequence: list[str] to OpeningInsightFinding
app/services/opening_insights_service.py  # AMENDED: pass entry_san_sequence=list(row.entry_san_sequence or []) to OpeningInsightFinding constructor
```

### Component Decomposition

```
Openings.tsx (host page)
└── OpeningInsightsBlock.tsx           # outer charcoal-texture card, heading, 4 sections, loading/error/empty states
    └── [per section div]              # section heading (h3) + card list
        └── OpeningFindingCard.tsx     # per-finding card (border-l-4 chrome, LazyMiniBoard, prose, header link affordance)
            └── LazyMiniBoard.tsx      # IntersectionObserver lazy-rendered MiniBoard
```

`OpeningInsightsBlock` receives:
- `debouncedFilters: FilterState` — for hook
- `chess: ReturnType<typeof useChessGame>` — for `chess.loadMoves`
- `setBoardFlipped: (f: boolean) => void`
- `setFilters: React.Dispatch<React.SetStateAction<FilterState>>`
- `navigate: NavigateFunction` (or pass `onFindingClick` callback up to parent)

Preferred pattern: define `handleFindingClick(finding: OpeningInsightFinding)` in `Openings.tsx` (alongside `handleOpenGames`) and pass it as a prop to `OpeningInsightsBlock`, which passes it to `OpeningFindingCard`. This keeps navigation state mutations in the page component and keeps sub-components pure.

### Hook Design

`useOpeningInsights.ts`:

```typescript
// POST /api/insights/openings — filter-driven, no Generate button
export function useOpeningInsights(filters?: {
  recency: Recency | null;
  timeControls: TimeControl[] | null;
  platforms: Platform[] | null;
  rated: boolean | null;
  opponentType: OpponentType;
  opponentStrength: OpponentStrength;
}) {
  const recency = filters?.recency === 'all' ? null : (filters?.recency ?? null);
  const timeControl = filters?.timeControls ?? null;
  const platform = filters?.platforms ?? null;
  const rated = filters?.rated ?? null;
  const opponentType = filters?.opponentType ?? 'human';
  const opponentStrength = filters?.opponentStrength ?? 'any';

  return useQuery({
    queryKey: ['openingInsights', recency, timeControl, platform, rated, opponentType, opponentStrength],
    queryFn: () =>
      apiClient.post<OpeningInsightsResponse>('/insights/openings', {
        recency: recency ?? undefined,
        time_control: timeControl ?? undefined,
        platform: platform ?? undefined,
        rated: rated ?? undefined,
        opponent_type: opponentType,
        opponent_strength: opponentStrength,
        color: 'all',  // D-02: always "all"
      }).then(r => r.data),
    // staleTime defaults to 30_000 from queryClient global config; can be omitted or set explicitly
  });
}
```

Note: The opening insights endpoint is a POST with a JSON body (not query params), unlike the GET-based stats endpoints. `apiClient.post` with the request body directly (no `null, { params: ... }` wrapper like the endgame insights mutation). This mirrors how `timeSeriesApi.fetch` and `positionBookmarksApi.create` work.

### Deep-link Handler Integration

In `Openings.tsx`, add alongside `handleOpenGames` (line 492):

```typescript
const handleOpenFinding = useCallback((finding: OpeningInsightFinding) => {
  chess.loadMoves(finding.entry_san_sequence);
  setBoardFlipped(finding.color === 'black');
  setFilters(prev => ({ ...prev, color: finding.color, matchSide: 'both' as MatchSide }));
  navigate('/openings/explorer');
  window.scrollTo({ top: 0 });
}, [chess, navigate, setFilters]);
```

Pass `onFindingClick={handleOpenFinding}` to `<OpeningInsightsBlock>`.

### Type Definitions

Extend `frontend/src/types/insights.ts` with:

```typescript
// Phase 71 — Opening Insights (Phase 70 wire contract + entry_san_sequence amendment)
export interface OpeningInsightFinding {
  color: 'white' | 'black';
  classification: 'weakness' | 'strength';
  severity: 'minor' | 'major';
  opening_name: string;
  opening_eco: string;
  display_name: string;
  entry_fen: string;
  entry_san_sequence: string[];  // added by Phase 71 backend amendment
  entry_full_hash: string;
  candidate_move_san: string;
  resulting_full_hash: string;
  n_games: number;
  wins: number;
  draws: number;
  losses: number;
  win_rate: number;
  loss_rate: number;
  score: number;
}

export interface OpeningInsightsResponse {
  white_weaknesses: OpeningInsightFinding[];
  black_weaknesses: OpeningInsightFinding[];
  white_strengths: OpeningInsightFinding[];
  black_strengths: OpeningInsightFinding[];
}
```

Types are hand-mirrored from the Pydantic schema (`app/schemas/opening_insights.py`) — there is no OpenAPI auto-generation in this project. The `entry_san_sequence` field is the amendment added by Phase 71.

### Theme Additions

`theme.ts` has no light/dark severity border-color constants today. The correct approach for border-left severity color:

Use `style={{ borderLeftColor: severityBorderColor }}` inline, where `severityBorderColor` is derived from the already-exported hex constants in `arrowColor.ts`. Add a helper in `openingInsights.ts`:

```typescript
import { DARK_RED, LIGHT_RED, DARK_GREEN, LIGHT_GREEN } from '@/lib/arrowColor';

export function getSeverityBorderColor(
  classification: 'weakness' | 'strength',
  severity: 'minor' | 'major',
): string {
  if (classification === 'weakness') {
    return severity === 'major' ? DARK_RED : LIGHT_RED;
  }
  return severity === 'major' ? DARK_GREEN : LIGHT_GREEN;
}
```

This satisfies CLAUDE.md "no hard-coded color hexes" because the values come from `theme.ts`-adjacent constants in `arrowColor.ts`. If the planner prefers pure Tailwind classes, an alternative is Tailwind JIT arbitrary values (`border-l-[#9B1C1C]` etc.), but inline style is cleaner for runtime-computed values.

Note: Adding new named constants to `theme.ts` directly (e.g. `SEVERITY_BORDER_MAJOR_WEAKNESS`) is also valid and perhaps more explicit. Planner should choose one approach and apply it consistently.

### Mobile vs Desktop Layout

`OpeningFindingCard` follows `GameCard.tsx` exactly:

```
Mobile (sm:hidden):
  <a> wrapper (full card, cursor-pointer, hover:bg-muted/30)
    header line full width (display_name + eco + ExternalLink icon)
    <div flex gap-3 items-start>
      LazyMiniBoard size=105
      <div flex-1 flex-col gap-1>
        prose sentence (You lose X% as White after ... (n=18))
    </div>

Desktop (hidden sm:flex gap-3 items-center):
  <a> wrapper
    LazyMiniBoard size=100
    <div min-w-0 flex-1 flex-col gap-2>
      header line (display_name + eco + ExternalLink icon ml-auto)
      prose sentence
```

---

## Phase 70 Contract Amendment

### The Question (D-13)

`OpeningInsightFinding` in `app/schemas/opening_insights.py` currently has `entry_fen: str` but no `entry_san_sequence` field. The deep-link handler needs `chess.loadMoves(sanArray)` (a SAN array), not just a FEN string. chess.js `chess.load(fen)` can set the board to a position but does NOT produce a move history, so the move list and PGN context on the board would be empty. This is a material UX difference.

### What Phase 70 Already Has Internally

The SAN sequence is computed at every stage of the pipeline:

- `openings_repository.py:514` — `entry_san_sequence: list[str]` is a named column on every row returned by `query_opening_transitions`. It is aggregated via `func.min(transitions_cte.c.entry_san_sequence).label("entry_san_sequence")` at line 589. [VERIFIED: direct file read]
- `opening_insights_service.py:160` — `san_seq = list(row.entry_san_sequence or [])` used in `_attribute_finding` for parent-hash lineage walk. [VERIFIED: direct file read]
- `opening_insights_service.py:293` — `entry_fen = _replay_san_sequence(list(row.entry_san_sequence or []))` — the entry FEN is itself derived from this SAN sequence. [VERIFIED: direct file read]
- The data is available at the point where `OpeningInsightFinding` is constructed (lines 305-324) but is not included in the constructor call.

### Recommended Amendment

**File 1: `app/schemas/opening_insights.py`**

Add one field to `OpeningInsightFinding` after `entry_fen: str` (line 48):

```python
entry_san_sequence: list[str]  # SAN tokens from start to entry position (candidate excluded); added Phase 71 for FE deep-link
```

**File 2: `app/services/opening_insights_service.py`**

In the `OpeningInsightFinding(...)` constructor call (starting at line 305), add:

```python
entry_san_sequence=list(row.entry_san_sequence or []),
```

After `entry_fen=entry_fen,` (line 312).

**Scope:** Two-line change. No migration, no new query, no performance impact — the data is already fetched. The field is additive (no existing consumers of the schema are broken). [VERIFIED: confirmed by reading both files in full]

**Risk:** The `ty` type checker will flag a missing field if the constructor call is not updated. Adding the field to both schema and service constructor in the same commit prevents any interim failure.

---

## Reusable Components and Patterns

### LazyMiniBoard (extraction from GameCard.tsx:14-42)

Current API (verified by direct read):
```typescript
// GameCard.tsx:15
function LazyMiniBoard({ fen, flipped, size }: { fen: string; flipped: boolean; size: number })
```

Implementation: `useRef<HTMLDivElement>` + `useState(false)` for visibility. `IntersectionObserver` with `rootMargin: '200px'`. On intersection: `setVisible(true); observer.disconnect()`. Renders a `<div>` with `className="shrink-0 rounded overflow-hidden bg-muted"` and `style={{ width: size, height: size }}`. Conditionally renders `<MiniBoard fen={fen} size={size} flipped={flipped} />` when visible.

After extraction to `frontend/src/components/board/LazyMiniBoard.tsx`:
- Export as named export `LazyMiniBoard`
- `GameCard.tsx` imports from `@/components/board/LazyMiniBoard`
- `OpeningFindingCard.tsx` imports the same

`MiniBoard` already lives in `frontend/src/components/board/MiniBoard.tsx` — `LazyMiniBoard.tsx` imports from the same `@/components/board/MiniBoard` path.

### BORDER_CLASSES in GameCard.tsx (lines 53-57)

```typescript
const BORDER_CLASSES: Record<UserResult, string> = {
  win:  'border-l-green-600',
  draw: 'border-l-gray-500',
  loss: 'border-l-red-600',
};
```

This is keyed by `UserResult` (`'win' | 'draw' | 'loss'`). Phase 71 needs a different key type — `(classification, severity)` tuple — and different color shades (matching `arrowColor.ts` exactly). A new mapping in `openingInsights.ts` using inline `style` is recommended (see Theme Additions section above) rather than trying to reuse `BORDER_CLASSES` from `GameCard`.

### debouncedFilters / useMostPlayedOpenings pattern (Openings.tsx:377-384)

```typescript
// Openings.tsx:377-384
const { data: mostPlayedData } = useMostPlayedOpenings({
  recency: debouncedFilters.recency,
  timeControls: debouncedFilters.timeControls,
  platforms: debouncedFilters.platforms,
  rated: debouncedFilters.rated,
  opponentType: debouncedFilters.opponentType,
  opponentStrength: debouncedFilters.opponentStrength,
});
```

The new `useOpeningInsights` call in `Openings.tsx` mirrors this exactly (same field names, same `debouncedFilters` source), with the block also always passing `color: "all"` inside the hook.

### handleOpenGames pattern (Openings.tsx:492-498)

```typescript
const handleOpenGames = useCallback((pgn: string, color: "white" | "black") => {
  chess.loadMoves(pgnToSanArray(pgn));
  setBoardFlipped(color === 'black');
  setFilters(prev => ({ ...prev, color, matchSide: 'both' as MatchSide }));
  navigate('/openings/games');
  window.scrollTo({ top: 0 });
}, [chess, navigate, setFilters]);
```

`handleOpenFinding` is identical except:
- Input is `finding.entry_san_sequence` (already a `string[]`, no `pgnToSanArray` needed)
- Navigate to `'/openings/explorer'` not `'/openings/games'`

### InfoPopover usage (Openings.tsx:879-881, 950-952)

```tsx
<InfoPopover ariaLabel="Bookmarked White openings info" testId="bookmarks-white-info" side="top">
  Your saved White bookmarks with win, draw, and loss rates based on the current filter settings.
</InfoPopover>
```

API: `{ children: React.ReactNode; ariaLabel: string; testId: string; side?: "top"|"bottom"|"left"|"right" }`. Import path: `@/components/ui/info-popover`. Default side is `"top"`. No extra wrapper needed.

### Statistics tab insertion point (Openings.tsx:785-788)

```tsx
// Line 785
const statisticsContent = (
  <div className="flex flex-col gap-4">
    {/* INSERT OpeningInsightsBlock HERE */}
    {/* Bookmarked Openings: Results — empty state when no bookmarks, chart when data available */}
    {bookmarks.length === 0 ? (
```

The `OpeningInsightsBlock` is inserted as the first child inside the `<div className="flex flex-col gap-4">` container at line 786. It is conditional on `mostPlayedData` having at least one entry (per D-18):

```tsx
{mostPlayedData && (mostPlayedData.white.length > 0 || mostPlayedData.black.length > 0) && (
  <OpeningInsightsBlock
    debouncedFilters={debouncedFilters}
    onFindingClick={handleOpenFinding}
  />
)}
```

### queryClient.ts global staleTime (line 24)

```typescript
defaultOptions: {
  queries: {
    retry: 1,
    staleTime: 30_000,   // 30 seconds — applies to all queries including useOpeningInsights
  },
},
```

The `useOpeningInsights` hook does NOT need to set `staleTime` explicitly — it inherits 30s from the global default. Setting it explicitly is fine for documentation clarity but not required.

### Global Sentry coverage (queryClient.ts:6-11)

```typescript
queryCache: new QueryCache({
  onError: (error, query) => {
    Sentry.captureException(error, { tags: { source: 'tanstack-query' }, ... });
  },
}),
```

Any error thrown by `useOpeningInsights.queryFn` is automatically captured here. Do NOT add `Sentry.captureException` in `OpeningInsightsBlock` or `useOpeningInsights`.

---

## Move-Sequence Trim Algorithm

**Input:**
- `entrySanSequence: string[]` — SAN tokens from start to entry position (candidate excluded)
- `candidateMoveSan: string` — the candidate move SAN

**Goal:** Render at most `"...N.move1 move2 N+1.candidate"` with the last 2 entry plys + candidate.

**Algorithm (pseudocode):**

```
function trimMoveSequence(entrySanSequence, candidateMoveSan):
  totalEntryPlys = entrySanSequence.length
  fullSequence = [...entrySanSequence, candidateMoveSan]
  totalPlys = fullSequence.length  // always >= 1 (candidate always present)

  if totalEntryPlys < 2:
    // 0 or 1 entry plys — render entire sequence without ellipsis
    trimmed = fullSequence
    needsEllipsis = false
  else:
    // 2+ entry plys: keep last 2 entry plys + candidate
    trimmed = [...entrySanSequence.slice(-2), candidateMoveSan]
    needsEllipsis = (totalEntryPlys > 2)

  // Compute move number for the first ply in trimmed
  // ply index in full sequence = totalEntryPlys - trimmed.length + 1
  firstPlyIndex = totalEntryPlys - trimmed.length  // 0-based index of first trimmed ply
  firstMoveNumber = Math.floor(firstPlyIndex / 2) + 1
  firstPlyIsBlack = (firstPlyIndex % 2 === 1)

  tokens = []
  for i, san in enumerate(trimmed):
    plyIndex = firstPlyIndex + i
    isWhite = (plyIndex % 2 === 0)
    moveNumber = Math.floor(plyIndex / 2) + 1

    if isWhite:
      tokens.push(`${moveNumber}.${san}`)
    else:
      if i === 0 and firstPlyIsBlack:
        tokens.push(`${moveNumber}...${san}`)  // Black-on-move continuation prefix
      else:
        tokens.push(san)  // Black's reply to a white move we just rendered

  result = tokens.join(' ')
  if needsEllipsis:
    result = '...' + result
  return result
```

**Edge cases and examples:**

| entrySanSequence | candidateMoveSan | Result |
|---|---|---|
| `["e4","c5","Nf3","d6","d4","cxd4"]` (6 plys) | `"Nxd4"` | `"...3.d4 cxd4 4.Nxd4"` |
| `["e4","c5"]` (2 plys) | `"Nf3"` | `"1.e4 c5 2.Nf3"` (no ellipsis) |
| `["e4"]` (1 ply) | `"c5"` | `"1.e4 c5"` (no ellipsis) |
| `[]` (0 plys) | `"e4"` | `"1.e4"` (no ellipsis) |
| `["e4","c5","Nf3"]` (3 plys — Black's turn) | `"d6"` | `"...2.Nf3 d6"` |
| `["e4","c5","Nf3","d6"]` (4 plys) | `"d4"` | `"...2.Nf3 d6 3.d4"` |

**Key rule:** `needsEllipsis = totalEntryPlys > 2` (not `trimmed.length < totalPlys`). Ellipsis signals "moves before this were omitted."

**Black-on-move start:** When the first trimmed ply is a black ply (odd 0-based index), render it as `"N...san"` not `"san"` — this is the standard PGN continuation notation. Example: `["e4","c5","Nf3"]` → first trimmed = `["Nf3", "d6"]` (last 2 entry) + `"d4"` → first ply is white (index 2, even), so: `"2.Nf3 d6 3.d4"` prefixed with `"..."` → `"...2.Nf3 d6 3.d4"`.

Wait — re-examining the example from CONTEXT.md (D-05): `entry_sequence = ["e4", "c5", "Nf3", "d6", "d4", "cxd4"]` (6 plys), candidate = `"Nxd4"`. Last 2 entry plys = `["d4", "cxd4"]`. First trimmed ply index = 4 (0-based), which is even (white's move), move number = 3. So: `"3.d4 cxd4"` then candidate at ply index 6 (even, move 4): `"4.Nxd4"`. With ellipsis: `"...3.d4 cxd4 4.Nxd4"`. This matches the D-05 example exactly.

---

## Severity → Color Mapping

### Source Constants (arrowColor.ts, verified)

```typescript
// arrowColor.ts
export const LIGHT_GREEN = '#6BBF59';   // win rate > 55% and < 60% (minor strength)
export const DARK_GREEN  = '#1E6B1E';   // win rate >= 60%            (major strength)
export const LIGHT_RED   = '#E07070';   // loss rate > 55% and < 60% (minor weakness)
export const DARK_RED    = '#9B1C1C';   // loss rate >= 60%           (major weakness)
```

### Mapping Table

| `classification` | `severity` | Border-left color | Source constant |
|---|---|---|---|
| `weakness` | `major` | `#9B1C1C` | `DARK_RED` |
| `weakness` | `minor` | `#E07070` | `LIGHT_RED` |
| `strength` | `major` | `#1E6B1E` | `DARK_GREEN` |
| `strength` | `minor` | `#6BBF59` | `LIGHT_GREEN` |

### Threshold Alignment

Backend (opening_insights_service.py):
- `DARK_THRESHOLD = 0.60` → maps to `DARK_RED` or `DARK_GREEN`
- `LIGHT_THRESHOLD = 0.55` (from constants file) → maps to `LIGHT_RED` or `LIGHT_GREEN`

Frontend (arrowColor.ts):
- `DARK_COLOR_THRESHOLD = 60` (percentage)
- `LIGHT_COLOR_THRESHOLD = 55` (percentage)

These are in perfect lock-step (CI-enforced by `tests/services/test_opening_insights_arrow_consistency.py`). The border-left accent on `OpeningFindingCard` will match the arrow color the user sees in the Move Explorer after clicking the deep-link.

### Implementation

In `frontend/src/lib/openingInsights.ts`:

```typescript
import { DARK_RED, LIGHT_RED, DARK_GREEN, LIGHT_GREEN } from '@/lib/arrowColor';
import type { OpeningInsightFinding } from '@/types/insights';

export function getSeverityBorderColor(
  classification: OpeningInsightFinding['classification'],
  severity: OpeningInsightFinding['severity'],
): string {
  if (classification === 'weakness') {
    return severity === 'major' ? DARK_RED : LIGHT_RED;
  }
  return severity === 'major' ? DARK_GREEN : LIGHT_GREEN;
}
```

Used in `OpeningFindingCard.tsx`:
```tsx
<a
  style={{ borderLeftColor: getSeverityBorderColor(finding.classification, finding.severity) }}
  className="border-l-4 charcoal-texture border border-border/20 rounded px-4 py-3 ..."
  ...
>
```

`border-l-4` sets the border-left width; `style.borderLeftColor` overrides the color without conflicting with Tailwind.

### `<unnamed line>` Sentinel Handling

Per Phase 70's D-34 and verified in `opening_insights_service.py:284-287`: findings with no opening attribution are **DROPPED** server-side (return value `None` → `continue`). The `<unnamed line>` sentinel is present in the constants (`UNNAMED_LINE_NAME = "<unnamed line>"`) but the service never returns a finding with that value because unmatched findings are dropped before constructing `OpeningInsightFinding`.

The frontend should still defensively handle it in `OpeningFindingCard.tsx` per D-04:
```tsx
const displayName = finding.opening_name === '<unnamed line>'
  ? <span className="italic text-muted-foreground">{finding.display_name}</span>
  : <span>{finding.display_name}</span>;
```
This is defensive code against future schema relaxation — it will never fire with current Phase 70 logic.

---

## Validation Architecture

Nyquist validation is enabled (`workflow.nyquist_validation: true` in config.json). Framework: Vitest 4.x + Testing Library (confirmed by `frontend/src/hooks/__tests__/useEndgameInsights.test.tsx` which uses `@testing-library/react`, `renderHook`, `waitFor`).

### Test Framework

| Property | Value |
|---|---|
| Framework | Vitest 4.1.x (confirmed via package.json) |
| Config file | `vite.config.ts` (Vitest config embedded — no separate vitest.config.ts) |
| Quick run command | `npm test` (runs `vitest run`) |
| Full suite command | `npm test` |
| Watch mode | `npm run test:watch` |

### Test Categorization by Requirement

| Req ID | Behavior | Test Type | File | Automated Command |
|---|---|---|---|---|
| INSIGHT-STATS-01 | Block renders on Stats subtab | Visual (manual) | — | Manual |
| INSIGHT-STATS-02 | Severity colors match arrow-color constants | Unit | `src/lib/openingInsights.test.ts` | `npm test -- openingInsights` |
| INSIGHT-STATS-02 | Prose template renders correctly | Component | `src/components/insights/OpeningFindingCard.test.tsx` | `npm test -- OpeningFindingCard` |
| INSIGHT-STATS-03 | Deep-link handler calls correct state mutations | Component | `src/components/insights/OpeningInsightsBlock.test.tsx` | `npm test -- OpeningInsightsBlock` |
| INSIGHT-STATS-04 | Empty state renders for empty response | Component | `src/components/insights/OpeningInsightsBlock.test.tsx` | `npm test -- OpeningInsightsBlock` |
| INSIGHT-STATS-05 | Hook refetches when query key changes | Integration | `src/hooks/__tests__/useOpeningInsights.test.tsx` | `npm test -- useOpeningInsights` |
| INSIGHT-STATS-06 | Mobile layout renders board in correct position | Visual (manual UAT) | — | Manual UAT at 375px |

### Unit Tests (pure helpers)

`src/lib/openingInsights.test.ts`:
- `trimMoveSequence` — all edge cases from the algorithm section (6 plys with ellipsis, 2 plys no ellipsis, 1 ply, 0 plys, black-on-move start)
- `getSeverityBorderColor` — 4 combinations, verify returns correct hex string matching `arrowColor.ts` exports

Pattern: mirrors `arrowColor.test.ts` structure (plain Vitest `describe`/`it`/`expect`, no jsdom needed).

### Component Tests (Vitest + Testing Library)

`src/components/insights/OpeningInsightsBlock.test.tsx`:
- Loading state: skeleton renders with `data-testid="opening-insights-skeleton"` (or similar), no cards
- Error state: `role="alert"` present, "Try again" button present
- Empty state (all 4 sections empty): block-level empty message present
- Populated state: 4 section headings rendered, card count matches mock data
- Click handler: clicking a card calls `onFindingClick` with the correct `finding` argument

Pattern: `@vitest-environment jsdom` header, mock `apiClient.post`, `QueryClientProvider` wrapper, `renderHook` or `render` — mirrors `useEndgameInsights.test.tsx`.

`src/components/insights/OpeningFindingCard.test.tsx`:
- Prose renders correct template for weakness vs strength
- `<unnamed line>` sentinel renders as italicized muted text
- ExternalLink icon present in header
- `data-testid` attributes present

### Integration Test (hook)

`src/hooks/__tests__/useOpeningInsights.test.tsx`:
- `POST /insights/openings` called with correct body (including `color: "all"` always)
- Query key changes when filter prop changes → `apiClient.post` called again
- Response data accessible via `result.current.data`

Pattern: exact copy of `useEndgameInsights.test.tsx` structure with `apiClient.post` mock.

### Manual UAT Checklist

- [ ] Block renders at top of Stats tab, above bookmarks section
- [ ] Severity colors: major weakness card has dark red left border, minor weakness has light red, etc.
- [ ] Left border color matches the arrow color shown for the same move in Move Explorer after deep-link
- [ ] Deep-link click: board loads at correct position, filter color updates, page scrolls to top
- [ ] Mobile (375px width): header full-width on top, board + prose side by side below
- [ ] InfoPopover on block heading opens and shows threshold copy
- [ ] Loading skeleton: 4 section placeholder rows + 2-3 card placeholders each
- [ ] Empty state: block-level message shown when all sections empty
- [ ] Error state: "Try again" button triggers refetch

### Wave 0 Gaps

- [ ] `src/lib/openingInsights.test.ts` — covers trimMoveSequence + getSeverityBorderColor
- [ ] `src/hooks/__tests__/useOpeningInsights.test.tsx` — covers hook POST behavior
- [ ] `src/components/insights/OpeningInsightsBlock.test.tsx` — covers loading/error/empty/populated + click handler

*(Existing test infrastructure — Vitest, @testing-library/react, jsdom — is already installed and configured. No new framework setup needed.)*

---

## Open Questions

1. **Prose color shading for rate-percent number**
   - What we know: D-07 says "rate-percent number MAY also be color-shaded (planner picks based on visual balance)"
   - Recommendation: Apply the same color as the border-left accent to the rate number for visual consistency. E.g. `<span style={{ color: getSeverityBorderColor(f.classification, f.severity) }}>{rate}%</span>`.

2. **Exact `OpeningInsightsBlock` props interface**
   - What we know: The block needs `debouncedFilters`, chess state setters, and `navigate` for the deep-link handler
   - Recommendation: Define `handleOpenFinding` in `Openings.tsx` and pass it as `onFindingClick: (finding: OpeningInsightFinding) => void` prop. This is cleaner than threading chess/setBoardFlipped/setFilters/navigate through the block.

3. **D-18 gating condition**
   - What we know: D-18 says "when the user has zero imported games" but `mostPlayedData` may be `undefined` (loading) or may have empty arrays
   - Recommendation: Gate on `mostPlayedData && (mostPlayedData.white.length > 0 || mostPlayedData.black.length > 0)` — same as the existing Most Played Openings gate. If `mostPlayedData` is undefined (loading), the block is hidden; this is acceptable because the insights call would also return empty data.

4. **Section icon choice**
   - What we know: D-01 says "leading icon" on section subheadings but doesn't specify which icons
   - Recommendation: Use `AlertTriangle` (lucide-react) for weakness sections, `Star` or `TrendingUp` for strength sections. Both are available in the existing icon import set.

---

## Environment Availability

Step 2.6: SKIPPED (frontend-only phase with no new external dependencies beyond the existing project stack).

---

## Sources

### Primary (HIGH confidence — direct file reads)

All findings were verified by reading the actual project files. No web searches were required.

- `app/schemas/opening_insights.py` — Phase 70 wire schema, confirmed `entry_san_sequence` absent
- `app/services/opening_insights_service.py` — confirmed `row.entry_san_sequence` available internally at all construction points; `_replay_san_sequence` at line 83; `OpeningInsightFinding` constructor at lines 305-324
- `app/repositories/openings_repository.py:514` — confirmed `entry_san_sequence: list[str]` as named row column
- `frontend/src/components/results/GameCard.tsx:1-264` — `LazyMiniBoard` at lines 14-42, `BORDER_CLASSES` at lines 53-57, card chrome at lines 224-227, mobile/desktop layout at lines 229-261
- `frontend/src/components/insights/EndgameInsightsBlock.tsx` — outer block chrome, skeleton pattern lines 170-189, error state lines 322-352
- `frontend/src/pages/Openings.tsx:377-384` — `useMostPlayedOpenings` filter-passing pattern; lines 492-498 — `handleOpenGames`; lines 785-788 — `statisticsContent` insertion point; lines 877, 908 — piece-color swatch pattern
- `frontend/src/lib/arrowColor.ts` — `LIGHT_GREEN`, `DARK_GREEN`, `LIGHT_RED`, `DARK_RED` hex constants; `LIGHT_COLOR_THRESHOLD = 55`, `DARK_COLOR_THRESHOLD = 60`
- `frontend/src/lib/theme.ts` — confirmed no light/dark severity border-color constants exist today
- `frontend/src/hooks/useStats.ts:35-61` — `useMostPlayedOpenings` hook pattern
- `frontend/src/lib/queryClient.ts` — global staleTime 30_000, QueryCache Sentry capture
- `frontend/src/types/insights.ts` — existing types; no Phase 70 types present yet
- `frontend/src/components/filters/FilterPanel.tsx:16-37` — `FilterState` interface, `DEFAULT_FILTERS`
- `frontend/src/components/ui/info-popover.tsx` — `InfoPopover` API: `{ children, ariaLabel, testId, side? }`
- `frontend/src/hooks/useEndgameInsights.ts` — mutation/POST pattern for insights endpoint
- `frontend/src/api/client.ts:67-85` — `buildFilterParams`; line 24 global staleTime
- `frontend/vite.config.ts` — Vitest embedded in Vite config
- `frontend/package.json` — Vitest 4.1.x confirmed
- `frontend/src/hooks/__tests__/useEndgameInsights.test.tsx` — test pattern for insight hooks (jsdom, renderHook, QueryClientProvider wrapper)
- `frontend/src/lib/arrowColor.test.ts` — unit test pattern for pure lib functions

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries confirmed in package.json and existing code
- Architecture: HIGH — insertion point, component decomposition, and handler integration verified by file reads
- Pitfalls: HIGH — `entry_san_sequence` gap identified by direct schema + service read
- Phase 70 contract amendment: HIGH — both files read in full; amendment scope confirmed minimal

**Research date:** 2026-04-27
**Valid until:** 2026-05-27 (stable frontend stack)

---

## RESEARCH COMPLETE
