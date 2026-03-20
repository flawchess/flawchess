# Phase 13: Frontend Move Explorer Component - Research

**Researched:** 2026-03-16
**Domain:** React/TypeScript frontend — TanStack Query, react-chessboard arrows API, chess.js SAN-to-squares, mini WDL bar
**Confidence:** HIGH

## Summary

Phase 13 builds the Move Explorer UI component on the Dashboard's right column. The backend API (`POST /analysis/next-moves`) is already complete from Phase 12, returning `NextMovesResponse` with a `moves` array of `NextMoveEntry` objects. The frontend requires: a `useNextMoves` TanStack Query hook (auto-fetch on hash/filter change), a `MoveExplorer` component (table with mini WDL bars + transposition icons), an extension of `ChessBoard` to accept an `arrows` prop, and TypeScript type additions to `api.ts`.

The react-chessboard `arrows` option is confirmed in v5.10.0 (currently installed). The `Arrow` type is `{ startSquare: string; endSquare: string; color: string }`. Per-arrow opacity must be encoded into the `color` string as an RGBA or CSS `rgba()` value because `arrowOptions.opacity` is a single global value for all arrows. Chess.js `moves({ verbose: true })` resolves SAN strings to `from`/`to` squares in O(moves) time. All patterns (TanStack Query, shadcn/ui, data-testid, FilterState) are well-established in this codebase.

The dominant integration risk is the `clearArrowsOnPositionChange` default (`true`) in react-chessboard — it will clear externally-supplied arrows whenever the position changes unless explicitly set to `false`. This must be overridden.

**Primary recommendation:** Add `useNextMoves` hook (TanStack `useQuery` auto-fetching on `[hash, filters]`), create `MoveExplorer` component placed above the WDL bar in `rightColumn`, extend `ChessBoard` with an `arrows?: Arrow[]` prop, add TypeScript types. Use RGBA color encoding for per-arrow opacity.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **Explorer table layout**: Right column of Dashboard, above W/D/L bar and game cards. 3-column table: Move (SAN), Games (count), Results (mini stacked W/D/L bar). Rows ordered by game_count descending. Mini stacked bar reuses WDL color scheme (green/gray/red), hover tooltip shows W/D/L percentages. Always visible — shows next moves even from starting position (no positionFilterActive gating for the explorer). Built as self-contained component for Phase 14 portability.
- **Board integration & navigation**: Clicking a move row plays the move on the board via `useChessGame.makeMove`, extending the move history. Back/Forward navigation works normally. Auto-fetch: explorer refreshes automatically on position change (move played, bookmark loaded, navigation) AND on filter changes — no Filter button click needed. W/D/L bar and game list still require the Filter button (heavier query). Explorer uses `full_hash` only (ignoring piece filter / match_side). Explorer respects all other active filters (time control, platform, rated, opponent, recency).
- **Arrow overlays on board**: Blue arrows with opacity proportional to move frequency. Show arrows for ALL moves in the explorer (no cap). Minimum 15% opacity so even rare moves remain visible. Most-played move gets full opacity, proportional scaling down from there. Uses react-chessboard's native `arrows` option.
- **Transposition indicators**: Small icon (⇄) appears after the Games count number when `transposition_count > game_count`. Hover tooltip shows: "Position reached in X total games (Y via other move orders)". `transposition_count` comes from backend; frontend derives "via other move orders" as `transposition_count - game_count`.

### Claude's Discretion
- Exact component file structure and naming
- Loading/skeleton state design while explorer fetches
- Empty state message when no moves available for current position
- Debounce strategy for auto-fetch on rapid filter changes
- Exact opacity scaling formula for arrows
- Mobile responsive layout adjustments for the explorer table

### Deferred Ideas (OUT OF SCOPE)
- MEXP-08: Move sorting options (by win rate, alphabetical) — future requirement
- MEXP-09: Show resulting position FEN/thumbnail on move hover — future requirement
- Sub-tab structure (Move Explorer / Games / Statistics) — Phase 14 UI Restructuring
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| MEXP-06 | Move Explorer displays 3-column table (Move, Games, Results) with W/D/L stacked bar in Results column | WDL color constants from WDLBar.tsx; mini inline bar pattern established; table via HTML `<table>` or div rows with `data-testid` per row |
| MEXP-07 | Clicking a move row advances the board and refreshes explorer with new position's next moves | `useChessGame.makeMove(from, to)` confirmed — takes square coordinates, not SAN; `chess.moves({verbose: true})` resolves SAN to from/to; TanStack Query auto-refetch on hash key change |
| MEXP-11 | Move Explorer shows transposition warning icon with hover tooltip when resulting position reached via other move orders | `transposition_count > game_count` condition from backend schema confirmed; shadcn/ui `Tooltip` component available; ⇄ or custom SVG icon approach |
| MEXP-12 | Chessboard displays transparent arrows for all next moves, opacity proportional to move frequency | react-chessboard v5.10.0 `arrows?: Arrow[]` prop confirmed; `Arrow = {startSquare, endSquare, color: string}`; RGBA color encodes per-arrow opacity; `clearArrowsOnPositionChange: false` required |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| @tanstack/react-query | installed | `useQuery` for auto-fetching next-moves on hash/filter change | Established pattern in project (`useGamesQuery`, `useAnalysis`) |
| react-chessboard | 5.10.0 | `arrows` option for move arrows overlay | Already installed; native feature confirmed in types.d.ts |
| chess.js | installed | `moves({verbose: true})` to resolve SAN to from/to squares | Already used in `useChessGame`; O(legal-moves) overhead, called client-side |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| shadcn/ui Tooltip | installed | Hover tooltip for transposition indicator | Consistent with existing component use (Button, Collapsible, ToggleGroup) |
| lucide-react | installed | Icon for transposition indicator (ArrowLeftRight or custom ⇄) | Consistent with existing icon usage (Bookmark, Filter, Download, etc.) |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| RGBA in `color` string for per-arrow opacity | `arrowOptions.opacity` (global) | Global opacity applies to ALL arrows equally — cannot scale per move; RGBA per-arrow is the only option |
| TanStack `useQuery` (auto-fetch) | `useMutation` (like `useAnalysis`) | Mutation requires manual trigger; query auto-refetches on key change — correct for explorer |

**Installation:** No new packages needed. All required libraries are already installed.

## Architecture Patterns

### Recommended Project Structure
```
frontend/src/
├── hooks/
│   └── useNextMoves.ts          # new: TanStack useQuery hook for POST /analysis/next-moves
├── components/
│   └── move-explorer/
│       └── MoveExplorer.tsx     # new: 3-column table with mini WDL, transposition icons, arrows computation
├── types/
│   └── api.ts                   # extend: add NextMoveEntry, NextMovesRequest, NextMovesResponse
└── components/board/
    └── ChessBoard.tsx           # extend: add arrows?: Arrow[] prop
```

### Pattern 1: useNextMoves Hook (TanStack useQuery)
**What:** `useQuery` with `queryKey: ['nextMoves', fullHashString, filtersKey]` — auto-refetches whenever hash or filter changes.
**When to use:** Anytime the component needs live server data that must refresh on state changes without a manual trigger.
**Example:**
```typescript
// Source: existing useGamesQuery in frontend/src/hooks/useAnalysis.ts (adapted to useQuery)
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/api/client';
import type { NextMovesRequest, NextMovesResponse } from '@/types/api';

export function useNextMoves(params: {
  target_hash: string;            // BigInt as string (hashToString(hashes.fullHash))
  filters: Partial<NextMovesRequest>;
  enabled?: boolean;
}) {
  return useQuery<NextMovesResponse>({
    queryKey: ['nextMoves', params.target_hash, params.filters],
    queryFn: async () => {
      const response = await apiClient.post<NextMovesResponse>('/analysis/next-moves', {
        target_hash: params.target_hash,
        ...params.filters,
      });
      return response.data;
    },
    enabled: params.enabled !== false,
  });
}
```

### Pattern 2: SAN to Arrow Squares (chess.js verbose moves)
**What:** Use `chess.moves({ verbose: true })` on the current board to map SAN strings from API response to `from`/`to` squares for arrow rendering.
**When to use:** When API returns SAN strings but react-chessboard `arrows` needs square coordinates.
**Example:**
```typescript
// Source: chess.js confirmed behavior via local node test
import { Chess } from 'chess.js';

function buildArrows(position: string, moves: NextMoveEntry[]): Arrow[] {
  const chess = new Chess(position);
  const legalMoves = chess.moves({ verbose: true });
  const moveMap = new Map(legalMoves.map(m => [m.san, { from: m.from, to: m.to }]));

  const maxCount = Math.max(...moves.map(m => m.game_count), 1);
  const MIN_OPACITY = 0.15;

  return moves
    .map(entry => {
      const squares = moveMap.get(entry.move_san);
      if (!squares) return null;
      const opacity = MIN_OPACITY + (1 - MIN_OPACITY) * (entry.game_count / maxCount);
      const alpha = Math.round(opacity * 255).toString(16).padStart(2, '0');
      return {
        startSquare: squares.from,
        endSquare: squares.to,
        color: `#1d6ab1${alpha}`,   // blue with proportional alpha
      };
    })
    .filter(Boolean) as Arrow[];
}
```

### Pattern 3: Mini Inline WDL Bar
**What:** Reuse WDL color constants from `WDLBar.tsx` for an inline stacked bar sized for a table cell.
**When to use:** Results column in Move Explorer table.
**Example:**
```typescript
// Source: WDLBar.tsx color constants (WDL_WIN, WDL_DRAW, WDL_LOSS)
const WDL_WIN = 'oklch(0.55 0.18 145)';
const WDL_DRAW = 'oklch(0.65 0.01 260)';
const WDL_LOSS = 'oklch(0.55 0.2 25)';

// Export constants from WDLBar.tsx so MoveExplorer can import them
// Mini bar: h-3 (12px) instead of h-6, no legend
<div className="flex h-3 w-full overflow-hidden rounded"
     title={`W:${win_pct.toFixed(0)}% D:${draw_pct.toFixed(0)}% L:${loss_pct.toFixed(0)}%`}>
  <div style={{ width: `${win_pct}%`, backgroundColor: WDL_WIN }} />
  <div style={{ width: `${draw_pct}%`, backgroundColor: WDL_DRAW }} />
  <div style={{ width: `${loss_pct}%`, backgroundColor: WDL_LOSS }} />
</div>
```

### Pattern 4: clearArrowsOnPositionChange Override (CRITICAL)
**What:** react-chessboard defaults `clearArrowsOnPositionChange: true`, which clears the arrows passed via the `arrows` prop when position changes. Must be set to `false` to keep externally-managed arrows.
**When to use:** Any time external arrows are passed to react-chessboard.
**Example:**
```typescript
// Source: react-chessboard dist/index.js line 4856 — default is true
<Chessboard
  options={{
    ...existingOptions,
    arrows: computedArrows,
    clearArrowsOnPositionChange: false,   // REQUIRED — prevents arrows being wiped on move
  }}
/>
```

### Anti-Patterns to Avoid
- **Passing SAN directly as arrow squares:** react-chessboard `arrows` takes `startSquare`/`endSquare` (e.g. "e2"/"e4"), not SAN ("e4"). Chess.js verbose moves must be used to resolve SAN to squares.
- **Using arrowOptions.opacity for frequency scaling:** Global opacity applies uniformly to all arrows. Use RGBA alpha in the `color` string instead.
- **Using useMutation for explorer:** The explorer is a live-updating view (not a user action), so `useQuery` with auto-refetch is correct. `useMutation` requires manual trigger.
- **Calling makeMove with SAN:** `useChessGame.makeMove` accepts `(sourceSquare, targetSquare)` — square coordinates. Cannot pass SAN directly; must resolve via chess.js verbose moves first.
- **Omitting clearArrowsOnPositionChange: false:** Without this, react-chessboard clears externally-supplied arrows when position changes, making arrows disappear immediately after clicking a move row.
- **Relying on positionFilterActive gating:** The CONTEXT.md decision specifies the explorer is always visible (even from the starting position). Do not gate the explorer behind `positionFilterActive`.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Arrow rendering on board | Custom SVG overlay | react-chessboard `arrows` prop | Already built into the library with SVG arrowheads, path math, board coordinate mapping |
| Auto-refetch on state change | Manual useEffect + setState | TanStack `useQuery` with reactive key | Query key change triggers automatic refetch, handles loading/error/stale states |
| WDL color scheme | New color constants | Export from existing WDLBar.tsx | Single source of truth; colors already tuned for the app's dark theme |
| Hover tooltip | Custom CSS :hover + div | shadcn/ui `Tooltip` + `TooltipTrigger` + `TooltipContent` | Accessible, consistent with existing UI, handles positioning automatically |
| SAN to squares | Manual regex parsing | chess.js `moves({ verbose: true })` | Already installed; handles all edge cases (castling, en passant, promotion) |

**Key insight:** All the hard parts are already solved by installed libraries. Phase 13 is mostly wiring.

## Common Pitfalls

### Pitfall 1: clearArrowsOnPositionChange Default
**What goes wrong:** Arrows disappear immediately after clicking a move row because react-chessboard (default `clearArrowsOnPositionChange: true`) clears the `arrows` array when the position prop changes.
**Why it happens:** The library assumes user-drawn arrows should be cleared on position change. But externally-computed arrows need to persist (or update) on position change.
**How to avoid:** Always pass `clearArrowsOnPositionChange: false` when supplying the `arrows` prop programmatically.
**Warning signs:** Arrows render initially but vanish the moment any move is played on the board.

### Pitfall 2: makeMove Accepts Squares, Not SAN
**What goes wrong:** Clicking a move row and calling `chess.makeMove(entry.move_san, ...)` — `makeMove` signature is `(sourceSquare: string, targetSquare: string)`.
**Why it happens:** The API returns SAN; `makeMove` takes squares. Mixing them causes silent failure (returns `false`).
**How to avoid:** Resolve SAN to from/to via `chess.moves({ verbose: true })` before calling `makeMove`. Build a lookup map once per position.
**Warning signs:** Click on a move row appears to do nothing; `makeMove` returns `false`.

### Pitfall 3: BigInt Hash Precision
**What goes wrong:** Passing `hashes.fullHash` (BigInt) directly in the TanStack Query key or API call body as a number causes silent precision loss for hashes > 2^53.
**Why it happens:** JavaScript JSON serializes BigInt naively or throws. The backend expects the hash as a decimal string (field_validator handles the conversion).
**How to avoid:** Always call `hashToString(hashes.fullHash)` before putting the hash in the query key or request body. The `hashToString` utility already exists in `@/lib/zobrist`.
**Warning signs:** API returns 0 results for positions that should have matches; backend logs show hash mismatch.

### Pitfall 4: Filter State Drift (match_side / piece filter)
**What goes wrong:** Including `match_side` or `matchSide` in the next-moves request. The `NextMovesRequest` schema has no `match_side` field — it always uses `full_hash`.
**Why it happens:** Copy-paste from `AnalysisRequest` which does have `match_side`.
**How to avoid:** The `useNextMoves` hook must only forward: `time_control`, `platform`, `rated`, `opponent_type`, `recency`, `color`. Omit `match_side` and pagination fields entirely.
**Warning signs:** TypeScript error on unknown field, or 422 response from backend.

### Pitfall 5: Stale Explorer Data on Rapid Navigation
**What goes wrong:** User clicks back/forward quickly; multiple in-flight requests resolve out of order and the explorer shows data for a stale position.
**Why it happens:** TanStack Query by default keeps previous data and may show stale results briefly.
**How to avoid:** Use `placeholderData: keepPreviousData` (TanStack Query v5) or accept brief flash of stale data. The query key changes immediately so the latest response always wins in TanStack's deduplication. Optional: 150ms debounce on position changes before firing the query.
**Warning signs:** Explorer shows N+2 position data while board shows N+1 position.

## Code Examples

Verified patterns from official sources:

### Arrow Type (confirmed from dist/types.d.ts)
```typescript
// Source: react-chessboard/dist/types.d.ts (verified locally)
export type Arrow = {
  startSquare: string;   // e.g. "e2"
  endSquare: string;     // e.g. "e4"
  color: string;         // any CSS color string — use rgba() for per-arrow opacity
};
```

### ChessBoard Props Extension
```typescript
// Source: frontend/src/components/board/ChessBoard.tsx (extend existing interface)
import type { Arrow } from 'react-chessboard/dist/types';

interface ChessBoardProps {
  position: string;
  onPieceDrop: (sourceSquare: string, targetSquare: string) => boolean;
  flipped?: boolean;
  lastMove?: { from: string; to: string } | null;
  arrows?: Arrow[];   // new prop — defaults to []
}
```

### TypeScript API Types Addition
```typescript
// Source: app/schemas/analysis.py NextMovesRequest, NextMoveEntry, NextMovesResponse
// Add to frontend/src/types/api.ts:

export interface NextMovesRequest {
  target_hash: string;         // BigInt as string
  time_control?: TimeControl[] | null;
  platform?: Platform[] | null;
  rated?: boolean | null;
  opponent_type?: OpponentType;
  recency?: Recency | null;
  color?: Color | null;
  sort_by?: 'frequency' | 'win_rate';
}

export interface NextMoveEntry {
  move_san: string;
  game_count: number;
  wins: number;
  draws: number;
  losses: number;
  win_pct: number;
  draw_pct: number;
  loss_pct: number;
  result_hash: string;    // BigInt as string
  result_fen: string;     // board FEN (piece placement only)
  transposition_count: number;
}

export interface NextMovesResponse {
  position_stats: WDLStats;
  moves: NextMoveEntry[];
}
```

### Dashboard Integration Point
```typescript
// Source: frontend/src/pages/Dashboard.tsx rightColumn (insert above positionFilterActive block)
const rightColumn = (
  <div className="flex flex-col gap-4">
    {/* Move Explorer — always shown, auto-fetches */}
    <MoveExplorer
      fullHash={chess.hashes.fullHash}
      position={chess.position}
      filters={filters}
      onMoveClick={(from, to) => chess.makeMove(from, to)}
    />
    {positionFilterActive ? (
      // ... existing analysis result block
    ) : (
      // ... existing default games list
    )}
  </div>
);
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Manual fetch + useEffect | TanStack Query `useQuery` | Established in this project already | Automatic deduplication, caching, background refetch |
| Custom arrow rendering | react-chessboard `arrows` option | Available since react-chessboard v4+ | No custom SVG needed |
| Global arrowOptions.opacity | Per-arrow RGBA color for opacity | react-chessboard v5 limitation | Must encode opacity in color string |

**Deprecated/outdated:**
- `clearArrowsOnPositionChange` default `true`: Fine for user-drawn arrows; override to `false` for programmatic arrows.

## Open Questions

1. **Debounce on position changes for explorer fetch**
   - What we know: TanStack Query fires a new request on every query key change; rapid back/forward navigation could fire many requests.
   - What's unclear: Whether the perceived UX is acceptable without debounce, given the query response should be sub-100ms for typical game counts.
   - Recommendation: Start without debounce. Add 150ms debounce if UX testing reveals visible thrashing. Claude's discretion per CONTEXT.md.

2. **WDL color export from WDLBar.tsx**
   - What we know: Colors are currently `const` declarations (not exported) inside WDLBar.tsx.
   - What's unclear: Whether to export them from WDLBar.tsx or duplicate in MoveExplorer.
   - Recommendation: Export the constants from WDLBar.tsx as named exports, or move them to a shared `wdlColors.ts` helper to avoid duplication. Planner should choose.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (backend only — no frontend test framework detected) |
| Config file | pyproject.toml (pytest config section) |
| Quick run command | `uv run pytest tests/test_analysis_service.py -x` |
| Full suite command | `uv run pytest` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| MEXP-06 | Explorer table renders with Move/Games/Results columns | manual (frontend) | manual browser verification | N/A — no frontend test runner |
| MEXP-07 | Clicking move row advances board and triggers explorer refresh | manual (frontend) | manual browser verification | N/A — no frontend test runner |
| MEXP-11 | Transposition icon appears when transposition_count > game_count | manual (frontend) | manual browser verification | N/A — no frontend test runner |
| MEXP-12 | Board arrows rendered with opacity proportional to frequency | manual (frontend) | manual browser verification | N/A — no frontend test runner |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/test_analysis_service.py -x` (backend not touched in this phase; confirms no regression)
- **Per wave merge:** `uv run pytest`
- **Phase gate:** Full backend suite green + manual browser verification of all 4 MEXP requirements before `/gsd:verify-work`

### Wave 0 Gaps
- No backend test gaps — backend API is complete from Phase 12.
- Frontend has no automated test runner. All MEXP-06/07/11/12 verification is manual.

*(Note: If a frontend test framework is desired for this phase, Vitest + React Testing Library could be added, but this is not in scope per CONTEXT.md constraints.)*

## Sources

### Primary (HIGH confidence)
- `react-chessboard/dist/types.d.ts` — Arrow type shape confirmed: `{startSquare, endSquare, color: string}`
- `react-chessboard/dist/ChessboardProvider.d.ts` — `ChessboardOptions.arrows?: Arrow[]` and `clearArrowsOnPositionChange?: boolean` confirmed
- `react-chessboard/dist/index.js` line 4795-4804 — `defaultArrowOptions` including `opacity: 0.65` (global, not per-arrow), `color` used as SVG `fill` and `stroke`
- `react-chessboard/dist/index.js` line 4856 — `clearArrowsOnPositionChange = true` default confirmed
- `app/schemas/analysis.py` — `NextMovesRequest`, `NextMoveEntry`, `NextMovesResponse` schemas verified
- `frontend/src/hooks/useChessGame.ts` — `makeMove(sourceSquare, targetSquare)` signature confirmed
- `frontend/src/components/results/WDLBar.tsx` — WDL color constants confirmed
- `frontend/src/types/api.ts` — Current type definitions (no NextMoveEntry yet)
- `frontend/src/pages/Dashboard.tsx` — Dashboard layout, `rightColumn` integration point confirmed
- Local node test — chess.js `moves({verbose: true})` returns `{san, from, to}` objects, confirmed

### Secondary (MEDIUM confidence)
- react-chessboard version `5.10.0` — confirmed via `node_modules/react-chessboard/package.json`

### Tertiary (LOW confidence)
- None

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries verified locally in installed node_modules
- Architecture: HIGH — all integration points confirmed by reading actual source files
- Pitfalls: HIGH — identified from type definitions and dist source, not assumptions
- API contract: HIGH — read directly from app/schemas/analysis.py

**Research date:** 2026-03-16
**Valid until:** 2026-04-16 (stable stack — 30 days)
