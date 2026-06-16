# Phase 121: Remote-worker tier-1 claiming - Context

**Gathered:** 2026-06-15
**Status:** Ready for planning
**Source:** SEED-048 (decisions locked 2026-06-15 explore session)

<domain>
## Phase Boundary

Let a remote eval worker (`scripts/remote_eval_worker.py`, added in Phase 120) claim
**tier-1** single-game "analyze" requests via the lease/submit contract, not just the
tier-3 idle backlog it drains today. This shortens click-to-pickup latency when the
**server pool is busy** (mid-game on another job): a second idle machine can pick up a
freshly-enqueued single-game analysis instead of the click waiting for the server to
finish its current game.

**First-come-first-served (FCFS).** Whichever machine claims first wins. The server's
in-process drain still usually wins tier-1 when it is idle (no network hop, no poll
interval), so this deliberately targets only the **server-busy overflow** case.

This is a 3-change backend phase with **no DB migration**.

</domain>

<decisions>
## Implementation Decisions

### Tier-1 claiming via the lease endpoint
- `POST /api/eval/remote/lease` MUST call `claim_eval_job` (tier-1 > tier-2 > tier-3,
  `lease_expiry` + `SKIP LOCKED`, stale-lease sweep) instead of `_claim_tier3_derived`.
- `claim_eval_job` in `app/services/eval_queue_service.py` already implements the tiered
  claim, lease semantics, and the stale-lease expiry sweep — reuse it, do not reimplement.
- Tier-3 still falls through as the derived path, unchanged. `SKIP LOCKED` is what
  guarantees the server's in-process drain and the remote worker never double-claim the
  same job.

### Thread `job_id` through lease → submit round-trip
- The lease response carries the claimed `eval_jobs.id` as an **opaque job token**; it is
  `None` for tier-3 claims (which come from the derived path, not `eval_jobs`).
- The worker echoes the same token back on submit.
- The submit handler stamps `eval_jobs.status='completed', completed_at=now()` **only when
  `job_id` is present**. Tier-3 keeps `job_id=None` and behaves exactly as today (no
  `eval_jobs` write).
- The token is opaque to the worker — it stores and returns it without interpreting it.

### Worker idle poll interval
- Drop `idle_sleep` default in `scripts/remote_eval_worker.py` from 5s to ~1s so an idle
  remote worker notices a freshly-enqueued tier-1 quickly.
- Only the empty-queue / 204 path sleeps. The busy path is already a tight loop, so this
  change affects **only** the idle-pickup case — exactly the one we care about.

### Schemas
- Add the opaque job-token field to the lease-response and submit-request Pydantic schemas.
  `None`/optional for the tier-3 case.

### Claude's Discretion
- Exact field naming for the job token in the Pydantic schemas (must be `Optional`/nullable).
- Internal structure of the submit-handler branch that stamps `eval_jobs`.
- How the soak/verification is structured (manual UAT vs. automated test), provided it
  confirms no tier-1/tier-3 double-claim and that submit correctly stamps `eval_jobs`.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase scope & locked decisions
- `.planning/seeds/SEED-048-remote-worker-tier1-claiming.md` — full rationale, FCFS scope,
  deferred follow-ons, breadcrumbs to exact line numbers.

### Code to modify
- `app/routers/eval_remote.py` — `lease_eval_game` (~line 291, currently
  `_claim_tier3_derived`) and `submit_eval` (~line 359, currently no `eval_jobs` write).
- `app/services/eval_queue_service.py` — `claim_eval_job` (tiered claim + lease sweep),
  `_claim_tier3_derived`, `enqueue_tier1_game`, `LEASE_TTL_SECONDS`.
- `scripts/remote_eval_worker.py` — lease loop, `idle_sleep` default, submit token echo.
- `app/models/eval_jobs.py` — `eval_jobs` schema, tier constants.
- Lease/submit Pydantic schemas (opaque job-token field).

</canonical_refs>

<specifics>
## Specific Ideas

- The submit `eval_jobs` stamp must be idempotent-safe under FCFS — a job already
  completed (or whose lease expired and was re-claimed) should not be corrupted by a late
  submit. Confirm the stamp behavior against `claim_eval_job`'s lease/sweep semantics.
- Verification needs a **soak**: confirm under concurrent server-drain + remote-worker load
  that (a) no tier-1/tier-3 job is double-claimed, and (b) submit correctly stamps
  `eval_jobs.status='completed'`.

</specifics>

<deferred>
## Deferred Ideas (explicit scope fence — DO NOT implement)

- **Bias tier-1 to the faster remote worker** (server pool grace-yields tier-1 for a short
  window so the fast machine claims first). This is what would actually route analysis to
  the faster box in the common idle case. Out of scope — FCFS overflow-only is the chosen
  simple version.
- **Interruptible tier-3** (chunking tier-3 leases into ply-batches and checking the tier-1
  queue between batches, so a worker pegged on a long tier-3 game can yield to tier-1).
  Out of scope.

</deferred>

---

*Phase: 121-remote-worker-tier1-claiming*
*Context gathered: 2026-06-15 from SEED-048 (locked explore-session decisions)*
