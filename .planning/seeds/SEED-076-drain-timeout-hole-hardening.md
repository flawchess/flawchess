---
id: SEED-076
status: open
planted: 2026-07-03
planted_during: /gsd-explore session investigating prod user 218's eval-chart gaps. Quantified 36 games / 642 opening-weighted hole plies stamped complete via the Path-C cap. Root cause (confirmed via Sentry FLAWCHESS-8B, `atomic-submit ... residual holes`, geo DE): a **weak Hetzner remote worker** ran the same engine (`_NODES_TIMEOUT_S = 5.0s`, engine.py:100) and timed out on high-branching opening positions on slower hardware, submitting partial evals; the server re-leased 3× and Path-C-stamped (`eval_remote.py:1300`). NOT the in-process server pool. Full evidence: `.planning/notes/eval-chart-opening-holes-root-cause.md`.
design_locked_during: /gsd-explore follow-up 2026-07-03 (chose the cache-aware incremental-lease approach below over the seed's original "don't stamp / reroute" lever, which needs a new lease-time attempts gate and is not quick-sized).
trigger_when: Next eval-pipeline / remote-worker phase, OR when Sentry FLAWCHESS-8B (`atomic-submit: stamping complete after MAX_EVAL_ATTEMPTS with residual holes`) recurs on a large single-user import, OR when a user reports eval-chart gaps again. Watch it when the remote fleet grows (more heterogeneous / weaker boxes) or when a slow worker's leases climb.
scope: quick (1 plan) — server-side only, on the atomic eval lease/submit pair. No new data model, no new column: reuse `full_eval_attempts` + `MAX_EVAL_ATTEMPTS` (existing bound) and the `opening_position_eval` cache. Add a regression test that simulates a worker submitting a partial (opening-missing) eval set and asserts (a) cached opening plies are filled server-side without a worker round-trip, and (b) genuinely-uncached residual holes stay bounded by Path C.
depends_on: none. The 36 existing prod rows were self-healed 2026-07-03 via `scripts/resweep_holed_games.py --db prod` (the paired self-heal TODO is done and removed); this seed is purely go-forward prevention.
---

# SEED-076: Harden `/atomic-submit` against weak-worker timeout holes

## The problem

The Path-C cap (D-116-07 no-loop invariant) is a *correctness* safety valve — it stops a
deterministically-unevaluable position from looping forever. But the **atomic eval path
skips the opening-cache dedup** that the in-process server pool has: `_apply_atomic_submit`
passes `dedup_map = {}` (`eval_remote.py:1241`), so the worker is expected to eval *every*
position from scratch, and `atomic-lease` re-leases the **whole game** on every retry
(`_collect_full_ply_targets` builds a target per ply regardless of whether it already has an
eval). A **weak worker** times out (`_NODES_TIMEOUT_S = 5s`) on the slowest positions
(openings, high branching factor), submits partial evals, and — because nothing fills the
holes from the warm cache and each retry re-grinds the same slow openings — the game hits
`MAX_EVAL_ATTEMPTS = 3` and gets Path-C-stamped `full_evals_completed_at` **permanently**,
even though the openings are trivially fillable from `opening_position_eval` (or by a stronger
worker).

Observed impact: a Hetzner worker on user 218's batch produced 36 games with 642
opening-weighted holes, all permanently stamped (Sentry FLAWCHESS-8B, 45 events). Scales
with how much a weak/slow worker is handed and gets worse as the remote fleet grows more
heterogeneous.

## Chosen design (LOCKED) — cache-aware incremental lease, no new column

Give the atomic path the dedup the in-process pool already has, and make its re-lease
incremental. Reuses `full_eval_attempts` + `MAX_EVAL_ATTEMPTS` as the bound (no new state).

1. **Atomic-lease** (`atomic_lease_eval_game` / `_build_lease_positions` /
   `_collect_full_ply_targets`, `eval_remote.py` + `eval_drain.py`): exclude plies whose eval
   is **already present** OR **available in `opening_position_eval`** from the leased
   positions. Reuse the in-process pool's exact dedup guards (`ply <= DEDUP_MAX_PLY`,
   non-flaw, non-terminal — see `_fetch_dedup_evals` read-side guards). Always keep the
   terminal eval-donor (SEED-044) and genuinely-uncached plies. → the lease is both
   **incremental** (skips already-eval'd plies) and **cache-aware** (skips cached openings),
   so a weak worker never re-grinds a position we can fill for free.

2. **Atomic-submit** (`_apply_atomic_submit`): replace the `dedup_map = {}` at
   `eval_remote.py:1241` with the real cache-backed lookup (mirror how `_full_drain_tick`
   builds its dedup_map) so the excluded-but-cached plies are filled server-side **before**
   `failed_ply_count` is computed. This keeps the Path-A completion decision correct even
   though those plies were never leased.

3. **Bounded retry unchanged** (Path A/B/C at `eval_remote.py:1268`): Path B stores the
   partial evals, does not stamp, increments `full_eval_attempts`; Path C accepts residual
   holes after `MAX_EVAL_ATTEMPTS`. This already handles "super-hard positions over and over"
   with no new column — genuinely-uncached hard positions are accepted after the cap, exactly
   as today. The net change is that the *fillable* (cached-opening) holes no longer reach the
   cap.

4. **Blobs untouched.** The timeout-holes are opening eval positions, which are almost never
   flaw plies, so they carry ~no MultiPV-2 blob work; the expensive blobs live on midgame
   flaw plies that attempt 1 already evaluated and blobbed. An incremental re-lease of just
   the residual opening eval-holes is therefore naturally blob-cheap. Edge case — a filled
   opening hole that turns out to sit on a flaw ply needing a blob — is already caught by the
   existing tier-4 blob backfill (`flaw-blob-lease`, `allowed_pv_lines IS NULL`), so no blob
   is lost.

## Plan-level details to verify (not decisions)

- **`failed_ply_count` must be computed over the whole game**, not just the leased subset, or
  a game with a cache-filled hole outside the lease would mis-decide Path A vs B/C.
- **The terminal eval-donor must survive the lease filter** (SEED-044 pitfall 3 — it has no
  eval and is not a hole; don't let the "skip already-eval'd" filter drop it).
- **The cache-guard predicate must match the pool's exactly** (`_fetch_dedup_evals` read-side
  guards) so a flaw ply is never wrongly filled from cache (flaw plies need a fresh eval +
  blob, not a dedup transplant).
- Regression test: simulate a worker submitting a partial (opening-missing) eval set and
  assert cached openings fill server-side without a worker round-trip AND uncached residual
  holes stay bounded by Path C (no permanent stamp of a fillable hole; no infinite re-lease).

## Directions considered but NOT chosen

- **"Don't stamp / reroute the timeout-hole" (the original primary lever).** Rejected as not
  quick-sized: the tier-1/2/3 claim predicate is `full_evals_completed_at IS NULL` with **no
  `full_eval_attempts` gate** (`eval_queue_service.py:371,402,450`), so the loop is broken
  *only* at submit-time by the Path-C stamp. Simply not-stamping re-opens the game to the
  same weak worker → infinite re-lease (the exact D-116-07 loop). Making it safe needs a new
  lease-time attempts gate across the mixed-fleet lease pair — a real design pass, not `/gsd-quick`.
- **Auto-resweep loop** (periodically clear markers via `resweep_holed_games()`). Rejected:
  the drain's Path C does not persist the incremented attempt count (`eval_drain.py:2688`),
  so `full_eval_attempts` is not a running memory; a genuinely-unevaluable ply would churn
  forever unless we add a convergence column (`eval_holes_reswept_at`). The chosen design
  avoids the churn entirely by filling from cache at lease time instead of re-arming.
- **Worker self-retry at a lower node budget** / **capability-aware leasing** — good
  complementary root-cause reducers for a later remote-worker phase, but heavier than this
  server-only change and not needed to close the observed failure.
