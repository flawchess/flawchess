---
phase: quick-23
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - frontend/src/types/api.ts
  - frontend/src/types/position_bookmarks.ts
  - frontend/src/components/filters/FilterPanel.tsx
  - frontend/src/pages/Dashboard.tsx
  - frontend/src/hooks/useChessGame.ts
autonomous: true
requirements: [quick-23]

must_haves:
  truths:
    - "Played as toggle options show color circle icons (filled white circle for White, filled black circle for Black)"
    - "Match side filter shows Mine/Opponent/Both labels instead of White/Black/Both"
    - "When played as White, Mine resolves to white_hash and Opponent resolves to black_hash"
    - "When played as Black, Mine resolves to black_hash and Opponent resolves to white_hash"
    - "Bookmarks save and load match_side correctly with the new mine/opponent/both values"
  artifacts:
    - path: "frontend/src/pages/Dashboard.tsx"
      provides: "Color icons on Played as, Mine/Opponent/Both on Match side"
    - path: "frontend/src/types/api.ts"
      provides: "Updated MatchSide type"
  key_links:
    - from: "frontend/src/pages/Dashboard.tsx"
      to: "frontend/src/hooks/useChessGame.ts"
      via: "getHashForAnalysis resolves mine/opponent based on color"
      pattern: "resolveMatchSide|getHashForAnalysis"
---

<objective>
Add color circle icons to the "Played as" toggle options and change the "Match side" filter
from White/Black/Both to Mine/Opponent/Both. The logic change: "mine" refers to the user's
color (from Played as), "opponent" refers to the opposite color. The backend API continues
to receive white/black/full -- the frontend resolves mine/opponent to the correct hash column
based on the selected color.

Purpose: More intuitive UX -- when you switch from playing as White to Black, "mine"
automatically refers to the correct side without the user needing to also switch match side.

Output: Updated Dashboard with color icons and relabeled match side filter.
</objective>

<execution_context>
@/home/aimfeld/.claude/get-shit-done/workflows/execute-plan.md
@/home/aimfeld/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@frontend/src/pages/Dashboard.tsx
@frontend/src/types/api.ts
@frontend/src/types/position_bookmarks.ts
@frontend/src/hooks/useChessGame.ts
@frontend/src/components/filters/FilterPanel.tsx
@frontend/src/components/position-bookmarks/PositionBookmarkCard.tsx

<interfaces>
<!-- Key types and contracts the executor needs -->

From frontend/src/types/api.ts:
```typescript
export type MatchSide = 'white' | 'black' | 'full';  // CHANGE to 'mine' | 'opponent' | 'both'
export type Color = 'white' | 'black';
```

From frontend/src/hooks/useChessGame.ts:
```typescript
getHashForAnalysis: (matchSide: MatchSide) => string;
// Currently maps white->whiteHash, black->blackHash, full->fullHash
// CHANGE: accept new MatchSide + color param to resolve mine/opponent
```

From frontend/src/types/position_bookmarks.ts:
```typescript
match_side: 'white' | 'black' | 'full';  // CHANGE to 'mine' | 'opponent' | 'both'
```

Backend HASH_COLUMN_MAP (NOT changing):
```python
HASH_COLUMN_MAP = {
    "white": GamePosition.white_hash,
    "black": GamePosition.black_hash,
    "full": GamePosition.full_hash,
}
```

Backend AnalysisRequest.match_side (NOT changing):
```python
match_side: Literal["white", "black", "full"] = "full"
```
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Update MatchSide type and add resolution utility</name>
  <files>
    frontend/src/types/api.ts,
    frontend/src/types/position_bookmarks.ts,
    frontend/src/hooks/useChessGame.ts
  </files>
  <action>
1. In `frontend/src/types/api.ts`:
   - Change `MatchSide` type from `'white' | 'black' | 'full'` to `'mine' | 'opponent' | 'both'`
   - Add a new exported type: `export type ApiMatchSide = 'white' | 'black' | 'full';`
   - Add a resolver function:
     ```typescript
     export function resolveMatchSide(matchSide: MatchSide, color: Color): ApiMatchSide {
       if (matchSide === 'both') return 'full';
       if (matchSide === 'mine') return color;  // mine when white = 'white', mine when black = 'black'
       // opponent
       return color === 'white' ? 'black' : 'white';
     }
     ```
   - Update `AnalysisRequest.match_side` to use `ApiMatchSide` (since this is what goes to the backend)

2. In `frontend/src/types/position_bookmarks.ts`:
   - Update `match_side` in `PositionBookmarkResponse`, `PositionBookmarkCreate`, and `TimeSeriesBookmarkParam` from `'white' | 'black' | 'full'` to `'mine' | 'opponent' | 'both'`

3. In `frontend/src/hooks/useChessGame.ts`:
   - Update `getHashForAnalysis` signature to take `(matchSide: MatchSide, color: Color)` instead of just `(matchSide: MatchSide)`
   - Import `resolveMatchSide` and `Color` from `@/types/api`
   - Inside `getHashForAnalysis`, first resolve: `const resolved = resolveMatchSide(matchSide, color)` then use resolved to pick the hash (resolved === 'white' -> whiteHash, 'black' -> blackHash, 'full' -> fullHash)

NOTE: Existing bookmarks in the DB store match_side as 'white'/'black'/'full'. We need to handle backward compatibility. In `handleLoadBookmark` in Dashboard.tsx (Task 2), convert legacy values when loading: 'white'->'mine' is WRONG because we don't know if 'white' meant "my side" or literally white. Since this is a small personal app and quick-22 just removed the Any option, the simplest approach is: treat stored 'full' as 'both', and for 'white'/'black' in existing bookmarks, map them to 'mine' if they match the bookmark's color, 'opponent' if they don't match. Actually the cleanest approach: add a migration helper in the resolveMatchSide area:
```typescript
export function legacyToMatchSide(apiSide: string): MatchSide {
  if (apiSide === 'full') return 'both';
  // Legacy 'white'/'black' stored in bookmarks - treat as 'mine'
  // since users typically bookmarked their own side
  return 'mine';
}
```
Use this in bookmark loading/response handling.
  </action>
  <verify>
    <automated>cd /home/aimfeld/Projects/Python/chessalytics/frontend && npx tsc --noEmit 2>&1 | head -30</automated>
  </verify>
  <done>MatchSide type is mine/opponent/both throughout frontend, resolveMatchSide converts to API format, getHashForAnalysis accepts color parameter, legacy bookmark values handled</done>
</task>

<task type="auto">
  <name>Task 2: Add color icons to Played as and relabel Match side in Dashboard</name>
  <files>
    frontend/src/pages/Dashboard.tsx,
    frontend/src/components/filters/FilterPanel.tsx,
    frontend/src/components/position-bookmarks/PositionBookmarkCard.tsx
  </files>
  <action>
1. In `frontend/src/pages/Dashboard.tsx`:
   - Update the "Played as" ToggleGroup items (lines 326-327) to include color circle icons:
     - White option: Add a small filled white circle before "White" text. Use an inline SVG circle or a span with CSS: `<span className="inline-block h-3 w-3 rounded-full border border-foreground bg-white mr-1" />` before "White"
     - Black option: Add a small filled black circle before "Black" text: `<span className="inline-block h-3 w-3 rounded-full bg-black mr-1" />` (or bg-foreground for dark theme compatibility) before "Black". Actually for dark theme where bg is dark, use: white circle = `border border-muted-foreground bg-white`, black circle = `bg-foreground` (foreground is light in dark theme... no). Better approach: white = `border border-muted-foreground bg-white`, black = `bg-zinc-900 dark:bg-white` NO. Simplest correct approach for dark-only theme (per CLAUDE.md "Nova/Radix theme locked, dark-only"): white circle = `border border-muted-foreground bg-white`, black circle = `bg-zinc-800 border border-muted-foreground` (dark fill visible against dark bg due to border). Actually since it's dark-only: white = white fill is clearly visible on dark bg. Black = needs to be visible on dark bg too. Use the Unicode approach matching BookmarkCard: ● (U+25CF) for white text, ○ (U+25CB) could work but let's use proper styled spans. Final approach: White = `<span className="inline-block h-3 w-3 rounded-full border border-muted-foreground bg-white" />`, Black = `<span className="inline-block h-3 w-3 rounded-full border border-muted-foreground bg-zinc-900" />`. The border makes both visible on dark background.

   - Update the "Match side" ToggleGroup (lines 332-344):
     - Change values from `white`/`black`/`full` to `mine`/`opponent`/`both`
     - Change labels from "White"/"Black"/"Both" to "Mine"/"Opponent"/"Both"
     - Update data-testid values: `filter-match-side-mine`, `filter-match-side-opponent`, `filter-match-side-both`
     - Update the onValueChange handler to cast `v as MatchSide` (already correct since MatchSide is now mine/opponent/both)

   - Update `handleAnalyze` and `handlePageChange`: where `match_side: filters.matchSide` is sent to the API, resolve it first:
     ```typescript
     match_side: resolveMatchSide(filters.matchSide, filters.color),
     ```
     Import `resolveMatchSide` from `@/types/api`.

   - Update `chess.getHashForAnalysis(filters.matchSide)` calls to include color: `chess.getHashForAnalysis(filters.matchSide, filters.color)`

   - Update `handleBookmarkSave`: the bookmark save sends `match_side: matchSide` which is now mine/opponent/both. This is fine since the DB will store the new values.

   - Update `handleLoadBookmark`: when loading a bookmark, convert legacy match_side values:
     ```typescript
     import { legacyToMatchSide } from '@/types/api';
     // In handleLoadBookmark:
     setFilters(prev => ({ ...prev, color: bkm.color ?? 'white', matchSide: legacyToMatchSide(bkm.match_side) }));
     ```

   - Update `DEFAULT_FILTERS` in FilterPanel.tsx: change `matchSide: 'full'` to `matchSide: 'both'`

2. In `frontend/src/components/filters/FilterPanel.tsx`:
   - Update `DEFAULT_FILTERS.matchSide` from `'full'` to `'both'`
   - No other changes needed since FilterPanel doesn't render Played as or Match side (those are in Dashboard)

3. In `frontend/src/components/position-bookmarks/PositionBookmarkCard.tsx`:
   - No changes needed (it displays color indicator from bookmark.color which is still white/black, not match_side)

4. In `frontend/src/pages/Openings.tsx`:
   - Where bookmarks' match_side is passed to the time-series API, resolve it:
     ```typescript
     match_side: resolveMatchSide(b.match_side as MatchSide, b.color as Color),
     ```
     This converts the stored mine/opponent/both to white/black/full for the backend API.
     Import resolveMatchSide, MatchSide, Color from @/types/api. Handle legacy stored values with legacyToMatchSide if needed.
  </action>
  <verify>
    <automated>cd /home/aimfeld/Projects/Python/chessalytics/frontend && npx tsc --noEmit && npm run build 2>&1 | tail -5</automated>
  </verify>
  <done>Played as toggle shows color circle icons next to White/Black labels. Match side filter shows Mine/Opponent/Both. API calls correctly resolve mine/opponent to white/black based on the selected color. Legacy bookmarks load correctly.</done>
</task>

</tasks>

<verification>
1. TypeScript compiles without errors: `cd frontend && npx tsc --noEmit`
2. Frontend builds successfully: `cd frontend && npm run build`
3. Lint passes: `cd frontend && npm run lint`
</verification>

<success_criteria>
- Played as toggle items show white/black circle icons next to text labels
- Match side filter displays "Mine", "Opponent", "Both" instead of "White", "Black", "Both"
- When Played as = White and Match side = Mine, analysis uses white_hash
- When Played as = Black and Match side = Mine, analysis uses black_hash
- When Played as = White and Match side = Opponent, analysis uses black_hash
- Existing bookmarks with legacy match_side values (white/black/full) load correctly
- Frontend builds and lints cleanly
</success_criteria>

<output>
After completion, create `.planning/quick/23-add-color-icons-to-played-as-options-and/23-SUMMARY.md`
</output>
