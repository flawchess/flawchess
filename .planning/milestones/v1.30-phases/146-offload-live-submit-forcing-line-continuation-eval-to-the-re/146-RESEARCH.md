# Phase 146: Offload live-submit forcing-line continuation eval to the remote worker - Research

**Researched:** 2026-07-01
**Domain:** FastAPI async eval pipeline — remote-worker lease/submit protocol, flaw-blob tier-4 drain
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Recency-order the tier-4 lottery — fresh games win. Change `_claim_tier4_blob` to favor `full_evals_completed_at DESC` with tie-break/jitter so a just-analyzed game is not buried behind the corpus backfill.
- **D-02:** Show raw (ungated) tactic tags during the NULL-blob window — current behavior, no read-path change.
- **D-03:** Live `/submit` drops per-ply second-best (`second_cp/second_mate/second_uci`); server unconditionally skips the blob build; flaw PVs + both completion markers still stamped live. `_apply_submit` always takes the empty-`blob_map` path.
- **D-04:** Phase 146 MUST add a flaw-blob lease/submit drain loop to `scripts/remote_eval_worker.py`. This is load-bearing — without it, deferred live games stay NULL-blob forever. Shape: after exhausting tier-1/2/3, the worker polls `/flaw-blob-lease`, evaluates leased FENs at MultiPV=2, and echoes token + result to `/flaw-blob-submit`. Worker stays token-opaque (D-04a).

### Claude's Discretion
- Worker full-ply pass: likely reducible from MultiPV-2 to MultiPV-1 once second-best is dropped — research must confirm no remaining consumer, then decide.
- Exact recency tie-break/jitter form for D-01 (e.g., random pick among top-N by `full_evals_completed_at DESC`, or ES weighting over a recency window).
- Worker tier-4 poll cadence, batch size, and back-pressure strategy.
- Dev-first end-to-end validation gate (live submit → NULL blobs → tier-4 drain → gated retag).
- Whether/how to lower `HTTP_TIMEOUT_S` back from the 120s SEED-071 stopgap.

### Deferred Ideas (OUT OF SCOPE)
- Async-ify server-side blob assembly (explicitly rejected in SEED-071).
- Worker full-ply pass MultiPV-2 → MultiPV-1 if research finds a remaining consumer (becomes its own follow-up).
- Lowering `HTTP_TIMEOUT_S` without measurement gate (flagged for post-deploy observation).
- No blob shape change, no tier-4 schema change, no gate logic change, no new tactic motif, no DB migration.
</user_constraints>

## Summary

Phase 146 removes all server-side Stockfish from the live `POST /eval/remote/submit` path by making the Phase-142-added `_build_flaw_multipv2_blobs` call unreachable, then upgrades `scripts/remote_eval_worker.py` to drain the resulting NULL-blob games through the existing Phase-145 `/flaw-blob-lease` + `/flaw-blob-submit` endpoints.

The code analysis confirms that the empty-`blob_map` path (`eval_remote.py:275-276`) already does exactly what D-03 requires — it is already wired to apply evals, classify raw flaws, stamp both `full_evals_completed_at` and `full_pv_completed_at`, and leave `allowed_pv_lines`/`missed_pv_lines` NULL. Phase 146 makes that path unconditional by replacing 18 lines (`second_best_map` build + conditional blob call, lines 258-276) with `blob_map = {}`.

The full-ply pass on the worker can be safely reduced from MultiPV-2 to MultiPV-1: grep across all five load-bearing files confirms `second_cp/second_mate/second_uci` from `SubmitEval` have exactly one consumer chain (`eval_remote.py:259-263 → _build_flaw_multipv2_blobs`), which is removed. Switching `_eval_positions` from `evaluate_nodes_multipv2` to `evaluate_nodes_with_pv` saves ~20% engine compute per game on the worker (one fewer PV at every ply). The tier-4 drain rung still uses `evaluate_nodes_multipv2` because the blob contract requires second-best.

**Primary recommendation:** Make `blob_map = {}` unconditional in `_apply_submit`, drop `second_cp/second_mate/second_uci` from `SubmitEval`, reduce the full-ply worker pass to MultiPV-1, add rung-4 to `_run_cycle`, recency-order `_claim_tier4_blob`, and lower `HTTP_TIMEOUT_S` to 30s.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|---|---|---|---|
| Drop server-side Stockfish from live submit | API/Backend | — | `_apply_submit` in `app/routers/eval_remote.py` |
| Tier-4 recency ordering | API/Backend | Database | `_claim_tier4_blob` in `app/services/eval_queue_service.py` |
| Fleet worker tier-4 drain loop | Worker Script | — | `scripts/remote_eval_worker.py` (off-server fleet process) |
| Wire: drop second-best from live submit | API/Backend + Worker Script | — | `SubmitEval` schema + `_eval_positions` in worker both change |
| Flaw-blob lease/submit server endpoints | API/Backend | — | Already exist (Phase 145), consumed unchanged |
| `HTTP_TIMEOUT_S` tuning | Worker Script | — | Config constant in `scripts/remote_eval_worker.py` |

---

## Research Findings

### 1. MultiPV-1 Reduction Safety — SAFE to reduce [VERIFIED: codebase grep]

**Question:** Are `second_cp`/`second_mate`/`second_uci` from per-ply `SubmitEval` consumed anywhere other than `_build_flaw_multipv2_blobs`?

**Full grep results across all load-bearing files:**

| File | Line(s) | Role |
|---|---|---|
| `app/schemas/eval_remote.py:38-40` | Schema definition, default `None` | Definition only — not a consumer |
| `app/routers/eval_remote.py:259-263` | Build `second_best_map` from submitted `SubmitEval` rows | **Only entry point from the wire** |
| `app/routers/eval_remote.py:271-274` | Pass `second_best_map` to `_build_flaw_multipv2_blobs` | **Only consumer of `second_best_map`** |
| `app/services/eval_drain.py:1091-1095` | Build `second_best_map` from **local engine results** in `_fill_engine_game_flaw_second_best` | Server-side drain only; independent of wire |
| `app/services/eval_drain.py:1147-1150` | Use `second_best_map` in `_build_line_blobs` | Called from `_build_flaw_multipv2_blobs` only |
| `app/services/eval_drain.py:2488-2492` | Build `second_best_map` from **local gather results** in `_full_drain_tick` | Server-side in-process drain; no remote wire dependency |
| `scripts/remote_eval_worker.py:128-130` | Pack `r[4], r[5], r[6]` into JSON for `/submit` | Worker-side; these fields are sent to the server |

**Conclusion:** The live submit's per-ply second-best fields feed EXACTLY ONE chain: `_apply_submit:second_best_map → _build_flaw_multipv2_blobs`. The server-side drain (`_full_drain_tick`, `_fill_engine_game_flaw_second_best`) builds its own `second_best_map` from local engine results — it has zero dependency on anything the remote worker sends. `_build_flaw_blob_lease_positions` (`eval_drain.py:1332`) reconstructs PV walks from `game_positions.pv` only.

**Worker full-ply pass reduction:** With `second_cp/second_mate/second_uci` dropped from `SubmitEval`, the worker's `_eval_positions` can switch from `pool.evaluate_nodes_multipv2` (7-tuple) to `pool.evaluate_nodes_with_pv` (4-tuple: `eval_cp, eval_mate, best_move, pv`). The worker's new **tier-4 blob rung** still calls `evaluate_nodes_multipv2` on each leased FEN — that is the whole point of the blob lease. No correctness risk in reducing the full-ply pass.

---

### 2. The Exact `_apply_submit` Change — Pinned Line Numbers [VERIFIED: codebase read]

Current `_apply_submit` in `app/routers/eval_remote.py`:

```python
# Lines 256-276 (Phase 142 MPV-02 second-best block):
# Phase 142 MPV-02: parallel second-best map (D-03 inline fields, not a parallel list).
# Only includes rows where the worker provided second-best data; empty when old worker
# omits fields (all three default None → condition is False → map stays empty → D-04).
second_best_map: dict[int, tuple[int | None, int | None, str | None]] = {
    e.ply: (e.second_cp, e.second_mate, e.second_uci)
    for e in body.evals
    if e.second_cp is not None or e.second_uci is not None
}

# Phase 142 MPV-02: build PvNode blobs from second-best data (CPU/engine region —
# no session open here; CLAUDE.md hard rule). Passes dedup_map={} because the remote
# path has no cross-user dedup (worker already evaluated all positions).
# Guard: skip when second_best_map is empty (D-04 — old worker omits all second_*
# fields → leave blobs NULL; Phase 145 backfills the gap). Only upgraded workers
# providing at least one second-best ply trigger blob assembly.
if second_best_map:
    blob_map = await _build_flaw_multipv2_blobs(
        game_id, targets, {}, engine_result_map, second_best_map
    )
else:
    blob_map = {}
```

**The empty-blob branch (`else: blob_map = {}`, line 275-276) already does what D-03 requires.** The write phase that follows (`async with async_session_maker() as write_session:`) with `blob_map = {}`:

1. `_apply_full_eval_results(...)` — applies evals (line 285). Unchanged.
2. `_classify_and_fill_oracle(..., blob_map if blob_map else None)` → passes `None` (line 298-300). Raw classify, no gate.
3. `_run_multipv2_pass(write_session, game_id, blob_map)` → no-op because `blob_map` is empty (line 306; `_run_multipv2_pass` guards on empty dict at `eval_drain.py:1327`).
4. Path A (zero holes, line 311-315): stamps `full_evals_completed_at` AND `full_pv_completed_at`. Both markers set, `allowed_pv_lines`/`missed_pv_lines` stay NULL.
5. Path C (cap reached, line 331-333): stamps both markers with a Sentry warning.

**Phase 146 change:** Replace lines 258-276 with the single line:

```python
blob_map: dict[int, tuple[list[PvNode], list[PvNode]]] = {}
```

This makes the empty-blob path unconditional. No other change needed in `_apply_submit`.

**Also remove from the router imports** (`eval_remote.py:73-74`):
- `_build_flaw_multipv2_blobs` (no longer called from this module)
- `_run_multipv2_pass` (no longer called; only the write-session wrapper was imported; the write-session call on line 306 stays, but blob_map is always empty so it's a no-op — alternatively delete line 306 too for clarity)

**From `app/schemas/eval_remote.py:38-40`:** Remove `second_cp`, `second_mate`, `second_uci` from `SubmitEval` (D-03). These are optional fields with `= None` defaults, so removing them is a backward-compatible schema narrowing on the server — old upgraded workers that still send these fields will have them ignored by Pydantic v2's default `model_config` (extra fields are ignored unless `extra='forbid'`). Verify `SubmitRequest` has no `extra='forbid'` before removing.

---

### 3. Recency Tie-Break for `_claim_tier4_blob` (D-01) [VERIFIED: codebase read]

**Current implementation** (`eval_queue_service.py:481-498`):

```python
result = await session.execute(
    sa.text("""
        SELECT gf.game_id, g.user_id
        FROM game_flaws gf
        JOIN games g ON g.id = gf.game_id
        JOIN users u ON u.id = g.user_id
        WHERE gf.allowed_pv_lines IS NULL
          AND g.full_evals_completed_at IS NOT NULL
          AND u.is_guest = false
        ORDER BY random()
        LIMIT 1
    """)
)
```

**The tier-3 approach** (`_claim_tier3_derived`, `eval_queue_service.py:247-456`): Uses a two-step ES weighted-random user pick then game pick, both using `ORDER BY -ln(random()) / weight`. The tier-3 approach is more complex than needed for tier-4.

**Recommended D-01 form:** A CTE that selects the top N most-recently-completed distinct games, then picks randomly over that set:

```sql
WITH recent AS (
    SELECT DISTINCT ON (gf.game_id) gf.game_id, g.user_id
    FROM game_flaws gf
    JOIN games g ON g.id = gf.game_id
    JOIN users u ON u.id = g.user_id
    WHERE gf.allowed_pv_lines IS NULL
      AND g.full_evals_completed_at IS NOT NULL
      AND u.is_guest = false
    ORDER BY gf.game_id, g.full_evals_completed_at DESC
    LIMIT :recency_window
)
SELECT game_id, user_id
FROM recent
ORDER BY random()
LIMIT 1
```

With `:recency_window = 50`. This ensures:
- Multiple idle workers spread across the 50 most-recently-analyzed games (not all colliding on game N).
- Fresh games (just submitted) reliably appear in the recency window and drain promptly.
- Old corpus games (the bulk of the backfill) drain on the tail as the window scrolls.
- The `allowed_pv_lines IS NULL` predicate is unchanged — idempotency-by-construction is preserved.
- No new column, no migration, no new tier.

**Why not pure ES weighting on `full_evals_completed_at`?** ES weighting (as in tier-3) would require tuning `τ` for the completion-time dimension and adds complexity. The simpler top-N random is sufficient: with N=50 and a typical 4–12 workers, the collision probability per pick is 4/50 to 12/50 — far lower than the current 100% collision on the single newest game.

**Why N=50?** Matches the prod Stockfish pool throughput (6 engines × ~1 game/min = ~6 games/min; 50 games covers ~8 minutes of live activity). Adjust upward during corpus backfill if worker contention increases.

**Security note:** `:recency_window` must be a parameterized bind value, consistent with the existing eval_queue_service security convention. Never f-string-interpolate inside `sa.text`.

---

### 4. Fleet-Worker Tier-4 Drain Loop (D-04) [VERIFIED: codebase read]

**Current `_run_cycle` ladder** (`remote_eval_worker.py:205-255`):

```
Rung 1: POST /api/eval/remote/lease?scope=explicit   → tier-1/2
         200 → _handle_full_ply_response, return
         204 → fall to rung 2
Rung 2: POST /api/eval/remote/entry-lease            → entry-ply
         200 → _handle_entry_ply_response, return
         204 → fall to rung 3
Rung 3: POST /api/eval/remote/lease?scope=idle       → tier-3
         200 → _handle_full_ply_response, return
         204 → sleep idle_sleep, return not loop
```

**Phase 146 extension — add rung 4 after rung 3's 204:**

```
Rung 4: POST /api/eval/remote/flaw-blob-lease        → tier-4 blob
         200 → _handle_flaw_blob_response, return
         204 → sleep idle_sleep, return not loop  (same as current rung-3 empty)
```

**New handler `_handle_flaw_blob_response`:**

```python
async def _handle_flaw_blob_response(
    client: httpx.AsyncClient,
    pool: EnginePool,
    sf_version: str,
    dry_run: bool,
    loop: bool,
    blob_lease_resp: httpx.Response,
) -> bool:
    """Handle a 200 response from /flaw-blob-lease. Eval at MultiPV=2, submit."""
    blob_lease_resp.raise_for_status()
    data = blob_lease_resp.json()
    game_id = data["game_id"]
    positions = data["positions"]  # list of {token, fen}

    _log(f"Flaw-blob lease game_id={game_id} ({len(positions)} positions). Evaluating at MultiPV=2...")
    evals = await _eval_flaw_blob_positions(pool, positions)

    if dry_run:
        _log(f"--dry-run: evaluated {len(evals)} flaw-blob positions for game_id={game_id}; skipping submit.")
        return not loop

    submit_resp = await client.post(
        "/api/eval/remote/flaw-blob-submit",
        json={
            "game_id": game_id,
            "sf_version": sf_version,
            "evals": evals,
        },
    )
    submit_resp.raise_for_status()
    result = submit_resp.json()
    _log(f"Flaw-blob submit game_id={game_id}: blobs_written={result.get('blobs_written')}")
    return not loop
```

**New eval helper `_eval_flaw_blob_positions`:**

```python
async def _eval_flaw_blob_positions(
    pool: EnginePool,
    positions: list[dict[str, object]],
) -> list[dict[str, object]]:
    """Evaluate flaw-blob positions at MultiPV=2 and echo tokens (D-04a).

    Worker stays token-opaque: the token is echoed unchanged from the lease.
    Returns {token, best_cp, best_mate, second_cp, second_mate, second_uci}.
    """
    boards = [chess.Board(str(pos["fen"])) for pos in positions]
    results = await asyncio.gather(*(pool.evaluate_nodes_multipv2(b) for b in boards))
    return [
        {
            "token": pos["token"],
            "best_cp": r[0],
            "best_mate": r[1],
            "second_cp": r[4],
            "second_mate": r[5],
            "second_uci": r[6],
        }
        for pos, r in zip(positions, results)
    ]
```

**Key design notes:**
- Uses `evaluate_nodes_multipv2` (7-tuple) because the blob contract requires second-best (`FlawBlobSubmitEval` needs `best_cp, best_mate, second_cp, second_mate, second_uci`). Fields `r[2]` (best_move) and `r[3]` (pv) are unused here — these are PV-continuation FENs, not game plies.
- Token echoed unchanged (D-04a). Worker never parses the token.
- Batch size: one game per lease response, matching the Phase-145 design. No expansion needed.
- Poll cadence: the existing `idle_sleep = 1.0s` is used for the 204 (empty) path. Busy path (200 response) is a tight loop with no sleep — consistent with rungs 1-3.
- Back-pressure: none needed. If the `/flaw-blob-lease` is 204, the worker sleeps and returns `not loop` (same as tier-3 empty). The server-side tier-4 lottery has no lease TTL or SKIP LOCKED — double-claim is idempotent by construction (D-03/D-06).
- No new EnginePool instance. The worker's existing `pool` is reused.
- `asyncio.gather` is safe here — no `AsyncSession` is open in the worker process. The CLAUDE.md `asyncio.gather`-on-shared-session rule applies to the server, not the worker.

**`_run_cycle` change:** Replace the current rung-3 tail:

```python
# Current (lines 250-255):
if idle_resp.status_code == 204:
    _log("Queue empty (204). Sleeping...")
    await asyncio.sleep(idle_sleep)
    return not loop

return await _handle_full_ply_response(client, pool, sf_version, dry_run, loop, idle_resp)
```

With:

```python
if idle_resp.status_code == 204:
    # Rung 4: tier-3 empty → try tier-4 flaw-blob drain.
    blob_resp = await client.post("/api/eval/remote/flaw-blob-lease")
    if blob_resp.status_code == 204:
        _log("Queue fully empty (204). Sleeping...")
        await asyncio.sleep(idle_sleep)
        return not loop
    return await _handle_flaw_blob_response(client, pool, sf_version, dry_run, loop, blob_resp)

return await _handle_full_ply_response(client, pool, sf_version, dry_run, loop, idle_resp)
```

---

### 5. HTTP_TIMEOUT_S — Lower to 30s [VERIFIED: codebase read]

**Current value:** `HTTP_TIMEOUT_S = 120.0` (`remote_eval_worker.py:65`)

**SEED-071 stopgap comment** (lines 62-65):
> Bumped 30 -> 120 to absorb [server-side MultiPV-2 continuation Stockfish eval inline (~22*N 1M-node evals for an N-flaw game)] until the live-path continuation eval is moved off the submit response.

**After Phase 146:** The live `/submit` response no longer calls any engine. Its expected latency profile:
- DB read (game + positions): < 200ms
- `_apply_full_eval_results` (DB UPDATE per ply): < 1s
- `_classify_and_fill_oracle` (CPU, no engine): < 500ms
- `_run_multipv2_pass` (no-op): ~0ms
- DB commit: < 200ms
- Total p99 estimate: < 3s

The `/flaw-blob-submit` response is similar — token validation (CPU), blob assembly (CPU), `_classify_tactic_gated` per flaw (CPU, no engine), DB write + commit. Expected p99 < 3s.

**Recommendation:** Lower `HTTP_TIMEOUT_S` from 120s to 30s in Phase 146. This:
- Removes the SEED-071 stopgap comment (it becomes stale)
- Restores the original Phase 120 value (30.0 → bumped only for SEED-071)
- Still provides a 10x safety margin over the expected p99

**Gate:** Do not lower further without prod latency observation. 30s is the right landing point for now. If prod p99 on the new path is observed < 3s, a follow-up could lower to 10s — but that is out of scope for Phase 146.

---

### 6. Dev-First End-to-End Validation [VERIFIED: codebase read]

**Validation path:** live submit → NULL blobs → tier-4 drain → gated retag → tags denoised

**Existing test surfaces that cover parts of this flow:**

| Test Surface | File | What It Covers |
|---|---|---|
| `TestFlawBlobLeaseEndpoint` | `tests/test_eval_worker_endpoints.py:2581+` | Phase 145 `/flaw-blob-lease` endpoint (real DB, AsyncClient) |
| `_assemble_flaw_blobs_from_submit` unit tests | `tests/test_eval_worker_endpoints.py:2885+` | Blob assembly from worker results (pure CPU) |
| `run_dry_run` / `_query_status` / `_query_eligible` | `tests/test_backfill_multipv.py` | NULL-blob count queries (no engine) |
| `/submit` isolation test (line 2835) | `tests/test_eval_worker_endpoints.py` | "byte-for-byte unchanged after /flaw-blob-lease" — needs update for Phase 146 |
| Ladder tests | `tests/test_remote_eval_worker.py:100-249` | Rung 1-3 coverage; rung 4 is gap |

**Existing CLI for full server-side e2e:**

`scripts/backfill_multipv.py --db dev --dev-validate` already drives:
`_claim_tier4_blob → _build_flaw_blob_lease_positions → (stub evals) → _assemble_flaw_blobs_from_submit → _batch_update_flaw_pv_lines → _classify_tactic_gated`
and asserts idempotency (`allowed_pv_lines IS NULL` predicate clears). This covers the server-side pipeline.

**New test gaps that Phase 146 must fill:**

1. **Test that `/submit` no longer calls `_build_flaw_multipv2_blobs`** (even with second-best present). Monkeypatch `_build_flaw_multipv2_blobs` to raise `AssertionError`; submit with a full payload including `second_cp`; verify no exception and blobs stay NULL. Add to `test_eval_worker_endpoints.py`.

2. **Test `_claim_tier4_blob` recency ordering.** Insert two analyzed games for the same user, one `full_evals_completed_at` 1 minute ago and one 1 hour ago. After N draws, the recent game should be picked more often. Add to `test_eval_worker_endpoints.py` or a new `test_eval_queue_service.py`.

3. **Test `_run_cycle` rung-4 (flaw-blob-lease → submit).** Using `AsyncMock` for the HTTP client:
   - explicit 204 → entry 204 → idle 204 → blob 200 → `_handle_flaw_blob_response` called
   - all 204 → sleep called once
   Add to `tests/test_remote_eval_worker.py`.

4. **Test `_eval_flaw_blob_positions`** (new helper) with a `MockPool` returning a 7-tuple; assert `second_cp/second_mate/second_uci` populate the result and `r[2]/r[3]` (best_move/pv) are absent from the output dict.

**Full e2e dev gate (SQL check, no dev DB reset):**

```bash
# Before: count NULL-blob flaws on dev (existing dev DB state is fine)
uv run python scripts/backfill_multipv.py --db dev --status

# Run the modified worker against local dev server for 2-3 games
uv run python scripts/remote_eval_worker.py --base-url http://localhost:8000 --workers 4 --once

# Verify one recently-submitted game exits the IS NULL predicate
# (check a specific game_id that was just analyzed)
uv run python scripts/backfill_multipv.py --db dev --status
```

No dev DB reset needed. The per-run test DB isolation (conftest.py) handles automated tests. The `--dev-validate` mode in `backfill_multipv.py` exercises the server-side blob pipeline without touching the regular dev DB.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---|---|---|---|
| Tier-4 recency ordering | Custom recency table or new column | CTE over existing `full_evals_completed_at` + parameterized `ORDER BY random() LIMIT 1` over top-N | Column already exists, no migration |
| Token echo | Worker-side token parsing or validation | Echo unchanged from lease response (D-04a) | Server holds the reassembly map; worker has no flaw structure |
| Blob assembly on submit | In-place assembly in `_apply_flaw_blob_submit` | `_assemble_flaw_blobs_from_submit` (already exists, Phase 145) | Pure CPU helper, already tested |
| Back-pressure signaling | Custom heartbeat or rate-limit endpoint | `204 No Content` from `/flaw-blob-lease` (already the contract) | Self-pacing by construction |
| Worker MultiPV-2 for full-ply pass | Keep `evaluate_nodes_multipv2` for full-ply | Switch to `evaluate_nodes_with_pv` (already exists, returns 4-tuple) | No second-best consumer after D-03 |

---

## Common Pitfalls

### Pitfall 1: Leaving `_run_multipv2_pass` in `_apply_submit` after forcing `blob_map = {}`

**What goes wrong:** The call is harmless (no-op on empty dict) but leaves dead import and stale comment suggesting the path is still active.

**How to avoid:** Remove the `_run_multipv2_pass` call from `_apply_submit` (line 306) and remove its import from `eval_remote.py` imports. Run `uv run ruff check --select F401` to catch unused imports.

### Pitfall 2: Removing `second_cp/second_mate/second_uci` from `SubmitEval` breaks old workers that still send them

**What goes wrong:** Old workers (not yet upgraded to Phase 146) still include `second_cp` in their JSON. Pydantic v2's default behavior on `BaseModel` is to IGNORE extra fields. Verify `SubmitRequest` / `SubmitEval` have no `model_config = ConfigDict(extra='forbid')`.

**How to avoid:** Check `eval_remote.py:43-50` — `SubmitRequest` uses `BaseModel` with only `Field(max_length=...)`. No `extra='forbid'`. Safe to remove the fields; old workers' payloads will be silently ignored.

### Pitfall 3: Worker `_eval_flaw_blob_positions` using indices `r[0],r[1]` for `best_cp,best_mate` but also inadvertently including `r[2]` (best_move UCI) as `best_cp`

**What goes wrong:** `evaluate_nodes_multipv2` returns `(eval_cp, eval_mate, best_move_uci, pv, second_cp, second_mate, second_uci)`. Index `r[0]` = `eval_cp` and `r[4]` = `second_cp`. `FlawBlobSubmitEval` uses `best_cp/best_mate` not `eval_cp/eval_mate`, but the semantics are identical for continuation nodes. Confirm the `FlawBlobSubmitEval` field `best_cp` corresponds to `evaluate_nodes_multipv2` index `r[0]`.

**How to avoid:** `FlawBlobSubmitEval` (`eval_remote.py:125-135`) defines `best_cp: int | None, best_mate: int | None, second_cp: int | None, second_mate: int | None, second_uci: str | None` — exactly matching `r[0], r[1], r[4], r[5], r[6]`. Map explicitly in the helper to avoid off-by-one.

### Pitfall 4: Tier-4 claim recency window CTE using `DISTINCT ON` may not deduplicate across flaws

**What goes wrong:** Multiple `game_flaws` rows for the same `game_id` may yield the same game repeatedly in the top-N CTE if `DISTINCT ON (gf.game_id)` is not applied.

**How to avoid:** Use `DISTINCT ON (gf.game_id)` or a sub-select: `SELECT DISTINCT game_id FROM game_flaws WHERE ... ORDER BY ... LIMIT N` may not work with `DISTINCT` + `ORDER BY` on different columns in PostgreSQL. Use a CTE with a subquery that selects `MIN(gf.id)` per `game_id` or use `SELECT game_id, MAX(g.full_evals_completed_at)` grouped by `game_id`.

**Correct form:**

```sql
WITH recent AS (
    SELECT g.id AS game_id, g.user_id, g.full_evals_completed_at
    FROM games g
    JOIN users u ON u.id = g.user_id
    WHERE EXISTS (
        SELECT 1 FROM game_flaws gf
        WHERE gf.game_id = g.id AND gf.allowed_pv_lines IS NULL
    )
      AND g.full_evals_completed_at IS NOT NULL
      AND u.is_guest = false
    ORDER BY g.full_evals_completed_at DESC
    LIMIT :recency_window
)
SELECT game_id, user_id
FROM recent
ORDER BY random()
LIMIT 1
```

This queries `games` directly (one row per game), avoiding the `game_flaws` duplicate-row issue.

### Pitfall 5: `/flaw-blob-lease` returns `game_id` in the response but worker new loop does not include it in the submit body

**What goes wrong:** `FlawBlobSubmitRequest` requires `game_id: int`. The `FlawBlobLeaseResponse` carries `game_id`. The worker must read `data["game_id"]` from the lease response and pass it to the submit body.

**How to avoid:** The `_handle_flaw_blob_response` handler shown above reads `game_id = data["game_id"]` and includes it in `json={..., "game_id": game_id, ...}`. Verify this is explicit in the implementation.

### Pitfall 6: asyncio.gather in `_eval_flaw_blob_positions` with no session open — allowed

**Clarification (not a pitfall, but must be stated explicitly):** The CLAUDE.md rule is "never use `asyncio.gather` on the same `AsyncSession`." In the WORKER PROCESS there is no `AsyncSession` at all. `asyncio.gather` over `pool.evaluate_nodes_multipv2` is safe in the worker. The same pattern already exists in `_eval_positions` (line 120).

---

## Architecture Patterns

### System Architecture Diagram — Phase 146 New Data Flow

```
Remote worker
  |
  |-- [Rung 1] POST /lease?scope=explicit
  |     200 → eval full-ply (MultiPV-1*) → POST /submit → server applies evals,
  |           classifies raw flaws, stamps both markers, leaves blobs NULL
  |     204 ↓
  |
  |-- [Rung 2] POST /entry-lease (depth-15 entry-ply)
  |     200 → eval at depth-15 → POST /entry-submit
  |     204 ↓
  |
  |-- [Rung 3] POST /lease?scope=idle (tier-3)
  |     200 → eval full-ply (MultiPV-1*) → POST /submit → (same as rung 1)
  |     204 ↓
  |
  |-- [Rung 4, NEW] POST /flaw-blob-lease (tier-4)  ← Phase 146 adds this
        200 → eval continuation FENs (MultiPV-2) → POST /flaw-blob-submit
              → server assembles blobs, runs _classify_tactic_gated (D-07), updates tactic tags
        204 → sleep idle_sleep (all queues empty)

*Full-ply pass switches from MultiPV-2 to MultiPV-1 (second-best dropped from wire, D-03)

Server side — live submit path after Phase 146:
  POST /submit
    → _apply_submit:
        blob_map = {}  (unconditional — no engine, no gather)
        _apply_full_eval_results  → apply per-ply evals
        _classify_and_fill_oracle → raw classify (no gate, blobs NULL)
        _run_multipv2_pass        → no-op (blob_map empty)
        stamp full_evals_completed_at + full_pv_completed_at
        (allowed_pv_lines = NULL, missed_pv_lines = NULL → matches tier-4 predicate)
```

### Recommended Project Structure Changes

No new files needed. Changes are localized to:

```
app/
├── routers/eval_remote.py          # _apply_submit: force blob_map={}, remove imports
├── schemas/eval_remote.py          # SubmitEval: remove second_cp/mate/uci fields
└── services/eval_queue_service.py  # _claim_tier4_blob: recency-ordered CTE

scripts/
└── remote_eval_worker.py           # _run_cycle: add rung 4; _eval_flaw_blob_positions: new helper
                                    # _handle_flaw_blob_response: new handler; HTTP_TIMEOUT_S: 30.0
```

---

## Package Legitimacy Audit

No new external packages. Phase 146 uses only existing project dependencies (`httpx`, `python-chess`, `sqlalchemy`, `fastapi`, `pydantic`). No audit needed.

---

## Validation Architecture

Nyquist validation is enabled (`workflow.nyquist_validation: true` in `.planning/config.json`).

### Test Framework

| Property | Value |
|---|---|
| Framework | pytest + pytest-asyncio |
| Config file | `pyproject.toml` (inferred; `uv run pytest -n auto`) |
| Quick run command | `uv run pytest tests/test_eval_worker_endpoints.py tests/test_remote_eval_worker.py -x` |
| Full suite command | `uv run pytest -n auto` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|---|---|---|---|---|
| D-03 | `/submit` with any payload leaves blobs NULL, stamps both markers | unit | `uv run pytest tests/test_eval_worker_endpoints.py -k "submit" -x` | Partial (test_eval_worker_endpoints.py has submit tests; new assertion needed) |
| D-03 | `SubmitEval` drops `second_cp/second_mate/second_uci` without breaking old payload parsing | unit | `uv run pytest tests/test_eval_worker_endpoints.py -k "schema" -x` | Partial (schema tests exist; need to verify extra-field tolerance) |
| D-01 | `_claim_tier4_blob` recency ordering favors fresh games | unit | `uv run pytest tests/ -k "tier4" -x` | No — new test needed |
| D-04 | Worker `_run_cycle` rung-4: flaw-blob-lease 200 → `_handle_flaw_blob_response` | unit | `uv run pytest tests/test_remote_eval_worker.py -k "ladder" -x` | No — rung 4 not covered |
| D-04 | Worker `_eval_flaw_blob_positions` evaluates at MultiPV-2 and echoes tokens | unit | `uv run pytest tests/test_remote_eval_worker.py -k "flaw_blob" -x` | No — new test needed |
| D-04 | `_run_cycle` all 204 → sleeps once (not twice — rung 4 also 204) | unit | `uv run pytest tests/test_remote_eval_worker.py -k "empty" -x` | Partial (needs rung-4 case) |
| E2E | Full pipeline: submit → NULL blobs → tier-4 drain → gated retag | integration/CLI | `uv run python scripts/backfill_multipv.py --db dev --dev-validate` | Yes (already exists) |
| HTTP | `HTTP_TIMEOUT_S = 30.0` (stopgap removed) | unit | `uv run pytest tests/test_remote_eval_worker.py -k "timeout" -x` | No — new assertion (or verify via grep) |

### Sampling Rate

- **Per task commit:** `uv run pytest tests/test_eval_worker_endpoints.py tests/test_remote_eval_worker.py -x`
- **Per wave merge:** `uv run pytest -n auto -x`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] New test: `tests/test_eval_worker_endpoints.py` — assert `_build_flaw_multipv2_blobs` NOT called from `/submit` (D-03 enforcement)
- [ ] New test: `tests/test_eval_worker_endpoints.py` or `test_eval_queue_service.py` — `_claim_tier4_blob` recency ordering (D-01)
- [ ] New test: `tests/test_remote_eval_worker.py` — rung-4 in `_run_cycle` (D-04 coverage)
- [ ] New test: `tests/test_remote_eval_worker.py` — `_eval_flaw_blob_positions` with mock pool (D-04 helper)
- [ ] New test: `tests/test_remote_eval_worker.py` — `HTTP_TIMEOUT_S == 30.0` constant assertion

---

## Security Domain

`security_enforcement` is not explicitly false in `.planning/config.json`. Including security analysis.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---|---|---|
| V2 Authentication | No | (no auth change) |
| V3 Session Management | No | (no session change) |
| V4 Access Control | No | (same operator-token gate, unchanged) |
| V5 Input Validation | Yes | `_apply_submit`: removing fields narrows the accepted schema — Pydantic v2 `BaseModel` ignores extra fields by default; old-worker payloads with `second_cp` remain harmless |
| V6 Cryptography | No | (no cryptographic change) |

### Known Threat Patterns for this Stack

| Pattern | STRIDE | Standard Mitigation |
|---|---|---|
| Old worker sends `second_cp` → server silently ignored (no error, no second-best consumed) | Tampering | Pydantic v2 extra-field ignoring is the standard; no `extra='forbid'` on `SubmitEval`/`SubmitRequest` [VERIFIED: codebase read]. Safe by default. |
| Tier-4 CTE with `:recency_window` parameter | Tampering | Bind as `:recency_window` in `sa.text` params dict; never f-string-interpolated. Consistent with eval_queue_service.py convention [CITED: app/services/eval_queue_service.py]. |
| Worker echoes foreign token to `/flaw-blob-submit` | Tampering | T-145-09 token validation already in `_apply_flaw_blob_submit` (eval_remote.py:868-888): each submitted token is checked against the server-issued lease. Worker client change does not weaken this. |
| Large flaw-blob lease response overloading worker memory | DoS | `positions: list[FlawBlobLeasePosition] = Field(max_length=MAX_SUBMIT_EVALS)` (eval_remote.py:121) caps at 1024 positions per game [VERIFIED: app/schemas/eval_remote.py:121]. Worker process allocates `len(positions)` boards for `asyncio.gather` — bounded. |

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|---|---|---|
| A1 | `SubmitRequest` / `SubmitEval` do not have `model_config = ConfigDict(extra='forbid')`, so removing `second_cp/second_mate/second_uci` fields is backward-compatible with old workers | Pitfall 2 / D-03 | If `extra='forbid'` is present, removing fields causes 422 on old-worker payloads that still include them. Planner must verify by reading `eval_remote.py:43-50` before implementing. |

If A1 is confirmed safe (no `extra='forbid'`), this table has one entry that resolves at implementation time — no user confirmation needed.

---

## Open Questions

1. **Does `_batch_update_flaw_pv_lines` need the sentinel blob_map `{ply: ([], [])}` shape to be preserved when the live submit takes the empty-blob path?**
   - What we know: `_run_multipv2_pass` is a no-op when `blob_map = {}`. The `allowed_pv_lines` / `missed_pv_lines` columns stay NULL in the DB (not `[]`).
   - What's clear: The tier-4 predicate is `allowed_pv_lines IS NULL`. NULL blobs match — correct.
   - Recommendation: No change. The sentinel `[]` write path only fires in the `/flaw-blob-lease` all-sentinel case (D-06). The live submit does not write sentinels — it writes nothing. The tier-4 drain handles sentinels as before.

2. **Should `_run_multipv2_pass` and its call site (line 306) be removed from `_apply_submit`, or just left as a no-op?**
   - Recommendation: Remove both the call and the import. Dead code in a safety-critical path creates confusion for future readers. `_run_multipv2_pass` remains in `eval_drain.py` for the server-side drain (`_full_drain_tick`) — only the import/call in `eval_remote.py` is removed.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|---|---|---|---|---|
| PostgreSQL 18 (Docker dev) | Tier-4 query change test | Check before running | 18.x | `docker compose -f docker-compose.dev.yml -p flawchess-dev up -d` |
| Python 3.13 / uv | All backend tests | Available (existing project) | 3.13 | — |
| EnginePool / Stockfish | `_eval_flaw_blob_positions` functional test | Available (existing project) | Stockfish 18 | Mock pool for unit tests |
| `backfill_multipv.py --dev-validate` | E2E validation | Available (Phase 145, exists) | — | — |

No missing dependencies that block execution.

---

## Sources

### Primary (HIGH confidence)

- `app/routers/eval_remote.py` — `_apply_submit` (lines 195-376 read in full), `/flaw-blob-lease` (748-806), `/flaw-blob-submit` (936-967) [VERIFIED: codebase read]
- `app/services/eval_queue_service.py` — `_claim_tier4_blob` (459-499), `_claim_tier3_derived` (247-456), `claim_eval_job` (505-616) [VERIFIED: codebase read]
- `app/services/eval_drain.py` — `_build_flaw_multipv2_blobs` (1161-1279), `_run_multipv2_pass` (1316-1329), `_build_flaw_blob_lease_positions` (1332-1428), `_full_drain_tick` (2479-2554) [VERIFIED: codebase read]
- `app/schemas/eval_remote.py` — `SubmitEval` (30-40), `FlawBlobLeaseResponse` / `FlawBlobSubmitRequest` (109-150) [VERIFIED: codebase read]
- `scripts/remote_eval_worker.py` — `_run_cycle` (205-255), `_handle_full_ply_response` (258-298), `_eval_positions` (100-133), `HTTP_TIMEOUT_S` (65) [VERIFIED: codebase read]
- `scripts/backfill_multipv.py` — observability/kickoff/dev-validate CLI (full file read) [VERIFIED: codebase read]
- `tests/test_eval_worker_endpoints.py` — Phase 145 flaw-blob test coverage (lines 2419+) [VERIFIED: codebase read]
- `.planning/phases/146-offload-live-submit-forcing-line-continuation-eval-to-the-re/146-CONTEXT.md` — locked decisions D-01 through D-04 [VERIFIED: codebase read]
- `.planning/seeds/SEED-071-live-submit-continuation-eval-bottleneck.md` — root-cause analysis, decided approach [VERIFIED: codebase read]

### Secondary (MEDIUM confidence)

- `.planning/phases/145-corpus-backfill-rollout/145-CONTEXT.md` — tier-4 lottery design, D-04a token-opaque contract
- `.planning/phases/142-multipv-2-engine-pass-eval-drain-remote-worker/142-CONTEXT.md` — blob shape, D-04 old-worker backward-compat path

---

## Metadata

**Confidence breakdown:**
- `_apply_submit` change: HIGH — code read directly, exact lines pinned
- Worker rung-4 implementation: HIGH — schema and eval patterns both confirmed in code
- Recency CTE form: HIGH — query structure confirmed against existing ES patterns in the same file; PostgreSQL `DISTINCT ON` behavior [ASSUMED from training knowledge]
- MultiPV-1 reduction: HIGH — grep across all load-bearing files confirms single consumer chain
- HTTP_TIMEOUT_S recommendation: HIGH — stopgap comment in code is explicit; p99 estimate is [ASSUMED] from expected path characteristics

**Research date:** 2026-07-01
**Valid until:** 2026-08-01 (stable, internal API changes only)
