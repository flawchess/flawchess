#!/usr/bin/env python3
"""Stress-test monitor for the FlawChess import pipeline.

Samples docker container memory/CPU, host memory/swap, and import-job
progress at a fixed interval and writes the same plaintext block format as
the historical reference logs:

  - logs/import-stress-20k-each-2026-05-20.log (Phase 41.1 OOM run)
  - logs/import-stress-20k-each-2026-05-21.log (Phase 91 follow-up)

Two environments are supported:

  --target dev   : sample local Docker on this machine, query the dev DB
                   container (flawchess-dev-db-1) directly. No SSH.

  --target prod  : sample Docker on the production server via SSH (default
                   host: `flawchess`, matching CLAUDE.md), query the prod
                   DB container (flawchess-db-1) via the same SSH session.
                   You can sit in dev and monitor a live prod import.

The script terminates automatically once every monitored import_job has
reached a terminal status (completed/failed) AND the Stockfish eval
pending count is zero — confirmed across two consecutive ticks to avoid
exiting on a transient race. Override with --no-stop-on-complete to keep
sampling indefinitely; --max-duration-min is a hard safety cap.

Output block format (one block per tick):

    === <ISO-8601 UTC timestamp> ===
    flawchess-caddy-1 28.98MiB / 7.564GiB 0.37% CPU=0.00%
    flawchess-backend-1 955.4MiB / 7.564GiB 12.33% CPU=0.19%
    flawchess-umami-1 96.27MiB / 7.564GiB 1.24% CPU=0.00%
    flawchess-db-1 2.705GiB / 7.564GiB 35.76% CPU=0.19%
    mem used=4055M free=247M avail=3690M
    swap used=327M
    job: <uuid>|<platform>|<status>|<games_fetched>|<games_imported>|<games_evaluated>

Typical use:

    # Monitor a live prod import from your laptop:
    uv run python scripts/import_stress_monitor.py --target prod

    # Dev-side: run alongside a local dual-import (or measure_dual_import_rss.py):
    uv run python scripts/import_stress_monitor.py --target dev

For dev-side Phase 91 acceptance gates with structured pass/fail, use
scripts/measure_dual_import_rss.py instead — this script is a lightweight
black-box monitor with the historical log format.
"""

from __future__ import annotations

import argparse
import logging
import shlex
import signal
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants — no magic numbers
# ---------------------------------------------------------------------------

DEFAULT_INTERVAL_S: int = 33
DEFAULT_LOOKBACK_MIN: int = 90
DEFAULT_LABEL: str = "import-stress"
DEFAULT_OUT_DIR: Path = Path("logs")
DEFAULT_MAX_DURATION_MIN: int = 240
SHELL_TIMEOUT_S: float = 30.0

# Two consecutive zero-pending readings before exit. Postgres replication of
# evals_completed_at is not the issue here, but the cold-drain queue can
# briefly empty between batches; one tick of grace prevents premature exit.
REQUIRED_ZERO_STREAK: int = 2

PROD_SSH_HOST: str = "flawchess"
PROD_DB_CONTAINER: str = "flawchess-db-1"
PROD_CONTAINER_PREFIX: str = "flawchess-"
PROD_PG_USER_DEFAULT: str = "flawchess"
PROD_PG_DB_DEFAULT: str = "flawchess"

DEV_DB_CONTAINER: str = "flawchess-dev-db-1"
DEV_CONTAINER_PREFIX: str = "flawchess-dev-"
DEV_PG_USER_DEFAULT: str = "postgres"
DEV_PG_DB_DEFAULT: str = "flawchess"

TERMINAL_STATUSES: frozenset[str] = frozenset({"completed", "failed"})

DOCKER_STATS_FMT: str = "{{.Name}} {{.MemUsage}} {{.MemPerc}} CPU={{.CPUPerc}}"

logger = logging.getLogger("import_stress_monitor")


# ---------------------------------------------------------------------------
# Command runner — local or SSH
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Runner:
    """Executes a shell command locally or via SSH.

    When `ssh_host` is set, commands are forwarded with `ssh -o BatchMode=yes`,
    which fails fast if the host requires interactive auth instead of hanging.
    """

    ssh_host: str | None

    def run(self, cmd: str, timeout: float = SHELL_TIMEOUT_S) -> str:
        if self.ssh_host:
            argv = ["ssh", "-o", "BatchMode=yes", self.ssh_host, cmd]
        else:
            argv = ["bash", "-c", cmd]
        try:
            result = subprocess.run(
                argv, capture_output=True, text=True, timeout=timeout, check=False
            )
        except subprocess.TimeoutExpired:
            logger.warning("command timed out after %ss: %s", timeout, cmd[:80])
            return ""
        except FileNotFoundError as exc:
            logger.error("required binary missing: %s", exc)
            return ""
        if result.returncode != 0 and result.stderr.strip():
            logger.debug("non-zero exit (%s): %s", result.returncode, result.stderr.strip()[:200])
        return result.stdout


# ---------------------------------------------------------------------------
# Collectors
# ---------------------------------------------------------------------------


def collect_docker_stats(runner: Runner, prefix: str) -> str:
    """One `docker stats` snapshot, optionally filtered to containers whose
    name starts with `prefix`. Empty `prefix` returns all containers."""
    raw = runner.run(f"docker stats --no-stream --format '{DOCKER_STATS_FMT}'")
    if not raw.strip():
        return ""
    if not prefix:
        return raw.strip()
    return "\n".join(line for line in raw.splitlines() if line.startswith(prefix))


def collect_host_memory(runner: Runner) -> str:
    """Two lines: `mem used=... free=... avail=...` + `swap used=...` in MB.

    Matches the historical log format exactly (`free -m` column layout:
    total used free shared buff/cache available)."""
    raw = runner.run("free -m")
    mem_line = ""
    swap_line = ""
    for line in raw.splitlines():
        parts = line.split()
        if not parts:
            continue
        if parts[0] == "Mem:" and len(parts) >= 7:
            mem_line = f"mem used={parts[2]}M free={parts[3]}M avail={parts[6]}M"
        elif parts[0] == "Swap:" and len(parts) >= 3:
            swap_line = f"swap used={parts[2]}M"
    return "\n".join(x for x in (mem_line, swap_line) if x)


def build_job_query(lookback_min: int, user_id: int | None) -> str:
    """SQL that emits one `job: ...` line per recent import.

    The third numeric column is `games_evaluated` for that user+platform —
    i.e. games whose Stockfish eval finished. Joining via user+platform is
    accurate because import_jobs uniquely scope a (user, platform) pair."""
    user_filter = f" AND i.user_id = {int(user_id)}" if user_id is not None else ""
    return f"""
SELECT 'job: ' || i.id
            || '|' || i.platform
            || '|' || i.status
            || '|' || i.games_fetched
            || '|' || i.games_imported
            || '|' || COALESCE((
                 SELECT count(*) FROM games g
                  WHERE g.user_id = i.user_id
                    AND g.platform = i.platform
                    AND g.evals_completed_at IS NOT NULL
               ), 0)
  FROM import_jobs i
 WHERE i.started_at >= NOW() - INTERVAL '{int(lookback_min)} minutes'{user_filter}
 ORDER BY i.started_at;
""".strip()


def _psql_exec(runner: Runner, db_container: str, pg_user: str, pg_db: str, sql: str) -> str:
    cmd = (
        f"docker exec -i {shlex.quote(db_container)} "
        f"psql -U {shlex.quote(pg_user)} -d {shlex.quote(pg_db)} -tAc {shlex.quote(sql)}"
    )
    return runner.run(cmd).strip()


def collect_jobs(
    runner: Runner, db_container: str, pg_user: str, pg_db: str, query: str
) -> tuple[str, list[str]]:
    """Run the per-job query; return (raw_output, list_of_statuses)."""
    out = _psql_exec(runner, db_container, pg_user, pg_db, query)
    statuses: list[str] = []
    for line in out.splitlines():
        if not line.startswith("job: "):
            continue
        parts = line[len("job: ") :].split("|")
        if len(parts) >= 3:
            statuses.append(parts[2])
    return out, statuses


def collect_pending_eval_count(
    runner: Runner,
    db_container: str,
    pg_user: str,
    pg_db: str,
    lookback_min: int,
    user_id: int | None,
) -> int | None:
    """Games still pending Stockfish eval, scoped to either a specific user
    or all users with import_jobs started in the lookback window.

    Returns None if the query failed (treat as "don't exit yet")."""
    if user_id is not None:
        sql = (
            f"SELECT count(*) FROM games WHERE evals_completed_at IS NULL "
            f"AND user_id = {int(user_id)};"
        )
    else:
        sql = (
            "SELECT count(*) FROM games g WHERE g.evals_completed_at IS NULL "
            f"AND g.user_id IN (SELECT DISTINCT user_id FROM import_jobs "
            f"WHERE started_at >= NOW() - INTERVAL '{int(lookback_min)} minutes');"
        )
    out = _psql_exec(runner, db_container, pg_user, pg_db, sql)
    try:
        return int(out)
    except ValueError:
        logger.debug("could not parse pending count from psql output: %r", out)
        return None


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------


def _iso_utc_now() -> str:
    """ISO-8601 with `+00:00` offset (colon-separated) — matches existing log."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument(
        "--target",
        choices=["dev", "prod"],
        default="dev",
        help="Environment to monitor. dev=local docker, prod=SSH to flawchess host.",
    )
    ap.add_argument(
        "--ssh-host",
        default=None,
        help=f"SSH host when --target=prod (default: {PROD_SSH_HOST}).",
    )
    ap.add_argument("--interval", type=int, default=DEFAULT_INTERVAL_S, help="Sample interval (s).")
    ap.add_argument("--lookback-min", type=int, default=DEFAULT_LOOKBACK_MIN)
    ap.add_argument("--label", default=DEFAULT_LABEL, help="Filename label when --out is omitted.")
    ap.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Output log path. Defaults to logs/<label>-<env>-<date>.log.",
    )
    ap.add_argument("--db-container", default=None, help="Override Postgres container name.")
    ap.add_argument(
        "--container-prefix",
        default=None,
        help="Container-name prefix filter for docker stats. Pass '' for all containers.",
    )
    ap.add_argument("--pg-user", default=None)
    ap.add_argument("--pg-db", default=None)
    ap.add_argument(
        "--user-id",
        type=int,
        default=None,
        help="Restrict monitoring (and the eval-pending count) to a single user_id.",
    )
    ap.add_argument(
        "--no-stop-on-complete",
        action="store_true",
        help="Keep sampling even after all imports are terminal and evals=0.",
    )
    ap.add_argument(
        "--max-duration-min",
        type=int,
        default=DEFAULT_MAX_DURATION_MIN,
        help="Safety cap on total monitor runtime (minutes).",
    )
    ap.add_argument("--verbose", "-v", action="store_true")
    return ap.parse_args(argv)


def _resolve_env_defaults(args: argparse.Namespace) -> tuple[str | None, str, str, str, str]:
    """Return (ssh_host, db_container, container_prefix, pg_user, pg_db) for the target."""
    is_prod = args.target == "prod"
    ssh_host: str | None
    if is_prod:
        ssh_host = args.ssh_host or PROD_SSH_HOST
    else:
        # In dev, --ssh-host is still honoured if explicitly passed (e.g. for a
        # remote dev box), but defaults to local execution.
        ssh_host = args.ssh_host
    db_container = args.db_container or (PROD_DB_CONTAINER if is_prod else DEV_DB_CONTAINER)
    container_prefix = (
        args.container_prefix
        if args.container_prefix is not None
        else (PROD_CONTAINER_PREFIX if is_prod else DEV_CONTAINER_PREFIX)
    )
    pg_user = args.pg_user or (PROD_PG_USER_DEFAULT if is_prod else DEV_PG_USER_DEFAULT)
    pg_db = args.pg_db or (PROD_PG_DB_DEFAULT if is_prod else DEV_PG_DB_DEFAULT)
    return ssh_host, db_container, container_prefix, pg_user, pg_db


def _preflight(runner: Runner, db_container: str) -> None:
    """Fail fast if docker isn't reachable or the DB container is missing.

    Raises SystemExit with a clear message instead of silently producing empty
    blocks every tick."""
    docker_ok = runner.run("docker version --format '{{.Server.Version}}'").strip()
    if not docker_ok:
        raise SystemExit(
            "import_stress_monitor: cannot reach docker on the target host. "
            "Check that Docker is running and (for --target prod) that you can `ssh flawchess docker ps`."
        )
    inspect = runner.run(f"docker inspect -f '{{{{.State.Status}}}}' {shlex.quote(db_container)}")
    if "running" not in inspect:
        raise SystemExit(
            f"import_stress_monitor: DB container {db_container!r} is not running on the target host "
            f"(docker inspect returned: {inspect.strip() or 'no output'}). "
            "Pass --db-container to override if your stack uses a different name."
        )


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        stream=sys.stderr,
    )

    ssh_host, db_container, container_prefix, pg_user, pg_db = _resolve_env_defaults(args)
    runner = Runner(ssh_host=ssh_host)

    out_path = args.out or (
        DEFAULT_OUT_DIR
        / f"{args.label}-{args.target}-{datetime.now(timezone.utc).strftime('%Y-%m-%d')}.log"
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)

    _preflight(runner, db_container)

    job_query = build_job_query(args.lookback_min, args.user_id)
    deadline = time.monotonic() + args.max_duration_min * 60
    eval_zero_streak = 0

    logger.info(
        "target=%s ssh=%s db=%s prefix=%r writing=%s every=%ss",
        args.target,
        ssh_host or "local",
        db_container,
        container_prefix,
        out_path,
        args.interval,
    )

    # Cooperative termination on SIGINT/SIGTERM — finish the current tick,
    # flush the file, then exit. Avoids a half-written block at the tail.
    stop_requested = False

    def _request_stop(signum: int, _frame: object) -> None:
        nonlocal stop_requested
        logger.info("signal %s received, stopping after this tick", signum)
        stop_requested = True

    signal.signal(signal.SIGINT, _request_stop)
    signal.signal(signal.SIGTERM, _request_stop)

    exit_reason = "interrupted"
    with out_path.open("a", encoding="utf-8") as fh:
        while not stop_requested:
            ts = _iso_utc_now()
            fh.write(f"=== {ts} ===\n")

            stats = collect_docker_stats(runner, container_prefix)
            if stats:
                fh.write(stats + "\n")

            mem = collect_host_memory(runner)
            if mem:
                fh.write(mem + "\n")

            jobs_raw, statuses = collect_jobs(runner, db_container, pg_user, pg_db, job_query)
            if jobs_raw:
                fh.write(jobs_raw + "\n")

            fh.flush()

            # Stop condition: every observed job is terminal AND eval queue is
            # empty for two consecutive ticks. If there are zero jobs in the
            # window we don't auto-stop (probably nothing started yet).
            if not args.no_stop_on_complete and statuses:
                all_terminal = all(s in TERMINAL_STATUSES for s in statuses)
                if all_terminal:
                    pending = collect_pending_eval_count(
                        runner, db_container, pg_user, pg_db, args.lookback_min, args.user_id
                    )
                    if pending == 0:
                        eval_zero_streak += 1
                        logger.info(
                            "all jobs terminal, pending evals = 0 (streak %d/%d)",
                            eval_zero_streak,
                            REQUIRED_ZERO_STREAK,
                        )
                        if eval_zero_streak >= REQUIRED_ZERO_STREAK:
                            exit_reason = "evals complete"
                            break
                    else:
                        if pending is not None:
                            logger.info("all jobs terminal, but %d eval(s) still pending", pending)
                        eval_zero_streak = 0
                else:
                    eval_zero_streak = 0

            if time.monotonic() >= deadline:
                exit_reason = "max-duration cap"
                break

            # Sleep in 1s slices so SIGINT/SIGTERM is responsive.
            for _ in range(args.interval):
                if stop_requested:
                    break
                time.sleep(1)

    logger.info("exit: %s — log: %s", exit_reason, out_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
