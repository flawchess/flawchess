---
phase: quick-260702-snc
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - scripts/remote_eval_worker.py
  - tests/test_remote_eval_worker.py
  - docker-compose.worker.yml
  - Dockerfile.worker
  - REMOTE_WORKER.md
autonomous: true
requirements: [SEED-063]
must_haves:
  truths:
    - "Running the worker with no flags launches a supervisor that relaunches the real work process whenever it exits for any reason."
    - "A wedged worker (all Stockfish dead, in-flight future never resolves) self-terminates via a watchdog and is relaunched, because a hang is converted into a process exit."
    - "Ctrl-C / SIGINT (interactive and Docker `docker stop`) stops the worker cleanly with no relaunch storm."
    - "`--once` runs the work directly with no supervision and exits with the real exit code."
    - "Docker logs stay bounded during an InvalidStateError flood, and `docker ps` shows `unhealthy` while wedged."
  artifacts:
    - "scripts/remote_eval_worker.py (supervisor + child dispatch + watchdog + loop exception handler)"
    - "tests/test_remote_eval_worker.py (unit tests for the pure dispatch + stall predicates)"
    - "docker-compose.worker.yml (log rotation + observability healthcheck)"
  key_links:
    - "child-marker env var connects supervisor (parent) to the child process role dispatch"
    - "heartbeat file mtime connects the watchdog's last-progress signal to the Docker healthcheck"
---

<objective>
Make the remote eval worker (`scripts/remote_eval_worker.py`) self-supervising: it always
runs as a supervisor that spawns a child of itself to do the real lease/eval/submit work,
and an in-child watchdog converts a HANG into a process exit so the supervisor (and Docker's
`restart: unless-stopped`) can relaunch it. Implements SEED-063 locked decisions D1–D6.

Purpose: Volunteers run the worker on Windows/macOS/Linux (bare-metal and Docker) with no
supervisor. A crash or — critically — a silent hang (the observed InvalidStateError storm where
all Stockfish subprocesses die at once and the in-flight future never resolves) currently stops
contributing eval capacity until a human notices. The watchdog is the load-bearing fix: it turns
a hang into `os._exit(1)`, which is the exit that both the in-process supervisor AND
`restart: unless-stopped` need to react to.

Output: Restructured worker script (supervisor/child/`--once` dispatch, signal handling,
watchdog heartbeat + checker + asyncio exception handler), unit tests for the pure decision logic,
Docker hardening (log rotation + observability healthcheck), a Dockerfile comment review, and a
REMOTE_WORKER.md update.
</objective>

<execution_context>
@$HOME/.claude/gsd-core/workflows/execute-plan.md
@$HOME/.claude/gsd-core/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@.planning/seeds/SEED-063-remote-worker-self-supervising-auto-restart.md
@scripts/remote_eval_worker.py
@tests/test_remote_eval_worker.py
@docker-compose.worker.yml
@Dockerfile.worker
@REMOTE_WORKER.md

Locked decisions (do NOT revisit): D1 cross-platform Python supervisor (no OS-specific tooling);
D2 supervisor lives INSIDE remote_eval_worker.py (no separate script); D3 ALWAYS supervised, no
`--supervise` flag, parent-vs-child via an INTERNAL env marker (NOT argparse); D4 full process
restart on failure (do NOT add in-process EnginePool rebuild); D5 keep `restart: unless-stopped`;
D6 Docker hardening (log rotation, observability-only healthcheck, PID-1 signal correctness).

Resolved open questions (seed leanings, confirmed): backoff = fixed-small (predictable, NOT
capped-exponential); STALL_THRESHOLD_S ~= 4 minutes (NOT seconds); N-callback-in-window fast-path
= DEFERRED (the stall timer alone is sufficient — but STILL install the loop exception handler to
count + Sentry-capture the storm); NO max-restart safety valve (keep trying forever, matching
`unless-stopped`); signal handling via `signal.signal()` / `KeyboardInterrupt`, NEVER
`loop.add_signal_handler()` (Unix-only, raises NotImplementedError on Windows ProactorEventLoop).

All new numbers/strings become named constants alongside the existing "Named constants" block.
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Supervisor + child/once dispatch + cross-platform signal handling</name>
  <files>scripts/remote_eval_worker.py</files>
  <behavior>
    - `_worker_role(once=True, child_marker=False)` returns "once".
    - `_worker_role(once=False, child_marker=True)` returns "child".
    - `_worker_role(once=False, child_marker=False)` returns "supervisor".
    - `_worker_role(once=True, child_marker=True)` returns "once" (once always bypasses supervision).
  </behavior>
  <action>
    Restructure the entrypoint so the script is ALWAYS the supervisor unless `--once` (D3).

    Add named constants in the existing "Named constants" block: `_CHILD_MARKER_ENV` = the internal
    marker env var name (e.g. "_FLAWCHESS_WORKER_CHILD"), `_CHILD_MARKER_VALUE` = "1", and
    `SUPERVISOR_BACKOFF_S` (fixed-small, e.g. 3.0). Add imports: `os`, `signal`, `subprocess`,
    `time`, `contextlib`, `from types import FrameType`, `from typing import Literal` (keep the
    existing `cast` import).

    Add a PURE predicate `_worker_role(once: bool, child_marker: bool) -> Literal["once", "supervisor", "child"]`
    that returns "once" if once else "child" if child_marker else "supervisor". This is the unit-tested
    dispatch logic — keep it side-effect-free.

    Add `_run_supervisor() -> int` (SYNCHRONOUS — subprocess + signal + time.sleep, NOT asyncio):
    install `signal.signal(signal.SIGINT, handler)` and `signal.signal(signal.SIGTERM, handler)` (D6
    PID-1 correctness — Docker `STOPSIGNAL SIGINT` and Linux SIGTERM). Do NOT use
    `loop.add_signal_handler()`. The handler (signature `(signum: int, frame: FrameType | None) -> None`)
    sets a stop flag and, ONLY on POSIX (`if os.name == "posix":`), forwards SIGINT to the live child via
    `proc.send_signal(signal.SIGINT)` guarded by try/except (ProcessLookupError, OSError) — on Windows the
    console Ctrl-C already reaches the whole process group, and `send_signal(SIGINT)` raises there, so it
    must be skipped. Loop while not stopped: spawn the child with
    `subprocess.Popen([sys.executable, str(Path(__file__).resolve()), *sys.argv[1:]], env={**os.environ, _CHILD_MARKER_ENV: _CHILD_MARKER_VALUE})`,
    `code = proc.wait()` (this reaps the direct child — PID-1 zombie reaping for the one child we own), then
    if stop was requested break (intentional stop → NO relaunch), else log the exit code and
    `time.sleep(SUPERVISOR_BACKOFF_S)` before relaunching. NO max-restart cap (keep trying forever). Return 0
    on clean stop. Note in a comment that grandchild Stockfish processes are either already dead (the wedge
    case) or cleanly quit by EnginePool.stop() (the graceful case), so no broader reaping is needed (D4 — do
    NOT add heavier process management).

    Convert `main()` to a synchronous `def main() -> int`: parse_args, resolve token, and if the token is
    missing print the existing error and `return 1` (fail fast in BOTH supervisor and child so a missing
    token never becomes an infinite relaunch loop). Init Sentry as today. Compute
    `role = _worker_role(once=args.once, child_marker=os.environ.get(_CHILD_MARKER_ENV) == _CHILD_MARKER_VALUE)`.
    If role == "supervisor": log a one-line "supervisor (auto-restart on crash/hang)" startup message and
    `return _run_supervisor()`. Otherwise (role "child" or "once"): generate worker_id and log the existing
    startup line, then `asyncio.run(_run_async(args, token, worker_id, supervised=(role == "child")))` and
    `return 0`. Task 2 defines `_run_async` and the watchdog; for THIS task, add a thin `_run_async` that
    calls `run_worker(...)` directly (supervised branch filled in by Task 2) so the file stays runnable.

    Update `__main__`: `try: sys.exit(main()) except KeyboardInterrupt: pass`. Keep the existing swallow so
    the child's asyncio.run Ctrl-C exits 0 without a crash-looking traceback. The child is a fresh subprocess
    with DEFAULT signal handlers, so SIGINT there raises KeyboardInterrupt into `run_worker`'s existing
    handler → clean EnginePool shutdown; do NOT install signal handlers in the child.

    Do NOT add a `--supervise` argparse flag and do NOT surface the marker env var in `--help` (D3).
    ty: annotate the signal handler, `_run_supervisor -> int`, `main -> int`, and `_worker_role`'s Literal
    return explicitly.
  </action>
  <verify>
    <automated>cd /home/aimfeld/Projects/Python/flawchess && uv run ruff check scripts/remote_eval_worker.py && uv run ty check scripts/remote_eval_worker.py 2>&1 | tail -3</automated>
  </verify>
  <done>_worker_role and _run_supervisor exist; main() is sync returning int; no --supervise flag; ruff + ty clean for the script.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Watchdog heartbeat + checker + asyncio exception handler + unit tests</name>
  <files>scripts/remote_eval_worker.py, tests/test_remote_eval_worker.py</files>
  <behavior>
    - `_is_stalled(now=100.0, last_progress=0.0, threshold_s=50.0)` returns True (100-0 > 50).
    - `_is_stalled(now=40.0, last_progress=0.0, threshold_s=50.0)` returns False (idle-but-healthy, not stalled).
    - `_Heartbeat.mark()` advances `last_progress` toward now and writes the current wall-clock to the heartbeat file (its mtime freshens).
    - `_worker_role` cases from Task 1 (add tests here since both predicates ship together).
  </behavior>
  <action>
    Add named constants: `STALL_THRESHOLD_S` (~= 240.0, i.e. 4 minutes — MUST clear the slowest legit cycle
    of ~125s; NOT seconds), `WATCHDOG_POLL_INTERVAL_S` (e.g. 15.0), `HEARTBEAT_FILE_ENV` = the heartbeat file
    override env var name (e.g. "FLAWCHESS_WORKER_HEARTBEAT_FILE"), and `_DEFAULT_HEARTBEAT_FILE` =
    `Path(tempfile.gettempdir()) / "flawchess-worker.heartbeat"` (add `import tempfile`).

    Add PURE predicate `_is_stalled(now: float, last_progress: float, threshold_s: float) -> bool` returning
    `(now - last_progress) > threshold_s`. This is the unit-tested stall logic; the checker never calls
    os._exit in this function so it is safe to test.

    Add `class _Heartbeat`: `__init__(self, path: Path | None) -> None` sets `self.last_progress: float = time.time()`.
    `mark(self) -> None` sets `self.last_progress = time.time()` and, if path is not None, writes
    `str(self.last_progress)` to the file inside try/except OSError (heartbeat is observability-only — a write
    failure must NEVER kill the worker). Writing the file freshens its mtime for the Docker healthcheck (D6).
    Use WALL-CLOCK `time.time()` (NOT monotonic) so a laptop sleep produces a huge gap → instant restart on
    resume.

    Add `_heartbeat_file_path() -> Path` returning `Path(os.environ[HEARTBEAT_FILE_ENV])` if that env is set
    else `_DEFAULT_HEARTBEAT_FILE`.

    Add `async def _watchdog_checker(heartbeat: _Heartbeat, threshold_s: float, poll_interval_s: float) -> None`:
    loop `await asyncio.sleep(poll_interval_s)`, then if `_is_stalled(time.time(), heartbeat.last_progress, threshold_s)`
    log a "no progress for >Ns — forcing restart" line, `sentry_sdk.capture_message(...)` (a fixed message,
    NO interpolated variables per the Sentry grouping rule), and `os._exit(1)`. os._exit intentionally bypasses
    cleanup — the process is wedged with dead engines that cannot be cleanly stopped.

    Add the loop exception handler `_loop_exception_handler(loop: asyncio.AbstractEventLoop, context: dict[str, object]) -> None`:
    pull `context.get("exception")` and `sentry_sdk.capture_exception(exc)` when present (else
    `sentry_sdk.capture_message` a fixed string), plus a terse `_log` line. This captures the InvalidStateError
    storm that fires in the event loop's `_call_connection_lost` callback and today bypasses `_run_loop`'s
    try/except entirely (root cause step 3 in the seed). Do NOT add the N-in-window fast-path (deferred — the
    stall timer covers it). Sentry groups the identical storm entries, so per-callback capture is safe.

    Add `async def _run_async(args: argparse.Namespace, token: str, worker_id: str, supervised: bool) -> None`:
    when `supervised`, build `heartbeat = _Heartbeat(_heartbeat_file_path())`,
    `asyncio.get_running_loop().set_exception_handler(_loop_exception_handler)`, start
    `checker = asyncio.create_task(_watchdog_checker(heartbeat, STALL_THRESHOLD_S, WATCHDOG_POLL_INTERVAL_S))`,
    then `try: await run_worker(..., heartbeat=heartbeat) finally: checker.cancel();` await it swallowing
    CancelledError via `contextlib.suppress`. When NOT supervised (`--once`): `await run_worker(..., heartbeat=None)`
    with NO watchdog (a bounded one-shot run needs no supervision).

    Thread the heartbeat through: give `run_worker(...)` a new trailing param `heartbeat: _Heartbeat | None = None`
    (default None keeps existing callers/tests valid) and pass it to `_run_loop`. Give `_run_loop(...)` the same
    trailing `heartbeat: _Heartbeat | None = None` param and, after each `_run_cycle` returns WITHOUT raising,
    call `heartbeat.mark()` when heartbeat is not None BEFORE the `if stop: return`. CRITICAL: a clean 204 idle
    cycle returns normally from `_run_cycle`, so it counts as progress — an idle worker with an empty queue is
    healthy, not stalled. Do NOT mark in the `except` branch (a failed cycle is not progress).

    Tests (`tests/test_remote_eval_worker.py`): add unit tests importing `_worker_role`, `_is_stalled`,
    `_Heartbeat`, `STALL_THRESHOLD_S`. Cover: the four `_worker_role` cases from Task 1's behavior; `_is_stalled`
    True (gap > threshold) and False (idle-but-under-threshold); `_Heartbeat.mark` writes a tmp_path file whose
    contents parse as a float and whose mtime is recent, and advances `last_progress`. Keep them pure — do NOT
    call `_watchdog_checker` (it calls os._exit and would kill the test runner). All existing tests must still pass.
  </action>
  <verify>
    <automated>cd /home/aimfeld/Projects/Python/flawchess && uv run pytest tests/test_remote_eval_worker.py -q 2>&1 | tail -8 && uv run ty check scripts/remote_eval_worker.py tests/test_remote_eval_worker.py 2>&1 | tail -3</automated>
  </verify>
  <done>_is_stalled, _Heartbeat, _watchdog_checker, _loop_exception_handler, _run_async exist; heartbeat marked on every successful cycle incl. idle 204; new unit tests pass; full worker test file green; ty clean.</done>
</task>

<task type="auto">
  <name>Task 3: Docker hardening (compose logging + healthcheck), Dockerfile/engine review, doc update</name>
  <files>docker-compose.worker.yml, Dockerfile.worker, REMOTE_WORKER.md</files>
  <action>
    docker-compose.worker.yml (D6): add a `logging:` block (`driver: json-file`, `options: max-size: "10m"`,
    `max-file: "3"`) so the unbounded InvalidStateError storm cannot fill the host disk before the watchdog
    fires. Add `FLAWCHESS_WORKER_HEARTBEAT_FILE: /tmp/flawchess-worker.heartbeat` to `environment:` so the
    worker and healthcheck agree on the path. Add an OBSERVABILITY-ONLY `healthcheck:` whose `test:` runs a
    python one-liner that exits 0 when the heartbeat file exists and `time.time() - os.path.getmtime(path)`
    is under a staleness bound LARGER than STALL_THRESHOLD_S (e.g. 300s — the watchdog fires first at ~240s),
    else exits 1; set `interval`, `timeout`, `retries`, and a `start_period` (~120s) that covers EnginePool
    startup. Add a comment: plain `docker compose` does NOT act on health status (only Swarm / an autoheal
    sidecar do) — the in-process watchdog remains the restart mechanism; this only surfaces `unhealthy` in
    `docker ps`. Do NOT add an autoheal sidecar and do NOT require Swarm (D6, rejected as over-engineering).
    Keep `restart: unless-stopped` (D5).

    Dockerfile.worker (review under D6): keep `STOPSIGNAL SIGINT` and the `CMD` unchanged (it now launches the
    supervisor). Update ONLY the comment near STOPSIGNAL to reflect the new PID-1 owner: the SUPERVISOR is now
    PID 1; on `docker stop` it receives SIGINT, forwards it to the child (clean EnginePool shutdown + exit 0),
    reaps the child, and exits without relaunching — so `docker stop` still exits cleanly (no SIGTERM grace-period
    SIGKILL / exit 137). No functional Dockerfile change.

    app/services/engine.py (REVIEW ONLY — confirm NO change): `_restart_worker` / `_analyse` / `_analyse_with_pv`
    already restart individual workers and always return the slot to the queue, so there is no queue deadlock;
    the mass-simultaneous-death + callback-race failure is handled at the PROCESS level by the supervisor/watchdog
    (D4). Confirm with a git-diff check that engine.py is untouched.

    REMOTE_WORKER.md: update the "Leave it running" (step 7, Linux/macOS) copy and the Docker section closing line
    so both can promise self-restart on crash OR hang. State plainly that stopping with Ctrl-C (or `docker stop`)
    is clean and does not trigger a relaunch. Keep the prose plain and volunteer-friendly (no jargon like
    "watchdog"/"SIGINT" in the user-facing steps); em-dashes sparingly.
  </action>
  <verify>
    <automated>cd /home/aimfeld/Projects/Python/flawchess && python -c "import yaml,sys; d=yaml.safe_load(open('docker-compose.worker.yml')); w=d['services']['worker']; assert 'logging' in w and 'healthcheck' in w and w['restart']=='unless-stopped', w; print('compose ok')" && git diff --quiet app/services/engine.py && echo "engine.py unchanged"</automated>
  </verify>
  <done>Compose has logging + healthcheck + `restart: unless-stopped`; Dockerfile STOPSIGNAL/CMD unchanged with updated comment; engine.py untouched; REMOTE_WORKER.md promises self-restart and clean stop.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| supervisor (PID 1) → child process | supervisor spawns a child of itself with an internal env marker; a compromised/altered env could change dispatch role |
| child → OS signals | SIGINT/SIGTERM delivery drives clean stop vs. relaunch; cross-OS delivery differs |

## STRIDE Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation Plan |
|-----------|----------|-----------|----------|-------------|-----------------|
| T-snc-01 | Denial of Service | watchdog `os._exit(1)` on false-positive stall | medium | mitigate | STALL_THRESHOLD_S ~= 240s clears the slowest legit cycle (~125s); heartbeat marks on every completed cycle incl. idle 204 so a healthy idle worker is never killed |
| T-snc-02 | Denial of Service | supervisor infinite relaunch of a config error (missing token) | medium | mitigate | token presence checked BEFORE role dispatch → both supervisor and child exit 1 immediately; no relaunch loop |
| T-snc-03 | Tampering | `_CHILD_MARKER_ENV` in child env | low | accept | internal-only marker; the worker is a trusted-operator tool run by the volunteer themselves; a hostile local env can already run arbitrary code |
| T-snc-04 | Denial of Service | unbounded InvalidStateError log flood filling host disk | high | mitigate | docker-compose `logging:` max-size/max-file rotation caps container logs |
</threat_model>

<verification>
Automated (run all): `cd /home/aimfeld/Projects/Python/flawchess && uv run ruff check scripts/remote_eval_worker.py tests/test_remote_eval_worker.py && uv run ty check scripts/remote_eval_worker.py tests/test_remote_eval_worker.py && uv run pytest tests/test_remote_eval_worker.py -q`

Manual (cross-OS, cannot be automated here — recommend before merge, at least on the dev Linux box):
- Start the worker with no flags; `pkill stockfish` mid-run → child self-exits and the supervisor relaunches, processing resumes.
- Ctrl-C the supervisor → clean stop, no relaunch storm.
- `uv run python scripts/remote_eval_worker.py --once` exits cleanly with the real exit code (no supervision).
- Docker: `docker compose -f docker-compose.worker.yml up -d --build`, kill stockfish inside the container → `docker ps` shows `unhealthy` then healthy again after relaunch; `docker stop` exits cleanly (not 137); `docker logs` stays bounded after an error flood.
</verification>

<success_criteria>
- Worker with no flags runs as a supervisor that relaunches the child on ANY exit with fixed backoff, no max cap.
- Watchdog converts a hang (no completed cycle for > STALL_THRESHOLD_S) into `os._exit(1)`; idle 204 cycles count as progress.
- asyncio loop exception handler Sentry-captures the InvalidStateError storm that previously bypassed `_run_loop`.
- SIGINT/SIGTERM stop cleanly with no relaunch; `--once` bypasses supervision entirely.
- Docker: log rotation + observability healthcheck present; `restart: unless-stopped` retained; engine.py unchanged.
- `ruff`, `ty`, and the full `test_remote_eval_worker.py` suite pass; new pure-logic unit tests included.
</success_criteria>

<output>
Create `.planning/quick/260702-snc-self-supervising-auto-restart-watchdog-f/260702-snc-SUMMARY.md` when done.
</output>