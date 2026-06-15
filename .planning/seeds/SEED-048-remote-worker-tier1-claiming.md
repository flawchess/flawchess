---
id: SEED-048
status: promoted (Phase 121, 2026-06-15)
planted: 2026-06-15
planted_during: Phase 120 remote eval worker (deployed; dev-machine worker running)
trigger_when: when you want a single-game "analyze" click to be picked up by a remote eval worker (not just the server pool) so a second machine shortens click-to-pickup latency when the server is busy
scope: small
---

# SEED-048: Let remote eval workers claim tier-1 (single-game) requests

## Why This Matters

Phase 120 added the remote eval worker (`scripts/remote_eval_worker.py`) which leases
work via `POST /api/eval/remote/lease`. That endpoint calls `_claim_tier3_derived`
**directly**, so the worker only drains the tier-3 idle backlog. It never sees tier-1
(explicit single-game "analyze" requests) — those live in the `eval_jobs` table and are
claimed only by the server's in-process drain (`claim_eval_job`, tier-1 > tier-2 > tier-3).
The remote submit path also never touches `eval_jobs.status`, so there's no machinery for
a remote worker to report a tier-1 job complete.

Goal: with a second (faster) machine running a worker, a single-game analysis click should
be able to get picked up by either machine, shortening click-to-pickup latency.

## The Simple Version (this seed's scope)

First-come-first-served. Whichever machine claims first wins.

1. **`lease` endpoint calls `claim_eval_job` instead of `_claim_tier3_derived`.**
   `claim_eval_job` already does tier-1 > tier-2 > tier-3, lease semantics (lease_expiry +
   SKIP LOCKED so server and remote never double-claim the same job), and the
   stale-lease expiry sweep. Tier-3 still falls through as the derived path, unchanged.
2. **Thread `job_id` through the lease → submit round-trip.** Lease response carries the
   claimed `eval_jobs.id` (None for tier-3). Submit echoes it; the submit handler stamps
   `eval_jobs.status='completed', completed_at=now()` when `job_id` is present. Tier-3
   keeps `job_id=None` and behaves exactly as today.
3. **Drop the worker idle poll `idle_sleep` 5s → ~1s** so an idle remote worker notices a
   freshly-enqueued tier-1 quickly. (Only the empty-queue/204 path sleeps; busy path is
   already a tight loop, so this only affects the idle-pickup case — exactly the one we
   care about.)

Files: `app/routers/eval_remote.py` (lease/submit handlers + auth unchanged),
`app/services/eval_queue_service.py` (`claim_eval_job` already does the work),
`scripts/remote_eval_worker.py` (idle_sleep default; echo job token on submit),
lease/submit Pydantic schemas (add the opaque job token field). No DB migration.

## Deliberate Limitation (FCFS, accepted)

Under FCFS the **server usually wins tier-1 when it's idle** — its in-process drain has no
network hop and no poll interval, so it grabs and evaluates the job *itself*, on the
(slower) server. The remote worker only gets tier-1 as **overflow**, when the server is
already mid-game on another job. So this change helps the **server-busy** case (today a
click waits for the server to finish its current game; with this, an idle remote worker can
take it) but does **not** route single-game analysis to the faster box in the common idle
case. This was chosen knowingly for simplicity (2026-06-15 explore session) — see the two
follow-on options below if that limitation starts to bite.

## Not In Scope (deferred follow-ons)

- **Bias tier-1 to the faster remote worker** — server pool grace-yields tier-1 for a short
  window if a remote worker has leased recently, so the fast machine claims it first; server
  falls back if no worker takes it. This is what actually delivers "the fast box does the
  analysis." Revisit if FCFS overflow-only isn't good enough.
- **Interruptible tier-3** — both machines process one whole game at a time, fanning all
  plies across their local pool. So the worst case for tier-1 pickup is "both machines
  mid-tier-3-game" (~50-60 plies). Fixing that means chunking tier-3 leases into ply-batches
  and checking the tier-1 queue between batches. Revisit if tier-1 still feels slow because
  the workers are pegged on a large tier-3 backlog 24/7.

## Scope Estimate

**Small** as a code change, but phase-sized (touches 3-4 files + schemas, needs a soak to
confirm no tier-1/tier-3 double-claim and that submit correctly stamps `eval_jobs`). Run
`/gsd-phase` (or `/gsd-mvp-phase`) when promoting this, not `/gsd-quick`.

## Breadcrumbs

- `app/routers/eval_remote.py:290` — `lease` endpoint (currently `_claim_tier3_derived`).
- `app/routers/eval_remote.py:358` — `submit` endpoint (currently no `eval_jobs` write).
- `app/services/eval_queue_service.py` — `claim_eval_job` (tiered claim + lease sweep),
  `_claim_tier3_derived`, `enqueue_tier1_game`, `LEASE_TTL_SECONDS=120`.
- `app/routers/imports.py:296` — `POST /eval/tier1/{game_id}` (tier-1 enqueue trigger).
- `app/models/eval_jobs.py` — `eval_jobs` schema, `TIER_EXPLICIT/AUTO_WINDOW/IDLE_BACKLOG`.
- `scripts/remote_eval_worker.py` — lease loop, `idle_sleep`, `EnginePool` driver.
