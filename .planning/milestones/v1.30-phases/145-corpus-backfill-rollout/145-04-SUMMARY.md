---
phase: 145-corpus-backfill-rollout
plan: "04"
subsystem: eval-remote
tags: [flaw-blob, submit, blob-assembly, token-validation, sentinel, tactic-retag, D-04, D-06, D-07, tdd]
dependency_graph:
  requires: [145-01-PLAN.md, 145-02-PLAN.md, 145-03-PLAN.md]
  provides: [_parse_token, _assemble_one_line_blob, _assemble_flaw_blobs_from_submit, POST /eval/remote/flaw-blob-submit]
  affects: [app/services/eval_drain.py, app/routers/eval_remote.py, tests/test_eval_worker_endpoints.py]
tech_stack:
  added: []
  patterns: [TDD-RED-GREEN, pure-CPU-blob-assembly, token-keyed-submit, read-CPU-write-session-discipline, D-04-isolation]
key_files:
  created: []
  modified:
    - app/services/eval_drain.py
    - app/routers/eval_remote.py
    - tests/test_eval_worker_endpoints.py
decisions:
  - "D-04 isolation: _apply_flaw_blob_submit never branches _apply_submit; dedicated schema set unchanged"
  - "D-03 idempotency: no NULL-blob flaws remain after first submit -> return blobs_written=0 immediately (before token validation)"
  - "T-145-09 guard: every submitted token validated against re-derived lease; foreign tokens -> 422"
  - "D-06 sentinel write: sentinel_lines from _build_flaw_blob_lease_positions -> [] blobs written; D-06 fix from Plan 01 makes [] skip _classify_tactic_gated gate"
  - "D-07 rolling retag: only 8 tactic columns updated via bulk_update_tactic_tags (no severity/phase reclassification)"
  - "Read/CPU/write session discipline: read_session closed before re-derive lease (which opens own sessions) and CPU phase; write_session opened only at write phase"
  - "second_uci None -> su='' in PvNode (Pitfall 3); all 3 token components used as dict key (Pitfall 5)"
metrics:
  duration: "30 minutes"
  completed: 2026-06-30
  tasks_completed: 2
  files_modified: 3
  files_created: 0
status: complete
---

# Phase 145 Plan 04: Flaw-Blob Submit Half — Summary

## One-liner

Token-keyed flaw-blob submit endpoint: blob reassembly from worker MultiPV=2 results with D-06 sentinel write, T-145-09 foreign-token rejection, D-07 per-game gated retag, and write-idempotent double-submit handling.

## What Was Built

### Task 1: Blob Assembly Helper (TDD RED+GREEN)

Added three pure CPU functions to `app/services/eval_drain.py`:

**`_parse_token(token: str) -> tuple[int, str, int]`**
- Parses `"{flaw_ply}:{line}:{node_k}"` token (D-04a) with `ValueError` on malformed input.
- Validates line is `"missed"` or `"allowed"` (Pitfall 5: all 3 components used as index key so `"10:missed:2"` and `"10:allowed:2"` remain distinct).

**`_assemble_one_line_blob(flaw_ply, line, node_results, sentinel_lines) -> list[PvNode]`**
- Sentinel lines (from lease builder) and lines missing node-0 result both return `[]`.
- Walks k=0, 1, 2, ... until a gap; `second_uci=None` maps to `su=""` (Pitfall 3).

**`_assemble_flaw_blobs_from_submit(game_id, submit_evals, sentinel_lines) -> dict[int, tuple[list[PvNode], list[PvNode]]]`**
- Indexes all worker results by `(flaw_ply, line, node_k)` via `_parse_token`; malformed tokens skipped silently (endpoint validates upstream).
- Covers all flaw plies from both submitted evals and sentinel_lines.
- Returns `blob_map: {flaw_ply -> (allowed_blob, missed_blob)}` where both values are `list[PvNode]` (possibly `[]`).

Added `FlawBlobSubmitEval` to import from `app.schemas.eval_remote`.

**TDD:** RED (4 unit tests: full sequence + Pitfall-3, sentinel [], missing-node0 [], missed/allowed distinct Pitfall-5) → GREEN (all 4 pass).

### Task 2: POST /eval/remote/flaw-blob-submit Endpoint (TDD RED+GREEN)

Added `_apply_flaw_blob_submit(game_id, body)` and the endpoint to `app/routers/eval_remote.py`.

**Handler flow (read/CPU/write session discipline per CLAUDE.md hard rule):**

1. **Read phase** (dedicated `read_session`, closed before next phase):
   - Load `Game` → 404 if not found.
   - Load all `GamePosition` rows ordered by ply (for `_classify_tactic_gated`).
   - Load `set[int]` of flaw plies with `allowed_pv_lines IS NULL` (NULL-blob flaws).

2. **Idempotency gate (D-03):** If `null_flaw_plies` is empty → return `FlawBlobSubmitResponse(game_id, blobs_written=0)` immediately, before any token validation or session work. Makes double-submit write-idempotent.

3. **Re-derive lease** (`_build_flaw_blob_lease_positions(game_id)` — opens its own sessions internally, called after `read_session` is closed so no concurrent session usage): extracts `valid_tokens: set[str]` and `sentinel_lines: set[tuple[int, str]]`.

4. **Token validation (T-145-09):** Every submitted token in `body.evals` validated against `valid_tokens`. Foreign or sentinel-line tokens → `422 Unprocessable Content`. Prevents both cross-game injection and sentinel-line tampering.

5. **CPU phase** (no session):
   - `_assemble_flaw_blobs_from_submit(game_id, body.evals, sentinel_lines)` → `blob_map`.
   - `_recompute_fen_map(game.pgn)` → FEN map for `_classify_tactic_gated`.
   - For each `flaw_ply` in `null_flaw_plies`: run `_classify_tactic_gated` for both `"allowed"` and `"missed"` lines using the in-memory `blob_map` pair. D-06 fix from Plan 01 ensures `[]` blobs skip the tactic gate cleanly. Build `updates` list for bulk tactic-tag update.

6. **Write phase** (dedicated `write_session`):
   - `_batch_update_flaw_pv_lines(write_session, game_id, blob_map)` — writes real blobs and `[]` sentinels.
   - `bulk_update_tactic_tags(write_session, updates)` — updates only the 8 tactic columns (D-07 rolling rollout; no severity/phase reclassification).
   - `await write_session.commit()`.

7. Returns `FlawBlobSubmitResponse(game_id, blobs_written=len(blob_map))`.

**Endpoint:** `POST /flaw-blob-submit` with `require_operator_token` auth (D-05 SF-version gate same pattern as `/submit`). D-04 isolation enforced: `_apply_submit` is byte-for-byte unchanged (isolation test verifies this).

**TDD:** RED (7 endpoint integration tests: auth, 404, roundtrip-writes-blobs, sentinel-[], foreign-token-422, idempotent, D-04-isolation) → GREEN (all 7 pass).

**New imports added to `app/routers/eval_remote.py`:**
- `FlawBlobSubmitRequest`, `FlawBlobSubmitResponse` from schemas
- `_assemble_flaw_blobs_from_submit`, `_parse_token` from `eval_drain`
- `GameFlaw` from models
- `bulk_update_tactic_tags` from `game_flaws_repository`
- `_classify_tactic_gated`, `_recompute_fen_map` from `flaws_service`

## Verification Results

- `uv run pytest tests/test_eval_worker_endpoints.py -n auto`: **65 passed** (all Plan 03 + Plan 04 tests)
- `uv run ruff check app/ tests/`: **All checks passed** (1 lint error auto-fixed, 7 files reformatted)
- `uv run ty check app/ tests/`: **All checks passed** (zero errors)

## Deviations from Plan

None — plan executed exactly as written. All must_haves satisfied:

- PvNode blobs assembled from worker tokens and written via `_batch_update_flaw_pv_lines` (D-01).
- Lines with no walkable PV or no node-0 result get `[]` sentinel written (D-06).
- `_classify_tactic_gated` called per flaw; 8 tactic columns updated via `bulk_update_tactic_tags` (D-07).
- Tokens validated against current lease; double-submit idempotent (D-03, T-145-09).
- `_apply_submit` untouched — isolation test passes (D-04).

## Known Stubs

None. All blobs written (real PvNode lists or `[]` sentinels) satisfy the `allowed_pv_lines IS NULL` predicate elimination. The gated retag (D-07) updates tactic columns in the same transaction.

## Threat Flags

New endpoint `POST /eval/remote/flaw-blob-submit`:

| Flag | File | Description |
|------|------|-------------|
| new_endpoint | app/routers/eval_remote.py | POST /eval/remote/flaw-blob-submit behind require_operator_token |

Addressed by plan threat register:
- T-145-05b (spoofing) → mitigated by `require_operator_token` (same pattern as all eval endpoints)
- T-145-09 (token injection) → mitigated by per-token validation against re-derived lease (422 on foreign)
- T-145-10 (body cap) → mitigated by `max_length=MAX_SUBMIT_EVALS` on `FlawBlobSubmitRequest.evals`
- T-145-11 (idempotency) → early-exit on `null_flaw_plies == empty`, returns `blobs_written=0`
- T-145-12 (isolation) → dedicated handler, `_apply_submit` byte-for-byte unchanged, verified by test

## Self-Check: PASSED

All files present and all commits found in git log.

| Item | Status |
|------|--------|
| app/services/eval_drain.py | FOUND |
| app/routers/eval_remote.py | FOUND |
| tests/test_eval_worker_endpoints.py | FOUND |
| .planning/phases/145-corpus-backfill-rollout/145-04-SUMMARY.md | FOUND |
| cef8027e test(145-04): RED tests | FOUND |
| 6b55396d feat(145-04): Task 1 GREEN | FOUND |
| 22076c32 feat(145-04): Task 2 GREEN | FOUND |
| f3e487ef style(145-04): ruff format | FOUND |
