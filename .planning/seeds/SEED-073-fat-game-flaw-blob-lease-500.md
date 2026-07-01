---
id: SEED-073
status: dormant
planted: 2026-07-01
planted_during: SEED-072 post-deploy prod monitoring (2026-07-01, ~05:00–08:07Z). While watching the tier-4 flaw-blob drain after shipping SEED-072, the draining worker (194.191.211.24) logged a steady ~4–5% rate of HTTP 500s on `POST /api/eval/remote/flaw-blob-lease` immediately after deploy, then sporadic 500s (0 in most 30-min windows). Traced to a `FlawBlobLeaseResponse` Pydantic ValidationError at `eval_remote.py` flaw_blob_lease. NOT caused by SEED-072 — pre-existing Phase-146 bug; SEED-072 just surfaced it by finally routing all tier-4 draining through `/flaw-blob-lease`.
trigger_when: soon-ish — low urgency but a real correctness gap. It does NOT block the bulk drain (only the fattest games are affected; 99%+ drain fine), but every over-cap game is permanently un-leasable: it stays NULL-blob, gets re-picked by the tier-4 lottery, 500s again, and never drains — so a residue of the biggest games will never gate-retag and will keep burning a worker's lease attempt each time they're drawn. Fix before declaring the corpus backfill "complete".
scope: Small backend, eval flaw-blob lease path only (~5 lines). When a game's total walkable PV positions exceed MAX_SUBMIT_EVALS (=1024), write the `[]` sentinel for ALL its NULL-blob flaws and return 204 — reusing the existing all-sentinel path (`eval_remote.py:769-777`). No schema migration, no new constant, no submit-side change. DECIDED APPROACH (revised 2026-07-01 after prod quantification): over-cap sentinel. Rejected: (1) raising MAX_SUBMIT_EVALS — shared DoS guard on the submit path (T-123-05 / T-145-05), weakens the guard, and is not a permanent ceiling (a long bullet game could produce thousands of positions), so a sentinel fallback is needed anyway; (2) chunking the lease — correct and zero-loss but ~15-20 lines to save the MPV=2 blob *refinement* on 17 games out of 410k (see quantification below), not worth the ratio.
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

Note the submit side has the **same 1024 cap**: `FlawBlobSubmitRequest.evals = Field(max_length=MAX_SUBMIT_EVALS)` (`schemas/eval_remote.py:143`). So even if the lease didn't 500, a >1024-position game couldn't be submitted in one request either. The decided fix sidesteps both caps: over-cap games never return a lease (they get sentineled and 204'd), so the submit path is never reached for them.

## Evidence (prod, 2026-07-01, during SEED-072 drain monitoring)

- Draining worker `194.191.211.24` logged ~4–5% 500s on `/flaw-blob-lease` in the first minutes post-deploy; sporadic afterward (many 30-min windows had 0). So only the fattest games trigger it — rare but real and permanent.
- The worker console showed games leasing fine at **426 FENs across 18 flaws** (so a game at 426 positions is under the 1024 cap and succeeds). The 500s are games whose total walkable positions exceed 1024 (many flaws and/or long PVs).
- Traceback tail (repeated): `File ".../app/routers/eval_remote.py", line 779, in flaw_blob_lease` → `pydantic_core._pydantic_core.ValidationError: 1 validation error for FlawBlobLeaseResponse`.

## Prod quantification (2026-07-01, `flawchess-prod-db`)

Estimated per-game total walkable positions across NULL-blob flaws (node count per line = `min(len(pv), PV_CAP_PLIES=12) + 1`; ignores illegal-move truncation, so an upper bound):

| Metric | Value |
|---|---|
| Eligible games (non-guest, `full_evals_completed_at IS NOT NULL`, ≥1 NULL-blob flaw) | 409,605 |
| Games over the 1024 cap | **17** (0.0042%, ~1 in 24,000) |
| Largest game | 1,680 positions (1.64× cap) |
| p99 / p99.9 of the distribution | 489 / 693 |
| Flaw count in the 17 over-cap games | 44–78 flaws each |

The 17 over-cap games are pathological (44–78 blunders/mistakes — bullet blitz-fests). The fattest is only 1.64× the cap, so the seed's original "drains over 2–3 draws" concern never materializes.

**Key correction that flips the decision:** the all-sentinel path returns 204 **without** running the gated retag, so sentinel-ing these games does NOT erase their tactic tags — they keep the tags from the original Phase-142 classification. The only thing forgone is the MultiPV=2 blob *refinement* on 17 noisy games. That is noise-level, so the simpler sentinel wins over chunking.

## Decided fix: over-cap sentinel (revised 2026-07-01)

In `flaw_blob_lease` (`eval_remote.py`), after building `lease_positions`, when `len(lease_positions) > MAX_SUBMIT_EVALS`, write the `[]` sentinel for **every** NULL-blob flaw ply of the game and return 204 — reusing the exact `sentinel_blob_map = {ply: ([], []) ...}` + `_batch_update_flaw_pv_lines` block already at `eval_remote.py:769-777`. Keep `MAX_SUBMIT_EVALS = 1024` unchanged.

Effect: the fattest games clear the `allowed_pv_lines IS NULL` predicate in one shot, stop 500ing, and are never re-picked. No cap raise, no chunking, no migration, no submit-side change, no DoS-guard change.

## Plan-time checks

- The over-cap sentinel MUST cover **every** NULL-blob flaw ply of the game in the single write (not just the overflow), so the game fully clears the `allowed_pv_lines IS NULL` predicate and is never re-picked. Build the ply set from the flaws, not from `sentinel_lines` (which only holds un-walkable lines). The fully-walkable flaws must be included too.
- Do NOT reuse the `if not lease_positions:` branch — over-cap games have a non-empty `lease_positions`. Add a distinct `elif len(lease_positions) > MAX_SUBMIT_EVALS:` branch that sentinels all NULL-blob flaw plies (derive them from the flaw rows / `_build_flaw_blob_lease_positions` inputs, not just `sentinel_lines`).
- No token / submit change: over-cap games never return a lease, so `/flaw-blob-submit` and its token validation are untouched.
- Guests still excluded; tier-1/2/3 and the SEED-072 idle routing unchanged.
- Add a test: a synthetic game with > MAX_SUBMIT_EVALS walkable positions leases → 204, and afterward has zero NULL-blob flaws (all sentineled, no 500), while its existing tactic tags are unchanged.

## Acceptance / done-when

- A game with > 1024 flaw-blob positions no longer 500s `/flaw-blob-lease`; it gets `[]` sentinels for all its NULL-blob flaws and returns 204 in one pass.
- Such a game reaches zero NULL-blob flaws immediately (never re-picked by the tier-4 lottery).
- `/flaw-blob-lease` 500 rate → 0 in prod.
- No regression to normal (≤1024) games; existing tactic tags on the sentineled games are preserved; blob shape / gate logic for normal games unchanged.

## Cross-refs

- [[SEED-072]] — removing the idle `/lease` tier-4 fallthrough routed ALL tier-4 draining through `/flaw-blob-lease`, which is what surfaced this latent 500 at scale.
- `app/routers/eval_remote.py::flaw_blob_lease` (~779) and `::_build_flaw_blob_lease_positions`.
- `app/schemas/eval_remote.py::FlawBlobLeaseResponse` (positions `max_length=MAX_SUBMIT_EVALS`), `::FlawBlobSubmitRequest` (evals same cap), `MAX_SUBMIT_EVALS = 1024`.
