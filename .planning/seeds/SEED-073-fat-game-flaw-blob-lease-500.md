---
id: SEED-073
status: dormant
planted: 2026-07-01
planted_during: SEED-072 post-deploy prod monitoring (2026-07-01, ~05:00–08:07Z). While watching the tier-4 flaw-blob drain after shipping SEED-072, the draining worker (194.191.211.24) logged a steady ~4–5% rate of HTTP 500s on `POST /api/eval/remote/flaw-blob-lease` immediately after deploy, then sporadic 500s (0 in most 30-min windows). Traced to a `FlawBlobLeaseResponse` Pydantic ValidationError at `eval_remote.py` flaw_blob_lease. NOT caused by SEED-072 — pre-existing Phase-146 bug; SEED-072 just surfaced it by finally routing all tier-4 draining through `/flaw-blob-lease`.
trigger_when: soon-ish — low urgency but a real correctness gap. It does NOT block the bulk drain (only the fattest games are affected; 99%+ drain fine), but every over-cap game is permanently un-leasable: it stays NULL-blob, gets re-picked by the tier-4 lottery, 500s again, and never drains — so a residue of the biggest games will never gate-retag and will keep burning a worker's lease attempt each time they're drawn. Fix before declaring the corpus backfill "complete".
scope: Small backend, eval flaw-blob lease/submit path only. Cap or chunk the flaw-blob lease so a game with > MAX_SUBMIT_EVALS (=1024) PV-node positions is leased in bounded slices instead of failing response validation. Likely also needs the submit side to accept partial coverage (it already is per-flaw idempotent). No schema migration; possibly a new constant + slice logic in `_build_flaw_blob_lease_positions` and/or the handler. DECIDED APPROACH: chunk the lease (lease whole flaws up to ≤ MAX_SUBMIT_EVALS positions per call; game re-picked by the lottery to finish remaining flaws over multiple passes). Rejected: raising MAX_SUBMIT_EVALS — it is a shared DoS guard on the submit path (T-123-05 / T-145-05), doesn't scale, and just moves the ceiling.
---

# SEED-073: `/flaw-blob-lease` 500s on "fat" games (flaw-PV-node count > MAX_SUBMIT_EVALS) → those games are permanently un-drainable

## Root cause (verified against deployed code)

`flaw_blob_lease` (`app/routers/eval_remote.py`, ~line 779) builds its response as:

```python
return FlawBlobLeaseResponse(
    game_id=game_id,
    positions=lease_positions,       # <-- one entry per walkable PV node across all NULL-blob flaws
    leased_at=datetime.now(timezone.utc),
)
```

and the schema (`app/schemas/eval_remote.py:116`) bounds it:

```python
class FlawBlobLeaseResponse(BaseModel):
    game_id: int
    # Bounded by MAX_SUBMIT_EVALS (DoS guard reused — T-145-05 / T-123-05).
    positions: list[FlawBlobLeasePosition] = Field(max_length=MAX_SUBMIT_EVALS)  # MAX_SUBMIT_EVALS = 1024
    leased_at: datetime
```

`_build_flaw_blob_lease_positions` walks **every** NULL-blob flaw's two PV lines and emits one `FlawBlobLeasePosition` per walkable node. A game with enough flaws × line length can produce **more than 1024** positions. When it does, constructing `FlawBlobLeaseResponse` raises `pydantic_core.ValidationError` → the handler 500s **before** any lease is returned.

Because the pick (`_claim_tier4_blob`) still sees the game as NULL-blob, the tier-4 lottery **re-selects it later and 500s again** — the game never drains, never gate-retags, and each draw wastes a worker's lease attempt.

Note the submit side has the **same 1024 cap**: `FlawBlobSubmitRequest.evals = Field(max_length=MAX_SUBMIT_EVALS)` (`schemas/eval_remote.py:143`). So even if the lease didn't 500, a >1024-position game couldn't be submitted in one request. Any fix must bound BOTH sides, which is exactly why chunking (not raising the cap) is the right shape.

## Evidence (prod, 2026-07-01, during SEED-072 drain monitoring)

- Draining worker `194.191.211.24` logged ~4–5% 500s on `/flaw-blob-lease` in the first minutes post-deploy; sporadic afterward (many 30-min windows had 0). So only the fattest games trigger it — rare but real and permanent.
- The worker console showed games leasing fine at **426 FENs across 18 flaws** (so a game at 426 positions is under the 1024 cap and succeeds). The 500s are games whose total walkable positions exceed 1024 (many flaws and/or long PVs).
- Traceback tail (repeated): `File ".../app/routers/eval_remote.py", line 779, in flaw_blob_lease` → `pydantic_core._pydantic_core.ValidationError: 1 validation error for FlawBlobLeaseResponse`.

## Decided fix: chunk the flaw-blob lease

Lease at most `MAX_SUBMIT_EVALS` positions per call, packing **whole flaws** (both `allowed` + `missed` lines of a flaw stay together so blob reassembly is never split across leases). A game with more than one chunk's worth of positions simply gets leased again on a later lottery draw; the tier-4 predicate (`allowed_pv_lines IS NULL`) already guarantees forward progress because each `/flaw-blob-submit` clears the flaws it covered (D-03 idempotency + the lease builder's `allowed_pv_lines IS NULL` filter).

Effect: the fattest games drain over 2–3 lease/submit round-trips instead of 500ing forever. No cap raise, no migration, no change to the DoS guard.

## Plan-time checks

- Confirm `_build_flaw_blob_lease_positions` emits positions grouped by flaw so a chunk boundary never splits a flaw's two lines (else `_assemble_flaw_blobs_from_submit` would see a partial flaw). If it interleaves, group before slicing.
- Verify the all-sentinel / partial-sentinel paths (T-145-07 forward-progress) still hold when only a subset of a game's flaws is leased per call — sentinels for un-leased flaws must NOT be written prematurely, or they'd mark still-pending flaws as done.
- Decide the token scheme is unaffected: tokens are `{flaw_ply}:{line}:{node_k}` and already per-flaw, so chunking by flaw needs no token change.
- Add a test: a synthetic game with > MAX_SUBMIT_EVALS positions leases in bounded chunks (≤1024 each), each chunk submits, and after N passes the game has zero NULL-blob flaws (fully drained, no 500).
- Guests still excluded; tier-1/2/3 and the SEED-072 idle routing unchanged.

## Acceptance / done-when

- A game with > 1024 flaw-blob positions no longer 500s `/flaw-blob-lease`; it leases in ≤1024-position chunks.
- After enough lottery draws, such a game reaches zero NULL-blob flaws (drained + gate-retagged), same as normal games.
- `/flaw-blob-lease` 500 rate → 0 in prod.
- No regression to normal (≤1024) games; submit remains idempotent; blob shape / gate logic unchanged.

## Cross-refs

- [[SEED-072]] — removing the idle `/lease` tier-4 fallthrough routed ALL tier-4 draining through `/flaw-blob-lease`, which is what surfaced this latent 500 at scale.
- `app/routers/eval_remote.py::flaw_blob_lease` (~779) and `::_build_flaw_blob_lease_positions`.
- `app/schemas/eval_remote.py::FlawBlobLeaseResponse` (positions `max_length=MAX_SUBMIT_EVALS`), `::FlawBlobSubmitRequest` (evals same cap), `MAX_SUBMIT_EVALS = 1024`.
