---
phase: 145-corpus-backfill-rollout
plan: "03"
subsystem: eval-remote
tags: [flaw-blob, lease, token-keyed, tier-4, sentinel, tdd, D-04]
dependency_graph:
  requires: [145-01-PLAN.md, 145-02-PLAN.md]
  provides: [FlawBlobLeasePosition, FlawBlobLeaseResponse, _build_flaw_blob_lease_positions, POST /eval/remote/flaw-blob-lease]
  affects: [app/schemas/eval_remote.py, app/services/eval_drain.py, app/routers/eval_remote.py]
tech_stack:
  added: []
  patterns: [TDD-RED-GREEN, PV-walk-board-replay, token-keyed-lease, sentinel-forward-progress]
key_files:
  created: []
  modified:
    - app/schemas/eval_remote.py
    - app/services/eval_drain.py
    - app/routers/eval_remote.py
    - tests/test_eval_worker_endpoints.py
    - tests/services/test_eval_drain.py
decisions:
  - "D-04: FlawBlob schemas are isolated — never reuse LeaseResponse/SubmitRequest (live path safety)"
  - "D-04a: token format '{flaw_ply}:{line}:{node_k}'; worker stays opaque, echoes unchanged"
  - "T-145-07: all-sentinel games immediately write [] via _batch_update_flaw_pv_lines and return 204"
  - "Mixed-sentinel design: sentinel lines in walkable games deferred to Plan 04 submit handler"
metrics:
  duration: "15 minutes"
  completed: 2026-06-30
  tasks_completed: 3
  files_modified: 5
  files_created: 0
status: complete
---

# Phase 145 Plan 03: Flaw-Blob Lease Half — Summary

## One-liner

Token-keyed flaw-blob lease endpoint: dedicated FlawBlob schemas, PV-walk lease builder with sentinel detection, and `POST /eval/remote/flaw-blob-lease` that hands the fleet one game's continuation FENs to evaluate at MultiPV=2.

## What Was Built

### Task 1: FlawBlob Lease/Submit Pydantic Schemas (D-04)

Added five schema classes to `app/schemas/eval_remote.py` under a Phase 145 SHIP-01 section header:

- `FlawBlobLeasePosition` — `token: str` (opaque reassembly key, D-04a) + `fen: str`
- `FlawBlobLeaseResponse` — `game_id`, `positions: list[FlawBlobLeasePosition]` (bounded by `MAX_SUBMIT_EVALS`), `leased_at: datetime`
- `FlawBlobSubmitEval` — `token` echoed from lease + `best_cp/best_mate/second_cp/second_mate/second_uci` (wire type `str | None`; maps to `""` at assembly time per Pitfall 3)
- `FlawBlobSubmitRequest` — `game_id`, `sf_version`, `evals: list[FlawBlobSubmitEval]` with `max_length=MAX_SUBMIT_EVALS` DoS cap
- `FlawBlobSubmitResponse` — `game_id + blobs_written`

Token format documented in comment: `"{flaw_ply}:{line}:{node_k}"` where `line` ∈ `{"missed", "allowed"}`. The existing `MAX_SUBMIT_EVALS = 1024` is reused as the DoS guard. `LeaseResponse`/`SubmitRequest` are untouched (D-04 isolation).

**TDD:** RED (5 schema unit tests: `test_flaw_blob_schema_*`) → GREEN (add schema classes).

### Task 2: Server-Side Lease Builder with Sentinel Detection

Added `_build_flaw_blob_lease_positions(game_id)` to `app/services/eval_drain.py` plus two top-level imports (`GameFlaw` from `app.models.game_flaw`, `FlawBlobLeasePosition` from `app.schemas.eval_remote`).

**Function signature:**
```python
async def _build_flaw_blob_lease_positions(
    game_id: int,
) -> tuple[list[FlawBlobLeasePosition], set[tuple[int, str]]]:
```

**Algorithm:**
1. Read phase (short session, closed before CPU): load `Game` (pgn), `game_flaws WHERE allowed_pv_lines IS NULL`, and `game_positions (ply, pv)` at `{flaw_ply, flaw_ply+1}` for all flaws.
2. CPU phase (no session): replay PGN via `chess.pgn.read_game` to build `board_at_ply: dict[int, chess.Board]`.
3. For each flaw's two lines `("missed", flaw_ply)` and `("allowed", flaw_ply+1)`: call `_walk_pv_boards(start_board, pv, PV_CAP_PLIES)`. Walk length ≥ 2 → emit `FlawBlobLeasePosition(token=f"{flaw_ply}:{line}:{k}", fen=board.fen())` for each node `k`. Walk length < 2 or missing start board → add `(flaw_ply, line)` to sentinel set.

No `asyncio.gather`, no engine calls (CLAUDE.md hard rule preserved). Engine and lichess games handled identically (D-09).

**TDD:** RED (3 integration tests: normal walkable line, NULL-pv sentinel, lichess game identical) → GREEN.

### Task 3: POST /eval/remote/flaw-blob-lease Endpoint

Added the endpoint to `app/routers/eval_remote.py` with the following additions to imports:
- `_batch_update_flaw_pv_lines`, `_build_flaw_blob_lease_positions` from `eval_drain`
- `_claim_tier4_blob` from `eval_queue_service`
- `FlawBlobLeaseResponse` from schemas

**Endpoint flow:**
1. Open own session → call `_claim_tier4_blob` → close session.
2. If None → 204 (empty backfill queue).
3. Call `_build_flaw_blob_lease_positions(game_id)` → `(lease_positions, sentinel_lines)`.
4. If `lease_positions` is empty (all-sentinel game): build sentinel blob_map `{ply: ([], [])}` for each sentinel flaw ply, write via `_batch_update_flaw_pv_lines` in a write session → return 204. This clears `allowed_pv_lines IS NULL` so the game is never re-picked (T-145-07 forward-progress guarantee).
5. Otherwise: return `FlawBlobLeaseResponse(game_id, positions, leased_at)`.

The `_apply_submit` and `/submit` endpoint are byte-for-byte unchanged (D-04 isolation verified by an explicit test).

**TDD:** RED (6 endpoint tests: auth check, empty queue 204, positions response, token parsing, all-sentinel 204 + sentinel write, `/submit` isolation) → GREEN.

## Verification Results

- `uv run pytest tests/test_eval_worker_endpoints.py tests/services/test_eval_drain.py -x`: **75 passed**
- `uv run ruff check app/ tests/`: **All checks passed**
- `uv run ty check app/ tests/`: **All checks passed** (zero errors)

## Deviations from Plan

None — plan executed exactly as written.

Design choice documented per plan's "Choose the design that guarantees forward progress":
- **All-sentinel games**: endpoint writes `[]` sentinels and returns 204 (no retry).
- **Mixed games**: sentinel lines deferred to Plan 04 submit handler (only all-sentinel triggers immediate write in this endpoint).

This matches the threat model mitigation for T-145-07 (DoS: all-sentinel game loop → mitigated).

## Known Stubs

`FlawBlobSubmitEval` / `FlawBlobSubmitRequest` / `FlawBlobSubmitResponse` are defined in schemas (consumed by Plan 04). The submit handler for `/flaw-blob-submit` is Plan 04's responsibility. No Plan 03 stub — the schemas are complete; the handler is out of scope.

## Threat Flags

New endpoint `POST /eval/remote/flaw-blob-lease` at trust boundary (T-145-05):
| Flag | File | Description |
|------|------|-------------|
| new_endpoint | app/routers/eval_remote.py | POST /eval/remote/flaw-blob-lease behind require_operator_token (HMAC auth, same pattern as all eval endpoints) |

Addressed by plan threat register: T-145-05 (Spoofing → mitigated by `require_operator_token`), T-145-07 (DoS loop → mitigated by sentinel write), T-145-08 (Tampering → test verifies `/submit` unchanged).

## Self-Check

Verified commits exist and files are present.
