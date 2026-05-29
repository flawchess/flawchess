"""Pooled-per-user CTE builders for Phase 94.2.

Phase 94.2 (this module's current state) replaces the per-cell stratified
methodology from Phase 94.1 with a *one-point-per-user pooled* model. Each
subject (a cohort user during CDF construction; an app user during per-user
lookup) contributes a single ``metric_value`` and ``n_games`` aggregate to
the output, computed over their recent-3000-per-TC × 36-month game window
pooled across all time controls.

Methodology source-of-truth:
``.planning/notes/per-user-percentile-pooled-redesign.md`` and the locked
decisions in ``.planning/phases/94.2-pooled-per-user-percentile-redesign/
94.2-CONTEXT.md`` (D-1, D-5, D-6, D-8, D-10).

Consumers (call into the same builders to keep the CDF and per-user lookup
structurally aligned — D-10 "drift remains structurally impossible"):

1. ``scripts/gen_global_percentile_cdf.py`` — benchmark CDF generation.
   Calls every builder with ``source="benchmark"`` and a CLI-supplied
   ``snapshot_date`` so the 36-month recency window anchors to the dump
   month (not the operator's clock).

2. ``app/services/user_benchmark_percentiles_service.py`` —
   per-user canonical-slice compute service. Calls with
   ``source="single_user"`` and ``snapshot_date=None`` so the recency
   window anchors to ``NOW()``.

Structural diff between the two sources (the ONLY documented diff):

* ``selected_users`` CTE shape:

  - ``"benchmark"``: deduped cohort. Joins ``benchmark_selected_users``
    grouped by ``lower(lichess_username)`` (one row per username) and
    drops users whose ONLY selection slot is ``(rating_bucket=2400,
    tc_bucket='classical')`` per D-1. Emits ``user_id`` only — downstream
    pooled CTEs no longer need ``tc_bucket`` / ``selection_rating_bucket``
    / ``median_elo`` projections.

  - ``"single_user"``: scalar single-row CTE projecting an explicit
    SQLAlchemy bindparam ``CAST(:user_id AS int)`` (V5 security mitigation).
    The explicit-CAST form is required so SQLAlchemy's ``text()`` tokeniser
    actually detects the parameter (94.1 Plan 09 fix — preserved load-bearing).

Pooled-aggregate shape (identical on both sources, per D-5):

* ``recent_capped``: per-(user, TC) ``ROW_NUMBER() OVER … ORDER BY
  played_at DESC <= 3000`` with the universal filter (rated, non-computer,
  both ratings non-null, equal-footing ±100) and the 36-month recency
  predicate.

* Metric-specific aggregation (endgame/non-endgame split, span derivation,
  bucket gating) over ``recent_capped``.

* ``per_user``: ``GROUP BY user_id`` (no ``elo_bucket`` / ``tc_bucket``
  projection per D-5) with a ``HAVING`` inclusion-floor gate of ≥30 of the
  metric-relevant unit (D-6).

* ``per_user_values``: emits exactly ``(metric_value, n_games)``.
  ``n_games`` is the metric-relevant count on the pooled set per the
  amendment to D-9 (endgame games for ``score_gap``; eval'd entry games
  for ``achievable_score_gap``; bucket spans for ``score_gap_bucket_*``).

Removed in 94.2:

* The ``apply_floor`` dual-mode argument (D-8). Below-floor → CTE emits no
  row → caller stores no row → chip suppressed. The 94.1 ``percentile=NULL +
  value stored`` rationale is moot because the cell-based model that
  motivated it is gone.

* Per-row ``sparse_exclusion_sql`` invocations inside ``per_user_cte_*``
  (D-1). Sparse-cell exclusion is now a cohort-selection concern, applied
  by ``selected_users_cte(source="benchmark")`` only. The helper is still
  exported because ``tests/services/test_canonical_slice_sql.py`` still
  references it for column-substitution coverage.

Security note (V5 — T-94.2-01-01 / T-94.2-01-02):

All SQL fragments contain STATIC SQL plus one bindparam (``:user_id``) and
one Python-formatted ISO date string (``snapshot_date``). The bindparam
seam is preserved verbatim from 94.1. The ``snapshot_date`` parameter is a
build-time ``date | None`` controlled by Plan 02's CLI; Python's
``date.isoformat()`` produces only ``YYYY-MM-DD`` digits, so the f-string
into SQL has no injection vector. Never f-string ``user_id`` here.
"""

from __future__ import annotations

from datetime import date
from typing import Final, Literal, TypeAlias

from app.services.chesscom_to_lichess import CHESSCOM_BLITZ_TO_LICHESS
from app.services.global_percentile_cdf import CdfMetricId

# Per-TC bucket identifier — used by Phase 94.3 per-TC builders so the leading
# positional argument is type-checked (CLAUDE.md type-safety rule per D-8).
TimeControlBucket: TypeAlias = Literal["bullet", "blitz", "rapid", "classical"]

# ---------------------------------------------------------------------------
# Module-level constants (CLAUDE.md no-magic-numbers).
# ---------------------------------------------------------------------------

# Per-metric inclusion floors on the pooled set (D-6 — all 4 metrics ≥30).
SCORE_GAP_MIN_ENDGAME_N: int = 30
SCORE_GAP_MIN_NON_ENDGAME_N: int = 30
ACHIEVABLE_MIN_GAMES: int = 30
SCORE_GAP_BUCKET_MIN_SPANS: int = 30

# Pooled-window shape (D-5).
RECENT_GAMES_PER_TC_CAP: int = 3000
RECENCY_WINDOW_MONTHS: int = 36

# Phase 94.3 per-TC time-pressure builder thresholds (CONTEXT D-6).
# `TIME_PRESSURE_CLOCK_PCT_THRESHOLD` defines the "under time pressure"
# cutoff applied to each side's clock fraction at endgame entry: clock_pct
# < 0.40 = pressured. The remaining three constants are the inclusion
# floors gated via HAVING on the pooled per-user aggregate (≥30 mirrors
# Phase 94.2 D-6 for every other metric in this module).
TIME_PRESSURE_CLOCK_PCT_THRESHOLD: float = 0.40
TIME_PRESSURE_MIN_PRESSURED_N: int = 30
CLOCK_GAP_MIN_POOL_N: int = 30
NET_FLAG_RATE_MIN_POOL_N: int = 30

# Phase 94.4 D-04: per-(user, TC) median rating anchor inclusion floor.
# 30 games is the lower bound for a stable per-TC median on the recent-3000
# pool (CLAUDE.md no-magic-numbers); tighter floors should be planner-tuned
# post-Plan-04 regen report. Used as the default `min_games` in
# `per_user_cte_median_anchor` below.
MEDIAN_ANCHOR_MIN_GAMES: Final[int] = 30

# Shared SQL constants.
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


def _recency_window_sql(snapshot_date: date | None) -> str:
    """Render the lower bound of the 36-month recency window.

    ``None`` → ``NOW() - INTERVAL '36 months'`` (per-user lookup path, anchored
    at the caller's clock).
    Explicit ``date`` → ``DATE 'YYYY-MM-DD' - INTERVAL '36 months'`` (CDF
    construction path, anchored at the benchmark DB snapshot month so the
    window does not slide with the operator's clock).

    Security note (T-94.2-01-02): ``snapshot_date.isoformat()`` emits only
    digits and dashes — no SQL-injection surface. Use this rendering instead
    of a SQLAlchemy bindparam because the snapshot date is a build-time
    artifact, not user input (consistent with how ``BENCHMARK_DB_SNAPSHOT_MONTH``
    is f-stringed into SQL by ``scripts/gen_global_percentile_cdf.py``).
    """
    if snapshot_date is None:
        return f"NOW() - INTERVAL '{RECENCY_WINDOW_MONTHS} months'"
    return f"DATE '{snapshot_date.isoformat()}' - INTERVAL '{RECENCY_WINDOW_MONTHS} months'"


# ---------------------------------------------------------------------------
# Exported builders — public API.
# ---------------------------------------------------------------------------


def selected_users_cte(*, source: Literal["benchmark", "single_user"]) -> str:
    """Return the ``selected_users`` CTE block.

    ``source="benchmark"`` → deduped cohort (D-1). Groups
    ``benchmark_selected_users`` by ``lower(lichess_username)`` and keeps
    only usernames that have at least one non-``(2400, classical)``
    selection slot. Joins to ``users`` for the surrogate ``user_id`` the
    pooled aggregates need.

    ``source="single_user"`` → scalar SELECT with ``CAST(:user_id AS int)``
    bindparam (V5 — load-bearing per 94.1 Plan 09 fix).
    """
    if source == "benchmark":
        return f"""selected_users AS (
  SELECT u.id AS user_id
  FROM users u
  JOIN (
    SELECT lower(bsu.lichess_username) AS lname
    FROM benchmark_selected_users bsu
    JOIN benchmark_ingest_checkpoints bic
      ON bic.lichess_username = bsu.lichess_username
     AND bic.tc_bucket = bsu.tc_bucket
     AND bic.status = 'completed'
    GROUP BY lower(bsu.lichess_username)
    HAVING bool_or(NOT (bsu.rating_bucket = {_SPARSE_CELL_ELO} AND bsu.tc_bucket = '{_SPARSE_CELL_TC}'))
  ) deduped ON lower(u.lichess_username) = deduped.lname
)"""
    # single_user: scalar bindparam; pools across all TCs (D-5). The explicit
    # CAST() form is load-bearing — see 94.1 Plan 09 — SQLAlchemy's text()
    # tokeniser silently drops `:user_id::int` and raises ArgumentError at
    # .bindparams() time. CAST(:user_id AS int) is parsed correctly.
    return "selected_users AS (SELECT CAST(:user_id AS int) AS user_id)"


def elo_bucket_expr(user_elo_alias: str) -> str:
    """SQL CASE WHEN expression to bucket ``user_elo_alias`` into 5 canonical anchors.

    Returns NULL for sub-800 ratings (callers gate with
    ``WHERE user_elo_at_game >= 800``).

    Retained for ``scripts/gen_global_percentile_cdf.py:_build_per_bucket_sanity_query``
    (a diagnostic over the per-cell shape) and tests; NOT invoked by the
    pooled ``per_user_cte_*`` builders.
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

    Used in every pooled per-user CTE prelude.
    """
    return (
        f"abs("
        f"(CASE WHEN g.user_color='white' THEN g.white_rating ELSE g.black_rating END)"
        f" - (CASE WHEN g.user_color='white' THEN g.black_rating ELSE g.white_rating END)"
        f") <= {_EQUAL_FOOTING_TOL}"
    )


# D-1: NO LONGER invoked in per_user_cte_*; retained for the per-bucket sanity
# diagnostic and the column-substitution test reference. Sparse-cell exclusion
# under the pooled methodology lives in selected_users_cte("benchmark") only.
def sparse_exclusion_sql(elo_col: str, tc_col: str) -> str:
    """SQL fragment to exclude the sparse ``(2400, classical)`` cell.

    Retained for ``_build_per_bucket_sanity_query`` (a per-cell diagnostic
    in the regen report) and for ``tests/services/test_canonical_slice_sql.py
    ::test_sparse_exclusion_sql_parametrises_columns``.

    Column names are SQL identifiers provided by the caller (never user input).
    """
    return f"NOT ({elo_col} = {_SPARSE_CELL_ELO} AND {tc_col} = '{_SPARSE_CELL_TC}')"


# ---------------------------------------------------------------------------
# Pooled per-user CTE builders (D-5 / D-6 / D-8).
# ---------------------------------------------------------------------------


def _recent_capped_cte(snapshot_date: date | None) -> str:
    """Shared ``recent_capped`` CTE — recent-3000-per-TC + 36-month window.

    Identical on benchmark and single_user paths (the per-TC predicate goes
    away on BOTH sources per D-5). The cohort difference lives entirely
    inside ``selected_users``.
    """
    recency = _recency_window_sql(snapshot_date)
    return f"""recent_capped AS (
  SELECT g.id, g.user_id, g.user_color, g.result, g.played_at
  FROM (
    SELECT g.*,
           row_number() OVER (PARTITION BY g.user_id, g.time_control_bucket
                              ORDER BY g.played_at DESC) AS rn
    FROM games g
    JOIN selected_users su ON su.user_id = g.user_id
    WHERE g.rated AND NOT g.is_computer_game
      AND g.white_rating IS NOT NULL AND g.black_rating IS NOT NULL
      AND g.played_at >= {recency}
      AND {equal_footing_filter_sql()}
  ) g
  WHERE g.rn <= {RECENT_GAMES_PER_TC_CAP}
)"""


def _recent_capped_per_tc_cte(snapshot_date: date | None, tc: TimeControlBucket) -> str:
    """Phase 94.3 per-TC sibling of ``_recent_capped_cte`` (PATTERNS.md lines 120-147).

    Restricts the canonical slice to a single ``time_control_bucket`` so the
    per-TC percentile chips can be computed against a per-TC pooled set.

    Two structural differences from ``_recent_capped_cte``:

    1. ``AND g.time_control_bucket = '{tc}'`` is added to the inner WHERE.
       Safe to f-string because ``tc`` is constrained to four literal values
       by ``TimeControlBucket``; no SQL-injection vector.
    2. ``ROW_NUMBER() OVER (PARTITION BY g.user_id ...)`` — the per-(user, TC)
       partition collapses to per-user because the inner set is already
       restricted to one TC. The 3000-cap then means "most recent 3000 games
       of this TC per user" (RESEARCH §Pattern 1).
    """
    recency = _recency_window_sql(snapshot_date)
    return f"""recent_capped AS (
  SELECT g.id, g.user_id, g.user_color, g.result, g.played_at
  FROM (
    SELECT g.*,
           row_number() OVER (PARTITION BY g.user_id
                              ORDER BY g.played_at DESC) AS rn
    FROM games g
    JOIN selected_users su ON su.user_id = g.user_id
    WHERE g.rated AND NOT g.is_computer_game
      AND g.white_rating IS NOT NULL AND g.black_rating IS NOT NULL
      AND g.played_at >= {recency}
      AND {equal_footing_filter_sql()}
      AND g.time_control_bucket = '{tc}'
  ) g
  WHERE g.rn <= {RECENT_GAMES_PER_TC_CAP}
)"""


def per_user_cte_score_gap(
    *,
    source: Literal["benchmark", "single_user"],
    snapshot_date: date | None = None,
) -> str:
    """Pooled ``per_user_values(metric_value, n_games)`` CTE for ``score_gap``.

    ``metric_value`` = ``eg_score - non_eg_score`` over the user's pooled
    36-month / 3000-per-TC window. ``n_games`` = endgame-game count on the
    pooled set (the binding floor per CONTEXT.md "Claude's Discretion —
    n_games"; the paired non-endgame count goes in the backfill summary
    log, not the row).

    HAVING gates on BOTH ``count(*) FILTER (WHERE has_endgame) >= 30`` and
    ``count(*) FILTER (WHERE NOT has_endgame) >= 30`` per D-6. Below-floor
    users contribute no row.

    No per-TC predicate, no per-row sparse-cell exclusion (D-1, D-5).
    ``source`` parameter is accepted for API symmetry with the cohort CTE
    but does not alter the pooled SQL body — the cohort difference lives
    entirely in ``selected_users``.
    """
    _ = source  # cohort difference is in selected_users_cte; pooled body is identical
    return f"""{_recent_capped_cte(snapshot_date)},
endgame_game_ids AS (
  SELECT game_id FROM game_positions
  WHERE endgame_class IS NOT NULL
  GROUP BY game_id HAVING count(*) >= 6
),
scored AS (
  SELECT
    rc.user_id,
    CASE
      WHEN (rc.result = '1-0' AND rc.user_color = 'white')
        OR (rc.result = '0-1' AND rc.user_color = 'black') THEN 1.0
      WHEN rc.result = '1/2-1/2' THEN 0.5
      ELSE 0.0
    END AS score,
    (eg.game_id IS NOT NULL) AS has_endgame
  FROM recent_capped rc
  LEFT JOIN endgame_game_ids eg ON eg.game_id = rc.id
),
per_user AS (
  SELECT
    user_id,
    avg(score) FILTER (WHERE has_endgame)     AS eg_score,
    avg(score) FILTER (WHERE NOT has_endgame) AS non_eg_score,
    count(*)   FILTER (WHERE has_endgame)     AS eg_n
  FROM scored
  GROUP BY user_id
  HAVING count(*) FILTER (WHERE has_endgame)     >= {SCORE_GAP_MIN_ENDGAME_N}
     AND count(*) FILTER (WHERE NOT has_endgame) >= {SCORE_GAP_MIN_NON_ENDGAME_N}
),
per_user_values AS (
  SELECT
    (eg_score - non_eg_score) AS metric_value,
    eg_n AS n_games
  FROM per_user
)"""


def per_user_cte_achievable(
    *,
    source: Literal["benchmark", "single_user"],
    snapshot_date: date | None = None,
) -> str:
    """Pooled ``per_user_values(metric_value, n_games)`` CTE for ``achievable_score_gap``.

    ``metric_value`` = ``avg(d_i)`` over endgame-entry rows with non-null
    ``d_i`` (the score-vs-Lichess-sigmoid gap at endgame entry).
    ``n_games`` = count of endgame-entry games with non-null ``d_i`` (the
    binding floor per D-6).

    HAVING ≥30 on ``count(*) FILTER (WHERE d_i IS NOT NULL)`` per D-6.

    No per-TC predicate, no per-row sparse-cell exclusion (D-1, D-5).
    """
    _ = source  # cohort difference is in selected_users_cte; pooled body is identical
    return f"""{_recent_capped_cte(snapshot_date)},
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
scored AS (
  SELECT
    rc.user_id,
    (
      CASE
        WHEN (rc.result = '1-0' AND rc.user_color = 'white')
          OR (rc.result = '0-1' AND rc.user_color = 'black') THEN 1.0
        WHEN rc.result = '1/2-1/2' THEN 0.5
        ELSE 0.0
      END
      -
      CASE
        WHEN er.eval_mate IS NOT NULL AND
             (er.eval_mate * (CASE WHEN rc.user_color='white' THEN 1 ELSE -1 END)) > 0 THEN 1.0
        WHEN er.eval_mate IS NOT NULL AND
             (er.eval_mate * (CASE WHEN rc.user_color='white' THEN 1 ELSE -1 END)) < 0 THEN 0.0
        WHEN er.eval_cp IS NOT NULL AND abs(er.eval_cp) < 2000
             THEN 1.0 / (1.0 + exp(-0.00368208 *
                  (er.eval_cp * (CASE WHEN rc.user_color='white' THEN 1 ELSE -1 END))))
        ELSE NULL
      END
    ) AS d_i
  FROM recent_capped rc
  JOIN entry_rows er ON er.game_id = rc.id AND er.rn = 1
),
per_user AS (
  SELECT
    user_id,
    avg(d_i) AS achievable_gap,
    count(*) FILTER (WHERE d_i IS NOT NULL) AS di_n
  FROM scored
  GROUP BY user_id
  HAVING count(*) FILTER (WHERE d_i IS NOT NULL) >= {ACHIEVABLE_MIN_GAMES}
),
per_user_values AS (
  SELECT
    achievable_gap AS metric_value,
    di_n AS n_games
  FROM per_user
  WHERE achievable_gap IS NOT NULL
)"""


def per_user_cte_score_gap_bucket(
    *,
    bucket_label: Literal["conversion", "parity", "recovery"],
    source: Literal["benchmark", "single_user"],
    snapshot_date: date | None = None,
) -> str:
    """Pooled ``per_user_values(metric_value, n_games)`` CTE for ``score_gap_{conv,parity,recovery}``.

    ``bucket_label`` filters spans by entry-eval bucket:
    - ``'conversion'`` — user up material at endgame entry
      (entry_eval_cp * user_color_sign >= 100, or entry_eval_mate > 0 signed).
    - ``'parity'`` — equal at entry (|entry_eval_cp * sign| < 100,
      or entry_eval_mate IS NULL AND entry_eval_cp IS NULL).
    - ``'recovery'`` — user down material at entry
      (entry_eval_cp * user_color_sign <= -100, or entry_eval_mate < 0 signed).
      Added in Phase 94.4 Plan 03 Task 2 per RESEARCH Open Question 3 — the
      widening is purely at the Literal type level + the bucket WHERE dispatch.
      The existing ``gap_rows`` CASE classification (below) already emits
      ``'recovery'`` rows; the WHERE clause in ``per_user_values`` simply
      selects them when ``bucket_label='recovery'``.

    ``metric_value`` = per-user ``avg(gap_span)`` on spans in the selected
    bucket. ``n_games`` = span count in the selected bucket (the binding
    floor per D-6).

    HAVING ≥30 on ``count(*)`` inside the per-user/per-bucket aggregation
    per D-6.

    The ``>= _SUB_800_FLOOR`` user-rating gate inside ``gap_rows`` is kept —
    it defends against missing rating data, independent of any bucketing
    scheme.

    No per-TC predicate, no per-row sparse-cell exclusion (D-1, D-5).
    """
    _ = source  # cohort difference is in selected_users_cte; pooled body is identical
    ueag = _user_elo_at_game_expr()
    return f"""{_recent_capped_cte(snapshot_date)},
spans AS (
  SELECT
    gp.game_id, gp.endgame_class,
    (array_agg(gp.eval_cp   ORDER BY gp.ply ASC))[1] AS entry_eval_cp,
    (array_agg(gp.eval_mate ORDER BY gp.ply ASC))[1] AS entry_eval_mate,
    min(gp.ply) AS span_min_ply
  FROM game_positions gp
  JOIN recent_capped rc ON rc.id = gp.game_id
  WHERE gp.endgame_class IS NOT NULL
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
  JOIN games g ON g.id = swn.game_id
  WHERE (swn.entry_eval_cp IS NOT NULL OR swn.entry_eval_mate IS NOT NULL)
    AND {ueag} >= {_SUB_800_FLOOR}
),
per_user_bucket AS (
  SELECT user_id, bucket,
         avg(gap_span) AS mean_gap,
         count(*) AS span_n
  FROM gap_rows
  WHERE gap_span IS NOT NULL
  GROUP BY user_id, bucket
  HAVING count(*) >= {SCORE_GAP_BUCKET_MIN_SPANS}
),
per_user_values AS (
  SELECT
    mean_gap AS metric_value,
    span_n AS n_games
  FROM per_user_bucket
  WHERE bucket = '{bucket_label}'
)"""


def _endgame_entry_clocks_cte() -> str:
    """Per-game endgame-entry clock derivation for the three Phase 94.3 per-TC builders.

    Mirrors the Python ``_extract_entry_clocks`` logic (``app/services/endgame_service.py``
    lines 1626-1647): for each game that reached an endgame phase (≥6 endgame
    plies under the whole-game rule, quick-260414-pv4), aggregate the first
    non-null ``clock_seconds`` per ply parity:

    - white_entry_clock = first non-null clock at an even ply (white just moved)
    - black_entry_clock = first non-null clock at an odd ply (black just moved)

    The user/opp assignment then collapses by ``rc.user_color`` in the
    consumer's ``joined`` CTE. Centralised here because all three Phase 94.3
    per-TC builders need the identical derivation.

    All three callers prepend ``_recent_capped_per_tc_cte`` immediately before
    this CTE in the WITH chain, so ``recent_capped`` is always in scope.
    Scoping to ``recent_capped`` is result-equivalent: only games whose id
    appears in ``recent_capped`` survive the downstream ``joined`` CTE join
    (``joined JOIN endgame_entry_clocks ee ON ee.game_id = rc.id``). The per-game
    ``HAVING count(gp.ply) >= 6`` is unaffected by game_id membership filtering
    because it counts rows within each retained game, not across games.
    """
    return """endgame_entry_clocks AS (
  SELECT
    gp.game_id,
    (array_agg(gp.clock_seconds ORDER BY gp.ply ASC)
       FILTER (WHERE gp.clock_seconds IS NOT NULL AND gp.ply % 2 = 0))[1] AS white_entry_clock,
    (array_agg(gp.clock_seconds ORDER BY gp.ply ASC)
       FILTER (WHERE gp.clock_seconds IS NOT NULL AND gp.ply % 2 = 1))[1] AS black_entry_clock
  -- recent_capped is always prepended by all 3 callers (_recent_capped_per_tc_cte);
  -- JOIN scopes to the selected user's games only (result-equivalent: only recent_capped
  -- games survive the downstream joined CTE anyway).
  FROM game_positions gp JOIN recent_capped rc ON rc.id = gp.game_id
  WHERE gp.endgame_class IS NOT NULL
  GROUP BY gp.game_id
  HAVING count(gp.ply) >= 6
)"""


def per_user_cte_time_pressure_score_gap(
    tc: TimeControlBucket,
    *,
    source: Literal["benchmark", "single_user"],
    snapshot_date: date | None = None,
) -> str:
    """Pooled ``per_user_values(metric_value, n_games)`` for ``time_pressure_score_gap_{tc}``.

    Per-TC version of the SEED-025 / D-6 time-pressure score gap. Restricted
    to one ``time_control_bucket`` via ``_recent_capped_per_tc_cte`` and gated
    on a *dual* ≥30 floor: both ≥30 endgame-entry games where the USER hit
    clock_pct < 0.40 AND ≥30 endgame-entry games where the OPPONENT hit
    clock_pct < 0.40.

    ``metric_value`` = ``user_pressured_score - opp_pressured_score`` where
    each side's "pressured score" is the average user-side game score on the
    cell whose clock dropped below the 0.40 threshold (opponent score is
    mirrored via ``1.0 - user_score``).

    ``n_games`` = ``least(user_pressured_n, opp_pressured_n)`` — the binding
    floor on the dual-HAVING gate.

    No per-row sparse-cell exclusion (D-1); cohort dedup lives in
    ``selected_users_cte("benchmark")``. ``source`` is accepted for API
    symmetry but does not alter the pooled body (D-10).

    Security: ``tc`` is constrained to a 4-value ``Literal`` so the f-string
    interpolation has no injection vector; ``snapshot_date.isoformat()``
    emits only digits and dashes. Bindparams are confined to ``:user_id``
    inside ``selected_users_cte("single_user")``.
    """
    _ = source  # cohort difference is in selected_users_cte; pooled body is identical
    return f"""{_recent_capped_per_tc_cte(snapshot_date, tc)},
{_endgame_entry_clocks_cte()},
joined AS (
  SELECT
    rc.user_id,
    rc.user_color,
    rc.result,
    g.base_time_seconds,
    CASE WHEN rc.user_color = 'white' THEN ee.white_entry_clock
         ELSE ee.black_entry_clock END::float
      / NULLIF(g.base_time_seconds, 0) AS user_clock_pct,
    CASE WHEN rc.user_color = 'white' THEN ee.black_entry_clock
         ELSE ee.white_entry_clock END::float
      / NULLIF(g.base_time_seconds, 0) AS opp_clock_pct,
    CASE
      WHEN (rc.result='1-0' AND rc.user_color='white')
        OR (rc.result='0-1' AND rc.user_color='black') THEN 1.0
      WHEN rc.result='1/2-1/2' THEN 0.5
      ELSE 0.0
    END AS user_score
  FROM recent_capped rc
  JOIN games g ON g.id = rc.id
  JOIN endgame_entry_clocks ee ON ee.game_id = rc.id
  WHERE g.base_time_seconds IS NOT NULL AND g.base_time_seconds > 0
),
per_user AS (
  SELECT
    user_id,
    avg(user_score)
      FILTER (WHERE user_clock_pct < {TIME_PRESSURE_CLOCK_PCT_THRESHOLD:.2f}) AS user_pressured_score,
    avg(1.0 - user_score)
      FILTER (WHERE opp_clock_pct < {TIME_PRESSURE_CLOCK_PCT_THRESHOLD:.2f}) AS opp_pressured_score,
    count(*)
      FILTER (WHERE user_clock_pct < {TIME_PRESSURE_CLOCK_PCT_THRESHOLD:.2f}) AS user_pressured_n,
    count(*)
      FILTER (WHERE opp_clock_pct < {TIME_PRESSURE_CLOCK_PCT_THRESHOLD:.2f}) AS opp_pressured_n
  FROM joined
  WHERE user_clock_pct IS NOT NULL AND opp_clock_pct IS NOT NULL
  GROUP BY user_id
  HAVING count(*) FILTER (WHERE user_clock_pct < {TIME_PRESSURE_CLOCK_PCT_THRESHOLD:.2f}) >= {TIME_PRESSURE_MIN_PRESSURED_N}
     AND count(*) FILTER (WHERE opp_clock_pct < {TIME_PRESSURE_CLOCK_PCT_THRESHOLD:.2f}) >= {TIME_PRESSURE_MIN_PRESSURED_N}
),
per_user_values AS (
  -- user_id widened per Phase 94.4 Pitfall 1 (cohort-CDF JOIN against per_user_anchor).
  SELECT
    user_id,
    (user_pressured_score - opp_pressured_score) AS metric_value,
    least(user_pressured_n, opp_pressured_n)::int AS n_games
  FROM per_user
)"""


def per_user_cte_clock_gap(
    tc: TimeControlBucket,
    *,
    source: Literal["benchmark", "single_user"],
    snapshot_date: date | None = None,
) -> str:
    """Pooled ``per_user_values(metric_value, n_games)`` for ``clock_gap_{tc}``.

    Per-game endgame-entry clock advantage as a fraction of the base clock:
    ``(user_clock - opp_clock) / base_time_seconds`` averaged across the
    user's per-TC pooled endgame-entry games.

    ``metric_value`` = ``avg((user_clock - opp_clock) / base_time_seconds)``
    over endgame-entry games in the restricted TC.
    ``n_games`` = pooled-set count (the binding floor per ``CLOCK_GAP_MIN_POOL_N``).

    No per-row sparse-cell exclusion (D-1); cohort dedup lives in
    ``selected_users_cte("benchmark")``. ``source`` is accepted for API
    symmetry but does not alter the pooled body (D-10).
    """
    _ = source  # cohort difference is in selected_users_cte; pooled body is identical
    return f"""{_recent_capped_per_tc_cte(snapshot_date, tc)},
{_endgame_entry_clocks_cte()},
joined AS (
  SELECT
    rc.user_id,
    (
      (CASE WHEN rc.user_color = 'white' THEN ee.white_entry_clock
            ELSE ee.black_entry_clock END)
      - (CASE WHEN rc.user_color = 'white' THEN ee.black_entry_clock
              ELSE ee.white_entry_clock END)
    )::float / NULLIF(g.base_time_seconds, 0) AS clock_gap_frac
  FROM recent_capped rc
  JOIN games g ON g.id = rc.id
  JOIN endgame_entry_clocks ee ON ee.game_id = rc.id
  WHERE g.base_time_seconds IS NOT NULL AND g.base_time_seconds > 0
    AND ee.white_entry_clock IS NOT NULL
    AND ee.black_entry_clock IS NOT NULL
),
per_user AS (
  SELECT
    user_id,
    avg(clock_gap_frac) AS clock_gap_frac_avg,
    count(*) AS pool_n
  FROM joined
  WHERE clock_gap_frac IS NOT NULL
  GROUP BY user_id
  HAVING count(*) >= {CLOCK_GAP_MIN_POOL_N}
),
per_user_values AS (
  -- user_id widened per Phase 94.4 Pitfall 1 (cohort-CDF JOIN against per_user_anchor).
  SELECT
    user_id,
    clock_gap_frac_avg AS metric_value,
    pool_n AS n_games
  FROM per_user
)"""


def per_user_cte_net_flag_rate(
    tc: TimeControlBucket,
    *,
    source: Literal["benchmark", "single_user"],
    snapshot_date: date | None = None,
) -> str:
    """Pooled ``per_user_values(metric_value, n_games)`` for ``net_flag_rate_{tc}``.

    Per-game timeout-outcome rate on endgame-entry games in the restricted TC.
    A user "wins on time" when the opponent flagged (``termination='timeout'``
    and user is the winner); a user "loses on time" when the user flagged.

    ``metric_value`` = ``(timeout_wins - timeout_losses) / total_endgame_games``
    averaged per user; mirrors the existing ``net_timeout_rate`` field on
    ``TimePressureTcCard`` (``app/services/endgame_service.py`` lines 1941-1956).
    ``n_games`` = pooled endgame-entry count (the binding floor per
    ``NET_FLAG_RATE_MIN_POOL_N``).

    Verified column: ``games.termination`` is an ENUM whose time-forfeit value
    is the string literal ``'timeout'`` (per 94.3-01 SUMMARY "Verified column
    names"; NOT ``'time forfeit'`` as the RESEARCH sketch suggested).

    No per-row sparse-cell exclusion (D-1); cohort dedup lives in
    ``selected_users_cte("benchmark")``. ``source`` is accepted for API
    symmetry but does not alter the pooled body (D-10).
    """
    _ = source  # cohort difference is in selected_users_cte; pooled body is identical
    return f"""{_recent_capped_per_tc_cte(snapshot_date, tc)},
{_endgame_entry_clocks_cte()},
joined AS (
  SELECT
    rc.user_id,
    g.termination,
    CASE
      WHEN (rc.result='1-0' AND rc.user_color='white')
        OR (rc.result='0-1' AND rc.user_color='black') THEN 'win'
      WHEN rc.result='1/2-1/2' THEN 'draw'
      ELSE 'loss'
    END AS user_outcome
  FROM recent_capped rc
  JOIN games g ON g.id = rc.id
  JOIN endgame_entry_clocks ee ON ee.game_id = rc.id
),
per_user AS (
  SELECT
    user_id,
    (
      count(*) FILTER (WHERE termination::text = 'timeout' AND user_outcome = 'win')::float
      - count(*) FILTER (WHERE termination::text = 'timeout' AND user_outcome = 'loss')::float
    ) / NULLIF(count(*), 0) AS net_flag_rate,
    count(*) AS pool_n
  FROM joined
  GROUP BY user_id
  HAVING count(*) >= {NET_FLAG_RATE_MIN_POOL_N}
),
per_user_values AS (
  -- user_id widened per Phase 94.4 Pitfall 1 (cohort-CDF JOIN against per_user_anchor).
  SELECT
    user_id,
    net_flag_rate AS metric_value,
    pool_n AS n_games
  FROM per_user
)"""


# ---------------------------------------------------------------------------
# Phase 94.4 Plan 03 Task 2 — 4 new per-TC ΔES builders.
#
# These mirror the Phase 94.3 per-TC builder pattern (above) for the 4
# page-level ΔES metric families previously only available pooled across
# all TCs. The cohort CDF (Plan 04) builds at (metric, anchor, tc) granularity
# so every metric family must be available per-TC.
#
# All 4 new builders project user_id in per_user_values (Pitfall 1 — the
# cohort-CDF JOIN against per_user_anchor needs user identity).
# ---------------------------------------------------------------------------


def per_user_cte_score_gap_tc(
    tc: TimeControlBucket,
    *,
    source: Literal["benchmark", "single_user"],
    snapshot_date: date | None = None,
) -> str:
    """Per-TC pooled ``per_user_values(user_id, metric_value, n_games)`` for ``score_gap``.

    Per-TC version of ``per_user_cte_score_gap``. Restricted to one
    ``time_control_bucket`` via ``_recent_capped_per_tc_cte``. The metric_value
    formula and HAVING gates are byte-identical to the non-per-TC analog
    (``eg_score - non_eg_score`` projection; dual ≥30 floor on
    endgame / non-endgame game counts).

    ``n_games`` = endgame-game count on the per-TC pooled set.

    Security: ``tc`` is constrained to a 4-value ``Literal`` so the f-string
    interpolation has no injection vector (the closed value set is enforced
    by ty at every call site). ``snapshot_date.isoformat()`` emits only
    digits and dashes via ``_recency_window_sql``. Bindparams are confined
    to ``:user_id`` inside ``selected_users_cte("single_user")``.

    Source-mode parity (D-10): the pooled body is byte-identical between
    ``source='benchmark'`` and ``source='single_user'``. The cohort
    difference lives entirely inside ``selected_users_cte``.

    Pitfall 1 (RESEARCH lines 1168-1177): ``per_user_values`` projects
    ``user_id`` so the cohort-CDF JOIN (Plan 04) against ``per_user_anchor``
    can locate users by ID.
    """
    _ = source  # cohort difference is in selected_users_cte; pooled body is identical
    return f"""{_recent_capped_per_tc_cte(snapshot_date, tc)},
endgame_game_ids AS (
  -- Scoped to recent_capped (result-equivalent): only recent_capped games survive the
  -- downstream scored LEFT JOIN anyway. HAVING count(*) >= 6 counts rows within each
  -- retained game, so membership filtering does not alter the count or retained set.
  SELECT game_id FROM game_positions
  WHERE endgame_class IS NOT NULL AND game_id IN (SELECT id FROM recent_capped)
  GROUP BY game_id HAVING count(*) >= 6
),
scored AS (
  SELECT
    rc.user_id,
    CASE
      WHEN (rc.result = '1-0' AND rc.user_color = 'white')
        OR (rc.result = '0-1' AND rc.user_color = 'black') THEN 1.0
      WHEN rc.result = '1/2-1/2' THEN 0.5
      ELSE 0.0
    END AS score,
    (eg.game_id IS NOT NULL) AS has_endgame
  FROM recent_capped rc
  LEFT JOIN endgame_game_ids eg ON eg.game_id = rc.id
),
per_user AS (
  SELECT
    user_id,
    avg(score) FILTER (WHERE has_endgame)     AS eg_score,
    avg(score) FILTER (WHERE NOT has_endgame) AS non_eg_score,
    count(*)   FILTER (WHERE has_endgame)     AS eg_n
  FROM scored
  GROUP BY user_id
  HAVING count(*) FILTER (WHERE has_endgame)     >= {SCORE_GAP_MIN_ENDGAME_N}
     AND count(*) FILTER (WHERE NOT has_endgame) >= {SCORE_GAP_MIN_NON_ENDGAME_N}
),
per_user_values AS (
  -- user_id widened per Phase 94.4 Pitfall 1 (cohort-CDF JOIN against per_user_anchor).
  SELECT
    user_id,
    (eg_score - non_eg_score) AS metric_value,
    eg_n AS n_games
  FROM per_user
)"""


def per_user_cte_achievable_tc(
    tc: TimeControlBucket,
    *,
    source: Literal["benchmark", "single_user"],
    snapshot_date: date | None = None,
) -> str:
    """Per-TC pooled ``per_user_values(user_id, metric_value, n_games)`` for ``achievable_score_gap``.

    Per-TC version of ``per_user_cte_achievable``. Restricted to one
    ``time_control_bucket`` via ``_recent_capped_per_tc_cte``. The metric_value
    formula (``avg(d_i)`` where d_i is the per-game score-vs-Lichess-sigmoid
    gap at endgame entry) and HAVING gate (≥30 d_i-non-null games per D-6)
    are byte-identical to the non-per-TC analog.

    Security and source-mode parity identical to ``per_user_cte_score_gap_tc``.
    Pitfall 1 user_id widening applied.
    """
    _ = source  # cohort difference is in selected_users_cte; pooled body is identical
    return f"""{_recent_capped_per_tc_cte(snapshot_date, tc)},
endgame_game_ids AS (
  -- Scoped to recent_capped (result-equivalent): only recent_capped games survive the
  -- downstream scored JOIN (via entry_rows JOIN endgame_game_ids then rc.id = rc.id).
  -- entry_rows inherits the scoping automatically via its JOIN on endgame_game_ids.
  -- HAVING count(*) >= 6 counts rows within each retained game; membership filtering
  -- does not alter the per-game count or the retained game set.
  SELECT game_id FROM game_positions
  WHERE endgame_class IS NOT NULL AND game_id IN (SELECT id FROM recent_capped)
  GROUP BY game_id HAVING count(*) >= 6
),
entry_rows AS (
  SELECT gp.game_id, gp.eval_cp, gp.eval_mate,
         ROW_NUMBER() OVER (PARTITION BY gp.game_id ORDER BY gp.ply ASC) AS rn
  FROM game_positions gp
  JOIN endgame_game_ids eg ON eg.game_id = gp.game_id
  WHERE gp.endgame_class IS NOT NULL
),
scored AS (
  SELECT
    rc.user_id,
    (
      CASE
        WHEN (rc.result = '1-0' AND rc.user_color = 'white')
          OR (rc.result = '0-1' AND rc.user_color = 'black') THEN 1.0
        WHEN rc.result = '1/2-1/2' THEN 0.5
        ELSE 0.0
      END
      -
      CASE
        WHEN er.eval_mate IS NOT NULL AND
             (er.eval_mate * (CASE WHEN rc.user_color='white' THEN 1 ELSE -1 END)) > 0 THEN 1.0
        WHEN er.eval_mate IS NOT NULL AND
             (er.eval_mate * (CASE WHEN rc.user_color='white' THEN 1 ELSE -1 END)) < 0 THEN 0.0
        WHEN er.eval_cp IS NOT NULL AND abs(er.eval_cp) < 2000
             THEN 1.0 / (1.0 + exp(-0.00368208 *
                  (er.eval_cp * (CASE WHEN rc.user_color='white' THEN 1 ELSE -1 END))))
        ELSE NULL
      END
    ) AS d_i
  FROM recent_capped rc
  JOIN entry_rows er ON er.game_id = rc.id AND er.rn = 1
),
per_user AS (
  SELECT
    user_id,
    avg(d_i) AS achievable_gap,
    count(*) FILTER (WHERE d_i IS NOT NULL) AS di_n
  FROM scored
  GROUP BY user_id
  HAVING count(*) FILTER (WHERE d_i IS NOT NULL) >= {ACHIEVABLE_MIN_GAMES}
),
per_user_values AS (
  -- user_id widened per Phase 94.4 Pitfall 1 (cohort-CDF JOIN against per_user_anchor).
  SELECT
    user_id,
    achievable_gap AS metric_value,
    di_n AS n_games
  FROM per_user
  WHERE achievable_gap IS NOT NULL
)"""


def per_user_cte_score_gap_bucket_tc(
    tc: TimeControlBucket,
    *,
    source: Literal["benchmark", "single_user"],
    snapshot_date: date | None = None,
    bucket_label: Literal["conversion", "parity", "recovery"],
) -> str:
    """Per-TC pooled ``per_user_values(user_id, metric_value, n_games)`` for ``score_gap_{conv,parity,recovery}``.

    Per-TC version of ``per_user_cte_score_gap_bucket`` — restricted to one
    ``time_control_bucket`` via ``_recent_capped_per_tc_cte``. The ``gap_rows``
    bucket classification (conversion / parity / recovery — see lines 502-512
    of the non-per-TC builder) and per-bucket HAVING ≥30 floor are
    byte-identical to the non-per-TC analog.

    The ``bucket_label`` Literal includes ``'recovery'`` (Phase 94.4 Plan 03
    Task 2) for the recovery-rescue cohort: rows where the user entered the
    endgame down material (entry_eval signed by user_color <= -100 cp, or
    entry_eval_mate < 0 signed).

    Security and source-mode parity identical to ``per_user_cte_score_gap_tc``.
    Pitfall 1 user_id widening applied.
    """
    _ = source  # cohort difference is in selected_users_cte; pooled body is identical
    ueag = _user_elo_at_game_expr()
    return f"""{_recent_capped_per_tc_cte(snapshot_date, tc)},
spans AS (
  SELECT
    gp.game_id, gp.endgame_class,
    (array_agg(gp.eval_cp   ORDER BY gp.ply ASC))[1] AS entry_eval_cp,
    (array_agg(gp.eval_mate ORDER BY gp.ply ASC))[1] AS entry_eval_mate,
    min(gp.ply) AS span_min_ply
  FROM game_positions gp
  JOIN recent_capped rc ON rc.id = gp.game_id
  WHERE gp.endgame_class IS NOT NULL
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
  JOIN games g ON g.id = swn.game_id
  WHERE (swn.entry_eval_cp IS NOT NULL OR swn.entry_eval_mate IS NOT NULL)
    AND {ueag} >= {_SUB_800_FLOOR}
),
per_user_bucket AS (
  SELECT user_id, bucket,
         avg(gap_span) AS mean_gap,
         count(*) AS span_n
  FROM gap_rows
  WHERE gap_span IS NOT NULL
  GROUP BY user_id, bucket
  HAVING count(*) >= {SCORE_GAP_BUCKET_MIN_SPANS}
),
per_user_values AS (
  -- user_id widened per Phase 94.4 Pitfall 1 (cohort-CDF JOIN against per_user_anchor).
  SELECT
    user_id,
    mean_gap AS metric_value,
    span_n AS n_games
  FROM per_user_bucket
  WHERE bucket = '{bucket_label}'
)"""


def _chesscom_conversion_values_sql(target_tc: TimeControlBucket) -> str:
    """Emit a VALUES body for the (chesscom_anchor, lichess_equiv) lookup table.

    Reads ``CHESSCOM_BLITZ_TO_LICHESS`` from ``app.services.chesscom_to_lichess``
    and emits all rows whose ``target_tc`` column is not None. Returns the VALUES
    expression body suitable for use inside a named CTE, e.g.:

        VALUES (600, 632), (650, 681), ...

    The returned string is intended for use inside a column-aliased CTE body:

        chesscom_conversion_lookup(chesscom_anchor, lichess_equiv) AS (
            {_chesscom_conversion_values_sql(tc)}
        )

    This is the standard PostgreSQL CTE VALUES pattern — the column names are
    declared in the CTE name clause, not via an alias on the VALUES expression.

    Security: the rows are emitted from a ``Final`` Python-controlled snapshot
    constant (``CHESSCOM_BLITZ_TO_LICHESS``) — all values are Python ``int``
    literals with no user-input injection surface (T-94.4-10-02).

    Raises:
        ValueError: if no rows have a non-None lichess equivalent for
            ``target_tc`` (defensive — shouldn't happen for the 4 standard TCs).
    """
    rows: list[tuple[int, int]] = [
        (anchor, equiv)
        for anchor, tc_map in CHESSCOM_BLITZ_TO_LICHESS.items()
        if (equiv := tc_map.get(target_tc)) is not None  # type: ignore[assignment]
    ]
    if not rows:
        raise ValueError(f"CHESSCOM_BLITZ_TO_LICHESS has no entries for target_tc={target_tc!r}")
    return "VALUES " + ", ".join(f"({anchor}, {equiv})" for anchor, equiv in rows)


def per_user_cte_median_anchor(
    tc: TimeControlBucket,
    *,
    source: Literal["benchmark", "single_user"],
    snapshot_date: date | None = None,
    platform: Literal["lichess", "chesscom"] | None = None,
    min_games: int = MEDIAN_ANCHOR_MIN_GAMES,
    blend: bool = False,
) -> str:
    """Per-(user, TC) median rating anchor over the recent-3000-per-TC × 36-month pool.

    Phase 94.4 D-04 / RESEARCH Pattern 6 (lines 622-666). Substrate for the
    peer-relative percentile chip lookup: the median anchor per (user, TC) is
    persisted in ``user_rating_anchors`` and later joined against the cohort
    CDF artifact to read the percentile (Plan 04 benchmark-side; Plan 05
    single-user-side).

    Two modes, selected by ``blend``:

    **Non-blend mode** (``blend=False``, default):

    Output CTE: ``per_user_anchor(user_id, anchor_rating INT, n_games INT)``.
    ``anchor_rating`` is ``percentile_cont(0.5) WITHIN GROUP (ORDER BY ...)::int``
    over the user's rating at game time (white_rating / black_rating, whichever
    side the user played); ``n_games`` is the count of games used (HAVING
    >= ``min_games``).

    The ``platform`` parameter restricts the join to a single platform:

    * ``None`` → no platform filter (both Lichess and chess.com games
      contribute to the median; the cohort CDF generator in Plan 04 uses
      this form on the benchmark DB which is Lichess-only by construction).
    * ``'lichess'`` / ``'chesscom'`` → emit ``AND g.platform = '<value>'``.
      The Plan 05 Python wrapper drove the Lichess-precedence policy
      (D-12 original) by calling this builder first with ``platform='lichess'``
      and falling back to ``platform='chesscom'`` — this policy is superseded
      by the D-12 Reversal Amendment (see blend mode below).

    **Blended mode** (``blend=True``, D-12 Reversal Amendment 2026-05-27):

    Output CTE: ``per_user_anchor(user_id, anchor_rating INT, n_chesscom_games INT,
    n_lichess_games INT, chesscom_median_native INT, lichess_median_native INT)``.

    Per-game weighted blended anchor. chess.com (non-Daily) games are converted
    via the ``chesscom_conversion_lookup`` VALUES CTE (generated from
    ``CHESSCOM_BLITZ_TO_LICHESS`` via ``_chesscom_conversion_values_sql``). Each
    chess.com game is matched to the nearest anchor row via
    ``ORDER BY ABS(rating_at_game_time - chesscom_anchor) LIMIT 1`` and the
    ``lichess_equiv`` is used as the blended rating. Lichess games pass through
    their native rating unchanged. The per-user median of the combined
    (converted + native) pool is the blended ``anchor_rating``.

    ``blend=True`` with ``platform!=None`` is mutually exclusive and raises
    ``ValueError`` — blended mode pools both platforms inherently; a platform
    filter would defeat the purpose.

    Suppression rule (§Suppression rule of the D-12 Reversal Amendment):
    the HAVING clause applies to the POOLED count (n_chesscom_games +
    n_lichess_games >= min_games). A chess.com-Daily-only user in the
    ``classical`` bucket has zero qualifying games and produces no row.

    Worked example (from ``.planning/notes/percentile-anchor-d12-reversal.md``):
    4000 chess.com games @ 2200 (→ ~2050 lichess-equiv) + 100 lichess games
    @ 1900 → pooled median ≈ 2046 (game-weighted; heavy chess.com side dominates).

    ``n_chesscom_games``: count of non-Daily chess.com games in the pooled window.
    ``n_lichess_games``: count of lichess games in the pooled window.
    ``chesscom_median_native``: median of RAW chess.com ratings (pre-conversion);
      NULL when n_chesscom_games = 0. Tooltip-disclosure source (D-07 bullet 4).
    ``lichess_median_native``: median of native lichess ratings; NULL when
      n_lichess_games = 0. Tooltip-disclosure source.

    **Common documentation (both modes)**:

    Daily-classical drop (RESEARCH Pitfall 11): chess.com Daily games are
    bucketed ``classical`` by the import pipeline but are excluded from the
    median anchor via ``WHERE NOT (g.platform = 'chess.com' AND
    g.time_control_str LIKE '1/%')``. The drop is unconditional on ``tc`` for
    structural symmetry — Daily games are filtered out everywhere, not just
    when ``tc='classical'`` (RESEARCH Pitfall 2). As a result, classical
    anchors may be absent for users who play only chess.com Daily, and the
    chip suppresses naturally for that (user, classical) cell (D-04
    suppression semantics).

    The ``source`` parameter is accepted for API symmetry with the other
    pooled builders (the cohort difference lives entirely in
    ``selected_users_cte``); the pooled body is identical on both paths
    (D-10 "drift remains structurally impossible").

    Security: ``tc`` and ``platform`` are ``Literal`` parameters constrained
    by ty + Pydantic to the closed value set (4-value × 3-value matrix of
    known strings), so the f-string interpolation has no SQL-injection
    surface (T-94.4-02-01 / T-94.4-02-02 / T-94.4-10-01). ``min_games`` is
    an ``int``, safe to embed directly. ``snapshot_date.isoformat()`` emits
    only digits and dashes via the existing ``_recency_window_sql`` helper.
    The ``_chesscom_conversion_values_sql`` output is generated from
    Python-controlled snapshot data (a ``Final`` constant of Python ints) —
    no user-input injection surface (T-94.4-10-02). ``user_id`` flows through
    ``.bindparams()`` in the caller; never f-stringed here (V5).

    f-string ``%`` convention: ``time_control_str LIKE '1/%'`` uses a single
    ``%`` — this module's builders return raw SQL passed to asyncpg via
    SQLAlchemy ``text()`` with ``:name``-style bindparams, NOT with Python
    ``%``-style formatting, so no ``%%`` doubling is required.

    Design-decision record: D-12 Reversal Amendment (CONTEXT 2026-05-27) and
    ``.planning/notes/percentile-anchor-d12-reversal.md``.
    """
    if blend and platform is not None:
        raise ValueError(
            "blend=True is mutually exclusive with platform!=None — "
            "blended mode pools both platforms inherently"
        )
    _ = source  # cohort difference is in selected_users_cte; pooled body is identical

    if blend:
        return _per_user_cte_median_anchor_blended(tc, snapshot_date, min_games)

    # --- Non-blend mode (byte-for-byte unchanged from pre-Task-1 baseline) ---
    # ``platform`` is the AnchorSource Literal ('lichess' | 'chesscom') used by
    # the user_rating_anchors model, but the games table stores the chess.com
    # platform string with a dot (``platform='chess.com'``). Translate before
    # emitting the SQL filter so the (AnchorSource) → (games.platform) mapping
    # is the only place we paper over the discrepancy. Bug found in Plan 05b
    # (#94.4-05b-Rule1): the benchmark DB is Lichess-only so the chess.com path
    # was never exercised by Plan 02's tests.
    if platform is None:
        platform_filter = ""
    elif platform == "chesscom":
        platform_filter = "AND g.platform = 'chess.com'"
    else:
        platform_filter = f"AND g.platform = '{platform}'"
    return f"""{_recent_capped_per_tc_cte(snapshot_date, tc)},
recent_capped_no_daily AS (
  SELECT rc.*
  FROM recent_capped rc
  JOIN games g ON g.id = rc.id
  WHERE NOT (g.platform = 'chess.com' AND g.time_control_str LIKE '1/%')
    {platform_filter}
),
per_user_anchor AS (
  SELECT
    rc.user_id,
    percentile_cont(0.5) WITHIN GROUP (ORDER BY {_user_elo_at_game_expr()})::int AS anchor_rating,
    count(*) AS n_games
  FROM recent_capped_no_daily rc
  JOIN games g ON g.id = rc.id
  GROUP BY rc.user_id
  HAVING count(*) >= {min_games}
)"""


def _per_user_cte_median_anchor_blended(
    tc: TimeControlBucket,
    snapshot_date: date | None,
    min_games: int,
) -> str:
    """Emit the blended-mode ``per_user_anchor`` CTE chain.

    Internal helper for ``per_user_cte_median_anchor(blend=True)``. Extracted
    to keep the parent function readable (CLAUDE.md nesting-depth rule). Not
    exported; callers use ``per_user_cte_median_anchor``.

    Emits:
      recent_capped, recent_capped_no_daily,
      chesscom_conversion_lookup,
      per_game_blended_rating,
      per_user_anchor (6 columns)

    The LATERAL nearest-anchor join is bounded by the recent-3000-per-TC cap
    (3000 games × ~50 lookup rows ≈ 150K comparisons per user per TC) —
    T-94.4-10-04 accept disposition.
    """
    elo_expr = _user_elo_at_game_expr()
    conv_values = _chesscom_conversion_values_sql(tc)
    return f"""{_recent_capped_per_tc_cte(snapshot_date, tc)},
recent_capped_no_daily AS (
  SELECT rc.*
  FROM recent_capped rc
  JOIN games g ON g.id = rc.id
  WHERE NOT (g.platform = 'chess.com' AND g.time_control_str LIKE '1/%')
),
chesscom_conversion_lookup(chesscom_anchor, lichess_equiv) AS (
  {conv_values}
),
per_game_blended_rating AS (
  -- chess.com non-Daily: convert via nearest-anchor lookup
  SELECT rc.user_id, lookup.lichess_equiv AS blended_rating, 'chesscom' AS platform_tag,
         {elo_expr} AS native_rating
  FROM recent_capped_no_daily rc
  JOIN games g ON g.id = rc.id
  JOIN LATERAL (
    SELECT lichess_equiv
    FROM chesscom_conversion_lookup
    ORDER BY ABS(chesscom_anchor - {elo_expr})
    LIMIT 1
  ) lookup ON true
  WHERE g.platform = 'chess.com'
  UNION ALL
  -- lichess: pass through native rating, no conversion
  SELECT rc.user_id, {elo_expr} AS blended_rating, 'lichess' AS platform_tag,
         {elo_expr} AS native_rating
  FROM recent_capped_no_daily rc
  JOIN games g ON g.id = rc.id
  WHERE g.platform = 'lichess'
),
per_user_anchor AS (
  SELECT
    user_id,
    percentile_cont(0.5) WITHIN GROUP (ORDER BY blended_rating)::int AS anchor_rating,
    count(*) FILTER (WHERE platform_tag = 'chesscom') AS n_chesscom_games,
    count(*) FILTER (WHERE platform_tag = 'lichess') AS n_lichess_games,
    percentile_cont(0.5) WITHIN GROUP (ORDER BY native_rating)
      FILTER (WHERE platform_tag = 'chesscom')::int AS chesscom_median_native,
    percentile_cont(0.5) WITHIN GROUP (ORDER BY native_rating)
      FILTER (WHERE platform_tag = 'lichess')::int AS lichess_median_native
  FROM per_game_blended_rating
  GROUP BY user_id
  HAVING count(*) >= {min_games}
)"""


def per_user_cte_for(
    metric_id: CdfMetricId,
    *,
    source: Literal["benchmark", "single_user"],
    snapshot_date: date | None = None,
) -> str:
    """Dispatch to the metric-specific pooled ``per_user_values`` CTE block.

    ``source`` selects the cohort definition (handled by ``selected_users_cte``;
    the pooled aggregate body is identical on both paths per D-10).

    ``snapshot_date`` controls the recency anchor:
      - ``None`` → ``NOW()`` (per-user lookup path).
      - explicit ``date`` → that date (CDF construction path; passed by
        ``scripts/gen_global_percentile_cdf.py``).

    Note: the ``apply_floor`` argument from 94.1 is removed (D-8). Passing
    it raises ``TypeError`` (the inclusion floor is always applied; below-floor
    → no row emitted → no row stored → chip suppressed).
    """
    if metric_id == "score_gap":
        return per_user_cte_score_gap(source=source, snapshot_date=snapshot_date)
    if metric_id == "achievable_score_gap":
        return per_user_cte_achievable(source=source, snapshot_date=snapshot_date)
    if metric_id == "score_gap_conv":
        return per_user_cte_score_gap_bucket(
            bucket_label="conversion", source=source, snapshot_date=snapshot_date
        )
    if metric_id == "score_gap_parity":
        return per_user_cte_score_gap_bucket(
            bucket_label="parity", source=source, snapshot_date=snapshot_date
        )
    # Phase 94.3 Plan B — 12 new dispatcher arms for the per-(metric × TC)
    # percentile chips. The CdfMetricId Literal is widened to 16 entries by
    # Plan C; here we match string literals directly so this plan can land
    # before the Literal expansion (D-10 atomic-cutover trio B → C → D).
    if metric_id == "time_pressure_score_gap_bullet":
        return per_user_cte_time_pressure_score_gap(
            "bullet", source=source, snapshot_date=snapshot_date
        )
    if metric_id == "time_pressure_score_gap_blitz":
        return per_user_cte_time_pressure_score_gap(
            "blitz", source=source, snapshot_date=snapshot_date
        )
    if metric_id == "time_pressure_score_gap_rapid":
        return per_user_cte_time_pressure_score_gap(
            "rapid", source=source, snapshot_date=snapshot_date
        )
    if metric_id == "time_pressure_score_gap_classical":
        return per_user_cte_time_pressure_score_gap(
            "classical", source=source, snapshot_date=snapshot_date
        )
    if metric_id == "clock_gap_bullet":
        return per_user_cte_clock_gap("bullet", source=source, snapshot_date=snapshot_date)
    if metric_id == "clock_gap_blitz":
        return per_user_cte_clock_gap("blitz", source=source, snapshot_date=snapshot_date)
    if metric_id == "clock_gap_rapid":
        return per_user_cte_clock_gap("rapid", source=source, snapshot_date=snapshot_date)
    if metric_id == "clock_gap_classical":
        return per_user_cte_clock_gap("classical", source=source, snapshot_date=snapshot_date)
    if metric_id == "net_flag_rate_bullet":
        return per_user_cte_net_flag_rate("bullet", source=source, snapshot_date=snapshot_date)
    if metric_id == "net_flag_rate_blitz":
        return per_user_cte_net_flag_rate("blitz", source=source, snapshot_date=snapshot_date)
    if metric_id == "net_flag_rate_rapid":
        return per_user_cte_net_flag_rate("rapid", source=source, snapshot_date=snapshot_date)
    if metric_id == "net_flag_rate_classical":
        return per_user_cte_net_flag_rate("classical", source=source, snapshot_date=snapshot_date)
    raise ValueError(f"Unknown metric_id: {metric_id!r}")
