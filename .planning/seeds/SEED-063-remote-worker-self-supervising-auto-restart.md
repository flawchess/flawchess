---
id: SEED-063
status: dormant
planted: 2026-06-21
planted_during: v1.28 Tactic Tagging (current_phase 999.1 BACKLOG)
trigger_when: when hardening the remote eval worker, addressing worker reliability/uptime, or revisiting the eval pipeline (SEED-048/051 lineage)
scope: Small
---

# SEED-063: Self-supervising auto-restart for the remote eval worker (always-on, cross-platform)

## Why This Matters

A bare-metal (non-Docker) Windows remote eval worker crashed mid-game on 2026-06-21
(`temp/worker-error.txt`). Volunteers run the worker outside Docker on
Windows/macOS/Linux, and those runners have **no supervisor** — so a crash or hang
silently stops contributing eval capacity until the human notices and restarts it by
hand. Docker users are already covered (`docker-compose.worker.yml` has
`restart: unless-stopped`); bare-metal users are not. This closes that gap so
"Leave it running" in REMOTE_WORKER.md can actually promise resilience.

### Root cause (observed)

The log shows a flood of identical python-chess tracebacks, then goes silent:

```
BaseSubprocessTransport._call_connection_lost
  -> chess.engine.connection_lost -> _engine_terminated -> engine_terminated
  -> analysis.set_exception -> _finished.set_exception
asyncio.exceptions.InvalidStateError: invalid state
```

1. **ALL Stockfish subprocesses in the EnginePool died at ~the same instant** — the
   flood is one traceback per dead engine. On a personal non-Docker machine the
   overwhelmingly likely trigger is the host **sleeping/hibernating and resuming**,
   which breaks every child-process pipe at once (OOM / antivirus are distant
   runners-up).
2. **python-chess race:** when an engine terminates, its transport calls
   `analysis.set_exception()` on a future that `asyncio.wait_for`
   (`app/services/engine.py:455` / `:506`, `_NODES_TIMEOUT_S=5s`) had ALREADY
   resolved → `set_exception` on a done future → `InvalidStateError`. A long-standing
   python-chess quirk, **not our bug**.
3. **These are asyncio CALLBACK exceptions** raised inside the event loop's
   `_call_connection_lost` handler — they fire OUTSIDE the `try/except` in
   `scripts/remote_eval_worker.py:_run_loop` (~line 177), so they **bypass our Sentry
   capture and back-off logic entirely**. asyncio's default handler just prints them
   to stderr and the loop keeps running. Net effect: the process stays **ALIVE but
   WEDGED** (engines gone; the in-flight `analyse` future never resolves because the
   very call that should complete it — `set_exception` — threw).

This is why a plain "relaunch on exit" wrapper is insufficient: the failure is a
**hang**, not a clean exit.

## When to Surface

**Trigger:** when hardening the remote eval worker, when worker uptime/reliability
comes up, or when next touching the eval pipeline (SEED-048 Phase 120/121, SEED-051
Phase 123). Small/self-contained — a good `/gsd-quick` candidate when convenient.

## Scope Estimate

**Small** — a few hours. One script (`scripts/remote_eval_worker.py`), a doc update,
and a couple of unit tests for the pure decision logic. No DB, no API, no migration.

### Decisions LOCKED (discussion 2026-06-21)

- **D1 — Cross-platform via a Python supervisor**, NOT OS-specific tooling (no batch /
  PowerShell / Task Scheduler / NSSM / systemd / launchd). One mechanism, all three
  OSes, since volunteers already run the same
  `uv run python scripts/remote_eval_worker.py ...` everywhere.
- **D2 — NO separate supervisor script.** The supervisor lives inside
  `remote_eval_worker.py` itself.
- **D3 — ALWAYS supervised.** No user-facing `--supervise` flag; the entrypoint is
  always the supervisor.
- **D4 — Full process restart on failure**, NOT in-process EnginePool rebuild. Exactly
  one recovery path; strictly more robust (covers wedged-loop and suspend cases
  in-process recovery can't); simpler to reason about. **Do NOT add in-process
  pool-rebuild** — explicitly rejected as over-engineering.
- **D5 — Docker users change nothing** (already have `restart: unless-stopped`).

### Proposed architecture — self-re-exec

One script, always-on, no flag → the entrypoint becomes the **SUPERVISOR (parent)**,
which spawns a **child subprocess of ITSELF** to do the real lease/eval/submit work.

- Distinguish parent vs child with an **INTERNAL marker** (env var, e.g.
  `_FLAWCHESS_WORKER_CHILD=1`) — NOT an argparse flag; keep it out of `--help` and the
  public CLI.
- Parent loop: launch child (`sys.executable` + this script + same argv), wait,
  **relaunch with backoff** whenever the child exits for ANY reason.
- Honor Ctrl-C / SIGINT / SIGTERM in the parent so a user stop does NOT trigger a
  relaunch (mirror `restart: unless-stopped` semantics — stop on intentional shutdown,
  restart on crash).
- `--once` **bypasses supervision** (run the work directly and exit with the real code).

### Watchdog — turns a HANG into an EXIT (the key piece)

The child must self-terminate so the parent can relaunch:

- **Heartbeat:** record a "last progress" **wall-clock** timestamp every time a cycle
  COMPLETES WITHOUT ERROR. CRITICAL: a clean **204 idle cycle counts as progress** — an
  idle worker with an empty queue is healthy, not stalled. Only a genuinely wedged loop
  produces zero completed cycles. Wall-clock (not monotonic) so that after a laptop
  sleep the gap is huge → instant restart on resume, exactly what we want.
- **Checker task:** a separate asyncio task wakes periodically; if
  `now - last_progress > STALL_THRESHOLD`, it logs + Sentry-captures + forces
  `os._exit(1)`. Parent relaunches with fresh engines.
- **STALL_THRESHOLD** must clear the slowest LEGITIMATE cycle. A tier-1 game = 100
  positions; with `--workers 4` and `_NODES_TIMEOUT_S=5s`, worst case ≈ 25 batches ×
  5s ≈ 125s if everything times out. Pick **~3–4 minutes** (NOT seconds) so a
  slow-but-healthy worker is never killed. Named constant `STALL_THRESHOLD_S`.
- **asyncio exception handler:** `loop.set_exception_handler(...)` in the CHILD so the
  `InvalidStateError` storm gets counted + Sentry-captured (today it only hits stderr
  because it bypasses `_run_loop`'s try/except). Optional fast-path: N callback
  exceptions within a short window is itself an exit trigger (faster than waiting out
  the full stall threshold) — decide during planning.

## Breadcrumbs

- `scripts/remote_eval_worker.py` — supervisor wrapper + watchdog + child marker +
  exception handler. Phase-owned: SEED-048 (Phase 120/121), SEED-051 (Phase 123).
  Relevant spots: `_run_loop` (~L176-189, the existing try/except boundary that the
  callback exceptions bypass), `run_worker` (~L327), `main`/`__main__`
  (~L454-508, where supervision + `--once` bypass slot in).
- `app/services/engine.py` — **review only.** `EnginePool._restart_worker` (L409) and
  `_analyse` / `_analyse_with_pv` (L435 / L486) already restart individual workers and
  always return the slot to the queue, so no queue deadlock. The gap is
  mass-simultaneous death + the callback-level race, handled at the **process** level
  by the supervisor/watchdog. Likely NO change here — confirm during planning.
- `docker-compose.worker.yml` — has `restart: unless-stopped`; the bare-metal parity
  target. No change.
- `REMOTE_WORKER.md` — update so "Leave it running" / "Start the worker" can promise
  self-restart on crash/hang; note Docker users already had this.
- `temp/worker-error.txt` — the original crash log (2026-06-21).

### Constants / no magic numbers

`STALL_THRESHOLD_S`, supervisor backoff (and cap, if exponential), checker poll
interval, and the child-marker env-var name all become named constants.

### Verification ideas

- Kill all `stockfish` child processes mid-run (`taskkill` / `pkill`) → worker detects,
  child exits, parent relaunches, processing resumes.
- Simulate a hang (or sleep/resume the machine) → stall threshold fires → restart.
- `--once` still exits cleanly with the correct exit code (no supervision wrap).
- SIGINT / Ctrl-C stops cleanly with no relaunch storm.
- Existing `remote_eval_worker` tests still pass; add unit tests for the
  supervisor child-vs-parent dispatch and the heartbeat/stall predicate (pure
  function, testable without real engines).

## Open Questions for Planning

- Backoff shape: fixed few-seconds vs capped exponential. Lean **fixed-small** for a
  volunteer tool (predictable).
- Add the "N callback-exceptions in a window → exit" fast-path, or rely solely on the
  stall timer?
- Max-restart safety valve? Probably **NOT** (a volunteer wants it to keep trying
  forever, matching `unless-stopped`). Confirm.

## Notes

Captured 2026-06-21 from a live crash investigation. Decisions D1–D5 are locked from
that discussion; the open questions above are intentionally deferred to plan time.
