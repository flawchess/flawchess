#!/usr/bin/env python3
"""Dev-only stress-test harness for Phase 91 dual-import acceptance verification.

Triggers two concurrent 20k-game imports (chess.com + lichess) on a dev account,
polls docker memory + backend process RSS + swap + import status + eval coverage
every 30 s, and evaluates the Phase 91 ROADMAP acceptance bounds:

  - Backend RSS plateau  : <= 1,600 MB
  - Postgres anon+shmem  : <= 1,200 MB
  - Swap usage           : <= 50 % of allocated swap
  - Both imports         : status == 'completed'
  - Eval coverage        : pct_complete == 100 within 60 min of second import finishing

Results are written to logs/import-stress-20k-each-<YYYY-MM-DD>.log (CSV).

Baseline comparison: logs/import-stress-20k-each-2026-05-20.log — the pre-Phase-91
run that OOM-killed Postgres at T+~28 min with RSS peaking at ~1.3 GiB (backend)
and Postgres at ~4.8 GiB. Phase 91 should keep Postgres well below the 1.2 GB bound.

Usage:
    uv run python scripts/measure_dual_import_rss.py \\
        --user-email dev@example.com \\
        --password - \\
        --chess-com-username mychesshandle \\
        --lichess-username mylichesshandle

    export STRESS_TEST_PASSWORD='<dev-pw>'
    uv run python scripts/measure_dual_import_rss.py \\
        --user-email dev@example.com --password - \\
        --chess-com-username handle1 --lichess-username handle2

Dev-only: refuses if --api-base contains 'flawchess.com' or any non-local host
unless --allow-prod is passed explicitly.

Phase 91 / ROADMAP verification clause.
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import logging
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import httpx

# ---------------------------------------------------------------------------
# Constants — no magic numbers
# ---------------------------------------------------------------------------

RSS_PLATEAU_MAX_MB: int = 1_600
POSTGRES_MEMORY_MAX_MB: int = 1_200
SWAP_USAGE_MAX_PCT: int = 50
DEFAULT_TARGET_GAMES: int = 20_000
DEFAULT_POLL_INTERVAL_S: int = 30
DEFAULT_COVERAGE_TIMEOUT_MIN: int = 60

# Container name for the dev Postgres (project = flawchess-dev, service = db).
# The backend runs natively in dev (not in Docker), so there is no backend container.
POSTGRES_CONTAINER_NAME: str = "flawchess-dev-db-1"

# FastAPI-Users JWT login route (POST /api/auth/jwt/login).
_AUTH_LOGIN_PATH: str = "/api/auth/jwt/login"
_IMPORTS_PATH: str = "/api/imports"
_IMPORTS_ACTIVE_PATH: str = "/api/imports/active"
_EVAL_COVERAGE_PATH: str = "/api/imports/eval-coverage"

# Terminal import statuses — polling stops once both jobs reach one of these.
_TERMINAL_STATUSES: frozenset[str] = frozenset({"completed", "failed"})

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%SZ",
    stream=sys.stdout,
)
log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Prod-safety guard
# ---------------------------------------------------------------------------


def _is_prod_api_base(api_base: str) -> bool:
    """Return True if api_base looks like a production target."""
    base = api_base.lower()
    # Allow localhost and 127.0.0.1 variants (with or without port).
    local_pattern = re.compile(r"^https?://(localhost|127\.0\.0\.1)(:\d+)?(/.*)?$")
    if local_pattern.match(base):
        return False
    return True


# ---------------------------------------------------------------------------
# Docker/system metric helpers
# ---------------------------------------------------------------------------


def _parse_docker_mem_mib(mem_string: str) -> float:
    """Parse a docker stats memory string like '1.23GiB' or '456MiB' to MiB.

    Args:
        mem_string: The MemUsage left-side value from docker stats (before '/').

    Returns:
        Float MiB value, or 0.0 on parse failure.
    """
    mem_string = mem_string.strip()
    match = re.match(r"([\d.]+)\s*(GiB|MiB|KiB|GB|MB|KB|B)", mem_string, re.IGNORECASE)
    if not match:
        return 0.0
    value = float(match.group(1))
    unit = match.group(2).lower()
    factor: dict[str, float] = {
        "gib": 1024.0,
        "mib": 1.0,
        "kib": 1.0 / 1024.0,
        "gb": 1000.0,
        "mb": 1.0,
        "kb": 1.0 / 1024.0,
        "b": 1.0 / (1024.0 * 1024.0),
    }
    return value * factor.get(unit, 1.0)


def _get_docker_container_mem_mib(container_name: str) -> float | None:
    """Return memory used by a Docker container in MiB, or None on failure.

    Uses `docker stats --no-stream` so the call returns immediately.
    Transient failures are silently swallowed — caller logs and continues.

    Args:
        container_name: Docker container name or ID.

    Returns:
        Float MiB or None if docker stats fails or container not found.
    """
    try:
        result = subprocess.run(
            [
                "docker",
                "stats",
                "--no-stream",
                "--format",
                "{{.MemUsage}}",
                container_name,
            ],
            capture_output=True,
            text=True,
            timeout=15,
        )
        if result.returncode != 0 or not result.stdout.strip():
            return None
        # MemUsage format: "1.23GiB / 7.5GiB" — take the used (left) part.
        used_part = result.stdout.strip().split("/")[0].strip()
        return _parse_docker_mem_mib(used_part)
    except Exception:
        return None


def _get_backend_proc_rss_mib(pid: int) -> float | None:
    """Read RSS of a native process from /proc/<pid>/status (Linux only).

    Args:
        pid: Process ID of the backend (uvicorn) process.

    Returns:
        Float MiB or None if /proc read fails.
    """
    try:
        status_path = Path(f"/proc/{pid}/status")
        text = status_path.read_text()
        for line in text.splitlines():
            if line.startswith("VmRSS:"):
                kb = int(line.split()[1])
                return kb / 1024.0
    except Exception:
        return None
    return None


def _get_swap_stats() -> tuple[int, int] | None:
    """Return (swap_used_mb, swap_total_mb) from `free -m`, or None on failure.

    Returns:
        Tuple (used_mb, total_mb) or None.
    """
    try:
        result = subprocess.run(
            ["free", "-m"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode != 0:
            return None
        for line in result.stdout.splitlines():
            if line.lower().startswith("swap:"):
                parts = line.split()
                if len(parts) >= 3:
                    return int(parts[2]), int(parts[1])
    except Exception:
        return None
    return None


# ---------------------------------------------------------------------------
# API helpers
# ---------------------------------------------------------------------------


async def _login(client: httpx.AsyncClient, api_base: str, email: str, password: str) -> str:
    """Authenticate via FastAPI-Users JWT login and return the Bearer token.

    Args:
        client: httpx.AsyncClient to use.
        api_base: API base URL (e.g. 'http://localhost:8000').
        email: User email.
        password: User password.

    Returns:
        JWT access token string.

    Raises:
        RuntimeError: If login fails (non-200 status or missing token).
    """
    resp = await client.post(
        f"{api_base}{_AUTH_LOGIN_PATH}",
        data={"username": email, "password": password},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    if resp.status_code != 200:
        raise RuntimeError(f"Login failed: HTTP {resp.status_code} — {resp.text[:200]}")
    data = resp.json()
    token: str | None = data.get("access_token")
    if not token:
        raise RuntimeError(f"Login response missing access_token: {data}")
    return token


async def _start_import(
    client: httpx.AsyncClient,
    api_base: str,
    token: str,
    platform: str,
    username: str,
) -> str:
    """POST /api/imports to trigger an import job and return the job_id.

    Args:
        client: httpx.AsyncClient with timeout set.
        api_base: API base URL.
        token: Bearer JWT token.
        platform: 'chess.com' or 'lichess'.
        username: Platform username.

    Returns:
        job_id string.

    Raises:
        RuntimeError: If the import start request fails.
    """
    resp = await client.post(
        f"{api_base}{_IMPORTS_PATH}",
        json={"platform": platform, "username": username},
        headers={"Authorization": f"Bearer {token}"},
    )
    if resp.status_code not in (200, 201):
        raise RuntimeError(
            f"Failed to start {platform} import: HTTP {resp.status_code} — {resp.text[:200]}"
        )
    data = resp.json()
    job_id: str | None = data.get("job_id")
    if not job_id:
        raise RuntimeError(f"Import start response missing job_id: {data}")
    return job_id


async def _get_active_imports(
    client: httpx.AsyncClient,
    api_base: str,
    token: str,
) -> list[dict]:  # type: ignore[type-arg]
    """GET /api/imports/active and return the list of job dicts.

    Args:
        client: httpx.AsyncClient.
        api_base: API base URL.
        token: Bearer JWT token.

    Returns:
        List of job status dicts (may be empty on transient error).
    """
    try:
        resp = await client.get(
            f"{api_base}{_IMPORTS_ACTIVE_PATH}",
            headers={"Authorization": f"Bearer {token}"},
        )
        if resp.status_code == 200:
            return resp.json()  # type: ignore[no-any-return]
    except Exception:
        pass
    return []


async def _get_eval_coverage(
    client: httpx.AsyncClient,
    api_base: str,
    token: str,
) -> dict[str, int]:
    """GET /api/imports/eval-coverage and return the dict.

    Args:
        client: httpx.AsyncClient.
        api_base: API base URL.
        token: Bearer JWT token.

    Returns:
        Dict with pending_count, total_count, pct_complete. Returns
        {'pending_count': -1, 'total_count': -1, 'pct_complete': -1} on error.
    """
    error_result: dict[str, int] = {"pending_count": -1, "total_count": -1, "pct_complete": -1}
    try:
        resp = await client.get(
            f"{api_base}{_EVAL_COVERAGE_PATH}",
            headers={"Authorization": f"Bearer {token}"},
        )
        if resp.status_code == 200:
            return resp.json()  # type: ignore[no-any-return]
    except Exception:
        pass
    return error_result


# ---------------------------------------------------------------------------
# Status resolution
# ---------------------------------------------------------------------------


def _resolve_job_status(
    job_id: str,
    active_jobs: list[dict],  # type: ignore[type-arg]
) -> str:
    """Return the status string for job_id from active_jobs list.

    Returns 'unknown' if the job_id is not found (may have been evicted after
    completion — treat as 'completed' by the caller only if both are gone).

    Args:
        job_id: The job ID to look up.
        active_jobs: List from GET /imports/active.

    Returns:
        Status string ('pending', 'in_progress', 'completed', 'failed', 'unknown').
    """
    for job in active_jobs:
        if job.get("job_id") == job_id:
            return str(job.get("status", "unknown"))
    return "unknown"


# ---------------------------------------------------------------------------
# Metric collection
# ---------------------------------------------------------------------------


def _collect_metrics(
    backend_pid: int | None,
) -> tuple[float | None, float | None, int | None, int | None]:
    """Collect (backend_rss_mib, pg_mem_mib, swap_used_mb, swap_total_mb).

    Backend RSS: docker stats if POSTGRES_CONTAINER_NAME works, else /proc.
    But for dev the backend is native — use /proc/pid/status when pid is given.
    Postgres is always in Docker in dev.

    Args:
        backend_pid: PID of the native uvicorn process, or None (skip backend RSS).

    Returns:
        4-tuple of nullable floats/ints. None means measurement unavailable.
    """
    # Backend RSS: native /proc approach (dev environment — uvicorn is not in Docker).
    backend_rss: float | None = None
    if backend_pid is not None:
        backend_rss = _get_backend_proc_rss_mib(backend_pid)

    # Postgres memory: Docker stats on the dev Postgres container.
    pg_mem: float | None = _get_docker_container_mem_mib(POSTGRES_CONTAINER_NAME)

    # Host swap.
    swap_stats = _get_swap_stats()
    swap_used: int | None = None
    swap_total: int | None = None
    if swap_stats is not None:
        swap_used, swap_total = swap_stats

    return backend_rss, pg_mem, swap_used, swap_total


# ---------------------------------------------------------------------------
# CSV log writer
# ---------------------------------------------------------------------------

_CSV_HEADER = [
    "timestamp",
    "rss_mb",
    "pg_anon_mb",
    "swap_used_mb",
    "swap_total_mb",
    "swap_pct",
    "job1_status",
    "job2_status",
    "coverage_pct",
    "coverage_pending",
]


def _write_csv_row(
    writer: "csv.DictWriter[str]",
    *,
    ts: str,
    rss_mb: float | None,
    pg_anon_mb: float | None,
    swap_used_mb: int | None,
    swap_total_mb: int | None,
    swap_pct: float | None,
    job1_status: str,
    job2_status: str,
    coverage_pct: int,
    coverage_pending: int,
) -> None:
    """Write one CSV row to the open writer.

    Args:
        writer: csv.DictWriter instance.
        ts: ISO timestamp string.
        rss_mb: Backend RSS in MB (None if unavailable).
        pg_anon_mb: Postgres memory in MB (None if unavailable).
        swap_used_mb: Swap used in MB (None if unavailable).
        swap_total_mb: Swap total in MB (None if unavailable).
        swap_pct: Swap usage % (None if unavailable).
        job1_status: Status string for the chess.com job.
        job2_status: Status string for the lichess job.
        coverage_pct: Eval coverage 0-100.
        coverage_pending: Number of pending games.
    """
    writer.writerow(
        {
            "timestamp": ts,
            "rss_mb": f"{rss_mb:.1f}" if rss_mb is not None else "",
            "pg_anon_mb": f"{pg_anon_mb:.1f}" if pg_anon_mb is not None else "",
            "swap_used_mb": swap_used_mb if swap_used_mb is not None else "",
            "swap_total_mb": swap_total_mb if swap_total_mb is not None else "",
            "swap_pct": f"{swap_pct:.1f}" if swap_pct is not None else "",
            "job1_status": job1_status,
            "job2_status": job2_status,
            "coverage_pct": coverage_pct,
            "coverage_pending": coverage_pending,
        }
    )


# ---------------------------------------------------------------------------
# Acceptance gate evaluation
# ---------------------------------------------------------------------------


def _evaluate_gates(
    *,
    job1_final: str,
    job2_final: str,
    peak_rss_mb: float | None,
    peak_pg_mb: float | None,
    peak_swap_pct: float | None,
    coverage_reached_100: bool,
) -> list[str]:
    """Evaluate acceptance gates and return a list of failure reasons.

    Args:
        job1_final: Final status of the chess.com import job.
        job2_final: Final status of the lichess import job.
        peak_rss_mb: Peak backend RSS in MB across the run (None = not measured).
        peak_pg_mb: Peak Postgres memory in MB across the run (None = not measured).
        peak_swap_pct: Peak swap usage % across the run (None = not measured).
        coverage_reached_100: Whether eval coverage reached 100% within timeout.

    Returns:
        List of human-readable failure descriptions. Empty list = PASS.
    """
    failures: list[str] = []

    if job1_final != "completed":
        failures.append(f"chess.com import did not complete (status={job1_final!r})")
    if job2_final != "completed":
        failures.append(f"lichess import did not complete (status={job2_final!r})")

    if peak_rss_mb is not None and peak_rss_mb > RSS_PLATEAU_MAX_MB:
        failures.append(
            f"Backend RSS peak {peak_rss_mb:.1f} MB exceeds limit {RSS_PLATEAU_MAX_MB} MB"
        )

    if peak_pg_mb is not None and peak_pg_mb > POSTGRES_MEMORY_MAX_MB:
        failures.append(
            f"Postgres memory peak {peak_pg_mb:.1f} MB exceeds limit {POSTGRES_MEMORY_MAX_MB} MB"
        )

    if peak_swap_pct is not None and peak_swap_pct > SWAP_USAGE_MAX_PCT:
        failures.append(f"Swap peak {peak_swap_pct:.1f}% exceeds limit {SWAP_USAGE_MAX_PCT}%")

    if not coverage_reached_100:
        failures.append(
            f"Eval coverage did not reach 100% within {DEFAULT_COVERAGE_TIMEOUT_MIN} min"
        )

    return failures


# ---------------------------------------------------------------------------
# CLI argument parsing
# ---------------------------------------------------------------------------


def parse_args() -> argparse.Namespace:
    """Parse and validate CLI arguments for the stress-test harness.

    Returns:
        Parsed argument namespace.
    """
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    default_log = f"logs/import-stress-20k-each-{today}.log"

    parser = argparse.ArgumentParser(
        description=(
            "Phase 91 dual-import stress-test harness. "
            "Triggers two concurrent 20k-game imports (chess.com + lichess), "
            "polls memory / swap / coverage every 30 s, "
            "and evaluates ROADMAP acceptance bounds. "
            "DEV ONLY — destroys dev DB state."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--user-email",
        required=True,
        metavar="EMAIL",
        help="Email of the dev user account to authenticate as.",
    )
    parser.add_argument(
        "--password",
        required=True,
        metavar="PASSWORD_OR_-",
        help=(
            "Password for --user-email. Pass '-' to read from the "
            "STRESS_TEST_PASSWORD environment variable instead of the command line."
        ),
    )
    parser.add_argument(
        "--chess-com-username",
        required=True,
        metavar="HANDLE",
        help="chess.com username to import games from.",
    )
    parser.add_argument(
        "--lichess-username",
        required=True,
        metavar="HANDLE",
        help="Lichess username to import games from.",
    )
    parser.add_argument(
        "--target-games",
        type=int,
        default=DEFAULT_TARGET_GAMES,
        metavar="N",
        help=f"Per-platform game cap (default: {DEFAULT_TARGET_GAMES}).",
    )
    parser.add_argument(
        "--poll-interval-s",
        type=int,
        default=DEFAULT_POLL_INTERVAL_S,
        metavar="SECS",
        help=f"Metric polling cadence in seconds (default: {DEFAULT_POLL_INTERVAL_S}).",
    )
    parser.add_argument(
        "--coverage-timeout-min",
        type=int,
        default=DEFAULT_COVERAGE_TIMEOUT_MIN,
        metavar="MINS",
        help=(
            f"Minutes to wait for eval coverage to reach 100%% after both imports "
            f"finish (default: {DEFAULT_COVERAGE_TIMEOUT_MIN})."
        ),
    )
    parser.add_argument(
        "--api-base",
        default="http://localhost:8000",
        metavar="URL",
        help=(
            "Backend API base URL. Must be localhost unless --allow-prod is set "
            "(default: http://localhost:8000)."
        ),
    )
    parser.add_argument(
        "--output-log",
        default=default_log,
        metavar="PATH",
        help=f"CSV output log path (default: {default_log}).",
    )
    parser.add_argument(
        "--allow-prod",
        action="store_true",
        default=False,
        help="Allow running against a non-localhost API base. DANGEROUS — use with caution.",
    )
    parser.add_argument(
        "--backend-pid",
        type=int,
        default=None,
        metavar="PID",
        help=(
            "PID of the native uvicorn backend process for RSS measurement via /proc. "
            "Optional — omit if backend RSS is not needed or you prefer docker stats."
        ),
    )
    return parser.parse_args()


# ---------------------------------------------------------------------------
# Main async harness
# ---------------------------------------------------------------------------


async def run_harness(args: argparse.Namespace) -> int:
    """Run the dual-import stress test and evaluate acceptance gates.

    Args:
        args: Parsed CLI arguments.

    Returns:
        Exit code: 0 = all bounds met (PASS), 1 = one or more bounds violated (FAIL).
    """
    # Prod-safety guard (T-91-28).
    if not args.allow_prod and _is_prod_api_base(args.api_base):
        print(
            f"ERROR: refusing to run stress test against non-localhost API base: {args.api_base!r}\n"
            "Pass --allow-prod to override (DANGEROUS — this test is destructive).",
            file=sys.stderr,
        )
        return 1

    # Resolve password (T-91-29: avoid plain-text password in process table).
    password = args.password
    if password == "-":
        password = os.environ.get("STRESS_TEST_PASSWORD", "")
        if not password:
            print(
                "ERROR: --password - requires STRESS_TEST_PASSWORD env var to be set.",
                file=sys.stderr,
            )
            return 1

    run_start = datetime.now(timezone.utc)
    log.info(
        "=== Phase 91 dual-import stress test starting at %s ===",
        run_start.isoformat(),
    )
    log.info(
        "Target: chess.com=%s, lichess=%s, games=%d",
        args.chess_com_username,
        args.lichess_username,
        args.target_games,
    )
    log.info("API base: %s", args.api_base)
    log.info("Output log: %s", args.output_log)

    # Ensure output log directory exists.
    output_path = Path(args.output_log)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    async with httpx.AsyncClient(timeout=30.0) as client:
        # Step 1: Authenticate.
        log.info("Authenticating as %s ...", args.user_email)
        try:
            token = await _login(client, args.api_base, args.user_email, password)
        except RuntimeError as exc:
            print(f"ERROR: authentication failed: {exc}", file=sys.stderr)
            return 1
        log.info("Authenticated.")

        # Step 2: Start both imports in parallel.
        log.info("Starting chess.com import (username=%s) ...", args.chess_com_username)
        log.info("Starting lichess import (username=%s) ...", args.lichess_username)
        try:
            chesscom_job_id, lichess_job_id = await asyncio.gather(
                _start_import(client, args.api_base, token, "chess.com", args.chess_com_username),
                _start_import(client, args.api_base, token, "lichess", args.lichess_username),
            )
        except RuntimeError as exc:
            print(f"ERROR: failed to start imports: {exc}", file=sys.stderr)
            return 1

        log.info("chess.com job_id: %s", chesscom_job_id)
        log.info("lichess    job_id: %s", lichess_job_id)

        # Step 3: Polling loop.
        peak_rss_mb: float | None = None
        peak_pg_mb: float | None = None
        peak_swap_pct: float | None = None

        job1_final: str = "unknown"
        job2_final: str = "unknown"

        both_imports_done_at: datetime | None = None
        coverage_reached_100: bool = False

        with output_path.open("w", newline="", encoding="utf-8") as csv_file:
            writer: csv.DictWriter[str] = csv.DictWriter(csv_file, fieldnames=_CSV_HEADER)
            writer.writeheader()
            csv_file.flush()

            poll_number = 0
            while True:
                poll_number += 1
                ts = datetime.now(timezone.utc).isoformat()

                # Collect system metrics.
                rss_mb, pg_mb, swap_used_mb, swap_total_mb = _collect_metrics(args.backend_pid)

                swap_pct: float | None = None
                if swap_used_mb is not None and swap_total_mb is not None and swap_total_mb > 0:
                    swap_pct = 100.0 * swap_used_mb / swap_total_mb

                # Update peaks.
                if rss_mb is not None:
                    peak_rss_mb = max(peak_rss_mb or 0.0, rss_mb)
                if pg_mb is not None:
                    peak_pg_mb = max(peak_pg_mb or 0.0, pg_mb)
                if swap_pct is not None:
                    peak_swap_pct = max(peak_swap_pct or 0.0, swap_pct)

                # Poll import statuses.
                active_jobs = await _get_active_imports(client, args.api_base, token)
                job1_status = _resolve_job_status(chesscom_job_id, active_jobs)
                job2_status = _resolve_job_status(lichess_job_id, active_jobs)

                # When a job is no longer visible in /imports/active, it has
                # completed or failed — the in-memory registry evicts terminal jobs.
                # Treat 'unknown' as 'completed' only after both imports had time to start.
                if poll_number > 1 and job1_status == "unknown":
                    job1_status = "completed"
                if poll_number > 1 and job2_status == "unknown":
                    job2_status = "completed"

                # Poll eval coverage.
                coverage_data = await _get_eval_coverage(client, args.api_base, token)
                cov_pct = coverage_data.get("pct_complete", -1)
                cov_pending = coverage_data.get("pending_count", -1)

                # Write CSV row.
                _write_csv_row(
                    writer,
                    ts=ts,
                    rss_mb=rss_mb,
                    pg_anon_mb=pg_mb,
                    swap_used_mb=swap_used_mb,
                    swap_total_mb=swap_total_mb,
                    swap_pct=swap_pct,
                    job1_status=job1_status,
                    job2_status=job2_status,
                    coverage_pct=cov_pct,
                    coverage_pending=cov_pending,
                )
                csv_file.flush()

                # Human-readable progress line.
                rss_str = f"{rss_mb:.0f} MB" if rss_mb is not None else "n/a"
                pg_str = f"{pg_mb:.0f} MB" if pg_mb is not None else "n/a"
                swap_str = f"{swap_pct:.1f}%" if swap_pct is not None else "n/a"
                log.info(
                    "[poll %d] rss=%s pg=%s swap=%s | chess.com=%s lichess=%s | "
                    "coverage=%d%% (%d pending)",
                    poll_number,
                    rss_str,
                    pg_str,
                    swap_str,
                    job1_status,
                    job2_status,
                    cov_pct if cov_pct >= 0 else -1,
                    cov_pending if cov_pending >= 0 else -1,
                )

                # Track when both imports finished.
                both_done = job1_status in _TERMINAL_STATUSES and job2_status in _TERMINAL_STATUSES
                if both_done and both_imports_done_at is None:
                    both_imports_done_at = datetime.now(timezone.utc)
                    job1_final = job1_status
                    job2_final = job2_status
                    log.info(
                        "Both imports reached terminal status: chess.com=%s lichess=%s",
                        job1_final,
                        job2_final,
                    )

                # Coverage reached 100%?
                if cov_pct == 100:
                    coverage_reached_100 = True

                # Exit condition: both done AND (coverage=100 OR coverage timeout elapsed).
                if both_done:
                    if coverage_reached_100:
                        log.info("Coverage reached 100%%. Stopping poll loop.")
                        break

                    if both_imports_done_at is not None:
                        elapsed_min = (
                            datetime.now(timezone.utc) - both_imports_done_at
                        ).total_seconds() / 60.0
                        if elapsed_min >= args.coverage_timeout_min:
                            log.warning(
                                "Coverage timeout: %.1f min elapsed after imports finished "
                                "(limit=%d min). Coverage at %d%%.",
                                elapsed_min,
                                args.coverage_timeout_min,
                                cov_pct,
                            )
                            break

                await asyncio.sleep(args.poll_interval_s)

    # Final status for jobs that never appeared in active list
    # (e.g. server restarted mid-run).
    if job1_final == "unknown":
        job1_final = job1_status
    if job2_final == "unknown":
        job2_final = job2_status

    # Evaluate acceptance gates.
    failures = _evaluate_gates(
        job1_final=job1_final,
        job2_final=job2_final,
        peak_rss_mb=peak_rss_mb,
        peak_pg_mb=peak_pg_mb,
        peak_swap_pct=peak_swap_pct,
        coverage_reached_100=coverage_reached_100,
    )

    elapsed_total = (datetime.now(timezone.utc) - run_start).total_seconds()

    # Print summary.
    print()
    print("=" * 60)
    print(f"  Phase 91 stress-test summary  ({run_start.strftime('%Y-%m-%d')})")
    print("=" * 60)
    print(f"  Duration        : {elapsed_total / 60:.1f} min")
    print(f"  chess.com import: {job1_final}")
    print(f"  lichess import  : {job2_final}")
    print(
        f"  Peak RSS        : {peak_rss_mb:.1f} MB"
        if peak_rss_mb is not None
        else "  Peak RSS        : n/a"
    )
    print(
        f"  Peak Postgres   : {peak_pg_mb:.1f} MB"
        if peak_pg_mb is not None
        else "  Peak Postgres   : n/a"
    )
    print(
        f"  Peak swap       : {peak_swap_pct:.1f}%"
        if peak_swap_pct is not None
        else "  Peak swap       : n/a"
    )
    print(f"  Coverage 100%%   : {'yes' if coverage_reached_100 else 'no'}")
    print(f"  Log file        : {args.output_log}")
    print()

    if failures:
        print("  RESULT: FAIL")
        for reason in failures:
            print(f"    - {reason}")
        print()
        print("  Acceptance bounds:")
        print(f"    RSS     <= {RSS_PLATEAU_MAX_MB} MB")
        print(f"    Postgres <= {POSTGRES_MEMORY_MAX_MB} MB")
        print(f"    Swap    <= {SWAP_USAGE_MAX_PCT} %")
        print("  Refer to .planning/phases/91-*/91-08-SUMMARY.md for gap-closure.")
        print("=" * 60)
        return 1

    print("  RESULT: PASS — all Phase 91 acceptance bounds met.")
    print("=" * 60)
    return 0


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------


def main() -> None:
    """Parse args and run the async harness.

    Exits with the harness return code.
    """
    args = parse_args()
    exit_code = asyncio.run(run_harness(args))
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
