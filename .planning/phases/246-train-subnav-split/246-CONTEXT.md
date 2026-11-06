# Phase 246: Train Subnav Split, Today / Leaderboard / Archive (SEED-261106-gw8) - Context

**Gathered:** 2026-11-06
**Status:** Ready for planning

<domain>
## Phase Boundary

Split the single-column Train landing into three URL-routed tabs: Today at `/train`, Leaderboard at `/train/leaderboard`, Archive at `/train/archive`. Turn the mastered and parked counts into a browsable, paginated archive backed by one new list endpoint.

Out of scope: Retry (SEED-261106-q92), the Stats tab, archive filters. Never list active puzzles with an Analyze button, because seeing the solution before the next review defeats spaced repetition.

</domain>

<decisions>
## Implementation Decisions

### Carried forward from SEED-261106-gw8 (locked, not re-discussed)
- **D-01:** Tabs and URLs as above. `/train` must keep working for reminders, PWA and nav. Archive keeps its name; statistics get a separate fourth Stats tab later. Desktop and mobile follow the `TabsList variant="brand"` pattern.
- **D-02:** Today holds the streak card with Start button and a new rank line, plus the full schedule card. The collapsible and its collapsed summary are removed. The completed state's "Next session" line stays.
- **D-03:** Leaderboard holds the existing `TrainLeaderboardCard`.
- **D-04:** Archive has a Mastered / Parked toggle with counts and the existing explainer popovers, replacing `TrainStatsCard`. 20 per page via the existing `Pagination`, newest first, list and page in the URL so browser back from Analysis returns to the same spot. No filters in v1.
- **D-05:** New small `TrainPuzzleCard` on `LazyMiniBoard`, not `FlawCard`. Horizontal, board left, details and buttons right. One column on phones, two on desktop. Pre-mistake position with no arrows on both lists.
- **D-06:** Hide the subnav during solve, score and restored-reveal views. `TrainMedalDialogHost` moves to the layout. `POST /train/sessions` and the grading engine must not run on Leaderboard or Archive.

### Archive card details
- **D-07:** Beside the board, above Analyze: game details (opponent and rating, game date, time control) plus a status line, for example `Mastered Oct 3, 2026` or `Parked Oct 3, 2026 · 4 misses`. The date is the latest solve date for that puzzle (see D-13) and the miss count is `drill_items.fail_count`.
- **D-08:** No originally played move on the card, as text or otherwise. No motif or severity either: all would hint at the answer on a later Retry, and Analyze shows them anyway.
- **D-09:** An empty Mastered or Parked list shows per-list explainer copy based on the existing explainers, plus a link to Today. Example: "No mastered puzzles yet. Solve a puzzle correctly twice in a row to master it." The copy for an empty Parked list should read as good news, not a dead end. Zero-game accounts get the same empty state, no import button.

### Streak card additions
- **D-10:** The rank line uses the Points board only and reads `#4 this week`, linking to `/train/leaderboard`. Accuracy is excluded because it stays tentative and unranked until 20 puzzles.
- **D-11:** With no Points rank this week, the same spot shows a link reading `See this week's leaderboard`. Guests and opted-out players get the same rank line they see on their own board view. Planning must confirm `viewer.rank` is populated for hidden and guest rows; if it isn't, they get this link instead.
- **D-12:** `Points today: 5/9` is a muted text line in the streak card's details column, under the week caption and rank line, on the completed state only. `TrainStatsCard` is deleted.

### Archive data
- **D-13:** Sort by latest `drill_solves.solved_at` per puzzle, newest first. Verified: `_advance_drill_item` (`app/repositories/train_repository.py:3092`) is the only status writer in `app/`, and new items are inserted ACTIVE. Status therefore only changes on a solve.
- **D-14:** Keep puzzles whose `game_flaws` row was evicted: `LEFT JOIN` to `game_flaws`, with `mastered_count` and `parked_count` unchanged, so the list always matches the toggle counts. This matches the anchoring rule in `app/models/drill_item.py`. The user did not select this area, so this is a default rather than a discussed choice. Nothing on the card needs the flaw row, since the FEN comes from `games.pgn` via `fen_and_last_move_at_ply`. Later Retry needs a rule for these puzzles (see Deferred Ideas).

### Tab width and visibility
- **D-15:** Tabs span `max-w-7xl` on every tab, matching Library, where the narrow Import form already sits under wide tabs. Today and Leaderboard stay in a centered `max-w-2xl` column; Archive uses the full width. Tabs must not change size or position when switching.
- **D-16:** Tabs always show on the landing, including during Tank's first-visit intro and in the no-games state. The only hidden states are those in D-06. Accepted cost: Start moves down about 40px on a phone.

### Claude's Discretion
Defaults the user saw and accepted at the end of the discussion, or left unasked:
- Mobile tabs are non-sticky, like Library.
- Mastered is the default list.
- The list lives in the URL path, for example `/train/archive/parked?page=2`, with `/train/archive` resolving to Mastered. The pageview therefore covers it and no Umami event is needed.
- How Retry's space is reserved. No visible placeholder.
- Whether the card shows the arriving move highlight (not an arrow, and not a spoiler) and whether the board itself is clickable.
- Rank line loading and error states, which must not flash the D-11 fallback link before the query resolves.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Scope and locked decisions
- `.planning/seeds/SEED-261106-gw8-train-subnav-split.md` — source decisions, traps and breadcrumbs for this phase
- `.planning/seeds/SEED-261106-q92-train-archive-retry.md` — the follow-up this phase must leave room for; explains why cards carry no spoilers
- `.planning/ROADMAP.md` §Phase 246 — phase goal and trap list

### Data model
- `app/models/drill_item.py` — lifecycle and the locked anchoring rationale (no FK to `game_flaws`)
- `app/models/drill_solve.py` — `solved_at` (nullable), `game_id` (`SET NULL`), composite primary key

### Project rules
- `frontend/CLAUDE.md` — `data-testid`, button variants, `text-sm` floor, Umami rules for URL-routed tabs

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `frontend/src/components/board/LazyMiniBoard.tsx`: base for `TrainPuzzleCard`
- `frontend/src/components/results/Pagination.tsx`: pagination, wired as in `frontend/src/pages/library/FlawsTab.tsx` (`PAGE_SIZE = 20`). `FlawsTab` holds its offset in state, so URL-held page is new here.
- `frontend/src/components/library/FlawCard.tsx`: layout and board-size reference only (`DESKTOP_BOARD_SIZE = 200`, `MOBILE_BOARD_SIZE = 132`)
- `frontend/src/components/train/TrainStatsCard.tsx`: `MASTERED_EXPLAINER` and `PARKED_EXPLAINER` copy to move before deleting it, along with its test file
- `frontend/src/hooks/useTrainLeaderboard.ts`: already fetched on the landing; `points.viewer?.rank` drives the rank line
- `frontend/src/components/train/TrainLeaderboardCard.tsx`: already has its own empty, error, loading and guest CTA states, so check them before adding new Leaderboard empty-state work

### Established Patterns
- `frontend/src/pages/library/LibraryPage.tsx`: closest subnav model, with path-derived active tab, `navigate()` on change, separate desktop and mobile `TabsList`, `max-w-7xl` wrapper
- `frontend/src/pages/Endgames.tsx`: same `TabsList variant="brand"` pattern
- `frontend/src/components/train/TrainStartScreen.tsx`: landing states resolve through one ordered branch chain (`resolveLandingState`); keep that shape

### Integration Points
- `frontend/src/App.tsx:1085`: route is already `/train/*`; nav active state and the page title need checking for sub-paths (`ROUTE_TITLES` lookup at `App.tsx:384`)
- `frontend/src/pages/Train.tsx`: session and engine hooks, loop state, dev clock, profile loading and error branches to split between layout and Today
- `frontend/src/components/train/TrainScheduleSettings.tsx`: collapsible shell and summary to remove, including the `panel-open` `train-schedule` event that goes with it
- `frontend/src/components/train/TrainStreakCard.tsx`: only rendered from `TrainStartScreen`, so the rank line needs no opt-in prop
- `app/repositories/train_repository.py`: new list query beside `_count_drill_items_by_status`

### Findings to resolve in planning
- **Analyze ply is possibly off by one from the seed.** The seed says `buildGameAnalysisUrl(game_id, ply)`, but `TrainSolveScreen.tsx:947` uses `puzzle.ply > 0 ? puzzle.ply - 1 : null`. Verify and land on the position the card shows.
- **"No migration" is unproven.** `drill_solves` has only a partial index on `solved_at` plus its primary key, with nothing on `user_id` or `(user_id, game_id, ply)`. Run `EXPLAIN` on the sort query and flag a migration if it is a sequential scan.
- **Returning to Today is costly.** `useTrainGradingEngine` terminates its Worker on unmount (`useTrainGradingEngine.ts:577`) and `TrainPage` re-fires `POST /train/sessions` on every mount, so each return respawns the Worker, repeats the POST and can flash "Loading…". iOS has a tight wasm reservation budget, so check repeated respawns there. A layout-level latch that starts only after Today's first visit may beat moving the hooks to the Today route, while still honouring D-06.
- **The layout needs loop state.** Hiding the subnav and the medal dialog depends on state owned by Today. `TrainStartScreen`'s docstring promises the medal dialog never appears mid-session, and that must survive the move. A cached restored reveal must count as immersive from first paint, because `restoredActive` is false until the session loads and the subnav would otherwise flash.
- **Page cost.** Each card needs a PGN parse through `fen_and_last_move_at_ply`. 20 per page should be fine; confirm no N+1 on `games`.
- **Prod sizes not checked.** The prod DB tunnel was down during discussion, so evicted-row counts and per-user list sizes remain unknown. Neither changes a decision.

</code_context>

<specifics>
## Specific Ideas

- Status line format: `Mastered Oct 3, 2026`, `Parked Oct 3, 2026 · 4 misses`. Use the `MMM d, yyyy` format already used by the "Next session" line.
- Rank line copy: `#4 this week`; fallback: `See this week's leaderboard`.
- Points line copy: `Points today: 5/9`.

</specifics>

<deferred>
## Deferred Ideas

- **Retry on evicted puzzles (SEED-261106-q92):** D-14 keeps puzzles with no `game_flaws` row in the Archive, but the solve path skips them as unservable. Retry must hide or disable the button on those cards, so the list endpoint may want to expose that fact when Retry ships.
- **Tactic motif filter and Stats tab:** already recorded in SEED-261106-gw8 as later work.

### Reviewed Todos (not folded)
Keyword-only matches with no connection to this phase:
- `172-deferred-review-findings.md`
- `2026-03-11-bitboard-storage-for-partial-position-queries.md`
- `2026-08-29-variation-tree-nested-button.md`
- `2026-05-18-wr01-pt33-invalid-tailwind-score-axis-label.md`

</deferred>

---

*Phase: 246-train-subnav-split*
*Context gathered: 2026-11-06*
