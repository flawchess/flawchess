"""Per-TC, one-point-per-user CTE builders for the canonical benchmark slice.

Each subject (a cohort user during CDF construction; an app user during
per-user lookup) contributes a single ``metric_value`` and ``n_games``
aggregate to the output, computed over their most recent 3000 games in ONE
time control within a 36-month recency window. Every builder takes a
``TimeControlBucket``; there is no cross-TC pooled form.

Consumers (both call the same builders, so the CDF and the per-user lookup
cannot drift apart):

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
    tc_bucket='classical')``. Emits ``user_id`` only.

  - ``"single_user"``: scalar single-row CTE projecting an explicit
    SQLAlchemy bindparam ``CAST(:user_id AS int)``. The explicit-CAST form
    is required so SQLAlchemy's ``text()`` tokeniser actually detects the
    parameter.

Per-user aggregate shape (identical on both sources):

* ``recent_capped``: ``ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY
  played_at DESC) <= 3000`` over one time control, with the universal
  filter (rated, non-computer, both ratings non-null, equal-footing ±100)
  and the 36-month recency predicate.

* Metric-specific aggregation (endgame/non-endgame split, span derivation,
  bucket gating) over ``recent_capped``.

* ``per_user``: ``GROUP BY user_id`` (no ``elo_bucket`` / ``tc_bucket``
  projection) with a ``HAVING`` inclusion-floor gate of ≥30 of the
  metric-relevant unit.

* ``per_user_values``: emits ``(user_id, metric_value, n_games)``.
  ``n_games`` is the metric-relevant count on the per-TC set (endgame games
  for ``score_gap``; eval'd entry games for ``achievable_score_gap``;
  bucket spans for ``score_gap_bucket_*``).

Below-floor users produce no row, so the caller stores no row and the chip
is suppressed.

Documented exception to "one point per user": the two "out of the opening" builders
(``per_user_cte_opening_out_counts`` / ``per_user_cte_opening_out_rate``) emit up to
TWO rows per user, one per colour, because the metric is a per-colour rate (Phase 243
D-04/D-05). Their ``per_user_values`` therefore carries a ``user_color`` column.

Sparse-cell exclusion is a cohort-selection concern, applied by
``selected_users_cte(source="benchmark")`` only.

Security note:

All SQL fragments contain STATIC SQL plus one bindparam (``:user_id``) and
one Python-formatted ISO date string (``snapshot_date``). The
``snapshot_date`` parameter is a build-time ``date | None`` supplied by the
CDF generator CLI; Python's ``date.isoformat()`` produces only
``YYYY-MM-DD`` digits, so the f-string into SQL has no injection vector.
Never f-string ``user_id`` here.
"""

from __future__ import annotations

from datetime import date
from typing import Final, Literal, Mapping, TypeAlias

from app.services.chesscom_to_lichess import (
    ChessComSourceTC,
    composed_chesscom_to_lichess_grid,
)
from app.services.global_percentile_cdf import OpeningOutMetricId
from app.services.opening_insights_constants import (
    EVAL_BASELINE_PAWNS_BLACK,
    EVAL_BASELINE_PAWNS_WHITE,
    OPENING_OUT_THRESHOLD_PAWNS,
)

# Per-TC bucket identifier, used by the per-TC builders so the leading
# positional argument is type-checked (CLAUDE.md type-safety rule).
TimeControlBucket: TypeAlias = Literal["bullet", "blitz", "rapid", "classical"]

# FlawChess TimeControlBucket -> chess.com source TC for the anchor-conversion
# lookup. Each bucket's chess.com games carry a NATIVE rating
# on that source TC's scale; the composed grid is keyed on native ratings so the
# nearest-anchor SQL join converts correctly. classical->rapid: chess.com has no
# classical category, and chess.com games bucketed `classical` carry rapid
# ratings (chess.com Daily games are dropped upstream by the
# `time_control_str LIKE '1/%'` filter, so the classical bucket only ever sees
# rapid-rated chess.com games here).
_BUCKET_TO_CHESSCOM_SOURCE_TC: Final[Mapping[TimeControlBucket, ChessComSourceTC]] = {
    "bullet": "bullet",
    "blitz": "blitz",
    "rapid": "rapid",
    "classical": "rapid",
}

# ---------------------------------------------------------------------------
# Module-level constants (CLAUDE.md no-magic-numbers).
# ---------------------------------------------------------------------------

# Per-metric inclusion floors on the per-TC set (all 4 metrics ≥30).
SCORE_GAP_MIN_ENDGAME_N: int = 30
SCORE_GAP_MIN_NON_ENDGAME_N: int = 30
ACHIEVABLE_MIN_GAMES: int = 30
SCORE_GAP_BUCKET_MIN_SPANS: int = 30

# Window shape.
RECENT_GAMES_PER_TC_CAP: int = 3000
RECENCY_WINDOW_MONTHS: int = 36

# Per-TC time-pressure builder thresholds.
# `TIME_PRESSURE_CLOCK_PCT_THRESHOLD` defines the "under time pressure"
# cutoff applied to each side's clock fraction at endgame entry: clock_pct
# < 0.40 = pressured. The remaining three constants are the inclusion
# floors gated via HAVING on the per-user aggregate (≥30, like every other
# metric in this module).
TIME_PRESSURE_CLOCK_PCT_THRESHOLD: float = 0.40
TIME_PRESSURE_MIN_PRESSURED_N: int = 30
CLOCK_GAP_MIN_POOL_N: int = 30
NET_FLAG_RATE_MIN_POOL_N: int = 30

# Per-(rate metric, TC) chip-inclusion floor — minimum number of
# endgame spans in the relevant bucket (conversion / parity / recovery) for a
# user's rate chip to render. Same value as SCORE_GAP_BUCKET_MIN_SPANS (both
# ≥30) but named separately so future tuning of one does not silently move
# the other (CLAUDE.md no-magic-numbers).
MINIMUM_RATE_BUCKET_SPANS: int = 30

# Per-(user, TC) median rating anchor inclusion floor.
# 30 games is the lower bound for a stable per-TC median on the recent-3000
# pool (CLAUDE.md no-magic-numbers); a tighter floor is a tuning decision
# for the CDF regen report. Used as the default `min_games` in
# `per_user_cte_median_anchor` below.
MEDIAN_ANCHOR_MIN_GAMES: Final[int] = 30

# "Out of the opening" worse/better rates (Phase 243).
# D-05 floor: minimum qualifying games per colour x TC, applied to benchmark peers
# (for CDF points) and to the user alike. Only the rate builder applies it; the
# counts builder feeds the on-read "k of n" display and applies no floor.
OPENING_OUT_MIN_GAMES_PER_COLOR: Final[int] = 30
# lichess Divider phase encoding (see app/models/game_position.py): 1 = middlegame.
_MIDDLEGAME_PHASE: Final[int] = 1
_CP_PER_PAWN: Final[int] = 100
# Colour baselines and the clear-advantage cut, in centipawns (int literals only, so
# the f-string into SQL has no injection surface).
_OPENING_OUT_BASELINE_CP_WHITE: Final[int] = round(EVAL_BASELINE_PAWNS_WHITE * _CP_PER_PAWN)
_OPENING_OUT_BASELINE_CP_BLACK: Final[int] = round(EVAL_BASELINE_PAWNS_BLACK * _CP_PER_PAWN)
_OPENING_OUT_CUT_CP: Final[int] = round(OPENING_OUT_THRESHOLD_PAWNS * _CP_PER_PAWN)
# D-02: a game with no middlegame ply counts by result only when it ended this way.
_DECISIVE_EARLY_TERMINATIONS: Final[tuple[str, ...]] = ("resignation", "checkmate", "timeout")
_DECISIVE_EARLY_TERMINATIONS_SQL: Final[str] = (
    "(" + ", ".join(f"'{t}'" for t in _DECISIVE_EARLY_TERMINATIONS) + ")"
)
# Count column of per_user_color_counts feeding each metric's numerator.
_OPENING_OUT_COUNT_COLUMN: Final[Mapping[OpeningOutMetricId, str]] = {
    "opening_worse_rate": "worse_n",
    "opening_better_rate": "better_n",
}

# Shared SQL constants.
_EQUAL_FOOTING_TOL: int = 100
_SPARSE_CELL_ELO: int = 2400
_SPARSE_CELL_TC: str = "classical"
_SUB_800_FLOOR: int = 800
# Public alias so the on-read ranked service applies the exact same
# sub-800 exclusion floor as the rate / bucket-gap CTEs below.
SUB_800_FLOOR: Final[int] = _SUB_800_FLOOR


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

    Security note: ``snapshot_date.isoformat()`` emits only
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

    ``source="benchmark"`` → deduped cohort. Groups
    ``benchmark_selected_users`` by ``lower(lichess_username)`` and keeps
    only usernames that have at least one non-``(2400, classical)``
    selection slot. Joins to ``users`` for the surrogate ``user_id`` the
    pooled aggregates need.

    ``source="single_user"`` → scalar SELECT with ``CAST(:user_id AS int)``
    bindparam (the explicit CAST form is load-bearing).
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
    # single_user: scalar bindparam. The explicit CAST() form is load-bearing:
    # SQLAlchemy's text() tokeniser silently drops `:user_id::int` and raises
    # ArgumentError at .bindparams() time. CAST(:user_id AS int) is parsed
    # correctly.
    return "selected_users AS (SELECT CAST(:user_id AS int) AS user_id)"


def elo_bucket_expr(user_elo_alias: str) -> str:
    """SQL CASE WHEN expression to bucket ``user_elo_alias`` into 5 canonical anchors.

    Returns NULL for sub-800 ratings (callers gate with
    ``WHERE user_elo_at_game >= 800``).

    Retained only for tests/services/test_canonical_slice_sql.py; NOT invoked
    by any builder or script.
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


# Not invoked by per_user_cte_*: sparse-cell exclusion lives in
# selected_users_cte("benchmark") only.
def sparse_exclusion_sql(elo_col: str, tc_col: str) -> str:
    """SQL fragment to exclude the sparse ``(2400, classical)`` cell.

    Retained only for tests/services/test_canonical_slice_sql.py
    (``::test_sparse_exclusion_sql_parametrises_columns``); NOT invoked by any
    builder or script.

    Column names are SQL identifiers provided by the caller (never user input).
    """
    return f"NOT ({elo_col} = {_SPARSE_CELL_ELO} AND {tc_col} = '{_SPARSE_CELL_TC}')"


# ---------------------------------------------------------------------------
# Per-TC per-user CTE builders.
# ---------------------------------------------------------------------------


def _recent_capped_per_tc_cte(snapshot_date: date | None, tc: TimeControlBucket) -> str:
    """Per-TC ``recent_capped`` CTE.

    Restricts the canonical slice to a single ``time_control_bucket`` so the
    per-TC percentile chips can be computed against a per-TC pooled set.

    Two structural properties vs the pooled-TC form:

    1. ``AND g.time_control_bucket = '{tc}'`` is added to the inner WHERE.
       Safe to f-string because ``tc`` is constrained to four literal values
       by ``TimeControlBucket``; no SQL-injection vector.
    2. ``ROW_NUMBER() OVER (PARTITION BY g.user_id ...)`` — the per-(user, TC)
       partition collapses to per-user because the inner set is already
       restricted to one TC. The 3000-cap then means "most recent 3000 games
       of this TC per user".
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


def ranked_games_sql(tc: TimeControlBucket) -> str:
    """The per-TC ranked sample (the games Stage A/B rank) with display columns.

    The ``WITH`` chain is the same ``selected_users_cte("single_user")`` +
    ``_recent_capped_per_tc_cte(None, tc)`` prelude every ``per_user_cte_*``
    builder uses, so the on-read ranked games are exactly the games the
    persisted percentiles were computed from. Only the outer ``SELECT`` is
    specific to this function.

    Columns: ``game_id``, ``played_at``, ``platform``, ``time_control_str``
    (the anchor count must exclude chess.com Daily, ``time_control_str LIKE
    '1/%'``), ``user_elo`` (rating at game time; the rate / bucket-gap
    metrics drop sub-800 games), ``eval_pending`` (entry evals not yet
    completed for the game).

    Security: ``tc`` is interpolated by ``_recent_capped_per_tc_cte``
    and is safe only because it is the 4-value ``TimeControlBucket`` Literal,
    enforced by ty at every call site. ``user_id`` flows only through the
    ``CAST(:user_id AS int)`` bindparam inside ``selected_users_cte``; callers
    bind it with ``text(sql).bindparams(user_id=...)``, never an f-string.
    """
    return (
        f"WITH {selected_users_cte(source='single_user')},\n"
        f"{_recent_capped_per_tc_cte(None, tc)}\n"
        "SELECT rc.id AS game_id, rc.played_at, g.platform, g.time_control_str,\n"
        f"       {_user_elo_at_game_expr()} AS user_elo,\n"
        "       (g.evals_completed_at IS NULL) AS eval_pending\n"
        "FROM recent_capped rc\n"
        "JOIN games g ON g.id = rc.id\n"
        "ORDER BY rc.played_at ASC, rc.id ASC"
    )


def _endgame_entry_clocks_cte() -> str:
    """Per-game endgame-entry clock derivation for the three per-TC builders.

    Mirrors ``endgame_service.extract_entry_clocks``: for each game that
    reached an endgame phase (≥6 endgame plies under the whole-game rule),
    aggregate the first non-null ``clock_seconds`` per ply parity:

    - white_entry_clock = first non-null clock at an even ply (white just moved)
    - black_entry_clock = first non-null clock at an odd ply (black just moved)

    The user/opp assignment then collapses by ``rc.user_color`` in the
    consumer's ``joined`` CTE. Centralised here because all three per-TC
    builders need the identical derivation.

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

    Per-TC time-pressure score gap. Restricted
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

    No per-row sparse-cell exclusion; cohort dedup lives in
    ``selected_users_cte("benchmark")``. ``source`` is accepted for API
    symmetry but does not alter the pooled body.

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

    No per-row sparse-cell exclusion; cohort dedup lives in
    ``selected_users_cte("benchmark")``. ``source`` is accepted for API
    symmetry but does not alter the pooled body.
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
    averaged per user; mirrors ``_net_flag_metric`` in
    ``app/services/endgame_ranked_service.py``.
    ``n_games`` = pooled endgame-entry count (the binding floor per
    ``NET_FLAG_RATE_MIN_POOL_N``).

    Verified column: ``games.termination`` is an ENUM whose time-forfeit value
    is the string literal ``'timeout'``, NOT ``'time forfeit'``.

    No per-row sparse-cell exclusion; cohort dedup lives in
    ``selected_users_cte("benchmark")``. ``source`` is accepted for API
    symmetry but does not alter the pooled body.
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
# Per-TC ΔES builders for the 4 page-level ΔES metric families. The cohort
# CDF builds at (metric, anchor, tc) granularity, so every metric family
# must be available per-TC.
#
# All 4 project user_id in per_user_values (the cohort-CDF JOIN against
# per_user_anchor needs user identity).
# ---------------------------------------------------------------------------


def per_user_cte_score_gap_tc(
    tc: TimeControlBucket,
    *,
    source: Literal["benchmark", "single_user"],
    snapshot_date: date | None = None,
) -> str:
    """Per-TC pooled ``per_user_values(user_id, metric_value, n_games)`` for ``score_gap``.

    Per-TC ``score_gap`` builder. Restricted to one ``time_control_bucket``
    via ``_recent_capped_per_tc_cte``. The metric_value formula and HAVING
    gates mirror the pooled form: ``eg_score - non_eg_score`` projection;
    dual ≥30 floor on endgame / non-endgame game counts.

    ``n_games`` = endgame-game count on the per-TC pooled set.

    Security: ``tc`` is constrained to a 4-value ``Literal`` so the f-string
    interpolation has no injection vector (the closed value set is enforced
    by ty at every call site). ``snapshot_date.isoformat()`` emits only
    digits and dashes via ``_recency_window_sql``. Bindparams are confined
    to ``:user_id`` inside ``selected_users_cte("single_user")``.

    Source-mode parity: the pooled body is byte-identical between
    ``source='benchmark'`` and ``source='single_user'``. The cohort
    difference lives entirely inside ``selected_users_cte``.

    ``per_user_values`` projects ``user_id`` so the cohort-CDF JOIN against
    ``per_user_anchor`` can locate users by ID.
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

    Per-TC ``achievable_score_gap`` builder. Restricted to one
    ``time_control_bucket`` via ``_recent_capped_per_tc_cte``. The metric_value
    formula is ``avg(d_i)`` where d_i is the per-game score-vs-Lichess-sigmoid
    gap at endgame entry; HAVING gate is ≥30 d_i-non-null games.

    Security and source-mode parity identical to ``per_user_cte_score_gap_tc``.
    ``per_user_values`` also projects ``user_id``.
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

    Per-TC ``score_gap_{conv,parity,recovery}`` builder — restricted to one
    ``time_control_bucket`` via ``_recent_capped_per_tc_cte``. The ``gap_rows``
    bucket classification (conversion / parity / recovery via entry-eval
    signed by user_color) and per-bucket HAVING ≥30 floor mirror the
    pooled-TC form.

    The ``bucket_label`` Literal includes ``'recovery'`` for the
    recovery-rescue cohort: rows where the user entered the
    endgame down material (entry_eval signed by user_color <= -100 cp, or
    entry_eval_mate < 0 signed).

    Security and source-mode parity identical to ``per_user_cte_score_gap_tc``.
    ``per_user_values`` also projects ``user_id``.
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


def per_user_cte_conv_rate_tc(
    tc: TimeControlBucket,
    *,
    source: Literal["benchmark", "single_user"],
    snapshot_date: date | None = None,
) -> str:
    """Pooled ``per_user_values(user_id, metric_value, n_games)`` for ``conversion_rate_{tc}``.

    ``metric_value`` = wins / conv_spans (pooled over the recent-3000-per-TC ×
    36-month pool). ``n_games`` = conversion span count (the binding floor
    ≥ MINIMUM_RATE_BUCKET_SPANS).

    No ``lead()`` / ``spans_with_next`` — rate is measured from game outcome,
    not ΔES delta. Terminal-span semantics: one row per endgame span; the game
    result is the exit-score proxy.

    Security: ``tc`` is a 4-value Literal; ty enforces the closed set at every
    call site — no user string is interpolated (identical to the other
    builders; see the module docstring).

    Source-mode parity: ``_ = source`` — cohort difference lives entirely in
    ``selected_users_cte``; pooled body is byte-identical for both sources.
    """
    _ = source  # cohort difference is in selected_users_cte; pooled body is identical
    ueag = _user_elo_at_game_expr()
    return f"""{_recent_capped_per_tc_cte(snapshot_date, tc)},
spans AS (
  SELECT gp.game_id,
         (array_agg(gp.eval_cp   ORDER BY gp.ply ASC))[1] AS entry_eval_cp,
         (array_agg(gp.eval_mate ORDER BY gp.ply ASC))[1] AS entry_eval_mate
  FROM game_positions gp
  JOIN recent_capped rc ON rc.id = gp.game_id
  WHERE gp.endgame_class IS NOT NULL
  GROUP BY gp.game_id
  HAVING count(gp.ply) >= 6
),
bucket_rows AS (
  SELECT g.user_id,
    CASE
      WHEN (s.entry_eval_mate IS NOT NULL
            AND (s.entry_eval_mate * (CASE WHEN g.user_color='white' THEN 1 ELSE -1 END)) > 0)
        OR (s.entry_eval_cp IS NOT NULL
            AND (s.entry_eval_cp * (CASE WHEN g.user_color='white' THEN 1 ELSE -1 END)) >= 100)
      THEN true ELSE false
    END AS is_conversion,
    CASE
      WHEN (g.result='1-0' AND g.user_color='white') OR (g.result='0-1' AND g.user_color='black')
      THEN 1 ELSE 0
    END AS is_win
  FROM spans s
  JOIN games g ON g.id = s.game_id
  WHERE (s.entry_eval_cp IS NOT NULL OR s.entry_eval_mate IS NOT NULL)
    AND {ueag} >= {_SUB_800_FLOOR}
),
per_user AS (
  SELECT user_id,
    count(*) FILTER (WHERE is_conversion) AS conv_n,
    sum(is_win) FILTER (WHERE is_conversion)::float AS conv_wins
  FROM bucket_rows
  GROUP BY user_id
  HAVING count(*) FILTER (WHERE is_conversion) >= {MINIMUM_RATE_BUCKET_SPANS}
),
per_user_values AS (
  -- user_id widened per Phase 94.4 Pitfall 1 (cohort-CDF JOIN against per_user_anchor).
  SELECT user_id,
    conv_wins / NULLIF(conv_n, 0) AS metric_value,
    conv_n::int AS n_games
  FROM per_user
  WHERE conv_wins IS NOT NULL
)"""


def per_user_cte_parity_rate_tc(
    tc: TimeControlBucket,
    *,
    source: Literal["benchmark", "single_user"],
    snapshot_date: date | None = None,
) -> str:
    """Pooled ``per_user_values(user_id, metric_value, n_games)`` for ``parity_rate_{tc}``.

    ``metric_value`` = (wins + 0.5 * draws) / parity_spans (chess-score formula,
    pooled over the recent-3000-per-TC × 36-month pool). ``n_games`` = parity
    span count (the binding floor ≥ MINIMUM_RATE_BUCKET_SPANS).

    No ``lead()`` / ``spans_with_next`` — rate is measured from game outcome,
    not ΔES delta.

    Source-mode parity and security identical to ``per_user_cte_conv_rate_tc``.
    """
    _ = source  # cohort difference is in selected_users_cte; pooled body is identical
    ueag = _user_elo_at_game_expr()
    return f"""{_recent_capped_per_tc_cte(snapshot_date, tc)},
spans AS (
  SELECT gp.game_id,
         (array_agg(gp.eval_cp   ORDER BY gp.ply ASC))[1] AS entry_eval_cp,
         (array_agg(gp.eval_mate ORDER BY gp.ply ASC))[1] AS entry_eval_mate
  FROM game_positions gp
  JOIN recent_capped rc ON rc.id = gp.game_id
  WHERE gp.endgame_class IS NOT NULL
  GROUP BY gp.game_id
  HAVING count(gp.ply) >= 6
),
bucket_rows AS (
  SELECT g.user_id,
    CASE
      WHEN s.entry_eval_mate IS NOT NULL THEN
        CASE
          WHEN (s.entry_eval_mate * (CASE WHEN g.user_color='white' THEN 1 ELSE -1 END)) > 0
          THEN 'conversion'
          ELSE 'recovery'
        END
      WHEN s.entry_eval_cp IS NOT NULL THEN
        CASE
          WHEN (s.entry_eval_cp * (CASE WHEN g.user_color='white' THEN 1 ELSE -1 END)) >= 100
          THEN 'conversion'
          WHEN (s.entry_eval_cp * (CASE WHEN g.user_color='white' THEN 1 ELSE -1 END)) <= -100
          THEN 'recovery'
          ELSE 'parity'
        END
      ELSE 'parity'
    END AS bucket,
    CASE
      WHEN (g.result='1-0' AND g.user_color='white') OR (g.result='0-1' AND g.user_color='black')
      THEN 1 ELSE 0
    END AS is_win,
    CASE WHEN g.result='1/2-1/2' THEN 1 ELSE 0 END AS is_draw
  FROM spans s
  JOIN games g ON g.id = s.game_id
  WHERE (s.entry_eval_cp IS NOT NULL OR s.entry_eval_mate IS NOT NULL)
    AND {ueag} >= {_SUB_800_FLOOR}
),
per_user AS (
  SELECT user_id,
    count(*) FILTER (WHERE bucket = 'parity') AS parity_n,
    sum(is_win)  FILTER (WHERE bucket = 'parity')::float AS parity_wins,
    sum(is_draw) FILTER (WHERE bucket = 'parity')::float AS parity_draws
  FROM bucket_rows
  GROUP BY user_id
  HAVING count(*) FILTER (WHERE bucket = 'parity') >= {MINIMUM_RATE_BUCKET_SPANS}
),
per_user_values AS (
  -- user_id widened per Phase 94.4 Pitfall 1 (cohort-CDF JOIN against per_user_anchor).
  SELECT user_id,
    (parity_wins + 0.5 * parity_draws) / NULLIF(parity_n, 0) AS metric_value,
    parity_n::int AS n_games
  FROM per_user
  WHERE parity_wins IS NOT NULL
)"""


def per_user_cte_recovery_rate_tc(
    tc: TimeControlBucket,
    *,
    source: Literal["benchmark", "single_user"],
    snapshot_date: date | None = None,
) -> str:
    """Pooled ``per_user_values(user_id, metric_value, n_games)`` for ``recovery_rate_{tc}``.

    ``metric_value`` = (wins + draws) / recov_spans (saves formula — both wins
    and draws count as successful recoveries, pooled over the recent-3000-per-TC
    × 36-month pool). ``n_games`` = recovery span count (the binding floor
    ≥ MINIMUM_RATE_BUCKET_SPANS).

    No ``lead()`` / ``spans_with_next`` — rate is measured from game outcome,
    not ΔES delta.

    Source-mode parity and security identical to ``per_user_cte_conv_rate_tc``.
    """
    _ = source  # cohort difference is in selected_users_cte; pooled body is identical
    ueag = _user_elo_at_game_expr()
    return f"""{_recent_capped_per_tc_cte(snapshot_date, tc)},
spans AS (
  SELECT gp.game_id,
         (array_agg(gp.eval_cp   ORDER BY gp.ply ASC))[1] AS entry_eval_cp,
         (array_agg(gp.eval_mate ORDER BY gp.ply ASC))[1] AS entry_eval_mate
  FROM game_positions gp
  JOIN recent_capped rc ON rc.id = gp.game_id
  WHERE gp.endgame_class IS NOT NULL
  GROUP BY gp.game_id
  HAVING count(gp.ply) >= 6
),
bucket_rows AS (
  SELECT g.user_id,
    CASE
      WHEN (s.entry_eval_mate IS NOT NULL
            AND (s.entry_eval_mate * (CASE WHEN g.user_color='white' THEN 1 ELSE -1 END)) > 0)
        OR (s.entry_eval_cp IS NOT NULL
            AND (s.entry_eval_cp * (CASE WHEN g.user_color='white' THEN 1 ELSE -1 END)) >= 100)
      THEN 'conversion'
      WHEN s.entry_eval_mate IS NOT NULL
        OR (s.entry_eval_cp IS NOT NULL
            AND (s.entry_eval_cp * (CASE WHEN g.user_color='white' THEN 1 ELSE -1 END)) <= -100)
      THEN 'recovery'
      ELSE 'parity'
    END AS bucket,
    CASE
      WHEN (g.result='1-0' AND g.user_color='white') OR (g.result='0-1' AND g.user_color='black')
      THEN 1 ELSE 0
    END AS is_win,
    CASE WHEN g.result='1/2-1/2' THEN 1 ELSE 0 END AS is_draw
  FROM spans s
  JOIN games g ON g.id = s.game_id
  WHERE (s.entry_eval_cp IS NOT NULL OR s.entry_eval_mate IS NOT NULL)
    AND {ueag} >= {_SUB_800_FLOOR}
),
per_user AS (
  SELECT user_id,
    count(*) FILTER (WHERE bucket = 'recovery') AS recov_n,
    sum(is_win)  FILTER (WHERE bucket = 'recovery')::float AS recov_wins,
    sum(is_draw) FILTER (WHERE bucket = 'recovery')::float AS recov_draws
  FROM bucket_rows
  GROUP BY user_id
  HAVING count(*) FILTER (WHERE bucket = 'recovery') >= {MINIMUM_RATE_BUCKET_SPANS}
),
per_user_values AS (
  -- user_id widened per Phase 94.4 Pitfall 1 (cohort-CDF JOIN against per_user_anchor).
  SELECT user_id,
    (recov_wins + recov_draws) / NULLIF(recov_n, 0) AS metric_value,
    recov_n::int AS n_games
  FROM per_user
  WHERE recov_wins IS NOT NULL
)"""


def _chesscom_conversion_values_sql(target_tc: TimeControlBucket) -> str:
    """Emit a VALUES body for the (chesscom_anchor, lichess_equiv) lookup table.

    The table is keyed on NATIVE chess.com ratings for the bucket's source TC
    (``_BUCKET_TO_CHESSCOM_SOURCE_TC``), and each ``lichess_equiv`` is produced
    by the canonical :func:`convert_chesscom_to_lichess` via
    :func:`composed_chesscom_to_lichess_grid` (single source of truth). Returns
    the VALUES expression body suitable for use inside a named CTE, e.g.:

        VALUES (735, 1205), (750, 1224), ...

    The returned string is intended for use inside a column-aliased CTE body:

        chesscom_conversion_lookup(chesscom_anchor, lichess_equiv) AS (
            {_chesscom_conversion_values_sql(tc)}
        )

    This is the standard PostgreSQL CTE VALUES pattern — the column names are
    declared in the CTE name clause, not via an alias on the VALUES expression.

    Bug fix: the previous implementation keyed the table on
    chess.com BLITZ anchors and read ``CHESSCOM_BLITZ_TO_LICHESS`` directly. The
    nearest-anchor LATERAL join then matched every chess.com game's native rating
    against blitz-scale anchors regardless of the game's actual TC, skipping the
    intra-TC inversion the canonical converter applies (inflated rapid/classical
    anchors, deflated bullet). Keying the grid on native chess.com ratings for
    the bucket's source TC (bullet->bullet, blitz->blitz, rapid->rapid,
    classical->rapid) makes the join correct.

    Security: the rows are generated from a Python-controlled snapshot via the
    converter — all values are Python ``int`` literals with no user-input
    injection surface.

    Raises:
        ValueError: if the composed grid is empty for ``target_tc`` (defensive —
            shouldn't happen for the 4 standard TCs).
    """
    source_tc = _BUCKET_TO_CHESSCOM_SOURCE_TC[target_tc]
    rows = composed_chesscom_to_lichess_grid(source_tc, target_tc)
    if not rows:
        raise ValueError(
            f"composed_chesscom_to_lichess_grid empty for source_tc={source_tc!r}, "
            f"target_tc={target_tc!r}"
        )
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

    Substrate for the peer-relative percentile chip lookup: the median anchor
    per (user, TC) is persisted in ``user_rating_anchors`` and later joined
    against the cohort CDF artifact to read the percentile.

    Two modes, selected by ``blend``:

    **Non-blend mode** (``blend=False``, default):

    Output CTE: ``per_user_anchor(user_id, anchor_rating INT, n_games INT)``.
    ``anchor_rating`` is ``percentile_cont(0.5) WITHIN GROUP (ORDER BY ...)::int``
    over the user's rating at game time (white_rating / black_rating, whichever
    side the user played); ``n_games`` is the count of games used (HAVING
    >= ``min_games``).

    The ``platform`` parameter restricts the join to a single platform:

    * ``None`` → no platform filter (both Lichess and chess.com games
      contribute to the median; the cohort CDF generator uses
      this form on the benchmark DB which is Lichess-only by construction).
    * ``'lichess'`` / ``'chesscom'`` → emit ``AND g.platform = '<value>'``.

    **Blended mode** (``blend=True``):

    Output CTE: ``per_user_anchor(user_id, anchor_rating INT, n_chesscom_games INT,
    n_lichess_games INT, chesscom_median_native INT, lichess_median_native INT)``.

    Per-game weighted blended anchor. chess.com (non-Daily) games are converted
    via the ``chesscom_conversion_lookup`` VALUES CTE, which is keyed on NATIVE
    chess.com ratings for this bucket's source TC (bullet->bullet, blitz->blitz,
    rapid->rapid, classical->rapid) and composed via the canonical
    ``convert_chesscom_to_lichess`` (``_chesscom_conversion_values_sql`` →
    ``composed_chesscom_to_lichess_grid``). Each chess.com game is matched to the
    nearest anchor row via
    ``ORDER BY ABS(rating_at_game_time - chesscom_anchor) LIMIT 1`` and the
    ``lichess_equiv`` is used as the blended rating. The native-rating keying
    means the nearest-anchor match applies the correct intra-TC inversion.
    Lichess games pass through their native rating
    unchanged. The per-user median of the combined (converted + native) pool is
    the blended ``anchor_rating``.

    ``blend=True`` with ``platform!=None`` is mutually exclusive and raises
    ``ValueError`` — blended mode pools both platforms inherently; a platform
    filter would defeat the purpose.

    Suppression rule:
    the HAVING clause applies to the POOLED count (n_chesscom_games +
    n_lichess_games >= min_games). A chess.com-Daily-only user in the
    ``classical`` bucket has zero qualifying games and produces no row.

    Worked example:
    4000 chess.com games @ 2200 (→ ~2050 lichess-equiv) + 100 lichess games
    @ 1900 → pooled median ≈ 2046 (game-weighted; heavy chess.com side dominates).

    ``n_chesscom_games``: count of non-Daily chess.com games in the pooled window.
    ``n_lichess_games``: count of lichess games in the pooled window.
    ``chesscom_median_native``: median of RAW chess.com ratings (pre-conversion);
      NULL when n_chesscom_games = 0. Tooltip-disclosure source.
    ``lichess_median_native``: median of native lichess ratings; NULL when
      n_lichess_games = 0. Tooltip-disclosure source.

    **Common documentation (both modes)**:

    Daily-classical drop: chess.com Daily games are bucketed ``classical`` by
    the import pipeline but are excluded from the median anchor via
    ``WHERE NOT (g.platform = 'chess.com' AND g.time_control_str LIKE '1/%')``.
    The drop is unconditional on ``tc`` for structural symmetry — Daily games
    are filtered out everywhere, not just when ``tc='classical'``. As a
    result, classical anchors may be absent for users who play only chess.com
    Daily, and the chip suppresses naturally for that (user, classical) cell.

    The ``source`` parameter is accepted for API symmetry with the other
    pooled builders (the cohort difference lives entirely in
    ``selected_users_cte``); the pooled body is identical on both paths, so
    the CDF and the per-user lookup cannot drift apart.

    Security: ``tc`` and ``platform`` are ``Literal`` parameters constrained
    by ty + Pydantic to the closed value set (4-value × 3-value matrix of
    known strings), so the f-string interpolation has no SQL-injection
    surface. ``min_games`` is an ``int``, safe to embed directly.
    ``snapshot_date.isoformat()`` emits only digits and dashes via the
    existing ``_recency_window_sql`` helper.
    The ``_chesscom_conversion_values_sql`` output is generated from
    Python-controlled snapshot data (a ``Final`` constant of Python ints) —
    no user-input injection surface. ``user_id`` flows through
    ``.bindparams()`` in the caller; never f-stringed here.

    f-string ``%`` convention: ``time_control_str LIKE '1/%'`` uses a single
    ``%`` — this module's builders return raw SQL passed to asyncpg via
    SQLAlchemy ``text()`` with ``:name``-style bindparams, NOT with Python
    ``%``-style formatting, so no ``%%`` doubling is required.
    """
    if blend and platform is not None:
        raise ValueError(
            "blend=True is mutually exclusive with platform!=None — "
            "blended mode pools both platforms inherently"
        )
    _ = source  # cohort difference is in selected_users_cte; pooled body is identical

    if blend:
        return _per_user_cte_median_anchor_blended(tc, snapshot_date, min_games)

    # --- Non-blend mode ---
    # ``platform`` is the AnchorSource Literal ('lichess' | 'chesscom') used by
    # the user_rating_anchors model, but the games table stores the chess.com
    # platform string with a dot (``platform='chess.com'``). Translate before
    # emitting the SQL filter so the (AnchorSource) → (games.platform) mapping
    # is the only place we paper over the discrepancy. The benchmark DB is
    # Lichess-only, so the chess.com path is not exercised there.
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
    (3000 games × ~50 lookup rows ≈ 150K comparisons per user per TC), which
    is acceptable.
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
  -- chess.com non-Daily: convert via nearest-anchor lookup. The lookup is keyed
  -- on NATIVE chess.com ratings for this bucket's source TC (bullet->bullet,
  -- blitz->blitz, rapid->rapid, classical->rapid) and composed via the canonical
  -- convert_chesscom_to_lichess, so the nearest-anchor match applies the correct
  -- intra-TC inversion (quick-260529-js1 fix; was keyed on chess.com Blitz
  -- anchors, which skipped the inversion and inflated rapid/classical anchors).
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


# ---------------------------------------------------------------------------
# "Out of the opening" worse/better builders (Phase 243).
# ---------------------------------------------------------------------------


def _opening_out_classified_cte() -> str:
    """The ``opening_out_mg_entry`` + ``opening_out_classified`` CTE pair.

    ``opening_out_classified(game_id, user_id, user_color, side)`` gives every slice
    game a ``side``: -1 worse, 0 even, +1 better, NULL non-qualifying (D-01, D-02).

    * Middlegame entry = the game's first ply with ``phase = 1``. ``gp.user_id =
      rc.user_id`` in the join lets the ``(user_id, game_id, ply)`` PK drive an
      index scan.
    * No middlegame ply: counts by result only for resignation / checkmate / timeout
      with a decisive result (win = +1, loss = -1); draws, abandoned, unknown and NULL
      termination are NULL.
    * Middlegame entry with a mate score: the sign of the mate in the user's POV
      (``eval_mate = 0`` is even).
    * Middlegame entry with ``eval_cp``: the user-POV eval minus the colour baseline,
      at or below -cut is worse, at or above +cut is better. The baselines render
      PARENTHESISED: an unparenthesised negative literal after a minus would form a
      ``--`` SQL line comment.
    * Both evals NULL: NULL (not a qualifying game).
    * Sub-800 games (rating at game time) are dropped, as in the other rate builders.
    """
    ueag = _user_elo_at_game_expr()
    colour_sign = "(CASE WHEN rc.user_color = 'white' THEN 1 ELSE -1 END)"
    baseline = (
        f"(CASE WHEN rc.user_color = 'white' THEN ({_OPENING_OUT_BASELINE_CP_WHITE}) "
        f"ELSE ({_OPENING_OUT_BASELINE_CP_BLACK}) END)"
    )
    centred = f"(me.eval_cp * {colour_sign} - {baseline})"
    return f"""opening_out_mg_entry AS (
  SELECT DISTINCT ON (gp.game_id) gp.game_id, gp.eval_cp, gp.eval_mate
  FROM game_positions gp
  JOIN recent_capped rc ON rc.id = gp.game_id AND gp.user_id = rc.user_id
  WHERE gp.phase = {_MIDDLEGAME_PHASE}
  ORDER BY gp.game_id, gp.ply
),
opening_out_classified AS (
  SELECT rc.id AS game_id, rc.user_id, rc.user_color::text AS user_color,
    CASE
      WHEN me.game_id IS NULL THEN
        CASE
          WHEN g.termination IN {_DECISIVE_EARLY_TERMINATIONS_SQL} AND g.result <> '1/2-1/2'
          THEN CASE WHEN (g.result = '1-0') = (rc.user_color = 'white') THEN 1 ELSE -1 END
        END
      WHEN me.eval_mate IS NOT NULL THEN sign(me.eval_mate)::int * {colour_sign}
      WHEN me.eval_cp IS NOT NULL THEN
        CASE
          WHEN {centred} <= -{_OPENING_OUT_CUT_CP} THEN -1
          WHEN {centred} >= {_OPENING_OUT_CUT_CP} THEN 1
          ELSE 0
        END
    END AS side
  FROM recent_capped rc
  JOIN games g ON g.id = rc.id
  LEFT JOIN opening_out_mg_entry me ON me.game_id = rc.id
  WHERE {ueag} >= {_SUB_800_FLOOR}
)"""


def per_user_cte_opening_out_counts(
    tc: TimeControlBucket,
    *,
    source: Literal["benchmark", "single_user"],
    snapshot_date: date | None = None,
) -> str:
    """Per-(user, colour) worse/better counts: ``per_user_color_counts``.

    Columns: ``user_id``, ``user_color`` (``'white'`` / ``'black'``), ``n_games``
    (qualifying games), ``worse_n``, ``better_n``. NO floor is applied: the on-read
    path shows "k of n" for colours below the floor, and the rate builder applies
    ``OPENING_OUT_MIN_GAMES_PER_COLOR`` on top of this same chain.

    The body is identical for both sources; the cohort difference lives only in
    ``selected_users_cte``. Up to two rows per user (one per colour).

    Security: only the ``TimeControlBucket`` Literal and int constants are
    interpolated; ``user_id`` flows only through the ``CAST(:user_id AS int)``
    bindparam in ``selected_users_cte``, bound via ``text(sql).bindparams(...)``.
    """
    _ = source  # cohort difference is in selected_users_cte; the body is identical
    return f"""{_recent_capped_per_tc_cte(snapshot_date, tc)},
{_opening_out_classified_cte()},
per_user_color_counts AS (
  SELECT user_id, user_color,
    count(side)::int AS n_games,
    (count(*) FILTER (WHERE side = -1))::int AS worse_n,
    (count(*) FILTER (WHERE side = 1))::int AS better_n
  FROM opening_out_classified
  GROUP BY user_id, user_color
)"""


def per_user_cte_opening_out_rate(
    tc: TimeControlBucket,
    *,
    metric: OpeningOutMetricId,
    source: Literal["benchmark", "single_user"],
    snapshot_date: date | None = None,
) -> str:
    """Per-(user, colour) ``per_user_values(user_id, user_color, metric_value, n_games)``.

    ``metric_value`` = worse_n (``opening_worse_rate``) or better_n
    (``opening_better_rate``) divided by the qualifying game count. Only colours with
    at least ``OPENING_OUT_MIN_GAMES_PER_COLOR`` qualifying games produce a row.

    Same source-mode parity and security as ``per_user_cte_opening_out_counts``;
    ``metric`` is the ``OpeningOutMetricId`` Literal, mapped to a fixed column name.
    """
    count_column = _OPENING_OUT_COUNT_COLUMN[metric]
    return f"""{per_user_cte_opening_out_counts(tc, source=source, snapshot_date=snapshot_date)},
per_user_values AS (
  SELECT user_id, user_color,
    {count_column}::float / n_games AS metric_value,
    n_games
  FROM per_user_color_counts
  WHERE n_games >= {OPENING_OUT_MIN_GAMES_PER_COLOR}
)"""
