# Pitfalls Research

**Domain:** Chess analysis platform — adding move explorer and UI restructuring to existing system
**Researched:** 2026-03-16
**Confidence:** HIGH (based on direct codebase inspection + verified patterns)

This file covers pitfalls specific to v1.1: adding `move_san` to `game_positions`, the move
explorer aggregation queries, and the UI restructuring from flat pages to a tabbed Openings page
with shared filter sidebar.

---

## Critical Pitfalls

### Pitfall 1: DISTINCT ON Breaks the GROUP BY Aggregation for Next-Move Stats

**What goes wrong:**
The existing `_build_base_query` uses `DISTINCT ON (game_id)` to deduplicate games that contain
the target position at multiple plies. When you need to aggregate next moves (GROUP BY move_san
with counts and W/D/L sums), adding `DISTINCT ON` inside a subquery before the GROUP BY is not
straightforward — the optimizer cannot simply combine them. Writing the aggregation as a single
query with both `DISTINCT ON` and `GROUP BY` causes a PostgreSQL syntax error or wrong counts
because `DISTINCT ON` and `GROUP BY` cannot coexist directly in the same SELECT.

**Why it happens:**
Developers copy the existing analysis pattern for stats and try to bolt on `GROUP BY gp.move_san`
without realising that `DISTINCT ON (game_id)` must be resolved first (to avoid counting a game
twice when the position appears at ply 4 AND ply 6 in that same game) before the GROUP BY can
aggregate correctly.

**How to avoid:**
Use a two-level query:
1. **Inner CTE/subquery:** join `game_positions` (filtered by `parent_hash`) to `games` (filtered
   by all active filters), apply `DISTINCT ON (game_id)` so each game appears at most once per
   move_san that leads to the target position. Select `(game_id, move_san, result)`.
2. **Outer query:** GROUP BY `move_san`, SUM wins/draws/losses, COUNT(*).

The key insight is that "next moves" means rows at ply N+1 where the *parent* position (ply N) is
the current board position. The join is on `parent_hash` (the hash stored at ply N, which is the
hash at ply N+1 minus one move). This requires either storing `parent_hash` per row in
`game_positions`, or doing a self-join: find all `game_id + ply` combos where ply N matches the
target hash, then fetch ply N+1's `move_san` from the same `game_positions` table.

The self-join approach avoids a schema change to add `parent_hash` but adds query complexity.
The stored `parent_hash` approach adds a column but makes queries clean. Given that the project
accepts a DB wipe for v1.1, adding `parent_hash` (or simply querying ply+1) is the cleaner path.

**Warning signs:**
- SQL errors mentioning `DISTINCT ON` and `GROUP BY` in the same level
- Move counts that sum to more than the total matched game count (double-counting)
- Correct move SAN returned but W/D/L totals wrong (aggregated before dedup)

**Phase to address:** The schema phase (adding move_san) — design the aggregation query pattern
before writing the Alembic migration so the column set is sufficient.

---

### Pitfall 2: Storing move_san at Ply 0 (Starting Position Has No Move)

**What goes wrong:**
`hashes_for_game()` in `zobrist.py` inserts a row at `ply=0` representing the initial position
before any move is played. This row has no associated move — it is the position *before* the first
move. If `move_san` is added as a NOT NULL column, the ply-0 row requires a placeholder value
(e.g., an empty string `""` or `NULL`). Forgetting this causes import failures with NOT NULL
constraint violations.

Beyond the constraint, the ply-0 row with `move_san=""` or `move_san=NULL` should be excluded
from move-explorer aggregations — it represents the starting position node, not a move.

**Why it happens:**
The current `hashes_for_game()` logic is clean: ply 0 = before move 1, ply 1 = after move 1, etc.
When developers add `move_san` they naturally populate it from the `move` variable in the loop
`for ply, move in enumerate(moves, start=1)` — but the ply-0 row is inserted *before* the loop and
has no corresponding move in scope.

**How to avoid:**
Make `move_san` nullable (VARCHAR or TEXT, nullable). Ply-0 rows store NULL. The move-explorer
aggregation query always filters `WHERE gp.move_san IS NOT NULL` or `WHERE gp.ply > 0`. This is
semantically correct: the move_san at ply N is the move that *led to* the position at ply N.

**Warning signs:**
- Import failures with NOT NULL violations during the first test import after schema change
- Move explorer showing a blank/null move entry with very high game counts (all games start from
  ply 0, so the null-move entry would match every game)

**Phase to address:** Schema migration phase — define nullability explicitly in the model before
writing any migration.

---

### Pitfall 3: move_san Missing the Composite Index with user_id and hash

**What goes wrong:**
Adding a standalone index on `game_positions.move_san` does not help the move-explorer query.
The query pattern is: `WHERE gp.user_id = :uid AND gp.full_hash = :current_position_hash`. The
existing indexes are `(user_id, full_hash)`, `(user_id, white_hash)`, `(user_id, black_hash)`.
The move_san lookup is not a *filter* — it is a *projection* after the hash lookup. No extra index
on `move_san` alone is needed.

The pitfall is adding an unnecessary composite index like `(user_id, full_hash, move_san)` thinking
it helps, when the existing `ix_gp_user_full_hash` already covers the lookup and PostgreSQL can
fetch `move_san` from the heap after the index scan. On a hot table with millions of rows, adding
extra indexes slows writes without proportional read benefit.

A related pitfall: forgetting to also store `move_san` for the *current* ply (the move that led to
the current position, stored on the current row) vs. the *next* ply. The move explorer shows "what
moves were played *from* this position" — that is the `move_san` at ply N+1 where ply N is the
current board position. The existing ply model stores `move_san` at the ply it was *played* (after
the move). Make sure this is consistent throughout the codebase.

**How to avoid:**
Use the existing hash indexes for lookup. Read `move_san` as a plain column in the SELECT. Do not
add a new composite index for move_san unless EXPLAIN ANALYZE on real data shows it helps. Document
in the model comment whether `move_san` at ply N is "the move that led to this position" (correct)
or "the move played from this position" (would require fetching ply N+1).

**Warning signs:**
- Slow migration due to building a large unnecessary index
- Aggregation queries returning moves for the wrong ply (off-by-one in the explorer)

**Phase to address:** Schema migration phase — document the ply/move_san semantic clearly in the
model before the migration runs.

---

### Pitfall 4: Aggregation Query Fetches the Entire Matching Game Set Before Grouping

**What goes wrong:**
A naive implementation of the next-move aggregation joins `game_positions` to `games` and then
calls Python-level GROUP BY (e.g., using `Counter` in the service layer) instead of pushing the
aggregation to PostgreSQL. For a user with 10,000 games × 40 plies = 400,000 rows, fetching all
matching position rows to Python and aggregating there produces massive result sets over the network
and is orders of magnitude slower than `GROUP BY` in SQL.

**Why it happens:**
The existing service layer already does lightweight Python aggregation for W/D/L (counting `result`
values from the `query_all_results()` tuples). Developers extend this pattern for move aggregation
without realising the cardinality is much higher (one row per matching game per move, not one row
per game).

**How to avoid:**
Push `GROUP BY gp.move_san, g.result` entirely to PostgreSQL. The aggregation query should return
at most ~30 rows (number of legal moves from any position is ≤ 30 in practice) regardless of how
many games match. Use `COUNT(DISTINCT g.id)` or the two-level CTE approach from Pitfall 1 to
avoid double-counting.

**Warning signs:**
- Move explorer endpoint response time scales with game count instead of being O(1) for a given
  position
- Memory spikes in the FastAPI process during move explorer queries

**Phase to address:** Backend aggregation endpoint phase — write the SQL query in EXPLAIN ANALYZE
against test data before wiring it to the API.

---

### Pitfall 5: Shared Filter State Not Propagated When Switching Sub-Tabs

**What goes wrong:**
The v1.1 design has a shared filter sidebar across Move Explorer / Games / Statistics sub-tabs.
If filter state lives inside each sub-tab's local component state, switching tabs resets the
filters. If the filters are lifted to the parent Openings page component, React unmounts the
sub-tab component on tab switch — resetting any sub-tab-local state (e.g., the board position in
the move explorer, the games page offset, the expanded statistics section). The symptoms are:
user sets filters → navigates to Move Explorer → plays a few moves → switches to Games tab →
switches back → move explorer board is reset and filters are still correct. Or worse: the
sub-tab re-fetches data with stale filters because the query key didn't include the filter params.

**Why it happens:**
React unmounts components when they are not rendered. Sub-tab routing via conditional rendering
(`activeTab === 'explorer' ? <ExplorerTab /> : null`) causes full unmount/remount cycles. The
developer puts `const [filters, setFilters] = useState(DEFAULT_FILTERS)` inside each sub-tab
thinking it's self-contained.

**How to avoid:**
Lift ALL shared filter state to the parent `OpeningsPage` component and pass it down as props.
Sub-tab-local state (board position in the explorer, scroll position in the games list) is
acceptable as local state. For the move explorer board position specifically, consider whether it
should survive tab switches — if yes, lift it to the parent too, or use a hidden-not-unmounted
pattern (`display: none` instead of conditional render).

React TanStack Query handles the re-fetch correctly as long as the `queryKey` includes all filter
params. Verify the query keys include filters when implementing the hooks.

**Warning signs:**
- Switching tabs resets filter chip selections
- Games list jumps to page 1 when you switch away and back
- Move explorer board resets to starting position when switching away and back

**Phase to address:** UI restructuring phase — design the state architecture on paper before
writing any component code.

---

### Pitfall 6: Import Page Breaks the positionFilterActive Pattern

**What goes wrong:**
The current `DashboardPage` embeds import logic alongside the position filter. The `positionFilterActive`
flag controls whether the default games list or the filtered results list is shown. When import is
moved to a dedicated `/import` page (or to the new sub-tab structure), the `handleJobDone`
callback currently calls `queryClient.invalidateQueries(['games'])` and `refetchGameCount()` —
both of which are wired to the dashboard state. Moving import breaks these invalidations unless
the same query keys are invalidated from the new import page context.

A secondary issue: after a successful import on the Import page, the user navigates back to Games.
If TanStack Query's `staleTime` is 30,000ms, the games list may not reflect the newly imported
games if the user returns within 30 seconds.

**Why it happens:**
The import side effects (invalidate `['games']`, `['gameCount']`, `['userProfile']`) are currently
co-located with the `DashboardPage`. When import moves to its own page, developers forget to carry
forward the post-import invalidation logic.

**How to avoid:**
Use TanStack Query's global `queryClient` (accessible via `useQueryClient()`) in the Import page
component, and invalidate the same keys (`['games']`, `['gameCount']`, `['userProfile']`) on job
completion. Set `staleTime: 0` on the `['games']` query if you want immediate refresh after import,
or call `queryClient.invalidateQueries` explicitly from `handleJobDone` on the Import page.

**Warning signs:**
- Games list doesn't update after import completes on the new Import page
- Game count badge shows stale number after import
- `userProfile` (platform usernames) doesn't refresh after first-ever import

**Phase to address:** Import page migration phase — checklist item: "verify all post-import query
invalidations transferred from Dashboard to Import page."

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Python-level move aggregation (Counter) | Reuses existing pattern | O(N) network transfer for N matching positions; slow at scale | Never — push to SQL from the start |
| Hardcoding `move_san` as NOT NULL with empty string default | Avoids null handling in frontend | Blank-string entries pollute aggregation queries; requires filtering `!= ''` everywhere | Never — use nullable |
| Storing `move_san` only on the `game_positions` table without documenting ply semantics | Fast to implement | Off-by-one in explorer (showing "move that led here" vs "moves from here") causes subtle wrong results | Acceptable if documented clearly |
| Sub-tab state via URL query params (`?tab=explorer`) | Bookmarkable, shareable links | Adds complexity to state sync; URL updates can be laggy in React Router | Acceptable only if simple — avoid for complex board state |
| Keeping import modal alongside new Import page during transition | Reduces merge conflicts | Dead code; two import entry points confuse users | Only during phased migration, must be removed in same milestone |

---

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| `hashes_for_game()` → `move_san` | Adding move_san inside the existing `for ply, move` loop but forgetting ply-0 row | Insert ply-0 with `move_san=None`, then set `move_san=board.san(move)` **before** `board.push(move)` for each subsequent ply |
| chess.js (frontend) → SAN display | Using `move.san` from chess.js which includes check symbols (`Nf3+`) | SAN stored in backend via python-chess `board.san(move)` also includes check/checkmate symbols — consistent, no transformation needed |
| react-chessboard v5 `customArrows` / move highlights | Passing arrow data as flat props instead of inside the `boardOptions` object | All visual customisation goes through the `options` prop object (confirmed v5 API) |
| TanStack Query cache + sub-tabs | Different sub-tabs using different query keys for the same filter state | Define a single `queryKey` factory function shared across all sub-tab hooks so cache is shared |
| Alembic migration on `game_positions` | Running `ALTER TABLE ADD COLUMN` on a table that may have millions of rows blocks reads in old PostgreSQL | Adding a nullable column with no default in modern PostgreSQL (≥11) is a metadata-only operation (no table rewrite) — this is safe and fast |

---

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Full table scan for move aggregation | Move explorer response >2s | Push GROUP BY to SQL; use existing `(user_id, full_hash)` index | ~5,000+ games per user |
| Fetching all sub-tab data on Openings page mount | Initial page load slow; unnecessary API calls when no position is set | Only fetch move explorer data when a position is actually selected (`enabled: positionFilterActive`) | Always — wasteful even at small scale |
| Redundant re-renders when filter state is in parent | Every filter change re-renders all sub-tabs | Use `React.memo` on sub-tab components; pass only the props each tab needs | Medium complexity apps — becomes noticeable with chart components |
| `COUNT(DISTINCT game_id)` in aggregation query | Slow on large tables (requires dedup before counting) | Use the two-level CTE: dedup first, then COUNT(*) on the outer level | ~50,000+ position rows |
| Missing `user_id` in move-explorer WHERE clause | Returns moves from all users' games | Always include `WHERE gp.user_id = :uid` — the `game_positions` table is multi-user | Day 1 — data isolation bug, not a scale issue |

---

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| Exposing move aggregation endpoint without user scoping | User A can query move stats for User B's games | Always filter `game_positions.user_id = current_user.id`; existing analysis router pattern already does this — replicate exactly |
| Returning `move_san` directly from DB without validation | Theoretically correct since it was stored from python-chess output; not a risk | No action needed — python-chess SAN output is safe |

---

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| Move explorer shows moves at starting position before user plays any moves | Confusing "all possible openings" list with hundreds of entries | Only show the move explorer when the board has at least 1 move played, or when a bookmark is loaded |
| Sub-tab switching loses the user's position in the Games list | User pages to page 3, switches to Explorer, comes back and is on page 1 | Preserve `offset` as state in the parent `OpeningsPage` component, not in the Games sub-tab |
| "Analyze" button on the new Openings page required before move explorer loads | Extra friction; user expects explorer to auto-load when position changes | Auto-trigger move explorer query when `positionFilterActive=true`, matching the existing auto-analyze pattern on Dashboard |
| Import page lacks the same import-progress toasts as the old modal | User can't tell if import is running | Reuse `ImportProgress` component on the Import page with the same `activeJobIds` pattern |
| Move explorer move buttons (e.g., "e4 — 58%") not clickable to advance the board | Explorer exists but can't navigate the position | Every move row must call `chess.loadMoves([...currentMoves, san])` on click; this is the core interactive value proposition |

---

## "Looks Done But Isn't" Checklist

- [ ] **move_san migration:** Verify ply-0 rows have `move_san = NULL` after migration, not empty string
- [ ] **Move aggregation:** Confirm total W+D+L in move explorer equals total matched games (no double-counting from multi-ply positions)
- [ ] **user_id scoping:** Verify move-explorer endpoint returns 0 results for a position from another user's games
- [ ] **Shared filters:** Confirm changing time control filter while on Games sub-tab, then switching to Explorer sub-tab, shows explorer data with the same filter applied
- [ ] **Import page invalidations:** After completing an import on the Import page, navigate to Games — verify game count and games list update without manual refresh
- [ ] **positionFilterActive flag:** Verify the Openings page's Explorer sub-tab shows "no position selected" state (not empty results) when the board is at the starting position
- [ ] **data-testid coverage:** All move-explorer move rows, sub-tab buttons, and the dedicated Import page controls have `data-testid` attributes per CLAUDE.md conventions
- [ ] **Mobile layout:** Shared filter sidebar collapses correctly on small screens; sub-tabs stack vertically or scroll horizontally without horizontal overflow

---

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Wrong ply semantics for move_san (off-by-one) | HIGH — requires re-importing all games | Wipe DB (already accepted for v1.1), fix `hashes_for_game()`, re-run migration, re-import |
| Double-counting in move aggregation | MEDIUM — SQL fix only | Fix the aggregation query in `analysis_repository.py`; no schema change needed |
| Filter state not shared across sub-tabs | LOW — React refactor | Lift state to parent component; no backend changes needed |
| Import page missing post-import invalidations | LOW — one-line fix | Add `queryClient.invalidateQueries` calls to `handleJobDone` in Import page |
| Missing `user_id` scope in move-explorer query | HIGH — data isolation bug | Immediate hotfix; add `WHERE gp.user_id = :uid`; audit all new repository functions |

---

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| DISTINCT ON + GROUP BY conflict | Schema + aggregation query phase | EXPLAIN ANALYZE the move aggregation query; check totals sum correctly |
| Ply-0 move_san nullability | Schema migration phase | `SELECT COUNT(*) FROM game_positions WHERE ply = 0 AND move_san IS NOT NULL` = 0 |
| Wrong index strategy for move_san | Schema migration phase | No new index added beyond existing hash indexes; EXPLAIN shows index scan on existing ix_gp_user_full_hash |
| Python-level aggregation anti-pattern | Backend explorer endpoint phase | Response time < 200ms for a user with 5,000 games |
| Shared filter state isolation | UI restructuring phase | Switch tabs, verify filter chips retain their state |
| Import page broken invalidations | Import page migration phase | Import completes → navigate to Games → count updates without refresh |
| Missing user_id scope | Backend explorer endpoint phase | Unit test: query with another user's position hash returns 0 moves |

---

## Sources

- Direct codebase inspection: `app/models/game_position.py`, `app/repositories/analysis_repository.py`,
  `app/services/zobrist.py`, `frontend/src/pages/Dashboard.tsx`, `frontend/src/pages/Openings.tsx`,
  `frontend/src/App.tsx`
- Existing v1.0 pitfalls in this file (chess.com/lichess API, PGN parsing, position representation)
- PostgreSQL documentation on DISTINCT ON ORDER BY constraint (known issue from v1.0 `analysis_repository.py`
  comments — the two-subquery pattern is already in place)
- PostgreSQL `ALTER TABLE ADD COLUMN` metadata-only for nullable columns with no default (PostgreSQL ≥11)
- TanStack Query staleTime and invalidation patterns

---
*Pitfalls research for: Chessalytics v1.1 — Move Explorer + UI Restructuring*
*Researched: 2026-03-16*
