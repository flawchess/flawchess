"""Tests for tactic per-slot suppression and independent depth/orientation in
library_repository.py (Quick 260621-sm8).

Covers the five scenarios from the plan:
(a) family+depth filter: allowed slot nulled when out of depth range
(b) depth-only filter: restricts rows, nulls out-of-range slots
(c) orientation-only filter: restricts rows, nulls the opposite slot
(d) default state: returns ALL flaws (including non-tactic) with both slots populated
(e) regression guard: default state is non-restrictive

All tests use the rollback-scoped db_session fixture so they do not reset the dev DB.
"""

from typing import cast

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.game import Game as GameModel
from app.models.game_flaw import GameFlaw
from app.models.game_position import GamePosition
from app.repositories.library_repository import (
    ALLOWED_DECISION_DEPTH_OFFSET,
    _TACTIC_DEPTH_FULL_MAX,
    _TACTIC_DEPTH_FULL_MIN,
    _build_flaw_item,
    query_flaws,
    tactic_slot_visible,
)

# TacticMotifInt values used in tests (must match FAMILY_TO_MOTIF_INTS).
# FORK = 1, DISCOVERED_ATTACK = 6
_FORK_INT = 1
_DISCOVERED_ATTACK_INT = 6


# ---------------------------------------------------------------------------
# Unit tests for tactic_slot_visible (pure Python, no DB)
# ---------------------------------------------------------------------------


class TestTacticSlotVisible:
    """Pure unit tests for tactic_slot_visible — no DB required."""

    def test_confidence_below_threshold_returns_false(self) -> None:
        """A slot with confidence < 70 is not visible regardless of other controls."""
        assert not tactic_slot_visible(
            _FORK_INT,
            69,
            0,
            orientation_kind="missed",
            tactic_families=[],
            tactic_orientation="either",
            min_tactic_depth=None,
            max_tactic_depth=None,
        )

    def test_none_confidence_returns_false(self) -> None:
        assert not tactic_slot_visible(
            _FORK_INT,
            None,
            0,
            orientation_kind="missed",
            tactic_families=[],
            tactic_orientation="either",
            min_tactic_depth=None,
            max_tactic_depth=None,
        )

    def test_missed_slot_excluded_when_orientation_allowed(self) -> None:
        """orientation='allowed' excludes the missed slot."""
        assert not tactic_slot_visible(
            _FORK_INT,
            90,
            0,
            orientation_kind="missed",
            tactic_families=[],
            tactic_orientation="allowed",
            min_tactic_depth=None,
            max_tactic_depth=None,
        )

    def test_allowed_slot_excluded_when_orientation_missed(self) -> None:
        """orientation='missed' excludes the allowed slot."""
        assert not tactic_slot_visible(
            _FORK_INT,
            90,
            0,
            orientation_kind="allowed",
            tactic_families=[],
            tactic_orientation="missed",
            min_tactic_depth=None,
            max_tactic_depth=None,
        )

    def test_either_includes_both_slots(self) -> None:
        """orientation='either' includes both missed and allowed slots."""
        assert tactic_slot_visible(
            _FORK_INT,
            90,
            0,
            orientation_kind="missed",
            tactic_families=[],
            tactic_orientation="either",
            min_tactic_depth=None,
            max_tactic_depth=None,
        )
        assert tactic_slot_visible(
            _FORK_INT,
            90,
            0,
            orientation_kind="allowed",
            tactic_families=[],
            tactic_orientation="either",
            min_tactic_depth=None,
            max_tactic_depth=None,
        )

    def test_family_mismatch_returns_false(self) -> None:
        """A fork slot is not visible when only 'pin' family is selected."""
        assert not tactic_slot_visible(
            _FORK_INT,
            90,
            0,
            orientation_kind="missed",
            tactic_families=["pin"],
            tactic_orientation="either",
            min_tactic_depth=None,
            max_tactic_depth=None,
        )

    def test_family_match_returns_true(self) -> None:
        """A fork slot IS visible when 'fork' family is selected."""
        assert tactic_slot_visible(
            _FORK_INT,
            90,
            0,
            orientation_kind="missed",
            tactic_families=["fork"],
            tactic_orientation="either",
            min_tactic_depth=None,
            max_tactic_depth=None,
        )

    def test_missed_depth_no_offset(self) -> None:
        """Missed slot depth uses no offset (raw depth is compared directly)."""
        # Depth 2, range {0, 1} -> missed raw 2 is out of range.
        assert not tactic_slot_visible(
            _FORK_INT,
            90,
            2,
            orientation_kind="missed",
            tactic_families=[],
            tactic_orientation="either",
            min_tactic_depth=0,
            max_tactic_depth=1,
        )
        # Depth 1, range {0, 1} -> in range.
        assert tactic_slot_visible(
            _FORK_INT,
            90,
            1,
            orientation_kind="missed",
            tactic_families=[],
            tactic_orientation="either",
            min_tactic_depth=0,
            max_tactic_depth=1,
        )

    def test_allowed_depth_uses_decision_anchored_offset(self) -> None:
        """Allowed slot adds ALLOWED_DECISION_DEPTH_OFFSET before range check.

        Range {1, 2}: allowed raw depth 1 → anchored 2 (1+1) → IN range.
        Allowed raw depth 0 → anchored 1 (0+1) → IN range.
        Allowed raw depth 2 → anchored 3 (2+1) → OUT of range [1,2].
        """
        assert ALLOWED_DECISION_DEPTH_OFFSET == 1  # sanity
        # raw 1 + 1 = 2, inside [1, 2]
        assert tactic_slot_visible(
            _FORK_INT,
            90,
            1,
            orientation_kind="allowed",
            tactic_families=[],
            tactic_orientation="either",
            min_tactic_depth=1,
            max_tactic_depth=2,
        )
        # raw 2 + 1 = 3, outside [1, 2]
        assert not tactic_slot_visible(
            _FORK_INT,
            90,
            2,
            orientation_kind="allowed",
            tactic_families=[],
            tactic_orientation="either",
            min_tactic_depth=1,
            max_tactic_depth=2,
        )

    def test_full_range_bounds_treat_as_no_depth_filter(self) -> None:
        """Full-range bounds (_TACTIC_DEPTH_FULL_MIN / _TACTIC_DEPTH_FULL_MAX) are treated
        as no depth filter — even a very deep tactic passes."""
        assert tactic_slot_visible(
            _FORK_INT,
            90,
            11,  # max raw depth
            orientation_kind="missed",
            tactic_families=[],
            tactic_orientation="either",
            min_tactic_depth=_TACTIC_DEPTH_FULL_MIN,
            max_tactic_depth=_TACTIC_DEPTH_FULL_MAX,
        )

    def test_default_controls_shows_everything(self) -> None:
        """With all defaults (no families, either, no bounds) every confident slot passes."""
        for motif in (_FORK_INT, _DISCOVERED_ATTACK_INT):
            for orientation_kind in ("missed", "allowed"):
                assert tactic_slot_visible(
                    motif,
                    70,  # exactly at threshold
                    0,
                    orientation_kind=orientation_kind,  # type: ignore[arg-type]
                    tactic_families=[],
                    tactic_orientation="either",
                    min_tactic_depth=None,
                    max_tactic_depth=None,
                )


# ---------------------------------------------------------------------------
# DB-backed integration tests for query_flaws per-slot suppression
# ---------------------------------------------------------------------------


async def _seed_tactic_flaw(
    session: AsyncSession,
    *,
    user_id: int,
    game_id: int,
    ply: int,
    missed_motif: int | None = None,
    missed_conf: int | None = None,
    missed_depth: int | None = None,
    allowed_motif: int | None = None,
    allowed_conf: int | None = None,
    allowed_depth: int | None = None,
    severity: int = 2,
) -> None:
    """Insert a GameFlaw row with tactic fields for testing."""
    from app.models.game_flaw import GameFlaw

    flaw = GameFlaw(
        user_id=user_id,
        game_id=game_id,
        ply=ply,
        severity=severity,
        phase=1,  # middlegame
        is_miss=False,
        is_lucky=False,
        is_reversed=False,
        is_squandered=False,
        fen="",
        missed_tactic_motif=missed_motif,
        missed_tactic_confidence=missed_conf,
        missed_tactic_depth=missed_depth,
        allowed_tactic_motif=allowed_motif,
        allowed_tactic_confidence=allowed_conf,
        allowed_tactic_depth=allowed_depth,
    )
    session.add(flaw)
    await session.flush()


async def _seed_non_tactic_flaw(
    session: AsyncSession,
    *,
    user_id: int,
    game_id: int,
    ply: int,
    severity: int = 2,
) -> None:
    """Insert a plain (non-tactic) GameFlaw row."""
    from app.models.game_flaw import GameFlaw

    flaw = GameFlaw(
        user_id=user_id,
        game_id=game_id,
        ply=ply,
        severity=severity,
        phase=1,
        is_miss=False,
        is_lucky=False,
        is_reversed=False,
        is_squandered=False,
        fen="",
        missed_tactic_motif=None,
        missed_tactic_confidence=None,
        missed_tactic_depth=None,
        allowed_tactic_motif=None,
        allowed_tactic_confidence=None,
        allowed_tactic_depth=None,
    )
    session.add(flaw)
    await session.flush()


async def _seed_game_with_flaw(
    session: AsyncSession,
    *,
    user_id: int,
) -> GameModel:
    """Seed a minimal analyzed game. Returns the Game ORM object."""
    import datetime
    import uuid

    game = GameModel(
        user_id=user_id,
        platform="lichess",
        platform_game_id=str(uuid.uuid4()),
        platform_url="https://lichess.org/test",
        pgn="1. e4 e5 *",
        result="1-0",
        user_color="white",
        time_control_str="600+0",
        time_control_bucket="blitz",
        time_control_seconds=600,
        base_time_seconds=600,
        increment_seconds=0.0,
        rated=True,
        is_computer_game=False,
        ply_count=10,
        white_blunders=1,
        played_at=datetime.datetime(2026, 1, 1, tzinfo=datetime.timezone.utc),
        full_evals_completed_at=datetime.datetime(2026, 1, 1, tzinfo=datetime.timezone.utc),
    )
    session.add(game)
    await session.flush()
    return game


class TestQueryFlawsPerSlotSuppression:
    """Integration tests for query_flaws per-slot suppression (Quick 260621-sm8).

    Each test seeds unique user_id values to avoid cross-test leakage within the
    single rollback transaction. The db_session fixture rolls back the transaction
    after each test so no manual cleanup is needed.
    """

    @pytest.mark.asyncio
    async def test_family_and_depth_filter_nulls_out_of_range_allowed_slot(
        self, db_session: object
    ) -> None:
        """Scenario (a): missed-fork@depth1 + allowed-discovered-attack@depth12.

        Filter: depth {1,2}, family=fork, orientation=either.
        Expected: row returned, missed_* populated (fork, depth1 in range),
        allowed_* NULLED (discovered_attack depth12: anchored 12+1=13, out of range
        AND wrong family).
        """
        from tests.conftest import ensure_test_user

        session = cast(AsyncSession, db_session)
        uid = 88801
        await ensure_test_user(session, uid)
        game = await _seed_game_with_flaw(session, user_id=uid)
        gid: int = game.id

        # missed fork at raw depth 1 (anchored 1, in [1,2])
        # allowed discovered_attack at raw depth 11 (anchored 11+1=12, out of [1,2]; also wrong family)
        await _seed_tactic_flaw(
            session,
            user_id=uid,
            game_id=gid,
            ply=2,
            missed_motif=_FORK_INT,
            missed_conf=80,
            missed_depth=1,
            allowed_motif=_DISCOVERED_ATTACK_INT,
            allowed_conf=80,
            allowed_depth=11,
        )

        items, count = await query_flaws(
            session,
            user_id=uid,
            severity=[],
            tags=[],
            time_control=None,
            platform=None,
            rated=None,
            opponent_type="all",
            from_date=None,
            to_date=None,
            color=None,
            tactic_families=["fork"],
            orientation="either",
            min_tactic_depth=1,
            max_tactic_depth=2,
        )
        assert count == 1
        item = items[0]
        # missed fork at depth 1 passes: family=fork, missed anchored depth=1, in [1,2]
        assert item.missed_tactic_motif == "fork"
        assert item.missed_tactic_confidence == 80
        assert item.missed_tactic_depth == 1
        # allowed slot: wrong family (discovered_attack) AND depth out of range → nulled
        assert item.allowed_tactic_motif is None
        assert item.allowed_tactic_confidence is None
        assert item.allowed_tactic_depth is None

    @pytest.mark.asyncio
    async def test_depth_only_filter_restricts_rows_and_nulls_out_of_range(
        self, db_session: object
    ) -> None:
        """Scenario (b): depth-only filter (Low {0,1}) without any family selection.

        Expects: non-tactic flaw EXCLUDED (no tactic slot to match the depth clause),
        in-range tactic included with out-of-range allowed slot nulled.
        """
        from tests.conftest import ensure_test_user

        session = cast(AsyncSession, db_session)
        uid = 88802
        await ensure_test_user(session, uid)

        game_tactic = await _seed_game_with_flaw(session, user_id=uid)
        gid_t: int = game_tactic.id

        game_non_tactic = await _seed_game_with_flaw(session, user_id=uid)
        gid_nt: int = game_non_tactic.id

        # Tactic game: missed fork at depth 0 (in [0,1]) and allowed fork at depth 2
        # (anchored 2+1=3, out of [0,1]).
        await _seed_tactic_flaw(
            session,
            user_id=uid,
            game_id=gid_t,
            ply=2,
            missed_motif=_FORK_INT,
            missed_conf=80,
            missed_depth=0,
            allowed_motif=_FORK_INT,
            allowed_conf=80,
            allowed_depth=2,  # anchored = 3, out of [0,1]
        )

        # Non-tactic game: plain flaw with no tactic motifs.
        await _seed_non_tactic_flaw(session, user_id=uid, game_id=gid_nt, ply=4)

        items, count = await query_flaws(
            session,
            user_id=uid,
            severity=[],
            tags=[],
            time_control=None,
            platform=None,
            rated=None,
            opponent_type="all",
            from_date=None,
            to_date=None,
            color=None,
            tactic_families=[],
            orientation="either",
            min_tactic_depth=_TACTIC_DEPTH_FULL_MIN,
            max_tactic_depth=1,  # Low preset max; only _TACTIC_DEPTH_FULL_MIN check matters
        )
        # Only the tactic flaw that has at least one in-range slot should appear.
        # The non-tactic flaw has no slot to satisfy the depth clause → excluded.
        returned_game_ids = {it.game_id for it in items}
        assert gid_t in returned_game_ids
        assert gid_nt not in returned_game_ids

        tactic_item = next(it for it in items if it.game_id == gid_t)
        # missed depth 0 in [0,1]: populated
        assert tactic_item.missed_tactic_motif is not None
        assert tactic_item.missed_tactic_depth == 0
        # allowed depth 2 → anchored 3, out of [0,1]: nulled
        assert tactic_item.allowed_tactic_motif is None
        assert tactic_item.allowed_tactic_depth is None

    @pytest.mark.asyncio
    async def test_orientation_only_filter_restricts_rows_and_nulls_opposite_slot(
        self, db_session: object
    ) -> None:
        """Scenario (c): orientation-only filter (orientation='missed') without family.

        A flaw with ONLY an allowed slot (no missed) should be excluded.
        A flaw with a missed slot should be included with the allowed slot nulled.
        """
        from tests.conftest import ensure_test_user

        session = cast(AsyncSession, db_session)
        uid = 88803
        await ensure_test_user(session, uid)

        game_missed = await _seed_game_with_flaw(session, user_id=uid)
        gid_m: int = game_missed.id

        game_allowed_only = await _seed_game_with_flaw(session, user_id=uid)
        gid_a: int = game_allowed_only.id

        # Game with missed slot only.
        await _seed_tactic_flaw(
            session,
            user_id=uid,
            game_id=gid_m,
            ply=2,
            missed_motif=_FORK_INT,
            missed_conf=80,
            missed_depth=0,
            allowed_motif=_FORK_INT,  # also has allowed but filter will null it
            allowed_conf=80,
            allowed_depth=0,
        )

        # Game with allowed-only slot (no missed).
        await _seed_tactic_flaw(
            session,
            user_id=uid,
            game_id=gid_a,
            ply=4,
            missed_motif=None,
            missed_conf=None,
            missed_depth=None,
            allowed_motif=_FORK_INT,
            allowed_conf=80,
            allowed_depth=0,
        )

        items, count = await query_flaws(
            session,
            user_id=uid,
            severity=[],
            tags=[],
            time_control=None,
            platform=None,
            rated=None,
            opponent_type="all",
            from_date=None,
            to_date=None,
            color=None,
            tactic_families=[],
            orientation="missed",  # missed orientation only
            min_tactic_depth=None,
            max_tactic_depth=None,
        )
        returned_game_ids = {it.game_id for it in items}
        # Game with missed slot: included.
        assert gid_m in returned_game_ids
        # Game with only allowed slot: excluded (no missed slot to match).
        assert gid_a not in returned_game_ids

        missed_item = next(it for it in items if it.game_id == gid_m)
        # missed slot populated
        assert missed_item.missed_tactic_motif is not None
        # allowed slot nulled (orientation='missed' excludes it)
        assert missed_item.allowed_tactic_motif is None
        assert missed_item.allowed_tactic_depth is None

    @pytest.mark.asyncio
    async def test_default_state_returns_all_flaws_both_slots_populated(
        self, db_session: object
    ) -> None:
        """Scenario (d)+(e): default controls return ALL flaws (incl. non-tactic)
        with BOTH tactic slots populated when confident.

        This is the regression guard: the refactor must NOT make the default
        state restrictive.
        """
        from tests.conftest import ensure_test_user

        session = cast(AsyncSession, db_session)
        uid = 88804
        await ensure_test_user(session, uid)

        game_tactic = await _seed_game_with_flaw(session, user_id=uid)
        gid_t: int = game_tactic.id

        game_non_tactic = await _seed_game_with_flaw(session, user_id=uid)
        gid_nt: int = game_non_tactic.id

        await _seed_tactic_flaw(
            session,
            user_id=uid,
            game_id=gid_t,
            ply=2,
            missed_motif=_FORK_INT,
            missed_conf=80,
            missed_depth=1,
            allowed_motif=_DISCOVERED_ATTACK_INT,
            allowed_conf=75,
            allowed_depth=3,
        )
        await _seed_non_tactic_flaw(session, user_id=uid, game_id=gid_nt, ply=4)

        # Default state: no tactic controls active
        items, count = await query_flaws(
            session,
            user_id=uid,
            severity=[],
            tags=[],
            time_control=None,
            platform=None,
            rated=None,
            opponent_type="all",
            from_date=None,
            to_date=None,
            color=None,
            tactic_families=None,  # no family filter
            orientation="either",  # default
            min_tactic_depth=None,  # no depth filter
            max_tactic_depth=None,
        )
        # Both flaws must appear.
        assert count == 2
        returned_game_ids = {it.game_id for it in items}
        assert gid_t in returned_game_ids
        assert gid_nt in returned_game_ids

        tactic_item = next(it for it in items if it.game_id == gid_t)
        # Both slots populated (both confident, no filter to suppress them).
        assert tactic_item.missed_tactic_motif == "fork"
        assert tactic_item.allowed_tactic_motif == "discovered-attack"
        assert tactic_item.missed_tactic_depth == 1
        assert tactic_item.allowed_tactic_depth == 3

        non_tactic_item = next(it for it in items if it.game_id == gid_nt)
        # Non-tactic flaw: both tactic slots are None (no motif in DB).
        assert non_tactic_item.missed_tactic_motif is None
        assert non_tactic_item.allowed_tactic_motif is None


# ---------------------------------------------------------------------------
# Unit tests for _build_flaw_item clock/move-time suppression (no DB needed)
# ---------------------------------------------------------------------------


def _make_flaw(
    game_id: int = 1,
    ply: int = 4,
    severity: int = 2,  # 2 = blunder
) -> GameFlaw:
    """Build a minimal GameFlaw ORM object for pure unit testing (no DB flush)."""
    flaw = GameFlaw()
    flaw.game_id = game_id
    flaw.user_id = 1
    flaw.ply = ply
    flaw.severity = severity
    flaw.phase = 1
    flaw.is_miss = False
    flaw.is_lucky = False
    flaw.is_reversed = False
    flaw.is_squandered = False
    flaw.tempo = None
    flaw.fen = "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1"
    flaw.allowed_tactic_motif = None
    flaw.allowed_tactic_confidence = None
    flaw.allowed_tactic_depth = None
    flaw.missed_tactic_motif = None
    flaw.missed_tactic_confidence = None
    flaw.missed_tactic_depth = None
    return flaw


def _make_flaw_game(
    time_control_str: str | None = None,
    base_time_seconds: int | None = None,
) -> GameModel:
    """Build a minimal Game ORM object for _build_flaw_item unit testing (no DB flush)."""
    game = GameModel()
    game.user_color = "white"
    game.result = "1-0"
    game.time_control_str = time_control_str
    game.base_time_seconds = base_time_seconds
    game.increment_seconds = 0.0
    game.time_control_bucket = "classical"
    game.platform = "chess.com"
    game.platform_url = "https://www.chess.com/game/live/1"
    game.white_username = "alice"
    game.black_username = "bob"
    game.white_rating = 1500
    game.black_rating = 1500
    game.played_at = None
    game.ply_count = 10
    game.termination = "resignation"
    return game


def _make_flaw_pos(
    ply: int,
    clock_seconds: float | None = None,
    eval_cp: int | None = None,
    eval_mate: int | None = None,
    move_san: str | None = "Nf3",
    best_move: str | None = None,
) -> GamePosition:
    """Build a minimal GamePosition ORM object for _build_flaw_item unit testing."""
    pos = GamePosition()
    pos.ply = ply
    pos.clock_seconds = clock_seconds
    pos.eval_cp = eval_cp
    pos.eval_mate = eval_mate
    pos.move_san = move_san
    pos.best_move = best_move
    pos.full_hash = 0
    pos.white_hash = 0
    pos.black_hash = 0
    return pos


class TestBuildFlawItemClockSuppression:
    """Pure unit tests for _build_flaw_item clock/move-time suppression.

    No DB required — objects are constructed in memory using the same pattern
    as the eval-chart service tests. The suppression is display-only: storage
    (game_positions.clock_seconds) is untouched.
    """

    def test_daily_game_suppresses_clock_and_move_seconds(self) -> None:
        """A chess.com daily game (time_control_str='1/86400') yields
        clock_seconds=None and move_seconds=None in FlawListItem, even when
        pos_at and pos_two_before carry clock_seconds values.
        """
        flaw = _make_flaw(ply=4)
        game = _make_flaw_game(time_control_str="1/86400", base_time_seconds=None)
        pos_at = _make_flaw_pos(ply=4, clock_seconds=1008.0, eval_cp=-50)
        pos_before = _make_flaw_pos(ply=3, clock_seconds=90.0, eval_cp=50)
        pos_two_before = _make_flaw_pos(ply=2, clock_seconds=21.3, eval_cp=50)

        item = _build_flaw_item(
            flaw,
            game,
            pos_at,
            pos_before,
            pos_two_before,
            tactic_families=[],
            orientation="either",
            min_tactic_depth=None,
            max_tactic_depth=None,
        )

        assert item.clock_seconds is None, (
            "Daily game must suppress clock_seconds regardless of stored value"
        )
        assert item.move_seconds is None, (
            "Daily game must suppress move_seconds regardless of stored clocks"
        )

    def test_classical_game_preserves_clock_seconds(self) -> None:
        """A classical game (time_control_str='1800') with pos_at.clock_seconds
        set still surfaces non-null clock_seconds in FlawListItem.
        """
        flaw = _make_flaw(ply=4)
        game = _make_flaw_game(time_control_str="1800", base_time_seconds=1800)
        pos_at = _make_flaw_pos(ply=4, clock_seconds=1750.0, eval_cp=-50)
        pos_before = _make_flaw_pos(ply=3, clock_seconds=1760.0, eval_cp=50)
        pos_two_before = _make_flaw_pos(ply=2, clock_seconds=1790.0, eval_cp=50)

        item = _build_flaw_item(
            flaw,
            game,
            pos_at,
            pos_before,
            pos_two_before,
            tactic_families=[],
            orientation="either",
            min_tactic_depth=None,
            max_tactic_depth=None,
        )

        assert item.clock_seconds == 1750.0, "Classical game must preserve clock_seconds"
        # move_seconds: prev_same_side (pos_two_before) - clock_after + increment
        # = 1790.0 - 1750.0 + 0.0 = 40.0
        assert item.move_seconds == 40.0, "Classical game must compute move_seconds from clock data"
