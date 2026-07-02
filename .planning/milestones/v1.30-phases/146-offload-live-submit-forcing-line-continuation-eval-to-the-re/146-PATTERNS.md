# Phase 146: Offload live-submit forcing-line continuation eval to the remote worker - Pattern Map

**Mapped:** 2026-07-01
**Files analyzed:** 5 modified files (no new files)
**Analogs found:** 5 / 5

## File Classification

| Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `app/routers/eval_remote.py` | router | request-response | `app/routers/eval_remote.py` (same file, existing empty-blob branch) | exact |
| `app/schemas/eval_remote.py` | schema | — | `app/schemas/eval_remote.py` (existing `FlawBlobSubmitEval` etc.) | exact |
| `app/services/eval_queue_service.py` | service | CRUD | `app/services/eval_queue_service.py` `_claim_tier3_derived` | role+flow match |
| `scripts/remote_eval_worker.py` | worker script | event-driven | `scripts/remote_eval_worker.py` (existing rungs 1–3 + `_handle_entry_ply_response`) | exact |
| `tests/test_remote_eval_worker.py` | test | — | `tests/test_remote_eval_worker.py` existing ladder tests | exact |

---

## Pattern Assignments

### `app/routers/eval_remote.py` — force `blob_map = {}` in `_apply_submit`

**Analog:** The existing `else: blob_map = {}` branch at lines 103–103 (quoted in RESEARCH.md §2), plus the empty-blob write path starting at line 285.

**Change:** Replace lines 258–276 (the `second_best_map` build + conditional blob call) with one line:

```python
blob_map: dict[int, tuple[list[PvNode], list[PvNode]]] = {}
```

**Remove unused imports** — after the replacement, `_build_flaw_multipv2_blobs` and `_run_multipv2_pass` are no longer called from this module. Remove their import lines (`eval_remote.py:73-74`). Also remove the `_run_multipv2_pass` call at line 306 (no-op on empty dict — remove for clarity per RESEARCH Pitfall 1 and Open Question 2).

**Core empty-blob write path (lines 285–333, unchanged — confirm these remain intact):**

```python
# Line 285 — applies per-ply evals
_apply_full_eval_results(...)

# Lines 298-300 — raw classify (blob_map={} → passes None, skips gate)
_classify_and_fill_oracle(..., blob_map if blob_map else None)

# Line 306 — _run_multipv2_pass: no-op on empty dict → REMOVE this call and its import

# Lines 311-315 (Path A: zero holes) — stamps BOTH completion markers
#   full_evals_completed_at AND full_pv_completed_at
#   allowed_pv_lines / missed_pv_lines stay NULL → matches tier-4 predicate
```

**Auth/security note:** No auth change. `SubmitRequest` uses `BaseModel` with no `extra='forbid'` (verified: `eval_remote.py:43-50`) — removing `second_cp/second_mate/second_uci` from `SubmitEval` is backward-compatible; old workers that still send those fields have them silently ignored by Pydantic v2.

---

### `app/schemas/eval_remote.py` — drop `second_cp/second_mate/second_uci` from `SubmitEval`

**Analog:** The existing `FlawBlobSubmitEval` at lines 125–135 (below) shows the sibling schema that KEEPS second-best (because it IS the blob eval). `SubmitEval` (lines 30–40) is the one that LOSES it.

**`SubmitEval` before (lines 30–40):**

```python
class SubmitEval(BaseModel):
    ply: int = Field(ge=0)
    eval_cp: int | None
    eval_mate: int | None
    best_move: str | None  # UCI string
    pv: str | None  # space-joined UCI, up to 12 plies
    # Phase 142 MPV-02: second-best per ply for JSONB blob assembly (D-03).
    # Default None = old worker omits field → server treats as no second-best (D-04).
    second_cp: int | None = None
    second_mate: int | None = None
    second_uci: str | None = None  # wire type str|None; None maps to su="" sentinel in blob
```

**After Phase 146** — remove the three `second_*` fields and their comment block entirely. The schema becomes:

```python
class SubmitEval(BaseModel):
    ply: int = Field(ge=0)
    eval_cp: int | None
    eval_mate: int | None
    best_move: str | None  # UCI string
    pv: str | None  # space-joined UCI, up to 12 plies
```

**`FlawBlobSubmitEval` (lines 125–135) — UNCHANGED, kept as-is (the blob rung still needs second-best):**

```python
class FlawBlobSubmitEval(BaseModel):
    token: str  # echoed from FlawBlobLeasePosition.token unchanged (D-04a)
    best_cp: int | None
    best_mate: int | None
    second_cp: int | None
    second_mate: int | None
    second_uci: str | None
```

**`FlawBlobLeaseResponse` (lines 116–122) — UNCHANGED, reused by the new worker rung:**

```python
class FlawBlobLeaseResponse(BaseModel):
    game_id: int
    positions: list[FlawBlobLeasePosition] = Field(max_length=MAX_SUBMIT_EVALS)
    leased_at: datetime
```

---

### `app/services/eval_queue_service.py` — recency-order `_claim_tier4_blob` (D-01)

**Analog:** `_claim_tier3_derived` (lines 247–456) — the ES lottery pattern showing: `sa.text(...)` query, parameterized bind values, `session.execute`, `.one_or_none()`, typed return.

**Current `_claim_tier4_blob` query (lines 481–493) — the one being replaced:**

```python
result = await session.execute(
    sa.text("""
        SELECT gf.game_id, g.user_id
        FROM game_flaws gf
        JOIN games g ON g.id = gf.game_id
        JOIN users u ON u.id = g.user_id
        WHERE gf.allowed_pv_lines IS NULL
          AND g.full_evals_completed_at IS NOT NULL
          AND u.is_guest = false  -- intentional: guests excluded (QUEUE-08)
        ORDER BY random()
        LIMIT 1
    """)
)
```

**Replacement — recency CTE with jitter (D-01, RESEARCH §3 Pitfall 4 corrected form):**

```python
TIER4_RECENCY_WINDOW: int = 50  # top-N most-recently-analyzed games spread among idle workers

result = await session.execute(
    sa.text("""
        WITH recent AS (
            SELECT g.id AS game_id, g.user_id, g.full_evals_completed_at
            FROM games g
            JOIN users u ON u.id = g.user_id
            WHERE EXISTS (
                SELECT 1 FROM game_flaws gf
                WHERE gf.game_id = g.id AND gf.allowed_pv_lines IS NULL
            )
              AND g.full_evals_completed_at IS NOT NULL
              AND u.is_guest = false  -- intentional: guests excluded (QUEUE-08)
            ORDER BY g.full_evals_completed_at DESC
            LIMIT :recency_window
        )
        SELECT game_id, user_id
        FROM recent
        ORDER BY random()
        LIMIT 1
    """),
    {"recency_window": TIER4_RECENCY_WINDOW},
)
```

**Security rule (copy from tier-3 pattern):** `:recency_window` MUST be a parameterized bind value — never f-string-interpolated inside `sa.text`. Consistent with the comment in `_claim_tier3_derived` (lines 331–332): "All variable values bound as :tau_s, :floor — never f-string-interpolated."

**Post-query extract pattern (lines 494–499, unchanged):**

```python
row = result.one_or_none()
if row is None:
    return None
game_id: int = row[0]
user_id: int = row[1]
return game_id, user_id
```

**Where to define the constant:** Add `TIER4_RECENCY_WINDOW: int = 50` in the module-level constants block, near the existing `RECENCY_HALF_LIFE_DAYS` / `WEIGHT_FLOOR` constants.

---

### `scripts/remote_eval_worker.py` — add rung 4 + `_handle_flaw_blob_response` + `_eval_flaw_blob_positions` + lower `HTTP_TIMEOUT_S`

#### 1. `HTTP_TIMEOUT_S` constant (line 65)

**Before:**
```python
# Stopgap (SEED-071): the live /submit handler runs server-side MultiPV-2 continuation
# Stockfish eval inline (~22*N 1M-node evals for an N-flaw game) before responding, so a
# flaw-heavy game's submit can take well over 30s under load and trip a ReadTimeout. Bumped
# 30 -> 120 to absorb it until the live-path continuation eval is moved off the submit response.
HTTP_TIMEOUT_S: float = 120.0
```

**After Phase 146** — restore 30s, remove the stopgap comment:
```python
HTTP_TIMEOUT_S: float = 30.0
```

#### 2. `_eval_flaw_blob_positions` helper

**Analog:** `_eval_positions` (lines 100–133) — same fan-out pattern via `asyncio.gather` + `pool.evaluate_nodes_multipv2`. The new helper differs in: (a) positions are keyed by `token` not `ply`, (b) `best_move`/`pv` (indices `r[2]`/`r[3]`) are NOT included in output, (c) field names match `FlawBlobSubmitEval` (`best_cp`, `second_cp` etc. rather than `eval_cp`).

**`_eval_positions` analog (lines 100–133):**
```python
async def _eval_positions(
    pool: EnginePool,
    positions: list[dict[str, object]],
) -> list[dict[str, object]]:
    boards: list[chess.Board] = [chess.Board(str(pos["fen"])) for pos in positions]
    results = await asyncio.gather(*(pool.evaluate_nodes_multipv2(b) for b in boards))
    return [
        {
            "ply": pos["ply"],
            "eval_cp": r[0],
            "eval_mate": r[1],
            "best_move": r[2],
            "pv": r[3],
            "second_cp": r[4],
            "second_mate": r[5],
            "second_uci": r[6],
        }
        for pos, r in zip(positions, results)
    ]
```

**New `_eval_flaw_blob_positions` — mirror the same pattern with token key and blob fields:**
```python
async def _eval_flaw_blob_positions(
    pool: EnginePool,
    positions: list[dict[str, object]],
) -> list[dict[str, object]]:
    """Evaluate flaw-blob positions at MultiPV=2 and echo tokens (D-04a).

    Worker stays token-opaque: the token is echoed unchanged from the lease.
    evaluate_nodes_multipv2 returns (eval_cp, eval_mate, best_move, pv, second_cp,
    second_mate, second_uci); indices r[2] and r[3] (best_move/pv) are unused here —
    these are PV-continuation FENs, not game plies. Map r[0]/r[1]/r[4]/r[5]/r[6]
    explicitly to avoid off-by-one errors (RESEARCH Pitfall 3).

    asyncio.gather is safe here — no AsyncSession is open in the worker process
    (CLAUDE.md gather rule applies to the server only; RESEARCH Pitfall 6).
    """
    boards: list[chess.Board] = [chess.Board(str(pos["fen"])) for pos in positions]
    results = await asyncio.gather(*(pool.evaluate_nodes_multipv2(b) for b in boards))
    return [
        {
            "token": str(pos["token"]),  # echoed unchanged (D-04a)
            "best_cp": r[0],
            "best_mate": r[1],
            "second_cp": r[4],
            "second_mate": r[5],
            "second_uci": r[6],
        }
        for pos, r in zip(positions, results)
    ]
```

#### 3. `_handle_flaw_blob_response` handler

**Analog:** `_handle_entry_ply_response` (lines 301–334) — same shape: `raise_for_status`, read `data`, `_log`, eval helper call, dry_run guard, `client.post` submit, `raise_for_status`, log result, `return not loop`.

**`_handle_entry_ply_response` analog (lines 301–334):**
```python
async def _handle_entry_ply_response(
    client: httpx.AsyncClient,
    pool: EnginePool,
    sf_version: str,
    dry_run: bool,
    loop: bool,
    entry_resp: httpx.Response,
) -> bool:
    """Handle a 200 response from /entry-lease (depth-15 entry-ply path)."""
    entry_resp.raise_for_status()
    data = entry_resp.json()
    positions = data["positions"]

    _log(f"Leased {len(positions)} entry-ply position(s). Evaluating at depth-15...")
    evals = await _eval_entry_positions(pool, positions)

    if dry_run:
        _log(f"--dry-run: evaluated {len(evals)} entry-ply positions; skipping submit.")
        return not loop

    submit_resp = await client.post(
        "/api/eval/remote/entry-submit",
        json={"sf_version": sf_version, "evals": evals},
    )
    submit_resp.raise_for_status()
    result = submit_resp.json()
    _log(f"Entry-submit complete: game_ids={result.get('game_ids')}, stamped_count={result.get('stamped_count')}")
    return not loop
```

**New `_handle_flaw_blob_response` — mirror the same structure:**
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
    positions = data["positions"]

    _log(f"Flaw-blob lease game_id={game_id} ({len(positions)} positions). Evaluating at MultiPV=2...")
    evals = await _eval_flaw_blob_positions(pool, positions)

    if dry_run:
        _log(f"--dry-run: evaluated {len(evals)} flaw-blob positions for game_id={game_id}; skipping submit.")
        return not loop

    submit_resp = await client.post(
        "/api/eval/remote/flaw-blob-submit",
        json={"game_id": game_id, "sf_version": sf_version, "evals": evals},
    )
    submit_resp.raise_for_status()
    result = submit_resp.json()
    _log(f"Flaw-blob submit game_id={game_id}: blobs_written={result.get('blobs_written')}")
    return not loop
```

#### 4. `_run_cycle` — add rung 4

**Current rung-3 tail (lines 250–255):**
```python
    if idle_resp.status_code == 204:
        _log("Queue empty (204). Sleeping...")
        await asyncio.sleep(idle_sleep)
        return not loop

    return await _handle_full_ply_response(client, pool, sf_version, dry_run, loop, idle_resp)
```

**Replacement — insert rung 4 between the tier-3 204 and the sleep:**
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

**Update the `_run_cycle` docstring** to document rung 4:
```
      4. POST /flaw-blob-lease (tier-4 blob drain)  [Phase 146]
         200 → eval continuation FENs at MultiPV=2, submit to /flaw-blob-submit, done.
         204 → all queues empty; sleep idle_sleep.
```

#### 5. Full-ply pass: MultiPV-2 → MultiPV-1 (research-confirmed, optional in discretion — CONFIRMED safe by RESEARCH §1)

**Analog:** `_eval_positions` uses `pool.evaluate_nodes_multipv2` (line 120). With `second_cp/second_mate/second_uci` dropped from `SubmitEval`, switch the full-ply pass to `pool.evaluate_nodes_with_pv` (4-tuple: `eval_cp, eval_mate, best_move, pv`).

**`_eval_positions` lines 119–133 — change call and output fields:**
```python
# Before (line 120):
results = await asyncio.gather(*(pool.evaluate_nodes_multipv2(b) for b in boards))
# After:
results = await asyncio.gather(*(pool.evaluate_nodes_with_pv(b) for b in boards))

# Before (output dict):
{"ply": pos["ply"], "eval_cp": r[0], "eval_mate": r[1], "best_move": r[2], "pv": r[3],
 "second_cp": r[4], "second_mate": r[5], "second_uci": r[6]}
# After (4-tuple, no second-best):
{"ply": pos["ply"], "eval_cp": r[0], "eval_mate": r[1], "best_move": r[2], "pv": r[3]}
```

**Update the `_eval_positions` docstring** — remove the Phase 142 MPV-02 note about `second_cp/second_mate/second_uci`; the tier-4 blob rung (not the full-ply rung) now carries second-best.

---

### `tests/test_remote_eval_worker.py` — add rung-4 ladder tests + `_eval_flaw_blob_positions` test

**Analog:** Existing ladder tests (lines 100–244) — same mock structure: `_make_response(status_code, body)`, `AsyncMock()` client, `client.post = AsyncMock(side_effect=[...])`, `pool = AsyncMock()`, `await _run_cycle(...)`, assert `client.post.call_args_list`.

**`_make_response` helper (lines 91–97 — copy as-is, already present):**
```python
def _make_response(status_code: int, body: dict | None = None) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status_code
    resp.raise_for_status = MagicMock()
    resp.json = MagicMock(return_value=body or {})
    return resp
```

**New test 1 — rung-4 reached on all-204 from rungs 1-3, blob 200 → `_handle_flaw_blob_response`:**
```python
async def test_ladder_flaw_blob_on_all_tier123_204() -> None:
    blob_lease_body = {
        "game_id": 7,
        "positions": [{"token": "10:missed:0", "fen": "<fen>"}],
        "leased_at": "2026-07-01T10:00:00Z",
    }
    submit_body = {"game_id": 7, "blobs_written": 1}

    client = AsyncMock()
    client.post = AsyncMock(side_effect=[
        _make_response(204),           # /lease?scope=explicit
        _make_response(204),           # /entry-lease
        _make_response(204),           # /lease?scope=idle
        _make_response(200, blob_lease_body),  # /flaw-blob-lease
        _make_response(200, submit_body),      # /flaw-blob-submit
    ])

    pool = AsyncMock()
    pool.evaluate_nodes_multipv2 = AsyncMock(return_value=(100, None, "e2e4", "e2e4 e7e5", 50, None, "d2d4"))

    await _run_cycle(client=client, pool=pool, sf_version="sf18", idle_sleep=1.0, dry_run=False, loop=False)

    called_urls = [c.args[0] for c in client.post.call_args_list]
    assert "/api/eval/remote/flaw-blob-lease" in called_urls
    assert "/api/eval/remote/flaw-blob-submit" in called_urls
```

**New test 2 — all queues empty (rung-4 also 204) → sleep once:**
```python
async def test_ladder_all_queues_empty_sleeps_once() -> None:
    # All four rungs return 204 — only one sleep should fire.
    client = AsyncMock()
    client.post = AsyncMock(side_effect=[
        _make_response(204),  # /lease?scope=explicit
        _make_response(204),  # /entry-lease
        _make_response(204),  # /lease?scope=idle
        _make_response(204),  # /flaw-blob-lease
    ])
    pool = AsyncMock()

    with patch("scripts.remote_eval_worker.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        await _run_cycle(client=client, pool=pool, sf_version="sf18", idle_sleep=1.0, dry_run=False, loop=False)
        mock_sleep.assert_awaited_once_with(1.0)
```

**New test 3 — `_eval_flaw_blob_positions` maps 7-tuple correctly:**
```python
async def test_eval_flaw_blob_positions_maps_indices_correctly() -> None:
    """_eval_flaw_blob_positions maps r[0]/r[1]/r[4]/r[5]/r[6]; never r[2]/r[3]."""
    from scripts.remote_eval_worker import _eval_flaw_blob_positions

    pool = AsyncMock()
    # 7-tuple: (eval_cp, eval_mate, best_move, pv, second_cp, second_mate, second_uci)
    pool.evaluate_nodes_multipv2 = AsyncMock(return_value=(100, None, "e2e4", "e2e4 e7e5", 50, None, "d2d4"))

    positions = [{"token": "10:missed:0", "fen": "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1"}]
    results = await _eval_flaw_blob_positions(pool, positions)

    assert len(results) == 1
    r = results[0]
    assert r["token"] == "10:missed:0"
    assert r["best_cp"] == 100
    assert r["best_mate"] is None
    assert r["second_cp"] == 50
    assert r["second_mate"] is None
    assert r["second_uci"] == "d2d4"
    assert "best_move" not in r  # r[2] must not leak into output
    assert "pv" not in r          # r[3] must not leak into output
```

**New test 4 — `HTTP_TIMEOUT_S` constant assertion:**
```python
def test_http_timeout_s_restored_to_30() -> None:
    """HTTP_TIMEOUT_S must be 30.0 — the SEED-071 120s stopgap is removed in Phase 146."""
    from scripts.remote_eval_worker import HTTP_TIMEOUT_S
    assert HTTP_TIMEOUT_S == 30.0
```

**Import additions for new tests** — add to the existing import block:
```python
from scripts.remote_eval_worker import (
    ...
    HTTP_TIMEOUT_S,
    _eval_flaw_blob_positions,
    _handle_flaw_blob_response,
    ...
)
```

---

## Shared Patterns

### `sa.text` parameterized bind values
**Source:** `app/services/eval_queue_service.py` lines 331–352 (`_claim_tier3_derived` Step 1)
**Apply to:** `_claim_tier4_blob` recency CTE
```python
# CORRECT — bind as :param_name in dict
result = await session.execute(
    sa.text("... LIMIT :recency_window"),
    {"recency_window": TIER4_RECENCY_WINDOW},
)
# WRONG — never f-string-interpolate inside sa.text
sa.text(f"... LIMIT {TIER4_RECENCY_WINDOW}")
```

### `asyncio.gather` fan-out over EnginePool (worker-side only)
**Source:** `scripts/remote_eval_worker.py` lines 119–120 (`_eval_positions`)
**Apply to:** `_eval_flaw_blob_positions`
```python
boards = [chess.Board(str(pos["fen"])) for pos in positions]
results = await asyncio.gather(*(pool.evaluate_nodes_multipv2(b) for b in boards))
```
Safe in the worker process only — no `AsyncSession` open (CLAUDE.md gather rule is server-only).

### Handler signature + dry_run guard + `return not loop`
**Source:** `scripts/remote_eval_worker.py` lines 258–298 (`_handle_full_ply_response`) and 301–334 (`_handle_entry_ply_response`)
**Apply to:** `_handle_flaw_blob_response`
```python
async def _handle_*(client, pool, sf_version, dry_run, loop, resp) -> bool:
    resp.raise_for_status()
    data = resp.json()
    # ... eval ...
    if dry_run:
        _log("--dry-run: ...")
        return not loop
    submit_resp = await client.post(...)
    submit_resp.raise_for_status()
    _log(f"... result ...")
    return not loop
```

### Ladder mock structure (tests)
**Source:** `tests/test_remote_eval_worker.py` lines 91–97, 118–148
**Apply to:** new rung-4 test cases
```python
def _make_response(status_code, body=None) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status_code
    resp.raise_for_status = MagicMock()
    resp.json = MagicMock(return_value=body or {})
    return resp

client = AsyncMock()
client.post = AsyncMock(side_effect=[_make_response(204), _make_response(200, body)])
```

---

## No Analog Found

None — all changes are surgical modifications to existing files with direct in-file analogs.

---

## Metadata

**Analog search scope:** `app/routers/`, `app/services/`, `app/schemas/`, `scripts/`, `tests/`
**Files scanned:** 5 primary (read in full or targeted range)
**Pattern extraction date:** 2026-07-01
