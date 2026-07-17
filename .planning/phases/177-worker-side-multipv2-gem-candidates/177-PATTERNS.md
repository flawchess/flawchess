# Phase 177: Worker-side MultiPV-2 gem-candidate searches, protocol v2 - Pattern Map

**Mapped:** 2026-07-17
**Files analyzed:** 6 (all existing files, modified in place — no new top-level modules per RESEARCH.md's "Recommended Project Structure")
**Analogs found:** 6 / 6 (this phase edits files that already contain the closest possible analog — sibling code paths in the SAME file)

This phase is unusual for pattern-mapping purposes: RESEARCH.md already identified that every new behavior is an *extension* of an existing sibling code path in the same file/module, not a new file needing an external analog. The "analog" for each touched file is therefore the neighboring endpoint/function pair already in that file (flaw-blob lease/submit as the template for the new tier-4b lease/submit; the fresh-lane atomic-submit's own dormant `second_best_map=None` argument as the template for wiring it non-None).

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog (same or sibling file) | Match Quality |
|---|---|---|---|---|
| `app/schemas/eval_remote.py` (extend) | model/schema | request-response | `FlawBlobLeasePosition`/`FlawBlobLeaseResponse`/`FlawBlobSubmitEval`/`FlawBlobSubmitRequest`/`FlawBlobSubmitResponse` (lines 85-127) | exact |
| `app/routers/eval_remote.py` (extend) | controller/route | request-response | `flaw_blob_lease` (723-806) + `_apply_flaw_blob_submit`/`flaw_blob_submit` (812-937) as the new `/bestmove-lease`+`/bestmove-submit` template; `atomic_lease_eval_game` (384-481) for the `worker_schema_version` query-param gating point; `_apply_atomic_submit` (1002-1234) for the `second_best_map` wiring | exact |
| `app/services/eval_apply.py` (extend) | service | CRUD / transform | `_build_best_move_candidates` (1823-1966) — reused verbatim, not rewritten; new tier-4b candidate-ply + minimal-apply helpers are new but sit beside it in the same module | exact |
| `app/services/eval_queue_service.py` (extend) | service | CRUD (lottery pick) | `_claim_tier4_bestmove` (666-743, Phase 176, already exists) — reused directly by the new `/bestmove-lease` endpoint instead of via `claim_eval_job`'s bundled path | exact |
| `app/services/eval_drain.py` (extend) | service (background loop) | batch | `_full_drain_tick`'s own existing shape (656-908) — the new tier-4b branch is inserted before Step 3 using the SAME session-discipline pattern (short read → gather with no session → late write session) | exact |
| `scripts/remote_eval_worker.py` (extend) | worker/client | request-response (HTTP polling) | `_run_cycle`'s existing 4-rung ladder (588-654) + `_handle_flaw_blob_response`/`_eval_atomic_game` (331-352) as the shape for the new rung-5 handler and the targeted MultiPV-2 re-search | exact |
| `app/core/config.py` (comment fix only) | config | — | `BEST_MOVE_BACKFILL_ENABLED` (94-96) — stale comment to correct, no structural analog needed | n/a (doc fix) |

## Pattern Assignments

### `app/schemas/eval_remote.py` (schema, request-response)

**Analog:** the flaw-blob schema block (lines 69-127), which is explicitly documented as "a DEDICATED, ISOLATED schema set" — copy that isolation discipline for the new tier-4b pair, and separately extend the existing atomic pair for the fresh-lane `second_best` field.

**Isolation-pair pattern to copy** (lines 85-127):
```python
class FlawBlobLeasePosition(BaseModel):
    token: str  # opaque to worker
    fen: str

class FlawBlobLeaseResponse(BaseModel):
    game_id: int
    positions: list[FlawBlobLeasePosition] = Field(max_length=MAX_SUBMIT_EVALS)
    leased_at: datetime

class FlawBlobSubmitEval(BaseModel):
    token: str
    best_cp: int | None
    best_mate: int | None
    second_cp: int | None
    second_mate: int | None
    second_uci: str | None

class FlawBlobSubmitRequest(BaseModel):
    game_id: int
    sf_version: str
    evals: list[FlawBlobSubmitEval] = Field(max_length=MAX_SUBMIT_EVALS)

class FlawBlobSubmitResponse(BaseModel):
    game_id: int
    blobs_written: int
```
Per RESEARCH.md Open Question #3, the new tier-4b lease/submit shape should be smaller than this: `{game_id, positions: [{ply, fen}]}` for lease (no `move_uci`, no `is_terminal` — the server has already validated candidacy) and `{game_id, second_best: [{ply, second_cp, second_mate}]}` for submit — same per-field bounds convention (`Field(ge=..., le=...)`) as `EVAL_CP_MIN/MAX`, `MAX_PLY` already defined at the top of this file (lines 20-26).

**Fresh-lane extension pattern** (extend, don't replace, lines 147-205):
```python
class AtomicSubmitRequest(BaseModel):
    game_id: int
    sf_version: str
    worker_schema_version: int
    evals: list[AtomicSubmitEval] = Field(max_length=MAX_SUBMIT_EVALS)
    blob_nodes: list[AtomicBlobNode] = Field(max_length=MAX_SUBMIT_BLOB_NODES)
    job_id: int | None = None
    # NEW: second_best: list[AtomicSecondBestEval] = Field(max_length=MAX_SUBMIT_EVALS)
```
`AtomicSecondBestEval` should mirror `AtomicSubmitEval`'s `ply`/eval bounds shape (lines 160-167) — `{ply: int = Field(ge=0, le=MAX_PLY), second_cp: int | None = Field(...), second_mate: int | None = Field(...), second_uci: str | None}`.
`LeasePosition` (lines 29-32) needs a new `move_uci: str | None` field for the fresh lane per CONTEXT.md Claude's Discretion — the tier-4b lease response does NOT need this field (Open Question #3 resolution: omit it there).

---

### `app/routers/eval_remote.py` (controller, request-response)

**Analog A — version gating on lease** (`atomic_lease_eval_game`, lines 384-481): the endpoint currently has no version param — add `worker_schema_version: Annotated[int, Query()] = 1` and gate BOTH `scope="explicit"` and `scope="idle"` (Pitfall 4 — gate the WHOLE atomic lane, not just tier-4b):
```python
@router.post("/atomic-lease", response_model=None)
async def atomic_lease_eval_game(
    _auth: Annotated[None, Depends(require_operator_token)],
    worker_id: Annotated[str, Depends(worker_id_label)],
    scope: Annotated[Literal["explicit", "idle"] | None, Query()] = None,
    # NEW: worker_schema_version: Annotated[int, Query()] = 1,
) -> Response | AtomicLeaseResponse:
    # NEW: if worker_schema_version < 2: return Response(status_code=status.HTTP_204_NO_CONTENT)
    claim = await claim_eval_job(worker_id=worker_id, scope=scope)
    if claim is None:
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    ...
```

**Analog B — isolated lease/submit pair template** (`flaw_blob_lease` 723-806 + `_apply_flaw_blob_submit`/`flaw_blob_submit` 812-937): copy this shape exactly for `/bestmove-lease` + `/bestmove-submit`, swapping `_claim_tier4_blob` → `_claim_tier4_bestmove`:
```python
@router.post("/bestmove-lease", response_model=None)
async def bestmove_lease(
    _auth: Annotated[None, Depends(require_operator_token)],
) -> Response | BestMoveLeaseResponse:
    async with async_session_maker() as session:
        pick = await _claim_tier4_bestmove(session)
    if pick is None:
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    game_id, _user_id = pick
    lease_positions = await _build_bestmove_lease_positions(game_id)  # NEW helper, server-computed candidate plies
    if not lease_positions:
        # Pitfall 2: zero-candidate pick must still stamp best_moves_completed_at
        # directly here (mirrors the all-sentinel branch below) — do not leave
        # the game eligible forever.
        await _stamp_best_moves_completed_directly(game_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    if len(lease_positions) > MAX_SUBMIT_EVALS:
        # SEED-073 over-cap sentinel pattern (mirrors flaw_blob_lease 787-800):
        # stamp complete and 204 rather than ever building an oversized response.
        await _stamp_best_moves_completed_directly(game_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    return BestMoveLeaseResponse(game_id=game_id, positions=lease_positions, leased_at=datetime.now(timezone.utc))
```
Isolation discipline to copy verbatim from `_apply_flaw_blob_submit`'s docstring (lines 818-822): "Isolated ... does not branch that handler, does not call `_classify_and_fill_oracle`, does not stamp `full_evals_completed_at`" — for tier-4b the equivalent constraint (S-06/D-02) is: does not call `apply_full_eval`, writes ONLY `game_best_moves` rows + `best_moves_completed_at`.

**Analog C — token/tamper-guard pattern** (`_apply_atomic_submit`'s blob_nodes guard, lines 1132-1149; and `_apply_flaw_blob_submit`'s token check, lines 867-879) — apply the SAME shape to validate `second_best`/tier-4b submitted plies:
```python
for node in body.blob_nodes:
    try:
        node_flaw_ply, _line, _k = _parse_token(node.token)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"Malformed token: {node.token!r}") from exc
    if not (0 <= node_flaw_ply < game_length):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"Unknown or foreign token: {node.token!r}")
```
For the tier-4b submit (D-03, stateless recompute), the equivalent isn't a token check but a set-membership drop: recompute the candidate-ply set server-side and silently drop/422 any submitted ply outside it — same shape as `valid_tokens` set-membership check at lines 865-879.

**Analog D — wiring `second_best_map` into `_build_best_move_candidates`** (the one-line change site, line 1170):
```python
# BEFORE (current, S-04 fallback always fires for the remote lane):
best_move_rows = await _build_best_move_candidates(game_id, targets, engine_result_map, None)

# AFTER (this phase): build a real map from body.second_best (new field)
second_best_map = {
    e.ply: (e.second_cp, e.second_mate, e.second_uci) for e in body.second_best
}
best_move_rows = await _build_best_move_candidates(game_id, targets, engine_result_map, second_best_map)
```
The docstring comment at lines 1162-1169 ("Pitfall 1: the remote worker's full-ply pass is MultiPV-1, so there is NO per-ply second-best here") must be updated — it becomes false after this phase and a stale reader would be misled (same class of stale-comment risk as Pitfall 5 in RESEARCH.md).

---

### `app/services/eval_apply.py` (service, CRUD/transform)

**Analog:** `_build_best_move_candidates` itself (1823-1966) — do NOT rewrite; only its caller's `second_best_map` argument changes from `None` to real data. New code needed alongside it:

**Gap-fill contract to preserve unchanged** (lines 1879-1893):
```python
fallback_targets = [t for t in candidate_targets if t.ply not in second_best_map]
fallback_by_ply: dict[int, tuple[...]] = {}
if fallback_targets:
    results = await asyncio.gather(
        *(engine_service.evaluate_nodes_multipv2(t.board) for t in fallback_targets)
    )
    for t, res in zip(fallback_targets, results, strict=True):
        fallback_by_ply[t.ply] = res
```
D-06 instrumentation point: wrap the `if fallback_targets:` branch with a Sentry tag distinguishing source (`drain-local` vs `worker-submit-fallback`) — per CLAUDE.md Sentry rules, use `set_tag`/`set_context`, never embed the game_id in the message string.

**New tier-4b helper** (co-located in this module, reusing the SAME candidate-detection loop shown at lines 1861-1877 — out-of-book test via `find_opening_ply_count(_contiguous_san_prefix(...))`, played==best filter): must build `engine_result_map` via the INVERSE post-move shift (Pitfall 1 in RESEARCH.md) — `eval_of_position[ply] = stored eval at row (ply - 1)`, with `ply=0 → (None, None)`. Contrast with the existing forward-shift helper it must invert:
```python
# Existing forward-shift convention (verbatim, DO NOT reuse directly — invert it):
def _post_move_eval(pos_eval: dict[int, tuple[int|None,int|None]], ply: int) -> tuple[int|None,int|None]:
    """row `ply`'s STORED eval = eval of position `ply + 1`."""
    return pos_eval.get(ply + 1, (None, None))
```
`best_move` stays un-shifted (row `ply`'s own `best_move` column). Write a dedicated unit test asserting the shift direction against a small fixture game (RESEARCH.md Pitfall 1 explicit ask).

**Anti-pattern to avoid:** do not duplicate `passes_inaccuracy_gate`/`pinned_elo_for_mover`/`score_move`/`mover_color_for_ply` from `app/services/best_move_candidates.py` inline in a new tier-4b helper — import and call them exactly as `_build_best_move_candidates` already does (lines 1932, 1939, 1945, 1931).

---

### `app/services/eval_queue_service.py` (service, CRUD lottery pick)

**Analog:** `_claim_tier4_bestmove` (666-743) already exists from Phase 176 — reuse it directly, do not re-derive. The new `/bestmove-lease` endpoint should call it the same way `flaw_blob_lease` calls `_claim_tier4_blob` (NOT via `claim_eval_job(scope=None)`, which is drain-only per the Anti-Pattern section of RESEARCH.md):
```python
async def _claim_tier4_bestmove(session: AsyncSession) -> tuple[int, int] | None:
    picked_user_id = await _es_weighted_user_pick(session, candidate_exists_sql="""...""", ...)
    if picked_user_id is None:
        return None
    game_id = await _es_weighted_game_pick(session, game_where_sql="...", ...)
    if game_id is None:
        return None
    return game_id, picked_user_id
```
D-01 extension point is `claim_eval_job`'s `scope == "idle"` branch (lines 784-798) — currently returns `None` once tier-3 is empty (SEED-072 comment explains why: `/lease` used to strand blob writes). This phase's D-01 says v2 workers should fall through past tier-3 to tier-4b here too, gated on `settings.BEST_MOVE_BACKFILL_ENABLED` — mirror the bundled-path's own tier-4b fall-through shape (lines 855-874):
```python
if bestmove_pick is None:
    return None
game_id4b, user_id4b = bestmove_pick
return ClaimedJob(
    game_id=game_id4b, user_id=user_id4b,
    tier=TIER_BESTMOVE_BACKFILL, is_lichess_eval_game=False, job_id=None,
)
```

---

### `app/services/eval_drain.py` (service, background loop)

**Analog:** `_full_drain_tick`'s own existing shape (656-908) — insert the D-05 tier branch using the SAME session-discipline comment convention already documented at lines 666-672 (short read → gather with no session → late write session).

**The bug to fix** (verified, line 908):
```python
_signal_flaw_completion(user_id)
_ = tier  # tier is available for Phase 118 tier-aware cache logic
```
`tier: int = claimed.tier` is captured at line 691 but never branched on — every claimed game (including `TIER_BESTMOVE_BACKFILL` picks) runs the FULL Step 3 gather (`evaluate_nodes_multipv2` over every non-terminal ply, lines 766-786) and the full `apply_full_eval` write (lines 868-897), re-evaluating and reclassifying an already-analyzed tier-4b game from scratch.

**Fix shape:** add an early branch right after line 693 (`job_id: int | None = claimed.job_id`), before Step 2's PGN load:
```python
if tier == TIER_BESTMOVE_BACKFILL:
    return await _tier4b_minimal_drain_tick(game_id, user_id)  # NEW — reuses the
    # same server-side candidate/writer helper the /bestmove-submit handler uses
    # (Pattern from eval_apply.py's new tier-4b helper) — candidate searches only,
    # minimal write (game_best_moves + best_moves_completed_at), no reclassify.
```
Session discipline for the new `_tier4b_minimal_drain_tick` should copy the existing tick's three-phase shape (short read session → gather with NO session open → late write session, single commit) — same structure as lines 700-897, just with a far smaller Step 2 (candidate plies only, no full-game target collection) and Step 4 (2-column write, no `apply_full_eval`).

---

### `scripts/remote_eval_worker.py` (worker/client, request-response polling)

**Analog A — version bump + lease-time version send:**
```python
WORKER_SCHEMA_VERSION: int = 1  # → bump to 2
```
The existing submit-only usage (line 702, inside `_handle_atomic_response`, `"worker_schema_version": WORKER_SCHEMA_VERSION`) must ALSO be added as a query param on the lease call (Pitfall 4):
```python
lease_resp = await client.post(
    "/api/eval/remote/atomic-lease",
    params={"scope": "explicit", "worker_schema_version": WORKER_SCHEMA_VERSION},
)
```

**Analog B — targeted re-search after the MultiPV-1 pass** (`_eval_atomic_game`, 331-352) — the exact insertion point for the new S-01 targeted second re-search:
```python
async def _eval_atomic_game(
    pool: EnginePool,
    positions: list[dict[str, object]],
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    evals = await _eval_positions(pool, positions)  # MultiPV-1, UNCHANGED (D-03 invariant)
    flaw_plies = _hint_flaw_plies(evals)
    boards, tokens = _build_blob_walk_targets(positions, evals, flaw_plies)
    blob_nodes = await _eval_atomic_blob_nodes(pool, boards, tokens) if boards else []
    # NEW: for every ply where move_uci(played) == best_move (from `evals`), run
    # evaluate_nodes_multipv2(board) via the SAME asyncio.gather + pool pattern
    # `_eval_atomic_blob_nodes` already uses — collect {ply: (second_cp, second_mate, second_uci)}.
    return evals, blob_nodes  # NEW return signature: (evals, blob_nodes, second_best)
```
`_eval_atomic_blob_nodes` (referenced, not read this session but named at line 351 and again at RESEARCH.md's "Reusable Assets") is the concrete `asyncio.gather` + pool pattern to copy for the new targeted re-search — same gather-over-boards shape, no new pooling primitive needed.

**Analog C — new rung-5 ladder entry** (`_run_cycle`, 588-654) — insert AFTER rung 4 (Pitfall 6: tier ordering must mirror `TIER_BLOB_BACKFILL(4) < TIER_BESTMOVE_BACKFILL(5)`):
```python
    if idle_resp.status_code == 204:
        blob_resp = await client.post("/api/eval/remote/flaw-blob-lease")
        if blob_resp.status_code == 204:
            # NEW Rung 5: tier-4 blob empty → try tier-4b best-move backfill.
            bestmove_resp = await client.post("/api/eval/remote/bestmove-lease")
            if bestmove_resp.status_code == 204:
                _log("Queue fully empty (204). Sleeping...")
                await asyncio.sleep(idle_sleep)
                return not loop
            return await _handle_bestmove_response(client, pool, sf_version, dry_run, loop, bestmove_resp)
        return await _handle_flaw_blob_response(client, pool, sf_version, dry_run, loop, blob_resp)
```
The new `_handle_bestmove_response` should mirror `_handle_flaw_blob_response`'s shape (evaluate leased FENs via `pool.evaluate_nodes_multipv2` — no MultiPV-1 pass needed here, no blob walk, just per-ply second-best — then submit to `/bestmove-submit`).

---

### `app/core/config.py` (doc-only fix)

**Site:** lines 94-96, `BEST_MOVE_BACKFILL_ENABLED` comment claiming best-move backfill "cannot be shed to the remote worker fleet." This phase makes that statement false (D-01/D-02 shed exactly this to workers) — update the comment as part of this phase (Pitfall 5), no code change needed beyond the docstring.

## Shared Patterns

### Auth / Operator token
**Source:** `Depends(require_operator_token)` used on every `/eval/remote/*` endpoint (e.g. `flaw_blob_lease` line 725, `atomic_lease_eval_game` line 386).
**Apply to:** the new `/bestmove-lease` and `/bestmove-submit` endpoints — identical dependency injection, no new auth mechanism.

### SF-version gate
**Source:** `atomic_submit_eval` lines 1265-1270 — `if settings.EXPECTED_SF_VERSION and body.sf_version != settings.EXPECTED_SF_VERSION: raise HTTPException(422, ...)`.
**Apply to:** the new `/bestmove-submit` endpoint (D-5 gate, same as `/submit`, `/entry-submit`, `/flaw-blob-submit`).

### Tamper-guard / in-range ply check
**Source:** `_apply_atomic_submit` lines 1137-1149 (token parse + in-range check) and `_apply_flaw_blob_submit` lines 874-879 (`valid_tokens` set-membership).
**Apply to:** `second_best` field validation on `/atomic-submit` and candidate-ply validation on `/bestmove-submit` — both are "422 on garbage, never trust which plies the worker chose to send" (S-02/D-03).

### 204-as-no-work / over-cap sentinel
**Source:** `flaw_blob_lease` lines 756-757 (empty queue → 204) and lines 787-800 (over-cap → sentinel-stamp + 204, SEED-073 pattern).
**Apply to:** `/bestmove-lease`'s empty-queue AND zero-candidate-plies (Pitfall 2) AND over-cap branches — all three should 204, and the zero-candidate/over-cap cases must additionally stamp `best_moves_completed_at` directly for forward progress (no natural sentinel column exists here the way `allowed_pv_lines=[]` works for flaw-blob).

### Sentry instrumentation (fallback source tagging, D-06)
**Source:** CLAUDE.md Sentry rules — tags for filterable dimensions (`source`), `set_context` for structured data, never embed variables in the message. Existing example: `eval_drain.py` lines 798-804 (`sentry_sdk.set_tag("source", "full_eval_drain")`).
**Apply to:** the `_build_best_move_candidates` fallback branch (`app/services/eval_apply.py` ~1888) — tag `source="drain-local"` vs `source="worker-submit-fallback"` so the regression watch (worker-submit dimension only) is queryable independent of the expected drain-local noise.

### Session discipline (no AsyncSession across asyncio.gather)
**Source:** CLAUDE.md hard rule + `_build_best_move_candidates`'s own docstring (lines 1837-1844): "candidate identification is pure in-memory ... the Pitfall-1 targeted evaluate_nodes_multipv2 fallback runs in ONE asyncio.gather with NO session open ... rating metadata is read in a short session that is CLOSED before any Maia inference."
**Apply to:** every new helper in this phase that calls `evaluate_nodes_multipv2` (worker-side targeted re-search, tier-4b drain minimal path) — three-phase shape: short read session (closed) → gather (no session) → late write session (single commit).

## No Analog Found

None — every file this phase touches already contains a directly-analogous sibling code path in the same module (see table above). No new top-level modules, directories, or wholly novel subsystems are introduced.

## Metadata

**Analog search scope:** `app/routers/eval_remote.py`, `app/schemas/eval_remote.py`, `app/services/eval_apply.py`, `app/services/eval_queue_service.py`, `app/services/eval_drain.py`, `scripts/remote_eval_worker.py`, `app/core/config.py` — all read directly this session (targeted, non-overlapping ranges) plus RESEARCH.md's own already-verified line citations reused where a repeat read would have duplicated context already in RESEARCH.md.
**Files scanned:** 7
**Pattern extraction date:** 2026-07-17
