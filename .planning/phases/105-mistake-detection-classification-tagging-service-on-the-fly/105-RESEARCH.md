# Phase 105: Mistake-Detection + Classification + Tagging Service (on-the-fly) — Research

**Researched:** 2026-06-05
**Domain:** Python service layer — per-ply Stockfish eval derivation, severity classification, attribution tagging
**Confidence:** HIGH (all key facts grounded in actual source files; no external library research needed — pure project-internal design)

> **Amendment (2026-06-05, post-research, user-approved).** Contract narrowed: `classify_game_mistakes` **emits tagged flaw records for mistakes + blunders only**; **inaccuracies are count-only** (served by SQL aggregates / the `games.white_/black_*` oracle columns, never emitted). Where this note says "every flaw" / "emit per flaw" / "every flaw the mover made," read it as **every emitted mistake/blunder**. `_classify_severity` and `INACCURACY_DROP` are unchanged (still return/define the inaccuracy band — used for counts and the oracle test). Serving design for the cross-game filter + stats panel = SQL window-scan + Python tagging (Option 2), no materialization. See the `<amendment>` blocks in 105-01-PLAN.md / 105-02-PLAN.md and the "On-the-fly" amendment in 105-CONTEXT.md.

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **Severity thresholds (halved from Lichess):** `INACCURACY_DROP = 0.05`, `MISTAKE_DROP = 0.10`, `BLUNDER_DROP = 0.15` on the [0,1] ES scale. Highest band wins.
- **drop = ES_before − ES_after from the mover's POV** (side-to-move signed, matching lila `info.color.fold(-d, d)`).
- **Pure drop, NO position guard** — no `ES_before < 0.85` gate, no losing-side floor; sigmoid saturation is the only suppression.
- **ES via `eval_cp_to_expected_score`** — the existing un-clamped cp sigmoid. Do NOT use `eval_mate_to_expected_score` (hard 1.0/0.0) for drop math.
- **Mate — Option B:** map mate → ±1000 cp-equivalent ES (≈ 0.998 / 0.002); accepted divergence from lila's `MateAdvice` ladder is documented.
- **Eight attribution tags** (orthogonal, additive, never change severity): `miss`, `unpunished`, `from-winning`, `result-changing`, `time-pressure`, `hasty`, `knowledge-gap`, `phase`. Every flaw carries exactly one tempo tag.
- **`from-winning`**: `ES_before ≥ 0.85` (`FROM_WINNING_ES`).
- **`miss`**: the error's immediately-preceding opponent move was itself a Mistake or Blunder (adjacency tag; requires classifying both players' moves).
- **`unpunished`**: the flaw's immediately-following opponent move failed to recover the eval (mirror of `miss`).
- **On-the-fly, NOT materialized**: no new columns / table / migration / reimport. Design service so materialization is a drop-in later optimization.
- **Output contract**: each flaw = typed object with ply, FEN, side, severity, tags, eval before/after.
- **"Analyzed" iff ≥ 90% of per-ply positions have `eval_cp` or `eval_mate`**; unanalyzed → explicit "no engine analysis" result.
- **Backend only. No UI. No HTTP endpoint wiring.**
- **Tests including close-but-not-identical agreement** with game-level Lichess `white_/black_blunders/mistakes/inaccuracies` columns.

### Claude's Discretion

- Service location/naming (e.g. `app/services/mistakes_service.py`).
- Exact TypedDict/dataclass field names.
- Whether per-ply ES derivation is Python-side or SQL `LAG` window (benchmark later; correctness first).
- Test-fixture construction.
- Optional dev-only validation script comparing derived counts to game-level columns.
- **Initial tempo thresholds** — pick documented defaults, lean relative-to-base-clock; on-the-fly makes retuning free.

### Deferred Ideas (OUT OF SCOPE)

- Mistake-type filter integration into `apply_game_filters()`.
- Games / Flaws / Analysis UI, best-move endpoint.
- Materialization / caching.
- Final tempo-threshold calibration against real data.
- Option-A exact `MateAdvice` ladder.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| LIBG-02 | On-the-fly mistake-detection service deriving per-ply severity (inaccuracy/mistake/blunder) from stored `eval_cp`/`eval_mate`, using Lichess-aligned halved thresholds (0.05/0.10/0.15), mover POV, mate via ±1000 cp Option B, no materialization, no schema change; chess.com / unanalyzed games yield "no analysis" result. | Per-ply derivation mechanics in §Architecture Patterns; ES function reuse documented; eval coverage gate specified. |
| LIBG-06 | Emit all eight attribution tags per flaw: `miss`, `unpunished`, `from-winning`, `result-changing`, `phase`, and exactly one tempo tag {`time-pressure`,`hasty`,`knowledge-gap`}. | All eight tags fully specified with data sources and derivation logic in §Architecture Patterns. |
| LIBG-07 | Each flaw returned as a typed structured object (ply, FEN, side, severity, tags, eval before/after), documented as the consumption contract, designed for drop-in materialization. | Output contract section specifies TypedDict shape per project ty rules; FEN recomputation approach documented. |
</phase_requirements>

---

## Summary

Phase 105 builds `app/services/mistakes_service.py` — a pure Python service that, given a game's ordered `GamePosition` rows plus game metadata, derives every flaw the mover made and returns a typed list of flaw objects. There are no new columns, no migration, no endpoint, and no materialization. The service reads positions via a new repository function that fetches all `GamePosition` rows for a game ordered by `ply`.

The core computation iterates over consecutive ply pairs. For each ply N (even = white to move, odd = black to move), it computes ES_before from the eval at ply N-1 and ES_after from the eval at ply N, both in the mover's perspective, then checks the drop against the three thresholds. Mate is mapped to ±1000 cp before the sigmoid call. This produces an all-moves classification (both players) needed for the `miss` and `unpunished` adjacency tags. The user's flaws are the subset where `mover == user_color`.

The output contract is a `FlawResult` TypedDict (or a `NamedTuple`) with fields aligning to what the Games / Flaws / Analysis surfaces and SEED-037 Train will consume. FEN is recomputed from the PGN at service time using python-chess (already a project dependency; `board.fen()` at each ply, piece-placement only via `board.board_fen()`). The unanalyzed-game gate counts positions with a non-null eval and gates at the 90% threshold before running the classifier.

**Primary recommendation:** Implement as `app/services/mistakes_service.py` using Python-side iteration over a repository-loaded ordered list of `GamePosition` rows. No SQL `LAG` window function in v1 — correctness first, SQL window optimization as a later drop-in. Test in `tests/services/test_mistakes_service.py` using inline `GamePosition` object construction (no DB required for pure derivation; DB-backed tests only for the repository function).

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Per-ply ES computation | Service (Python) | — | Pure math reusing `eval_utils.py`; no I/O |
| Severity classification | Service (Python) | — | Threshold comparison over ES pairs |
| Attribution tagging | Service (Python) | — | Reads existing stored columns (`phase`, `clock_seconds`) plus game metadata |
| Position loading for a game | Repository (SQL) | — | One SELECT ordered by ply; service must not contain SQL |
| FEN recomputation per ply | Service (Python) | — | python-chess replay from `game.pgn`; no stored FEN per ply |
| Coverage gate | Service (Python) | — | Count non-null evals over total positions |
| Game metadata (result, colors, increment) | Repository (SQL) | — | Already on `Game` model; pass into service as a dataclass/TypedDict |

---

## Standard Stack

### Core (all already project dependencies — zero new installs)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| python-chess | 1.11.x | PGN replay to recompute per-ply FEN | Already used in `app/services/zobrist.py`; `board.board_fen()` is the project standard |
| SQLAlchemy 2.x async | project version | Load `GamePosition` rows ordered by ply | Project ORM; `select(GamePosition)` with `where` + `order_by` |
| Pydantic v2 / TypedDict | project version | Output contract typing | `ty` compliance requires explicit types |

### No new packages needed

All derivation logic uses stdlib (`math`, `dataclasses`/`typing`) plus existing project imports. No new `npm install` or `pip install` steps.

---

## Package Legitimacy Audit

> No new external packages are installed in this phase. Skip.

---

## Architecture Patterns

### System Architecture Diagram

```
Caller (later phase: Games/Flaws router or test)
         |
         | game_id, user_id
         v
[mistakes_repository.py]
  fetch_game_positions(session, game_id, user_id)
  -> list[GamePosition] ordered by ply ASC
         |
         v
[mistakes_service.py]
  classify_game_mistakes(game, positions)
         |
         +--[eval coverage gate]-- < 90% non-null evals -> GameNotAnalyzed result
         |
         +--[iterate ply pairs]
              for each ply N in 1..len(positions)-1:
                mover = white if N%2==0 else black
                ES_before = _ply_es(positions[N-1], mover)
                ES_after  = _ply_es(positions[N],   mover)
                drop      = ES_before - ES_after
                severity  = _classify_severity(drop)
                -> all_moves[N] = (mover, severity, ES_before, ES_after)
         |
         +--[tag pass]
              for each user flaw:
                miss        <- opponent move at N-1 was Mistake|Blunder?
                unpunished  <- opponent move at N+1 was not Mistake|Blunder?
                from_winning<- ES_before >= FROM_WINNING_ES
                result_changing <- result-boundary cross check
                tempo       <- _classify_tempo(move_time, clock_after, base_time)
                phase_tag   <- positions[N].phase -> "opening"/"middlegame"/"endgame"
         |
         v
  list[FlawRecord] | GameNotAnalyzed
         |
         v
Caller
```

### Recommended Project Structure

```
app/
├── services/
│   └── mistakes_service.py       # New: severity + 8-tag classification
├── repositories/
│   └── mistakes_repository.py    # New: fetch_game_positions for one game
│   (or add to game_repository.py if the function is trivially small)
tests/
├── services/
│   └── test_mistakes_service.py  # New: pure unit tests (no DB)
└── test_mistakes_repository.py   # New: DB-backed test for position loading
```

---

### Pattern 1: Per-Ply ES Derivation (mover POV)

**Key finding from `app/services/eval_utils.py`:**

`eval_cp_to_expected_score(eval_cp: int, user_color: Literal["white", "black"]) -> float`

- Takes white-perspective `eval_cp` and the user's color.
- Sign convention: `sign = 1 if user_color == "white" else -1`; feeds `exp(-K * sign * eval_cp)`.
- Symmetry invariant: `f(+x, "white") + f(+x, "black") == 1.0` (verified by `test_eval_utils.py`).
- **No clamp on input cp** — correct for judgment (Lichess doesn't clamp in its judgment path either).

**Per-ply mover color from ply number (confirmed from `seed_fixtures.py` line 100 and `zobrist.py` line 173):**

```python
# ply 0 = initial position, white to move
# even ply => white is the mover; odd ply => black is the mover
mover_color: Literal["white", "black"] = "white" if ply % 2 == 0 else "black"
```

**Ply semantics from `zobrist.py` lines 173–207 (`process_game_pgn`):**

At stored ply N:
- `full_hash`, `white_hash`, `black_hash` = board state **BEFORE** move N was played.
- `eval_cp`, `eval_mate` = eval annotation from the move node = eval **AFTER** move N.
- `move_san` = the SAN of move N (played from ply N position).
- `clock_seconds` = clock of the side that just played move N (from `%clk` annotation).

Therefore for classifying the mover at ply N:
```python
# ES_before: eval at ply N-1 (board after move N-1, before mover plays move N)
# ES_after:  eval at ply N   (board after mover plays move N)
ES_before = _ply_to_es(positions[N-1], mover_color)
ES_after  = _ply_to_es(positions[N],   mover_color)
drop = ES_before - ES_after  # positive drop = mover weakened their position
```

**`_ply_to_es` helper (Option B mate handling):**

```python
MATE_CP_EQUIVALENT: int = 1000  # ±1000 cp maps to ES ≈ 0.975/0.025

def _ply_to_es(pos: GamePosition, mover_color: Literal["white", "black"]) -> float | None:
    """Return mover-POV ES for this ply, or None if eval unavailable."""
    if pos.eval_mate is not None:
        # Option B: map mate to ±1000 cp equivalent, NOT hard 1.0/0.0.
        cp_equiv = MATE_CP_EQUIVALENT if pos.eval_mate > 0 else -MATE_CP_EQUIVALENT
        return eval_cp_to_expected_score(cp_equiv, mover_color)
    if pos.eval_cp is not None:
        return eval_cp_to_expected_score(pos.eval_cp, mover_color)
    return None
```

**[VERIFIED: app/services/eval_utils.py]** — function signature and sign convention confirmed from source.

### Pattern 2: Severity Classification

```python
# Named constants (no magic numbers — CLAUDE.md)
INACCURACY_DROP: float = 0.05   # = Lichess 0.10 on [-1,1] winningChances, halved
MISTAKE_DROP:    float = 0.10   # = Lichess 0.20
BLUNDER_DROP:    float = 0.15   # = Lichess 0.30
FROM_WINNING_ES: float = 0.85   # ~+471 cp for white user; FlawChess tag threshold

Severity = Literal["inaccuracy", "mistake", "blunder"]

def _classify_severity(drop: float) -> Severity | None:
    if drop >= BLUNDER_DROP:    return "blunder"
    if drop >= MISTAKE_DROP:    return "mistake"
    if drop >= INACCURACY_DROP: return "inaccuracy"
    return None
```

**[VERIFIED: .planning/notes/lichess-judgment-source.md]** — halved thresholds confirmed against lila `Advice.scala` source.

### Pattern 3: Output Contract — `FlawRecord` TypedDict

**Why TypedDict over dataclass:** consistent with the project's `PlyData` TypedDict in `zobrist.py` for structured per-item data; also consistent with `NormalizedGame` in `normalization.py`. Use TypedDict for the serializable contract consumed by downstream services/endpoints. Dataclass works too but TypedDict is lighter for read-only output.

```python
from typing import TypedDict, Literal

FlawSeverity = Literal["inaccuracy", "mistake", "blunder"]
FlawTag = Literal[
    "miss", "unpunished", "from-winning", "result-changing",
    "time-pressure", "hasty", "knowledge-gap", "phase-opening",
    "phase-middlegame", "phase-endgame",
]

class FlawRecord(TypedDict):
    ply: int                          # half-move number (0-indexed)
    fen: str                          # board_fen() at this ply (piece placement)
    side: Literal["white", "black"]   # the mover who made the flawed move
    severity: FlawSeverity
    tags: list[FlawTag]               # ordered, additive, orthogonal
    es_before: float                  # mover-POV ES before the flaw
    es_after: float                   # mover-POV ES after the flaw
    move_san: str | None              # SAN of the flawed move (from positions[N].move_san)
```

**Phase tag encoding decision (Claude's Discretion):** encode phase as `"phase-opening"` / `"phase-middlegame"` / `"phase-endgame"` in the `tags` list rather than a separate field. This keeps the tags list self-contained and avoids needing a separate `"phase"` field in `FlawRecord`. Maps `positions[N].phase` (0/1/2) to the tag string. [ASSUMED] — Claude's Discretion per CONTEXT.md.

**"No analysis" result type:**

```python
class GameNotAnalyzed(TypedDict):
    reason: Literal["no_engine_analysis"]
    eval_coverage: float     # fraction of plies with non-null eval (0.0–1.0)

GameMistakesResult = list[FlawRecord] | GameNotAnalyzed
```

### Pattern 4: FEN Recomputation

FEN is NOT stored per ply in `game_positions` — only `board_fen()` of the **final** position is stored on `Game.result_fen`. For per-ply FEN, replay the PGN:

```python
import chess
import chess.pgn
import io

def _recompute_fen_map(pgn: str) -> dict[int, str]:
    """Return {ply: board_fen()} for every ply from 0 to len(moves)."""
    game = chess.pgn.read_game(io.StringIO(pgn))
    if game is None:
        return {}
    board = game.board()
    fens: dict[int, str] = {0: board.board_fen()}
    for ply, node in enumerate(game.mainline(), start=1):
        board.push(node.move)
        fens[ply] = board.board_fen()
    return fens
```

**`board.board_fen()` is the project standard** — returns piece-placement only, not full FEN (no castling/en passant). Confirmed from `CLAUDE.md`: "Use `board.board_fen()` (piece placement only) not `board.fen()` (includes castling/en passant) when comparing positions."

**Cost:** one PGN parse per game call. Acceptable for on-the-fly (the whole service is per-request). The FEN map can be built once per `classify_game_mistakes` call and reused for all flaw records.

**[VERIFIED: app/services/zobrist.py line 270]** — `result_fen = board.board_fen()` confirms the convention.

### Pattern 5: Eval Coverage Gate

```python
EVAL_COVERAGE_MIN: float = 0.90  # analyzed iff >= 90% of plies have eval

def _compute_eval_coverage(positions: list[GamePosition]) -> float:
    if not positions:
        return 0.0
    n_with_eval = sum(
        1 for p in positions
        if p.eval_cp is not None or p.eval_mate is not None
    )
    return n_with_eval / len(positions)
```

**Note:** The final position row (ply = max ply) always has `eval_cp=None` and `eval_mate=None` because `zobrist.py` lines 239–258 explicitly leave eval null on the final position (no move was played from it, so there is no move annotation to attach eval to). This means the raw coverage for a fully-analyzed N-ply game is (N)/(N+1) ≈ 1 − 1/N. For a 40-move game (80 plies, 81 rows) the true coverage is 80/81 = 98.8% — well above 90%. The gate correctly handles this: the final null is expected and counted as not-analyzed, but the numerator still captures all analyzed positions. **No special case needed.**

**[VERIFIED: app/services/zobrist.py lines 239–258]** — final position row has `eval_cp=None`.

### Pattern 6: Tempo Tag Derivation (Initial Thresholds)

**Input data:**
- `positions[N].clock_seconds` — clock remaining after move N was played (from `%clk`), in seconds. Type `float | None`. `REAL` column.
- `game.increment_seconds` — per-move increment in seconds (`float | None`). Parsed from `time_control_str` e.g. `"600+5"`. **[VERIFIED: app/models/game.py lines 83–85]**
- `game.base_time_seconds` — starting clock in seconds (`int | None`). **[VERIFIED: app/models/game.py lines 80–82]**

**Move-time derivation:**

At ply N, the mover's clock is at `positions[N].clock_seconds`. The mover's previous clock was at `positions[N-2].clock_seconds` (same-side: two plies back). Increment is added when the move is played.

```python
# move_time = prev_clock - current_clock + increment
# prev_clock for ply N = positions[N-2].clock_seconds (same side's prior clock)
# Handle first move (N < 2): positions[N-2] doesn't exist
```

**First-move clock noise:** The first move for each color (ply 0 for white, ply 1 for black) has no prior same-side clock. The move time cannot be computed; treat as `None` and skip tempo tagging for first moves.

**Initial thresholds (relative to base clock — Claude's Discretion):**

```python
# All thresholds are relative to base_time_seconds when available.
# Rationale: a 5s move is "hasty" in classical (3600s base) but normal in bullet (60s base).
# Tuning target: calibrate against real data once the ruleset ships.

# Fraction of base time: clock_after / base_time < TIME_PRESSURE_CLOCK_FRACTION
TIME_PRESSURE_CLOCK_FRACTION: float = 0.05   # < 5% of base = low clock
# Fraction of base time: move_time / base_time < HASTY_MOVE_FRACTION (on comfortable clock)
HASTY_MOVE_FRACTION: float = 0.01            # < 1% of base = fast move
# Anything else (move_time >= HASTY_MOVE_FRACTION * base_time, clock > TIME_PRESSURE_CLOCK_FRACTION * base_time)
# => knowledge-gap
```

**Fallback when base_time_seconds is None or 0:** Use absolute thresholds.
```python
TIME_PRESSURE_CLOCK_ABS_SECONDS: float = 30.0   # < 30s remaining
HASTY_MOVE_ABS_SECONDS: float = 5.0             # < 5s move on comfortable clock
```

**Tempo classification logic:**

```python
TempoTag = Literal["time-pressure", "hasty", "knowledge-gap"]

def _classify_tempo(
    move_time: float | None,
    clock_after: float | None,
    base_time: int | None,
) -> TempoTag:
    """Every flaw carries exactly one tempo tag."""
    if clock_after is None or move_time is None:
        # Missing clock data — cannot distinguish hasty from knowledge-gap.
        # Default to knowledge-gap (the most conservative label).
        return "knowledge-gap"

    # Determine low-clock threshold
    if base_time and base_time > 0:
        low_clock_threshold = base_time * TIME_PRESSURE_CLOCK_FRACTION
        fast_move_threshold = base_time * HASTY_MOVE_FRACTION
    else:
        low_clock_threshold = TIME_PRESSURE_CLOCK_ABS_SECONDS
        fast_move_threshold = HASTY_MOVE_ABS_SECONDS

    if clock_after < low_clock_threshold:
        return "time-pressure"
    if move_time < fast_move_threshold:
        return "hasty"
    return "knowledge-gap"
```

**[ASSUMED]** — initial threshold values (TIME_PRESSURE_CLOCK_FRACTION = 0.05, HASTY_MOVE_FRACTION = 0.01) are reasonable starting points but are not calibrated against real data. Flagged as tunable per CONTEXT.md.

### Pattern 7: Result-Changing Tag

The game result is stored as `Game.result: str` (`"1-0"`, `"0-1"`, `"1/2-1/2"`). The user's color is `Game.user_color: str`. The project's `derive_user_result(result, user_color)` from `openings_service.py` returns `Literal["win", "draw", "loss"]`.

**Result-changing definition:** The flaw is result-changing if:
- User actually won (`"win"`) AND `ES_before >= RESULT_WIN_THRESHOLD` AND `ES_after < RESULT_WIN_THRESHOLD` (was winning, move dropped below winning).
- User drew (`"draw"`) AND `ES_before >= RESULT_DRAW_THRESHOLD` AND `ES_after < RESULT_DRAW_THRESHOLD` (was drawing or winning, dropped to losing zone).
- User lost (`"loss"`) AND `ES_before >= RESULT_DRAW_THRESHOLD` AND `ES_after < RESULT_DRAW_THRESHOLD` (as above — flaw contributed to the loss by crossing drawn/losing boundary).

```python
RESULT_WIN_THRESHOLD:  float = 0.70  # ES >= 0.70 = "winning" zone
RESULT_DRAW_THRESHOLD: float = 0.40  # ES >= 0.40 = "at least drawing" zone
```

**[ASSUMED]** — threshold values 0.70 / 0.40 are reasonable starting points. The key insight: if the user won, a flaw is only `result-changing` if it briefly threatened to turn the win into a draw/loss; if the user drew or lost, a flaw is `result-changing` if it crossed the boundary from drawing (≥0.40) to losing (<0.40). These values are tunable.

The simpler definition used in practice: "the first flaw that crosses the result boundary given the actual outcome." Pick one boundary per actual outcome. [ASSUMED] — the exact boundary choice is Claude's Discretion.

### Pattern 8: `miss` and `unpunished` Tags

Both require classifying ALL moves (not just the user's) — the all-moves classification pass is required.

```python
# all_moves[N] = (mover_color, severity | None, es_before, es_after)
# Populated for N in range(1, len(positions))

# miss: user's flaw at ply N where opponent's move at ply N-1 was Mistake|Blunder
def _is_miss(n: int, all_moves: dict[int, tuple], user_color: str) -> bool:
    opponent_n = n - 1
    if opponent_n < 1:
        return False
    opp_severity = all_moves.get(opponent_n, (None, None))[1]
    return opp_severity in ("mistake", "blunder")

# unpunished: user's flaw at ply N where opponent's move at ply N+1 was NOT Mistake|Blunder
def _is_unpunished(n: int, all_moves: dict[int, tuple]) -> bool:
    opp_n = n + 1
    opp_entry = all_moves.get(opp_n)
    if opp_entry is None:
        # No following opponent move (end of game): opponent "didn't punish"
        return True
    opp_severity = opp_entry[1]
    return opp_severity not in ("mistake", "blunder")
```

Note: `unpunished` applies only to user **blunders** per the CONTEXT.md spec ("your blunder the opponent let slide"). Applied to inaccuracies/mistakes it would be too noisy. [ASSUMED] — apply `unpunished` only to user blunders. Confirm with user if desired.

### Pattern 9: Position Loading — Repository

A new repository function is needed to load all positions for a single game, ordered by ply:

```python
# app/repositories/mistakes_repository.py
# (or extend game_repository.py if small enough)

async def fetch_game_positions_ordered(
    session: AsyncSession,
    game_id: int,
    user_id: int,
) -> list[GamePosition]:
    """Load all GamePosition rows for one game, ordered by ply ASC.

    user_id is used as a security guard — GamePosition has (game_id, user_id, ply) PK.
    """
    stmt = (
        select(GamePosition)
        .where(GamePosition.game_id == game_id, GamePosition.user_id == user_id)
        .order_by(GamePosition.ply)
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())
```

**[VERIFIED: app/models/game_position.py lines 79–86]** — composite PK is `(game_id, user_id, ply)`, so the `order_by(GamePosition.ply)` query is index-backed via the PK scan.

No existing index gap: the natural PK order provides the ply-ordered scan. PostgreSQL can scan the PK in ply order for a given (game_id, user_id) prefix — this is efficient. An explicit `index=True` on `game_id` alone (line 80) also exists.

**[VERIFIED: app/models/game_position.py line 80]** — `game_id` has `index=True` (standalone btree), so the filter `WHERE game_id = X AND user_id = Y` hits the btree, then PK ordering applies.

### Anti-Patterns to Avoid

- **Using `eval_mate_to_expected_score` for drop math:** This returns hard 1.0/0.0 and was built for endgame span averaging, not ply-pair drops. A mate→non-mate transition with 1.0/0.0 would produce a 1.0 or 0.0 drop, making every mate-adjacent move a blunder. Use Option B (±1000 cp mapping) instead.
- **Not classifying opponent moves:** Tags `miss` and `unpunished` require `all_moves` to include both sides. Classifying only the user's side breaks these.
- **Using `board.fen()` instead of `board.board_fen()`:** The project standard is piece-placement only; full FEN includes castling/en passant that is not position-invariant.
- **Assuming ply 0 has a prior same-side clock:** First moves have no computable move time; skip tempo tagging.
- **`asyncio.gather` on the same session:** CLAUDE.md critical constraint — never concurrent queries on one `AsyncSession`.
- **Not guarding `base_time_seconds == 0`:** Division by zero in relative threshold computation. Always check `base_time and base_time > 0`.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Sigmoid ES from cp | Custom sigmoid | `eval_cp_to_expected_score` | Already correct, tested, matches Lichess constant |
| PGN ply replay | Custom board stepper | `chess.pgn.read_game` + `board.push` | python-chess handles all edge cases |
| Game result → user outcome | `if result == "1-0"` inline | `derive_user_result(result, user_color)` | Already in `openings_service.py`, handles all 3 cases |
| Time control parsing | Custom string splitter | `parse_base_and_increment(tc_str)` from `normalization.py` | Already handles fractional increments (`"10+0.1"`), edge cases |

---

## Key Research Questions — Answered

### Q1: Per-Ply Derivation Mechanics

**Recommendation: Python-side iteration over ordered list.** Load all `GamePosition` rows for a game via one repository SELECT ordered by `ply ASC`. Iterate in Python as a list — no SQL `LAG` window needed in v1. Correctness is clear, testing is straightforward (pure functions), and the on-the-fly / no-materialization + "performance accepted" constraint makes v1 simplicity the right call.

**SQL LAG option:** A future optimization could compute drops in SQL with `LAG(eval_cp) OVER (PARTITION BY game_id, user_id ORDER BY ply)`. This would be faster for aggregate queries over many games (e.g., the stats panel) but is not needed for single-game on-the-fly use. The service interface remains identical — materialization is still a drop-in.

**Ply ordering column:** `ply` (SmallInteger, PK component). The PK `(game_id, user_id, ply)` guarantees uniqueness and ordering. **[VERIFIED: `app/models/game_position.py` lines 79–86]**

**Mover per ply:** `ply % 2 == 0` → white to move; `ply % 2 == 1` → black to move. **[VERIFIED: `tests/seed_fixtures.py` line 100, `app/services/zobrist.py` line 173]**

### Q2: Sign/POV Handling

`eval_cp_to_expected_score(eval_cp, mover_color)` handles the sign flip internally. For a white mover: `sign = 1`; for a black mover: `sign = -1`. The function takes the white-perspective `eval_cp` from the column and the mover's color, and returns the mover's POV ES.

To verify: `eval_cp_to_expected_score(+100, "white") ≈ 0.591` (white is ahead, good for white mover). `eval_cp_to_expected_score(+100, "black") ≈ 0.409` (white is ahead, bad for black mover). **[VERIFIED: `tests/services/test_eval_utils.py` lines 41–54]**

### Q3: Mate Option B

Map `eval_mate != None` → `cp_equiv = +1000 if eval_mate > 0 else -1000`. Then call `eval_cp_to_expected_score(cp_equiv, mover_color)`. This gives ES ≈ 0.975 / 0.025, not hard 1.0/0.0.

ES at ±1000 cp = `1/(1+exp(-0.00368208*1000)) ≈ 0.9754`. This is the Option B mapping. The drop between two mate positions of the same sign (mate persists, same side) ≈ 0 — no classification, matching lila's "Mate persists → no judgment" behavior. **[VERIFIED: math computed above]**

### Q4: Tag Computation Data Sources

| Tag | Data needed | Column / field |
|-----|-------------|----------------|
| `miss` | opponent's prev move severity | `all_moves[N-1]` (requires full-game classification) |
| `unpunished` | opponent's next move severity | `all_moves[N+1]` (requires full-game classification) |
| `from-winning` | ES_before | computed ES, threshold 0.85 |
| `result-changing` | ES_before, ES_after, game result, user color | `Game.result`, `Game.user_color` |
| `time-pressure` | clock after move, base time | `positions[N].clock_seconds`, `Game.base_time_seconds` |
| `hasty` | move time, clock comfort | computed move time, same columns |
| `knowledge-gap` | residual (not hasty, not time-pressure) | same |
| `phase-*` | `positions[N].phase` | `GamePosition.phase` (0=opening, 1=middlegame, 2=endgame) |

**Increment source:** `Game.increment_seconds` (float, nullable). **[VERIFIED: `app/models/game.py` lines 83–85]**

**Clock convention confirmed from `seed_fixtures.py` lines 294–296:**
> "clock_seconds is the clock of the player who just moved"
> Even ply → white's clock; odd ply → black's clock.

This means `positions[N].clock_seconds` is the clock of the mover (the player who played move N) immediately after playing it. This is what we need for `clock_after` in the tempo tag.

For move time: `move_time = positions[N-2].clock_seconds - positions[N].clock_seconds + increment_seconds` (two plies back for the same side, plus increment added when move was made).

### Q5: Output Contract Typing

Use `TypedDict` (consistent with `PlyData` in `zobrist.py`). `ty` compliance rules from CLAUDE.md:
- Use `Literal["inaccuracy", "mistake", "blunder"]` for severity (not bare `str`).
- Use `Literal["miss", "unpunished", ...]` for tag types.
- Return type annotation required on all functions.
- Avoid `any`.

`GameMistakesResult = list[FlawRecord] | GameNotAnalyzed` — the union type is the public return type of `classify_game_mistakes(...)`.

### Q6: "No Analysis" Detection

```python
def _is_game_analyzed(positions: list[GamePosition]) -> bool:
    coverage = _compute_eval_coverage(positions)
    return coverage >= EVAL_COVERAGE_MIN  # 0.90
```

**Edge case: final position** always has null eval (see Pattern 5). This is handled correctly — a 40-move analyzed game has 80/81 ≈ 98.8% coverage, above the 90% threshold.

**chess.com games:** `eval_cp` and `eval_mate` are always null (evals are not in the chess.com API). Coverage = 0% for any chess.com game. The gate correctly returns `GameNotAnalyzed`. **[VERIFIED: `app/models/game_position.py` line 124]** — comment says "NULL for chess.com and unanalyzed games."

**LIBG-02 requirement:** "chess.com / unanalyzed games yield an explicit 'no analysis' result, never a false zero-flaw game." Satisfied by the gate.

### Q7: Test Oracle

**How `white_/black_blunders` etc. are produced (normalization.py lines 401–439):**

These columns are populated directly from Lichess's own API response:
```python
white_blunders=white_analysis.get("blunder"),
white_mistakes=white_analysis.get("mistake"),
white_inaccuracies=white_analysis.get("inaccuracy"),
```
**[VERIFIED: `app/services/normalization.py` lines 430–437]**

Lichess computes these server-side from the game's eval annotations before returning the game JSON. They represent Lichess's **own** classification applied with Lichess's **own** thresholds on the **[−1, +1] winningChances scale** (cutoffs 0.10/0.20/0.30 on that scale). Our thresholds are equivalent after halving but there are two differences:

1. **Mate handling**: Lichess uses the full `MateAdvice` ladder (cp↔mate transitions classified by the non-mate endpoint). We use Option B (±1000 cp, no ladder). This under-flags some mate transitions — the counts will differ for games with cp↔mate transitions.
2. **Floating point / edge cases**: Minor differences at exact threshold values.

**Assert closeness, not equality:**
```python
# In test_mistakes_service.py sanity check:
assert abs(derived_blunders - lichess_blunders) <= SANITY_TOLERANCE
SANITY_TOLERANCE: int = 2  # allow ≤2 off per color per severity
```
[ASSUMED] — `SANITY_TOLERANCE = 2` is a starting point. The real tolerance should be validated against a sample of analyzed lichess games with mate transitions.

### Q8: Service Placement and Layering

**Service:** `app/services/mistakes_service.py` — pure Python, no direct DB access, receives `Game` + `list[GamePosition]` as inputs. This matches the existing pattern (`endgame_service.py`, `eval_utils.py`): services compute, repositories fetch.

**Repository:** `app/repositories/mistakes_repository.py` — one function: `fetch_game_positions_ordered(session, game_id, user_id) -> list[GamePosition]`. Could alternatively be a new function in `game_repository.py` if it remains small, but a dedicated file keeps domain separation clean.

**Service function signature:**

```python
from app.models.game import Game
from app.models.game_position import GamePosition

async def classify_game_mistakes(
    game: Game,
    positions: list[GamePosition],
) -> GameMistakesResult:
    ...
```

The function is **synchronous** (pure computation over already-loaded objects) but can be `async` if the caller is async and for future compatibility. No `AsyncSession` inside the service.

---

## Common Pitfalls

### Pitfall 1: Wrong Eval Semantics (eval AFTER, not BEFORE the ply's move)

**What goes wrong:** Treating `positions[N].eval_cp` as the eval BEFORE move N is played.
**Why it happens:** Naming ambiguity — "ply N position eval" sounds like the eval of position N.
**Actual convention:** In `zobrist.py` `process_game_pgn` (line 185), `node.eval()` is the eval annotation on the move node, which per PGN convention annotates the position AFTER the move. So `positions[N].eval_cp` = eval of the board state AFTER move N.
**How to avoid:** Clearly document in code: `ES_before = _ply_to_es(positions[N-1], color)` (previous ply = board before mover's move); `ES_after = _ply_to_es(positions[N], color)` (current ply = board after mover's move).
**Warning sign:** Severity on the starting/initial move; ES_before = ES_after for a clearly poor move.

### Pitfall 2: Off-by-One on Same-Side Clock Lookup

**What goes wrong:** Computing move time as `positions[N-1].clock_seconds - positions[N].clock_seconds` (one ply back) instead of `positions[N-2].clock_seconds - positions[N].clock_seconds` (same-side, two plies back).
**Why it happens:** Forgetting that chess alternates sides; ply N-1 is the opponent's clock, not the mover's.
**How to avoid:** Same-side clock is always two plies back (`N-2`). Handle `N < 2` as no prior clock (first move).
**Warning sign:** Bullet games with implausibly huge move times; all white moves showing black's clock delta.

### Pitfall 3: Hard 1.0/0.0 Mate in Drop Math

**What goes wrong:** Calling `eval_mate_to_expected_score(eval_mate, mover_color)` for ES in drop computation. A mate-to-non-mate transition produces a drop of ~0.998, always classifying as a blunder even when the position was already completely winning.
**Why it happens:** `eval_mate_to_expected_score` exists and looks like the right function.
**How to avoid:** `eval_mate_to_expected_score` is only for endgame span averaging (hard 1.0/0.0 is correct when averaging ES over an entire endgame span). For per-ply drop math, always use `eval_cp_to_expected_score(±MATE_CP_EQUIVALENT, color)`.
**Warning sign:** Every game with a checkmate shows a blunder on the final move regardless of the position.

### Pitfall 4: Null Eval Interior to the Game (Non-Coverage Cases)

**What goes wrong:** Null `eval_cp`/`eval_mate` at a ply interior to a fully-analyzed game. This can happen for book moves (Lichess sometimes omits evals for the first few book plies), threefold repetition positions, or corrupt annotations.
**Why it happens:** Not all positions in an "analyzed" game necessarily have eval.
**How to avoid:** When `_ply_to_es` returns `None` for either `positions[N-1]` or `positions[N]`, skip that ply (no flaw record). The coverage gate (90%) ensures this is exceptional, not the norm.
**Warning sign:** Missing flaws on obviously bad moves; IndexError if code assumes all evals are present.

### Pitfall 5: `miss` Tag Mis-Applied Without Full Classification

**What goes wrong:** Only classifying user's moves, then checking if the prior ply was an opponent error. But the prior ply's severity is never computed because only user moves were classified.
**Why it happens:** Forgetting that `miss` requires an all-moves pass.
**How to avoid:** Run the ES-drop computation for ALL plies (both sides), store in `all_moves: dict[int, ...]`, then filter to user flaws for the final result.

### Pitfall 6: `unpunished` Applied Too Broadly

**What goes wrong:** Applying `unpunished` to inaccuracies and mistakes, producing a flood of `unpunished` tags.
**Design decision:** `unpunished` is most meaningful for blunders ("you got away with a blunder"). Consider restricting to severity == "blunder" only. [ASSUMED] — flag for confirmation.

---

## Runtime State Inventory

> This is a new greenfield service — no rename/refactor. Skip.

---

## Environment Availability

> Step 2.6 SKIPPED — this phase is a pure Python service addition with no new external dependencies. All required tools (python-chess, SQLAlchemy, FastAPI) are already in the project's `uv` lockfile and running in the dev environment.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (async via pytest-asyncio) |
| Config file | `pyproject.toml` [tool.pytest.ini_options] |
| Quick run command | `uv run pytest tests/services/test_mistakes_service.py -x` |
| Full suite command | `uv run pytest -n auto -x` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| LIBG-02 | Severity derived from cp drop at halved thresholds | unit | `pytest tests/services/test_mistakes_service.py::test_severity_thresholds -x` | ❌ Wave 0 |
| LIBG-02 | Mate Option B maps ±1000 cp before sigmoid | unit | `pytest tests/services/test_mistakes_service.py::test_mate_option_b -x` | ❌ Wave 0 |
| LIBG-02 | chess.com game → GameNotAnalyzed | unit | `pytest tests/services/test_mistakes_service.py::test_no_analysis_chess_com -x` | ❌ Wave 0 |
| LIBG-02 | 0% eval coverage → GameNotAnalyzed | unit | `pytest tests/services/test_mistakes_service.py::test_eval_coverage_gate -x` | ❌ Wave 0 |
| LIBG-02 | ≥90% eval coverage → flaws list | unit | `pytest tests/services/test_mistakes_service.py::test_analyzed_game -x` | ❌ Wave 0 |
| LIBG-06 | `miss` tag on flaw preceded by opponent blunder | unit | `pytest tests/services/test_mistakes_service.py::test_tag_miss -x` | ❌ Wave 0 |
| LIBG-06 | `unpunished` tag on blunder not followed by recovery | unit | `pytest tests/services/test_mistakes_service.py::test_tag_unpunished -x` | ❌ Wave 0 |
| LIBG-06 | `from-winning` tag when ES_before >= 0.85 | unit | `pytest tests/services/test_mistakes_service.py::test_tag_from_winning -x` | ❌ Wave 0 |
| LIBG-06 | Exactly one tempo tag per flaw | unit | `pytest tests/services/test_mistakes_service.py::test_tempo_exclusive -x` | ❌ Wave 0 |
| LIBG-06 | `phase-*` tag maps `positions[N].phase` correctly | unit | `pytest tests/services/test_mistakes_service.py::test_phase_tag -x` | ❌ Wave 0 |
| LIBG-07 | FlawRecord TypedDict has all required fields | unit | `pytest tests/services/test_mistakes_service.py::test_flaw_record_shape -x` | ❌ Wave 0 |
| LIBG-07 | FEN recomputed per ply (board_fen not full fen) | unit | `pytest tests/services/test_mistakes_service.py::test_fen_recomputed -x` | ❌ Wave 0 |
| LIBG-02/07 | Derived counts close to Lichess oracle columns | sanity | `pytest tests/services/test_mistakes_service.py::test_oracle_closeness -x` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `uv run pytest tests/services/test_mistakes_service.py -x`
- **Per wave merge:** `uv run pytest -n auto -x`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `tests/services/test_mistakes_service.py` — covers all LIBG-02/06/07 behaviors above
- [ ] `tests/test_mistakes_repository.py` — DB-backed test for `fetch_game_positions_ordered` ordering correctness

*(No framework install needed — pytest + pytest-asyncio already in the project.)*

---

## Security Domain

> This phase adds **no external input surface** (no endpoint, reads existing owned data). No new threat-modeled surface. Per CONTEXT.md specifics: "The PLAN threat_model block should state this and stay minimal." The later best-move endpoint (Phase N) is where authentication + rate-limiting matters — deferred.

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V5 Input Validation | No (internal data only) | — |
| V4 Access Control | Partial | `user_id` passed to repository for ownership guard (PK prefix filter) |
| V2 Authentication | No | No new endpoint |
| V6 Cryptography | No | — |

---

## Code Examples

### Minimal service skeleton

```python
# Source: project conventions from app/services/eval_utils.py, endgame_service.py

from __future__ import annotations

import io
from typing import Literal, TypedDict

import chess
import chess.pgn

from app.models.game import Game
from app.models.game_position import GamePosition
from app.services.eval_utils import eval_cp_to_expected_score

# --- Constants ---
INACCURACY_DROP: float = 0.05
MISTAKE_DROP:    float = 0.10
BLUNDER_DROP:    float = 0.15
FROM_WINNING_ES: float = 0.85
MATE_CP_EQUIVALENT: int = 1000
EVAL_COVERAGE_MIN: float = 0.90
TIME_PRESSURE_CLOCK_FRACTION: float = 0.05
HASTY_MOVE_FRACTION: float = 0.01
TIME_PRESSURE_CLOCK_ABS_SECONDS: float = 30.0
HASTY_MOVE_ABS_SECONDS: float = 5.0

# --- Types ---
FlawSeverity = Literal["inaccuracy", "mistake", "blunder"]
FlawTag = Literal[
    "miss", "unpunished", "from-winning", "result-changing",
    "time-pressure", "hasty", "knowledge-gap",
    "phase-opening", "phase-middlegame", "phase-endgame",
]

class FlawRecord(TypedDict):
    ply: int
    fen: str
    side: Literal["white", "black"]
    severity: FlawSeverity
    tags: list[FlawTag]
    es_before: float
    es_after: float
    move_san: str | None

class GameNotAnalyzed(TypedDict):
    reason: Literal["no_engine_analysis"]
    eval_coverage: float

GameMistakesResult = list[FlawRecord] | GameNotAnalyzed

# --- ES helper ---
def _ply_to_es(
    pos: GamePosition,
    mover_color: Literal["white", "black"],
) -> float | None:
    if pos.eval_mate is not None:
        cp = MATE_CP_EQUIVALENT if pos.eval_mate > 0 else -MATE_CP_EQUIVALENT
        return eval_cp_to_expected_score(cp, mover_color)
    if pos.eval_cp is not None:
        return eval_cp_to_expected_score(pos.eval_cp, mover_color)
    return None
```

### Test fixture pattern (pure-unit, no DB)

```python
# Source: pattern from tests/services/test_eval_utils.py, tests/test_endgame_repository.py

from app.models.game_position import GamePosition
from app.models.game import Game

def _make_pos(ply: int, eval_cp: int | None = None, eval_mate: int | None = None,
              clock_seconds: float | None = None, phase: int = 1) -> GamePosition:
    """Build a GamePosition with eval and clock fields for unit testing."""
    pos = GamePosition.__new__(GamePosition)
    pos.ply = ply
    pos.eval_cp = eval_cp
    pos.eval_mate = eval_mate
    pos.clock_seconds = clock_seconds
    pos.phase = phase
    pos.move_san = None
    pos.full_hash = 0
    pos.white_hash = 0
    pos.black_hash = 0
    pos.material_count = 1000
    pos.material_signature = "KR_KR"
    pos.material_imbalance = 0
    pos.has_opposite_color_bishops = False
    pos.piece_count = 2
    pos.backrank_sparse = False
    pos.mixedness = 100
    pos.endgame_class = None
    return pos
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Game-level Lichess B/M/I columns as primary mistake data | Per-ply derivation (this service) | Phase 105 | Enables ply-level FEN, per-flaw tags, consistent method across all surfaces |
| Hard 1.0/0.0 mate ES for span averaging | Hard 1.0/0.0 for averaging, ±1000 cp for per-ply drops | Phase 105 | Prevents mate-adjacent positions from always registering as blunders |

**Not deprecated by this phase:**
- `eval_mate_to_expected_score`: still correct and needed for endgame span-entry ES averaging in `endgame_service.py`.
- Game-level Lichess columns (`white_blunders` etc.): still used as the test oracle and as cheap badges on game cards (later phase).

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Initial tempo thresholds: `TIME_PRESSURE_CLOCK_FRACTION = 0.05`, `HASTY_MOVE_FRACTION = 0.01` | Pattern 6 | Mis-classifies too many / too few moves as hasty or time-pressure; fully tunable post-ship |
| A2 | Absolute fallback thresholds: 30s for time-pressure, 5s for hasty | Pattern 6 | Same as A1; fallback rarely fires in practice (most games have base_time_seconds) |
| A3 | `result-changing` thresholds: 0.70 (winning) and 0.40 (drawing) | Pattern 7 | May over- or under-count result-changing tags; tunable |
| A4 | `unpunished` applies to blunders only (not inaccuracies/mistakes) | Pattern 8 | If applies to all severities: too many unpunished tags; if wrong severity: low impact |
| A5 | `SANITY_TOLERANCE = 2` for oracle closeness test | Q7 | If too tight: test flaps on mate-edge games; if too loose: misses real divergences |
| A6 | Phase tag encoded in `tags` list as `"phase-opening"` etc. (not a separate field) | Pattern 3 | Downstream consumers expect a separate `phase` field; easily changed in the TypedDict |

---

## Open Questions (RESOLVED)

> All three are **Claude's Discretion** per 105-CONTEXT.md (tunable defaults, not locked design unknowns). They are answered with documented `[ASSUMED]` defaults in this research body and implemented as named, tunable constants in the plans; on-the-fly detection makes retuning free once real data is available. Not blocking execution.

1. **Tempo threshold calibration**
   - What we know: relative-to-base-clock is the right approach; initial defaults are A1/A2 above.
   - What's unclear: the right fraction values — 5% for time-pressure and 1% for hasty are guesses.
   - Recommendation: ship the documented defaults; add a note that these are the first values to tune once real data confirms coverage.

2. **`unpunished` scope: blunders only vs all severities**
   - What we know: "your blunder the opponent let slide" is the user-facing framing in CONTEXT.md.
   - What's unclear: whether mistake-level `unpunished` is valuable enough to show.
   - Recommendation: start with blunders only; widen later if the stats panel shows demand.

3. **`result-changing` boundary definition**
   - What we know: it should detect "this error flipped the game outcome."
   - What's unclear: the exact ES boundary that maps to "winning" vs "drawing" is subjective.
   - Recommendation: use 0.70/0.40 as initial values; validate against a few analyzed games before finalizing.

---

## Sources

### Primary (HIGH confidence)
- `app/services/eval_utils.py` — `eval_cp_to_expected_score`, `LICHESS_K`, sign convention, symmetry property
- `app/models/game_position.py` — all per-ply columns, PK structure, `phase` encoding (0/1/2)
- `app/models/game.py` — `Game.result`, `Game.user_color`, `Game.base_time_seconds`, `Game.increment_seconds`, `white_/black_blunders` oracle columns (lines 111–120)
- `app/services/zobrist.py` lines 173–207 — ply semantics (eval AFTER move, clock of mover)
- `app/services/normalization.py` lines 430–437 — how Lichess analysis columns are populated from API response
- `.planning/notes/lichess-judgment-source.md` — verified against lila `Advice.scala`, threshold halving, Option B mate rationale
- `.planning/phases/105-mistake-detection-classification-tagging-service-on-the-fly/105-CONTEXT.md` — all locked decisions
- `tests/seed_fixtures.py` lines 100, 280–307 — clock parity convention (even ply = white's clock)
- `tests/services/test_eval_utils.py` — ES function behavior verified

### Secondary (MEDIUM confidence)
- `app/services/endgame_service.py` `_compute_span_scores` — ES-gap derivation precedent (span-level not per-ply, but the ES derivation pattern is the same)
- `tests/test_endgame_repository.py` `_seed_game_position` — GamePosition construction pattern for tests

---

## Metadata

**Confidence breakdown:**
- Severity thresholds: HIGH — source-verified from lila `Advice.scala`
- ES derivation mechanics: HIGH — verified from `eval_utils.py`, `zobrist.py`, symmetry tests
- Output contract shape: HIGH — follows project TypedDict conventions
- Tempo thresholds: LOW — initial guesses, explicitly tagged [ASSUMED]
- `result-changing` thresholds: LOW — [ASSUMED], tunable
- `miss`/`unpunished` scope: MEDIUM — `miss` is source-specified; `unpunished` scope is [ASSUMED]

**Research date:** 2026-06-05
**Valid until:** stable — this is a greenfield service with no external dependencies; the only stale risk is if the `GamePosition` schema changes (unlikely without a migration)

---

## RESEARCH COMPLETE
