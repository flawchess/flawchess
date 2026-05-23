"""Tests for app.services.canonical_slice_sql — Phase 94.1 Plan 01 Wave 0.

Extended in Plan 03 to cover the ``apply_floor`` dual-mode (RESEARCH Open Q3):
  ``test_per_user_cte_for_apply_floor_toggle`` asserts that
  ``apply_floor=True`` (default) retains the per-metric HAVING gate and
  ``apply_floor=False`` drops it entirely.

These tests define the contract for the shared SQL module that Plan 03 will
implement. The module does not exist yet; ``pytest.importorskip`` at module
level causes the entire file to be skipped gracefully until Plan 03 ships it.

Cross-consumer drift guard (RESEARCH Pitfall 8 / D-11):
  Once the module exists, ``test_per_user_cte_for_all_four_metrics_byte_identical_shared_fragments``
  asserts that the shared SQL building blocks are byte-identical between the
  ``"benchmark"`` and ``"single_user"`` consumers, catching any future
  edit that diverges the two paths inadvertently.
"""

from __future__ import annotations

import pytest

# Skip the entire module gracefully if app.services.canonical_slice_sql
# has not been created yet (Plan 03 ships it). CI stays green; once
# Plan 03 lands, the skip is removed and every test becomes active.
canonical_slice_sql = pytest.importorskip(
    "app.services.canonical_slice_sql",
    reason="canonical_slice_sql not implemented yet; will pass after Plan 03",
)

# The 4 metric IDs Phase 94.1 chips (mirrors CdfMetricId in global_percentile_cdf).
METRIC_IDS: tuple[str, ...] = (
    "score_gap",
    "achievable_score_gap",
    "section2_score_gap_conv",
    "section2_score_gap_parity",
)


# ---------------------------------------------------------------------------
# Test 1 — equal_footing_filter_sql is a pure deterministic string
# ---------------------------------------------------------------------------


def test_equal_footing_filter_sql_is_constant() -> None:
    """Repeated calls return byte-identical strings (pure function, no mutable state)."""
    fn = canonical_slice_sql.equal_footing_filter_sql
    first = fn()
    second = fn()
    assert first == second, "equal_footing_filter_sql must be deterministic"
    # Snapshot check: the clause must reference the ±100 ELO tolerance.
    assert "<= 100" in first, "equal_footing_filter clause must contain '<= 100'"
    assert "white_rating" in first or "g.user_color" in first, (
        "clause must reference game ratings and user color"
    )
    assert len(first) > 20, "clause must not be empty"


# ---------------------------------------------------------------------------
# Test 2 — sparse_exclusion_sql substitutes column names cleanly
# ---------------------------------------------------------------------------


def test_sparse_exclusion_sql_parametrises_columns() -> None:
    """Column-name substitution does not produce SQL injection vectors.

    Callers provide column *names* (identifiers), not user input.
    Security note (V5 mitigation): the boundary for user_id parameterisation
    is the SQLAlchemy bindparam seam in the query builder, not here.
    """
    fn = canonical_slice_sql.sparse_exclusion_sql

    # Standard production call shape
    standard = fn("elo_bucket", "tc_bucket")
    assert "elo_bucket" in standard
    assert "tc_bucket" in standard
    assert "2400" in standard
    assert "classical" in standard

    # Alternative column aliases (e.g. from a subquery alias)
    alt = fn("elo_col_alias", "tc_col_alias")
    assert "elo_col_alias" in alt
    assert "tc_col_alias" in alt
    assert "2400" in alt

    # The two variants differ only in the column names
    assert standard != alt, "Different column names must produce different SQL"

    # No raw string injection vector: the output must not contain semicolons
    # or UNION/DROP keywords that would indicate accidental injection.
    for result in (standard, alt):
        lowered = result.lower()
        assert ";" not in result, "sparse_exclusion_sql must not contain ';'"
        assert "union" not in lowered, "sparse_exclusion_sql must not contain UNION"
        assert "drop" not in lowered, "sparse_exclusion_sql must not contain DROP"


# ---------------------------------------------------------------------------
# Test 3 — elo_bucket_expr produces a CASE WHEN structure
# ---------------------------------------------------------------------------


def test_elo_bucket_expr_format() -> None:
    """CASE WHEN structure matches the canonical ELO bucketing (SKILL.md §1)."""
    fn = canonical_slice_sql.elo_bucket_expr

    expr = fn("user_elo_at_game")
    lowered = expr.lower()

    assert "case when" in lowered, "elo_bucket_expr must produce a CASE WHEN expression"
    assert "user_elo_at_game" in expr, "alias must appear in the output"

    # 5 canonical ELO anchors: 800, 1200, 1600, 2000, 2400
    for anchor in ("800", "1200", "1600", "2000", "2400"):
        assert anchor in expr, f"ELO anchor {anchor} missing from elo_bucket_expr"

    # NULL for sub-800 (SKILL.md §1 "Rating-lag selection bias")
    assert "null" in lowered, "elo_bucket_expr must return NULL for sub-800 ratings"

    # A different alias should appear in the expression, not the original
    expr_alt = fn("g_elo")
    assert "g_elo" in expr_alt
    assert "user_elo_at_game" not in expr_alt


# ---------------------------------------------------------------------------
# Test 4 — selected_users_cte shape differs between sources
# ---------------------------------------------------------------------------


def test_selected_users_cte_benchmark_vs_single_user() -> None:
    """CTE shape: benchmark joins benchmark tables; single_user is a scalar select."""
    fn = canonical_slice_sql.selected_users_cte

    benchmark = fn(source="benchmark")
    single = fn(source="single_user")

    # Both must declare the CTE name
    assert "selected_users" in benchmark
    assert "selected_users" in single

    # Benchmark shape: joins to benchmark_selected_users + benchmark_ingest_checkpoints
    assert "benchmark_selected_users" in benchmark
    assert "benchmark_ingest_checkpoints" in benchmark
    assert "status = 'completed'" in benchmark

    # Single-user shape: scalar select with user_id bindparam; NO benchmark tables
    assert "benchmark_selected_users" not in single
    assert "benchmark_ingest_checkpoints" not in single
    # Must reference :user_id (SQLAlchemy bindparam for the specific user)
    assert ":user_id" in single or "user_id" in single

    # The two shapes must be distinct
    assert benchmark != single


# ---------------------------------------------------------------------------
# Test 5 — per_user_cte_for: shared fragments are byte-identical (D-11 drift guard)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("metric_id", METRIC_IDS)
def test_per_user_cte_for_all_four_metrics_byte_identical_shared_fragments(
    metric_id: str,
) -> None:
    """Shared SQL building blocks are byte-identical between benchmark and single_user.

    This is the byte-identical cross-consumer drift guard (RESEARCH Pitfall 8).
    If a future edit changes a shared fragment for one consumer only, this test
    catches the drift on every CI run.
    """
    benchmark_cte = canonical_slice_sql.per_user_cte_for(
        metric_id,
        source="benchmark",  # type: ignore[arg-type]
    )
    single_cte = canonical_slice_sql.per_user_cte_for(
        metric_id,
        source="single_user",  # type: ignore[arg-type]
    )

    equal_footing = canonical_slice_sql.equal_footing_filter_sql()
    sparse_excl = canonical_slice_sql.sparse_exclusion_sql("elo_bucket", "tc_bucket")
    elo_expr = canonical_slice_sql.elo_bucket_expr(
        "(CASE WHEN g.user_color::text='white' THEN g.white_rating ELSE g.black_rating END)"
    )

    # The shared fragments must appear byte-identically in BOTH variants.
    assert equal_footing in benchmark_cte, (
        f"equal_footing fragment missing from benchmark CTE for {metric_id}"
    )
    assert equal_footing in single_cte, (
        f"equal_footing fragment missing from single_user CTE for {metric_id}"
    )

    assert sparse_excl in benchmark_cte, (
        f"sparse_exclusion fragment missing from benchmark CTE for {metric_id}"
    )
    assert sparse_excl in single_cte, (
        f"sparse_exclusion fragment missing from single_user CTE for {metric_id}"
    )

    assert elo_expr in benchmark_cte, f"elo_bucket_expr missing from benchmark CTE for {metric_id}"
    assert elo_expr in single_cte, f"elo_bucket_expr missing from single_user CTE for {metric_id}"


# ---------------------------------------------------------------------------
# Test 6 — per_user_cte_for(source="single_user") drops the per-TC predicate (D-09)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("metric_id", METRIC_IDS)
def test_per_user_cte_single_user_drops_tc_bucket_predicate(metric_id: str) -> None:
    """TC-bucket equality predicate present in benchmark, absent in single_user (D-09).

    The canonical slice for a single user pools across all time controls
    (no per-TC cap), so the ``g.time_control_bucket::text = su.tc_bucket``
    join predicate that restricts benchmark rows to a specific TC must be
    dropped in the single_user path.
    """
    tc_predicate = "g.time_control_bucket::text = su.tc_bucket"

    benchmark_cte = canonical_slice_sql.per_user_cte_for(
        metric_id,
        source="benchmark",  # type: ignore[arg-type]
    )
    single_cte = canonical_slice_sql.per_user_cte_for(
        metric_id,
        source="single_user",  # type: ignore[arg-type]
    )

    assert tc_predicate in benchmark_cte, (
        f"TC-bucket predicate must be PRESENT in benchmark CTE for {metric_id}"
    )
    assert tc_predicate not in single_cte, (
        f"TC-bucket predicate must be ABSENT in single_user CTE for {metric_id} "
        f"(D-09: pooled across TCs, no per-TC cap)"
    )


# ---------------------------------------------------------------------------
# Test 7 — apply_floor dual-mode: HAVING gate present/absent (added in Plan 03)
# ---------------------------------------------------------------------------


# Per-metric HAVING fragments that uniquely identify the inclusion-floor gate.
# These are the HAVING clauses on the per-user/per-user-bucket aggregation CTEs,
# NOT the structural "HAVING count(*) >= 6" clause used in endgame_game_ids /
# spans which is always present regardless of apply_floor.
_FLOOR_HAVING_FRAGMENTS: dict[str, str] = {
    "score_gap": "HAVING count(*) FILTER (WHERE has_endgame)",
    "achievable_score_gap": "HAVING count(*) FILTER (WHERE d_i IS NOT NULL)",
    "section2_score_gap_conv": "HAVING count(*) >= 20",
    "section2_score_gap_parity": "HAVING count(*) >= 20",
}


@pytest.mark.parametrize("metric_id", METRIC_IDS)
def test_per_user_cte_for_apply_floor_toggle(metric_id: str) -> None:
    """Inclusion-floor HAVING gate is present with apply_floor=True (default).

    And absent with apply_floor=False — so Plan 05 can emit a row with a
    value but percentile=NULL for users below the inclusion floor (RESEARCH
    Open Q3 / D-10 "percentile=NULL + value stored" recommendation).

    Note: structural HAVING clauses (e.g. ``HAVING count(*) >= 6`` inside
    ``endgame_game_ids`` / ``spans``) are always present — they are data-quality
    filters on span length, not inclusion-floor gates on per-user sample size.
    Only the per-user / per-user-bucket HAVING that enforces the inclusion
    floor (>= 20 or >= 30 games) is toggled by apply_floor.
    """
    floor_fragment = _FLOOR_HAVING_FRAGMENTS[metric_id]

    cte_with_floor = canonical_slice_sql.per_user_cte_for(
        metric_id,
        source="single_user",  # type: ignore[arg-type]
        apply_floor=True,
    )
    cte_no_floor = canonical_slice_sql.per_user_cte_for(
        metric_id,
        source="single_user",  # type: ignore[arg-type]
        apply_floor=False,
    )

    # apply_floor=True (default) must contain the inclusion-floor HAVING gate.
    assert floor_fragment in cte_with_floor, (
        f"apply_floor=True must include inclusion-floor HAVING gate for {metric_id}: "
        f"expected fragment {floor_fragment!r}"
    )

    # apply_floor=False must NOT contain the inclusion-floor HAVING gate.
    assert floor_fragment not in cte_no_floor, (
        f"apply_floor=False must drop the inclusion-floor HAVING gate for {metric_id}: "
        f"fragment {floor_fragment!r} must be absent "
        f"(RESEARCH Open Q3 / D-10 'percentile=NULL + value stored' path)"
    )

    # The two variants must differ (the floor HAVING is the only difference).
    assert cte_with_floor != cte_no_floor, (
        f"apply_floor=True and apply_floor=False must produce different SQL for {metric_id}"
    )

    # Also verify the default (no apply_floor arg) matches apply_floor=True.
    cte_default = canonical_slice_sql.per_user_cte_for(
        metric_id,
        source="single_user",  # type: ignore[arg-type]
    )
    assert cte_default == cte_with_floor, (
        f"Default apply_floor must equal apply_floor=True for {metric_id}"
    )


# ---------------------------------------------------------------------------
# Test 8 — single_user bindparam round-trip (Phase 94.1 Plan 09 gap-closure)
# ---------------------------------------------------------------------------


class TestSingleUserBindparamRoundTrip:
    """Regression guard for the `:user_id::int` parser bug.

    Phase 94.1 Plan 09 closes VERIFICATION.md gap #1: SQLAlchemy's `text()`
    tokeniser silently fails to recognise `:user_id` when immediately followed
    by the Postgres `::int` cast operator. The fix uses the explicit
    `CAST(:user_id AS int)` form so the bindparam IS detected. Without these
    tests, the next agent who "simplifies" the CAST back to `::int` would
    re-ship the silent failure.
    """

    def test_single_user_cte_bindparam_is_detected_by_sqlalchemy(self) -> None:
        """SQLAlchemy text().compile().params must list `user_id` as a bindparam."""
        from sqlalchemy import text

        sql = canonical_slice_sql.selected_users_cte(source="single_user")
        params = list(text(sql).compile().params)
        assert params == ["user_id"], (
            f"expected exactly one bindparam 'user_id', got {params!r} "
            f"(SQLAlchemy did not detect :user_id — the `::int` shorthand "
            f"cast confuses the tokeniser; use CAST(:user_id AS int))"
        )

    def test_single_user_cte_uses_cast_form_not_shorthand(self) -> None:
        """Source must contain CAST(:user_id AS int), never :user_id::int."""
        sql = canonical_slice_sql.selected_users_cte(source="single_user")
        assert "CAST(:user_id AS int)" in sql, (
            "single_user CTE must use the explicit CAST() form so SQLAlchemy's "
            "text() parser detects the bindparam"
        )
        assert ":user_id::int" not in sql, (
            "the `:user_id::int` shorthand cast confuses SQLAlchemy's tokeniser "
            "and silently drops the bindparam (VERIFICATION.md gap #1)"
        )

    def test_single_user_cte_emits_tc_bucket_column(self) -> None:
        """single_user CTE must project tc_bucket so downstream `su.tc_bucket` resolves.

        REVIEW.md WR-03 surfaced the latent bug: downstream per-metric CTEs
        all reference `su.tc_bucket AS tc_bucket`, but the single_user CTE
        previously emitted only `user_id`. The fix emits `NULL::text AS
        tc_bucket` (the per-user path pools across TCs anyway, so no real
        bucket value is needed; NULL satisfies the sparse-cell exclusion
        and lets the projection compile).
        """
        sql = canonical_slice_sql.selected_users_cte(source="single_user")
        assert "tc_bucket" in sql, (
            "single_user CTE must project a tc_bucket column so downstream "
            "su.tc_bucket references resolve (REVIEW.md WR-03)"
        )

    def test_single_user_cte_bindparam_round_trip_does_not_raise(self) -> None:
        """text(...).bindparams(user_id=42) must NOT raise ArgumentError."""
        from sqlalchemy import text

        sql = canonical_slice_sql.selected_users_cte(source="single_user")
        wrapped = f"WITH {sql} SELECT user_id FROM selected_users"
        # If the parser failed to detect the bindparam, this line raises:
        #   sqlalchemy.exc.ArgumentError: This text() construct doesn't define
        #   a bound parameter named 'user_id'
        bound = text(wrapped).bindparams(user_id=42)
        assert bound is not None

    def test_benchmark_cte_unchanged_regression_guard(self) -> None:
        """The benchmark branch is byte-identical to its pre-change form.

        Only the single_user branch changes in Plan 09; if a future edit
        inadvertently disturbs the benchmark CTE (which the byte-identical
        CDF regression gate in `tests/scripts/test_gen_global_percentile_cdf_unchanged.py`
        also enforces from the script side), this test catches it earlier.
        """
        expected = """selected_users AS (
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
        actual = canonical_slice_sql.selected_users_cte(source="benchmark")
        assert actual == expected, (
            "benchmark CTE drifted from its pre-Plan-09 form; only the "
            "single_user branch is supposed to change in Plan 09"
        )
