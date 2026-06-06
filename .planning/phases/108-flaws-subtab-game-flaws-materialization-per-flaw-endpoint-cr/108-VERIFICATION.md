---
phase: 108-flaws-subtab-game-flaws-materialization-per-flaw-endpoint-cr
verified: 2026-06-06T20:00:00Z
status: passed
human_verified: 2026-06-06
score: 22/22
overrides_applied: 0
human_verification:
  - test: "Navigate to /library/flaws (as user with analyzed Lichess games). Verify each row shows a miniboard at the correct position with a correctly-placed red arrow marking the actual blunder/mistake move."
    expected: "Arrow points from the source square to the destination square of the flawed move. No row shows a misleading e1→e1 marker or a missing arrow when move_san is present."
    why_human: "The sanToSquares utility runs in the browser. Automated tests mock the hook and cannot exercise the actual chess.js SAN parsing against real FEN+SAN pairs from the DB."
  - test: "In the Flaws tab, use the FlawFilterControl: (a) select only 'Blunders'; (b) select a tag (e.g. 'result-changing'); (c) combine a Timing tag and an Impact tag. Verify the list updates to show matching rows only."
    expected: "Severity-only filter returns only blunder rows. Single tag filter returns rows with that tag. Cross-family AND (Timing + Impact) returns rows where a SINGLE flaw is tagged with BOTH families."
    why_human: "Single-flaw EXISTS semantics (AND across families in one row) cannot be fully tested from the frontend alone — requires real rows in game_flaws where the combination is/is not satisfied."
  - test: "Click a tag chip on a Games-tab game card. Verify navigation to /library/flaws?tag={TAG}, the Flaws tab activates with that tag pre-selected, and the severity defaults to M+B."
    expected: "URL changes to /library/flaws?tag=<tagname>. FlawFilterControl shows the tag button highlighted in its family color. Flaws list shows only flaws with that tag."
    why_human: "React Router navigation + URL-to-store initialization + visual filter state cannot be fully exercised by unit tests with mocked hooks."
  - test: "Switch between Games tab and Flaws tab while a flaw filter is active. Verify the selection is preserved in both directions."
    expected: "Selected severity/tags in Games tab appear pre-selected when switching to Flaws tab, and vice versa."
    why_human: "Shared Zustand-style store behavior across tab switches requires a running app to verify end-to-end."
  - test: "Open /library/flaws on a mobile viewport (375px wide). Tap 'Filters' to open the drawer. Verify FlawFilterControl renders inside the drawer with all 3 family groups visible and tappable."
    expected: "Drawer opens, FlawFilterControl is fully visible with Timing/Opportunity/Impact sections, tag buttons have adequate tap targets (h-11 = 44px touch target)."
    why_human: "Mobile drawer layout and touch-target sizing require visual/device inspection; automated tests use desktop viewport."
  - test: "On the Flaws tab with no analyzed Lichess games imported, verify the correct empty state appears."
    expected: "Heading 'No analyzed games' and body 'Only Lichess games with engine analysis have flaws. Import Lichess games to see your flaws.' — not the generic 'No games imported yet' state."
    why_human: "Empty-state branching (no analyzed games vs no games imported vs filter mismatch) requires real data conditions to trigger correctly."
---

# Phase 108: Flaws Subtab — game_flaws Materialization, Per-Flaw Endpoint, Cross-Tab Flaw Filter Verification Report

**Phase Goal:** The Library Flaws subtab gives one row per flawed position (miniboard + marked move + severity/tags), backed by a new per-flaw list endpoint, with a shared cross-tab Flaw filter (single-flaw EXISTS semantics, family-aware OR-within / AND-across logic) surfaced in both Games and Flaws, made efficient and paginable by materializing Phase 105's on-the-fly classifier output into a derived `game_flaws` table. Also wires Phase 107's Games-card tag chips to deep-link into the pre-filtered Flaws view.

**Verified:** 2026-06-06T20:00:00Z
**Status:** passed (6 human verification items confirmed by Adrian on 2026-06-06)
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `game_flaws` table exists with composite PK (user_id, game_id, ply) and CASCADE FKs | VERIFIED | `app/models/game_flaw.py` defines `GameFlaw` with composite PK + `ForeignKey(..., ondelete="CASCADE")` on both `user_id` and `game_id`; migration `20260606_151439_a7e0b4796501_add_game_flaws_table.py` creates the table with both FK constraints and the `ix_game_flaws_user_severity` index. Alembic current = `a7e0b4796501 (head)`. |
| 2 | `game_flaws` is M+B only (severity 1=mistake, 2=blunder; never 0=inaccuracy) | VERIFIED | Model comment: "0=inaccuracy is NEVER stored here per D-03". `flaw_record_to_row` only maps `{"mistake":1, "blunder":2}`; `classify_game_flaws` inaccuracies produce no rows. `test_flaws_materialization.py` asserts no inaccuracy row. |
| 3 | Each row carries full display payload (fen, es_before, es_after, move_san) | VERIFIED | `GameFlaw` has non-nullable `fen`, `es_before`, `es_after` plus nullable `move_san`. `FlawListItem` schema carries all four. `flaw_record_to_row` passes them through from `FlawRecord`. |
| 4 | The single materialization path: import hook in `eval_drain.py` calls `classify_game_flaws` + `flaw_record_to_row` (D-10) | VERIFIED | `_classify_and_insert_flaws` in `eval_drain.py` imports and calls both functions. It runs sequentially (no `asyncio.gather`), is Sentry-guarded per-game, and is called between `_apply_eval_results` and `_mark_evals_completed`. |
| 5 | `reclassify_positions.py` also recomputes `game_flaws` via the same classify path (D-10) | VERIFIED | `reclassify_positions.py` imports `delete_flaws_for_game`, `flaw_record_to_row`, `bulk_insert_game_flaws`, and `classify_game_flaws`. `_recompute_game_flaws` calls delete-then-insert per game sequentially. |
| 6 | `scripts/backfill_flaws.py` with `--db`, `--user-id`, `--dry-run` and batched commit | VERIFIED | File exists. `BACKFILL_GAMES_PER_BATCH = 100` named constant. CLI supports `--db {dev,benchmark,prod}`, `--user-id`, `--dry-run`, `--limit`. Commit per chunk. Uses the same `classify_game_flaws + flaw_record_to_row + bulk_insert_game_flaws` path. |
| 7 | One shared predicate builder `build_flaw_filter_clauses` reused by BOTH Games EXISTS and Flaws SELECT (SEED-038) | VERIFIED | `build_flaw_filter_clauses` in `library_repository.py` is called by `flaw_exists_from_table` (Games EXISTS path) and by `query_flaws` (Flaws SELECT). `query_utils.apply_game_filters` calls `flaw_exists_from_table` for the Games tab. |
| 8 | Tag families: OR within family, AND across families (single-flaw EXISTS semantics) | VERIFIED | `build_flaw_filter_clauses` returns multiple clauses (caller ANDs them = AND across families); tempo uses `.in_()`, opportunity/impact use `or_()` within family. `test_flaw_predicate.py` explicitly tests the split-flaw scenario (two plies with different families do NOT satisfy the AND-across filter). |
| 9 | Phase tags (opening/middlegame/endgame) are NOT filter predicates | VERIFIED | `build_flaw_filter_clauses` has no branch for phase tags. Router `FlawTagFilter` `Literal` excludes them. `test_library_router.py` asserts 422 on phase-tag query param. |
| 10 | Games-surface migrated onto `game_flaws` (D-02); inaccuracy counts stay a cheap aggregate (D-03) | VERIFIED | `library_service.py` docstring and code: chips + M+B counts come from `game_flaws` via batched page query; inaccuracy from `game.white_inaccuracies`/`black_inaccuracies` oracle columns. No `classify_game_flaws` call in Games path remains. |
| 11 | `GET /library/flaws` endpoint: user-scoped (IDOR-safe), recent-first, paginated (default 20, limit 1-100), severity M+B only | VERIFIED | Router at `/flaws` (relative path), `current_active_user` dep. `Query(default=20, ge=1, le=100)` for limit. `SeverityFilter = Literal["mistake","blunder"]`. `query_flaws` orders `played_at DESC NULLS LAST, ply ASC`. IDOR: `user_id` from authenticated user only. |
| 12 | `FlawsTab` component exists with `flaw-list` section, `flaws-tab-content` testid, pagination (20/page), URL sync, mandatory isError branch | VERIFIED | `FlawsTab.tsx` has `data-testid="flaws-tab-content"`, `<section aria-label="Flaw results" data-testid="flaw-list">`, `useLibraryFlaws`, `PAGE_SIZE = 20`, `useSearchParams` for URL sync, mandatory isError branch with correct copy. |
| 13 | `FlawFilterControl` renders severity (M+B) + 3 tag-family groups (Timing/Opportunity/Impact) excluding phase tags; all required `data-testid` and ARIA present | VERIFIED | `FlawFilterControl.tsx` has all testids: `flaw-filter-control`, `filter-flaw-severity-blunder|mistake`, `filter-flaw-family-tempo|opportunity|impact`, `filter-flaw-tag-{low-clock|impatient|considered|miss|lucky-escape|result-changing|while-ahead}`, `btn-clear-flaw-filter`. `aria-pressed` on all toggles. Phase tags absent. |
| 14 | At-least-one-severity guard: cannot deselect both severity buttons | VERIFIED | `handleSeverityToggle` returns early when `next.length === 0`. `FlawFilterControl.test.tsx` tests this case explicitly. |
| 15 | `useFlawFilterStore` is the shared cross-tab store (mirrors `useFilterStore`); no Zustand | VERIFIED | `useFlawFilterStore.ts` uses `useSyncExternalStore` pattern (no Zustand import). Exports `useFlawFilterStore` and `DEFAULT_FLAW_FILTER`. |
| 16 | The boolean severity toggle is removed from `LibraryFilterPanel`; `FlawFilterControl` replaces it (D-01) | VERIFIED | `LibraryFilterPanel.tsx` comment: "D-01: the boolean severity toggle is removed; FlawFilterControl replaces it." Props changed from `severityFilter/onSeverityChange` to `flawFilter/onFlawFilterChange`. `FlawFilterControl` rendered above metadata filters. |
| 17 | `GamesTab` uses `useFlawFilterStore` (not local `severityFilter` state) (D-04) | VERIFIED | `GamesTab.tsx` imports and calls `useFlawFilterStore`; no local `severityFilter` state variable present. |
| 18 | Games-card tag chips navigate to `/library/flaws?tag={TAG}` with NO `game_id` (D-05) | VERIFIED | `TagChip.tsx` calls `navigate(\`/library/flaws?tag=${tag}\`)`. No `game_id` in the URL. `TagChip.test.tsx` asserts the exact URL pattern for multiple tags. |
| 19 | Flaws tab is present in `LibraryPage` in tab order Import · Games · Flaws · Stats (desktop and mobile) | VERIFIED | `LibraryPage.tsx` has `TabsTrigger` with `value="flaws"`, `data-testid="tab-flaws"` (desktop) and `data-testid="tab-flaws-mobile"` (mobile), `AlertTriangle` icon, in position 3 (after Games, before Stats). |
| 20 | Marked-move arrow derives from/to via `sanToSquares` against the pre-move FEN (CR-01 fix verified) | VERIFIED | `FlawsTab.tsx` imports `sanToSquares` from `@/lib/sanToSquares`. `moveSquares = sanToSquares(\`${flaw.fen} ${sideToMove} - - 0 1\`, flaw.move_san)`. Arrow uses `moveSquares.from` / `moveSquares.to`. No hardcoded `e1` squares. |
| 21 | Arrow color sourced from `theme.ts` `SEV_BLUNDER` (CR-02 fix verified) | VERIFIED | `FlawsTab.tsx` imports `SEV_BLUNDER` from `@/lib/theme`. `color: SEV_BLUNDER` in the arrow definition. No inline oklch literal. |
| 22 | Full backend suite (2402 passed) + frontend (805 passed) green; ty + ruff + knip clean | VERIFIED | `uv run pytest -n auto` → 2402 passed, 10 skipped. `npm test -- --run` → 805 passed, 69 files. `uv run ty check app/ tests/` → All checks passed. `uv run ruff check app/ tests/` → All checks passed. `npm run lint` → clean. `npm run knip` → exit 0. |

**Score:** 22/22 truths verified

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `app/models/game_flaw.py` | GameFlaw ORM model with composite PK + CASCADE FKs | VERIFIED | All columns correct: severity/phase non-nullable SmallInteger, tempo nullable SmallInteger, 4 boolean columns non-nullable, es_before/es_after Float, fen non-nullable String, move_san nullable String. |
| `alembic/versions/20260606_151439_a7e0b4796501_add_game_flaws_table.py` | Migration creating game_flaws + ix_game_flaws_user_severity | VERIFIED | `create_table("game_flaws", ...)` with both FK constraints (ondelete="CASCADE"), PrimaryKeyConstraint, and the index in an autocommit block (CONCURRENTLY). |
| `app/repositories/game_flaws_repository.py` | bulk_insert_game_flaws + delete_flaws_for_game + flaw_record_to_row | VERIFIED | All three functions exported. `_SEVERITY_INT/_TEMPO_INT/_PHASE_INT` encoding maps defined. ON CONFLICT DO NOTHING on insert. `delete_flaws_for_game` scoped to both `game_id` AND `user_id`. |
| `app/services/eval_drain.py` | `_classify_and_insert_flaws` hook after _apply_eval_results | VERIFIED | Hook defined and called at line 619, between `_apply_eval_results` (613) and `_mark_evals_completed` (622). Sequential loop, Sentry-guarded per game. |
| `app/repositories/library_repository.py` | build_flaw_filter_clauses + flaw_exists_from_table + query_flaws | VERIFIED | All three functions present. `build_flaw_filter_clauses` returns `true()` on empty inputs, handles all 3 families correctly. `query_flaws` orders played_at DESC NULLS LAST, ply ASC. |
| `app/repositories/query_utils.py` | flaw_tags param + flaw_exists_from_table call replacing old window scan | VERIFIED | `flaw_tags: Sequence[str] | None = None` added. Calls `flaw_exists_from_table` from `library_repository` (lazy import to avoid cycle). Old `flaw_exists_subquery` window-scan removed. |
| `app/schemas/library.py` | FlawListItem + LibraryFlawsResponse | VERIFIED | Both schemas present. Pagination fields (matched_count, offset, limit) mirror `LibraryGamesResponse`. No hash columns exposed. |
| `app/routers/library.py` | GET /library/flaws with Literal severity/tag filters, limit 1-100, user-scoped | VERIFIED | Route at relative path `/flaws`. `SeverityFilter = Literal["mistake","blunder"]`. `FlawTagFilter` excludes phase tags. `limit = Query(default=20, ge=1, le=100)`. `user_id` from `current_active_user` only. |
| `app/services/library_service.py` | get_library_flaws; Games migrated to game_flaws; no classify_game_flaws re-call in Games path | VERIFIED | `get_library_flaws` at line 515. Comment confirms classify_game_flaws no longer called in Games path. Inaccuracy from oracle columns. |
| `scripts/backfill_flaws.py` | batched --db/--user-id/--dry-run/--limit CLI with BACKFILL_GAMES_PER_BATCH constant | VERIFIED | All CLI args present. `BACKFILL_GAMES_PER_BATCH = 100`. Uses delete-then-insert per game. Sequential loop. Sentry-guarded. |
| `scripts/reclassify_positions.py` | Also recomputes game_flaws (D-10) | VERIFIED | `_recompute_game_flaws` function calls delete_flaws_for_game + classify_game_flaws + flaw_record_to_row + bulk_insert_game_flaws. Called from main loop at line 310. |
| `frontend/src/hooks/useFlawFilterStore.ts` | Shared flaw-filter store; DEFAULT_FLAW_FILTER; isFlawFilterNonDefault exported | VERIFIED | `useSyncExternalStore` pattern (no Zustand). `DEFAULT_FLAW_FILTER = { severity: ['blunder','mistake'], tags: [] }`. `isFlawFilterNonDefault` exported. |
| `frontend/src/components/filters/FlawFilterControl.tsx` | severity + 3 family groups; all testids/ARIA; at-least-one guard; theme.ts colors | VERIFIED | All 17+ data-testid attributes present. `aria-pressed` on all toggles. Family groups use `FAM_*/FAM_*_BG` from `theme.ts`. At-least-one guard at line 70. |
| `frontend/src/pages/library/FlawsTab.tsx` | Flaws subtab with miniboard list, URL sync, isError branch, pagination | VERIFIED | `useSearchParams` for URL sync. `sanToSquares` for marked-move arrow. `LazyMiniBoard` rendering. Mandatory isError branch. `PAGE_SIZE = 20`. `Pagination` component. |
| `frontend/src/pages/library/LibraryPage.tsx` | Flaws tab trigger in both desktop and mobile; AlertTriangle icon; Import·Games·Flaws·Stats order | VERIFIED | `tab-flaws` (desktop) and `tab-flaws-mobile` present in both Tabs blocks. `AlertTriangle` icon. Tab order: import → games → flaws → stats. |
| `frontend/src/components/filters/LibraryFilterPanel.tsx` | FlawFilterControl rendered above metadata filters; severity toggle removed | VERIFIED | `FlawFilterControl` imported and rendered. Props changed to `flawFilter/onFlawFilterChange/onClearFlawFilter`. "Reset Filters" (brand-outline) preserved separately. |
| `frontend/src/pages/library/GamesTab.tsx` | Uses useFlawFilterStore; no local severityFilter state; no URL sync | VERIFIED | `useFlawFilterStore` imported and used. No `useState` for severity. No `setSearchParams`. |
| `frontend/src/components/library/TagChip.tsx` | Navigates to /library/flaws?tag={TAG}; no game_id in URL; aria-label updated | VERIFIED | `useNavigate` called with `/library/flaws?tag=${tag}`. No game_id appended. Comment confirms D-05 compliance. |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|----|--------|---------|
| `eval_drain.py` | `game_flaws_repository.bulk_insert_game_flaws` | `_classify_and_insert_flaws` hook | WIRED | Called at line 619 in cold-lane write session |
| `game_flaws_repository.py` | `flaws_service.classify_game_flaws` | `flaw_record_to_row` mapping | WIRED | `flaw_record_to_row` imports and uses `FlawRecord` type from `flaws_service`; used in eval_drain, backfill, reclassify |
| `query_utils.apply_game_filters` | `library_repository.flaw_exists_from_table` | flaw_severity + flaw_tags EXISTS path | WIRED | Lazy import at line 118, called at line 124 |
| `library_repository.build_flaw_filter_clauses` | Games EXISTS + Flaws SELECT | Shared predicates | WIRED | `flaw_exists_from_table` (line 145) and `query_flaws` (line 227) both call `build_flaw_filter_clauses` |
| `routers/library.py` | `library_service.get_library_flaws → query_flaws` | `GET /library/flaws` route | WIRED | Route at line 138 calls `library_service.get_library_flaws`; service calls `query_flaws` |
| `FlawsTab.tsx` | `GET /api/library/flaws` | `useLibraryFlaws → libraryApi.getFlaws` | WIRED | `useLibraryFlaws` imported at line 23; called at line 266 |
| `LibraryPage.tsx` | `/library/flaws` route + FlawsTab | Flaws TabsTrigger + TabsContent | WIRED | `FlawsTab` imported at line 8; rendered in both desktop (line 88) and mobile (line 159) |
| `TagChip.tsx` | `/library/flaws?tag={TAG}` | `useNavigate onClick` | WIRED | `navigate(\`/library/flaws?tag=${tag}\`)` at line 102 |
| `GamesTab.tsx` | `useFlawFilterStore` | shared cross-tab flaw filter state | WIRED | `useFlawFilterStore` imported from `hooks/useFlawFilterStore`; called at line 65 |
| `LibraryFilterPanel.tsx` | `FlawFilterControl` | Props: flawFilter + onFlawFilterChange | WIRED | `FlawFilterControl` rendered at line 74 with all required props |

---

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|--------------|--------|--------------------|--------|
| `FlawsTab` | `flaws` (list) | `useLibraryFlaws` → `GET /api/library/flaws` → `query_flaws` → `SELECT GameFlaw JOIN Game WHERE user_id = ...` | Yes — real DB query on `game_flaws` table with user-scoped WHERE | FLOWING |
| `GamesTab` | chips + M+B counts | `_build_card` → `fetch_page_game_flaws` → batched `SELECT FROM game_flaws WHERE game_id IN (page_ids)` | Yes — real DB query, no static returns | FLOWING |
| `FlawsTab` | `matched_count` | `query_flaws` count subquery | Yes — `select(func.count()).select_from(base_stmt.subquery())` | FLOWING |

---

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| `sanToSquares` utility exports a function | `node -e "const m = require('./frontend/src/lib/sanToSquares.ts'); console.log(typeof m.sanToSquares)"` | SKIP — TypeScript source, not runnable directly | SKIP |
| Backend test suite green (all 2402) | `uv run pytest -n auto --tb=short` | 2402 passed, 10 skipped, 1 warning | PASS |
| Frontend test suite green (all 805) | `cd frontend && npm test -- --run` | 805 passed, 69 files | PASS |
| Phase tag rejected by router | `uv run pytest tests/test_library_router.py -k flaws -x` | 20 passed including `test_phase_tag_in_query_rejected_422` | PASS |

---

### Probe Execution

No probe scripts were declared in the phase PLAN files or SUMMARY files for Phase 108. Step 7c skipped — not applicable.

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|---------|
| D-01 | Plan 08 | Boolean severity toggle removed from LibraryFilterPanel; FlawFilterControl replaces it | SATISFIED | LibraryFilterPanel.tsx confirmed |
| D-02 | Plans 03, 04 | Games-surface (chips, counts, EXISTS) migrated to game_flaws | SATISFIED | library_service.py reads game_flaws via batched page query; old kernel re-call removed |
| D-03 | Plans 01-05 | Inaccuracy counts stay cheap aggregate; game_flaws is M+B only | SATISFIED | model, router, and service all enforce M+B only; oracle columns for inaccuracy |
| D-04 | Plans 07, 08 | Flaw filter state shared via useFlawFilterStore; Flaws URL-synced, Games not | SATISFIED | GamesTab uses store (no URL sync); FlawsTab uses useSearchParams |
| D-05 | Plans 07, 08 | Chip deep-link = /library/flaws?tag={TAG}, no game_id | SATISFIED | TagChip.tsx confirmed; tests assert exact URL |
| D-07 | Plan 05 | Recent-first ordering: played_at DESC, ply ASC | SATISFIED | query_flaws orders `Game.played_at.desc().nulls_last(), GameFlaw.ply.asc()` |
| D-08 | Plans 05, 07 | Page size 20; severity M+B only on Flaws | SATISFIED | `PAGE_SIZE = 20`; `limit = Query(default=20, ge=1, le=100)` |
| D-09 | Plan 06 | backfill_flaws.py with --db/--user-id/--dry-run; batched; prod not gated | SATISFIED | Script exists with all args and BACKFILL_GAMES_PER_BATCH constant |
| D-10 | Plans 02, 06 | One classify path: import hook + reclassify + backfill all call classify_game_flaws + flaw_record_to_row | SATISFIED | All three write paths confirmed in code |

---

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| No TBD/FIXME/XXX/TODO/HACK/PLACEHOLDER in any phase-modified file | — | — | — | Clean |

No debt markers found. No stubs. No hardcoded empty arrays as rendered state. All critical REVIEW findings (CR-01 marked-move arrow, CR-02 theme.ts color, CR-03 deduplicated default check) were fixed in commit 527f8e4d as documented in the phase description.

**Remaining REVIEW warnings (non-blocking, advisory):**
- WR-01: `query_filtered_games` count subquery fetches full ORM model (minor perf, pre-existing pattern)
- WR-02: `fen` column `server_default=""` in migration (never exercised by flaw_record_to_row in practice)
- WR-03: URL-sync write effect may fire before mount-init completes (transient flicker on deep-link, self-corrects)
- WR-04: `query_flaws` applies user_id scoping twice (functionally correct, extra subquery)
- WR-05: `backfill_flaws.py` loads all game IDs into memory before batching (acceptable at current scale)

These are documented in 108-REVIEW.md and do not block the phase goal.

---

### Human Verification Required

### 1. Miniboard Marked-Move Arrow Correctness

**Test:** Navigate to `/library/flaws` as a user with analyzed Lichess games. Inspect multiple flaw rows. For each row with a `move_san`, verify the red arrow on the miniboard points from the source square to the destination square of that specific move.
**Expected:** Arrow correctly highlights the flawed move. No row shows an arrow at `e1→e1` or any wrong squares. Rows with castling or en passant (where `sanToSquares` returns null) show no arrow — this is correct fallback behavior.
**Why human:** `sanToSquares` runs in the browser using chess.js against real FEN+SAN data from the DB. The unit test (`FlawsTab.test.tsx`) mocks `useLibraryFlaws` and cannot exercise actual chess.js SAN parsing against production FEN strings.

### 2. Cross-Family AND Filter (Single-Flaw EXISTS Semantics)

**Test:** In the Flaws tab, select a Timing tag (e.g. "low-clock") and an Impact tag (e.g. "result-changing"). Observe the matched count and results.
**Expected:** Only rows where a SINGLE ply is tagged with BOTH low-clock AND result-changing appear. If you have separate flaws where one is low-clock and another (different ply) is result-changing, those games are NOT returned. The matched count may be 0 — this is correct (proving single-flaw EXISTS semantics are working).
**Why human:** The AND-across-families-per-flaw behavior is tested at the DB layer by `test_flaw_predicate.py`, but the end-to-end filter UX (select combinations, see results update) requires a running app with real data.

### 3. Deep-Link Navigation and Pre-Population

**Test:** Click a tag chip (e.g. "result-changing") on a game card in the Games tab.
**Expected:** Browser navigates to `/library/flaws?tag=result-changing`. The Flaws tab activates. The "Impact" family group in FlawFilterControl shows "result-changing" button highlighted in its family color. The list shows only flaws with that tag. The "Clear flaw filter" link is visible.
**Why human:** React Router navigation + URL parameter to Zustand store initialization + visual component state requires a running app.

### 4. Cross-Tab Filter State Persistence

**Test:** On the Games tab, select only "Blunders" severity. Then switch to the Flaws tab. Then switch back to the Games tab.
**Expected:** Both tabs show "Blunders" selected throughout. The Flaws tab URL updates to `?severity=blunder`. Switching back to Games preserves the selection (no reset to default).
**Why human:** Shared store behavior across tab switches in a real running app cannot be covered by unit tests.

### 5. Mobile Drawer Layout (FlawFilterControl)

**Test:** Open the app on a mobile viewport (or browser DevTools 375px). Navigate to `/library/flaws`. Tap the "Filters" button. Verify the drawer opens and FlawFilterControl is visible with all 3 family groups.
**Expected:** Drawer renders FlawFilterControl with "Show flaws with:" section, Timing/Opportunity/Impact groups, tag buttons with adequate 44px touch targets. "Clear flaw filter" appears when filter is non-default.
**Why human:** Mobile drawer and touch-target sizing require visual inspection; automated tests use a jsdom environment.

### 6. Empty-State Discrimination

**Test:** As a user with Lichess games imported but none with engine analysis, navigate to `/library/flaws`.
**Expected:** Empty state heading "No analyzed games" with body "Only Lichess games with engine analysis have flaws. Import Lichess games to see your flaws." — NOT the "No games imported yet" state.
**Why human:** Triggering this specific empty state requires a real data condition (games imported but none analyzed); not covered by mocked tests.

---

### Gaps Summary

No gaps found. All 22 must-have truths are verified in the codebase. The 6 human verification items above are for visual/interaction correctness of new UI surfaces that automated tests cannot fully cover.

The phase goal is substantively achieved: `game_flaws` table is materialized and populated by the import pipeline; the Games-surface reads from it; `GET /library/flaws` is live with IDOR protection, pagination, and Literal-validated filters; the shared predicate builder enforces cross-tab unification in code; the Flaws subtab renders per-flaw miniboard rows with correct marked-move arrows (CR-01 fix confirmed); FlawFilterControl is wired in both tabs via the shared store; tag chips deep-link correctly to `/library/flaws?tag={TAG}` without game_id.

---

_Verified: 2026-06-06T20:00:00Z_
_Verifier: Claude (gsd-verifier)_
