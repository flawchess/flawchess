# Architecture Research

**Domain:** Incremental eval-pipeline extension — MultiPV=2 storage + offline re-tagger
**Researched:** 2026-06-29
**Confidence:** HIGH (derived from first-party source reading; no external fetch required)

## Standard Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                         API / Routers                                │
│   /api/eval/remote/lease   /api/eval/remote/submit                  │
│   (HTTP only, no business logic)                                     │
├─────────────────────────────────────────────────────────────────────┤
│                        Services (business logic)                     │
│                                                                      │
│  eval_drain.py          flaws_service.py       forcing_line_gate.py  │
│  ┌──────────────┐       ┌────────────────┐     ┌──────────────────┐  │
│  │_full_drain_  │──────>│classify_game_  │────>│apply_forcing_    │  │
│  │tick()        │       │flaws()         │     │line_filter()     │  │
│  │              │       │                │     │(NEW, pure math)  │  │
│  │ step 3b NEW: │       │_detect_tactic_ │     └──────────────────┘  │
│  │ MultiPV=2    │       │for_flaw()      │              │            │
│  │ gather per   │       │(gate pre-filter│              │            │
│  │ flaw node    │       │ added)         │              v            │
│  └──────────────┘       └────────────────┘     tactic_detector.py   │
│         │                      │               ┌──────────────────┐  │
│         │                      │               │detect_tactic_    │  │
│         v                      v               │motif() UNCHANGED │  │
│  engine.py                game_flaws_repo.py   └──────────────────┘  │
│  ┌──────────────┐         ┌────────────────┐                         │
│  │EnginePool    │         │write_flaws()   │                         │
│  │evaluate_nodes│         │ + JSONB blobs  │                         │
│  │_multipv2()   │         │ (NEW fields)   │                         │
│  │(NEW method)  │         └────────────────┘                         │
│  └──────────────┘                                                    │
├─────────────────────────────────────────────────────────────────────┤
│                      Repositories (DB access only)                   │
│   game_flaws_repository.py    eval_queue_service.py                 │
├─────────────────────────────────────────────────────────────────────┤
│                         PostgreSQL                                   │
│   game_flaws.allowed_pv_lines JSONB   (NEW, Alembic migration)      │
│   game_flaws.missed_pv_lines  JSONB   (NEW, Alembic migration)      │
│   game_positions.pv (existing, MultiPV=1 best-move line, unchanged) │
└─────────────────────────────────────────────────────────────────────┘
```

```
┌─────────────────────────────────────────────────────────────────────┐
│                   Remote Worker (headless CLI)                       │
│   scripts/remote_worker.py  (MODIFIED)                              │
│                                                                      │
│   1. Lease full game  =>  run MultiPV=1 per ply (existing)          │
│   2. In-memory classify_game_flaws => identify flaw ply numbers      │
│   3. Run MultiPV=2 per flaw-PV-node (NEW)                           │
│   4. Submit evals + flaw_pv_lines (SubmitRequest extended)          │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│                  Offline Scripts (new / modified)                    │
│   scripts/backfill_multipv.py  (NEW)  -- writes JSONB to existing   │
│                                          game_flaws rows             │
│   scripts/retag_flaws.py       (NEW)  -- pure offline re-tagger;    │
│                                          reads JSONB, applies gate,  │
│                                          updates tactic columns       │
└─────────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Responsibility | New vs Modified |
|-----------|----------------|-----------------|
| `app/services/forcing_line_gate.py` | Pure-math forcing-line gate: `PvNode` TypedDict, `is_solver_node_forced()`, `apply_forcing_line_filter()`. No DB, no engine. | NEW |
| `app/models/game_flaw.py` | Add `allowed_pv_lines: JSONB` + `missed_pv_lines: JSONB` mapped columns | MODIFIED |
| Alembic migration | `ADD COLUMN allowed_pv_lines JSONB, ADD COLUMN missed_pv_lines JSONB` on `game_flaws` | NEW |
| `app/repositories/game_flaws_repository.py` | Write/read the two JSONB columns alongside existing tactic columns | MODIFIED |
| `app/services/engine.py` | Add `evaluate_nodes_multipv2(board)` public API + `EnginePool.evaluate_nodes_multipv2(board)` + internal `_analyse_multipv2()`. Uses same 1M-node budget, `multipv=2` UCI option | MODIFIED |
| `app/services/eval_drain.py::_full_drain_tick` | Add step 3b: in-memory flaw identification, MultiPV=2 gather per flaw-PV-node, JSONB blob assembly. Pass blobs to write session | MODIFIED |
| `app/services/flaws_service.py::_detect_tactic_for_flaw` | Accept optional `pv_lines_by_ply` param. When present, call `apply_forcing_line_filter` before `detect_tactic_motif`. Fall through when absent (backward compat) | MODIFIED |
| `app/schemas/eval_remote.py` | Extend `SubmitRequest` with optional `flaw_pv_lines: list[FlawPvLinesSubmit]` (additive, no break of existing workers) | MODIFIED |
| `scripts/remote_worker.py` | After MultiPV=1 pass: in-memory flaw classify, MultiPV=2 per flaw node, include `flaw_pv_lines` in submit body | MODIFIED |
| `scripts/backfill_multipv.py` | Offline backfill: reads existing `game_flaws` where JSONB is NULL, re-evaluates flaw-PV-node positions with MultiPV=2, writes blobs | NEW |
| `scripts/retag_flaws.py` | Offline re-tagger: reads `game_flaws` where `allowed_pv_lines IS NOT NULL`, applies gate, updates tactic columns. `--user-id` and `--dry-run` flags | NEW |
| `app/services/tactic_detector.py` | UNCHANGED. The forcing-line gate is a pre-filter in the caller layer; `detect_tactic_motif` itself is not modified | UNCHANGED |

## Recommended Project Structure

The v1.30 additions slot into existing directories without structural changes:

```
app/
├── models/
│   └── game_flaw.py              MODIFIED: +allowed_pv_lines, +missed_pv_lines JSONB
├── repositories/
│   └── game_flaws_repository.py  MODIFIED: write/read JSONB columns
├── schemas/
│   └── eval_remote.py            MODIFIED: +FlawPvLinesSubmit, +flaw_pv_lines in SubmitRequest
├── services/
│   ├── engine.py                 MODIFIED: +evaluate_nodes_multipv2, +_analyse_multipv2
│   ├── eval_drain.py             MODIFIED: +step 3b in _full_drain_tick
│   ├── flaws_service.py          MODIFIED: _detect_tactic_for_flaw gains gate pre-filter
│   ├── forcing_line_gate.py      NEW: PvNode, is_solver_node_forced, apply_forcing_line_filter
│   └── tactic_detector.py        UNCHANGED
└── ...

scripts/
├── backfill_multipv.py           NEW: fills JSONB for existing game_flaws rows
├── retag_flaws.py                NEW: offline re-tagger applying forcing-line gate
└── ... (existing backfill_flaws.py, backfill_tactic_tags.py unchanged)

migrations/
└── <hash>_add_game_flaws_pv_lines.py   NEW: Alembic migration
```

## Architectural Patterns

### Pattern 1: Gate as Pre-Filter, Detector Unchanged

**What:** The forcing-line gate (`apply_forcing_line_filter`) sits above `detect_tactic_motif` in `_detect_tactic_for_flaw`. When the gate rejects a PV line, the function returns `(None, None, None, None)` before ever calling the detector. `detect_tactic_motif` itself is not touched.

**When to use:** Any time new filtering logic wraps an existing pure detector. Keeps the fixture-tested, stable detector unchanged and adds the gate as a caller-layer concern.

**Trade-offs:** The gate is invisible inside `detect_tactic_motif` — callers that bypass `_detect_tactic_for_flaw` and call the detector directly skip the gate. In this codebase that is fine: all production paths go through `_detect_tactic_for_flaw`.

```python
# forcing_line_gate.py (new)
LICHESS_FORCING_MARGIN: float = 0.35  # p(best) - p(second) > 0.35 in [0,1] space
ALREADY_WINNING_CP: int = 300         # prev_score > 300cp => reject (no tactic needed)
STILL_WINNING_FLOOR_CP: int = 200     # stop extending when best drops below 200cp

class PvNode(TypedDict):
    b: int | None    # best eval cp (white-perspective)
    bm: int | None   # best eval mate
    s: int | None    # second eval cp
    sm: int | None   # second eval mate
    su: str | None   # second best move UCI

def is_solver_node_forced(node: PvNode) -> bool:
    """True when best-second win-prob gap > LICHESS_FORCING_MARGIN (0.35)."""
    ...

def apply_forcing_line_filter(
    pv_lines: list[PvNode],
    prev_eval_cp: int | None,     # already-winning reject (>300cp)
    prev_eval_mate: int | None,
) -> bool:
    """True = PV line passes the gate; False = reject."""
    ...

# flaws_service.py (modified)
def _detect_tactic_for_flaw(
    n: int,
    fen_map: dict[int, str],
    positions: list[GamePosition],
    pv_by_ply: Mapping[int, str] | None = None,
    pv_lines_by_ply: dict[int, list[PvNode]] | None = None,  # NEW
    orientation: Literal["allowed", "missed"] = "allowed",
) -> tuple[int | None, int | None, int | None, int | None]:
    ...
    # NEW gate: applied before detect_tactic_motif when JSONB data available
    if pv_lines_by_ply is not None:
        pv_lines = pv_lines_by_ply.get(n if orientation == "missed" else n + 1)
        if pv_lines is not None:
            prev_cp = positions[n].eval_cp
            prev_mate = positions[n].eval_mate
            if not apply_forcing_line_filter(pv_lines, prev_cp, prev_mate):
                return None, None, None, None
    return detect_tactic_motif(board, pv, has_forced_mate=has_forced_mate)
```

### Pattern 2: Two-Phase Flaw Processing in the Eval Drain

**What:** `_full_drain_tick` runs `classify_game_flaws` twice: once in step 3b (no DB session, pure function) to identify flaw positions for the MultiPV=2 gather, and once in step 4 (write session) as the authoritative write. The step-3b call is discarded; it only produces the flaw-ply set needed to build the MultiPV=2 task list.

**When to use:** When a downstream computation (MultiPV=2 task list) depends on the output of a pure function (`classify_game_flaws`) that also runs inside the write session. Calling it twice avoids threading interim results through the session boundary.

**Trade-offs:** `classify_game_flaws` is called twice per game, adding ~1ms CPU (pure Python, no I/O). Justified because it keeps the step-3b / step-4 boundary clean and avoids an AsyncSession-open span covering the MultiPV=2 gather (which would violate CLAUDE.md's "no asyncio.gather inside AsyncSession" hard rule).

```python
# eval_drain.py (modified _full_drain_tick, new step 3b)
async def _full_drain_tick() -> bool:
    ...
    # Step 3: existing full-game MultiPV=1 gather (unchanged)
    engine_results_raw = await asyncio.gather(
        *(engine_service.evaluate_nodes_with_pv(t.board) for t in engine_targets)
    )
    pv_by_ply = _build_pv_by_ply(engine_targets, engine_results_raw)

    # Step 3b: NEW -- identify flaws, run MultiPV=2 on flaw-PV-node positions.
    # classify_game_flaws is pure; safe to call with no session open.
    flaw_records_preview = classify_game_flaws(game, positions, pv_by_ply=pv_by_ply)
    pv_lines_by_ply = await _run_multipv2_pass(flaw_records_preview, pv_by_ply, positions)

    # Step 4: write session (unchanged except pv_lines_by_ply threaded through)
    async with async_session_maker() as write_session:
        ...
        flaw_result = classify_game_flaws(
            game, positions, pv_by_ply=pv_by_ply, pv_lines_by_ply=pv_lines_by_ply
        )
        # write flaws with tactic cols + JSONB blobs
```

The helper `_run_multipv2_pass` is extracted to keep nesting depth <= 3 (CLAUDE.md):

```python
async def _run_multipv2_pass(
    flaw_records: GameFlawsResult,
    pv_by_ply: dict[int, str],
    positions: list[GamePosition],
) -> dict[int, list[PvNode]]:
    """Run MultiPV=2 on each node of each flaw's PV line.
    Returns {ply -> list[PvNode]} for both allowed (ply=flaw+1) and missed (ply=flaw).
    No session open -- pure engine calls."""
    if not isinstance(flaw_records, list) or not flaw_records:
        return {}
    tasks = _build_multipv2_tasks(flaw_records, pv_by_ply, positions)
    results = await asyncio.gather(
        *(engine_service.evaluate_nodes_multipv2(t.board) for t in tasks)
    )
    return _assemble_pv_lines(tasks, results)
```

### Pattern 3: Solver-Only Gate, Every-Node Storage

**What:** The forcing-line gate checks ONLY solver nodes (even-indexed positions in the PV, where pov is the refuting side). Defender nodes have no uniqueness check. BUT the JSONB storage captures every node (both solver and defender).

**When to use:** During the v1.30 experiment. Storing every node costs ~2x vs solver-only but preserves all data for potential future defender-side rules without a re-backfill. After the experiment confirms no defender rules are needed, optimize to solver-only in a follow-up.

**JSONB schema (per node in the array, keys abbreviated for compactness):**
```json
{"b": 320, "bm": null, "s": -15, "sm": null, "su": "e4e5"}
```
- `b` / `bm`: best-move eval (cp / mate), white-perspective (matches existing `eval_cp` convention)
- `s` / `sm`: second-best-move eval (cp / mate)
- `su`: second-best-move UCI string (future-proofs "is the alternative also a capture?" rules)

### Pattern 4: JSONB on game_flaws, Not a Sidecar Table

**What:** Two nullable JSONB columns (`allowed_pv_lines`, `missed_pv_lines`) on the existing `game_flaws` table, not a separate `game_flaw_pv_lines` sidecar with a FK.

**Why JSONB, not parallel Text columns:** The data is variable-length, per-node structured, read only by Python (never filtered in SQL), and expected to grow new fields without migration. JSONB's no-migration-for-new-field property is the design note's explicit goal: adding a `"cap"` or defender-flag field to existing blobs requires no schema change.

**Why inline on game_flaws, not a sidecar:** `game_flaws` is NOT a huge table; it holds M+B flaws only (both movers), unlike `game_positions` (all plies, all games). Postgres TOASTs large JSONB out-of-line automatically, so the main row stays narrow for stats scans that do not SELECT the JSONB columns. A sidecar adds a JOIN on every re-tagger query with no benefit at this table size.

**Fallback condition:** If `game_flaws` JSONB column width causes measurable stat-scan regression (confirm via `EXPLAIN ANALYZE` on the `ix_game_flaws_user_severity` index scan), move to the sidecar. That is a documented follow-up, not a day-1 decision.

### Pattern 5: Extend SubmitRequest Additively, Not via a New Endpoint

**What:** Extend `SubmitRequest` with an optional `flaw_pv_lines: list[FlawPvLinesSubmit] = []` field. Old workers that do not include this field submit `[]` — the server treats that as "no JSONB data" and writes NULL. New workers include the blobs.

**Why not a new endpoint (`/api/eval/remote/pv-submit`):** The JSONB data is per-game and is the direct result of the MultiPV=2 pass for the same game's evaluation. Bundling it with the existing submit keeps the lease/submit contract atomic per game and avoids a second HTTP round-trip.

```python
# eval_remote.py (modified -- additive, no break)
class FlawPvLinesSubmit(BaseModel):
    flaw_ply: int            # ply index of the flaw (allowed = flaw_ply+1 PV)
    allowed_pv_lines: list[dict[str, int | str | None]] | None = None
    missed_pv_lines: list[dict[str, int | str | None]] | None = None

class SubmitRequest(BaseModel):
    game_id: int
    sf_version: str
    evals: list[SubmitEval] = Field(max_length=MAX_SUBMIT_EVALS)
    job_id: int | None = None
    flaw_pv_lines: list[FlawPvLinesSubmit] = []  # NEW -- default empty preserves compat
```

## Data Flow

### New Data Flow -- Full-Game Drain with MultiPV=2

```
Claim game (tiered SKIP-LOCKED queue)
    |
    v
Load PGN + game_positions rows  [short read session, close]
    |
    v
Step 3: asyncio.gather(evaluate_nodes_with_pv per ply)  [no session]
    |  => pv_by_ply: {ply -> pv_string}
    |  => eval_results: {ply -> (eval_cp, eval_mate, best_move)}
    |
    v
Step 3b: NEW -- MultiPV=2 pass  [no session]
    |
    +- classify_game_flaws(game, positions, pv_by_ply)  [pure; preview only]
    |      => flaw_plies: set[int]
    |
    +- Parse PV strings => board states at each PV node per flaw
    |
    +- asyncio.gather(evaluate_nodes_multipv2 per flaw-PV-node)
    |      => PvNode results per node
    |
    +- _assemble_pv_lines() => pv_lines_by_ply: dict[int, list[PvNode]]
    |      allowed: {flaw_ply+1 -> [PvNode, ...]}
    |      missed:  {flaw_ply   -> [PvNode, ...]}
    |
    v
Step 4: Write session [open LATE]
    |
    +- UPDATE game_positions SET eval_cp, eval_mate, best_move, pv
    |
    +- classify_game_flaws(game, positions, pv_by_ply, pv_lines_by_ply)
    |      => FlawRecord list with gate-applied tactic tags
    |
    +- INSERT/UPSERT game_flaws
    |      (existing tactic columns + allowed_pv_lines JSONB + missed_pv_lines JSONB)
    |
    +- stamp full_evals_completed_at, mark job complete
```

### Offline Re-tagger Data Flow

```
scripts/retag_flaws.py  [--user-id N  --dry-run  --margin 0.35]
    |
    +- SELECT game_flaws WHERE allowed_pv_lines IS NOT NULL
    |         [batched, BACKFILL_GAMES_PER_BATCH pattern]
    |
    |  Per flaw row:
    +- Load allowed_pv_lines JSON => list[PvNode]
    +- Load missed_pv_lines JSON  => list[PvNode]
    |
    +- Reconstruct board_after_flaw from fen column + move_san
    |
    +- allowed pass:
    |     apply_forcing_line_filter(allowed_pv_lines, prev_eval_cp, prev_eval_mate)
    |     if passes => detect_tactic_motif(board_after_flaw, pv_allowed)
    |     => (new_motif, new_piece, new_confidence, new_depth)
    |
    +- missed pass:
    |     apply_forcing_line_filter(missed_pv_lines, ...)
    |     if passes => detect_tactic_motif(board_before, pv_missed)
    |     => (new_motif, new_piece, new_confidence, new_depth)
    |
    +- UPDATE game_flaws SET
           allowed_tactic_motif = new_motif,
           allowed_tactic_piece = new_piece, ...
           missed_tactic_motif = ..., ...
       [batch commit; --dry-run prints diff without writing]
```

### A/B Experiment Data Flow (user-28, dev)

```
Dev DB (user-28 only):

1. Run backfill_multipv.py --user-id 28
      => fills allowed_pv_lines / missed_pv_lines for all user-28 game_flaws

2. Snapshot old tactic columns (un-gated tags):
      old_tags_28 = SELECT ply, allowed_tactic_motif, missed_tactic_motif
                    FROM game_flaws WHERE user_id = 28

3. Run retag_flaws.py --user-id 28 --dry-run --margin 0.35
      => new_tags_28 = in-memory diff (motif, depth before/after per flaw)

4. Diff old_tags_28 vs new_tags_28:
      - Tags removed per motif (noise reduction)
      - Tags shifted shallower (depth distribution)
      - False negatives: good tags killed (hand-review ~30)

5. Adjust margin (0.35 +/- tweak) => repeat steps 3-4 (engine-free, seconds to run)

Prod DB (user-28): read-only sanity baseline ONLY.
    Eval non-determinism isolation: BOTH old and new detector runs use dev-computed
    JSONB blobs (same engine run). Prod-28 is never compared directly against dev evals.
```

## engine.py Integration Points

### New Function: evaluate_nodes_multipv2

Extends `_analyse_with_pv` with a `multipv=2` parameter. python-chess `protocol.analyse(board, limit, multipv=2)` returns `list[InfoDict]` -- one dict per PV. New constants:

```python
_NODES_BUDGET_MULTIPV2: int = _NODES_BUDGET      # 1M nodes, same budget; tune post-v1.30
_NODES_TIMEOUT_MULTIPV2_S: float = _NODES_TIMEOUT_S  # 5.0s
```

`EnginePool.evaluate_nodes_multipv2` acquires a worker via the same `_available` queue (same fairness / restart-on-failure discipline as `_analyse_with_pv`), calls `protocol.analyse(board, Limit(nodes=_NODES_BUDGET_MULTIPV2), multipv=2)`, extracts `PvNode` from `infos[0]` (best) and `infos[1]` (second, if present).

Failure semantics: returns `None` on timeout / crash / single-PV-only result (only one legal move). The caller stores `None` nodes as `{"b": null, "bm": null, "s": null, "sm": null, "su": null}` in the JSONB blob, preserving node-count in the array. A `None` node always fails `is_solver_node_forced` (treated as non-forced).

## Eval Non-Determinism Isolation

The A/B experiment is designed specifically to avoid the documented `eval_cp` non-determinism (project memory `project_eval_nondeterminism`):

- `eval_cp` differs between dev and prod even on identical games (wall-clock timeout, TT persistence across positions in the same pool worker).
- Raw dev-vs-prod tag diff would conflate gate effect with eval drift.
- Clean isolation: run `backfill_multipv.py` in dev ONCE. Then run BOTH old `detect_tactic_motif` and new gated `retag_flaws.py` on the SAME stored JSONB (same engine run). The diff is purely algorithmic.
- Prod-28 is NOT used for algorithmic comparison; it is only a "current user experience" sanity check.

## Dependency-Ordered Build Sequence

Phases 141-145 map directly to the seed design note's proposed order: storage => MultiPV pass => re-tagger => validation => backfill+ship.

### Phase 141: JSONB Schema

Everything else depends on this. No engine changes. No scripts.

Files changed:
- `app/models/game_flaw.py` -- add `allowed_pv_lines: Mapped[dict | None]` and `missed_pv_lines: Mapped[dict | None]` as `MappedColumn(JSONB, nullable=True)`.
- `app/repositories/game_flaws_repository.py` -- include JSONB columns in the upsert dict (read from `FlawRecord`; write NULL when not provided). The `flaw.get(...)` pattern already handles optional keys.
- New Alembic migration: `ADD COLUMN allowed_pv_lines JSONB DEFAULT NULL, ADD COLUMN missed_pv_lines JSONB DEFAULT NULL` on `game_flaws`.
- `app/services/forcing_line_gate.py` (NEW) -- `PvNode` TypedDict, `LICHESS_FORCING_MARGIN = 0.35`, `is_solver_node_forced()`, `apply_forcing_line_filter()`. Already-winning reject (`prev_score > ALREADY_WINNING_CP`), still-winning floor (`best_score < STILL_WINNING_FLOOR_CP` stops extension), length rules (reject one-movers). Pure math, unit-testable in isolation.

Verification: migration runs cleanly on dev DB; existing tests still pass (NULL JSONB is neutral).

### Phase 142: MultiPV=2 Pass -- Engine + Eval Drain + Remote Worker

Depends on Phase 141 (FlawRecord can carry JSONB; repository can write it).

Files changed:
- `app/services/engine.py` -- add `_analyse_multipv2()`, `EnginePool.evaluate_nodes_multipv2()`, module-level `evaluate_nodes_multipv2()`. Constants `_NODES_BUDGET_MULTIPV2` and `_NODES_TIMEOUT_MULTIPV2_S`.
- `app/services/eval_drain.py` -- add `_build_multipv2_tasks()`, `_assemble_pv_lines()`, `_run_multipv2_pass()` helpers. Modify `_full_drain_tick` to call `_run_multipv2_pass` as step 3b. Thread `pv_lines_by_ply` into `classify_game_flaws` and the write flow.
- `app/services/flaws_service.py` -- extend `FlawRecord` TypedDict with optional `allowed_pv_lines` / `missed_pv_lines` keys. Extend `classify_game_flaws` and `_build_flaw_record` signatures to accept `pv_lines_by_ply: dict[int, list[PvNode]] | None = None`. Extend `_detect_tactic_for_flaw` with gate pre-filter.
- `app/schemas/eval_remote.py` -- add `FlawPvLinesSubmit`, extend `SubmitRequest` with `flaw_pv_lines: list[FlawPvLinesSubmit] = []`.
- `scripts/remote_worker.py` -- add MultiPV=2 pass between full-game eval and submit; include `flaw_pv_lines` in `SubmitRequest`.

Verification: for a test game in dev, confirm `game_flaws` rows show non-NULL JSONB after a full-drain tick. Confirm remote worker submit produces non-NULL JSONB. Confirm existing tactic tag counts are unchanged (gate not active in live drain until pv_lines_by_ply is plumbed through; JSONB is stored, gate applied by re-tagger).

### Phase 143: Offline Re-tagger

Depends on Phase 142 (JSONB must be populated to re-tag).

Files changed:
- `scripts/retag_flaws.py` (NEW) -- reads `game_flaws WHERE allowed_pv_lines IS NOT NULL`, applies gate, updates tactic columns. Flags: `--user-id`, `--dry-run`, `--margin` (default from `forcing_line_gate.LICHESS_FORCING_MARGIN`), `--db dev|benchmark|prod`. Same batch-commit discipline as `backfill_flaws.py`.
- `scripts/backfill_multipv.py` (NEW) -- reads `game_flaws WHERE allowed_pv_lines IS NULL` for analyzed games; reconstructs flaw-PV-node board states from the stored `game_positions.pv` column (no PGN replay needed -- PV string gives exact board states); runs MultiPV=2; writes blobs. Same `--db`, `--user-id`, `--dry-run` flags.

Note: `backfill_multipv.py` uses the stored PV string in `game_positions.pv` (already persisted from the full-eval drain) to reconstruct board states. This is simpler than `backfill_flaws.py` (no full PGN replay).

Verification: run `retag_flaws.py --user-id 28 --dry-run` on dev. Confirm diff output shows motif changes only for the expected noisy motifs (clearance, sacrifice, capturing-defender at depth > 2).

### Phase 144: A/B Validation (user-28)

Depends on Phase 143 (backfill_multipv + retag_flaws available). No new files.

Validation is operational:
1. `uv run python scripts/backfill_multipv.py --db dev --user-id 28` -- fills JSONB (~minutes)
2. Snapshot old tags: `SELECT ply, allowed_tactic_motif, missed_tactic_motif FROM game_flaws WHERE user_id = 28`
3. `uv run python scripts/retag_flaws.py --db dev --user-id 28 --dry-run` -- dry-run diff
4. Inspect per-motif stats: tags removed, depth distribution shift
5. Hand-review ~30 dropped tags to confirm they are the noisy/disconnected class
6. Count false negatives: good tags killed (expected to be few for clearance/sacrifice/capturing-defender)
7. Adjust `--margin` if needed; re-run dry-run (engine-free, seconds)
8. Commit confirmed margin to `LICHESS_FORCING_MARGIN` constant in `forcing_line_gate.py`

Prod-28 sanity: compare current prod-28 chip mix against the dev post-gate distribution for directional sanity only. Do NOT treat as a metric because the eval sources differ.

### Phase 145: Corpus Backfill + Rollout

Depends on Phase 144 (margin confirmed).

1. Run `backfill_multipv.py --db prod` (fills JSONB for all analyzed `game_flaws` in prod)
2. Run `retag_flaws.py --db prod` (applies gate to all rows with JSONB data)
3. Monitor tactic chip counts per motif before/after; confirm expected reduction in noisy motifs
4. Ship: the live drain now writes JSONB for all new games; `retag_flaws.py` can be re-run on-demand whenever gate parameters change (no engine re-pass needed)

## Scaling Considerations

| Concern | Current | With v1.30 MultiPV=2 |
|---------|---------|----------------------|
| Per-game engine cost (full drain) | N x 1M node calls (N = ply count) | + M x 6-12 extra 1M-node calls (M = flaw count, ~3 avg) |
| JSONB storage per flaw row | -- | ~500 bytes per flaw (6-12 nodes x ~40 bytes/node) |
| Re-tagger speed | -- | ~0.5ms per flaw (pure Python, no engine) |
| Backfill scope | All analyzed games | All game_flaws rows where JSONB IS NULL |
| Remote worker submit body | ~1KB per game | +~1.5KB per flaw (flaw_pv_lines) |

MultiPV=2 overhead is bounded: it runs only on flaw positions (M+B, ~3-5 per game average), not all plies. The full-drain tick is already dominated by the N x 1M-node all-ply pass; the flaw-PV MultiPV=2 pass adds roughly 15-25% to per-game engine time.

## Anti-Patterns

### Anti-Pattern 1: Running MultiPV=2 Inside an AsyncSession

**What people do:** Open the write session first, then gather MultiPV=2 engine calls inside that session.

**Why it's wrong:** CLAUDE.md hard rule: `AsyncSession` is not safe for concurrent use from multiple coroutines. `asyncio.gather` spans cannot run inside an open AsyncSession scope.

**Do this instead:** The MultiPV=2 gather (step 3b) must run with NO session open. Only after all engine results are collected does the write session open (step 4). `_full_drain_tick` already follows this pattern for the MultiPV=1 gather; step 3b mirrors it exactly.

### Anti-Pattern 2: Modifying detect_tactic_motif

**What people do:** Add the forcing-line gate logic inside `tactic_detector.py::detect_tactic_motif` itself.

**Why it's wrong:** `tactic_detector.py` has 29 motifs, 130+ fixture rows, and a precision gate at >= 0.95 on a held-out CC0 TEST split. Changing the dispatcher risks breaking precision across all motifs. The fixture report cannot see the forcing-line bug (no non-forced tail in fixtures) but CAN see regressions from gate logic inserted in the wrong place.

**Do this instead:** Gate as pre-filter in `_detect_tactic_for_flaw` (caller layer). `detect_tactic_motif` stays byte-for-byte unchanged. Gate logic lives in the new `forcing_line_gate.py` (pure math, independently testable).

### Anti-Pattern 3: Re-running the Engine Per Threshold Change

**What people do:** Re-run `backfill_multipv.py` every time the margin (0.35) is adjusted.

**Why it's wrong:** The MultiPV=2 engine pass is expensive (~15-25% overhead per game, across the whole prod corpus on backfill). The whole point of persisting JSONB is to decouple the expensive engine pass from the cheap gate re-derivation.

**Do this instead:** `retag_flaws.py` reads already-stored JSONB blobs and applies the gate in pure Python. A margin change from 0.35 to 0.30 is a `--margin 0.30` flag -- the script re-tags in seconds, no engine involved.

### Anti-Pattern 4: Sidecar Table for JSONB Data

**What people do:** Create a `game_flaw_pv_lines (user_id, game_id, ply, allowed_pv_lines JSONB, missed_pv_lines JSONB)` sidecar table with a composite FK to `game_flaws`.

**Why it's wrong:** Adds a JOIN on every re-tagger query. `game_flaws` is not a high-cardinality table -- it holds M+B flaws only. JSONB on the main table, TOASTed by Postgres for large values, provides the same physical decoupling without the join cost or FK maintenance.

**Do this instead:** Inline JSONB columns on `game_flaws`. If TOAST behavior or stat-scan regression becomes measurable (confirm via `EXPLAIN ANALYZE` on `ix_game_flaws_user_severity`), revisit the sidecar in a follow-up.

## Integration Points

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| `engine.py` <-> `eval_drain.py` | `evaluate_nodes_multipv2(board)` => `PvNode | None` | Same pool-acquisition / restart-on-failure discipline as `evaluate_nodes_with_pv` |
| `forcing_line_gate.py` <-> `flaws_service.py` | `apply_forcing_line_filter(pv_lines, prev_cp, prev_mate) -> bool` | Pure function; no imports from flaws_service; independently testable |
| `eval_drain.py` <-> `flaws_service.py` | `classify_game_flaws(game, positions, pv_by_ply, pv_lines_by_ply)` | `pv_lines_by_ply` is the new optional param; absent in backfill path (backward compat) |
| `flaws_service.py` <-> `tactic_detector.py` | `detect_tactic_motif(board, pv, has_forced_mate)` UNCHANGED | Gate is in flaws_service, never inside tactic_detector |
| `eval_remote.py` <-> `remote_worker.py` | `SubmitRequest.flaw_pv_lines: list[FlawPvLinesSubmit]` | Additive field; old workers submit `[]`, new workers include blobs |
| `game_flaws_repository.py` <-> `eval_drain.py` | `write_flaws(session, game_id, flaw_records)` -- `FlawRecord` gains optional JSONB keys | Null-safe: repository writes NULL when JSONB keys absent |
| `backfill_multipv.py` <-> `engine.py` | Direct `EnginePool` use (same pattern as `backfill_eval.py`) | Off-box; separate pool, no interference with lifespan pool |
| `retag_flaws.py` <-> `forcing_line_gate.py` + `tactic_detector.py` | Import both; no engine | Pure re-derivation; no HTTP, no sessions except DB reads/writes |

### Existing Touchpoints Confirmed Unchanged

| Component | Why Unchanged |
|-----------|---------------|
| `tactic_detector.py::detect_tactic_motif` | Gate is a pre-filter in the caller; dispatcher logic, fixture precision gate, 29 motif detectors all untouched |
| `game_positions` table | MultiPV=2 data lands on `game_flaws` (flaw-level), not on `game_positions` (position-level). No new columns on the large table. |
| `apply_game_filters()` in `query_utils.py` | Tactic filtering criteria (motif, orientation) unchanged; JSONB is never filtered in SQL |
| `eval_queue_service.py` | Queue claim/lease/complete contract unchanged; MultiPV=2 is a post-claim computation within the existing drain |
| `classify_game_flaws` existing callers | The new `pv_lines_by_ply` parameter defaults to `None`; all existing call sites (`backfill_flaws.py`, `reclassify_positions.py`, `eval_drain` lichess-eval path) pass nothing and see no behavior change |

## Sources

- First-party source reading: `app/services/engine.py`, `app/services/tactic_detector.py`, `app/models/game_flaw.py`, `app/services/eval_utils.py`, `app/services/flaws_service.py`, `app/services/eval_drain.py` (partial), `app/schemas/eval_remote.py`, `app/repositories/game_flaws_repository.py`, `scripts/backfill_flaws.py` (header), `.planning/PROJECT.md`, `.planning/notes/tactic-forcing-line-gate.md`
- AGPL boundary: lichess-puzzler heuristics and constants (0.00368208, 0.7 margin, 300cp/200cp floors) are facts/ideas, not copyrightable. Reference clone at `/home/aimfeld/Projects/Python/lichess-puzzler`. No source copied.

---
*Architecture research for: v1.30 Forcing-Line Tactic Gate (FlawChess)*
*Researched: 2026-06-29*
