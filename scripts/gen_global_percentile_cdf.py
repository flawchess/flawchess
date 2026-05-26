"""Regenerate the cohort empirical-CDF artifact from the benchmark DB.

Phase 94.4 — cohort sliding-window methodology
----------------------------------------------

The Phase 94.3 flat ``GLOBAL_PERCENTILE_CDF`` (16-key, pooled across all
anchors) retires. Plan 04 replaces it with ``COHORT_PERCENTILE_CDF`` — an
8-metric × ~33-anchor × 4-TC nested registry where each cell is the 99-
breakpoint CDF over the K=200 nearest-anchor users in that (metric, anchor,
TC) cohort (CONTEXT D-09 / D-11 / D-13).

In-Python ranking strategy (RESEARCH Pitfall 8)
-----------------------------------------------

A naive per-anchor SQL approach would issue ``8 metrics × 33 anchors × 4 TCs
= 1,056 queries`` against the benchmark DB. The chosen strategy collapses
this to ``8 × 4 = 32 queries`` by:

1. Issuing one query per (metric, TC) returning ``(user_id, metric_value,
   n_games, anchor_rating)`` over the joint pool: ``per_user_values
   JOIN per_user_anchor USING (user_id)``.
2. Ranking the result in Python across each of the 33 anchors on the
   50-Elo grid (800..2400). Each anchor's K=200 nearest users by
   ``abs(anchor_rating - anchor)`` form the cohort for that cell.
3. A user_id tiebreaker on the sort is REQUIRED for byte-identical
   deterministic regen: when multiple users share the same anchor
   distance, sort by ``(distance, user_id)`` so the K=200 cohort is
   stable across runs.

Strict-default suppression policy (CONTEXT D-11)
------------------------------------------------

A cell is SUPPRESSED (no entry in COHORT_PERCENTILE_CDF) when:
- ``len(ranked) < COHORT_K_USERS_PER_ANCHOR`` (insufficient K), OR
- ``abs(ranked[-1].anchor_rating - anchor) > COHORT_MAX_WINDOW_ELO``
  (window too wide — the K-th nearest user is more than ±150 Elo away).

Strict defaults are intentional. The regen report's TOP-LINE suppression
table is the operator's signal for whether to relax the constants before
Plan 06 backfill.

What this script produces
-------------------------
1. Overwrites the ``COHORT_PERCENTILE_CDF = {...}`` literal in
   ``app/services/global_percentile_cdf.py`` between the
   ``BEGIN GENERATED REGISTRY`` / ``END GENERATED REGISTRY`` sentinels.
2. Writes ``reports/cohort-percentile-cdf-latest.md`` with the
   per-(metric, anchor, TC) suppression-flag table as the TOP-LINE section.

Operator workflow::

    bin/benchmark_db.sh start
    uv run python scripts/gen_global_percentile_cdf.py --target benchmark \\
        --snapshot-date 2026-05-26

CLI:

* ``--target benchmark`` (required) — only the benchmark Docker DB on port
  5433 is supported. ``_assert_benchmark_db`` refuses to run unless the
  resolved URL contains both ``flawchess_benchmark`` and ``:5433`` (94.1
  Plan 09 safety guard).
* ``--snapshot-date YYYY-MM-DD`` (optional) — anchors the 36-month recency
  window. Defaults to today (UTC).
* ``--regen-report-path PATH`` (optional) — defaults to
  ``reports/cohort-percentile-cdf-latest.md``.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import re
import sys
import time
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Final
from urllib.parse import urlparse, urlunparse

import sentry_sdk
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Bootstrap project root so ``app.*`` imports resolve when running as a script.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.config import settings  # noqa: E402
from app.services.canonical_slice_sql import (  # noqa: E402
    TimeControlBucket,
    per_user_cte_achievable_tc,
    per_user_cte_clock_gap,
    per_user_cte_median_anchor,
    per_user_cte_net_flag_rate,
    per_user_cte_score_gap_tc,
    per_user_cte_section2_tc,
    per_user_cte_time_pressure_score_gap,
    selected_users_cte,
)
from app.services.global_percentile_cdf import (  # noqa: E402
    BENCHMARK_DB_SNAPSHOT_MONTH,
    CdfMetricId,
    CdfTable,
)

# ---------------------------------------------------------------------------
# Module-level constants (no magic numbers — CLAUDE.md; CONTEXT D-11).
# ---------------------------------------------------------------------------

# Sliding-window cohort policy. The operator may relax these after reviewing
# the regen report's suppression table (HUMAN-VERIFY checkpoint at end of
# Plan 04). Strict defaults ship unless the operator explicitly relaxes.

# CONTEXT D-11 — cohort size per anchor. Higher = tighter CI, more suppression.
COHORT_K_USERS_PER_ANCHOR: Final[int] = 200

# CONTEXT D-11 — maximum Elo distance from anchor to k-th user. Wider = more
# coverage, looser peer-relativity.
COHORT_MAX_WINDOW_ELO: Final[int] = 150

# CONTEXT D-11 — anchor grid step. Must match COHORT_ANCHOR_STEP_ELO in
# ``app/services/global_percentile_cdf.py`` (interpolate_cohort_percentile
# rounds inputs to this grid).
COHORT_ANCHOR_STEP_ELO: Final[int] = 50

# CONTEXT D-11 — anchor sweep range.
COHORT_ANCHOR_MIN_ELO: Final[int] = 800
COHORT_ANCHOR_MAX_ELO: Final[int] = 2400

# Time-control sweep order — canonical bullet → blitz → rapid → classical.
ALL_TIME_CONTROLS: Final[tuple[TimeControlBucket, ...]] = (
    "bullet",
    "blitz",
    "rapid",
    "classical",
)

# 8-value CdfMetricId tuple. Order matters: registry-literal emission walks
# this tuple so two regen runs against the same DB produce byte-identical
# Python source. Order mirrors the Literal in
# ``app/services/global_percentile_cdf.py`` (CONTEXT D-13).
IN_SCOPE_METRICS: Final[tuple[CdfMetricId, ...]] = (
    "score_gap",
    "achievable_score_gap",
    "section2_score_gap_conv",
    "section2_score_gap_parity",
    "recovery_score_gap",
    "time_pressure_score_gap",
    "clock_gap",
    "net_flag_rate",
)

# Output paths.
OUTPUT_MODULE_PATH: Final[Path] = Path("app/services/global_percentile_cdf.py")
DEFAULT_REPORT_PATH: Final[Path] = Path("reports/cohort-percentile-cdf-latest.md")
ARCHIVE_DIR: Final[Path] = Path("reports/archive")

# Safety-guard tokens (mirrors ``scripts/backfill_eval.py --db benchmark``).
BENCHMARK_DB_NAME_TOKEN: Final[str] = "flawchess_benchmark"
BENCHMARK_DB_PORT_TOKEN: Final[str] = ":5433"

# Sentinel comments wrapping the COHORT_PERCENTILE_CDF literal. The script
# rewrites only the block between these markers.
REGISTRY_BEGIN_MARKER: Final[str] = "# --- BEGIN GENERATED REGISTRY ---"
REGISTRY_END_MARKER: Final[str] = "# --- END GENERATED REGISTRY ---"

# Floats are rendered to 4 decimal places. This is the byte-identical regen
# precision: all breakpoint floats are emitted as `f"{v:.4f}"` so two runs
# against the same DB snapshot produce identical Python source.
FLOAT_PRECISION: Final[int] = 4

# Port map for --target choices.
_TARGET_PORT: Final[dict[str, int]] = {"benchmark": 5433}
_LOCAL_HOSTS: Final[frozenset[str]] = frozenset({"localhost", "127.0.0.1", "::1"})


# ---------------------------------------------------------------------------
# Logging.
# ---------------------------------------------------------------------------


def _log(msg: str = "") -> None:
    """Print ``msg`` prefixed with a UTC second-precision timestamp."""
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] {msg}")


# ---------------------------------------------------------------------------
# DB URL resolution + safety guard (94.1 Plan 09 pattern, preserved).
# ---------------------------------------------------------------------------


def _db_url(target: str) -> str:
    """Build the asyncpg URL for the chosen ``--target``.

    Mirrors ``scripts/backfill_eval.py:_db_url`` and the prior Phase 94.3
    ``--db benchmark`` form. Phase 94.4 keeps ``benchmark`` as the only
    supported target.
    """
    if target not in _TARGET_PORT:
        raise ValueError(f"Unknown --target: {target!r}. Must be one of: {list(_TARGET_PORT)}")

    override_var = f"BACKFILL_{target.upper()}_DB_URL"
    override = os.environ.get(override_var)
    if override:
        host = urlparse(override).hostname
        if host not in _LOCAL_HOSTS:
            raise ValueError(
                f"{override_var} host is {host!r}, but this script always reaches "
                f"the benchmark DB via localhost (Docker on port 5433). Update the "
                f"override to use localhost:{_TARGET_PORT[target]} (keeping the credentials)."
            )
        return override

    port = _TARGET_PORT[target]
    parsed = urlparse(settings.DATABASE_URL)
    new_netloc = f"{parsed.username}:{parsed.password}@localhost:{port}"
    return urlunparse(parsed._replace(netloc=new_netloc))


def _mask_password(url: str) -> str:
    """Replace the password in ``url`` with ``***`` for safe logging."""
    parsed = urlparse(url)
    if parsed.password is None:
        return url
    safe_netloc = f"{parsed.username}:***@{parsed.hostname}:{parsed.port}"
    return urlunparse(parsed._replace(netloc=safe_netloc))


def _assert_benchmark_db(url: str) -> None:
    """Refuse to run unless ``url`` points at the benchmark DB (T-94.4-04-01)."""
    if BENCHMARK_DB_NAME_TOKEN not in url or BENCHMARK_DB_PORT_TOKEN not in url:
        raise SystemExit(
            f"Refusing to run: resolved DB URL does not contain both "
            f"{BENCHMARK_DB_NAME_TOKEN!r} and {BENCHMARK_DB_PORT_TOKEN!r}. "
            f"Got: {_mask_password(url)}. "
            f"This script only operates against the benchmark Docker DB on port 5433."
        )


# ---------------------------------------------------------------------------
# SQL composition — per-(metric, TC) per_user_values × per_user_anchor join.
# ---------------------------------------------------------------------------


def _per_user_cte_for_metric_and_tc(
    metric: CdfMetricId,
    tc: TimeControlBucket,
    *,
    snapshot_date: date,
) -> str:
    """Dispatch to the correct per-TC ``per_user_values`` CTE builder for one metric.

    Phase 94.4 8-value CdfMetricId dispatcher. The builders are imported
    from ``app.services.canonical_slice_sql`` (Plans 02 + 03):

    - ``score_gap``                  → ``per_user_cte_score_gap_tc``
    - ``achievable_score_gap``       → ``per_user_cte_achievable_tc``
    - ``section2_score_gap_conv``    → ``per_user_cte_section2_tc(bucket_label='conversion')``
    - ``section2_score_gap_parity``  → ``per_user_cte_section2_tc(bucket_label='parity')``
    - ``recovery_score_gap``         → ``per_user_cte_section2_tc(bucket_label='recovery')``
    - ``time_pressure_score_gap``    → ``per_user_cte_time_pressure_score_gap(tc)``
    - ``clock_gap``                  → ``per_user_cte_clock_gap(tc)``
    - ``net_flag_rate``              → ``per_user_cte_net_flag_rate(tc)``

    All return a CTE block ending in ``per_user_values(user_id, metric_value, n_games)``
    restricted to TC ``tc``. The CTE is joined against
    ``per_user_cte_median_anchor(tc, ...)`` in the outer query.
    """
    if metric == "score_gap":
        return per_user_cte_score_gap_tc(tc, source="benchmark", snapshot_date=snapshot_date)
    if metric == "achievable_score_gap":
        return per_user_cte_achievable_tc(tc, source="benchmark", snapshot_date=snapshot_date)
    if metric == "section2_score_gap_conv":
        return per_user_cte_section2_tc(
            tc, source="benchmark", snapshot_date=snapshot_date, bucket_label="conversion"
        )
    if metric == "section2_score_gap_parity":
        return per_user_cte_section2_tc(
            tc, source="benchmark", snapshot_date=snapshot_date, bucket_label="parity"
        )
    if metric == "recovery_score_gap":
        return per_user_cte_section2_tc(
            tc, source="benchmark", snapshot_date=snapshot_date, bucket_label="recovery"
        )
    if metric == "time_pressure_score_gap":
        return per_user_cte_time_pressure_score_gap(
            tc, source="benchmark", snapshot_date=snapshot_date
        )
    if metric == "clock_gap":
        return per_user_cte_clock_gap(tc, source="benchmark", snapshot_date=snapshot_date)
    if metric == "net_flag_rate":
        return per_user_cte_net_flag_rate(tc, source="benchmark", snapshot_date=snapshot_date)
    raise ValueError(f"Unknown metric: {metric!r}")


def _build_per_user_with_anchor_query(
    metric: CdfMetricId,
    tc: TimeControlBucket,
    *,
    snapshot_date: date,
) -> str:
    """Build the per-(metric, TC) SQL query joining per_user_values × per_user_anchor.

    Returns rows of ``(user_id, metric_value, n_games, anchor_rating)`` over
    the cohort selected by ``selected_users_cte(source="benchmark")``. Plan 04
    of Phase 94.4 ranks these rows in Python (RESEARCH Pitfall 8) — collapses
    1,056 per-anchor queries to 32 per-(metric, TC) queries.

    The two CTE blocks (``per_user_values`` and ``per_user_anchor``) emit
    distinct top-level CTE names that don't collide; the JOIN ``USING
    (user_id)`` aligns each user's metric value with their median anchor.
    """
    per_user_block = _per_user_cte_for_metric_and_tc(metric, tc, snapshot_date=snapshot_date)
    anchor_block = per_user_cte_median_anchor(tc, source="benchmark", snapshot_date=snapshot_date)
    # Both builders share the ``recent_capped`` CTE name via their common
    # ``_recent_capped_per_tc_cte`` dependency. Joining the two builders inside
    # one WITH chain triggers ``DuplicateAliasError: WITH query name
    # "recent_capped" specified more than once``. Rename the anchor block's
    # local CTEs to a unique prefix — they're internal to that block and only
    # the final ``per_user_anchor`` name is referenced by the outer SELECT.
    anchor_block_renamed = anchor_block.replace(
        "recent_capped AS (", "recent_capped_anchor AS ("
    ).replace("recent_capped_no_daily", "recent_capped_anchor_no_daily").replace(
        "FROM recent_capped rc", "FROM recent_capped_anchor rc"
    )
    return f"""
WITH {selected_users_cte(source="benchmark")},
{per_user_block},
{anchor_block_renamed}
SELECT
  puv.user_id,
  puv.metric_value,
  puv.n_games,
  pua.anchor_rating
FROM per_user_values puv
JOIN per_user_anchor pua USING (user_id)
""".strip()


# ---------------------------------------------------------------------------
# Per-cell cohort CDF computation (in-Python ranking).
# ---------------------------------------------------------------------------


# Row from the benchmark-DB JOIN. ``user_id`` is required for the deterministic
# tiebreaker on the sort (RESEARCH Pitfall 1 + W3 fix). Use a NamedTuple so
# the sort key can write ``r.anchor_rating`` / ``r.user_id`` (matches the
# RESEARCH Pattern 1 reference style and the plan-acceptance literal grep).
from typing import NamedTuple  # noqa: E402 — local to keep the row type near its sort


class _PerUserRow(NamedTuple):
    user_id: int
    metric_value: float
    n_games: int
    anchor_rating: int


# Per-cell suppression log entry. Captures both suppressed and non-suppressed
# anchors so the regen report can render the full 1,056-row table.
_CellLogEntry = dict[str, object]


def _percentile_linear(sorted_values: list[float], p: int) -> float:
    """Linear-interpolation percentile, matching numpy's default 'linear' method.

    ``sorted_values`` must already be sorted ascending. ``p`` is an integer
    percentile in [0, 100]. Returns ``float(sorted_values[i] + frac * (next-cur))``
    where ``i = (len(values) - 1) * p / 100`` (linear interpolation between
    the two surrounding ranks, matching ``numpy.percentile(..., method='linear')``).

    Pure-Python implementation so the script does not depend on numpy
    (which is not a project dependency — see pyproject.toml).

    Determinism: byte-identical results across runs given identical input.
    """
    n = len(sorted_values)
    if n == 0:
        raise ValueError("_percentile_linear called with empty list")
    if n == 1:
        return float(sorted_values[0])
    idx = (n - 1) * p / 100.0
    lo = int(idx)
    hi = min(lo + 1, n - 1)
    frac = idx - lo
    return float(sorted_values[lo] + frac * (sorted_values[hi] - sorted_values[lo]))


async def _query_per_user_with_anchor(
    session: AsyncSession,
    metric: CdfMetricId,
    tc: TimeControlBucket,
    snapshot_date: date,
) -> list[_PerUserRow]:
    """Fetch all (user_id, metric_value, n_games, anchor_rating) rows for one (metric, TC)."""
    sql = _build_per_user_with_anchor_query(metric, tc, snapshot_date=snapshot_date)
    result = await session.execute(text(sql))
    out: list[_PerUserRow] = []
    for r in result.all():
        out.append(
            _PerUserRow(
                user_id=int(r.user_id),
                metric_value=float(r.metric_value),
                n_games=int(r.n_games),
                anchor_rating=int(r.anchor_rating),
            )
        )
    return out


def _build_cohort_cdf_for(
    rows: list[_PerUserRow],
    metric: CdfMetricId,
    tc: TimeControlBucket,
) -> tuple[dict[int, CdfTable], list[_CellLogEntry]]:
    """In-Python rank ``rows`` across the 33 anchors; return (per-anchor CDF map, log).

    For each anchor on the 50-Elo grid 800..2400:

    1. Sort all rows by ``(abs(anchor_rating - anchor), user_id)`` — the
       ``user_id`` tiebreaker is REQUIRED for byte-identical regen
       determinism when multiple users share the same anchor distance.
    2. Take the first K=200 as the cohort for this cell.
    3. If ``len(ranked) < K`` → suppress (insufficient_k).
    4. If ``abs(ranked[-1].anchor_rating - anchor) > COHORT_MAX_WINDOW_ELO``
       → suppress (window_too_wide).
    5. Otherwise compute 99-breakpoint CDF via ``numpy.percentile`` and
       record under ``result[anchor]``.

    Returns a parallel suppression log capturing per-anchor n_users, k-th
    distance, suppressed flag, and suppression reason. The log feeds the
    Task 4 regen report.
    """
    result: dict[int, CdfTable] = {}
    log: list[_CellLogEntry] = []
    for anchor in range(COHORT_ANCHOR_MIN_ELO, COHORT_ANCHOR_MAX_ELO + 1, COHORT_ANCHOR_STEP_ELO):
        # The (|distance|, user_id) tiebreaker is REQUIRED for byte-identical
        # regen determinism — when multiple users share the same anchor
        # distance, sort by user_id so the K=200 cohort is stable across runs.
        ranked = sorted(rows, key=lambda r: (abs(r.anchor_rating - anchor), r.user_id))[
            :COHORT_K_USERS_PER_ANCHOR
        ]
        n_users = len(ranked)
        kth_dist: int = abs(ranked[-1].anchor_rating - anchor) if ranked else 0
        suppressed = False
        suppression_reason: str | None = None
        if n_users < COHORT_K_USERS_PER_ANCHOR:
            suppressed = True
            suppression_reason = "insufficient_k"
        elif kth_dist > COHORT_MAX_WINDOW_ELO:
            suppressed = True
            suppression_reason = "window_too_wide"
        if not suppressed:
            values = sorted(r.metric_value for r in ranked)
            breakpoints = tuple(_percentile_linear(values, p) for p in range(1, 100))
            result[anchor] = CdfTable(
                breakpoints=breakpoints,
                n_users=n_users,
                snapshot_month=BENCHMARK_DB_SNAPSHOT_MONTH,
            )
        log.append(
            {
                "metric": metric,
                "anchor": anchor,
                "tc": tc,
                "n_users": n_users,
                "kth_dist_elo": kth_dist,
                "suppressed": suppressed,
                "suppression_reason": suppression_reason,
            }
        )
    return result, log


# ---------------------------------------------------------------------------
# Python source emission — overwrite COHORT_PERCENTILE_CDF block.
# ---------------------------------------------------------------------------


def _emit_breakpoints_literal(breakpoints: tuple[float, ...]) -> str:
    """Render breakpoints as a parenthesized tuple at fixed precision."""
    parts = [f"{v:.{FLOAT_PRECISION}f}" for v in breakpoints]
    # 10 values per line keeps the diff readable; 99 / 10 = 10 lines + 9 on the last.
    chunks = [", ".join(parts[i : i + 10]) for i in range(0, len(parts), 10)]
    body = ",\n                    ".join(chunks)
    return f"(\n                    {body},\n                )"


def _emit_registry_block(
    cells: dict[CdfMetricId, dict[tuple[int, TimeControlBucket], CdfTable]],
) -> str:
    """Render the BEGIN…END block with one nested entry per (metric, anchor, TC) cell."""
    lines: list[str] = [REGISTRY_BEGIN_MARKER]
    lines.append(
        "COHORT_PERCENTILE_CDF: Mapping["
        "CdfMetricId, Mapping[tuple[int, TimeControlBucket], CdfTable]"
        "] = {"
    )
    for metric in IN_SCOPE_METRICS:
        per_metric = cells.get(metric, {})
        if not per_metric:
            # All cells suppressed for this metric — still emit an empty
            # inner dict so every CdfMetricId is keyed in the registry.
            lines.append(f'    "{metric}": {{}},')
            continue
        lines.append(f'    "{metric}": {{')
        # Sort (anchor ASC, tc in canonical order) so two runs produce byte-
        # identical Python source.
        tc_order = {tc: i for i, tc in enumerate(ALL_TIME_CONTROLS)}
        sorted_keys = sorted(per_metric.keys(), key=lambda k: (k[0], tc_order[k[1]]))
        for anchor, tc in sorted_keys:
            table = per_metric[(anchor, tc)]
            lines.append(f'        ({anchor}, "{tc}"): CdfTable(')
            lines.append(f"            breakpoints={_emit_breakpoints_literal(table.breakpoints)},")
            lines.append(f"            n_users={table.n_users},")
            lines.append(f'            snapshot_month="{table.snapshot_month}",')
            lines.append("        ),")
        lines.append("    },")
    lines.append("}")
    lines.append(REGISTRY_END_MARKER)
    return "\n".join(lines)


def _rewrite_module_source(
    existing_source: str,
    cells: dict[CdfMetricId, dict[tuple[int, TimeControlBucket], CdfTable]],
) -> str:
    """Replace the BEGIN…END registry block in ``existing_source`` with new values."""
    pattern = re.compile(
        re.escape(REGISTRY_BEGIN_MARKER) + r".*?" + re.escape(REGISTRY_END_MARKER),
        flags=re.DOTALL,
    )
    if not pattern.search(existing_source):
        raise SystemExit(
            f"Could not find sentinel markers ({REGISTRY_BEGIN_MARKER!r} / "
            f"{REGISTRY_END_MARKER!r}) in {OUTPUT_MODULE_PATH}. "
            f"Task 1 must commit the markers around the placeholder registry."
        )
    new_block = _emit_registry_block(cells)
    return pattern.sub(new_block, existing_source, count=1)


def _write_module(
    cells: dict[CdfMetricId, dict[tuple[int, TimeControlBucket], CdfTable]],
) -> None:
    """Rewrite ``app/services/global_percentile_cdf.py`` then run ruff format + check."""
    existing = OUTPUT_MODULE_PATH.read_text()
    new_source = _rewrite_module_source(existing, cells)

    tmp = OUTPUT_MODULE_PATH.with_suffix(".py.tmp")
    tmp.write_text(new_source)

    import subprocess  # local import — this is the only function that shells out

    subprocess.run(["uv", "run", "ruff", "format", str(tmp)], check=True)
    subprocess.run(["uv", "run", "ruff", "check", "--fix", str(tmp)], check=True)

    tmp.replace(OUTPUT_MODULE_PATH)
    _log(f"Wrote {OUTPUT_MODULE_PATH}")


# ---------------------------------------------------------------------------
# Regen report.
# ---------------------------------------------------------------------------


_METRIC_DISPLAY: Final[dict[CdfMetricId, str]] = {
    "score_gap": "Endgame Score Gap",
    "achievable_score_gap": "Achievable Score Gap",
    "section2_score_gap_conv": "Section 2 Conversion ΔES",
    "section2_score_gap_parity": "Section 2 Parity ΔES",
    "recovery_score_gap": "Recovery Score Gap",
    "time_pressure_score_gap": "Time Pressure Score Gap",
    "clock_gap": "Clock Gap",
    "net_flag_rate": "Net Flag Rate",
}


def _render_regen_report(
    log: list[_CellLogEntry],
    snapshot_date: date,
    runtime_seconds: float,
    git_commit: str,
) -> str:
    """Compose the markdown text of the regen report.

    CONTEXT D-11 requires the per-(metric, anchor, TC) suppression-flag
    table as the TOP-LINE section after a brief intro + snapshot metadata.
    """
    snapshot_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    intro = (
        f"# Cohort Percentile CDF — Sliding-Window Methodology (Phase 94.4)\n\n"
        f"**Methodology:** Each cell is the 99-breakpoint empirical CDF over the "
        f"K={COHORT_K_USERS_PER_ANCHOR} nearest-anchor users in that (metric, "
        f"anchor, TC) cohort, ranked in Python after one per-(metric, TC) SQL "
        f"query joining ``per_user_values × per_user_anchor`` "
        f"(RESEARCH Pitfall 8). Anchors sweep "
        f"{COHORT_ANCHOR_MIN_ELO}..{COHORT_ANCHOR_MAX_ELO} Elo on a "
        f"{COHORT_ANCHOR_STEP_ELO}-Elo grid (33 anchors per (metric, TC)). "
        f"A cell is SUPPRESSED when ``len(ranked) < K`` "
        f"(``insufficient_k``) or ``abs(k-th distance) > "
        f"{COHORT_MAX_WINDOW_ELO}`` Elo (``window_too_wide``). "
        f"Strict-default policy per CONTEXT D-11.\n\n"
        f"- **DB**: benchmark (Docker on localhost:5433, "
        f"{BENCHMARK_DB_NAME_TOKEN})\n"
        f"- **Snapshot date (recency anchor)**: {snapshot_date.isoformat()} "
        f"(36-month window: ≥ {snapshot_date.isoformat()} − INTERVAL '36 months')\n"
        f"- **Report generated**: {snapshot_iso}\n"
        f"- **Benchmark DB snapshot month**: {BENCHMARK_DB_SNAPSHOT_MONTH}\n"
        f"- **Git commit (gen script)**: {git_commit}\n"
        f"- **Regen runtime**: {runtime_seconds:.1f}s\n"
        f"- **Generated by**: ``scripts/gen_global_percentile_cdf.py "
        f"--target benchmark --snapshot-date {snapshot_date.isoformat()}``\n\n"
        f"## Policy constants\n\n"
        f"- ``COHORT_K_USERS_PER_ANCHOR = {COHORT_K_USERS_PER_ANCHOR}``\n"
        f"- ``COHORT_MAX_WINDOW_ELO = {COHORT_MAX_WINDOW_ELO}``\n"
        f"- ``COHORT_ANCHOR_STEP_ELO = {COHORT_ANCHOR_STEP_ELO}``\n"
        f"- ``COHORT_ANCHOR_MIN_ELO = {COHORT_ANCHOR_MIN_ELO}``\n"
        f"- ``COHORT_ANCHOR_MAX_ELO = {COHORT_ANCHOR_MAX_ELO}``\n\n"
    )

    # TOP-LINE suppression-flag table.
    table_header = (
        "## Per-(metric, anchor, TC) suppression-flag table (TOP-LINE)\n\n"
        "Per-cell rows for all 8 metrics × 33 anchors × 4 TCs = 1,056 cells. "
        "Sorted by metric ASC, anchor ASC, TC in canonical order (bullet, "
        "blitz, rapid, classical).\n\n"
        "| metric | anchor (Elo) | TC | suppressed | reason | k-th distance (Elo) | n_users |\n"
        "|---|---:|---|---|---|---:|---:|\n"
    )
    tc_order = {tc: i for i, tc in enumerate(ALL_TIME_CONTROLS)}
    sorted_log = sorted(
        log,
        key=lambda e: (
            IN_SCOPE_METRICS.index(e["metric"]),  # type: ignore[arg-type]
            int(e["anchor"]),  # type: ignore[arg-type]
            tc_order[e["tc"]],  # type: ignore[index]
        ),
    )
    rows: list[str] = []
    for entry in sorted_log:
        metric = entry["metric"]
        anchor = entry["anchor"]
        tc = entry["tc"]
        suppressed = bool(entry["suppressed"])
        reason = entry["suppression_reason"] or "—"
        kth = entry["kth_dist_elo"]
        n_users = entry["n_users"]
        rows.append(
            f"| {metric} | {anchor} | {tc} | {'Y' if suppressed else 'N'} | "
            f"{reason} | {kth} | {n_users} |"
        )
    table_body = "\n".join(rows)

    # Per-metric coverage summary.
    coverage_lines: list[str] = ["\n\n## Per-metric coverage\n"]
    for metric in IN_SCOPE_METRICS:
        per_metric_log = [e for e in log if e["metric"] == metric]
        non_suppressed = sum(1 for e in per_metric_log if not e["suppressed"])
        total = len(per_metric_log)
        per_tc_counts: list[str] = []
        for tc in ALL_TIME_CONTROLS:
            tc_log = [e for e in per_metric_log if e["tc"] == tc]
            tc_non = sum(1 for e in tc_log if not e["suppressed"])
            per_tc_counts.append(f"{tc} {tc_non}/{len(tc_log)}")
        coverage_lines.append(
            f"- **{_METRIC_DISPLAY[metric]}** (`{metric}`): "
            f"{non_suppressed}/{total} cells non-suppressed; " + ", ".join(per_tc_counts)
        )

    # Relaxation-guidance paragraph (cites CONTEXT D-11).
    guidance = (
        "\n\n## Relaxation guidance\n\n"
        "If coverage in the table above is too sparse for the shipping goal "
        "(per CONTEXT D-11 strict-default policy), the operator can choose:\n\n"
        "- **Option A — ship strict defaults**: chip suppresses for users in "
        "the affected (metric, anchor, TC) cells; ``interpolate_cohort_percentile`` "
        f"returns ``None`` → frontend renders nothing. Recommended when rapid "
        "mid-range coverage is adequate (RESEARCH Pattern 4 expects this band "
        "to be the comfortable case).\n"
        "- **Option B — relax K**: lower ``COHORT_K_USERS_PER_ANCHOR`` from "
        f"{COHORT_K_USERS_PER_ANCHOR} (e.g. to 150 or 100) and rerun Task 3. "
        "Tradeoff: wider CIs on the chip percentile.\n"
        "- **Option C — widen the window**: raise ``COHORT_MAX_WINDOW_ELO`` "
        f"from {COHORT_MAX_WINDOW_ELO} Elo (e.g. to 200 Elo) and rerun Task 3. "
        "Tradeoff: chip becomes less peer-relative as the window widens.\n\n"
        "All three constants are module-level in ``scripts/gen_global_percentile_cdf.py`` "
        "for one-line tuning. The HUMAN-VERIFY checkpoint at the end of Plan 04 "
        "is where the operator records the chosen option.\n"
    )

    return intro + table_header + table_body + "\n".join(coverage_lines) + guidance


def _archive_prior_report(report_path: Path) -> Path | None:
    """Copy the prior report (if any) into ``reports/archive/`` before overwrite.

    Idempotent: if the dated archive destination already exists, logs a warning
    and returns the existing path without copying. The archive filename embeds
    today's date so successive regenerations across days produce non-colliding
    archive names.
    """
    if not report_path.exists():
        return None
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    today = date.today()
    # Try a tag based on the prior report's H1.
    try:
        head = report_path.read_text().splitlines()[0]
        m = re.search(r"\(Phase (\d+(?:\.\d+)*)\)", head)
        phase_tag = m.group(1) if m else "prior"
    except (OSError, IndexError):
        phase_tag = "prior"
    archive_path = ARCHIVE_DIR / f"{report_path.stem}-{today.isoformat()}-phase-{phase_tag}.md"
    if archive_path.exists():
        _log(f"Archive already exists: {archive_path}; not overwriting.")
        return archive_path
    import shutil

    shutil.copy2(report_path, archive_path)
    _log(f"Archived {report_path} -> {archive_path}")
    return archive_path


# ---------------------------------------------------------------------------
# Driver.
# ---------------------------------------------------------------------------


async def regenerate(
    *,
    target: str,
    snapshot_date: date,
    report_path: Path,
) -> tuple[dict[CdfMetricId, dict[tuple[int, TimeControlBucket], CdfTable]], list[_CellLogEntry]]:
    """Run the 3-level loop and emit the populated registry + regen report.

    Returns ``(cells, suppression_log)`` for testing / inspection. Side effects:
    overwrites ``app/services/global_percentile_cdf.py`` between the sentinel
    markers and writes the regen report to ``report_path``.
    """
    url = _db_url(target)
    _assert_benchmark_db(url)
    _log(f"Resolved DB URL: {_mask_password(url)}")
    _log(f"Snapshot date (recency anchor): {snapshot_date.isoformat()}")

    start_epoch = time.monotonic()
    cells: dict[CdfMetricId, dict[tuple[int, TimeControlBucket], CdfTable]] = {}
    full_log: list[_CellLogEntry] = []

    engine = create_async_engine(url, pool_pre_ping=True)
    try:
        session_maker = async_sessionmaker(engine, expire_on_commit=False)
        async with session_maker() as session:
            for metric in IN_SCOPE_METRICS:
                for tc in ALL_TIME_CONTROLS:
                    _log(f"  [{metric}|{tc}] querying per_user_values × per_user_anchor...")
                    rows = await _query_per_user_with_anchor(session, metric, tc, snapshot_date)
                    _log(f"  [{metric}|{tc}] received {len(rows)} rows; ranking in Python...")
                    per_anchor, log = _build_cohort_cdf_for(rows, metric, tc)
                    full_log.extend(log)
                    if per_anchor:
                        cells.setdefault(metric, {}).update(
                            {(anchor, tc): table for anchor, table in per_anchor.items()}
                        )
                    non_suppressed = sum(1 for e in log if not e["suppressed"])
                    _log(f"  [{metric}|{tc}] {non_suppressed}/{len(log)} anchors non-suppressed")
    finally:
        await engine.dispose()

    runtime = time.monotonic() - start_epoch

    # Resolve git commit for the gen script (audit-trail).
    git_commit = "unknown"
    try:
        import subprocess

        out = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        )
        git_commit = out.stdout.strip()
    except Exception:  # pragma: no cover — best-effort audit
        pass

    _write_module(cells)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    _archive_prior_report(report_path)
    report_md = _render_regen_report(full_log, snapshot_date, runtime, git_commit)
    report_path.write_text(report_md)
    _log(f"Wrote {report_path}")
    return cells, full_log


def _parse_snapshot_date(raw: str) -> date:
    try:
        return date.fromisoformat(raw)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            f"Invalid --snapshot-date {raw!r}: must be YYYY-MM-DD ({exc})"
        ) from exc


def parse_args() -> argparse.Namespace:
    """Parse and validate CLI arguments."""
    parser = argparse.ArgumentParser(
        description=(
            "Regenerate the cohort empirical-CDF artifact from the benchmark DB "
            "under the Phase 94.4 sliding-window cohort methodology "
            "(CONTEXT D-09 / D-11 / D-13)."
        ),
    )
    parser.add_argument(
        "--target",
        choices=["benchmark"],
        required=True,
        help=(
            "Database target. Only 'benchmark' is supported "
            f"(localhost:{_TARGET_PORT['benchmark']}, {BENCHMARK_DB_NAME_TOKEN})."
        ),
    )
    parser.add_argument(
        "--snapshot-date",
        type=_parse_snapshot_date,
        default=date.today(),
        dest="snapshot_date",
        metavar="YYYY-MM-DD",
        help=(
            "Anchor for the 36-month recency window. Defaults to today (UTC). "
            "Pinning to a specific date is recommended for byte-identical regen."
        ),
    )
    parser.add_argument(
        "--regen-report-path",
        type=Path,
        default=DEFAULT_REPORT_PATH,
        dest="report_path",
        help=(f"Output path for the markdown regen report. Defaults to {DEFAULT_REPORT_PATH}."),
    )
    return parser.parse_args()


async def main() -> None:
    """Entry point: parse CLI args, init Sentry, run regeneration."""
    args = parse_args()
    if settings.SENTRY_DSN:
        sentry_sdk.init(dsn=settings.SENTRY_DSN, environment=settings.ENVIRONMENT)
    _log(
        f"Starting regen: target={args.target} "
        f"snapshot_date={args.snapshot_date.isoformat()} "
        f"report_path={args.report_path}"
    )
    await regenerate(
        target=args.target,
        snapshot_date=args.snapshot_date,
        report_path=args.report_path,
    )
    _log("Done.")


if __name__ == "__main__":
    asyncio.run(main())
