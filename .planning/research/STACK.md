# Stack Research

**Domain:** Chess analysis platform — v1.1 Move Explorer & UI Restructuring
**Researched:** 2026-03-16
**Confidence:** HIGH

## Scope Note

This document covers ONLY additions and changes needed for v1.1. The base
stack (FastAPI, React 19, PostgreSQL, SQLAlchemy async, TanStack Query,
Tailwind, shadcn/ui, Recharts, react-chessboard, chess.js, python-chess)
is validated and in production. Those choices are not re-evaluated here.

---

## Recommended Stack

### Core Technologies

All core technologies carry over from v1.0 unchanged.

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| python-chess | >=1.10.0 | SAN generation at import time | `board.san(board.peek())` after pushing a move yields the SAN string for the move just played — already a dependency, zero new cost |
| SQLAlchemy async | 2.x | Move explorer aggregation query (self-join on game_positions) | The existing `select()` API handles the self-join pattern cleanly; no raw SQL or new extension needed |
| shadcn/ui Tabs | installed | Sub-tabs in Openings page | Already installed at `components/ui/tabs.tsx`; uses radix-ui already present |
| react-router-dom | ^7.13.1 | `/import` route for dedicated Import page | Already installed; add one `<Route>` entry |

### Supporting Libraries

No new libraries are required. The following existing libraries satisfy all v1.1 needs:

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| chess.js | ^1.4.0 | Advance board state on move click in Move Explorer | Call `chess.move(san)` when user clicks a next-move row; pass updated FEN to react-chessboard and issue a new query |
| TanStack Query | ^5.90.21 | Fetch next-move aggregations from new endpoint | Add a `useNextMoves(hash, filters)` hook using `useQuery`; same pattern as existing analysis hooks |
| lucide-react | ^0.577.0 | Icons in Move Explorer rows (W/D/L color indicators, back button) | Already installed; no new icon set needed |
| shadcn Table | installed | Render next-move rows with SAN, counts, percentages | `components/ui/table.tsx` is already installed |

### Development Tools

No new development tools required. Existing ruff, pytest, TypeScript, Vite, and ESLint setup covers all v1.1 work.

---

## Installation

No new packages to install. All required capabilities are already present.

```bash
# Backend — no changes to pyproject.toml
# Frontend — no changes to package.json
```

The only changes are:
1. A new Alembic migration adding `move_san VARCHAR(10)` and a `(game_id, ply)` index to `game_positions`
2. New source files following existing patterns

---

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| shadcn Tabs (already installed) | react-tabs, @headlessui/react Tabs | Never — adding a second tab primitive creates competing abstractions for no benefit |
| SQL self-join on game_positions for next moves | Precompute a `move_tree` table | Only if profiling shows the self-join is slow at scale (thousands of users, millions of positions); premature now |
| python-chess `board.san()` at import time | Derive SAN at query time from move UCI | Import time is the right place — same approach as Zobrist hash computation; querying with replay would be O(n × depth) |
| Lifted React state for shared filter sidebar | Zustand, Redux, Jotai | Only if filter state needs to be shared across page-level route boundaries; here it stays within the Openings page subtree |
| react-router-dom `/import` page route | Keep Import as a modal | A dedicated page is the stated goal; also simplifies deep-linking and removes the Dialog wrapper complexity |

---

## What NOT to Add

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| A polyglot opening book library (e.g., python-chess `polyglot`) | Opening books contain engine-selected moves; this feature shows the user's own game statistics, not engine recommendations | SQL GROUP BY aggregation over the user's game_positions |
| Zustand or Redux for filter state | The shared filter sidebar lives in one React subtree (Openings page); `useState` lifted to the parent is the correct scope | `useState` in the restructured `Openings.tsx` or a shared `useOpeningsFilters` hook |
| react-router nested routes for sub-tabs | Sub-tabs are UI-only state, not distinct URLs; nested routes would couple URL structure to a UI detail without user benefit | shadcn `Tabs` with `defaultValue` state |
| A materialized `move_tree` or `move_aggregates` table | Adds write-time complexity, cache invalidation, and schema surface area; the self-join is efficient on indexed columns | Query-time aggregation in the new analysis_repository function |
| Any new HTTP client or API integration | v1.1 adds no new external data sources | Existing httpx AsyncClient handles all external calls |

---

## Schema Change Summary

The only backend schema addition needed:

```sql
-- Add move SAN to game_positions (NULL for ply 0, before any move)
ALTER TABLE game_positions ADD COLUMN move_san VARCHAR(10);

-- Index to accelerate the self-join (ply + 1 lookup)
CREATE INDEX ix_gp_game_id_ply ON game_positions (game_id, ply);
```

`move_san` is populated at import time in the import pipeline, immediately
after `board.push(move)` — call `board.san(board.peek())` before pushing, or
use the existing `board.move_stack` to retrieve the SAN after the push via
`board.peek()`.

The PROJECT.md decision to wipe and reimport for v1.1 means no backfill
migration is needed; a clean `ALTER TABLE` migration is sufficient.

---

## Move Explorer Query Pattern

The aggregation query the new repository function will execute:

```sql
SELECT
    gp_next.move_san,
    gp_next.full_hash   AS next_full_hash,
    COUNT(DISTINCT g.id) AS total,
    SUM(CASE WHEN g.result = 'win'  THEN 1 ELSE 0 END) AS wins,
    SUM(CASE WHEN g.result = 'draw' THEN 1 ELSE 0 END) AS draws,
    SUM(CASE WHEN g.result = 'loss' THEN 1 ELSE 0 END) AS losses
FROM game_positions gp_current
JOIN game_positions gp_next
    ON  gp_next.game_id = gp_current.game_id
    AND gp_next.ply     = gp_current.ply + 1
JOIN games g
    ON  g.id = gp_current.game_id
WHERE gp_current.user_id   = :user_id
  AND gp_current.<hash_col> = :target_hash
  -- optional: AND g.time_control_bucket IN (...) etc.
GROUP BY gp_next.move_san, gp_next.full_hash
ORDER BY total DESC;
```

The `(user_id, full_hash)` composite index on `game_positions` (existing)
covers the `gp_current` filter. The new `(game_id, ply)` index covers the
`gp_next` self-join lookup. SQLAlchemy ORM or core expression layer handles
this without raw SQL.

---

## Version Compatibility

No version bumps required for v1.1. All additions use APIs stable in current
installed versions.

| Package | Current Version | v1.1 Usage | Notes |
|---------|----------------|------------|-------|
| radix-ui | ^1.4.3 | Tabs (already using) | No change |
| python-chess | >=1.10.0 | `board.san()`, `board.peek()` | Stable since 1.x |
| react-router-dom | ^7.13.1 | Add `/import` route | No config changes |
| TanStack Query | ^5.90.21 | New `useNextMoves` hook | Same pattern as existing hooks |
| shadcn Table | installed | Move Explorer rows | Already in project |

---

## Sources

- Codebase inspection: `frontend/src/components/ui/tabs.tsx` — Tabs component confirmed installed, using radix-ui — HIGH confidence
- Codebase inspection: `frontend/package.json` — all existing deps confirmed — HIGH confidence
- Codebase inspection: `frontend/src/components/ui/table.tsx` confirmed present via `ls components/ui/` — HIGH confidence
- Codebase inspection: `app/models/game_position.py` — current schema confirmed — HIGH confidence
- Codebase inspection: `app/repositories/analysis_repository.py` — existing query pattern confirmed — HIGH confidence
- python-chess API: `board.san()`, `board.peek()` — standard documented API, unchanged in 1.x — HIGH confidence

---
*Stack research for: Chessalytics v1.1 Move Explorer & UI Restructuring*
*Researched: 2026-03-16*
