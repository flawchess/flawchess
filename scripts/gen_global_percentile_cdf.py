"""Regenerate the global empirical-CDF artifact from the benchmark DB.

Mirrors the ``scripts/backfill_eval.py --db benchmark`` pattern. Methodology
source-of-truth: ``.claude/skills/benchmarks/SKILL.md`` Chapter 4.

What this script produces
-------------------------
1. Overwrites the ``GLOBAL_PERCENTILE_CDF = {...}`` literal in
   ``app/services/global_percentile_cdf.py`` (between the
   ``BEGIN GENERATED REGISTRY`` / ``END GENERATED REGISTRY`` sentinel
   comments — the rest of the module is preserved verbatim).
2. Writes ``reports/global-percentile-cdf-latest.md``, archiving the
   previous file in place per the D-07 rotation rule.

Operator workflow (Plan 93-02 Task 3 — HUMAN-UAT)::

    bin/benchmark_db.sh start
    uv run python scripts/gen_global_percentile_cdf.py --db benchmark --dry-run
    uv run python scripts/gen_global_percentile_cdf.py --db benchmark

The script supports only ``--db benchmark``. The artifact is regenerated
from the benchmark DB only — there is no dev or prod equivalent. The
safety guard refuses to run unless the resolved DATABASE_URL contains
BOTH ``flawchess_benchmark`` (database name) AND ``:5433`` (port).

Phase 93 ships the artifact + the runtime helper. Phase 94 wires the
helper into endpoint responses.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal
from urllib.parse import urlparse, urlunparse

import sentry_sdk
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Bootstrap project root so ``app.*`` imports resolve when running as a script.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.config import settings  # noqa: E402

# ---------------------------------------------------------------------------
# Constants — no magic numbers in function bodies.
# ---------------------------------------------------------------------------

# Per-metric inclusion floors (Plan 02 `<key_links>` + SKILL.md §3.1.5 / §3.1.6
# / §3.2.2). score_gap pairs the two endgame / non-endgame floors; the rest
# are scalar.
INCLUSION_FLOOR_SCORE_GAP_EG: int = 30
INCLUSION_FLOOR_SCORE_GAP_NON_EG: int = 30
INCLUSION_FLOOR_ACHIEVABLE: int = 20
INCLUSION_FLOOR_SECTION2_PER_BUCKET: int = 20

# 99 — every integer percentile from p1 through p99, matches
# ``BREAKPOINT_PERCENTILES`` in ``app/services/global_percentile_cdf.py``
# (ROADMAP success criterion #5).
BREAKPOINTS: tuple[float, ...] = tuple(i / 100.0 for i in range(1, 100))

# Sparse-cell exclusion (SKILL.md §1).
SPARSE_CELL_ELO: int = 2400
SPARSE_CELL_TC: str = "classical"

# Equal-footing opponent filter tolerance (SKILL.md §1).
EQUAL_FOOTING_TOL: int = 100

# Sub-800 drop floor (SKILL.md §1 "Rating-lag selection bias").
SUB_800_FLOOR: int = 800

# Output paths.
OUTPUT_MODULE_PATH: Path = Path("app/services/global_percentile_cdf.py")
OUTPUT_REPORT_PATH: Path = Path("reports/global-percentile-cdf-latest.md")

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

# In-scope metric IDs (D-02). Order matters: registry literal emission walks
# this tuple so two runs produce byte-identical Python source.
CdfMetricId = Literal[
    "score_gap",
    "achievable_score_gap",
    "section2_score_gap_conv",
    "section2_score_gap_parity",
]

IN_SCOPE_METRICS: tuple[CdfMetricId, ...] = (
    "score_gap",
    "achievable_score_gap",
    "section2_score_gap_conv",
    "section2_score_gap_parity",
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
# subchapter's inclusion floor and sparse-cell exclusion.
PerBucketRow = tuple[int, int, float, float, float]
"""(rating_bucket, n_users, median, skew, excess_kurtosis)."""

MetricResult = tuple[list[float], int]
"""(99-element breakpoint list in p1..p99 order, n_users)."""


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
# ---------------------------------------------------------------------------


def _canonical_selected_users_cte() -> str:
    """Return the ``selected_users`` CTE block (SKILL.md §1 Standard CTE).

    NB: the SKILL.md §1.5 "Current-DB-state checkpoint exception" allows
    falling back to a no-checkpoint join when the DB is partially ingested.
    We assume the canonical (checkpoint-joined) shape here — Plan 93-02
    Task 3 verifies cohort sizes are sane in the dry-run before regenerating.
    """
    return """
selected_users AS (
  SELECT u.id AS user_id, bsu.tc_bucket,
         bsu.rating_bucket AS selection_rating_bucket,
         bsu.median_elo
  FROM benchmark_selected_users bsu
  JOIN benchmark_ingest_checkpoints bic
    ON bic.lichess_username = bsu.lichess_username
   AND bic.tc_bucket = bsu.tc_bucket
   AND bic.status = 'completed'
  JOIN users u ON lower(u.lichess_username) = lower(bsu.lichess_username)
)
""".strip()


def _user_elo_at_game_expr() -> str:
    """SQL expression for the cohort user's rating at game time (SKILL.md §1)."""
    return "(CASE WHEN g.user_color::text='white' THEN g.white_rating ELSE g.black_rating END)"


def _elo_bucket_expr(user_elo_alias: str) -> str:
    """SQL expression to bucket ``user_elo_alias`` into the 5 canonical anchors.

    Returns NULL for sub-800 (callers gate with ``WHERE user_elo_at_game >= 800``).
    """
    return (
        f"(CASE WHEN {user_elo_alias} < {SUB_800_FLOOR} THEN NULL "
        f"WHEN {user_elo_alias} < 1200 THEN 800 "
        f"WHEN {user_elo_alias} < 1600 THEN 1200 "
        f"WHEN {user_elo_alias} < 2000 THEN 1600 "
        f"WHEN {user_elo_alias} < 2400 THEN 2000 "
        f"ELSE 2400 END)"
    )


def _equal_footing_filter_sql() -> str:
    """Equal-footing opponent filter clause (SKILL.md §1, universal)."""
    return (
        f"abs("
        f"(CASE WHEN g.user_color='white' THEN g.white_rating ELSE g.black_rating END)"
        f" - (CASE WHEN g.user_color='white' THEN g.black_rating ELSE g.white_rating END)"
        f") <= {EQUAL_FOOTING_TOL}"
    )


def _sparse_exclusion_sql(elo_col: str, tc_col: str) -> str:
    """SQL fragment to exclude the sparse ``(2400, classical)`` cell."""
    return f"NOT ({elo_col} = {SPARSE_CELL_ELO} AND {tc_col} = '{SPARSE_CELL_TC}')"


def _per_user_cte_score_gap() -> str:
    """``per_user_values(metric_value, elo_bucket, tc_bucket)`` CTE for ``score_gap``.

    Per-user ``eg_score - non_eg_score`` over the user's endgame and
    non-endgame games (SKILL.md §3.1.6). Inclusion floor: ≥30 endgame AND
    ≥30 non-endgame games.
    """
    ueag = _user_elo_at_game_expr()
    elo_bucket = _elo_bucket_expr(ueag)
    return f"""
endgame_game_ids AS (
  SELECT game_id FROM game_positions
  WHERE endgame_class IS NOT NULL
  GROUP BY game_id HAVING count(*) >= 6
),
rows AS (
  SELECT
    g.user_id,
    {ueag} AS user_elo_at_game,
    {elo_bucket} AS elo_bucket,
    su.tc_bucket AS tc_bucket,
    CASE
      WHEN (g.result = '1-0' AND g.user_color = 'white')
        OR (g.result = '0-1' AND g.user_color = 'black') THEN 1.0
      WHEN g.result = '1/2-1/2' THEN 0.5
      ELSE 0.0
    END AS score,
    (eg.game_id IS NOT NULL) AS has_endgame
  FROM games g
  JOIN selected_users su ON su.user_id = g.user_id
  LEFT JOIN endgame_game_ids eg ON eg.game_id = g.id
  WHERE g.rated AND NOT g.is_computer_game
    AND g.time_control_bucket::text = su.tc_bucket
    AND g.white_rating IS NOT NULL AND g.black_rating IS NOT NULL
    AND {_equal_footing_filter_sql()}
),
per_user AS (
  SELECT
    user_id, elo_bucket, tc_bucket,
    avg(score) FILTER (WHERE has_endgame)     AS eg_score,
    avg(score) FILTER (WHERE NOT has_endgame) AS non_eg_score
  FROM rows
  WHERE elo_bucket IS NOT NULL
  GROUP BY user_id, elo_bucket, tc_bucket
  HAVING count(*) FILTER (WHERE has_endgame)     >= {INCLUSION_FLOOR_SCORE_GAP_EG}
     AND count(*) FILTER (WHERE NOT has_endgame) >= {INCLUSION_FLOOR_SCORE_GAP_NON_EG}
),
per_user_values AS (
  SELECT (eg_score - non_eg_score) AS metric_value, elo_bucket, tc_bucket
  FROM per_user
  WHERE {_sparse_exclusion_sql("elo_bucket", "tc_bucket")}
)
""".strip()


def _per_user_cte_achievable() -> str:
    """``per_user_values`` CTE for ``achievable_score_gap`` (SKILL.md §3.1.5)."""
    ueag = _user_elo_at_game_expr()
    elo_bucket = _elo_bucket_expr(ueag)
    return f"""
endgame_game_ids AS (
  SELECT game_id FROM game_positions
  WHERE endgame_class IS NOT NULL
  GROUP BY game_id HAVING count(*) >= 6
),
entry_rows AS (
  SELECT gp.game_id, gp.eval_cp, gp.eval_mate,
         ROW_NUMBER() OVER (PARTITION BY gp.game_id ORDER BY gp.ply ASC) AS rn
  FROM game_positions gp
  JOIN endgame_game_ids eg ON eg.game_id = gp.game_id
  WHERE gp.endgame_class IS NOT NULL
),
rows AS (
  SELECT
    g.user_id,
    {ueag} AS user_elo_at_game,
    {elo_bucket} AS elo_bucket,
    su.tc_bucket AS tc_bucket,
    (
      CASE
        WHEN (g.result = '1-0' AND g.user_color = 'white')
          OR (g.result = '0-1' AND g.user_color = 'black') THEN 1.0
        WHEN g.result = '1/2-1/2' THEN 0.5
        ELSE 0.0
      END
      -
      CASE
        WHEN er.eval_mate IS NOT NULL AND
             (er.eval_mate * (CASE WHEN g.user_color='white' THEN 1 ELSE -1 END)) > 0 THEN 1.0
        WHEN er.eval_mate IS NOT NULL AND
             (er.eval_mate * (CASE WHEN g.user_color='white' THEN 1 ELSE -1 END)) < 0 THEN 0.0
        WHEN er.eval_cp IS NOT NULL AND abs(er.eval_cp) < 2000
             THEN 1.0 / (1.0 + exp(-0.00368208 *
                  (er.eval_cp * (CASE WHEN g.user_color='white' THEN 1 ELSE -1 END))))
        ELSE NULL
      END
    ) AS d_i
  FROM games g
  JOIN selected_users su ON su.user_id = g.user_id
  JOIN entry_rows er ON er.game_id = g.id AND er.rn = 1
  WHERE g.rated AND NOT g.is_computer_game
    AND g.time_control_bucket::text = su.tc_bucket
    AND g.white_rating IS NOT NULL AND g.black_rating IS NOT NULL
    AND {_equal_footing_filter_sql()}
),
per_user AS (
  SELECT user_id, elo_bucket, tc_bucket,
         avg(d_i) AS achievable_gap
  FROM rows
  WHERE elo_bucket IS NOT NULL
  GROUP BY user_id, elo_bucket, tc_bucket
  HAVING count(*) FILTER (WHERE d_i IS NOT NULL) >= {INCLUSION_FLOOR_ACHIEVABLE}
),
per_user_values AS (
  SELECT achievable_gap AS metric_value, elo_bucket, tc_bucket
  FROM per_user
  WHERE achievable_gap IS NOT NULL
    AND {_sparse_exclusion_sql("elo_bucket", "tc_bucket")}
)
""".strip()


def _per_user_cte_section2(bucket_label: str) -> str:
    """``per_user_values`` CTE for ``section2_score_gap_{conv,parity}`` (SKILL.md §3.2.2).

    ``bucket_label`` is one of ``'conversion'`` / ``'parity'`` — partitions the
    per-span gaps to spans whose entry-eval bucket matches.
    """
    ueag = _user_elo_at_game_expr()
    elo_bucket = _elo_bucket_expr(ueag)
    # The §3.2.2 query is identical up to the final per-user-bucket aggregation;
    # we just filter `bucket = bucket_label` at the per-user step.
    return f"""
spans AS (
  SELECT
    gp.game_id, gp.endgame_class,
    (array_agg(gp.eval_cp   ORDER BY gp.ply ASC))[1] AS entry_eval_cp,
    (array_agg(gp.eval_mate ORDER BY gp.ply ASC))[1] AS entry_eval_mate,
    min(gp.ply) AS span_min_ply
  FROM game_positions gp
  JOIN games g           ON g.id = gp.game_id
  JOIN selected_users su ON su.user_id = g.user_id
  WHERE gp.endgame_class IS NOT NULL
    AND g.rated AND NOT g.is_computer_game
    AND g.time_control_bucket::text = su.tc_bucket
    AND g.white_rating IS NOT NULL AND g.black_rating IS NOT NULL
    AND {_equal_footing_filter_sql()}
  GROUP BY gp.game_id, gp.endgame_class
  HAVING count(gp.ply) >= 6
),
spans_with_next AS (
  SELECT s.*,
         lead(s.entry_eval_cp)   OVER (PARTITION BY s.game_id ORDER BY s.span_min_ply) AS next_eval_cp,
         lead(s.entry_eval_mate) OVER (PARTITION BY s.game_id ORDER BY s.span_min_ply) AS next_eval_mate
  FROM spans s
),
gap_rows AS (
  SELECT
    g.user_id,
    {ueag} AS user_elo_at_game,
    {elo_bucket} AS elo_bucket,
    su.tc_bucket AS tc_bucket,
    CASE
      WHEN swn.entry_eval_mate IS NOT NULL THEN
        CASE WHEN (swn.entry_eval_mate * (CASE WHEN g.user_color='white' THEN 1 ELSE -1 END)) > 0
          THEN 'conversion' ELSE 'recovery' END
      WHEN swn.entry_eval_cp IS NOT NULL THEN
        CASE
          WHEN (swn.entry_eval_cp * (CASE WHEN g.user_color='white' THEN 1 ELSE -1 END)) >= 100
            THEN 'conversion'
          WHEN (swn.entry_eval_cp * (CASE WHEN g.user_color='white' THEN 1 ELSE -1 END)) <= -100
            THEN 'recovery'
          ELSE 'parity'
        END
      ELSE 'parity'
    END AS bucket,
    (
      CASE
        WHEN swn.next_eval_mate IS NOT NULL
          THEN CASE WHEN (swn.next_eval_mate * (CASE WHEN g.user_color='white' THEN 1 ELSE -1 END)) > 0
                    THEN 1.0 ELSE 0.0 END
        WHEN swn.next_eval_cp IS NOT NULL
          THEN 1.0 / (1.0 + exp(-0.00368208 *
                 (swn.next_eval_cp * (CASE WHEN g.user_color='white' THEN 1 ELSE -1 END))))
        ELSE
          CASE
            WHEN (g.result='1-0' AND g.user_color='white')
              OR (g.result='0-1' AND g.user_color='black') THEN 1.0
            WHEN g.result='1/2-1/2' THEN 0.5
            ELSE 0.0
          END
      END
    ) - (
      CASE
        WHEN swn.entry_eval_mate IS NOT NULL
          THEN CASE WHEN (swn.entry_eval_mate * (CASE WHEN g.user_color='white' THEN 1 ELSE -1 END)) > 0
                    THEN 1.0 ELSE 0.0 END
        WHEN swn.entry_eval_cp IS NOT NULL
          THEN 1.0 / (1.0 + exp(-0.00368208 *
                 (swn.entry_eval_cp * (CASE WHEN g.user_color='white' THEN 1 ELSE -1 END))))
        ELSE NULL
      END
    ) AS gap_span
  FROM spans_with_next swn
  JOIN games g           ON g.id = swn.game_id
  JOIN selected_users su ON su.user_id = g.user_id
  WHERE (swn.entry_eval_cp IS NOT NULL OR swn.entry_eval_mate IS NOT NULL)
    AND {ueag} >= {SUB_800_FLOOR}
),
per_user_bucket AS (
  SELECT user_id, elo_bucket, tc_bucket, bucket,
         avg(gap_span) AS mean_gap
  FROM gap_rows
  WHERE gap_span IS NOT NULL
    AND elo_bucket IS NOT NULL
    AND {_sparse_exclusion_sql("elo_bucket", "tc_bucket")}
  GROUP BY user_id, elo_bucket, tc_bucket, bucket
  HAVING count(*) >= {INCLUSION_FLOOR_SECTION2_PER_BUCKET}
),
per_user_values AS (
  SELECT mean_gap AS metric_value, elo_bucket, tc_bucket
  FROM per_user_bucket
  WHERE bucket = '{bucket_label}'
)
""".strip()


def _per_user_cte_for(metric_id: CdfMetricId) -> str:
    """Dispatch to the metric-specific ``per_user_values`` CTE block."""
    if metric_id == "score_gap":
        return _per_user_cte_score_gap()
    if metric_id == "achievable_score_gap":
        return _per_user_cte_achievable()
    if metric_id == "section2_score_gap_conv":
        return _per_user_cte_section2("conversion")
    if metric_id == "section2_score_gap_parity":
        return _per_user_cte_section2("parity")
    raise ValueError(f"Unknown metric_id: {metric_id!r}")


def _breakpoint_sql_array() -> str:
    """Render ``BREAKPOINTS`` as a PostgreSQL ``ARRAY[…]::double precision[]`` literal."""
    inside = ", ".join(f"{b:.2f}" for b in BREAKPOINTS)
    return f"ARRAY[{inside}]::double precision[]"


def _build_metric_breakpoint_query(metric_id: CdfMetricId) -> str:
    """Full SQL for ``metric_id``: canonical CTE + per_user_values + percentile_cont."""
    return f"""
WITH {_canonical_selected_users_cte()},
{_per_user_cte_for(metric_id)}
SELECT
  percentile_cont({_breakpoint_sql_array()}) WITHIN GROUP (ORDER BY metric_value) AS breakpoints,
  count(*) AS n_users
FROM per_user_values
""".strip()


def _build_per_bucket_sanity_query(metric_id: CdfMetricId) -> str:
    """Per-rating-bucket sanity-check query (median + skew + excess kurtosis + n_users).

    Postgres has no built-in skew/kurtosis aggregate; we compute from the
    standard moment formulas. Excess kurtosis = ``E[((x-μ)/σ)^4] − 3``.
    """
    return f"""
WITH {_canonical_selected_users_cte()},
{_per_user_cte_for(metric_id)},
stats AS (
  SELECT
    elo_bucket,
    count(*)         AS n_users,
    avg(metric_value)     AS mu,
    stddev_pop(metric_value) AS sigma,
    percentile_cont(0.5) WITHIN GROUP (ORDER BY metric_value) AS median_v
  FROM per_user_values
  GROUP BY elo_bucket
),
moments AS (
  SELECT
    pv.elo_bucket,
    avg(power(pv.metric_value - s.mu, 3)) AS m3,
    avg(power(pv.metric_value - s.mu, 4)) AS m4
  FROM per_user_values pv
  JOIN stats s ON s.elo_bucket = pv.elo_bucket
  GROUP BY pv.elo_bucket
)
SELECT
  s.elo_bucket,
  s.n_users::int,
  s.median_v::float8 AS median_v,
  CASE WHEN s.sigma > 0 THEN (m.m3 / power(s.sigma, 3))::float8 ELSE 0.0 END AS skew,
  CASE WHEN s.sigma > 0 THEN ((m.m4 / power(s.sigma, 4)) - 3.0)::float8 ELSE 0.0 END AS excess_kurt
FROM stats s
JOIN moments m ON m.elo_bucket = s.elo_bucket
WHERE s.elo_bucket IS NOT NULL
ORDER BY s.elo_bucket
""".strip()


# ---------------------------------------------------------------------------
# Query execution.
# ---------------------------------------------------------------------------


async def _query_metric_breakpoints(
    session: AsyncSession,
    metric_id: CdfMetricId,
) -> MetricResult:
    """Run the breakpoint query for ``metric_id`` and return ``(breakpoints, n_users)``."""
    sql = _build_metric_breakpoint_query(metric_id)
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
    """Run the per-rating-bucket sanity-check query for ``metric_id``."""
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
            f"≥{INCLUSION_FLOOR_SCORE_GAP_NON_EG} non-endgame games per user."
        )
    if metric_id == "achievable_score_gap":
        return (
            f"achievable_score_gap — inclusion floor "
            f"≥{INCLUSION_FLOOR_ACHIEVABLE} endgame-entry games per user."
        )
    if metric_id == "section2_score_gap_conv":
        return (
            f"section2_score_gap_conv — inclusion floor "
            f"≥{INCLUSION_FLOOR_SECTION2_PER_BUCKET} spans per entry-eval bucket."
        )
    if metric_id == "section2_score_gap_parity":
        return (
            f"section2_score_gap_parity — inclusion floor "
            f"≥{INCLUSION_FLOOR_SECTION2_PER_BUCKET} spans per entry-eval bucket."
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


def _metric_display_name(metric_id: CdfMetricId) -> str:
    """Human-readable metric label for report headings."""
    return {
        "score_gap": "Endgame Score Gap",
        "achievable_score_gap": "Achievable Score Gap",
        "section2_score_gap_conv": "Section 2 Conversion ΔES",
        "section2_score_gap_parity": "Section 2 Parity ΔES",
    }[metric_id]


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


def _emit_report(
    metric_results: dict[CdfMetricId, MetricResult],
    per_bucket_results: dict[CdfMetricId, list[PerBucketRow]],
    snapshot_iso: str,
) -> str:
    """Compose the markdown text of ``reports/global-percentile-cdf-latest.md``."""
    date_str = snapshot_iso[:10]
    header = (
        f"# FlawChess Global Percentile CDF — {date_str}\n\n"
        f"- **DB**: benchmark (Docker on localhost:5433, flawchess_benchmark)\n"
        f"- **Snapshot taken**: {snapshot_iso}\n"
        f"- **Benchmark DB snapshot month**: {BENCHMARK_DB_SNAPSHOT_MONTH}\n"
        f"- **Methodology**: see `.claude/skills/benchmarks/SKILL.md` Chapter 4.\n"
        f"- **Canonical CTE inherited verbatim** from SKILL.md §1 (selected_users + "
        f"checkpoint-status filter + game-time ELO bucketing + sparse-cell "
        f"`({SPARSE_CELL_ELO}, {SPARSE_CELL_TC})` exclusion + universal "
        f"equal-footing opponent filter `|opp - user| ≤ {EQUAL_FOOTING_TOL}`).\n"
        f"- **Breakpoint set**: every integer percentile p1..p99 (99 entries, no "
        f"sub-percent steps). Values rendered in pp (×100, one decimal).\n"
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
            f"- **Sparse cell** `({SPARSE_CELL_ELO}, {SPARSE_CELL_TC})` excluded from the pooled distribution.\n\n"
            f"### Breakpoint table (p1..p99)\n\n"
            f"{_emit_breakpoint_table(bps)}\n\n"
            f"### Per-rating-bucket sanity check\n\n"
            f"{_emit_per_bucket_table(per_bucket)}\n"
        )

    return header + "\n".join(cohort_lines) + "\n\n" + "\n".join(sections)


def _rotate_report(existing_path: Path) -> None:
    """Apply the D-07 rotation rule to ``existing_path`` before overwrite.

    Reads the first-line date header (``# FlawChess Global Percentile CDF — YYYY-MM-DD``)
    and renames the file to ``reports/global-percentile-cdf-{YYYY-MM-DD}.md``. If
    the dated archive already exists, leaves it alone and lets the caller
    overwrite the latest in place (same convention as ``reports/benchmarks-latest.md``).
    """
    if not existing_path.exists():
        return
    first_line = existing_path.read_text().splitlines()[0] if existing_path.stat().st_size else ""
    match = re.search(r"(\d{4}-\d{2}-\d{2})", first_line)
    if not match:
        _log(f"Existing report has no parseable date header; overwriting in place: {first_line!r}")
        return
    archive_date = match.group(1)
    archive_path = existing_path.with_name(f"global-percentile-cdf-{archive_date}.md")
    if archive_path.exists():
        _log(f"Dated archive already exists: {archive_path}; overwriting latest in place.")
        return
    existing_path.rename(archive_path)
    _log(f"Rotated {existing_path} -> {archive_path}")


def _write_report(
    metric_results: dict[CdfMetricId, MetricResult],
    per_bucket_results: dict[CdfMetricId, list[PerBucketRow]],
) -> None:
    """Apply the rotation rule then write the new latest report."""
    OUTPUT_REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    _rotate_report(OUTPUT_REPORT_PATH)
    snapshot_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    OUTPUT_REPORT_PATH.write_text(_emit_report(metric_results, per_bucket_results, snapshot_iso))
    _log(f"Wrote {OUTPUT_REPORT_PATH}")


# ---------------------------------------------------------------------------
# Driver.
# ---------------------------------------------------------------------------


async def run_regen(
    *,
    db: str,
    dry_run: bool,
    report_only: bool,
) -> None:
    """Main driver. Connects to the benchmark DB, runs queries, emits outputs."""
    url = _db_url(db)
    _assert_benchmark_db(url)
    _log(f"Resolved DB URL: {_mask_password(url)}")

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
                _log(f"  [{metric_id}] querying breakpoints + n_users...")
                bps, n_users = await _query_metric_breakpoints(session, metric_id)
                metric_results[metric_id] = (bps, n_users)
                _log(
                    f"  [{metric_id}] n_users={n_users} "
                    f"p1={bps[0]:+.4f} p50={bps[49]:+.4f} p99={bps[-1]:+.4f}"
                )
                if not dry_run:
                    _log(f"  [{metric_id}] querying per-rating-bucket sanity check...")
                    per_bucket_results[metric_id] = await _query_per_bucket_sanity_check(
                        session, metric_id
                    )

        if dry_run:
            _log(f"--dry-run: would write {OUTPUT_MODULE_PATH} and {OUTPUT_REPORT_PATH}")
            return

        if not report_only:
            _write_module(metric_results)
        _write_report(metric_results, per_bucket_results)
    finally:
        await engine.dispose()


def parse_args() -> argparse.Namespace:
    """Parse and validate CLI arguments."""
    parser = argparse.ArgumentParser(
        description=(
            "Regenerate the global empirical-CDF artifact from the benchmark DB. "
            "Mirrors the scripts/backfill_eval.py --db benchmark pattern. "
            "Methodology source-of-truth: .claude/skills/benchmarks/SKILL.md Chapter 4."
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
    _log(f"Starting regen: db={args.db} dry_run={args.dry_run} report_only={args.report_only}")
    await run_regen(db=args.db, dry_run=args.dry_run, report_only=args.report_only)
    _log("Done.")


if __name__ == "__main__":
    asyncio.run(main())
