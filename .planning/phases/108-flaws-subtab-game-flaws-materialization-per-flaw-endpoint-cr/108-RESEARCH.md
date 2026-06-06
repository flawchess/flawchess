# Phase 108: Flaws Subtab — game_flaws Materialization, Per-Flaw Endpoint, Cross-Tab Flaw Filter & Miniboard List — Research

**Researched:** 2026-06-06
**Domain:** FastAPI / SQLAlchemy async, Alembic migrations, React/Zustand/TanStack Query, asyncpg bulk insert, on-the-fly classifier materialization
**Confidence:** HIGH (all findings from direct codebase inspection of live files)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Remove the boolean severity toggle from `LibraryFilterPanel`; replace with the new `FlawFilterControl` (severity x tag families). Severity-only filtering still works through `FlawFilterControl`.
- **D-02:** Migrate `/library/games` and `/library/flaw-stats` off on-the-fly kernel re-calls to reading M+B from `game_flaws` via the shared predicate builder.
- **D-03:** `game_flaws` stores mistakes + blunders only. Inaccuracy counts remain a cheap SQL aggregate from existing columns.
- **D-04:** Flaw-filter state shared across both tabs via a new `useFlawFilterStore` (mirrors `useFilterStore` pattern). Flaws tab URL-syncs `?tag=&severity=`; Games tab does not.
- **D-05:** Games-card tag chip deep-links to `/library/flaws?tag={TAG}` (no `game_id`). Amends SEED-038's original deep-link shape.
- **D-06:** UI-SPEC scoped to the new shared `FlawFilterControl` only. Miniboard list, Pagination, sidebar/drawer chrome are spec'd in-plan as reuse of existing components.
- **D-07:** Default order `ORDER BY g.played_at DESC, f.ply` (recent-first flat list). Multiple flaws from one game appear as adjacent independent rows.
- **D-08:** Paginate by flaw, page size 20, reusing the shared `Pagination` component from Phase 107. Severity filter on Flaws tab is M+B-only (forced by M+B-only table); default severity = M+B.
- **D-09:** Build `scripts/backfill_flaws.py` with `--db {dev|benchmark|prod}` and optional `--user-id`, verify against `--db dev --user-id 28`. Prod backfill is manual out-of-band. Phase completion is NOT gated on prod backfill.
- **D-10:** One classify path: import hook (post-`eval_cp` store), `reimport_games.py` (CASCADE-drops rows, hook repopulates), `reclassify_positions.py` (also recomputes), `backfill_flaws.py` (threshold-change recomputes).

### Claude's Discretion

- Per-flaw list endpoint route name (likely `GET /library/flaws`) and pagination contract shape.
- Exact `game_flaws` indexing strategy: start with PK `(user_id, game_id, ply)` + `(user_id, severity)`; add per-boolean partial indexes only if profiling demands.
- Bulk-insert mechanism for the import hook (per-game vs per-batch): stay within the import pipeline's existing batch-size / memory envelope.
- Whether the shared predicate builder lives in `library_repository` or `query_utils`: pick the seam that lets both `/library/games` (EXISTS wrapper) and `/library/flaws` (`SELECT f.*`) share one WHERE-clause builder.

### Deferred Ideas (OUT OF SCOPE)

- Analysis detail viewer (`/library/analysis/{game_id}?ply={N}`) and on-demand best-move endpoint.
- `game_id`-scoped "this game only" Flaws view.
- Tracked release-ops automation for the prod backfill.
- Per-boolean partial indexes on `game_flaws` (only if profiling demands).
</user_constraints>

---

## Summary

Phase 108 materializes the Phase 105 classifier output into a derived `game_flaws` table (M+B only, typed columns, composite PK), wires a post-eval import hook, migrates the Games and Flaw-Stats endpoints off the on-the-fly kernel re-call, adds a new `GET /library/flaws` per-flaw list endpoint, builds the shared `FlawFilterControl` (severity x tag-family multi-select), and adds the Flaws subtab to `LibraryPage`.

All design decisions are locked in CONTEXT.md (D-01..D-10) and SEED-038. Research confirms the exact signatures, line numbers, and insertion points against the live codebase. The implementation involves four layers: (1) DB migration + ORM model, (2) import hook + backfill script, (3) backend service/repository refactor, and (4) frontend store + components.

**Primary recommendation:** Build in wave order — migration first, then backfill script, then backend endpoints (the Games migration is a prerequisite for the Games tab working), then frontend. Keep the shared predicate builder in `library_repository` as a new `flaw_filter_predicate()` function, mirroring the existing `flaw_exists_subquery()` pattern.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| `game_flaws` table + migration | Database | — | Derived materialization table; PK, FKs, indexes live here |
| Import hook (classify + insert) | API / Backend | — | Runs in `eval_drain.py` cold-lane after `evals_completed_at` is stamped |
| Shared flaw predicate builder | API / Backend (`library_repository`) | `query_utils` | Both Games EXISTS + Flaws SELECT share one builder |
| `GET /library/flaws` endpoint | API / Backend | — | New route on existing `APIRouter(prefix="/library")` |
| `GET /library/games` (migrated) | API / Backend | — | Migrated from on-the-fly to `game_flaws` read |
| `GET /library/flaw-stats` (migrated) | API / Backend | — | Migrated from on-the-fly kernel re-call |
| Backfill script | API / Backend (script) | — | Mirrors `scripts/backfill_eval.py` pattern |
| `useFlawFilterStore` | Frontend (module state) | — | Mirrors `useFilterStore`; shared across both tabs |
| `FlawFilterControl` | Frontend (component) | — | New `components/filters/FlawFilterControl.tsx` |
| Flaws subtab (`FlawsTab`) | Frontend (page) | — | New page at `/library/flaws`, mirrors `GamesTab` |
| `LibraryPage` tab additions | Frontend (page) | — | Add "Flaws" `TabsTrigger`, route, and subtab order |
| Tag chip navigation | Frontend (component) | — | Convert `TagChip` from popover to navigation trigger |

---

## Standard Stack

### Core (all already installed — no new packages needed)

| Library | Purpose | Confirmed Present |
|---------|---------|-------------------|
| SQLAlchemy 2.x async + asyncpg | ORM, bulk insert, migrations | `app/repositories/game_repository.py` — `copy_records_to_table` in use |
| Alembic | Migrations | Live migrations in `alembic/versions/` |
| FastAPI | Routing | `app/routers/library.py` |
| Pydantic v2 | Schemas | `app/schemas/library.py` |
| python-chess | FEN replay in `classify_game_flaws` | `app/services/flaws_service.py` |
| React + TanStack Query | Frontend data fetching | `frontend/src/hooks/useLibrary.ts` |
| `useSyncExternalStore` | Shared filter store | `frontend/src/hooks/useFilterStore.ts` — ZERO new dependencies |
| lucide-react | Icons for filter buttons | `frontend/src/components/library/TagChip.tsx` — already imported |
| react-router-dom | Navigation for chip deep-link | `frontend/src/pages/library/LibraryPage.tsx` |

**No new packages are required for this phase.** [VERIFIED: codebase inspection]

---

## Package Legitimacy Audit

> **Skipped — no new packages installed in this phase.** All code reuses existing installed dependencies.

---

## Architecture Patterns

### System Architecture Diagram

```
Import pipeline (eval_drain.py cold-lane)
  evals_completed_at set → classify_game_flaws(game, positions)
       ↓
  game_flaws repository: bulk INSERT INTO game_flaws ... ON CONFLICT DO NOTHING
       ↓
game_flaws table (user_id, game_id, ply) PK
  FK → games.id CASCADE
  FK → users.id CASCADE
  columns: severity, tempo, phase, is_miss, is_lucky_escape,
           is_while_ahead, is_result_changing, es_before, es_after, move_san

GET /library/games (migrated)
  → game_flaws JOIN games (EXISTS subquery via shared predicate builder)
  → chips sourced from game_flaws rows (no kernel re-call per game)

GET /library/flaw-stats (migrated)
  → game_flaws JOIN games (single-pass COUNT(*) FILTER aggregates)

GET /library/flaws (new)
  → game_flaws JOIN games (SELECT f.* with shared predicate + ORDER BY)
  → paginated, 20 per page

Frontend: FlawsTab
  useFlawFilterStore (shared with GamesTab)
  URL sync (?tag=&severity= via replace-state)
  FlawFilterControl → severity buttons + family tag buttons
  FlawList → LazyMiniBoard rows (fen + move_san arrow)
  Pagination
```

### Recommended Project Structure

```
app/
├── models/
│   └── game_flaw.py              # NEW: GameFlaw ORM model
├── repositories/
│   ├── library_repository.py     # MODIFIED: add flaw_filter_predicate(), query_flaws()
│   └── game_flaws_repository.py  # NEW: bulk_insert_game_flaws(), delete_for_game()
├── services/
│   ├── library_service.py        # MODIFIED: migrate games/stats to game_flaws; add get_library_flaws()
│   └── eval_drain.py             # MODIFIED: add classify+insert hook after _mark_evals_completed
├── schemas/
│   └── library.py                # MODIFIED: add FlawListItem, LibraryFlawsResponse
├── routers/
│   └── library.py                # MODIFIED: add GET /flaws route
alembic/versions/
└── YYYYMMDD_HHMMSS_<hash>_add_game_flaws_table.py  # NEW
scripts/
└── backfill_flaws.py             # NEW: mirrors backfill_eval.py pattern
frontend/src/
├── hooks/
│   ├── useFlawFilterStore.ts     # NEW: mirrors useFilterStore.ts exactly
│   └── useLibrary.ts             # MODIFIED: add useLibraryFlaws hook
├── api/
│   └── client.ts                 # MODIFIED: add libraryApi.getFlaws()
├── types/
│   └── library.ts                # MODIFIED: add FlawListItem, LibraryFlawsResponse
├── components/
│   ├── filters/
│   │   ├── FlawFilterControl.tsx # NEW: per UI-SPEC
│   │   └── LibraryFilterPanel.tsx # MODIFIED: swap severity toggle for FlawFilterControl
│   └── results/
│       └── LibraryGameCard.tsx   # MODIFIED: make TagChip navigate to /library/flaws?tag=
└── pages/library/
    ├── FlawsTab.tsx              # NEW: mirrors GamesTab.tsx structure
    ├── GamesTab.tsx              # MODIFIED: replace severityFilter local state with useFlawFilterStore
    └── LibraryPage.tsx           # MODIFIED: add Flaws TabsTrigger + route
```

---

## Key Implementation Details

### 1. `game_flaws` ORM Model — Column-to-FlawRecord Mapping

[VERIFIED: codebase inspection of `app/services/flaws_service.py`]

The `FlawRecord` TypedDict (lines 95-103) maps to `game_flaws` columns as follows:

| FlawRecord field | game_flaws column | SQLAlchemy type | Notes |
|-----------------|-------------------|-----------------|-------|
| `ply` | `ply` | `SmallInteger` | PK component |
| — | `game_id` | `Integer` FK | PK component; from `game.id` |
| — | `user_id` | `Integer` FK | PK component; from `game.user_id` |
| `severity` | `severity` | `SmallInteger` | 1=mistake, 2=blunder (ordered; never 0=inaccuracy) |
| `tags` (tempo) | `tempo` | `SmallInteger | None` | 0=low-clock, 1=impatient, 2=considered; NULL when no clock data |
| `tags` (phase) | `phase` | `SmallInteger` | 0=opening, 1=middlegame, 2=endgame (denormalized from `game_positions.phase`) |
| `tags` contains `"miss"` | `is_miss` | `Boolean` | |
| `tags` contains `"lucky-escape"` | `is_lucky_escape` | `Boolean` | |
| `tags` contains `"while-ahead"` | `is_while_ahead` | `Boolean` | |
| `tags` contains `"result-changing"` | `is_result_changing` | `Boolean` | |
| `es_before` | `es_before` | `Float` | mover-POV ES before flaw |
| `es_after` | `es_after` | `Float` | mover-POV ES after flaw |
| `move_san` | `move_san` | `String` | from `positions[n].move_san` |
| `fen` | NOT STORED | — | recomputed from `move_san` + `game.pgn` at display time, or stored as a string column if display performance demands it |

**Decision on `fen` storage:** The SEED-038 schema omits `fen` but the Flaws-tab miniboard needs a FEN to render the position. `FlawRecord.fen` comes from `_recompute_fen_map(game.pgn)` at classify time. Two options: (a) store `fen` as a `String` column in `game_flaws` (avoids re-parsing PGN per row at display time), or (b) join to `game.pgn` and replay at query time. Option (a) is strongly preferred — the `es_before/es_after/move_san` payload was explicitly added to "avoid re-parsing PGN to render a Flaws-tab card" (SEED-038). Storing `fen` completes this intent. Planner should add `fen: String` to the schema. [ASSUMED — not explicitly locked in SEED-038/CONTEXT.md, but strongly implied by the "display payload" rationale]

**Composite PK:** `(user_id, game_id, ply)` — mirrors `game_positions` PK pattern.

**FKs:**
- `user_id → users.id CASCADE`
- `game_id → games.id CASCADE` (CASCADE ensures reimport auto-cleans)

**Severity integer encoding:**
```python
_SEVERITY_INT: dict[str, int] = {"mistake": 1, "blunder": 2}
```

**Tempo integer encoding:**
```python
_TEMPO_INT: dict[str, int] = {"low-clock": 0, "impatient": 1, "considered": 2}
```

### 2. Import Hook Insertion Point

[VERIFIED: codebase inspection of `app/services/eval_drain.py`]

The eval drain cold-lane in `run_eval_drain()` (line 493) already has the right structure:

```python
# Current flow (lines 543-551):
async with async_session_maker() as session:
    if eval_targets:
        await _apply_eval_results(session, eval_targets, list(eval_results))
    await _mark_evals_completed(session, game_ids)  # ← stamps evals_completed_at
    await session.commit()
```

The flaw materialization hook inserts **after** `_apply_eval_results` and **before** `_mark_evals_completed` (so it runs in the same short write-window session):

```python
async with async_session_maker() as session:
    if eval_targets:
        await _apply_eval_results(session, eval_targets, list(eval_results))
    # NEW: classify + bulk-insert game_flaws for all just-evaluated games
    await _classify_and_insert_flaws(session, game_ids)
    await _mark_evals_completed(session, game_ids)
    await session.commit()
```

`_classify_and_insert_flaws` must: load positions for each game_id (short sequential query — no asyncio.gather on same session), call `classify_game_flaws`, convert `FlawRecord` list to `game_flaws` dicts, then bulk-insert. The `_DRAIN_BATCH_SIZE` is 10 games (D-11). Each game typically has 1-5 flaws (M+B only), so per-batch ~50 rows — well within the memory envelope.

**Important:** `classify_game_flaws` needs the `Game` object. The cold-drain already has `game_ids`; load `Game` rows with a single `select(Game).where(Game.id.in_(game_ids))` in the write session (or a separate short read session before).

### 3. `classify_game_flaws` Current Signature

[VERIFIED: `app/services/flaws_service.py` lines 447-512]

```python
def classify_game_flaws(
    game: Game,
    positions: list[GamePosition],
) -> GameFlawsResult:  # list[FlawRecord] | GameNotAnalyzed
```

Returns `list[FlawRecord]` (possibly empty) for analyzed games, `GameNotAnalyzed` for unanalyzed. The import hook should skip `GameNotAnalyzed` games silently (they have no evals to classify).

### 4. Current `apply_game_filters` Signature — Flaw Severity EXISTS Param

[VERIFIED: `app/repositories/query_utils.py` lines 11-114]

```python
def apply_game_filters(
    stmt: Any,
    time_control: Sequence[str] | None,
    platform: Sequence[str] | None,
    rated: bool | None,
    opponent_type: str,
    from_date: datetime.date | None,
    to_date: datetime.date | None,
    color: str | None = None,
    *,
    opponent_gap_min: int | None = None,
    opponent_gap_max: int | None = None,
    flaw_severity: Sequence[str] | None = None,  # ← Phase 106 keyword-only
    user_id: int | None = None,                  # ← Phase 106 keyword-only
) -> Any:
```

The `flaw_severity` param currently triggers a SQL window-scan EXISTS subquery via `library_repository.flaw_exists_subquery()`. **After D-02 migration**, this must be updated to use the new `game_flaws`-backed EXISTS subquery instead — a simple `EXISTS (SELECT 1 FROM game_flaws WHERE game_id = games.id AND severity >= threshold AND ...)`.

The `flaw_severity` param semantics stay identical: `["blunder"]` = blunders only, `["mistake"]` = mistakes or worse (MIN threshold logic). The internal mechanism changes from the SQL window-scan to a direct `game_flaws` lookup.

### 5. Current `library_repository.flaw_exists_subquery` — What Gets Replaced

[VERIFIED: `app/repositories/library_repository.py` lines 164-193]

The current `flaw_exists_subquery()` (line 164) builds a SQL window-function subquery over `game_positions`, computing per-ply ES drops in SQL. Post-D-02, this is replaced by a direct `game_flaws` EXISTS:

```python
# NEW: simple game_flaws-backed EXISTS (replaces the window-scan)
def flaw_exists_subquery_from_table(
    user_id: int,
    severities: Sequence[FlawSeverity],
) -> ColumnElement[bool]:
    threshold = min(_SEVERITY_INT[s] for s in severities)
    return exists(
        select(GameFlaw.ply).where(
            GameFlaw.game_id == Game.id,
            GameFlaw.user_id == user_id,
            GameFlaw.severity >= threshold,
        )
    )
```

The `_per_ply_drop_subquery`, `_drop_filter`, `_user_ply_filter`, and `flaw_exists_subquery` functions in `library_repository.py` can be retired after the migration. The SQL<->kernel cross-check test (B2 / `flagged_plies_for_severity`) can be similarly retired or adapted.

### 6. Per-Flaw Predicate Builder — Shared Between Games EXISTS and Flaws SELECT

[VERIFIED: SEED-038 design + codebase inspection]

The shared predicate builder filters `game_flaws` rows. It accepts the Flaw-filter state (severity list + tag selection per family) and returns a list of SQLAlchemy column expressions:

```python
def build_flaw_filter_clauses(
    severity: Sequence[FlawSeverity],           # ["mistake", "blunder"] or subset
    tags: Sequence[FlawTag],                    # selected tags from FlawFilterControl
) -> list[ColumnElement[bool]]:
    """Return WHERE clauses for game_flaws rows matching the flaw filter.
    
    OR within family, AND across families (SEED-038 semantics).
    """
    clauses: list[ColumnElement[bool]] = []
    
    # Severity filter (MIN threshold — ["mistake"] matches mistakes OR worse)
    if severity:
        threshold = min(_SEVERITY_INT[s] for s in severity)
        clauses.append(GameFlaw.severity >= threshold)
    
    # Tag families: OR within, AND across
    tempo_tags = [t for t in tags if t in {"low-clock", "impatient", "considered"}]
    opportunity_tags = [t for t in tags if t in {"miss", "lucky-escape"}]
    impact_tags = [t for t in tags if t in {"while-ahead", "result-changing"}]
    
    if tempo_tags:
        tempo_ints = [_TEMPO_INT[t] for t in tempo_tags]
        clauses.append(GameFlaw.tempo.in_(tempo_ints))  # OR within tempo family
    
    if opportunity_tags:
        opp_clauses = []
        if "miss" in opportunity_tags:
            opp_clauses.append(GameFlaw.is_miss == True)
        if "lucky-escape" in opportunity_tags:
            opp_clauses.append(GameFlaw.is_lucky_escape == True)
        clauses.append(or_(*opp_clauses))  # OR within opportunity family
    
    if impact_tags:
        imp_clauses = []
        if "while-ahead" in impact_tags:
            imp_clauses.append(GameFlaw.is_while_ahead == True)
        if "result-changing" in impact_tags:
            imp_clauses.append(GameFlaw.is_result_changing == True)
        clauses.append(or_(*imp_clauses))  # OR within impact family
    
    return clauses  # caller ANDs all clauses together
```

**Games tab:** wraps in `EXISTS (SELECT 1 FROM game_flaws WHERE game_id = Game.id AND user_id = :uid AND <clauses>)`

**Flaws tab:** uses clauses directly in a `SELECT f.* FROM game_flaws f JOIN games g WHERE f.user_id = :uid AND <clauses> ORDER BY g.played_at DESC, f.ply`

This function lives in `library_repository.py` (alongside the other Games-surface repository functions).

**Note:** Phase tags (`opening`, `middlegame`, `endgame`) are NOT filter predicates — they are excluded from the `FlawFilterControl` per UI-SPEC. The `build_flaw_filter_clauses` function need not handle them.

### 7. `get_library_games` / `get_flaw_stats` — Current On-The-Fly Call Points

[VERIFIED: `app/services/library_service.py` live code]

**`get_library_games`** (line 143): calls `library_repository.query_filtered_games` then `_build_card` for each game in the page. `_build_card` (line 87) calls `fetch_game_positions_ordered` + `count_game_severities` + `classify_game_flaws`. Post-D-02:

- `query_filtered_games` still used for the paginated `Game` objects.
- `_build_card` is replaced: chips + severity counts read from `game_flaws` JOIN, no kernel re-call.
- The `flaw_severity` EXISTS subquery in `query_filtered_games` is upgraded to the `game_flaws`-backed version.

**`get_flaw_stats`** (line 423): calls `count_filtered_and_analyzed` → `analyzed_game_ids` → `_load_analyzed_flaws` (the N+1 kernel re-call loop). Post-D-02:

- Severity counts + tag distribution come from a single `COUNT(*) FILTER (WHERE ...)` pass over `game_flaws JOIN games`.
- The `_load_analyzed_flaws` inner loop is retired.
- The `analyzed_n` / `total_n` denominator still uses `_analyzed_game_ids_subquery` (unchanged — it's based on `game_positions` eval coverage, not `game_flaws`).
- The rolling trend (`_compute_trend`) still needs per-game data; this can be derived from a `SELECT g.played_at, COUNT(*) FROM game_flaws f JOIN games g GROUP BY g.id ORDER BY g.played_at` aggregate.

### 8. Per-Flaw List Endpoint — Recommended Schema

[ASSUMED — not locked in CONTEXT.md, within Claude's discretion]

```python
# app/schemas/library.py additions

class FlawListItem(BaseModel):
    """One row in the Flaws subtab list — one flawed position."""
    game_id: int
    ply: int
    fen: str                          # board_fen() at this ply
    move_san: str | None              # the flawed move in SAN
    severity: FlawSeverity            # "mistake" | "blunder"
    tags: list[FlawTag]               # reconstructed from typed columns
    es_before: float
    es_after: float
    # Game metadata for the row header (opponent / date / result)
    user_result: Literal["win", "draw", "loss"]
    played_at: datetime.datetime | None
    time_control_bucket: str | None
    platform: str
    platform_url: str | None
    white_username: str | None
    black_username: str | None
    user_color: str

class LibraryFlawsResponse(BaseModel):
    flaws: list[FlawListItem]
    matched_count: int
    offset: int
    limit: int
```

The `tags` list is reconstructed from typed columns in the repository:
```python
# Reconstruct tags list from typed columns (deterministic order matching FlawRecord)
tags = []
if flaw.is_while_ahead: tags.append("while-ahead")
if flaw.is_result_changing: tags.append("result-changing")
if flaw.is_miss: tags.append("miss")
if flaw.is_lucky_escape: tags.append("lucky-escape")
tags.append(_PHASE_INT_TO_TAG[flaw.phase])  # always present
if flaw.tempo is not None: tags.append(_TEMPO_INT_TO_TAG[flaw.tempo])
```

### 9. `scripts/backfill_flaws.py` Pattern

[VERIFIED: `scripts/backfill_eval.py` inspected — full 900-line script]

The backfill script mirrors `backfill_eval.py`'s architecture:

**CLI arguments:**
```python
parser.add_argument("--db", choices=["dev", "benchmark", "prod"], required=True)
parser.add_argument("--user-id", type=int, default=None, dest="user_id")
parser.add_argument("--dry-run", action="store_true", dest="dry_run")
parser.add_argument("--limit", type=int, default=None)  # optional, cap games processed
```

**No `--workers` arg** — classify_game_flaws is CPU-only (no Stockfish), fast enough serial.

**Key differences from `backfill_eval.py`:**
- No EnginePool — classification is pure Python (no engine calls).
- Idempotency: `DELETE FROM game_flaws WHERE game_id = :gid AND user_id = :uid` before re-inserting (or `ON CONFLICT DO NOTHING` if only backfilling missing rows; full recompute uses DELETE + INSERT).
- Batch size: process games in groups of e.g. 100 (load positions, classify, insert, commit). No streaming cursor needed for flaws (per-game position load is already bounded).
- The `BATCH_SIZE` constant must be documented and named (no magic numbers).

**Skeleton:**
```python
BACKFILL_GAMES_PER_BATCH = 100  # games per commit chunk

async def run_backfill(*, db: str, user_id: int | None, dry_run: bool, limit: int | None) -> None:
    url = db_url_for_target(db)
    engine = create_async_engine(url, pool_pre_ping=True)
    session_maker = async_sessionmaker(engine, expire_on_commit=False)
    
    # Stream analyzed game IDs (coverage >= EVAL_COVERAGE_MIN)
    # Delete existing game_flaws rows for each game, then reclassify and insert
    # Process in BACKFILL_GAMES_PER_BATCH chunks, commit per chunk
    # Log progress; capture Sentry on errors
    ...
```

**Verification target:** `--db dev --user-id 28` must complete without error and produce rows in `game_flaws` for dev user 28.

### 10. Alembic Migration Conventions

[VERIFIED: `alembic/versions/` inspected, especially the SEED-035 migration]

**Filename pattern:** `YYYYMMDD_HHMMSS_<8-char-hash>_<description>.py`

**Key rules from existing migrations:**
- Never import live app constants in migrations (they are version-pinned snapshots). Inline all column sizes, types, and threshold values as literals.
- For `CONCURRENTLY` index builds, use `op.get_context().autocommit_block()` (required — CONCURRENTLY cannot run inside a transaction).
- Always provide `downgrade()` even if it is a dev-only escape hatch.
- Explicit `ondelete` policy on all FKs (project rule: mandatory).

**Migration content for `game_flaws`:**

```python
def upgrade() -> None:
    op.create_table(
        "game_flaws",
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("game_id", sa.Integer(), nullable=False),
        sa.Column("ply", sa.SmallInteger(), nullable=False),
        sa.Column("severity", sa.SmallInteger(), nullable=False),
        sa.Column("tempo", sa.SmallInteger(), nullable=True),
        sa.Column("phase", sa.SmallInteger(), nullable=False),
        sa.Column("is_miss", sa.Boolean(), nullable=False),
        sa.Column("is_lucky_escape", sa.Boolean(), nullable=False),
        sa.Column("is_while_ahead", sa.Boolean(), nullable=False),
        sa.Column("is_result_changing", sa.Boolean(), nullable=False),
        sa.Column("es_before", sa.Float(), nullable=False),
        sa.Column("es_after", sa.Float(), nullable=False),
        sa.Column("move_san", sa.String(), nullable=True),
        sa.Column("fen", sa.String(), nullable=False, server_default=""),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["game_id"], ["games.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id", "game_id", "ply"),
    )
    # SEED-038: additional index on (user_id, severity) for severity scans
    with op.get_context().autocommit_block():
        op.create_index(
            "ix_game_flaws_user_severity",
            "game_flaws",
            ["user_id", "severity"],
            postgresql_concurrently=True,
        )
```

### 11. Bulk Insert Mechanism for `game_flaws`

[VERIFIED: `app/repositories/game_repository.py` — `bulk_insert_positions` uses asyncpg COPY]

For the import hook (per-game, ~1-5 rows per game): **SQLAlchemy `INSERT ... ON CONFLICT DO NOTHING`** is appropriate. The rows are few and the insert is simple. `asyncpg COPY` is only beneficial for large bulk loads (hundreds+ rows).

For `backfill_flaws.py` (potentially thousands of rows per user): use `asyncpg COPY` via `copy_records_to_table` mirroring `bulk_insert_positions`. Or use executemany with `pg_insert(...).on_conflict_do_nothing()`. Given row sizes are small, executemany is simpler to implement correctly.

**Recommended approach:**
- Import hook: `pg_insert(GameFlaw).values(rows).on_conflict_do_nothing()` (simple, safe, idempotent)
- Backfill: delete-then-insert for full recompute (cleaner than ON CONFLICT for threshold changes)

### 12. `useFlawFilterStore` — Mirrors `useFilterStore` Exactly

[VERIFIED: `app/frontend/src/hooks/useFilterStore.ts` — 37 lines, zero dependencies]

`useFilterStore` is a module-level `useSyncExternalStore` pattern (not Zustand). The new `useFlawFilterStore` follows the identical pattern:

```typescript
// frontend/src/hooks/useFlawFilterStore.ts
import { useSyncExternalStore, useCallback } from 'react';
import type { FlawTag } from '@/types/library';

export interface FlawFilterState {
  severity: ('blunder' | 'mistake')[];  // default: both
  tags: FlawTag[];                      // default: []
}

export const DEFAULT_FLAW_FILTER: FlawFilterState = {
  severity: ['blunder', 'mistake'],
  tags: [],
};

// ... identical module-level store pattern
```

**No Zustand required.** The existing pattern is sufficient.

### 13. `LibraryPage.tsx` — Current Tab Structure and Where to Insert "Flaws"

[VERIFIED: `frontend/src/pages/library/LibraryPage.tsx`]

Current tabs: `import | games | stats`. The Flaws tab inserts between `games` and `stats`:

**New tab order:** `Import · Games · Flaws · Stats` (CONTEXT.md D-06 says "Import · Games · Flaws · Overview" — but the current code uses `stats` not `overview`/`stats`; the tab value `stats` corresponds to the Stats/Overview subtab. The tab label shown is "Stats".)

The `activeTab` detection (line 38-42) needs a `flaws` branch:
```typescript
const activeTab = location.pathname.includes('/import') ? 'import'
  : location.pathname.includes('/games') ? 'games'
  : location.pathname.includes('/flaws') ? 'flaws'  // NEW
  : 'stats';
```

### 14. `TagChip` — Converting from Popover Trigger to Navigation

[VERIFIED: `frontend/src/components/library/TagChip.tsx`]

Current `TagChip` is a Radix `PopoverPrimitive.Root` with `<span role="button">` trigger (lines 107-144). Phase 107 shipped it as display-only. Phase 108 makes it a navigation trigger:

- Replace the `PopoverPrimitive.Root/Trigger` with a `<button type="button">` that calls `navigate('/library/flaws?tag=${tag}')`.
- `aria-label` changes from `"Tag: ${tag} — ${TAG_DEFINITIONS[tag]}"` to `"Filter flaws by tag: ${tag}"` (per UI-SPEC).
- `data-testid="chip-${tag}-${gameId}"` unchanged.
- The popover definition display is removed (the chip is now navigation, not info).

This is a **breaking change to TagChip's API** — the `gameId` prop may become optional or be renamed. Confirm that no other consumers of `TagChip` expect the popover behavior before removing it. [VERIFIED: only `LibraryGameCard.tsx` uses `TagChip`]

### 15. GamesTab.tsx — Migration from Local `severityFilter` to `useFlawFilterStore`

[VERIFIED: `frontend/src/pages/library/GamesTab.tsx` lines 57-58]

Current local state:
```typescript
const [severityFilter, setSeverityFilter] = useState<('blunder' | 'mistake')[]>([]);
```

Phase 108 replaces this with the shared store:
```typescript
const [flawFilter, setFlawFilter] = useFlawFilterStore();
```

The `handleSeverityChange` and `handlePendingSeverityChange` callbacks are replaced by a `handleFlawFilterChange` that writes to the store. The query hook call changes from:
```typescript
useLibraryGames(appliedFilters, severityFilter, offset, PAGE_SIZE)
```
to:
```typescript
useLibraryGames(appliedFilters, flawFilter.severity, flawFilter.tags, offset, PAGE_SIZE)
```

The `useLibrary.ts` `buildLibraryParams` function gets new `tags` parameter and serializes them as multi-value `tag=low-clock&tag=result-changing` params.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Shared module-level state | Zustand store | `useSyncExternalStore` pattern (see `useFilterStore.ts`) | Already established pattern; zero new deps |
| Bulk insert game_flaws | Custom SQL text | `pg_insert(...).on_conflict_do_nothing()` or asyncpg COPY | Existing patterns in `game_repository.py` |
| URL sync (replace-state) | Custom history.pushState | `useSearchParams` from react-router-dom | Already used elsewhere in the app |
| Miniboard with arrow | Custom board rendering | `LazyMiniBoard` + `MiniBoardArrow` | Already complete in `components/board/` |
| Pagination | Custom page controls | `Pagination` component (`components/results/Pagination.tsx`) | Shared component already extracted in Phase 107 |
| Tag icons | Custom SVGs | `lucide-react` icons already mapped in `TagChip.tsx` | `TAG_ICONS` record already exists |
| Tag labels/definitions | Inline JSX copy | `TAG_DEFINITIONS` / `TAG_LABELS` from `tagDefinitions.ts` | Already authoritative |

---

## Common Pitfalls

### Pitfall 1: asyncio.gather on the Same AsyncSession in the Import Hook

**What goes wrong:** If `_classify_and_insert_flaws` loads positions for multiple games using `asyncio.gather`, it violates the CLAUDE.md hard rule and may corrupt the session.

**How to avoid:** Loop sequentially over `game_ids` inside `_classify_and_insert_flaws`. The batch size is 10 games (eval drain `_DRAIN_BATCH_SIZE`) — sequential is fast enough.

### Pitfall 2: Writing `game_flaws` Rows Before `eval_cp` is Committed

**What goes wrong:** The import hook must run after eval results are written and committed, or `classify_game_flaws` reads NULL evals and produces no rows (or `GameNotAnalyzed`).

**How to avoid:** The hook runs inside the same write-window session as `_apply_eval_results` — eval writes happen first (line order), then classification, then `_mark_evals_completed`, then `session.commit()`. All in one atomic transaction.

### Pitfall 3: On-the-fly `flaw_exists_subquery` SQL<->Kernel Cross-Check Test

**What goes wrong:** After migrating the Games-tab EXISTS filter from the window-scan to `game_flaws`, the `flagged_plies_for_severity` test helper and the SQL<->kernel cross-check test (B2) become stale/incorrect.

**How to avoid:** Update or retire the cross-check test when migrating. The `game_flaws` table IS the materialized kernel output, so there is no longer a separate SQL path to drift from the kernel. The new invariant to test: `game_flaws` rows match what `classify_game_flaws` would return for that game.

### Pitfall 4: `fen` Column Missing from `game_flaws` — Miniboard Cannot Render

**What goes wrong:** If `fen` is not stored in `game_flaws`, the per-flaw list endpoint must JOIN to `game.pgn` and replay the PGN for every row in a page — O(page_size * game_length) work per request.

**How to avoid:** Store `fen` in `game_flaws` as a `String` column. It is already computed by `classify_game_flaws` via `_recompute_fen_map(game.pgn)` and stored in `FlawRecord.fen`. Simply include it in the insert dict.

### Pitfall 5: FlawFilterControl Tag-Phase Exclusion

**What goes wrong:** Including `opening`, `middlegame`, `endgame` in the `FlawFilterControl` toggle buttons or in the `build_flaw_filter_clauses` tag handler.

**How to avoid:** Per UI-SPEC §"Tag-family sections" — phase tags are NOT filter predicates. They appear only in the Flaw-Stats histogram. The `FlawFilterControl` renders only the 7 non-phase tags. The predicate builder handles only those 7.

### Pitfall 6: Stats Migration — Analyzed Game Count Denominator

**What goes wrong:** After migrating `get_flaw_stats` to read from `game_flaws`, the `analyzed_n` / `total_n` denominators could erroneously be derived from `game_flaws` row counts instead of the `_analyzed_game_ids_subquery` eval-coverage gate.

**How to avoid:** `analyzed_n` still uses `_analyzed_game_ids_subquery` (based on `game_positions` eval coverage >= 90%). A game with analyzed games but zero M+B flaws still contributes to `analyzed_n` but has zero `game_flaws` rows. The denominator is the number of analyzed games, not the number of flaw rows.

### Pitfall 7: Chip Deep-Link URL Shape (D-05 Amendment)

**What goes wrong:** Using `/library/flaws?game_id={ID}&tag={TAG}` from SEED-038's original spec (which D-05 explicitly amends).

**How to avoid:** The chip deep-link is `/library/flaws?tag={TAG}` with NO `game_id`. The Flaws tab shows all user flaws with that tag, not scoped to a single game.

### Pitfall 8: Severity Toggle Deselect-All State

**What goes wrong:** `FlawFilterControl` severity buttons can be deselected to have both unchecked (empty array), which would send `severity=[]` to the backend — showing no results or crashing.

**How to avoid:** Per UI-SPEC §"Severity section" — enforce at-least-one-selected: prevent deselecting the last active button. If a user clicks the only active button, ignore the click (or snap back). Default is both selected; deselecting one (to get blunders-only or mistakes-only) is the useful action.

---

## Code Examples

### Verified Pattern: Shared predicate builder + EXISTS (Games tab) and SELECT (Flaws tab)

Based on existing `flaw_exists_subquery` in `library_repository.py` and SEED-038 query patterns [VERIFIED: codebase inspection]:

```python
# library_repository.py — new shared predicate builder
def build_flaw_filter_clauses(
    severity: Sequence[FlawSeverity],
    tags: Sequence[FlawTag],
) -> list[ColumnElement[bool]]:
    """OR within family, AND across families (SEED-038)."""
    clauses: list[ColumnElement[bool]] = []
    if severity:
        threshold = min(_SEVERITY_INT[s] for s in severity)
        clauses.append(GameFlaw.severity >= threshold)
    # ... tag family clauses (see Pattern 6 above)
    return clauses

# Games tab: wrap in EXISTS
def flaw_exists_from_table(
    user_id: int,
    severity: Sequence[FlawSeverity],
    tags: Sequence[FlawTag],
) -> ColumnElement[bool]:
    clauses = build_flaw_filter_clauses(severity, tags)
    if not clauses:
        return true()  # no filter = match all
    return exists(
        select(GameFlaw.ply).where(
            GameFlaw.game_id == Game.id,
            GameFlaw.user_id == user_id,
            *clauses,
        )
    )

# Flaws tab: SELECT f.* with JOIN
async def query_flaws(
    session: AsyncSession,
    user_id: int,
    *,
    game_filters: dict,         # same game-metadata filters as Games tab
    severity: Sequence[FlawSeverity],
    tags: Sequence[FlawTag],
    offset: int,
    limit: int,
) -> tuple[list[FlawListItem], int]:
    flaw_clauses = build_flaw_filter_clauses(severity, tags)
    base = (
        select(GameFlaw, Game)
        .join(Game, Game.id == GameFlaw.game_id)
        .where(GameFlaw.user_id == user_id)
        .where(*flaw_clauses)
    )
    base = apply_game_filters(base, **game_filters, user_id=user_id)
    # count + paginate
    ...
    # ORDER BY g.played_at DESC NULLS LAST, f.ply ASC (D-07)
```

### Verified Pattern: FlawFilterControl toggle button (from UI-SPEC)

```tsx
// components/filters/FlawFilterControl.tsx
<button
  type="button"
  data-testid="filter-flaw-severity-blunder"
  aria-pressed={severity.includes('blunder')}
  className={cn(
    "h-11 sm:h-7 rounded-md px-3 text-sm font-bold border transition-colors",
    severity.includes('blunder')
      ? "border-toggle-active bg-toggle-active text-toggle-active-foreground"
      : "border-border bg-inactive-bg text-muted-foreground"
  )}
  onClick={() => handleSeverityToggle('blunder')}
>
  Blunders
</button>
```

### Verified Pattern: URL sync on Flaws tab (replace-state)

```typescript
// pages/library/FlawsTab.tsx
const [searchParams, setSearchParams] = useSearchParams();
const [flawFilter, setFlawFilter] = useFlawFilterStore();

// On mount: read URL params and initialize store
useEffect(() => {
  const tags = searchParams.getAll('tag') as FlawTag[];
  const severity = searchParams.getAll('severity') as ('blunder' | 'mistake')[];
  setFlawFilter({
    tags,
    severity: severity.length > 0 ? severity : ['blunder', 'mistake'],
  });
}, []); // eslint-disable-line react-hooks/exhaustive-deps — intentional mount-only

// On store change: update URL (replace, not push)
useEffect(() => {
  const params = new URLSearchParams();
  if (flawFilter.tags.length > 0) {
    flawFilter.tags.forEach(t => params.append('tag', t));
  }
  if (flawFilter.severity.length < 2) {
    flawFilter.severity.forEach(s => params.append('severity', s));
  }
  setSearchParams(params, { replace: true });
}, [flawFilter, setSearchParams]);
```

---

## Runtime State Inventory

> Not a rename/refactor phase — skip full table. One note relevant to D-10 freshness:

After the migration, existing `game_flaws` rows in prod will be empty (table is new). The Games tab (migrated to read `game_flaws`) will show an empty list until `backfill_flaws.py --db prod` runs. This is the D-09 accepted consequence: "existing users see an empty Games tab until the table is populated." The backfill is manual, post-deploy.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest + pytest-asyncio |
| Config file | `pyproject.toml` / `pytest.ini` |
| Quick run command | `uv run pytest tests/test_library*.py -x` |
| Full suite command | `uv run pytest -n auto -x` |
| Frontend tests | `npm test -- --run` |

### Phase Requirements → Test Map

| Behavior | Test Type | Automated Command | Notes |
|----------|-----------|-------------------|-------|
| `game_flaws` table created by migration | Integration | `uv run alembic upgrade head` | Migration creates table |
| `classify_game_flaws` → `game_flaws` INSERT round-trip | Integration | `uv run pytest tests/test_game_flaws_repository.py -x` | New test file |
| Flaw predicate builder: OR-within / AND-across family logic | Unit | `uv run pytest tests/test_library_repository.py::test_flaw_filter_predicate -x` | |
| GET /library/flaws returns paginated rows | Integration | `uv run pytest tests/test_library_routes.py::test_get_flaws -x` | |
| GET /library/games returns same results as pre-migration (migrated from on-the-fly) | Regression | `uv run pytest tests/test_library_routes.py::test_games_migration -x` | |
| Backfill script dry-run on dev | Manual | `uv run python scripts/backfill_flaws.py --db dev --user-id 28 --dry-run` | Smoke check |
| Backfill script populates game_flaws | Manual | `uv run python scripts/backfill_flaws.py --db dev --user-id 28` | Verify rows in DB |
| FlawFilterControl renders all family sections | Frontend unit | `npm test -- --run` (vitest) | |
| Chip deep-link navigates to `/library/flaws?tag=X` | Frontend unit | `npm test -- --run` | |

### Sampling Rate

- **Per commit:** `uv run pytest tests/test_library*.py -x && (cd frontend && npm test -- --run)`
- **Per wave merge:** `uv run pytest -n auto -x && (cd frontend && npm run lint && npm test -- --run)`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `tests/test_game_flaws_repository.py` — covers bulk insert + round-trip classify
- [ ] `tests/test_library_flaws_route.py` — covers GET /library/flaws pagination + filter
- [ ] `tests/test_backfill_flaws.py` — covers dry-run + batch insert (reuse session-maker injection pattern from `test_backfill_eval.py`)
- [ ] `frontend/src/components/filters/__tests__/FlawFilterControl.test.tsx` — covers toggle behavior, OR/AND semantics display, clear affordance

---

## Security Domain

> `security_enforcement` not set to false — section included.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V4 Access Control | yes | `user_id` FK on `game_flaws`; all queries scope to `user_id = :uid` |
| V5 Input Validation | yes | FastAPI Query params with `Literal["mistake", "blunder"]`; FlawTag validated as Literal in schemas |
| V3 Session Management | no | Existing FastAPI-Users session unchanged |
| V2 Authentication | no | Existing `current_active_user` dependency unchanged |
| V6 Cryptography | no | No new cryptography |

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Cross-user flaw data access | Information Disclosure | `GameFlaw.user_id == user_id` in all queries (same as `game_positions` ownership guard) |
| SQL injection via tag/severity params | Tampering | Literal type constraint at FastAPI layer; parameterized SQLAlchemy binds |
| Unauthorized `game_flaws` write via import hook | Tampering | Hook runs inside `eval_drain.py` which operates on authenticated game_ids only |

---

## Open Questions (RESOLVED)

> All three resolved at planning time and implemented in the plans:
> (1) `fen` stored as a column in `game_flaws` (Plan 108-01); (2) stats trend via
> `GROUP BY game_id ... ORDER BY played_at` over `game_flaws JOIN games` (Plan 108-04);
> (3) FlawsTab URL→store sync applied only when URL params are present, else
> initialize from the shared store (Plan 108-07).

1. **`fen` storage in `game_flaws`**
   - What we know: SEED-038 schema omits `fen`; `FlawRecord.fen` is computed during `classify_game_flaws`.
   - What's unclear: Whether to store it as a column or recompute per display request.
   - Recommendation: Store as `String` column. The "display payload" rationale for `es_before/es_after/move_san` applies equally to `fen` — without it the Flaws list endpoint must replay PGNs per request.

2. **Stats migration trend computation**
   - What we know: The current rolling-trend in `_compute_trend` needs per-game played_at + flaw counts.
   - What's unclear: Whether a `GROUP BY game_id` + `ORDER BY played_at` query over `game_flaws JOIN games` is efficient enough vs keeping a per-game summary table.
   - Recommendation: `SELECT g.played_at, COUNT(*) as mb_count FROM game_flaws f JOIN games g ON f.game_id = g.id WHERE f.user_id = :uid AND <filters> GROUP BY g.id, g.played_at ORDER BY g.played_at` — the per-user flaw count is bounded (thousands of rows), so this is cheap.

3. **FlawsTab URL sync initialization vs GamesTab state**
   - What we know: Both tabs share `useFlawFilterStore`. The Flaws tab URL-syncs on mount.
   - What's unclear: If a user is on the Games tab with a custom flaw filter and then navigates to the Flaws tab, the URL sync on mount will read URL params (empty) and overwrite the store — losing the Games tab selection.
   - Recommendation: URL sync on mount should only apply when URL params are present. If `?tag=` is absent from the URL (direct navigation, not chip deep-link), initialize from the store's existing state (no overwrite). Only apply URL→store sync when URL has params.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `fen` should be stored as a `String` column in `game_flaws` (not recomputed at display time) | Key Implementation Details §1 + Open Questions | If wrong: per-flaw list endpoint must replay PGN per request (expensive); OR FEN is omitted (miniboard cannot render) |
| A2 | The rolling trend in `get_flaw_stats` can be served by a `GROUP BY game_id, played_at` query over `game_flaws JOIN games` | Key Implementation Details §7 | If wrong: requires a per-game summary or separate query path |
| A3 | FlawsTab URL sync on mount only applies when URL params are present | Open Questions §3 | If wrong: switching Games→Flaws always clears the flaw filter state |

---

## Sources

### Primary (HIGH confidence — all from direct codebase inspection)

- `app/services/flaws_service.py` — `classify_game_flaws` signature (line 447), `FlawRecord` TypedDict (lines 95-103), tag taxonomy
- `app/services/library_service.py` — `get_library_games` (line 143), `get_flaw_stats` (line 423), `_build_card` (line 87), `_load_analyzed_flaws` (line 261)
- `app/repositories/library_repository.py` — `flaw_exists_subquery` (line 164), `_per_ply_drop_subquery` (line 97), `query_filtered_games` (line 268)
- `app/repositories/query_utils.py` — `apply_game_filters` signature (line 11), `flaw_severity` keyword-only param (line 24)
- `app/repositories/flaws_repository.py` — `fetch_game_positions_ordered` (line 13)
- `app/repositories/game_repository.py` — `bulk_insert_positions` asyncpg COPY pattern (line 195), `bulk_insert_games` ON CONFLICT DO NOTHING (line 48)
- `app/services/eval_drain.py` — `run_eval_drain` structure (line 493), insertion point for hook (lines 543-551)
- `app/services/import_service.py` — `_BATCH_SIZE = 30` (line 78), cold-lane architecture comment (lines 719-721)
- `app/schemas/library.py` — existing schema shapes
- `app/routers/library.py` — `APIRouter(prefix="/library")`, existing routes
- `alembic/versions/20260603_153628_f4d88c3659c6_gp_natural_composite_pk_seed_035.py` — migration conventions, `autocommit_block` pattern
- `app/core/config.py` — `db_url_for_target()` signature (line 80)
- `frontend/src/hooks/useFilterStore.ts` — `useSyncExternalStore` pattern to mirror
- `frontend/src/pages/library/GamesTab.tsx` — `severityFilter` local state (line 57-58)
- `frontend/src/pages/library/LibraryPage.tsx` — tab structure, `activeTab` detection
- `frontend/src/components/library/TagChip.tsx` — current popover-trigger API
- `frontend/src/components/results/Pagination.tsx` — `PaginationProps` interface
- `frontend/src/components/board/MiniBoard.tsx` — `MiniBoardProps` interface, arrow overlay
- `frontend/src/hooks/useLibrary.ts` — `buildLibraryParams`, `useLibraryGames` signature
- `frontend/src/api/client.ts` — `libraryApi.getGames`, `libraryApi.getFlawStats` shapes
- `frontend/src/types/library.ts` — `FlawTag`, `FlawSeverity`, `GameFlawCard`, etc.
- `scripts/backfill_eval.py` — full `--db/--user-id/--dry-run/--limit` CLI pattern, session_maker + async architecture

### Secondary (MEDIUM confidence)

- SEED-038 — `game_flaws` schema design, query patterns, indexing guidance
- CONTEXT.md D-01..D-10 — locked decisions
- UI-SPEC 108 — `FlawFilterControl` component contract

---

## Metadata

**Confidence breakdown:**
- Schema + migration: HIGH — SEED-038 locked schema verified against existing ORM conventions
- Backend service migration: HIGH — all call sites read directly from live code
- Import hook insertion point: HIGH — `eval_drain.py` structure read directly
- Backfill script pattern: HIGH — `backfill_eval.py` read in full
- Frontend store pattern: HIGH — `useFilterStore.ts` read directly
- Frontend component structure: HIGH — `GamesTab.tsx`, `LibraryPage.tsx`, `TagChip.tsx` all read

**Research date:** 2026-06-06
**Valid until:** 2026-07-06 (stable codebase — no fast-moving external deps)
