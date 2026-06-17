---
phase: 120-headless-remote-trusted-operator-eval-worker-seed-048
reviewed: 2026-06-14T00:00:00Z
depth: standard
files_reviewed: 9
files_reviewed_list:
  - app/core/config.py
  - app/schemas/eval_remote.py
  - app/services/engine.py
  - app/services/eval_queue_service.py
  - app/routers/eval_remote.py
  - app/main.py
  - scripts/remote_eval_worker.py
  - tests/test_eval_worker_endpoints.py
  - tests/services/test_eval_queue.py
findings:
  critical: 0
  warning: 4
  info: 5
  total: 9
status: resolved
warnings_resolved: true
resolved_at: 2026-06-14
resolution_note: >-
  All 4 warnings fixed (WR-01 byte-compare auth, WR-02 worker exception boundary
  + Sentry, WR-03 evals max_length + ply>=0 bounds, WR-04 authoritative owner for
  cache signal — body.user_id dropped from the submit contract). Info findings
  IN-01..IN-03, IN-05 not actioned (advisory); IN-04 folded into WR-03.
---

# Phase 120: Code Review Report

**Reviewed:** 2026-06-14
**Depth:** standard
**Files Reviewed:** 9
**Status:** issues_found

## Summary

Reviewed the new trusted-operator remote eval surface: two HTTP endpoints
(`/eval/remote/lease`, `/eval/remote/submit`), the operator-token auth gate, the
D-7 weighted-random tier-3 game pick, the SF-version helper, and the headless CLI
worker. The core security posture is sound: token comparison is constant-time
(`hmac.compare_digest`), fail-closed when unconfigured (403), 401 on mismatch, the
token is never logged, and all SQL in the ES lottery is properly parameterized (no
f-string interpolation into `sa.text`). The SEED-044 +1 post-move shift is correctly
owned server-side, and the read-then-write session discipline avoids
`asyncio.gather` on a shared `AsyncSession`.

No Critical findings. Four Warnings concern robustness and input-trust gaps that
matter for a long-running daemon facing the network: a non-ASCII token header crashes
the auth check with a 500 instead of 401; the worker loop has no exception boundary
(any transient network error kills the daemon and is never Sentry-captured); the
`evals` payload is unbounded; and the post-commit cache signal trusts the
worker-supplied `user_id` rather than the game's authoritative owner.

## Narrative Findings (AI reviewer)

## Warnings

### WR-01: Non-ASCII operator-token header raises TypeError → 500 instead of 401

**File:** `app/routers/eval_remote.py:85`
**Issue:** `hmac.compare_digest(configured, x_operator_token)` is called with two
`str` operands. `hmac.compare_digest` rejects non-ASCII `str` with
`TypeError: comparing strings with non-ASCII characters is not supported`
(verified). An attacker (or a misconfigured client) sending an `X-Operator-Token`
header containing any non-ASCII byte triggers an uncaught `TypeError`, which surfaces
as HTTP 500 instead of the intended 401, and Sentry-captures the exception on every
such request (a cheap unauthenticated way to spam the error tracker). The auth path
should never raise on attacker-controlled input.
**Fix:** Compare bytes, encoding defensively:
```python
import hmac

configured_b = configured.encode("utf-8")
supplied_b = (x_operator_token or "").encode("utf-8")
if x_operator_token is None or not hmac.compare_digest(configured_b, supplied_b):
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid operator token")
```
Encoding both sides keeps the comparison constant-time over the byte length and
removes the ASCII-only restriction.

### WR-02: Worker loop has no exception boundary — a transient error kills the daemon and is never Sentry-captured

**File:** `scripts/remote_eval_worker.py:117-161` (and `175-205`)
**Issue:** `_run_loop` performs `client.post(...)`, `raise_for_status()`,
`chess.Board(str(pos["fen"]))`, and `pool.evaluate_nodes_with_pv(...)` with no
try/except inside the loop. `run_worker`'s only `except` catches `KeyboardInterrupt`.
Consequences for a daemon documented as "Continuous loop (default)":
- A single transient network blip or a 5xx from the server (`raise_for_status`)
  raises `httpx.HTTPError` that propagates all the way out and terminates the worker
  permanently. A long-running drainer should log and retry, not die.
- An invalid/unexpected FEN in a lease response raises `ValueError` from
  `chess.Board(...)` and kills the loop.
- CLAUDE.md requires `sentry_sdk.capture_exception()` in non-trivial except blocks in
  service/operational code. The worker initializes Sentry (lines 285-291) but never
  captures any operational exception, so these crashes are invisible in Sentry.
**Fix:** Wrap the body of the `while True` loop in a try/except that captures
unexpected exceptions to Sentry and continues (with a backoff sleep) when `loop` is
true, re-raising only `KeyboardInterrupt`/`asyncio.CancelledError`:
```python
while True:
    try:
        ...  # lease → eval → submit
    except (KeyboardInterrupt, asyncio.CancelledError):
        raise
    except Exception:
        sentry_sdk.capture_exception()
        _log("Cycle failed; backing off.")
        if not loop:
            raise
        await asyncio.sleep(idle_sleep)
```

### WR-03: `SubmitRequest.evals` has no upper bound — unbounded request body

**File:** `app/schemas/eval_remote.py:30-34` (consumed at `app/routers/eval_remote.py:203-205`)
**Issue:** `evals: list[SubmitEval]` has no `max_length`. The endpoint deserializes
the entire list into `engine_result_map` in memory before any DB work. Although the
endpoint is behind operator auth (lowering the abuse risk), a buggy or compromised
worker can post an arbitrarily large body and force the API process to materialize it
all at once. A real game has at most ~a few hundred plies, so a generous cap is free
insurance and also catches client bugs early with a clean 422 rather than a memory
spike.
**Fix:** Add a Pydantic bound, e.g. `evals: list[SubmitEval] = Field(max_length=1024)`
(pick a constant comfortably above the longest realistic game). Also consider
`ply: int = Field(ge=0)` on `SubmitEval`/`LeasePosition` so negative plies are rejected
at the boundary.

### WR-04: Post-commit cache signal uses client-supplied `user_id`, not the game's authoritative owner

**File:** `app/routers/eval_remote.py:267` (value from `app/routers/eval_remote.py:172-189`, `373-377`)
**Issue:** `_apply_submit` reads the game and scopes all writes to the real owner
(`GamePosition.user_id == game.user_id`, line 184; `_classify_and_fill_oracle`
re-loads the game by `game_id` and derives the owner server-side). But the post-commit
hook `_signal_flaw_completion(user_id)` is called with the *worker-supplied*
`body.user_id` (threaded through `_apply_submit(user_id=body.user_id, ...)`), not
`game.user_id`. If a worker submits a stale or wrong `user_id` (the lease echoes it
back, but nothing enforces consistency at submit), the flaw-completion signal fires for
the wrong user — the actual owner's analysis cache is never invalidated and stays
stale, while an unrelated user gets a spurious signal. The data writes are safe; only
the cache-invalidation target is wrong. This is a correctness defect, not a security
one, but it defeats the very signal it intends to send.
**Fix:** Capture the authoritative owner in the read phase and use it for the signal.
Return `game.user_id` from `_apply_submit` (or signal inside it) and ignore
`body.user_id` for this purpose:
```python
# read phase:
owner_id: int = game.user_id
...
# after commit:
if stamp_complete:
    _signal_flaw_completion(owner_id)
```
`body.user_id` can then be dropped from the submit contract entirely (it is only used
here and adds a trust surface for no benefit).

## Info

### IN-01: Submit does not re-validate `is_lichess_eval_game` against the leased game

**File:** `app/routers/eval_remote.py:174`
**Issue:** `_apply_submit` recomputes `is_lichess_eval_game` from
`game.lichess_evals_at` at submit time (good), so a stale lease is mostly handled.
However, the lease defers lichess games with a 204 and never sends them to a worker,
yet submit will happily process a `game_id` whose `lichess_evals_at` became non-NULL
between lease and submit and take the lichess-preserve branch. This is benign given
the idempotent write path, but worth a comment noting the race is intentionally
tolerated.
**Fix:** Add a one-line comment at line 174 documenting that the lichess gate is
re-derived at submit and the lease/submit race is acceptable (idempotent path).

### IN-02: `_eval_positions` uses loosely-typed `list[dict[str, object]]`

**File:** `scripts/remote_eval_worker.py:73-97`
**Issue:** Positions and eval results are passed as `dict[str, object]`, forcing
`chess.Board(str(pos["fen"]))` casts and losing type safety on `ply`/`is_terminal`.
CLAUDE.md prefers TypedDicts for internal structured data. A `TypedDict` (or reusing a
lightweight dataclass) would catch key/shape mistakes at type-check time.
**Fix:** Define `class LeasePositionDict(TypedDict): ply: int; fen: str; is_terminal: bool`
and a matching `EvalResultDict`, and annotate `_eval_positions` accordingly.

### IN-03: `get_stockfish_version` does not guard `protocol.quit()` like the pool paths do

**File:** `app/services/engine.py:311-321`
**Issue:** `EnginePool.stop`/`_restart_worker` carefully wrap `protocol.quit()` in
try/except for `EngineError`/`EngineTerminatedError`/`RuntimeError` (FLAWCHESS-59:
quitting a dead engine writes to a closed uvloop transport). `get_stockfish_version`
opens a one-shot connection and calls `await protocol.quit()` unguarded. In the normal
path the engine is alive so this is fine, but for consistency with the documented
FLAWCHESS-59 hazard it should use the same guard (or a `try/finally`).
**Fix:** Wrap the `quit()` in the same `except (EngineError, EngineTerminatedError,
RuntimeError): pass` guard used elsewhere in the module.

### IN-04: `SubmitEval.ply` / `LeasePosition.ply` accept negative values

**File:** `app/schemas/eval_remote.py:9, 23`
**Issue:** `ply: int` has no lower bound. A negative ply in a submit payload would be
silently dropped by `engine_result_map`/`_resolve_full_eval` (no matching target), but
validating at the boundary is cleaner and self-documenting.
**Fix:** `ply: int = Field(ge=0)`. (Folded into WR-03's fix is fine.)

### IN-05: Worker `--token` default surfaces the env var into argparse help/namespace

**File:** `scripts/remote_eval_worker.py:226-232`
**Issue:** `default=os.environ.get("EVAL_OPERATOR_TOKEN", "")` reads the secret into the
argparse default. This is not logged (startup log correctly omits it, line 293-294) and
argparse does not echo defaults unless `--help` formats them, so the risk is low. Still,
binding a secret as an argparse default is a mild footgun (e.g. a future
`print(args)` or `%` default-in-help formatter would leak it). Prefer resolving the env
var after parse, leaving the default empty.
**Fix:** Keep `--token` default `""`, then `token = args.token or os.environ.get("EVAL_OPERATOR_TOKEN", "")`
in `main()`.

---

_Reviewed: 2026-06-14_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
