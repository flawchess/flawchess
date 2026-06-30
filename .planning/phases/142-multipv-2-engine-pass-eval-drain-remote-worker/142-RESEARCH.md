# Phase 142: MultiPV=2 Engine Pass + Eval Drain + Remote Worker — Research

**Researched:** 2026-06-29
**Domain:** python-chess multipv=2 engine integration, eval drain extension, remote worker contract, margin histogram validation
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**D-01:** Extend the existing whole-game per-ply PV pass to `multipv=2` — do NOT add a separate flaw-only second engine pass. The existing `evaluate_nodes_with_pv` (eval_drain Step 3) already runs a 1M-node PV search on every ply, parallelized and remote-worker-able. MultiPV=2 is "the increment" on that same search (a second PV line at the same node budget, not new positions). Remote workers return second-best per ply; the server's `_run_multipv2_pass()` is an **assembly + write** step that builds the flaw-line blob arrays from the per-ply second-best data already in `engine_result_map`, then writes the JSONB. Rationale: reconciles SC3 (schema extension is load-bearing, not vestigial), reuses the remote fleet, marginal engine cost.

**D-02:** A new `_analyse_multipv2()` method on `EnginePool` is required — `_analyse_with_pv` returns `InfoDict | None` and cannot be reused for the `list[InfoDict]` multi-line return (per MPV-01). Guard for single-legal-move positions (no second line → `su=""`, `s/sm=null`).

**D-03:** Inline optional fields on `SubmitEval` — add `second_cp: int | None = None`, `second_mate: int | None = None`, `second_uci: str | None = None` directly to the existing per-ply `SubmitEval` row (NOT a parallel `multipv2_evals` list on `SubmitRequest`). Co-located with the ply they belong to, simplest, naturally backward-compatible: un-upgraded workers omit the fields → they default to `None` and the submit handler treats them as "no second-best".

**D-04:** Old-worker gap → leave NULL, Phase 145 backfills. When an un-upgraded worker analyzes a whole game it sends no second-best for any ply, so that game's flaw blobs stay NULL; the planned `backfill_multipv.py` (Phase 145, `WHERE allowed_pv_lines IS NULL`) fills the tail. New games on upgraded workers get blobs immediately. MPV-02's "every newly analyzed game" is therefore best-effort-for-upgraded-workers in 142, with the corpus guarantee landing in 145.

**D-05:** Eval gap → local SEED-056-style recovery. Flaw nodes whose eval came from the opening dedup cache (Step 2c, ply ≤ DEDUP_MAX_PLY) or from a lichess `%eval` game have no engine second-best even on an upgraded worker. For just those flaw nodes, recompute multipv **locally**, mirroring the existing `_fill_engine_game_flaw_pvs` PV-recovery pattern (SEED-056). This is a few nodes per game (cheap), distinct from the worker-version gap (all nodes → too many → defer to 145).

**D-06:** Keep the existing 1M node budget + 5s timeout (`_NODES_BUDGET`, `_NODES_TIMEOUT_S`) as the starting value for the multipv=2 search. Run the histogram; only raise to 1.5–2M if the SC4 test fails (>10% of positions within ±0.05 of the margin). Don't pre-pay cost.

**D-07:** Committed `scripts/` + `reports/` validation tool (benchmarks / db-report style), re-runnable on ≥200 dev flaw positions, gating the merge. Must be repeatable because Phases 144 (A/B) and 145 (rollout) re-tune the margin offline against the same stored evals. NOT a one-off pasted into VERIFICATION.md.

### Claude's Discretion

Exact `_analyse_multipv2()` / `_run_multipv2_pass()` signatures and helper names, the precise `scripts/`/`reports/` filenames and CLI flags for the histogram tool, the transaction boundary for the blob write (recommend same txn as the oracle-count UPDATE in Step 4b for atomicity), and the multipv search timeout tuning — planner/executor decide within the decisions above.

### Deferred Ideas (OUT OF SCOPE)

- Solver-only blob storage (halve MultiPV cost) — explicit later optimization; Phase 141 D-03 locked every-node storage for now.
- Server-local MultiPV fallback for old-worker games — rejected for 142 (D-04); the gap is filled by the Phase 145 backfill instead.
- Offline re-tagger CLI + mate-hierarchy / defender-branch tests + idempotency — Phase 143.
- User-28 A/B validation + final `ONLY_MOVE_WIN_PROB_MARGIN` commit — Phase 144.
- `backfill_multipv.py --db prod` + corpus rollout + per-motif chip-count monitoring — Phase 145.
- Raising `STOCKFISH_POOL_SIZE` to 8 — gated separately on a 24h soak (CLAUDE.md).
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| MPV-01 | `EnginePool` computes MultiPV=2 per flaw-line node (best + second eval cp/mate + second-best UCI) via a dedicated `_analyse_multipv2` method (the `list[InfoDict]` return type forbids reusing `_analyse_with_pv`), persisting the result into the JSONB columns on every new analysis. | New method modeled on existing `_analyse_with_pv` (engine.py:486); `protocol.analyse(board, limit, multipv=2)` returns `list[InfoDict]`; guarded for single-legal-move positions. |
| MPV-02 | The MultiPV pass is wired into the eval drain and the remote-worker lease/submit contract additively (backward-compatible with un-upgraded workers), reusing the module-level `EnginePool` within the 4g container RSS budget. | Inline optional fields on `SubmitEval` (D-03); `_run_multipv2_pass()` after `_classify_and_fill_oracle` in the write session; module-level pool reuse per QUEUE-07 accounting. |
| MPV-03 | The node budget for trustworthy best-vs-second ordering is validated via a margin histogram on ≥200 dev flaw positions before lock-in (raise budget if >10% of positions fall within ±0.05 of the margin). | `scripts/` + `reports/` histogram tool modeled on `tactic_tagger_report.py`; run against dev DB; histogram gates merge decision. |
</phase_requirements>

---

## Summary

Phase 142 wires the MultiPV=2 engine pass into the existing eval drain, remote-worker contract, and JSONB storage layer. It is a pure engine + persistence phase: the gate logic from Phase 141 is left untouched. The primary output is that every new game analyzed by an upgraded worker produces non-NULL `allowed_pv_lines` / `missed_pv_lines` JSONB on its `game_flaws` rows; a margin histogram on the dev corpus gates the merge decision.

The architecture extends three existing paths: (1) `EnginePool` gains a new `_analyse_multipv2` method returning `list[InfoDict]` (D-02); (2) the eval drain's `_full_drain_tick` gains a new step that assembles JSONB blobs from the per-ply second-best data already collected during the whole-game gather and writes them after `_classify_and_fill_oracle`; (3) `SubmitEval` gains inline optional `second_cp / second_mate / second_uci` fields that un-upgraded workers simply omit (D-03).

The most important open design question (see Open Questions below) is how the multi-node PV blob is assembled: D-01 says `_run_multipv2_pass` is an "assembly + write" step using data already in `engine_result_map` (game plies), while the blob schema requires second-best at each node of a 6–12-ply PV line. Node 0 (flaw_ply / flaw_ply+1) has second-best from engine_result_map; deeper nodes are hypothetical positions. The planner must resolve whether the worker walks the PV to evaluate deep nodes, or whether the blob is intentionally 1-node-per-flaw.

**Primary recommendation:** Let the planner decide the PV-depth approach after reading D-01 vs the blob multi-node requirement; implement the `_analyse_multipv2` method and `SubmitEval` extension first (clear from decisions), then address the assembly design explicitly in the PLAN.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| MultiPV=2 engine call | Backend service (`engine.py`) | Remote worker | New `_analyse_multipv2` runs on server pool or remote worker pool |
| Second-best data transport | Remote worker schema (`eval_remote.py`) | — | D-03: inline per-ply fields on `SubmitEval`; backward-compatible |
| JSONB blob assembly | Backend service (`eval_drain.py`) | — | Server assembles blobs from in-memory engine_result_map after classify |
| JSONB persistence | Repository (`game_flaws_repository.py`) | — | Batched UPDATE mirrors `_batch_update_pv_rows` pattern |
| Margin histogram validation | Script (`scripts/validate_multipv_budget.py`) | — | Committed re-runnable tool; not a one-off test |
| D-05 eval-gap recovery | Backend service (`eval_drain.py`) | — | Local targeted multipv=2 for dedup/lichess flaw nodes |

---

## Standard Stack

No new PyPI dependency is required. All mechanics exist in installed versions.

### Core (verified from codebase source)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| python-chess | 1.11.x (installed) | `protocol.analyse(board, limit, multipv=2)` → `list[InfoDict]` | Existing multipv overload in the installed version |
| SQLAlchemy `JSONB` | 2.x (installed) | `allowed_pv_lines` / `missed_pv_lines` already added in Phase 141 | Already in `game_flaw.py` |
| asyncpg | installed | Async PostgreSQL driver, auto-registers JSONB codec | Already wired; no changes needed |
| Stockfish 18 | prod/dev (installed) | MultiPV=2 UCI option | Standard Stockfish UCI; no new binary needed |

### No New Packages

The Package Legitimacy Audit section is omitted: no external packages are installed in this phase.

---

## Architecture Patterns

### System Architecture Diagram

```
Eval Drain (_full_drain_tick)
    │
    ├─ Step 3: asyncio.gather(evaluate_nodes_multipv2 per game ply)  [no session]
    │       engine_result_map[ply] = (cp, mt, bm, pv, second_cp, second_mt, second_uci)
    │
    ├─ SEED-056 analog (D-05): targeted local multipv=2 for dedup/lichess flaw plies
    │       Mutates engine_result_map in place (same pattern as _fill_engine_game_flaw_pvs)
    │
    └─ Step 4 (write session):
            ├─ _apply_full_eval_results (existing)
            ├─ _classify_and_fill_oracle (existing, UNCHANGED in Phase 142)
            └─ _run_multipv2_pass (NEW) — assemble PvNode blobs + batched UPDATE
                    Reads engine_result_map for second-best data
                    Writes allowed_pv_lines / missed_pv_lines via _batch_update_flaw_pv_lines

Remote Worker (_handle_full_ply_response)
    │
    ├─ _eval_positions: asyncio.gather(pool.evaluate_nodes_multipv2 per game ply)
    │       Returns 7-tuple per ply including second_cp/second_mate/second_uci
    │
    └─ Submit: SubmitRequest with SubmitEval carrying inline second_cp/second_mate/second_uci
               (old workers omit these fields → None → server writes NULL blobs)

SubmitEval extension (D-03):
    ply, eval_cp, eval_mate, best_move, pv   [existing]
    second_cp: int | None = None             [NEW — default None for old workers]
    second_mate: int | None = None           [NEW]
    second_uci: str | None = None            [NEW]
```

### Pattern 1: _analyse_multipv2 — New EnginePool Method

**What:** Parallel sibling to `_analyse_with_pv` (engine.py:486) that passes `multipv=2` to `protocol.analyse` and returns `list[InfoDict] | None`.

**Why separate method:** `protocol.analyse(board, limit)` returns `InfoDict`; `protocol.analyse(board, limit, multipv=2)` returns `list[InfoDict]`. This is a typed overload in python-chess — the return types differ and cannot be unified. Passing the results to existing helpers like `_score_to_cp_mate(info)` would crash if given a list.

**Exact pattern (modeled on engine.py:486–519):** [VERIFIED: codebase]
```python
# app/services/engine.py (new method)
async def _analyse_multipv2(
    self,
    board: chess.Board,
    limit: chess.engine.Limit,
    timeout: float,
) -> list[chess.engine.InfoDict] | None:
    """Shared worker-acquisition path returning list[InfoDict] for multipv=2.

    Returns None on timeout/crash/no protocol.
    Caller must handle len(result) < 2 (only one legal move — single-legal-move guard D-02).
    """
    if not self._started:
        return None
    idx = await self._available.get()
    try:
        protocol = self._protocols[idx]
        if protocol is None:
            return None
        try:
            info_list = await asyncio.wait_for(
                protocol.analyse(board, limit, multipv=2),
                timeout=timeout,
            )
        except (
            asyncio.TimeoutError,
            chess.engine.EngineError,
            chess.engine.EngineTerminatedError,
        ):
            await self._restart_worker(idx)
            return None
        return info_list
    finally:
        self._available.put_nowait(idx)

async def evaluate_nodes_multipv2(
    self,
    board: chess.Board,
) -> tuple[int | None, int | None, str | None, str | None, int | None, int | None, str | None]:
    """Evaluate at 1M nodes with multipv=2. Returns (cp, mt, bm, pv, second_cp, second_mt, second_uci)."""
    info_list = await self._analyse_multipv2(
        board, chess.engine.Limit(nodes=_NODES_BUDGET), _NODES_TIMEOUT_S
    )
    if info_list is None:
        return None, None, None, None, None, None, None
    eval_cp, eval_mate = _score_to_cp_mate(info_list[0])
    best_move = _pv_to_best_move(info_list[0])
    pv_string = _pv_to_uci_string(info_list[0])
    if len(info_list) > 1:
        second_cp, second_mate = _score_to_cp_mate(info_list[1])
        second_pv = info_list[1].get("pv") or []
        second_uci: str | None = second_pv[0].uci() if second_pv else None
    else:
        second_cp = second_mate = second_uci = None
    return eval_cp, eval_mate, best_move, pv_string, second_cp, second_mate, second_uci
```

**Module-level wrapper** (mirrors `evaluate_nodes_with_pv` pattern at engine.py:521):
```python
async def evaluate_nodes_multipv2(
    board: chess.Board,
) -> tuple[int | None, int | None, str | None, str | None, int | None, int | None, str | None]:
    if _pool is None:
        return None, None, None, None, None, None, None
    return await _pool.evaluate_nodes_multipv2(board)
```

### Pattern 2: SubmitEval Extension (D-03)

**What:** Add three optional fields inline to the existing `SubmitEval` model. Old workers that omit these fields get `None` defaults and the server writes NULL blobs. [VERIFIED: codebase — existing `job_id: int | None = None` in `SubmitRequest` is the precedent for "old worker omits → None"]

```python
# app/schemas/eval_remote.py (existing SubmitEval at line 30–35, extended)
class SubmitEval(BaseModel):
    ply: int = Field(ge=0)
    eval_cp: int | None
    eval_mate: int | None
    best_move: str | None
    pv: str | None
    # Phase 142 MPV-02: second-best per ply for JSONB blob assembly.
    # Default None = old worker omit → server treats as no second-best.
    second_cp: int | None = None
    second_mate: int | None = None
    second_uci: str | None = None
```

**No change to `SubmitRequest`** beyond the inline `SubmitEval` fields (D-03 explicitly rejects a parallel `multipv2_evals` list).

### Pattern 3: _run_multipv2_pass — Assembly + Write

**What:** A new function called inside the write session after `_classify_and_fill_oracle`. It reads the already-computed second-best data from `engine_result_map` and assembles `PvNode` blobs, then performs a batched UPDATE on `game_flaws`. [ASSUMED for signature details; D-01 constrains the assembly approach]

**Session constraint:** The blob write is a DB UPDATE → must happen inside the write session. The engine result data is already in `engine_result_map` (computed in Step 3 before the session opens) so no engine calls occur inside the session. [VERIFIED: CLAUDE.md hard rule confirmed]

**Key shape:** `PvNode` TypedDict is defined in `app/services/forcing_line_gate.py`:
```python
class PvNode(TypedDict):
    b: int | None    # best_cp, white-perspective
    bm: int | None   # best_mate, white-perspective
    s: int | None    # second_cp, white-perspective
    sm: int | None   # second_mate, white-perspective
    su: str          # second-best UCI or "" (never None per D-02 sentinel)
```

**Write pattern** to follow: `_batch_update_pv_rows` at eval_drain.py:443 is the model. The JSONB write needs a similar batched single UPDATE via `sa.text()` using `VALUES` clause — one round-trip per game rather than one per flaw row. [VERIFIED: codebase, FLAWCHESS-6B comment]

### Pattern 4: D-05 Eval-Gap Recovery

**What:** For flaw-adjacent game plies that were filled from the opening dedup cache (ply ≤ `_DEDUP_MAX_PLY`) or from lichess `%eval`, no engine second-best exists in `engine_result_map`. These plies need a targeted local `evaluate_nodes_multipv2` call, identical to how `_fill_engine_game_flaw_pvs` (eval_drain.py:991) recovers PV strings for dedup-transplanted flaw plies. [VERIFIED: codebase, SEED-056 pattern]

**Key difference from SEED-056:** SEED-056 recovers PV strings for opening flaw plies. D-05 recovers second-best evals for those same plies. Same triggering condition (`has_opening_dedup` check), same asymmetry: no-op for lichess games (they pre-classify flaw plies up front via `_flaw_engine_plies`) vs engine games (dedup may have hit).

**Steps:**
1. After Step 3 gather completes, dry-run `classify_game_flaws` to find flaw plies
2. Check which flaw plies are in `dedup_map` (engine game) or are lichess eval plies
3. For those that have no `second_cp` in `engine_result_map`, call `evaluate_nodes_multipv2` locally
4. Merge second-best data back into engine_result_map (or a parallel second-best map)
5. Continue to Step 4 (write session)

**MUST run with no session open** (gathers inside AsyncSession violate CLAUDE.md hard rule). [VERIFIED: CLAUDE.md + _fill_engine_game_flaw_pvs pattern]

### Pattern 5: Histogram Tool Convention

**What:** A committed `scripts/validate_multipv_budget.py` that queries dev `game_flaws` rows with non-NULL `allowed_pv_lines` / `missed_pv_lines`, computes the win-prob margin (`p(best) − p(second)`) at each solver node, plots the distribution, and writes a timestamped markdown report to `reports/multipv-validation/`. [VERIFIED: codebase — `tactic_tagger_report.py` is the model]

**Convention observed in `scripts/tactic_tagger_report.py`:** [VERIFIED: codebase]
- `_REPORT_DIR = Path(__file__).resolve().parents[1] / "reports" / "<subdirectory>"`
- Reports named `<slug>-YYYY-MM-DD.md`
- `argparse` with `--db dev|benchmark|prod`, `--limit N`
- `--check-goals` mode for gate evaluation (exits 0 = pass, 1 = fail)
- No DB session inside the report writer itself (reads a pre-computed DataFrame, or uses a short read session then closes)

**Histogram tool responsibilities (MPV-03):**
1. Query ≥200 dev flaw positions with non-NULL `allowed_pv_lines` (or `missed_pv_lines`)
2. For each PvNode (each element of each blob), compute `p(best) − p(second)` using `eval_cp_to_expected_score` and `eval_mate_to_expected_score` from `eval_utils`
3. Plot histogram of margins (or print ASCII histogram to the markdown)
4. Count fraction within ±0.05 of 0.35 (the SC4 criterion)
5. Exit-code gate: >10% within ±0.05 → fail (raise budget to 1.5–2M before merge)
6. **ALSO include PV1 drift check:** compare eval_cp from `engine_result_map` (multipv=2) against stored `game_positions.eval_cp` (multipv=1 from before Phase 142 was deployed) on the same positions; flag systematic delta > 10cp

### Anti-Patterns to Avoid

- **Running `asyncio.gather` inside an open AsyncSession:** The multipv=2 engine calls and the D-05 eval-gap recovery must complete before the write session opens. [VERIFIED: CLAUDE.md hard rule]
- **Modifying `_analyse_with_pv` in-place to add multipv:** Changes return type from `InfoDict | None` to `list[InfoDict] | None`, breaking all existing callers. Use a new method. [VERIFIED: Pitfall 10 in PITFALLS.md]
- **Applying the forcing-line gate in Phase 142:** The gate (`apply_forcing_line_filter`) is NOT called in this phase. JSONB blobs are stored; gate application is Phase 143. Existing tactic tag counts must be unchanged after Phase 142. [VERIFIED: CONTEXT.md scope boundary]
- **Creating a second EnginePool for the D-05 recovery:** Reuse the module-level `_pool`. QUEUE-07 accounting: 6 workers = ~1,586 MB; 4g container headroom ~0.76 GB. A second pool would push RSS into OOM zone. [VERIFIED: codebase QUEUE-07 comment]
- **Reading `allowed_pv_lines` / `missed_pv_lines` in existing stats queries:** Both columns are `deferred=True` on the ORM model (Phase 141 D-02). This means any `select(GameFlaw)` ORM call that tries to access them without `.options(undefer(...))` will raise `MissingGreenlet`. All existing stats paths already exclude them. [VERIFIED: game_flaw.py:120–121]

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Extracting best/second eval from InfoDict | Custom score parsing | `_score_to_cp_mate(info)` + `_pv_to_best_move(info)` (engine.py) | These helpers already handle PovScore, mate extraction, white-perspective conversion |
| Batched JSONB UPDATE | Per-row UPDATE loop | Pattern from `_batch_update_pv_rows` (eval_drain.py:443) | One round-trip per game vs N round-trips; follows FLAWCHESS-6B |
| Win-prob margin computation | Inline sigmoid | `eval_cp_to_expected_score(cp, color)` from `eval_utils.py` | Consistent with gate; same `LICHESS_K = 0.00368208`; handles white-perspective flip |
| PvNode shape | New TypedDict | `PvNode` from `app/services/forcing_line_gate.py` (Phase 141) | Already committed with correct keys `b/bm/s/sm/su` and docstring |
| Solver color at flaw ply | Recompute from scratch | `board_after_flaw.turn` for allowed; `board_before.turn` for missed (same as `_detect_tactic_for_flaw`) | Parity logic already correct in existing code |

---

## PV1 Drift — RESEARCH FLAG

**Concern (from CONTEXT.md §Specific Ideas):** Switching the whole-game pass to `multipv=2` changes how Stockfish computes the primary line (PV1) at every ply. Stockfish with MultiPV=2 uses less aggressive pruning to preserve the second PV, which can cause PV1 eval to drift slightly vs MultiPV=1 at the same node budget. PV1 feeds `eval_cp`, flaw classification, and benchmarks.

**Magnitude estimate:** [ASSUMED] At 1M nodes with 1 thread, effective depth per line drops from roughly 22 (multipv=1) to roughly 19–21 (multipv=2). Typical eval delta is 5–15 cp on most positions. This is sub-threshold for the 15pp severity classification boundary in most cases.

**Systematic risk:** The project already tolerates eval non-determinism (memory `project_eval_nondeterminism`): eval_cp varies between machines, TT persistence, and wall-clock timeout variation. The accepted view is sub-percentile differences at the ±100cp classification boundary. A multipv=2 PV1 drift of 5–15 cp falls within the same category of acceptable non-determinism. [ASSUMED]

**Guard strategy for Phase 142:** The histogram tool (MPV-03 / D-07) must include a PV1 drift spot-check section:
1. Query 50–100 dev `game_positions` rows where `allowed_pv_lines IS NOT NULL` (populated by Phase 142)
2. Compare `game_flaws`-adjacent `game_positions.eval_cp` (the current value, computed with multipv=2 after Phase 142) against any stored baseline (e.g., from before the Phase 142 drain ran, or from a deliberately-held-back set)
3. If no pre-Phase-142 baseline is available, the indirect check is: run the full test suite and verify flaw counts on well-known test games (any game currently in `tests/services/test_flaws_service.py` or `tests/services/test_eval_drain.py`) are within expected range after the drain ticks with multipv=2

**Conclusion:** Small PV1 drift is acceptable (the project already tolerates it); a systematic shift that moves flaw classification boundaries is the concern. The test suite provides the practical safety net: if flaw counts diverge on existing test fixtures after switching to multipv=2, the drift is too large and the node budget must be tuned. [ASSUMED — the ±15cp threshold for 15pp severity boundary]

---

## Common Pitfalls

### Pitfall 1: multipv=2 returns a list — existing callers crash on a scalar assumption

**What goes wrong:** `_analyse_with_pv` passes the `InfoDict` result to `_score_to_cp_mate(info)` which calls `info.get("score")`. If the new method accidentally passes a `list[InfoDict]` to these helpers, they fail with `AttributeError: 'list' object has no attribute 'get'`. [VERIFIED: Pitfall 10 in PITFALLS.md]

**How to avoid:** The new `_analyse_multipv2` method must never feed its `list[InfoDict]` to any helper that expects a scalar `InfoDict`. Unit test with a mock that returns `[InfoDict, InfoDict]`; verify correct extraction of index 0 vs index 1.

### Pitfall 2: len(infos) == 1 — single-legal-move position

**What goes wrong:** Positions with only one legal move (e.g., king in check with one escape) return a list of length 1. `info_list[1]` → `IndexError`. The gate treats a missing second line as forced (no alternative), but the code must guard this explicitly.

**How to avoid:** Guard `len(info_list) > 1` before extracting second-best. When `len == 1`, set `second_cp = second_mate = None`, `second_uci = ""` (the `PvNode.su` sentinel is `""` not `None`). [VERIFIED: PvNode.su is `str`, not `str | None` — forcing_line_gate.py:86]

### Pitfall 3: PvNode.su is str (not str | None)

**What goes wrong:** `PvNode.su` is typed as `str` (empty string = no second move), not `str | None`. Writing `second_uci: str | None` and assigning `None` when no second move exists would fail ty type-checking and misrepresent the blob schema. [VERIFIED: forcing_line_gate.py:86 — `su: str`]

**How to avoid:** When no second move exists, write `su=""`. When second move is present, write `su=second_uci` (the UCI string from `info_list[1]["pv"][0].uci()`).

### Pitfall 4: deferred=True means SELECT won't load the blob without undefer()

**What goes wrong:** `allowed_pv_lines` and `missed_pv_lines` are `deferred=True` on the ORM model (Phase 141). Any `session.get(GameFlaw, pk)` or `select(GameFlaw).where(...)` will NOT load these columns. Accessing `flaw.allowed_pv_lines` in that session raises `MissingGreenlet` (asyncpg async implicit load violation). [VERIFIED: game_flaw.py:120–121, `deferred=True`]

**How to avoid:** The `_run_multipv2_pass` writes blobs via a raw `sa.text()` UPDATE (not via the ORM model), so it never reads the column back through the ORM. The histogram tool (Phase 142) reads blobs via an explicit `select(GameFlaw.allowed_pv_lines, ...).where(...)` with explicit column projection — never via `select(GameFlaw)`.

### Pitfall 5: The JSONB write must happen inside the write session, not after commit

**What goes wrong:** If `_run_multipv2_pass` opens its own session for the blob write (separate from the write session opened in Step 4), the flaw rows and JSONB blobs commit in different transactions. A crash between the two transactions leaves flaw rows with NULL blobs that look complete (no retry trigger). [ASSUMED]

**How to avoid:** The JSONB blob write runs inside the same Step 4 `async with async_session_maker() as write_session:` block, after `_classify_and_fill_oracle`. Same commit → atomic with flaw rows and oracle counts (mirrors T-117-11 principle). [VERIFIED: T-117-11 mentioned in eval_drain.py:2004 comments]

### Pitfall 6: White-perspective cp stored in the blob, side-to-move perspective at gate

**What goes wrong:** The `PvNode` blob stores ALL cp values as white-perspective (`b` and `s` are white-perspective centipawns). `eval_cp_to_expected_score(cp, "white")` always returns the white win probability. If the gate reads `b` and passes `"white"` as solver_color when the solver is actually black, the gate applies the wrong sign convention. [VERIFIED: game_flaw.py:110–116 blob shape comment]

**How to avoid:** When assembling blobs, store white-perspective cp as-is. When `_run_multipv2_pass` stores the blobs, it does NOT flip cp to side-to-move perspective — it stores raw white-perspective. The gate (`is_solver_node_forced`) receives `solver_color` as a parameter and handles the flip via `eval_cp_to_expected_score(b, solver_color)`. Confirmed from forcing_line_gate.py:187–188.

---

## Open Questions (RESOLVED)

1. **PV node depth in the JSONB blob vs D-01 "assembly step"** — **RESOLVED: Option B** (Plan 142-02 objective, "Design Resolution: who computes PV-continuation-node second-best").

   What we know: D-01 says `_run_multipv2_pass` is an "assembly + write" step building blobs from data "already in `engine_result_map`" (game ply second-best). The `PvNode` blob is typed as `list[PvNode]` (array, 1–12 elements). The gate requires ≥2 solver nodes; a 1-element blob always fails the one-mover discard rule (`len(solver_nodes) < 2 → False`).

   What's unclear: Do deeper PV nodes (positions 2–11 in a 12-ply PV line, which are hypothetical continuation positions NOT in engine_result_map) get second-best data, and if so, how?

   Options to resolve:
   - (A) Extend remote workers to walk the PV string and run `evaluate_nodes_multipv2` on each PV node position (up to PV_CAP_PLIES). Workers submit these via the `SubmitEval` schema extended with a PV-node indicator, or via a separate `flaw_pv_lines` field on `SubmitRequest`. The "no separate pass" in D-01 means no second HTTP round-trip, not no additional engine calls.
   - (B) `_run_multipv2_pass` (server-side) walks the PV string, derives board positions at each PV node, and runs `evaluate_nodes_multipv2` locally (mirroring D-05's local recovery, but for all PV nodes not just eval-gap nodes). This is more local engine cost but simpler worker contract.
   - (C) The blob intentionally has 1 node (only the root position, flaw_ply or flaw_ply+1), and the Phase 143 gate is designed to accept 1-node blobs as "trivially forced" or "no deep forcing check." Requires gate redesign in Phase 143.

   **Recommendation:** Option (A) aligns best with D-01's remote-worker framing; the ARCHITECTURE.md remote worker section also shows this. The planner should read D-01 carefully and decide between (A) and (B), then verify that the chosen approach produces ≥2-node blobs that pass the gate's solver-node count requirement.

   **RESOLVED → Option (B):** `_build_flaw_multipv2_blobs` / `_run_multipv2_pass` walk each flaw's PV line server-side and evaluate the hypothetical continuation positions with `evaluate_nodes_multipv2` locally (node 0 reuses worker- or Step-3-supplied second-best; nodes 1..N are always local). This yields ≥2-node blobs that pass the gate's solver-node count requirement while keeping the worker contract simple (D-03 inline fields only, no `flaw_pv_lines`). See Plan 142-02 objective rationale and Plan 142-03 Task 2 (remote path reuses the same helpers).

2. **How engine_result_map carries second-best data through the write session** — **RESOLVED: parallel `second_best_map`** (Plan 142-02 Task 1; Plan 142-03 Task 2 threads the same map on the remote path).

   What we know: The current `engine_result_map` type is `dict[int, tuple[int | None, int | None, str | None, str | None]]` (ply → (cp, mt, bm, pv)). After Phase 142, it needs to carry second-best per ply.

   What's unclear: Should the map be widened to a 7-tuple `(cp, mt, bm, pv, second_cp, second_mt, second_uci)`, or should a parallel `second_best_map: dict[int, tuple[int | None, int | None, str | None]]` be introduced to avoid touching the existing tuple signature?

   **Recommendation:** Prefer a parallel map to minimize the blast radius of changing an existing signature used in 10+ call sites. The parallel map is passed only to `_run_multipv2_pass` and is not threaded through `_apply_full_eval_results` or `_classify_and_fill_oracle`.

   **RESOLVED → parallel `second_best_map`:** Plan 142-02 Task 1 keeps `engine_result_map` as the existing 4-tuple (sliced `res[:4]`) and builds a parallel `second_best_map: dict[int, tuple[int|None,int|None,str|None]]` from `res[4:7]`, so no existing downstream signature changes. Plan 142-03 Task 2 builds the identical parallel map from `SubmitEval` fields on the remote path.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest + pytest-asyncio (installed, `uv run pytest -n auto`) |
| Config file | `pyproject.toml` (`[tool.pytest.ini_options]`) |
| Quick run command | `uv run pytest tests/services/test_engine_nodes.py tests/services/test_forcing_line_gate.py -x` |
| Full suite command | `uv run pytest -n auto -x` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| MPV-01 | `_analyse_multipv2` returns `list[InfoDict]` with correct best/second extraction | unit (mock protocol) | `uv run pytest tests/services/test_engine_nodes.py -x` | Wave 0 |
| MPV-01 | Single-legal-move guard: returns `su=""`, `s=null`, `sm=null` when `len(infos)==1` | unit (mock) | `uv run pytest tests/services/test_engine_nodes.py -x` | Wave 0 |
| MPV-01 | `evaluate_nodes_multipv2` returns 7-tuple `(None,)*7` when pool not started | unit | `uv run pytest tests/services/test_engine_nodes.py::TestEvaluateNodesMultipv2 -x` | Wave 0 |
| MPV-02 | `SubmitEval` accepts `second_cp/second_mate/second_uci` as optional; old payloads without them parse without error | unit | `uv run pytest tests/services/test_eval_remote.py -x` | Wave 0 |
| MPV-02 | Full-drain tick: `game_flaws` rows show non-NULL JSONB after one drain tick on a test game | integration (DB) | `uv run pytest tests/services/test_full_eval_drain.py -x` | Wave 0 |
| MPV-02 | Existing tactic tag counts unchanged after Phase 142 drain tick (gate not applied) | integration (DB) | `uv run pytest tests/services/test_full_eval_drain.py -x` | Wave 0 |
| MPV-03 | Margin histogram produces a report with ≥200 positions and computes fraction within ±0.05 | manual / script run | `uv run python scripts/validate_multipv_budget.py --db dev --check-goals` | Wave 0 (script) |

### Sampling Rate

- **Per task commit:** `uv run pytest tests/services/test_engine_nodes.py tests/services/test_forcing_line_gate.py -x`
- **Per wave merge:** `uv run pytest -n auto -x`
- **Phase gate:** Full suite green + `scripts/validate_multipv_budget.py --db dev --check-goals` exits 0 before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `tests/services/test_engine_nodes.py::TestEvaluateNodesMultipv2` — new test class covering `_analyse_multipv2` list return, single-legal-move guard, and module-level `evaluate_nodes_multipv2` wrapper
- [ ] `tests/services/test_eval_remote.py::test_submit_eval_accepts_second_best_fields` — verify Pydantic accepts new optional fields; verify old payload without them still parses
- [ ] `tests/services/test_full_eval_drain.py` — extend existing drain test to verify `allowed_pv_lines IS NOT NULL` after a tick (or add a new test)
- [ ] `scripts/validate_multipv_budget.py` — new histogram tool (MPV-03 / D-07 gate)

---

## Security Domain

**Assessment:** This phase adds no authentication, authorization, input validation, session management, cryptography, or user-facing endpoints. The `SubmitEval` schema extension adds three optional integer/string fields; Pydantic v2 validates them (int or None, string or None). No security domain items apply.

The remote-worker contract already uses `require_operator_token` (eval_remote.py:453). The new `second_cp / second_mate / second_uci` fields are processed as eval data on the same authenticated endpoint — no new attack surface.

---

## Environment Availability

Phase 142 has no external dependencies beyond what is already running:

| Dependency | Required By | Available | Notes |
|------------|------------|-----------|-------|
| Stockfish 18 | `_analyse_multipv2` | Required (existing) | Same binary; multipv=2 is a UCI option, no binary change |
| PostgreSQL 18 (dev Docker) | JSONB write verification | Required (existing) | `docker compose -f docker-compose.dev.yml -p flawchess-dev up -d` |
| Dev `game_flaws` rows with evals | MPV-03 histogram | Required | ≥200 rows with `full_evals_completed_at IS NOT NULL`; check before running Phase 142 |

---

## Code Examples

### Extracting second-best from multipv=2 InfoDict list

[VERIFIED: STACK.md + python-chess engine docs]
```python
# Source: app/services/engine.py patterns + python-chess 1.11.x multipv overload
info_list: list[chess.engine.InfoDict] = await protocol.analyse(board, limit, multipv=2)

# Best line (always present if engine returned anything)
best = info_list[0]
eval_cp, eval_mate = _score_to_cp_mate(best)       # existing helper
best_move = _pv_to_best_move(best)                  # existing helper
pv_string = _pv_to_uci_string(best)                 # existing helper

# Second-best line (guard for single-legal-move positions)
if len(info_list) > 1:
    second = info_list[1]
    second_white = second["score"].white()
    second_cp: int | None = second_white.score(mate_score=None)
    second_mate: int | None = second_white.mate()
    second_pv = second.get("pv") or []
    second_uci: str = second_pv[0].uci() if second_pv else ""
else:
    second_cp = second_mate = None
    second_uci = ""   # PvNode.su sentinel (str, not None)
```

### Building a PvNode dict for the JSONB blob

[VERIFIED: forcing_line_gate.py:63–86 (PvNode TypedDict), game_flaw.py:109–116 (blob shape comment)]
```python
# Source: forcing_line_gate.PvNode + game_flaw.py blob shape comment
from app.services.forcing_line_gate import PvNode

node: PvNode = PvNode(
    b=eval_cp,        # white-perspective best cp (or None if mate)
    bm=eval_mate,     # white-perspective mate (or None if cp)
    s=second_cp,      # white-perspective second cp (None if no second move)
    sm=second_mate,   # white-perspective second mate (None if cp or no second)
    su=second_uci,    # second-best UCI string, "" if no legal second move
)
```

### Existing _fill_engine_game_flaw_pvs signature (D-05 mirror pattern)

[VERIFIED: eval_drain.py:991–1028]
```python
# Source: app/services/eval_drain.py:991 — SEED-056 pattern to mirror for D-05
async def _fill_engine_game_flaw_pvs(
    game_id: int,
    targets: Sequence[_FullPlyEvalTarget],
    dedup_map: dict[int, tuple[int | None, int | None, str | None]],
    engine_result_map: dict[int, tuple[int | None, int | None, str | None, str | None]],
    is_lichess_eval_game: bool,
) -> None:
    # 1. no-op if no opening dedup hits and no lichess eval game
    # 2. classify game flaws (pure, no session)
    # 3. find pv-less flaw plies
    # 4. asyncio.gather(evaluate_nodes_with_pv per gap target)  ← NO session open
    # 5. merge results into engine_result_map (mutate in place)
```

### Existing _batch_update_pv_rows (JSONB write model)

[VERIFIED: eval_drain.py:443–479]
```python
# Source: app/services/eval_drain.py:443
# Model for the per-game batched UPDATE: one VALUES clause per flaw row.
# Adapt for JSONB: use CAST(:blob AS jsonb) syntax in the VALUES clause.
async def _batch_update_pv_rows(
    session: AsyncSession,
    game_id: int,
    pv_rows: list[tuple[int, str]],
) -> None: ...
```

---

## State of the Art

| Old Approach | Current Approach | Notes |
|--------------|------------------|-------|
| `evaluate_nodes_with_pv` (multipv=1, returns InfoDict) | `evaluate_nodes_multipv2` (multipv=2, returns list[InfoDict]) | Phase 142 adds the new method alongside; existing method may remain for callers that don't need second-best |
| No second-best data in SubmitEval | `second_cp/second_mate/second_uci` optional fields inline | D-03 backward-compatible extension |
| NULL `allowed_pv_lines` / `missed_pv_lines` | Non-NULL JSONB blobs for upgraded-worker games | Phase 142 populates; Phase 145 backfills the rest |

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | PV1 eval drift at multipv=2 vs multipv=1 is 5–15 cp on most positions at 1M nodes (sub-threshold) | PV1 Drift section | If drift is systematic and larger (>15–20 cp), some flaw classification boundaries shift, requiring validation before merge |
| A2 | `apply_forcing_line_filter` requires ≥2 solver nodes → the JSONB blob must have multiple nodes | Open Questions #1 | If the gate is redesigned to accept 1-node blobs, the PV-node assembly question is moot (but gate behavior changes) |
| A3 | A parallel `second_best_map` avoids widening the 7-tuple signature with minimal call-site impact | Open Questions #2 | Planner may prefer extending the tuple; either approach is correct, just different blast radius |
| A4 | `_NODES_TIMEOUT_S` (5.0s) is sufficient for multipv=2 at 1M nodes on dev and prod | Standard Stack section | If multipv=2 consistently times out at 5.0s on dev, increase proportionally (recommend `_NODES_TIMEOUT_MULTIPV2_S = 7.0` as fallback) |

---

## Sources

### Primary (HIGH confidence — verified in codebase)

- `app/services/engine.py` — `EnginePool`, `_analyse_with_pv` (line 486), `evaluate_nodes_with_pv` (line 521), `_NODES_BUDGET = 1_000_000`, `_NODES_TIMEOUT_S = 5.0`, QUEUE-07 RSS accounting comment (lines 115–135)
- `app/services/forcing_line_gate.py` — `PvNode` TypedDict (line 63), `apply_forcing_line_filter` (line 265), `is_solver_node_forced` (line 153); confirms blob shape, solver_color parameter, white-perspective convention
- `app/models/game_flaw.py` — `allowed_pv_lines` / `missed_pv_lines` columns (lines 120–121, `deferred=True`); D-05 blob key comment (lines 109–116)
- `app/schemas/eval_remote.py` — `SubmitEval` (lines 30–35), `SubmitRequest` (lines 38–45); confirms `job_id: int | None = None` backward-compat precedent
- `app/services/eval_drain.py` — `_full_drain_tick` (lines 1812–2077), `_fill_engine_game_flaw_pvs` (lines 991–1028), `_batch_update_pv_rows` (lines 443–479), `_classify_and_fill_oracle` (lines 674–840)
- `app/services/flaws_service.py` — `FlawRecord` TypedDict (lines 121–155), `classify_game_flaws` signature (line 787), `_build_flaw_record` (line 503), `_detect_tactic_for_flaw` (line 401)
- `scripts/tactic_tagger_report.py` + `scripts/backfill_tactic_tags.py` — script/report convention (`_REPORT_DIR`, argparse, `--db`, `--check-goals`)
- `.planning/phases/142-multipv-2-engine-pass-eval-drain-remote-worker/142-CONTEXT.md` — locked decisions D-01 through D-07, canonical refs
- `.planning/notes/tactic-forcing-line-gate.md` (lines 85–147) — blob shape design, every-node storage rationale, node budget framing
- `.planning/research/STACK.md`, `ARCHITECTURE.md`, `PITFALLS.md`, `SUMMARY.md` — prior milestone research (HIGH confidence, verified against codebase)

### Secondary (MEDIUM confidence — documented prior research)

- python-chess 1.11.x engine docs — `analyse()` multipv overload; `list[InfoDict]` return when multipv is int; `info_list[0]` = best, `info_list[1]` = second

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all patterns verified from codebase source
- Architecture: HIGH — derived from first-party source reading of all canonical ref files
- PV1 drift: ASSUMED — no empirical measurement; prior non-determinism memory file supports tolerating small drift
- PV-node assembly (open question): UNDECIDED — D-01 and blob requirements create a design tension the planner must resolve

**Research date:** 2026-06-29
**Valid until:** 2026-07-29 (stable project codebase; python-chess and SQLAlchemy versions locked via uv lockfile)
