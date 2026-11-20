---
id: SEED-261119-c7l
status: closed. Resolved by commit 8d315d777 on main (2026-11-19, release #489).
planted: 2026-11-19
planted_during: Phase 252 plan 07 (prod flaw-line re-walk running, about 2,300 games per hour, 2.6 weeks projected)
trigger_when: now. The prod re-walk runs until about 2026-12-07 and every day without the lease wastes worker time. Also before the benchmark re-walk (Phase 252 plan 08).
scope: small. One backend change in the tier-4 claim, tests, one prod deploy. No worker release.
---

# SEED-261119-c7l: Claim lease for the tier-4 flaw-line backfill

## Problem

`_claim_tier4_blob` (`../../../app/services/eval_queue_service.py`) is a plain-SELECT lottery with no lock and no
lease. `/flaw-blob-lease` (`../../../app/routers/eval_remote.py`) hands the picked game to the worker and records
nothing. Until that worker submits, every other worker can draw the same game. The second submit finds
nothing pending (`apply_flaw_blob_results` returns `nothing_pending`) and its engine work is discarded.

This was harmless while tier 4 was a large, slowly drained backlog. The Phase 252 feeder
(`../../../scripts/repair_short_lines.py feed`) keeps only 150 to 500 games pending at a time, and the lottery
weights concentrate the draw on recently active users.

## Evidence (prod, 2026-11-19, read-only)

- Snapshot of the pending pool: 460 games, 71 users. Per-pick probabilities reproduced from the lottery
  weights (user recency half-life 1 day plus floor, game recency half-life 30 days plus floor, TC
  multiplier): sum of squared probabilities 0.0655, i.e. an effective pool of about 15 games. The most
  likely game had a 13.7% chance per pick.
- Five version-3 workers, one lease each, 4 to 15 seconds per game.
- Estimate from those two facts: 20 to 30% of re-walks are done twice. This is an estimate from one
  snapshot. It was not measured: a discarded duplicate returns before the heartbeat hook, so
  `worker_heartbeats.submit_count` and `evals_submitted` do not count it.

## What to build

A short lease on the tier-4 pick so a game handed out is not drawn again until it is submitted or the
lease expires. Two shapes, to be decided in planning:

1. A nullable `games.blob_leased_until` timestamp, set when `/flaw-blob-lease` returns positions and
   excluded by the lottery while in the future. Needs a migration. Keep the existing predicate
   `full_evals_completed_at IS NOT NULL AND blobs_completed_at IS NULL` in exactly its current clause form
   so `ix_games_blob_backfill_pending` still matches; add the lease condition as an extra filter.
2. An in-process map of game id to expiry in the backend. No migration, lost on restart (harmless), but
   only correct if prod serves these endpoints from a single process. Check that first.

Requirements either way:

- The lease expires by itself (a crashed worker must not block a game). TTL from the observed worst cycle:
  see the timeout notes at the top of `../../../scripts/remote_eval_worker.py` (up to about 500 s at `--workers 1`).
- When every pending game is leased, the claim returns "no work". On prod the worker then tries rung 5
  (best-move backfill) and sleeps; that is acceptable. Do not fall back to handing out a leased game.
- The bundled server-pool path (`claim_eval_job`, consumed by `eval_drain._full_drain_tick`) and
  `_blob_backfill_pending` (added in Phase 252, commit c58e57c18) use the same pick and must respect the
  lease, otherwise the server pool collides with the fleet.
- All-sentinel and over-cap branches of `/flaw-blob-lease` stamp the game and return 204; they need no
  lease.
- Add a way to see collisions afterwards, for example a counter or log line when a submit ends in
  `nothing_pending`. Today they are invisible.
- Tests must prove it: two consecutive claims with one pending game return the game once; an expired
  lease is claimable again; revert the fix and watch the test fail.

## Second finding, not yet understood

Per-worker throughput over 323 s on 2026-11-19 (prod, tier 4 only):

| Worker | Games/h | Evals/s | Seconds per game | Evals per game |
|---|---|---|---|---|
| amalie-pc | 813 | 6.5 | 4.4 | 28.8 |
| amalie-nb | 524 | 4.5 | 6.9 | 31.1 |
| 5weldaqh | 412 | 3.3 | 8.7 | 28.8 |
| mqvsj27e | 479 | 3.2 | 7.5 | 23.9 |
| 3cur1kzs | 234 | 1.6 | 15.4 | 24.7 |

A game is about 29 positions, each a 1M-node MultiPV-2 search. A worker holds one lease at a time and
spreads it over its engines, so a machine with many engines finishes the searches in one or two seconds
and then spends the rest of the cycle on HTTP: three empty lease calls (rungs 1 to 3), the blob lease,
and a submit that runs the retag and the Maia re-score on the server. If the two home machines run many
engines, they are mostly idle in this lane. Not verified: the `--workers` values of those machines are
not visible from the database, and discarded duplicates also lower these numbers.

Cheap test before building anything: start a second worker process on one large machine and see whether
its games per hour add up. If they do, either document "several processes per machine" for this lane or
let `/flaw-blob-lease` return several games per call. More concurrent claimers raise the collision rate,
so do this after the lease.

## Constraints

- Prod claim order stays tier 1 > tier 3 > tier 4 > tier 4b.
- Do not stop or restart the running prod feeder. A deploy restarts the backend; the feeder and the
  workers tolerate that (they retry), but check the feeder is still alive afterwards with
  `uv run python scripts/repair_short_lines.py status --db prod`.
- Deploy only through `../../../bin/deploy.sh` or the deploy skill, with the owner's go-ahead.
