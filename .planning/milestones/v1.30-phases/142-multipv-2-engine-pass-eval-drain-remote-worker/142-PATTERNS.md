# Phase 142: MultiPV=2 Engine Pass + Eval Drain + Remote Worker - Pattern Map

**Mapped:** 2026-06-29
**Files analyzed:** 5
**Analogs found:** 5 / 5

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `app/services/engine.py` (add `_analyse_multipv2` + `evaluate_nodes_multipv2`) | service | request-response | `_analyse_with_pv` / `evaluate_nodes_with_pv` (same file, lines 486–542) | exact |
| `app/services/eval_drain.py` (add `_run_multipv2_pass` after line 2006; add D-05 second-best recovery after line 1973) | service | CRUD / batch | `_fill_engine_game_flaw_pvs` (line 991) + `_batch_update_pv_rows` (line 443) | exact |
| `app/schemas/eval_remote.py` (extend `SubmitEval` with 3 optional fields) | model/schema | request-response | `SubmitEval` (lines 30–35); backward-compat precedent `job_id: int \| None = None` (line 27) | exact |
| `app/routers/eval_remote.py` (thread second-best through `_apply_submit`) | controller | request-response | `_apply_submit` (lines 183–328) itself | exact (modification) |
| `app/models/game_flaw.py` (blob-key comment update at lines 109–116) | model | — | `allowed_pv_lines` / `missed_pv_lines` (lines 120–121) | exact (doc only) |
| `scripts/validate_multipv_budget.py` (new histogram tool) | utility/script | batch | `scripts/tactic_tagger_report.py` + `scripts/backfill_tactic_tags.py` | role-match |

---

## Pattern Assignments

### `app/services/engine.py` — `_analyse_multipv2` + `evaluate_nodes_multipv2`

**Analog:** `_analyse_with_pv` (lines 486–519) + `evaluate_nodes_with_pv` (lines 521–542) in the same file.

**Constants pattern** (lines 94–95, reuse as-is — D-06):
```python
_NODES_BUDGET: int = 1_000_000  # EVAL-02
_NODES_TIMEOUT_S: float = 5.0   # 4x prod p90
```

**Core `_analyse_with_pv` pattern to copy** (lines 486–519):
```python
async def _analyse_with_pv(
    self,
    board: chess.Board,
    limit: chess.engine.Limit,
    timeout: float,
) -> chess.engine.InfoDict | None:
    if not self._started:
        return None
    idx = await self._available.get()
    try:
        protocol = self._protocols[idx]
        if protocol is None:
            return None
        try:
            info = await asyncio.wait_for(
                protocol.analyse(board, limit),
                timeout=timeout,
            )
        except (
            asyncio.TimeoutError,
            chess.engine.EngineError,
            chess.engine.EngineTerminatedError,
        ):
            await self._restart_worker(idx)
            return None
        return info
    finally:
        self._available.put_nowait(idx)
```

**New `_analyse_multipv2` — change `protocol.analyse(board, limit)` to `protocol.analyse(board, limit, multipv=2)` and return type to `list[chess.engine.InfoDict] | None`.**

**Core `evaluate_nodes_with_pv` wrapper pattern to copy** (lines 521–542):
```python
async def evaluate_nodes_with_pv(
    self,
    board: chess.Board,
) -> tuple[int | None, int | None, str | None, str | None]:
    info = await self._analyse_with_pv(
        board, chess.engine.Limit(nodes=_NODES_BUDGET), _NODES_TIMEOUT_S
    )
    if info is None:
        return None, None, None, None
    eval_cp, eval_mate = _score_to_cp_mate(info)
    best_move = _pv_to_best_move(info)
    pv_string = _pv_to_uci_string(info)
    return eval_cp, eval_mate, best_move, pv_string
```

**New `evaluate_nodes_multipv2` — widen return to 7-tuple; call `_analyse_multipv2`; guard `len(info_list) > 1` for single-legal-move (Pitfall 2); set `su=""` (not `None`) when no second move (Pitfall 3).**

**Module-level wrapper pattern** — mirrors the existing module-level `evaluate_nodes_with_pv` function (after line 542):
```python
async def evaluate_nodes_with_pv(board: chess.Board) -> tuple[...]:
    if _pool is None:
        return None, None, None, None
    return await _pool.evaluate_nodes_with_pv(board)
```

---

### `app/services/eval_drain.py` — `_run_multipv2_pass` + D-05 second-best recovery

**Analog 1 — `_fill_engine_game_flaw_pvs`** (lines 991–1028): exact pattern for the D-05 eval-gap recovery (structure, session-free gather, engine_result_map mutation).

**`_fill_engine_game_flaw_pvs` signature and structure** (lines 991–1028):
```python
async def _fill_engine_game_flaw_pvs(
    game_id: int,
    targets: Sequence[_FullPlyEvalTarget],
    dedup_map: dict[int, tuple[int | None, int | None, str | None]],
    engine_result_map: dict[int, tuple[int | None, int | None, str | None, str | None]],
    is_lichess_eval_game: bool,
) -> None:
    """SEED-056: targeted second engine pass for pv-less opening flaw plies (engine games).
    ...
    No-op for lichess games ... MUST be called with NO session open.
    """
    if is_lichess_eval_game:
        return
    has_opening_dedup = any(
        not t.is_terminal and t.ply <= _DEDUP_MAX_PLY and t.full_hash in dedup_map for t in targets
    )
    if not has_opening_dedup:
        return
    pv_gap_targets = await _missing_flaw_pv_targets(...)
    if not pv_gap_targets:
        return
    pv_gap_results = await asyncio.gather(
        *(engine_service.evaluate_nodes_with_pv(t.board) for t in pv_gap_targets)
    )
    for t, res in zip(pv_gap_targets, pv_gap_results, strict=True):
        if res[3] is not None:
            engine_result_map[t.ply] = res
```

**Call site for SEED-056 (line 1971)** — D-05 second-best recovery call goes immediately after this:
```python
    await _fill_engine_game_flaw_pvs(
        game_id, targets, dedup_map, engine_result_map, is_lichess_eval_game
    )

    # NEW: D-05 multipv second-best recovery for dedup/lichess flaw plies
    await _fill_engine_game_flaw_second_best(...)
```

**Analog 2 — `_batch_update_pv_rows`** (lines 443–480): exact pattern for the JSONB batched UPDATE (`_batch_update_flaw_pv_lines`).

**`_batch_update_pv_rows` write pattern** (lines 443–480):
```python
async def _batch_update_pv_rows(
    session: AsyncSession,
    game_id: int,
    pv_rows: list[tuple[int, str]],
) -> None:
    if not pv_rows:
        return
    params: dict[str, int | str] = {"game_id": game_id}
    values_parts: list[str] = []
    for i, (ply, pv) in enumerate(pv_rows):
        params[f"ply_{i}"] = ply
        params[f"pv_{i}"] = pv
        values_parts.append(f"(CAST(:ply_{i} AS smallint), CAST(:pv_{i} AS text))")
    values_sql = ", ".join(values_parts)
    sql = sa.text(
        f"UPDATE game_positions"
        f" SET pv = v.pv"
        f" FROM (VALUES {values_sql}) AS v(ply, pv)"
        f" WHERE game_positions.game_id = :game_id"
        f" AND game_positions.ply = v.ply"
    )
    await session.execute(sql, params)
```

**For JSONB blob write:** adapt using `CAST(:blob_{i} AS jsonb)` in the VALUES clause; target `game_flaws` table with `(flaw_id, allowed_blob, missed_blob)` shape. One round-trip per game.

**Call site for `_run_multipv2_pass`** (after line 2006, inside the write session):
```python
    async with async_session_maker() as write_session:
        failed_ply_count = await _apply_full_eval_results(...)

        # EVAL-06 / D-117-08: classify game_flaws ...
        await _classify_and_fill_oracle(write_session, game_id, engine_result_map)

        # Phase 142 MPV-02: assemble + write allowed_pv_lines / missed_pv_lines blobs.
        # Runs AFTER classify so flaw plies are known. Same txn = atomic with flaw rows.
        await _run_multipv2_pass(write_session, game_id, engine_result_map, second_best_map)

        await _upsert_opening_cache(...)
```

---

### `app/schemas/eval_remote.py` — extend `SubmitEval`

**Analog:** existing `SubmitEval` (lines 30–35) and backward-compat precedent `job_id: int | None = None` on `SubmitRequest` (line 27 / 44).

**Current `SubmitEval`** (lines 30–35):
```python
class SubmitEval(BaseModel):
    ply: int = Field(ge=0)
    eval_cp: int | None
    eval_mate: int | None
    best_move: str | None  # UCI string
    pv: str | None  # space-joined UCI, up to 12 plies
```

**Extension pattern — add three optional fields with `= None` default** (mirrors `job_id: int | None = None` at line 44):
```python
    # Phase 142 MPV-02: second-best per ply for JSONB blob assembly (D-03).
    # Default None = old worker omit → server treats as no second-best.
    second_cp: int | None = None
    second_mate: int | None = None
    second_uci: str | None = None
```

No change to `SubmitRequest` structure (D-03 explicitly rejects a parallel list).

---

### `app/routers/eval_remote.py` — thread second-best through `_apply_submit`

**Analog:** `_apply_submit` (lines 183–328) itself — the write path mirrors `_full_drain_tick`.

**`engine_result_map` construction pattern** (lines 241–243) — widen to carry second-best in a parallel map:
```python
    # Existing:
    engine_result_map: dict[int, tuple[int | None, int | None, str | None, str | None]] = {
        e.ply: (e.eval_cp, e.eval_mate, e.best_move, e.pv) for e in body.evals
    }
    # Add parallel second-best map (D-03 / Open Question #2 recommendation):
    second_best_map: dict[int, tuple[int | None, int | None, str | None]] = {
        e.ply: (e.second_cp, e.second_mate, e.second_uci)
        for e in body.evals
        if e.second_cp is not None or e.second_uci is not None
    }
```

**Write session pattern** (lines 249–318) — add `_run_multipv2_pass` call after `_classify_and_fill_oracle` at line 259, same as the eval_drain.py insertion point:
```python
    async with async_session_maker() as write_session:
        failed_ply_count = await _apply_full_eval_results(...)
        await _classify_and_fill_oracle(write_session, game_id, engine_result_map)
        # Phase 142 MPV-02: write JSONB blobs (same txn — atomic with flaw rows).
        await _run_multipv2_pass(write_session, game_id, engine_result_map, second_best_map)
        ...
        await write_session.commit()
```

---

### `app/models/game_flaw.py` — blob-key comment (lines 109–116, doc-only)

**No structural change needed** — `allowed_pv_lines` and `missed_pv_lines` columns were added in Phase 141. Only the comment block at lines 109–116 may need updating to reflect Phase 142 population semantics if the planner decides to extend it.

**Existing column pattern** (lines 120–121):
```python
allowed_pv_lines: Mapped[list[Any] | None] = mapped_column(JSONB, nullable=True, deferred=True)
missed_pv_lines: Mapped[list[Any] | None] = mapped_column(JSONB, nullable=True, deferred=True)
```

`deferred=True` means the blob write must use raw `sa.text()` UPDATE, not ORM attribute assignment, to avoid `MissingGreenlet` (Pitfall 4 in RESEARCH.md).

---

### `scripts/validate_multipv_budget.py` (new)

**Analog:** `scripts/tactic_tagger_report.py` (structure, `_REPORT_DIR`, argparse, `--check-goals`) + `scripts/backfill_tactic_tags.py` (`--db` arg, `sys.path.insert` bootstrap, `db_url_for_target`).

**Report dir pattern** (`tactic_tagger_report.py` line 96):
```python
_REPORT_DIR = Path(__file__).resolve().parents[1] / "reports" / "tactic-tagger"
```
Adapt to: `Path(__file__).resolve().parents[1] / "reports" / "multipv-validation"`

**argparse + `--db` pattern** (`backfill_tactic_tags.py` lines 85–148):
```python
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.config import db_url_for_target, settings  # noqa: E402

def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="...")
    parser.add_argument(
        "--db",
        choices=["dev", "benchmark", "prod"],
        required=True,
        help="DB target: dev (localhost:5432), benchmark (localhost:5433), prod (SSH tunnel).",
    )
    ...
```

**`--check-goals` exit-code pattern** (`tactic_tagger_report.py` lines 546–568):
```python
parser.add_argument("--check-goals", action="store_true", help="Exit 0=pass, 1=fail.")
...
_REPORT_DIR.mkdir(parents=True, exist_ok=True)
out_path = _REPORT_DIR / f"validate-multipv-budget-{generated.strftime('%Y-%m-%d')}.md"
```

**Win-prob margin computation** — use `eval_cp_to_expected_score` from `app/services/eval_utils.py` (do not hand-roll sigmoid). `PvNode` import from `app/services/forcing_line_gate.py`.

**Read blobs via explicit column projection** (Pitfall 4 — never `select(GameFlaw)` for deferred columns):
```python
select(GameFlaw.id, GameFlaw.allowed_pv_lines, GameFlaw.missed_pv_lines).where(
    GameFlaw.allowed_pv_lines.isnot(None)
)
```

---

## Shared Patterns

### Session discipline (CLAUDE.md hard rule)
**Source:** `eval_drain.py` lines 1971–1997 + `eval_remote.py` lines 228–249
**Apply to:** `_fill_engine_game_flaw_second_best` (D-05 recovery), `evaluate_nodes_multipv2` gather in drain Step 3
All `asyncio.gather` engine calls must complete BEFORE the write session opens. No gather inside an open `AsyncSession`.

### CAST() not `::` in raw SQL
**Source:** `_batch_update_pv_rows` (eval_drain.py lines 457–471)
**Apply to:** `_batch_update_flaw_pv_lines` (JSONB write)
asyncpg requires `CAST(:param AS jsonb)` not `::jsonb` syntax in `sa.text()` statements.

### Sentry capture pattern
**Source:** `eval_remote.py` lines 286–298
**Apply to:** Any exception paths in `_run_multipv2_pass` or the D-05 recovery
```python
sentry_sdk.set_context("eval", {"game_id": game_id, ...})
sentry_sdk.set_tag("source", "multipv_pass")
sentry_sdk.capture_exception(exc)
```
Never embed variable data in message strings (CLAUDE.md).

### Backward-compatible schema extension
**Source:** `SubmitRequest.job_id: int | None = None` (eval_remote.py line 27 / 44)
**Apply to:** Three new `SubmitEval` fields — all default `None` so un-upgraded workers parse without error.

---

## No Analog Found

All files have close analogs in the codebase. No entries.

---

## Metadata

**Analog search scope:** `app/services/engine.py`, `app/services/eval_drain.py`, `app/routers/eval_remote.py`, `app/schemas/eval_remote.py`, `app/models/game_flaw.py`, `scripts/tactic_tagger_report.py`, `scripts/backfill_tactic_tags.py`
**Files scanned:** 7
**Pattern extraction date:** 2026-06-29
