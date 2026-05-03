# Phase 79: Position-phase classifier and middlegame eval — Pattern Map

**Mapped:** 2026-05-02
**Files analyzed:** 7 (6 modified + 1 new alembic revision)
**Analogs found:** 7 / 7

All analogs are **inside the same files being modified** — Phase 78 just shipped the `eval_cp`/`eval_mate` plumbing through the same import path, backfill script, classifier, model, and TypedDict. Phase 79 extends each pattern uniformly. Per-file analogs are explicit and verbatim line references are provided so the planner can produce concrete `<read_first>` lists and `<action>` blocks without re-discovery.

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `app/services/position_classifier.py` | service (pure-fn classifier) | transform | itself (lines 86-99, 291-314) | exact (extend dataclass + classify_position) |
| `app/services/zobrist.py` | service (PGN walker) | transform | itself (lines 32-54, 199-225, 232-255) | exact (extend PlyData + both ply loops) |
| `app/services/import_service.py` | service (orchestrator + bulk insert + eval pass) | batch | itself (lines 500-522, 528-615) | exact (extend bulk-insert payload + eval pass loop) |
| `app/models/game_position.py` | model | CRUD | itself (lines 82-88, sibling to `piece_count`/`backrank_sparse`/`mixedness`) | exact (sibling SmallInteger nullable column) |
| `scripts/backfill_eval.py` | script (CLI batch) | batch | itself (lines 136-231, 234-362) | exact (sibling stmt + new pass + phase UPDATE pass) |
| `tests/test_position_classifier.py` | test | transform | itself (TestMaterialCount/TestMaterialSignature classes) | exact (sibling TestPhaseClassification class) |
| `alembic/versions/{new}_add_phase_column.py` | migration | schema | `20260502_125433_c92af8282d1a_reshape_ix_gp_user_endgame_game_for_.py` | role-match (column-add migration, no embedded backfill) |

## Pattern Assignments

### `app/services/position_classifier.py` — extend dataclass + classify_position (CLASS-01, CLASS-02)

**Analog:** itself

**Read first:** lines 27-99 (constants + dataclass), lines 167-183 (`_compute_piece_count`), lines 210-222 (`_compute_backrank_sparse`), lines 291-314 (`classify_position`).

**Existing constant pattern** (line 35-63 — module-level named threshold):
```python
# Backrank sparseness threshold: if either side has fewer than this many pieces
# on their back rank, the position is considered "backrank sparse".
BACKRANK_SPARSE_THRESHOLD = 4
```
**New constants to add (top-level, alongside `BACKRANK_SPARSE_THRESHOLD`):**
- `MIDGAME_MAJORS_AND_MINORS_THRESHOLD = 10` — Lichess Divider.scala default
- `MIDGAME_MIXEDNESS_THRESHOLD = 10` — Lichess Divider.scala default

`ENDGAME_PIECE_COUNT_THRESHOLD = 6` is already defined in `app/repositories/endgame_repository.py:35` and re-used by `zobrist.py` — do **not** redefine. Either import it here, or define a sibling local constant and have a Python-level assertion in tests that they agree, OR the SPEC's preferred path: keep the existing import boundary as-is and reference it via cross-module import. Planner should import from `endgame_repository` to preserve single source of truth.

**Frozen dataclass pattern** (lines 86-99 — extend with `phase`):
```python
@dataclass(frozen=True)
class PositionClassification:
    """Classification output for a single chess position.

    All fields are read-only (frozen dataclass).
    """

    material_count: int
    material_signature: str
    material_imbalance: int
    has_opposite_color_bishops: bool
    piece_count: int
    backrank_sparse: bool
    mixedness: int
    # NEW: phase: Literal[0, 1, 2]  # 0=opening, 1=middlegame, 2=endgame
```
**Required `Literal[0, 1, 2]` import** (top of file): `from typing import Literal`. ty check requires this annotation exactly — do not use bare `int`.

**Helper function pattern** (lines 210-222 — `_compute_backrank_sparse` is the closest analog: takes the board, returns a derived value):
```python
def _compute_backrank_sparse(board: chess.Board) -> bool:
    white_backrank_count = bin(board.occupied_co[chess.WHITE] & chess.BB_RANK_1).count("1")
    black_backrank_count = bin(board.occupied_co[chess.BLACK] & chess.BB_RANK_8).count("1")
    return (
        white_backrank_count < BACKRANK_SPARSE_THRESHOLD
        or black_backrank_count < BACKRANK_SPARSE_THRESHOLD
    )
```
**New predicate functions to add** (siblings to `_compute_backrank_sparse`, but operating on already-derived inputs, **not** the board):
```python
def is_endgame(piece_count: int) -> bool:
    """Lichess Divider.scala isEndGame predicate."""
    return piece_count <= ENDGAME_PIECE_COUNT_THRESHOLD


def is_middlegame(piece_count: int, backrank_sparse: bool, mixedness: int) -> bool:
    """Lichess Divider.scala isMidGame predicate."""
    return (
        piece_count <= MIDGAME_MAJORS_AND_MINORS_THRESHOLD
        or backrank_sparse
        or mixedness >= MIDGAME_MIXEDNESS_THRESHOLD
    )
```

**`classify_position` extension pattern** (lines 291-314 — current return; planner adds inline phase derivation, **`is_endgame` first** so PHASE-INV-01 holds by construction):
```python
def classify_position(board: chess.Board) -> PositionClassification:
    material_count = _compute_material_count(board)
    material_signature = _compute_material_signature(board)
    material_imbalance = _compute_material_imbalance(board)
    has_opposite_color_bishops = _compute_opposite_color_bishops(board)
    piece_count = _compute_piece_count(board)
    backrank_sparse = _compute_backrank_sparse(board)
    mixedness = _compute_mixedness(board)

    # Phase 79 CLASS-02: derive phase from already-computed inputs (no second board scan).
    # is_endgame is checked first so PHASE-INV-01 (phase=2 ⟺ endgame_class IS NOT NULL) holds by construction.
    phase: Literal[0, 1, 2]
    if is_endgame(piece_count):
        phase = 2
    elif is_middlegame(piece_count, backrank_sparse, mixedness):
        phase = 1
    else:
        phase = 0

    return PositionClassification(
        material_count=material_count,
        material_signature=material_signature,
        material_imbalance=material_imbalance,
        has_opposite_color_bishops=has_opposite_color_bishops,
        piece_count=piece_count,
        backrank_sparse=backrank_sparse,
        mixedness=mixedness,
        phase=phase,
    )
```
The current code calls helpers inline inside the constructor; the rewrite hoists them to locals so phase can read them. This is a structural refactor of `classify_position` — minimal new logic, but the call sites of helpers move. Update the docstring at line 300-304 to mention the eight fields.

---

### `app/services/zobrist.py` — extend `PlyData` TypedDict + populate phase in both ply loops (SCHEMA-02)

**Analog:** itself

**Read first:** lines 22-24 (imports — note `from app.services.position_classifier import classify_position` already exists), lines 32-54 (`PlyData` TypedDict), lines 172-227 (intermediate-ply loop), lines 229-256 (final-position append).

**TypedDict extension pattern** (lines 32-54):
```python
class PlyData(TypedDict):
    ply: int
    white_hash: int
    black_hash: int
    full_hash: int
    move_san: str | None
    clock_seconds: float | None
    eval_cp: int | None
    eval_mate: int | None
    material_count: int
    material_signature: str
    material_imbalance: int
    has_opposite_color_bishops: bool
    piece_count: int
    backrank_sparse: bool
    mixedness: int
    endgame_class: int | None
    # NEW: phase: int     # 0=opening, 1=middlegame, 2=endgame
```
Use bare `int` here (not `Literal[0, 1, 2]`) — TypedDicts inside heavily-iterated loops typically use the wider type to avoid ty-check overhead, and the producer side (`classify_position`) already enforces the Literal. Planner can choose `Literal[0, 1, 2]` if desired; either passes ty.

**Intermediate-ply loop append pattern** (lines 208-227 — copy `classification.phase` into `PlyData`):
```python
plies.append(
    PlyData(
        ply=ply,
        white_hash=wh,
        black_hash=bh,
        full_hash=fh,
        move_san=move_san,
        clock_seconds=clock_seconds,
        eval_cp=eval_cp,
        eval_mate=eval_mate,
        material_count=classification.material_count,
        material_signature=classification.material_signature,
        material_imbalance=classification.material_imbalance,
        has_opposite_color_bishops=classification.has_opposite_color_bishops,
        piece_count=classification.piece_count,
        backrank_sparse=classification.backrank_sparse,
        mixedness=classification.mixedness,
        endgame_class=endgame_class,
        # NEW: phase=classification.phase,
    )
)
```

**Final-position append pattern** (lines 237-256 — second insertion point, identical pattern):
```python
plies.append(
    PlyData(
        ply=len(nodes),
        white_hash=wh,
        black_hash=bh,
        full_hash=fh,
        move_san=None,
        clock_seconds=None,
        eval_cp=None,
        eval_mate=None,
        material_count=classification.material_count,
        material_signature=classification.material_signature,
        material_imbalance=classification.material_imbalance,
        has_opposite_color_bishops=classification.has_opposite_color_bishops,
        piece_count=classification.piece_count,
        backrank_sparse=classification.backrank_sparse,
        mixedness=classification.mixedness,
        endgame_class=endgame_class_final,
        # NEW: phase=classification.phase,
    )
)
```
**Both ply loops must be modified.** The PR diff for SCHEMA-02 should touch exactly these two append blocks plus the TypedDict definition.

---

### `app/services/import_service.py` — bulk-insert payload + middlegame entry import-time eval (SCHEMA-02 + PHASE-IMP-01)

**Analog:** itself

**Read first:** lines 26-34 (imports, including `engine as engine_service` and `_board_at_ply`), lines 39-50 (`_board_at_ply` helper, reused unchanged), lines 500-522 (bulk-insert payload), lines 528-615 (Phase 78 eval pass — extend with middlegame call before the per-class endgame loop).

**Bulk-insert payload pattern** (lines 502-522 — sibling to `endgame_class` line 520):
```python
for ply_data in processing_result["plies"]:
    row: dict[str, Any] = {
        "game_id": game_id,
        "user_id": user_id,
        "ply": ply_data["ply"],
        "white_hash": ply_data["white_hash"],
        # ...
        "piece_count": ply_data["piece_count"],
        "backrank_sparse": ply_data["backrank_sparse"],
        "mixedness": ply_data["mixedness"],
        "endgame_class": ply_data["endgame_class"],
        # NEW: "phase": ply_data["phase"],
    }
    position_rows.append(row)
```

**Eval pass extension pattern** (lines 541-604 — current loop iterates `game_eval_data` and evaluates each endgame span entry; PHASE-IMP-01 inserts a single middlegame entry eval **before** the per-class endgame inner loop). Use this exact structure (mirrors the existing `eval_cp is not None or eval_mate is not None` skip + Sentry-tagged engine-error path):

```python
for g_id, pgn_text, plies_list in game_eval_data:
    # Phase 79 PHASE-IMP-01: middlegame entry eval — MIN(ply) where phase == 1.
    # At most one middlegame entry per game (later phase=1 stretches after an endgame
    # are NOT re-evaluated, mirroring lichess Divider's single-transition return).
    midgame_entries = [pd for pd in plies_list if pd["phase"] == 1]
    if midgame_entries:
        mid_pd = min(midgame_entries, key=lambda p: p["ply"])
        if mid_pd["eval_cp"] is None and mid_pd["eval_mate"] is None:
            board = _board_at_ply(pgn_text, mid_pd["ply"])
            if board is not None:
                eval_cp, eval_mate = await engine_service.evaluate(board)
                eval_calls_made += 1
                if eval_cp is None and eval_mate is None:
                    eval_calls_failed += 1
                    sentry_sdk.set_context("eval", {
                        "game_id": g_id,
                        "ply": mid_pd["ply"],
                        # NO pgn / NO user_id / NO fen — T-78-18
                    })
                    sentry_sdk.set_tag("source", "import")
                    sentry_sdk.set_tag("eval_kind", "middlegame_entry")
                    sentry_sdk.capture_message(
                        "import-time engine returned None tuple", level="warning"
                    )
                else:
                    await session.execute(
                        update(GamePosition)
                        .where(
                            GamePosition.game_id == g_id,
                            GamePosition.ply == mid_pd["ply"],
                        )
                        .values(eval_cp=eval_cp, eval_mate=eval_mate)
                    )

    # Existing Phase 78 per-class endgame span entry loop continues unchanged below
    class_plies: dict[int, list[PlyData]] = defaultdict(list)
    # ... lines 543-604 unchanged ...
```

**Key structural notes:**
- `_board_at_ply` is already defined at line 39-50, reused unchanged for the new call.
- The `eval_calls_made` / `eval_calls_failed` counters at lines 539-540 are reused so `eval_pass_ms` log line at lines 607-615 covers both endgame and middlegame counts (PHASE-IMP-02 budget instrumentation).
- T-78-17 lichess preservation: the `eval_cp is None and eval_mate is None` guard is the same one used for endgame span entries at line 568.
- No `asyncio.gather`: sequential `await engine_service.evaluate(board)` inside the same session per CLAUDE.md.
- Sentry tags: extend the existing `set_tag("source", "import")` pattern with a new `set_tag("eval_kind", "middlegame_entry")` for filterability vs `endgame_span_entry`. The endgame span loop should also gain `set_tag("eval_kind", "endgame_span_entry")` at line 589 for symmetry.

---

### `app/models/game_position.py` — add `phase` SmallInteger column (SCHEMA-01)

**Analog:** itself, lines 82-88 (sibling to `piece_count`, `backrank_sparse`, `mixedness`).

**Read first:** lines 1-7 (imports — `SmallInteger` already imported), lines 80-99 (the cluster of position-metadata columns).

**Existing sibling pattern** (line 80-88, exact analog — `piece_count`):
```python
# Lichess piece-count for endgame classification: count of Q+R+B+N for both sides combined.
# Nullable because existing rows won't have it until the backfill migration.
piece_count: Mapped[Optional[int]] = mapped_column(SmallInteger, nullable=True)

# Lichess middlegame detection columns (nullable — existing rows backfilled via reimport)
# True when < 4 pieces on either side's back rank
backrank_sparse: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
# Lichess mixedness score: measures how interleaved white/black pieces are (0-~400)
mixedness: Mapped[Optional[int]] = mapped_column(SmallInteger, nullable=True)
```

**New column to add** (sibling, immediately after `mixedness` at line 88):
```python
# Lichess Divider.scala phase classification: 0=opening, 1=middlegame, 2=endgame.
# Nullable column — populated by import-path code from import time forward; existing
# rows are populated by scripts/backfill_eval.py (PHASE-FILL-01). Nullability is
# transient and closes out post-backfill. PHASE-INV-01: phase=2 ⟺ endgame_class IS NOT NULL.
phase: Mapped[Optional[int]] = mapped_column(SmallInteger, nullable=True)
```

`Optional`, `Mapped`, `mapped_column`, `SmallInteger` are all already imported at lines 1-4. No `__table_args__` change (no new index in this phase per SPEC constraints — defer until a query measurably regresses).

---

### `scripts/backfill_eval.py` — add phase-column UPDATE pass + sibling middlegame entry stmt (PHASE-FILL-01, PHASE-FILL-02)

**Analog:** itself

**Read first:** lines 64-67 (imports), lines 112-133 (`_board_at_ply` reused unchanged), lines 136-231 (`_build_span_entry_stmt` — sibling to add), lines 234-362 (`run_backfill` — extend with two new passes), lines 365-400 (`parse_args`).

**Existing imports pattern** (line 57 — `update` is already imported; planner needs no new imports beyond `from app.services.position_classifier import ENDGAME_PIECE_COUNT_THRESHOLD, MIDGAME_MAJORS_AND_MINORS_THRESHOLD, MIDGAME_MIXEDNESS_THRESHOLD` for the SQL CASE expression's threshold interpolation per D-79-01):
```python
from sqlalchemy import func, select, text, update
```

**Phase-column UPDATE pass pattern** (NEW — runs FIRST inside `run_backfill` per D-79-02; chunked by `id` range, COMMIT per chunk, `WHERE phase IS NULL` predicate). Insert immediately after the session_maker bootstrap at lines 256-264, before the existing eval count phase at line 266:
```python
# Phase 79 PHASE-FILL-01: chunked SQL CASE UPDATE for phase column.
# Pure function of (piece_count, backrank_sparse, mixedness) — no PGN replay needed.
# Idempotent on re-run via WHERE phase IS NULL. Threshold constants are interpolated
# from position_classifier.py so SQL and Python share one source of truth (D-79-01).
PHASE_BACKFILL_CHUNK_SIZE = 10_000

phase_update_sql = text(f"""
    UPDATE game_positions
    SET phase = CASE
        WHEN piece_count <= {ENDGAME_PIECE_COUNT_THRESHOLD} THEN 2
        WHEN (piece_count <= {MIDGAME_MAJORS_AND_MINORS_THRESHOLD}
              OR backrank_sparse
              OR mixedness >= {MIDGAME_MIXEDNESS_THRESHOLD}) THEN 1
        ELSE 0
    END
    WHERE phase IS NULL
      AND id BETWEEN :lo AND :hi
""")

async with session_maker() as phase_session:
    # Find the id range to walk.
    bounds = (await phase_session.execute(
        text("SELECT COALESCE(MIN(id), 0), COALESCE(MAX(id), 0) FROM game_positions WHERE phase IS NULL")
    )).one()
    lo_total, hi_total = bounds
    if hi_total > 0:
        _log(f"Phase-column backfill: id range [{lo_total}, {hi_total}], chunk size {PHASE_BACKFILL_CHUNK_SIZE}")
        if dry_run:
            null_count = (await phase_session.execute(
                text("SELECT COUNT(*) FROM game_positions WHERE phase IS NULL")
            )).scalar_one()
            _log(f"--dry-run: would update {null_count} rows with NULL phase")
        else:
            cursor = lo_total
            updated_total = 0
            while cursor <= hi_total:
                chunk_hi = cursor + PHASE_BACKFILL_CHUNK_SIZE - 1
                result = await phase_session.execute(
                    phase_update_sql, {"lo": cursor, "hi": chunk_hi}
                )
                updated_total += result.rowcount or 0
                await phase_session.commit()
                cursor = chunk_hi + 1
                if updated_total and updated_total % (PHASE_BACKFILL_CHUNK_SIZE * 10) == 0:
                    _log(f"  phase backfill: {updated_total} rows updated, cursor={cursor}")
            _log(f"Phase-column backfill complete: {updated_total} rows updated")
    else:
        _log("Phase-column backfill: zero rows with NULL phase (no-op)")
```

**Sibling `_build_middlegame_entry_stmt` pattern** (NEW, parallel to lines 136-231 — the existing `_build_span_entry_stmt`). Insert directly below `_build_span_entry_stmt`. The middlegame stmt is **simpler** because there is no class and no island concept — just `MIN(ply)` per game where `phase=1`:

```python
def _build_middlegame_entry_stmt(
    user_id: int | None,
    limit: int | None,
) -> Select[tuple[int, int, int, str]]:
    """Build the middlegame entry SELECT statement (PHASE-FILL-02).

    Selects GamePosition rows where:
    1. eval_cp IS NULL AND eval_mate IS NULL  (row-level idempotency, T-78-17 lichess preserve)
    2. phase = 1                               (middlegame row)
    3. ply == MIN(ply) of phase=1 rows in the same game

    At most one middlegame entry per game. Later phase=1 stretches after an
    endgame are NOT re-evaluated (D-79-08 — mirrors lichess Divider's single
    Division(midGame, endGame) return).

    Optional filters mirror _build_span_entry_stmt: --user-id, --limit.
    """
    midgame_min = (
        select(
            GamePosition.game_id.label("gid"),
            func.min(GamePosition.ply).label("min_ply"),
        )
        .where(GamePosition.phase == 1)
        .group_by(GamePosition.game_id)
        .subquery("midgame_min")
    )

    stmt = (
        select(
            GamePosition.id,
            GamePosition.game_id,
            GamePosition.ply,
            Game.pgn,
        )
        .join(Game, Game.id == GamePosition.game_id)
        .join(
            midgame_min,
            (GamePosition.game_id == midgame_min.c.gid)
            & (GamePosition.ply == midgame_min.c.min_ply),
        )
        .where(
            GamePosition.eval_cp.is_(None),
            GamePosition.eval_mate.is_(None),
            GamePosition.phase == 1,
        )
    )

    if user_id is not None:
        stmt = stmt.where(GamePosition.user_id == user_id)

    stmt = stmt.order_by(GamePosition.game_id, GamePosition.ply)

    if limit is not None:
        stmt = stmt.limit(limit)

    return stmt
```

**Eval+write loop reuse pattern** (lines 287-349 — existing endgame-span eval loop). Refactor: extract the body of the eval+write loop into a helper `async def _evaluate_and_write_rows(rows, session, *, db, eval_kind)` that takes a `eval_kind` tag for Sentry differentiation, then call it twice — once with the span-entry rows from `_build_span_entry_stmt`, once with the middlegame rows from `_build_middlegame_entry_stmt`. This preserves the existing `skipped_no_board` / `skipped_engine_err` counters per pass and the COMMIT-every-100 cadence.

The Sentry context block at lines 308-320 gains a `set_tag("eval_kind", "middlegame_entry")` (or `"endgame_span_entry"`) per D-79-04.

**Order inside `run_backfill` per D-79-02:**
1. Phase-column UPDATE pass (cheap, SQL-bound) — see above
2. Endgame span-entry eval pass (existing Phase 78 work, lines 266-349) — refactored into helper
3. Middlegame entry eval pass (new) — calls same helper with new stmt + new tag

**`--dry-run` extension** (line 275-279): now reports three counts (phase-NULL row count + endgame span-entry NULL-eval count + middlegame-entry NULL-eval count) instead of one. Same exit-without-engine-start behaviour.

**No new CLI flag** per D-79-05 — `--phase-only` was rejected. Same `--db {dev|benchmark|prod}`, `--user-id`, `--dry-run`, `--limit` as Phase 78.

---

### `tests/test_position_classifier.py` — add `TestPhaseClassification` class (PHASE-VAL-01)

**Analog:** itself, `TestMaterialCount` class at lines 36-80 and `TestMaterialSignature` at lines 88+.

**Read first:** lines 1-25 (module imports + `board_from_fen` helper), lines 36-80 (`TestMaterialCount` — closest structural sibling).

**Existing test class pattern** (lines 36-80 — extend with sibling class):
```python
class TestMaterialCount:
    def test_starting_position_material_count(self, starting_board: chess.Board) -> None:
        result = classify_position(starting_board)
        assert result.material_count == _STARTING_MATERIAL_COUNT

    def test_bare_kings_zero_material(self) -> None:
        board = chess.Board()
        board.clear()
        board.set_piece_at(chess.E1, chess.Piece(chess.KING, chess.WHITE))
        board.set_piece_at(chess.E8, chess.Piece(chess.KING, chess.BLACK))
        result = classify_position(board)
        assert result.material_count == 0
```

**New class to add (sibling, ≥10 assertions per D-79-12):**

Required cases per D-79-12:
1. `test_starting_position_phase_opening` — `phase=0` (initial board, `piece_count=14`, no backrank-sparse, low mixedness)
2. `test_kqr_vs_kqr_phase_endgame` — `phase=2` because `piece_count=4 ≤ 6`
3. `test_kr_vs_kr_phase_endgame` — `phase=2` because `piece_count=2 ≤ 6`
4. `test_kq_vs_kq_with_8_pawns_each_phase_endgame` — `phase=2` because `piece_count=2 ≤ 6` (pawns excluded from piece_count)
5. `test_piece_count_11_mid_development_phase_opening` — `phase=0` unless backrank-sparse / mixedness fires (boundary at 10/11)
6. `test_piece_count_10_phase_middlegame` — `phase=1` by majors-and-minors threshold (boundary)
7. `test_backrank_sparse_high_piece_count_phase_middlegame` — `phase=1` (e.g. 12+ pieces but kingside castled both sides, < 4 on each backrank)
8. `test_high_mixedness_high_piece_count_phase_middlegame` — `phase=1` (mixedness ≥ 10)
9. `test_mixedness_9_boundary_not_middlegame` — NOT `phase=1` unless other criteria fire
10. `test_mixedness_10_boundary_middlegame` — `phase=1`
11. (recommended) `test_endgame_takes_precedence_over_middlegame` — `is_endgame` checked first; piece_count=6 + mixedness=20 → `phase=2` not 1

**Skeleton:**
```python
class TestPhaseClassification:
    """Divider parity tests — expected values sourced from lichess Divider.scala (NOT the Python implementation under test).

    Reference: https://github.com/lichess-org/scalachess/blob/master/core/src/main/scala/Divider.scala
    """

    def test_starting_position_phase_opening(self, starting_board: chess.Board) -> None:
        """Initial position: piece_count=14, no backrank sparse, low mixedness → opening."""
        result = classify_position(starting_board)
        assert result.phase == 0

    def test_kqr_vs_kqr_phase_endgame(self) -> None:
        """KQR vs KQR: piece_count=4 ≤ 6 → endgame (is_endgame wins even though is_middlegame would also fire)."""
        board = board_from_fen("4k3/8/8/8/8/8/8/R2QK3 w - - 0 1")
        # ...

    # ... ≥ 10 total assertions ...
```

The `starting_board` fixture is already used in existing tests (line 37) — see `tests/conftest.py` for definition. Use `board_from_fen` helper for non-trivial positions; use `board.clear()` + `board.set_piece_at()` for trivially constructed positions (matches existing style at lines 44-48).

---

### `alembic/versions/{new}_add_phase_column.py` — new migration (SCHEMA-01)

**Analog:** `alembic/versions/20260502_125433_c92af8282d1a_reshape_ix_gp_user_endgame_game_for_.py` (Phase 78 migration — adjacent in time, same file under modification).

**Read first:** the full migration above (already excerpted) plus any existing `op.add_column` example in the codebase. Generate via `uv run alembic revision --autogenerate -m "add phase column to game_positions"`. The autogenerator will pick up the new `phase` column on the model.

**Down-revision:** `c92af8282d1a` (the latest Phase 78 migration shown above). Phase 79's branch is rebased on Phase 78, so the migration chain is `... → 4be323b0e0fd → c92af8282d1a → {new phase migration}`.

**Migration body pattern (per D-79-11, no embedded backfill):**
```python
def upgrade() -> None:
    """Add nullable phase SmallInteger column to game_positions.

    Phase 79 SCHEMA-01: nullable because existing rows are populated by
    scripts/backfill_eval.py (PHASE-FILL-01), not by this migration. New rows
    inserted by the import path (after this migration deploys) are populated
    at insert time via classify_position(board).phase.
    """
    op.add_column(
        "game_positions",
        sa.Column("phase", sa.SmallInteger(), nullable=True),
    )


def downgrade() -> None:
    """Drop the phase column."""
    op.drop_column("game_positions", "phase")
```

**Reversibility:** `op.drop_column` is clean and reversible per SCHEMA-01 acceptance.
**Apply path on prod:** `deploy/entrypoint.sh` runs `alembic upgrade head` automatically on backend container startup. Operator manually applies on benchmark via `BACKFILL_BENCHMARK_DB_URL=... uv run alembic upgrade head` before running the benchmark backfill.

---

## Shared Patterns

### Sentry context tagging on engine errors

**Source:** `scripts/backfill_eval.py:307-320` and `app/services/import_service.py:583-593`.
**Apply to:** All new engine-error paths in `import_service.py` (middlegame entry import-time eval) and `backfill_eval.py` (middlegame entry backfill eval).

Verbatim pattern (`backfill_eval.py:307-320`):
```python
sentry_sdk.set_context(
    "backfill_eval",
    {
        "game_position_id": row.id,
        "game_id": row.game_id,
        "ply": row.ply,
        "db_target": db,
    },
)
sentry_sdk.set_tag("source", "backfill")
sentry_sdk.capture_message(
    "backfill engine returned (None, None) tuple", level="warning"
)
```
**Phase 79 extension:** add `sentry_sdk.set_tag("eval_kind", "middlegame_entry")` (and the symmetric `"endgame_span_entry"` on the existing path) so Sentry can filter the two row sets independently. Bounded context — **never** include `pgn`, `fen`, or `user_id` (T-78-13 / T-78-18 information-disclosure mitigation).

---

### Row-level idempotency on backfill writes

**Source:** `scripts/backfill_eval.py:217-220` (eval cols) and the new `WHERE phase IS NULL` predicate.
**Apply to:** Both new backfill passes.

```python
.where(
    GamePosition.eval_cp.is_(None),
    GamePosition.eval_mate.is_(None),
)
```
For the phase column, the resume predicate is `WHERE phase IS NULL` interpolated into the chunked SQL UPDATE. No cross-row hash dedup (D-10 stance carried over verbatim).

---

### COMMIT-every-N batching with resume predicate

**Source:** `scripts/backfill_eval.py:333-340`.
**Apply to:** Both new backfill passes.

```python
# D-09: COMMIT every 100 evals so a mid-run kill loses at most 100 rows.
if (i + 1) % EVAL_BATCH_SIZE == 0:
    await session.commit()
    _log(
        f"Committed {i + 1}/{len(rows)} rows "
        f"(evaluated={evaluated}, "
        f"skipped_no_board={skipped_no_board}, "
        f"skipped_engine_err={skipped_engine_err})"
    )
```
For the phase-column SQL UPDATE pass, COMMIT happens per chunk (10_000 rows, see PHASE-FILL-01 above). For the middlegame entry eval pass, COMMIT every 100 (same `EVAL_BATCH_SIZE` constant reused).

---

### Async session sequential execution (no `asyncio.gather` over same session)

**Source:** CLAUDE.md hard constraint + `import_service.py:528-615` and `backfill_eval.py:295-340`.
**Apply to:** All eval-loop modifications in this phase.

Engine calls inside the same session must be sequential `await engine_service.evaluate(board)` — never wrapped in `asyncio.gather`. The shared `asyncio.Lock` inside the engine wrapper would serialize them anyway, but the constraint is also on the session itself (SQLAlchemy `AsyncSession` is not safe for concurrent coroutines).

---

### TypedDict + bulk-insert payload symmetry

**Source:** `zobrist.py:32-54` (PlyData) ↔ `import_service.py:502-521` (row dict).
**Apply to:** Adding any new column on `game_positions` (here: `phase`).

Every key added to `PlyData` must be added to the bulk-insert row dict in `import_service.py` with the **same key name**. The dict is consumed by `game_repository.bulk_insert_positions()` (line 526) which maps keys 1:1 to columns. A drift between `PlyData` and the row dict surfaces only at INSERT time as a NOT-NULL violation or a silent NULL.

---

## No Analog Found

None. Every modification has a direct in-file analog from Phase 78. The new alembic migration's analog is a sibling Phase 78 migration in the same directory.

---

## Metadata

**Analog search scope:**
- `app/services/position_classifier.py` (full read)
- `app/services/zobrist.py` (full read)
- `app/services/import_service.py` (lines 1-50, 480-650 — top imports + bulk-insert payload + eval pass)
- `app/models/game_position.py` (full read)
- `scripts/backfill_eval.py` (full read)
- `tests/test_position_classifier.py` (lines 1-100 — header + first two test classes)
- `app/repositories/endgame_repository.py` (lines 1-50 — to confirm `ENDGAME_PIECE_COUNT_THRESHOLD = 6` lives there)
- `alembic/versions/` directory listing + Phase 78 migration `c92af8282d1a` (full read)

**Files scanned:** 8.
**Pattern extraction date:** 2026-05-02.
