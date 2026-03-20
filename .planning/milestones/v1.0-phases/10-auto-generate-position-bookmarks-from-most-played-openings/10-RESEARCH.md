# Phase 10: Auto-generate position bookmarks from most played openings - Research

**Researched:** 2026-03-15
**Domain:** PostgreSQL aggregate queries, FastAPI service layer, React modal UI, react-chessboard v5 mini boards
**Confidence:** HIGH

## Summary

Phase 10 introduces two related but distinct capabilities: (1) a backend query that identifies the user's most-played positions within a ply range, applies a piece-filter heuristic, deduplicates against existing bookmarks, and returns candidate suggestions; (2) a generation modal in the frontend that previews each suggestion with a mini board, game count, opening name, and piece filter toggle, allowing the user to bulk-save selected candidates.

The phase also enhances existing bookmark cards with three improvements: inline mini board thumbnails (~80px), inline piece filter (match_side) control, and a new backend endpoint to update match_side (which requires recomputing `target_hash`).

All backend work follows the established pattern: new query in `analysis_repository` or a new `suggestion_repository`, service orchestration, new router endpoint, and Pydantic schemas. No new dependencies are needed on either side. The `react-chessboard` v5 `options` API already supports arbitrary `boardStyle` sizing, making mini boards straightforward without any additional library.

**Primary recommendation:** Implement as three plans: (1) backend suggestion endpoint + match_side update endpoint, (2) generation modal frontend, (3) bookmark card enhancements (mini board + inline piece filter). This keeps each plan independently testable and deployable.

## Standard Stack

### Core (all already in project)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| SQLAlchemy 2.x async | project standard | Aggregate GROUP BY query for most-played positions | Existing ORM layer |
| FastAPI 0.115.x | project standard | New router endpoints | Existing HTTP layer |
| Pydantic v2 | project standard | Request/response schemas | Existing validation layer |
| react-chessboard | 5.10.0 | Mini board thumbnails in modal and cards | Already used in ChessBoard.tsx |
| chess.js | 1.4.0 | Replay moves to compute FEN for mini boards | Already used in useChessGame |
| TanStack Query | project standard | New query hooks for suggestions | Existing data fetching layer |
| shadcn/ui | project standard | Dialog, Checkbox, ToggleGroup for modal | Existing component set |

### No New Dependencies Required
All required libraries are present. Mini boards use the existing `react-chessboard` v5 `options.boardStyle` with `width`/`height` set to `~80px`.

## Architecture Patterns

### Recommended Project Structure (additions only)
```
app/
├── repositories/
│   └── position_bookmark_repository.py   # add: get_existing_target_hashes(), update_match_side()
├── routers/
│   └── position_bookmarks.py             # add: GET /position-bookmarks/suggestions, PATCH /position-bookmarks/{id}/match-side
├── schemas/
│   └── position_bookmarks.py             # add: SuggestionResponse, MatchSideUpdateRequest
└── services/
    └── (no new service file needed — suggestions are pure DB aggregation)

frontend/src/
├── api/
│   └── client.ts                         # add: positionBookmarksApi.getSuggestions(), updateMatchSide()
├── components/
│   ├── position-bookmarks/
│   │   ├── PositionBookmarkCard.tsx      # extend: add mini board thumbnail + inline piece filter
│   │   ├── PositionBookmarkList.tsx      # unchanged
│   │   └── SuggestionsModal.tsx          # new: generation modal
├── hooks/
│   └── usePositionBookmarks.ts           # add: usePositionSuggestions(), useUpdateMatchSide()
└── types/
    └── position_bookmarks.ts             # add: PositionSuggestion, MatchSideUpdateRequest
```

### Pattern 1: Top-N Positions by Frequency Query
**What:** GROUP BY hash + COUNT, filtered to ply range 6-14, ordered by count DESC, limit 5 per color.
**When to use:** Computing bookmark suggestions.

```python
# Source: project analysis_repository.py patterns + SQLAlchemy 2.x docs
from sqlalchemy import func, select

async def get_top_positions(
    session: AsyncSession,
    user_id: int,
    color: str,            # "white" | "black"
    ply_min: int = 6,
    ply_max: int = 14,
    limit: int = 5,
    exclude_hashes: set[int] | None = None,
) -> list[tuple[int, int, int, int]]:
    """
    Returns list of (white_hash, black_hash, full_hash, game_count)
    for the most frequently reached positions in [ply_min, ply_max],
    filtered by user_color on joined games table, excluding already-bookmarked hashes.
    """
    stmt = (
        select(
            GamePosition.white_hash,
            GamePosition.black_hash,
            GamePosition.full_hash,
            func.count(GamePosition.game_id.distinct()).label("game_count"),
        )
        .join(Game, Game.id == GamePosition.game_id)
        .where(
            GamePosition.user_id == user_id,
            GamePosition.ply >= ply_min,
            GamePosition.ply <= ply_max,
            Game.user_color == color,
        )
        .group_by(
            GamePosition.white_hash,
            GamePosition.black_hash,
            GamePosition.full_hash,
        )
        .order_by(func.count(GamePosition.game_id.distinct()).desc())
        .limit(limit * 3)   # over-fetch before dedup filtering
    )
    rows = await session.execute(stmt)
    results = list(rows.all())

    # Exclude already-bookmarked positions
    if exclude_hashes:
        results = [r for r in results if r.full_hash not in exclude_hashes]

    return results[:limit]
```

**Critical note:** `game_positions` stores ALL plies. A single game can have the same full_hash at multiple plies (e.g. repeated position). Use `func.count(GamePosition.game_id.distinct())` not `func.count()` to count games, not position rows.

### Pattern 2: Piece Filter Heuristic
**What:** For each candidate position, compute the ratio of distinct `full_hash` values per `white_hash` (when playing white) or per `black_hash` (when playing black).

```python
# Heuristic: if distinct(full_hash) / count(game_id) is low, position is
# piece-placement-stable (opponent follows consistent patterns) -> suggest "mine"
# If ratio is high, opponent varies widely -> suggest "both" for broader matching.

async def suggest_match_side(
    session: AsyncSession,
    user_id: int,
    color: str,
    white_hash: int,
    black_hash: int,
) -> str:
    """
    Returns "mine" or "both" based on opponent variation ratio.
    color = "white" -> player's pieces are on white_hash, opponent on black_hash.
    Check how many distinct full_hashes exist for this white_hash:
    - few distinct full_hashes = opponent's pieces vary little = "mine" is meaningful
    - many distinct full_hashes = opponent varies widely = "both" may be better

    Threshold: if distinct_full / game_count <= 1.5, suggest "mine", else "both".
    """
    hash_col = GamePosition.white_hash if color == "white" else GamePosition.black_hash
    hash_val = white_hash if color == "white" else black_hash

    stmt = select(
        func.count(GamePosition.game_id.distinct()).label("game_count"),
        func.count(GamePosition.full_hash.distinct()).label("distinct_full"),
    ).where(
        GamePosition.user_id == user_id,
        hash_col == hash_val,
    )
    row = (await session.execute(stmt)).one()
    ratio = row.distinct_full / row.game_count if row.game_count > 0 else 1.0
    return "mine" if ratio <= 1.5 else "both"
```

**Note:** "mine" in frontend maps to `white_hash` (when color=white) or `black_hash` (when color=black) as `target_hash`. This is what `resolveMatchSide` already handles.

### Pattern 3: Reconstructing FEN from Moves for Mini Boards
**What:** Backend returns list of SAN moves; frontend replays them via `chess.js` to get FEN for the mini board. No FEN storage required for suggestions — the backend computes FEN during query.

Backend computes FEN by replaying moves from PGN of the first matching game up to the target ply. Simpler: store the FEN directly in the suggestion response (derived at query time by replaying a representative game's moves).

**Preferred approach:** Backend returns FEN directly in `SuggestionResponse`. Compute it by fetching one representative game's PGN and replaying to the representative ply where the hash first appeared.

```python
# In suggestion service:
# 1. For each top position, fetch one representative game_id + ply
# 2. Fetch that game's PGN
# 3. Replay to ply with python-chess to get board.board_fen()
# 4. Include in response

import chess.pgn, io

def fen_at_ply(pgn_text: str, target_ply: int) -> str:
    game = chess.pgn.read_game(io.StringIO(pgn_text))
    board = game.board()
    moves = list(game.mainline_moves())
    for move in moves[:target_ply]:
        board.push(move)
    return board.fen()  # full FEN for react-chessboard position prop
```

**Also:** SAN moves list for the suggestion must be computed to allow loading into the main board. Replay the same representative game to extract the SAN move list up to the target ply.

### Pattern 4: match_side Update Endpoint (recomputing target_hash)
**What:** When user changes `match_side` on a bookmark card, the backend must recompute `target_hash` from the stored `fen` and new `match_side`.

```python
# NEW endpoint: PATCH /position-bookmarks/{id}/match-side
# Schema: MatchSideUpdateRequest { match_side: str, color: str }
# Service: recompute target_hash from bookmark.fen using python-chess + Zobrist

from app.services.zobrist import compute_hashes
import chess

def target_hash_for_match_side(fen: str, match_side: str, color: str) -> int:
    board = chess.Board(fen)
    white_hash, black_hash, full_hash = compute_hashes(board)
    if match_side == "both":
        return full_hash
    if match_side == "mine":
        return white_hash if color == "white" else black_hash
    # "opponent"
    return black_hash if color == "white" else white_hash
```

**Critical note:** The frontend stores `match_side` as `"mine" | "opponent" | "both"` but the backend stores `white | black | full`. The PATCH endpoint must accept the frontend representation and do the resolution internally (using `color`), OR accept `ApiMatchSide` directly. Recommend accepting frontend `MatchSide` + `color` to keep backend consistent with existing schemas (the existing `PositionBookmarkCreate` already stores `match_side` in backend format `white|black|full` — see schema). Check the existing `PositionBookmarkCreate.match_side` field: it accepts `"mine" | "opponent" | "both"` (frontend format) based on the TypeScript type `PositionBookmarkCreate.match_side: 'mine' | 'opponent' | 'both'`.

**Wait — verify the actual stored format.** Looking at existing code: `PositionBookmarkCreate.match_side: str = "full"` (backend schema), and `PositionBookmarkResponse.match_side: str` returns `MatchSide` (frontend: `mine|opponent|both`). The DB stores `match_side` as `mine|opponent|both` (frontend format). The conversion to `white|black|full` happens in frontend via `resolveMatchSide()` only for API calls. Confirmed: `PositionBookmarkCreate.match_side` stores the user-facing `"mine" | "opponent" | "both"` value. So the PATCH endpoint takes `match_side: str` (mine|opponent|both) + `color: str`, resolves to backend hash column, computes new `target_hash`.

### Pattern 5: Mini Board in React (react-chessboard v5)
**What:** Read-only board thumbnail at ~80px using the existing `options` API.
**When to use:** In suggestion modal cards and bookmark cards.

```typescript
// Source: existing ChessBoard.tsx v5 options API + react-chessboard 5.10 docs
import { Chessboard } from 'react-chessboard';

function MiniBoard({ fen, flipped = false, size = 80 }: { fen: string; flipped?: boolean; size?: number }) {
  return (
    <div style={{ width: size, height: size }} data-testid="mini-board">
      <Chessboard
        options={{
          position: fen,
          boardOrientation: flipped ? 'black' : 'white',
          boardStyle: { width: size, height: size },
          darkSquareStyle: { backgroundColor: '#4a5568' },
          lightSquareStyle: { backgroundColor: '#718096' },
          // Disable interactivity for static thumbnails:
          // No onPieceDrop, no onSquareClick
        }}
      />
    </div>
  );
}
```

**Important:** react-chessboard v5 uses a single `options` object prop (not flat props). The `boardStyle` takes an inline style object with `width` and `height`. No `arePiecesDraggable=false` prop — interactivity is absent when `onPieceDrop` is not provided.

### Anti-Patterns to Avoid
- **Querying FEN columns instead of hashes:** The `game_positions` table has no `fen` column — hashes are the queryable surface. FEN is reconstructed from PGN replay.
- **COUNT(*) for game frequency:** Use `COUNT(DISTINCT game_id)` — a position appearing at multiple plies in the same game must count as one game.
- **Storing match_side as white|black|full in new code:** Existing bookmarks store `mine|opponent|both` (frontend format). Follow the same convention for consistency.
- **Fetching all game_positions rows in Python:** Push the GROUP BY into SQL — this table can have millions of rows.
- **N+1 FEN reconstruction:** Batch-fetch representative games for all top positions in one query, then replay in Python.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| FEN computation | Custom board serializer | `chess.Board.fen()` (python-chess) | Already used throughout codebase |
| Zobrist hash computation from FEN | Custom hash function | `app.services.zobrist.compute_hashes(chess.Board(fen))` | Already used in import pipeline |
| Board thumbnail rendering | SVG/Canvas renderer | `react-chessboard` v5 with small `boardStyle` | Already in project, handles all piece types |
| SAN move validation | Custom move parser | `chess.js` (frontend) / `chess.pgn` (backend) | Already used throughout |
| Modal dialog | Custom overlay | shadcn/ui `Dialog` | Already used in ImportModal, bookmark dialog |
| Checkbox/multi-select | Custom checkbox | shadcn/ui `Checkbox` | Already in UI library |

## Common Pitfalls

### Pitfall 1: COUNT(*) vs COUNT(DISTINCT game_id)
**What goes wrong:** Same position appears at ply 6 AND ply 8 in the same game. `COUNT(*)` returns 2, inflating the count.
**Why it happens:** `game_positions` stores every ply. A repeated position or a transposition shows up at multiple plies.
**How to avoid:** Always use `func.count(GamePosition.game_id.distinct())` in the GROUP BY query.
**Warning signs:** Suggestion game_count exceeds total games the user has played.

### Pitfall 2: Ply Range Includes Position 0 (Starting Position)
**What goes wrong:** Starting position (ply=0) would always be the most played, with 100% of games.
**Why it happens:** `game_positions` includes ply 0.
**How to avoid:** Filter `GamePosition.ply >= 6` in the suggestion query. The chosen range 6-14 targets opening transpositions (moves 3-7).

### Pitfall 3: target_hash BigInt Precision in JS
**What goes wrong:** Suggestion response returns `target_hash` as a JSON number — JS loses precision for values > 2^53.
**Why it happens:** IEEE-754 double precision.
**How to avoid:** `SuggestionResponse` must serialize `target_hash` as a string (same as `PositionBookmarkResponse`). Add `@field_serializer("target_hash")` returning `str(v)`.

### Pitfall 4: Deduplication Must Use the Correct Hash Column
**What goes wrong:** Deduplicating suggestions against existing bookmarks using `full_hash` when the existing bookmark uses `white_hash` (i.e., `match_side = "mine"` for white).
**Why it happens:** Logical duplicate: same white pieces position, already bookmarked with match_side=mine.
**How to avoid:** Deduplicate by `full_hash` (position identity). A position is "already bookmarked" if any existing bookmark's FEN resolves to the same `full_hash` regardless of match_side. Use `full_hash` as the deduplication key.

### Pitfall 5: react-chessboard v5 Options API
**What goes wrong:** Using flat props syntax from v4 (`arePiecesDraggable={false}`, `position={fen}` at top level).
**Why it happens:** v5 changed to a single `options` object.
**How to avoid:** All Chessboard props go inside `options={{ ... }}`. Reference `ChessBoard.tsx` for the correct pattern.

### Pitfall 6: PATCH /position-bookmarks/{id}/match-side Route Ordering
**What goes wrong:** FastAPI interprets `match-side` as an integer bookmark ID due to route ordering.
**Why it happens:** `/position-bookmarks/{id}` catches everything with an integer-like second segment.
**How to avoid:** Define `/position-bookmarks/reorder` before `/{id}` — existing code already does this. Add `/position-bookmarks/{id}/match-side` as a sub-path — this is safe because `{id}` is positional followed by a literal `/match-side`.

### Pitfall 7: Opening Name Requires Frontend Replay
**What goes wrong:** Backend returns SAN moves for the suggestion but opening name lookup happens in the frontend via `findOpening(moves)`.
**Why it happens:** Opening names are resolved via the `openings.tsv` prefix-match lookup in the frontend (`lib/openings.ts`).
**How to avoid:** Two options: (a) frontend computes opening name by calling `findOpening(moves)` for each suggestion after receiving the response; (b) backend uses `opening_lookup.py` to compute it server-side. Either works — backend already has `opening_lookup.py`. Using backend is simpler for the modal (no async per-suggestion lookup needed). Recommend backend computes opening name in `SuggestionResponse`.

### Pitfall 8: Performance — game_positions is the Hot Table
**What goes wrong:** Full table scan on `game_positions` for the GROUP BY query.
**Why it happens:** Without the right index, the planner may scan all rows.
**How to avoid:** The query filters by `user_id` first (covered by `ix_gp_user_full_hash`, `ix_gp_user_white_hash`, `ix_gp_user_black_hash`). Add `ply` range filter after `user_id`. Existing indexes on `(user_id, full_hash)` etc. cover the user_id prefix. The GROUP BY on all three hashes is a new query pattern — PostgreSQL will use the `user_id` index prefix for filtering then sort for grouping. For typical users (< 50k games, < 1M position rows), this will be fast enough without a new index.

## Code Examples

### Backend: Suggestion Repository Query Pattern
```python
# Source: based on analysis_repository.py patterns in this codebase
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.game import Game
from app.models.game_position import GamePosition

async def get_top_positions_for_color(
    session: AsyncSession,
    user_id: int,
    color: str,
    ply_min: int,
    ply_max: int,
    limit: int,
    exclude_full_hashes: set[int],
) -> list[tuple]:
    stmt = (
        select(
            GamePosition.white_hash,
            GamePosition.black_hash,
            GamePosition.full_hash,
            func.count(GamePosition.game_id.distinct()).label("game_count"),
        )
        .join(Game, Game.id == GamePosition.game_id)
        .where(
            GamePosition.user_id == user_id,
            GamePosition.ply.between(ply_min, ply_max),
            Game.user_color == color,
        )
        .group_by(
            GamePosition.white_hash,
            GamePosition.black_hash,
            GamePosition.full_hash,
        )
        .order_by(text("game_count DESC"))
        .limit(limit + len(exclude_full_hashes) + 10)  # over-fetch for post-filter
    )
    rows = list((await session.execute(stmt)).all())
    # Post-filter already-bookmarked positions
    filtered = [r for r in rows if r.full_hash not in exclude_full_hashes]
    return filtered[:limit]
```

### Backend: FEN Reconstruction for Suggestion
```python
# Source: existing zobrist.py hashes_for_game() + python-chess pgn module
import chess.pgn
import io

def fen_and_moves_at_ply(pgn_text: str, target_ply: int) -> tuple[str, list[str]]:
    """Returns (full_fen, san_moves_list) at the given ply."""
    game = chess.pgn.read_game(io.StringIO(pgn_text))
    if game is None:
        return chess.Board().fen(), []
    board = game.board()
    moves = list(game.mainline_moves())
    sans: list[str] = []
    for i, move in enumerate(moves[:target_ply]):
        san = board.san(move)
        board.push(move)
        sans.append(san)
    return board.fen(), sans
```

### Backend: Pydantic Schema for Suggestion Response
```python
# Source: existing PositionBookmarkResponse pattern in app/schemas/position_bookmarks.py
from pydantic import BaseModel, field_serializer

class PositionSuggestion(BaseModel):
    """A single auto-generated bookmark suggestion."""
    white_hash: str   # string for JS precision safety
    black_hash: str
    full_hash: str
    fen: str
    moves: list[str]          # SAN moves to reach this position
    color: str                # "white" | "black" — which color this suggestion is for
    suggested_match_side: str  # "mine" | "both" — heuristic suggestion
    game_count: int
    opening_name: str | None
    opening_eco: str | None

    @field_serializer("white_hash", "black_hash", "full_hash")
    def serialize_hash(self, v: int) -> str:
        return str(v)

class SuggestionsResponse(BaseModel):
    suggestions: list[PositionSuggestion]
```

### Frontend: Mini Board Component
```typescript
// Source: existing ChessBoard.tsx v5 options API in this codebase
import { Chessboard } from 'react-chessboard';

interface MiniBoardProps {
  fen: string;
  flipped?: boolean;
  size?: number;
}

export function MiniBoard({ fen, flipped = false, size = 80 }: MiniBoardProps) {
  return (
    <div style={{ width: size, height: size, flexShrink: 0 }} data-testid="mini-board">
      <Chessboard
        options={{
          position: fen,
          boardOrientation: flipped ? 'black' : 'white',
          boardStyle: { width: size, height: size },
          darkSquareStyle: { backgroundColor: '#4a5568' },
          lightSquareStyle: { backgroundColor: '#718096' },
        }}
      />
    </div>
  );
}
```

### Frontend: API Client Extension
```typescript
// Additions to positionBookmarksApi in api/client.ts
getSuggestions: () =>
  apiClient.get<SuggestionsResponse>('/position-bookmarks/suggestions').then(r => r.data),

updateMatchSide: (id: number, data: MatchSideUpdateRequest) =>
  apiClient.patch<PositionBookmarkResponse>(`/position-bookmarks/${id}/match-side`, data).then(r => r.data),

bulkCreate: (suggestions: PositionBookmarkCreate[]) =>
  Promise.all(suggestions.map(s => positionBookmarksApi.create(s))),
```

**Note on bulk save:** Use sequential `create` calls for each selected suggestion — no need for a dedicated bulk endpoint. The existing `POST /position-bookmarks` handles one at a time. Since the modal is user-initiated and creates at most 10 bookmarks, N serial requests is acceptable.

### Frontend: TanStack Query Hook for Suggestions
```typescript
// Addition to usePositionBookmarks.ts
export function usePositionSuggestions() {
  return useQuery({
    queryKey: ['position-bookmark-suggestions'],
    queryFn: positionBookmarksApi.getSuggestions,
    staleTime: 60_000,  // suggestions don't change often; re-fetch on window focus
  });
}

export function useUpdateMatchSide() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: MatchSideUpdateRequest }) =>
      positionBookmarksApi.updateMatchSide(id, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['position-bookmarks'] }),
  });
}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| react-chessboard flat props | Single `options` object | v5.x | All board usage must use options API — verified in ChessBoard.tsx |
| Manual FEN storage | Compute from PGN + python-chess | N/A (project pattern) | No FEN column on game_positions; always derived |

**Current project conventions to follow:**
- `match_side` stored as `mine|opponent|both` (frontend format) in `position_bookmarks` table
- `target_hash` stored as BIGINT, returned as string in responses, sent as string from frontend
- Session commit happens automatically via `get_async_session` yield — use `flush()` for within-request visibility
- Route ordering: literal segments before `/{id}` parameters — `GET /position-bookmarks/suggestions` must be defined before `GET /position-bookmarks/{id}` (note: currently no GET by ID endpoint, but keep in mind for future)

## Open Questions

1. **Ply range for suggestions: 6-14 fixed or configurable?**
   - What we know: User discussion specified ply 6-14
   - What's unclear: Whether to expose this as a query parameter for the API
   - Recommendation: Hardcode 6-14 as constants in the repository function; no API parameter needed for v1

2. **Piece filter heuristic threshold (1.5)**
   - What we know: The ratio of `distinct(full_hash) / game_count` approximates opponent variation. No empirical calibration done.
   - What's unclear: Whether 1.5 is the right threshold for typical chess player game sets
   - Recommendation: Use 1.5 as initial default; document it as a constant so it can be tuned later

3. **How many suggestions to show per color: 5 or variable?**
   - What we know: User discussion specified top 5 white + top 5 black = 10 total
   - What's unclear: Whether to always show exactly 10 or fewer if deduplication removes some
   - Recommendation: Return up to 5 per color after deduplication; show whatever remains (could be 0-5 each)

4. **Should the suggestions modal trigger automatically after import or be user-initiated?**
   - What we know: User discussion says "facilitate initial bookmark creation after importing games"
   - What's unclear: Auto-open vs. a prominent button
   - Recommendation: Add a "Suggest bookmarks" button in the Position bookmarks section; do not auto-open (avoids annoying returning users who already have bookmarks)

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest + pytest-asyncio (session scope) |
| Config file | `pytest.ini` / `pyproject.toml` |
| Quick run command | `uv run pytest tests/test_suggestion_repository.py -x` |
| Full suite command | `uv run pytest` |

### Phase Requirements -> Test Map
| ID | Behavior | Test Type | Automated Command | File Exists? |
|----|----------|-----------|-------------------|-------------|
| SUG-01 | get_top_positions returns at most N results, distinct game_id count | unit | `uv run pytest tests/test_suggestion_repository.py::test_top_positions_count -x` | Wave 0 |
| SUG-02 | Excludes already-bookmarked full_hashes from suggestions | unit | `uv run pytest tests/test_suggestion_repository.py::test_deduplication -x` | Wave 0 |
| SUG-03 | suggest_match_side returns "mine" for low variation, "both" for high | unit | `uv run pytest tests/test_suggestion_repository.py::test_heuristic -x` | Wave 0 |
| SUG-04 | PATCH match-side endpoint recomputes target_hash correctly | integration | `uv run pytest tests/test_bookmark_repository.py::test_update_match_side -x` | Wave 0 |
| SUG-05 | GET /position-bookmarks/suggestions returns valid SuggestionResponse | integration | `uv run pytest tests/test_position_bookmarks_router.py::test_get_suggestions -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/test_suggestion_repository.py tests/test_bookmark_repository.py -x`
- **Per wave merge:** `uv run pytest`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_suggestion_repository.py` — covers SUG-01, SUG-02, SUG-03
- [ ] `tests/test_position_bookmarks_router.py` — covers SUG-04, SUG-05 (new router test file)
- [ ] Existing `tests/test_bookmark_repository.py` — extend with `test_update_match_side` for SUG-04

*(Existing `tests/conftest.py` with `db_session` fixture covers all new repository tests without changes)*

## Sources

### Primary (HIGH confidence)
- Existing codebase: `app/repositories/analysis_repository.py` — GROUP BY + DISTINCT patterns verified
- Existing codebase: `app/services/zobrist.py` — `compute_hashes(board)` signature confirmed
- Existing codebase: `app/schemas/position_bookmarks.py` — `match_side` field format confirmed as `mine|opponent|both`
- Existing codebase: `frontend/src/components/board/ChessBoard.tsx` — react-chessboard v5 `options` API confirmed
- Existing codebase: `frontend/src/types/position_bookmarks.ts` — `PositionBookmarkCreate.match_side: 'mine' | 'opponent' | 'both'`
- `frontend/package.json` — react-chessboard 5.10.0, chess.js 1.4.0 confirmed

### Secondary (MEDIUM confidence)
- react-chessboard v5 docs: `boardStyle` prop accepts inline style with `width`/`height` — consistent with working ChessBoard.tsx usage

### Tertiary (LOW confidence)
- Piece filter heuristic threshold of 1.5 for `distinct(full_hash) / game_count` — no empirical data; reasonable starting point

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries already in project, versions confirmed from package.json
- Architecture: HIGH — follows established patterns from analysis_repository, position_bookmark_repository, existing router/schema conventions
- SQL query patterns: HIGH — GROUP BY with DISTINCT count mirrors existing analysis patterns
- Piece filter heuristic: LOW — threshold value (1.5) is a heuristic with no empirical calibration
- Frontend mini board: HIGH — react-chessboard v5 options API confirmed from working ChessBoard.tsx

**Research date:** 2026-03-15
**Valid until:** 2026-04-15 (stable dependencies, no fast-moving libraries involved)
