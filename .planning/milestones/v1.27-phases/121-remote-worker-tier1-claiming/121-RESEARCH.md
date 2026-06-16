# Phase 121: Remote-worker tier-1 claiming - Research

**Researched:** 2026-06-15
**Domain:** Eval queue service / remote worker protocol
**Confidence:** HIGH

## Summary

This is a 3-change backend phase with no DB migration. All the hard work already
exists: `claim_eval_job` in `eval_queue_service.py` implements the full tiered claim
(tier-1 > tier-2 > tier-3) with SKIP LOCKED and stale-lease sweep, and already
returns `ClaimedJob.job_id` as `int | None`. The lease endpoint currently bypasses
it and calls `_claim_tier3_derived` directly. The changes are: (1) wire the lease
handler to `claim_eval_job` instead; (2) thread the opaque `job_id` token through
lease response and submit request so the submit handler can stamp `eval_jobs`; (3)
lower `DEFAULT_IDLE_SLEEP` from 5.0 s to 1.0 s.

The main implementation risk is the `EVAL_AUTO_DRAIN_ENABLED` gate inside
`claim_eval_job`: the gate blocks tier-3 (idle backlog) when the flag is False, but
it does NOT block tier-1/tier-2. The lease handler must pass through the gate
transparently — `claim_eval_job` already handles this correctly; the handler just
needs to call it and handle `None` as it does today (return 204). No gate bypass is
needed or desired.

The submit-handler `eval_jobs` stamp must guard against late submits: use the same
`WHERE status = 'leased'` predicate already present in `eval_drain._full_drain_tick`
and `report_job_complete`, so a job whose lease expired and was re-claimed cannot be
corrupted by a stale submit.

**Primary recommendation:** Wire `lease_eval_game` to call `claim_eval_job(worker_id="remote-worker")`, carry `ClaimedJob.job_id` in the lease response, echo it in the submit request, stamp in `_apply_submit` when present, lower `DEFAULT_IDLE_SLEEP` to 1.0.

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- `POST /api/eval/remote/lease` MUST call `claim_eval_job` (tier-1 > tier-2 > tier-3,
  `lease_expiry` + `SKIP LOCKED`, stale-lease sweep) instead of `_claim_tier3_derived`.
- `claim_eval_job` in `app/services/eval_queue_service.py` already implements the tiered
  claim, lease semantics, and the stale-lease expiry sweep — reuse it, do not reimplement.
- Tier-3 still falls through as the derived path, unchanged. `SKIP LOCKED` is what
  guarantees the server's in-process drain and the remote worker never double-claim the
  same job.
- The lease response carries the claimed `eval_jobs.id` as an opaque job token; it is
  `None` for tier-3 claims (which come from the derived path, not `eval_jobs`).
- The worker echoes the same token back on submit.
- The submit handler stamps `eval_jobs.status='completed', completed_at=now()` only when
  `job_id` is present. Tier-3 keeps `job_id=None` and behaves exactly as today (no
  `eval_jobs` write).
- Drop `idle_sleep` default in `scripts/remote_eval_worker.py` from 5s to ~1s.
- Add the opaque job-token field to the lease-response and submit-request Pydantic schemas.
  `None`/optional for the tier-3 case.

### Claude's Discretion
- Exact field naming for the job token in the Pydantic schemas (must be `Optional`/nullable).
- Internal structure of the submit-handler branch that stamps `eval_jobs`.
- How the soak/verification is structured (manual UAT vs. automated test), provided it
  confirms no tier-1/tier-3 double-claim and that submit correctly stamps `eval_jobs`.

### Deferred Ideas (OUT OF SCOPE)
- Bias tier-1 to the faster remote worker (server pool grace-yields tier-1 for a short
  window so the fast machine claims first).
- Interruptible tier-3 (chunking tier-3 leases into ply-batches and checking the tier-1
  queue between batches).
</user_constraints>

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Claim eval job (tiered) | API / Backend | — | `claim_eval_job` owns sessions, SKIP LOCKED, sweep |
| Lease response payload | API / Backend | — | Router assembles positions from DB |
| Submit eval + stamp eval_jobs | API / Backend | — | Server owns all storage convention (D-2) |
| Worker idle poll interval | Worker script | — | CLI constant in `scripts/remote_eval_worker.py` |
| job_id token threading | API schemas + Worker | — | Token opaque to worker; interpreted only by server |

---

## Current Code: Exact Signatures and Behavior

### `claim_eval_job` (eval_queue_service.py)

```python
async def claim_eval_job(
    worker_id: str = WORKER_ID_SERVER_POOL,
) -> ClaimedJob | None:
```

Returns `ClaimedJob | None`. `ClaimedJob` is a frozen dataclass:

```python
@dataclass(frozen=True)
class ClaimedJob:
    game_id: int
    user_id: int
    tier: int
    is_lichess_eval_game: bool
    job_id: int | None  # None for tier-3 derived pick
```

`job_id` is `None` exactly when the claim fell through to tier-3 (`_claim_tier3_derived`).
For tier-1 and tier-2, `job_id` is the `eval_jobs.id` of the leased row.

**Tier-3 gate:** `claim_eval_job` checks `settings.EVAL_AUTO_DRAIN_ENABLED` before
calling `_claim_tier3_derived`. If False, it returns `None` instead of a tier-3 pick.
Tier-1/tier-2 picks are NEVER gated by this flag. This is exactly the right behavior
for the lease endpoint — a remote worker calling it with only tier-3 available on a dev
machine (where `EVAL_AUTO_DRAIN_ENABLED=False`) gets `None` → 204, which is correct.

### `_claim_tier3_derived` (eval_queue_service.py)

```python
async def _claim_tier3_derived(
    session: AsyncSession,
) -> tuple[int, int, bool] | None:
```

Returns `(game_id, user_id, is_lichess_eval_game)` or `None`. **Shape mismatch:** the
current lease handler destructures this 3-tuple directly after calling it. After the
change, the handler will call `claim_eval_job` which returns `ClaimedJob` — a different
type. The handler needs to be rewritten to read from `ClaimedJob` fields, not a 3-tuple.

### `lease_eval_game` handler (eval_remote.py, line 290–355)

Current behavior:
1. Opens `read_session`, calls `_claim_tier3_derived(read_session)` — the session is
   passed in (the handler controls it).
2. Destructures `(game_id, user_id, is_lichess_eval_game) = claim`.
3. Opens a second `read_session` to load PGN + `game_positions`.
4. Calls `_build_lease_positions(...)`.
5. Returns `LeaseResponse(game_id, user_id, is_lichess_eval_game, positions, leased_at)`.

**After the change:** `claim_eval_job` opens its OWN sessions internally and commits
before returning — the handler must not pass a session to it. The session-management
pattern changes from "caller-owned session" to "service-owned sessions". Steps 2 onward
stay the same, reading from `ClaimedJob` fields instead of the 3-tuple.

The `import` statement at line 54:
```python
from app.services.eval_queue_service import _claim_tier3_derived
```
becomes:
```python
from app.services.eval_queue_service import claim_eval_job
```
(keep `_claim_tier3_derived` removed — it is no longer called directly by the handler;
`claim_eval_job` calls it internally for tier-3).

**`worker_id` for the remote worker:** The server drain uses `WORKER_ID_SERVER_POOL =
"server-pool"`. The remote worker should supply a distinct identity, e.g.
`"remote-worker"`. This is Claude's discretion (any stable string works); it is used
for `eval_jobs.leased_by` and future debugging.

### `submit_eval` handler + `_apply_submit` (eval_remote.py, line 358–385 + 154–282)

Current behavior: receives `SubmitRequest(game_id, sf_version, evals)`. The
`_apply_submit` function does the full write path (evals, flaws, oracle, markers) but
does NOT touch `eval_jobs`. `stamp_complete` gates `_signal_flaw_completion`.

**After the change:** when `body.job_id is not None`, `_apply_submit` (or the handler
inline) must add an `eval_jobs` stamp inside the write session. The exact inline
pattern from `eval_drain._full_drain_tick` (lines 1531–1542) is the model:

```python
if stamp_complete and job_id is not None:
    jobs_table = EvalJob.__table__
    now_ts = datetime.now(timezone.utc)
    await write_session.execute(
        update(jobs_table)  # ty: ignore[invalid-argument-type]
        .where(
            jobs_table.c.id == job_id,
            jobs_table.c.status == "leased",  # idempotency / late-submit guard
        )
        .values(status="completed", completed_at=now_ts)
    )
```

The `WHERE status = 'leased'` predicate is the idempotency/late-submit guard: if the
lease expired and was re-claimed (status is now "leased" again for the new claimant, or
"completed" if it finished), this UPDATE silently skips the stale submit. This is exactly
right and consistent with how `_full_drain_tick` handles it.

**Path B (holes remain, under cap):** the drain does NOT stamp the job in this path
(the game stays pending for retry). For the remote submit path, the same decision tree
applies: stamp `eval_jobs` only in paths A and C (when `stamp_complete=True`).

### `LeaseResponse` schema (eval_remote.py)

Current fields:
```python
class LeaseResponse(BaseModel):
    game_id: int
    user_id: int
    is_lichess_eval_game: bool
    positions: list[LeasePosition]
    leased_at: datetime
```

Add `job_id: int | None = None` (optional, nullable). The worker reads this and echoes
it in the submit. Naming is Claude's discretion; `job_id` is the obvious choice.

### `SubmitRequest` schema (eval_remote.py)

Current fields:
```python
class SubmitRequest(BaseModel):
    game_id: int
    sf_version: str
    evals: list[SubmitEval]
```

Add `job_id: int | None = None` (optional, nullable). Default `None` preserves backward
compatibility — an old worker that doesn't send this field gets the tier-3 behavior.

### `SubmitResponse` (eval_remote.py)

No change needed. The response already carries `stamp_complete` and `failed_ply_count`.

### Worker script (scripts/remote_eval_worker.py)

`DEFAULT_IDLE_SLEEP: float = 5.0` at line 54 → change to `1.0`.

The submit payload at lines 168–175:
```python
submit_resp = await client.post(
    "/api/eval/remote/submit",
    json={
        "game_id": game_id,
        "sf_version": sf_version,
        "evals": evals,
    },
)
```

Add `"job_id": data.get("job_id")` (reads the opaque token from the lease response dict,
echoes it back). The worker does not interpret or validate it.

The lease response dict is already read at:
```python
data = lease_resp.json()
game_id = data["game_id"]
positions = data["positions"]
```

Add `job_id = data.get("job_id")` here, then include it in the submit payload.

### `EvalJob` model (eval_jobs.py)

No changes. The `status`, `completed_at`, `leased_by`, and `lease_expiry` columns
already exist. `TIER_EXPLICIT`, `TIER_AUTO_WINDOW`, `TIER_IDLE_BACKLOG` constants are
already exported from this module.

---

## Shape Compatibility Analysis

This is the central question: can the lease handler swap `_claim_tier3_derived` for
`claim_eval_job` cleanly?

| Field | `_claim_tier3_derived` returns | `claim_eval_job` returns (ClaimedJob) |
|-------|-------------------------------|----------------------------------------|
| `game_id` | `tuple[0]` | `.game_id` |
| `user_id` | `tuple[1]` | `.user_id` |
| `is_lichess_eval_game` | `tuple[2]` | `.is_lichess_eval_game` |
| `job_id` | (not returned) | `.job_id` (`None` for tier-3) |
| `tier` | (not returned) | `.tier` (informational) |

The handler currently destructures `game_id, user_id, is_lichess_eval_game = claim` —
this must be rewritten to `claim.game_id`, `claim.user_id`, `claim.is_lichess_eval_game`.
Otherwise the semantics are identical: tier-3 claims still exist (via `claim_eval_job`'s
fallthrough to `_claim_tier3_derived` internally), still return
`is_lichess_eval_game=True/False`, and the handler's existing lichess-game 204 guard
still works unchanged.

**The session argument changes:** `_claim_tier3_derived` takes a caller-supplied session;
`claim_eval_job` opens its own sessions. The first `async with async_session_maker() as
read_session: claim = await _claim_tier3_derived(read_session)` block must be replaced
by a plain `claim = await claim_eval_job(worker_id="remote-worker")` call with no
session context.

---

## Concurrency / Idempotency Analysis

### Double-claim prevention (tier-1)

`_claim_queued_job` uses `SELECT FOR UPDATE OF ej SKIP LOCKED`. Two concurrent callers
(server drain and remote worker) cannot both claim the same `eval_jobs` row: whichever
runs the CTE UPDATE first locks and updates the row; the other's `FOR UPDATE SKIP LOCKED`
skips it and gets `None` (falls through to tier-3). This is guaranteed by PostgreSQL's
SKIP LOCKED — no application-level guard is needed.

### Double-claim prevention (tier-3)

`_claim_tier3_derived` has NO locking (noted in its docstring: "two concurrent workers
can pick the same game (double-claim)"). This is pre-existing and accepted (D-7: wasted
eval cycles are idempotent). Phase 121 does not change this behavior.

### Late-submit hazard (job_id stamp)

Race: remote worker finishes evaluating game, lease expires (120s), server re-claims the
job (status back to 'leased'), remote worker submits with the old `job_id`.

With `WHERE status = 'leased'` predicate:
- If the lease expired and the re-claim has not yet run: job is still 'leased' with the
  NEW `lease_expiry`. The late submit's UPDATE matches and stamps 'completed'. This is
  harmless: the evals + flaws are already written idempotently (ON CONFLICT DO NOTHING
  for flaws, idempotent oracle UPDATE). The re-claim was for the same `job_id` (same
  row), so stamping it completed prevents the server from re-evaluating unnecessarily.
- If the re-claim ran and the server stamped 'completed' first: status is 'completed',
  the late submit's `WHERE status = 'leased'` misses, UPDATE is a no-op. Correct.
- If the game was deleted (CASCADE): the `eval_jobs` row is gone, UPDATE is a no-op.
  Correct.

**Conclusion:** the late-submit guard is sufficient. No additional idempotency mechanism
is needed. The existing `WHERE status = 'leased'` pattern (from `eval_drain`) must be
copied exactly into `_apply_submit`.

### Path B (holes remain) and the eval_jobs row

In Path B, the game's `full_evals_completed_at` is NOT set and the `eval_jobs` row stays
'leased'. The stale-lease sweep at the top of the next `claim_eval_job` call will requeue
it to 'pending' after 120s if the worker doesn't re-submit. Since the remote worker
evaluates ALL plies in one shot and submits once, holes in Path B will be left for the
server drain to pick up on the next tick (the row returns to 'pending' via sweep). The
submit does not need to handle Path B specially for the `eval_jobs` stamp: stamp only
when `stamp_complete=True`.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead |
|---------|-------------|-------------|
| Tiered claim with SKIP LOCKED | Custom SQL | `claim_eval_job` (already in eval_queue_service.py) |
| Lease sweep | Custom requeue | `_sweep_expired_leases` called inside `claim_eval_job` |
| eval_jobs stamp | Custom UPDATE | Pattern from `eval_drain._full_drain_tick` lines 1531–1542 |
| Idempotency guard | Check-then-set | `WHERE status = 'leased'` predicate on the UPDATE |

---

## Common Pitfalls

### Pitfall 1: Calling `claim_eval_job` inside a caller-owned session

`claim_eval_job` opens its own sessions internally. Do NOT call it inside an `async with
async_session_maker()` block. The current lease handler has such a block for
`_claim_tier3_derived`; replace the whole block with a bare `await claim_eval_job(...)`.

### Pitfall 2: Forgetting the `EVAL_AUTO_DRAIN_ENABLED` gate interaction

`claim_eval_job` gates tier-3 on `EVAL_AUTO_DRAIN_ENABLED`. In dev (default False), a
remote worker will get 204 when only tier-3 is available. This is correct behavior but
must be documented in the test fixtures (monkeypatch `EVAL_AUTO_DRAIN_ENABLED=True` when
testing tier-3 fallthrough via `claim_eval_job`).

### Pitfall 3: Stamping `eval_jobs` in Path B

The drain does NOT stamp the job in Path B (holes remain, under cap). The submit handler
must follow the same decision: stamp only when `stamp_complete=True`. Stamping on every
submit would mark the job 'completed' even when the game needs a retry.

### Pitfall 4: Omitting `WHERE status = 'leased'` on the stamp UPDATE

Without the status guard, a late submit can corrupt a job that was re-claimed and is
mid-evaluation by the server. Always use `WHERE status = 'leased'` exactly as in
`eval_drain._full_drain_tick`.

### Pitfall 5: Worker ID collision

The remote worker must supply a distinct `worker_id` (e.g. `"remote-worker"`) to
`claim_eval_job`, not `WORKER_ID_SERVER_POOL` (`"server-pool"`). The `leased_by` column
in `eval_jobs` records which worker holds the lease; mixing identities makes operational
debugging impossible.

### Pitfall 6: `_claim_tier3_derived` still imported after the change

The `import` at `eval_remote.py` line 54 imports `_claim_tier3_derived`. After the
change, the handler no longer calls it directly. Remove the import to satisfy Knip (CI
dead-export check) and `ruff check`.

---

## Architecture Patterns

### System Architecture Diagram

```
Remote Worker                 FlawChess API                 PostgreSQL
─────────────                 ─────────────                 ──────────
POST /lease       ──────────> lease_eval_game()
                              claim_eval_job("remote-worker")
                              ├─ _sweep_expired_leases()  --> eval_jobs (reset stale)
                              ├─ _claim_queued_job()      --> eval_jobs SKIP LOCKED
                              │  (tier-1 or tier-2)            UPDATE leased
                              └─ if None: _claim_tier3_derived() --> games (derived)
                              Build LeaseResponse
                              + job_id (int|None)
<── 200 (positions+job_id) ───

[evaluate locally via EnginePool]

POST /submit      ──────────> submit_eval()
  + job_id                    _apply_submit()
                              ├─ write evals, flaws, oracle (idempotent)
                              ├─ stamp full_evals_completed_at (if complete)
                              └─ if job_id and stamp_complete:
                                   UPDATE eval_jobs SET status='completed'
                                   WHERE id=job_id AND status='leased'
<── 200 (stamp_complete, …) ──
```

### Recommended Change Structure

No new files needed. All changes are edits to existing files:

```
app/schemas/eval_remote.py      — add job_id: int | None = None to LeaseResponse + SubmitRequest
app/routers/eval_remote.py      — swap _claim_tier3_derived → claim_eval_job; thread job_id
app/services/eval_queue_service.py  — no changes (claim_eval_job already correct)
scripts/remote_eval_worker.py   — DEFAULT_IDLE_SLEEP 5.0 → 1.0; echo job_id on submit
```

---

## Existing Tests: What to Sit Alongside

### `tests/test_eval_worker_endpoints.py`

Phase 120 integration tests for lease/submit. Key patterns used:

- `_make_client()` — `httpx.AsyncClient` with `ASGITransport`.
- `_patch_router_session(monkeypatch, session_maker)` — patches `app.routers.eval_remote.async_session_maker`.
- `monkeypatch.setattr(eval_remote_module, "_claim_tier3_derived", AsyncMock(...))` — controls which game is leased without hitting the lottery.

After the change, tests that mock the claim function must switch from mocking
`_claim_tier3_derived` to mocking `claim_eval_job` (now the function called by the
handler). Tests that exercise the full stack (no mock) must ensure an `eval_jobs` row
exists with `status='pending'` so `_claim_queued_job` can pick it up, OR set
`EVAL_AUTO_DRAIN_ENABLED=True` to allow tier-3 fallthrough.

### `tests/services/test_eval_queue.py`

DB-level queue tests. New tests for Phase 121 can sit in this file or a new
`tests/test_eval_worker_endpoints.py` test class. The session-maker fixture pattern
(`monkeypatch.setattr(svc, "async_session_maker", queue_session_maker)`) is reusable.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest + pytest-asyncio + pytest-xdist |
| Config file | `pytest.ini` (or `pyproject.toml [tool.pytest]`) |
| Quick run | `uv run pytest tests/test_eval_worker_endpoints.py -x` |
| Full suite | `uv run pytest -n auto -x` |

### Phase Requirements → Test Map

| Req | Behavior | Test Type | Automated Command | Notes |
|-----|----------|-----------|-------------------|-------|
| R1 | Lease endpoint returns tier-1 `job_id` when a tier-1 job is pending | Integration | `pytest tests/test_eval_worker_endpoints.py::... -x` | New test, alongside existing lease tests |
| R2 | Lease endpoint returns `job_id=None` for tier-3 claim | Integration | Same file | Verifies None propagates correctly |
| R3 | Submit with `job_id` stamps `eval_jobs.status='completed'` | Integration | Same file | New test using seeded `eval_jobs` row |
| R4 | Submit without `job_id` (tier-3 path) does NOT touch `eval_jobs` | Integration | Same file | Assert no eval_jobs write |
| R5 | Late submit (job re-claimed) does not corrupt `eval_jobs` | Integration | Same file | Set status to something other than 'leased', verify no-op |
| R6 | `DEFAULT_IDLE_SLEEP` is 1.0 | Unit (constant check) | `pytest tests/test_eval_worker_endpoints.py -k idle_sleep` or inline assert | Simple constant assertion |
| R7 | No double-claim under concurrent server+remote calls | Soak (manual UAT or serial concurrency test) | Manual or pytest with two concurrent claim calls | SKIP LOCKED guarantee is DB-level; confirmed by existing QUEUE-06 tests |

### Wave 0 Gaps

- [ ] New test class `TestTier1Claiming` in `tests/test_eval_worker_endpoints.py` covering R1, R2, R3, R4, R5.
- [ ] Existing `test_lease_no_pending_games` and `test_lease_returns_positions` mock
  `_claim_tier3_derived` directly — these must be updated to mock `claim_eval_job`
  (or the tests become wrong after the import swap).

**Existing tests that MUST be updated (not just new tests):**

`tests/test_eval_worker_endpoints.py`:
- `test_lease_no_pending_games` — patches `eval_remote_module._claim_tier3_derived`; must patch `eval_remote_module.claim_eval_job` instead (or patch at the service level).
- `test_lease_returns_positions` — same; the mock return must change from a 3-tuple `(game_id, user_id, False)` to a `ClaimedJob(game_id=..., user_id=..., tier=3, is_lichess_eval_game=False, job_id=None)`.

### Sampling Rate

- Per task commit: `uv run pytest tests/test_eval_worker_endpoints.py -x`
- Per wave merge: `uv run pytest -n auto -x`
- Phase gate: full suite green before `/gsd-verify-work`

---

## Security Domain

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V5 Input Validation | yes | Pydantic v2 on `SubmitRequest.job_id` (`int | None`) |
| V4 Access Control | yes | `require_operator_token` dependency unchanged — both endpoints still require the operator token |
| V6 Cryptography | no | — |

**`job_id` trust boundary:** The `job_id` in the submit body is supplied by the remote
worker (an operator-authenticated machine, not an end-user). The submit handler trusts
it enough to stamp `eval_jobs` but uses `WHERE status = 'leased'` to limit blast radius:
the worst a compromised/buggy worker can do with a crafted `job_id` is mark an arbitrary
`leased` eval_job as `completed`, skipping its evaluation. This is acceptable for an
operator-authenticated endpoint. No additional validation is needed.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `worker_id="remote-worker"` is a safe distinct identity for the leased_by column | Pitfall 5 | Low — any stable string works; `leased_by` is informational only |
| A2 | Path B (holes remain) behavior for remote submit is the same as for server drain: don't stamp job | Pitfall 3 | Medium — if holes are common, the eval_jobs row stays 'leased' until sweep, costing 120s retry delay; but this is identical to the existing server-drain behavior and acceptable |

---

## Sources

### Primary (HIGH confidence — code read directly)

- `app/services/eval_queue_service.py` — `claim_eval_job`, `ClaimedJob`, `_claim_tier3_derived`, `LEASE_TTL_SECONDS`, `report_job_complete` [VERIFIED: codebase]
- `app/routers/eval_remote.py` — `lease_eval_game` (line 290), `submit_eval` (line 358), `_apply_submit` (line 154) [VERIFIED: codebase]
- `app/schemas/eval_remote.py` — `LeaseResponse`, `SubmitRequest`, `SubmitResponse`, `SubmitEval` [VERIFIED: codebase]
- `app/models/eval_jobs.py` — `EvalJob`, `TIER_EXPLICIT`, `TIER_AUTO_WINDOW`, `TIER_IDLE_BACKLOG`, `status`, `completed_at` [VERIFIED: codebase]
- `scripts/remote_eval_worker.py` — `DEFAULT_IDLE_SLEEP=5.0`, `_run_cycle`, submit payload construction [VERIFIED: codebase]
- `app/services/eval_drain.py` lines 1528–1543 — `eval_jobs` stamp pattern with `WHERE status = 'leased'` [VERIFIED: codebase]
- `tests/test_eval_worker_endpoints.py` — existing test patterns and mocking strategy [VERIFIED: codebase]
- `tests/services/test_eval_queue.py` — queue test patterns, session-maker fixture [VERIFIED: codebase]

## Metadata

**Confidence breakdown:**
- Exact current signatures: HIGH — read directly from source
- Shape compatibility analysis: HIGH — both return types read and compared
- Concurrency analysis: HIGH — SKIP LOCKED semantics well-established
- Test impact (which tests break): HIGH — traced mock targets by line

**Research date:** 2026-06-15
**Valid until:** No external dependencies; valid until codebase changes.
