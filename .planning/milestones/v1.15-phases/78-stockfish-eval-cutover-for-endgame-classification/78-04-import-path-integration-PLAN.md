---
phase: 78
plan: 04
type: execute
wave: 2
depends_on: [78-02]
files_modified:
  - app/services/import_service.py
  - tests/services/test_import_service_eval.py
autonomous: true
requirements: [IMP-01, IMP-02]
tags: [import, span-entry, eval, sentry, timing]

must_haves:
  truths:
    - "Import path evaluates per-class span-entry rows where lichess `%eval` did NOT already populate them (IMP-01); lichess values are byte-for-byte unchanged."
    - "Insertion point is `_flush_batch` in `app/services/import_service.py`, AFTER `bulk_insert_positions` and BEFORE the final `session.commit()` (RESEARCH.md Option A)."
    - "Span entries are detected from the in-memory `plies` list returned by `process_game_pgn` — group by `endgame_class`, find `MIN(ply)` for groups with `count >= ENDGAME_PLY_THRESHOLD`."
    - "On engine error / timeout: skip row, leave eval NULL, capture to Sentry with bounded context (`game_id`, `ply`, `endgame_class`) per D-11 — DO NOT fail the import."
    - "Sentry context MUST NOT include the PGN, FEN, or any unbounded user-identifying field (information disclosure mitigation)."
    - "Timing instrumentation logs p50/p95 wall-clock added per game; IMP-02 budget is sub-1 second per typical game (1-3 span entries × ~70ms)."
    - "No `asyncio.gather` over the same `AsyncSession` (CLAUDE.md hard constraint)."
  artifacts:
    - path: "app/services/import_service.py"
      provides: "Import-time eval of new span entries; Sentry on engine error; timing instrumentation"
      contains: "engine.evaluate"
    - path: "tests/services/test_import_service_eval.py"
      provides: "IMP-01 integration test: chess.com game (no lichess eval) → eval populated; lichess game with eval → unchanged"
      min_lines: 60
  key_links:
    - from: "app/services/import_service.py:_flush_batch"
      to: "app/services/engine.py evaluate"
      via: "import + await call"
      pattern: "await engine_service.evaluate\\(board\\)"
    - from: "app/services/import_service.py"
      to: "GamePosition (UPDATE eval_cp / eval_mate)"
      via: "sa.update"
      pattern: "update\\(GamePosition\\).*eval_cp"
    - from: "app/services/import_service.py"
      to: "Sentry"
      via: "set_context + capture_exception"
      pattern: "sentry_sdk.set_context\\(\"eval\""
---

<objective>
Hook the engine wrapper from Plan 78-02 into the import pipeline so newly imported games have eval populated on per-class span-entry rows. This makes IMP-01/IMP-02 satisfy the SPEC requirement that future imports of chess.com games (which have no lichess `%eval`) get evaluated automatically — no manual backfill needed for new data.

Purpose: The backfill script (Plan 78-03) handles historical data; this plan handles new imports going forward. Without this, every chess.com import after the cutover would create endgame span-entry rows with NULL eval, causing them to fall out of conv/recov classification.

Output: Modified `app/services/import_service.py` with a post-insert eval pass on span-entry rows, timing instrumentation, Sentry error capture, plus a Wave 0 integration test covering both the chess.com-eval-populated and lichess-eval-preserved branches.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@.planning/milestones/v1.15-phases/78-stockfish-eval-cutover-for-endgame-classification/78-CONTEXT.md
@.planning/milestones/v1.15-phases/78-stockfish-eval-cutover-for-endgame-classification/78-SPEC.md
@.planning/milestones/v1.15-phases/78-stockfish-eval-cutover-for-endgame-classification/78-RESEARCH.md
@.planning/milestones/v1.15-phases/78-stockfish-eval-cutover-for-endgame-classification/78-PATTERNS.md
@.planning/milestones/v1.15-phases/78-stockfish-eval-cutover-for-endgame-classification/78-VALIDATION.md
@.planning/milestones/v1.15-phases/78-stockfish-eval-cutover-for-endgame-classification/78-02-engine-wrapper-PLAN.md
@CLAUDE.md
@app/services/import_service.py
@app/services/zobrist.py

<interfaces>
<!-- Engine wrapper API from Plan 78-02 -->
```python
from app.services import engine as engine_service
# evaluate(board: chess.Board) -> tuple[int | None, int | None]
# Returns (None, None) on engine timeout / crash. Wrapper handles 2s timeout
# and engine restart internally — caller does NOT wrap in another wait_for.
```

<!-- PlyData TypedDict from app/services/zobrist.py:33-55 (verify exact field names) -->
```python
class PlyData(TypedDict):
    ply: int
    full_hash: int
    white_hash: int
    black_hash: int
    material_imbalance: int
    eval_cp: int | None
    eval_mate: int | None
    endgame_class: int | None
    # ... other fields
```

<!-- _flush_batch insertion point — app/services/import_service.py around lines 488-506 -->
```python
# Step 5 (existing): bulk insert positions
if position_rows:
    await game_repository.bulk_insert_positions(session, position_rows)

# >>> NEW STEP 5a: eval pass on span-entry rows (IMP-01) <<<

# Step 6 (existing): bulk UPDATE move_count / result_fen
if move_counts:
    await session.execute(update(Game)...)

await session.commit()  # final commit
```

<!-- Sentry context pattern (existing in zobrist.py:157-160 + import_service.py:452-455) -->
```python
sentry_sdk.set_context("eval", {
    "game_id": game_id,
    "ply": span_entry_ply,
    "endgame_class": ec,
})
sentry_sdk.set_tag("source", "import")
sentry_sdk.capture_exception(exc)
# DO NOT include pgn, fen, or full PlyData — bounded fields only.
```

<!-- ENDGAME_PLY_THRESHOLD — same constant as Plan 78-03 -->
```python
from app.repositories.endgame_repository import ENDGAME_PLY_THRESHOLD
```
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Wave 0 — IMP-01 integration test</name>
  <files>tests/services/test_import_service_eval.py</files>
  <read_first>
    - tests/conftest.py (existing fixtures)
    - tests/services/test_import_service.py if exists, OR tests/test_import_service.py — the existing import test setup
    - app/services/import_service.py (current `_flush_batch` shape and how it's called from `import_user_games`)
    - .planning/milestones/v1.15-phases/78-stockfish-eval-cutover-for-endgame-classification/78-VALIDATION.md "Wave 0 Requirements"
  </read_first>
  <behavior>
    - Test 1 (chess.com path): import a synthetic chess.com game whose PGN reaches an endgame; mock `engine.evaluate` to return `(150, None)`; assert the span-entry row has `eval_cp=150` after import.
    - Test 2 (lichess preservation): import a synthetic lichess game whose PGN includes `%eval` annotations covering the span-entry ply; assert the original lichess values are unchanged AND `engine.evaluate` was NOT called for that ply.
    - Test 3 (engine error): mock `engine.evaluate` to return `(None, None)`; assert the span-entry row's `eval_cp` / `eval_mate` remain NULL AND a Sentry call was issued with `set_context("eval", ...)`.
    - Test 4 (no endgame): import a short game (no plies cross the endgame threshold); assert `engine.evaluate` was NOT called at all (zero-engine-call short-circuit for non-endgame games).
    - Test 5 (multi-class span entries): import a game that crosses two endgame classes (e.g. mixed → pawn) with each class having ≥ threshold plies; assert evaluate is called once per class span entry (not once per ply).
  </behavior>
  <action>
    Create `tests/services/test_import_service_eval.py` (the directory exists from Plan 78-02). Use existing import-service test fixtures if any; otherwise build a minimal `import_user_games` invocation around a synthetic PGN.

    Mock `app.services.engine.evaluate` via `unittest.mock.patch` so tests don't depend on Stockfish. Use `from unittest.mock import AsyncMock, patch`.

    Test skeleton:
    ```python
    """Import-time engine eval integration tests (IMP-01). Phase 78 Wave 0."""
    from __future__ import annotations

    from unittest.mock import AsyncMock, patch

    import pytest

    pytestmark = pytest.mark.asyncio


    # PGN that reaches a recognizable endgame at ply ~30 with at least 6 endgame plies
    # Executor: pick a real game from tests/fixtures/ if available, or construct a synthetic
    # one that pushes pieces off until piece_count <= ENDGAME_PIECE_COUNT_THRESHOLD for ≥6 plies.
    CHESS_COM_PGN_REACHES_ENDGAME = """[Event "Test"]
    [Site "chess.com"]
    [White "user_a"]
    [Black "user_b"]
    [Result "1-0"]
    [TimeControl "300"]
    ...
    """  # executor finalizes from existing fixtures

    LICHESS_PGN_WITH_EVAL_AT_SPAN_ENTRY = """[Event "Test"]
    [Site "lichess.org"]
    ...
    1. e4 { [%eval 0.3] } e5 { [%eval 0.0] } ...
    """  # executor finalizes; %eval must be present at the span-entry ply


    class TestImportEvalChessCom:
        async def test_chess_com_import_populates_span_entry_eval(self, db_session, ...):
            with patch("app.services.import_service.engine_service.evaluate",
                       new=AsyncMock(return_value=(150, None))) as mock_eval:
                await import_chess_com_game(db_session, CHESS_COM_PGN_REACHES_ENDGAME, user=...)
            # At least one engine call (1 per span-entry class)
            assert mock_eval.call_count >= 1
            # Span-entry row has eval_cp=150
            ...


    class TestImportEvalLichessPreservation:
        async def test_lichess_eval_at_span_entry_skips_engine(self, db_session, ...):
            with patch("app.services.import_service.engine_service.evaluate",
                       new=AsyncMock(return_value=(999, None))) as mock_eval:
                await import_lichess_game(db_session, LICHESS_PGN_WITH_EVAL_AT_SPAN_ENTRY, user=...)
            # The lichess %eval covers the span entry → engine MUST NOT be called for that ply
            # (other span entries without lichess eval may still trigger calls; assertion is
            #  per-row, not per-game)
            ...
            # Original lichess value preserved
            ...


    class TestImportEvalEngineError:
        async def test_engine_error_skips_row_and_captures_to_sentry(self, db_session, ...):
            with patch("app.services.import_service.engine_service.evaluate",
                       new=AsyncMock(return_value=(None, None))), \
                 patch("app.services.import_service.sentry_sdk.set_context") as mock_ctx, \
                 patch("app.services.import_service.sentry_sdk.capture_exception") as mock_capture:
                await import_chess_com_game(db_session, CHESS_COM_PGN_REACHES_ENDGAME, user=...)
            # The (None, None) return is treated as engine error → no UPDATE issued for that row
            # AND Sentry context set with bounded fields
            mock_ctx.assert_called()
            ctx_args = mock_ctx.call_args
            assert ctx_args.args[0] == "eval"
            ctx_payload = ctx_args.args[1]
            assert "game_id" in ctx_payload
            assert "ply" in ctx_payload
            assert "endgame_class" in ctx_payload
            # Information disclosure mitigation: NO pgn, NO user_id, NO fen
            assert "pgn" not in ctx_payload
            assert "user_id" not in ctx_payload
            assert "fen" not in ctx_payload


    class TestImportEvalNoEndgame:
        async def test_short_game_zero_engine_calls(self, db_session, ...):
            short_pgn = "[Event ...] 1. e4 e5 1/2-1/2"  # 2 plies, no endgame
            with patch("app.services.import_service.engine_service.evaluate",
                       new=AsyncMock(return_value=(0, None))) as mock_eval:
                await import_chess_com_game(db_session, short_pgn, user=...)
            assert mock_eval.call_count == 0


    class TestImportEvalMultiClass:
        async def test_two_class_span_entries_two_evaluations(self, db_session, ...):
            ...  # PGN with two endgame classes each ≥ 6 plies → 2 evaluate calls
    ```

    The patch target `app.services.import_service.engine_service.evaluate` is intentional — Task 2's executor will import the module as `from app.services import engine as engine_service` so the test patches the alias, not the wrapper module directly. This allows alternate import-style choices without breaking the test.

    Tests will FAIL initially because `app.services.import_service` does not yet import `engine_service` or call `evaluate`. RED phase.
  </action>
  <verify>
    <automated>
      uv run pytest tests/services/test_import_service_eval.py -x 2>&1 | tail -30
      # Expected RED: AttributeError on engine_service in import_service module until Task 2 lands.
    </automated>
  </verify>
  <acceptance_criteria>
    - File `tests/services/test_import_service_eval.py` exists.
    - `grep -n "TestImportEvalChessCom\|TestImportEvalLichessPreservation\|TestImportEvalEngineError\|TestImportEvalNoEndgame\|TestImportEvalMultiClass" tests/services/test_import_service_eval.py` returns at least 5 matches.
    - `grep -n "pgn.*not in\|user_id.*not in\|fen.*not in" tests/services/test_import_service_eval.py` returns matches (information-disclosure assertion present).
    - Pytest output shows AttributeError or NameError on `engine_service` (RED phase confirmed).
  </acceptance_criteria>
  <done>Wave 0 test file present (RED).</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Hook engine eval into _flush_batch (GREEN)</name>
  <files>app/services/import_service.py</files>
  <read_first>
    - app/services/import_service.py (full read of `_flush_batch` lines 399-506; existing Sentry usage 452-455; existing imports lines 1-40)
    - app/services/zobrist.py:33-55 (PlyData TypedDict — exact field names; pgn variable in scope at flush time)
    - app/repositories/endgame_repository.py (ENDGAME_PLY_THRESHOLD constant location)
    - .planning/milestones/v1.15-phases/78-stockfish-eval-cutover-for-endgame-classification/78-RESEARCH.md "Import-Path Integration" section (lines 454-518) — the exact Option A implementation
    - .planning/milestones/v1.15-phases/78-stockfish-eval-cutover-for-endgame-classification/78-PATTERNS.md "app/services/import_service.py" section
    - .planning/milestones/v1.15-phases/78-stockfish-eval-cutover-for-endgame-classification/78-CONTEXT.md (D-11 Sentry pattern)
    - tests/services/test_import_service_eval.py (the contract from Task 1)
    - CLAUDE.md "Sentry Backend Rules" — bounded fields only, no PGN
  </read_first>
  <action>
    Modify `app/services/import_service.py` to add a post-insert eval pass in `_flush_batch`. The pass MUST:

    1. Run AFTER `bulk_insert_positions` succeeds (so row IDs / (game_id, ply, endgame_class) keys exist in DB).
    2. Run BEFORE the final `session.commit()` (so all eval UPDATEs land in the same transaction).
    3. Use the in-memory `plies` list (or whatever the variable is called inside `_flush_batch`) to detect span entries — do NOT round-trip through the DB.
    4. For each `(game_id, endgame_class)` group with `count >= ENDGAME_PLY_THRESHOLD`:
       - Find `min_ply` (the span entry).
       - If the span-entry's PlyData has `eval_cp is None and eval_mate is None` (lichess didn't populate it):
         - Reconstruct the board via `_board_at_ply(pgn, min_ply)`. Either:
           a) Define `_board_at_ply` as a private helper inside `import_service.py` (mirrors `scripts/backfill_eval.py`), OR
           b) Import a shared helper from a new `app/services/_board_replay.py` module if both this plan and Plan 78-03 want to share. **Recommendation: define locally in both places to keep wave 2 plans independent; refactor to a shared module is out-of-scope deferred work.**
         - Call `await engine_service.evaluate(board)`.
         - If result is `(None, None)`: set Sentry context with bounded fields (`game_id`, `ply`, `endgame_class`) and capture as warning; do NOT raise.
         - Else: UPDATE the row by `(game_id, ply, endgame_class)` triple (per RESEARCH.md Option A).
    5. Add timing instrumentation: `time.perf_counter()` around the entire eval pass per game; log `eval_pass_ms` so IMP-02 budget can be observed in production logs.

    Imports to add at top of file:
    ```python
    import io
    import time
    from collections import defaultdict

    import chess
    import chess.pgn
    from sqlalchemy import update as sa_update

    from app.repositories.endgame_repository import ENDGAME_PLY_THRESHOLD
    from app.services import engine as engine_service
    ```
    (`sentry_sdk` and `chess` likely already imported; verify before duplicating.)

    Helper function (define near top of module, after imports):
    ```python
    def _board_at_ply(pgn_text: str, target_ply: int) -> chess.Board | None:
        """Replay PGN to target_ply (0-indexed, pre-push). Mirrors scripts/backfill_eval.py."""
        try:
            game = chess.pgn.read_game(io.StringIO(pgn_text))
        except Exception:
            return None
        if game is None:
            return None
        board = game.board()
        for i, node in enumerate(game.mainline()):
            if i == target_ply:
                return board
            board.push(node.move)
        return board
    ```

    Eval-pass code (insert into `_flush_batch` after `await game_repository.bulk_insert_positions(session, position_rows)` and before the final `session.commit()`):
    ```python
    # Phase 78 IMP-01: evaluate per-class span-entry rows where lichess %eval did not populate.
    # This MUST run after bulk_insert_positions (so the rows exist in DB) and before
    # the final commit (so all UPDATEs land in the same transaction).
    eval_pass_start = time.perf_counter()
    eval_calls_made = 0
    eval_calls_failed = 0
    for processing_result in batch_processing_results:  # executor: confirm exact variable name
        plies_list = processing_result["plies"]  # PlyData list
        pgn = processing_result["pgn"]            # source PGN (already in scope; verify exact key)
        game_id = processing_result["game_id"]    # confirm
        # Group plies by endgame_class
        class_plies: dict[int, list[dict]] = defaultdict(list)
        for pd in plies_list:
            ec = pd.get("endgame_class")
            if ec is not None:
                class_plies[ec].append(pd)
        for ec, pds in class_plies.items():
            if len(pds) < ENDGAME_PLY_THRESHOLD:
                continue
            span_pd = min(pds, key=lambda p: p["ply"])
            if span_pd["eval_cp"] is not None or span_pd["eval_mate"] is not None:
                continue  # lichess (or prior pass) populated; do not overwrite
            board = _board_at_ply(pgn, span_pd["ply"])
            if board is None:
                continue
            try:
                eval_cp, eval_mate = await engine_service.evaluate(board)
            except Exception as exc:  # defensive: wrapper should already swallow timeouts
                eval_cp, eval_mate = None, None
                sentry_sdk.set_context("eval", {
                    "game_id": game_id,
                    "ply": span_pd["ply"],
                    "endgame_class": ec,
                })
                sentry_sdk.set_tag("source", "import")
                sentry_sdk.capture_exception(exc)
            eval_calls_made += 1
            if eval_cp is None and eval_mate is None:
                # D-11: skip the row, capture to Sentry, continue importing
                eval_calls_failed += 1
                sentry_sdk.set_context("eval", {
                    "game_id": game_id,
                    "ply": span_pd["ply"],
                    "endgame_class": ec,
                })
                sentry_sdk.set_tag("source", "import")
                sentry_sdk.capture_message("import-time engine returned None tuple", level="warning")
                continue
            await session.execute(
                sa_update(GamePosition)
                .where(
                    GamePosition.game_id == game_id,
                    GamePosition.ply == span_pd["ply"],
                    GamePosition.endgame_class == ec,
                )
                .values(eval_cp=eval_cp, eval_mate=eval_mate)
            )
    eval_pass_ms = (time.perf_counter() - eval_pass_start) * 1000
    # Lightweight structured log for IMP-02 budget observation; format follows project pattern
    logger.info(
        "import_eval_pass",
        extra={
            "games_in_batch": len(batch_processing_results),
            "eval_calls_made": eval_calls_made,
            "eval_calls_failed": eval_calls_failed,
            "eval_pass_ms": round(eval_pass_ms, 1),
        },
    )
    ```

    **Executor adjustments:**
    - Confirm exact variable names in `_flush_batch` (`batch_processing_results`, `plies_list`, `pgn`, `game_id`). The variable names above are placeholders; the executor reads `_flush_batch` and substitutes the actual names.
    - Confirm `logger` exists at module level; if not, use `_log` print pattern or add `logger = logging.getLogger(__name__)`.
    - Confirm whether the project uses `sa.update` aliased as `sa_update` elsewhere; match local convention.
    - Verify `processing_result` is the correct iteration variable; `batch_processing_results` may instead be `batch` (a list of `(game, processing_result)` tuples). Whatever the actual structure, the eval pass needs `pgn`, `plies`, `game_id` per game — extract those.
    - The `try/except Exception` block around `engine_service.evaluate` is defensive overkill — the wrapper already swallows engine errors and returns `(None, None)`. Keep the bare `try/except` only if the project's general practice is to belt-and-suspenders Sentry-wrap third-party calls; otherwise drop it and rely on the wrapper's contract. The Wave 0 test for engine error simulates `(None, None)` return, not a raised exception.
  </action>
  <verify>
    <automated>
      uv run ruff check app/services/import_service.py
      uv run ty check app/services/import_service.py
      uv run pytest tests/services/test_import_service_eval.py -x
      uv run pytest tests/test_import_service.py tests/services/test_import_service.py -x 2>/dev/null || true
      # Existing import-service tests must not regress (whichever file holds them).
      grep -c "asyncio.gather" app/services/import_service.py  # MUST be 0 (CLAUDE.md)
      grep -n "engine_service.evaluate" app/services/import_service.py
      grep -n "ENDGAME_PLY_THRESHOLD" app/services/import_service.py
      grep -n "set_context.*eval" app/services/import_service.py
      grep -A5 "set_context.*eval" app/services/import_service.py | grep -c "pgn\|fen"  # MUST be 0 (no info disclosure)
    </automated>
  </verify>
  <acceptance_criteria>
    - `grep -n "from app.services import engine as engine_service" app/services/import_service.py` returns a match.
    - `grep -n "engine_service.evaluate" app/services/import_service.py` returns at least 1 match.
    - `grep -n "_board_at_ply" app/services/import_service.py` returns at least 2 matches (definition + usage).
    - `grep -n "ENDGAME_PLY_THRESHOLD" app/services/import_service.py` returns at least 1 match (imported, not redeclared).
    - `grep -A5 "set_context.*eval" app/services/import_service.py | grep -E "pgn\|fen"` returns 0 matches (information-disclosure mitigation).
    - `grep -c "asyncio.gather" app/services/import_service.py` returns the SAME count as before this task (no new gather introduced).
    - `grep -n "eval_pass_ms\|perf_counter" app/services/import_service.py` returns matches (timing instrumentation).
    - `uv run ruff check app/services/import_service.py` exits 0.
    - `uv run ty check app/services/import_service.py` exits 0.
    - `uv run pytest tests/services/test_import_service_eval.py -x` exits 0 (GREEN).
    - Existing import service tests (whichever file holds them) still pass — no regressions.
  </acceptance_criteria>
  <done>Import path evaluates new span-entry rows; lichess evals untouched; engine errors logged to Sentry with bounded context; type-checks clean.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Background import worker → engine wrapper | Async call; engine subprocess is shared across all import workers via `_lock` |
| Engine error → Sentry | Bounded fields only crossing this boundary (`game_id`, `ply`, `endgame_class`) |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-78-17 | Tampering | Lichess `%eval` annotations get overwritten by import-time engine call | mitigate | Skip condition `if span_pd["eval_cp"] is not None or span_pd["eval_mate"] is not None: continue` ensures the engine never runs for rows that already have any eval. Wave 0 test `test_lichess_eval_at_span_entry_skips_engine` asserts mock_eval.call_count == 0 for the lichess-populated span entry. |
| T-78-18 | Information disclosure | Sentry context contains user-identifying PGN or full game state | mitigate | D-11 + CLAUDE.md Sentry rules: context dict contains ONLY `game_id`, `ply`, `endgame_class`. Wave 0 test `test_engine_error_skips_row_and_captures_to_sentry` asserts `pgn`, `user_id`, `fen` are NOT in the context payload. Tag is `source=import`. |
| T-78-19 | Denial of service | Engine error during import wedges entire import job | mitigate | D-11: engine error → skip row, log, continue. Import never raises from the eval pass. Wrapper's 2s timeout caps wall-clock per call. |
| T-78-20 | Tampering | New eval not flushed to DB if commit fails after eval | accept | Eval UPDATEs are part of the same `session.commit()` as the bulk insert; if commit fails the entire batch rolls back including the eval writes. This is correct behavior — partial state is worse than retry. |
| T-78-21 | DoS | IMP-02 budget blown — eval pass exceeds 1s per typical game | mitigate (observe) | Timing instrumentation logs `eval_pass_ms` per batch. Operator monitors prod logs after deploy; if p50 > 1000ms per game, lower depth or tune in a follow-up phase. Not a hard gate — logged metric. |
</threat_model>

<verification>
- `uv run pytest tests/services/test_import_service_eval.py -x` GREEN.
- `uv run ty check app/services/import_service.py` exits 0.
- Existing import-service tests still pass.
- `grep -c "asyncio.gather" app/services/import_service.py` unchanged from baseline.
- Information-disclosure grep gate clean: Sentry context payload does not contain `pgn`, `fen`, `user_id`, or any unbounded user data.
</verification>

<success_criteria>
- New span-entry rows on chess.com imports get evaluated automatically.
- Lichess `%eval` annotations are byte-for-byte preserved.
- Engine errors degrade to NULL eval + Sentry warning, never failing the import.
- IMP-02 budget observable via structured log (`eval_pass_ms`).
</success_criteria>

<output>
After completion, create `.planning/milestones/v1.15-phases/78-stockfish-eval-cutover-for-endgame-classification/78-04-SUMMARY.md` recording: insertion-point line numbers, observed `eval_pass_ms` from local test imports, any deviations from the RESEARCH.md Option A pattern.
</output>
