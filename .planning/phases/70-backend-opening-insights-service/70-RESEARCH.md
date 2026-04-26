# Phase 70: Backend opening insights service - Research

**Researched:** 2026-04-26
**Domain:** Backend service layer (FastAPI + async SQLAlchemy + PostgreSQL)
**Confidence:** HIGH

## Summary

Phase 70 has a fully locked design in CONTEXT.md (D-01..D-33) — the algorithm, classifier, response shape, file layout, and a verified Alembic index migration are all decided. This research's job is to map every decision to concrete codebase paths, signatures, and reuse points so the planner writes atomic plans without re-investigating the codebase.

The phase is **first-principles transition aggregation** — one SQL query per color over `(entry_hash, candidate_san)` transitions in `entry_ply ∈ [3, 16]`, classification at SQL HAVING level, then Python orchestrates dedupe / attribution / ranking / cap. No reuse of `query_top_openings_sql_wdl`, no reuse of `query_next_moves`, no bookmark consumption. New schema artifact: a single partial composite covering index (`ix_gp_user_game_ply`) verified to drop the heaviest user from 2.0 s to 816 ms.

**Primary recommendation:** Six artifacts to land in this phase: `app/schemas/opening_insights.py` (new), `app/services/opening_insights_service.py` (new), `app/repositories/openings_repository.py` (extend with one new function — D-27 leaves "new repo file vs. extend existing" to planner; extending is cheaper and matches existing conventions), `app/routers/insights.py` (add `POST /openings` route + extract user from `current_active_user`), one Alembic migration adding `ix_gp_user_game_ply` (CONCURRENTLY, separate revision from any data migration), and the `__table_args__` declaration on `GamePosition` so future autogenerate doesn't drop it. Plus three test files: repository SQL contract test, service unit test against synthetic fixtures, and a frontend-constants-consistency test.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Auth (extract user_id) | API / Backend (router) | — | `Depends(current_active_user)` already established |
| Filter validation / parsing | API / Backend (router → schema) | — | Pydantic v2 `OpeningInsightsRequest` validates at HTTP boundary |
| Transition aggregation SQL | Database / Storage (repository function) | — | Single CTE+HAVING query per color; no business logic in SQL beyond classifier gate |
| Classification / severity / dedupe / ranking / caps | API / Backend (service) | — | Pure Python over repository rows; testable without DB |
| Opening name attribution | Database / Storage (repository) → service | — | Batched `WHERE full_hash IN (...)` then Python picks `MAX(ply_count)` |
| Entry FEN reconstruction | API / Backend (service) | — | python-chess SAN replay; no DB column for FEN on `game_positions` |
| Frontend rendering | Browser / Client (Phase 71) | — | Out of scope for Phase 70 |

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| INSIGHT-CORE-01 | Filters reshape findings; same-filter equivalence | `apply_game_filters` (verified `app/repositories/query_utils.py:13`) embedded in transition CTE; `OpeningInsightsRequest` mirrors filter surface 1:1 (D-10) |
| INSIGHT-CORE-02 | Scan input definition | Replaced per D-15: single transition CTE in `entry_ply ∈ [3, 16]`; bookmarks not consumed (D-18). REQUIREMENTS.md amendment lands at commit time (D-17) |
| INSIGHT-CORE-03 | Single next-ply, no recursion | Inherent to transition CTE: each row is ONE entry → ONE candidate-move pair, never deeper |
| INSIGHT-CORE-04 | Min-games floor | `MIN_GAMES_PER_CANDIDATE = 20` (D-33); enforced in SQL HAVING |
| INSIGHT-CORE-05 | Classify weakness/strength | `loss_rate > 0.55` (weakness) / `win_rate > 0.55` (strength), strict `>`; SQL HAVING drops neutrals (D-04) |
| INSIGHT-CORE-06 | Dedupe by Zobrist hash, deepest opening | `MAX(ply_count)` lookup against `openings.full_hash`; cross-entry dedupe with deeper-entry-wins tiebreak (D-21..D-24) |
| INSIGHT-CORE-07 | Ranking + caps | `(severity desc, n_games desc)` per section; per-color caps 5/3 (D-07, D-08) |
| INSIGHT-CORE-08 | OpeningInsightFinding payload shape | Locked schema in CONTEXT.md §Specifics; new file `app/schemas/opening_insights.py` |
| INSIGHT-CORE-09 | Latency budget, no precompute | Index `ix_gp_user_game_ply` makes Hikaru-class user 816 ms; no caching this phase (D-29) |

## Project Constraints (from CLAUDE.md)

| Directive | Source | How research honors it |
|-----------|--------|------------------------|
| `AsyncSession` not safe for `asyncio.gather` | §Critical Constraints | Two color queries run sequentially on the same session (CONTEXT.md D-30 explicit) |
| `httpx.AsyncClient` only for HTTP | §Critical Constraints | N/A — no external HTTP in this phase |
| Pydantic v2 + Literal for fixed enums | §Coding Guidelines | All `OpeningInsightFinding` state fields (`color`, `classification`, `severity`) are `Literal` (D-05); request fields use existing patterns |
| `uv run ty check` zero errors | §Coding Guidelines | Annotate all new function signatures explicitly; use `Sequence[str]` for filter param types matching existing repos |
| Sentry capture on non-trivial except | §Sentry | Wrap the public `compute_insights` entry point's repository calls in try/except + `sentry_sdk.set_context({"user_id": ..., "request": request.model_dump()})` (mirrors `insights_service.compute_findings` lines 162-169) |
| No magic numbers | §Coding Guidelines | All thresholds as module-level constants at top of `opening_insights_service.py` (D-28) |
| Router prefix in `APIRouter()` only, relative paths in decorators | §Router Convention | `insights.py` already has `prefix="/insights"`; new route is `@router.post("/openings", ...)` not `/insights/openings` |
| `commit_docs: true` | `.planning/config.json` | RESEARCH.md gets committed |

## Standard Stack

### Core (already in project — no new dependencies)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| FastAPI | 0.115.x | HTTP routing | Project standard `[VERIFIED: pyproject + CLAUDE.md]` |
| SQLAlchemy 2.x async | — | Async ORM with `select()` | Project standard; `func`, `case`, `over`, `lag` all imported via `from sqlalchemy import ...` `[VERIFIED: openings_repository.py:7]` |
| asyncpg | — | PG driver | Project standard |
| Pydantic v2 | — | Schema validation | Project standard `[VERIFIED: schemas/insights.py imports pydantic.BaseModel, Field, model_validator]` |
| python-chess | 1.10.x | SAN replay → FEN | Already used in `openings_service.py:9-10` for entry FEN reconstruction (D-25) |
| sentry-sdk | — | Error reporting | Already wired in `app/main.py`; usage pattern at `insights_service.py:165-168` |
| Alembic | — | Migrations | Project standard; CONCURRENTLY pattern not yet used in any prior migration |

**Installation:** No new dependencies needed. All imports resolve from current `pyproject.toml`.

### SQL Window Function: `LAG`

The transition CTE uses `LAG(gp.full_hash) OVER (PARTITION BY gp.game_id ORDER BY gp.ply)` to derive `entry_hash` from the prior ply.

`[CITED: PostgreSQL docs https://www.postgresql.org/docs/16/functions-window.html]` — `lag(value, [offset], [default])` is a standard PostgreSQL window function. SQLAlchemy 2.x exposes it via `from sqlalchemy import func; func.lag(GamePosition.full_hash).over(partition_by=GamePosition.game_id, order_by=GamePosition.ply)`.

The index `(user_id, game_id, ply) INCLUDE (full_hash, move_san) WHERE ply BETWEEN 1 AND 17` is column-ordered to match the partition+order so PostgreSQL can stream rows from the index without a re-sort. CONTEXT.md verified this against the dev DB.

## Existing Code Reuse Map

| Capability | Module | Symbol | Signature / Notes |
|------------|--------|--------|-------------------|
| Filter clause builder | `app/repositories/query_utils.py:13` | `apply_game_filters(stmt, time_control, platform, rated, opponent_type, recency_cutoff, color, *, opponent_strength, elo_threshold)` | Embed AFTER joining `Game`; passes `color` as user_color filter when set. Phase 70 does NOT use the `color` arg of this helper because the user_color filter is hardcoded into each color-specific query (one query for white, one for black) |
| Recency string → datetime | `app/services/openings_service.py:78` | `recency_cutoff(recency: str | None) -> datetime.datetime | None` | Maps `"week"`, `"month"`, etc. to UTC cutoff. `None` and `"all"` both return None. Reuse identically (CONTEXT.md canonical-refs) |
| Default elo threshold | `app/repositories/query_utils.py:11` | `DEFAULT_ELO_THRESHOLD = 50` | Use as default in `OpeningInsightsRequest.elo_threshold` |
| Auth dependency | `app/users.py:257` | `current_active_user = fastapi_users.current_user(active=True)` | Standard `Annotated[User, Depends(current_active_user)]` pattern; pass `user.id` to service |
| Async session dep | `app/core/database.py` | `get_async_session` | Standard `Annotated[AsyncSession, Depends(get_async_session)]` |
| Game model | `app/models/game.py` | `Game` | Has `user_id`, `user_color`, `result` (literal "1-0", "0-1", "1/2-1/2"), and all filter columns |
| GamePosition model | `app/models/game_position.py:9` | `GamePosition` | `user_id`, `game_id`, `ply` (SmallInt), `full_hash` (BigInt), `move_san` (String(10), nullable on final ply). **No `fen` column** — entry FEN must be replayed |
| Opening model | `app/models/opening.py:7` | `Opening` | `eco`, `name`, `pgn`, `ply_count` (SmallInt), `fen` (String(100)), `full_hash` (BigInt nullable). The `pgn` column is the SAN sequence used for parent-lineage walk (D-23) |
| Stats router pattern | `app/routers/insights.py` | `router = APIRouter(prefix="/insights", tags=["insights"])` | EXTEND this file. Do not introduce a new router. New route: `@router.post("/openings", response_model=OpeningInsightsResponse)`. Do NOT call `_validate_full_history_filters` (D-14 explicit) |
| Reference orchestration shape | `app/services/insights_service.py:122` | `compute_findings(filter_context, session, user_id) -> EndgameTabFindings` | Mirror this single-public-entry-point shape. Sequential awaits, Sentry context capture, no concurrent gather |
| Reference repo function shape | `app/repositories/openings_repository.py:359` | `query_next_moves(...)` | Use as a template for SQL composition style: `func.count(...).filter(win_cond)`, `apply_game_filters(stmt, ...)` chaining. **Do NOT call this function** — Phase 70 needs the cross-entry transition aggregation, not per-entry next-moves |
| Reference top-openings query | `app/repositories/stats_repository.py:209` | `query_top_openings_sql_wdl(...)` | NOT called by Phase 70 (algorithm changed per D-15). But it shows the `display_name` "vs. " prefix logic at lines 250-260 — adopt the same convention if Phase 70 attribution yields a name whose `ply_count` parity disagrees with the user's color |

### Win/Loss/Draw Conditions (copy verbatim from `query_top_openings_sql_wdl`)

```python
# stats_repository.py:240-248
win_cond = or_(
    and_(Game.result == "1-0", Game.user_color == "white"),
    and_(Game.result == "0-1", Game.user_color == "black"),
)
draw_cond = Game.result == "1/2-1/2"
loss_cond = or_(
    and_(Game.result == "0-1", Game.user_color == "white"),
    and_(Game.result == "1-0", Game.user_color == "black"),
)
```

When the new query has already filtered `Game.user_color = :color` in the WHERE, these can simplify to a per-color short form, but copying the full forms keeps the predicates correct if the per-color filter is ever lifted.

## Architecture Patterns

### System Architecture Diagram

```
HTTP POST /api/insights/openings
            │
            ▼
┌─────────────────────────────┐
│ insights router             │  ── current_active_user → user.id
│ app/routers/insights.py     │  ── parse OpeningInsightsRequest (Pydantic v2)
└────────────┬────────────────┘
             │ compute_insights(session, user_id, request)
             ▼
┌─────────────────────────────────────────────┐
│ opening_insights_service                    │
│ app/services/opening_insights_service.py    │
│                                             │
│  1. recency_cutoff(request.recency)         │
│  2. for color in colors_to_query():         │  ── D-12 optimization: skip
│       rows = query_opening_transitions(...) │     unused color when filter
│  3. classify + severity (per-row)           │     narrows it
│  4. attribute opening (batched IN-query)    │
│  5. dedupe by resulting_full_hash within    │
│     section (deeper-entry-wins)             │
│  6. rank (severity desc, n_games desc)      │
│  7. cap per section (5 weak / 3 strong)     │
│  8. reconstruct entry_fen via python-chess  │
│  9. assemble OpeningInsightsResponse        │
└────────────┬─────────────────┬──────────────┘
             │                 │
             ▼                 ▼
   ┌──────────────────┐  ┌──────────────────────────────┐
   │ openings_repo    │  │ openings_repo (existing or   │
   │ NEW:             │  │ new): batched opening lookup │
   │  query_opening_  │  │  WHERE full_hash IN (...)    │
   │  transitions()   │  │                              │
   └────────┬─────────┘  └─────────┬────────────────────┘
            │                      │
            ▼                      ▼
       PostgreSQL            PostgreSQL `openings` table
       game_positions ⨝ games
       (uses ix_gp_user_game_ply
        index — Heap Fetches: 0)
```

### Recommended File Layout

```
app/
├── schemas/
│   └── opening_insights.py        # NEW — request, response, finding models
├── services/
│   └── opening_insights_service.py # NEW — single public entry compute_insights()
├── repositories/
│   └── openings_repository.py     # EXTEND — add query_opening_transitions()
│                                  # and query_openings_by_hashes() helpers
├── routers/
│   └── insights.py                # EXTEND — add @router.post("/openings")
└── models/
    └── game_position.py           # EXTEND __table_args__ — declare new index

alembic/versions/
└── {YYYYMMDD_HHMMSS}_{rev}_add_gp_user_game_ply_index.py  # NEW

tests/
├── test_opening_insights_repository.py        # NEW — SQL contract tests
└── services/
    ├── test_opening_insights_service.py        # NEW — unit tests over fixtures
    └── test_opening_insights_arrow_consistency.py  # NEW — regex-parses arrowColor.ts
```

D-27 says "new repo function in `openings_repository.py` OR a new `opening_insights_repository.py` — planner picks". Recommendation: extend `openings_repository.py`. The two new functions (`query_opening_transitions`, `query_openings_by_hashes`) are semantically aligned with existing functions in that file (`query_next_moves`, `query_transposition_counts`) and only ~150 lines together — splitting into a new module would fragment the openings DB-access surface for no gain.

### Pattern 1: Sequential Awaits on Single AsyncSession

**What:** When a service needs multiple queries, run them sequentially on the same session. Never `asyncio.gather`.
**When to use:** Always with `AsyncSession` per CLAUDE.md §Critical Constraints.
**Example:**
```python
# Source: app/services/insights_service.py:142-161
all_time_resp = await get_endgame_overview(session=session, ...)
last_3mo_resp = await get_endgame_overview(session=session, ...)
```

### Pattern 2: SQL HAVING Pre-Filter + Python Post-Process

**What:** Push the n-floor and classifier into the SQL HAVING clause; let Python handle attribution / dedupe / ranking / caps. Reduces the Python-side row count from millions to <1000.
**Example:** Phase 70 transition CTE (D-30):
```python
# Pseudocode — actual implementation lives in openings_repository.query_opening_transitions
transitions_cte = (
    select(
        GamePosition.game_id,
        GamePosition.ply,
        GamePosition.move_san,
        func.lag(GamePosition.full_hash).over(
            partition_by=GamePosition.game_id,
            order_by=GamePosition.ply,
        ).label("entry_hash"),
    )
    .where(
        GamePosition.user_id == user_id,
        GamePosition.ply.between(MIN_ENTRY_PLY - 2, MAX_ENTRY_PLY + 1),  # 1..17
    )
    .cte("transitions")
)

n_games = func.count(func.distinct(Game.id))
wins = n_games.filter(win_cond)
losses = n_games.filter(loss_cond)

stmt = (
    select(
        transitions_cte.c.entry_hash,
        transitions_cte.c.move_san,
        n_games.label("n"),
        wins.label("w"),
        n_games.filter(draw_cond).label("d"),
        losses.label("l"),
    )
    .select_from(transitions_cte)
    .join(Game, Game.id == transitions_cte.c.game_id)
    .where(
        Game.user_id == user_id,
        Game.user_color == color,
        transitions_cte.c.entry_hash.is_not(None),
        transitions_cte.c.move_san.is_not(None),
        transitions_cte.c.ply.between(MIN_ENTRY_PLY + 1, MAX_ENTRY_PLY + 1),  # 4..17
    )
    .group_by(transitions_cte.c.entry_hash, transitions_cte.c.move_san)
    .having(
        and_(
            n_games >= MIN_GAMES_PER_CANDIDATE,
            or_(
                cast(wins, Float) / cast(n_games, Float) > LIGHT_THRESHOLD,
                cast(losses, Float) / cast(n_games, Float) > LIGHT_THRESHOLD,
            ),
        )
    )
)
stmt = apply_game_filters(stmt, time_control, platform, rated, opponent_type,
                          recency_cutoff,
                          opponent_strength=opponent_strength,
                          elo_threshold=elo_threshold)
```

Note: passing `color` to `apply_game_filters` would also work, but the explicit `Game.user_color == color` predicate keeps the per-color intent visible at the call site.

`[ASSUMED]` The exact SQLAlchemy 2.x cast-to-float syntax for the HAVING ratio condition. PostgreSQL supports `(int::float) / int`, but SQLAlchemy may need explicit `cast(n_games, Float)` or `n_games * 1.0`. Planner should verify on first run.

### Pattern 3: Module-Level Constants Block

**What:** All thresholds and tunables at the top of the service file, following the `arrowColor.ts` constant block.
**When to use:** D-28 mandates this for Phase 70.
**Example:**
```python
# At top of app/services/opening_insights_service.py
MIN_ENTRY_PLY: int = 3
MAX_ENTRY_PLY: int = 16
MIN_GAMES_PER_CANDIDATE: int = 20
LIGHT_THRESHOLD: float = 0.55  # mirrors arrowColor.ts LIGHT_COLOR_THRESHOLD/100
DARK_THRESHOLD: float = 0.60   # mirrors arrowColor.ts DARK_COLOR_THRESHOLD/100
WEAKNESS_CAP_PER_COLOR: int = 5
STRENGTH_CAP_PER_COLOR: int = 3
```

### Pattern 4: Pydantic v2 with Literal Enums

**What:** Use `Literal[...]` for fixed enumerations (color, classification, severity, recency, opponent_type, etc.).
**Source:** `app/schemas/insights.py:109-147` (FilterContext) and `endgame_zones.py` Literal aliases.
**Example schema** (locked by D-10, D-26, CONTEXT.md §Specifics):
```python
# app/schemas/opening_insights.py
from typing import Literal
from pydantic import BaseModel, Field
from app.repositories.query_utils import DEFAULT_ELO_THRESHOLD


class OpeningInsightsRequest(BaseModel):
    recency: Literal[
        "all", "week", "month", "3months", "6months", "year", "3years", "5years"
    ] | None = None
    time_control: list[str] | None = None
    platform: list[str] | None = None
    rated: bool | None = None
    opponent_type: Literal["human", "bot", "all"] = "human"
    opponent_strength: Literal["any", "stronger", "similar", "weaker"] = "any"
    elo_threshold: int = DEFAULT_ELO_THRESHOLD
    color: Literal["all", "white", "black"] = "all"


class OpeningInsightFinding(BaseModel):
    color: Literal["white", "black"]
    classification: Literal["weakness", "strength"]
    severity: Literal["minor", "major"]

    opening_name: str           # "<unnamed line>" when no openings-table match anywhere
    opening_eco: str            # "" when no match
    display_name: str           # may include "vs. " prefix when off-color attribution

    entry_fen: str              # reconstructed via python-chess SAN replay
    entry_full_hash: str        # str-form for JSON precision (mirrors OpeningWDL.full_hash)
    candidate_move_san: str
    resulting_full_hash: str    # for Phase 72 dedupe matching

    n_games: int
    wins: int
    draws: int
    losses: int

    win_rate: float             # used as classifier for strengths
    loss_rate: float            # used as classifier for weaknesses
    score: float                # (W + D/2) / n; informative only


class OpeningInsightsResponse(BaseModel):
    white_weaknesses: list[OpeningInsightFinding] = Field(default_factory=list)
    black_weaknesses: list[OpeningInsightFinding] = Field(default_factory=list)
    white_strengths: list[OpeningInsightFinding] = Field(default_factory=list)
    black_strengths: list[OpeningInsightFinding] = Field(default_factory=list)
```

`[ASSUMED]` The `recency` Literal exact value list. `recency_cutoff()` accepts the values shown above (verified `app/services/openings_service.py:46-54`), but the existing endgame `FilterContext.recency` uses `"all_time"` (without the underscore) instead of `"all"`. Reusing the openings convention `"all"` keeps the new endpoint aligned with `/api/openings/*`. The planner should pin the exact Literal in the request schema to match what `recency_cutoff()` accepts.

### Anti-Patterns to Avoid

- **`asyncio.gather(query_white, query_black)`** — same-session concurrent queries. CLAUDE.md §Critical Constraints. Run sequentially.
- **Inlining raw SQL in the service** — D-27 forbids this. The repo function owns the SQL; the service calls it.
- **Calling `query_top_openings_sql_wdl` or `query_next_moves`** — explicit "do not reuse" per CONTEXT.md §canonical-refs.
- **Embedding `color` filter via `apply_game_filters` only** — works correctly, but the explicit `Game.user_color == color` predicate at the join point keeps the per-color SQL self-documenting and matches `query_top_openings_sql_wdl` style.
- **String-form 64-bit hash arithmetic** — return as `str` at the API boundary (per `OpeningWDL.full_hash` convention) but operate as `int` in Python and SQL.
- **Re-using `app/schemas/insights.py::FilterContext`** — explicitly forbidden by D-11.
- **Applying `_validate_full_history_filters`** — explicitly forbidden by D-14.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Filter SQL building | Per-call `if rated is not None: stmt = stmt.where(...)` | `apply_game_filters` | Single source of truth across all openings/stats/endgames repos |
| Recency parsing | Manual `timedelta(days=...)` mapping | `openings_service.recency_cutoff()` | Already maps every accepted recency string |
| FEN reconstruction | Manual board state tracking | `chess.Board()` + `.push_san(san)` loop | python-chess handles every edge case (castling, en passant, promotion). The `pgn` column on `openings` is space-separated SAN; replay via `chess.pgn.read_game(io.StringIO(pgn))` or per-token `board.push_san()` |
| Win-rate / loss-rate / score formulas | Re-deriving from raw `Game.result` in Python | `func.count(...).filter(win_cond)` in SQL | Already a verified pattern in `query_top_openings_sql_wdl` and `query_next_moves` |
| Window function `lag()` | Self-join with `gp1.ply + 1 = gp2.ply` (the existing `query_next_moves` style) | `func.lag(GamePosition.full_hash).over(partition_by=..., order_by=...)` | The self-join doesn't help here — we need ALL transitions across ALL entries in one pass, and the lag stays in-index given `ix_gp_user_game_ply` ordering |
| 4-section ranking by hand | Loop over flat list and bin by `(color, classification)` | Already-decided 4-list response shape | Planner-recommended (D-01) |

**Key insight:** Every supporting capability the phase needs has a verified, named existing implementation in the repo. The only genuinely new code is (a) the transition CTE SQL and (b) the small Python orchestrator. Everything else is glue.

## Common Pitfalls

### Pitfall 1: BigInt Hash Precision Loss in JSON
**What goes wrong:** 64-bit Zobrist hashes serialize as JSON numbers and silently truncate to ~53 bits in JS clients (and some Python JSON parsers).
**Why it happens:** JSON spec uses IEEE-754 double precision; values > 2^53 lose low bits.
**How to avoid:** Stringify hash fields at the API boundary. CONTEXT.md §code_context calls this out: `OpeningInsightFinding.entry_full_hash: str` and `resulting_full_hash: str`. Mirrors `app/schemas/stats.py::OpeningWDL.full_hash: str`.
**Warning signs:** Phase 72 frontend can't match `entry_full_hash` to its own computed Zobrist — the low bits differ.

### Pitfall 2: LAG Across Game Boundaries
**What goes wrong:** Without `PARTITION BY gp.game_id`, the LAG would yield the prior game's last position as a phantom `entry_hash` for the next game's ply 1.
**Why it happens:** Default LAG sees the entire result set ordered by ply.
**How to avoid:** The CTE in D-30 already partitions correctly. Tests must verify that `entry_hash IS NULL` for the very first ply of each game (i.e., `ply=1` rows have NULL entry_hash and are excluded by the outer `t.entry_hash IS NOT NULL` predicate).
**Warning signs:** Spurious entry_hashes that don't appear in the user's actual position graph.

### Pitfall 3: Index Column Order Wrong "for Symmetry"
**What goes wrong:** A future maintainer reorders `ix_gp_user_game_ply` to `(user_id, ply, game_id)` to match sibling indexes. The LAG window function's PARTITION BY game_id then forces a re-sort and the index degrades to a regular scan.
**Why it happens:** Column ordering looks arbitrary at a glance.
**How to avoid:** Add a multi-line comment in BOTH the migration file AND `GamePosition.__table_args__` explaining the LAG-aware ordering. CONTEXT.md §canonical-refs explicitly calls this out.
**Warning signs:** Hikaru-class users regress from <1 s to 2+ s after a "harmless" index refactor.

### Pitfall 4: ply_count Parity Mismatch on Attribution
**What goes wrong:** Attribution returns an opening name defined for the OTHER color (e.g., a black-defined opening name surfaces in the white_weaknesses list).
**Why it happens:** `openings.full_hash` matches positions reached at any ply; an opening defined on white's 4th move (ply_count=7, odd) and one on black's 4th move (ply_count=8, even) can collide on the same position via transposition.
**How to avoid:** Apply the same `display_name` "vs. " prefix logic from `query_top_openings_sql_wdl:250-260`. Implementation: in the service after attribution, if `(opening.ply_count % 2 == 1) != (finding.color == "white")`, prefix the display_name with "vs. ".
**Warning signs:** Frontend renders "London System" in a black-section finding without the "vs. " prefix.

### Pitfall 5: Float Division in HAVING Clause
**What goes wrong:** PostgreSQL integer division returns 0 for any ratio; SQLAlchemy's `count_filter / count` may not auto-cast.
**Why it happens:** Python's `/` operator becomes SQL's plain `/` which is integer-by-integer in PG.
**How to avoid:** Use explicit `cast(numerator, Float) / cast(denominator, Float)` or multiply by `1.0`. Verify the generated SQL via `print(stmt.compile(compile_kwargs={"literal_binds": True}))` during plan-check.
**Warning signs:** SQL HAVING returns no rows even when classification thresholds are clearly exceeded.

### Pitfall 6: openings.full_hash NULL
**What goes wrong:** `Opening.full_hash` is `BigInteger | None` (model line 21). A `WHERE full_hash IN (...)` won't match NULLs (correct behavior), but iterating returned rows assumes non-null `ply_count` ordering.
**Why it happens:** Model allows nulls; some legacy seed data may have them.
**How to avoid:** In the attribution query, filter `full_hash IS NOT NULL` defensively, then sort by `ply_count DESC` and take the first row per entry hash.
**Warning signs:** AttributeError on `opening.ply_count` when the row has all-None metadata.

### Pitfall 7: Empty Sections vs. Empty User
**What goes wrong:** A new user with 50 games returns four empty lists, frontend interprets as "service broken".
**Why it happens:** No findings cleared `n >= 20` and `>0.55` thresholds.
**How to avoid:** Per D-20, no per-user floor — empty sections are valid. The response is always 4 keys with possibly-empty lists. Phase 71 owns the empty-state copy.
**Warning signs:** Test treats empty 200 response as 400.

### Pitfall 8: Pgn Column Format on Opening Rows
**What goes wrong:** Trying to replay `Opening.pgn` to derive entry FEN, but format is space-separated SAN (e.g., `"e4 c6 Bc4"`) not standard PGN game text.
**Why it happens:** `seed_openings.py` writes a compact form.
**How to avoid:** Replay token-by-token: `for san in pgn.split(): board.push_san(san)`. Do not use `chess.pgn.read_game()` for `Opening.pgn`.
**Warning signs:** `chess.pgn.read_game` returns None for opening pgns.

## Runtime State Inventory

> Phase 70 is greenfield (new service, new endpoint, new schema artifact). It does NOT rename, refactor, or migrate existing data. Section omitted per the spec.

## Code Examples

### Reconstructing entry FEN from openings.pgn (D-25 fallback)
```python
# Source: pattern derived from app/services/openings_service.py imports + python-chess docs
import chess
from io import StringIO

def reconstruct_entry_fen(opening_pgn: str) -> str:
    """Replay an Opening.pgn (space-separated SAN) and return the resulting FEN."""
    board = chess.Board()
    for san in opening_pgn.split():
        board.push_san(san)
    return board.fen()
```

For findings whose entry doesn't match an `openings` row at any depth (D-23 unnamed-line fallback), the entry FEN must come from a different source. Options:

1. **Replay from a sample game.** The transition CTE can be extended to expose the SAN sequence via `array_agg(move_san) OVER (PARTITION BY game_id ORDER BY ply ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW)` — but that's expensive.
2. **Use `Opening.fen` directly when an attribution match exists.** Already a column on the model — preferred. For unnamed lines, fall back to picking any one `game_id` whose transitions include this entry_hash and running a second query to fetch its first-N SAN moves, then replay.

`[ASSUMED]` The exact unnamed-line entry-FEN fallback strategy. CONTEXT.md D-25 says "the entry FEN is reconstructed by replaying the entry-position SAN sequence from the start" but doesn't specify the SAN-sequence source for unnamed lines. The planner needs to pick: (a) walk the parent_hash chain through the openings table until a match is found, replay that opening's PGN; (b) issue a second SQL query to fetch one example game's SAN sequence up to the entry_ply; (c) skip unnamed-line findings entirely. Recommendation: (a) — D-23 already requires walking the parent chain for the opening name, so reuse the same chain to pick the deepest matched ancestor's PGN, then replay the user's continuation SAN tokens stored on the transition row.

### Attribution lookup (D-22)
```python
# Source: pattern derived from app/repositories/openings_repository.py:437 (query_transposition_counts)
async def query_openings_by_hashes(
    session: AsyncSession,
    full_hashes: list[int],
) -> dict[int, Opening]:
    """Return {full_hash: deepest matching Opening} for each input hash.

    "Deepest" = MAX(ply_count). Hashes with no match are absent from the dict.
    """
    if not full_hashes:
        return {}
    stmt = select(Opening).where(
        Opening.full_hash.is_not(None),
        Opening.full_hash.in_(full_hashes),
    )
    rows = await session.execute(stmt)
    by_hash: dict[int, Opening] = {}
    for opening in rows.scalars():
        existing = by_hash.get(opening.full_hash)
        if existing is None or opening.ply_count > existing.ply_count:
            by_hash[opening.full_hash] = opening
    return by_hash
```

### Sentry context capture (CLAUDE.md §Sentry)
```python
# Source: app/services/insights_service.py:162-169 (verified)
import sentry_sdk

try:
    rows_white = await query_opening_transitions(session, user_id, "white", ...)
    rows_black = await query_opening_transitions(session, user_id, "black", ...)
except Exception as exc:
    sentry_sdk.set_context(
        "opening_insights",
        {"user_id": user_id, "request": request.model_dump()},
    )
    sentry_sdk.capture_exception(exc)
    raise
```

### Alembic Migration Template (CONCURRENTLY)
```python
# Source: pattern from alembic/versions/20260327_093252_befacc0fce23 + Alembic docs
# CRITICAL: postgresql_concurrently=True requires running OUTSIDE a transaction.
"""add ix_gp_user_game_ply partial composite index for opening insights

Revision ID: <generated>
Revises: 6809b7c79eb3
Create Date: 2026-04-27 ...

Phase 70 (v1.13). Composite covering index on game_positions used by the
opening_insights_service transition aggregation. Column order
(user_id, game_id, ply) is LOAD-BEARING — it matches the LAG window's
PARTITION BY game_id ORDER BY ply within a per-user predicate, so PostgreSQL
streams rows directly from the index without a re-sort. INCLUDE keeps
full_hash and move_san on the leaf pages so query plans report
Heap Fetches: 0. Partial-on-ply<=17 keeps the index ~9% of table size.

DO NOT reorder these columns "for symmetry" with sibling ix_gp_user_*
indexes. Verified 2026-04-26 against dev DB:
  user 7 (Hikaru, 65k games / 5.7M positions): 2.0 s -> 816 ms
  user 28 (5,045 games / 336k positions):       65 ms (Index Only Scan)
"""
from alembic import op
import sqlalchemy as sa

revision: str = "<generated>"
down_revision: str | None = "6809b7c79eb3"
branch_labels: str | None = None
depends_on: str | None = None

# CONCURRENTLY requires running outside a transaction
def upgrade() -> None:
    with op.get_context().autocommit_block():
        op.create_index(
            "ix_gp_user_game_ply",
            "game_positions",
            ["user_id", "game_id", "ply"],
            unique=False,
            postgresql_concurrently=True,
            postgresql_where=sa.text("ply BETWEEN 1 AND 17"),
            postgresql_include=["full_hash", "move_san"],
        )


def downgrade() -> None:
    with op.get_context().autocommit_block():
        op.drop_index(
            "ix_gp_user_game_ply",
            table_name="game_positions",
            postgresql_concurrently=True,
            postgresql_where=sa.text("ply BETWEEN 1 AND 17"),
        )
```

`[CITED: Alembic docs https://alembic.sqlalchemy.org/en/latest/cookbook.html#run-alembic-operation-objects-inside-of-a-custom-script]` — the `autocommit_block()` context manager is the canonical way to run CONCURRENTLY operations.

`[ASSUMED]` This will be the FIRST migration in the project to use `postgresql_concurrently=True` (verified by grep — no prior migration uses it). Verify the production deployment path tolerates a CONCURRENTLY index build during `entrypoint.sh` migration step. Hikaru-scale build will take ~30-60 s on the prod hardware; backend startup blocks until done. If this is a concern, ship the migration in a maintenance window or add a pre-deploy step to apply it before image swap.

### `__table_args__` Update on GamePosition

```python
# app/models/game_position.py — add to existing __table_args__ tuple
Index(
    "ix_gp_user_game_ply",
    "user_id", "game_id", "ply",
    postgresql_where=text("ply BETWEEN 1 AND 17"),
    postgresql_include=["full_hash", "move_san"],
    # COLUMN ORDER IS LOAD-BEARING. The opening_insights_service transition
    # CTE uses LAG(full_hash) OVER (PARTITION BY game_id ORDER BY ply); this
    # ordering matches so PostgreSQL streams rows from the index without
    # a re-sort. Do NOT reorder for symmetry with ix_gp_user_full_hash etc.
    # See alembic migration <revision_id>_add_gp_user_game_ply_index.py
    # for the full rationale and verified perf numbers.
),
```

This declaration ensures `alembic revision --autogenerate` doesn't propose dropping the index in some future migration cycle.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Top-N entry × `query_next_moves` per entry (~40 sequential round-trips) | Single transition CTE per color (2 round-trips total) | 2026-04-26 redesign | 20× fewer queries; deep-line findings reachable |
| `n ≥ 10` evidence floor | `n ≥ 20` | 2026-04-26 (D-33) | Tighter signal-to-noise at the cost of dropping a few thin findings |
| Score classifier `(W + D/2) / n` | win_rate / loss_rate (separate) | 2026-04-26 (D-04) | Aligns exactly with `arrowColor.ts` board coloring |
| Bookmarks as algorithmic input | Bookmarks ignored by algorithm | 2026-04-26 (D-18) | Simpler discovery; Phase 74 uses bookmarks at UI layer only |

**Deprecated/outdated for this phase:**
- `query_next_moves` — works but unused; per-entry call pattern doesn't scale to 60+ entries within latency budget
- `query_top_openings_sql_wdl` for entry sourcing — superseded by transition aggregation
- `FilterContext` from `app/schemas/insights.py` — endgame-LLM-coupled; new `OpeningInsightsRequest` decouples (D-11)

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 9.0.3 (verified `tests/services/__pycache__/*.cpython-313-pytest-9.0.3.pyc`) + pytest-asyncio |
| Config file | `pyproject.toml` (project standard) |
| Quick run command | `uv run pytest tests/services/test_opening_insights_service.py -x` |
| Full suite command | `uv run pytest` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| INSIGHT-CORE-01 | Filter changes reshape findings; same filters → same ranking | unit | `uv run pytest tests/services/test_opening_insights_service.py::test_filter_equivalence` | ❌ Wave 0 |
| INSIGHT-CORE-02 | Transition CTE bounds (entry_ply 3..16 inclusive) | repo SQL | `uv run pytest tests/test_opening_insights_repository.py::test_entry_ply_boundaries` | ❌ Wave 0 |
| INSIGHT-CORE-02 | Bookmarks NOT consumed | unit | `uv run pytest tests/services/test_opening_insights_service.py::test_bookmarks_ignored` | ❌ Wave 0 |
| INSIGHT-CORE-03 | Single next-ply, no recursion | repo SQL | `uv run pytest tests/test_opening_insights_repository.py::test_single_next_ply` | ❌ Wave 0 |
| INSIGHT-CORE-04 | n=19 excluded, n=20 included | repo SQL | `uv run pytest tests/test_opening_insights_repository.py::test_min_games_floor` | ❌ Wave 0 |
| INSIGHT-CORE-05 | Strict `>0.55` boundary; severity at `≥0.60` | unit | `uv run pytest tests/services/test_opening_insights_service.py::test_classification_boundaries` | ❌ Wave 0 |
| INSIGHT-CORE-05 | Frontend constant alignment | consistency | `uv run pytest tests/services/test_opening_insights_arrow_consistency.py` | ❌ Wave 0 |
| INSIGHT-CORE-06 | Within-section dedupe by resulting_hash, deepest entry wins | unit | `uv run pytest tests/services/test_opening_insights_service.py::test_dedupe_deepest_entry` | ❌ Wave 0 |
| INSIGHT-CORE-06 | Cross-color same hash preserved as 2 findings | unit | `uv run pytest tests/services/test_opening_insights_service.py::test_cross_color_dedupe` | ❌ Wave 0 |
| INSIGHT-CORE-07 | Sort by (severity desc, n_games desc); per-section caps applied | unit | `uv run pytest tests/services/test_opening_insights_service.py::test_ranking_and_caps` | ❌ Wave 0 |
| INSIGHT-CORE-08 | Payload shape, hash str-form, severity Literal | router contract | `uv run pytest tests/test_insights_router.py::test_openings_endpoint_contract` | ⚠️ Extend existing |
| INSIGHT-CORE-09 | <1s response budget for ~2k-game user | manual | `uv run pytest tests/test_opening_insights_repository.py::test_query_perf_smoke` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `uv run pytest tests/services/test_opening_insights_service.py tests/test_opening_insights_repository.py -x`
- **Per wave merge:** `uv run pytest tests/test_opening_insights_repository.py tests/services/test_opening_insights_service.py tests/services/test_opening_insights_arrow_consistency.py tests/test_insights_router.py`
- **Phase gate:** Full suite green (`uv run pytest`) + `uv run ty check app/ tests/` + `uv run ruff check . && uv run ruff format --check .` before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `tests/services/test_opening_insights_service.py` — service unit tests over synthetic findings (12 test cases above)
- [ ] `tests/test_opening_insights_repository.py` — SQL contract tests for transition CTE against `seed_fixtures.py` portfolio
- [ ] `tests/services/test_opening_insights_arrow_consistency.py` — regex-parses `frontend/src/lib/arrowColor.ts` for `LIGHT_COLOR_THRESHOLD = 55` and `DARK_COLOR_THRESHOLD = 60`, asserts equality with Python module constants × 100
- [ ] Extend `tests/test_insights_router.py` with `test_openings_endpoint_contract` (auth required, payload shape, 4-section response always present)
- [ ] Synthetic test fixtures need positions at boundary plies (1, 2, 3, 4, 16, 17, 18) to verify the partial index `WHERE ply BETWEEN 1 AND 17` boundary AND the entry_ply BETWEEN 3 AND 16 boundary

### Critical Sample Dimensions (Nyquist)

These are the boundaries where bugs hide. Synthetic test data MUST include all of them.

| Dimension | Required samples |
|-----------|-----------------|
| Evidence floor | n=19 (excluded), n=20 (included), n=21 (included) |
| Loss rate boundary | loss_rate = 0.549 (neutral), 0.550 (neutral, strict `>`), 0.551 (minor weakness) |
| Loss rate severity tier | loss_rate = 0.599 (minor), 0.600 (major), 0.650 (major) |
| Win rate boundary | win_rate = 0.549, 0.550 (neutral), 0.551 (minor strength) |
| Win rate severity tier | win_rate = 0.599 (minor), 0.600 (major), 0.700 (major) |
| Entry ply | 2 (excluded), 3 (included), 16 (included), 17 (excluded) |
| Candidate ply (from CTE) | 1 (excluded — first ply of game), 4 (included), 17 (included), 18 (excluded) |
| Game boundary LAG | First-ply rows in different games — verify `entry_hash IS NULL` for `ply=0` and that LAG doesn't leak from prior game |
| Dedup collisions | Same `resulting_full_hash` from two different entries (transposition); two different colors hitting same hash |
| Color filter optimization | `color="white"` → only white_weaknesses + white_strengths populated (D-12 optimization) |
| Bookmark presence | User has bookmarks; verify findings unchanged whether bookmarks exist or not (D-18 verification) |
| Per-user empty | New user with <20 games per any candidate; all four lists return [] |
| ply_count parity | Black-section finding attributed to white-defined opening → `display_name` gets "vs. " prefix |

## Security Domain

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | yes | `Depends(current_active_user)` (FastAPI-Users) — already wired on every existing route |
| V3 Session Management | yes | JWT bearer transport via FastAPI-Users (already wired) |
| V4 Access Control | yes | All queries filter by `user_id` derived from authenticated session — never accept `user_id` from request body. Verify in router contract test that endpoint without auth returns 401 |
| V5 Input Validation | yes | Pydantic v2 `OpeningInsightsRequest` validates all input. `Literal` enums reject invalid `recency` / `opponent_strength` / `color` values. `elo_threshold: int` natural type-check |
| V6 Cryptography | no | No cryptographic operations in this phase |

### Known Threat Patterns for FastAPI + async SQLAlchemy

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| SQL injection via filter values | Tampering | SQLAlchemy `select()` with bound parameters — applies automatically. Never use `text()` with user input |
| User enumeration via response timing | Information Disclosure | Endpoint requires auth; user_id comes from session, not request — no enumeration vector |
| Authorization bypass (querying another user's data) | Elevation of Privilege | All queries pin `user_id == authenticated_user.id`; planner must add a router-level test that an authenticated user can only see their own findings |
| DoS via expensive queries | Denial of Service | Index-only scan caps the heaviest user at <1 s; rate-limiting at infra layer (already in place via FastAPI-Users middleware patterns) |

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| PostgreSQL 18 (dev DB) | All test runs | ✓ (when `docker compose -f docker-compose.dev.yml -p flawchess-dev up -d` is up) | 18 | None — required |
| python-chess | Service (FEN replay) | ✓ | 1.10.x | None |
| FastAPI / SQLAlchemy / asyncpg / pydantic-v2 / sentry-sdk | All layers | ✓ | per pyproject | None — already in lockfile |
| Alembic | Migration | ✓ | per pyproject | None |
| `uv` | Build tool | ✓ | per CLAUDE.md | None |

**No missing dependencies.** All required tools are already in the project's lockfile and dev environment.

## Risks / Pitfalls / Open Questions

### Risks

1. **Migration timing on production deploy.** This will be the first migration in the project to use `postgresql_concurrently=True`. The Hikaru-scale 5.7M-row partial index build will take ~30-60 s on prod hardware. The current `entrypoint.sh` runs `alembic upgrade head` before backend serves requests — so the deploy is non-blocking for users (backend just takes longer to come up) but the deploy.sh CI job will have a corresponding extra latency. Risk: deploy timeout. Mitigation: planner should pre-test the migration against `flawchess-prod-db` via SSH tunnel + a one-shot `alembic upgrade --sql` plan.

2. **Empty-string vs. None for unmatched openings.** D-23 says `opening_eco = ""` and `opening_name = "<unnamed line>"`. Frontend Phase 71 must handle these as empty-state strings, not `null`. Locked decision; just flagging for the planner so the schema doesn't drift to `Optional[str]`.

3. **`recency` Literal mismatch.** `app/services/openings_service.py::recency_cutoff()` accepts `"all"` (or None) for "no cutoff". The endgame `FilterContext` uses `"all_time"`. The planner needs to choose ONE for `OpeningInsightsRequest.recency` and document — recommendation: match `recency_cutoff()` accepted values (i.e., `"all" | "week" | "month" | ...` or `None`).

### Open Questions

1. **Unnamed-line entry-FEN reconstruction strategy.**
   - What we know: D-25 says entry FEN comes from SAN replay; D-23 says the parent-lineage walk is the attribution fallback.
   - What's unclear: When NO ancestor matches `openings`, what SAN sequence do we replay? CONTEXT.md leaves this to the planner.
   - Recommendation: Extend the transition CTE to `array_agg(move_san) OVER (PARTITION BY game_id ORDER BY ply ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW)` for one example game per surviving entry_hash, take the first occurrence, slice to `entry_ply`, and replay with python-chess. Adds one extra column to the CTE; well within the index-only-scan plan.

2. **Whether to skip the SQL query for unused color (D-12 optimization).**
   - What we know: D-12 permits skipping the query for the off-color when `color != "all"`, returning empty lists for those two sections. Saves ~50% latency.
   - What's unclear: Whether to ship this in Phase 70 or defer.
   - Recommendation: Ship it. It's a 3-line conditional in the service; saves real time for narrowed-view users.

3. **Whether the transition CTE should expose `parent_hash` for the lineage walk, or do it as a second query.**
   - What we know: D-23 says the lineage walk is "fine either way".
   - What's unclear: Single CTE vs. two queries.
   - Recommendation: Two queries. After the transition CTE returns surviving findings, issue ONE batched `SELECT * FROM openings WHERE full_hash IN (entry_hashes)` (D-22), then for any entry_hash that didn't match, walk back via the SAN sequence (already replayed for entry_fen) and probe the openings table at successive depths. Keeps the main aggregation query simple.

## Project Skills Hookup

`[VERIFIED: bash ls .claude/skills/]` — no project-local skills exist. The `db-report` and `benchmarks` skills mentioned in the research focus brief are not present in this repo.

CONTEXT.md §Performance Evidence already provides the threshold-default justification (n=20 binomial CI ~±22%) and perf budget (816 ms heaviest user, 65 ms median). No additional skill-driven inputs needed.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Exact SQLAlchemy 2.x cast syntax for HAVING float ratio | Pattern 2 | HAVING returns no rows; planner verifies on first SQL execution |
| A2 | `recency` Literal value list for `OpeningInsightsRequest` | Pattern 4 | Frontend filter-builder integration breaks; planner pins values to `recency_cutoff()` accepted set |
| A3 | Unnamed-line entry-FEN fallback uses parent-walk + SAN replay | Code Examples / Open Question 1 | Findings without an opening match return wrong entry_fen; planner formalizes |
| A4 | This is the first project migration using `postgresql_concurrently=True` | Risks | Deploy time regression; planner verifies against prod migration runner |
| A5 | `Opening.pgn` is space-separated SAN tokens (not full PGN game text) | Pitfall 8 | FEN replay returns wrong board; planner verifies by reading one row from `openings` table |
| A6 | Index `WHERE ply BETWEEN 1 AND 17` matches the partial query predicate exactly | Migration Template | PostgreSQL won't use the partial index; planner cross-checks generated SQL with `EXPLAIN` against actual outer filter |

A1, A2, A5 are easy 1-2 minute verifications during planning. A3 needs an explicit decision. A4, A6 need a dev-DB EXPLAIN check.

## Sources

### Primary (HIGH confidence)
- CONTEXT.md (`.planning/phases/70-backend-opening-insights-service/70-CONTEXT.md`) — D-01..D-33 locked decisions, performance evidence, canonical refs
- DISCUSSION-LOG.md — algorithm redesign rationale, perf verification numbers
- `app/repositories/query_utils.py:13` — `apply_game_filters` signature and behavior
- `app/repositories/openings_repository.py:359` — `query_next_moves` reference pattern
- `app/repositories/stats_repository.py:209` — `query_top_openings_sql_wdl` for win/loss/draw conditions and display_name parity
- `app/services/openings_service.py:78` — `recency_cutoff` accepted values
- `app/services/insights_service.py:122-169` — service orchestration shape, Sentry pattern
- `app/routers/insights.py` — router placement, `current_active_user` wiring (lines 36, 81, 115)
- `app/models/game_position.py` — schema; verified no `fen` column, BIGINT hash columns
- `app/models/opening.py` — `ply_count`, `pgn`, `full_hash` fields
- `frontend/src/lib/arrowColor.ts` — `LIGHT_COLOR_THRESHOLD = 55`, `DARK_COLOR_THRESHOLD = 60`, strict `>` semantics (lines 18-19, 50-61)
- `alembic/versions/20260327_093252_befacc0fce23_add_covering_index_for_endgame_queries.py` — INCLUDE pattern reference
- `CLAUDE.md` — §Critical Constraints, §Sentry, §Coding Guidelines, §Router Convention

### Secondary (MEDIUM confidence)
- `[CITED: PostgreSQL 16 docs https://www.postgresql.org/docs/16/functions-window.html]` — LAG semantics
- `[CITED: Alembic cookbook https://alembic.sqlalchemy.org/en/latest/cookbook.html]` — `autocommit_block()` for CONCURRENTLY

### Tertiary (LOW confidence)
- None — all claims verified against codebase or official docs.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all dependencies verified in pyproject + import grep
- Architecture: HIGH — CONTEXT.md locks every meaningful decision; perf verified against dev DB
- Pitfalls: HIGH — derived from existing codebase patterns and CONTEXT.md §canonical-refs
- Migration mechanics: MEDIUM — `autocommit_block` cited but no prior migration in this project uses it; planner verifies on dev DB first

**Research date:** 2026-04-26
**Valid until:** 2026-05-26 (stable backend stack; CONTEXT.md decisions locked)
