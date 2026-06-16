---
phase: 123-remote-worker-fan-out-for-entry-ply-import-time-eval-on-big-
reviewed: 2026-06-16T00:00:00Z
depth: standard
files_reviewed: 10
files_reviewed_list:
  - alembic/versions/20260616_120000_phase_123_entry_eval_lease.py
  - app/models/game.py
  - app/routers/eval_remote.py
  - app/schemas/eval_remote.py
  - app/services/eval_drain.py
  - app/services/eval_queue_service.py
  - scripts/remote_eval_worker.py
  - tests/services/test_eval_drain.py
  - tests/test_eval_worker_endpoints.py
  - tests/test_remote_eval_worker.py
findings:
  critical: 1
  warning: 4
  info: 3
  total: 8
status: issues_found
---

# Phase 123: Code Review Report

**Reviewed:** 2026-06-16
**Depth:** standard
**Files Reviewed:** 10
**Status:** issues_found

## Summary

Phase 123 adds entry-ply (import-time) lease columns and a remote-worker fan-out
path: `/eval/remote/entry-lease` claims a batch of pending games via SKIP-LOCKED
LIFO, ships server-derived FENs to a trusted off-box worker, and
`/eval/remote/entry-submit` applies depth-15 evals through the no-shift write path.

The security posture is solid: operator-token auth is fail-closed and constant-time,
all SQL values are bound parameters (no f-string interpolation), and the server
re-derives ply/endgame_class so a worker cannot corrupt the storage convention. The
SKIP-LOCKED claim + TTL reclaim logic is correct and well-tested.

The one blocker is a **completion-stamp gap unique to the remote path**: a leased
game that produces zero eval targets at drain time is never stamped
`evals_completed_at`, so it is re-leased every TTL cycle indefinitely. The in-process
server pool stamps every claimed game regardless of target count; the remote path
only stamps games that appear in the worker's submission body. Combined with a few
input-validation and robustness gaps, this should be fixed before shipping.

## Critical Issues

### CR-01: Remote entry-submit never stamps zero-target leased games — re-lease livelock

**File:** `app/routers/eval_remote.py:573-576`, `app/routers/eval_remote.py:608-611`
**Issue:**
`/entry-lease` claims `ENTRY_LEASE_BATCH_SIZE` games and stamps a lease
(`entry_eval_lease_expiry`, `entry_eval_leased_by`) on all of them. The endpoint then
derives positions via `_collect_eval_targets_from_db`. A claimed game can yield
**zero** positions — e.g. when a target ply is unreachable in the mainline walk
(`_snapshot_boards` silently drops unreachable plies, eval_drain.py:843-848), or when
drain-time target derivation diverges from the import-time Stage 5c "covered" check.

Such a game contributes nothing to the lease response, so it never appears in the
worker's `/entry-submit` body. In `entry_submit_eval`, `game_ids_submitted` is built
**only** from games present in `body.evals` (line 573), and `_mark_evals_completed`
is called only on `game_ids_submitted` (line 610). The zero-target game is therefore
never stamped `evals_completed_at`.

Because its lease expires after `ENTRY_LEASE_TTL_SECONDS` (20s), it is reclaimed on
the next `/entry-lease` and the cycle repeats forever. The in-process server pool
(`run_eval_drain` Step 5, eval_drain.py:1324) avoids this by stamping **all** picked
game IDs regardless of target count (D-09 / R-02 "no permanent retry") — but the
server pool's SKIP-LOCKED claim excludes rows with a live lease, so while remote
workers are actively draining, these games bounce between remote leases and are never
completed by either path.

This is a correctness/liveness defect: affected games are permanently stuck pending,
and every cycle burns a lease + FEN-derivation round-trip on them.

**Fix:** Stamp every game that was *leased to this worker*, not just the games that
came back with evals. Mirror the server-pool invariant. Two viable approaches:

```python
# Option A — worker echoes the full leased game_ids back; server stamps the full set.
# (add leased_game_ids to EntryLeaseResponse + EntrySubmitRequest)
await _mark_evals_completed(write_session, body.leased_game_ids)

# Option B — stamp by lease ownership at submit time (no schema change):
await write_session.execute(
    update(Game.__table__)  # ty: ignore[invalid-argument-type]
    .where(
        Game.__table__.c.entry_eval_leased_by == worker_id,
        Game.__table__.c.evals_completed_at.is_(None),
    )
    .values(evals_completed_at=datetime.now(timezone.utc))
)
```

Add a regression test that leases a game with an unreachable target ply and asserts
`evals_completed_at` is set after submit.

## Warnings

### WR-01: X-Worker-Id header is unvalidated and overflows VARCHAR(16) on entry-lease

**File:** `app/routers/eval_remote.py:335-344`, `app/services/eval_drain.py:1050-1067`
**Issue:**
`worker_id_label` returns `x_worker_id or _WORKER_ID_REMOTE` with no length check.
`_claim_entry_eval_games` writes it to `games.entry_eval_leased_by`, which is
`VARCHAR(16)` (migration line 48, model lines 193-196). An X-Worker-Id header longer
than 16 chars raises a PostgreSQL `StringDataRightTruncation` → unhandled 500 (and
Sentry noise). The CLI worker validates `< 10` chars (`parse_args`,
remote_eval_worker.py:444), but nothing enforces that server-side, and the full-ply
path's `eval_jobs.leased_by` is `VARCHAR(100)`, so the same header succeeds on
`/lease` but fails on `/entry-lease` — an inconsistent, surprising failure mode.

**Fix:** Validate/truncate the header in `worker_id_label` (defense-in-depth; the
worker's own validation is not authoritative):

```python
async def worker_id_label(
    x_worker_id: Annotated[str | None, Header(alias="X-Worker-Id")] = None,
) -> str:
    label = x_worker_id or _WORKER_ID_REMOTE
    # games.entry_eval_leased_by is VARCHAR(16); truncate so a long header can
    # never surface as a 500 on entry-lease (it succeeds on /lease's VARCHAR(100)).
    return label[:16]
```

### WR-02: entry-submit trusts worker-supplied game_id without verifying the lease

**File:** `app/routers/eval_remote.py:569-573`
**Issue:**
`evals_by_game` is keyed by `e.game_id` straight from the worker payload, and every
distinct game_id is then re-derived, classified, and stamped
`evals_completed_at`/flaws. The server controls ply/endgame_class (T-123-04) but NOT
which game is targeted. A buggy or out-of-sync worker that submits a stale or wrong
game_id will stamp an unrelated game complete and run classification against it. The
operator is trusted, so this is not an authz hole, but there is no check that the
submitted game was ever leased — by anyone, let alone by this worker.

**Fix:** Filter `game_ids_submitted` to games currently pending (lease-owned) and
ignore the rest:

```python
async with async_session_maker() as guard_session:
    valid = set((await guard_session.execute(
        select(Game.id).where(
            Game.id.in_(game_ids_submitted),
            Game.evals_completed_at.is_(None),
        )
    )).scalars().all())
game_ids_submitted = [g for g in game_ids_submitted if g in valid]
```

### WR-03: Backlog probe counts leased rows, masking an all-leased empty claim

**File:** `app/routers/eval_remote.py:494-519`
**Issue:**
The D-5 existence probe counts `games WHERE evals_completed_at IS NULL` with no lease
predicate, while `_claim_entry_eval_games` only claims rows whose lease is NULL or
expired. When the backlog is deep but every available row is already leased by other
workers, the probe passes ("deep enough"), the claim returns `[]`, and the endpoint
does a wasted claim transaction before returning 204. Under N concurrent workers this
is N-1 wasted claim attempts per cycle near the tail. The 204-on-empty-claim guard at
line 518 keeps it correct, but the probe and claim using divergent predicates is the
kind of drift that hides future bugs.

**Fix:** Make the probe predicate match the claim predicate:

```sql
SELECT 1 FROM games
WHERE evals_completed_at IS NULL
  AND (entry_eval_lease_expiry IS NULL OR entry_eval_lease_expiry < now())
ORDER BY id DESC
LIMIT 1 OFFSET :offset
```

### WR-04: entry-submit failure leaves leases live for the full TTL with no release

**File:** `app/routers/eval_remote.py:613-621`
**Issue:**
On a write-phase exception, `/entry-submit` captures and re-raises but does nothing to
release the leases set by `/entry-lease`. Those games stay `evals_completed_at IS
NULL` with `entry_eval_lease_expiry` still in the future, so they are not reclaimable
until the 20s TTL expires. The full-ply path solves the analogous case explicitly via
`release_job` (eval_queue_service.py:560) precisely to avoid TTL-length stalls; the
entry path has no equivalent. A 50-game batch that fails mid-write stalls up to 50
games for 20s on each failure. Blast radius is bounded (short TTL), so this is a
Warning, but it contradicts the deliberate "release now, don't wait for TTL" design.

**Fix:** Best-effort clear the lease in the `except` block before re-raising:

```python
except Exception as exc:
    sentry_sdk.set_context("entry_submit", {"game_ids": game_ids_submitted})
    sentry_sdk.set_tag("source", "remote_eval_worker")
    sentry_sdk.capture_exception(exc)
    async with async_session_maker() as rel:
        await rel.execute(
            update(Game.__table__)  # ty: ignore[invalid-argument-type]
            .where(Game.__table__.c.id.in_(game_ids_submitted))
            .values(entry_eval_lease_expiry=None, entry_eval_leased_by=None)
        )
        await rel.commit()
    raise
```

## Info

### IN-01: Hardcoded worker label in Sentry context contradicts its own key name

**File:** `app/routers/eval_remote.py:617`
**Issue:**
The Sentry context sets `"worker_id": "entry-submit"` — a static literal that is not
the worker's identity. The endpoint has no access to the lease owner here, but the key
name reads like a worker ID while being a constant tag.
**Fix:** Drop the key or rename it (`{"phase": "entry-submit"}`); rely on
`set_tag("source", ...)` for the dimension.

### IN-02: EntrySubmitEval.game_id / batch size lack bounds or cross-field validation

**File:** `app/schemas/eval_remote.py:71-80`
**Issue:**
`EntrySubmitEval` validates `ply >= 0` but `game_id` has no bound and there is no cap
on distinct game_ids per request (only the flat `MAX_SUBMIT_EVALS` total cap). The
schema does not encode "evals must belong to the leased batch," leaving that to the
handler (see WR-02). Documenting the trust boundary on the schema makes the contract
explicit.
**Fix:** Add `Field(ge=1)` on `game_id` and a comment noting game-id membership is
enforced in the handler.

### IN-03: entry-lease consumes claim order without the re-sort its sibling applies

**File:** `app/routers/eval_remote.py:530-537`, `app/services/eval_drain.py:1083-1092`
**Issue:**
`_pick_pending_game_ids` explicitly re-sorts the `RETURNING` result DESC (with a
comment that `UPDATE ... RETURNING` does not guarantee order), but `/entry-lease`
consumes `_claim_entry_eval_games`'s output directly. For entry-ply the order does not
affect correctness (positions are batched across games), so this is fine today — but
the asymmetry is a latent footgun if a future caller assumes LIFO order from the
endpoint.
**Fix:** Add a one-line "order not relied upon here" comment, or sort for consistency.

---

_Reviewed: 2026-06-16_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
