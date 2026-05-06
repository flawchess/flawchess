---
quick_id: 260506-rtk
type: execute
mode: quick
wave: 1
depends_on: []
files_modified:
  - frontend/src/components/stats/OpeningStatsCard.tsx
  - frontend/src/components/stats/OpeningStatsSection.tsx
  - frontend/src/pages/Openings.tsx
  - frontend/src/components/stats/MostPlayedOpeningsTable.tsx
  - frontend/src/components/stats/__tests__/MostPlayedOpeningsTable.test.tsx
  - frontend/src/components/stats/__tests__/OpeningStatsCard.test.tsx
autonomous: true
must_haves:
  truths:
    - On desktop (lg+), the Openings -> Stats subtab renders white openings on the left column and black openings on the right column, mirroring the Openings -> Insights subtab.
    - Each opening (bookmark or most-played) renders as a card with a permanent inline miniboard on the left and stacked content on the right — header (name + ECO), WDL chart, eval bullet chart, and Moves + Games links — replacing the previous list/table layout and hover-only minimap.
    - The Moves link routes to the Move Explorer for that opening, and the Games link routes to the Games tab filtered to the opening, identically to the existing Stats-tab behavior.
    - On mobile, the same card component renders in a single column (existing single-column stack of bookmark + most-played sections preserved), with no separate table/row variant.
    - The hover-only `MinimapPopover` and the `MobileMostPlayedRows` helper are no longer referenced from the Stats tab. Any newly dead exports/components are deleted (knip clean).
    - `npm run lint`, `npm run knip`, and `npm test` all pass.
  artifacts:
    - path: frontend/src/components/stats/OpeningStatsCard.tsx
      provides: New card component used by the Stats subtab (one per opening row).
    - path: frontend/src/components/stats/OpeningStatsSection.tsx
      provides: Section wrapper that lays out cards in 2 columns (white left / black right) on lg+, single column on mobile.
    - path: frontend/src/pages/Openings.tsx
      provides: `statisticsContent` block updated to use OpeningStatsSection for both Bookmarks and Most-Played, dropping the desktop table + mobile rows split.
  key_links:
    - from: frontend/src/components/stats/OpeningStatsCard.tsx
      to: frontend/src/components/board/LazyMiniBoard.tsx
      via: permanent inline miniboard (no hover popover)
    - from: frontend/src/components/stats/OpeningStatsCard.tsx
      to: frontend/src/components/charts/WDLChartRow.tsx
      via: WDL chart (replaces "You score..." prose)
    - from: frontend/src/components/stats/OpeningStatsCard.tsx
      to: frontend/src/components/charts/MiniBulletChart.tsx
      via: eval bullet (mirrors MostPlayedOpeningsTable bullet column, anchored on 0 cp with per-color baseline tick)
    - from: frontend/src/components/stats/OpeningStatsCard.tsx
      to: frontend/src/components/insights/BulletConfidencePopover.tsx
      via: eval confidence info-icon next to bullet
    - from: frontend/src/components/stats/OpeningStatsSection.tsx
      to: frontend/src/components/stats/OpeningStatsCard.tsx
      via: 2-column grid (white col-start-1, black col-start-2 at lg:; grid-cols-1 mobile)
---

<objective>
Replace the Openings -> Stats subtab list/table layout with a 2-column card grid that mirrors Openings -> Insights. Each opening (bookmark + most-played) renders as a card with a permanent inline miniboard, the WDL chart (replacing the "You score X%" prose), the existing eval bullet chart, and Moves + Games links. White openings stack in the left column, black openings in the right column on lg+; single column on mobile.

Pure frontend refactor: no backend, no migrations, no API changes. Reuse existing components — `LazyMiniBoard`, `WDLChartRow`, `MiniBulletChart`, `BulletConfidencePopover`, the score-zone helpers from `lib/openingStatsZones.ts`, and the `OpeningFindingCard` card-shell visual conventions (border-left in zone color, charcoal-texture, rounded, padding).

Output:
- New `OpeningStatsCard` component (the single card used for both bookmarks and most-played rows; takes an `OpeningWDL`).
- New `OpeningStatsSection` component (white-left / black-right 2-column grid wrapper).
- `statisticsContent` in `Openings.tsx` rewritten to use the new section + card.
- `MostPlayedOpeningsTable` and the inline `MobileMostPlayedRows` helper deleted (no remaining references; knip clean).
- Tests: drop the obsolete `MostPlayedOpeningsTable.test.tsx`, add a focused `OpeningStatsCard.test.tsx` covering the desktop card (board + WDL + eval text + bullet + Moves/Games + low-data muting).
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
</execution_context>

<context>
@CLAUDE.md
@frontend/src/pages/Openings.tsx
@frontend/src/components/insights/OpeningFindingCard.tsx
@frontend/src/components/insights/OpeningInsightsBlock.tsx
@frontend/src/components/stats/MostPlayedOpeningsTable.tsx
@frontend/src/components/stats/MinimapPopover.tsx
@frontend/src/components/board/LazyMiniBoard.tsx
@frontend/src/components/charts/WDLChartRow.tsx
@frontend/src/components/charts/MiniBulletChart.tsx
@frontend/src/components/insights/BulletConfidencePopover.tsx
@frontend/src/lib/openingStatsZones.ts
@frontend/src/lib/clockFormat.ts
@frontend/src/lib/theme.ts
@frontend/src/types/stats.ts

<interfaces>
<!-- Key types and contracts the executor uses. Extracted from codebase. -->

From `frontend/src/types/stats.ts`:
```typescript
export interface OpeningWDL {
  opening_eco: string;
  opening_name: string;
  display_name: string;       // carries "vs. " prefix for off-color rows
  label: string;
  pgn: string;
  fen: string;
  full_hash: string;
  wins: number; draws: number; losses: number; total: number;
  win_pct: number; draw_pct: number; loss_pct: number;
  avg_eval_pawns?: number | null;
  eval_ci_low_pawns?: number | null;
  eval_ci_high_pawns?: number | null;
  eval_n: number;
  eval_p_value?: number | null;
  eval_confidence: 'low' | 'medium' | 'high';
}
```

From `frontend/src/components/charts/WDLChartRow.tsx` (key props):
```typescript
interface WDLChartRowProps {
  data: WDLRowData;            // wins/draws/losses/total + pcts
  showSegmentCounts?: boolean; // we'll pass false to keep cards compact
  testId?: string;
}
```
The `data` shape is what `OpeningWDL` already exposes (wins/draws/losses/total/win_pct/draw_pct/loss_pct).

From `frontend/src/components/charts/MiniBulletChart.tsx` — already used inline in `MostPlayedOpeningsTable.tsx` lines 92-101 with these props: `value`, `ciLow`, `ciHigh`, `tickPawns`, `neutralMin`, `neutralMax`, `domain`, `ariaLabel`. Reuse the exact call shape from there.

From `frontend/src/lib/openingStatsZones.ts`:
```typescript
export const EVAL_BULLET_DOMAIN_PAWNS: number;
export const EVAL_NEUTRAL_MIN_PAWNS: number;
export const EVAL_NEUTRAL_MAX_PAWNS: number;
export function evalZoneColor(pawns: number): string;
```

From `frontend/src/lib/clockFormat.ts`:
```typescript
export function formatSignedEvalPawns(pawns: number): string; // e.g. "+2.1"
```

From `frontend/src/lib/theme.ts`:
```typescript
export const MIN_GAMES_OPENING_ROW: number; // muting threshold (mute opacity when total < this)
export const UNRELIABLE_OPACITY: number;
```

From `frontend/src/components/board/LazyMiniBoard.tsx`:
```typescript
export function LazyMiniBoard(props: {
  fen: string;
  flipped: boolean;
  size: number;
  arrows?: ReadonlyArray<{ from: string; to: string; color: string }>;
}): JSX.Element;
```

From `frontend/src/components/insights/BulletConfidencePopover.tsx` — used identically to `MostPlayedOpeningsTable.tsx` lines 156-164: `level`, `pValue`, `gameCount`, `evalMeanPawns`, `color`, `testId`.

From `frontend/src/pages/Openings.tsx` — Stats-tab callers (current `statisticsContent` block, lines 1127-1378) pass these section configs:
- `bookmarks-white` / `bookmarks-black` sections (built from `whiteBookmarkRows` / `blackBookmarkRows` via `buildBookmarkRows()`), `onOpenGames = handleOpenBookmarkRow`, `evalBaselinePawns = mostPlayedData?.eval_baseline_pawns_white|black ?? EVAL_BASELINE_PAWNS_WHITE|BLACK`.
- `mpo-white` / `mpo-black` sections (`mostPlayedData.white` / `mostPlayedData.black`), `onOpenGames = (opening, color) => handleOpenGames(opening.pgn, color)`, `evalBaselinePawns = mostPlayedData.eval_baseline_pawns_white|black`.
</interfaces>

<reference_layouts>
- 2-column grid pattern (mirror exactly): see `OpeningInsightsBlock.tsx` `SectionsContent` lines 192-228 — `grid grid-cols-1 lg:grid-cols-2 gap-x-6 gap-y-4` with explicit `lg:col-start-1/2` + `lg:row-start-1/2` so white sections share the left column and black sections share the right column. The Stats-tab equivalent has 2 white sections (Bookmarks, Most Played) and 2 black sections — same shape.
- Card visuals (mirror exactly): see `OpeningFindingCard.tsx` lines 171-209 — `block relative border-l-4 charcoal-texture border border-border/20 rounded px-4 py-4` with `borderLeftColor` driven by score-zone (Stats-tab card uses `evalZoneColor(avg_eval_pawns)` instead of `scoreZoneColor(score)` since the card's primary signal is MG-entry eval, not WDL score; falls back to a neutral border tint when `eval_n === 0`).
- Mobile vs desktop card body: see `OpeningFindingCard.tsx` lines 178-209 — mobile = header full-width on top then `<board + content column>` row; desktop = `<board + content column>` row with header inside the content column. Reuse this two-branch structure verbatim.
- Eval cell behavior (text + bullet + confidence info icon + zone color + low-data muting): see `MostPlayedOpeningsTable.tsx` lines 73-104 (`hasMgEval`, `mgEvalTextContent`, `mgBulletContent`, `BulletConfidencePopover` block) — copy this logic into the new card.
</reference_layouts>

<mobile_decision>
Per CLAUDE.md "Always apply changes to mobile too": the new card replaces both the desktop `MostPlayedOpeningsTable` and the mobile `MobileMostPlayedRows` paths. On mobile the section grid collapses to a single column (matching `OpeningInsightsBlock` `grid-cols-1`), and the card itself uses the same internal mobile layout as `OpeningFindingCard` (header above, board+content row below). No separate `lg:hidden` / `hidden lg:block` Stats branches remain.

Card miniboard sizes match Insights: `MOBILE_BOARD_SIZE = 115`, `DESKTOP_BOARD_SIZE = 110` (extracted as local constants at the top of `OpeningStatsCard.tsx`, mirroring `OpeningFindingCard.tsx` lines 26-27).
</mobile_decision>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Add OpeningStatsCard + OpeningStatsSection components and replace Stats-tab layout</name>
  <files>
    frontend/src/components/stats/OpeningStatsCard.tsx (new)
    frontend/src/components/stats/OpeningStatsSection.tsx (new)
    frontend/src/components/stats/__tests__/OpeningStatsCard.test.tsx (new)
    frontend/src/components/stats/__tests__/MostPlayedOpeningsTable.test.tsx (delete)
    frontend/src/components/stats/MostPlayedOpeningsTable.tsx (delete)
    frontend/src/pages/Openings.tsx
  </files>
  <behavior>
    OpeningStatsCard:
    - Test 1: Renders the LazyMiniBoard with `fen` from the OpeningWDL and `flipped` derived from `color === 'black'`.
    - Test 2: Renders the WDL bar (segments matching win/draw/loss percentages) — assert via `data-testid="opening-stats-card-{idx}-wdl"`.
    - Test 3: When `eval_n > 0` and `avg_eval_pawns` is set, renders the signed pawn text in zone color (e.g. "+2.1"), the MiniBulletChart, and the BulletConfidencePopover info icon. When `eval_n === 0`, renders an em-dash placeholder for both text and bullet (no popover).
    - Test 4: Renders a Moves link (`data-testid="opening-stats-card-{idx}-moves"`) and a Games link (`data-testid="opening-stats-card-{idx}-games"`) that invoke their respective callbacks with the OpeningWDL.
    - Test 5: When `total < MIN_GAMES_OPENING_ROW`, applies `UNRELIABLE_OPACITY` muting on the card body (style attribute).
    - Test 6: Border-left color comes from `evalZoneColor(avg_eval_pawns)` when MG eval is present; falls back to a neutral border-token color (e.g. `border` token via `borderLeftColor: 'transparent'` or class — pick one consistent rule; document inline) when `eval_n === 0`.

    OpeningStatsSection: smoke-rendered indirectly via Openings.tsx; no direct test required (the 2-column grid is a thin CSS shell mirroring OpeningInsightsBlock — already covered by visual check).
  </behavior>
  <action>
    1. Create `frontend/src/components/stats/OpeningStatsCard.tsx`:
       - Props: `{ opening: OpeningWDL; color: 'white' | 'black'; idx: number; testIdPrefix: string; onOpenMoves: (o: OpeningWDL, color: 'white'|'black') => void; onOpenGames: (o: OpeningWDL, color: 'white'|'black') => void; evalBaselinePawns: number; }`. The `onOpenMoves` callback is the new "Moves" link handler — see step 4 below for the routing target.
       - Compute `hasMgEval`, `mgEvalTextContent`, `mgBulletContent` exactly as in `MostPlayedOpeningsTable.tsx` lines 73-104 (copy the logic).
       - Compute `borderLeftColor` from `evalZoneColor(avg_eval_pawns)` when `hasMgEval`, otherwise leave a neutral fallback (use `'transparent'` so the `border-l-4` reserves space without color, OR fall back to a muted theme token — pick one and add a one-line code comment explaining).
       - Render exactly the JSX shape of `OpeningFindingCard.tsx` lines 171-209 (mobile then desktop branch), but replace:
         * the prose line ("You score X% as <Color> after <SAN>") with `<WDLChartRow data={{wins, draws, losses, total, win_pct, draw_pct, loss_pct}} showSegmentCounts={false} testId={...wdl}/>`
         * the score bullet line with the eval bullet block (text + bullet + BulletConfidencePopover) — same JSX as `MostPlayedOpeningsTable.tsx` lines 150-174 but stacked vertically inside the card content column.
         * the links row: keep the same Moves + Games button shape (ArrowRightLeft icon + "Moves" label, Swords icon + "{n} Games" label) with `data-testid` `opening-stats-card-{idx}-moves` and `opening-stats-card-{idx}-games`. Both buttons invoke the prop callbacks with `(opening, color)`.
       - Apply `UNRELIABLE_OPACITY` to the card root style when `opening.total < MIN_GAMES_OPENING_ROW` (matches existing MostPlayedOpeningsTable / MobileMostPlayedRows muting rule).
       - Header line shows `display_name` (carries the "vs. " prefix per PRE-01), with `opening_eco` in muted parens when present. No PGN line — the miniboard is the visual identifier now (PGN was a fallback for the table layout).
       - Miniboard sizes: `MOBILE_BOARD_SIZE = 115`, `DESKTOP_BOARD_SIZE = 110` (local constants).

    2. Create `frontend/src/components/stats/OpeningStatsSection.tsx`:
       - Props: `{ heading: ReactNode; sections: ReadonlyArray<{ key: string; color: 'white'|'black'; cards: ReactNode }>; testId: string; }`.
       - Actually a simpler shape works better: this section component represents ONE color column-group (e.g. "White Bookmarks + White Most Played" stacked, or just "White Most Played") and the parent wires two sections side-by-side. Decide between two shapes — pick the one closer to OpeningInsightsBlock SectionsContent:
         * Option A (preferred, matches Insights): `OpeningStatsSection` IS the 2-column grid wrapper and accepts a list of section descriptors `{ key, color, title, cards }`. Layout uses explicit `lg:col-start-1` for white-* keys and `lg:col-start-2` for black-* keys, with `lg:row-start-N` per descriptor index.
         * Option B (simpler): `OpeningStatsSection` is a single titled column-section containing N cards. Caller composes the 2-column grid in Openings.tsx.
       - Choose Option A (mirrors OpeningInsightsBlock most closely). One usage in `statisticsContent`, called twice — once for Bookmarks (when bookmarks exist), once for Most Played — OR called once with all 4 descriptors. Pick whichever yields the cleanest `statisticsContent` (likely: keep the Bookmarks-presence and most-played-loading branches as siblings rendered into the SAME 2-column grid — i.e. ONE OpeningStatsSection call that takes up to 4 descriptors `[white-bookmarks, black-bookmarks, white-mpo, black-mpo]` and assigns rows to `lg:row-start-1` (bookmarks) and `lg:row-start-2` (most-played)).
       - Provide a per-section title (heading from current statisticsContent: "White Opening Bookmarks", "Black Opening Bookmarks", "Most Played Openings as White", "Most Played Openings as Black"), color swatch, and matching InfoPopover where it currently exists.
       - Preserve the existing `INITIAL_VISIBLE_COUNT = 3` collapse/expand behavior from `MostPlayedOpeningsTable` for the Most-Played sections (Bookmarks pass `showAll`).
       - Preserve all existing `data-testid` values on section containers: `bookmarks-white-section`, `bookmarks-black-section`, `mpo-white-section`, `mpo-black-section`, plus `mpo-white-info` / `mpo-black-info` for InfoPopovers.

    3. Update `frontend/src/pages/Openings.tsx`:
       - Replace the `statisticsContent` block (lines 1127-1378). Keep the early branches unchanged: empty-bookmarks message, loading / error branches for `mostPlayedData`. Change ONLY the rendering of the four sections (white-bookmarks, black-bookmarks, mpo-white, mpo-black) to use `OpeningStatsSection` with `OpeningStatsCard` items.
       - Drop both the `<div className="hidden lg:block"><MostPlayedOpeningsTable .../></div>` and `<div className="lg:hidden"><MobileMostPlayedRows .../></div>` branches at all four sites — the new card layout is responsive on its own.
       - Delete the `MobileMostPlayedRows` helper (lines ~146-307) and its no-longer-used local constant `MOBILE_MPO_INITIAL_VISIBLE_COUNT`. Drop now-orphaned imports (`MinimapPopover`, `WDLChartRow`, etc. are still used elsewhere — only remove the ones that become truly unused; `npm run knip` will catch any miss).
       - Wire `onOpenMoves`: clicking the Moves link should route into the Move Explorer for that opening. Mirror `handleOpenFinding`'s pattern from the Insights block. Concretely: set the chess game position from `opening.pgn` (use the existing helper `chess.loadPgnText` or whichever exists — search for the equivalent in `handleOpenGames` / Move Explorer wiring) and `navigate('/openings/explorer')`. If a precise existing helper is not obvious, replicate `handleOpenChartBookmarkGames`'s pattern. Add an inline comment documenting the chosen routing path.

    4. Delete `frontend/src/components/stats/MostPlayedOpeningsTable.tsx` and `frontend/src/components/stats/__tests__/MostPlayedOpeningsTable.test.tsx`.

    5. Add `frontend/src/components/stats/__tests__/OpeningStatsCard.test.tsx` with the 6 test cases listed in `<behavior>`. Mock `LazyMiniBoard`, `MiniBulletChart`, `BulletConfidencePopover`, `Tooltip`, and `WDLChartRow` (or render the real WDLChartRow if it works headless; the existing MostPlayedOpeningsTable test mocks the bullet chart, so follow the same pattern).

    6. Theme constants & data-testids: any new color usage must come from `frontend/src/lib/theme.ts` or `lib/openingStatsZones.ts` (`evalZoneColor`). Every interactive element gets a kebab-case `data-testid` per CLAUDE.md (the testids listed in step 1 already follow the convention).

    7. Verify the change preserves all current Stats-tab behavior:
       - Bookmark cards still render only for bookmarks with games (the empty buildBookmarkRows guard stays).
       - The MG-entry eval text + bullet + zero-anchored centering + per-color baseline tick + low-data muting + confidence popover are all preserved (carry over the full logic from MostPlayedOpeningsTable lines 73-104).
       - The "{N} more / Less" collapse/expand on Most-Played sections still works at INITIAL_VISIBLE_COUNT = 3.
       - The Games link routes to the same destination as before (handleOpenGames(opening.pgn, color) for Most-Played, handleOpenChartBookmarkGames for bookmarks).

    Do not commit — orchestrator handles the docs commit at quick-task wrap-up.
  </action>
  <verify>
    <automated>cd frontend && npm run lint && npm run knip && npm test -- --run</automated>
  </verify>
  <done>
    - `OpeningStatsCard.tsx` and `OpeningStatsSection.tsx` exist with the props and behavior above.
    - `Openings.tsx` `statisticsContent` block uses the new components; the desktop-table / mobile-rows split is gone; `MobileMostPlayedRows` helper is deleted.
    - `MostPlayedOpeningsTable.tsx` and its test file are deleted.
    - `OpeningStatsCard.test.tsx` covers the 6 test cases listed.
    - `npm run lint`, `npm run knip`, and `npm test -- --run` all pass green.
    - Manual smoke (developer's responsibility, post-task): `/openings/stats` shows the 2-column card layout on desktop, single-column stack on mobile; Moves link opens Move Explorer at the position; Games link opens Games tab filtered to the opening; eval text / bullet / confidence popover behave identically to the previous list.
  </done>
</task>

</tasks>

<verification>
- `cd frontend && npm run lint` — zero errors.
- `cd frontend && npm run knip` — zero errors (no dead exports, no unused dependencies).
- `cd frontend && npm test -- --run` — all suites pass; the new `OpeningStatsCard.test.tsx` covers the 6 behaviors above; `Openings.statsBoard.test.tsx` still passes (it tests the board container className, unaffected by the layout change).
- `cd frontend && npm run build` — production build succeeds.
- Manual desktop check at `/openings/stats`: white opening cards in the left column, black in the right, each with permanent inline miniboard + WDL chart + eval bullet + Moves/Games links. Border-left color tracks the MG eval zone.
- Manual mobile check at `/openings/stats`: cards stack in a single column; mobile card layout (header on top, board+content row below) matches the Insights tab's mobile card.
</verification>

<success_criteria>
The Openings -> Stats subtab uses the same 2-column card layout as Openings -> Insights on desktop and a single-column stack on mobile. Each card has a permanent inline miniboard, WDL chart, eval bullet chart with confidence info icon, and Moves + Games links. The previous list/table layout (`MostPlayedOpeningsTable`) and the parallel mobile renderer (`MobileMostPlayedRows`) are deleted; no dead exports remain. All lint, knip, type, and test gates pass.
</success_criteria>

<output>
After completion, create `.planning/quick/260506-rtk-change-openings-stats-page-layout-to-two/260506-rtk-SUMMARY.md` per quick-task convention.
</output>
