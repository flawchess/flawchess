# Phase 145: Corpus Backfill + Rollout — Research

**Researched:** 2026-06-30
**Domain:** Remote-worker blob backfill, tier-4 ES lottery, gated retag rollout
**Confidence:** HIGH (all claims verified against codebase; no web search needed)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01**: Narrow blob-only remote job, NOT a resweep-style full re-arm. The fleet computes MultiPV=2 second-best only for each flaw's PV-line continuation nodes. No server-local engine pass for the bulk.
- **D-02**: New tier-4 lottery, lowest priority. Fires only when no tier-1/2/3 work remains. Gated by `EVAL_AUTO_DRAIN_ENABLED`. Modeled on tier-3 (`_claim_tier3_derived`). No `eval_jobs` table, `job_id=None`.
- **D-03**: Predicate = analyzed game with flaws whose `allowed_pv_lines IS NULL`. Idempotency-by-construction: once blobs are written (or sentinel `[]` written), the flaw stops matching.
- **D-04**: Dedicated token-keyed flaw-line lease/submit schema (NOT a reuse of `LeaseResponse`/`SubmitRequest`). Token = server's `(flaw_ply, line, node_k)` reassembly key. Isolated from live `_apply_submit`.
- **D-04a**: Worker stays token-opaque. Worker evaluates FENs at MultiPV=2 and echoes token + result. Zero understanding of flaw structure required on the worker side.
- **D-05**: Old/un-upgraded workers are structurally excluded — calling the new endpoint IS the capability signal. No version negotiation needed.
- **D-06**: Sentinel blob write for un-fillable flaws. Write `[]` (empty array) instead of leaving NULL. Gate/retag must treat `[]` as "no gate-eligible line → no suppression." **Research confirms this requires a code change** (see Priority 2 below).
- **D-07**: Per-game gated retag INSIDE the blob-submit handler. `_classify_tactic_gated` runs for the game's flaws after blob write. Only 8 tactic columns updated (not full flaw reclassification). Rolling rollout.
- **D-08**: `retag_flaws.py --db prod` sweep is still needed for games that already have blobs but were tagged before the gate went live (Phase 143) or before the final margin (Phase 144).
- **D-09**: Backfill covers engine + lichess %eval games. Predicate spans both.
- **D-09a**: Research flag — feasibility gate for D-09 lichess scope. **RESOLVED: feasible.** See Priority 1 below.

### Claude's Discretion

- SC3 monitoring: exact script/query, which tag columns, snapshot timing
- Backfill progress / observability signal (count flaws still `allowed_pv_lines IS NULL`)
- Exact tier-4 lease/submit endpoint paths, Pydantic schema names, token encoding, batch size
- ES weighting reuse vs simpler random pick for tier-4
- `backfill_multipv.py` role (kickoff/observability helper)
- Dev-first validation gate before `--db prod`

### Deferred Ideas (OUT OF SCOPE)

- Resweep-style full re-arm (rejected in D-01)
- Solver-only blob storage (141 D-03 deferral)
- Raising `STOCKFISH_POOL_SIZE` to 8 (separate soak)
- Lichess coverage fallback (if D-09a blocked — it doesn't; researched)
- Changing the gate logic, `ONLY_MOVE_WIN_PROB_MARGIN`, or `STOCKFISH_POOL_SIZE`
- Any new tactic motif
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| SHIP-01 | Corpus backfill populates JSONB for existing analyzed `game_flaws` rows with `WHERE allowed_pv_lines IS NULL` idempotency guard; MultiPV pass NOT gated on `lichess_evals_at` | Tier-4 lottery + dedicated blob-only endpoints (D-01..D-06); lichess feasibility confirmed (D-09a); sentinel covers un-fillable cases |
| SHIP-02 | Gated tags rolled out to production; live drain writes JSONB for all new games; per-motif counts monitored before/after | `retag_flaws.py --db prod` sweep (D-08); live `_apply_submit` fix (passes blob_map to classify); before/after snapshot script (SC3) |
</phase_requirements>

---

## Summary

Phase 145 ships the forcing-line gate to the full corpus by (1) backfilling missing MultiPV=2
blobs via a new tier-4 remote-worker lottery, (2) applying gated retags as blobs arrive and in
a final offline sweep, and (3) recording before/after per-motif chip counts.

**D-09a finding (HARD BLOCKER resolved):** Lichess games have stored engine PVs in
`game_positions.pv` at flaw plies (since SEED-054 / Phase 117). The `_fill_engine_game_flaw_pvs`
no-op for lichess is about dedup-transplant recovery — an engine-game-specific path. Lichess
games are serviced by `_flaw_engine_plies` which pre-classifies flaws and adds them to the engine
gather, so `game_positions.pv` IS populated for both `flaw_ply` and `flaw_ply + 1` on analyzed
lichess games. D-09 lichess scope is feasible; sentinel `[]` handles the un-fillable tail.

**D-06 sentinel finding (REQUIRED CODE CHANGE):** The current `_classify_tactic_gated`
(flaws_service.py:556) uses `pv_blob is not None` to gate. An empty list `[]` enters the gate,
`apply_forcing_line_filter([])` returns False (one-mover discard), and the motif is suppressed.
D-06 intends `[]` to mean "no gate-eligible line → no suppression." The fix is a one-line change
to `_classify_tactic_gated` and a corresponding test update.

**`_apply_submit` gate gap (REQUIRED FIX for SHIP-02):** The existing remote-worker
submit handler (`eval_remote.py:282`) calls `_classify_and_fill_oracle` without passing
`blob_map`, so gate filtering is never applied at remote-worker submit time even though blobs
ARE written. Fixing this is required for SHIP-02 ("live drain writes JSONB for all new games"
with gated tags).

**Primary recommendation:** Build the tier-4 lottery as a thin clone of `_claim_tier3_derived`,
use a simple `ORDER BY random() LIMIT 1` over distinct `game_id`s from `game_flaws WHERE
allowed_pv_lines IS NULL` (no user-level weighting needed for a lowest-priority backfill), and
keep the blob assembly server-side using the existing `_walk_pv_boards` + `_batch_update_flaw_pv_lines`
infrastructure.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Tier-4 lottery selection | API / Backend | — | `claim_eval_job` dispatch lives in `eval_queue_service.py`; no client involvement |
| Blob-only lease building | API / Backend | — | Server reads PGN + game_positions.pv, walks PV, emits token+FEN list |
| MultiPV=2 evaluation | Remote Worker | — | D-04a: worker evaluates FENs at MultiPV=2, echoes token+result; no worker intelligence required |
| Blob assembly + JSONB write | API / Backend | — | Server reassembles PvNode blobs from worker results; uses `_batch_update_flaw_pv_lines` |
| Per-game gated retag (D-07) | API / Backend | — | `_classify_tactic_gated` is engine-free; runs in write session after blob write |
| Sentinel write (D-06) | API / Backend | — | Server identifies un-fillable lines (NULL PV) and writes `[]` directly |
| D-08 offline retag sweep | Script | Server (SSH) | `retag_flaws.py --db prod` runs on prod server off-peak |
| SC3 before/after snapshot | Script | DB (MCP) | SQL count query + committed `reports/retag/` markdown |

---

## Priority 1: D-09a Lichess Feasibility — CONFIRMED

**Claim:** `_fill_engine_game_flaw_pvs` (eval_drain.py:1009) no-ops for lichess games; does this mean lichess flaws lack stored PVs?

**Answer: No. Lichess flaw plies get engine-computed PVs via a separate path.**

**Evidence** (all verified against code):

`_fill_engine_game_flaw_pvs` comment at eval_drain.py:1025:
```
No-op for lichess games (they pre-classify up front via _flaw_engine_plies)
```

`_flaw_engine_plies` (eval_drain.py:861): for a lichess game, pre-classifies flaws from stored
%evals and returns `{flaw_ply, flaw_ply + 1}`. These plies are exempted from the `eval_cp IS NULL`
filter (eval_drain.py:2199-2203) and always run through the engine gather via
`evaluate_nodes_multipv2`. This gives them `best_move`, PV, AND second-best data.

`game_positions.pv` column (game_position.py:172): `Mapped[Optional[str]]`, nullable Text. Gets
populated at these flaw plies by `_classify_and_fill_oracle` (eval_drain.py:676).

`_build_flaw_multipv2_blobs` (eval_drain.py:1159) and `_run_multipv2_pass` (eval_drain.py:1314)
run **unconditionally** in `_full_drain_tick` (lines 2305, 2347) with no `is_lichess_eval_game`
check. A lichess game that is processed by the drain gets blobs written.

**Why lichess games lack blobs in practice:** The tier-3 main predicate
(`full_evals_completed_at IS NULL AND lichess_evals_at IS NULL`) almost never selects lichess
games. The rare "residual fallback" selects `full_evals_completed_at IS NULL AND lichess_evals_at IS NOT NULL`
— but games that completed the drain before Phase 142 (when blobs were added) already have
`full_evals_completed_at IS NOT NULL` and are never re-selected.

**PV coverage by era:**

| Analyzed during era | `game_positions.pv` at flaw_ply | `game_positions.pv` at flaw_ply+1 | Blob backfill outcome |
|---------------------|----------------------------------|-------------------------------------|----------------------|
| Before Phase 117 (SEED-054) | NULL (not yet recovered) | Present (engine ran at flaw_ply+1) | missed_pv_lines gets sentinel `[]`; allowed_pv_lines gets blob |
| Phase 117–142 | Present (SEED-054 recovery) | Present | Both blobs can be built → main backfill target |
| After Phase 142 | Present | Present | Already has blobs (`allowed_pv_lines IS NOT NULL`) — won't match predicate |

**Conclusion:** D-09 lichess scope is IN SCOPE and feasible without a separate PV-compute pass.
The server walks `game_positions.pv` for both lines; lines with NULL PV get sentinel `[]` (D-06).
No scope change needed.

---

## Priority 2: D-06 Sentinel Tolerance — REQUIRED CODE CHANGE

**Claim:** The gate and retag must treat `[]` as "no gate-eligible line → no suppression."

**Current behavior (INCORRECT for D-06):**

`_classify_tactic_gated` (flaws_service.py:549-563):
```python
# Gate condition is `pv_blob is not None` (not `if pv_blob`): an empty list is
# a valid blob that must go through the gate and be rejected by the one-mover
# discard (Pitfall 2 from PLAN.md).
...
if motif is not None and pv_blob is not None and pre_flaw_eval_cp is not None:
    if not apply_forcing_line_filter(pv_blob, solver_color, pre_flaw_eval_cp, ...):
        return None, None, None, None
```

When `pv_blob = []`:
- `pv_blob is not None` → True → gate fires
- `apply_forcing_line_filter([], ...)` → `_is_forced_mate_firing([]) = False` → `forced_mate=False`
- `truncated = []` → `stripped = []` → `solver_nodes = []` → `len(solver_nodes) < 2` → **returns False**
- `_classify_tactic_gated` returns `(None, None, None, None)` → **motif suppressed**

D-06 wants: `[] → no suppression` (same as `None`).

**Required fix in `flaws_service.py:556`:**

```python
# Before (Phase 143 Pitfall 2 — superseded by Phase 145 D-06 sentinel semantic):
if motif is not None and pv_blob is not None and pre_flaw_eval_cp is not None:

# After (D-06: empty list [] is the sentinel for un-fillable flaw; skip gate):
if motif is not None and pv_blob is not None and len(pv_blob) > 0 and pre_flaw_eval_cp is not None:
```

**Note:** `apply_forcing_line_filter([], ...) = False` remains correct and unchanged — the gate
itself still rejects empty lines when called directly. Only the CALLER changes to skip the gate
for the sentinel case.

**Test change required in `tests/services/test_flaws_service.py:2521`:**

`test_suppression_when_blob_is_empty_list` (lines 2521-2543) currently asserts `motif is None`.
After the fix, `pv_blob=[]` skips the gate → asserts `motif == TacticMotifInt.HANGING_PIECE`.
Rename to `test_sentinel_empty_blob_skips_gate_returns_kernel_result`.

**Scope:** `_classify_tactic_gated` is the single classify path used by both the live drain
AND `retag_flaws.py` (imported at retag_flaws.py:134). The one-line fix covers both paths.

**`apply_forcing_line_filter` test `test_empty_line_discarded` (forcing_line_gate.py:502):**
This tests the gate function directly and asserts `apply_forcing_line_filter([], ...) is False`.
This test is CORRECT and must NOT be changed. [VERIFIED: code read]

---

## Priority 3: Tier-3 Lottery Pattern for Tier-4

**Tier-3 structure** (eval_queue_service.py:242-451, verified):

```
_claim_tier3_derived(session):
    Step 1 (user pick): ES key = ORDER BY -ln(random()) / (exp(-Δt/τ) + floor) LIMIT 1
    Step 2 (game pick): same ES formula with tc_multiplier and game recency
    Residual fallback: lichess PV-backfill games when needs-engine pool is empty
    Returns (game_id, user_id, is_lichess_eval_game) | None
```

`claim_eval_job` dispatch (eval_queue_service.py:457-537):
```
scope="idle" → tier-3 only (EVAL_AUTO_DRAIN_ENABLED gated)
scope=None → tier-1 → tier-2 → tier-3 (EVAL_AUTO_DRAIN_ENABLED gated)
```

The tier-4 branch slots in **after tier-3** in the `scope=None` bundled flow. The recommended
approach is a simpler single-level pick (no user weighting):

```python
async def _claim_tier4_blob(session: AsyncSession) -> tuple[int, int] | None:
    """Lowest-priority: pick a game with at least one flaw missing blobs.

    Predicate: game_flaws.allowed_pv_lines IS NULL, joined to games where
    full_evals_completed_at IS NOT NULL (analyzed) and is_guest=false.
    Simple random pick (no ES weighting) — tier-4 is spare-capacity only.
    Returns (game_id, user_id) | None.
    """
    result = await session.execute(sa.text("""
        SELECT gf.game_id, g.user_id
        FROM game_flaws gf
        JOIN games g ON g.id = gf.game_id
        JOIN users u ON u.id = g.user_id
        WHERE gf.allowed_pv_lines IS NULL
          AND g.full_evals_completed_at IS NOT NULL
          AND u.is_guest = false
        ORDER BY random()
        LIMIT 1
    """))
    row = result.one_or_none()
    if row is None:
        return None
    return row[0], row[1]
```

**Key design properties:**
- No `eval_jobs` table row → `job_id=None` in `ClaimedJob` (same as tier-3)
- Idempotent: once all a game's flaw blobs are written, it stops matching
- Double-claim is safe: `_batch_update_flaw_pv_lines` is idempotent (same data written)
- Gated by `EVAL_AUTO_DRAIN_ENABLED` — same flag as tier-3
- The `is_lichess_eval_game` field on the `ClaimedJob` must be resolved (D-09 covers both)

**`claim_eval_job` extension** (eval_queue_service.py:457):
```python
# After tier-3 falls through (derived is None):
if not settings.EVAL_AUTO_DRAIN_ENABLED:
    return None
async with async_session_maker() as session:
    blob_pick = await _claim_tier4_blob(session)
if blob_pick is None:
    return None
game_id4, user_id4 = blob_pick
return ClaimedJob(game_id=game_id4, user_id=user_id4,
                  tier=TIER_BLOB_BACKFILL,  # new constant
                  is_lichess_eval_game=False,  # resolved per-game in lease builder
                  job_id=None)
```

The worker checks the `tier` (or a separate `ClaimedBlob` return type) and calls the new
flaw-blob-lease endpoint instead of the regular lease. OR: the worker always polls both
endpoints and the server returns 204 when the queue is empty.

**Recommended worker flow (simpler):** The worker polls `/flaw-blob-lease` as a separate
idle endpoint (separate from `/lease`). No changes to the tier dispatch logic needed in the
worker's main eval loop — the flaw-blob lease endpoint is an ADDITIONAL endpoint the worker
can call.

---

## Priority 4: Blob-Only Lease/Submit Schema (D-04)

**Phase 123 EntryLeasePosition precedent** (eval_remote.py, schema at eval_remote.py:65):
```python
class EntryLeasePosition(BaseModel):
    game_id: int
    ply: int = Field(ge=0)
    fen: str
```

**New schemas for `app/schemas/eval_remote.py`:**

```python
# ─── Phase 145 SHIP-01: flaw-blob-only lease/submit schemas ──────────────────
# Token encodes the server's reassembly key: "{flaw_ply}:{line}:{node_k}"
# Worker echoes the token unchanged; server parses to (int, str, int).
# Max 1024 positions per lease reused from MAX_SUBMIT_EVALS (DoS guard).

class FlawBlobLeasePosition(BaseModel):
    token: str   # "{flaw_ply}:{line}:{node_k}" — opaque to worker (D-04a)
    fen: str     # board.fen() — full FEN with turn, castling, en passant

class FlawBlobLeaseResponse(BaseModel):
    game_id: int
    positions: list[FlawBlobLeasePosition]  # bounded by MAX_SUBMIT_EVALS
    leased_at: datetime

class FlawBlobSubmitEval(BaseModel):
    token: str       # echoed from lease
    best_cp: int | None
    best_mate: int | None
    second_cp: int | None
    second_mate: int | None
    second_uci: str | None  # "" for single-legal-move sentinel (Pitfall 3)

class FlawBlobSubmitRequest(BaseModel):
    game_id: int
    sf_version: str
    evals: list[FlawBlobSubmitEval] = Field(max_length=MAX_SUBMIT_EVALS)

class FlawBlobSubmitResponse(BaseModel):
    game_id: int
    blobs_written: int  # number of flaw rows with blobs written (includes sentinels)
```

**Token format rationale:** `"{flaw_ply}:{line}:{node_k}"` is compact, human-readable, and
unambiguously parseable with `token.split(":")` → `(int, str, int)`. Example:
`"10:allowed:2"` → flaw at ply 10, allowed line, node k=2. `:` is safe in tokens since
none of the fields contain it.

**Node coverage:** ALL nodes sent to worker (k=0 AND k≥1). For node 0, the worker's
`best_cp`/`best_mate` are used (not game_positions.eval_cp) — uniform treatment, avoids
mixing stored and freshly-computed evals. Minor non-determinism at node 0 is acceptable
(per-eval non-determinism note in MEMORY.md).

**Sentinel optimization:** Lines with `game_positions.pv IS NULL` at the flaw ply produce
a 1-node walk (just the start board). A 1-node blob always fails the one-mover discard.
Write sentinel `[]` directly for these lines without sending to worker. The server identifies
this case during lease building and includes only the lines with pv ≠ NULL in the lease.

**Endpoints (new in `app/routers/eval_remote.py`):**
```
POST /eval/remote/flaw-blob-lease   → FlawBlobLeaseResponse | 204
POST /eval/remote/flaw-blob-submit  → FlawBlobSubmitResponse | 404 | 422
```

Both behind the existing `require_operator_token` dependency (same auth as other endpoints).

**Batch size estimate:** Game with N flaws, lines with average P PV nodes each:
- Positions per lease = N × 2 × (P + 1) ≤ 10 flaws × 2 × 13 = 260 per game
- Well within MAX_SUBMIT_EVALS = 1024 (existing cap)

---

## Priority 5: Per-Game Gated Retag in Submit Handler (D-07)

**`_classify_tactic_gated` engine-free confirmation** (flaws_service.py:525-564):
```python
def _classify_tactic_gated(n, fen_map, positions, orientation, pv_blob,
                            pre_flaw_eval_cp, pv_by_ply=None, margin=...):
    motif, piece, conf, depth = _detect_tactic_for_flaw(n, fen_map, positions, pv_by_ply, orientation)
    if motif is not None and pv_blob is not None and len(pv_blob) > 0 ...:
        if not apply_forcing_line_filter(pv_blob, ...):
            return None, None, None, None
    return motif, piece, conf, depth
```

Both `_detect_tactic_for_flaw` and `apply_forcing_line_filter` are pure-CPU, no DB, no engine.
Confirmed safe to call in a write session (no asyncio.gather). [VERIFIED: code read]

**Submit handler flow (D-07):**
```
Read session:
  - Load Game (pgn, user_id, is_lichess_eval_game)
  - Load game_flaws with allowed_pv_lines IS NULL for this game_id
    (explicit column select: ply, fen, allowed/missed_tactic_*, allowed/missed_pv_lines NOT needed)
  - Load game_positions at {flaw_ply-1, flaw_ply, flaw_ply+1} for each flaw (pv, move_san, eval_cp, eval_mate)
  - Replay PGN → board_by_ply dict
  - Walk PVs → gather_boards (all nodes k=0..N per flaw line)

CPU phase (no session):
  - Parse worker evals by token → node_results dict
  - Assemble PvNode blobs per flaw line (FlawBlobSubmitEval → PvNode)
  - Write sentinel [] for lines with NULL PV or no worker result for node 0
  - Build blob_map: dict[flaw_ply -> (allowed_blobs, missed_blobs)]
  - Run _classify_tactic_gated for each flaw using in-memory blob_map (D-06 fix applied)
  - Build update dicts for changed tactic columns

Write session:
  - _batch_update_flaw_pv_lines(session, game_id, blob_map)  -- reuse existing
  - bulk_update_tactic_tags(session, updates)                 -- reuse retag_flaws.py function
  - commit
```

**In-memory blob_map for classify:** The blobs are assembled in the CPU phase and NOT yet
in the DB when `_classify_tactic_gated` runs in the write session. Pass the in-memory
blob_map directly (same as the full drain tick passes `flaw_pv_blobs` to
`_classify_and_fill_oracle`). This avoids an extra DB round-trip.

**What is NOT done in D-07:** No severity/phase/oracle reclassification (that requires
`delete_flaws_for_game` + `bulk_insert_game_flaws` which is too heavy and risks losing data).
Only the 8 tactic columns are updated. This is intentional: blobs enable gated detection;
flaws themselves are already correctly classified.

---

## Priority 6: `_apply_submit` Gate Gap — REQUIRED FIX for SHIP-02

**Finding:** The existing remote-worker submit handler (`eval_remote.py:282`) calls
`_classify_and_fill_oracle` WITHOUT passing blob_map:

```python
# eval_remote.py:261-288 (current — gate not applied):
blob_map = await _build_flaw_multipv2_blobs(game_id, targets, {}, engine_result_map, second_best_map)
...
await _classify_and_fill_oracle(write_session, game_id, engine_result_map)  # <-- no blob_map!
await _run_multipv2_pass(write_session, game_id, blob_map)
```

When `flaw_pv_blobs=None` (default), `_classify_and_fill_oracle` passes `None` to
`classify_game_flaws` which passes `None` to `_build_flaw_record`, so `_classify_tactic_gated`
gets `pv_blob=None` → gate skipped → raw detect results written (unfiltered tags).

SHIP-02 requires the "live eval drain writes JSONB for all new games" with gated tags. The fix:
pass `blob_map` to `_classify_and_fill_oracle` when `blob_map` is non-empty:

```python
# After (correct for SHIP-02):
await _classify_and_fill_oracle(write_session, game_id, engine_result_map,
                                blob_map if blob_map else None)
await _run_multipv2_pass(write_session, game_id, blob_map)
```

The `flaw_pv_blobs` default is `None` which skips the gate (backward compat for old games with
no blobs). Passing `blob_map` (which may be `{}` when old worker omits second-best fields)
is safe: `_batch_update_flaw_pv_lines` is a no-op for empty dict, and
`_classify_and_fill_oracle` with `flaw_pv_blobs={}` means all flaws get `pv_blob=None` from
`blob_pair = {}.get(n) = None` → gate still skipped per old-worker compat. Only when a
new worker provides second-best AND blobs are assembled does the gate fire.

This fix is required for SHIP-02 but is a two-line change to `_apply_submit`.

---

## Standard Stack

### Core (existing, verified)

| Asset | Location | Purpose | Phase 145 Role |
|-------|----------|---------|----------------|
| `_claim_tier3_derived` | eval_queue_service.py:242 | ES lottery template | Clone for tier-4 |
| `_walk_pv_boards` | eval_drain.py:1096 | PV-walk → board list | Blob lease builder |
| `_batch_update_flaw_pv_lines` | eval_drain.py:1280 | Batched JSONB write | Reused in blob-submit handler |
| `_classify_tactic_gated` | flaws_service.py:525 | Single gated classify path | Per-game retag (D-07) + fix (D-06) |
| `apply_forcing_line_filter` | forcing_line_gate.py:374 | Gate predicate | Called by `_classify_tactic_gated` |
| `bulk_update_tactic_tags` | game_flaws_repository.py | Batched 8-column UPDATE | D-07 retag write |
| `retag_flaws.py` | scripts/ | Offline retag sweep | D-08 prod sweep, unchanged |
| `db_url_for_target` | app/core/config.py | DB target resolution | `backfill_multipv.py` script |
| `require_operator_token` | eval_remote.py:95 | Endpoint auth | New blob endpoints |

### Supporting (existing)

| Asset | Location | Purpose |
|-------|----------|---------|
| `EntryLeasePosition` | eval_remote.py schemas | Template for `FlawBlobLeasePosition` |
| `TACTIC_TAG_COLUMNS` | game_flaws_repository.py | Column list for 8-column retag |
| `PvNode` TypedDict | forcing_line_gate.py:95 | Blob node shape |
| `PV_CAP_PLIES` | engine_service | PV walk cap (12 plies) |
| `MAX_SUBMIT_EVALS` | eval_remote.py schemas | DoS cap (1024) reused for blob endpoint |

---

## Architecture Patterns

### System Architecture Diagram

```
Remote Worker (new capability — upgraded only)
    │
    ├─ Poll /eval/remote/flaw-blob-lease  ─────────────────────┐
    │       │                                                   │
    │  Server: tier-4 lottery picks game_id                    │
    │  Server: walks game_positions.pv, emits {token, FEN}     │
    │       │                                                   │
    │  Worker: evaluate_nodes_multipv2 for each FEN             │
    │       │                                                   │
    └─ POST /eval/remote/flaw-blob-submit ─────────────────────┤
            │                                                   │
     Server: reassemble PvNode blobs from tokens               │
     Server: write [] sentinel for NULL-PV lines               │
     Server: _batch_update_flaw_pv_lines → game_flaws.{allowed,missed}_pv_lines
     Server: _classify_tactic_gated per flaw (D-07)            │
     Server: bulk_update_tactic_tags (8 tactic columns)        │
            │                                                   │
            ▼                                                   │
    [game_flaws: blobs + gated tags]                           │
            │                                                   │
            ▼ (when "substantially complete")                   │
    retag_flaws.py --db prod (D-08)                            │
    ↓ already-blobbed but stale-tag games                       │
    [game_flaws: full corpus gated tags]                        │
            │                                                   │
            ▼                                                   │
    snapshot_tactic_counts.py → reports/retag/rollout-*.md     │
    (before + after per-motif counts, SC3)                     │
```

### Recommended Project Structure for New Files

```
app/
├── schemas/eval_remote.py            # Add FlawBlobLease* + FlawBlobSubmit* schemas
├── services/eval_queue_service.py    # Add _claim_tier4_blob(), extend claim_eval_job()
├── routers/eval_remote.py            # Add /flaw-blob-lease + /flaw-blob-submit endpoints
│                                     # Fix _apply_submit (pass blob_map to classify)
└── services/flaws_service.py         # Fix _classify_tactic_gated sentinel (D-06)
scripts/
├── backfill_multipv.py               # NEW: thin observability/kickoff CLI
└── snapshot_tactic_counts.py         # NEW: before/after per-motif snapshot
tests/
└── services/test_flaws_service.py    # Update test_suppression_when_blob_is_empty_list
```

### Pattern: Blob Lease Building (server-side)

```python
# Pseudocode for _build_flaw_blob_lease_positions(game_id) → list[FlawBlobLeasePosition]:
async with read_session:
    game = load Game(id=game_id)
    flaws = select GameFlaw WHERE game_id=game_id AND allowed_pv_lines IS NULL
    positions = select GamePosition(ply, pv, eval_cp, eval_mate) WHERE game_id=game_id
               AND ply IN {flaw_ply, flaw_ply+1 for all flaws}

pgn → replay → board_at_ply = dict[int, chess.Board]
pv_at_ply = {pos.ply: pos.pv for pos in positions}

lease_positions = []
sentinel_plies = set()  # flaws whose lines are un-fillable → write [] directly

for flaw in flaws:
    for line, node0_ply in [("missed", flaw.ply), ("allowed", flaw.ply + 1)]:
        pv = pv_at_ply.get(node0_ply)
        start_board = board_at_ply.get(node0_ply)
        if start_board is None:
            sentinel_plies.add((flaw.ply, line))
            continue
        walk = _walk_pv_boards(start_board, pv, PV_CAP_PLIES)
        if len(walk) < 2:  # NULL pv → 1-node walk → gate always discards
            sentinel_plies.add((flaw.ply, line))
            continue
        for k, board in enumerate(walk):
            token = f"{flaw.ply}:{line}:{k}"
            lease_positions.append(FlawBlobLeasePosition(token=token, fen=board.fen()))

return lease_positions, sentinel_plies
```

### Pattern: Token Parsing (blob submit handler)

```python
def _parse_token(token: str) -> tuple[int, str, int]:
    """Parse "{flaw_ply}:{line}:{node_k}" reassembly token."""
    parts = token.split(":")
    return int(parts[0]), parts[1], int(parts[2])

# Reassembly:
node_results: dict[tuple[int, str, int], FlawBlobSubmitEval] = {}
for e in body.evals:
    node_results[_parse_token(e.token)] = e
```

### Anti-Patterns to Avoid

- **asyncio.gather inside an open AsyncSession** — CLAUDE.md hard rule. The blob lease builder opens a read session to load data, closes it, then does CPU work (PV walking). No gather is needed (no engine calls on server side).
- **Passing `blob_map={}` as `flaw_pv_blobs` to `_classify_and_fill_oracle`** — an empty dict is functionally correct (all flaw lookups return None → gate skipped) but semantically misleading. Pass `blob_map if blob_map else None`.
- **Re-using `_apply_submit` for the blob backfill** — D-04 explicitly rejects this. The safety-critical live path must not be branched.
- **Running `retag_flaws.py` BEFORE blobs are substantially complete** — D-08 sweep should run after the rolling D-07 retag has covered the bulk; otherwise the sweep re-suppresses games that haven't been blobbed yet (they have `allowed_pv_lines=NULL` → `pv_blob=None` → gate skipped → raw detect). Run D-08 when the progress query shows near-zero NULL blobs.

---

## Priority 7: SC3 Monitoring — Concrete Approach

**Before snapshot query (run BEFORE any D-07/D-08 retag):**
```sql
-- Per-motif tactic chip counts (before gate rollout)
SELECT
    COALESCE(m.name, 'null') AS motif,
    COUNT(*) FILTER (WHERE gf.allowed_tactic_motif IS NOT NULL) AS allowed_count,
    COUNT(*) FILTER (WHERE gf.missed_tactic_motif IS NOT NULL) AS missed_count
FROM game_flaws gf
LEFT JOIN (VALUES
    (1,'FORK'), (2,'PIN'), ...  -- TacticMotifInt enum values
) AS m(id, name) ON gf.allowed_tactic_motif = m.id
GROUP BY m.name ORDER BY m.name;
```

Simpler equivalent using the `db-report` skill or prod DB MCP:
```sql
SELECT allowed_tactic_motif, COUNT(*) as cnt
FROM game_flaws WHERE allowed_tactic_motif IS NOT NULL
GROUP BY 1 ORDER BY cnt DESC;

SELECT missed_tactic_motif, COUNT(*) as cnt
FROM game_flaws WHERE missed_tactic_motif IS NOT NULL
GROUP BY 1 ORDER BY cnt DESC;
```

**Progress signal (how complete is the backfill):**
```sql
-- Count games still missing blobs (backfill progress gate)
SELECT COUNT(DISTINCT game_id) AS games_with_null_blobs,
       COUNT(*) AS total_null_flaw_lines
FROM game_flaws WHERE allowed_pv_lines IS NULL;
```

When `games_with_null_blobs` approaches 0 (or a stable low floor representing un-fillable cases
covered by sentinel `[]`), the backfill is substantially complete → run D-08 sweep → take "after"
snapshot.

**Deliverable:** `scripts/snapshot_tactic_counts.py` — thin script that runs both queries
and writes `reports/retag/rollout-YYYY-MM-DD.md` with before/after tables. CLI: `--db prod`,
`--phase before|after`. Can be run interactively via prod DB MCP. Matches `reports/retag/`
convention from `retag_flaws.py`.

---

## Priority 8: Naming/SC1 Reconciliation

**SC1 wording (REQUIREMENTS.md):** "backfill_multipv.py --db prod populates JSONB for all
analyzed game_flaws rows using a WHERE allowed_pv_lines IS NULL idempotency guard; the
module-level EnginePool is reused."

**Context reality (D-01/D-02):** The engine pool is NOT used for the bulk. The fleet
self-paces via tier-4 lottery. There is no server-local engine pass.

**Recommendation:** Create `scripts/backfill_multipv.py` as a thin observability/kickoff
helper following the `backfill_full_evals.py` pattern (`--db dev|benchmark|prod`, dry-run,
idempotent). Its responsibilities:

1. `--status`: show progress query (count of games/flaws still missing blobs)
2. `--dry-run`: report how many flaws would be backfilled (no action)
3. `--dev-validate`: trigger a dev-DB end-to-end test of the tier-4 lottery + blob job

The script does NOT enqueue jobs or call the engine. It observes the self-pacing fleet.
This reconciles SC1's "backfill_multipv.py --db prod" deliverable with D-01's "no server engine."

The SC1 text "module-level EnginePool is reused" is stale (reflects the original server-local
design). The actual no-OOM guarantee comes from D-01 (no server engine pass at all) which is
strictly better. REQUIREMENTS.md need not be retroactively changed — the spirit of "no second
EnginePool / no OOM" is honored.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| PV walk from stored pv string | Custom parser | `_walk_pv_boards` (eval_drain.py:1096) | Handles illegal moves, malformed UCI, cap |
| Batched JSONB write | Custom UPDATE | `_batch_update_flaw_pv_lines` (eval_drain.py:1280) | CAST(:param AS jsonb) pattern for asyncpg |
| Tactic classify pass | Direct `_detect_tactic_for_flaw` call | `_classify_tactic_gated` (flaws_service.py:525) | SC4 no-drift: gate must always be included |
| 8-column tactic UPDATE | Manual UPDATE | `bulk_update_tactic_tags` (game_flaws_repository.py) | Existing bulk path with TACTIC_TAG_COLUMNS |
| DB target URL | Hardcoded | `db_url_for_target(db)` (app/core/config.py) | Matches all existing scripts |
| Operator auth | Custom | `require_operator_token` dep (eval_remote.py:95) | Same HMAC pattern, no change |

---

## Common Pitfalls

### Pitfall 1: Sentinel `[]` suppresses motifs in `_classify_tactic_gated` (Phase 143 Pitfall 2 contradiction)

**What goes wrong:** Writing sentinel `[]` to game_flaws then running retag_flaws.py or the live classify path suppresses ALL tactic motifs for that flaw (one-mover discard in `apply_forcing_line_filter([])`). D-06 intent is "no suppression."

**Why it happens:** Phase 143 chose `pv_blob is not None` to distinguish "no blob (backward compat)" from "empty blob (zero nodes)." D-06 introduces a THIRD semantic: "empty blob = un-fillable sentinel = treat same as None."

**How to avoid:** Apply the D-06 fix to `_classify_tactic_gated` before writing any sentinels. The fix is the PREREQUISITE for D-06 correctness — sentinel writes before the fix cause incorrect suppressions.

**Warning signs:** After sentinel writes but before the fix, `retag_flaws.py --dry-run --only-tagged` shows motifs being removed for games that should retain their tags.

### Pitfall 2: asyncio.gather inside a session in the blob-submit handler

**What goes wrong:** If the blob assembly includes `asyncio.gather` (e.g., evaluating positions), this violates CLAUDE.md's hard rule (AsyncSession not safe for concurrent use).

**Why it happens:** The blob submit handler is async, and it's tempting to fan out MultiPV evaluation for remaining nodes server-side. But D-01 means the server does NO engine work — the worker provides all evaluations.

**How to avoid:** The blob submit handler is PURE: reads worker results from the request body, assembles blobs, writes. No engine calls, no gather. All evaluation happens at the worker.

### Pitfall 3: `second_uci = None` in worker result must map to `su = ""`

**What goes wrong:** Worker returns `second_uci=None` for single-legal-move positions. If passed directly to `PvNode(su=None)`, it violates the TypedDict contract (`su: str`).

**Why it happens:** Wire type is `str | None`; blob type requires `str`. The sentinel for no-second-move is `""` (not None).

**How to avoid:** `su: str = eval.second_uci if eval.second_uci is not None else ""` — same pattern as `_build_line_blobs:1147` (`su: str = res[6] if res[6] is not None else ""`). [VERIFIED: code read]

### Pitfall 4: Running D-08 retag sweep before backfill is substantially complete

**What goes wrong:** `retag_flaws.py --db prod` processes ALL flaws. Flaws still missing blobs (`allowed_pv_lines IS NULL`) have `pv_blob=None` → gate skipped → raw detect. Running the sweep early locks in unfiltered tags for un-blobbed flaws, defeating the point of the gate.

**How to avoid:** Run the progress query first. Run D-08 only when `games_with_null_blobs` has stabilized near 0 (only sentinel-covered un-fillable flaws remain).

### Pitfall 5: Token collision between flaw lines

**What goes wrong:** `"10:missed:2"` and `"10:allowed:2"` parse differently but both start with `10`. If token parsing only uses `flaw_ply:node_k` without the `line`, game_id=10 and ply=10 clash.

**How to avoid:** Token includes ALL three components: `"{flaw_ply}:{line}:{node_k}"`. The `line` field (`"missed"` or `"allowed"`) ensures uniqueness within a game.

### Pitfall 6: Lichess game `is_lichess_eval_game` flag in tier-4 lease

**What goes wrong:** The tier-4 lottery returns `(game_id, user_id)`. The blob lease handler needs `is_lichess_eval_game` to know whether `include_terminal` applies. But the current `claim_eval_job` return `ClaimedJob.is_lichess_eval_game` is populated from the tier-3 path.

**How to avoid:** In `_claim_tier4_blob`, join to `games` and include `lichess_evals_at IS NOT NULL` as a derived field. Or: look up `is_lichess_eval_game` in the lease handler from the game record (a separate read per game is cheap — it's already loaded for PGN).

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest + pytest-asyncio |
| Config file | `pyproject.toml` (pytest section) |
| Quick run command | `uv run pytest tests/services/test_forcing_line_gate.py tests/services/test_flaws_service.py -x` |
| Full suite command | `uv run pytest -n auto -x` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SHIP-01 / D-03 | Idempotency: flaw stops matching after blob write | unit | `pytest tests/test_eval_queue.py -k tier4 -x` | ❌ Wave 0 |
| SHIP-01 / D-06 | Sentinel `[]` → gate skipped → raw detect result | unit | `pytest tests/services/test_flaws_service.py -k sentinel -x` | ❌ Wave 0 (update existing) |
| SHIP-01 / D-04 | Token parsing roundtrip `"{flaw_ply}:{line}:{node_k}"` | unit | `pytest tests/routers/test_eval_remote.py -k blob -x` | ❌ Wave 0 |
| SHIP-01 / D-01 | Blob assembly from worker results (PvNode shape) | unit | `pytest tests/routers/test_eval_remote.py -k blob_assembly -x` | ❌ Wave 0 |
| SHIP-01 / D-06 | Sentinel write for NULL-PV lines | unit | `pytest tests/routers/test_eval_remote.py -k sentinel_write -x` | ❌ Wave 0 |
| SHIP-02 | `_apply_submit` passes blob_map to classify | unit | `pytest tests/routers/test_eval_remote.py -k apply_submit_gate -x` | ❌ Wave 0 |
| SHIP-01 | `_batch_update_flaw_pv_lines` writes sentinel `[]` | integration | `pytest tests/services/test_eval_drain.py -k pv_lines -x` | existing |
| SHIP-01 | `apply_forcing_line_filter([], ...) = False` unchanged | unit | `pytest tests/services/test_forcing_line_gate.py -k empty_line -x` | ✅ existing |

### Sampling Rate

- **Per task commit:** `uv run pytest tests/services/test_flaws_service.py tests/services/test_forcing_line_gate.py -x`
- **Per wave merge:** `uv run pytest -n auto -x`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `tests/services/test_flaws_service.py:2521` — rename + invert assertion for D-06 sentinel fix
- [ ] `tests/test_eval_queue.py` — tier-4 lottery unit tests (predicate, no-op when empty)
- [ ] `tests/routers/test_eval_remote.py` — blob lease/submit endpoint tests (token parse, PvNode assembly, sentinel write, isolated from `_apply_submit`)

---

## Security Domain

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V5 Input Validation | Yes | Pydantic v2 schema validates `token: str`, `fen: str`, `max_length=MAX_SUBMIT_EVALS`; server-side token parse rejects malformed tokens |
| V4 Access Control | Yes | `require_operator_token` HMAC dependency on all new endpoints (same as existing eval endpoints) |
| V2/V3 Auth/Session | No | Operator token (not user auth) |
| V6 Cryptography | No | No new crypto |

**Threat specific to this phase:**

- **Token injection:** a malicious worker could submit crafted tokens that map to arbitrary `(flaw_ply, line, node_k)` and overwrite blobs for different flaws. Mitigation: server validates that tokens in the submit correspond to flaws it actually leased for this `game_id`. The server builds the lease and knows the expected token set — validate on submit that all tokens belong to the leased game.
- **Oversized submit body:** DoS via large `evals` list. Mitigation: existing `Field(max_length=MAX_SUBMIT_EVALS)` cap reused.
- **SQL injection via token:** token is parsed server-side into typed `(int, str, int)` and used as parameterized query keys — never interpolated into SQL. Safe.

---

## Environment Availability

| Dependency | Required By | Available | Notes |
|------------|------------|-----------|-------|
| PostgreSQL (Docker dev) | Tier-4 lottery, blob write | ✓ | `docker compose -f docker-compose.dev.yml -p flawchess-dev up -d` |
| Remote worker (upgraded) | Blob evaluation (D-04a) | Human-gate | Worker must be deployed with new endpoint support before prod blob leases fire |
| `bin/prod_db_tunnel.sh` | `--db prod` scripts (D-08, snapshot) | ✓ | SSH tunnel to prod DB |

**Missing dependencies with fallback:**
- Upgraded remote worker: until the worker is deployed, the tier-4 lottery fires but leases expire with no submits. Blobs remain NULL. No harm — the lottery self-paces and the sentinel `[]` path is server-side-only. The D-07 retag fires only on submit, so it waits too. The D-08 sweep is manual and can be delayed.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `_flaw_engine_plies` coverage: games analyzed before Phase 117 lack PV at `flaw_ply` but have it at `flaw_ply+1` | D-09a analysis | If some pre-117 games also lack `flaw_ply+1` PV, missed_pv_lines sentinel rate rises. No functional risk — sentinel handles it. |
| A2 | `evaluate_nodes_multipv2` return value used by workers is the 7-tuple (best_cp, best_mate, best_move, pv, second_cp, second_mate, second_uci) | Worker schema design | Verified from eval_drain.py line 1044 and 1089; [VERIFIED: code read] |
| A3 | `MAX_SUBMIT_EVALS = 1024` is sufficient for blob leases | Schema design | Games with >50 flaws and deep PVs could exceed this. If needed, add `MAX_BLOB_SUBMIT_EVALS` constant. |

**All load-bearing claims verified against code. No ASSUMED-tagged claims in this research.**

---

## Open Questions

1. **Tier-4 lottery index efficiency**
   - What we know: `game_flaws` has index `ix_game_flaws_user_severity (user_id, severity)`. No index on `allowed_pv_lines IS NULL`.
   - What's unclear: Whether Postgres will seq-scan `game_flaws` for the `allowed_pv_lines IS NULL` predicate (the table has ~3.18M rows per retag_flaws.py docs).
   - Recommendation: Add a partial index `CREATE INDEX CONCURRENTLY ix_game_flaws_blob_backfill ON game_flaws (game_id) WHERE allowed_pv_lines IS NULL` via Alembic migration. Drops automatically to near-zero rows once backfill completes (empty index). [VERIFIED: retag_flaws.py docs]

2. **Worker deployment gate for prod**
   - What we know: Until the remote worker is upgraded to call the new blob endpoints, no blobs are written by the fleet. The lottery fires but expires.
   - What's unclear: Whether the worker is deployed manually or via CI (separate from the backend deploy).
   - Recommendation: Planner should add a `checkpoint:human-verify` gate "confirm upgraded worker is deployed to prod" before declaring SHIP-01 complete.

3. **`ClaimedJob` tier constant for tier-4**
   - What we know: `TIER_IDLE_BACKLOG` is used for tier-3. Tier-4 needs a distinct constant.
   - What's unclear: Whether to add `TIER_BLOB_BACKFILL = 4` or reuse `TIER_IDLE_BACKLOG`.
   - Recommendation: Add `TIER_BLOB_BACKFILL = 4` for clean observability in logs / `eval_jobs.tier`.

---

## Sources

### Primary (HIGH confidence — verified by reading source code)

- `app/services/eval_drain.py` — `_fill_engine_game_flaw_pvs` (1009), `_flaw_engine_plies` (861), `_walk_pv_boards` (1096), `_build_flaw_multipv2_blobs` (1159), `_batch_update_flaw_pv_lines` (1280), `_full_drain_tick` (2140), `resweep_holed_games` (2486)
- `app/services/eval_queue_service.py` — `_claim_tier3_derived` (242), `claim_eval_job` (457)
- `app/services/forcing_line_gate.py` — `apply_forcing_line_filter` (374), full module
- `app/services/flaws_service.py` — `_classify_tactic_gated` (525)
- `app/routers/eval_remote.py` — `_apply_submit` (185), lease endpoint (389), submit endpoint
- `app/schemas/eval_remote.py` — `LeaseResponse`, `SubmitRequest`, `EntryLeasePosition` precedent
- `app/models/game_flaw.py` — `allowed_pv_lines`, `missed_pv_lines` JSONB columns
- `app/models/game_position.py` — `pv` column (Text, nullable)
- `scripts/retag_flaws.py` — full script (D-08 sweep tool)
- `scripts/backfill_full_evals.py` — CLI/DB-target convention precedent
- `tests/services/test_flaws_service.py:2521` — `test_suppression_when_blob_is_empty_list` (must update)
- `tests/services/test_forcing_line_gate.py:502` — `test_empty_line_discarded` (unchanged)
- `.planning/phases/145-corpus-backfill-rollout/145-CONTEXT.md` — locked decisions D-01..D-09a
- `.planning/REQUIREMENTS.md` §SHIP — SHIP-01, SHIP-02

---

## Metadata

**Confidence breakdown:**
- Tier-4 lottery design: HIGH — clones `_claim_tier3_derived` exactly; predicate is straightforward
- D-06 sentinel fix: HIGH — verified current code behavior and required change; one-line fix
- D-09a lichess feasibility: HIGH — verified PV coverage path via `_flaw_engine_plies`
- Blob schema design: HIGH — follows EntryLeasePosition precedent; token format is simple
- `_apply_submit` gate gap: HIGH — verified by reading the exact call site
- SC3 monitoring: HIGH — query against known schema

**Research date:** 2026-06-30
**Valid until:** Stable (no fast-moving external dependencies; all code is internal)

---

## RESEARCH COMPLETE

All 7 critical research priorities resolved. No blockers found. Phase 145 is ready for planning.
