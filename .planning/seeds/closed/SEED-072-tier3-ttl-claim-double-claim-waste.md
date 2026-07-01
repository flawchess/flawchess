---
id: SEED-072
status: dormant
planted: 2026-07-01
planted_during: post-Phase-146-deploy prod investigation. After deploying Phase 146 (offload live-submit forcing-line continuation eval to the remote fleet), the eval-worker fleet showed a ~5:1 full-ply submit-to-completion ratio and the tier-4 flaw-blob (gating) drain barely progressed. Initially mis-diagnosed as a tier-3 double-claim/pacing problem; corrected by reading the deployed code — the real cause is tier-4 blob games being served through the wrong endpoint (see below). NOT a data-corruption or gating bug; wasted spare capacity + stalled gating backfill.
trigger_when: soon — small, high-value backend fix. Not an outage (fresh games still complete, no data loss), but the entire fleet's idle capacity is being burned re-evaluating already-complete games instead of filling gating blobs, so the tier-4 backfill is effectively stuck. A parallel /gsd-quick session began implementing the OLD (tier-3 TTL) approach — redirect it to the corrected fix in this seed.
scope: Small backend, eval queue only — a ~13-line deletion, no migration, no schema change. Remove the tier-4 fallthrough from `claim_eval_job(scope="idle")` so `/lease?scope=idle` returns 204 when tier-3 is empty and the worker falls through to its dedicated rung-4 `/flaw-blob-lease`. DECIDED APPROACH: Option 1 (corrected) — stop routing tier-4 games through the full-ply `/lease` path; let them drain only via the Phase-146 `/flaw-blob-lease` → `/flaw-blob-submit` rung. Rejected: tier-3 ephemeral TTL claim (the original framing of this seed) — it targets the wrong tier (tier-3 is empty; the churn is tier-4-via-/lease) and would not stop the re-serve loop.
---

# SEED-072: tier-4 blob games are served through the full-ply `/lease` path and can no longer drain there (Phase 146) → infinite re-serve loop, idle fleet capacity wasted, gating backfill stalled

## Corrected root cause (verified against deployed code, origin/production @ 8dab0182)

Phase 145 (v1.30) added tier-4 (the flaw-blob gating backfill) AND wired it into
`claim_eval_job(scope="idle")` as a fallthrough after tier-3. So `/lease?scope=idle` stopped
returning 204 on an empty tier-3 backlog and started returning tier-4 games instead. (This is why
workers stopped idling on a 0-backlog after v1.30 — there is now always a ~3.3M NULL-blob tier-4
backlog behind the empty tier-3.)

That was survivable pre-Phase-146. **Phase 146 broke the drain of tier-4-via-`/lease`** while
leaving the routing in place. Full deployed chain today:

1. Worker calls `POST /lease?scope=idle` (its rung 3).
2. tier-3 is empty (0 non-guest needs-engine games) → `claim_eval_job` falls through to
   `_claim_tier4_blob` → returns a tier-4 game (already `full_evals_completed_at`-complete, has
   NULL-blob flaws), `is_lichess_eval_game=False`, `tier=TIER_BLOB_BACKFILL`, `job_id=None`.
   (`eval_queue_service.py`, the `if scope == "idle":` block — the "Tier-3 empty → try tier-4
   blob-backfill" fallthrough.)
3. The `/lease` handler does **not** check `tier` — it only special-cases `is_lichess_eval_game`.
   So for this non-lichess claim it builds **full-ply** positions (`_build_lease_positions`) and
   returns a normal `LeaseResponse` (`eval_remote.py` `/lease` handler, ~415-473).
4. Worker full-ply **re**-evaluates the already-complete game (~30s) and submits to `/submit`.
5. **Phase 146 forced `blob_map={}` in `_apply_submit`.** So the submit re-applies evals (no-op on
   a complete game), `_mark_full_evals_completed` no-ops (already stamped), and **leaves the blobs
   NULL**. No blobs are ever written on this path anymore.
6. The game still has NULL-blob flaws → still matches `_claim_tier4_blob` → **re-served at step 2.
   Infinite loop.**

Because step 2 always finds a tier-4 game (huge backlog), `/lease?scope=idle` **never returns 204**,
so the worker **never reaches its new rung-4 `/flaw-blob-lease`** — the only path that post-146
actually writes blobs (worker MultiPV-2 on continuation FENs → `/flaw-blob-submit` → PvNode blobs +
D-07 gated retag). Net: the whole fleet burns idle capacity re-evaluating complete games via the
dead path, and the gating backfill is starved.

Pre-146 this same `/lease` path *worked*: `/submit` built the blobs from the worker's MultiPV-2
second-best (the expensive inline server walk = SEED-071), so tier-4 games drained via `/lease`.
Phase 146 removed that walk to kill the ReadTimeouts but **left tier-4 in the `/lease` fallthrough**
— a missed deletion. The dedicated `/flaw-blob-lease` rung was added to replace it, but the
fallthrough shadows it.

## Evidence (prod, 2026-07-01)

- ~3,100 full-ply submits/hr but only ~620 distinct completions/hr (~5:1). The ~2,500/hr excess are
  tier-4 games re-evaluated via `/lease` and re-submitted with no blob written and no new completion.
- `max(full_eval_attempts) = 2` across all games → not Path-B holes/churn; the re-submits are Path A
  no-ops on already-complete games (attempts untouched, `_mark_full_evals_completed` guarded on NULL).
- tier-3 pools are drained (non-guest needs-engine ≈ 0; lichess PV-backfill 4,991→0), so essentially
  every `/lease?scope=idle` hit is the tier-4 fallthrough — i.e. the churn is entirely tier-4-via-/lease,
  not tier-3 double-claims.
- tier-4 blobs barely move (6,240 → 6,486 over ~50 min) and **no `/flaw-blob-lease` traffic appears**
  in the backend access log — workers never get there.
- Red herrings ruled out: the 239,675 `full_evals`-NULL games are **guest** games (excluded by
  QUEUE-08, unrelated); the lock-free tier-3 two-randomization design is fine; not lichess-specific.

## Decided fix (corrected): remove the tier-4 fallthrough from the idle `/lease` path

In `claim_eval_job(scope="idle")`, delete the "Tier-3 empty → try tier-4 blob-backfill" block so
that when `_claim_tier3_derived` returns None the idle scope simply `return None` (→ 204):

```python
if scope == "idle":
    if not settings.EVAL_AUTO_DRAIN_ENABLED:
        return None
    async with async_session_maker() as session:
        derived = await _claim_tier3_derived(session)
    if derived is not None:
        game_id_idle, user_id_idle, is_lichess_eval_game_idle = derived
        return ClaimedJob(
            game_id=game_id_idle, user_id=user_id_idle,
            tier=TIER_IDLE_BACKLOG,
            is_lichess_eval_game=is_lichess_eval_game_idle, job_id=None,
        )
    return None   # <-- was: fall through to _claim_tier4_blob (DELETE that block)
```

Effect: `/lease?scope=idle` returns 204 once tier-3 is empty → the worker's rung-4
`/flaw-blob-lease` fires → tier-4 drains the correct Phase-146 way (MultiPV-2 → `/flaw-blob-submit`
→ blobs written + gated retag). The re-serve loop is gone and idle capacity goes to gating.

Server-side + version-agnostic: it fixes the behavior for **all** workers, including the one the
operator cannot update (that worker also stops receiving tier-4 games via `/lease`). Old workers with
no rung-4 will simply idle on 204 instead of churning — acceptable; the updated workers do the gating.

## Plan-time checks

- Confirm `/flaw-blob-lease` uses `_claim_tier4_blob` (or an equivalent tier-4 pick) to select the
  game whose continuation FENs it leases — so removing the `/lease` fallthrough does **not** orphan
  tier-4 draining, only re-routes it. (If `/flaw-blob-lease` selects differently, `_claim_tier4_blob`
  may become dead code reachable only by tests — fine, note it.)
- The Phase-146 D-01 recency ordering inside `_claim_tier4_blob` stays relevant only if
  `/flaw-blob-lease` uses it; verify and keep.
- The bundled `scope=None` path (legacy un-updated workers) also falls tier-1>2>3>4; decide whether
  it should keep tier-4 (it has the same broken-drain problem post-146). Safer to remove tier-4 from
  the bundled path too, or document why it's retained.
- Guests still excluded; no change to tier-1/2 (explicit/entry) or the blob shape / gate logic.

## Acceptance / done-when

- `/lease?scope=idle` returns 204 when the non-guest needs-engine (tier-3) pool is empty.
- `/flaw-blob-lease` traffic appears in the backend log and tier-4 blob-fill rate rises materially.
- Full-ply submit:completion ratio drops from ~5:1 toward ~1:1 (no more re-serve of complete games).
- No regression to tier-1/2 latency; guests still excluded; blob shape / gate logic unchanged.
- Test: with tier-3 empty and tier-4 non-empty, `claim_eval_job(scope="idle")` returns None (not a
  TIER_BLOB_BACKFILL job).

## Superseded framing (do not implement)

The original version of this seed proposed an **ephemeral TTL claim on tier-3** (`tier3_leased_until`
column, exclude leased games from the lottery). That is the WRONG fix: tier-3 is empty, so there are
no tier-3 double-claims to prevent; the observed churn is entirely tier-4 games routed through
`/lease`. A tier-3 TTL would add a migration and complexity without stopping the re-serve loop. If a
residual tier-3 double-claim concern ever appears under a genuinely fat tier-3 backlog, revisit the
TTL/SKIP-LOCKED idea as a separate, lower-priority hardening — but it is NOT this fix.

## Cross-refs

- [[SEED-071]] — Phase 146 (shipped 2026-07-01, prod `8dab0182`) removed the inline server walk that
  used to fill tier-4 blobs on the `/lease` path; this seed removes the now-dead routing it left behind.
- `app/services/eval_queue_service.py::claim_eval_job` (the `scope == "idle"` block — delete the
  tier-4 fallthrough) and `::_claim_tier4_blob`.
- `app/routers/eval_remote.py` `/lease` handler (~415-473, no tier check), `_apply_submit`
  (`blob_map={}`), and the `/flaw-blob-lease` + `/flaw-blob-submit` rung-4 endpoints.
