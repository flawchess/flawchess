# Phase 175: Board & Filter — Gem/Great Consumption - Research

**Researched:** 2026-07-16
**Domain:** Internal codebase consumption (backend query-time classification -> SQLAlchemy EXISTS filter; backend-to-frontend stored-data plumbing for an existing UI pattern). No new external library or service integration.
**Confidence:** HIGH (all findings are direct codebase reads with file:line citations; no web research was needed or performed — this phase composes existing, already-shipped internal patterns)

## Summary

Phase 175 has zero new-technology risk. Every piece it needs already exists in the
codebase from Phases 163/172 (frontend gem detection), 106-172 (flaw/tactic EXISTS
filter machinery), and 174 (the `game_best_moves` table + `classify_best_move`).
The work is entirely **plumbing**: read two already-computed backend values
(`maia_prob`, cp margin) through an existing per-ply assembly path onto an existing
schema, and replicate one pure Python classifier's logic as a SQLAlchemy boolean
expression inside an existing EXISTS-filter helper.

The single highest-value finding: **Phase 174's storage gate (`INACCURACY_DROP` =
0.05) is strictly looser than the classification gate (`MISTAKE_DROP` = 0.10)**
used inside `classify_best_move`. This means every ply that could *possibly*
classify as gem/great already has a row in `game_best_moves` (Phase 174 writes a
candidate row whenever `best_es - second_es >= 0.05`, and `classify_best_move`
only returns non-"neither" when that margin is also `>= 0.10`). Consequently, for
an **analyzed game's mainline**, the *absence* of a `game_best_moves` row for a ply
is itself authoritative "not a gem/great" — no live engine call is ever needed to
resolve a mainline ply of an analyzed game. This directly satisfies BOARD-01's "no
background sweep delay" success criterion by construction, not by racing a sweep to
finish before render.

The second highest-value finding: FILT-01's EXISTS filter **cannot** call the
Python `classify_best_move` function from SQL. It must express the same math —
Option-B mate-to-cp mapping, the Lichess winning-chances sigmoid, and the two
probability-ceiling comparisons — as a SQLAlchemy `case()`/`func.exp()` boolean
expression. This is a genuinely new but non-exotic construction; the codebase
already has one raw-SQL precedent for the identical sigmoid
(`app/services/canonical_slice_sql.py:704-708`, `800-801`, `816-817`, hardcoding
the same `0.00368208` Lichess K constant), which de-risks the approach but is in a
different subsystem (raw f-string CTEs) than the ORM `case()`/`and_()`/`exists()`
idiom `library_repository.py`/`query_utils.py` use everywhere else. The plan
should build the new SQL twin using the ORM idiom, importing the constants (not
re-declaring them), so a future threshold retune (GEMS-07 future work) changes one
Python module and both the board and the filter follow automatically.

**Primary recommendation:** For BOARD-01/BOARD-02, extend `EvalPoint` with
`best_move_tier: Literal['gem','great'] | None` and `maia_prob: float | None`
computed in `_build_eval_series` (`app/services/library_service.py`) via a new
`fetch_page_best_moves` repository function (mirrors `fetch_page_eval_positions`
exactly) joined by `(game_id, ply)`, calling the existing `classify_best_move`
directly (no new Python logic). For FILT-01, add a SQL-expression twin of
`classify_best_move` next to it in `app/services/best_move_candidates.py`, and
wire two new `has_gem`/`has_great` booleans through `apply_game_filters` exactly
like the existing `flaw_severity`/`tactic_families` params, producing a new
`best_move_exists_from_table()` helper that mirrors `flaw_exists_from_table()`.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Gem/great tier classification (single source) | API / Backend | — | `classify_best_move` (Python, already exists) is the one authoritative classifier; a SQL twin reproduces it for the filter, never a second independent implementation |
| EvalPoint stored-tier assembly | API / Backend | — | `_build_eval_series`/`fetch_page_best_moves` in `library_service.py`/`library_repository.py`; pure server-side join + classify, no client compute |
| Board marker rendering (gem/great glyphs) | Browser / Client | — | Board/move-list/popover/chart are pure rendering of `EvalPoint.best_move_tier`; zero client-side classification math for the stored (mainline, analyzed) path |
| Live-engine fallback classification (off-mainline / free-play / unanalyzed) | Browser / Client | — | `classifyGem`/new `classifyGreat` in `frontend/src/lib/gemMove.ts`, invoked only when no stored row exists for the position (D-01/D-03c) |
| Library Games filter (has-gem/has-great) | API / Backend | Database | Correlated EXISTS over `game_best_moves`, composed into `apply_game_filters()` alongside every other filter; no client-side filtering (breaks pagination/count semantics — see Pitfall 1) |
| `game_best_moves` storage | Database | — | Already shipped (Phase 174); this phase only reads it |

## Standard Stack

No new libraries, packages, or services. This phase is additive backend Python
(SQLAlchemy Core expressions, Pydantic schema fields) and additive frontend
TypeScript/React (existing icon/glyph/chart component patterns). No `npm install`
or `uv add` is needed.

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| SQL-expression twin of `classify_best_move` (case/func.exp in the EXISTS) | Raw `text()` SQL matching `canonical_slice_sql.py`'s literal-hardcoded sigmoid | Raw SQL text is the pattern the codebase already uses for this exact sigmoid elsewhere, but it hardcodes the constant as a literal (`0.00368208`) rather than importing it — accepts drift risk the ORM `case()`/`func.exp()` approach avoids by binding the actual Python constants as query parameters. Recommend the ORM approach for consistency with `library_repository.py`'s existing idiom (`case()`, `and_()`, `exists()` throughout) and single-source retunability. |
| Python-side EXISTS-eligibility + application-level filter | Fetch broader row set, run `classify_best_move` in Python, filter in application code | **Rejected** — `query_filtered_games` computes `matched_count` via a separate SQL COUNT and paginates via SQL LIMIT/OFFSET (`app/repositories/library_repository.py:1591-1651`+). Post-filtering in Python after the DB has already applied LIMIT/OFFSET would silently corrupt both the page contents and the total count. The filter predicate MUST live in SQL to compose with pagination (D-05a). |

## Package Legitimacy Audit

Not applicable — this phase installs no new backend or frontend packages (no
`pyproject.toml` or `package.json` changes). Skip the legitimacy gate.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| BOARD-01 | Analysis board shows gem/great markers from stored backend data (`EvalPoint` gains gem/great fields) | `EvalPoint`/`FlawMarker` schema location (`app/schemas/library.py:32-46`), `_build_eval_series` assembly point (`app/services/library_service.py:114-201`), new `fetch_page_best_moves` repository function pattern (mirrors `fetch_page_eval_positions`, `app/repositories/library_repository.py:1163-1194`), `classify_best_move` reuse (`app/services/best_move_candidates.py:129-156`) |
| BOARD-02 | `useGemSweep.ts` retired/demoted to free-play fallback; SEED-107 closes superseded | Full `useGemSweep.ts` read (dedicated-worker sweep-ahead mechanism); **critical finding**: Analysis.tsx ALSO has a second, separate live-per-node gem mechanism (`gemC1`/`gemGrading`/`gemByNode`, lines ~1528-1780) predating the sweep — BOTH must gate on "no stored row for this ply", not just the sweep hook (see Pitfall 2) |
| FILT-01 | "has gem"/"has great" Library filter via existing flaw/tactic EXISTS machinery | `apply_game_filters()` (`app/repositories/query_utils.py:94-286`), `flaw_exists_from_table()` pattern (`app/repositories/library_repository.py:677-750`), router/service/repository/frontend param-threading chain fully traced below |
</phase_requirements>

## Architecture Patterns

### System Architecture Diagram

```
┌─────────────────────────── BOARD-01/BOARD-02 (read path) ───────────────────────────┐
│                                                                                        │
│  GET /library/games/{id} or /library/games                                          │
│         │                                                                             │
│         v                                                                             │
│  library_service.get_library_game / get_library_games                                │
│         │                                                                             │
│         v                                                                             │
│  library_repository.fetch_page_eval_positions(game_ids)  ──┐                         │
│  library_repository.fetch_page_best_moves(game_ids) [NEW]  ─┤ batched, no N+1         │
│         │                                                    │                        │
│         v                                                    │                        │
│  library_service._build_card -> _build_eval_series           │                        │
│         │  for each GamePosition at ply P:                   │                        │
│         │    row = best_moves_by_ply.get(P)                  │                        │
│         │    tier = classify_best_move(row.*, mover_color_for_ply(P)) if row else None│
│         │    EvalPoint(..., best_move_tier=tier, maia_prob=row.maia_prob if row)      │
│         v                                                                             │
│  GameFlawCard.eval_series: EvalPoint[]  ──> HTTP response (FEN/tier only, no hashes)  │
│         │                                                                             │
│         v                                                                             │
│  frontend Analysis.tsx: renders EvalPoint.best_move_tier directly on the board,        │
│  move list, chart, popover — NO live Maia/Stockfish call for mainline plies of an     │
│  analyzed game (row present -> tier known; row absent -> tier is deterministically    │
│  null, since storage gate 0.05 <= classify gate 0.10, see Summary)                    │
│                                                                                        │
│  Fallback (off-mainline / free-play / unanalyzed game — NO game_best_moves rows       │
│  exist at all for these positions):                                                   │
│    useGemSweep.ts (demoted) + Analysis.tsx's live gemC1/gemGrading path               │
│    -> classifyGem / classifyGreat (frontend/src/lib/gemMove.ts)                       │
│                                                                                        │
└────────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────── FILT-01 (filter path) ────────────────────────────────────┐
│                                                                                        │
│  GET /library/games?has_gem=true&has_great=true&...other filters                     │
│         │                                                                             │
│         v                                                                             │
│  router: has_gem/has_great bool|None Query params                                    │
│         │                                                                             │
│         v                                                                             │
│  library_service.get_library_games -> library_repository.query_filtered_games        │
│         │                                                                             │
│         v                                                                             │
│  apply_game_filters(stmt, ..., has_gem=, has_great=, user_id=)                        │
│         │  if has_gem or has_great:                                                  │
│         │    stmt = stmt.where(best_move_exists_from_table(tiers=[...], user_id))     │
│         v                                                                             │
│  best_move_exists_from_table (NEW, mirrors flaw_exists_from_table):                  │
│    EXISTS (SELECT 1 FROM game_best_moves gbm                                         │
│            WHERE gbm.game_id = Game.id                                               │
│              AND player_only_gate(gbm.ply, Game.user_color)   -- D-04 user-scoping   │
│              AND best_move_tier_sql(gbm.*, Game.user_color) IN ('gem'/'great' subset))│
│         │                                                                             │
│         v                                                                             │
│  best_move_tier_sql (NEW, SQL twin of classify_best_move, in                         │
│  best_move_candidates.py): case()/func.exp() expression reproducing the Option-B      │
│  mate mapping + Lichess-K sigmoid + MISTAKE_DROP/GEM_MAIA_MAX_PROB/                   │
│  GREAT_MAIA_MAX_PROB comparisons, importing the SAME module constants (no re-decl)    │
│                                                                                        │
└────────────────────────────────────────────────────────────────────────────────────┘
```

### Recommended Project Structure

No new files/directories are required — every addition lands in an existing
module:

```
app/
├── services/best_move_candidates.py   # ADD: best_move_tier_sql() SQL-expression twin
├── repositories/library_repository.py # ADD: fetch_page_best_moves(); ADD: best_move_exists_from_table()
├── repositories/query_utils.py        # EXTEND: apply_game_filters(has_gem=, has_great=)
├── services/library_service.py        # EXTEND: _build_eval_series() joins best-move rows
├── schemas/library.py                 # EXTEND: EvalPoint.best_move_tier, EvalPoint.maia_prob
└── routers/library.py                 # EXTEND: GET /library/games has_gem/has_great Query params

frontend/src/
├── lib/theme.ts                       # ADD: GREAT_ACCENT constant
├── lib/greatGlyph.ts                  # NEW: mirrors gemGlyph.ts (one record, two consumers)
├── lib/gemMove.ts                     # ADD: classifyGreat + GREAT_MAIA_MAX_PROB (fallback-only)
├── components/icons/GreatMoveIcon.tsx # NEW: mirrors GemIcon.tsx (blue circle, white "!")
├── components/board/boardMarkers.tsx  # EXTEND: SquareMarker.great branch (mirrors .book)
├── components/analysis/GreatMoveBadge.tsx # NEW: mirrors GemMoveBadge.tsx
├── components/analysis/UnifiedMovePopover.tsx # EXTEND: isGreat prop (mirrors isGem)
├── components/analysis/VariationTree.tsx # EXTEND: MoveNode.great* fields, resolveMarkerIcon
├── lib/moveQuality.ts                  # EXTEND: MoveQuality |'great', colorForQuality case
├── types/library.ts                    # EXTEND: EvalPoint.best_move_tier, maia_prob
├── hooks/useGemSweep.ts                # DEMOTE: fallback-only gate + WR-06 useCallback fix
├── pages/Analysis.tsx                  # EXTEND: mainline reads EvalPoint.best_move_tier;
│                                        #         gemC1/gemGrading/useGemSweep gated to
│                                        #         "no stored row" positions only
├── hooks/useFlawFilterStore.ts         # EXTEND: FlawFilterState.hasGem/hasGreat
├── components/filters/FlawFilterControl.tsx # EXTEND: "Best Moves" toggle section
├── hooks/useLibrary.ts                 # EXTEND: buildLibraryParams has_gem/has_great
└── api/client.ts                       # EXTEND: libraryApi.getGames has_gem/has_great params
```

### Pattern 1: Batched per-page join, no N+1 (mirror `fetch_page_eval_positions`)

**What:** A new repository function fetches all `game_best_moves` rows for a page
of games in ONE query, grouped by `game_id`, exactly like `fetch_page_eval_positions`.
**When to use:** Both `get_library_game` (single-game path) and `get_library_games`
(list path) already batch-fetch `GamePosition` rows this way — the new function
slots into the exact same call sites.
**Example:**
```python
# Source: app/repositories/library_repository.py:1163-1194 (fetch_page_eval_positions, existing)
async def fetch_page_best_moves(
    session: AsyncSession,
    game_ids: Sequence[int],
) -> dict[int, dict[int, GameBestMove]]:
    """Batch-load GameBestMove rows for the given games, grouped by game_id then ply.

    Unlike fetch_page_eval_positions / fetch_page_game_flaws, this has NO user_id
    scoping — game_best_moves has no user_id column (candidacy is position-scoped,
    per app/models/game_best_move.py's own docstring). IDOR is not a concern here:
    the caller (get_library_game/get_library_games) already scopes game_ids to the
    authenticated user's own games before this is called.
    """
    if not game_ids:
        return {}
    stmt = select(GameBestMove).where(GameBestMove.game_id.in_(game_ids))
    rows = list((await session.execute(stmt)).scalars().all())
    result: dict[int, dict[int, GameBestMove]] = {gid: {} for gid in game_ids}
    for row in rows:
        result[row.game_id][row.ply] = row
    return result
```

### Pattern 2: Reuse `classify_best_move` directly for the board (no new Python logic)

**What:** `_build_eval_series` looks up the row for `pos.ply`, derives
`mover_color_for_ply(pos.ply)` (already exported from `best_move_candidates.py`),
and calls the existing classifier.
**Example:**
```python
# Source: app/services/best_move_candidates.py:50-53, 129-156 (existing, unmodified)
from app.services.best_move_candidates import classify_best_move, mover_color_for_ply

# Inside _build_eval_series's per-position loop (app/services/library_service.py:166-201):
best_row = best_moves_by_ply.get(pos.ply)  # dict[int, GameBestMove] for this game
best_move_tier: Literal["gem", "great"] | None = None
maia_prob_out: float | None = None
if best_row is not None:
    tier = classify_best_move(
        best_row.maia_prob,
        best_row.best_cp, best_row.best_mate,
        best_row.second_cp, best_row.second_mate,
        mover_color_for_ply(pos.ply),
    )
    if tier != "neither":
        best_move_tier = tier
    maia_prob_out = best_row.maia_prob
```
Note: `maia_prob` is surfaced even when the tier is "neither" is a **planner
decision** — D-03a says `maia_prob` feeds the popover detail ("~X% of rating-peers
would find this"), which only makes sense when a tier IS gem/great. Recommend
`maia_prob_out` is set only when `best_move_tier is not None`, mirroring how
`GemMoveBadge`'s `maiaProbability` prop is only meaningful alongside a real gem.

### Pattern 3: The SQL-expression twin of `classify_best_move` (the phase's one genuinely new construction)

**What:** A SQLAlchemy Core expression reproducing `classify_best_move`'s math,
for use inside the FILT-01 correlated EXISTS. This is new code, but every
sub-expression has a direct precedent in the codebase.
**When to use:** Inside `best_move_exists_from_table` (new function, mirrors
`flaw_exists_from_table`).
**Simplification available:** Because the EXISTS row set is already restricted to
`player_only_gate(gbm.ply, Game.user_color)` (i.e., only rows where the mover IS
the user), the sigmoid's sign flip can use `Game.user_color` directly instead of
re-deriving mover color from `ply % 2` — they are provably equal for any row that
survives the gate.
**Example:**
```python
# Source: sigmoid precedent — app/services/canonical_slice_sql.py:704-708 (raw SQL,
# hardcodes 0.00368208 literally); mate-Option-B precedent —
# app/services/best_move_candidates.py:92-104 (_eval_to_expected_score, Python).
# This is a NEW function combining both patterns as a SQLAlchemy Core expression,
# to be added to app/services/best_move_candidates.py alongside classify_best_move.
from sqlalchemy import case, func, literal
from sqlalchemy.sql.elements import ColumnElement

from app.services.eval_utils import LICHESS_K
from app.services.flaws_service import MATE_CP_EQUIVALENT, MISTAKE_DROP
from app.services.best_move_candidates import GEM_MAIA_MAX_PROB, GREAT_MAIA_MAX_PROB


def _es_sql(cp_col: Any, mate_col: Any, user_color_col: Any) -> ColumnElement[float | None]:
    """SQL twin of _eval_to_expected_score's Option-B mate mapping + Lichess sigmoid."""
    sign = case((user_color_col == "white", 1.0), else_=-1.0)
    mate_cp_equiv = case((mate_col > 0, float(MATE_CP_EQUIVALENT)), else_=-float(MATE_CP_EQUIVALENT))
    return case(
        (mate_col.isnot(None), 1.0 / (1.0 + func.exp(-LICHESS_K * sign * mate_cp_equiv))),
        (cp_col.isnot(None), 1.0 / (1.0 + func.exp(-LICHESS_K * sign * cp_col))),
        else_=literal(None),
    )


def best_move_tier_sql(
    maia_prob_col: Any,
    best_cp_col: Any, best_mate_col: Any,
    second_cp_col: Any, second_mate_col: Any,
    user_color_col: Any,
) -> ColumnElement[str | None]:
    """SQL twin of classify_best_move — returns 'gem' / 'great' / NULL.

    Must stay consistent with classify_best_move (the Python counterpart used by
    the board). If either is changed, update the other — same discipline as
    is_decided_lost / decided_lost_sql elsewhere in this codebase.
    """
    best_es = _es_sql(best_cp_col, best_mate_col, user_color_col)
    second_es = _es_sql(second_cp_col, second_mate_col, user_color_col)
    return case(
        (best_es.is_(None), literal(None)),
        (second_es.is_(None), literal(None)),
        ((best_es - second_es) < MISTAKE_DROP, literal(None)),
        (maia_prob_col <= GEM_MAIA_MAX_PROB, literal("gem")),
        (maia_prob_col <= GREAT_MAIA_MAX_PROB, literal("great")),
        else_=literal(None),
    )
```
Then `best_move_exists_from_table`:
```python
# Mirrors flaw_exists_from_table (app/repositories/library_repository.py:677-750)
def best_move_exists_from_table(tiers: Sequence[Literal["gem", "great"]]) -> ColumnElement[bool]:
    if not tiers:
        return true()
    tier_expr = best_move_tier_sql(
        GameBestMove.maia_prob,
        GameBestMove.best_cp, GameBestMove.best_mate,
        GameBestMove.second_cp, GameBestMove.second_mate,
        Game.user_color,
    )
    return exists(
        select(GameBestMove.ply)
        .where(
            GameBestMove.game_id == Game.id,
            player_only_gate(GameBestMove.ply, Game.user_color),  # D-04 user-scoping
            tier_expr.in_(tiers),
        )
    )
```
No new index is needed (Claude's Discretion item, resolved): `game_best_moves`'
primary key is `(game_id, ply)` (`app/models/game_best_move.py:35-38`), so the
correlated `WHERE game_best_moves.game_id = Game.id` predicate already leads with
the PK's first column — this is the same access pattern `flaw_exists_from_table`
relies on via `game_flaws`' PK. A supporting index would only help if the filter
frequently needed to scan ALL `game_best_moves` rows without a `game_id`
correlation, which it never does.

### Pattern 4: The "additive, mutually-exclusive marker field" pattern (clone for `great`)

**What:** `boardMarkers.tsx`'s `SquareMarker.book` field is the most recent
precedent for adding a third mutually-exclusive marker alongside `severity`/`gem`
(Phase 172, SEED-106 D-08) — this is the exact shape to clone for `great`.
**Example:**
```typescript
// Source: frontend/src/components/board/boardMarkers.tsx:28-43 (existing `book` field)
export interface SquareMarker {
  square: string;
  severity?: FlawSeverity;
  gem?: boolean;
  great?: boolean;  // NEW — mirrors `book`'s addition exactly
  book?: boolean;
  label?: string;
  labelColor?: string;
}
// SquareMarkerBadge: add a `marker.great` branch identical in shape to the
// existing `marker.book` branch (lines 143-158), using GREAT_GLYPH.color and a
// new GreatMoveIcon-equivalent inline SVG (circle + "!" glyph), reusing
// GEM_ICON_DIAMETER_RATIO verbatim (comment at boardMarkers.tsx:144 already
// establishes "reused verbatim, no new geometry constant" as the norm).
```

### Anti-Patterns to Avoid
- **Re-deriving mover color from ply parity inside the SQL filter when
  `Game.user_color` is already correlated and provably equal** (see Pattern 3) —
  adds an unnecessary second parity computation.
- **Filtering in Python after the DB query** — breaks `matched_count` and
  pagination (Pitfall 1). The predicate MUST be SQL.
- **A second independent gem/great constant set on the frontend without a
  documented "fallback-only" scope comment** — `gemMove.ts`'s `GEM_MAIA_MAX_PROB`
  already silently duplicates the backend's `GEM_MAIA_MAX_PROB` (both happen to be
  0.20 today, not code-linked); `classifyGreat`'s `GREAT_MAIA_MAX_PROB` must not
  repeat this without at least a comment cross-referencing
  `app/services/best_move_candidates.py` so a future retune isn't silently missed
  on one side (see Pitfall 4).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Gem/great classification math (board path) | A new Python or TS reimplementation of the sigmoid/threshold logic | `classify_best_move` (`app/services/best_move_candidates.py:129-156`), called directly | Already exists, already unit-tested (`tests/services/test_best_move_candidates.py`), already the single source of truth per GEMS-07/D-03b |
| User-scoped ply-parity gating | A new "is this the user's move" predicate | `player_only_gate` / `is_opponent_expr` (`app/repositories/query_utils.py:33-91`) | Single source of the ply-parity convention; a prior off-by-one bug lived exactly here (CLAUDE.md warns against scattering `ply % 2` math) |
| EXISTS-based game filtering | A parallel filter mechanism outside `apply_game_filters` | Extend `apply_game_filters()` + a new `best_move_exists_from_table` mirroring `flaw_exists_from_table` | D-05a explicitly requires this; `apply_game_filters` is documented as "the single implementation" (CLAUDE.md §Shared Query Filters) |
| Batched per-page DB reads | Per-game N+1 queries for `game_best_moves` | `fetch_page_best_moves`, one query for the whole page (Pattern 1) | Every existing Library data source (`fetch_page_game_flaws`, `fetch_page_eval_positions`, `fetch_page_analyzed_set`) already follows this batching discipline |
| Gem/great glyph color-vs-icon coupling | Inline hex colors + inline SVG scattered across components | `GREAT_GLYPH` record (mirrors `GEM_GLYPH`/`BOOK_GLYPH`) as the single source consumed by both the icon component and the board SVG | "One record, two consumers" is an established, twice-repeated pattern (`gemGlyph.ts`, `bookGlyph.ts`) specifically to prevent icon/board drift |

**Key insight:** Every "don't hand-roll" item in this phase has an existing,
already-battle-tested sibling to clone (gem -> great; book -> great marker slot;
flaw EXISTS -> best-move EXISTS). The risk in this phase is NOT inventing new
mechanisms — it's *silent divergence* from the sibling pattern (missing a surface,
missing a test, missing the SQL/Python consistency-comment discipline the
codebase uses everywhere else for these dual implementations).

## Runtime State Inventory

Not applicable — this is a schema-additive/consumption phase, not a
rename/refactor/migration phase. No existing runtime state changes identity.

## Common Pitfalls

### Pitfall 1: Filtering `game_best_moves` in Python instead of SQL breaks pagination
**What goes wrong:** `query_filtered_games` computes `matched_count` via a separate
COUNT query and pages results via SQL LIMIT/OFFSET
(`app/repositories/library_repository.py:1591-1660`+). If `has_gem`/`has_great`
were implemented by fetching a broader set of games and filtering in Python
(e.g., because `classify_best_move` "is easier to call from Python"), the reported
`matched_count` and the actual page contents would silently diverge from what SQL
LIMIT/OFFSET produced.
**Why it happens:** `classify_best_move` genuinely IS easier to call from Python —
the temptation is real.
**How to avoid:** The predicate must be a SQL boolean expression inside the
correlated EXISTS (Pattern 3), exactly like `flaw_exists_from_table`.
**Warning signs:** A test with >1 page of matching games where `matched_count`
disagrees with the actual count of gem/great games in the DB.

### Pitfall 2: Two distinct live gem mechanisms exist in Analysis.tsx — demoting only `useGemSweep.ts` misses the other one
**What goes wrong:** `useGemSweep.ts` is the Phase 172 SWEEP-AHEAD mechanism
(dedicated background workers, resolves plies ahead of the cursor). But
`Analysis.tsx` (lines ~1528-1780) ALSO runs a separate, older (Phase 163)
LIVE-AT-CURSOR mechanism — `gemC1` (Maia) -> `gemGrading` (Stockfish) ->
`gemByNode` — that resolves gem for the position the user is CURRENTLY viewing,
independent of the sweep. If the plan only demotes `useGemSweep.ts` to
fallback-only and leaves the live-at-cursor mechanism running unconditionally on
mainline plies, BOARD-01's "no background sweep delay" success criterion is only
half-satisfied: the user would still see the gem badge pop in AFTER a live
Maia+Stockfish round-trip on every navigation to a mainline ply, defeating the
purpose of the stored data.
**Why it happens:** The two mechanisms have similar-sounding names (`gemC1`/
`gemGrading`/`gemByNode` vs. `useGemSweep`'s `gemByPly`) and are easy to conflate.
**How to avoid:** The CONTEXT canonical refs explicitly flag both `classifyGem`
call sites (`Analysis.tsx` ~1233 the chart/bar display memo, and ~1745 the
live-at-cursor `gemByNode` resolution) as needing the switch to stored
`best_move_tier` for the mainline. Both `gemC1`'s existence gate
(`needParentGemGrade`, ~1592-1595) and `useGemSweep`'s `enabled` prop must be
extended with "AND no stored `best_move_tier` data exists for this position"
(equivalently: "AND the game is not analyzed, OR this ply is off-mainline / has no
`game_best_moves` row").
**Warning signs:** A live-browser UAT check where opening an already-analyzed game
still shows the gem badge appearing with a visible delay on a mainline ply.

### Pitfall 3: A stored `game_best_moves` row does NOT imply gem or great
**What goes wrong:** Phase 174 stores a candidate row whenever the write-time gate
passes (`best_es - second_es >= INACCURACY_DROP` = 0.05), but `classify_best_move`
only returns non-"neither" when the SAME margin clears `MISTAKE_DROP` = 0.10 at
read time — a strictly higher bar. A naive board implementation that treats "row
exists" as "show a marker" (skipping the `classify_best_move` call) would render a
false badge on every stored row with a margin in `[0.05, 0.10)`.
**Why it happens:** The two thresholds are close in value and easy to conflate;
"a candidate row exists" sounds like it should mean "candidate for a badge."
**How to avoid:** Always call `classify_best_move` (or its SQL twin) on the row's
raw floats; never infer the tier from row presence alone. `classify_best_move`'s
own docstring already states this is by design ("C2... else 'neither'").
**Warning signs:** A unit test seeding a row with margin exactly `0.07` should
produce `best_move_tier: null` on the EvalPoint — if it produces `'gem'`/`'great'`,
row-presence is being treated as sufficient.

### Pitfall 4: Frontend fallback classifier constants can silently drift from the backend's
**What goes wrong:** `frontend/src/lib/gemMove.ts`'s `GEM_MAIA_MAX_PROB = 0.2` is a
**hand-maintained** duplicate of `app/services/best_move_candidates.py`'s
`GEM_MAIA_MAX_PROB: float = 0.20` — they are not wired through the existing
`scripts/gen_flaw_thresholds_ts.py` generator (that generator only emits
`INACCURACY_DROP`/`MISTAKE_DROP`/`BLUNDER_DROP`/`MATE_CP_EQUIVALENT`/`LICHESS_K`
from `flaws_service.py`/`eval_utils.py` — NOT the gem/great ceilings, which live in
`best_move_candidates.py`). A future GEMS-07 threshold retune could update the
backend constant and silently leave the frontend's live-fallback classifier (used
for free-play/off-mainline positions) out of sync with the stored-data path.
**Why it happens:** This drift risk already exists today for `classifyGem` (has
existed since Phase 163, predates this phase) — Phase 175 will double it by adding
`classifyGreat`/`GREAT_MAIA_MAX_PROB` with the same hand-copied pattern unless
addressed.
**How to avoid:** Two options for the planner: (a) accept the existing precedent
(hand-copy `GREAT_MAIA_MAX_PROB = 0.5`, matching how `GEM_MAIA_MAX_PROB` was
already done) but add a code comment cross-referencing
`best_move_candidates.py` explicitly so a retune is at least discoverable via
grep; or (b) extend `scripts/gen_flaw_thresholds_ts.py` to also emit
`GEM_MAIA_MAX_PROB`/`GREAT_MAIA_MAX_PROB` from `best_move_candidates.py`, closing
the gap for both gem and great at once. Option (b) is more correct but touches a
generator script outside this phase's explicit file list — flag as a scope
question for the planner (see Open Questions).
**Warning signs:** `best_move_candidates.py`'s constants change but
`frontend/src/lib/gemMove.ts`'s do not, with no CI check catching the divergence
(unlike `flawThresholds.ts`, which CI diff-gates).

### Pitfall 5: `maia_prob` popover semantics for a "neither" ply
**What goes wrong:** If `EvalPoint.maia_prob` is populated whenever a
`game_best_moves` row exists (regardless of tier), the popover's "~X% of
rating-peers would find this" copy would render for a NON-gem/great ply that
merely happens to have a stored candidate row with margin `>= 0.05` — a confusing,
out-of-context statistic.
**Why it happens:** `EvalPoint`'s `maia_prob` and `best_move_tier` are two
independent optional fields; it's easy to populate one without gating on the
other.
**How to avoid:** Populate `maia_prob` only when `best_move_tier is not None` (see
Pattern 2's code example) — the planner should make this an explicit invariant
(and a test case).
**Warning signs:** A popover showing a Maia percentage stat with no gem/great
badge visible above it.

## Code Examples

### EvalPoint schema extension
```python
# Source: app/schemas/library.py:32-46 (existing EvalPoint, to extend)
class EvalPoint(BaseModel):
    ply: int
    es: float | None
    eval_cp: int | None
    eval_mate: int | None
    clock_seconds: float | None
    move_seconds: float | None
    best_move: str | None = None
    # NEW (BOARD-01, D-03): pre-classified tier from the authoritative backend
    # classifier. None when no candidate row exists OR the row classified as
    # "neither" (see Pitfall 3). Never a raw float shipped to the frontend for
    # the stored path — the board renders the tier string directly (D-03).
    best_move_tier: Literal["gem", "great"] | None = None
    # NEW (BOARD-01, D-03a): Maia policy probability, for the popover's "~X% of
    # rating-peers would find this" stat. Populated only alongside a non-None
    # best_move_tier (Pitfall 5).
    maia_prob: float | None = None
```

### TypeScript EvalPoint mirror
```typescript
// Source: frontend/src/types/library.ts:104-118 (existing EvalPoint, to extend)
export interface EvalPoint {
  ply: number;
  es: number | null;
  eval_cp: number | null;
  eval_mate: number | null;
  clock_seconds: number | null;
  move_seconds: number | null;
  best_move: string | null;
  // NEW (BOARD-01): pre-classified tier from the backend's classify_best_move.
  // null = no candidate row, or the row classified as "neither" — the board
  // must not distinguish these two cases (both render "no badge").
  best_move_tier: 'gem' | 'great' | null;
  // NEW (BOARD-01, D-03a): Maia probability for the popover stat line; null
  // unless best_move_tier is non-null.
  maia_prob: number | null;
}
```

### Router param addition (mirrors existing `severity`/`tactic_family` params)
```python
# Source: app/routers/library.py:72-88 (existing get_library_games signature, to extend)
@router.get("/games", response_model=LibraryGamesResponse)
async def get_library_games(
    ...,
    has_gem: bool | None = Query(default=None),
    has_great: bool | None = Query(default=None),
    ...,
) -> LibraryGamesResponse:
    ...
    return await library_service.get_library_games(
        ...,
        has_gem=has_gem,
        has_great=has_great,
        ...,
    )
```

### FlawFilterState extension (mirrors `severity`'s "empty/narrow" semantics)
```typescript
// Source: frontend/src/hooks/useFlawFilterStore.ts:9-45 (existing FlawFilterState, to extend)
export interface FlawFilterState {
  severity: ('blunder' | 'mistake')[];
  tags: FlawTag[];
  tacticFamilies: TacticFamily[];
  tacticOrientation: TacticOrientation;
  tacticDepthMin: number;
  tacticDepthMax: number;
  // NEW (FILT-01, D-05): independent boolean toggles, default false (off).
  // Both true = union semantics (OR), matching how the existing flaw-family
  // EXISTS unions severity/tags/tactics.
  hasGem: boolean;
  hasGreat: boolean;
}

export const DEFAULT_FLAW_FILTER: FlawFilterState = {
  severity: [], tags: [], tacticFamilies: [], tacticOrientation: 'either',
  tacticDepthMin: DEFAULT_TACTIC_DEPTH_VALUE.min, tacticDepthMax: DEFAULT_TACTIC_DEPTH_VALUE.max,
  hasGem: false, hasGreat: false,  // NEW
};

// isFlawFilterNonDefault must also gate on these (drives the filter-dot indicator):
//   filter.hasGem || filter.hasGreat || <existing checks>
```

## State of the Art

Not applicable in the "external ecosystem changed" sense — this section normally
tracks library/API deprecations. Nothing in this phase's dependency surface has
changed; it is 100% internal-pattern reuse. The one "old -> current approach" shift
worth naming:

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|---------------|--------|
| Gem detection: client-side Maia+Stockfish live sweep (Phase 172) | Gem/great detection: backend-stored, query-time classified (Phase 174/175) | This milestone (v2.4) | Removes device/load dependency for analyzed games; the sweep/live-at-cursor mechanisms become a documented fallback for the narrow no-stored-data case only |

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | The "eval-chart dot" surface named in CONTEXT.md D-02b most plausibly refers to `MovesByRatingChart.tsx`'s existing `colorForQuality`/`bucketKeyForQuality` gem case (`frontend/src/lib/moveQuality.ts:191-192,212`) rather than the Library `EvalChart.tsx` (per-ply eval-over-time chart), since the latter has no gem rendering today (verified via grep — its only "gem" substring hits are false positives from "engagement"). | Architecture Patterns, Pattern 4 area; Open Questions | If the planner intends the Library `EvalChart.tsx` instead, that would be a NEW capability (gem/great never appeared there before), not an extension — different LOC estimate and a different data source (FlawMarker doesn't carry tier today) |
| A2 | `EvalPoint.maia_prob` should be populated only when `best_move_tier` is non-null (Pitfall 5) — this is a researcher recommendation, not literally stated in CONTEXT.md D-03a. | Code Examples, Pitfall 5 | Low risk either way (cosmetic popover-copy concern), but worth the planner locking down explicitly to avoid an ambiguous "0.34 probability, no badge" popover state |
| A3 | No new database index is needed on `game_best_moves` for the FILT-01 EXISTS (the existing `(game_id, ply)` PK already leads with the correlating column). | Pattern 3 | If production query plans show a sequential scan under real data volume (unlikely given the PK leads with game_id), a supporting index would need to be added later — low risk, cheap to add post-hoc if measured necessary |

## Open Questions

1. **Does BOARD-02's "no background sweep delay" scope include the Phase-163 live-at-cursor gem mechanism (`gemC1`/`gemGrading`), or only `useGemSweep.ts` literally?**
   - What we know: REQUIREMENTS.md/ROADMAP.md name `useGemSweep.ts` specifically;
     CONTEXT.md's canonical refs also flag the `classifyGem` call site at
     `Analysis.tsx:~1745` (inside the live-at-cursor mechanism, not the sweep hook)
     as needing the stored-tier switch.
   - What's unclear: whether the live-at-cursor mechanism should be deleted
     entirely for analyzed-mainline plies (my read of D-01/D-03c: yes, both
     mechanisms gate on "no stored row"), or left running as an unconditional
     double-check.
   - Recommendation: Treat both mechanisms as in-scope for the "stored row exists
     -> skip live compute" gate (Pitfall 2). This is the interpretation that
     actually satisfies BOARD-01's "no background sweep delay" success criterion.
2. **Should `GREAT_MAIA_MAX_PROB` (frontend fallback) be added to the existing
   `scripts/gen_flaw_thresholds_ts.py` generator (sourcing from
   `best_move_candidates.py`), closing the pre-existing `GEM_MAIA_MAX_PROB` drift
   gap at the same time — or hand-copied matching the current precedent?**
   - What we know: the generator today only covers `flaws_service.py`/
     `eval_utils.py` constants, not `best_move_candidates.py`'s gem/great
     ceilings; `gemMove.ts`'s `GEM_MAIA_MAX_PROB` has been a hand-maintained
     duplicate since Phase 163.
   - What's unclear: whether extending the generator is in scope for this phase
     (touches a file (`scripts/gen_flaw_thresholds_ts.py`) not in CONTEXT.md's
     canonical refs) or a separate follow-up.
   - Recommendation: hand-copy for this phase (matches existing precedent,
     smallest diff), but add an explicit cross-reference comment in both
     `gemMove.ts` and `best_move_candidates.py` so the drift is at least
     discoverable; flag the generator extension as a candidate follow-up seed if
     the user wants it addressed now instead.
3. **Exact request-param encoding for the two filter toggles** (Claude's
   Discretion per CONTEXT.md): recommend two independent `bool | None` Query
   params (`has_gem`, `has_great`) at the HTTP boundary — mirrors `rated: bool |
   None` already on this exact endpoint — combined into a
   `tiers: list[Literal["gem","great"]]` internally before calling
   `best_move_exists_from_table` (mirrors `flaw_severity: Sequence[str]`'s
   set-membership shape).

## Environment Availability

Not applicable — no new external tool/service/runtime dependency. The phase only
touches already-running PostgreSQL (dev DB via
`docker compose -f docker-compose.dev.yml -p flawchess-dev up -d`, per CLAUDE.md)
and the existing FastAPI/Vite dev servers.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Backend framework | pytest 8.x + pytest-xdist (`-n auto`), per-run cloned Postgres DB (`tests/conftest.py`) |
| Frontend framework | Vitest (`npm test`) |
| Config file | `pyproject.toml` ([tool.pytest.ini_options]); `frontend/vitest.config.ts` |
| Quick run command (backend, targeted) | `uv run pytest tests/services/test_best_move_candidates.py tests/test_query_utils.py tests/services/test_library_service.py -x` |
| Quick run command (frontend, targeted) | `cd frontend && npm test -- --run gemMove FlawFilterControl useGemSweep` |
| Full suite command (backend) | `uv run pytest -n auto -x` |
| Full suite command (frontend) | `cd frontend && npm run lint && npm test -- --run` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| BOARD-01 | `EvalPoint.best_move_tier`/`maia_prob` populated correctly from a stored `game_best_moves` row via `classify_best_move` | unit | `uv run pytest tests/services/test_library_service.py -k eval_series -x` | ✅ file exists, ❌ new test cases needed |
| BOARD-01 | A stored row with margin in `[0.05, 0.10)` (INACCURACY_DROP <= margin < MISTAKE_DROP) produces `best_move_tier: null` (Pitfall 3) | unit | same file, new `test_stored_row_below_mistake_drop_yields_no_tier` | ❌ Wave 0 |
| BOARD-01 | Router/schema round-trip exposes the two new fields, no internal hash leakage | integration | `uv run pytest tests/test_library_router.py -k eval_series -x` | ✅ file exists, ❌ new cases needed |
| BOARD-02 | An analyzed game's mainline renders gem/great with no live Maia/Stockfish call | manual/UAT | live-browser check: open an analyzed game, confirm badge appears with the first paint, DevTools network/worker panel shows no Maia/Stockfish worker activity for mainline navigation | N/A (manual) |
| BOARD-02 | `useGemSweep` only activates for positions with no stored row (free-play/off-mainline/unanalyzed) | unit | `cd frontend && npm test -- --run useGemSweep` | ✅ file exists, ❌ new "fallback-only gate" cases needed |
| BOARD-02 | WR-06 stale-closure fix (`resolveCandidate` wrapped in `useCallback([])`) | unit/lint | existing `useGemSweep.test.ts` + `eslint-plugin-react-hooks` exhaustive-deps check | ✅ |
| FILT-01 | `has_gem=true` returns only games with >=1 qualifying user-move gem row | integration | `uv run pytest tests/test_library_router.py -k has_gem -x` | ❌ Wave 0 (mirrors existing `test_severity_filter_blunder_only`, `tests/test_library_router.py:742`) |
| FILT-01 | `has_gem`+`has_great` both true = union (OR), not AND | integration | same file, new `test_has_gem_and_has_great_union` | ❌ Wave 0 |
| FILT-01 | `has_gem` composes with `time_control`/`color`/`rated`/severity/tactic filters simultaneously (D-05a) | integration | `uv run pytest tests/test_query_utils.py -k best_move -x` (mirrors existing `test_apply_game_filters_*`) | ❌ Wave 0 |
| FILT-01 | `matched_count`/pagination stay correct with the new filter active (Pitfall 1) | integration | `uv run pytest tests/test_library_repository.py -k best_move_exists -x` (mirrors `flaw_exists_from_table` test pattern) | ❌ Wave 0 |
| FILT-01 | `best_move_tier_sql` agrees with `classify_best_move` across a fixture matrix (boundary values at exactly GEM_MAIA_MAX_PROB/GREAT_MAIA_MAX_PROB/MISTAKE_DROP) | unit | `uv run pytest tests/services/test_best_move_candidates.py -k tier_sql -x` | ❌ Wave 0 — this is the highest-value new test in the phase (proves the SQL twin doesn't drift from the Python original) |

### Sampling Rate
- **Per task commit:** targeted quick-run commands above (backend + frontend).
- **Per wave merge:** full backend suite (`uv run pytest -n auto -x`) + full
  frontend suite (`npm run lint && npm test -- --run`).
- **Phase gate:** Full suite green before `/gsd-verify-work`; additionally a
  live-browser UAT pass for BOARD-02's "no live engine call on mainline" claim
  (not mechanically provable by a unit test alone — DevTools inspection needed).

### Wave 0 Gaps
- [ ] `tests/services/test_best_move_candidates.py` — add `best_move_tier_sql`
  fixture-matrix tests (boundary agreement with `classify_best_move`)
- [ ] `tests/test_query_utils.py` — add `has_gem`/`has_great` composition tests
- [ ] `tests/test_library_repository.py` — add `best_move_exists_from_table`
  correlated-EXISTS tests (mirror the existing `flaw_exists_from_table` test
  block)
- [ ] `tests/test_library_router.py` — add `has_gem`/`has_great` HTTP-boundary
  tests (mirror `test_severity_filter_blunder_only`, line 742)
- [ ] `tests/services/test_library_service.py` — add `_build_eval_series`
  best-move-tier assembly tests, including the Pitfall 3 "row exists but
  classifies neither" case
- [ ] `frontend/src/hooks/__tests__/useGemSweep.test.ts` — add "gated to
  no-stored-row positions only" cases
- [ ] `frontend/src/lib/__tests__/gemMove.test.ts` — add `classifyGreat` tests
  (mirror existing `classifyGem` tests)
- [ ] `frontend/src/components/filters/__tests__/FlawFilterControl.test.tsx` —
  add hasGem/hasGreat toggle tests

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | Unchanged — existing `current_active_user` dependency on `/library/games` |
| V3 Session Management | no | Unchanged |
| V4 Access Control | yes | `game_best_moves` has no `user_id` column (position-scoped, per Phase 174 design), so IDOR protection relies ENTIRELY on the outer `Game.user_id == user_id` / `game_id.in_(game_ids)` scoping already present in `get_library_game`/`get_library_games`/`query_filtered_games`. `fetch_page_best_moves` (new) must never be called with an unscoped/unvalidated `game_ids` list — always the already-user-scoped list the existing callers pass to `fetch_page_eval_positions`. |
| V5 Input Validation | yes | `has_gem`/`has_great` as `bool \| None` FastAPI `Query` params — Pydantic/FastAPI rejects any non-boolean value at the HTTP boundary automatically (same as the existing `rated: bool \| None` param on this endpoint) |
| V6 Cryptography | no | N/A — no crypto surface in this phase |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Cross-user data disclosure via an unscoped `game_best_moves` join (the table has no `user_id`, unlike `game_flaws`) | Information Disclosure | The join/EXISTS must always correlate on `Game.id`/`Game.user_id` from an already-user-scoped outer query — verified present in every existing call site (`get_library_game`'s IDOR guard at `library_service.py:653-655`; `query_filtered_games`'s `Game.user_id == user_id` at `library_repository.py:1630`). No new endpoint is added in this phase, so no new attack surface beyond the two new boolean query params. |
| SQL injection via the new `best_move_tier_sql` expression | Tampering | All values are SQLAlchemy Core-bound (columns + Python float/string literals passed through `case()`/`func.exp()`/`literal()`), never raw string interpolation — consistent with every other expression in `query_utils.py`/`library_repository.py`. No `text()` SQL is introduced. |

## Sources

### Primary (HIGH confidence — direct codebase reads, file:line cited throughout)
- `app/services/best_move_candidates.py` — `classify_best_move`, `mover_color_for_ply`, `passes_inaccuracy_gate`, `pinned_elo_for_mover`, constants
- `app/models/game_best_move.py` — `GameBestMove` ORM model (PK, column types)
- `app/services/eval_apply.py:1785-1945` — `_build_best_move_candidates`/`_upsert_best_move_rows` (confirms storage gate = INACCURACY_DROP=0.05, the key finding)
- `app/services/flaws_service.py:46-56` — `INACCURACY_DROP`, `MISTAKE_DROP`, `BLUNDER_DROP`, `MATE_CP_EQUIVALENT`
- `app/services/eval_utils.py` — `LICHESS_K`, `eval_cp_to_expected_score` sigmoid definition
- `app/services/canonical_slice_sql.py:670-820` — raw-SQL sigmoid precedent (confirms `func.exp()`-style reproduction is a known, tolerated pattern in this codebase)
- `app/schemas/library.py:1-46` — `EvalPoint`/`FlawMarker` schema
- `app/services/library_service.py:1-260,374-460,631-830` — `_build_eval_series`, `_build_card`, `get_library_game`, `get_library_games`
- `app/repositories/library_repository.py:260-750,1097-1660` — `_tactic_orientation_pairs`, `build_flaw_filter_clauses`, `flaw_exists_from_table`, `fetch_page_*` functions, `query_filtered_games`
- `app/repositories/query_utils.py` — `apply_game_filters`, `is_opponent_expr`, `player_only_gate`
- `app/routers/library.py:1-140` — `GET /library/games` param wiring
- `frontend/src/lib/gemMove.ts`, `gemGlyph.ts`, `bookGlyph.ts` — classifier + glyph patterns
- `frontend/src/components/icons/GemIcon.tsx`, `components/board/boardMarkers.tsx`, `components/analysis/GemMoveBadge.tsx`, `UnifiedMovePopover.tsx`, `VariationTree.tsx`, `MaiaMoveQualityBar.tsx`, `MovesByRatingChart.tsx`, `lib/moveQuality.ts` — every existing gem-rendering surface
- `frontend/src/hooks/useGemSweep.ts`, `pages/Analysis.tsx` (gem sites ~1210-1780) — the two live gem mechanisms
- `frontend/src/hooks/useFlawFilterStore.ts`, `components/filters/FlawFilterControl.tsx`, `LibraryFilterPanel.tsx`, `MobileFilterDrawer.tsx`, `pages/library/GamesTab.tsx` — filter UI composition (LibraryFilterPanel/FlawFilterControl split, not literally FilterPanel.tsx as CONTEXT.md's canonical refs list — see note below)
- `frontend/src/hooks/useLibrary.ts`, `api/client.ts`, `types/library.ts` — query param threading
- `.planning/todos/pending/172-deferred-review-findings.md` — WR-01/03/05/06, IN-01..04 exact text
- `scripts/gen_flaw_thresholds_ts.py`, `frontend/src/generated/flawThresholds.ts` — the generated-constants precedent and its scope gap (Pitfall 4)

### Correction to CONTEXT.md's canonical refs
CONTEXT.md's canonical refs list `frontend/src/components/filters/FilterPanel.tsx`
and `MobileFilterDrawer.tsx` as places to mirror the flaw/tactic toggle pattern.
Direct inspection shows `FilterPanel.tsx` contains ZERO flaw/tactic code (it's the
game-metadata-only filter: time control, platform, rated, recency, opponent) —
the actual flaw/tactic toggle UI lives entirely in `FlawFilterControl.tsx`, which
`GamesTab.tsx` renders as a SEPARATE "Tags" strip panel/drawer (desktop
`GamesTab.tsx:325-349`, mobile `GamesTab.tsx:503-527`), independent of
`LibraryFilterPanel.tsx` (which composes `FilterPanel` + optionally
`FlawFilterControl`, but `GamesTab.tsx` passes `showFlawFilter={false}` to it and
renders `FlawFilterControl` on its own instead). The correct mirror target for the
two new gem/great toggles is `FlawFilterControl.tsx` (both its desktop and mobile
render call sites in `GamesTab.tsx`), not `FilterPanel.tsx`/`MobileFilterDrawer.tsx`
directly. `MobileFilterDrawer.tsx` itself is generic drawer chrome (header/footer
slots) with no filter-specific content at all.

### Secondary / Tertiary
None — no web research was performed for this phase (purely internal
architecture consumption; no external library, API, or ecosystem claim required
verification against a non-codebase source).

## Metadata

**Confidence breakdown:**
- Standard stack: N/A (no new stack) — HIGH (nothing to get wrong)
- Architecture: HIGH — every pattern traced to specific file:line, cross-checked against 2+ sibling implementations (gem/book glyph pattern, flaw/tactic EXISTS pattern)
- Pitfalls: HIGH — Pitfall 1/3/5 derived from direct arithmetic on the actual Phase 174 threshold constants (0.05 vs 0.10); Pitfall 2 derived from reading the full `Analysis.tsx` gem-related line range end to end; Pitfall 4 derived from diffing the generator script's actual coverage against `gemMove.ts`'s constant

**Research date:** 2026-07-16
**Valid until:** No expiry driver (internal codebase, not a fast-moving external ecosystem) — revalidate only if Phase 174's `game_best_moves` schema or `classify_best_move` signature changes before this phase is planned/executed.
