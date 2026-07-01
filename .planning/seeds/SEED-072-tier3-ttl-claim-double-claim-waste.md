---
id: SEED-072
status: dormant
planted: 2026-07-01
planted_during: post-Phase-146-deploy prod investigation. After deploying Phase 146 (offload live-submit forcing-line continuation eval to the remote fleet), the eval-worker fleet showed a ~5:1 full-ply submit-to-completion ratio — most worker capacity spent re-evaluating games another worker was already evaluating, starving the tier-4 flaw-blob (gating) drain. Root-caused live on prod. NOT a data-corruption or gating bug; spare-capacity waste only.
trigger_when: soon — implement next as a focused backend task (user's plan: a new session via /gsd-quick). It is not an outage (fresh games still complete ~620/hr, tier-4 still fills, no data loss), but Phase 146 made the deferred D-4 TTL-lease necessary, and the waste grows with worker concurrency. Do it deliberately, not under incident pressure.
scope: Small–Medium backend, eval queue only. Add an ephemeral TTL claim marker to the tier-3 idle lottery (app/services/eval_queue_service.py::_claim_tier3_derived) so a game currently being evaluated is not re-handed to other workers. Server-side + version-agnostic (covers the one worker the operator cannot update). Likely needs a lightweight persistence for the claim (games.tier3_leased_until column or a small claims table) → a migration → this may exceed true /gsd-quick size; scope it at plan time. DECIDED APPROACH: Option 1 — server-side ephemeral TTL-lease for tier-3 (the code's own deferred "D-4" endgame). Rejected alternatives: worker-side pacing (only reaches controllable workers, and to close the window you'd have to slow workers back toward the pre-146 rate, undoing Phase 146); plain SKIP LOCKED (the row lock releases when the claim SELECT commits, ~30s before the eval finishes, so it does not cover the eval window).
---

# SEED-072: tier-3 idle lottery double-claims games during the eval window → ~5:1 wasted worker capacity, starving the tier-4 gating drain

## Why This Matters

`_claim_tier3_derived` (`app/services/eval_queue_service.py:254`) is a **lock-free** two-level
Efraimidis–Spirakis lottery (recency-weighted user pick → recency-weighted game pick). It is
correct and works well **when there is a fat needs-engine backlog to spread picks across** — the
double randomization keeps concurrent workers on different games (docstring lines 307–311 explicitly
accept residual double-claims and note "Add FOR UPDATE SKIP LOCKED when multi-worker leasing is
added"; the "ephemeral TTL-lease escalation (D-4 'later')" is the deferred zero-collision endgame).

**Phase 146 unmasked the double-claim cost by removing the accidental pacing.** The double-claim
window is the *eval duration*, not submit frequency:

- A worker claims a tier-3 game, evaluates its full ply set (~30s, MultiPV-1) — the game stays
  `full_evals_completed_at IS NULL` and claimable the whole time — then submits.
- **Pre-146 cycle:** ~30s eval **+ up to ~120s blocked on the server's inline MultiPV-2 continuation
  walk** (the SEED-071 bottleneck) ≈ **~150s/game**. Slow submits were accidental back-pressure.
- **Post-146 cycle:** ~30s eval **+ instant submit** ≈ **~30s/game**. Workers cycle ~5× faster, so
  ~5× more workers claim the same still-NULL game during its eval window before anyone finishes it.

## Evidence (prod, 2026-07-01, right after the Phase 146 deploy)

- **~3,100 full-ply submits/hr but only ~620 distinct completions/hr** (~5:1). Measured repeatedly:
  ~200 idle submits / 5 min vs ~52 `full_evals_completed_at` stamps / 5 min.
- **`max(full_eval_attempts) = 2` across all games** → this is NOT Path-B re-lease churn (holes);
  the losing workers submit a game that a peer already completed → `_mark_full_evals_completed`
  no-ops (guarded on NULL), so no new completion, no attempt increment. Pure duplicate eval work.
- Backfill pools were essentially drained (non-guest needs-engine ≈ 0; lichess PV-backfill 4,991→0
  during the investigation), so the fleet was thrashing a thin fresh-game pool.
- **tier-4 flaw-blob gating drain starved:** blobs filled only ~260/hr (6,240 → 6,486 over ~50 min)
  because tier-3 (higher priority) kept the fleet busy and `/lease?scope=idle` rarely returned 204,
  so workers rarely fell through to rung-4 (`/flaw-blob-lease`). No `flaw-blob-lease` traffic seen.
- Red herrings ruled out during triage: the 239,675 `full_evals` NULL games are **guest** games,
  excluded from tier-3 by design (QUEUE-08, `u.is_guest = false`) — not a backlog and unrelated.
  Not a lock-collision-on-a-large-pool problem (the design is fine at scale). Not lichess-specific
  (remote workers already defer lichess PV-backfill to the in-process pool: `eval_remote.py:430`).

## Constraint that forces a server-side fix

The operator controls **4 of ~5 workers**; **one worker cannot be updated** (external/not theirs).
So any worker-side mitigation is permanently partial. Only a **server-side** claim marker is
version-agnostic and covers the uncontrolled worker.

## Decided approach (Option 1): ephemeral TTL claim marker on tier-3

When `_claim_tier3_derived` (and the HTTP `/lease?scope=idle` path in `eval_remote.py`) hands out a
game, stamp a short-lived claim so the lottery excludes it while it is being evaluated:

- **Claim on pick:** set `leased_until = now() + TIER3_CLAIM_TTL` for the picked game (TTL a bit
  longer than the worst-case eval, e.g. ~3–5 min — flaw-heavy games can take a while; err long).
- **Exclude in the lottery `WHERE`:** add `AND (g.tier3_leased_until IS NULL OR g.tier3_leased_until < now())`
  to both Step-1 user EXISTS, Step-2 game pick, and the residual fallback (keep the `:param`-bound,
  no-f-string convention).
- **Release:** implicit on completion (game leaves the NULL predicate). On expiry (dead worker),
  the TTL lets it be re-claimed. No explicit release needed, but a submit MAY clear it early.
- **Persistence:** tier-3 derived picks are `job_id=None` (table-less by design), and the HTTP lease
  is stateless across requests, so the claim must be DB-backed. Simplest: a nullable
  `games.tier3_leased_until timestamptz` column + a partial index compatible with
  `ix_games_needs_engine_full_evals`. Alternative: a tiny `tier3_claims(game_id, leased_until)`
  table. Decide at plan time; prefer the column if it does not bloat the hot partial index.
- **Idempotency preserved:** the existing self-dedup (game leaves the pool once `full_evals`
  stamped) stays; the TTL only removes the *concurrent* double-claim during the eval window.

## Acceptance / done-when

- Under real fleet concurrency, full-ply submit:completion ratio drops from ~5:1 toward ~1:1.
- The uncontrolled worker cannot double-claim a game already leased (server refuses to re-hand it).
- `/lease?scope=idle` returns 204 promptly once the needs-engine pool is truly drained, so workers
  fall through to rung-4 and tier-4 blob fill rate rises materially (target: use idle fleet capacity
  for gating instead of duplicate full-ply evals).
- No regression to tier-1/2 (explicit/entry) latency; no change to the tier-4 lottery (SEED-071/D-01)
  or the blob shape/gate logic. Guests still excluded.
- Sweep/expiry path tested (dead-worker claim eventually re-claimable).

## Cross-refs

- [[SEED-071]] — the phase that removed the accidental pacing (Phase 146, shipped 2026-07-01,
  prod `8dab0182`). This seed is the necessary follow-up it created.
- `app/services/eval_queue_service.py::_claim_tier3_derived` (docstring already names this as the
  deferred D-4 TTL-lease).
- `app/routers/eval_remote.py` `/lease` handler + `_apply_submit`.
