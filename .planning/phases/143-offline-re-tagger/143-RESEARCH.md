# Phase 143: Offline Re-tagger — Research

**Researched:** 2026-06-30
**Domain:** Python offline re-tagger + forcing-line gate wiring + unit test audit
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**D-01:** Extend `scripts/backfill_tactic_tags.py`, then `git mv` it to `scripts/retag_flaws.py`.
Keep `--user-id` / `--dry-run` / `--db` and the inherited `--limit` / `--workers` / `--throttle-ms`.
Add `--margin` (float, defaults to the module constant). `--only-tagged` is kept but documented
as unable to discover newly-gated-in tags.

**D-01a:** Add `--margin` (float, defaults to `ONLY_MOVE_WIN_PROB_MARGIN`). Inherited flags unchanged.

**D-02:** Wire the gate into the live classify path now. Gate becomes part of
`_detect_tactic_for_flaw` (or a thin combined classify helper) reading the stored blobs.
Re-tagger and live eval-drain share the one path (SC4 no-drift).

**D-02a:** Acceptable consequence: new games analyzed between Phase 143 and 145 get gated at the
provisional 0.35 margin before Phase 144 validates it. Self-heals on corpus retag in Phase 145.

**D-02b:** Re-tagger must run the FULL classify (detection kernel + gate) from stored inputs,
not just read existing tag columns.

**D-03:** Parameterize gate functions — `margin: float = ONLY_MOVE_WIN_PROB_MARGIN` added to
`apply_forcing_line_filter` and `is_solver_node_forced`. No global mutation.

**D-04:** Committed `reports/` markdown, timestamped, following benchmarks/db-report convention.
Per-motif removed/survived counts (and where cheap, depth/quality breakdown). Planner picks
the exact path (suggest `reports/retag/retag-YYYY-MM-DD.md`).

**D-05:** Logic already exists (Phase 141); Phase 143 is audit-and-fill, not net-new logic.
`forcing_line_gate.py` already implements `_resolve_mate_priority` and solver-only uniqueness.
Existing tests cover both colors. Remaining GATE work: verify against exact SC2/SC3 wording and
add the residual multi-ply "branch-then-reconverge" defender test. If audit finds a true logic
gap (not just missing test), fix it and note the deviation.

### Claude's Discretion
- Exact CLI flag names beyond the locked set
- The precise combined-classify helper signature and where it lives (inside
  `flaws_service._detect_tactic_for_flaw` vs a thin wrapper both the drain and re-tagger call)
- Report file path/format details
- Blob-loading query shape (extend `_fetch_flaw_page` to project the two deferred JSONB columns
  + the flaw-ply `eval_cp` for the already-winning reject)
- Worker-payload shape for passing blobs across the process boundary

### Deferred Ideas (OUT OF SCOPE)
- User-28 A/B old-vs-new diff, per-motif removed/survived across depth buckets, ~30-case hand-check,
  and committing the final `ONLY_MOVE_WIN_PROB_MARGIN` — Phase 144
- `backfill_multipv.py --db prod`, `retag_flaws.py --db prod` corpus rollout with
  `WHERE allowed_pv_lines IS NULL` idempotency, and before/after per-motif chip-count monitoring — Phase 145
- Solver-only blob storage (halve MultiPV cost) — explicit later optimization (Phase 141 D-03)
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| GATE-03 | Mate scores handled by mate-priority hierarchy (only-best-is-mate → forced; both-mate → shorter forced; mate-in-1 never suppressed) | TestMatePriority (11 tests) covers all cases. Audit confirms full coverage; only residual: new margin-parameterized integration test once D-03 is wired. |
| GATE-04 | Uniqueness checked at solver nodes only; defender-node ambiguity does not kill a line (branch-then-reconverge treated as forced) | Single-node defender tests exist; missing case: multi-ply [S0, D0_amb, S1, D1_amb, S2] test — see §5. |
| RETAG-01 | Offline re-tagger re-derives tactic tags purely from stored JSONB (no engine), tunable via `--dry-run` / `--margin` / `--user-id` / `--db` | `scripts/backfill_tactic_tags.py` is ~90% of this; blob loading + `--margin` + gate is the delta. |
| RETAG-02 | Re-tagger is idempotent and updates `game_flaws` tactic columns via the single classify path | Change-only UPDATE already in `bulk_update_tactic_tags`; single path guaranteed by importing `_detect_tactic_for_flaw`. |
</phase_requirements>

---

## Summary

Phase 143 is a pure-Python extension of existing infrastructure: there are no new libraries to evaluate, no infrastructure to provision, and the gate logic is already implemented and tested. All questions are about wiring, extension, and test coverage.

The research identified five concrete implementation surfaces:

1. `scripts/backfill_tactic_tags.py` (496 lines) is the re-tagger's base. Its keyset paging, spawn-worker pool, change-only batched UPDATE, and all CLI flags are reused verbatim. The re-tagger adds three inputs to each worker: `allowed_pv_blob`, `missed_pv_blob`, and `pre_flaw_eval_cp` (sourced from the two deferred JSONB columns + `game_positions.eval_cp` at flaw_ply). The `git mv` has minimal collateral: two docstring comments in `game_flaws_repository.py` and no CI paths.

2. `forcing_line_gate.apply_forcing_line_filter` (line 265) and `is_solver_node_forced` (line 153) need a `margin: float` parameter threaded cleanly with a default; the comparison `p_best - p_second > ONLY_MOVE_WIN_PROB_MARGIN` (line 189) becomes `> margin`. No global mutation.

3. `_detect_tactic_for_flaw` (flaws_service.py line 401) is the single classify kernel. The gate wires in via optional blob + eval_cp params (or a thin wrapper). The live eval-drain path (`_classify_and_fill_oracle`) already builds blobs in memory before the write session opens; those in-memory blobs can be passed through the classify step. For rows with no blob (pre-Phase-142 flaws), the gate is skipped and the existing behavior is preserved.

4. **SC2 is fully satisfied:** all mate-priority cases are already tested in `TestMatePriority` (11 tests, both colors). **SC3 has one gap:** a multi-ply "branch-then-reconverge" test is missing — the existing defender tests cover only a single ambiguous defender node; a 5-node line [S0_forced, D0_ambiguous, S1_forced, D1_ambiguous, S2_forced] is the residual case.

5. The per-motif delta report (D-04) follows the `reports/{domain}/name-YYYY-MM-DD.md` convention. The re-tagger script can collect motif-level removed/survived counts during `--dry-run` cheaply by decoding `old_tuple[0]` (allowed motif) and `old_tuple[4]` (missed motif) against the new tuple.

**Primary recommendation:** Keep all changes tightly scoped to the five surfaces above. The gate logic, worker pool, and DB write path are already production-quality; the Phase 143 delta is parameter threading + blob loading + one missing test.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Offline re-tagging (DB read/write) | Backend scripts | — | Standalone Python script, not part of the API or frontend |
| Gate logic (margin comparison) | Python pure module | — | `forcing_line_gate.py` is engine-free, zero I/O |
| Blob loading (JSONB from game_flaws) | Backend scripts | — | Explicitly selected in `_fetch_flaw_page`; deferred on ORM entity |
| `pre_flaw_eval_cp` sourcing | Backend scripts | — | `game_positions.eval_cp` at flaw_ply, added to `_load_positions_for_page` |
| Live classify gate wiring | API / Backend | — | `_classify_and_fill_oracle` in `eval_drain.py` threads blobs to classify |
| Test coverage (gate unit tests) | Backend tests | — | `tests/services/test_forcing_line_gate.py` — no DB/engine needed |
| Per-motif delta report | Backend scripts | — | Re-tagger script writes `reports/retag/retag-YYYY-MM-DD.md` |

---

## 1. The Base Script — Verified Structure

**File:** `scripts/backfill_tactic_tags.py` [VERIFIED: codebase read]

### Key constants and types

```python
FLAWS_PER_BATCH = 2000  # line 110 — commit every N rows (OOM history)

@dataclass(frozen=True)
class _PosRow:          # line 113
    move_san: str | None
    pv: str | None
    eval_mate: int | None

@dataclass(frozen=True)
class _FlawWork:        # line 207
    user_id: int
    game_id: int
    ply: int
    fen: str            # game_flaws.fen is NOT NULL
    cur: _PosRow | None # position at ply (missed pass reads this)
    nxt: _PosRow | None # position at ply+1 (allowed pass reads this)
    old_tuple: tuple[int | None, ...]  # current 8 tactic cols
```

### CLI flags (current)

```
--db         dev|benchmark|prod   (required)
--user-id    int                  (optional, scopes to one user)
--only-tagged                     (only flaws with existing tactic tag)
--dry-run                         (no writes; count changed rows)
--limit      int                  (smoke test cap)
--workers    int                  (parallel detection processes; default CPU count)
--throttle-ms int                 (sleep after each page commit on live DB)
```

**To add:** `--margin float` (default `ONLY_MOVE_WIN_PROB_MARGIN`).

### Key function signatures

```python
async def _fetch_flaw_page(
    session: AsyncSession,
    *,
    user_id: int | None,
    only_tagged: bool,
    after: tuple[int, int, int] | None,
    limit: int,
) -> list[Row[Any]]:
    # line 274
    # Selects: user_id, game_id, ply, fen, + 8 TACTIC_TAG_COLUMNS
    # Keyset pagination: WHERE (user_id, game_id, ply) > after
    # Does NOT currently project allowed_pv_lines, missed_pv_lines, or eval_cp
```

```python
async def _load_positions_for_page(
    session: AsyncSession,
    flaws: list[Row[Any]],
) -> dict[tuple[int, int, int], _PosRow]:
    # line 314
    # Loads: move_san, pv, eval_mate for (user_id, game_id, ply) and (ply+1)
    # Does NOT currently load eval_cp
```

```python
def _worker_recompute(work: _FlawWork) -> tuple[int | None, ...] | None:
    # line 226
    # Pure-CPU, no DB. Returns new 8-tuple or None if unchanged (no-op).
    allowed = _detect_tactic_for_flaw(ply, fen_map, positions, None, orientation="allowed")
    missed  = _detect_tactic_for_flaw(ply, fen_map, positions, None, orientation="missed")
    new_tuple = (*allowed, *missed)
    return None if new_tuple == work.old_tuple else new_tuple
```

```python
async def run_backfill(
    *,
    db: str,
    user_id: int | None,
    only_tagged: bool,
    dry_run: bool,
    limit: int | None,
    workers: int | None = None,
    throttle_ms: int = 0,
    session_maker: async_sessionmaker[AsyncSession] | None = None,
) -> None:
    # line 365 — main orchestrator, injectable session_maker for testing
```

---

## 2. The Gate — Verified Signatures

**File:** `app/services/forcing_line_gate.py` [VERIFIED: codebase read]

### Constants (line 52-60)

```python
ONLY_MOVE_WIN_PROB_MARGIN: float = 0.35   # line 52 — provisional; Phase 144 commits final
ALREADY_WINNING_CP_THRESHOLD: int = 300   # line 55 — already-winning reject (D-08)
STILL_WINNING_FLOOR_CP: int = 200         # line 59 — stop extending below this (D-09)
```

### PvNode TypedDict (line 63)

```python
class PvNode(TypedDict):
    b:  int | None  # best_cp, white-perspective
    bm: int | None  # best_mate (positive=white mating)
    s:  int | None  # second_cp, white-perspective
    sm: int | None  # second_mate
    su: str         # second-best UCI (empty string when no second move)
```

### Public functions — current signatures, needed changes

```python
# line 265 — ADD margin: float = ONLY_MOVE_WIN_PROB_MARGIN
def apply_forcing_line_filter(
    line: Sequence[PvNode],
    solver_color: Literal["white", "black"],
    pre_flaw_eval_cp: int,
    margin: float = ONLY_MOVE_WIN_PROB_MARGIN,   # D-03 addition
) -> bool: ...

# line 153 — ADD margin: float = ONLY_MOVE_WIN_PROB_MARGIN
def is_solver_node_forced(
    node: PvNode,
    solver_color: Literal["white", "black"],
    margin: float = ONLY_MOVE_WIN_PROB_MARGIN,   # D-03 addition
) -> bool: ...
# line 189: change `> ONLY_MOVE_WIN_PROB_MARGIN` to `> margin`
# apply_forcing_line_filter must pass margin= to is_solver_node_forced
```

Private functions (`_resolve_mate_priority`, `_truncate_at_still_winning_floor`,
`_strip_trailing_only_moves`, `_is_already_winning`) need NO changes — they don't use the margin.

### Margin threading detail (D-03)

The only change in `is_solver_node_forced` is line 189:
```python
# current:
return p_best - p_second > ONLY_MOVE_WIN_PROB_MARGIN
# after D-03:
return p_best - p_second > margin
```

`apply_forcing_line_filter` already calls `all(is_solver_node_forced(node, solver_color) for node in solver_nodes)` (line 309); this becomes `all(is_solver_node_forced(node, solver_color, margin) for node in solver_nodes)`.

No global mutation needed — the committed constant remains the default; the CLI `--margin` flows via function args, which is worker-pool-safe (spawn workers re-import the module and would never see a mutated global).

---

## 3. The Classify Seam — Wire Point for D-02

**File:** `app/services/flaws_service.py` [VERIFIED: codebase read]

### Current `_detect_tactic_for_flaw` signature (line 401)

```python
def _detect_tactic_for_flaw(
    n: int,
    fen_map: dict[int, str],
    positions: list[GamePosition],
    pv_by_ply: Mapping[int, str] | None = None,
    orientation: Literal["allowed", "missed"] = "allowed",
) -> tuple[int | None, int | None, int | None, int | None]:
    # Returns (tactic_motif_int, tactic_piece, tactic_confidence, tactic_depth)
```

### Call sites

1. **Live eval-drain:** `_classify_and_fill_oracle` (eval_drain.py ~line 688) calls
   `classify_game_flaws(game, positions, pv_by_ply=pv_by_ply)`, which calls
   `_build_flaw_record(n, ...)`, which calls `_detect_tactic_for_flaw(n, ..., orientation="allowed")`
   and `_detect_tactic_for_flaw(n, ..., orientation="missed")` (lines 523-530 of flaws_service.py).

2. **Re-tagger / backfill:** `scripts/backfill_tactic_tags.py` imports `_detect_tactic_for_flaw`
   directly (line 106) and calls it in `_worker_recompute` (lines 246-247).

### Live drain ordering (eval_drain.py lines 2286-2329) [VERIFIED: codebase read]

```
Step 3d: flaw_pv_blobs = await _build_flaw_multipv2_blobs(...)  # blobs in memory, NO session
Step 4 (write_session):
    await _classify_and_fill_oracle(write_session, game_id, engine_result_map)
    await _run_multipv2_pass(write_session, game_id, flaw_pv_blobs)   # writes blobs to DB
```

**Critical:** `_classify_and_fill_oracle` runs BEFORE `_run_multipv2_pass`. So at classify time,
blobs are NOT yet in the DB — they're in memory as `flaw_pv_blobs`. For D-02 (gate in live
classify path), `flaw_pv_blobs` must be passed from the call site into `_classify_and_fill_oracle`.

### Recommended seam design (Claude's Discretion)

**Option A — thin wrapper (preferred, leaves kernel intact):**
Add a `_classify_tactic_gated()` function in flaws_service.py that wraps `_detect_tactic_for_flaw`:

```python
def _classify_tactic_gated(
    n: int,
    fen_map: dict[int, str],
    positions: list[GamePosition],
    orientation: Literal["allowed", "missed"],
    pv_blob: list[PvNode] | None,          # None = gate skipped (old rows / no blob)
    pre_flaw_eval_cp: int | None,           # None = gate skipped
    pv_by_ply: Mapping[int, str] | None = None,
    margin: float = ONLY_MOVE_WIN_PROB_MARGIN,
) -> tuple[int | None, int | None, int | None, int | None]:
    motif, piece, conf, depth = _detect_tactic_for_flaw(n, fen_map, positions, pv_by_ply, orientation)
    if motif is not None and pv_blob is not None and pre_flaw_eval_cp is not None:
        solver_color = _solver_color_for(n, orientation)
        if not apply_forcing_line_filter(pv_blob, solver_color, pre_flaw_eval_cp, margin):
            return None, None, None, None
    return motif, piece, conf, depth
```

`_build_flaw_record` calls `_classify_tactic_gated` instead of `_detect_tactic_for_flaw`, receiving the blobs from above via `_classify_and_fill_oracle`. The re-tagger calls `_classify_tactic_gated` from `_worker_recompute` after loading blobs + eval_cp.

**Option B — add optional params to `_detect_tactic_for_flaw`:** Modify the kernel directly.
More invasive, but avoids a new function. Either approach satisfies D-02/SC4.

### Solver color from ply parity

```python
def _solver_color_for(
    n: int,
    orientation: Literal["allowed", "missed"],
) -> Literal["white", "black"]:
    # Even ply: white moved (made the flaw). For "allowed": refuter (solver) = black.
    # For "missed": flaw-maker (solver) = white.
    if orientation == "allowed":
        return "black" if n % 2 == 0 else "white"
    else:  # "missed"
        return "white" if n % 2 == 0 else "black"
```

This matches the ply-parity convention already established in `_detect_tactic_for_flaw` (line 444-446):
`board_before.turn = chess.WHITE if n % 2 == 0 else chess.BLACK`.

---

## 4. Blob Loading — What Changes in the Re-tagger

**Files:** `app/models/game_flaw.py` lines 120-121, `scripts/backfill_tactic_tags.py` [VERIFIED: codebase read]

### The deferred columns

```python
# game_flaw.py lines 120-121
allowed_pv_lines: Mapped[list[Any] | None] = mapped_column(JSONB, nullable=True, deferred=True)
missed_pv_lines:  Mapped[list[Any] | None] = mapped_column(JSONB, nullable=True, deferred=True)
```

`deferred=True` means these are NEVER loaded in any `select(GameFlaw)` ORM entity. **But** when
selecting individual column attributes explicitly (not full ORM entities), deferred status is
irrelevant — the column value is returned directly. `_fetch_flaw_page` already selects individual
columns (`GameFlaw.user_id`, etc.), so adding `GameFlaw.allowed_pv_lines` and
`GameFlaw.missed_pv_lines` to the SELECT is straightforward and safe.

### Changes needed in `_fetch_flaw_page`

Add two column projections to the existing SELECT:
```python
stmt = select(
    GameFlaw.user_id,
    GameFlaw.game_id,
    GameFlaw.ply,
    GameFlaw.fen,
    *(getattr(GameFlaw, col) for col in TACTIC_TAG_COLUMNS),
    GameFlaw.allowed_pv_lines,   # new — JSONB list[PvNode] | None
    GameFlaw.missed_pv_lines,    # new — JSONB list[PvNode] | None
)
```

asyncpg auto-registers the JSONB codec — no manual setup. Each row's `.allowed_pv_lines` and
`.missed_pv_lines` will be `list[dict] | None` (the PvNode dicts, deserialized from JSON).

### Changes needed in `_load_positions_for_page` / `_PosRow`

`pre_flaw_eval_cp` is `game_positions.eval_cp` at the flaw ply (white-perspective). The existing
position query already covers the flaw ply key `(user_id, game_id, ply)`. Add `GamePosition.eval_cp`
to the SELECT:

```python
stmt = select(
    GamePosition.user_id,
    GamePosition.game_id,
    GamePosition.ply,
    GamePosition.move_san,
    GamePosition.pv,
    GamePosition.eval_mate,
    GamePosition.eval_cp,        # new — for pre_flaw_eval_cp
)
```

Extend `_PosRow`:
```python
@dataclass(frozen=True)
class _PosRow:
    move_san: str | None
    pv: str | None
    eval_mate: int | None
    eval_cp: int | None          # new — for gate's already-winning reject
```

### Extended `_FlawWork` payload

```python
@dataclass(frozen=True)
class _FlawWork:
    user_id: int
    game_id: int
    ply: int
    fen: str
    cur: _PosRow | None          # position at ply (missed pass + eval_cp source)
    nxt: _PosRow | None          # position at ply+1 (allowed pass)
    old_tuple: tuple[int | None, ...]
    allowed_pv_blob: list[Any] | None   # new — allowed_pv_lines JSONB
    missed_pv_blob:  list[Any] | None   # new — missed_pv_lines JSONB
    margin: float                       # new — passed from --margin CLI flag
```

`pre_flaw_eval_cp` can be derived in `_worker_recompute` as `work.cur.eval_cp if work.cur else None`
(the `cur` position is already at the flaw ply). No separate field needed.

### Memory cross-process boundary note

The JSONB blobs per flaw are small (6-12 PvNodes × 5 fields each ≈ a few hundred bytes). IPC
payload stays cheap. The existing spawn-worker approach is safe.

---

## 5. Existing Gate Tests — SC2/SC3 Audit

**File:** `tests/services/test_forcing_line_gate.py` (468 lines) [VERIFIED: codebase read]

### Test class inventory

| Class / Function | Lines | What it covers |
|-----------------|-------|----------------|
| `TestConstants` | ~56-69 | Pin the three constant values |
| `TestOnlyMoveMargin` | ~77-161 | Win-prob margin branch: large gap passes (both colors), small gap fails, no-second-move passes, boundary, all-solver-nodes-required, single ambiguous defender |
| `TestMatePriority` | ~169-248 | Mate-priority hierarchy: only-best-is-mate (both colors), both-mates-shorter-wins (both colors), both-mates-longer-not-forced, mate-in-1 never suppressed (4 tests both colors vs cp), fall-through, equal-distance |
| `TestAlreadyWinning` | ~256-311 | pre_flaw above/at/below threshold (both colors), neutral |
| `TestStillWinningFloor` | ~319-383 | Truncation (both colors), at-floor included, mate bypasses floor |
| `TestLineStripping` | ~391-468 | Trailing strip leaving 2 nodes, one-mover discard, single-solver discard, empty, multiple trailing, re-convergence, strip-to-one |

### SC2 audit (GATE-03 — mate-priority hierarchy)

**Requirement:** "only-best-is-mate means forced; both-mates means shorter-distance-to-mate is
forced; else fall through to sigmoid — and confirm mate-in-1 is never suppressed"

| SC2 clause | Covered by | Status |
|-----------|-----------|--------|
| only-best-is-mate → forced | `test_only_best_is_mate_white_solver`, `test_only_best_is_mate_black_solver` | COVERED |
| both-mates → shorter forced | `test_both_mates_shorter_wins_white_solver`, `test_both_mates_shorter_wins_black_solver` | COVERED |
| both-mates → longer NOT forced | `test_both_mates_longer_not_forced_white_solver`, `test_both_mates_longer_not_forced_black_solver` | COVERED |
| mate-in-1 never suppressed | `test_mate_in_1_never_suppressed_white_solver`, `test_mate_in_1_never_suppressed_black_solver`, `test_mate_in_1_vs_second_cp_white_solver`, `test_mate_in_1_vs_second_cp_black_solver` | COVERED (4 tests) |
| else fall through to sigmoid | `test_no_mate_falls_through_to_cp_margin` | COVERED |

**SC2 verdict:** FULLY SATISFIED. No new tests required for GATE-03 mate logic. The only
GATE-03 addition is a margin-parameterized test once D-03 is wired (confirm gate passes/fails
differ at `margin=0.1` vs `margin=0.5`), but this is a D-03 test, not a GATE-03 gap.

### SC3 audit (GATE-04 — defender-branch-then-reconverge)

**Requirement:** "A unit test with a defender-branching position confirms that ambiguity at
defender nodes does not kill a valid forcing line (branch-then-reconverge treated as forced)"

| Existing test | Lines | What it covers | Gap? |
|--------------|-------|----------------|------|
| `test_defender_ambiguity_does_not_kill_line` | 148-161 | [S0, D0_ambiguous, S1] — single ambiguous defender | partial |
| `test_defender_re_convergence_does_not_kill_line` | 442-457 | [S0, D0_ambiguous, S1] — single ambiguous defender (also single node) | partial |

Both existing tests cover a 3-node line with ONE ambiguous defender. **Missing case:** a
multi-ply line with MULTIPLE ambiguous defender nodes — the "branch-then-reconverge" pattern
across multiple plies. This is the residual SC3 gap:

```python
# MISSING TEST — add to TestLineStripping or a new TestDefenderBranching class:
def test_multi_ply_defender_ambiguity_does_not_kill_line() -> None:
    """Multiple ambiguous defender nodes in a 5-node line do not kill a forced solver line.

    [S0=forced, D0=ambiguous, S1=forced, D1=ambiguous, S2=forced] — branch-then-reconverge
    at BOTH D0 and D1; solver continuations S0/S1/S2 are all forced. The line must pass.
    """
    line: list[PvNode] = [
        _cp_node(b=800, s=0),    # S0 solver — forced (large gap)
        _cp_node(b=100, s=50),   # D0 defender — ambiguous (s close to b); NOT checked
        _cp_node(b=800, s=0),    # S1 solver — forced
        _cp_node(b=100, s=80),   # D1 defender — highly ambiguous; NOT checked
        _cp_node(b=800, s=0),    # S2 solver — forced
    ]
    assert apply_forcing_line_filter(line, "white", pre_flaw_eval_cp=0) is True
```

**SC3 verdict:** One new test needed. The gate LOGIC is already correct (defender nodes at odd
indices are never checked). The test gap is purely at the multi-ply coverage level.

---

## 6. Per-Motif Delta Report (D-04)

### Report convention [VERIFIED: codebase read]

Existing committed reports follow the pattern `reports/{domain}/name-YYYY-MM-DD.md`:
- `reports/tactic-tagger/tactic-tagger-2026-06-23.md`
- `reports/multipv-validation/validate-multipv-budget-2026-06-30.md`
- `reports/db-stats/db-report-prod-YYYY-MM-DD.md`

**Recommended path for re-tagger:** `reports/retag/retag-YYYY-MM-DD.md`

### What's cheaply available from a dry-run

During `--dry-run`, `_worker_recompute` returns the new 8-tuple (or None). For reporting:
- **Removed:** flaw had `old_tuple[0] != None` (allowed_tactic_motif set) but `new_tuple[0] is None` — gate suppressed it
- **Survived:** flaw had `old_tuple[0] != None` and `new_tuple[0] != None` (gate passed)
- **Per-motif split:** decode `old_tuple[0]` against `TacticMotifInt` enum (the same values stored as SmallInteger in game_flaws) for allowed; `old_tuple[4]` for missed

The writer can be inline in `run_backfill` (accumulate a `collections.Counter` per motif during the dry-run loop, write the report at the end). Alternatively a sibling `generate_retag_report()` function.

### Recommended report content

```markdown
# FlawChess Re-tagger Report

**Generated:** YYYY-MM-DD HH:MM:SS UTC
**Margin:** 0.35 (or --margin value)
**Scope:** all users / user-ID N
**Mode:** dry-run

## Allowed-orientation tag changes

| Motif | Total tagged | Gate suppressed | Survived | Suppression % |
|-------|-------------|-----------------|---------|--------------|
| fork  | N           | N               | N       | N%           |
...

## Missed-orientation tag changes
...
```

---

## 7. Idempotency Mechanics (SC4)

The change-only UPDATE mechanism guarantees idempotency:

1. First run at `--margin X`: `_worker_recompute` returns new_tuple != old_tuple for changed flaws → `bulk_update_tactic_tags` writes them. Changed rows now have new_tuple in DB.
2. Second run at same `--margin X`: `_worker_recompute` recomputes new_tuple from same blobs + same eval_cp + same margin → equals the DB value → returns `None` (no-op) → 0 updates.

`bulk_update_tactic_tags` (game_flaws_repository.py line 166) uses ORM bulk-UPDATE-by-PK with
explicit tactic columns only — no WAL for no-op rows (because they're never included in the
`updates` list from `_updates_from_results`).

**Verifier assertion:** `--dry-run` second run reports "0 flaw rows that would change" — this
is the concrete evidence of idempotency the SC4 check can verify.

---

## 8. `git mv` Rename (D-01) — Collateral Map

### Confirmed references to `backfill_tactic_tags.py` [VERIFIED: codebase read]

| Location | Line(s) | Nature | Action needed |
|----------|---------|--------|---------------|
| `scripts/backfill_tactic_tags.py` | entire file | The file itself | `git mv` |
| `app/repositories/game_flaws_repository.py` | 152, 172 | Docstring comments (`"Used by backfill_tactic_tags.py"`) | Update to `retag_flaws.py` |
| `.github/workflows/ci.yml` | none | Not referenced | No action |
| `pyproject.toml` | none | Not referenced | No action |
| `.planning/milestones/v1.28-phases/132-*/` | various | Historical planning docs (merged phases) | No action (history only) |
| `.planning/ROADMAP.md` | 109, 111, 157, 162, 191 | Already uses `retag_flaws.py` name for Phase 143+ | No action needed |
| `.claude/skills/` | none | Not referenced | No action |

`scripts/retag_flaws.py` does NOT currently exist — the `git mv` creates it cleanly.

### Module docstring update

The module docstring in `scripts/retag_flaws.py` (renamed file) should be updated to reflect:
- The script's new role: re-derive tactic tags from stored JSONB blobs, applying the forcing-line gate
- The `--margin` flag and its role in RETAG-01
- The "gate-free refresh tool no longer exists" rationale (D-01: once gate is wired into live classify, a gate-free re-backfill would diverge from production)

---

## 9. Standard Stack

No new libraries required. All code uses existing project dependencies.

### Core (all already in pyproject.toml)

| Library | Role | Notes |
|---------|------|-------|
| `python-chess` | Board FEN/SAN parsing in `_detect_tactic_for_flaw` | Unchanged |
| SQLAlchemy 2.x async | `_fetch_flaw_page`, `_load_positions_for_page`, `bulk_update_tactic_tags` | Unchanged |
| asyncio / multiprocessing | `ProcessPoolExecutor` spawn worker pool | Unchanged |
| Pydantic v2 / TypedDict | `PvNode` TypedDict in `forcing_line_gate.py` | Unchanged |
| `sentry_sdk` | Error capture in `run_backfill` exception handler | Unchanged |

---

## Package Legitimacy Audit

No new external packages required. This section is not applicable — Phase 143 installs nothing.

---

## Architecture Patterns

### System Architecture Diagram

```
CLI --margin / --dry-run / --db / --user-id
         |
         v
scripts/retag_flaws.py  (renamed from backfill_tactic_tags.py)
         |
    _fetch_flaw_page   <-- game_flaws (PK + 8 tactic cols + 2 JSONB blobs)
         |
    _load_positions_for_page  <-- game_positions (move_san, pv, eval_mate, eval_cp)
         |
    _make_works  -->  _FlawWork (+ allowed_pv_blob, missed_pv_blob, margin)
         |
    ProcessPoolExecutor (spawn)
         |
    _worker_recompute(work)
         |--- _classify_tactic_gated(orientation="allowed", pv_blob=allowed_pv_blob)
         |         |--- _detect_tactic_for_flaw(n, fen_map, positions)  [kernel unchanged]
         |         |--- apply_forcing_line_filter(blob, solver_color, eval_cp, margin)
         |
         |--- _classify_tactic_gated(orientation="missed", pv_blob=missed_pv_blob)
         |
         |--- compare new_tuple to work.old_tuple -> None (no-op) or new_tuple
         |
    _updates_from_results  -->  change-only update dicts
         |
    bulk_update_tactic_tags  (skip if --dry-run)
         |
    [optional] write reports/retag/retag-YYYY-MM-DD.md  (if --dry-run + --report flag)

Live eval-drain path (D-02):
    _build_flaw_multipv2_blobs  -->  flaw_pv_blobs (in memory)
         |
    _classify_and_fill_oracle(write_session, game_id, engine_result_map, flaw_pv_blobs)
         |--- classify_game_flaws -> _build_flaw_record -> _classify_tactic_gated
                                                                    |
                                                          apply_forcing_line_filter(blob_from_memory)
```

### Recommended Project Structure (unchanged — changes are additive)

```
scripts/
├── retag_flaws.py          # renamed + extended (D-01)
├── backfill_multipv.py     # Phase 145 (out of scope here)
app/services/
├── forcing_line_gate.py    # add margin param (D-03)
├── flaws_service.py        # add _classify_tactic_gated or extend _detect_tactic_for_flaw (D-02)
app/repositories/
├── game_flaws_repository.py  # update docstring comment only
reports/
├── retag/
│   └── retag-YYYY-MM-DD.md  # new directory + report (D-04)
tests/services/
├── test_forcing_line_gate.py  # add multi-ply defender test (SC3 gap)
```

### Pattern 1: Extend `_fetch_flaw_page` for JSONB blobs

```python
# Source: codebase read scripts/backfill_tactic_tags.py line 289-310
# Add GameFlaw.allowed_pv_lines and GameFlaw.missed_pv_lines to the SELECT.
# Deferred status on the ORM entity does NOT affect explicit column selects.
stmt = select(
    GameFlaw.user_id,
    GameFlaw.game_id,
    GameFlaw.ply,
    GameFlaw.fen,
    *(getattr(GameFlaw, col) for col in TACTIC_TAG_COLUMNS),
    GameFlaw.allowed_pv_lines,   # JSONB — list[dict] | None from asyncpg
    GameFlaw.missed_pv_lines,    # JSONB — list[dict] | None from asyncpg
)
```

### Pattern 2: Solver color from ply parity

```python
# Source: flaws_service.py line 444-446 (established convention)
# Even ply: white moved (made the flaw).
# For "allowed": refuter (solver) is the OPPONENT = black.
# For "missed": flaw-maker (solver) is white.
def _solver_color_for(n: int, orientation: Literal["allowed", "missed"]) -> Literal["white", "black"]:
    if orientation == "allowed":
        return "black" if n % 2 == 0 else "white"
    return "white" if n % 2 == 0 else "black"
```

### Anti-Patterns to Avoid

- **Mutating `ONLY_MOVE_WIN_PROB_MARGIN` globally** for the `--margin` flag: spawn workers re-import the module with the original constant — the override is invisible in child processes. Thread via function arg (D-03).
- **Loading full ORM entities (`select(GameFlaw)`) to get the JSONB blobs:** triggers `MissingGreenlet` due to `deferred=True` + asyncio. Select explicit columns instead.
- **Running `asyncio.gather` on the same `AsyncSession`** (CLAUDE.md hard rule): the existing paging loop already avoids this; the re-tagger MUST preserve this.
- **Second-guessing the blob shape:** Phase 142 locked `b/bm/s/sm/su` with white-perspective cp. The gate already handles this convention. Do not re-derive or transform at the re-tagger layer.
- **Applying the gate to the "missed" pass without blobs** (pre-Phase-142 rows have `missed_pv_lines IS NULL`): when `missed_pv_blob is None`, skip the gate for that orientation and return the raw detect result unchanged.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| CP → win-probability conversion | Custom sigmoid | `eval_utils.eval_cp_to_expected_score` | Already uses `LICHESS_K`; changing it here would break the gate's numeric guarantees |
| Keyset pagination | OFFSET-based paging | Existing `_fetch_flaw_page` pattern | OFFSET degrades to O(N) on millions of rows; the PK tuple comparison IS the standard |
| Parallel CPU dispatch | `multiprocessing.Pool` (fork) | `ProcessPoolExecutor(mp_context=mp.get_context("spawn"))` | Fork inherits async loops and DB connections; spawn is clean (existing pattern) |
| Bulk UPDATE | Per-row `session.execute(update(...))` | `bulk_update_tactic_tags` via SQLAlchemy ORM bulk-update-by-PK | Runs as one executemany, not N round-trips |

---

## Common Pitfalls

### Pitfall 1: Deferred JSONB columns raise MissingGreenlet on full entity load

**What goes wrong:** If the re-tagger accidentally calls `select(GameFlaw)` (full ORM entity),
accessing `.allowed_pv_lines` or `.missed_pv_lines` raises `MissingGreenlet` because the deferred
columns require a live session context.

**Why it happens:** `deferred=True` is intentional (STORE-02 leak guard — blobs must never leak
into stats scans).

**How to avoid:** Continue the existing pattern of selecting individual column attributes
(`GameFlaw.allowed_pv_lines`, `GameFlaw.missed_pv_lines` added to the explicit column tuple).
This bypasses deferred loading entirely.

### Pitfall 2: `None` blob vs empty blob vs gate skip

**What goes wrong:** A flaw row with `allowed_pv_lines = []` (empty list, not NULL) is different
from `NULL`. The gate would run on an empty line and immediately fail the one-mover-discard
check (0 solver nodes < 2), suppressing a motif that would not have been suppressed with a
correct blob.

**Why it happens:** Phase 142 wrote blobs for all newly analyzed games, but pre-142 rows have
`NULL` blobs. The re-tagger should skip the gate for NULL blobs (backward compat), but an
empty-list blob should run through the gate and be rejected (as designed).

**How to avoid:** Gate condition is `pv_blob is not None` (not `if pv_blob`). An empty list is
a valid blob that should go through the gate.

### Pitfall 3: Worker-pool `_FlawWork` must be picklable

**What goes wrong:** Adding a non-picklable object (e.g. a TypedDict type reference, an ORM
session, a lambda) to `_FlawWork` causes `ProcessPoolExecutor` to fail with a pickle error.

**Why it happens:** Spawn workers communicate via pickle.

**How to avoid:** The `allowed_pv_blob: list[Any] | None` and `missed_pv_blob: list[Any] | None`
fields are plain Python lists of dicts — fully picklable. `margin: float` is a scalar. All safe.

### Pitfall 4: Live drain — blobs not yet in DB when classify runs

**What goes wrong:** D-02 might be implemented by reading blobs from the DB inside
`_classify_and_fill_oracle`, but the blobs haven't been written yet at that point (they're in
memory, written by `_run_multipv2_pass` AFTER classify).

**Why it happens:** The ordering in `_full_drain_tick` is: classify → write blobs (lines 2324-2329).

**How to avoid:** Pass `flaw_pv_blobs` from the call site into `_classify_and_fill_oracle`.
The in-memory dict maps `flaw_ply → (allowed_blobs, missed_blobs)`. The classify step picks
blobs from this dict by flaw ply. No DB read needed.

### Pitfall 5: JSONB deserialization type — `list[dict]` not `list[PvNode]`

**What goes wrong:** Treating the raw JSONB as `list[PvNode]` without verification. The database
returns a plain Python list of dicts; TypedDict `PvNode` has no runtime enforcement.

**Why it happens:** `PvNode` is a TypedDict — a static type hint only.

**How to avoid:** Cast to `list[PvNode]` for type-checker satisfaction, but the values are plain
dicts at runtime. Access by key: `node["b"]`, `node["bm"]`, etc. The gate already handles this
correctly — `PvNode(TypedDict)` is structural, not a class. No runtime conversion needed.

---

## Runtime State Inventory

This phase does NOT rename any string embedded in runtime state. Phase 143 is a new script +
gate wiring, not a rename/refactor. This section is skipped.

---

## Validation Architecture

`workflow.nyquist_validation` is `true` in `.planning/config.json`.

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest |
| Config file | `pyproject.toml` (addopts) |
| Quick run command | `uv run pytest tests/services/test_forcing_line_gate.py -v` |
| Full suite command | `uv run pytest -n auto` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| GATE-03 | Mate-priority hierarchy (only-best-is-mate, both-mates-shorter, mate-in-1-never-suppressed) | unit | `uv run pytest tests/services/test_forcing_line_gate.py::TestMatePriority -v` | Yes |
| GATE-03 | `margin` param threads correctly (gate passes/fails differ at 0.1 vs 0.5) | unit | `uv run pytest tests/services/test_forcing_line_gate.py -k "margin" -v` | Partial (existing margin tests; new margin-param test needed) |
| GATE-04 | Multi-ply defender ambiguity does not kill forced line | unit | `uv run pytest tests/services/test_forcing_line_gate.py -k "defender" -v` | Partial — SC3 gap test missing |
| RETAG-01 | `--dry-run --margin X --user-id N` reports per-motif delta without writing | smoke | `uv run python scripts/retag_flaws.py --db dev --dry-run --margin 0.35 --user-id 28` | No (script does not exist yet) |
| RETAG-02 | Second run at same margin produces 0 changed rows | smoke | Run twice, compare "flaw rows changed" counts | No (script does not exist yet) |

### Sampling Rate

- **Per task commit:** `uv run pytest tests/services/test_forcing_line_gate.py -v`
- **Per wave merge:** `uv run pytest -n auto`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `tests/services/test_forcing_line_gate.py` — add multi-ply defender test (SC3 residual)
- [ ] `tests/services/test_forcing_line_gate.py` — add margin-parameterized test for D-03 (confirm `is_solver_node_forced` respects passed-in margin)
- [ ] `scripts/retag_flaws.py` — does not exist (created by D-01 `git mv`)

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | Not applicable (offline script) |
| V3 Session Management | no | Not applicable |
| V4 Access Control | no | Script is admin-only, not exposed via API |
| V5 Input Validation | yes | CLI args validated via argparse; `margin` is a float, not user-derived DB content |
| V6 Cryptography | no | Not applicable |

### Known Threat Patterns for {stack}

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| JSONB blob deserialization of malformed data | Tampering | Gate reads `node["b"]` etc.; malformed nodes with `None`/missing keys are handled by existing `_resolve_mate_priority` / `is_solver_node_forced` guards (conservative `return False` on malformed) |
| SQL injection via user_id CLI arg | Tampering | argparse forces `type=int`; SQLAlchemy parameterized queries throughout |
| Prod DB writes from a laptop | Escalation | CLAUDE.md: run prod backfill on the prod server; the SSH tunnel is for read-only access only |

**AGPL boundary (REQUIREMENTS.md Out-of-Scope):** heuristics, constants, and names from
lichess-puzzler are facts (not copyrightable). Only the original Python implementation in
`forcing_line_gate.py` is permitted. Copy NO source from the lichess-puzzler repository.
This phase adds only a `margin` parameter to existing functions — zero new AGPL-boundary content.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `game_positions.eval_cp` at flaw_ply is the correct `pre_flaw_eval_cp` for both "allowed" and "missed" orientation | §4 | For "missed", the semantically correct value might be positions[N-1].eval_cp (the board before the flaw). Using positions[N].eval_cp for missed may cause the already-winning reject to be less effective for that orientation. Risk is LOW — the reject only fires at >300 cp, and a blunder-maker is unlikely to be >300 cp ahead after their own blunder. |

**A1 mitigation:** The CONTEXT explicitly specifies "flaw-ply eval_cp" for both passes. If the
semantic edge case surfaces during Phase 144's A/B, the fix is a one-line change in the wrapper.

---

## Open Questions

1. **Gate applies to both `allowed` and `missed` blobs, or `allowed` only?**
   - What we know: CONTEXT refers to "the two stored JSONB blob lines" and "apply the gate". The
     forcing-line concept is identical for both orientations (is the tactic genuinely forced?).
   - Recommendation: apply gate to BOTH orientations. For "missed", `solver_color` = flaw-maker's
     color; for "allowed", `solver_color` = refuter's color. This is the most consistent design.

2. **Report writer — inline in `run_backfill` or separate function?**
   - Recommendation: inline in `run_backfill`, gated by `if dry_run and report_path`. A
     `--report` flag (optional path, or auto-generate `reports/retag/retag-{date}.md`) keeps the
     script self-contained without a sibling file. The planner can decide.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| PostgreSQL (Docker dev) | `--db dev` dry-run | Must be running | 18.x | Run `docker compose -f docker-compose.dev.yml -p flawchess-dev up -d` |
| Python 3.13 | Script execution | Yes | 3.13 | — |
| uv | Script runner | Yes | — | — |
| pytest | Gate unit tests | Yes | — | — |

The scripts require a populated `game_flaws` table with Phase 142 blobs for a meaningful dry-run.
Dev DB user-28 data should have blobs from the Phase 142 eval drain.

---

## Sources

### Primary (HIGH confidence — codebase reads)

- `scripts/backfill_tactic_tags.py` — complete function-level read; all signatures verified
- `app/services/forcing_line_gate.py` — complete read; all constants, signatures, and logic verified
- `app/services/flaws_service.py` — `_detect_tactic_for_flaw` (lines 401-500), `_build_flaw_record` (lines 503-549), `_classify_and_fill_oracle` call flow
- `app/services/eval_drain.py` — `_classify_and_fill_oracle` context (lines 688-758), blob ordering (lines 2286-2329)
- `app/models/game_flaw.py` — deferred JSONB columns (lines 97-121), tactic tag columns
- `app/repositories/game_flaws_repository.py` — `TACTIC_TAG_COLUMNS`, `bulk_update_tactic_tags`
- `tests/services/test_forcing_line_gate.py` — complete read (468 lines); all test classes mapped

### Secondary (HIGH confidence — planning docs)

- `.planning/phases/143-offline-re-tagger/143-CONTEXT.md` — locked decisions D-01 through D-05
- `.planning/REQUIREMENTS.md` — GATE-03, GATE-04, RETAG-01, RETAG-02 requirements
- `.planning/notes/tactic-forcing-line-gate.md` — design rationale, AGPL boundary, blob shape

### Tertiary (MEDIUM confidence — pattern observation)

- `reports/tactic-tagger/tactic-tagger-2026-06-23.md` — report format convention
- `reports/multipv-validation/validate-multipv-budget-2026-06-30.md` — report format convention

---

## Metadata

**Confidence breakdown:**
- Gate signatures and constants: HIGH — read from source
- Script structure: HIGH — read from source
- Test coverage audit: HIGH — read all 468 lines of test file
- Live drain wiring approach: HIGH — read eval_drain.py call ordering (lines 2286-2329)
- Report convention: HIGH — read actual committed reports

**Research date:** 2026-06-30
**Valid until:** 2026-09-30 (stable Python codebase; gate constants provisional until Phase 144)
