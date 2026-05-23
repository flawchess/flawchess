"""Canonical-slice CTE builders for Phase 94.1 D-11 / ROADMAP SC-7.

Extraction source: ``scripts/gen_global_percentile_cdf.py:214-509``.

This module provides pure-Python SQL string builders that are consumed by
two independent callers:

1. ``scripts/gen_global_percentile_cdf.py`` — benchmark CDF generation.
   Calls every builder with ``source="benchmark"`` (the pre-extraction
   behaviour, preserved verbatim for byte-identical output).

2. ``app/services/user_benchmark_percentiles_service.py`` (Phase 94.1 Plan 05)
   — per-user canonical-slice compute service. Calls with
   ``source="single_user"``.

Structural differences between the two sources (the ONLY two documented diffs):

* ``selected_users`` CTE shape:

  - ``"benchmark"``: joins ``benchmark_selected_users`` +
    ``benchmark_ingest_checkpoints`` + ``users`` — the full cohort join from
    SKILL.md §1. Columns include ``tc_bucket``, ``selection_rating_bucket``,
    ``median_elo``.

  - ``"single_user"``: ``SELECT :user_id::int AS user_id`` — a scalar
    single-row CTE with a SQLAlchemy bindparam (V5 security mitigation). No
    ``tc_bucket`` column is emitted, because the per-user path pools across
    all time controls (D-09: no per-TC cap).

* Per-TC equality predicate ``g.time_control_bucket::text = su.tc_bucket``:

  - ``"benchmark"``: predicate is **kept** in every rows/spans CTE —
    restricts each benchmark row to its selected-TC bucket.

  - ``"single_user"``: predicate is **dropped** — the canonical slice for a
    single user pools across all TCs (D-09). Dropping it is the only way to
    materialise a single pooled value per metric.

``apply_floor`` dual-mode (resolves RESEARCH Open Q3):

* ``apply_floor=True`` (default): the per-metric ``HAVING`` inclusion-floor
  gate is retained. This is the existing benchmark CDF behaviour — unchanged
  semantics for the benchmark consumer (the byte-identical regression gate
  in ``tests/scripts/test_gen_global_percentile_cdf_unchanged.py`` enforces
  this).

* ``apply_floor=False``: the ``HAVING`` clause is dropped so the CTE emits
  all rows regardless of sample size. Plan 05 uses this branch to store a
  ``value`` with ``percentile=NULL`` for users who are below the inclusion
  floor (CONTEXT.md D-10 / "no row when zero canonical-slice games" rule).

Security note (V5 — T-94.1-06):

All SQL fragments in this module contain STATIC SQL only. The single
user-controlled value, ``user_id``, is embedded as ``:user_id`` — a
SQLAlchemy named bindparam. Callers resolve it at the call site via
``sqlalchemy.text(sql).bindparams(user_id=user_id)``. Never f-string
user-supplied values into the strings returned by this module.
"""

from __future__ import annotations

from typing import Literal

from app.services.global_percentile_cdf import CdfMetricId

# ---------------------------------------------------------------------------
# Module-level constants (CLAUDE.md no-magic-numbers; mirrored from
# scripts/gen_global_percentile_cdf.py lines 58-61).
# ---------------------------------------------------------------------------

# Per-metric inclusion floors (SKILL.md §3.1.5 / §3.1.6 / §3.2.2).
SCORE_GAP_MIN_ENDGAME_N: int = 30
SCORE_GAP_MIN_NON_ENDGAME_N: int = 30
ACHIEVABLE_MIN_GAMES: int = 20
SECTION2_MIN_SPANS_PER_BUCKET: int = 20

# Shared SQL constants (mirrored from gen_global_percentile_cdf.py constants).
_EQUAL_FOOTING_TOL: int = 100
_SPARSE_CELL_ELO: int = 2400
_SPARSE_CELL_TC: str = "classical"
_SUB_800_FLOOR: int = 800


# ---------------------------------------------------------------------------
# Helper: user ELO at game time (internal — not exported; callers embed via
# the exported builders).
# ---------------------------------------------------------------------------


def _user_elo_at_game_expr() -> str:
    """SQL expression for the cohort user's rating at game time (SKILL.md §1)."""
    return "(CASE WHEN g.user_color::text='white' THEN g.white_rating ELSE g.black_rating END)"


# ---------------------------------------------------------------------------
# Exported builders — public API.
# ---------------------------------------------------------------------------


def selected_users_cte(*, source: Literal["benchmark", "single_user"]) -> str:
    """Return the ``selected_users`` CTE block.

    ``source="benchmark"`` → full benchmark cohort JOIN (SKILL.md §1
    Standard CTE, verbatim from
    ``scripts/gen_global_percentile_cdf.py:214-234``).

    ``source="single_user"`` → scalar SELECT with ``:user_id`` bindparam
    (V5 security: never f-string the user_id — it flows through
    SQLAlchemy text().bindparams() at the call site in Plan 05).
    """
    if source == "benchmark":
        return """selected_users AS (
  SELECT u.id AS user_id, bsu.tc_bucket,
         bsu.rating_bucket AS selection_rating_bucket,
         bsu.median_elo
  FROM benchmark_selected_users bsu
  JOIN benchmark_ingest_checkpoints bic
    ON bic.lichess_username = bsu.lichess_username
   AND bic.tc_bucket = bsu.tc_bucket
   AND bic.status = 'completed'
  JOIN users u ON lower(u.lichess_username) = lower(bsu.lichess_username)
)"""
    # single_user: no benchmark tables; :user_id is a SQLAlchemy bindparam
    # resolved at the call site via text(...).bindparams(user_id=user_id).
    # No tc_bucket column — the per-user path pools across all TCs (D-09).
    return "selected_users AS (SELECT :user_id::int AS user_id)"


def elo_bucket_expr(user_elo_alias: str) -> str:
    """SQL CASE WHEN expression to bucket ``user_elo_alias`` into 5 canonical anchors.

    Returns NULL for sub-800 ratings (callers gate with
    ``WHERE user_elo_at_game >= 800``). Verbatim from
    ``scripts/gen_global_percentile_cdf.py:242-254``.
    """
    return (
        f"(CASE WHEN {user_elo_alias} < {_SUB_800_FLOOR} THEN NULL "
        f"WHEN {user_elo_alias} < 1200 THEN 800 "
        f"WHEN {user_elo_alias} < 1600 THEN 1200 "
        f"WHEN {user_elo_alias} < 2000 THEN 1600 "
        f"WHEN {user_elo_alias} < 2400 THEN 2000 "
        f"ELSE 2400 END)"
    )


def equal_footing_filter_sql() -> str:
    """Equal-footing opponent filter clause (SKILL.md §1, universal).

    Verbatim from ``scripts/gen_global_percentile_cdf.py:257-264``.
    """
    return (
        f"abs("
        f"(CASE WHEN g.user_color='white' THEN g.white_rating ELSE g.black_rating END)"
        f" - (CASE WHEN g.user_color='white' THEN g.black_rating ELSE g.white_rating END)"
        f") <= {_EQUAL_FOOTING_TOL}"
    )


def sparse_exclusion_sql(elo_col: str, tc_col: str) -> str:
    """SQL fragment to exclude the sparse ``(2400, classical)`` cell.

    Verbatim from ``scripts/gen_global_percentile_cdf.py:267-269``.
    Column names are SQL identifiers provided by the caller (never user input).
    """
    return f"NOT ({elo_col} = {_SPARSE_CELL_ELO} AND {tc_col} = '{_SPARSE_CELL_TC}')"


def per_user_cte_score_gap(
    *,
    source: Literal["benchmark", "single_user"],
    apply_floor: bool = True,
) -> str:
    """``per_user_values(metric_value, elo_bucket, tc_bucket)`` CTE for ``score_gap``.

    Per-user ``eg_score - non_eg_score`` over the user's endgame and
    non-endgame games (SKILL.md §3.1.6).

    ``apply_floor=True`` (default): HAVING inclusion floor ≥ SCORE_GAP_MIN_*
    is applied — benchmark CDF behaviour, unchanged.
    ``apply_floor=False``: HAVING clause is dropped so below-floor rows are
    emitted; Plan 05 uses this to store ``value`` with ``percentile=NULL``.

    Structural diff vs benchmark: ``source="single_user"`` drops the
    ``g.time_control_bucket::text = su.tc_bucket`` predicate (D-09).
    """
    ueag = _user_elo_at_game_expr()
    elo_bucket = elo_bucket_expr(ueag)
    tc_predicate = (
        "    AND g.time_control_bucket::text = su.tc_bucket\n" if source == "benchmark" else ""
    )
    having_clause = (
        f"  HAVING count(*) FILTER (WHERE has_endgame)     >= {SCORE_GAP_MIN_ENDGAME_N}\n"
        f"     AND count(*) FILTER (WHERE NOT has_endgame) >= {SCORE_GAP_MIN_NON_ENDGAME_N}\n"
        if apply_floor
        else ""
    )
    return f"""endgame_game_ids AS (
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
{tc_predicate}    AND g.white_rating IS NOT NULL AND g.black_rating IS NOT NULL
    AND {equal_footing_filter_sql()}
),
per_user AS (
  SELECT
    user_id, elo_bucket, tc_bucket,
    avg(score) FILTER (WHERE has_endgame)     AS eg_score,
    avg(score) FILTER (WHERE NOT has_endgame) AS non_eg_score
  FROM rows
  WHERE elo_bucket IS NOT NULL
  GROUP BY user_id, elo_bucket, tc_bucket
{having_clause}),
per_user_values AS (
  SELECT (eg_score - non_eg_score) AS metric_value, elo_bucket, tc_bucket
  FROM per_user
  WHERE {sparse_exclusion_sql("elo_bucket", "tc_bucket")}
)""".strip()


def per_user_cte_achievable(
    *,
    source: Literal["benchmark", "single_user"],
    apply_floor: bool = True,
) -> str:
    """``per_user_values`` CTE for ``achievable_score_gap`` (SKILL.md §3.1.5).

    ``apply_floor=True`` (default): HAVING inclusion floor ≥ ACHIEVABLE_MIN_GAMES
    is applied — benchmark CDF behaviour, unchanged.
    ``apply_floor=False``: HAVING clause dropped for below-floor value emit.

    Structural diff vs benchmark: ``source="single_user"`` drops the
    ``g.time_control_bucket::text = su.tc_bucket`` predicate (D-09).
    """
    ueag = _user_elo_at_game_expr()
    elo_bucket = elo_bucket_expr(ueag)
    tc_predicate = (
        "    AND g.time_control_bucket::text = su.tc_bucket\n" if source == "benchmark" else ""
    )
    having_clause = (
        f"  HAVING count(*) FILTER (WHERE d_i IS NOT NULL) >= {ACHIEVABLE_MIN_GAMES}\n"
        if apply_floor
        else ""
    )
    return f"""endgame_game_ids AS (
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
{tc_predicate}    AND g.white_rating IS NOT NULL AND g.black_rating IS NOT NULL
    AND {equal_footing_filter_sql()}
),
per_user AS (
  SELECT user_id, elo_bucket, tc_bucket,
         avg(d_i) AS achievable_gap
  FROM rows
  WHERE elo_bucket IS NOT NULL
  GROUP BY user_id, elo_bucket, tc_bucket
{having_clause}),
per_user_values AS (
  SELECT achievable_gap AS metric_value, elo_bucket, tc_bucket
  FROM per_user
  WHERE achievable_gap IS NOT NULL
    AND {sparse_exclusion_sql(elo_col="elo_bucket", tc_col="tc_bucket")}
)""".strip()


def per_user_cte_section2(
    *,
    bucket_label: Literal["conversion", "parity"],
    source: Literal["benchmark", "single_user"],
    apply_floor: bool = True,
) -> str:
    """``per_user_values`` CTE for ``section2_score_gap_{conv,parity}`` (SKILL.md §3.2.2).

    ``bucket_label`` is ``'conversion'`` or ``'parity'`` — filters spans by
    entry-eval bucket.

    ``apply_floor=True`` (default): HAVING inclusion floor ≥
    SECTION2_MIN_SPANS_PER_BUCKET — benchmark CDF behaviour, unchanged.
    ``apply_floor=False``: HAVING clause dropped for below-floor value emit.

    Structural diff vs benchmark: ``source="single_user"`` drops the
    ``g.time_control_bucket::text = su.tc_bucket`` predicate (D-09).
    """
    ueag = _user_elo_at_game_expr()
    elo_bucket = elo_bucket_expr(ueag)
    tc_predicate = (
        "    AND g.time_control_bucket::text = su.tc_bucket\n" if source == "benchmark" else ""
    )
    having_clause = f"  HAVING count(*) >= {SECTION2_MIN_SPANS_PER_BUCKET}\n" if apply_floor else ""
    return f"""spans AS (
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
{tc_predicate}    AND g.white_rating IS NOT NULL AND g.black_rating IS NOT NULL
    AND {equal_footing_filter_sql()}
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
    AND {ueag} >= {_SUB_800_FLOOR}
),
per_user_bucket AS (
  SELECT user_id, elo_bucket, tc_bucket, bucket,
         avg(gap_span) AS mean_gap
  FROM gap_rows
  WHERE gap_span IS NOT NULL
    AND elo_bucket IS NOT NULL
    AND {sparse_exclusion_sql(elo_col="elo_bucket", tc_col="tc_bucket")}
  GROUP BY user_id, elo_bucket, tc_bucket, bucket
{having_clause}),
per_user_values AS (
  SELECT mean_gap AS metric_value, elo_bucket, tc_bucket
  FROM per_user_bucket
  WHERE bucket = '{bucket_label}'
)""".strip()


def per_user_cte_for(
    metric_id: CdfMetricId,
    *,
    source: Literal["benchmark", "single_user"],
    apply_floor: bool = True,
) -> str:
    """Dispatch to the metric-specific ``per_user_values`` CTE block.

    ``source`` is threaded through to the per-metric builder (selects the
    benchmark cohort vs single-user variant).
    ``apply_floor`` is threaded through to enable/disable the HAVING
    inclusion-floor gate (default True = benchmark CDF behaviour unchanged).
    """
    if metric_id == "score_gap":
        return per_user_cte_score_gap(source=source, apply_floor=apply_floor)
    if metric_id == "achievable_score_gap":
        return per_user_cte_achievable(source=source, apply_floor=apply_floor)
    if metric_id == "section2_score_gap_conv":
        return per_user_cte_section2(
            bucket_label="conversion", source=source, apply_floor=apply_floor
        )
    if metric_id == "section2_score_gap_parity":
        return per_user_cte_section2(bucket_label="parity", source=source, apply_floor=apply_floor)
    raise ValueError(f"Unknown metric_id: {metric_id!r}")
