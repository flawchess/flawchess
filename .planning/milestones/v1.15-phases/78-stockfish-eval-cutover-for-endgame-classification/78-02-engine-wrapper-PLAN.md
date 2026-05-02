---
phase: 78
plan: 02
type: execute
wave: 1
depends_on: []
files_modified:
  - app/services/engine.py
  - app/main.py
  - tests/services/test_engine.py
  - tests/conftest.py
autonomous: true
requirements: [ENG-02, ENG-03]
tags: [engine, stockfish, async, lifespan, wrapper]

must_haves:
  truths:
    - "`app/services/engine.py` exposes `start_engine()`, `stop_engine()`, and `async def evaluate(board) -> tuple[int | None, int | None]`."
    - "Sign convention is white-perspective and matches `app/services/zobrist.py:183-197` byte-for-byte (same `pov.white().score(mate_score=None)` / `.mate()` / clamp pattern)."
    - "Engine is a single long-lived UCI process per backend worker (D-01); concurrent callers serialize on `asyncio.Lock` (no `asyncio.gather` over the engine)."
    - "Per-eval `asyncio.wait_for` timeout = 2.0s (D-05); on timeout or `EngineError`/`EngineTerminatedError`, wrapper restarts the engine and returns `(None, None)` — caller decides what to log."
    - "UCI options `Hash=64`, `Threads=1`, depth=15 (D-03) live ONLY in `app/services/engine.py` — no other file configures the engine (ENG-03 grep gate)."
    - "FastAPI lifespan in `app/main.py` calls `start_engine()` after existing startup steps and `stop_engine()` in a `finally` block for guaranteed shutdown (D-02)."
    - "Wave 0 test file `tests/services/test_engine.py` covers known mate-in-N, white-winning cp, black-winning cp, near-equal positions; uses `@skip_if_no_stockfish` so the file is not load-bearing on Stockfish presence."
  artifacts:
    - path: "app/services/engine.py"
      provides: "Async-friendly Stockfish wrapper, single source of UCI option config (ENG-02, ENG-03)"
      exports: ["start_engine", "stop_engine", "evaluate"]
      min_lines: 60
    - path: "app/main.py"
      provides: "Lifespan-managed engine start/stop (D-02)"
      contains: "await start_engine()"
    - path: "tests/services/test_engine.py"
      provides: "Wave 0 wrapper unit tests (ENG-02 acceptance)"
      contains: "skip_if_no_stockfish"
    - path: "tests/conftest.py"
      provides: "Session-scoped engine fixture (per VAL doc Wave 0)"
      contains: "engine_started"
  key_links:
    - from: "app/services/engine.py"
      to: "app/services/zobrist.py:111-112 (EVAL_CP_MAX_ABS, EVAL_MATE_MAX_ABS)"
      via: "import"
      pattern: "from app.services.zobrist import EVAL_CP_MAX_ABS, EVAL_MATE_MAX_ABS"
    - from: "app/main.py lifespan"
      to: "app/services/engine.py start_engine / stop_engine"
      via: "lifespan context manager"
      pattern: "from app.services.engine import start_engine, stop_engine"
---

<objective>
Implement the shared Stockfish engine wrapper module (`app/services/engine.py`) — the single source of UCI option configuration consumed by both the import path (Plan 78-04) and the backfill script (Plan 78-03). Wire startup/shutdown into the FastAPI lifespan handler. Provide Wave 0 unit tests that pin the API contract before downstream plans depend on it.

Purpose: ENG-02 + ENG-03 are the contract that backfill, import, and tests all sit on. Locking it down in Wave 1 alongside the Dockerfile means downstream plans (78-03/78-04) can import `evaluate` and write code without re-deriving the wrapper shape.

Output: New `app/services/engine.py` (long-lived UCI subprocess + asyncio.Lock + 2s timeout + white-perspective sign convention + clamp), modified `app/main.py` (lifespan start/stop with try/finally), new `tests/services/test_engine.py` (Wave 0), modified `tests/conftest.py` (engine fixture).
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
@CLAUDE.md
@app/main.py
@app/services/zobrist.py

<interfaces>
<!-- Sign convention to match byte-for-byte (zobrist.py:183-197) -->
```python
# Already in zobrist.py — DO NOT redeclare in engine.py; import EVAL_CP_MAX_ABS / EVAL_MATE_MAX_ABS
EVAL_CP_MAX_ABS = 10000   # ±100 pawns
EVAL_MATE_MAX_ABS = 200   # no realistic mate-in-N exceeds this

# zobrist.py:183-197 (canonical pattern):
pov = node.eval()
if pov is not None:
    w = pov.white()
    eval_cp = w.score(mate_score=None)   # None for mate positions
    eval_mate = w.mate()                  # None for non-mate; +ve = white mates, -ve = black mates
    if eval_cp is not None:
        eval_cp = max(-EVAL_CP_MAX_ABS, min(EVAL_CP_MAX_ABS, eval_cp))
    if eval_mate is not None:
        eval_mate = max(-EVAL_MATE_MAX_ABS, min(EVAL_MATE_MAX_ABS, eval_mate))
```

<!-- python-chess engine API (verified in RESEARCH.md against installed package) -->
```python
import chess
import chess.engine

# popen_uci is a native async coroutine returning (transport, protocol)
transport, protocol = await chess.engine.popen_uci("/usr/local/bin/stockfish")
await protocol.configure({"Hash": 64, "Threads": 1})

# analyse is async; depth limit; returns InfoDict
info = await protocol.analyse(board, chess.engine.Limit(depth=15))
pov_score = info.get("score")  # PovScore or None

# Exception types (chess/engine.py:80-85)
chess.engine.EngineError              # protocol/parse error
chess.engine.EngineTerminatedError    # subclass of EngineError; engine process died

await protocol.quit()
```

<!-- FastAPI lifespan target shape (app/main.py:44-52 currently) -->
```python
# CURRENT (no try/finally):
@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    get_insights_agent()
    await cleanup_orphaned_jobs()
    yield

# TARGET (engine added with guaranteed cleanup):
@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    get_insights_agent()
    await cleanup_orphaned_jobs()
    await start_engine()
    try:
        yield
    finally:
        await stop_engine()
```
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Wave 0 — wrapper contract tests + conftest fixture</name>
  <files>tests/services/test_engine.py, tests/conftest.py</files>
  <read_first>
    - tests/conftest.py (current state — what fixtures already exist; do not duplicate)
    - tests/test_zobrist.py (board fixture style; pure unit-test pattern)
    - .planning/milestones/v1.15-phases/78-stockfish-eval-cutover-for-endgame-classification/78-RESEARCH.md "Test Strategy" section (lines 757-870) — test position FENs, skipif pattern
    - .planning/milestones/v1.15-phases/78-stockfish-eval-cutover-for-endgame-classification/78-VALIDATION.md "Wave 0 Requirements"
    - app/services/zobrist.py:183-197 (the sign convention the wrapper output must match)
  </read_first>
  <behavior>
    - Test 1: `evaluate()` on KQ-vs-K (white winning) returns `eval_cp >= 100`, `eval_mate is None`.
    - Test 2: `evaluate()` on K-vs-Q (black winning) returns `eval_cp <= -100`, `eval_mate is None`.
    - Test 3: `evaluate()` on a forced-mate-for-white position returns `eval_mate is not None and eval_mate > 0`.
    - Test 4: `evaluate()` on a forced-mate-for-black position returns `eval_mate is not None and eval_mate < 0`.
    - Test 5: `evaluate()` on near-equal opening (e.g. starting position after 1.e4) returns `abs(eval_cp) < 100` (with reasonable depth-15 tolerance).
    - Test 6: `evaluate()` returns `(None, None)` if engine has not been started (graceful degradation; required for tests that don't bring up the engine).
    - Test 7 (clamp): `evaluate()` returned `eval_cp` is always within `[-EVAL_CP_MAX_ABS, EVAL_CP_MAX_ABS]` and `eval_mate` (when set) within `[-EVAL_MATE_MAX_ABS, EVAL_MATE_MAX_ABS]`.
  </behavior>
  <action>
    Create `tests/services/` directory if missing. Create `tests/services/__init__.py` empty file. Create `tests/services/test_engine.py` with the structure below. Add a session-scoped engine fixture in `tests/conftest.py` so test runs start/stop the engine once per pytest session (not per test) — this matches D-02's "Tests pass `Stockfish` on PATH; fixture starts/stops the engine per test session, not per test".

    `tests/services/test_engine.py` skeleton:
    ```python
    """Engine wrapper contract tests (ENG-02). Phase 78 Wave 0."""
    import shutil

    import chess
    import pytest

    from app.services.engine import evaluate
    from app.services.zobrist import EVAL_CP_MAX_ABS, EVAL_MATE_MAX_ABS

    stockfish_missing = shutil.which("stockfish") is None
    skip_if_no_stockfish = pytest.mark.skipif(stockfish_missing, reason="Stockfish not on PATH")

    # Known positions (chosen for deterministic depth-15 outcome)
    KQ_VS_K_WHITE_WINS = "8/8/8/8/8/8/4Q3/4K2k w - - 0 1"
    K_VS_Q_BLACK_WINS = "8/8/8/8/8/8/4q3/4k2K w - - 0 1"  # white to move, severely losing
    NEAR_EQUAL_AFTER_E4 = "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1"
    # Forced mate positions: pick simple mate-in-1 / mate-in-2 known positions
    MATE_IN_1_WHITE = "6k1/5ppp/8/8/8/8/5PPP/R5K1 w - - 0 1"  # Ra8# is mate in 1
    MATE_IN_2_BLACK = "<find a known mate-in-2-for-black FEN; if simpler, use mate-in-1 with black to move>"


    @skip_if_no_stockfish
    @pytest.mark.usefixtures("engine_started")
    class TestEngineWrapper:
        async def test_white_winning_returns_positive_cp(self) -> None:
            cp, mate = await evaluate(chess.Board(KQ_VS_K_WHITE_WINS))
            # Either Stockfish reports cp >= 100, OR it sees the forced mate and reports eval_mate.
            # Both are correct — assert at least one of (cp >= 100, mate is not None and mate > 0).
            assert (cp is not None and cp >= 100) or (mate is not None and mate > 0)

        async def test_black_winning_returns_negative_cp(self) -> None:
            cp, mate = await evaluate(chess.Board(K_VS_Q_BLACK_WINS))
            assert (cp is not None and cp <= -100) or (mate is not None and mate < 0)

        async def test_near_equal_returns_small_cp(self) -> None:
            cp, mate = await evaluate(chess.Board(NEAR_EQUAL_AFTER_E4))
            assert mate is None
            assert cp is not None and abs(cp) < 100

        async def test_mate_for_white_returns_positive_mate(self) -> None:
            cp, mate = await evaluate(chess.Board(MATE_IN_1_WHITE))
            assert mate is not None and mate > 0

        async def test_clamp_bounds(self) -> None:
            cp, mate = await evaluate(chess.Board(KQ_VS_K_WHITE_WINS))
            if cp is not None:
                assert -EVAL_CP_MAX_ABS <= cp <= EVAL_CP_MAX_ABS
            if mate is not None:
                assert -EVAL_MATE_MAX_ABS <= mate <= EVAL_MATE_MAX_ABS


    class TestEngineNotStarted:
        async def test_evaluate_returns_none_tuple_if_engine_not_started(self) -> None:
            """When start_engine() has not been called, evaluate() degrades to (None, None).

            Required for tests that don't bring up the engine and for the import-time
            graceful-degradation path (D-11)."""
            # NOTE: This test must NOT be marked with @skip_if_no_stockfish — it tests
            # the not-started branch which is independent of binary presence.
            # NOTE: This test must run in isolation from `engine_started` (no autouse).
            cp, mate = await evaluate(chess.Board())
            # Pre-Wave-0 state: _protocol is None at module load → (None, None).
            # If a previous test in the same session started the engine, this assertion
            # may not hold; the pytest collection order is what makes this safe in CI.
            # If flaky, restructure as a pytest_xdist isolated test or call stop_engine() first.
            assert (cp, mate) == (None, None)
    ```

    Replace `MATE_IN_2_BLACK` placeholder with a real known FEN. Use python-chess to verify:
    ```bash
    uv run python -c "import chess; b = chess.Board('<your fen>'); print(b.is_checkmate(), list(b.legal_moves)[:3])"
    ```

    `tests/conftest.py` addition (append; do NOT modify existing fixtures):
    ```python
    import pytest_asyncio


    @pytest_asyncio.fixture(scope="session")
    async def engine_started():
        """Start Stockfish once per pytest session (D-02)."""
        from app.services.engine import start_engine, stop_engine
        await start_engine()
        try:
            yield
        finally:
            await stop_engine()
    ```

    If `tests/conftest.py` already imports pytest_asyncio, do not add a duplicate import.

    These tests will FAIL until Task 2 creates `app/services/engine.py`. That is the RED phase.
  </action>
  <verify>
    <automated>
      uv run pytest tests/services/test_engine.py -x 2>&1 | tail -30
      # Expected RED: ImportError or AttributeError on `from app.services.engine import evaluate` until Task 2 lands.
    </automated>
  </verify>
  <acceptance_criteria>
    - File `tests/services/__init__.py` exists.
    - File `tests/services/test_engine.py` exists with at least 5 test methods.
    - `grep -n "skip_if_no_stockfish" tests/services/test_engine.py` returns multiple matches.
    - `grep -n "engine_started" tests/conftest.py` returns a match.
    - Running pytest fails ONLY with ImportError on `app.services.engine` (Task 2 will satisfy this) — RED phase confirmed.
  </acceptance_criteria>
  <done>Wave 0 test file committed (RED); pytest output names the missing `app.services.engine` module.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Implement app/services/engine.py wrapper (GREEN)</name>
  <files>app/services/engine.py</files>
  <read_first>
    - app/services/zobrist.py:1-230 (sign convention, EVAL_CP_MAX_ABS / EVAL_MATE_MAX_ABS at lines 111-112)
    - .venv/lib/python3.13/site-packages/chess/engine.py (verify popen_uci signature at line 2840, Score.score / .mate at lines 415, 431)
    - .planning/milestones/v1.15-phases/78-stockfish-eval-cutover-for-endgame-classification/78-RESEARCH.md "Wrapper Implementation Pattern" (lines 144-228)
    - .planning/milestones/v1.15-phases/78-stockfish-eval-cutover-for-endgame-classification/78-CONTEXT.md (D-01 through D-05)
    - CLAUDE.md "Critical Constraints" — no asyncio.gather on same AsyncSession, async only
    - tests/services/test_engine.py (the contract from Task 1)
  </read_first>
  <action>
    Create `app/services/engine.py`. Make Wave 0 tests PASS without overshooting requirements. The full module:

    ```python
    """Stockfish engine wrapper (Phase 78 ENG-02 / ENG-03).

    Single source of UCI option configuration. Long-lived UCI process per Python
    process (D-01). Async-friendly via asyncio.Lock serialization. Sign convention
    is white-perspective and matches app/services/zobrist.py:183-197 byte-for-byte.

    Lifecycle:
        start_engine()       — call from FastAPI lifespan startup (or script main()).
        stop_engine()        — call from lifespan shutdown / script teardown.
        evaluate(board)      — async; returns (eval_cp, eval_mate) in white perspective.

    On engine timeout / crash, evaluate() restarts the engine and returns (None, None).
    The caller decides whether to log to Sentry (import path: D-11; backfill script: log).
    """
    from __future__ import annotations

    import asyncio
    import os

    import chess
    import chess.engine

    from app.services.zobrist import EVAL_CP_MAX_ABS, EVAL_MATE_MAX_ABS

    # D-06: env var with sensible default; Docker image sets STOCKFISH_PATH=/usr/local/bin/stockfish
    _STOCKFISH_PATH: str = os.environ.get("STOCKFISH_PATH", "/usr/local/bin/stockfish")
    # D-03: UCI options live ONLY in this module (ENG-03 grep gate)
    _HASH_MB: int = 64
    _THREADS: int = 1
    # SPEC constraint: depth 15 fixed, no per-call tuning
    _DEPTH: int = 15
    # D-05: defensive per-eval timeout
    _TIMEOUT_S: float = 2.0

    # Long-lived process state. Module-level globals per D-01 (single shared engine).
    _transport: asyncio.SubprocessTransport | None = None
    _protocol: chess.engine.UciProtocol | None = None
    _lock: asyncio.Lock = asyncio.Lock()


    async def start_engine() -> None:
        """Start the long-lived UCI process. Idempotent: a second call is a no-op."""
        global _transport, _protocol
        if _protocol is not None:
            return
        _transport, _protocol = await chess.engine.popen_uci(_STOCKFISH_PATH)
        await _protocol.configure({"Hash": _HASH_MB, "Threads": _THREADS})


    async def stop_engine() -> None:
        """Stop the UCI process. Safe to call without start (no-op if not started)."""
        global _transport, _protocol
        if _protocol is not None:
            try:
                await _protocol.quit()
            except (chess.engine.EngineError, chess.engine.EngineTerminatedError):
                pass
        _transport = None
        _protocol = None


    async def _restart_engine() -> None:
        """Restart after timeout / crash. Internal — callers do not invoke directly."""
        await stop_engine()
        await start_engine()


    async def evaluate(board: chess.Board) -> tuple[int | None, int | None]:
        """Evaluate position at depth 15. Returns (eval_cp, eval_mate) in white perspective.

        Returns (None, None) if the engine is not started, or on timeout / crash
        (engine is restarted before returning so the next caller sees a clean state).
        """
        async with _lock:
            if _protocol is None:
                return None, None
            try:
                info = await asyncio.wait_for(
                    _protocol.analyse(board, chess.engine.Limit(depth=_DEPTH)),
                    timeout=_TIMEOUT_S,
                )
            except (
                asyncio.TimeoutError,
                chess.engine.EngineError,
                chess.engine.EngineTerminatedError,
            ):
                await _restart_engine()
                return None, None

        pov_score = info.get("score")
        if pov_score is None:
            return None, None

        # White-perspective regardless of board.turn — matches zobrist.py:183-197
        white_score = pov_score.white()
        eval_cp = white_score.score(mate_score=None)  # None for mate
        eval_mate = white_score.mate()                # None for non-mate

        # Clamp to SMALLINT-safe bounds (mirrors zobrist.py:194-197)
        if eval_cp is not None:
            eval_cp = max(-EVAL_CP_MAX_ABS, min(EVAL_CP_MAX_ABS, eval_cp))
        if eval_mate is not None:
            eval_mate = max(-EVAL_MATE_MAX_ABS, min(EVAL_MATE_MAX_ABS, eval_mate))

        return eval_cp, eval_mate
    ```

    Type-check carefully: `EVAL_CP_MAX_ABS` and `EVAL_MATE_MAX_ABS` are `int`. `score()` returns `int | None`. `mate()` returns `int | None`. The function signature uses Python 3.10+ union syntax (`int | None`) which the project already uses (e.g. zobrist.py).

    Do NOT redeclare `EVAL_CP_MAX_ABS` / `EVAL_MATE_MAX_ABS` here — import from zobrist.py per PATTERNS.md.
  </action>
  <verify>
    <automated>
      uv run ruff check app/services/engine.py
      uv run ty check app/services/engine.py
      uv run pytest tests/services/test_engine.py -x
    </automated>
  </verify>
  <acceptance_criteria>
    - `grep -n "async def evaluate" app/services/engine.py` returns a match.
    - `grep -n "async def start_engine\|async def stop_engine" app/services/engine.py` returns 2 matches.
    - `grep -n "asyncio.wait_for" app/services/engine.py` returns at least 1 match (D-05 timeout).
    - `grep -n "asyncio.Lock" app/services/engine.py` returns at least 1 match (D-01 serialization).
    - `grep -n "Hash.*64\|Threads.*1\|depth=15\|_DEPTH = 15\|_HASH_MB = 64\|_THREADS = 1" app/services/engine.py` returns multiple matches (D-03 options present).
    - `grep -n "EVAL_CP_MAX_ABS\|EVAL_MATE_MAX_ABS" app/services/engine.py` shows IMPORT only (one `from app.services.zobrist import` line); not a redeclaration.
    - `uv run ruff check app/services/engine.py` exits 0.
    - `uv run ty check app/services/engine.py` exits 0 (zero errors per CLAUDE.md ty compliance).
    - `uv run pytest tests/services/test_engine.py -x` exits 0 (GREEN — Task 1 tests pass).
    - ENG-03 grep gate: `grep -rn "popen_uci\|chess.engine.Limit\|setoption" app/ scripts/` returns matches ONLY in `app/services/engine.py` (no leakage).
  </acceptance_criteria>
  <done>Wrapper module passes Task 1 tests; type checks clean; UCI option configuration appears only in `app/services/engine.py`.</done>
</task>

<task type="auto" tdd="false">
  <name>Task 3: Wire engine into FastAPI lifespan</name>
  <files>app/main.py</files>
  <read_first>
    - app/main.py (current lifespan at lines 44-52)
    - .planning/milestones/v1.15-phases/78-stockfish-eval-cutover-for-endgame-classification/78-PATTERNS.md "app/main.py" section (target pattern with try/finally)
    - .planning/milestones/v1.15-phases/78-stockfish-eval-cutover-for-endgame-classification/78-CONTEXT.md (D-02)
  </read_first>
  <action>
    Modify `app/main.py` lifespan to start/stop the engine, wrapped in `try/finally` for guaranteed cleanup. Order is critical: `start_engine()` comes AFTER `get_insights_agent()` and `await cleanup_orphaned_jobs()` so a Stockfish startup failure does not suppress existing deploy-blocker validation.

    Existing block (lines 44-52):
    ```python
    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        # D-22: validate insights Agent FIRST — startup failure is a deploy-blocker.
        # Orphan cleanup is best-effort and must not run if the app can't serve
        # the insights endpoint.
        get_insights_agent()
        await cleanup_orphaned_jobs()
        yield
    ```

    Modified block:
    ```python
    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        # D-22: validate insights Agent FIRST — startup failure is a deploy-blocker.
        # Orphan cleanup is best-effort and must not run if the app can't serve
        # the insights endpoint.
        get_insights_agent()
        await cleanup_orphaned_jobs()
        # Phase 78 D-02: long-lived Stockfish UCI process. Comes AFTER existing startup
        # so engine startup failure does not mask deploy-blocker validation. try/finally
        # ensures stop_engine runs on exception during yield (graceful shutdown of UCI).
        await start_engine()
        try:
            yield
        finally:
            await stop_engine()
    ```

    Add the import alongside the existing `from app.services.import_service import cleanup_orphaned_jobs` (line 18):
    ```python
    from app.services.engine import start_engine, stop_engine
    ```

    No other changes to `app/main.py`.
  </action>
  <verify>
    <automated>
      grep -n "from app.services.engine import start_engine, stop_engine" app/main.py
      grep -n "await start_engine()" app/main.py
      grep -n "await stop_engine()" app/main.py
      grep -n "try:\s*$" app/main.py
      uv run ruff check app/main.py
      uv run ty check app/main.py
      # Confirm app boots (will fail to bind port if 8000 in use; we just want import + lifespan-callable).
      timeout 5 uv run python -c "from app.main import app, lifespan; print('OK', lifespan)" 2>&1 | head -5
    </automated>
  </verify>
  <acceptance_criteria>
    - `grep -n "from app.services.engine import start_engine, stop_engine" app/main.py` returns a match.
    - `grep -n "await start_engine()" app/main.py` returns exactly 1 match.
    - `grep -n "await stop_engine()" app/main.py` returns exactly 1 match.
    - `grep -B1 -A2 "await start_engine" app/main.py` shows it follows `await cleanup_orphaned_jobs()`.
    - The lifespan body contains a `try:` / `finally:` pair (`grep -n "finally:" app/main.py`).
    - `uv run ruff check app/main.py` exits 0.
    - `uv run ty check app/main.py` exits 0.
    - `uv run pytest tests/services/test_engine.py tests/test_main.py -x` exits 0 (existing main tests must not regress; if no tests/test_main.py, skip that file).
  </acceptance_criteria>
  <done>FastAPI lifespan starts/stops the engine; existing startup ordering preserved; type checks clean.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| FastAPI worker → UCI subprocess | Long-lived `popen_uci` subprocess; backend talks to it over pipes |
| Caller → wrapper | Async callers from import path (Plan 78-04) and backfill script (Plan 78-03) serialize on `_lock` |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-78-06 | Denial of Service | Wedged UCI engine consuming a request indefinitely | mitigate | D-05 per-eval `asyncio.wait_for(..., timeout=2.0)`; on timeout the engine is restarted before next call (`_restart_engine`) so a single bad position cannot poison subsequent evals. |
| T-78-07 | Denial of Service | Concurrent callers fighting over a single engine | mitigate | D-01 `asyncio.Lock` serializes calls; queued callers wait at most timeout + restart per stuck call. CLAUDE.md "no asyncio.gather on same AsyncSession" is honored: this is engine-side, not session-side, but the principle (sequential coroutines for shared resources) is upheld. |
| T-78-08 | Tampering | Wrong sign convention introduced into eval columns | mitigate | Wrapper imports `EVAL_CP_MAX_ABS`/`EVAL_MATE_MAX_ABS` from zobrist.py and applies `pov.white().score()`/`.mate()` exactly mirroring zobrist.py:183-197; Wave 0 tests assert the convention on both white-winning and black-winning positions. |
| T-78-09 | Information disclosure | Exception traces leaked to logs | accept | The wrapper SWALLOWS engine exceptions (no Sentry call here per CONTEXT.md D-11 — Sentry capture is the call site's responsibility). Restart silently and return `(None, None)`. Caller in Plan 78-04 will set Sentry context with bounded fields (no PGN, no user identifiers beyond game_id / ply / endgame_class). |
| T-78-10 | Elevation of privilege | Stockfish subprocess inherits backend container's privileges | accept | Same container, same user, no privilege boundary added by Stockfish. Container itself is the existing privilege boundary. |
</threat_model>

<verification>
- `uv run pytest tests/services/test_engine.py -x` is GREEN.
- `uv run ty check app/services/engine.py app/main.py tests/services/test_engine.py` exits 0.
- `grep -rn "popen_uci\|chess.engine.Limit\|setoption" app/ scripts/` shows matches ONLY in `app/services/engine.py` (ENG-03).
- App boots: `uv run uvicorn app.main:app --reload` reaches the "Application startup complete" log line, indicating `start_engine` ran successfully against the locally installed Stockfish (operator-only manual confirmation; not gated by automated check).
</verification>

<success_criteria>
- `app/services/engine.py` exposes `start_engine`, `stop_engine`, `evaluate` with the contract above.
- Wave 0 test file passes against locally installed Stockfish.
- FastAPI lifespan starts/stops the engine in the correct order with `try/finally`.
- ENG-03 single-source-of-truth grep gate is clean.
</success_criteria>

<output>
After completion, create `.planning/milestones/v1.15-phases/78-stockfish-eval-cutover-for-endgame-classification/78-02-SUMMARY.md` recording: wrapper module signature, lifespan ordering, Stockfish version observed locally during test runs.
</output>
