---
phase: 260317-ppo
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - frontend/src/pages/Openings.tsx
autonomous: true
requirements: [PPO-01, PPO-02]

must_haves:
  truths:
    - "Piece filter on Moves tab is visually greyed out with tooltip explaining it is not applicable"
    - "Played as filter on Moves tab remains enabled and functional"
    - "Piece filter on Games tab works correctly — selecting Mine returns games matching user's pieces only"
    - "Played as and Piece filter on Statistics tab are both visually greyed out with tooltips"
    - "Filter state is preserved when switching tabs (greyed filters just become non-interactive)"
  artifacts:
    - path: "frontend/src/pages/Openings.tsx"
      provides: "Tab-aware filter disable logic + Games tab hash fix"
  key_links:
    - from: "Openings.tsx gamesQuery"
      to: "chess.getHashForAnalysis"
      via: "targetHash computed with matchSide+color instead of raw fullHash"
      pattern: "getHashForAnalysis.*matchSide.*color"
---

<objective>
Fix piece filter interaction across Openings page tabs: (1) disable inapplicable filters per tab with greyed-out styling and tooltips, (2) fix the Games tab empty-results bug where the piece filter hash is ignored.

Purpose: Users are confused by active-looking filters that have no effect, and the "Mine" piece filter returns empty results on the Games tab due to always using fullHash instead of the side-specific hash.
Output: Updated Openings.tsx with tab-aware filter disabling and correct hash computation for the Games tab query.
</objective>

<execution_context>
@/home/aimfeld/.claude/get-shit-done/workflows/execute-plan.md
@/home/aimfeld/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/quick/260317-ppo-fix-piece-filter-interaction-with-games-/260317-ppo-CONTEXT.md
@frontend/src/pages/Openings.tsx
@frontend/src/hooks/useAnalysis.ts
@frontend/src/hooks/useChessGame.ts
@frontend/src/components/ui/tooltip.tsx

<interfaces>
<!-- Key types and contracts the executor needs -->

From frontend/src/hooks/useChessGame.ts:
```typescript
getHashForAnalysis: (matchSide: MatchSide, color: Color) => string;
// resolved === 'white' => whiteHash, 'black' => blackHash, else fullHash
```

From frontend/src/types/api.ts:
```typescript
export type MatchSide = 'mine' | 'opponent' | 'both';
export type Color = 'white' | 'black';
export function resolveMatchSide(matchSide: MatchSide, color: Color): ApiMatchSide;
```

From frontend/src/hooks/useAnalysis.ts:
```typescript
export function usePositionAnalysisQuery(params: {
  targetHash: string;
  filters: FilterState;
  offset: number;
  limit: number;
});
// Already sends match_side via resolveMatchSide(params.filters.matchSide, params.filters.color)
```
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Fix Games tab hash computation to respect piece filter</name>
  <files>frontend/src/pages/Openings.tsx</files>
  <action>
Fix the root cause bug on the Games tab. Currently line ~132 computes:
```
const targetHash = hashToString(chess.hashes.fullHash);
```
This always uses fullHash regardless of the piece filter setting, causing empty results when "Mine" or "Opponent" is selected (because usePositionAnalysisQuery sends the correct match_side but a mismatched fullHash).

Change to:
```
const targetHash = chess.getHashForAnalysis(filters.matchSide, filters.color);
```
This mirrors how Dashboard.tsx computes the hash (line ~169) — it calls getHashForAnalysis which returns whiteHash/blackHash/fullHash based on matchSide+color.

Note: The `hashToString` import can be removed if no other usage remains in this file. Check — it is also used in the nextMoves hook call on line ~94 but that is inside useNextMoves.ts, not here. Actually line 132 is the only usage in Openings.tsx, so remove the `hashToString` import from line 41.

Also update the `debouncedFilters` usage: the targetHash should use non-debounced `filters` for matchSide/color (these are instant toggles, not text inputs) but the gamesQuery already receives `debouncedFilters` for the other filters. Actually, looking at the code, `targetHash` is computed outside the query and `debouncedFilters` is passed separately. The targetHash should react to filter changes immediately since matchSide/color are toggle selections. Keep using `filters.matchSide` and `filters.color` (non-debounced) for the hash computation, which is already the pattern.
  </action>
  <verify>
    <automated>cd /home/aimfeld/Projects/Python/chessalytics/frontend && npx tsc --noEmit 2>&1 | head -20</automated>
  </verify>
  <done>Games tab uses getHashForAnalysis(filters.matchSide, filters.color) instead of raw fullHash. Selecting "Mine" piece filter on Games tab will now query whiteHash/blackHash correctly instead of always fullHash.</done>
</task>

<task type="auto">
  <name>Task 2: Disable inapplicable filters per tab with greyed-out styling and tooltips</name>
  <files>frontend/src/pages/Openings.tsx</files>
  <action>
Add tab-aware disabling of filters in the sidebar section of Openings.tsx (the "Played as + Piece filter" div around line ~278).

1. **Derive disabled states from activeTab:**
```typescript
const pieceFilterDisabled = activeTab === 'explorer' || activeTab === 'statistics';
const playedAsDisabled = activeTab === 'statistics';
```

2. **Import Tooltip components** at the top:
```typescript
import { Tooltip, TooltipContent, TooltipTrigger, TooltipProvider } from '@/components/ui/tooltip';
```

3. **Wrap each filter group conditionally with Tooltip when disabled.** Create a small helper or inline the pattern. When disabled:
   - Add `opacity-50 pointer-events-none` classes to the filter container div
   - Wrap the entire filter group (label + ToggleGroup) in a Tooltip that shows "Not applicable for this tab"
   - The Tooltip wrapper itself must NOT have pointer-events-none (so the tooltip still shows on hover). Apply pointer-events-none only to the inner ToggleGroup.

Implementation pattern for each filter group:
```tsx
<div className={pieceFilterDisabled ? 'opacity-50' : ''}>
  <Tooltip>
    <TooltipTrigger asChild>
      <div>
        <p className="mb-1 text-xs text-muted-foreground">Piece filter</p>
        <ToggleGroup
          type="single"
          value={filters.matchSide}
          onValueChange={(v) => {
            if (pieceFilterDisabled || !v) return;
            setFilters(prev => ({ ...prev, matchSide: v as MatchSide }));
          }}
          variant="outline"
          size="sm"
          disabled={pieceFilterDisabled}
          data-testid="filter-piece-filter"
        >
          ...items...
        </ToggleGroup>
      </div>
    </TooltipTrigger>
    {pieceFilterDisabled && (
      <TooltipContent>Not applicable for this tab</TooltipContent>
    )}
  </Tooltip>
</div>
```

Apply the same pattern for the "Played as" filter using `playedAsDisabled`.

4. **Wrap the filter area in TooltipProvider** (if not already wrapped at a higher level). Check if TooltipProvider exists in the app — if it is in a layout/root component, skip this. Otherwise wrap just the filter flex container:
```tsx
<TooltipProvider>
  <div className="flex flex-wrap gap-x-4 gap-y-3">
    ...
  </div>
</TooltipProvider>
```

5. **Ensure ToggleGroup accepts `disabled` prop.** Check if shadcn ToggleGroup passes disabled to children. If not, also pass `disabled` to each ToggleGroupItem. The `onValueChange` guard already prevents state changes, but visual disabled state is also needed.

6. **Add data-testid** attributes: `data-testid="filter-piece-filter-disabled"` when disabled (or keep existing testid and add `aria-disabled="true"`).

IMPORTANT: Do NOT reset matchSide/color values when switching tabs. The filter state should persist — only the interactivity changes. This ensures switching back to Games tab retains the user's previous filter selection.
  </action>
  <verify>
    <automated>cd /home/aimfeld/Projects/Python/chessalytics/frontend && npx tsc --noEmit 2>&1 | head -20 && npm run build 2>&1 | tail -5</automated>
  </verify>
  <done>Piece filter is greyed out with tooltip on Moves and Statistics tabs. Played as filter is greyed out with tooltip on Statistics tab. Both filters remain fully interactive on Games tab. Filter state persists across tab switches. Build succeeds with no type errors.</done>
</task>

</tasks>

<verification>
1. TypeScript compiles without errors: `cd frontend && npx tsc --noEmit`
2. Production build succeeds: `cd frontend && npm run build`
3. Lint passes: `cd frontend && npm run lint`
</verification>

<success_criteria>
- Games tab with "Mine" piece filter selected returns games (not empty results)
- Piece filter is greyed out and shows tooltip on Moves tab and Statistics tab
- Played as filter is greyed out and shows tooltip on Statistics tab
- All filters remain interactive on Games tab
- Filter selections persist when switching between tabs
- No TypeScript errors, build succeeds
</success_criteria>

<output>
After completion, create `.planning/quick/260317-ppo-fix-piece-filter-interaction-with-games-/260317-ppo-SUMMARY.md`
</output>
