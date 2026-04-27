# Phase 71: Frontend Stats subtab — `OpeningInsightsBlock` - Pattern Map

**Mapped:** 2026-04-27
**Files analyzed:** 11 (7 new, 4 modified)
**Analogs found:** 11 / 11

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `frontend/src/components/board/LazyMiniBoard.tsx` | component | request-response (lazy render) | `GameCard.tsx` lines 14-42 (inline function) | exact — extract verbatim |
| `frontend/src/components/insights/OpeningFindingCard.tsx` | component | request-response | `frontend/src/components/results/GameCard.tsx` | exact — modeled directly |
| `frontend/src/components/insights/OpeningInsightsBlock.tsx` | component | request-response | `frontend/src/components/insights/EndgameInsightsBlock.tsx` | role-match (outer chrome, states) |
| `frontend/src/hooks/useOpeningInsights.ts` | hook | request-response (POST) | `frontend/src/hooks/useStats.ts` `useMostPlayedOpenings` | role-match |
| `frontend/src/lib/openingInsights.ts` | utility | transform | `frontend/src/lib/arrowColor.ts` | role-match |
| `frontend/src/types/insights.ts` (amended) | type definitions | — | `frontend/src/types/insights.ts` (existing) | exact — extend in place |
| `app/schemas/opening_insights.py` (amended) | schema | — | `app/schemas/opening_insights.py` (existing) | exact — add one field |
| `app/services/opening_insights_service.py` (amended) | service | CRUD | `app/services/opening_insights_service.py` (existing) | exact — one-line constructor amendment |
| `frontend/src/components/results/GameCard.tsx` (modified) | component | request-response | self | exact — swap inline fn for import |
| `frontend/src/pages/Openings.tsx` (modified) | page | request-response | self (handleOpenGames pattern) | exact — add handler + block insertion |
| Tests (`openingInsights.test.ts`, `useOpeningInsights.test.tsx`, `OpeningInsightsBlock.test.tsx`, `OpeningFindingCard.test.tsx`) | test | — | `frontend/src/lib/arrowColor.test.ts`, `frontend/src/hooks/__tests__/useEndgameInsights.test.tsx` | role-match |

---

## Pattern Assignments

### `frontend/src/components/board/LazyMiniBoard.tsx` (component, lazy render)

**Analog:** `frontend/src/components/results/GameCard.tsx` lines 14-42

**Core pattern — extract verbatim** (GameCard.tsx lines 1-42):
```typescript
import { useRef, useState, useEffect } from 'react';
import { MiniBoard } from '@/components/board/MiniBoard';

/** Renders MiniBoard only when the card scrolls into view. */
function LazyMiniBoard({ fen, flipped, size }: { fen: string; flipped: boolean; size: number }) {
  const ref = useRef<HTMLDivElement>(null);
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const observer = new IntersectionObserver(
      (entries) => {
        // safe: IntersectionObserver always provides at least 1 entry when observing 1 element
        if (entries[0]!.isIntersecting) { setVisible(true); observer.disconnect(); }
      },
      { rootMargin: '200px' },
    );
    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  return (
    <div
      ref={ref}
      className="shrink-0 rounded overflow-hidden bg-muted"
      style={{ width: size, height: size }}
    >
      {visible && <MiniBoard fen={fen} size={size} flipped={flipped} />}
    </div>
  );
}
```

**Export as named export** (not default, not inner function):
```typescript
export function LazyMiniBoard({ fen, flipped, size }: { fen: string; flipped: boolean; size: number }) { ... }
```

**MiniBoard import path** is `@/components/board/MiniBoard` — LazyMiniBoard lives in the same `board/` directory so the relative import becomes `'./MiniBoard'` or the alias still works.

---

### `frontend/src/components/insights/OpeningFindingCard.tsx` (component, request-response)

**Analog:** `frontend/src/components/results/GameCard.tsx` (lines 1-264) — copy card chrome, layout, and link/icon patterns exactly.

**Imports pattern** (GameCard.tsx lines 1-8, adapted):
```typescript
import { ExternalLink } from 'lucide-react';
import { LazyMiniBoard } from '@/components/board/LazyMiniBoard';
import { getSeverityBorderColor } from '@/lib/openingInsights';
import type { OpeningInsightFinding } from '@/types/insights';
```

**Size constants** (GameCard.tsx lines 44-45):
```typescript
const MOBILE_BOARD_SIZE = 105;
const DESKTOP_BOARD_SIZE = 100;
```

**Card chrome** (GameCard.tsx lines 221-227) — copy verbatim, replacing `BORDER_CLASSES[game.user_result]` with inline `style`:
```tsx
<a
  href="/openings/explorer"
  data-testid={`opening-finding-card-${idx}`}
  aria-label={`Open ${finding.display_name} (${finding.candidate_move_san}) in Move Explorer`}
  onClick={(e) => { e.preventDefault(); onFindingClick(finding); }}
  className="border-l-4 charcoal-texture border border-border/20 rounded px-4 py-3 block cursor-pointer hover:bg-muted/30 transition-colors"
  style={{ borderLeftColor: getSeverityBorderColor(finding.classification, finding.severity) }}
>
```

**Mobile layout** (GameCard.tsx lines 229-245) — mirror exactly:
```tsx
{/* Mobile layout: header full width on top, then board + content below */}
<div className="flex flex-col gap-2 sm:hidden">
  {headerLine}
  <div className="flex gap-3 items-start">
    <LazyMiniBoard
      fen={finding.entry_fen}
      flipped={finding.color === 'black'}
      size={MOBILE_BOARD_SIZE}
    />
    <div className="flex-1 min-w-0 flex flex-col gap-1">
      {proseLine}
    </div>
  </div>
</div>
```

**Desktop layout** (GameCard.tsx lines 247-261) — mirror exactly:
```tsx
{/* Desktop layout: board left, content stacked right */}
<div className="hidden sm:flex gap-3 items-center">
  <LazyMiniBoard
    fen={finding.entry_fen}
    flipped={finding.color === 'black'}
    size={DESKTOP_BOARD_SIZE}
  />
  <div className="min-w-0 flex-1 flex flex-col gap-2">
    {headerLine}
    {proseLine}
  </div>
</div>
```

**`platformIconAndLink`-style header affordance** (GameCard.tsx lines 114-132) — replicate with ExternalLink icon:
```tsx
const headerLine = (
  <div className="flex items-center gap-2 text-sm">
    <span className="truncate text-foreground font-medium">
      {finding.opening_name === '<unnamed line>'
        ? <span className="italic text-muted-foreground">{finding.display_name}</span>
        : finding.display_name}
      {finding.opening_eco && (
        <span className="ml-1 text-muted-foreground">({finding.opening_eco})</span>
      )}
    </span>
    <span className="ml-auto shrink-0 text-muted-foreground">
      <ExternalLink className="h-4 w-4" />
    </span>
  </div>
);
```

---

### `frontend/src/components/insights/OpeningInsightsBlock.tsx` (component, request-response)

**Analog:** `frontend/src/components/insights/EndgameInsightsBlock.tsx`

**Outer block chrome** (EndgameInsightsBlock.tsx lines 82-86):
```tsx
<div
  data-testid="opening-insights-block"
  className="charcoal-texture rounded-md p-4"
>
```

**Block heading pattern** (EndgameInsightsBlock.tsx lines 87-94):
```tsx
<div className="flex flex-wrap items-center gap-2 mb-2">
  <h2 className="text-lg font-semibold text-foreground mt-2 flex items-center gap-2">
    <span className="insight-lightbulb" aria-hidden="true">
      <Lightbulb className="size-5" />
    </span>
    Opening Insights
  </h2>
  <InfoPopover ariaLabel="Opening insights info" testId="opening-insights-info">
    {/* D-20 copy: scan domain, threshold, color filter scope */}
  </InfoPopover>
</div>
```

**Loading skeleton** (EndgameInsightsBlock.tsx lines 170-188) — adapt to 4-section structure:
```tsx
function SkeletonBlock() {
  return (
    <div data-testid="opening-insights-skeleton" className="animate-pulse space-y-4">
      {/* 4 sections: each has a header bar + 2 card placeholders */}
      {[0, 1, 2, 3].map((i) => (
        <div key={i} className="space-y-2">
          <div className="h-5 w-48 bg-muted/30 rounded" />  {/* section h3 */}
          <div className="h-16 w-full bg-muted/30 rounded border-l-4 border-l-muted/30" />
          <div className="h-16 w-full bg-muted/30 rounded border-l-4 border-l-muted/30" />
        </div>
      ))}
    </div>
  );
}
```

**Error state** (EndgameInsightsBlock.tsx lines 322-352) — copy structure, remove rate-limit branch:
```tsx
function ErrorState({ onRetry }: { onRetry: () => void }) {
  return (
    <div data-testid="opening-insights-error" role="alert">
      <p className="text-sm text-muted-foreground mb-2">
        Failed to load opening insights. Something went wrong. Please try again in a moment.
      </p>
      <Button
        variant="brand-outline"
        onClick={onRetry}
        data-testid="btn-opening-insights-retry"
        className="mt-3"
      >
        Try again
      </Button>
    </div>
  );
}
```

**Loading/error/empty ternary chain** (CLAUDE.md frontend rule):
```tsx
{isLoading ? <SkeletonBlock /> : isError ? <ErrorState onRetry={() => query.refetch()} /> : allEmpty ? <EmptyBlock /> : <SectionsContent />}
```

**Section subheading with piece-color swatch** (Openings.tsx lines 874-881 pattern):
```tsx
<h3 className="text-base font-semibold flex items-center gap-1.5 mb-2">
  <AlertTriangle className="h-4 w-4 text-muted-foreground" />  {/* or Star for strength */}
  <span className="inline-block h-3.5 w-3.5 rounded-xs border border-muted-foreground bg-white" />  {/* bg-zinc-900 for black */}
  White Opening Weaknesses
</h3>
```

**data-testid for sections** (D-21 — section keys: `white-weaknesses`, `black-weaknesses`, `white-strengths`, `black-strengths`):
```tsx
<div data-testid="opening-insights-section-white-weaknesses">
```

**Card stack inside section** (GameCardList.tsx line 83 — `space-y-3`):
```tsx
<div className="space-y-3">
  {findings.map((finding, idx) => (
    <OpeningFindingCard key={idx} finding={finding} idx={idx} onFindingClick={onFindingClick} />
  ))}
</div>
```

---

### `frontend/src/hooks/useOpeningInsights.ts` (hook, request-response POST)

**Analog:** `frontend/src/hooks/useStats.ts` `useMostPlayedOpenings` (lines 35-61) for filter normalization and query structure. **But uses `useQuery` with `apiClient.post`, not `statsApi.get`.**

**Filter normalization pattern** (useStats.ts lines 43-48):
```typescript
const normalizedRecency = filters?.recency === 'all' ? null : (filters?.recency ?? null);
const timeControl = filters?.timeControls ?? null;
const platform = filters?.platforms ?? null;
const rated = filters?.rated ?? null;
const opponentType = filters?.opponentType ?? 'human';
const opponentStrength = filters?.opponentStrength ?? 'any';
```

**Query structure** (useStats.ts lines 50-60, adapted for POST body):
```typescript
return useQuery({
  queryKey: ['openingInsights', normalizedRecency, timeControl, platform, rated, opponentType, opponentStrength],
  queryFn: () =>
    apiClient.post<OpeningInsightsResponse>('/insights/openings', {
      recency: normalizedRecency ?? undefined,
      time_control: timeControl ?? undefined,
      platform: platform ?? undefined,
      rated: rated ?? undefined,
      opponent_type: opponentType,
      opponent_strength: opponentStrength,
      color: 'all',  // D-02: always "all" regardless of global filter
    }).then(r => r.data),
  // staleTime inherits 30_000 from queryClient.ts line 370 global default
});
```

**POST body (not query params):** The opening insights endpoint accepts a JSON body, unlike the GET stats endpoints that use `statsApi.get` with params. The pattern matches `positionBookmarksApi.create` in `client.ts` line 92-93: `apiClient.post<T>(url, body).then(r => r.data)`.

**Sentry:** Do NOT add `Sentry.captureException`. Global `QueryCache.onError` in `queryClient.ts` handles it (confirmed at queryClient.ts lines 6-11).

---

### `frontend/src/lib/openingInsights.ts` (utility, transform)

**Analog:** `frontend/src/lib/arrowColor.ts` — pure function module with exported constants and typed helpers.

**Imports pattern** (arrowColor.ts lines 1-27, adapted):
```typescript
import { DARK_RED, LIGHT_RED, DARK_GREEN, LIGHT_GREEN } from '@/lib/arrowColor';
import type { OpeningInsightFinding } from '@/types/insights';
```

**Exported constants** (mirror arrowColor.ts naming convention):
```typescript
export const MIN_GAMES_FOR_INSIGHT = 20;  // matches backend MIN_GAMES threshold
export const INSIGHT_RATE_THRESHOLD = 55; // matches arrowColor LIGHT_COLOR_THRESHOLD

// Shared threshold copy — single source of truth for InfoPopover D-20 and empty states D-09/D-10
export const INSIGHT_THRESHOLD_COPY =
  'Insights are computed from candidate moves with at least 20 games where your win or loss rate exceeds 55%.';
```

**getSeverityBorderColor** (pure, typed, mirrors getArrowColor signature style):
```typescript
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

**trimMoveSequence** (pure helper, unit-tested per D-05):
```typescript
export function trimMoveSequence(
  entrySanSequence: string[],
  candidateMoveSan: string,
): string { ... }
```

Full algorithm is specified in RESEARCH.md "Move-Sequence Trim Algorithm" section with all edge cases and examples.

---

### `frontend/src/types/insights.ts` (amended — add Phase 71 types)

**Analog:** `frontend/src/types/insights.ts` existing content (lines 1-63).

**Extend in place** — add after the existing Phase 65 types, with a section comment:
```typescript
// ─── Phase 71 — Opening Insights ──────────────────────────────────────────
// Hand-mirrored from app/schemas/opening_insights.py.
// entry_san_sequence added by Phase 71 backend amendment (D-13).

export interface OpeningInsightFinding {
  color: 'white' | 'black';
  classification: 'weakness' | 'strength';
  severity: 'minor' | 'major';
  opening_name: string;
  opening_eco: string;
  display_name: string;
  entry_fen: string;
  entry_san_sequence: string[];  // added Phase 71: SAN tokens start→entry (candidate excluded)
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

---

### `app/schemas/opening_insights.py` (amended — add `entry_san_sequence`)

**Analog:** `app/schemas/opening_insights.py` existing `OpeningInsightFinding` class (lines 36-60).

**Add one field after `entry_fen: str` (line 50)**:
```python
entry_fen: str
entry_san_sequence: list[str]  # SAN tokens from start to entry position (candidate excluded); added Phase 71 for FE deep-link
entry_full_hash: str  # str-form for JSON precision (RESEARCH.md Pitfall 1)
```

---

### `app/services/opening_insights_service.py` (amended — pass field in constructor)

**Analog:** `app/services/opening_insights_service.py` `OpeningInsightFinding(...)` constructor call (lines 305-324).

**Add one keyword arg after `entry_fen=entry_fen,` (line 312)**:
```python
finding = OpeningInsightFinding(
    color=color_literal,
    classification=classification,
    severity=severity,
    opening_name=opening_name,
    opening_eco=opening_eco,
    display_name=display_name,
    entry_fen=entry_fen,
    entry_san_sequence=list(row.entry_san_sequence or []),  # Phase 71: expose for FE deep-link
    # BLOCKER-5 / Pitfall 1: stringify 64-bit ints at the API boundary.
    entry_full_hash=str(int(row.entry_hash)),
    candidate_move_san=row.move_san,
    ...
)
```

`row.entry_san_sequence` is already fetched by `openings_repository.py:514` (verified). No query change needed.

---

### `frontend/src/components/results/GameCard.tsx` (modified — import LazyMiniBoard)

**Change:** Remove inline `LazyMiniBoard` function (lines 14-42). Replace with import:
```typescript
import { LazyMiniBoard } from '@/components/board/LazyMiniBoard';
```

All other code in GameCard.tsx stays identical — `LazyMiniBoard` is called with the same API (`fen`, `flipped`, `size`).

---

### `frontend/src/pages/Openings.tsx` (modified — add handler + block insertion)

**Deep-link handler** — add alongside `handleOpenGames` (after line 498):
```typescript
/** Load entry SAN sequence onto the board, set color/flip/filters, navigate to Move Explorer */
const handleOpenFinding = useCallback((finding: OpeningInsightFinding) => {
  chess.loadMoves(finding.entry_san_sequence);
  setBoardFlipped(finding.color === 'black');
  setFilters(prev => ({ ...prev, color: finding.color, matchSide: 'both' as MatchSide }));
  navigate('/openings/explorer');
  window.scrollTo({ top: 0 });
}, [chess, navigate, setFilters]);
```

Compare to `handleOpenGames` (lines 492-498):
```typescript
const handleOpenGames = useCallback((pgn: string, color: "white" | "black") => {
  chess.loadMoves(pgnToSanArray(pgn));
  setBoardFlipped(color === 'black');
  setFilters(prev => ({ ...prev, color, matchSide: 'both' as MatchSide }));
  navigate('/openings/games');
  window.scrollTo({ top: 0 });
}, [chess, navigate, setFilters]);
```

**Block insertion** — at line 786 inside `statisticsContent`, as first child of `<div className="flex flex-col gap-4">`:
```tsx
const statisticsContent = (
  <div className="flex flex-col gap-4">
    {/* Opening Insights Block — D-19: top of Stats tab, before bookmarks section */}
    {mostPlayedData && (mostPlayedData.white.length > 0 || mostPlayedData.black.length > 0) && (
      <OpeningInsightsBlock
        debouncedFilters={debouncedFilters}
        onFindingClick={handleOpenFinding}
      />
    )}
    {/* Bookmarked Openings: Results — empty state when no bookmarks, chart when data available */}
    {bookmarks.length === 0 ? (
```

**useMostPlayedOpenings filter-passing pattern** (lines 377-384 — mirrors the hook call):
```typescript
const { data: openingInsightsData, isLoading: insightsLoading, isError: insightsError, refetch: refetchInsights } =
  useOpeningInsights({
    recency: debouncedFilters.recency,
    timeControls: debouncedFilters.timeControls,
    platforms: debouncedFilters.platforms,
    rated: debouncedFilters.rated,
    opponentType: debouncedFilters.opponentType,
    opponentStrength: debouncedFilters.opponentStrength,
  });
```

Note: The hook call can be inside `OpeningInsightsBlock` itself (receives `debouncedFilters` as prop and calls the hook internally), which avoids prop-drilling query state. Either placement works — the planner should pick one and be consistent.

---

## Shared Patterns

### Block Outer Chrome
**Source:** `frontend/src/components/insights/EndgameInsightsBlock.tsx` line 85
**Apply to:** `OpeningInsightsBlock.tsx`
```tsx
<div data-testid="opening-insights-block" className="charcoal-texture rounded-md p-4">
```

### `insight-lightbulb` CSS class + `<Lightbulb>` icon
**Source:** `frontend/src/components/insights/EndgameInsightsBlock.tsx` lines 89-92
**Apply to:** `OpeningInsightsBlock.tsx` heading
```tsx
<span className="insight-lightbulb" aria-hidden="true">
  <Lightbulb className="size-5" />
</span>
```

### Piece-color square swatch
**Source:** `frontend/src/pages/Openings.tsx` lines 877-878 and 908
**Apply to:** Section `<h3>` headings in `OpeningInsightsBlock.tsx`
```tsx
{/* White */}
<span className="inline-block h-3.5 w-3.5 rounded-xs border border-muted-foreground bg-white" />
{/* Black */}
<span className="inline-block h-3.5 w-3.5 rounded-xs border border-muted-foreground bg-zinc-900" />
```

### InfoPopover usage
**Source:** `frontend/src/pages/Openings.tsx` lines 879-881
**Apply to:** Block heading in `OpeningInsightsBlock.tsx`
```tsx
<InfoPopover ariaLabel="Opening insights info" testId="opening-insights-info" side="top">
  {INSIGHT_THRESHOLD_COPY} This block always shows both colors regardless of the active color filter.
</InfoPopover>
```

### `brand-outline` button for secondary actions
**Source:** `frontend/src/components/insights/EndgameInsightsBlock.tsx` lines 341-348
**Apply to:** "Try again" button in `OpeningInsightsBlock.tsx` error state
```tsx
<Button variant="brand-outline" onClick={onRetry} data-testid="btn-opening-insights-retry" className="mt-3">
  Try again
</Button>
```

### `animate-pulse bg-muted/30` skeleton pattern
**Source:** `frontend/src/components/insights/EndgameInsightsBlock.tsx` lines 181-186
**Apply to:** `SkeletonBlock` in `OpeningInsightsBlock.tsx`
```tsx
<div className="animate-pulse">
  <div className="h-4 w-full bg-muted/30 rounded mb-2" />
</div>
```

### `role="alert"` for error states
**Source:** `frontend/src/components/insights/EndgameInsightsBlock.tsx` line 330
**Apply to:** Error state div in `OpeningInsightsBlock.tsx`
```tsx
<div data-testid="opening-insights-error" role="alert">
```

### `isError` ternary chain (CLAUDE.md mandatory)
**Source:** CLAUDE.md frontend Sentry rules
**Apply to:** `OpeningInsightsBlock.tsx` render
```tsx
{isLoading ? <Skeleton /> : isError ? <ErrorState /> : hasData ? <Content /> : <EmptyState />}
```

### `data-testid` naming convention
**Source:** CLAUDE.md "Browser Automation Rules"
**Apply to:** All new components
- Block: `data-testid="opening-insights-block"`
- Section: `data-testid="opening-insights-section-{white-weaknesses|black-weaknesses|white-strengths|black-strengths}"`
- Card: `data-testid="opening-finding-card-{idx}"`
- Retry button: `data-testid="btn-opening-insights-retry"`

---

## Test Patterns

### Unit test for pure helpers
**Analog:** `frontend/src/lib/arrowColor.test.ts`

**File header and structure** (arrowColor.test.ts lines 1-11):
```typescript
import { describe, it, expect } from 'vitest';
import { trimMoveSequence, getSeverityBorderColor } from './openingInsights';
import { DARK_RED, LIGHT_RED, DARK_GREEN, LIGHT_GREEN } from './arrowColor';
```

No `@vitest-environment jsdom` needed (pure functions, no DOM).

### Integration test for hook
**Analog:** `frontend/src/hooks/__tests__/useEndgameInsights.test.tsx`

**File header and mock setup** (useEndgameInsights.test.tsx lines 1-28):
```typescript
// @vitest-environment jsdom
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { ReactNode } from 'react';

vi.mock('@/api/client', async () => {
  const actual = await vi.importActual<typeof import('@/api/client')>('@/api/client');
  return { ...actual, apiClient: { post: vi.fn() } };
});
import { apiClient } from '@/api/client';

function wrapper({ children }: { children: ReactNode }) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}
```

Key assertion to include (adapting useEndgameInsights.test.tsx line 74):
```typescript
// Always sends color: "all" regardless of filter input (D-02)
expect(body).toMatchObject({ color: 'all' });
```

---

## No Analog Found

All files have close analogs. No entries.

---

## Metadata

**Analog search scope:** `frontend/src/`, `app/schemas/`, `app/services/`
**Files scanned:** 12 source files read directly
**Pattern extraction date:** 2026-04-27

**Key observations:**
- `LazyMiniBoard` is extracted verbatim — the function body copies to the new file unchanged, only the export style changes (named export vs inner function).
- `OpeningFindingCard` copies the `GameCard` mobile/desktop dual-layout shell exactly; the only structural difference is the card is an `<a>` not a `<div>`, and severity color uses `style={{ borderLeftColor }}` instead of a `BORDER_CLASSES` Tailwind string.
- The hook uses `useQuery` (not `useMutation`) and POSTs a JSON body (not query params) — this is a hybrid pattern not present in other hooks. The POST-body approach matches `positionBookmarksApi.create` in `client.ts`.
- The backend amendment is two lines in two files with no migration; `row.entry_san_sequence` is already in every query result row.
