"""Shared query utilities for repository filter operations."""

import datetime
from collections.abc import Sequence
from typing import Any, Literal, cast, get_args

from sqlalchemy import Integer, and_, any_, bindparam, case, literal, or_
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.sql.elements import ColumnElement

from app.models.game import Game

# ---------------------------------------------------------------------------
# Ply-parity convention (single source)
# ---------------------------------------------------------------------------
# Even ply → white mover; odd ply → black mover.
# This mirrors _run_all_moves_pass in flaws_service.py:
#     mover = "white" if n % 2 == 0 else "black"
# A prior off-by-one bug lived here, hence the single source.
# Do NOT scatter ply % 2 math across query sites — always use is_opponent_expr.
_PLY_EVEN_MOVER_WHITE = 0  # ply % 2 == 0 means white moved

# ---------------------------------------------------------------------------
# Default platform exclusion (single source)
# ---------------------------------------------------------------------------
# Flawchess bot-practice games must stay invisible to every default analytics
# population while remaining reachable by any caller that passes an
# explicit platform list including "flawchess" (e.g. library_service's
# get_library_games opt-in). This is the ONE central seam — do not
# scatter per-router platform checks.
#
# A pasted PGN (platform="pgn") is excluded for the same reason and the same
# way. Pasted games are frequently NOT the user's own — a
# broadcast game, a friend's PGN, a scouted opponent — so they must never
# reach an analytics population. A pasted game that genuinely IS the user's
# own doesn't count either: import it from the platform it was actually
# played on. Unlike "flawchess", "pgn" has no default opt-in anywhere; the
# Library's "Pasted" filter chip opts back in by passing an
# explicit `platform=["pgn"]` list, which the existing `platform is not None`
# branch below already honors with no new plumbing.
DEFAULT_EXCLUDED_PLATFORMS = ("flawchess", "pgn")

# Every value of the Platform Literal (app/schemas/normalization.py) must
# appear in EXACTLY ONE of DEFAULT_EXCLUDED_PLATFORMS or
# ANALYTICS_INCLUDED_PLATFORMS — a future platform value that is added to one
# without a decision for the other is a silent analytics-eligibility bug.
# tests/repositories/test_query_utils.py::test_every_platform_has_an_analytics_disposition
# enforces this invariant by comparing typing.get_args(Platform) against the
# union of the two tuples.
#
# AnalyticsPlatform is the type-level twin of the tuple below, derived via
# get_args() so the two are structurally impossible to
# drift apart (rather than merely documented as agreeing). Exported for
# current_strength_repository / current_strength_service to import and cast
# a raw platform string once apply_game_filters(platform=None) has already
# excluded every other Platform member.
AnalyticsPlatform = Literal["chess.com", "lichess"]
ANALYTICS_INCLUDED_PLATFORMS: tuple[str, ...] = get_args(AnalyticsPlatform)


def mover_is_white_at_ply(ply: int) -> bool:
    """Return True when the mover at *ply* is White (Python read-path helper).

    Mirrors the SQL convention in is_opponent_expr — both derive from the same
    _PLY_EVEN_MOVER_WHITE constant so the Python and SQL paths agree on ply parity.
    Use this instead of bare ``ply % 2 == 0`` to keep the single source intact.
    """
    return ply % 2 == _PLY_EVEN_MOVER_WHITE


def is_opponent_expr(
    ply_col: Any,
    user_color_col: Any,
) -> ColumnElement[bool]:
    """Return a SQL expression that is True when the mover at ply_col is the OPPONENT.

    Convention (mirrors _run_all_moves_pass in flaws_service.py):
        even ply → white mover → is_opponent iff user_color == 'black'
        odd ply  → black mover → is_opponent iff user_color == 'white'

    Single source of the ply-parity convention. Unit-tested for all 4
    (ply parity × user_color) combinations (TestIsOpponentExpr). A prior
    off-by-one bug lived here.

    Args:
        ply_col: A column or literal expression resolving to the ply integer.
                 Accepts ColumnElement[int] or ORM InstrumentedAttribute[int]
                 (typed as Any because ty does not recognise InstrumentedAttribute
                 as a ColumnElement subtype — they share SQLColumnExpression lineage).
        user_color_col: A column or literal expression resolving to 'white'/'black'.
                 Same Any widening reason as ply_col.

    Returns:
        A SQLAlchemy ColumnElement[bool] usable in WHERE/FILTER clauses.
    """
    return case(
        (ply_col % 2 == _PLY_EVEN_MOVER_WHITE, user_color_col == "black"),
        else_=user_color_col == "white",
    )


def mover_color_expr(ply_col: Any) -> ColumnElement[str]:
    """Return a SQL expression yielding the mover's color ('white'/'black') at ply_col.

    SQL twin of `mover_color_for_ply` (app/services/best_move_candidates.py:65-68):
    even ply -> white, odd ply -> black. It exists so a caller that has a ply
    column but no `Game` join can still name the mover — e.g. Train's dead-band
    predicate (`app/services/train_pool.py`'s `dead_band_admissible`), which is
    applied at a COUNT statement that deliberately drops the `Game` join
    (`get_waiting_puzzle_count`'s due-count statement). This module is already
    documented as the single source of the ply-parity convention (see the module
    docstring above) — a second parity expression elsewhere is exactly what
    CLAUDE.md's "never hand-roll `ply % 2`" rule forbids. Its two output values
    are the same two strings `expected_score_sql`'s `user_color_col` argument
    compares against ('white'/'black').

    Args:
        ply_col: A column or literal expression resolving to the ply integer.
                 Accepts ColumnElement[int] or ORM InstrumentedAttribute[int]
                 (typed as Any because ty does not recognise InstrumentedAttribute
                 as a ColumnElement subtype — they share SQLColumnExpression lineage).

    Returns:
        A SQLAlchemy ColumnElement[str] yielding 'white' or 'black'.
    """
    return case(
        (ply_col % 2 == _PLY_EVEN_MOVER_WHITE, literal("white")),
        else_=literal("black"),
    )


def player_only_gate(
    ply_col: Any,
    user_color_col: Any,
) -> ColumnElement[bool]:
    """Convenience inverse of is_opponent_expr — True when the mover is the PLAYER.

    Use at read-gating call sites so intent reads as 'player only'
    rather than a negation. Equivalent to ~is_opponent_expr(...).

    Args:
        ply_col: A column or literal expression resolving to the ply integer.
                 Accepts ColumnElement[int] or ORM InstrumentedAttribute[int].
        user_color_col: A column or literal expression resolving to 'white'/'black'.

    Returns:
        A SQLAlchemy ColumnElement[bool] for player-only filtering.
    """
    return ~is_opponent_expr(ply_col, user_color_col)


def game_ids_any_predicate(column: Any, game_ids: Sequence[int]) -> ColumnElement[bool]:
    """``column = ANY(:ids)`` against ONE bound ``int[]`` parameter.

    Used by the on-read ranked Endgame Stats path to restrict a statement (or an
    inner aggregation subquery) to the ranked-sample game ids. Deliberately NOT an
    expanded ``IN (1, 2, ...)`` list and NOT an ``IN (subquery)``: the latter is the
    form documented as hanging the planner on users with many endgame games
    (see query_clock_stats_rows). ``unique=True`` gives each call its own parameter
    name so several statements / subqueries in one query can each carry the array.
    The ids come from our own ranked-sample query, never from a request.
    """
    ids_param = bindparam(
        "ranked_game_ids", value=list(game_ids), type_=ARRAY(Integer), unique=True
    )
    return column == any_(ids_param)


def apply_game_filters(
    stmt: Any,
    time_control: Sequence[str] | None,
    platform: Sequence[str] | None,
    rated: bool | None,
    opponent_type: str,
    from_date: datetime.date | None,
    to_date: datetime.date | None,
    color: str | None = None,
    *,
    # Keyword-only, default-False so every existing caller keeps today's behavior
    # unchanged; only library_repository's two Library-surface query functions
    # (query_flaws, query_filtered_games) set it True.
    native_games_bypass_opponent_and_rated: bool = False,
    opponent_gap_min: int | None = None,
    opponent_gap_max: int | None = None,
    flaw_severity: Sequence[str] | None = None,
    flaw_tags: Sequence[str] | None = None,
    tactic_families: Sequence[str] | None = None,
    user_id: int | None = None,
    # Default "either" is neutral: the tactic EXISTS activates on orientation alone
    # (_tactic_controls_active), so any other default would silently filter every
    # non-tactic caller (endgame/openings/stats pass no orientation) to games with
    # a tactic. "either" matches build_flaw_filter_clauses' default.
    orientation: Literal["either", "missed", "allowed"] = "either",
    min_tactic_depth: int | None = None,
    max_tactic_depth: int | None = None,
    has_gem: bool | None = None,
    has_great: bool | None = None,
    # Keyword-only, default None = unchanged behavior for every existing
    # caller. Only the on-read ranked Endgame Stats path sets it, to restrict a
    # statement to the ranked-sample game ids (alongside neutral other filters).
    game_ids: Sequence[int] | None = None,
) -> Any:
    """Apply standard game filter WHERE clauses to a SELECT statement.

    Args:
        stmt: The base SELECT statement to add filters to.
        time_control: Filter by time control buckets (bullet, blitz, rapid, classical).
        platform: Filter by platform (chess.com, lichess). None = default
                 population, which excludes DEFAULT_EXCLUDED_PLATFORMS
                 ("flawchess", "pgn"). Pass an explicit list including
                 "flawchess" or "pgn" to opt in.
                 ANALYTICS_INCLUDED_PLATFORMS is the explicit-list equivalent
                 of the `platform is None` default: passing
                 `platform=list(ANALYTICS_INCLUDED_PLATFORMS)` returns the
                 same rows as `platform=None`. The
                 test_every_platform_has_an_analytics_disposition invariant
                 test is what keeps the two readings equal — the `notin_`
                 default admits any future platform value by omission, while
                 an explicit `in_` list excludes it, so the two only agree
                 while every Platform member has a declared disposition in
                 exactly one of DEFAULT_EXCLUDED_PLATFORMS /
                 ANALYTICS_INCLUDED_PLATFORMS.
        rated: Filter by rated/unrated. None = no filter.
        opponent_type: "human", "bot", or "all".
        from_date: Include games played on or after this date (inclusive). None = no lower bound.
        to_date: Include games played on or before this date (inclusive, shifted +1 day
                 in SQL so ``played_at < to_date + 1 day`` covers the whole day).
                 None = no upper bound.
        color: Filter by user's piece color ("white"/"black"). None = no color filter
               (used by endgame and stats repos where color is not applicable).
        native_games_bypass_opponent_and_rated: Only the Library Games and Flaws
                 surfaces set this flag. When True, rows whose platform is in
                 DEFAULT_EXCLUDED_PLATFORMS ignore the Opponent and Rated filters
                 unconditionally (including an explicit user selection), because
                 those games are stored rated=False and, for "flawchess",
                 is_computer_game=True — so the new Human+Rated analytics
                 defaults would otherwise hide a game the user just finished
                 from the only place it is browsable. Those rows remain
                 governed by the Platform filter and, for "pgn", by the
                 Library "pasted" control. This extends the "always here"
                 guarantee for flawchess games from the platform axis to the
                 opponent/rated axes. Default False = today's behavior.
        opponent_gap_min: Lower bound (inclusive) on opponent_rating - user_rating.
                         None = unbounded below.
        opponent_gap_max: Upper bound (inclusive) on opponent_rating - user_rating.
                         None = unbounded above.
        flaw_severity: When set (e.g. ["blunder"] or ["mistake"]), restrict to games
                         containing >=1 flaw in game_flaws whose severity is one of the
                         listed values (set membership / IN, not a min-threshold; e.g.
                         ["mistake"] matches mistakes only, not blunders). None (default)
                         leaves the statement unchanged — all existing callers are unaffected.
                         Requires user_id (the EXISTS must be user-scoped).
        flaw_tags: When set (e.g. ["low-clock", "reversed"]), additionally
                         restrict to games containing a SINGLE flaw satisfying ALL
                         selected tag families (single-flaw EXISTS semantics).
                         OR within family, AND across families (phase tags filter on
                         game_flaws.phase).
                         None (default) leaves the statement unchanged.
                         Requires user_id when any flaw or tactic filter is active
                         (flaw_severity, flaw_tags, or a non-default tactic control).
        tactic_families: When set (e.g. ["fork", "skewer"]), restrict to games
                         containing >=1 flaw whose tactic motif int (in the orientation's
                         column) is in the union of FAMILY_TO_MOTIF_INTS values for the
                         selected families. Unknown family keys yield no ints (no-op),
                         never raw SQL. None (default) leaves the statement
                         unchanged. Uses lazy import of FAMILY_TO_MOTIF_INTS from
                         library_repository to avoid a circular import.
        user_id: The authenticated user's id — required when any flaw or tactic
                         filter is active (flaw_severity, flaw_tags, or a non-default
                         tactic control), to scope the EXISTS subquery's game_flaws
                         read. Ignored otherwise.
        orientation: Which tactic column set to query.
                         "either" (default) → OR across both column sets. The default
                         is neutral: the tactic EXISTS activates on orientation alone
                         (_tactic_controls_active), so any other default would silently
                         filter non-tactic callers.
                         "allowed" → allowed_tactic_motif only.
                         "missed"  → missed_tactic_motif only.
                         FAMILY_TO_MOTIF_INTS is shared by all orientations.
                         Orientation is a closed Literal enum — never raw column-name
                         interpolation.
        min_tactic_depth / max_tactic_depth: Inclusive depth-range bounds (0-based
                         ply) on the active orientation's depth column. Each side
                         optional; None = unbounded that side. Mates obey the range
                         too.
        has_gem: When True, restrict to games containing >=1 of the USER's own
                         plies (player-parity scoping) whose stored
                         game_best_moves candidate classifies as 'gem' via the
                         SAME classifier the board uses (best_move_tier_sql /
                         classify_best_move). None/False = no
                         gem filter. Composed via a single correlated EXISTS
                         (best_move_exists_from_table) — never a parallel path.
        has_great: Same as has_gem for the 'great' tier. has_gem=True AND
                         has_great=True is a UNION (gem OR great on the single
                         EXISTS), mirroring the flaw-family EXISTS union.
        game_ids: When set, restrict to ``Game.id = ANY(:ids)`` (one bound
                         int[] parameter; see ``game_ids_any_predicate``). None (default)
                         leaves the statement unchanged. Internal keyword: routers must
                         never expose it.

    Notes:
        When either gap bound is set, games with missing white/black ratings
        are excluded.

        Date boundary fuzz: ``played_at`` is a TIMESTAMPTZ column stored in UTC;
        ``from_date`` / ``to_date`` are plain DATE values without timezone. The
        comparison uses the server's session timezone (UTC in production), which
        is correct for UTC-normalised timestamps. Games close to midnight in
        non-UTC timezones may straddle the boundary by up to ~24 h — this is an
        accepted trade-off (no client_timezone param, to avoid scope creep).

    Returns:
        The statement with WHERE clauses appended.
    """
    if time_control is not None:
        stmt = stmt.where(Game.time_control_bucket.in_(time_control))
    if platform is not None:
        stmt = stmt.where(Game.platform.in_(platform))
    else:
        # Default population (no explicit platform filter)
        # excludes flawchess bot-practice games from every analytics surface,
        # including the opponent_type='bot' explicit-filter case. Callers that want flawchess must pass it
        # explicitly in `platform` (e.g. library_service.get_library_games).
        stmt = stmt.where(Game.platform.notin_(DEFAULT_EXCLUDED_PLATFORMS))
    # opponent_type and rated are composed into ONE predicate (rather
    # than independent .where() calls) so native_games_bypass_opponent_and_rated
    # can wrap the whole thing in a platform-exemption OR. When the flag is False
    # the AND of active conditions is equivalent to the old one-where-per-predicate
    # shape — same observable row set.
    opponent_rated_conditions: list[ColumnElement[bool]] = []
    if rated is not None:
        opponent_rated_conditions.append(Game.rated == rated)  # noqa: E712
    if opponent_type == "human":
        opponent_rated_conditions.append(Game.is_computer_game == False)  # noqa: E712
    elif opponent_type == "bot":
        opponent_rated_conditions.append(Game.is_computer_game == True)  # noqa: E712
    if opponent_rated_conditions:
        combined_condition = and_(*opponent_rated_conditions)
        if native_games_bypass_opponent_and_rated:
            # Library-only exemption: flawchess/pgn rows are stored
            # rated=False (and flawchess is_computer_game=True), so a Human+Rated
            # default would otherwise hide a game from the only surface that
            # browses it. The Platform filter above still governs these rows.
            stmt = stmt.where(
                or_(Game.platform.in_(DEFAULT_EXCLUDED_PLATFORMS), combined_condition)
            )
        else:
            stmt = stmt.where(combined_condition)
    # Apply date bounds only when set. to_date is shifted +1 day so the
    # comparison ``played_at < to_date + 1 day`` covers the full to_date day.
    if from_date is not None:
        stmt = stmt.where(Game.played_at >= from_date)
    if to_date is not None:
        stmt = stmt.where(Game.played_at < to_date + datetime.timedelta(days=1))
    if color is not None:
        stmt = stmt.where(Game.user_color == color)
    if opponent_gap_min is not None or opponent_gap_max is not None:
        user_rating = case(
            (Game.user_color == "white", Game.white_rating),
            else_=Game.black_rating,
        )
        opp_rating = case(
            (Game.user_color == "white", Game.black_rating),
            else_=Game.white_rating,
        )
        # Exclude games with missing ratings when filtering by opponent gap.
        stmt = stmt.where(Game.white_rating.isnot(None), Game.black_rating.isnot(None))
        gap = opp_rating - user_rating
        if opponent_gap_min is not None:
            stmt = stmt.where(gap >= opponent_gap_min)
        if opponent_gap_max is not None:
            stmt = stmt.where(gap <= opponent_gap_max)
    # Flaw + tactic filters form ONE family: a single game_flaws row must satisfy
    # ALL selected conditions (severity, context tags, AND tactic motif/orientation/
    # depth) together. flaw_exists_from_table ANDs the whole build_flaw_filter_clauses
    # list onto one row, the same single-row AND semantics the Flaws list uses
    # (query_flaws).
    #
    # Don't emit TWO separate correlated EXISTS (one for severity/context tags, one
    # for tactics): a game would match when one flaw was a depth-1-2 fork and a
    # DIFFERENT flaw was low-clock, because the tactic and context filters would be
    # ANDed at the game level, not the flaw-row level, diverging from the Flaws tab.
    # A single EXISTS over the full clause list gives the expected "one flaw is BOTH
    # a fork AND low-clock" semantics.
    #
    # Lazy import avoids a query_utils <-> library_repository import cycle
    # (mirrors endgame_repository's in-function import pattern).
    from app.repositories.library_repository import (
        FAMILY_TO_MOTIF_INTS,
        _tactic_controls_active,
        best_move_exists_from_table,
        flaw_exists_from_table,
    )
    from app.services.flaws_service import FlawSeverity, FlawTag

    # The tactic EXISTS must apply whenever ANY tactic control is active (family,
    # orientation, OR depth) — mirroring build_flaw_filter_clauses for the Flaws
    # list. resolved_families drop unknown keys (no-op), so an unknown-only
    # selection with default orientation/depth does not trigger a filter.
    families_seq: Sequence[str] = tactic_families or ()
    resolved_families: Sequence[str] = [fam for fam in families_seq if fam in FAMILY_TO_MOTIF_INTS]
    tactic_active = _tactic_controls_active(
        resolved_families, orientation, min_tactic_depth, max_tactic_depth
    )
    if flaw_severity or flaw_tags or tactic_active:
        if user_id is None:
            # Message intentionally omits variable values to preserve Sentry grouping
            # (scoping requires an authenticated user_id).
            raise ValueError("flaw/tactic filter requires user_id for EXISTS scoping")
        # Callers pass validated Literal values; cast narrows Sequence[str].
        severities = cast(Sequence[FlawSeverity], flaw_severity or [])
        tag_list = cast(Sequence[FlawTag], flaw_tags or [])
        exists_pred = flaw_exists_from_table(
            user_id=user_id,
            severity=severities,
            tags=tag_list,
            tactic_families=families_seq,
            orientation=orientation,
            min_tactic_depth=min_tactic_depth,
            max_tactic_depth=max_tactic_depth,
        )
        # flaw_exists_from_table returns true() only when no clause is produced;
        # this path is reached only when a filter is active, so exists_pred is a
        # real EXISTS predicate here (not true()).
        stmt = stmt.where(exists_pred)

    # has_gem / has_great: a single correlated EXISTS
    # composed alongside (not replacing) the flaw/tactic EXISTS above — both
    # booleans build ONE tiers list so has_gem=True AND has_great=True is a
    # UNION (gem OR great on the same row-set), never an intersection.
    best_move_tiers: list[Literal["gem", "great"]] = []
    if has_gem:
        best_move_tiers.append("gem")
    if has_great:
        best_move_tiers.append("great")
    if best_move_tiers:
        stmt = stmt.where(best_move_exists_from_table(best_move_tiers))
    if game_ids is not None:
        stmt = stmt.where(game_ids_any_predicate(Game.id, game_ids))
    return stmt
