---
phase: quick-260702-snc
plan: 01
subsystem: remote-eval-worker
tags: [reliability, supervisor, watchdog, docker, sentry]
dependency-graph:
  requires: []
  provides:
    - "self-supervising remote_eval_worker.py (supervisor/child/once dispatch)"
    - "watchdog heartbeat + stall checker (converts a hang into os._exit(1))"
    - "asyncio loop exception handler (Sentry-captures the InvalidStateError storm)"
    - "docker-compose.worker.yml log rotation + observability healthcheck"
  affects:
    - scripts/remote_eval_worker.py
    - tests/test_remote_eval_worker.py
    - docker-compose.worker.yml
    - Dockerfile.worker
    - REMOTE_WORKER.md
tech-stack:
  added: []
  patterns:
    - "self-re-exec supervisor: parent spawns subprocess.Popen of sys.executable + this script, relaunches on any child exit, distinguishes child via an internal env marker (not argparse)"
    - "wall-clock heartbeat + periodic asyncio checker task that forces os._exit(1) on a stall, letting an external supervisor (in-process parent, or Docker restart: unless-stopped) relaunch with fresh state"
key-files:
  created: []
  modified:
    - scripts/remote_eval_worker.py
    - tests/test_remote_eval_worker.py
    - docker-compose.worker.yml
    - Dockerfile.worker
    - REMOTE_WORKER.md
decisions:
  - "Followed SEED-063 locked decisions D1-D6 as specified in the plan (cross-platform Python supervisor, no --supervise flag, internal env marker, full process restart on failure, keep restart: unless-stopped, Docker log rotation + observability healthcheck) -- no deviations from the locked architecture."
metrics:
  duration: "~45 min"
  completed: "2026-07-02"
status: complete
---

# Quick Task 260702-snc: Self-supervising auto-restart watchdog for the remote eval worker Summary

Made `scripts/remote_eval_worker.py` always run as a supervisor that spawns a child of itself to do the real lease/eval/submit work, with an in-child watchdog that converts a silent hang (the observed InvalidStateError storm where all Stockfish subprocesses die at once) into a process exit the supervisor (or Docker's `restart: unless-stopped`) can react to.

## What Was Built

**Task 1 — Supervisor + child/once dispatch + cross-platform signal handling.**
Added a pure `_worker_role(once, child_marker) -> Literal["once", "supervisor", "child"]` predicate (`--once` always bypasses supervision; otherwise an internal `_FLAWCHESS_WORKER_CHILD` env var — NOT an argparse flag — distinguishes the spawned child from the supervisor). Added a synchronous `_run_supervisor()`: installs `signal.signal(SIGINT/SIGTERM, ...)` handlers (never `loop.add_signal_handler()`, which is Unix-only and raises `NotImplementedError` on Windows' ProactorEventLoop), spawns the child via `subprocess.Popen([sys.executable, __file__, *sys.argv[1:]], env={..., marker})`, `proc.wait()`s (reaping it), and on an unintentional exit relaunches after a fixed `SUPERVISOR_BACKOFF_S=3.0` — no max-restart cap, matching `unless-stopped` semantics. On POSIX only, the signal handler forwards SIGINT to the live child for a clean shutdown. `main()` became synchronous (`-> int`), with the operator-token check happening *before* role dispatch so a missing token fails fast (return 1) in both the supervisor and the child — never becoming an infinite relaunch loop.

**Task 2 — Watchdog heartbeat + checker + asyncio exception handler.**
Added `_is_stalled(now, last_progress, threshold_s) -> bool` (pure), a `_Heartbeat` class (wall-clock `time.time()`, not monotonic, so a laptop sleep/resume produces a huge gap → instant restart on resume; `mark()` swallows `OSError` on file write since the heartbeat file is observability-only), `_watchdog_checker` (polls every `WATCHDOG_POLL_INTERVAL_S=15.0`, forces `os._exit(1)` after `STALL_THRESHOLD_S=240.0` — ~4 minutes, chosen to clear the slowest legitimate cycle of ~125s — of no progress, Sentry-capturing a fixed message first), and `_loop_exception_handler` (Sentry-captures asyncio callback exceptions — specifically the `InvalidStateError` storm that fires from the event loop's `_call_connection_lost` callback and previously bypassed `_run_loop`'s try/except entirely). `run_worker` and `_run_loop` gained a trailing `heartbeat: _Heartbeat | None = None` parameter; `_run_loop` calls `heartbeat.mark()` after every `_run_cycle` that returns *without raising*, before the stop check — so a clean 204 idle cycle counts as progress (an idle worker with an empty queue is healthy, not stalled), while a failed cycle does not. `_run_async` wires the full watchdog (heartbeat + loop exception handler + checker task, cancelled in a `finally`) only for the supervised ("child") role; `--once` passes `heartbeat=None` and installs no checker at all.

**Task 3 — Docker hardening + doc update.**
`docker-compose.worker.yml`: added a `logging:` block (`json-file`, `max-size: "10m"`, `max-file: "3"`) so the unbounded log flood can't fill the host disk before the watchdog fires; added `FLAWCHESS_WORKER_HEARTBEAT_FILE=/tmp/flawchess-worker.heartbeat` so the healthcheck agrees with the worker on the same path; added an observability-only `healthcheck:` (a python one-liner checking the heartbeat file's mtime staleness against 300s — larger than the ~240s watchdog threshold, so the watchdog fires first) with `start_period: 120s` to cover `EnginePool` startup. Kept `restart: unless-stopped`. `Dockerfile.worker`: only the `STOPSIGNAL` comment changed to reflect that the supervisor is now PID 1 and forwards SIGINT to the child — `STOPSIGNAL`/`CMD` are functionally unchanged. Confirmed `app/services/engine.py` is untouched (`git diff --quiet` passed). `REMOTE_WORKER.md`: step 7 (Linux/macOS) and the Docker section's closing line now promise self-restart on crash *or* hang, and state plainly that stopping via `Ctrl-C` (or the Docker stop command) is clean and never triggers a relaunch.

## Deviations from Plan

None — plan executed exactly as written, following SEED-063's locked decisions D1–D6.

## Verification

- `uv run ruff check scripts/remote_eval_worker.py tests/test_remote_eval_worker.py` — clean.
- `uv run ty check scripts/remote_eval_worker.py tests/test_remote_eval_worker.py` — zero errors.
- `uv run pytest tests/test_remote_eval_worker.py -q` — 33 passed (10 new tests: 4 `_worker_role` cases, 2 `_is_stalled` cases, 2 `_Heartbeat.mark` cases, 1 `STALL_THRESHOLD_S` minutes-not-seconds regression guard, plus one existing suite unchanged). No DB fixture is used by this test file — all mocked unit tests, no dev DB required.
- `python -c "import yaml,sys; ..."` compose-shape assertion (`logging` + `healthcheck` + `restart: unless-stopped` present) — passed.
- `git diff --quiet app/services/engine.py` — confirmed untouched.

## Manual verification (NOT run in this session — recommended before merge)

The plan's `<verification>` block calls out cross-OS manual checks that cannot be automated here:
- Start the worker with no flags; `pkill stockfish` mid-run → child self-exits, supervisor relaunches, processing resumes.
- `Ctrl-C` the supervisor → clean stop, no relaunch storm.
- `uv run python scripts/remote_eval_worker.py --once` exits cleanly with the real exit code.
- Docker: `docker compose -f docker-compose.worker.yml up -d --build`, kill stockfish inside the container → `docker ps` shows `unhealthy` then healthy again after relaunch; `docker stop` exits cleanly (not 137); `docker logs` stays bounded after an error flood.

These are flagged as HUMAN-UAT, not blocking this quick task's completion, per the plan.

## Self-Check: PASSED

- `scripts/remote_eval_worker.py` — FOUND
- `tests/test_remote_eval_worker.py` — FOUND
- `docker-compose.worker.yml` — FOUND
- `Dockerfile.worker` — FOUND
- `REMOTE_WORKER.md` — FOUND
- Commit `d91d9544` (Task 1) — FOUND in `git log --oneline`
- Commit `ae007412` (Task 2) — FOUND in `git log --oneline`
- Commit `8a171735` (Task 3) — FOUND in `git log --oneline`
