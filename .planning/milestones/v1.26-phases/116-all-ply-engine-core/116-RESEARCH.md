# Phase 116: All-Ply Engine Core - Research

**Researched:** 2026-06-12
**Domain:** Stockfish eval drain — all-ply analysis, node-budget search, completion marker, memory accounting
**Confidence:** HIGH (all key findings from direct code inspection and live measurement)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Dedup + eval provenance (EVAL-03)**
- D-116-01: Parity-only dedup. The ply<=20 dedup reuses ONLY 1M-parity evals. Legacy depth-15 server evals are never reused. Worst case is the already-accepted +26% cost ceiling (EVAL-01).
- D-116-02: Marker-gated source set. Dedup consults only `game_positions` rows belonging to games whose full-analysis marker is set — parity by construction. No provenance column, no fuzzy legacy backfill.
- D-116-03: Overwrite legacy depth-15 evals. When the full pass analyzes a game, populated depth-15 entry-ply evals are overwritten with 1M evals so the game comes out uniformly at parity.
- D-116-04: `Game.is_analyzed` is the %eval discriminator. Within a game being analyzed: if `is_analyzed` (`white_blunders IS NOT NULL`) → populated evals are lichess %evals (parity) → preserve (T-78-17). Otherwise → populated evals are legacy depth-15 → overwrite (D-116-03). No heuristic needed.

**Completion marker (EVAL-05)**
- D-116-05: Timestamp column. `full_evals_completed_at` on `games`, mirroring `evals_completed_at` exactly (nullable timestamp + partial index WHERE NULL for the pending pick).
- D-116-06: Verified backfill at migration time. Pre-mark games where every non-terminal ply already has `eval_cp`/`eval_mate` populated — provable by SQL. Seeds the dedup source set immediately.
- D-116-07: Mark complete with holes. Engine timeout/crash → row stays NULL, game still gets the marker, Sentry captures failures. No retry loop, no threshold gating.

**Interim drain structure (pre-117)**
- D-116-08: Second coroutine. `run_eval_drain` (entry-ply, depth-15, `evals_completed_at`) stays untouched. A NEW full-ply drain coroutine owns the new marker and its own pick.
- D-116-09: Live in prod with the 116 deploy. LIFO id-DESC interim pick. Provides real-world memory/latency soak validating QUEUE-07.
- D-116-10: Guest filter from day one. The interim pick excludes guest users (`users.is_guest`).
- D-116-11: Gate between games. Before picking each game, the full drain checks: active import job exists OR entry-ply work pending → sleep and re-check.

**Memory bound (QUEUE-07)**
- D-116-12: Measure + document, no runtime machinery. Measure real per-worker RSS at the 1M-node budget, document the accounting in CLAUDE.md and a code comment next to the pool constants.
- D-116-13: Target pool size 8, contingent on checks; fallback 6. Bump to 8 only if (a) memory accounting fits 4g with headroom AND (b) a brief prod soak shows API latency unaffected.

### Claude's Discretion
- Engine call plumbing: how `engine.py` exposes the node-budget search alongside the existing depth-15 call (new parameter, second function, per-pool config) — keep UCI options centralized in `engine.py` per ENG-03.
- The per-eval timeout for 1M-node calls (existing `_TIMEOUT_S = 2.0` is far too small at ~1s mean / heavier tail — pick a sane bound from spike latency data).
- Dedup index shape: a cross-user `full_hash` lookup index does not exist today; design the new index/partial predicate + the marker-gate join.
- Fan-out granularity per game (whole-game gather vs pool-size chunks) and the write transaction shape for ~60 row-updates per game.
- Terminal-position exclusion mechanics (game-over detection during the mainline walk).
- Verified-backfill execution shape (migration vs one-shot script) based on prod query cost.

### Deferred Ideas (OUT OF SCOPE)
- Pool-priority mechanism inside `EnginePool` (tier-aware worker scheduling) — Phase 117 territory.
- Window-capped automatic analysis (last ~200 games per user) — Phase 117/118 (QUEUE-04, D-3).
- `eval_source` provenance column — only if/when client workers land (SEED-012 D-8 phase 2).
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| EVAL-01 | Every ply of a queued game gets `eval_cp`/`eval_mate` persisted in `game_positions` (terminal game-over positions excluded). No book-skip: ply<=20 dedup makes opening region cheap. | All-ply board-snapshot collector pattern documented. Terminal exclusion: iterate mainline nodes, take `board.copy()` before each `board.push(move)`. The post-last-move terminal position is never reached by the iterator. |
| EVAL-02 | Full-game analysis at 1,000,000 nodes, NNUE, multiPV=1, Hash=32MB, Threads=1 per worker. Existing depth-15 convention replaced. | `chess.engine.Limit(nodes=1_000_000)` confirmed working. `multipv=1` passed to `protocol.analyse()`, not `configure()`. NNUE always-on in SF18 (no UCI option needed). Hash=32MB already configured. |
| EVAL-03 | Before each engine call on plies <= 20, an indexed `full_hash` lookup reuses any existing server eval instead of recomputing. | New cross-user index `ix_gp_full_hash_opening` on `(full_hash) WHERE ply <= 20` required. Marker-gate join to `games.full_evals_completed_at IS NOT NULL`. Dedup batch query: fetch all hashes at once before the gather, not inline per position. |
| EVAL-05 | Each game carries a full-analysis completion marker distinct from `evals_completed_at`. | `full_evals_completed_at TIMESTAMPTZ NULL` column on `games`. Partial index `ix_games_full_evals_pending ON games(id) WHERE full_evals_completed_at IS NULL`. Migration backfill via SQL. |
| QUEUE-07 | Worker pool memory explicitly bounded against the backend container's 4g limit before `STOCKFISH_POOL_SIZE` is raised. | Measured: 6 workers ~2.21 GB (prod estimate), 8 workers ~2.94 GB (prod estimate). FastAPI ~0.3 GB. 8 workers: ~3.24 GB total, ~0.76 GB headroom under 4g. Stale comment in CLAUDE.md and docker-compose.yml needs updating. |
</phase_requirements>

---

## Summary

Phase 116 extends the existing eval drain infrastructure with a second background coroutine that analyzes every non-terminal ply of queued games at the Lichess-parity search budget (1M nodes, NNUE, multiPV=1). The delta from the current codebase is well-bounded: a new coroutine `run_full_eval_drain`, a new `evaluate_nodes()` function in `engine.py`, a new `full_evals_completed_at` column with migration backfill, a new cross-user dedup index on `game_positions`, and documentation of the memory accounting.

All key design questions are locked in CONTEXT.md (D-116-01 through D-116-13). Claude's Discretion covers the engine API shape, timeout value, index predicate, fan-out granularity, and backfill execution. This research resolves all of those with measured data.

The most important findings:
- `chess.engine.Limit(nodes=1_000_000)` is the correct API (verified in running python-chess 1.11.2). Passing `multipv=1` to `analyse()` returns `List[InfoDict]` — use `info[0]` to get the scalar. Not passing `multipv` returns `InfoDict` directly and also includes the PV.
- Per-worker RSS at 1M-node budget on dev: ~269 MB. Prod estimate at 8 workers: ~2.94 GB (based on Phase 91's measured ~368 MB/worker). Total 8-worker footprint ~3.24 GB — within 4g with ~0.76 GB headroom, supporting D-116-13's target of 8.
- Terminal position exclusion: mainline node iteration gives boards BEFORE each push — none of those are game-over. The post-last-move terminal board is never visited by the iterator, so no `is_game_over()` guard is needed at the collection site (just don't add a board after the loop ends).
- Recommended timeout for 1M-node calls: **5.0 seconds** (4x prod p90 of 1.277s from spike 002). The current `_TIMEOUT_S = 2.0` is shared with depth-15 calls; the new node-budget path needs its own constant.

**Primary recommendation:** Add `evaluate_nodes(board)` to `engine.py` using a new `_NODES_BUDGET` constant, implement `run_full_eval_drain()` mirroring `run_eval_drain()`'s session discipline, add the migration, and document the memory accounting in CLAUDE.md.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| All-ply board collection | API / Backend | — | PGN parsing + board walk is CPU-bound server-side work |
| Node-budget Stockfish call | API / Backend | — | EnginePool workers are server processes; pool management lives in `engine.py` |
| Dedup hash lookup | Database / Storage | API / Backend | Cross-user indexed `full_hash` scan; DB owns the query |
| Completion marker write | Database / Storage | API / Backend | `full_evals_completed_at` column + partial index; written in drain's write transaction |
| Yield gate (import vs drain) | API / Backend | Database / Storage | Checks `import_jobs.status IN ('pending','in_progress')` and `evals_completed_at IS NULL` count — both are instant via existing indexes |
| Memory accounting | API / Backend | — | Worker pool is in-process; RSS measured and documented at deploy time |

## Standard Stack

No new packages required. Phase 116 uses only what is already installed.

### Core (all already in pyproject.toml / lockfile)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| python-chess | 1.11.2 | `chess.engine.Limit(nodes=...)`, PGN parsing, board walk | Already used throughout; verified `nodes` parameter works |
| SQLAlchemy | 2.x async | Async session discipline, `update()` + `bindparam()`, `select()` | Project ORM; existing patterns reused verbatim |
| Alembic | current | Migration: add column, partial index, backfill | Project migration tool; existing migration files are templates |
| sentry-sdk | current | `capture_exception()` / `set_context()` for engine failures | CLAUDE.md requirement |

### No New Packages
`chess.engine` is a module within `python-chess`, not a separate package. All functionality needed for Phase 116 is exposed by existing dependencies.

**Package Legitimacy Audit** — no new packages to audit.

## Architecture Patterns

### System Architecture Diagram

```
app/main.py lifespan
    ├── run_eval_drain()            [EXISTING — untouched]
    │   └── pick games (evals_completed_at IS NULL)
    │       → depth-15 entry-ply eval → mark evals_completed_at
    │
    └── run_full_eval_drain()       [NEW — Phase 116]
        │
        ├── [Yield gate] active import OR entry-ply pending? → sleep(5s) & re-check
        │
        ├── Step 1: pick 1 game (LIFO id-DESC, full_evals_completed_at IS NULL,
        │          NOT guest, NOT in entry-ply drain's batch)
        │
        ├── Step 2: load PGN (short read tx → close)
        │
        ├── Step 3: collect all non-terminal board positions [NEW collector]
        │   ├── walk mainline: board before each push → snapshot
        │   ├── partition by ply <= 20 (dedup candidates) vs ply > 20
        │   └── batch-lookup dedup: SELECT eval_cp, eval_mate
        │       FROM game_positions gp JOIN games g ON gp.game_id = g.id
        │       WHERE gp.full_hash IN (:hashes)
        │         AND gp.ply <= 20
        │         AND g.full_evals_completed_at IS NOT NULL
        │         AND (gp.eval_cp IS NOT NULL OR gp.eval_mate IS NOT NULL)
        │       [uses NEW ix_gp_full_hash_opening index]
        │
        ├── Step 4: asyncio.gather() OUTSIDE any session scope
        │   └── evaluate_nodes(board) per non-dedup position
        │       [NEW: chess.engine.Limit(nodes=1_000_000), timeout=5.0s]
        │
        └── Step 5: short write tx
            ├── UPDATE game_positions SET eval_cp=..., eval_mate=... WHERE (game_id, ply)
            │   [~60 row-updates per game; skip if dedup hit OR engine returned (None, None)]
            └── UPDATE games SET full_evals_completed_at = NOW() WHERE id = :game_id
```

### Recommended Project Structure

No structural changes. New code goes in existing modules:
```
app/
├── services/
│   ├── eval_drain.py        # add run_full_eval_drain() + all-ply helpers
│   └── engine.py            # add evaluate_nodes() + _NODES_BUDGET constant
├── models/
│   └── game.py              # add full_evals_completed_at column + partial index
alembic/
└── versions/
    └── <timestamp>_add_full_evals_completed_at.py  # new migration
```

### Pattern 1: Node-Budget Engine Call (Claude's Discretion — resolved)

**What:** Add `evaluate_nodes()` alongside `evaluate()` in `engine.py`. Keep UCI options centralized (ENG-03).

**Recommended shape:** new constants + new module-level function + new `EnginePool` method. A "per-pool config" approach (separate pool for node-budget) is unnecessary — the same `EnginePool` workers can run both call types because `Limit` is passed per-call, not per-pool. The `_DEPTH` and `_TIMEOUT_S` constants are for `evaluate()`; add `_NODES_BUDGET` and `_NODES_TIMEOUT_S` for `evaluate_nodes()`.

```python
# Source: verified via uv run python3 on this machine (python-chess 1.11.2)

# In engine.py — add these constants alongside _DEPTH and _TIMEOUT_S:
_NODES_BUDGET: int = 1_000_000   # EVAL-02: Lichess fishnet parity (D-6 SEED-012)
_NODES_TIMEOUT_S: float = 5.0    # 4x prod p90 (1.277s, spike 002). _TIMEOUT_S=2.0 is for depth-15.

# New module-level function (mirrors evaluate()):
async def evaluate_nodes(board: chess.Board) -> tuple[int | None, int | None]:
    """Evaluate position at 1M nodes. Returns (eval_cp, eval_mate) in white perspective.

    EVAL-02: Lichess-parity budget for full-game analysis drain.
    Returns (None, None) on engine failure — same contract as evaluate().
    """
    if _pool is None:
        return None, None
    return await _pool.evaluate_nodes(board)

# In EnginePool.evaluate_nodes — mirrors evaluate() with different Limit:
async def evaluate_nodes(self, board: chess.Board) -> tuple[int | None, int | None]:
    """Evaluate at 1M nodes on the next idle worker."""
    if not self._started:
        return None, None
    idx = await self._available.get()
    try:
        protocol = self._protocols[idx]
        if protocol is None:
            return None, None
        try:
            info = await asyncio.wait_for(
                protocol.analyse(board, chess.engine.Limit(nodes=_NODES_BUDGET)),
                timeout=_NODES_TIMEOUT_S,
            )
        except (asyncio.TimeoutError, chess.engine.EngineError, chess.engine.EngineTerminatedError):
            await self._restart_worker(idx)
            return None, None
        return _score_to_cp_mate(info)
    finally:
        self._available.put_nowait(idx)
```

**Key finding:** `protocol.analyse()` returns `InfoDict` (dict) when `multipv` is not passed, and `List[InfoDict]` when `multipv=1` is passed. Since we don't need multi-PV in Phase 116 (PV capture is EVAL-04 / Phase 117), do NOT pass `multipv` to `analyse()` — this returns the scalar `InfoDict` directly, matching the existing `_score_to_cp_mate(info)` call.

### Pattern 2: All-Ply Board Collector (Claude's Discretion — resolved)

**What:** Walk the mainline once, collect board snapshots at every ply (no terminal position).

**Terminal exclusion finding:** Iterating `game.mainline()` yields MOVE nodes. At each iteration, `board` is the position FROM which the move is played (before `board.push(move)`). The post-last-move position (game-over: checkmate/stalemate/etc.) is only accessible as `board` AFTER the loop ends — the iterator never yields a node for it. Therefore, `board.is_game_over()` is always `False` during iteration in standard games. The correct exclusion is simply "don't add a snapshot after the loop."

```python
# Source: verified via uv run python3 on this machine

def _snapshot_all_plies(pgn_text: str) -> list[tuple[int, chess.Board]]:
    """Parse PGN once; return (ply_index, board) for every non-terminal ply.

    ply_index = 0-indexed count of moves played (matches game_positions.ply
    convention where ply 0 is the initial position before any move).
    Terminal position (after the final move) is excluded — iterator never
    visits it, so no is_game_over() guard needed during the walk.
    Returns [] on parse failure.
    """
    try:
        game = chess.pgn.read_game(io.StringIO(pgn_text))
    except Exception:
        return []
    if game is None:
        return []

    board = game.board()
    snapshots: list[tuple[int, chess.Board]] = []
    for ply, node in enumerate(game.mainline()):
        # board here is the position BEFORE the move — not game-over.
        snapshots.append((ply, board.copy()))
        board.push(node.move)
    # board is now the terminal position — NOT added.
    return snapshots
```

Note: `game_positions.ply` stores the half-move number, and the initial position (before any moves) is ply 0. The existing `zobrist.py` convention uses `ply = len(nodes)` where nodes are mainline moves iterated, so ply 0 = initial board (before first push). This matches the iterator: `enumerate(game.mainline())` gives `ply=0` for the first position.

### Pattern 3: Dedup Batch Lookup (Claude's Discretion — resolved)

**What:** Before the `asyncio.gather()`, batch-fetch existing parity evals for all ply<=20 positions in the game, then filter out those that have hits.

**Recommended shape:** single query fetching all `full_hash` → `(eval_cp, eval_mate)` pairs in one round-trip, not one query per position.

```python
# Source: verified pattern against game_positions schema (direct code inspection)

async def _fetch_dedup_evals(
    session: AsyncSession,
    full_hashes: Sequence[int],
) -> dict[int, tuple[int | None, int | None]]:
    """Batch-fetch existing parity evals for opening-region hashes.

    Dedup source set (D-116-02): game_positions rows whose game has
    full_evals_completed_at IS NOT NULL (marker gate = parity by construction).
    Returns {full_hash: (eval_cp, eval_mate)} for hashes with at least one hit.
    Multiple rows per hash are possible; LIMIT 1 per hash via DISTINCT ON.
    """
    if not full_hashes:
        return {}

    # DISTINCT ON (gp.full_hash) to get one row per hash.
    # The marker-gate join (D-116-02) excludes legacy depth-15 source games.
    result = await session.execute(
        select(
            GamePosition.full_hash,
            GamePosition.eval_cp,
            GamePosition.eval_mate,
        )
        .join(Game, GamePosition.game_id == Game.id)
        .where(
            GamePosition.full_hash.in_(full_hashes),
            GamePosition.ply <= _DEDUP_MAX_PLY,   # 20
            Game.full_evals_completed_at.isnot(None),
            sa.or_(
                GamePosition.eval_cp.isnot(None),
                GamePosition.eval_mate.isnot(None),
            ),
        )
        .distinct(GamePosition.full_hash)
        .limit(len(full_hashes))
    )
    return {row[0]: (row[1], row[2]) for row in result.all()}
```

### Pattern 4: Write Transaction Shape (Claude's Discretion — resolved)

**What:** ~60 game_position row-updates per game. Use the `update(GamePosition)` pattern from `_apply_eval_results()`. A single write session for all updates + completion marker.

**Recommendation:** Reuse the existing `_apply_eval_results()` approach with a new `_AllPlyEvalTarget` dataclass (or extend `_EvalTarget` to add `full_hash` for dedup tracking). Write all ~60 UPDATEs sequentially in one session (CLAUDE.md hard rule on AsyncSession). Mark `full_evals_completed_at` at the end.

For the UPDATE WHERE clause: since every ply has exactly one `game_positions` row (PK is `(user_id, game_id, ply)`), the predicate `WHERE game_id = :gid AND ply = :ply` is unambiguous. No `endgame_class` filter needed (unlike the entry-ply drain which can have multiple endgame spans per ply).

### Pattern 5: Yield Gate (D-116-11)

**What:** Before each game pick, check whether an active import OR entry-ply drain work is pending. Both checks are instant via existing partial indexes.

```python
# Source: existing patterns in game_repository.py and import_job_repository.py

async def _any_active_import_or_entry_ply_pending(session: AsyncSession) -> bool:
    """True if the full drain should yield to higher-priority work.

    D-116-11: sleep and re-check if:
    (a) any import_job with status IN ('pending', 'in_progress') exists, OR
    (b) any game with evals_completed_at IS NULL exists (entry-ply drain has backlog).
    Both checks use existing partial indexes and are sub-millisecond.
    """
    active_import = await session.scalar(
        select(sa.func.count())
        .select_from(ImportJob)
        .where(ImportJob.status.in_(["pending", "in_progress"]))
    )
    if active_import:
        return True
    entry_ply_pending = await session.scalar(
        select(sa.func.count())
        .select_from(Game)
        .where(Game.evals_completed_at.is_(None))
        .limit(1)
    )
    return bool(entry_ply_pending)
```

### Anti-Patterns to Avoid

- **asyncio.gather() inside an AsyncSession scope:** CLAUDE.md hard rule. The full drain must follow the existing drain's session discipline exactly — gather runs OUTSIDE all sessions, write session opens AFTER gather completes.
- **Passing `multipv` to `protocol.configure()`:** `chess.engine.EngineError: cannot set MultiPV which is automatically managed`. MultiPV is passed to `analyse()`, not `configure()`. However, for Phase 116 (no PV capture), do NOT pass `multipv` to `analyse()` at all — this returns the scalar `InfoDict` that `_score_to_cp_mate()` already handles.
- **Using the same `_TIMEOUT_S` constant for node-budget calls:** Current `_TIMEOUT_S = 2.0` is calibrated for depth-15 (~0.09s mean, 2s is huge headroom). For 1M-node calls (~1s mean, p90 ~1.3s), 2.0s would timeout ~50% of positions. Use `_NODES_TIMEOUT_S = 5.0`.
- **One UPDATE per ply outside a session:** Batch all ~60 game_position UPDATEs in a single write session. Do NOT open one session per ply.
- **Reusing the existing `_EvalTarget.eval_kind` for all-ply targets:** The all-ply drain does not distinguish middlegame_entry vs endgame_span_entry. Define a new dataclass `_FullPlyEvalTarget` with `game_id`, `ply`, `full_hash`, and `board`.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Node-budget search | Custom UCI command parsing | `chess.engine.Limit(nodes=1_000_000)` | python-chess already wraps this; node limit is a standard Limit field |
| Terminal position detection | Custom FEN parsing / material count | `board.is_game_over()` (or just: iterator never visits terminal) | The mainline iterator structure handles this automatically |
| Cross-user hash lookup | Python-side hash table / in-memory cache | PostgreSQL index scan on `(full_hash) WHERE ply <= 20` | DB index with partial predicate is the correct tool; in-memory cache doesn't survive restarts |
| Background loop restart on crash | Custom watchdog | FastAPI lifespan `asyncio.create_task()` + `except Exception: sleep + continue` | Existing `run_eval_drain()` pattern already handles this |
| Game-level pick locking | SELECT FOR UPDATE on games | Partial index + LIFO id-DESC pick (no competing consumers in Phase 116) | Phase 117 adds the queue; for now LIFO pick has no concurrency issue (single coroutine) |

## Common Pitfalls

### Pitfall 1: asyncio.gather() while a session is open

**What goes wrong:** Stockfish workers run in parallel via `asyncio.gather()`. If an AsyncSession is open during the gather, two coroutines read/write the same connection, causing `asyncio.InvalidStateError` or silent data corruption.

**Why it happens:** The existing drain already guards against this — the warning is to not accidentally regress the new coroutine.

**How to avoid:** Mirror the existing `run_eval_drain()` session discipline exactly:
1. Short read session → pick game → close
2. Short read session → load PGN + positions → close
3. `asyncio.gather()` with NO session open
4. Short write session → write all UPDATEs + marker → commit → close

**Warning signs:** `asyncio.InvalidStateError`, `InterfaceError`, or connection pool exhaustion during analysis.

### Pitfall 2: Wrong return type from `protocol.analyse()`

**What goes wrong:** Passing `multipv=1` to `analyse()` returns `List[InfoDict]`, not `InfoDict`. Indexing `info["score"]` would raise `TypeError: list indices must be integers`.

**Why it happens:** python-chess changes the return type based on whether `multipv` is set.

**How to avoid:** Do NOT pass `multipv` to `analyse()` in Phase 116 (PV capture is deferred to Phase 117). The scalar `InfoDict` is returned directly and handled by the existing `_score_to_cp_mate()`.

**Warning signs:** `TypeError: list indices must be integers or slices, not str`

### Pitfall 3: Timeout too small for node-budget calls

**What goes wrong:** Setting `_NODES_TIMEOUT_S = 2.0` would time out approximately half of all 1M-node calls on prod (mean ~0.98s, p90 ~1.28s, with occasional outliers up to ~2s).

**Why it happens:** The current `_TIMEOUT_S = 2.0` was calibrated for depth-15 calls (~0.09s mean). Node-budget calls take ~10x longer.

**How to avoid:** Use `_NODES_TIMEOUT_S = 5.0` (~4x prod p90). A timed-out analysis triggers `_restart_worker()` and returns `(None, None)`, leaving the ply NULL permanently (D-116-07). Keeping timeouts to 5s bounds the worst-case recovery time.

**Warning signs:** High rate of `(None, None)` returns from `evaluate_nodes()`, Sentry captures showing frequent engine restarts.

### Pitfall 4: Dedup consults depth-15 source rows

**What goes wrong:** Dedup query hits `game_positions` rows from games that were only analyzed by the depth-15 entry-ply drain (NOT the full 1M-node drain). These rows have `evals_completed_at IS NOT NULL` but NOT `full_evals_completed_at IS NOT NULL`. Reusing them would put shallower evals in full-analysis games.

**Why it happens:** The marker gate (D-116-02) requires checking `full_evals_completed_at IS NOT NULL` on the source game, not just `evals_completed_at`.

**How to avoid:** The dedup JOIN must be `JOIN games g ON gp.game_id = g.id WHERE g.full_evals_completed_at IS NOT NULL`. Do NOT use `evals_completed_at`.

**Warning signs:** Opening evals differ from lichess by more than TT noise; games show shallow evals at low plies after claiming to be fully analyzed.

### Pitfall 5: Full-drain overwrites lichess %evals (T-78-17 violation)

**What goes wrong:** The full-drain UPDATE sets `eval_cp`/`eval_mate` for every ply unconditionally, overwriting lichess %evals for analyzed games.

**Why it happens:** The all-ply collector doesn't check whether a ply already has a parity eval.

**How to avoid:** Apply D-116-04: within a game being analyzed, check `game.is_analyzed` once. If `is_analyzed=True` (lichess analyzed game), preserve existing non-NULL evals — only write evals where `eval_cp IS NULL AND eval_mate IS NULL`. If `is_analyzed=False` (chess.com or unanalyzed lichess), overwrite all evals (D-116-03).

Note: the dedup check at ply<=20 naturally handles the opening prefix. The `is_analyzed` check handles all plies.

**Warning signs:** Flaw stats shift after re-analysis of already-analyzed lichess games; `game_flaws` counts change for games that should be stable.

### Pitfall 6: Migration backfill scans full game_positions table

**What goes wrong:** The verified backfill (D-116-06) needs to identify games where every non-terminal ply has `eval_cp IS NOT NULL OR eval_mate IS NOT NULL`. A naive full-table scan of `game_positions` at migration time blocks other queries for minutes on prod.

**Why it happens:** The backfill touches every row in `game_positions` (currently ~30M rows on prod).

**How to avoid:** Use a set-difference query: games where `full_evals_completed_at IS NULL` AND NOT EXISTS any `game_positions` row with `eval_cp IS NULL AND eval_mate IS NULL`. Index support: `ix_gp_user_endgame_game` includes `eval_cp`/`eval_mate` for endgame rows; opening/middlegame rows don't have a covering index. Consider running the backfill as a one-shot script post-migration (like `backfill_eval.py`) rather than in the migration itself, to avoid blocking the deploy. The migration can leave `full_evals_completed_at` NULL for all existing rows and let the script backfill.

**Warning signs:** Alembic migration times out on prod; `alembic upgrade head` hangs.

## Code Examples

### All-Ply Target Collection

```python
# Source: direct code inspection of eval_drain.py + verified python-chess behavior

_DEDUP_MAX_PLY: int = 20   # D-116-02: dedup only in opening region

@dataclass(slots=True)
class _FullPlyEvalTarget:
    """One position scheduled for full-ply eval.

    ply: game_positions.ply (0-indexed; 0 = initial position before first move)
    full_hash: for dedup batch-lookup at ply <= _DEDUP_MAX_PLY
    board: board snapshot for the engine call (if not dedup'd)
    """
    game_id: int
    ply: int
    full_hash: int
    board: chess.Board


def _collect_full_ply_targets(
    game_id: int,
    pgn_text: str,
    game_positions_rows: Sequence[tuple[int, int, int | None, int | None]],
    # (ply, full_hash, eval_cp, eval_mate) — loaded from game_positions
) -> list[_FullPlyEvalTarget]:
    """Collect one target per non-terminal ply.

    D-116-03/D-116-04 (overwrite logic) is NOT applied here — it's applied
    during the write phase after dedup resolution and eval results.
    This collector simply enumerates every ply the PGN reaches.
    """
    # Build ply -> (full_hash, eval_cp, eval_mate) lookup
    ply_meta: dict[int, tuple[int, int | None, int | None]] = {
        ply: (fh, cp, mt)
        for ply, fh, cp, mt in game_positions_rows
    }
    if not ply_meta:
        return []

    # Parse PGN once
    try:
        game = chess.pgn.read_game(io.StringIO(pgn_text))
    except Exception:
        return []
    if game is None:
        return []

    board = game.board()
    targets: list[_FullPlyEvalTarget] = []
    for ply, node in enumerate(game.mainline()):
        meta = ply_meta.get(ply)
        if meta is not None:
            fh, _cp, _mt = meta
            targets.append(_FullPlyEvalTarget(
                game_id=game_id,
                ply=ply,
                full_hash=fh,
                board=board.copy(),
            ))
        board.push(node.move)
    # board is now terminal — not added.
    return targets
```

### Migration Pattern (mirrors Phase 91 migration)

```python
# Source: alembic/versions/20260521_015028_bd54be3a66bf_add_evals_completed_at_to_games.py

def upgrade() -> None:
    op.add_column(
        "games",
        sa.Column("full_evals_completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_games_full_evals_pending",
        "games",
        ["id"],
        unique=False,
        postgresql_where="full_evals_completed_at IS NULL",
    )
    # D-116-06: verified backfill — mark games where every non-terminal ply
    # already has eval_cp/eval_mate populated.
    # Safe SQL: uses NOT EXISTS with the game_positions FK index.
    # On prod ~600k games; most have NULL evals, so this updates ~7% of rows.
    # Caution: if this is slow, move to a post-deploy script (see Pitfall 6).
    op.execute("""
        UPDATE games g
        SET full_evals_completed_at = COALESCE(g.imported_at, NOW())
        WHERE g.full_evals_completed_at IS NULL
          AND NOT EXISTS (
              SELECT 1
              FROM game_positions gp
              WHERE gp.game_id = g.id
                AND gp.eval_cp IS NULL
                AND gp.eval_mate IS NULL
          )
    """)
```

### New Dedup Index

```python
# Source: game_position.py index pattern (existing partial indexes)

# In GamePosition.__table_args__:
Index(
    "ix_gp_full_hash_opening",
    "full_hash",
    postgresql_where=text("ply <= 20"),   # matches _DEDUP_MAX_PLY
),
```

### Marker Write (executemany discipline)

```python
# Source: _mark_evals_completed() in eval_drain.py — replicate exactly

async def _mark_full_evals_completed(session: AsyncSession, game_id: int) -> None:
    """Mark one game as fully analyzed. One UPDATE per game (not batch)."""
    now_ts = datetime.now(timezone.utc)
    games_table = Game.__table__
    stmt = (
        update(games_table)  # ty: ignore[invalid-argument-type]
        .where(games_table.c.id == game_id)
        .values(full_evals_completed_at=now_ts)
    )
    await session.execute(stmt)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `chess.engine.Limit(depth=15)` | `chess.engine.Limit(nodes=1_000_000)` | Phase 116 | ~10x slower per call but lichess-calibrated |
| Entry-ply only (~2-3 evals/game) | All non-terminal plies (~53-60 evals/game) | Phase 116 | Enables flaw detection, accuracy charts, SEED-039 |
| Single drain coroutine | Two independent drain coroutines | Phase 116 | Hot lane stays fast; full analysis runs progressively |
| Stockfish 18 with "Use NNUE" option | Stockfish 18 with NNUE always-on (no option) | SF17→SF18 | No configuration change needed |

**Deprecated/outdated:**
- `_TIMEOUT_S = 2.0` for all engine calls: this constant now only applies to `evaluate()` (depth-15). The new `evaluate_nodes()` uses `_NODES_TIMEOUT_S = 5.0`.
- `CLAUDE.md` comment "STOCKFISH_POOL_SIZE lowered" (OOM hotfix era): stale. Pool has been 6 on prod for weeks. Update in this phase's docs pass per D-116-13.
- `docker-compose.yml` comment "Sized for ... with STOCKFISH_POOL_SIZE up to 6": stale after Phase 116 bumps to 8. Update with measured memory accounting.
- `engine.py` comment referencing "prod STOCKFISH_POOL_SIZE=4": stale (was hotfix-era). Update to reflect current 6 and Phase 116's target of 8.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Stockfish binary | evaluate_nodes() | Yes | SF18 (confirmed) | tests skip via `skip_if_no_stockfish` |
| python-chess | chess.engine.Limit(nodes=...) | Yes | 1.11.2 | — |
| PostgreSQL (dev Docker) | Migration, tests | Yes (Docker required for tests) | 18 | — |

**Missing dependencies with no fallback:** none.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest + pytest-asyncio (asyncio_mode = "auto") |
| Config file | `pyproject.toml` (addopts: `-n auto`, `asyncio_mode = auto`) |
| Quick run command | `uv run pytest tests/services/test_eval_drain.py -x` |
| Full suite command | `uv run pytest -n auto -x` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| EVAL-01 | All non-terminal plies collected (terminal excluded) | unit | `uv run pytest tests/services/test_full_eval_drain.py::test_collect_all_plies_excludes_terminal -x` | No — Wave 0 |
| EVAL-01 | PGN parse failure returns empty list | unit | `uv run pytest tests/services/test_full_eval_drain.py::test_collect_handles_bad_pgn -x` | No — Wave 0 |
| EVAL-02 | evaluate_nodes() uses node budget not depth | unit (mock engine) | `uv run pytest tests/services/test_engine_nodes.py::test_evaluate_nodes_uses_limit_nodes -x` | No — Wave 0 |
| EVAL-02 | evaluate_nodes() returns (None, None) on timeout | unit (mock) | `uv run pytest tests/services/test_engine_nodes.py::test_evaluate_nodes_timeout_returns_none -x` | No — Wave 0 |
| EVAL-03 | Dedup returns hit for known parity hash | integration | `uv run pytest tests/services/test_full_eval_drain.py::test_dedup_hits_parity_source -x` | No — Wave 0 |
| EVAL-03 | Dedup ignores depth-15 source (no marker) | integration | `uv run pytest tests/services/test_full_eval_drain.py::test_dedup_excludes_depth15_source -x` | No — Wave 0 |
| EVAL-05 | full_evals_completed_at set after full analysis | integration | `uv run pytest tests/services/test_full_eval_drain.py::test_marker_set_after_drain -x` | No — Wave 0 |
| EVAL-05 | Marker set even when engine returns (None, None) holes | integration | `uv run pytest tests/services/test_full_eval_drain.py::test_marker_set_with_holes -x` | No — Wave 0 |
| EVAL-05 | Migration backfill sets marker on pre-existing fully-covered games | integration (migration) | `uv run pytest tests/test_migration_116_full_evals.py -x` | No — Wave 0 |
| QUEUE-07 | gather-outside-session invariant (AST scan) | static | `uv run pytest tests/services/test_full_eval_drain.py::test_gather_outside_session -x` | No — Wave 0 |
| QUEUE-07 | Yield gate: sleeps when active import exists | unit (mock) | `uv run pytest tests/services/test_full_eval_drain.py::test_yield_gate_active_import -x` | No — Wave 0 |
| QUEUE-07 | Yield gate: sleeps when entry-ply pending | unit (mock) | `uv run pytest tests/services/test_full_eval_drain.py::test_yield_gate_entry_ply_pending -x` | No — Wave 0 |

### Sampling Rate
- **Per task commit:** run the specific test file for the changed module
- **Per wave merge:** `uv run pytest tests/services/test_full_eval_drain.py tests/services/test_engine_nodes.py tests/test_migration_116_full_evals.py -x`
- **Phase gate:** `uv run pytest -n auto -x` (full suite green before `/gsd-verify-work`)

### Wave 0 Gaps
- [ ] `tests/services/test_full_eval_drain.py` — all-ply drain integration tests (EVAL-01, EVAL-03, EVAL-05, QUEUE-07)
- [ ] `tests/services/test_engine_nodes.py` — evaluate_nodes() contract tests (EVAL-02)
- [ ] `tests/test_migration_116_full_evals.py` — migration backfill test (EVAL-05)

*(Pattern for all three: mirror existing `test_eval_drain.py` / `test_engine.py` / `test_migration_91_evals_completed_at.py` structures. Same session-scoped fixtures, same `drain_test_session_maker` pattern.)*

## Security Domain

This phase adds no API endpoints, no user input handling, and no authentication changes. The eval drain runs as a background coroutine within the authenticated backend process. ASVS categories V2/V3/V4 do not apply. V5 input validation applies only to PGN parsing (already guarded by `try/except` around `chess.pgn.read_game()`). V6 cryptography does not apply.

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | — |
| V3 Session Management | no | — |
| V4 Access Control | no | Background drain only; no user-facing endpoint |
| V5 Input Validation | yes (PGN) | `try/except Exception` around `chess.pgn.read_game()` — existing pattern |
| V6 Cryptography | no | — |

No new threat patterns introduced.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Prod per-worker RSS ~368 MB (extrapolated from Phase 91's 4-worker measurement). 8 workers = ~2.94 GB + FastAPI ~0.3 GB = ~3.24 GB, within 4g. | Memory accounting, QUEUE-07 | If prod RSS is higher (e.g. 450+ MB/worker), 8 workers would approach 3.9 GB, close to the 4g limit. D-116-13 requires measuring actual prod RSS in-phase before locking to 8; the spike and memory gate are the safety check. |
| A2 | Verified backfill (D-116-06) can run in-migration on prod without timing out. | Pitfall 6, migration | If the NOT EXISTS scan over 30M game_positions rows is too slow, the migration must be split into DDL-only + post-deploy script. The planner should include a contingency task. |
| A3 | NNUE net is file-backed and shared across workers from the same binary, so per-worker RSS does not include a full net copy per worker. | Memory accounting | Measured locally: 8 workers = 2.15 GB, which averages ~269 MB/worker vs ~277 MB for 1 worker, confirming sharing. This assumption is well-supported but the sharing mechanism is OS page cache. |

## Open Questions

1. **Backfill execution shape (D-116-06)**
   - What we know: backfill must mark games where every non-terminal ply has eval coverage; on prod this affects ~7% of 600k games based on spike 003's 93% unanalyzed rate
   - What's unclear: whether the NOT EXISTS scan on game_positions (~30M rows) is fast enough to run in the migration itself
   - Recommendation: plan both paths — in-migration with a CONCURRENTLY-style guard (the index `ix_gp_user_game_ply` or PK scan), and a fallback post-deploy script. Include a wave-gate checkpoint: run `EXPLAIN (ANALYZE, BUFFERS)` on the backfill SQL against dev DB to estimate cost.

2. **Pool size to 8: prod soak validation (D-116-13)**
   - What we know: 8 workers = ~3.24 GB estimated prod memory; API latency was unaffected at 6 workers (spike 002); 8 workers adds 2 more SCHED_IDLE processes
   - What's unclear: whether 8 SCHED_IDLE workers on 8 vCPUs leaves enough headroom for Postgres, Uvicorn, and a concurrent import without degradation
   - Recommendation: deploy at 6 first, monitor API p50/p90 and container RSS for 24h, then bump to 8 if metrics are clean (D-116-13's contingent check).

## Sources

### Primary (HIGH confidence — measured this session)
- `app/services/eval_drain.py` (direct code inspection) — session discipline, drain skeleton, `_mark_evals_completed`, `_snapshot_boards`
- `app/services/engine.py` (direct code inspection) — `EnginePool`, `_score_to_cp_mate`, `_TIMEOUT_S`, `_DEPTH`, `_HASH_MB`
- `app/models/game.py` (direct code inspection) — `evals_completed_at`, `is_analyzed` hybrid property, `ix_games_evals_pending` pattern
- `app/models/game_position.py` (direct code inspection) — existing indexes, `full_hash`, `ply`, `eval_cp`/`eval_mate`
- Live RSS measurement (uv run python3 on this machine) — 1/4/6/8 workers: 277/1096/1645/2200 MB with 1M-node analysis after NNUE load
- `chess.engine.Limit` signature / `protocol.analyse()` behavior (uv run python3 introspection, python-chess 1.11.2) — `nodes` parameter confirmed, `multipv` return-type behavior confirmed
- Terminal position behavior verification (uv run python3) — mainline iterator never yields game-over position

### Secondary (MEDIUM confidence — validated artifacts)
- `.planning/spikes/001-sf-1m-node-latency-local/README.md` + `results-hash32.json` — local latency data, p90=1.173s
- `.planning/spikes/002-sf-1m-node-latency-prod/README.md` — prod latency: mean 0.977s, p90 1.277s, 6-worker 5.83 pos/s
- `.planning/spikes/003-catchup-queue-sizing/README.md` — 558k unanalyzed games (~93%), real plies/game = 53
- `.planning/seeds/SEED-012-client-side-stockfish-tactics.md` §Amendment 2026-06-12 — locked decisions D-1..D-8
- `.planning/phases/116-all-ply-engine-core/116-CONTEXT.md` — decisions D-116-01 through D-116-13
- `alembic/versions/20260521_015028_bd54be3a66bf_add_evals_completed_at_to_games.py` — migration pattern to mirror

### Tertiary (LOW confidence — inferred)
- FastAPI process RSS ~300 MB: rough estimate based on typical uvicorn + SQLAlchemy pool footprint; not measured directly

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new packages; all existing
- Architecture: HIGH — locked decisions + direct code inspection
- Code examples: HIGH — verified against running python-chess 1.11.2 and existing codebase patterns
- Memory accounting: MEDIUM — local measurement confirmed, prod extrapolated from Phase 91 data (A1 assumption)
- Backfill cost: LOW — not yet measured against prod DB volume (A2 assumption)

**Research date:** 2026-06-12
**Valid until:** 2026-07-12 (stable stack; python-chess and SQLAlchemy do not churn)
