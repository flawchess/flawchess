---
phase: quick
plan: 260328-mov
type: execute
wave: 1
depends_on: []
files_modified:
  - frontend/src/pages/Endgames.tsx
  - frontend/src/pages/Openings.tsx
  - frontend/src/components/results/GameCardList.tsx
autonomous: true
requirements: []
must_haves:
  truths:
    - "Endgames Games subtab shows a WDL chart bar for the selected endgame type, between the dropdown and the game list"
    - "Games-matched line in both Openings and Endgames Games tabs reads 'x of y games (p%) matched' with the percent number visually prominent"
  artifacts:
    - path: "frontend/src/pages/Endgames.tsx"
      provides: "WDL chart in Games tab using statsData category lookup"
    - path: "frontend/src/pages/Openings.tsx"
      provides: "Updated games-matched format"
    - path: "frontend/src/components/results/GameCardList.tsx"
      provides: "Updated default matchLabel format with highlighted percent"
  key_links:
    - from: "Endgames.tsx gamesContent"
      to: "WDLChartRow"
      via: "renders WDLChartRow with category stats for selectedCategory"
      pattern: "WDLChartRow.*data.*selectedCategory"
---

<objective>
Two UI improvements to the Games subtab across Openings and Endgames pages:
1. Add a WDL chart bar in the Endgames Games subtab for the currently selected endgame type
2. Standardize games-matched reporting to "x of y games (p%) matched" with the percent number visually prominent (larger/bolder)

Purpose: Consistent WDL visibility in Games tabs and clearer games-matched statistics
Output: Updated Endgames.tsx, Openings.tsx, GameCardList.tsx
</objective>

<execution_context>
@.claude/get-shit-done/workflows/execute-plan.md
@.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@frontend/src/pages/Endgames.tsx
@frontend/src/pages/Openings.tsx
@frontend/src/components/results/GameCardList.tsx
@frontend/src/components/charts/WDLChartRow.tsx
@frontend/src/types/endgames.ts
@frontend/src/types/api.ts
</context>

<interfaces>
<!-- Key types the executor needs -->

From frontend/src/types/endgames.ts:
```typescript
export interface EndgameCategoryStats {
  endgame_class: EndgameClass;
  label: string;
  wins: number; draws: number; losses: number; total: number;
  win_pct: number; draw_pct: number; loss_pct: number;
  conversion: ConversionRecoveryStats;
}
// EndgameCategoryStats satisfies WDLRowData interface

export interface EndgameGamesResponse {
  games: GameRecord[];
  matched_count: number;
  offset: number;
  limit: number;
}
// Note: NO stats/WDL in EndgameGamesResponse — must use statsData.categories lookup
```

From frontend/src/types/api.ts:
```typescript
export interface AnalysisResponse {
  stats: WDLStats;  // WDL stats available directly in Openings gamesData
  games: GameRecord[];
  matched_count: number;
  offset: number;
  limit: number;
}
```

From frontend/src/components/charts/WDLChartRow.tsx:
```typescript
interface WDLChartRowProps {
  data: WDLRowData;
  label?: string;
  barHeight?: 'h-5' | 'h-6';
  testId?: string;
  // ... other optional props
}
```
</interfaces>

<tasks>

<task type="auto">
  <name>Task 1: Add WDL chart to Endgames Games subtab</name>
  <files>frontend/src/pages/Endgames.tsx</files>
  <action>
In `Endgames.tsx`, modify `gamesContent` to show a WDL chart bar for the selected endgame type between the endgame type dropdown and the game list:

1. Derive the selected category's WDL stats from `statsData.categories` by finding the entry matching `selectedCategory`:
   ```typescript
   const selectedCategoryStats = statsData?.categories.find(c => c.endgame_class === selectedCategory);
   ```

2. In `gamesContent`, after the `endgameTypeDropdown` div and before the loading/empty/data conditionals, add a WDL chart row wrapped in a charcoal-texture container (same pattern as Openings Moves tab WDL):
   ```tsx
   {selectedCategoryStats && selectedCategoryStats.total > 0 && (
     <div className="charcoal-texture rounded-md p-4">
       <WDLChartRow
         data={selectedCategoryStats}
         label={`${ENDGAME_CLASS_LABELS[selectedCategory]} Endgame Results`}
         barHeight="h-6"
         testId="wdl-endgame-games"
       />
     </div>
   )}
   ```

3. Add `WDLChartRow` to the imports (from `@/components/charts/WDLChartRow`).

4. Also update the `matchLabel` prop passed to `GameCardList` in the endgame gamesContent to use the new format (see Task 2 pattern):
   Format: `"x of y games (P%) matched"` where P% is highlighted.
   Replace the current `matchLabel` with:
   ```tsx
   matchLabel={statsData ? (
     <>
       {gamesData.matched_count} of {statsData.endgame_games} games{' '}
       (<span className="text-base font-semibold text-foreground">{(gamesData.matched_count / statsData.endgame_games * 100).toFixed(1)}%</span>)
       {' '}matched
     </>
   ) : undefined}
   ```
   Note: The percent number gets `text-base font-semibold text-foreground` to make it visually prominent (larger than surrounding text-sm, bold, foreground color).
  </action>
  <verify>
    <automated>cd /home/aimfeld/Projects/Python/flawchess && npm run build --prefix frontend 2>&1 | tail -5</automated>
  </verify>
  <done>Endgames Games subtab shows WDL chart for selected endgame type. Games-matched line uses new "x of y games (P%) matched" format with prominent percent.</done>
</task>

<task type="auto">
  <name>Task 2: Update Openings Games tab and GameCardList default games-matched format</name>
  <files>frontend/src/pages/Openings.tsx, frontend/src/components/results/GameCardList.tsx</files>
  <action>
Two files need the new "x of y games (P%) matched" format where percent is visually prominent:

**GameCardList.tsx** — Update the default `matchLabel` fallback (lines 87-92):
Change the default from:
```tsx
<span className="font-medium text-foreground">{matchedCount}</span> of{' '}
<span className="font-medium text-foreground">{totalGames}</span> games matched
```
To:
```tsx
{matchedCount} of {totalGames} games{' '}
(<span className="text-base font-semibold text-foreground">
  {totalGames > 0 ? (matchedCount / totalGames * 100).toFixed(1) : '0.0'}%
</span>){' '}matched
```
The surrounding `<p>` already has `text-sm text-muted-foreground`, so the percent span with `text-base font-semibold text-foreground` will stand out — slightly larger font, bold, and foreground color vs muted.

**Openings.tsx** — The Openings Games tab currently uses `GameCardList` without a custom `matchLabel` (line 490-497), so it will pick up the new default format automatically. No changes needed in Openings.tsx.

Verify the Openings Moves tab WDL (lines 433-444) is unaffected — it uses `WDLChartRow` directly, not `GameCardList`, so no change there.
  </action>
  <verify>
    <automated>cd /home/aimfeld/Projects/Python/flawchess && npm run build --prefix frontend 2>&1 | tail -5</automated>
  </verify>
  <done>GameCardList default matchLabel shows "x of y games (P%) matched" with prominent percent. Openings Games tab inherits the new format. Endgames Games tab uses custom matchLabel with same pattern.</done>
</task>

</tasks>

<verification>
- `npm run build --prefix frontend` succeeds with no errors
- Endgames Games subtab shows WDL chart bar for selected endgame type between dropdown and game list
- Games-matched line in both pages reads "x of y games (P%) matched" with percent visually prominent
</verification>

<success_criteria>
- WDL chart visible in Endgames Games subtab, driven by statsData category lookup for selected type
- Games-matched format consistent across both Openings and Endgames Games tabs
- Percent number is visually prominent (text-base font-semibold text-foreground vs surrounding text-sm text-muted-foreground)
- Frontend builds successfully
</success_criteria>

<output>
After completion, create `.planning/quick/260328-mov-endgames-games-subtab-wdl-chart-games-ma/260328-mov-SUMMARY.md`
</output>
