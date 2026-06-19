---
id: SEED-059
status: resolved
resolved: 2026-06-19
resolved_by: quick task 260619-uk7 (commit c17f5e01)
planted: 2026-06-19
planted_during: v1.28 Tactic Tagging
trigger_when: whenever orphaned Stockfish (`sf`) processes are observed after a worker/script exit — most likely on a bare-metal remote worker or a maintenance script that's ctrl-c'd. Low urgency (Docker path is already safe), but cheap to close.
scope: small
---

# SEED-059: `EnginePool` Stockfish children can be orphaned on hard parent exit

## Why This Matters

Every consumer of `EnginePool` (the prod/dev backend drain, `scripts/remote_eval_worker.py`,
`scripts/backfill_best_move_pv.py`, `scripts/backfill_eval.py`) spawns N independent
`sf` UCI subprocesses. Today the only cleanup is a **best-effort async UCI quit**
(`EnginePool.stop()` → `await protocol.quit()` per worker). That works for the normal
exit path but leaves **orphaned `sf` processes** (reparented to PID 1) on any *hard*
parent exit:

- **Mashed ctrl-c** — a 2nd SIGINT lands *during* `await pool.stop()`, aborts the quit
  loop, and the not-yet-quit engines survive the dead parent. Observed in practice:
  ctrl-c'ing `backfill_best_move_pv.py` "a couple of times" left stray `sf` running.
- **`kill -9` / hard interpreter crash** — `stop()` never runs at all.

Orphaned engines keep consuming RAM (~180–320 MB RSS each) and CPU until manually killed.
CPU impact is bounded because they run `SCHED_IDLE` (`engine.py:149`), but the **RAM**
leak is real and accumulates across repeated runs — a meaningful problem on a memory-tight
workstation (e.g. a 16-thread laptop already near its RAM ceiling).

## What's Already Safe (don't re-solve these)

- **Docker remote worker** (`docker-compose.worker.yml` + `Dockerfile.worker`): orphan-proof.
  `STOPSIGNAL SIGINT` (`Dockerfile.worker:83`) routes `docker compose down` into the
  graceful `KeyboardInterrupt` path, and the worker python is **PID 1** in the container,
  so container teardown kills the whole PID namespace regardless. This is the *recommended*
  volunteer deployment, so the highest-traffic path is fine.
- **Single, patient ctrl-c on bare metal**: `remote_eval_worker.py` already handles this
  well — explicit `except KeyboardInterrupt` (`run_worker`, line ~366), `_run_loop`
  re-raises `KeyboardInterrupt`/`CancelledError` (lines ~180-181) so the generic
  `except Exception` retry path can't swallow a ctrl-c, and `__main__` swallows the
  re-raised interrupt for a clean exit 0. `backfill_best_move_pv.py` relies on the weaker
  implicit asyncio-cancellation path but still cleans up on a single ctrl-c.

The gap is purely the **bare-metal + adversarial-exit** quadrant (mashed ctrl-c / kill -9 /
crash), which no amount of Python-level handling can fully close — only the kernel can.

## The Fix (recommended): `PR_SET_PDEATHSIG` in the shared preexec

Add a parent-death-signal request to the existing Linux preexec so the **kernel** SIGKILLs
each `sf` the instant its parent process dies, by any means. This is the one change that
covers **every** `EnginePool` consumer at once (the decisive reason to fix it in
`engine.py`, not per-script):

```python
def _sched_idle_preexec() -> None:
    try:
        os.sched_setscheduler(0, os.SCHED_IDLE, os.sched_param(0))
    except OSError:
        pass
    # Kernel SIGKILLs this child if the parent dies (mashed ctrl-c / kill -9 / crash) so
    # no orphaned engines leak — best-effort UCI quit in EnginePool.stop() handles the
    # graceful path; this is the floor under it (SEED-059).
    try:
        import ctypes
        import signal

        ctypes.CDLL("libc.so.6", use_errno=True).prctl(1, signal.SIGKILL)  # PR_SET_PDEATHSIG=1
    except Exception:
        pass
```

`sf` is stateless (no data to flush), so a hard SIGKILL on parent death loses nothing vs.
the graceful UCI quit.

## Caveats / Things To Verify When Implementing

- **`PR_SET_PDEATHSIG` triggers on the spawning *thread's* death, not the process's.** Safe
  here because both the scripts and uvicorn spawn engines from their main asyncio thread,
  which dies with the process. If engine spawning ever moves to a non-main thread (e.g. a
  thread pool) that can exit while the process lives, this would mis-fire and kill live
  engines. Add a one-line comment noting this invariant.
- **Survives `execve`.** The setting is preserved across the `exec` into the `sf` binary as
  long as credentials don't change (no setuid here) — preexec runs post-fork/pre-exec, so
  the order is correct.
- **Linux-only, by design.** It belongs inside the `sys.platform == "linux"` branch
  (`_engine_popen_kwargs`, `engine.py:180`), alongside `SCHED_IDLE`. macOS/Windows keep
  today's behavior (no preexec) — acceptable; orphan risk there is the volunteer's local
  problem and the Docker path is the cross-platform recommendation anyway.
- **Don't break the swallow-on-error contract.** The `try/except Exception` keeps a
  containerised/seccomp host (where `prctl` may be blocked) from crashing worker spawn —
  same defensive posture as the existing `SCHED_IDLE` call.

## Optional Secondary Hardening (only if cheap, not required)

- Tighten `backfill_best_move_pv.py` to match the remote worker's explicit
  `KeyboardInterrupt` handling (catch in `run_backfill`/`main`, ensure `pool.stop()` in
  `finally`). Improves the *single*-ctrl-c story but does NOT cover mashed-ctrl-c/kill -9 —
  PDEATHSIG is the real fix. Skip unless trivially in scope.

## Verification

- Unit/manual: start an `EnginePool`, `kill -9` the parent python, confirm `pgrep -x sf`
  returns nothing (orphans = `sf` whose `/proc/<pid>/stat` ppid is 1).
- Manual mashed-ctrl-c repro against `backfill_best_move_pv.py --db dev --workers 4`:
  ctrl-c rapidly 3×, then assert no orphaned `sf` remain.
- Regression: existing engine/eval tests still pass (the preexec is additive and
  error-swallowed; no behavior change on the happy path).
- Cleanup one-liner for any pre-existing strays (kills only ppid==1 `sf`, never a live
  backend pool):
  ```bash
  for pid in $(pgrep -x sf); do [ "$(awk '{print $4}' /proc/$pid/stat)" = 1 ] && kill -9 "$pid"; done
  ```

## Breadcrumbs

- `app/services/engine.py:149` — `_sched_idle_preexec` (where the `prctl` call goes).
- `app/services/engine.py:168-182` — `_engine_popen_kwargs` (Linux-only preexec wiring).
- `app/services/engine.py:370-385` — `EnginePool.stop()` (the best-effort UCI quit this sits under).
- `scripts/remote_eval_worker.py:366-370` — the already-good graceful ctrl-c path (reference).
- `scripts/remote_eval_worker.py:180-181` — `_run_loop` re-raise of `KeyboardInterrupt`/`CancelledError`.
- `Dockerfile.worker:83` — `STOPSIGNAL SIGINT` (why the Docker path is already safe).
- `scripts/backfill_best_move_pv.py` — the script whose mashed-ctrl-c leak first surfaced this.

## Notes

Found 2026-06-19 while assessing whether `backfill_best_move_pv.py` could run on a remote
worker per `REMOTE_WORKER.md`, and then noticing 20 live `sf` processes (8 backfill + 12
dev backend) and a history of ctrl-c'd strays. The dev-backend pool was a red herring (a
legit running `uv run uvicorn`), but it prompted the orphan-lifecycle review that produced
this seed. Low urgency — Docker is safe and CPU is `SCHED_IDLE`-bounded — but it's a small,
high-leverage kernel-level guard that closes the leak for every consumer in one place.
