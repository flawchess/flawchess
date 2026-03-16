# Project Research Summary

**Project:** Chessalytics v1.1 — Move Explorer & UI Restructuring
**Domain:** Chess analysis platform — personal opening explorer with position-based statistics
**Researched:** 2026-03-16
**Confidence:** HIGH

## Executive Summary

Chessalytics v1.1 adds a Move Explorer to the existing Zobrist-hash-based position analysis platform and restructures the navigation from flat pages to a tabbed Openings page. The core technical work is a focused schema addition (`move_san VARCHAR(10) NULLABLE` on `game_positions`), one new backend endpoint (`POST /analysis/next-moves`), and a frontend reorganization from two pages to three (`/`, `/openings` with sub-tabs, `/import`). No new libraries or version bumps are required — the entire v1.1 scope is achievable with capabilities already present in the installed stack.

The recommended approach follows the existing architecture's discipline: push aggregation into PostgreSQL using a `GROUP BY move_san` query (not Python-level Counter), gate sub-tab queries with `enabled: activeTab === '...'` to avoid wasted fetches, and store `move_san` at the ply FROM which the move was played (not the destination ply). The existing `(user_id, full_hash)` index covers the move explorer query; a covering index extension `(user_id, full_hash, move_san)` eliminates heap fetches and is the only new index needed. The project already accepts a DB wipe for v1.1, so no backfill migration is required.

The key risk is the double-counting trap: transpositions can place the same position at multiple plies in one game, and `COUNT(*)` instead of `COUNT(DISTINCT g.id)` silently inflates move statistics. A secondary risk is filter state fragmentation — if filter state is not lifted to the `OpeningsPage` parent, switching between sub-tabs will reset filter selections, which is the most likely UX regression in the restructuring. Both risks have clear, low-cost prevention strategies documented in detail.

## Key Findings

### Recommended Stack

The v1.0 stack carries over entirely unchanged. No new packages are needed for v1.1. The only backend schema addition is `move_san VARCHAR(10) NULLABLE` on `game_positions`, populated at import time via `python-chess`'s `board.san(move)` before `board.push(move)`. The frontend uses the already-installed `shadcn/ui Tabs` (radix-ui), `shadcn Table`, `chess.js`, `TanStack Query`, and `react-router-dom` — all already present.

**Core technologies (v1.1 specific):**
- `python-chess board.san(move)`: SAN generation at import time — zero new cost, already a dependency
- `SQLAlchemy async self-join / GROUP BY on game_positions`: move explorer aggregation — existing `select()` API handles cleanly
- `shadcn/ui Tabs` (already installed): sub-tabs in Openings page — no competing tab primitives needed
- `TanStack Query useQuery`: `useNextMoves` hook follows identical pattern to existing analysis hooks
- `react-router-dom` (already installed): `/import` route requires one new `<Route>` entry

### Expected Features

**Must have (table stakes — v1.1 launch):**
- Move table showing next moves with SAN, game count, W/D/L counts and percentages
- Stacked W/D/L bar per move row — visual pattern users are trained on from lichess/chess.com
- Click a move row to advance board position — core interaction, drives new next-moves fetch
- Reset to starting position button
- Sub-tab structure: Openings splits into Move Explorer / Games / Statistics
- Shared filter sidebar — single filter state drives all three sub-tabs
- Dedicated Import page at `/import` — full page replacing the modal

**Should have (competitive differentiators):**
- Move explorer scoped to user's imported games only — personal stats, not global master DB
- "As white" / "as black" W/D/L split — shows YOUR results, not global averages
- Sub-tabs share filter AND board position state — unified view no competitor offers
- Position-independent of opening name — Zobrist hash works at any depth, not ECO-capped

**Defer (v2+):**
- Engine evaluation per move — Stockfish process management, CPU scaling, scope explosion risk
- Opening tree visualization — render performance problem at low sample sizes
- Rating-based filter — dilutes already-small personal game samples

### Architecture Approach

The architecture extends the existing three-layer pattern (router → service → repository) with one new endpoint and migrates the UI from two flat pages to three pages. The `hashes_for_game()` function in `zobrist.py` is extended to return 5-tuples `(ply, wh, bh, fh, move_san)` instead of 4-tuples, which propagates through `_flush_batch()` in the import pipeline. The frontend restructuring extracts `GamesTab` from Dashboard logic, `StatisticsTab` from the current OpeningsPage charts, and adds `MoveExplorerTab` as new functionality — with `OpeningsPage` owning all shared state.

**Major components:**
1. `game_positions` table — ADD `move_san VARCHAR(10) NULLABLE` + covering index `(user_id, full_hash, move_san)`
2. `hashes_for_game()` + `_flush_batch()` pipeline — MODIFY to populate `move_san` at import time
3. `query_next_moves()` / `get_next_moves()` / `POST /analysis/next-moves` — NEW aggregation stack
4. `MoveExplorerTab` + `useNextMoves` hook — NEW frontend explorer component
5. `OpeningsPage` restructure — ADD board state, shared `FilterPanel`, `Tabs` with three sub-tabs
6. `ImportPage` at `/import` — NEW full-page import UI lifted from the existing `ImportModal`

### Critical Pitfalls

1. **DISTINCT + GROUP BY double-counting** — transpositions cause the same position to appear at multiple plies in one game; use `COUNT(DISTINCT g.id)` in the aggregation, not `COUNT(*)`; the existing `_build_base_query` already applies `.distinct(Game.id)` for this exact reason and the next-moves query must match that discipline.

2. **Ply-0 move_san nullability** — ply-0 rows represent the initial position (no move played yet); `move_san` must be nullable; `NULL` is the correct value for the final game position too; any NOT NULL constraint causes import failures; always filter `WHERE gp.move_san IS NOT NULL` in explorer queries.

3. **Python-level aggregation anti-pattern** — the existing service does lightweight result counting in Python, which is fine for per-game rows; doing the same for move aggregation would fetch O(N×plies) rows; push `GROUP BY move_san` entirely to PostgreSQL to keep the response O(moves) regardless of game count.

4. **Shared filter state fragmentation** — if filter state lives inside each sub-tab component, React unmount/remount on tab switch resets filters; lift ALL shared filter state to `OpeningsPage` and pass down as read-only props.

5. **Import page missing post-import query invalidations** — after moving import to `/import`, the `handleJobDone` callbacks that invalidate `['games']`, `['gameCount']`, `['userProfile']` must be replicated in the new page; omitting them causes stale game counts after import.

## Implications for Roadmap

Based on the dependency graph and pitfall-to-phase mapping in the research, a four-phase structure is recommended:

### Phase 1: Schema + Import Pipeline (move_san)
**Rationale:** Everything else depends on `move_san` being populated. The DB wipe is already accepted. This is the only schema-blocking dependency. Ply semantics must be locked here — a wrong-ply bug requires a full re-import to fix (HIGH recovery cost).
**Delivers:** `move_san` populated on all `game_positions` rows; covering index added; clean DB with verified import
**Addresses:** SAN stored in game_positions (the P1 feature that blocks all explorer work)
**Avoids:** Pitfall 2 (ply-0 nullability), Pitfall 3 (wrong index strategy) — both must be resolved in this phase before migration runs

### Phase 2: Backend — Next-Moves Endpoint
**Rationale:** Frontend explorer is blocked on this endpoint. The query pattern (DISTINCT + GROUP BY conflict) must be solved before the frontend can be built. Validate the SQL with `EXPLAIN ANALYZE` against real data before wiring to the API.
**Delivers:** `POST /analysis/next-moves` returning `[{move_san, game_count, wins, draws, losses, win_pct, draw_pct, loss_pct}]`
**Uses:** `query_next_moves()` mirroring existing `query_all_results` pattern; new Pydantic schemas in `schemas/analysis.py`
**Avoids:** Pitfall 1 (DISTINCT + GROUP BY conflict), Pitfall 4 (Python-level aggregation)

### Phase 3: Frontend — Move Explorer Component
**Rationale:** Depends on Phase 2 endpoint. Can be built and validated standalone (MoveExplorerTab with board + move table) before the full Openings restructuring, reducing integration risk.
**Delivers:** `MoveExplorerTab` with clickable move rows, stacked W/D/L bars, reset button; `useNextMoves` TanStack Query hook
**Implements:** MoveExplorerTab component and useNextMoves hook

### Phase 4: Frontend — UI Restructuring (Openings + Import)
**Rationale:** Import page migration and Openings sub-tab restructuring are largely independent of each other and can be built in parallel. MoveExplorerTab integration into the restructured Openings page is the final integration step that unifies Phases 3 and 4.
**Delivers:** Restructured `/openings` with board, shared FilterPanel, three sub-tabs; `/import` dedicated page replacing Dashboard modal
**Avoids:** Pitfall 5 (shared filter state — design state architecture before writing any component code), Pitfall 6 (import page missing invalidations — explicit checklist item at handoff)

### Phase Ordering Rationale

- Phases 1 → 2 → 3 are a strict dependency chain: schema blocks endpoint, endpoint blocks explorer component.
- Phase 4 is largely independent and can begin once Phase 1 is done; ImportPage and sub-tab shell require no explorer work, but MoveExplorerTab integration waits for Phase 3.
- The pitfall-to-phase mapping from PITFALLS.md directly validates this order: schema pitfalls (2, 3) are resolved in Phase 1, query pitfalls (1, 4) in Phase 2, UI state pitfall (5) and import pitfall (6) in Phase 4.

### Research Flags

Phases with well-documented patterns (skip `research-phase` during planning):
- **Phase 1 (Schema):** Nullable column addition in PostgreSQL ≥11 is metadata-only; `board.san(move)` API is stable; pattern is identical to how Zobrist hashes are already populated.
- **Phase 2 (Backend endpoint):** Query pattern mirrors `query_all_results` with `_build_base_query`; `COUNT(DISTINCT)` and SQLAlchemy `func.count(...distinct())` are standard.
- **Phase 3 (Move Explorer component):** Follows identical pattern to existing TanStack Query hooks (`useAnalysis`, `useGamesQuery`).
- **Phase 4 (UI Restructuring):** shadcn Tabs already installed and used; React Router route addition is trivial; filter state lifting is a standard React pattern.

No phase requires deeper external research — all patterns are directly validated from codebase inspection.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All v1.1 requirements satisfied by currently installed packages; confirmed by direct `package.json` and `pyproject.toml` inspection |
| Features | HIGH | Move explorer feature set validated against lichess Explorer source, chess.com Game Explorer docs, and openingtree.com; table stakes and differentiators are well-established |
| Architecture | HIGH | Based on direct codebase analysis of v1.0 implementation; all component boundaries and data flows confirmed against actual source files |
| Pitfalls | HIGH | Derived from direct inspection of existing `analysis_repository.py` (DISTINCT ON pattern), `zobrist.py` (ply loop), and `Dashboard.tsx` (import invalidation logic) |

**Overall confidence:** HIGH

### Gaps to Address

- **move_san ply semantics — document explicitly:** ARCHITECTURE.md clarifies the correct semantic: `move_san` on ply N is the move played FROM the position at ply N (leading to ply N+1); the final position row has `NULL`. This must be documented in the model class before the Alembic migration runs to prevent off-by-one errors that require a full re-import to fix.

- **positionFilterActive gating for Move Explorer:** A UX decision is needed before Phase 3: should the Move Explorer auto-trigger when the board is at the starting position (showing potentially hundreds of moves), or should it only activate once the user has played at least one move or loaded a bookmark? Recommend gating on "at least 1 move played or bookmark loaded" to avoid an overwhelming starting-position list — this aligns with the `positionFilterActive` pattern already used in Dashboard.

- **GamesTab pagination state survival across tab switches:** Phase 4 planning should explicitly decide whether the Games sub-tab page offset survives tab switches. PITFALLS.md recommends lifting `offset` to `OpeningsPage` state — this should be a checklist item in Phase 4 to avoid a silent UX regression.

## Sources

### Primary (HIGH confidence)

- Direct codebase inspection: `app/models/game_position.py`, `app/repositories/analysis_repository.py`, `app/services/zobrist.py`, `app/services/import_service.py` — existing schema, query patterns, import pipeline
- Direct codebase inspection: `frontend/src/pages/Dashboard.tsx`, `frontend/src/pages/Openings.tsx`, `frontend/src/App.tsx` — UI structure, import modal, routing
- Direct codebase inspection: `frontend/package.json`, `frontend/src/components/ui/tabs.tsx`, `frontend/src/components/ui/table.tsx` — confirmed installed dependencies
- `.planning/PROJECT.md` — v1.1 scope, DB wipe decision confirmed
- python-chess API: `board.san()`, `board.peek()` — stable since 1.x

### Secondary (MEDIUM confidence)

- [lichess opening explorer source (lila-openingexplorer)](https://github.com/lichess-org/lila-openingexplorer) — confirms move table columns (move, white/draws/black)
- [chess.com Game Explorer help](https://support.chess.com/en/articles/8708732-how-do-i-use-the-game-explorer) — confirms stacked bar, click-to-navigate pattern
- [openingtree/openingtree GitHub](https://github.com/openingtree/openingtree) — confirms personal game move tree with W/D/L
- PostgreSQL documentation on DISTINCT ON + GROUP BY constraint and ALTER TABLE ADD COLUMN metadata-only behavior (≥11)
- TanStack Query staleTime and invalidation patterns

---
*Research completed: 2026-03-16*
*Ready for roadmap: yes*
