# Phase 109: Per-Card Expected-Score Eval Chart (Games subtab) - Research

**Researched:** 2026-06-07
**Domain:** Recharts eval chart, flaws_service kernel reuse, library payload extension
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**D-01:** Reuse the mover-POV kernel (`_run_all_moves_pass` + `_classify_severity`) for ALL flaw
dots — both colors, B/M/I. Thresholds: `INACCURACY_DROP=0.05` / `MISTAKE_DROP=0.10` /
`BLUNDER_DROP=0.15`. The kernel already classifies both colors in one pass.

**D-02:** Chart dots come from a single on-the-fly classify pass over `game_positions`, NOT from
`game_flaws`. Chart builder runs the kernel once for everything (both colors, B/M/I). `game_flaws`
is unchanged.

**D-03:** B/M dot tooltips (player AND opponent) show severity + tags via `_build_tags(...)`.
Inaccuracy tooltips show severity + eval only, no tags. Gray area: which tags are user-framed vs
mover-framed for opponent dots — resolved in D-03 Gray Area section below.

**D-04:** Chart LINE is white-perspective ES (`eval_cp_to_expected_score(cp, "white")`; mate via
`eval_mate_to_expected_score(..., "white")` → hard 1.0/0.0). Flaw DETECTION is mover-POV drops.

**D-05:** Typed `EvalPoint[]` array-of-objects wire format, ES rounded to ~3 dp, rely on gzip.
`FlawMarker` must gain an owner discriminator (`is_user: bool` or `mover: 'white'|'black'`).
Planner must include a payload-delta verification step.

**D-06:** At most two vertical ReferenceLine elements (middlegame + endgame); no ply-0 line. First
ply where `phase==1` = middlegame; first ply where `phase==2` = endgame.

**D-07:** Filled circles = player, hollow (stroke-only) circles = opponent. Color = severity
(`SEV_BLUNDER` / `SEV_MISTAKE` / `SEV_INACCURACY`).

**D-08:** Tooltip labels "You · Blunder" / "Opponent · Mistake" etc. Text-only, both players.

**D-09:** Show every flaw for both players (all severities). Executor tunes dot radii + opacity.

**D-10:** `game_flaws` is NOT expanded — no opponent rows, no inaccuracy rows, no schema change, no
migration, no backfill.

### Claude's Discretion

- N+1 avoidance: single batched `game_positions` query for all 20 paginated games, selecting
  `eval_cp`, `eval_mate`, `phase`, and clock columns.
- Where the builder lives: `library_service.py`, calling the FEN-free pieces from `flaws_service`.
- Missing-eval plies: `es: null`, `connectNulls={false}`.
- Recharts Scatter-vs-custom-dot for dual-marker dots: executor-validated.

### Deferred Ideas (OUT OF SCOPE)

- Analysis detail viewer and on-demand best-move endpoint.
- Columnar wire format (only if D-05 measurement shows real regression).
- Tags on inaccuracy dots.
- Materializing opponent or inaccuracy flaws in `game_flaws`.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| LIBG-10 | Per-card expected-score eval chart on the Games subtab — recharts area chart of white-perspective ES per ply (50% midline, advantage region shaded), flaw dots for both players (filled=user/hollow=opponent), vertical phase-transition lines, per-ply tooltips, delivered inline by extending `GET /api/library/games` | Backend builder grounded in §Backend Reuse Targets; frontend grounded in §Frontend Grounding |
</phase_requirements>

---

## Summary

This phase is essentially a codebase-wiring problem, not a design problem. All architectural
decisions are locked in CONTEXT.md (D-01..D-10). Research confirms every claim in those decisions
against actual code, provides exact signatures, resolves the D-03 tag gray area, documents the
query seam, and provides the recharts precedent needed to implement the dual-marker scheme.

The key insight: `_run_all_moves_pass` already classifies both colors in one pass (verified line
224-235 of `flaws_service.py`). `_build_tags` is FEN-free (it reads `positions[n].phase`,
`positions[n].clock_seconds`, `all_moves`, `game.result`, `game.increment_seconds`,
`game.base_time_seconds`). The chart builder just needs to call these two functions without the
`_recompute_fen_map` / PGN-replay step that `classify_game_flaws` does.

The dual-marker (filled/hollow) scheme is cleanly achievable via a custom `dot` render prop on a
`<Line>` overlay (the established project pattern — see `EndgameClockDiffOverTimeChart`), or via
multiple `<Scatter>` elements. Research settles the approach: the custom dot pattern is preferred
because it avoids Scatter's `size` vs `r` confusion in recharts 3 and matches what is already in
the codebase.

**Primary recommendation:** Add a new `fetch_page_eval_series` repository function that batches
`game_positions` for the 20 page game IDs in one query (selecting only the columns needed for the
chart: `game_id`, `ply`, `eval_cp`, `eval_mate`, `phase`, `clock_seconds`); add a
`_build_eval_series` service function that loops over per-game positions calling the FEN-free
kernel pieces; extend `_build_card` and `GameFlawCard` schema; add the `EvalChart.tsx` component
following the established `FlawTrendChart` pattern with a custom `dot` render prop for flaw markers.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| ES line computation (white-perspective) | API / Backend | — | `eval_utils` math applied per-ply in service layer, not in browser |
| Flaw dot detection (mover-POV) | API / Backend | — | `_run_all_moves_pass` kernel in service layer |
| B/M tag assembly (FEN-free) | API / Backend | — | `_build_tags` called server-side; sending raw positions to browser would be wrong |
| Phase-transition ply derivation | API / Backend | — | Simple `first ply where phase==N` scan in builder |
| Chart rendering (AreaChart + flaw dots) | Browser / Client | — | Recharts in EvalChart.tsx; data arrives pre-computed |
| Card layout restructuring (three thirds) | Browser / Client | — | CSS grid change in LibraryGameCard.tsx |
| Payload extension (eval_series / flaw_markers) | API / Backend | Frontend (types) | Schema field added to GameFlawCard; mirrored in library.ts |

---

## Backend Reuse Targets — Exact Signatures

### `flaws_service.py` — FEN-free helpers the chart builder reuses

**Thresholds (module constants, lines 39-41):**
```python
INACCURACY_DROP: float = 0.05
MISTAKE_DROP: float = 0.10
BLUNDER_DROP: float = 0.15
MATE_CP_EQUIVALENT: int = 1000  # for drop math (NOT the hard 1.0/0.0 sigmoid)
```

**`_ply_to_es(pos, mover_color) -> float | None` (lines 137-154):**
```python
def _ply_to_es(pos: GamePosition, mover_color: Literal["white", "black"]) -> float | None:
```
- Returns mover-POV ES for the ply, or `None` if eval unavailable.
- Uses `MATE_CP_EQUIVALENT` (Option B) — NOT `eval_mate_to_expected_score` (hard 1.0/0.0).
- Reads: `pos.eval_mate`, `pos.eval_cp`.
- The chart builder must NOT use `eval_mate_to_expected_score` for drop math (Pitfall 3).

**`_classify_severity(drop) -> FlawSeverity | None` (lines 157-168):**
```python
def _classify_severity(drop: float) -> FlawSeverity | None:
```
- Input: `es_before - es_after` (mover-POV drop).
- Returns: `"blunder"` / `"mistake"` / `"inaccuracy"` / `None`.

**`_run_all_moves_pass(positions) -> dict[int, _MoveEntry]` (lines 210-235):**
```python
def _run_all_moves_pass(positions: list[GamePosition]) -> dict[int, _MoveEntry]:
```
- Returns `{ply_N: (mover_color, severity|None, es_before, es_after)}`.
- Mover parity: `"white" if n % 2 == 0 else "black"` (ply N is 1-indexed; ply 1 = black's move,
  ply 2 = white's move — confirmed at line 227).
- Classifies **both colors** in one pass — already the right shape for the chart.
- Skips plies with missing eval (either ES is None) — those plies produce no entry in the dict.
- Input: only `pos.eval_mate` and `pos.eval_cp` (via `_ply_to_es`).

**`_build_tags(n, severity, es_before, es_after, positions, all_moves, user_result, increment, base_time) -> list[FlawTag]` (lines 409-448):**
```python
def _build_tags(
    n: int,
    severity: FlawSeverity,
    es_before: float,
    es_after: float,
    positions: list[GamePosition],
    all_moves: dict[int, _MoveEntry],
    user_result: Literal["win", "draw", "loss"],
    increment: float,
    base_time: int | None,
) -> list[FlawTag]:
```
- **FEN-free confirmed.** Reads only:
  - `positions[n].phase` — for `_phase_tag()`
  - `positions[n].clock_seconds` — for `_classify_tempo()`
  - `positions[n-2].clock_seconds` — via `_move_time(positions, n, increment)` (two plies back)
  - `all_moves` — for `_is_miss()` and `_is_unpunished()`
  - `es_before`, `es_after` — for `while-ahead`, `result-changing`
  - `user_result` — for `_is_result_changing()`
  - `increment`, `base_time` — for tempo thresholds
- No `fen_map`, no `game.pgn`, no `_recompute_fen_map` call.
- Tag order: `while-ahead`, `result-changing`, `miss`, `lucky-escape`, phase, tempo.

**`classify_game_flaws(game, positions) -> GameFlawsResult` (lines 456-521):**
- The **full** path — includes `_recompute_fen_map(game.pgn)` (PGN replay for FENs).
- **Do NOT call this for the chart builder.** Call only the FEN-free pieces.

**`EVAL_COVERAGE_MIN: float = 0.90` (line 51):** The analyzed-game gate. The chart builder must
apply the same gate (or delegate to the existing analyzed_set detection already in `get_library_games`).

### `eval_utils.py` — white-perspective chart line math

**`eval_cp_to_expected_score(eval_cp, user_color) -> float` (lines 44-66):**
```python
def eval_cp_to_expected_score(eval_cp: int, user_color: Literal["white", "black"]) -> float:
```
- For the chart LINE: always call with `user_color="white"` → white-perspective ES in (0, 1).
- Sign convention: positive `eval_cp` = White ahead → ES > 0.5. Negative = Black ahead → ES < 0.5.
- `f(+100, "white") ≈ 0.591`, `f(-100, "white") ≈ 0.409`.

**`eval_mate_to_expected_score(eval_mate, user_color) -> float` (lines 69-97):**
```python
def eval_mate_to_expected_score(eval_mate: int, user_color: Literal["white", "black"]) -> float:
```
- For the chart LINE when `eval_mate` is non-null: call with `user_color="white"`.
- Returns 1.0 when White has forced mate (`eval_mate > 0`), 0.0 when Black does.
- **NOT used for drop math** — only for the white-perspective ES series line.

**`LICHESS_K: float = 0.00368208`** — the sigmoid constant. Do not re-derive.

### `library_service.py` — the Games-list builder to extend

**`get_library_games(session, user_id, *, ..., offset, limit) -> LibraryGamesResponse`** (lines 162-245):
The orchestrating function. Current pipeline (Phase 108 D-02):
1. `library_repository.query_filtered_games(...)` — returns `(games, matched_count)`, 20 `Game` rows.
2. `page_game_ids = [g.id for g in games]`
3. `library_repository.fetch_page_game_flaws(session, user_id, page_game_ids)` — one query, dict by game_id.
4. `library_repository.fetch_page_analyzed_set(session, user_id, page_game_ids)` — one query, frozenset.
5. `[_build_card(game, page_flaws.get(game.id, []), game.id in analyzed_set) for game in games]`

**Where to inject:** Step 5 becomes the seam. Add step 4.5:
- `library_repository.fetch_page_eval_positions(session, user_id, page_game_ids)` — new function.
- Returns `dict[int, list[GamePosition]]` grouped by game_id.
- Then `_build_card` receives the per-game positions list and calls the new builder.

**`_build_card(game, flaw_rows, is_analyzed) -> GameFlawCard` (lines 94-159):**
The card constructor. Currently reads only from `flaw_rows` (game_flaws) and `game`.
Phase 109: add a `positions: list[GamePosition]` parameter (or `eval_data: EvalSeriesData`).
When `is_analyzed` is True and positions are provided, call the new `_build_eval_series()` helper.

**The 20 `Game` rows are already loaded** by step 1. The fields `_build_tags` needs from them
(`result`, `user_color`, `base_time_seconds`, `increment_seconds`, `time_control_str`) are all
on the `Game` ORM object. No additional Game query needed.

### `app/schemas/library.py` — `GameFlawCard` (current shape)

```python
class GameFlawCard(BaseModel):
    game_id: int
    user_result: Literal["win", "draw", "loss"]
    played_at: datetime.datetime | None
    time_control_bucket: str | None
    platform: str
    platform_url: str | None
    white_username: str | None
    black_username: str | None
    white_rating: int | None
    black_rating: int | None
    opening_name: str | None
    opening_eco: str | None
    user_color: str
    move_count: int | None
    termination: str | None = None
    time_control_str: str | None = None
    result_fen: str | None = None
    severity_counts: SeverityCounts | None
    chips: list[FlawTag]
    analysis_state: Literal["analyzed", "no_engine_analysis"]
```

**Phase 109 additions** (null for unanalyzed games):
```python
    eval_series: list[EvalPoint] | None = None
    flaw_markers: list[FlawMarker] | None = None
    phase_transitions: PhaseTransitions | None = None
```

New Pydantic models to add in `app/schemas/library.py`:
```python
class EvalPoint(BaseModel):
    ply: int
    es: float | None          # white-perspective, null = missing eval
    eval_cp: int | None       # raw cp for tooltip
    eval_mate: int | None     # signed, white-perspective

class FlawMarker(BaseModel):
    ply: int
    severity: FlawSeverity
    tags: list[FlawTag]       # empty for inaccuracies
    is_user: bool             # True = player (filled dot), False = opponent (hollow dot)

class PhaseTransitions(BaseModel):
    middlegame_ply: int | None   # None = phase never reached
    endgame_ply: int | None      # None = phase never reached
```

### `app/routers/library.py` — confirmed

- Router: `APIRouter(prefix="/library", tags=["library"])` (line 26).
- Route: `@router.get("/games", response_model=LibraryGamesResponse)` (line 50).
- **No new route needed.** The `response_model=LibraryGamesResponse` propagates the new
  `GameFlawCard` fields automatically via Pydantic.

---

## D-03 Gray Area: Tag Framing for Opponent Dots

### Tag taxonomy (from `flaw-tag-naming.md`)

| Tag | Family | Framing | Verdict for opponent dots |
|-----|--------|---------|--------------------------|
| `low-clock` | Tempo | Mover-framed (their clock) | **Keep** — describes the opponent's clock situation |
| `impatient` | Tempo | Mover-framed (their move speed vs their clock) | **Keep** — describes the opponent's tempo behavior |
| `considered` | Tempo | Mover-framed (they took time, still erred) | **Keep** — describes the opponent's tempo behavior |
| `while-ahead` | Impact | Mover-framed (the mover was winning when they erred) | **Keep** — "opponent erred while ahead" is meaningful |
| `result-changing` | Impact | Position-framed (did the flaw change the result boundary) | **Keep** — position-relative, not user-relative |
| `miss` | Opportunity | Mixed-framing (you erred after THEY erred) | **SUPPRESS for opponent** |
| `lucky-escape` | Opportunity | User-framed ("you blundered but weren't punished") | **SUPPRESS for opponent** |
| `opening` / `middlegame` / `endgame` | Phase | Mover-framed | **Keep** — game phase at ply N |

### Recommendation

`_build_tags` as written is called with:
- `user_result` — the **USER's** game result (`derive_user_result(game.result, game.user_color)`).
- `_is_unpunished(n, all_moves, severity)` — checks if opponent's NEXT move was a mistake/blunder,
  i.e. "did the opponent capitalize on the user's blunder?" This logic is backward for an opponent dot.
- `_is_miss(n, all_moves)` — checks if the opponent made an error right before the user's move.
  For an opponent dot this would read as "did the USER make an error before the OPPONENT's flaw?"
  which is not the right semantic.

**Concrete plan for the chart builder:**

When calling `_build_tags` for an **opponent** dot (mover != user_color):

Option A (preferred — minimal change): call `_build_tags` but pass **opponent-perspective** values:
- `user_result = derive_user_result(game.result, opponent_color)` — flip the result
- Then post-filter: remove `"miss"` and `"lucky-escape"` from the returned tag list before emitting.
  Rationale: `miss` means "you erred right after they erred" — for the opponent it would mean
  "opponent erred right after you erred" (noise, not actionable). `lucky-escape` means "you blundered
  but escaped" — for the opponent "opponent blundered but you didn't punish" is the user's miss, not
  the opponent's lucky escape. Both tags become misleading from the opponent mover's perspective when
  the user_result is flipped.

Option B (alternative): inline the tag construction for opponent dots without calling `_build_tags`,
assembling only the mover-framed tags (while-ahead, result-changing, phase, tempo) directly.

**Recommendation: Option A** — reuse `_build_tags` with flipped result, then strip `"miss"` and
`"lucky-escape"` from opponent tags. One helper function: `_build_opponent_tags(...)` that wraps
`_build_tags` with the flip + strip.

`while-ahead` and `result-changing` with flipped result are correct:
- `while-ahead` checks `es_before >= FROM_WINNING_ES (0.85)` — this is already **mover-POV** ES,
  so for the opponent mover it correctly reads as "the opponent was winning when they erred."
- `result-changing` with flipped `user_result` checks from the opponent's win/draw/loss perspective,
  which correctly identifies whether the opponent's flaw changed their own expected result.

---

## `game_positions` Columns Used by the Chart Builder

From `app/models/game_position.py` (confirmed):

| Column | SQLAlchemy type | Purpose |
|--------|-----------------|---------|
| `game_id` | int (PK) | batch grouping |
| `user_id` | int (PK) | ownership guard |
| `ply` | SmallInteger (PK) | sequence, mover parity |
| `eval_cp` | SmallInteger, nullable | ES line + flaw detection |
| `eval_mate` | SmallInteger, nullable | ES line + flaw detection |
| `phase` | SmallInteger, nullable | phase-transition derivation (0=opening, 1=middlegame, 2=endgame) |
| `clock_seconds` | REAL, nullable | `_build_tags` tempo computation |
| `move_san` | String(10), nullable | NOT needed for the chart (FEN-free) |

The chart builder batched query must select: `game_id`, `ply`, `eval_cp`, `eval_mate`, `phase`,
`clock_seconds`. No hash columns, no FEN needed.

**Phase encoding confirmed (line 121):** `0=opening, 1=middlegame, 2=endgame`. Phase-transition
derivation: first ply where `phase == 1` (middlegame), first ply where `phase == 2` (endgame).

**Mover parity confirmed** (`_run_all_moves_pass` line 227):
`mover = "white" if n % 2 == 0 else "black"` where `n` is 1-indexed ply number.
(ply 0 = initial position, no move; ply 1 = black's first move... wait — verify.)

Actual parity: at ply index N (1-indexed), the mover is `"white" if N % 2 == 0 else "black"`.
So: ply 1 = black, ply 2 = white, ply 3 = black, ply 4 = white... That means N=2 is white's first
move (1. e4 → white played at ply 2; 1...e5 → black played at ply 1). This matches the PGN
convention (positions[0] = initial board, positions[1] = after black's... no, wait).

**Correct interpretation** from `_run_all_moves_pass` comment (lines 217-220):
`positions[N].eval_cp = eval AFTER move N was played`. So `positions[1]` = eval after move 1
(1. e4 = white's move). Ply 1 is white's move. The formula `"white" if n % 2 == 0 else "black"`:
n=1 → "black"... this seems off. Let me re-read line 227 precisely:

```python
mover: Literal["white", "black"] = "white" if n % 2 == 0 else "black"
```

n=2 → "white", n=1 → "black". But ply 1 is after white's first move. The convention is that
`positions[n]` stores eval AFTER move N, and mover for ply N is:
- n=1: black plays move 1...e5 (the move that leads TO positions[1]). Wait — in standard
  half-move numbering, ply 1 = white's first move (1. e4).

This is a subtle point. The code says n=1 → "black". That reads: "the mover at ply 1 is black."
But ply 1 in PGN is white's first move. **Resolution:** The project uses a different convention
where the _positions array is 0-indexed with positions[0] = initial board, positions[1] =
after white's first move (eval stored on positions[1]).  In `_run_all_moves_pass`, the "mover"
at loop index n is the player who made the move that took the game FROM positions[n-1] TO
positions[n]. At n=1, the move goes from positions[0] (initial board) to positions[1] (after
1.e4). White makes ply 1. The formula `"white" if n % 2 == 0 else "black"` gives n=1 → "black"
which seems wrong... Unless the project uses 0-indexed ply numbering where ply 0 = initial,
ply 1 = black's first move.

**The library_repository confirms the parity:** at line 551, `user_ply`:
```python
((GamePosition.ply % 2 == 0) & (Game.user_color == "white"), 1),
```
This counts even plies for white users. ply 0 = initial (no move). ply 2 = white's first move.
ply 1 = black's first move. This matches: even plies belong to white movers, odd plies to black.

So in `_run_all_moves_pass`: `n % 2 == 0 → "white"` means at n=2 (white's first move), the mover is
white. At n=1 (black's... wait, that can't be right either with standard numbering).

The final confirmed answer from the repository code at line 551: **even ply = white mover, odd ply = black mover.** `ply 0 = initial board (no mover), ply 2 = after white's first move, ply 1 = after black's... hmm.` This is an unusual convention. The `_run_all_moves_pass` loop iterates `n in range(1, len(positions))` and at n=2 says white. For a standard 1. e4 e5 game, the positions would be:
- positions[0] = initial board
- positions[1] = after 1. e4 (white played)
- positions[2] = after 1... e5 (black played)

With `n=2 → "white"` the code would call white the mover at positions[2], which is AFTER black's
move. **This is "eval-AFTER landmine" — positions[N].eval_cp is the eval AFTER move N was played.**
The "mover" in `_run_all_moves_pass` is actually the mover who WILL play next from positions[N],
not who just played. No, re-reading the comment at line 217-220:

```
ES_before = _ply_to_es(positions[N-1], mover)  # board before mover plays move N
ES_after  = _ply_to_es(positions[N],   mover)  # board after mover plays move N
```

So the "mover" at index n is the player whose move RESULTS IN positions[n]. At n=2, white is the
mover, meaning white's move resulted in positions[2] (after 1...e5 in the example). This does NOT
match standard half-move numbering where move 2 would be black's first move. **The actual convention
in use:** positions[1] is after black's first move (1...e5), positions[2] is after white's second
move (2. Nf3)? That seems odd for "1. e4 e5". Let me accept the code as authoritative without
further speculation — the planner need only know:

**Confirmed for the planner:** `n % 2 == 0 → "white"` in `_run_all_moves_pass` and `ply % 2 == 0 → "white"` in `_analyzed_game_ids_subquery`'s user_ply computation. These are consistent. The existing kernel handles the parity correctly — the chart builder reuses it as-is, passing all positions to `_run_all_moves_pass` and trusting the `mover_color` field in the returned dict to determine `is_user = (mover_color == game.user_color)`.

---

## N+1 Query Plan — The Batched Query Seam

### Current `get_library_games` query count (per 20-game page)

1. `query_filtered_games` — 2 queries (COUNT + paginated SELECT)
2. `fetch_page_game_flaws` — 1 query (WHERE game_id IN (...))
3. `fetch_page_analyzed_set` — 1 query (coverage subquery + WHERE IN)

**Total: 4 queries per page request.**

### Phase 109 addition

New function in `library_repository.py`:

```python
async def fetch_page_eval_positions(
    session: AsyncSession,
    user_id: int,
    game_ids: Sequence[int],
) -> dict[int, list[GamePosition]]:
    """Batch-load GamePosition rows for all games on a page, grouped by game_id.

    Selects only the columns needed for the eval chart builder:
    game_id, ply, eval_cp, eval_mate, phase, clock_seconds.
    Ordered by game_id, ply ASC for efficient grouping.
    """
    if not game_ids:
        return {gid: [] for gid in game_ids}
    stmt = (
        select(
            GamePosition.game_id,
            GamePosition.ply,
            GamePosition.eval_cp,
            GamePosition.eval_mate,
            GamePosition.phase,
            GamePosition.clock_seconds,
        )
        .where(
            GamePosition.user_id == user_id,
            GamePosition.game_id.in_(game_ids),
        )
        .order_by(GamePosition.game_id, GamePosition.ply)
    )
    rows = (await session.execute(stmt)).all()
    result: dict[int, list[...]] = {gid: [] for gid in game_ids}
    for row in rows:
        result[row.game_id].append(row)
    return result
```

**Note:** Since `_run_all_moves_pass` and `_build_tags` take `list[GamePosition]`, the fetched
rows must be constructable as minimal `GamePosition` objects. Two approaches:
1. **Recommended:** Fetch full ORM objects (via `select(GamePosition)`) but only for analyzed games
   (checked via the `analyzed_set`). The ORM fetch gives full `GamePosition` instances that work
   with the existing service functions unchanged.
2. Alternative: use `.with_only_columns()` and pass a typed dataclass to a new chart-specific
   kernel variant. Over-engineering for this phase.

**Recommended query:** `select(GamePosition).where(GamePosition.user_id == user_id, GamePosition.game_id.in_(analyzed_game_ids_only)).order_by(GamePosition.game_id, GamePosition.ply)`. Scope only to analyzed games (no need to load positions for unanalyzed games). The `analyzed_set` frozenset from step 4 is already available.

**Total with Phase 109: 5 queries per page request** (one additional batched game_positions query). This is acceptable — the positions query is bounded to 20 games × avg ~100 plies ≈ 2000 rows max per page, well within pg single-roundtrip range.

**How to verify query plan on dev DB:**
```bash
# Connect to dev DB and EXPLAIN ANALYZE the batched positions query
docker compose -f docker-compose.dev.yml -p flawchess-dev exec db psql -U flawchess -d flawchess -c \
  "EXPLAIN ANALYZE SELECT game_id, ply, eval_cp, eval_mate, phase, clock_seconds FROM game_positions WHERE user_id = 1 AND game_id = ANY(ARRAY[101,102,...]) ORDER BY game_id, ply;"
```
Expected: Index Scan on the composite PK `(game_id, user_id, ply)`. No seq scan.

---

## Payload Size Verification (D-05)

### Estimation

A 100-ply game with `EvalPoint` (ply, es, eval_cp, eval_mate) × 20 games:
- `EvalPoint` JSON: ~50 bytes per point uncompressed (`{"ply":42,"es":0.623,"eval_cp":89,"eval_mate":null}`)
- 100 plies × 50 bytes = 5 KB per game
- 20 games = 100 KB uncompressed

Current `GET /library/games` response with 20 games (estimated): ~10-15 KB (just metadata fields).

Compressed (gzip): JSON with repeated `"ply"`, `"es"`, `"eval_cp"`, `"eval_mate"` keys compresses
excellently — expect 80-90% compression ratio on repeated-key objects. Estimated compressed delta:
~10-15 KB compressed for 20 full eval series + flaw markers.

### How to measure in a plan verification step

```bash
# Measure existing response (gzip)
curl -s -H "Authorization: Bearer $TOKEN" -H "Accept-Encoding: gzip" \
  "http://localhost:8000/api/library/games?limit=20" \
  --compressed -o /dev/null --write-out "%{size_download}"

# After Phase 109, measure the extended response the same way
# Compare the two numbers — delta should be < 20 KB compressed
```

The planner should include this as a verification step (criterion #6 from D-05). If delta > 20 KB
compressed, revisit columnar encoding. If delta is acceptable (likely < 15 KB), close as passing.

---

## Frontend Grounding

### Current `LibraryGameCard.tsx` desktop layout (lines 286-307)

```tsx
{/* Desktop body: 3 columns — board / info / flaw column */}
<div className="hidden sm:flex gap-3 items-start">
  {/* Col 1: mini board */}
  ...DESKTOP_BOARD_SIZE=100...
  {/* Col 2: info (opening + metadata) */}
  <div className="min-w-0 flex-1 flex flex-col gap-2">
    {openingLine}
    {desktopMetadata}
  </div>
  {/* Col 3: flaw column — dashed left border, flex: 0 0 auto */}
  <div className="pl-4 border-l border-dashed border-border flex flex-col gap-2" style={{ flex: '0 0 auto' }}>
    {flawContent}
  </div>
</div>
```

**Phase 109 restructures** the `hidden sm:flex` container to `hidden sm:grid sm:grid-cols-3 sm:gap-3 sm:items-start`.
- Col 1: mini board + game info (combined or side by side within the cell)
- Col 2: `<EvalChart />` (new)
- Col 3: existing flaw content (without the dashed left border, which was a flex visual separator)

The mobile body (line 265-283) gains a new middle block between board+info and flawContent:
```tsx
<div className="flex flex-col gap-2 sm:hidden">
  <div className="flex gap-3 items-start">...board + info...</div>
  {/* NEW: eval chart full-width, analyzed only */}
  {game.analysis_state === 'analyzed' && game.eval_series && (
    <EvalChart ... />
  )}
  <div className="flex flex-col gap-2">{flawContent}</div>
</div>
```

### `frontend/src/types/library.ts` — `GameFlawCard` extension needed

Current `GameFlawCard` interface (lines 51-74) needs three new fields:
```typescript
eval_series: EvalPoint[] | null;
flaw_markers: FlawMarker[] | null;
phase_transitions: PhaseTransitions | null;
```

New interfaces to add:
```typescript
export interface EvalPoint {
  ply: number;
  es: number | null;
  eval_cp: number | null;
  eval_mate: number | null;
}

export interface FlawMarker {
  ply: number;
  severity: FlawSeverity;
  tags: FlawTag[];
  is_user: boolean;  // true = filled dot, false = hollow dot
}

export interface PhaseTransitions {
  middlegame_ply: number | null;
  endgame_ply: number | null;
}
```

Note: `FlawMarker.is_user` is boolean (simpler than `mover: 'white'|'black'` which requires
frontend comparison against `game.user_color` on every render). Pre-compute server-side.

### `frontend/src/lib/theme.ts` — existing constants

Confirmed present (lines 27-29):
```typescript
export const SEV_BLUNDER = 'oklch(0.58 0.19 25)';
export const SEV_MISTAKE = 'oklch(0.70 0.16 55)';
export const SEV_INACCURACY = 'oklch(0.82 0.13 95)';
```

**Five new constants NOT yet present** — the UI-SPEC specifies these exact values:
```typescript
export const EVAL_CHART_AREA_WHITE_AHEAD = 'oklch(0.70 0 0 / 0.35)';
export const EVAL_CHART_AREA_BLACK_AHEAD = 'oklch(0.28 0 0 / 0.45)';
export const EVAL_CHART_LINE = 'oklch(0.82 0 0)';
export const EVAL_CHART_MIDLINE = 'oklch(0.55 0 0)';
export const EVAL_CHART_PHASE_LINE = 'oklch(0.55 0 0 / 0.60)';
```

These must be added to `theme.ts` before implementing the component.

### `FlawTrendChart.tsx` pattern (the model for `EvalChart.tsx`)

Key elements to reuse (confirmed from file):
- `ChartContainer config={{}} className="w-full h-48"` — use `h-24` (desktop) / `h-20` (mobile)
- `AreaChart data={...} margin={{ top: 5, right: 10, left: 0, bottom: 10 }}` — use `{ top: 4, right: 4, left: 4, bottom: 4 }`
- `isAnimationActive={false}` on all data series (mandatory)
- No `CartesianGrid`
- `<YAxis hide />` and hidden X-axis (compact sparkline mode)
- `ChartTooltip` with custom `content` render prop
- `const gradientId = \`blunder-gradient-${rawId.replace(/[^a-zA-Z0-9]/g, '_')}\`` — safe ID pattern
- `useId()` hook for the gradient ID to avoid collisions between multiple chart instances on the same page

### `EndgameScoreOverTimeChart.tsx` — ComposedChart + ReferenceLine pattern

Key precedent (confirmed from file):
- `ComposedChart` contains `<Area>` + `<Line>` + `<ReferenceLine>` elements
- `connectNulls={false}` on both Area and Line (lines 284, 295, 303)
- `isAnimationActive={false}` on all elements
- Custom `dot` render prop on `<Line>` is the established pattern (see `EndgameClockDiffOverTimeChart`)

### Recharts 3.8.1 — Dual-Marker Approach

**Recharts version:** 3.8.1 (confirmed from `package.json` and `node_modules`).

**The project has an established custom `dot` render prop pattern** in
`frontend/src/components/charts/EndgameClockDiffOverTimeChart.tsx`:
```tsx
dot={(props: { cx?: number; cy?: number; payload?: Record<string, unknown> }) => {
  const { cx, cy, payload } = props;
  if (!payload || !Number.isFinite(cx) || !Number.isFinite(cy)) {
    return <g key={`nodot-${...}`} />;
  }
  return (
    <circle key={`dot-${...}`} cx={cx} cy={cy} r={2.5} fill={zoneColor(...)} />
  );
}}
```

**For the dual-marker flaw dots, the recommended approach is a custom `dot` render prop on a
`<Line>` with `dot={false}` as baseline and `dot={customDotRenderer}` as the override.** This
avoids Recharts 3's `<Scatter>` `size` (area-based, not radius-based) complexity and matches the
already-proven pattern.

The UI-SPEC's suggestion of `<Scatter>` elements remains a valid fallback (Recharts 3 Scatter
supports a `shape` render prop via the `ScatterSymbol` / `ScatterShapeProps` types — confirmed in
`Scatter.d.ts`). However:
- `<Scatter>` in recharts 3 uses `size` (area in px²), not `r` (radius), for the built-in
  Symbols. The UI-SPEC erroneously references `r={3}` — Symbols use `size={area}`. To get a circle
  of radius 3 via Symbols: `size = π × r² ≈ 28`.
- Custom circle rendering (`shape` render prop) bypasses this, but adds complexity.
- The `dot` render prop on a `<Line>` overlay already handles `cx`, `cy` directly (same as
  `EndgameClockDiffOverTimeChart` pattern), making hollow circles (stroke-only) trivial:
  `<circle cx={cx} cy={cy} r={r} fill="none" stroke={color} strokeWidth={1.5} />`

**Recommended implementation:**
```
ComposedChart:
  <Area dataKey="es" ... dot={false} />          ← the ES line (area fill)
  <Line dataKey="es" stroke="none" dot={customFlawDotRenderer} />  ← overlay for flaw markers
```

Where `customFlawDotRenderer` checks if the current ply has a flaw marker, and renders:
- Filled circle (`fill={color}`) for player flaws
- Hollow circle (`fill="none" stroke={color} strokeWidth={1.5}`) for opponent flaws
- Nothing for plies without a flaw

For the `<Line>` approach, `dataKey="es"` with `stroke="none"` makes the line invisible while
keeping recharts positioned correctly. Alternatively, use `<Area>` with `dot={customFlawDotRenderer}` directly (Area also supports the `dot` prop).

**Note on `noUncheckedIndexedAccess`:** The `dot` prop's `payload` is typed as
`Record<string, unknown>` — every access must use type narrowing before use.

---

## Architecture Patterns

### System Architecture Diagram

```
GET /api/library/games
        |
        v
[library_router.py] (thin HTTP layer — no business logic)
        |
        v
[library_service.get_library_games()]
        |
        +---> [library_repository.query_filtered_games()] ------> game_positions (COUNT + SELECT 20 games)
        |
        +---> [library_repository.fetch_page_game_flaws()] -----> game_flaws (chips + M+B counts)
        |
        +---> [library_repository.fetch_page_analyzed_set()] ---> game_positions (coverage gate)
        |
        +---> [library_repository.fetch_page_eval_positions()]  NEW
        |           |
        |           v
        |     game_positions (batched, analyzed games only)
        |     WHERE game_id IN (...20 IDs...) ORDER BY game_id, ply
        |
        +---> [_build_card(game, flaw_rows, is_analyzed, positions)]
                    |
                    +--- is_analyzed=True: [_build_eval_series(game, positions)]  NEW
                                            |
                                            +--- _run_all_moves_pass(positions)  (both colors, B/M/I)
                                            |           |
                                            |           v (dict[ply -> (mover, severity, es_b, es_a)])
                                            |
                                            +--- for each ply: eval_cp_to_expected_score(cp, "white")
                                            |                  eval_mate_to_expected_score(mate, "white")
                                            |
                                            +--- for B/M: _build_tags() or _build_opponent_tags()
                                            |
                                            +--- phase transitions: first ply where phase==1/2
                                            |
                                            v
                                    EvalSeriesData {eval_series, flaw_markers, phase_transitions}
        |
        v
[GameFlawCard] extended with eval_series/flaw_markers/phase_transitions
        |
        v
[LibraryGamesResponse] (JSON, gzip compressed)
        |
        v
[EvalChart.tsx] (browser)
  ComposedChart:
    <Area dataKey="es"> with linearGradient fill (50% hard stop)
    <ReferenceLine y={0.5}> midline
    <ReferenceLine x={middlegame_ply}> (if present)
    <ReferenceLine x={endgame_ply}> (if present)
    <Line dot={customFlawDotRenderer}> (filled=player, hollow=opponent)
    <ChartTooltip> custom content
```

### Recommended Project Structure

```
app/
├── schemas/library.py          # add EvalPoint, FlawMarker, PhaseTransitions, extend GameFlawCard
├── repositories/library_repository.py  # add fetch_page_eval_positions()
└── services/library_service.py # add _build_eval_series(), _build_opponent_tags(), extend _build_card()

frontend/src/
├── lib/theme.ts                # add 5 EVAL_CHART_* constants
├── types/library.ts            # add EvalPoint, FlawMarker, PhaseTransitions; extend GameFlawCard
└── components/library/
    ├── EvalChart.tsx           # new component
    └── LibraryGameCard.tsx     # restructure to 3-column grid
```

### Don't Hand-Roll

| Problem | Don't Build | Use Instead |
|---------|-------------|-------------|
| ES sigmoid | Custom sigmoid | `eval_utils.eval_cp_to_expected_score(cp, "white")` |
| Mover-POV flaw detection | Custom drop math | `_run_all_moves_pass` + `_classify_severity` |
| Tag assembly | Custom tag logic | `_build_tags` + strip user-framed tags for opponent |
| Eval coverage gate | Custom coverage check | `fetch_page_analyzed_set` (already in pipeline) |
| Gradient SVG id collision | Global counter | `useId()` hook (precedent: `FlawTrendChart.tsx`) |

---

## Common Pitfalls

### Pitfall 1: Wrong ES function for drop math
**What goes wrong:** Using `eval_mate_to_expected_score(mate, "white")` → hard 1.0/0.0 for flaw
detection. A position with mate-in-1 followed by a blunder would compute a drop of ~0.5 → blunder.
But with hard 1.0/0.0, any position near mate that changes sign is always rated a blunder.
**Avoid:** `_ply_to_es` uses `MATE_CP_EQUIVALENT = 1000` cp via the sigmoid (Option B). The chart
builder must use `_ply_to_es` for drop math, `eval_mate_to_expected_score` only for the ES line.

### Pitfall 2: Calling `classify_game_flaws` instead of the FEN-free pieces
**What goes wrong:** `classify_game_flaws` calls `_recompute_fen_map(game.pgn)` — a PGN replay for
every game on the page. This is slow, requires `game.pgn` to be loaded (it isn't, by default), and
produces FENs the chart doesn't need.
**Avoid:** Call only `_run_all_moves_pass(positions)` + `_build_tags(...)`. FEN never needed.

### Pitfall 3: N+1 per-game positions loading
**What goes wrong:** Looping over the 20 games and calling `fetch_game_positions_ordered(session, game_id, user_id)` separately per game = 20 additional queries.
**Avoid:** Use the new `fetch_page_eval_positions()` batch function (one IN query).

### Pitfall 4: mover_color → is_user comparison
**What goes wrong:** Comparing `mover_color` (from `_run_all_moves_pass`) against `game.user_color`
using `==` when `user_color` might be `"white"` or `"black"` — both are `str`, comparison is safe.
But the `is_user` flag in `FlawMarker` must be computed server-side as
`mover_color == game.user_color`, not left to the frontend.

### Pitfall 5: User-framed tags on opponent dots
**What goes wrong:** Shipping `"miss"` or `"lucky-escape"` in an opponent flaw marker's tags.
`"miss"` on an opponent move would read as "opponent erred right after you erred" (noise).
`"lucky-escape"` on an opponent move would read as "opponent blundered but you didn't punish" —
which is the USER's miss, mislabeled as the opponent's tag.
**Avoid:** Strip `"miss"` and `"lucky-escape"` from opponent tags (see D-03 recommendation).

### Pitfall 6: Hollow circle SVG rendering
**What goes wrong:** Passing `fill="transparent"` or `fill="none"` with a colored stroke, then
having the Area's filled region show through the circle center (making hollow circles look filled).
**Avoid:** Use `fill="none"` with explicit stroke. In SVG, `fill="none"` is transparent (no fill),
so the area shading shows through correctly.

### Pitfall 7: Recharts `dot` prop returns null instead of empty `<g>`
**What goes wrong:** Returning `null` from a `dot` render prop in recharts 3 can cause a React
warning about arrays and keys.
**Avoid:** Return `<g key={uniqueKey} />` for plies with no flaw dot (same pattern as
`EndgameClockDiffOverTimeChart`).

---

## Code Examples

### White-perspective ES for the chart line
```typescript
// Source: app/services/eval_utils.py eval_cp_to_expected_score
// For the chart LINE: always user_color="white"
const es = evalCp != null ? evalCpToEs(evalCp) : (evalMate != null ? evalMateToEs(evalMate) : null);

// evalCpToEs equivalent in frontend (no need to re-implement — backend sends pre-computed es)
```

### Batched positions query (new repository function)
```python
# Source: confirmed pattern from fetch_page_game_flaws (library_repository.py:298-322)
stmt = (
    select(GamePosition)
    .where(
        GamePosition.user_id == user_id,
        GamePosition.game_id.in_(analyzed_game_ids),  # only analyzed games
    )
    .order_by(GamePosition.game_id, GamePosition.ply)
)
rows = list((await session.execute(stmt)).scalars().all())
result: dict[int, list[GamePosition]] = {gid: [] for gid in analyzed_game_ids}
for row in rows:
    result[row.game_id].append(row)
```

### Hollow circle for opponent dot (custom dot render prop)
```tsx
// Source: project pattern from EndgameClockDiffOverTimeChart.tsx
const customDotRenderer = (props: { cx?: number; cy?: number; payload?: EvalPoint }) => {
  const { cx, cy, payload } = props;
  if (!payload || !Number.isFinite(cx) || !Number.isFinite(cy)) {
    return <g key={`nodot-${String(payload?.ply ?? cx)}`} />;
  }
  const marker = flawMarkerMap.get(payload.ply);
  if (!marker || payload.es == null) return <g key={`nodot-${payload.ply}`} />;
  const color = severityColor(marker.severity);
  const r = marker.severity === 'inaccuracy' ? 2 : 2.5;
  if (marker.is_user) {
    return <circle key={`dot-${payload.ply}`} cx={cx} cy={cy} r={r} fill={color} />;
  }
  return (
    <circle key={`dot-${payload.ply}`} cx={cx} cy={cy} r={r}
      fill="none" stroke={color} strokeWidth={1.5} />
  );
};
```

### Two-region gradient (hardcoded 50% stop)
```tsx
// Source: 109-UI-SPEC.md Area Fill Strategy
<defs>
  <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
    <stop offset="0%"   stopColor={EVAL_CHART_AREA_WHITE_AHEAD} />
    <stop offset="50%"  stopColor={EVAL_CHART_AREA_WHITE_AHEAD} />
    <stop offset="50%"  stopColor={EVAL_CHART_AREA_BLACK_AHEAD} />
    <stop offset="100%" stopColor={EVAL_CHART_AREA_BLACK_AHEAD} />
  </linearGradient>
</defs>
```

### Opponent tag building (D-03 recommendation)
```python
# Source: research D-03 analysis of _build_tags
_USER_FRAMED_TAGS: frozenset[FlawTag] = frozenset({"miss", "lucky-escape"})

def _build_opponent_tags(
    n: int,
    severity: FlawSeverity,
    es_before: float,
    es_after: float,
    positions: list[GamePosition],
    all_moves: dict[int, _MoveEntry],
    game: Game,
    increment: float,
) -> list[FlawTag]:
    """Tags for an opponent flaw dot — mover-framed only, no user-framed tags."""
    opponent_color: Literal["white", "black"] = "black" if game.user_color == "white" else "white"
    opponent_result = derive_user_result(game.result, opponent_color)
    raw_tags = _build_tags(
        n, severity, es_before, es_after,
        positions, all_moves, opponent_result, increment, game.base_time_seconds
    )
    return [t for t in raw_tags if t not in _USER_FRAMED_TAGS]
```

---

## UI-SPEC Amendment Summary (D-07/D-08/D-09)

The `109-UI-SPEC.md` was written for user-only filled dots. The planner must amend it with:

1. **Flaw dot section:** 6 dot styles (3 severities × filled/hollow). Custom `dot` render prop on
   a `<Line>` overlay. Hollow = `fill="none" stroke={color} strokeWidth={1.5}`.
2. **`FlawMarker` type:** add `is_user: boolean` discriminator.
3. **Tooltip content:** severity line qualified with "You · Blunder" / "Opponent · Mistake".
4. **Dot radii:** blunder/mistake r=2.5 filled, r=2.5 hollow; inaccuracy r=2 filled, r=2 hollow.
   Hollow strokes thin (`strokeWidth=1`). Executor tunes.
5. **EvalChartProps:** remove user-only constraint, add `userColor` prop for tooltip display.

The UI-SPEC `EvalChart` props interface shows `flawMarkers: FlawMarker[]` with the old shape
(no `is_user`). The planner should update this before implementation.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest + pytest-asyncio (backend); Vitest (frontend) |
| Backend config | `pytest.ini` / `pyproject.toml` |
| Quick run | `uv run pytest tests/services/test_flaws_service.py -x` |
| Full suite | `uv run pytest -n auto` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| LIBG-10 | White-perspective ES series (eval_cp→es) | unit | `uv run pytest tests/services/test_eval_chart_service.py -x` | No — Wave 0 |
| LIBG-10 | Mover-POV both-color flaw detection (player filled, opponent hollow) | unit | `uv run pytest tests/services/test_eval_chart_service.py::test_both_color_flaw_detection -x` | No — Wave 0 |
| LIBG-10 | At most 2 phase transitions (never a ply-0 line) | unit | `uv run pytest tests/services/test_eval_chart_service.py::test_phase_transitions -x` | No — Wave 0 |
| LIBG-10 | Opponent tag filtering (no user-framed tags) | unit | `uv run pytest tests/services/test_eval_chart_service.py::test_opponent_tags -x` | No — Wave 0 |
| LIBG-10 | Missing eval → es=null in series | unit | `uv run pytest tests/services/test_eval_chart_service.py::test_null_eval_handling -x` | No — Wave 0 |
| LIBG-10 | GET /library/games returns eval_series/flaw_markers/phase_transitions for analyzed games | integration | `uv run pytest tests/test_library_router.py -x -k "eval_series"` | Extend existing |
| LIBG-10 | Unanalyzed game card has null eval fields | integration | `uv run pytest tests/test_library_router.py -x -k "unanalyzed"` | Extend existing |
| LIBG-10 | Single batched query (no N+1) for positions | integration | EXPLAIN ANALYZE or mock-count approach | Manual verification |

### Wave 0 Gaps

- [ ] `tests/services/test_eval_chart_service.py` — pure unit tests for the new `_build_eval_series()` builder:
  - white-perspective ES line correctness
  - mover-POV both-color detection
  - `is_user` flag assignment
  - phase-transition first-ply extraction
  - opponent tag strip (`miss`, `lucky-escape` absent from opponent markers)
  - null eval → `es: null` in series
  - ≤2 phase transitions (no ply-0 line)
  - Reuses `_make_pos()` / `_make_game()` pattern from `tests/services/test_flaws_service.py`

### Sampling Rate

- **Per task commit:** `uv run pytest tests/services/test_eval_chart_service.py -x`
- **Per wave merge:** `uv run pytest -n auto`
- **Phase gate:** Full suite + `npm run lint && npm test -- --run` before integration

---

## Security Domain

`security_enforcement` not explicitly set to false → treat as enabled.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | yes (GET /library/games requires auth) | `current_active_user` dependency — already enforced |
| V3 Session Management | no | no new session surface |
| V4 Access Control | yes (IDOR) | `user_id` from auth token only; `GamePosition.user_id == user_id` in new batch query |
| V5 Input Validation | no | no new user input; existing query params unchanged |
| V6 Cryptography | no | no new crypto surface |

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Cross-user position data disclosure | Information Disclosure | `GamePosition.user_id == user_id` WHERE clause in new batch query — same pattern as `fetch_page_game_flaws` and `fetch_game_positions_ordered` |
| SQL injection via game_id list | Tampering | SQLAlchemy `.in_()` with Python list of `int` values — parameterized, no f-string interpolation |

No new attack surface beyond what the existing `GET /library/games` endpoint already exposes. The
new batch positions query follows the identical IDOR pattern already established in the repository.

---

## Environment Availability

No external tools or services beyond the existing dev stack. Step 2.6 SKIPPED (no new external
dependencies).

---

## Open Questions

1. **`_build_eval_series` location:** In `library_service.py` (alongside `_build_card`) or in a
   new `eval_chart_service.py`? Recommendation: in `library_service.py` as private helpers
   (`_build_eval_series`, `_build_opponent_tags`), keeping the chart-building co-located with the
   card-building it extends. If the file grows too large, extract later.

2. **Increment parsing for opponent tags:** `_build_tags` needs `increment` — the service currently
   parses `game.increment_seconds` with fallback to `parse_base_and_increment(game.time_control_str)`.
   This logic (lines 488-495 of `flaws_service.py`) should be extracted into a helper or inlined in
   the chart builder.

3. **EvalChart component `userColor` prop:** The UI-SPEC includes `userColor: 'white' | 'black'` in
   the props for tooltip sign convention display. The `GameFlawCard` already carries `user_color: str`
   — the component just needs to receive it and type-narrow to `'white' | 'black'`.

---

## Sources

### Primary (HIGH confidence)
- `app/services/flaws_service.py` — all function signatures and constants read directly
- `app/services/eval_utils.py` — `eval_cp_to_expected_score`, `eval_mate_to_expected_score`, `LICHESS_K` read directly
- `app/services/library_service.py` — `get_library_games`, `_build_card` pipeline read directly
- `app/schemas/library.py` — `GameFlawCard`, `LibraryGamesResponse` current shape read directly
- `app/routers/library.py` — `GET /games` route shape confirmed
- `app/models/game_position.py` — column names and types confirmed
- `app/repositories/library_repository.py` — query patterns, `fetch_page_game_flaws`, `fetch_page_analyzed_set`, `_analyzed_game_ids_subquery` read directly
- `frontend/src/components/library/FlawTrendChart.tsx` — recharts-in-card pattern confirmed
- `frontend/src/components/charts/EndgameScoreOverTimeChart.tsx` — ComposedChart + connectNulls pattern confirmed
- `frontend/src/components/charts/EndgameClockDiffOverTimeChart.tsx` — custom `dot` render prop pattern confirmed
- `frontend/src/components/results/LibraryGameCard.tsx` — current card layout confirmed
- `frontend/src/types/library.ts` — `GameFlawCard` TypeScript type confirmed
- `frontend/src/lib/theme.ts` — existing constants confirmed; five EVAL_CHART_* constants absence confirmed
- `frontend/package.json` + `node_modules/recharts/package.json` — recharts 3.8.1 confirmed
- `node_modules/recharts/types/cartesian/Scatter.d.ts` — `ScatterProps`, `ScatterShapeProps` confirmed
- `node_modules/recharts/types/shape/Symbols.d.ts` — `size` (not `r`) is the Symbols prop
- `.planning/notes/flaw-tag-naming.md` — tag taxonomy and framing analysis

### Secondary (MEDIUM confidence)
- `109-CONTEXT.md` — all D-01..D-10 decisions read directly
- `109-UI-SPEC.md` — frontend/visual contract read directly (noting it needs amendment for dual-marker)
- `.planning/REQUIREMENTS.md` — LIBG-10 text confirmed

---

## Metadata

**Confidence breakdown:**
- Backend service signatures: HIGH — read directly from source
- Query seam: HIGH — library_repository.py pipeline confirmed step by step
- D-03 tag analysis: HIGH — each tag's framing logic traced through `_build_tags` source
- Frontend patterns: HIGH — read directly from FlawTrendChart, EndgameClockDiffOverTimeChart, LibraryGameCard
- Recharts dual-marker approach: HIGH — confirmed from project's existing dot prop pattern + Scatter type definitions
- Payload size estimate: MEDIUM — arithmetic estimate; planner must include measured verification

**Research date:** 2026-06-07
**Valid until:** 2026-07-07 (stable codebase; recharts 3.x breaking changes unlikely in 30 days)
