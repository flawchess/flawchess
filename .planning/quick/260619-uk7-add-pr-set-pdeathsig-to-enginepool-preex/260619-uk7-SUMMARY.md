---
quick_id: 260619-uk7
title: Add PR_SET_PDEATHSIG to EnginePool preexec (SEED-059 orphan guard)
status: complete
date: 2026-06-19
commit: c17f5e01
seed: SEED-059
---

# Summary — 260619-uk7

## What changed

`app/services/engine.py` `_sched_idle_preexec` now requests
`PR_SET_PDEATHSIG=SIGKILL` (via `ctypes` `libc.prctl(1, SIGKILL)`) right after
the existing `SCHED_IDLE` call. The kernel now SIGKILLs every child `sf` engine
the instant its parent process dies — covering the bare-metal + adversarial-exit
quadrant the best-effort `EnginePool.stop()` UCI quit can't (mashed ctrl-c that
aborts the quit loop, `kill -9`, hard interpreter crash).

Because the call sits in the existing Linux-only preexec branch
(`_engine_popen_kwargs`, `sys.platform == "linux"`), the guard is automatically
Linux-only and reaches **every** `EnginePool` consumer in one place: the
module-level pool (uvicorn lifespan), `scripts/remote_eval_worker.py`,
`scripts/backfill_best_move_pv.py`, and `scripts/backfill_eval.py`. macOS/Windows
keep prior behavior (no preexec), as designed.

The call is wrapped in `try/except Exception` so a seccomp-filtered host that
blocks `prctl` cannot crash worker spawn — the same defensive posture as the
adjacent `SCHED_IDLE` call. A comment documents the one invariant:
PR_SET_PDEATHSIG fires on the spawning *thread's* death, which is safe here only
because engines are always spawned from the main asyncio thread (dies with the
process); moving spawning to a pool thread that can outlive its spawner would
mis-fire.

## Verification

- **prctl smoke test** on this Linux box: `prctl(PR_SET_PDEATHSIG, SIGKILL)`
  returned 0; `PR_GET_PDEATHSIG` read back 9 (SIGKILL).
- **Orphan kill -9 test** (the seed's acceptance check): started an
  `EnginePool(size=3)`, confirmed 3 child `sf`, `kill -9`'d the parent python —
  0 of the 3 children survived (kernel SIGKILL'd them all). Without the guard the
  seed documents these would reparent to PID 1 and leak.
- **Regression**: `tests/services/test_engine.py`,
  `test_engine_nodes.py`, `test_engine_pv.py` — 26 passed.
- **Gates**: `ruff format` (no change), `ruff check`, `ty check` — all clean.

## Out of scope (per seed)

- Optional secondary hardening of `backfill_best_move_pv.py`'s single-ctrl-c
  `KeyboardInterrupt` handling — skipped; PDEATHSIG is the real fix and the
  single-ctrl-c path already cleans up.

## Notes

- SEED-059 (`.planning/seeds/SEED-059-engine-pool-pdeathsig-orphan-guard.md`)
  can be marked resolved.
- One-liner to reap any pre-existing strays from before this change (kills only
  `ppid==1` `sf`, never a live pool):
  `for pid in $(pgrep -x sf); do [ "$(awk '{print $4}' /proc/$pid/stat)" = 1 ] && kill -9 "$pid"; done`
