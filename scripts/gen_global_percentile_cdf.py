"""Regenerate the global empirical-CDF artifact from the benchmark DB.

Phase 94.2 — pooled-per-user methodology
----------------------------------------

Each CDF point is now **one deduped cohort user** rather than one (user,
elo_bucket, tc_bucket) cell. Per subject the script pools games across all
TCs played, caps at the most recent 1000 per TC, restricts to a 36-month
window anchored at the CLI-supplied ``--snapshot-date``, applies the
universal filters (rated, non-computer, both ratings non-null, equal-footing
±100), and computes the metric once on that pool. ``selected_users`` is
deduped via ``selected_users_cte(source="benchmark")`` from
``app.services.canonical_slice_sql`` and joined into the pooled aggregates.

What this script produces
-------------------------
1. Overwrites the ``GLOBAL_PERCENTILE_CDF = {...}`` literal in
   ``app/services/global_percentile_cdf.py`` (between the
   ``BEGIN GENERATED REGISTRY`` / ``END GENERATED REGISTRY`` sentinel
   comments — the rest of the module is preserved verbatim). The
   ``n_users`` field on each ``CdfTable`` now correctly reflects the
   distinct-user count post the ≥30-on-pooled-set inclusion floor.
2. Writes ``reports/global-percentile-cdf-latest.md`` (with the
   "Methodology change (Phase 94.2)" banner + Drift vs Phase 94.1 table)
   and archives the prior 94.1 report to
   ``reports/archive/global-percentile-cdf-94.1-YYYY-MM-DD.md``.

Operator workflow::

    bin/benchmark_db.sh start
    uv run python scripts/gen_global_percentile_cdf.py --db benchmark --dry-run
    uv run python scripts/gen_global_percentile_cdf.py --db benchmark

CLI:

* ``--db benchmark`` (required) — only the benchmark Docker DB on port 5433
  is supported. ``_assert_benchmark_db`` refuses to run unless the resolved
  URL contains both ``flawchess_benchmark`` and ``:5433``.
* ``--snapshot-date YYYY-MM-DD`` (optional) — anchors the 36-month recency
  window. Defaults to the last day of ``BENCHMARK_DB_SNAPSHOT_MONTH``
  (currently ``2026-03``, i.e. ``2026-03-31``). Threads into
  ``per_user_cte_for(..., snapshot_date=...)`` so the window does not slide
  with the operator's clock.

The script's safety guards (``_assert_benchmark_db``) are unchanged from
Phase 93. ``_build_per_bucket_sanity_query`` is preserved as a per-cell
distribution diagnostic but the regen report flags it prominently — under
the pooled methodology it no longer reflects the production CDF.
"""

from __future__ import annotations

import argparse
import asyncio
import calendar
import os
import re
import shutil
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.parse import urlparse, urlunparse

import sentry_sdk
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Bootstrap project root so ``app.*`` imports resolve when running as a script.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.config import settings  # noqa: E402

# Canonical-slice CTE builders extracted to `app.services.canonical_slice_sql`
# per Phase 94.1 D-11 and rewritten under Phase 94.2 (pooled-per-user). Single
# source of truth — both this script and the per-user compute service consume
# the same module. Phase 94.3 adds the per-TC inclusion-floor constants for
# the new time-management metric family.
from app.services.canonical_slice_sql import (  # noqa: E402
    ACHIEVABLE_MIN_GAMES,
    CLOCK_GAP_MIN_POOL_N,
    NET_FLAG_RATE_MIN_POOL_N,
    SCORE_GAP_MIN_ENDGAME_N,
    SCORE_GAP_MIN_NON_ENDGAME_N,
    SECTION2_MIN_SPANS_PER_BUCKET,
    TIME_PRESSURE_CLOCK_PCT_THRESHOLD,
    TIME_PRESSURE_MIN_PRESSURED_N,
    per_user_cte_for,
    selected_users_cte,
)

# Re-export ``CdfMetricId`` from the service module so the script and the
# service share a single source of truth (RESEARCH §Pattern 3 lines 222-225 —
# drift-impossibility). Any future widening of the Literal lands in one place.
from app.services.global_percentile_cdf import CdfMetricId  # noqa: E402

# ---------------------------------------------------------------------------
# Constants — no magic numbers in function bodies.
# ---------------------------------------------------------------------------

# Per-metric inclusion floors are now imported from app.services.canonical_slice_sql.
# Alias to the pre-refactor names used in this script's non-SQL code paths
# (registry comment emission in _registry_entry_comment).
INCLUSION_FLOOR_SCORE_GAP_EG: int = SCORE_GAP_MIN_ENDGAME_N
INCLUSION_FLOOR_SCORE_GAP_NON_EG: int = SCORE_GAP_MIN_NON_ENDGAME_N
INCLUSION_FLOOR_ACHIEVABLE: int = ACHIEVABLE_MIN_GAMES
INCLUSION_FLOOR_SECTION2_PER_BUCKET: int = SECTION2_MIN_SPANS_PER_BUCKET

# 99 — every integer percentile from p1 through p99, matches
# ``BREAKPOINT_PERCENTILES`` in ``app/services/global_percentile_cdf.py``
# (ROADMAP success criterion #5).
BREAKPOINTS: tuple[float, ...] = tuple(i / 100.0 for i in range(1, 100))

# Sparse-cell tokens (still referenced by report copy). Under 94.2 the sparse
# cell is excluded inside ``selected_users_cte(source="benchmark")``, not as a
# per-row filter (D-1).
SPARSE_CELL_ELO: int = 2400
SPARSE_CELL_TC: str = "classical"

# Equal-footing opponent filter tolerance (SKILL.md §1).
EQUAL_FOOTING_TOL: int = 100

# Sub-800 drop floor (SKILL.md §1 "Rating-lag selection bias").
SUB_800_FLOOR: int = 800

# Output paths.
OUTPUT_MODULE_PATH: Path = Path("app/services/global_percentile_cdf.py")
OUTPUT_REPORT_PATH: Path = Path("reports/global-percentile-cdf-latest.md")
OUTPUT_ARCHIVE_DIR: Path = Path("reports/archive")

# Safety-guard tokens (mirrors ``scripts/backfill_eval.py --db benchmark``).
BENCHMARK_DB_NAME_TOKEN: str = "flawchess_benchmark"
BENCHMARK_DB_PORT_TOKEN: str = ":5433"

# Sentinel comments wrapping the GLOBAL_PERCENTILE_CDF literal. The script
# rewrites only the block between these markers, preserving the docstring,
# type aliases, constants, dataclass, and ``interpolate_percentile`` helper.
REGISTRY_BEGIN_MARKER: str = "# --- BEGIN GENERATED REGISTRY ---"
REGISTRY_END_MARKER: str = "# --- END GENERATED REGISTRY ---"

# Audit-trail constant (mirrors ``BENCHMARK_DB_SNAPSHOT_MONTH`` in
# ``app/services/global_percentile_cdf.py`` — kept in sync at write time).
BENCHMARK_DB_SNAPSHOT_MONTH: str = "2026-03"

# Floats are rendered to 4 decimal places in both the Python source and the
# report; integers (n_users) are bare. This guarantees byte-identical output
# across runs against the same DB snapshot.
FLOAT_PRECISION: int = 4
SKEW_KURT_PRECISION: int = 4

# In-scope metric IDs. Order matters: registry literal emission walks this
# tuple so two runs produce byte-identical Python source. Grouped by metric
# family for grep-ability (and to make the 4 + 12 split immediately legible).
# ``CdfMetricId`` is imported from ``app.services.global_percentile_cdf``
# above; widening the Literal there propagates here automatically.
IN_SCOPE_METRICS: tuple[CdfMetricId, ...] = (
    # Phase 93 / 94.1 / 94.2 — original 4 (pooled across all TCs).
    "score_gap",
    "achievable_score_gap",
    "section2_score_gap_conv",
    "section2_score_gap_parity",
    # Phase 94.3 (SEED-025 / TPCTL-03) — per-TC time-management family.
    "time_pressure_score_gap_bullet",
    "time_pressure_score_gap_blitz",
    "time_pressure_score_gap_rapid",
    "time_pressure_score_gap_classical",
    "clock_gap_bullet",
    "clock_gap_blitz",
    "clock_gap_rapid",
    "clock_gap_classical",
    "net_flag_rate_bullet",
    "net_flag_rate_blitz",
    "net_flag_rate_rapid",
    "net_flag_rate_classical",
)

# Game-time ELO rating buckets for the per-bucket sanity-check table (SKILL.md
# §1 canonical anchors).
ELO_BUCKETS: tuple[int, ...] = (800, 1200, 1600, 2000, 2400)

# Port map for --db targets. Phase 93 only supports ``benchmark``; the dict is
# kept for parity with ``scripts/backfill_eval.py`` and to make the localhost
# override env-var pattern obvious.
_TARGET_PORT: dict[str, int] = {"benchmark": 5433}
_LOCAL_HOSTS: frozenset[str] = frozenset({"localhost", "127.0.0.1", "::1"})

# Per-metric `value_expr` block — composes onto the canonical CTE. Each entry
# returns a list of ``per_user_values.metric_value`` rows after applying the
# subchapter's inclusion floor (sparse-cell exclusion now lives at cohort
# selection, not per-row — D-1).
PerBucketRow = tuple[int, int, float, float, float]
"""(rating_bucket, n_users, median, skew, excess_kurtosis)."""

MetricResult = tuple[list[float], int]
"""(99-element breakpoint list in p1..p99 order, n_users)."""


# ---------------------------------------------------------------------------
# Snapshot-date default (derived from BENCHMARK_DB_SNAPSHOT_MONTH).
# ---------------------------------------------------------------------------


def _default_snapshot_date() -> date:
    """Last day of ``BENCHMARK_DB_SNAPSHOT_MONTH`` (e.g. ``'2026-03'`` → 2026-03-31).

    Used as the ``--snapshot-date`` CLI default. Threads through
    ``per_user_cte_for(..., snapshot_date=...)`` so the 36-month recency
    window anchors at the benchmark DB snapshot month rather than the
    operator's clock.
    """
    year_str, month_str = BENCHMARK_DB_SNAPSHOT_MONTH.split("-")
    year = int(year_str)
    month = int(month_str)
    _, last_day = calendar.monthrange(year, month)
    return date(year, month, last_day)


# ---------------------------------------------------------------------------
# Logging helper (mirrors backfill_eval.py).
# ---------------------------------------------------------------------------


def _log(msg: str = "") -> None:
    """Print ``msg`` prefixed with a UTC second-precision timestamp."""
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] {msg}")


# ---------------------------------------------------------------------------
# DB URL resolution + safety guard.
# ---------------------------------------------------------------------------


def _db_url(target: str) -> str:
    """Build the asyncpg URL for the chosen ``--db`` target.

    Mirrors ``scripts/backfill_eval.py:_db_url``. Phase 93 only supports
    ``benchmark`` (port 5433). Override via ``BACKFILL_BENCHMARK_DB_URL``
    (must be a localhost host — Docker on the operator workstation).
    """
    if target not in _TARGET_PORT:
        raise ValueError(f"Unknown --db target: {target!r}. Must be one of: {list(_TARGET_PORT)}")

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
    """Refuse to run unless ``url`` points at the benchmark DB.

    Mirrors the safety-guard pattern in ``scripts/backfill_eval.py``: both the
    DB-name token AND the port token MUST be present. This protects against a
    misconfigured ``BACKFILL_BENCHMARK_DB_URL`` accidentally pointing at dev
    (port 5432) or prod (port 15432) — the script is read-only at the SQL
    level but the safety guard is paranoia about misconfiguration (T-93-03).
    """
    if BENCHMARK_DB_NAME_TOKEN not in url or BENCHMARK_DB_PORT_TOKEN not in url:
        raise SystemExit(
            f"Refusing to run: resolved DB URL does not contain both "
            f"{BENCHMARK_DB_NAME_TOKEN!r} and {BENCHMARK_DB_PORT_TOKEN!r}. "
            f"Got: {_mask_password(url)}. "
            f"This script only operates against the benchmark Docker DB on port 5433."
        )


# ---------------------------------------------------------------------------
# SQL composition — canonical CTE + per-metric per_user blocks.
# (Builders are now imported from app.services.canonical_slice_sql above.)
# ---------------------------------------------------------------------------


def _breakpoint_sql_array() -> str:
    """Render ``BREAKPOINTS`` as a PostgreSQL ``ARRAY[…]::double precision[]`` literal."""
    inside = ", ".join(f"{b:.2f}" for b in BREAKPOINTS)
    return f"ARRAY[{inside}]::double precision[]"


def _build_metric_breakpoint_query(metric_id: CdfMetricId, *, snapshot_date: date) -> str:
    """Pooled CDF breakpoint SQL for ``metric_id``.

    Composes ``selected_users_cte(source="benchmark")`` (deduped cohort) with
    ``per_user_cte_for(metric_id, source="benchmark", snapshot_date=...)``
    (pooled per-user aggregate) and a final ``percentile_cont`` over the
    pooled ``per_user_values.metric_value``. The ``count(*) AS n_users``
    now correctly reflects the distinct cohort-user count post the ≥30
    inclusion floor (D-11 / D-6).
    """
    return f"""
WITH {selected_users_cte(source="benchmark")},
{per_user_cte_for(metric_id, source="benchmark", snapshot_date=snapshot_date)}
SELECT
  percentile_cont({_breakpoint_sql_array()}) WITHIN GROUP (ORDER BY metric_value) AS breakpoints,
  count(*) AS n_users
FROM per_user_values
""".strip()


def _build_per_bucket_sanity_query(metric_id: CdfMetricId) -> str:
    """DIAGNOSTIC ONLY (Phase 94.2): per-bucket aggregation **no longer reflects production CDF**.

    Under the pooled methodology the production CDF is computed over a single
    ``per_user_values`` row per deduped cohort user — there are no
    ``(user, elo_bucket, tc_bucket)`` cells to aggregate by, and
    ``per_user_values`` deliberately strips ``user_id`` (D-5). The per-cell
    diagnostic that this function emitted in Phase 94.1 is therefore not
    reconstructable from the production builders alone.

    The function is **preserved** (grep-able, importable, callable without
    raising) so the report still displays the "## Per-rating-bucket sanity
    check (diagnostic only)" subsection with the explanatory callout — but
    the SQL deliberately yields zero rows so the table is empty. Future
    phases can revive a meaningful diagnostic by widening the canonical
    builders to project user_id.

    The output columns are stable for the downstream parser
    (``_query_per_bucket_sanity_check``): ``elo_bucket INT, n_users INT,
    median_v FLOAT8, skew FLOAT8, excess_kurt FLOAT8``.
    """
    # Reference the metric_id to silence ty/ruff unused-arg warnings without
    # using # noqa — the parameter is part of the stable function signature
    # consumed by tests and may be re-honoured by a future diagnostic.
    _ = metric_id
    return """
SELECT
  NULL::int AS elo_bucket,
  NULL::int AS n_users,
  NULL::float8 AS median_v,
  NULL::float8 AS skew,
  NULL::float8 AS excess_kurt
WHERE FALSE
""".strip()


# ---------------------------------------------------------------------------
# Query execution.
# ---------------------------------------------------------------------------


async def _query_metric_breakpoints(
    session: AsyncSession,
    metric_id: CdfMetricId,
    snapshot_date: date,
) -> MetricResult:
    """Run the pooled breakpoint query for ``metric_id`` and return ``(breakpoints, n_users)``."""
    sql = _build_metric_breakpoint_query(metric_id, snapshot_date=snapshot_date)
    row = (await session.execute(text(sql))).one()
    breakpoints_raw = row.breakpoints
    n_users = int(row.n_users)
    if breakpoints_raw is None or n_users == 0:
        raise SystemExit(
            f"Metric {metric_id!r}: percentile_cont returned NULL (no rows). "
            f"Cohort likely below inclusion floor or benchmark DB not ingested."
        )
    # Postgres returns the array as a list of floats; coerce to list[float] for
    # downstream stability.
    breakpoints = [float(v) for v in breakpoints_raw]
    if len(breakpoints) != len(BREAKPOINTS):
        raise SystemExit(
            f"Metric {metric_id!r}: expected {len(BREAKPOINTS)} breakpoints, "
            f"got {len(breakpoints)}."
        )
    return breakpoints, n_users


async def _query_per_bucket_sanity_check(
    session: AsyncSession,
    metric_id: CdfMetricId,
) -> list[PerBucketRow]:
    """Run the per-rating-bucket sanity-check query for ``metric_id``.

    DIAGNOSTIC ONLY under the pooled methodology — see the function docstring
    of ``_build_per_bucket_sanity_query``.
    """
    sql = _build_per_bucket_sanity_query(metric_id)
    rows = (await session.execute(text(sql))).all()
    out: list[PerBucketRow] = []
    for r in rows:
        out.append(
            (
                int(r.elo_bucket),
                int(r.n_users),
                float(r.median_v),
                float(r.skew),
                float(r.excess_kurt),
            )
        )
    return out


# ---------------------------------------------------------------------------
# Python source emission (registry block only).
# ---------------------------------------------------------------------------


def _emit_breakpoints_literal(breakpoints: list[float]) -> str:
    """Render ``breakpoints`` as a parenthesized tuple literal at fixed precision."""
    parts = [f"{v:.{FLOAT_PRECISION}f}" for v in breakpoints]
    # 10 values per line keeps the diff readable; 99 / 10 = 10 lines + 9 on the last.
    chunks = [", ".join(parts[i : i + 10]) for i in range(0, len(parts), 10)]
    body = ",\n            ".join(chunks)
    return f"(\n            {body},\n        )"


def _emit_registry_block(metric_results: dict[CdfMetricId, MetricResult]) -> str:
    """Render the BEGIN…END marker block with one ``CdfTable`` entry per metric."""
    lines: list[str] = [REGISTRY_BEGIN_MARKER]
    lines.append("GLOBAL_PERCENTILE_CDF: Mapping[CdfMetricId, CdfTable] = {")
    for metric_id in IN_SCOPE_METRICS:
        bps, n_users = metric_results[metric_id]
        comment = _registry_entry_comment(metric_id)
        lines.append(f"    # {comment}")
        lines.append(f'    "{metric_id}": CdfTable(')
        lines.append(f"        breakpoints={_emit_breakpoints_literal(bps)},")
        lines.append(f"        n_users={n_users},")
        lines.append("    ),")
    lines.append("}")
    lines.append(REGISTRY_END_MARKER)
    return "\n".join(lines)


def _registry_entry_comment(metric_id: CdfMetricId) -> str:
    """Per-metric inline comment describing the inclusion floor."""
    if metric_id == "score_gap":
        return (
            f"score_gap — inclusion floor "
            f"≥{INCLUSION_FLOOR_SCORE_GAP_EG} endgame AND "
            f"≥{INCLUSION_FLOOR_SCORE_GAP_NON_EG} non-endgame games per user (pooled)."
        )
    if metric_id == "achievable_score_gap":
        return (
            f"achievable_score_gap — inclusion floor "
            f"≥{INCLUSION_FLOOR_ACHIEVABLE} endgame-entry games per user (pooled)."
        )
    if metric_id == "section2_score_gap_conv":
        return (
            f"section2_score_gap_conv — inclusion floor "
            f"≥{INCLUSION_FLOOR_SECTION2_PER_BUCKET} spans in Up-entry-eval bucket (pooled)."
        )
    if metric_id == "section2_score_gap_parity":
        return (
            f"section2_score_gap_parity — inclusion floor "
            f"≥{INCLUSION_FLOOR_SECTION2_PER_BUCKET} spans in Equal-entry-eval bucket (pooled)."
        )
    # Phase 94.3 per-TC time-management family. ``metric_id`` is structurally
    # ``{base}_{tc}`` for base in {time_pressure_score_gap, clock_gap,
    # net_flag_rate}; we split rather than redeclare 12 string-equal arms so
    # the body stays compact and the per-base wording is single-site.
    base, _, tc = metric_id.rpartition("_")
    if base == "time_pressure_score_gap":
        return (
            f"{metric_id} — inclusion floor "
            f"≥{TIME_PRESSURE_MIN_PRESSURED_N} pressured-cell games per user "
            f"on BOTH user side AND opponent side "
            f"(clock_pct < {TIME_PRESSURE_CLOCK_PCT_THRESHOLD:.2f} at endgame "
            f"entry; pooled within {tc})."
        )
    if base == "clock_gap":
        return (
            f"{metric_id} — inclusion floor "
            f"≥{CLOCK_GAP_MIN_POOL_N} endgame-entry games per user with "
            f"non-null user and opponent clock (pooled within {tc}; metric is "
            f"avg((user_clock − opp_clock) / base_time_seconds))."
        )
    if base == "net_flag_rate":
        return (
            f"{metric_id} — inclusion floor "
            f"≥{NET_FLAG_RATE_MIN_POOL_N} endgame games per user "
            f"(pooled within {tc}; metric is "
            f"(timeout_wins − timeout_losses) / total_endgame_games)."
        )
    raise ValueError(f"Unknown metric_id: {metric_id!r}")


def _rewrite_module_source(
    existing_source: str,
    metric_results: dict[CdfMetricId, MetricResult],
) -> str:
    """Replace the BEGIN…END registry block in ``existing_source`` with new values.

    The rest of the file (docstring, type aliases, constants, dataclass,
    ``interpolate_percentile`` helper) is preserved verbatim. Raises
    ``SystemExit`` if the sentinel markers are missing — that is a Task 1
    contract violation, not something the script should silently paper over.
    """
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
    new_block = _emit_registry_block(metric_results)
    return pattern.sub(new_block, existing_source, count=1)


def _write_module(metric_results: dict[CdfMetricId, MetricResult]) -> None:
    """Rewrite ``app/services/global_percentile_cdf.py`` then run ruff format + check.

    Writes to a temp file inside the target directory, runs ``ruff format``
    and ``ruff check --fix`` on it, and only renames over the real path when
    both succeed. Guarantees the committed file is always ruff-formatted
    regardless of the emission template's whitespace.
    """
    existing = OUTPUT_MODULE_PATH.read_text()
    new_source = _rewrite_module_source(existing, metric_results)

    tmp = OUTPUT_MODULE_PATH.with_suffix(".py.tmp")
    tmp.write_text(new_source)

    import subprocess  # local import — this is the only function that shells out

    subprocess.run(["uv", "run", "ruff", "format", str(tmp)], check=True)
    subprocess.run(["uv", "run", "ruff", "check", "--fix", str(tmp)], check=True)

    tmp.replace(OUTPUT_MODULE_PATH)
    _log(f"Wrote {OUTPUT_MODULE_PATH}")


# ---------------------------------------------------------------------------
# Report emission.
# ---------------------------------------------------------------------------


_PER_TC_DISPLAY_BASE: dict[str, str] = {
    "time_pressure_score_gap": "Time Pressure Score Gap",
    "clock_gap": "Clock Gap",
    "net_flag_rate": "Net Flag Rate",
}


def _metric_display_name(metric_id: CdfMetricId) -> str:
    """Human-readable metric label for report headings."""
    static_names: dict[str, str] = {
        "score_gap": "Endgame Score Gap",
        "achievable_score_gap": "Achievable Score Gap",
        "section2_score_gap_conv": "Section 2 Conversion ΔES",
        "section2_score_gap_parity": "Section 2 Parity ΔES",
    }
    if metric_id in static_names:
        return static_names[metric_id]
    # Phase 94.3 per-TC family — split on the trailing TC bucket and render
    # ``"<base> (<tc>)"``.
    base, _, tc = metric_id.rpartition("_")
    if base in _PER_TC_DISPLAY_BASE and tc in ("bullet", "blitz", "rapid", "classical"):
        return f"{_PER_TC_DISPLAY_BASE[base]} ({tc})"
    raise KeyError(metric_id)


def _emit_breakpoint_table(breakpoints: list[float]) -> str:
    """Render the 99-row breakpoint table in pp (×100, one decimal)."""
    lines = ["| percentile | value (pp) |", "|---:|---:|"]
    for i, bp in enumerate(breakpoints):
        label = f"p{i + 1}"
        lines.append(f"| {label} | {bp * 100:+.1f}pp |")
    return "\n".join(lines)


def _emit_per_bucket_table(rows: list[PerBucketRow]) -> str:
    """Render the per-rating-bucket sanity-check table."""
    out = [
        "| rating bucket | n_users | median (pp) | skew | excess kurt |",
        "|---|---:|---:|---:|---:|",
    ]
    by_bucket = {r[0]: r for r in rows}
    for elo in ELO_BUCKETS:
        if elo not in by_bucket:
            out.append(f"| {elo} (game-time) | — | — | — | — |")
            continue
        _, n_users, median_v, skew, excess_kurt = by_bucket[elo]
        out.append(
            f"| {elo} (game-time) | {n_users} | {median_v * 100:+.1f}pp | "
            f"{skew:+.{SKEW_KURT_PRECISION}f} | {excess_kurt:+.{SKEW_KURT_PRECISION}f} |"
        )
    return "\n".join(out)


# ---------------------------------------------------------------------------
# Drift vs Phase 94.1 — parse the archived 94.1 report's breakpoint tables
# and emit a side-by-side comparison for p1/p10/p25/p50/p75/p90/p99.
# ---------------------------------------------------------------------------

# Anchors used to slice the archived report into per-metric sections.
_DRIFT_PERCENTILES: tuple[int, ...] = (1, 10, 25, 50, 75, 90, 99)


def _parse_archived_breakpoints(archive_path: Path) -> dict[CdfMetricId, dict[int, float]]:
    """Parse per-metric ``p1..p99`` rows out of the 94.1 archive report.

    Returns ``{metric_id: {percentile_int: value_pp}}``. Silently returns an
    empty dict if the archive is missing or malformed — the drift section
    will then be skipped.
    """
    if not archive_path.exists():
        return {}
    try:
        text_blob = archive_path.read_text()
    except OSError:
        return {}
    out: dict[CdfMetricId, dict[int, float]] = {}
    for metric_id in IN_SCOPE_METRICS:
        # Section anchor: a section heading line "## ... (`{metric_id}`)" — the
        # leading "## " prefix is required so the cohort-listing line that
        # also mentions `(`{metric_id}`)` is not picked up first.
        anchor_re = re.compile(r"^## [^\n]*\(`" + re.escape(metric_id) + r"`\)", flags=re.MULTILINE)
        anchor_match = anchor_re.search(text_blob)
        if anchor_match is None:
            continue
        idx = anchor_match.start()
        # Slice until the next "## " heading (or EOF).
        next_section = text_blob.find("\n## ", anchor_match.end())
        section = text_blob[idx : next_section if next_section > 0 else len(text_blob)]
        # Match "| pN | +X.YYpp |" or "| pN | -X.YYpp |".
        row_re = re.compile(r"\|\s*p(\d+)\s*\|\s*([+-]?\d+\.\d+)pp\s*\|")
        rows: dict[int, float] = {}
        for m in row_re.finditer(section):
            p = int(m.group(1))
            v = float(m.group(2))
            rows[p] = v
        if rows:
            out[metric_id] = rows
    return out


def _emit_drift_table(
    metric_results: dict[CdfMetricId, MetricResult],
    archived: dict[CdfMetricId, dict[int, float]],
) -> str:
    """Render the ``## Drift vs Phase 94.1`` markdown subsection.

    Side-by-side per-metric block: rows = ``p1 / p10 / p25 / p50 / p75 / p90 / p99``;
    columns = ``94.1 / 94.2 / Δ`` (in pp). If a percentile is missing from
    the archive, render as ``—``.
    """
    if not archived:
        return ""
    out: list[str] = ["## Drift vs Phase 94.1\n"]
    out.append(
        "Side-by-side breakpoint values for the previous (per-cell) and current "
        "(pooled-per-user) methodologies. Δ is **(94.2 − 94.1)** in pp.\n"
    )
    for metric_id in IN_SCOPE_METRICS:
        out.append(f"### {_metric_display_name(metric_id)} (`{metric_id}`)\n")
        out.append("| percentile | 94.1 (pp) | 94.2 (pp) | Δ (pp) |")
        out.append("|---:|---:|---:|---:|")
        bps_94_2, _ = metric_results[metric_id]
        prior = archived.get(metric_id, {})
        for p in _DRIFT_PERCENTILES:
            v_94_2_pp = bps_94_2[p - 1] * 100.0
            v_94_1_pp = prior.get(p)
            if v_94_1_pp is None:
                out.append(f"| p{p} | — | {v_94_2_pp:+.1f}pp | — |")
            else:
                delta = v_94_2_pp - v_94_1_pp
                out.append(f"| p{p} | {v_94_1_pp:+.1f}pp | {v_94_2_pp:+.1f}pp | {delta:+.1f}pp |")
        out.append("")
    return "\n".join(out)


# ---------------------------------------------------------------------------
# Report assembly.
# ---------------------------------------------------------------------------

# Verbatim banner — the regen-report acceptance criterion in PLAN.md asserts
# this exact string is present at the top of the new report.
_METHODOLOGY_BANNER: str = (
    "**Methodology change (Phase 94.2):** Each CDF point is now one deduped "
    "cohort user (pooled across TCs played, capped at 1000 games/TC, ≤36 months "
    "from snapshot). Breakpoint values shift materially from prior reports; the "
    "per-rating-bucket sanity table below is a distribution-shape diagnostic and "
    "does NOT correspond to what the production CDF measures."
)

# Verbatim per-table callout — emitted above every per-rating-bucket sanity
# table. Acceptance criterion in PLAN.md asserts this exact string is present.
_PER_BUCKET_CALLOUT: str = "> This per-cell distribution no longer reflects the production CDF."


def _emit_report(
    metric_results: dict[CdfMetricId, MetricResult],
    per_bucket_results: dict[CdfMetricId, list[PerBucketRow]],
    snapshot_iso: str,
    snapshot_date: date,
    archived: dict[CdfMetricId, dict[int, float]],
) -> str:
    """Compose the markdown text of ``reports/global-percentile-cdf-latest.md``."""
    date_str = snapshot_iso[:10]
    header = (
        f"# Global Percentile CDF — Pooled-Per-User Methodology (Phase 94.2)\n\n"
        f"{_METHODOLOGY_BANNER}\n\n"
        f"- **DB**: benchmark (Docker on localhost:5433, flawchess_benchmark)\n"
        f"- **Report generated**: {snapshot_iso}\n"
        f"- **Snapshot anchor (recency window)**: "
        f"{snapshot_date.isoformat()} (36-month window: "
        f"≥ {snapshot_date.isoformat()} − INTERVAL '36 months')\n"
        f"- **Benchmark DB snapshot month**: {BENCHMARK_DB_SNAPSHOT_MONTH}\n"
        f"- **Methodology source**: `app/services/canonical_slice_sql.py` "
        f"(pooled-per-user, D-1 / D-5 / D-6 / D-8 / D-11).\n"
        f'- **Cohort selection** (`selected_users_cte(source="benchmark")`): '
        f"deduped on `lower(lichess_username)` from `benchmark_selected_users`, "
        f"filtered to `benchmark_ingest_checkpoints.status='completed'`, dropping "
        f"users whose only selection slot is `({SPARSE_CELL_ELO}, {SPARSE_CELL_TC})` "
        f"(D-1).\n"
        f"- **Per-user pool**: most-recent-1000-per-TC × 36-month window pooled "
        f"across all TCs played; universal filters (rated, non-computer, both "
        f"ratings non-null, equal-footing `|opp - user| ≤ {EQUAL_FOOTING_TOL}`).\n"
        f"- **Breakpoint set**: every integer percentile p1..p99 (99 entries). "
        f"Values rendered in pp (×100, one decimal).\n"
        f"- **Generated by**: `scripts/gen_global_percentile_cdf.py --db benchmark "
        f"--snapshot-date {snapshot_date.isoformat()}` against the local benchmark "
        f"Docker DB.\n"
        f"- **Date**: {date_str}\n"
        f"- **Cohort sizes (post per-metric inclusion floor)**:\n"
    )
    cohort_lines = []
    for metric_id in IN_SCOPE_METRICS:
        _, n_users = metric_results[metric_id]
        cohort_lines.append(
            f"  - **{_metric_display_name(metric_id)}** (`{metric_id}`): n_users = {n_users}"
        )

    sections: list[str] = []
    for metric_id in IN_SCOPE_METRICS:
        bps, n_users = metric_results[metric_id]
        per_bucket = per_bucket_results.get(metric_id, [])
        sections.append(
            f"## {_metric_display_name(metric_id)} (`{metric_id}`)\n\n"
            f"- **Cohort size**: n_users = {n_users}\n"
            f"- **Inclusion floor**: {_registry_entry_comment(metric_id)}\n"
            f"- **Sparse cell** `({SPARSE_CELL_ELO}, {SPARSE_CELL_TC})` excluded at cohort selection (D-1).\n\n"
            f"### Breakpoint table (p1..p99)\n\n"
            f"{_emit_breakpoint_table(bps)}\n\n"
            f"### Per-rating-bucket sanity check (diagnostic only)\n\n"
            f"{_PER_BUCKET_CALLOUT}\n\n"
            f"{_emit_per_bucket_table(per_bucket)}\n"
        )

    drift_section = _emit_drift_table(metric_results, archived)
    drift_block = ("\n" + drift_section + "\n") if drift_section else ""

    return header + "\n".join(cohort_lines) + "\n\n" + "\n".join(sections) + drift_block


def _archive_prior_report(today: date) -> Path | None:
    """Copy the prior 94.1 report (if any) into ``reports/archive/`` before overwrite.

    Returns the archive path that was written (or that already existed). Idempotent:
    if the dated archive destination already exists, logs a warning and returns
    the existing path without copying.
    """
    if not OUTPUT_REPORT_PATH.exists():
        _log(f"No prior {OUTPUT_REPORT_PATH} to archive; skipping archive step.")
        return None
    OUTPUT_ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    archive_path = OUTPUT_ARCHIVE_DIR / f"global-percentile-cdf-94.1-{today.isoformat()}.md"
    if archive_path.exists():
        _log(f"Archive already exists: {archive_path}; not overwriting.")
        return archive_path
    shutil.copy2(OUTPUT_REPORT_PATH, archive_path)
    _log(f"Archived {OUTPUT_REPORT_PATH} -> {archive_path}")
    return archive_path


def _write_report(
    metric_results: dict[CdfMetricId, MetricResult],
    per_bucket_results: dict[CdfMetricId, list[PerBucketRow]],
    snapshot_date: date,
) -> None:
    """Archive the prior 94.1 report, then write the new pooled-methodology report."""
    OUTPUT_REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    archive_path = _archive_prior_report(date.today())
    archived = _parse_archived_breakpoints(archive_path) if archive_path else {}
    if archive_path and not archived:
        _log(f"WARNING: could not parse breakpoints out of {archive_path}; drift section skipped.")
    snapshot_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    OUTPUT_REPORT_PATH.write_text(
        _emit_report(metric_results, per_bucket_results, snapshot_iso, snapshot_date, archived)
    )
    _log(f"Wrote {OUTPUT_REPORT_PATH}")


# ---------------------------------------------------------------------------
# Driver.
# ---------------------------------------------------------------------------


async def run_regen(
    *,
    db: str,
    dry_run: bool,
    report_only: bool,
    snapshot_date: date,
) -> None:
    """Main driver. Connects to the benchmark DB, runs queries, emits outputs."""
    url = _db_url(db)
    _assert_benchmark_db(url)
    _log(f"Resolved DB URL: {_mask_password(url)}")
    _log(f"Snapshot date (recency anchor): {snapshot_date.isoformat()}")

    if dry_run:
        _log("--dry-run: connecting to benchmark DB to verify cohort sizes only.")
    if report_only:
        _log("--report-only: will regenerate the report; Python source preserved.")

    engine = create_async_engine(url, pool_pre_ping=True)
    try:
        session_maker = async_sessionmaker(engine, expire_on_commit=False)
        async with session_maker() as session:
            metric_results: dict[CdfMetricId, MetricResult] = {}
            per_bucket_results: dict[CdfMetricId, list[PerBucketRow]] = {}
            for metric_id in IN_SCOPE_METRICS:
                _log(f"  [{metric_id}] querying pooled breakpoints + n_users...")
                bps, n_users = await _query_metric_breakpoints(session, metric_id, snapshot_date)
                metric_results[metric_id] = (bps, n_users)
                _log(
                    f"  [{metric_id}] n_users={n_users} "
                    f"p1={bps[0]:+.4f} p50={bps[49]:+.4f} p99={bps[-1]:+.4f}"
                )
                if not dry_run:
                    _log(f"  [{metric_id}] querying per-rating-bucket sanity check (diagnostic)...")
                    try:
                        per_bucket_results[metric_id] = await _query_per_bucket_sanity_check(
                            session, metric_id
                        )
                    except Exception as exc:
                        # The diagnostic must never block the production CDF regen.
                        _log(
                            f"  [{metric_id}] WARNING: per-bucket sanity diagnostic failed: {exc!r}; "
                            f"continuing without it."
                        )
                        per_bucket_results[metric_id] = []

        if dry_run:
            _log(f"--dry-run: would write {OUTPUT_MODULE_PATH} and {OUTPUT_REPORT_PATH}")
            return

        if not report_only:
            _write_module(metric_results)
        _write_report(metric_results, per_bucket_results, snapshot_date)
    finally:
        await engine.dispose()


def _parse_snapshot_date(raw: str) -> date:
    """Parse ``YYYY-MM-DD`` into a ``date``; raises argparse-friendly ValueError on bad input."""
    try:
        return date.fromisoformat(raw)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            f"Invalid --snapshot-date {raw!r}: must be YYYY-MM-DD ({exc})"
        ) from exc


def parse_args() -> argparse.Namespace:
    """Parse and validate CLI arguments."""
    default_snap = _default_snapshot_date()
    parser = argparse.ArgumentParser(
        description=(
            "Regenerate the global empirical-CDF artifact from the benchmark DB "
            "under the Phase 94.2 pooled-per-user methodology. "
            "Mirrors the scripts/backfill_eval.py --db benchmark pattern. "
            "Methodology source-of-truth: app/services/canonical_slice_sql.py."
        ),
    )
    parser.add_argument(
        "--db",
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
        default=default_snap,
        dest="snapshot_date",
        metavar="YYYY-MM-DD",
        help=(
            "Anchor for the 36-month recency window in the pooled per-user CTEs. "
            f"Defaults to the last day of BENCHMARK_DB_SNAPSHOT_MONTH "
            f"(default: {default_snap.isoformat()})."
        ),
    )
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument(
        "--dry-run",
        action="store_true",
        dest="dry_run",
        help=(
            "Resolve URL, run safety guard, query breakpoints to verify cohort "
            "sizes; do NOT overwrite Python source or report file."
        ),
    )
    mode_group.add_argument(
        "--report-only",
        action="store_true",
        dest="report_only",
        help=(
            "Regenerate reports/global-percentile-cdf-latest.md WITHOUT "
            f"overwriting {OUTPUT_MODULE_PATH}. Sanity-check the dataset before "
            "committing the Python source."
        ),
    )
    return parser.parse_args()


async def main() -> None:
    """Entry point: parse CLI args, init Sentry, run regeneration."""
    args = parse_args()
    if settings.SENTRY_DSN:
        sentry_sdk.init(dsn=settings.SENTRY_DSN, environment=settings.ENVIRONMENT)
    _log(
        f"Starting regen: db={args.db} dry_run={args.dry_run} "
        f"report_only={args.report_only} snapshot_date={args.snapshot_date.isoformat()}"
    )
    await run_regen(
        db=args.db,
        dry_run=args.dry_run,
        report_only=args.report_only,
        snapshot_date=args.snapshot_date,
    )
    _log("Done.")


if __name__ == "__main__":
    asyncio.run(main())
