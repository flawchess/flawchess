---
phase: quick-260610-vru
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - app/schemas/library.py
  - app/repositories/library_repository.py
  - frontend/src/types/library.ts
  - frontend/src/components/library/FlawCard.tsx
  - frontend/src/components/results/LibraryGameCard.tsx
  - frontend/src/components/results/LibraryGameCardList.tsx
  - frontend/src/pages/library/FlawsTab.tsx
autonomous: true
requirements: [QUICK-LIB-CARD-POLISH]
must_haves:
  truths:
    - "Library Games card shows move count on its own line below the time control"
    - "Library Flaw card shows '<clock icon> mm:ss (Move <n>s)' instead of TC + move count"
    - "Library Flaw card header shows only the opponent's name, prefixed 'vs <color square>'"
    - "Library Flaw card no longer shows the game-termination text"
    - "Library Games tab shows unanalyzed games as half-width cards in a 2-column grid; analyzed games span full width"
    - "Library Flaws tab shows a large 'engine analysis coming soon' message when the user has games but no analyzed flaws"
  artifacts:
    - path: "app/schemas/library.py"
      provides: "clock_seconds + move_seconds on FlawListItem"
      contains: "move_seconds"
    - path: "frontend/src/components/library/FlawCard.tsx"
      provides: "clock+move-time line, opponent-only header, no termination"
    - path: "frontend/src/components/results/LibraryGameCardList.tsx"
      provides: "2-column grid spanning analyzed full-width / unanalyzed half-width"
    - path: "frontend/src/pages/library/FlawsTab.tsx"
      provides: "large no-engine-analysis message styled like EndgamesProcessingState"
  key_links:
    - from: "frontend/src/components/library/FlawCard.tsx"
      to: "FlawListItem.clock_seconds / move_seconds"
      via: "prop read"
      pattern: "clock_seconds|move_seconds"
    - from: "frontend/src/components/results/LibraryGameCardList.tsx"
      to: "GameFlawCard.analysis_state"
      via: "grid col-span branch"
      pattern: "analysis_state"
---

<objective>
Polish the Library page card layout (frontend-first; one small backend data addition).

Four user-visible changes:
1. Games card: move count on its own line, below the time control.
2. Flaw card: replace TC + move count with "<clock icon> mm:ss (Move <seconds>s)"; remove termination text; header shows only the opponent.
3. Games tab: render unanalyzed games as smaller half-width cards in a 2-column grid; analyzed cards span both columns (full width).
4. Flaws tab: when the user has games but no analyzed flaws, show a large "engine analysis only for analyzed Lichess games, coming soon to FlawChess" message styled like the Endgames Stockfish-pending state.

Purpose: tighter, more honest Library cards that surface clock context on flaws and stop hiding unanalyzed games.
Output: schema/repo change for flaw clock+move-time, updated FlawCard, LibraryGameCard, LibraryGameCardList, FlawsTab.
</objective>

<execution_context>
@$HOME/.claude/gsd-core/workflows/execute-plan.md
</execution_context>

<context>
@CLAUDE.md

# Backend flaw query + schema (item 2 needs new fields)
@app/schemas/library.py
@app/repositories/library_repository.py
@app/services/flaws_service.py

# Frontend components to edit
@frontend/src/types/library.ts
@frontend/src/components/library/FlawCard.tsx
@frontend/src/components/results/LibraryGameCard.tsx
@frontend/src/components/results/LibraryGameCardList.tsx
@frontend/src/pages/library/FlawsTab.tsx
@frontend/src/pages/library/GamesTab.tsx

# Patterns to mirror
@frontend/src/components/EndgamesProcessingState.tsx
@frontend/src/components/library/NoAnalysisState.tsx
</context>

<tasks>

<task type="auto">
  <name>Task 1: Add clock_seconds + move_seconds to FlawListItem (backend + TS type)</name>
  <files>app/schemas/library.py, app/repositories/library_repository.py, frontend/src/types/library.ts</files>
  <action>
The Flaw card needs the mover's remaining clock and the seconds spent on the flawed move; FlawListItem does not currently carry them. Add two nullable fields to the `FlawListItem` Pydantic model in app/schemas/library.py: `clock_seconds: float | None` (mover's remaining clock AFTER the flawed move) and `move_seconds: float | None` (time spent on the flawed move, 1dp). Mirror them in the `FlawListItem` interface in frontend/src/types/library.ts with the same nullability and a brief comment matching the EvalPoint field comments.

In app/repositories/library_repository.py `list_flaws` (the function building the `select(GameFlaw, Game, PositionAt, PositionBefore)` base statement around line 253): `PositionAt` (ply=N) already carries `clock_seconds`. Add a third aliased GamePosition `PositionTwoBefore` for ply=N-2 (same-side previous clock), user-scoped exactly like the existing PositionBefore outerjoin but on `ply == GameFlaw.ply - 2`. Include it in the select tuple and unpack it in the row comprehension.

Compute the two fields in the FlawListItem construction:
- `clock_seconds = pos_at.clock_seconds if pos_at else None`.
- `move_seconds`: parse increment from `game.time_control_str` via `parse_base_and_increment` (import from app.services.normalization), then mirror flaws_service `_move_time`: `prev = pos_two_before.clock_seconds`, `curr = pos_at.clock_seconds`; if either is None or increment is None or `prev - curr + increment < 0`, set None; else `round(prev - curr + increment, 1)`. Do NOT import `_move_time` (private); inline the equivalent so the repo has no service dependency, and add a comment pointing to flaws_service `_move_time` as the source of truth for the formula (same-side clock is two plies back — Pitfall 2).

No new index needed (these joins reuse the existing user-scoped game_positions access). Do not change the Games-tab query.
  </action>
  <verify>
    <automated>uv run pytest -n auto tests/ -k "flaw" -x && uv run ty check app/ && ( cd frontend && npx tsc --noEmit )</automated>
  </verify>
  <done>FlawListItem (Pydantic + TS) has clock_seconds and move_seconds; list_flaws populates both from game_positions with the same-side N-2 clock and parsed increment; ty + tsc clean; flaw tests pass.</done>
</task>

<task type="auto">
  <name>Task 2: FlawCard — clock+move-time line, opponent-only header, drop termination</name>
  <files>frontend/src/components/library/FlawCard.tsx</files>
  <action>
Apply item 2 to frontend/src/components/library/FlawCard.tsx (apply to BOTH the desktop single-line and mobile two-line header branches per CLAUDE.md):

(a) Header opponent-only: replace the "■ White (rating) vs □ Black (rating)" markup with just the opponent. The opponent is the side the user is NOT playing: derive from `flaw.user_color` — if user is white, opponent is `blackName`/`blackRating` with the black square glyph "□"; if black, opponent is `whiteName`/`whiteRating` with the white square glyph "■". Render as `vs <square glyph><opponent name> <rating>`. Keep the existing `text-foreground min-w-0 truncate` styling and the "vs" muted prefix styling. Collapse the mobile two-line block into the same single opponent line (no longer two names). Keep `viewGameButton` and `platformIconAndLink` in the header unchanged.

(b) Replace timeControlItem + moveCountItem in the metadata block with a single clock/move-time item. Format: `<Clock icon> mm:ss (Move <n>s)` where mm:ss is the remaining clock from `flaw.clock_seconds` (reuse the m:ss flooring logic from EvalChart `formatClock` — add a small local `formatClock` helper here, do not import the private one from EvalChart) and `<n>` is `flaw.move_seconds` formatted with `.toFixed(1)`. Render the clock part only when `flaw.clock_seconds != null`, and the "(Move Ns)" suffix only when `flaw.move_seconds != null`; if both are null, render nothing for this item (so the metadata block just shows the date). Keep the existing Clock lucide icon. Remove the now-unused Hash import and `plysToFullMoves` import if they become unused after this change.

(c) Remove `terminationItem` from the metadata block and delete its definition. The `resultIndicator` / RESULT_* maps are still used elsewhere? — check: they are only used by terminationItem in this file; if so, remove the now-dead `resultIndicator`, `RESULT_CLASSES`, `RESULT_ICONS`, and the `Equal/Plus/Minus/UserResult` imports they depend on. Knip runs in CI, so leave no dead exports/imports.

The metadata block ends up: line 1 = clock/move-time (when available), line 2 = date. No termination line.
  </action>
  <verify>
    <automated>cd frontend && npm run lint && npx tsc --noEmit && npm test -- --run FlawCard FlawsTab</automated>
  </verify>
  <done>FlawCard header shows only the opponent ("vs <glyph><opponent> <rating>") on desktop and mobile; metadata shows "<clock> mm:ss (Move Ns)" (gracefully omitting parts when null) and the date; no termination text; no dead imports (knip-clean).</done>
</task>

<task type="auto">
  <name>Task 3: Games card move-count line + 2-col Games grid + Flaws no-analysis message</name>
  <files>frontend/src/components/results/LibraryGameCard.tsx, frontend/src/components/results/LibraryGameCardList.tsx, frontend/src/pages/library/FlawsTab.tsx</files>
  <action>
Three independent UI changes:

(1) Item 1 — Games card move count on its own line. In frontend/src/components/results/LibraryGameCard.tsx the `metadata` block currently wraps `timeControlItem` and `moveCountItem` together in one flex-wrap row. Split them so the move count is always on its own line below the time control: render `timeControlItem` on one line and `moveCountItem` on the next line (each as its own flex row), keeping the date and termination lines after. Apply to the single shared `metadata` block (used by both mobile and desktop bodies).

(2) Item 3 — 2-column Games grid. In frontend/src/components/results/LibraryGameCardList.tsx the card stack is currently a single-column `flex flex-col`. Change it to a CSS grid: `grid grid-cols-1 md:grid-cols-2 gap-2` (single column on mobile, 2 columns md+). For each game, give analyzed cards (`game.analysis_state === 'analyzed'`) `md:col-span-2` (full width) and unanalyzed cards (`no_engine_analysis`) `md:col-span-1` (half width). Pass the span class to a wrapping `<div>` around each `<LibraryGameCard>` (do not add a span prop to the card; wrap it). Keep the matched-count row and Pagination unchanged. The LibraryGameCard already renders a compact NoAnalysisState body for unanalyzed games, so half-width is visually appropriate; verify the existing card's internal responsive grid still reads acceptably at half width (it uses `sm:grid-cols-2 lg:grid-cols-3` internally — at half page width the eval-chart column is absent for unanalyzed games so it stays compact). Do NOT change LibraryGameCard's internal layout beyond item (1).

(3) Item 4 — Flaws tab no-engine-analysis message. In frontend/src/pages/library/FlawsTab.tsx, the `noMatchedFlaws`/`noAnalyzedGames` branch currently shows a generic "No flaws matched" EmptyState. The user wants a clear message that engine analysis is only available for analyzed games from Lichess and is "coming soon" on FlawChess. Add a new presentational component `frontend/src/components/library/NoEngineAnalysisFlawsState.tsx` mirroring EndgamesProcessingState's styling (centered column, `min-h`, Cpu icon, h2 + muted paragraphs, `text-sm` minimum, theme-driven colors — reuse the amber Cpu icon treatment). Copy (terse, no em-dashes, user-facing): heading "Engine analysis coming soon", body explaining engine analysis is currently available only for already-analyzed games imported from Lichess, and that native engine analysis on FlawChess is on the way. Give it `data-testid="flaws-no-engine-analysis"`. Render it in place of the existing "No flaws matched" EmptyState ONLY when the user has imported games but zero matched flaws (the existing `noMatchedFlaws` condition). Keep the "No games imported yet" empty state (no-games case) unchanged. Note: this is the same condition the tab already uses; we are swapping the component, not adding new gating. Add the new component to context as a sibling of NoAnalysisState. Keep the matched-count "{n} flaws matched" line.

Apply mobile + desktop parity: FlawsTab renders `mainContent` once and reuses it in both layouts, so the swap covers both. LibraryGameCardList is shared. LibraryGameCard metadata is shared. No separate mobile edits needed beyond confirming the shared blocks render.
  </action>
  <verify>
    <automated>cd frontend && npm run lint && npm run knip && npx tsc --noEmit && npm test -- --run GamesTab FlawsTab LibraryGameCard</automated>
  </verify>
  <done>Games card shows move count on its own line; Games tab renders a 2-col md+ grid with analyzed cards full-width and unanalyzed cards half-width; Flaws tab shows the new large "Engine analysis coming soon" message (testid flaws-no-engine-analysis) when games exist but no flaws matched; lint/knip/tsc/tests clean.</done>
</task>

</tasks>

<verification>
Full local gate before integrating:
- `uv run ruff format app/ tests/ && uv run ruff check app/ tests/ --fix`
- `uv run ty check app/ tests/`
- `uv run pytest -n auto -x`
- `( cd frontend && npm run lint && npm run knip && npm test -- --run )`

Manual smoke (HUMAN-UAT, against existing dev DB — no reset):
1. Library → Games tab: confirm move count sits on its own line under the time control; unanalyzed games appear as half-width cards in a 2-col grid (desktop), analyzed cards full-width.
2. Library → Flaws tab: open a flaw card — header reads "vs <glyph><opponent> <rating>", metadata shows "<clock> mm:ss (Move Ns)" and the date, no termination text.
3. Filter Flaws to a user with no analyzed games (or use a chess.com-only filter): confirm the large "Engine analysis coming soon" message renders.
</verification>

<success_criteria>
- All six must-have truths hold.
- Full backend + frontend gate green (ruff, ty, pytest, lint, knip, tsc, vitest).
- No dead imports/exports (knip clean).
- Changes applied to both mobile and desktop renderers (shared blocks confirmed).
</success_criteria>

<output>
Create `.planning/quick/260610-vru-library-card-layout-polish-games-card-mo/260610-vru-SUMMARY.md` when done.
</output>
