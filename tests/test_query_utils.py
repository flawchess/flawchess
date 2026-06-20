"""Unit tests for apply_game_filters date predicates (Phase 92 D-10).

Tests verify that the from_date / to_date parameters produce the correct
SQL WHERE clauses: from_date uses >= and to_date uses < with a +1-day shift
so that to_date is inclusive (covers the whole day).

These tests are INTENTIONALLY written before the signature change (TDD RED):
they call apply_game_filters with from_date= / to_date= keyword args that
do not yet exist, so they will fail with a TypeError until Task 2 lands.

Phase 128 Plan 03 (Task 2 TDD RED): orientation dimension tests for apply_game_filters.
Tests assert that orientation="missed" produces EXISTS referencing missed_tactic_motif
and orientation="allowed" (default) references allowed_tactic_motif.
"""

import datetime

from sqlalchemy import select

from app.models.game import Game
from app.repositories.query_utils import apply_game_filters


def _compile_sql(stmt: object) -> str:
    """Compile stmt to a SQL string without literal binds (parameterised form)."""
    from sqlalchemy.dialects import postgresql

    return str(stmt.compile(dialect=postgresql.dialect(), compile_kwargs={"literal_binds": False}))  # ty: ignore[unresolved-attribute]


def _get_params(stmt: object) -> dict:
    """Return the bind parameters dict from the compiled statement."""
    from sqlalchemy.dialects import postgresql

    compiled = stmt.compile(dialect=postgresql.dialect(), compile_kwargs={"literal_binds": False})  # ty: ignore[unresolved-attribute]
    return dict(compiled.params)


def test_apply_game_filters_no_date_filter() -> None:
    """from_date=None, to_date=None — no played_at predicate in WHERE clause."""
    stmt = select(Game)
    stmt = apply_game_filters(
        stmt,
        time_control=None,
        platform=None,
        rated=None,
        opponent_type="human",
        from_date=None,
        to_date=None,
    )
    sql = _compile_sql(stmt)
    # No date predicates should appear.
    assert "played_at >= " not in sql, f"Unexpected from_date predicate: {sql}"
    assert "played_at < " not in sql, f"Unexpected to_date predicate: {sql}"


def test_apply_game_filters_from_only() -> None:
    """from_date set, to_date=None — only the >= predicate appears."""
    stmt = select(Game)
    stmt = apply_game_filters(
        stmt,
        time_control=None,
        platform=None,
        rated=None,
        opponent_type="human",
        from_date=datetime.date(2026, 3, 1),
        to_date=None,
    )
    sql = _compile_sql(stmt)
    params = _get_params(stmt)

    # Lower-bound predicate must appear.
    assert "played_at >=" in sql, f"Missing from_date predicate: {sql}"
    # Upper-bound predicate must NOT appear.
    assert "played_at <" not in sql, f"Unexpected to_date predicate: {sql}"
    # The bind value must match the supplied from_date.
    from_val = next(
        (v for k, v in params.items() if "from_date" in k or "played_at" in k.lower()), None
    )
    assert from_val == datetime.date(2026, 3, 1) or any(
        v == datetime.date(2026, 3, 1) for v in params.values()
    ), f"Expected bind value 2026-03-01 in params: {params}"


def test_apply_game_filters_to_only() -> None:
    """to_date set, from_date=None — only the < predicate appears."""
    stmt = select(Game)
    stmt = apply_game_filters(
        stmt,
        time_control=None,
        platform=None,
        rated=None,
        opponent_type="human",
        from_date=None,
        to_date=datetime.date(2026, 4, 1),
    )
    sql = _compile_sql(stmt)

    # Upper-bound predicate must appear.
    assert "played_at <" in sql, f"Missing to_date predicate: {sql}"
    # Lower-bound predicate must NOT appear.
    assert "played_at >=" not in sql, f"Unexpected from_date predicate: {sql}"


def test_apply_game_filters_date_range() -> None:
    """Both bounds set — both predicates appear; upper bound is shifted +1 day.

    D-10: the upper bound uses ``<  to_date + 1 day`` so that to_date itself
    is inclusive (covers up to end-of-day in UTC without timezone math).
    """
    stmt = select(Game)
    to_date = datetime.date(2026, 4, 1)
    stmt = apply_game_filters(
        stmt,
        time_control=None,
        platform=None,
        rated=None,
        opponent_type="human",
        from_date=datetime.date(2026, 3, 1),
        to_date=to_date,
    )
    sql = _compile_sql(stmt)
    params = _get_params(stmt)

    # Both predicates must appear.
    assert "played_at >=" in sql, f"Missing from_date predicate: {sql}"
    assert "played_at <" in sql, f"Missing to_date predicate: {sql}"

    # The upper bound must be shifted by +1 day (2026-04-02, not 2026-04-01).
    expected_upper = datetime.date(2026, 4, 2)
    assert expected_upper in params.values(), (
        f"Expected upper bound {expected_upper} (to_date + 1 day) in params: {params}"
    )


# ---------------------------------------------------------------------------
# Phase 128 Plan 03 (Task 2 TDD) — orientation dimension tests (D-09)
# ---------------------------------------------------------------------------


class TestTacticOrientationFilter:
    """orientation param in apply_game_filters selects the correct column set.

    Phase 128 D-09: orientation selects the matching column pair at both filter
    sites. Unknown-family keys still yield no ints (no-op). Orientation is a
    closed Literal enum — never raw column-name interpolation (T-128-05).
    """

    _BASE_FAMILIES = ["fork"]  # single known family to get a non-empty motif int set

    def _stmt_sql(self, orientation: str | None = None) -> str:
        """Return compiled SQL for apply_game_filters with tactic_families=[fork]."""
        stmt = select(Game.id).where(Game.user_id == 1)
        kwargs: dict = dict(
            time_control=None,
            platform=None,
            rated=None,
            opponent_type="all",
            from_date=None,
            to_date=None,
            user_id=1,
            tactic_families=self._BASE_FAMILIES,
        )
        if orientation is not None:
            kwargs["orientation"] = orientation
        stmt = apply_game_filters(stmt, **kwargs)
        from sqlalchemy.dialects import postgresql

        return str(
            stmt.compile(
                dialect=postgresql.dialect(),
                compile_kwargs={"literal_binds": False},
            )
        )

    def test_default_orientation_references_allowed_column(self) -> None:
        """orientation unspecified (default) → EXISTS uses allowed_tactic_motif.

        Preserves current Library behavior (D-08): callers that omit orientation
        see the same behavior as before.
        """
        sql = self._stmt_sql()
        assert "allowed_tactic_motif" in sql, (
            f"Default orientation must reference allowed_tactic_motif; got: {sql}"
        )
        assert "missed_tactic_motif" not in sql, (
            f"Default orientation must NOT reference missed_tactic_motif; got: {sql}"
        )

    def test_allowed_orientation_references_allowed_column(self) -> None:
        """orientation='allowed' → EXISTS uses allowed_tactic_motif."""
        sql = self._stmt_sql(orientation="allowed")
        assert "allowed_tactic_motif" in sql, (
            f"orientation='allowed' must reference allowed_tactic_motif; got: {sql}"
        )
        assert "missed_tactic_motif" not in sql, (
            f"orientation='allowed' must NOT reference missed_tactic_motif; got: {sql}"
        )

    def test_missed_orientation_references_missed_column(self) -> None:
        """orientation='missed' → EXISTS uses missed_tactic_motif.

        The same FAMILY_TO_MOTIF_INTS expansion and EXISTS structure is used;
        only the column name changes (D-09).
        """
        sql = self._stmt_sql(orientation="missed")
        assert "missed_tactic_motif" in sql, (
            f"orientation='missed' must reference missed_tactic_motif; got: {sql}"
        )
        assert "allowed_tactic_motif" not in sql, (
            f"orientation='missed' must NOT reference allowed_tactic_motif; got: {sql}"
        )

    def test_unknown_family_is_noop_for_both_orientations(self) -> None:
        """Unknown family keys → no EXISTS clause added (no-op, T-126-02 preserved)."""
        for orientation in ("allowed", "missed"):
            stmt = select(Game.id).where(Game.user_id == 1)
            stmt = apply_game_filters(
                stmt,
                time_control=None,
                platform=None,
                rated=None,
                opponent_type="all",
                from_date=None,
                to_date=None,
                user_id=1,
                tactic_families=["not_a_real_family"],
                orientation=orientation,  # type: ignore[arg-type]
            )
            from sqlalchemy.dialects import postgresql

            sql = str(
                stmt.compile(
                    dialect=postgresql.dialect(),
                    compile_kwargs={"literal_binds": False},
                )
            )
            assert "tactic_motif" not in sql, (
                f"Unknown family with orientation={orientation!r} must produce no tactic EXISTS clause; got: {sql}"
            )


# ---------------------------------------------------------------------------
# Phase 129 Plan 01 (Task 1 TDD RED) — depth + either tests for apply_game_filters
# ---------------------------------------------------------------------------


class TestTacticDepthAndEitherFilter:
    """max_tactic_depth + orientation='either' in apply_game_filters.

    Phase 129 D-05/D-08: depth bound on the active orientation's depth column;
    'either' = OR across both missed_* and allowed_* column sets.
    These tests target apply_game_filters (Games-EXISTS site, no confidence gate).
    """

    def _stmt_sql(
        self,
        orientation: str = "allowed",
        max_tactic_depth: int | None = None,
    ) -> str:
        """Compile apply_game_filters with tactic_families=['fork'] to SQL text."""
        stmt = select(Game.id).where(Game.user_id == 1)
        kwargs: dict = dict(
            time_control=None,
            platform=None,
            rated=None,
            opponent_type="all",
            from_date=None,
            to_date=None,
            user_id=1,
            tactic_families=["fork"],
            orientation=orientation,
        )
        if max_tactic_depth is not None:
            kwargs["max_tactic_depth"] = max_tactic_depth
        stmt = apply_game_filters(stmt, **kwargs)
        from sqlalchemy.dialects import postgresql

        return str(
            stmt.compile(
                dialect=postgresql.dialect(),
                compile_kwargs={"literal_binds": False},
            )
        )

    def test_either_references_both_columns(self) -> None:
        """orientation='either' → EXISTS clause references BOTH missed and allowed motif columns."""
        sql = self._stmt_sql(orientation="either")
        assert "missed_tactic_motif" in sql, (
            f"either orientation must reference missed_tactic_motif; got: {sql}"
        )
        assert "allowed_tactic_motif" in sql, (
            f"either orientation must reference allowed_tactic_motif; got: {sql}"
        )

    def test_depth_none_omits_depth_column(self) -> None:
        """max_tactic_depth=None → no depth column in the clause."""
        sql = self._stmt_sql(orientation="allowed", max_tactic_depth=None)
        # No depth predicate when no bound is set
        assert "allowed_tactic_depth" not in sql, (
            f"max_tactic_depth=None must NOT add allowed_tactic_depth predicate; got: {sql}"
        )

    def test_depth_bound_references_depth_column(self) -> None:
        """max_tactic_depth=3 → clause includes the orientation's depth column."""
        sql = self._stmt_sql(orientation="allowed", max_tactic_depth=3)
        assert "allowed_tactic_depth" in sql, (
            f"max_tactic_depth=3 must add allowed_tactic_depth predicate; got: {sql}"
        )
        assert "missed_tactic_depth" not in sql, (
            f"allowed orientation must NOT reference missed_tactic_depth; got: {sql}"
        )

    def test_missed_depth_bound_references_missed_depth_column(self) -> None:
        """orientation='missed' + max_tactic_depth=3 → missed_tactic_depth predicate."""
        sql = self._stmt_sql(orientation="missed", max_tactic_depth=3)
        assert "missed_tactic_depth" in sql, (
            f"missed orientation + depth bound must add missed_tactic_depth predicate; got: {sql}"
        )
        assert "allowed_tactic_depth" not in sql, (
            f"missed orientation must NOT reference allowed_tactic_depth; got: {sql}"
        )

    def test_mate_exemption_present_when_depth_set(self) -> None:
        """When depth is bounded, the mate motif int(s) appear in the clause (exemption escape)."""
        # The mate exemption is: depth_col <= max OR motif_col IN (mate_ints).
        # Since the mate family is not in tactic_families=['fork'], the mate ints appear
        # only in the depth-exemption OR — not in the primary motif filter.
        sql = self._stmt_sql(orientation="allowed", max_tactic_depth=3)
        # Mate ints from FAMILY_TO_MOTIF_INTS['mate'] (e.g. BACK_RANK_MATE=10, MATE=11, ...)
        # should appear in the SQL as part of the depth exemption OR.
        assert "allowed_tactic_depth" in sql  # depth predicate is present
        # The clause must also include OR motif_col.in_(mate_ints) so mates are exempt.
        # We check the motif column appears more than once (primary filter + exemption).
        motif_occurrences = sql.count("allowed_tactic_motif")
        assert motif_occurrences >= 2, (
            f"Mate exemption requires allowed_tactic_motif to appear at least twice "
            f"(primary filter + depth exemption OR); got {motif_occurrences} in: {sql}"
        )

    def test_either_depth_references_both_depth_columns(self) -> None:
        """orientation='either' + max_tactic_depth → both missed and allowed depth columns."""
        sql = self._stmt_sql(orientation="either", max_tactic_depth=3)
        assert "missed_tactic_depth" in sql, (
            f"either + depth must reference missed_tactic_depth; got: {sql}"
        )
        assert "allowed_tactic_depth" in sql, (
            f"either + depth must reference allowed_tactic_depth; got: {sql}"
        )

    def test_no_confidence_gate_in_exists_site(self) -> None:
        """Games-EXISTS site (apply_game_filters) must NOT add a confidence predicate.

        Preserve the intentional asymmetry (Pitfall 3): confidence is gated only
        in build_flaw_filter_clauses (Flaws list), NOT in the Games-EXISTS.
        """
        for orientation in ("allowed", "missed", "either"):
            sql = self._stmt_sql(orientation=orientation)
            assert "tactic_confidence" not in sql, (
                f"apply_game_filters orientation={orientation!r} must NOT gate on confidence; got: {sql}"
            )
