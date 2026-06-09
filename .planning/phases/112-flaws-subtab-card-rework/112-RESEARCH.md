# Phase 112: Flaws Subtab Card Rework - Research

**Researched:** 2026-06-09
**Domain:** React card components, FastAPI endpoint, SQLAlchemy join, Alembic drop-column migration
**Confidence:** HIGH

## Summary

Phase 112 reworks the Library → Flaws subtab from a flat `FlawRow` list to a responsive 2-up `FlawCard` grid, adds a "View game" modal backed by a new `GET /api/library/games/{game_id}` endpoint, and slim the `game_flaws` schema by dropping three columns now served via a `game_positions` join. The decisions are fully locked in CONTEXT.md (D-01..D-12); this research is purely implementation-ready detail for the planner.

The backend work has a clean path: `game_positions` already stores `eval_cp`, `eval_mate`, and `move_san` indexed on the natural PK `(game_id, user_id, ply)`. The flaw-list query in `library_repository.query_flaws` simply joins one additional `game_positions` row per flaw row (same game_id + ply), reads those three columns, and the join replaces the three dropped columns. The drop-column Alembic migration follows the established `op.drop_column` pattern; because this is dev-only (v1.24 unshipped) the migration needs no server_default gymnastics.

The frontend work reuses all named components verbatim: `CardHeader`, `LazyMiniBoard` at 132px, `TagChip`/`TagLegend`, `SeverityBadge`, `Dialog`/`DialogContent`, `LoadError`, and `useLibraryFlaws`. The new `FlawCard` sibling component mirrors `LibraryGameCard`'s column-1 pattern. The eval swing formatter is extracted from `EvalChart.formatEval` (currently a module-private function, lines 303-315) by moving it to a shared utility or re-implementing it — the logic is trivially extractable: `eval_mate` → `#±N`, `eval_cp` → signed 1-decimal pawns using `formatSignedEvalPawns`.

**Primary recommendation:** Implement in four waves: (0) schema migration + backfill; (1) backend join + new endpoint; (2) new `FlawCard` component + `useLibraryGame` hook; (3) grid replacement + modal wiring in `FlawsTab`.

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01 (grid):** `grid-cols-1 lg:grid-cols-2` — 1-up below 1024px, 2-up at `lg`+. Never 3-up.
- **D-02 (within-card):** Board left (132px) + content stacked on the right: move (standard notation) + eval swing + severity badge → tag chips → `Explanation` (`TagLegend`) → metadata (date · TC · termination + result indicator).
- **D-03 (header):** `CardHeader` matching the Games card — desktop single line `■ White (rating) vs □ Black (rating)`, mobile two stacked lines — plus the platform link. Requires adding `white_rating`/`black_rating` to `FlawListItem`.
- **D-04 (notation):** Flawed move in standard notation (`16...Nxd4`; white `N.`, black `N...`) via the shared `formatCandidateMove` helper (`lib/openingInsights.ts`).
- **D-05 (eval swing — source):** Show before → after eval from `eval_cp`/`eval_mate` from `game_positions` — NOT an ES→eval round-trip. Rationale: ES saturates near ±1 for mate.
- **D-06 (eval swing — format & POV):** Both endpoints rendered user-POV — negate `eval_cp`/`eval_mate` for `user_color === 'black'`. Reuse a formatter extracted from `EvalChart.formatEval` (line 304). Do not reuse the ES→pawns `evalStr` inverse-sigmoid in `tagDefinitions.ts`.
- **D-07 (drop dead columns):** Drop `es_before`, `es_after`, AND `move_san` from `game_flaws`. Keep `fen`. Alter migration. Dev-only; re-run `scripts/backfill_flaws.py` for dev users.
- **D-08 (read via join):** Flaw-list endpoint joins `game_positions`. `game_flaws.ply = n`, `move_san = positions[n].move_san`, board-before = `fen_map[n]`. Before/after eval offsets must be verified empirically before dropping ES.
- **D-09 (presentation):** One responsive `Dialog` — wide + centered on desktop (`max-w-4xl`), near-fullscreen + internal scroll on mobile. Reuse `LibraryGameCard` verbatim as the body. Loading = spinner; error = `LoadError`.
- **D-10 (backend):** New `GET /api/library/games/{game_id}` returning one `GameFlawCard`, reusing the existing list card-builder scoped to a single id. New `useLibraryGame(id)` hook fetches on modal open.
- **D-11 (trigger):** Dedicated "View game" button only (in the card body). Not whole-card-clickable.
- **D-12:** Keep the existing exact-ply external platform deep-link (`flawPlyUrl`) in the card header AND add the in-app "View game" button. Two distinct destinations.

### Claude's Discretion
- "View game" button label/icon and exact placement in the content stack.
- Spinner vs skeleton for the modal loading state; the `Dialog` `max-w-*` value.
- Exact metadata ordering within the content stack (date/TC/termination grouping).
- `data-testid`/ARIA naming (follow CLAUDE.md browser-automation conventions).

### Deferred Ideas (OUT OF SCOPE)
- Modal auto-scrub/highlight to the specific flaw's ply.
- The Analysis detail viewer and best-move endpoint (SEED-036).
- Any change to flaw classification logic, tag taxonomy, or the cross-tab Flaw filter.
</user_constraints>

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| FlawListItem eval + move_san | API/Backend | Database (join) | Data lives in `game_positions`; repository joins it |
| `game_flaws` schema slim | Database | API/Backend (classifier) | Alter migration + stop persisting 3 cols in `flaw_record_to_row` |
| `GET /api/library/games/{game_id}` | API/Backend | — | Single-game `GameFlawCard` reusing existing `_build_card` |
| `FlawCard` 2-up grid | Browser/Client | — | Pure React component; no new server state |
| "View game" Dialog modal | Browser/Client | — | Client-side modal; fetches game on open via `useLibraryGame` |
| Eval swing formatter | Browser/Client | — | Extracted from `EvalChart.formatEval`; no server involvement |
| `useLibraryGame(id)` hook | Browser/Client | API/Backend | TanStack Query hook fetching the single-game endpoint |

---

## Standard Stack

### Core (already in project — no new installs)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| React 19 + TypeScript | 19.x | Component layer | Project stack [ASSUMED: project CLAUDE.md] |
| TanStack Query | 5.x | `useLibraryGame` hook | Existing pattern in `useLibrary.ts` [ASSUMED] |
| Radix UI `Dialog` | latest | Modal primitive | Already in `components/ui/dialog.tsx` [ASSUMED] |
| SQLAlchemy 2.x async | 2.x | `game_positions` join in repository | Project stack [ASSUMED] |
| Alembic | latest | Drop-column migration | Existing migration chain [ASSUMED] |
| chess.js | — | FEN/SAN (sanToSquares) | Already used in FlawsTab [ASSUMED] |

No new packages are installed in this phase.

### Package Legitimacy Audit

No new packages are introduced by this phase. Section is N/A.

---

## Architecture Patterns

### System Architecture Diagram

```
FlawsTab (existing)
  │
  ├── FlawCard (NEW — sibling to LibraryGameCard)
  │   ├── CardHeader   [reused verbatim]
  │   │   └── ■ White (rating) vs □ Black (rating) + platform link (flawPlyUrl)
  │   ├── body row:
  │   │   ├── LazyMiniBoard 132px [reused verbatim]
  │   │   └── content stack:
  │   │       ├── formatCandidateMove(plySequence, move_san) + formatFlawEval(before, after, user_color)
  │   │       ├── SeverityBadge  [reused verbatim]
  │   │       ├── TagChip × N   [reused verbatim, definition=true]
  │   │       ├── TagLegend     [reused verbatim]
  │   │       ├── metadata: date · TC · termination+result
  │   │       └── "View game" Button → opens Dialog
  │   └── Dialog (modal)
  │       └── LibraryGameCard (verbatim)
  │           └── fetched via GET /api/library/games/{game_id}
  │               └── useLibraryGame(id) hook [NEW]
  │
  └── grid: grid-cols-1 lg:grid-cols-2 (replaces flex-col gap-3)

Backend changes:
  game_flaws table ─── ALTER: drop es_before, es_after, move_san
  library_repository.query_flaws ─── JOIN game_positions ON (game_id, ply, user_id)
  FlawListItem schema ─── drop es/san fields; add white_rating, black_rating, eval_before/after
  GET /api/library/games/{game_id} [NEW] ─── reuses _build_card scoped to one game_id
```

### Recommended Project Structure

No new directories. New files:

```
frontend/src/
├── components/library/
│   └── FlawCard.tsx        # NEW — sibling to LibraryGameCard
├── hooks/
│   └── useLibrary.ts       # EXTEND — add useLibraryGame(id)
app/
├── routers/library.py      # EXTEND — add GET /games/{game_id}
├── schemas/library.py      # EXTEND — update FlawListItem + add FlawListItemEval
├── repositories/library_repository.py  # EXTEND — join in query_flaws + new fetch_single_game
├── services/library_service.py         # EXTEND — add get_library_game(game_id)
├── models/game_flaw.py     # EDIT — remove 3 mapped_columns + docstring update
alembic/versions/
└── 20260609_drop_game_flaws_display_cols.py  # NEW alter migration
```

---

## Eval-Join Off-By-One: Authoritative Offset Mapping

This is Pitfall 1 from CONTEXT.md. The research has read both `_run_all_moves_pass` and `_build_flaw_record` in `flaws_service.py` and can document the authoritative semantics.

### How positions indexing works

In `flaws_service._run_all_moves_pass` (lines 210-234):

```python
# n iterates 1..len(positions)-1
# mover: even n = white, odd n = black   (ply n % 2 == 0 → white plays, n % 2 == 1 → black plays)
es_before = _ply_to_es(positions[n - 1], mover)  # board BEFORE the move
es_after  = _ply_to_es(positions[n],     mover)  # board AFTER the move
```

And in `_build_flaw_record` (lines 238-264):

```python
# The comment is explicit:
# `n` is the 0-indexed half-move of the flawed move.
# positions[n].move_san  is the move played FROM ply n.
# fen_map[n]             is the board BEFORE the flawed move
#                        (fen_map[0]=start, fen_map[n] = n moves already played).
return FlawRecord(
    ply=n,
    fen=fen_map.get(n, ""),   # board BEFORE move n
    move_san=positions[n].move_san,   # move played AT ply n
    es_before=es_before,      # = _ply_to_es(positions[n-1], mover)
    es_after=es_after,        # = _ply_to_es(positions[n],   mover)
)
```

### Authoritative join mapping

For a `game_flaws` row with `ply = N`:

| Field | Source | SQL join |
|-------|--------|----------|
| `move_san` | `positions[N].move_san` | `game_positions WHERE game_id=? AND user_id=? AND ply=N` |
| eval BEFORE | `positions[N-1].eval_cp / eval_mate` | `game_positions WHERE ... AND ply=N-1` |
| eval AFTER | `positions[N].eval_cp / eval_mate` | `game_positions WHERE ... AND ply=N` (same row as move_san) |

The join for eval-after and move_san is the **same row** (`ply=N`). Eval-before requires a second join on `ply=N-1`. This is two joins per flaw row.

### Practical query pattern

```sql
-- join_ply_n:   game_positions p1 ON p1.game_id = f.game_id AND p1.user_id = f.user_id AND p1.ply = f.ply
-- join_ply_n_1: game_positions p0 ON p0.game_id = f.game_id AND p0.user_id = f.user_id AND p0.ply = f.ply - 1
SELECT f.*, p1.move_san, p1.eval_cp AS eval_cp_after, p1.eval_mate AS eval_mate_after,
            p0.eval_cp AS eval_cp_before, p0.eval_mate AS eval_mate_before
FROM game_flaws f
LEFT JOIN game_positions p1 ON p1.game_id=f.game_id AND p1.user_id=f.user_id AND p1.ply=f.ply
LEFT JOIN game_positions p0 ON p0.game_id=f.game_id AND p0.user_id=f.user_id AND p0.ply=f.ply-1
```

`LEFT JOIN` is correct: ply 0 has no ply-1 (first move), so `p0` may be NULL. The planner should handle `eval_cp_before IS NULL` by falling back to `None`.

### ES reproduction verification (regression guard)

Before dropping the ES columns, the planner's Wave 0 plan must:
1. Add the `game_positions` join to `query_flaws` producing `eval_cp_before/after`.
2. Convert joined eval to ES using `eval_cp_to_expected_score(cp, mover_color)` (same function as `_ply_to_es` uses, with `MATE_CP_EQUIVALENT=1000` for mate rows).
3. Run a pytest fixture that queries dev DB rows where `es_before` and `es_after` still exist, and asserts `abs(computed_es - stored_es) < 1e-6` on a sample.
4. Only after the fixture passes, run the alter migration to drop the ES columns.

This is the empirical lock required by D-08/Pitfall 1.

---

## Reusable Asset Inventory

### Backend assets (read, understand, reuse)

**`app/models/game_flaw.py`** — 65 lines. Three mapped columns to remove: `es_before: Mapped[float]`, `es_after: Mapped[float]`, `move_san: Mapped[Optional[str]]`. `fen: Mapped[str]` stays. Docstring needs updating.

**`app/models/game_position.py`** — PK: `(game_id, user_id, ply)` (composite, lines 79-87). Relevant columns for the join: `move_san` (line 95), `eval_cp` (line 124), `eval_mate` (line 125). No dedicated index on `(game_id, user_id, ply)` beyond the PK itself — the PK is the index.

**`app/repositories/library_repository.py::query_flaws`** (lines 192-295) — currently reads `flaw.move_san`, `flaw.es_before`, `flaw.es_after` from `game_flaws` directly (lines 279-281). These three lines must be replaced with join-sourced values. The ORM query pattern is `select(GameFlaw, Game).join(Game, ...)` — extend to also join `GamePosition` twice (for ply N and ply N-1).

**`app/services/library_service.py::_build_card`** (lines 294-390) — the card builder that produces `GameFlawCard`. The single-game endpoint reuses it. The new `get_library_game(game_id)` service function needs to: (1) fetch the single `Game` by `game_id` (user-scoped), (2) check if analyzed, (3) fetch `game_flaws` rows and positions for that game, then call `_build_card`. This mirrors the multi-game loop in `get_library_games` but for one game_id.

**`app/repositories/game_flaws_repository.py::flaw_record_to_row`** (lines 42-115) — currently writes `es_before`, `es_after`, `move_san` to the row dict (lines 111-113). These three keys must be removed after the migration.

**`scripts/backfill_flaws.py`** — no changes needed to its logic (it calls `flaw_record_to_row` which will be updated). After the migration, running `uv run python scripts/backfill_flaws.py --db dev --user-id <id>` is the dev rebuild step.

### Frontend assets (read, understand, reuse)

**`FlawsTab.tsx::FlawRow`** (lines 48-141) — replaced entirely by the new `FlawCard`. The tab's outer scaffolding (filters, drawer, pagination, URL sync, empty states) is preserved. Only the flaw list rendering block (lines 414-419) changes: `<FlawRow>` → `<FlawCard>`, and `flex flex-col gap-3` → `grid grid-cols-1 lg:grid-cols-2 gap-4`.

**`LibraryGameCard.tsx::CardHeader`** pattern (lines 280-293) — the exact template for the `FlawCard` header. The pattern:
```tsx
<CardHeader as="h4" size="compact" className="rounded-t-md">
  <span className="hidden sm:block truncate text-foreground min-w-0">
    ■ {whiteName} {whiteRating}
    <span className="mx-1.5 text-muted-foreground font-normal">vs</span>□ {blackName} {blackRating}
  </span>
  <div className="flex sm:hidden min-w-0 flex-1 flex-col text-foreground">
    <span className="truncate">■ {whiteName} {whiteRating}</span>
    <span className="truncate">□ {blackName} {blackRating}</span>
  </div>
  {platformIconAndLink}
</CardHeader>
```
For `FlawCard`, `platformIconAndLink` is the exact-ply `flawPlyUrl` link (already present in the old `FlawRow`), not the `gamePlatformUrl` game-level link used in `LibraryGameCard`.

**`EvalChart.formatEval`** (lines 303-315) — currently module-private, white-POV, with `"Eval: "` prefix. For `FlawCard`, the planner must extract the core formatting logic as a standalone function (e.g., `formatFlawEval`) in a shared utility file or directly in `FlawCard.tsx`. The extracted version:
- Accepts `eval_cp: int | null, eval_mate: int | null, user_color: string`.
- Negates both for `user_color === 'black'` before formatting.
- `eval_mate !== null` → `#N` (e.g., `#-3` for mate against user); `eval_cp !== null` → signed 1-decimal pawns using `formatSignedEvalPawns`.
- Returns just the value string (no `"Eval: "` prefix) — the flaw card renders it inline with the move, e.g. `16...Nxd4  +4.7 → #-3`.
- The `formatSignedEvalPawns` helper already exists in `frontend/src/lib/clockFormat.ts` line 41.

**`formatCandidateMove`** (`frontend/src/lib/openingInsights.ts` lines 14-22):
```typescript
export function formatCandidateMove(
  entrySanSequence: string[],
  candidateMoveSan: string,
): string {
  const plyIndex = entrySanSequence.length;  // 0-based index of candidate
  const isWhitePly = plyIndex % 2 === 0;
  const moveNumber = Math.floor(plyIndex / 2) + 1;
  return isWhitePly ? `${moveNumber}.${candidateMoveSan}` : `${moveNumber}...${candidateMoveSan}`;
}
```
For a flaw at `ply=N`, `entrySanSequence.length` must equal `N` (the number of half-moves played before the flaw move). This means passing `Array(N).fill('')` or an empty array of length N is sufficient — the actual SANs don't matter, only the length. **Simpler alternative:** compute the move label directly: `Math.floor(N/2) + 1` for move number, `N % 2 === 0 ? '.' : '...'` for white/black indicator. Since `FlawListItem` carries the `ply` integer and `move_san` string, the planner can use this trivially in `FlawCard` without passing a sequence array.

**`useLibraryFlaws`** pattern (`frontend/src/hooks/useLibrary.ts` lines 89-102) — the exact template for `useLibraryGame(id)`:
```typescript
export function useLibraryGame(gameId: number | null) {
  return useQuery({
    queryKey: ['library-game', gameId],
    queryFn: () => libraryApi.getGame(gameId!),
    enabled: gameId !== null,
    staleTime: LIBRARY_STALE_TIME,
    refetchOnWindowFocus: false,
  });
}
```
`enabled: gameId !== null` prevents the fetch until a game is selected for the modal. The `libraryApi.getGame` method needs to be added to `frontend/src/api/client.ts`.

**`Dialog` component** (`frontend/src/components/ui/dialog.tsx`) — exports: `Dialog`, `DialogContent`, `DialogHeader`, `DialogTitle`, `DialogFooter`. `DialogContent` defaults to `sm:max-w-sm` — the planner must override with `className="sm:max-w-4xl"` for the wide desktop modal. For mobile, the default near-fullscreen behavior of `max-w-[calc(100%-2rem)]` already applies. Internal scroll is handled by adding `overflow-y-auto max-h-[90vh]` to the `DialogContent` or a wrapping div inside it.

**`LoadError`** (`frontend/src/components/ui/load-error.tsx`) — use `<LoadError resource="game" />` in the modal's `isError` branch. CLAUDE.md mandates this pattern.

---

## Backend Schema Changes

### FlawListItem Pydantic model updates

Current fields in `app/schemas/library.py::FlawListItem` (lines 107-131):
- Remove: `es_before: float`, `es_after: float`, `move_san: str | None`
- Add: `white_rating: int | None`, `black_rating: int | None` (game already joins; these are on the `games` table and `game.white_rating` / `game.black_rating` already appear in `GameFlawCard`)
- Add: `eval_cp_before: int | None`, `eval_mate_before: int | None`, `eval_cp_after: int | None`, `eval_mate_after: int | None` (from the `game_positions` join)

Note: `white_rating` and `black_rating` come from `Game.white_rating` / `Game.black_rating`. Both fields already exist on the `Game` model (they are present in `GameFlawCard` per `library_service._build_card` lines 374-375).

### game_flaws ORM model updates

Remove from `app/models/game_flaw.py`:
- `es_before: Mapped[float]` (line 59)
- `es_after: Mapped[float]` (line 60)
- `move_san: Mapped[Optional[str]]` (line 61)

Keep all other columns. Keep `fen`.

### Alembic migration pattern

From the most recent column-drop migration (`20260607_alter_game_flaws_impact_cols.py`):

```python
def upgrade() -> None:
    op.drop_column("game_flaws", "is_while_ahead")
    op.drop_column("game_flaws", "is_result_changing")
    op.add_column(...)
```

For this phase, the migration is a pure drop (no add, no backfill needed — the data moves to a join):

```python
# 20260609_drop_game_flaws_display_cols.py
def upgrade() -> None:
    op.drop_column("game_flaws", "es_before")
    op.drop_column("game_flaws", "es_after")
    op.drop_column("game_flaws", "move_san")

def downgrade() -> None:
    # Re-add as nullable so existing rows don't break on rollback.
    op.add_column("game_flaws", sa.Column("move_san", sa.String(), nullable=True))
    op.add_column("game_flaws", sa.Column("es_after", sa.Float(), nullable=True))
    op.add_column("game_flaws", sa.Column("es_before", sa.Float(), nullable=True))
```

**Convention:** literal column names only — no import of live app constants (per repo rules, same as all prior migrations).

### flaw_record_to_row changes

Remove these three keys from the returned dict in `game_flaws_repository.flaw_record_to_row` (lines 111-113):
```python
# REMOVE:
"es_before": flaw["es_before"],
"es_after": flaw["es_after"],
"move_san": flaw["move_san"],
```

The `FlawRecord` TypedDict and `classify_game_flaws` kernel do NOT change — `flaws_service.py` is unmodified. Only the write path stops persisting those three keys.

### New GET /api/library/games/{game_id} endpoint

Router addition in `app/routers/library.py`:

```python
@router.get("/games/{game_id}", response_model=GameFlawCard)
async def get_library_game(
    game_id: int,
    session: Annotated[AsyncSession, Depends(get_async_session)],
    user: Annotated[User, Depends(current_active_user)],
) -> GameFlawCard:
    """Return a single GameFlawCard by game_id (Phase 112, D-10).

    Used by the FlawCard modal ("View game") to load the full analyzed game
    card without re-fetching the entire game list. User-scoped (IDOR:
    game_id is validated against user.id in the service layer, returning 404
    if the game does not belong to this user).
    """
    card = await library_service.get_library_game(session, user_id=user.id, game_id=game_id)
    if card is None:
        raise HTTPException(status_code=404, detail="Game not found")
    return card
```

Service function in `library_service.get_library_game`:
```python
async def get_library_game(
    session: AsyncSession,
    user_id: int,
    game_id: int,
) -> GameFlawCard | None:
    """Fetch a single game's full GameFlawCard (D-10, Phase 112).

    Reuses _build_card with the same three batch queries as get_library_games,
    but scoped to one game_id. Returns None (→ 404) if game_id does not
    belong to user_id (IDOR guard — user_id always from authenticated user).
    """
    # Sequential queries — no asyncio.gather on one session (CLAUDE.md)
    game = await session.get(Game, game_id)  # or SELECT ... WHERE id=? AND user_id=?
    if game is None or game.user_id != user_id:
        return None
    is_analyzed = game_id in await library_repository.fetch_page_analyzed_set(
        session, user_id, [game_id]
    )
    flaw_rows = (await library_repository.fetch_page_game_flaws(session, user_id, [game_id])).get(game_id, [])
    positions: list[GamePosition] = []
    if is_analyzed:
        positions = (await library_repository.fetch_page_eval_positions(session, user_id, [game_id])).get(game_id, [])
    return _build_card(game, flaw_rows, is_analyzed, positions)
```

---

## Common Pitfalls

### Pitfall 1: Eval-join off-by-one (CRITICAL — must lock before dropping ES columns)

**What goes wrong:** The ply semantics in `game_positions` are non-obvious. `eval_cp` at `ply=N` is the eval AFTER move N was played; the eval BEFORE move N is at `ply=N-1`.

**Why it happens:** The FEN map comment in `_build_flaw_record` is authoritative but easy to miss. `positions[N].eval_cp` is the eval of the RESULTING position, not the position before.

**How to avoid:** Join `ply=N` for eval-after + move_san; join `ply=N-1` for eval-before. See the Authoritative Offset Mapping section above. Run the ES reproduction pytest fixture before dropping the columns.

**Warning signs:** If computed ES differs from stored `es_before`/`es_after` by more than 1e-6 on the same rows, the ply offset is wrong.

### Pitfall 2: `LibraryGameCard` `overflowVisible` tooltip inside a scrollable Dialog

**What goes wrong:** `LibraryGameCard` uses `<Card overflowVisible>` which sets `overflow-visible` on the card element. Inside a `DialogContent` that has `overflow-y-auto` (needed for mobile scroll), the EvalChart tooltip may be clipped by the dialog's scroll container.

**Why it happens:** CSS `overflow-y: auto` creates a scroll stacking context that clips children even with `overflow: visible` on the child. Radix Tooltip/Popover portals avoid this, but Recharts' custom tooltip is rendered inside the chart SVG container (not portaled).

**How to avoid:** Test the modal on both desktop and mobile. If tooltip clips, wrap the `LibraryGameCard` in a div with `overflow-visible` and give the `DialogContent`'s scroll wrapper a fixed `max-h` without `overflow-hidden`. The Recharts tooltip in `EvalChart` renders via a custom `<ChartTooltipBox>` component — check whether it uses a portal (Radix) or is inline; if inline, the dialog overflow clipping applies.

**Mitigation:** The dialog scroll may only be needed on mobile (small screens). On desktop the content fits. A practical fix is: desktop dialog has no scroll, mobile dialog has `overflow-y-auto max-h-[90vh]`. The EvalChart tooltip may still clip on mobile but that is acceptable (chart is already small at 130px on mobile).

### Pitfall 3: Eval perspective + mate sign

**What goes wrong:** `eval_cp` and `eval_mate` in `game_positions` are white-POV (positive = white advantage). A user playing black who blunders into a forced mate sees `eval_mate > 0` (white has mate), which must be shown as negative from the user's perspective.

**How to avoid:** Apply the negation for `user_color === 'black'` BEFORE formatting. The rule: `displayEvalCp = user_color === 'black' ? -eval_cp : eval_cp` (same for `eval_mate`). A blunder-into-mate for black: stored `eval_mate = 3` (white has mate in 3) → displayed as `eval_mate = -3` (mate against the user in 3) → formatted as `#-3`.

**Warning signs:** If a black player's blunder shows the eval improving (positive swing), the sign is wrong.

### Pitfall 4: `fen` cannot be dropped from `game_flaws`

**What goes wrong:** `game_positions` has no `fen` column — only Zobrist hashes (`full_hash`, `white_hash`, `black_hash`). The board-before FEN for the miniboard cannot be derived from a join.

**How to avoid:** `game_flaws.fen` (the `board_fen()` before the flawed move) is the one denormalized display column that stays. The alter migration drops only `es_before`, `es_after`, `move_san`.

### Pitfall 5: `formatCandidateMove` requires ply-length array

**What goes wrong:** `formatCandidateMove(entrySanSequence, candidateMoveSan)` computes move number from `entrySanSequence.length`. Passing the wrong array length produces the wrong move number.

**How to avoid:** For a flaw at `ply=N`, `entrySanSequence.length` must be `N`. The simplest implementation: don't call `formatCandidateMove` at all. Compute inline:
```typescript
const moveNumber = Math.floor(ply / 2) + 1;
const notation = ply % 2 === 0
  ? `${moveNumber}.${move_san}`     // white move (even ply)
  : `${moveNumber}...${move_san}`;  // black move (odd ply)
```
This is equivalent to `formatCandidateMove(Array(ply).fill(''), move_san)` but avoids the array allocation.

**Note:** The parity rule here is: `ply=0` is the start (no move); `ply=1` is White's first move (move number 1); `ply=2` is Black's first move (move number 1). So White moves at odd plies, Black at even plies — the OPPOSITE of the kernel's mover parity (`even ply → white mover` in `_run_all_moves_pass`). Verify: in `_run_all_moves_pass`, `mover = "white" if n % 2 == 0 else "black"`. This means `ply=2` → `n=2` → `n%2==0` → white mover. But chess convention: ply 1 = white's first move, ply 2 = black's first move. The discrepancy arises because ply 0 is the initial position (no mover), so `n=1` is black's move? No — re-check: white plays from the initial position, so the first half-move (ply 1) is white's. But `n%2==0 → white`: `n=2` would be white again. This is a potential confusion. **Re-reading `_run_all_moves_pass` carefully:** `mover: Literal["white","black"] = "white" if n % 2 == 0 else "black"` — so `n=2,4,6...` are white moves, `n=1,3,5...` are black moves. This means ply 2 is white's second move, ply 1 is black's first move. That contradicts chess conventions. **This is the kernel's internal parity** — the stored `game_flaws.ply` follows this convention. For display, the planner must use the kernel's parity: `even ply → white, odd ply → black`. So move number = `floor(ply/2) + 1` and `ply % 2 === 0` → white → `N.san`, `ply % 2 === 1` → black → `N...san`. **Verify with an example:** ply=2 (white's second move) → `Math.floor(2/2)+1 = 2`, white → `2.san`. Ply=3 → black's second move → `Math.floor(3/2)+1 = 2`, black → `2...san`. This matches chess notation.

### Pitfall 6: `es_before`/`es_after` still in FlawRecord TypedDict

**What goes wrong:** `flaws_service.FlawRecord` TypedDict still declares `es_before: float` and `es_after: float`. After removing these from `game_flaws`, the TypedDict does NOT need to change — the kernel still computes ES internally. Only `flaw_record_to_row` stops writing them to the DB. The TypedDict is an internal contract for the classifier, not the DB schema.

**How to avoid:** Do NOT remove `es_before`/`es_after` from `FlawRecord`. They are still used internally by `_run_all_moves_pass`, `_build_flaw_record`, and `_build_tags`. Only remove them from `flaw_record_to_row`'s returned dict.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Modal primitive | Custom div with CSS | `Dialog`/`DialogContent` from `components/ui/dialog.tsx` | Already has overlay, animation, close button, portal |
| Tag chip rendering | Inline style props | `TagChip` + `TagLegend` from `components/library/TagChip.tsx` | Family colors, active-filter ring, definition popover |
| Miniboard | Raw `<img>` or chess SVG | `LazyMiniBoard` from `components/board/LazyMiniBoard.tsx` | Lazy intersection-observer loading, arrow rendering |
| Error state | Custom error div | `LoadError` from `components/ui/load-error.tsx` | CLAUDE.md mandatory for all `isError` branches |
| Eval pawns formatter | Custom `toFixed` | `formatSignedEvalPawns` from `lib/clockFormat.ts` | Already handles sign convention, 1dp rounding |
| Card header band | Custom `div` with `bg-black/20` | `CardHeader` from `components/ui/card.tsx` | Canonical banded header across the app |
| Game positions batch load | Per-row SELECT in loop | `fetch_page_eval_positions` from `library_repository` | Already batched for a page; call with `[game_id]` |

---

## Code Examples

### Pattern 1: FlawCard CardHeader (desktop + mobile)

```tsx
// Source: LibraryGameCard.tsx lines 280-293 (adapted for FlawCard)
// Platform link uses flawPlyUrl (exact-ply) not gamePlatformUrl (game-level)
const flawUrl = flawPlyUrl(flaw.platform, flaw.platform_url, flaw.ply, flaw.user_color);
const platformLink = flawUrl ? (
  <Tooltip content="Open at this move on platform">
    <a href={flawUrl} target="_blank" rel="noopener noreferrer"
       aria-label="Open at this move on platform"
       data-testid={`flaw-card-platform-link-${flaw.game_id}-${flaw.ply}`}>
      <ExternalLink className="h-4 w-4" />
    </a>
  </Tooltip>
) : null;

<CardHeader as="h4" size="compact" className="rounded-t-md">
  <span className="hidden sm:block truncate text-foreground min-w-0">
    ■ {whiteName} {whiteRating}
    <span className="mx-1.5 text-muted-foreground font-normal">vs</span>□ {blackName} {blackRating}
  </span>
  <div className="flex sm:hidden min-w-0 flex-1 flex-col text-foreground">
    <span className="truncate">■ {whiteName} {whiteRating}</span>
    <span className="truncate">□ {blackName} {blackRating}</span>
  </div>
  <span className="ml-auto shrink-0 flex items-center gap-1.5 text-muted-foreground">
    <PlatformIcon platform={flaw.platform} className="h-4 w-4" />
    {platformLink}
  </span>
</CardHeader>
```

### Pattern 2: Eval swing formatter (extracted from EvalChart.formatEval)

```typescript
// Extracted from EvalChart.tsx lines 303-315; user-POV negation added
// Source: EvalChart.tsx::formatEval + clockFormat.ts::formatSignedEvalPawns
function formatFlawEvalPart(evalCp: number | null, evalMate: number | null): string {
  if (evalMate !== null) return `#${evalMate > 0 ? '' : ''}${evalMate}`;  // e.g. "#3" or "#-3"
  if (evalCp !== null) return formatSignedEvalPawns(evalCp / 100);        // e.g. "+4.7"
  return '—';
}

function applyUserPov(evalCp: number | null, evalMate: number | null, userColor: string) {
  if (userColor !== 'black') return { evalCp, evalMate };
  return {
    evalCp: evalCp !== null ? -evalCp : null,
    evalMate: evalMate !== null ? -evalMate : null,
  };
}

// Usage in FlawCard:
const { evalCp: beforeCp, evalMate: beforeMate } = applyUserPov(
  flaw.eval_cp_before, flaw.eval_mate_before, flaw.user_color
);
const { evalCp: afterCp, evalMate: afterMate } = applyUserPov(
  flaw.eval_cp_after, flaw.eval_mate_after, flaw.user_color
);
const evalSwing = `${formatFlawEvalPart(beforeCp, beforeMate)} → ${formatFlawEvalPart(afterCp, afterMate)}`;
// e.g. "+4.7 → #-3"
```

### Pattern 3: Move notation (inline, avoiding formatCandidateMove array)

```typescript
// Produces standard PGN notation: "16.Nxd4" (white) or "16...Nxd4" (black)
// ply is the game_flaws.ply value (kernel parity: even=white, odd=black)
function formatFlawMove(ply: number, moveSan: string | null): string {
  if (!moveSan) return `Ply ${ply}`;
  const moveNumber = Math.floor(ply / 2) + 1;
  return ply % 2 === 0
    ? `${moveNumber}.${moveSan}`    // white (even ply)
    : `${moveNumber}...${moveSan}`; // black (odd ply)
}
```

### Pattern 4: useLibraryGame hook

```typescript
// Source: useLibrary.ts pattern (lines 89-102), adapted for single-game fetch
export function useLibraryGame(gameId: number | null) {
  return useQuery({
    queryKey: ['library-game', gameId],
    queryFn: () => libraryApi.getGame(gameId!),
    enabled: gameId !== null,
    staleTime: LIBRARY_STALE_TIME,
    refetchOnWindowFocus: false,
  });
}
```

### Pattern 5: "View game" modal with loading + error states

```tsx
// Source: CLAUDE.md mandatory isError pattern + Dialog usage convention
function FlawGameModal({ gameId, open, onClose }: {...}) {
  const { data: game, isLoading, isError } = useLibraryGame(open ? gameId : null);
  return (
    <Dialog open={open} onOpenChange={(v) => !v && onClose()}>
      <DialogContent
        className="sm:max-w-4xl overflow-y-auto max-h-[90vh]"
        data-testid="flaw-game-modal"
        aria-label="View full game"
      >
        {isLoading && <div className="flex justify-center p-8"><Spinner /></div>}
        {isError && <LoadError resource="game" variant="centered" />}
        {game && <LibraryGameCard game={game} />}
      </DialogContent>
    </Dialog>
  );
}
```

### Pattern 6: query_flaws join additions (SQLAlchemy)

```python
# Source: library_repository.query_flaws (lines 232-243) — extend with joins
from sqlalchemy.orm import aliased

PositionAt   = aliased(GamePosition)  # ply = N (move_san + eval_after)
PositionBefore = aliased(GamePosition)  # ply = N-1 (eval_before)

base_stmt = (
    select(GameFlaw, Game, PositionAt, PositionBefore)
    .join(Game, Game.id == GameFlaw.game_id)
    .outerjoin(
        PositionAt,
        (PositionAt.game_id == GameFlaw.game_id)
        & (PositionAt.user_id == GameFlaw.user_id)
        & (PositionAt.ply == GameFlaw.ply),
    )
    .outerjoin(
        PositionBefore,
        (PositionBefore.game_id == GameFlaw.game_id)
        & (PositionBefore.user_id == GameFlaw.user_id)
        & (PositionBefore.ply == GameFlaw.ply - 1),
    )
    .where(
        GameFlaw.user_id == user_id,
        *flaw_clauses,
    )
)
```

The `FlawListItem` constructor then reads:
```python
FlawListItem(
    ...
    move_san=pos_at.move_san if pos_at else None,
    eval_cp_before=pos_before.eval_cp if pos_before else None,
    eval_mate_before=pos_before.eval_mate if pos_before else None,
    eval_cp_after=pos_at.eval_cp if pos_at else None,
    eval_mate_after=pos_at.eval_mate if pos_at else None,
    white_rating=game.white_rating,
    black_rating=game.black_rating,
    ...
)
```

---

## FlawCard Grid Layout

The grid replaces the `<div className="flex flex-col gap-3">` block in `FlawsTab` (lines 414-419):

```tsx
{matchedCount > 0 && (
  <div className="grid grid-cols-1 lg:grid-cols-2 gap-4" data-testid="flaw-grid">
    {flaws.map((flaw) => (
      <FlawCard key={`${flaw.game_id}-${flaw.ply}`} flaw={flaw} />
    ))}
  </div>
)}
```

Within `FlawCard`, the body layout (board left + content right) mirrors `LibraryGameCard` column 1:

```tsx
<Card as="article" accentColor={severityColor} overflowVisible
      data-testid={`flaw-card-${flaw.game_id}-${flaw.ply}`}>
  {/* CardHeader: white vs black + platform link */}
  {header}

  {/* Body: board + content column */}
  <div className="flex gap-3 items-start p-3">
    <LazyMiniBoard fen={flaw.fen} flipped={flipped} size={132}
      arrows={moveSquares ? [{...arrow}] : undefined} />
    <div className="flex flex-col gap-1.5 min-w-0 flex-1">
      {/* Move + eval swing */}
      {/* SeverityBadge */}
      {/* TagChip row */}
      {/* TagLegend */}
      {/* Metadata */}
      {/* "View game" button */}
    </div>
  </div>
</Card>
```

---

## Validation Architecture

Nyquist validation is enabled (`workflow.nyquist_validation: true`).

### Test Framework

| Property | Value |
|----------|-------|
| Backend framework | pytest + pytest-asyncio + pytest-xdist |
| Frontend framework | Vitest |
| Quick run command (backend) | `uv run pytest tests/test_library_repository.py -x` |
| Full suite command | `uv run pytest -n auto -x` |
| Frontend test command | `cd frontend && npm test -- --run` |

### Phase Requirements → Test Map

| Req | Behavior | Test Type | Command | File exists? |
|-----|----------|-----------|---------|-------------|
| SC-1 | `FlawListItem` carries `eval_cp_before/after` + `white_rating/black_rating`, drops `es_before/es_after/move_san` | Integration | `pytest tests/test_library_repository.py::test_flaws_endpoint_schema -x` | No — Wave 0 |
| SC-2 | Eval join reproduces ES on sample rows (regression guard before ES drop) | Integration | `pytest tests/test_library_repository.py::test_eval_join_reproduces_es -x` | No — Wave 0 |
| SC-3 | `GET /api/library/games/{game_id}` returns 404 for wrong user; 200 + valid `GameFlawCard` for own game | Integration | `pytest tests/test_integration_routers.py::test_library_game_by_id -x` | No — Wave 0 |
| SC-4 | `FlawCard` renders CardHeader with white/black names + ratings, 132px board with arrow | Unit/Vitest | `npm test -- --run src/components/library/FlawCard.test.tsx` | No — Wave 0 |
| SC-5 | Move notation renders correctly (`2.Nxd4` for white ply=2, `2...c5` for black ply=3) | Unit/Vitest | `npm test -- --run src/components/library/FlawCard.test.tsx` | No — Wave 0 |
| SC-6 | Eval swing is user-POV negated for black: `eval_cp=-300 → "+3.0"`, not `"-3.0"` | Unit/Vitest | `npm test -- --run src/lib/__tests__/formatFlawEval.test.ts` | No — Wave 0 |
| SC-7 | "View game" button opens Dialog with `LibraryGameCard`; `LoadError` on fetch failure | Unit/Vitest | `npm test -- --run src/components/library/FlawCard.test.tsx` | No — Wave 0 |
| SC-8 | `grid-cols-1 lg:grid-cols-2` grid in `FlawsTab` (visual only) | Manual UAT | — | — |

### Sampling Rate

- Per task commit: targeted test file (e.g. `pytest tests/test_library_repository.py -x`)
- Per wave merge: `uv run pytest -n auto -x` + `cd frontend && npm test -- --run`
- Phase gate: full suite green before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `tests/test_library_repository.py` — add `test_flaws_endpoint_schema`, `test_eval_join_reproduces_es`
- [ ] `tests/test_integration_routers.py` — add `test_library_game_by_id` (404 for wrong user, 200 for own game)
- [ ] `frontend/src/components/library/__tests__/FlawCard.test.tsx` — new file; covers SC-4, SC-5, SC-7
- [ ] `frontend/src/lib/__tests__/formatFlawEval.test.ts` — covers SC-6 (user-POV negation + mate format)

---

## Security Domain

`security_enforcement` is not set to false in `.planning/config.json`; section is required.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | yes | FastAPI-Users `current_active_user` (already on all `/library` endpoints) |
| V3 Session Management | no | Token-based (existing) |
| V4 Access Control | yes | `GET /games/{game_id}` must validate `game.user_id == user.id` before returning (IDOR guard) |
| V5 Input Validation | yes | `game_id: int` (FastAPI path param — auto-validated as integer) |
| V6 Cryptography | no | No new crypto |

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| IDOR on `GET /games/{game_id}` | Info Disclosure | Check `game.user_id == user.id` in service before returning card; return 404 (not 403) to avoid confirming ID existence |
| Eval values leak internal hash | Info Disclosure | `FlawListItem` and `GameFlawCard` schemas never include `*_hash` columns — already enforced by design |

---

## Environment Availability

Step 2.6: SKIPPED (no new external dependencies; this phase modifies existing code + runs standard dev Docker stack).

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `formatCandidateMove` plyIndex = `entrySanSequence.length` determines white/black parity the same way as `_run_all_moves_pass`'s `n % 2` | Code Examples §3 | Wrong move notation if parity definitions differ — mitigated by using inline formula instead |
| A2 | `game.white_rating` / `game.black_rating` columns exist on the `games` table (evidenced by their presence in `GameFlawCard` and `_build_card`) | Backend Schema Changes | If absent, need to add them to `Game` model — but Phase 109 code already uses them at line 374-375 |
| A3 | `DialogContent` default `sm:max-w-sm` is overridable by className without specificity conflicts | Code Examples §5 | May need `!` prefix; verify in dev |
| A4 | Recharts `ChartTooltipBox` in EvalChart is inline (not portaled), so it clips inside Dialog scroll container | Pitfall 2 | If it is portaled, the tooltip works fine in the modal — no action needed |

**If this table is empty:** All claims were verified. It is not empty, but all assumptions are LOW risk due to direct code evidence in the codebase.

---

## Open Questions

1. **`aliased(GamePosition)` vs raw `join` syntax**
   - What we know: SQLAlchemy 2.x supports `aliased()` for self-joins or repeated entity joins.
   - What's unclear: Whether the existing `query_flaws` base statement composition (using `apply_game_filters` via a subquery) needs adjustment to accommodate two `GamePosition` aliases.
   - Recommendation: Use `aliased(GamePosition, name='pos_at')` and `aliased(GamePosition, name='pos_before')` with `outerjoin`. The planner should verify that `apply_game_filters` does not filter on `GamePosition` columns (it filters on `Game` columns only — confirmed by reading the function), so no conflict.

2. **`ply=0` eval-before: first move has no ply-1**
   - What we know: A flaw at `ply=1` would need `ply=0` for eval-before. In practice, `ply=1` is unlikely to be a blunder (opening moves rarely satisfy the ES-drop threshold). The kernel handles this via `es_before = _ply_to_es(positions[n-1], ...)` which reads `positions[0]`.
   - What's unclear: If `positions[0].eval_cp` is non-null (some games have eval at ply 0), the join works. If null (typical since the initial position has no eval annotation), `eval_cp_before = NULL`.
   - Recommendation: Return `NULL` for `eval_cp_before`/`eval_mate_before` when the join finds no row. The formatter handles `NULL` as `'—'`.

---

## Sources

### Primary (HIGH confidence — direct code inspection)
- `app/services/flaws_service.py` — `_run_all_moves_pass` (lines 210-235), `_build_flaw_record` (lines 238-264); authoritative ply semantics verified by reading source
- `app/models/game_flaw.py` — current column set; confirmed `es_before`, `es_after`, `move_san` are present
- `app/models/game_position.py` — PK structure `(game_id, user_id, ply)`, `eval_cp`, `eval_mate`, `move_san` columns confirmed
- `app/repositories/library_repository.py::query_flaws` — current join pattern (lines 232-295)
- `app/services/library_service.py::_build_card` — card builder reusable for single-game endpoint (lines 294-390)
- `app/repositories/game_flaws_repository.py::flaw_record_to_row` — three keys to remove (lines 111-113)
- `frontend/src/pages/library/FlawsTab.tsx` — `FlawRow` (lines 48-141) replaced; grid block (lines 414-419)
- `frontend/src/components/results/LibraryGameCard.tsx` — `CardHeader` pattern (lines 280-293), `DESKTOP_BOARD_SIZE=132` (line 34)
- `frontend/src/components/library/EvalChart.tsx::formatEval` — lines 303-315
- `frontend/src/components/ui/dialog.tsx` — `DialogContent` size defaults (line 50)
- `frontend/src/components/ui/card.tsx` — `overflowVisible` prop (lines 29, 44)
- `frontend/src/hooks/useLibrary.ts` — `useLibraryFlaws` pattern (lines 89-102)
- `frontend/src/lib/clockFormat.ts::formatSignedEvalPawns` — lines 41-44
- `frontend/src/lib/openingInsights.ts::formatCandidateMove` — lines 14-22
- `alembic/versions/20260607_alter_game_flaws_impact_cols.py` — drop-column migration pattern

### Secondary (MEDIUM confidence)
- `.planning/phases/112-flaws-subtab-card-rework/112-CONTEXT.md` — locked decisions D-01..D-12

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new packages; all reused assets verified by direct source read
- Architecture: HIGH — ply offset semantics locked by reading flaws_service.py; join pattern confirmed
- Pitfalls: HIGH — eval-join offset, mate sign, fen-cannot-drop all verified from source
- Validation: HIGH — test file paths match project conventions

**Research date:** 2026-06-09
**Valid until:** 2026-07-09 (30 days; stable phase, no external dependencies)
