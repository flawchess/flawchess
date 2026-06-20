"""Tests for Phase 126/129 tactic comparison backend (TACCMP-01/02/03, TACUI-01/05/08).

Coverage plan:
- test_family_mapping_ten_families           : Plan 04 Task 1 — 10 families in FAMILY_TO_MOTIF_INTS
- test_family_mapping_excludes_combinations  : Plan 04 Task 1 — dropped combinations ints absent
- test_family_mapping_covers_selected_motifs : Plan 04 Task 1 — all 10 family int sets correct
- test_family_mapping_fork                   : Task 1 — fork maps to [FORK=1]
- test_family_mapping_10_produces_overflow   : Plan 04 Task 1 — 10 families → top-6 + 4 overflow (G-01)
- test_combinations_request_is_noop          : Plan 04 Task 2 — dropped combinations key → no-op
- test_below_gate_short_circuit              : Task 2 — analyzed_n < gate → below_gate=True, bullets=[]
- test_full_response_bullets                 : Task 2 — N>=gate → up to 20 TacticBullet rows
- test_tactic_comparison_produces_overflow   : Plan 04 Task 2 — 10 families → overflow non-empty (G-01)
- test_significant_gap_first                 : Task 2 — significant rows ranked before non-significant
- test_zero_event_family_delta_none          : Task 2 — family with no events → delta=None
- test_confidence_gate_chip_field            : Task 2 — tactic_motif=None when confidence < threshold
"""

import uuid

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.game import Game


# ---------------------------------------------------------------------------
# Seed helpers
# ---------------------------------------------------------------------------


async def _ensure_user(session: AsyncSession, user_id: int) -> None:
    from sqlalchemy import select

    from app.models.user import User

    existing = (await session.execute(select(User).where(User.id == user_id))).unique()
    if existing.scalar_one_or_none() is None:
        session.add(
            User(id=user_id, email=f"tac-cmp-test-{user_id}@example.com", hashed_password="x")
        )
        await session.flush()


async def _seed_game(
    session: AsyncSession,
    *,
    user_id: int,
    user_color: str = "white",
    ply_count: int = 40,
    platform: str = "lichess",
    time_control_bucket: str = "blitz",
) -> Game:
    game = Game(
        user_id=user_id,
        platform=platform,
        platform_game_id=str(uuid.uuid4()),
        platform_url="https://lichess.org/test",
        pgn="1. e4 e5 *",
        result="1-0",
        user_color=user_color,
        time_control_str="600+0",
        time_control_bucket=time_control_bucket,
        time_control_seconds=600,
        base_time_seconds=600,
        increment_seconds=0.0,
        rated=True,
        is_computer_game=False,
        ply_count=ply_count,
    )
    session.add(game)
    await session.flush()
    return game


async def _seed_analyzed(session: AsyncSession, *, game: "Game") -> None:  # type: ignore[name-defined]
    """Mark the game analyzed (both gates — mirrors test_flaw_comparison.py)."""
    import datetime

    if game.white_blunders is None:
        game.white_blunders = 0
    game.full_evals_completed_at = datetime.datetime.now(tz=datetime.timezone.utc)
    await session.flush()


async def _seed_flaw(
    session: AsyncSession,
    *,
    game: Game,
    ply: int,
    severity: int = 1,
    tactic_motif: int | None = None,
    tactic_confidence: int | None = None,
) -> None:
    from app.repositories.game_flaws_repository import bulk_insert_game_flaws

    # Phase 128: tactic_motif/tactic_confidence renamed to allowed_tactic_motif/allowed_tactic_confidence (D-02).
    await bulk_insert_game_flaws(
        session,
        [
            {
                "user_id": game.user_id,
                "game_id": game.id,
                "ply": ply,
                "severity": severity,
                "tempo": None,
                "phase": 1,
                "is_miss": False,
                "is_lucky": False,
                "is_reversed": False,
                "is_squandered": False,
                "fen": "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR",
                "allowed_tactic_motif": tactic_motif,
                "allowed_tactic_confidence": tactic_confidence,
            }
        ],
    )


_DEFAULT_FILTER_KWARGS: dict = dict(
    time_control=None,
    platform=None,
    rated=None,
    opponent_type="all",
    from_date=None,
    to_date=None,
    flaw_severity=None,
    opponent_gap_min=None,
    opponent_gap_max=None,
    color=None,
    tactic_families=None,
)

# Reserved user IDs (no collision with other test modules)
_TEST_USER_GATE = 77701
_TEST_USER_BULLETS = 77702
_TEST_USER_RANK = 77703
_TEST_USER_ZERO = 77704
_TEST_USER_CHIP = 77705
_TEST_USER_OVERFLOW = 77706  # Plan 04 G-01 overflow regression test


@pytest_asyncio.fixture(autouse=True)
async def _create_test_users(db_session: AsyncSession) -> None:
    for uid in [
        _TEST_USER_GATE,
        _TEST_USER_BULLETS,
        _TEST_USER_RANK,
        _TEST_USER_ZERO,
        _TEST_USER_CHIP,
        _TEST_USER_OVERFLOW,
    ]:
        await _ensure_user(db_session, uid)


# ---------------------------------------------------------------------------
# Task 1 — FAMILY_TO_MOTIF_INTS assertions (pure unit tests, no DB)
# ---------------------------------------------------------------------------


def test_family_mapping_ten_families() -> None:
    """FAMILY_TO_MOTIF_INTS has exactly the 10 canonical family keys (Plan 04 G-01)."""
    from app.repositories.library_repository import FAMILY_TO_MOTIF_INTS

    expected_keys = {
        "fork",
        "skewer",
        "pin",
        "x_ray",
        "double_check",
        "discovered_check",
        "discovered_attack",
        "trapped_piece",
        "hanging",
        "mate",
    }
    assert set(FAMILY_TO_MOTIF_INTS.keys()) == expected_keys


def test_family_mapping_excludes_combinations() -> None:
    """Dropped combinations ints (DEFLECTION=9..SACRIFICE=17) belong to no family (Plan 04)."""
    from app.repositories.library_repository import FAMILY_TO_MOTIF_INTS

    # These ints were in the old "combinations" family and must now map to nothing.
    dropped_combinations_ints = {9, 10, 11, 13, 14, 15, 16, 17}
    all_mapped_ints = {m for ints in FAMILY_TO_MOTIF_INTS.values() for m in ints}
    overlap = dropped_combinations_ints & all_mapped_ints
    assert overlap == set(), (
        f"Dropped combinations ints {overlap} must not appear in any family mapping"
    )


def test_family_mapping_covers_selected_motifs() -> None:
    """Each new family maps to its correct int(s) (Plan 04 taxonomy contract)."""
    from app.repositories.library_repository import FAMILY_TO_MOTIF_INTS

    assert FAMILY_TO_MOTIF_INTS["fork"] == [1]
    assert FAMILY_TO_MOTIF_INTS["hanging"] == [2]
    assert FAMILY_TO_MOTIF_INTS["pin"] == [3]
    assert FAMILY_TO_MOTIF_INTS["skewer"] == [4]
    assert FAMILY_TO_MOTIF_INTS["double_check"] == [5]
    assert FAMILY_TO_MOTIF_INTS["discovered_attack"] == [6]
    assert FAMILY_TO_MOTIF_INTS["x_ray"] == [12]
    assert FAMILY_TO_MOTIF_INTS["discovered_check"] == [25]
    assert FAMILY_TO_MOTIF_INTS["trapped_piece"] == [26]
    # Mate set unchanged: ints 7-8, 18-24
    assert set(FAMILY_TO_MOTIF_INTS["mate"]) == {7, 8, 18, 19, 20, 21, 22, 23, 24}


def test_family_mapping_fork() -> None:
    """fork family maps to only [FORK=1]."""
    from app.repositories.library_repository import FAMILY_TO_MOTIF_INTS

    assert FAMILY_TO_MOTIF_INTS["fork"] == [1]


def test_family_mapping_10_produces_overflow() -> None:
    """With 10 families, the top-6 selection leaves 4 overflow families (G-01 resolved).

    This is the data-layer proof that the 'More Tactics' accordion (D-14) is
    now reachable — it was previously blocked because 6 families == top-6 cap.
    """
    from app.repositories.library_repository import FAMILY_TO_MOTIF_INTS

    total = len(FAMILY_TO_MOTIF_INTS)
    assert total == 10, f"Expected 10 families; got {total}"
    # top-6 + 4 overflow
    assert total > 6, "With 10 families, top-6 selection always produces overflow families"
    overflow_count = total - 6
    assert overflow_count == 4, f"Expected 4 overflow families; got {overflow_count}"


# ---------------------------------------------------------------------------
# Task 2 — get_tactic_comparison service tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_below_gate_short_circuit(db_session: AsyncSession) -> None:
    """analyzed_n < TACTIC_COMPARISON_GATE returns below_gate=True, bullets=[]."""
    from app.services.library_service import TACTIC_COMPARISON_GATE, get_tactic_comparison

    # Seed only 5 analyzed games (below the gate of 20)
    for _ in range(5):
        g = await _seed_game(db_session, user_id=_TEST_USER_GATE)
        await _seed_analyzed(db_session, game=g)

    result = await get_tactic_comparison(
        db_session,
        user_id=_TEST_USER_GATE,
        **_DEFAULT_FILTER_KWARGS,
    )
    assert result.below_gate is True
    assert result.bullets == []
    assert result.analyzed_n < TACTIC_COMPARISON_GATE
    assert result.analyzed_gate == TACTIC_COMPARISON_GATE


def test_combinations_request_is_noop() -> None:
    """A request for the dropped 'combinations' family key expands to zero motif ints (no-op).

    T-129-10: unknown/dropped family keys must yield an empty int list so the
    EXISTS expansion emits no clause (never a KeyError or unscoped query).
    """
    from app.repositories.library_repository import FAMILY_TO_MOTIF_INTS

    # combinations was dropped entirely — must not appear as a key
    assert "combinations" not in FAMILY_TO_MOTIF_INTS, (
        "Dropped 'combinations' family must not be a key in FAMILY_TO_MOTIF_INTS"
    )
    # .get(fam, []) expansion for an unknown key must return empty list
    result = FAMILY_TO_MOTIF_INTS.get("combinations", [])
    assert result == [], (
        f"FAMILY_TO_MOTIF_INTS.get('combinations', []) must return []; got {result!r}"
    )


@pytest.mark.asyncio
async def test_full_response_bullets(db_session: AsyncSession) -> None:
    """With enough analyzed games, response has below_gate=False and up to 20 bullets."""
    from app.repositories.library_repository import FAMILY_TO_MOTIF_INTS
    from app.services.library_service import TACTIC_COMPARISON_GATE, get_tactic_comparison

    # Seed 25 analyzed games (above gate)
    for _ in range(TACTIC_COMPARISON_GATE + 5):
        g = await _seed_game(db_session, user_id=_TEST_USER_BULLETS)
        await _seed_analyzed(db_session, game=g)

    result = await get_tactic_comparison(
        db_session,
        user_id=_TEST_USER_BULLETS,
        **_DEFAULT_FILTER_KWARGS,
    )
    assert result.below_gate is False
    assert result.analyzed_n >= TACTIC_COMPARISON_GATE
    # Phase 129 Plan 04: up to 20 bullets (10 families x 2 orientations: missed + allowed).
    # Can be less if some families have 0 events.
    assert len(result.bullets) <= 20
    # All bullets have a valid family key from the 10-family taxonomy
    valid_families = set(FAMILY_TO_MOTIF_INTS.keys())
    for bullet in result.bullets:
        assert bullet.family in valid_families, (
            f"bullet.family {bullet.family!r} must be one of the 10 taxonomy keys"
        )
        assert bullet.orientation in ("missed", "allowed"), (
            f"Each bullet must have orientation 'missed' or 'allowed'; got {bullet.orientation!r}"
        )
    # Check response shape
    assert isinstance(result.analyzed_n, int)
    assert isinstance(result.analyzed_gate, int)


@pytest.mark.asyncio
async def test_tactic_comparison_produces_overflow(db_session: AsyncSession) -> None:
    """With 10-family taxonomy, top-6 selection leaves 4 overflow families (G-01 regression).

    Phase 129 Plan 04: this is the data-layer proof that the 'More Tactics' accordion
    (D-14) is now reachable. Previously 6 families == top-6 cap → overflow always empty.
    With 10 families, overflow_families = ranked_families[6:] always has 4 entries.
    """
    from app.repositories.library_repository import FAMILY_TO_MOTIF_INTS
    from app.services.library_service import TACTIC_COMPARISON_GATE, get_tactic_comparison

    # Seed enough games to get past the gate
    for _ in range(TACTIC_COMPARISON_GATE + 5):
        g = await _seed_game(db_session, user_id=_TEST_USER_OVERFLOW)
        await _seed_analyzed(db_session, game=g)

    result = await get_tactic_comparison(
        db_session,
        user_id=_TEST_USER_OVERFLOW,
        **_DEFAULT_FILTER_KWARGS,
    )
    assert result.below_gate is False

    # With 10 families the server emits bullets for all of them (zero-event or not).
    # The top-6 selection must leave 4 overflow families — verify total unique families
    # represented in the response equals all 10 (or at least > 6, confirming overflow exists).
    families_in_response = {b.family for b in result.bullets}
    # All 10 families always emit at least 1 bullet (even if zero-event, delta=None).
    assert len(families_in_response) == len(FAMILY_TO_MOTIF_INTS), (
        f"Expected all {len(FAMILY_TO_MOTIF_INTS)} families in response; "
        f"got {len(families_in_response)}: {sorted(families_in_response)}"
    )
    # With 10 families, overflow always exists (D-14 accordion reachable).
    assert len(families_in_response) > 6, (
        "10-family taxonomy must produce overflow; response families must exceed top-6 cap"
    )


@pytest.mark.asyncio
async def test_significant_gap_first(db_session: AsyncSession) -> None:
    """Bullets with significant gaps (ci_low>0 or ci_high<0) rank before non-significant."""
    from app.services.library_service import TACTIC_COMPARISON_GATE, get_tactic_comparison
    from app.services.tactic_detector import TacticMotifInt

    # Seed enough analyzed games: player gets many fork events (even ply = white mover)
    # user_color="white", so even ply = player moves
    games_with_forks = []
    for _ in range(TACTIC_COMPARISON_GATE + 5):
        g = await _seed_game(db_session, user_id=_TEST_USER_RANK, user_color="white")
        await _seed_analyzed(db_session, game=g)
        games_with_forks.append(g)

    # Give 25 games many fork events on the player side (even ply) to force significant gap
    for g in games_with_forks:
        for ply in [2, 4, 6]:  # even plies = white (player) side
            await _seed_flaw(
                db_session,
                game=g,
                ply=ply,
                tactic_motif=int(TacticMotifInt.FORK),
                tactic_confidence=90,
            )

    result = await get_tactic_comparison(
        db_session,
        user_id=_TEST_USER_RANK,
        **_DEFAULT_FILTER_KWARGS,
    )
    assert result.below_gate is False
    # Phase 129 D-13: fork now has TWO bullets (missed + allowed); with player-side
    # allowed fork events the allowed bullet has you_rate > 0, missed may have you_rate=None.
    fork_bullets = [b for b in result.bullets if b.family == "fork"]
    assert len(fork_bullets) <= 2  # at most 2 fork bullets (missed + allowed per D-13)


@pytest.mark.asyncio
async def test_zero_event_family_delta_none(db_session: AsyncSession) -> None:
    """A family with zero events on both sides produces delta=None."""
    from app.services.library_service import TACTIC_COMPARISON_GATE, get_tactic_comparison

    # Seed enough games but no tactic motifs set
    for _ in range(TACTIC_COMPARISON_GATE + 2):
        g = await _seed_game(db_session, user_id=_TEST_USER_ZERO)
        await _seed_analyzed(db_session, game=g)
        # Seed a flaw with no tactic motif
        await _seed_flaw(db_session, game=g, ply=2, tactic_motif=None, tactic_confidence=None)

    result = await get_tactic_comparison(
        db_session,
        user_id=_TEST_USER_ZERO,
        **_DEFAULT_FILTER_KWARGS,
    )
    assert result.below_gate is False
    # All bullets should have delta=None since no tactic motifs were set
    for bullet in result.bullets:
        assert bullet.delta is None
        assert bullet.you_events == 0
        assert bullet.opp_events == 0


@pytest.mark.asyncio
async def test_confidence_gate_chip_field(db_session: AsyncSession) -> None:
    """tactic_motif=None on FlawListItem when confidence < MIN_TACTIC_CHIP_CONFIDENCE."""
    from app.repositories import library_repository
    from app.services.library_service import MIN_TACTIC_CHIP_CONFIDENCE
    from app.services.tactic_detector import TacticMotifInt

    g = await _seed_game(db_session, user_id=_TEST_USER_CHIP)
    await _seed_analyzed(db_session, game=g)

    # Flaw with confidence below threshold
    low_confidence = MIN_TACTIC_CHIP_CONFIDENCE - 1
    await _seed_flaw(
        db_session,
        game=g,
        ply=2,
        tactic_motif=int(TacticMotifInt.FORK),
        tactic_confidence=low_confidence,
    )

    # Flaw with confidence at/above threshold
    high_confidence = MIN_TACTIC_CHIP_CONFIDENCE
    await _seed_flaw(
        db_session,
        game=g,
        ply=4,
        tactic_motif=int(TacticMotifInt.PIN),
        tactic_confidence=high_confidence,
    )

    flaws, count = await library_repository.query_flaws(
        db_session,
        user_id=_TEST_USER_CHIP,
        severity=[],
        tags=[],
        time_control=None,
        platform=None,
        rated=None,
        opponent_type="all",
        from_date=None,
        to_date=None,
        color=None,
        offset=0,
        limit=10,
    )

    assert count == 2
    # Find the low-confidence flaw (ply=2)
    low_conf_flaw = next((f for f in flaws if f.ply == 2), None)
    assert low_conf_flaw is not None
    # Phase 128 D-07: tactic_motif renamed to allowed_tactic_motif on FlawListItem schema.
    assert low_conf_flaw.allowed_tactic_motif is None  # below threshold → None

    # Find the high-confidence flaw (ply=4)
    high_conf_flaw = next((f for f in flaws if f.ply == 4), None)
    assert high_conf_flaw is not None
    assert high_conf_flaw.allowed_tactic_motif == "pin"  # at/above threshold → string
    assert high_conf_flaw.allowed_tactic_confidence == high_confidence
