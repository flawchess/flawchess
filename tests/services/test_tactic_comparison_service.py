"""Tests for Phase 126/129/239 tactic comparison backend (TACCMP-01/02/03, TACUI-01/05/08).

Coverage plan:
- test_family_mapping_*                      : FAMILY_TO_MOTIF_INTS taxonomy contract (19 families)
- test_combinations_request_is_noop          : dropped combinations key expands to no motif ints
- test_fixed_order_per_tc                    : Phase 239 D-00h, D-02 — 38 bullets per TC, fixed order
- test_per_100_games_unit                    : Phase 239 D-00h — rates/deltas per 100 games
- test_below_gate_tc_still_lists_bullets    : Phase 239 D-03 — 12 analyzed games, below_gate with 38 bullets
- test_significance_gate                     : Phase 239 D-14 — 99% CI on the gap excludes 0
- test_zone_lookup_uses_each_bullets_tc      : Phase 239 D-08/D-11 — registry band per TC, rapid stopgap
- test_accepted_viable_entries_*             : Phase 239 plan 07 — accepted registry bands reach the API, no monkeypatch
- test_blob_pending_games_excluded_from_tactic_population : WR-01 — blob-pending analyzed games excluded from tactic, kept in flaw
- test_blob_pending_games_excluded_from_tactic_population : WR-01 — blob-pending games out of tactic, kept in flaw
- test_two_user_isolation                    : T-239-08 — each user sees only their own events
- test_zero_event_family_delta_none          : family with no events -> delta=None
- test_confidence_gate_chip_field            : tactic_motif=None when confidence < threshold
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


async def _seed_analyzed(session: AsyncSession, *, game: "Game", blobs_done: bool = True) -> None:  # type: ignore[name-defined]
    """Mark the game analyzed (both gates — mirrors test_flaw_comparison.py).

    The tactic population is blob-done games only (WR-01), so blobs_completed_at is
    set by default; pass blobs_done=False to seed an analyzed game whose tactic blobs
    are still pending.
    """
    import datetime

    now = datetime.datetime.now(tz=datetime.timezone.utc)
    if game.white_blunders is None:
        game.white_blunders = 0
    game.full_evals_completed_at = now
    if blobs_done:
        game.blobs_completed_at = now
    await session.flush()


async def _seed_flaw(
    session: AsyncSession,
    *,
    game: Game,
    ply: int,
    severity: int = 1,
    tactic_motif: int | None = None,
    tactic_confidence: int | None = None,
    missed_motif: int | None = None,
    missed_confidence: int | None = None,
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
                "missed_tactic_motif": missed_motif,
                "missed_tactic_confidence": missed_confidence,
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
_TEST_USER_ORDER = 77701
_TEST_USER_UNIT = 77702
_TEST_USER_ZERO = 77704
_TEST_USER_CHIP = 77705
_TEST_USER_GATE = 77706
_TEST_USER_LOW = 77707
_TEST_USER_BAND = 77708
_TEST_USER_ISO_A = 77709
_TEST_USER_ISO_B = 77710
_TEST_USER_E2E = 77711
_TEST_USER_BLOBS = 77712


@pytest_asyncio.fixture(autouse=True)
async def _create_test_users(db_session: AsyncSession) -> None:
    for uid in [
        _TEST_USER_ORDER,
        _TEST_USER_UNIT,
        _TEST_USER_ZERO,
        _TEST_USER_CHIP,
        _TEST_USER_GATE,
        _TEST_USER_LOW,
        _TEST_USER_BAND,
        _TEST_USER_ISO_A,
        _TEST_USER_ISO_B,
        _TEST_USER_E2E,
        _TEST_USER_BLOBS,
    ]:
        await _ensure_user(db_session, uid)


# ---------------------------------------------------------------------------
# Task 1 — FAMILY_TO_MOTIF_INTS assertions (pure unit tests, no DB)
# ---------------------------------------------------------------------------


def test_family_mapping_ten_families() -> None:
    """FAMILY_TO_MOTIF_INTS has 10 canonical + 6 tier-3 + 3 move-type families = 19.

    Quick 260623-6pd surfaced the shipped Phase-132 tier-3 motifs (deflection, intermezzo,
    interference, clearance, capturing_defender) as filterable families, expanding the
    taxonomy from 10 to 15. Phase 133 (plan 133-02) added attraction and sacrifice (15 → 17).
    Quick 260623 added the move-type families en_passant + under_promotion (17 → 19) after
    they unsuppressed at P=1.000 on the Phase-134 expanded fixture. promotion (28) was then
    surfaced when D-09 was reversed (19 → 20) — perfect-precision residual move-type motif,
    sibling of under_promotion. Phase 221 plan 06 (D-07) then REMOVED "clearance" (20 → 19)
    — the real-game keep/suppress bar measured real_share=0.667 with only 3 of 16
    surviving rows, below both REALGAME_MIN_ROWS_FOR_FLOOR and the 0.80 keep bar.
    """
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
        # Tier-3 "Advanced" families (Quick 260623-6pd). "clearance" REMOVED
        # (Phase 221 plan 06, D-07 suppression).
        "deflection",
        "intermezzo",
        "interference",
        "capturing_defender",
        # Phase 133 (plan 133-02): attraction + sacrifice unsuppressed
        "attraction",
        "sacrifice",
        # Move-type families (Quick 260623): en-passant + under-promotion; promotion added
        # when D-09 was reversed.
        "en_passant",
        "under_promotion",
        "promotion",
    }
    assert set(FAMILY_TO_MOTIF_INTS.keys()) == expected_keys


def test_family_mapping_excludes_suppressed_tier3() -> None:
    """self-interference (14) and clearance (15) are unmapped among the tier-3 ints.

    attraction (10) and sacrifice (17) were unsuppressed in Phase 133 (plan 133-02) and are
    now mapped as "Advanced" families. self-interference (14) still has no lichess theme
    equivalent and 0 TP — it stays unmapped. clearance (15) JOINED it in Phase 221 plan 06
    (D-07): the real-game keep/suppress bar measured real_share=0.667 with only 3 of 16
    surviving rows, below both REALGAME_MIN_ROWS_FOR_FLOOR and the 0.80 keep bar.
    """
    from app.repositories.library_repository import FAMILY_TO_MOTIF_INTS

    suppressed_tier3_ints = {14, 15}
    all_mapped_ints = {m for ints in FAMILY_TO_MOTIF_INTS.values() for m in ints}
    overlap = suppressed_tier3_ints & all_mapped_ints
    assert overlap == set(), (
        f"Still-suppressed tier-3 ints {overlap} must not appear in any family mapping"
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
    # Tier-3 "Advanced" families (Quick 260623-6pd). "clearance" (15) REMOVED
    # in Phase 221 plan 06 (D-07 suppression) — see test_family_mapping_
    # excludes_suppressed_tier3.
    assert FAMILY_TO_MOTIF_INTS["deflection"] == [9]
    assert FAMILY_TO_MOTIF_INTS["intermezzo"] == [11]
    assert FAMILY_TO_MOTIF_INTS["interference"] == [13]
    assert "clearance" not in FAMILY_TO_MOTIF_INTS
    assert FAMILY_TO_MOTIF_INTS["capturing_defender"] == [16]
    # Phase 133 (plan 133-02): attraction + sacrifice unsuppressed
    assert FAMILY_TO_MOTIF_INTS["attraction"] == [10]
    assert FAMILY_TO_MOTIF_INTS["sacrifice"] == [17]
    # Move-type families (Quick 260623): en-passant (27) + under-promotion (29)
    assert FAMILY_TO_MOTIF_INTS["en_passant"] == [27]
    assert FAMILY_TO_MOTIF_INTS["under_promotion"] == [29]


def test_family_mapping_fork() -> None:
    """fork family maps to only [FORK=1]."""
    from app.repositories.library_repository import FAMILY_TO_MOTIF_INTS

    assert FAMILY_TO_MOTIF_INTS["fork"] == [1]


def test_family_mapping_has_nineteen_families() -> None:
    """The payload is 19 families x 2 sides = 38 bullets per TC (Phase 239 D-00h)."""
    from app.repositories.library_repository import FAMILY_TO_MOTIF_INTS

    assert len(FAMILY_TO_MOTIF_INTS) == 19


# ---------------------------------------------------------------------------
# get_tactic_comparison service tests (Phase 239: per TC, per 100 games, fixed order)
# ---------------------------------------------------------------------------


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
async def test_fixed_order_per_tc(db_session: AsyncSession) -> None:
    """25 blitz games, one missed fork: tcs == [blitz] with 38 bullets in fixed order (D-00h)."""
    from app.services.library_service import TACTIC_COMPARISON_GATE, get_tactic_comparison
    from app.services.tactic_delta_zones import TACTIC_FAMILIES, tactic_delta_zone
    from app.services.tactic_detector import TacticMotifInt

    games = []
    for _ in range(TACTIC_COMPARISON_GATE + 5):
        g = await _seed_game(db_session, user_id=_TEST_USER_ORDER, user_color="white")
        await _seed_analyzed(db_session, game=g)
        games.append(g)
    # Ply 2 is a white (player) move: a missed fork on the user's side in one game.
    await _seed_flaw(
        db_session,
        game=games[0],
        ply=2,
        missed_motif=int(TacticMotifInt.FORK),
        missed_confidence=90,
    )

    result = await get_tactic_comparison(
        db_session, user_id=_TEST_USER_ORDER, **_DEFAULT_FILTER_KWARGS
    )

    assert result.analyzed_gate == TACTIC_COMPARISON_GATE
    assert [tc.tc for tc in result.tcs] == ["blitz"]
    blitz = result.tcs[0]
    assert blitz.analyzed_n == TACTIC_COMPARISON_GATE + 5
    assert blitz.below_gate is False
    assert [(b.family, b.orientation) for b in blitz.bullets] == [
        (family, side) for family in TACTIC_FAMILIES for side in ("missed", "allowed")
    ]
    assert len(blitz.bullets) == 38
    fork_missed = blitz.bullets[0]
    assert (fork_missed.family, fork_missed.orientation) == ("fork", "missed")
    assert fork_missed.you_events == 1
    assert fork_missed.opp_events == 0
    # 1 event over 25 games: 100 / 25 = 4.0 per 100 games (D-00h).
    assert fork_missed.you_rate == pytest.approx(4.0)
    assert fork_missed.opp_rate == pytest.approx(0.0)
    assert fork_missed.delta == pytest.approx(4.0)
    # has_zone mirrors the registry (plan 239-07 populated the 9 accepted viable entries).
    for bullet in blitz.bullets:
        band = tactic_delta_zone(bullet.family, bullet.orientation, "blitz")
        assert bullet.has_zone is (band is not None)
        assert bullet.zone_lo == (band.zone_lo if band else 0.0)
        assert bullet.zone_hi == (band.zone_hi if band else 0.0)


@pytest.mark.asyncio
async def test_per_100_games_unit(db_session: AsyncSession) -> None:
    """A single analyzed game whose only flaw is a missed fork reads 100.0 per 100 games."""
    from app.services.library_service import get_tactic_comparison
    from app.services.tactic_detector import TacticMotifInt

    g = await _seed_game(db_session, user_id=_TEST_USER_UNIT, user_color="white")
    await _seed_analyzed(db_session, game=g)
    await _seed_flaw(
        db_session,
        game=g,
        ply=2,
        missed_motif=int(TacticMotifInt.FORK),
        missed_confidence=90,
    )

    result = await get_tactic_comparison(
        db_session, user_id=_TEST_USER_UNIT, **_DEFAULT_FILTER_KWARGS
    )

    assert [tc.tc for tc in result.tcs] == ["blitz"]
    assert result.tcs[0].analyzed_n == 1
    fork_missed = next(
        b for b in result.tcs[0].bullets if (b.family, b.orientation) == ("fork", "missed")
    )
    assert fork_missed.you_rate == pytest.approx(100.0)
    assert fork_missed.opp_rate == pytest.approx(0.0)
    assert fork_missed.delta == pytest.approx(100.0)


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
    assert len(result.tcs) == 1
    assert result.tcs[0].below_gate is False
    # All bullets should have delta=None since no tactic motifs were set
    for bullet in result.tcs[0].bullets:
        assert bullet.delta is None
        assert bullet.you_rate is None
        assert bullet.you_events == 0
        assert bullet.opp_events == 0


@pytest.mark.asyncio
async def test_below_gate_tc_still_lists_bullets(db_session: AsyncSession) -> None:
    """A TC with 12 analyzed games is listed below_gate with 38 populated bullets (D-03)."""
    from app.services.library_service import TACTIC_COMPARISON_GATE, get_tactic_comparison
    from app.services.tactic_detector import TacticMotifInt

    games = []
    for _ in range(12):
        g = await _seed_game(db_session, user_id=_TEST_USER_GATE, user_color="white")
        await _seed_analyzed(db_session, game=g)
        games.append(g)
    await _seed_flaw(
        db_session,
        game=games[0],
        ply=2,
        missed_motif=int(TacticMotifInt.FORK),
        missed_confidence=90,
    )

    result = await get_tactic_comparison(
        db_session, user_id=_TEST_USER_GATE, **_DEFAULT_FILTER_KWARGS
    )

    assert 12 < TACTIC_COMPARISON_GATE
    assert [tc.tc for tc in result.tcs] == ["blitz"]
    blitz = result.tcs[0]
    assert blitz.analyzed_n == 12
    assert blitz.below_gate is True
    assert len(blitz.bullets) == 38
    fork_missed = blitz.bullets[0]
    assert (fork_missed.family, fork_missed.orientation) == ("fork", "missed")
    # Rates are populated below the gate: 1 event over 12 games.
    assert fork_missed.you_rate == pytest.approx(100.0 / 12)


@pytest.mark.asyncio
async def test_blob_pending_games_excluded_from_tactic_population(
    db_session: AsyncSession,
) -> None:
    """An analyzed game without tactic blobs is not a tactic game (WR-01).

    Tactic motifs are NULL while a flaw blob is pending, so such a game would count as a
    false zero-tactic game. It must be excluded from the tactic analyzed_n and rates but
    still be counted by the flaw comparison (tags do not depend on blobs).
    """
    from app.services.library_service import get_flaw_comparison, get_tactic_comparison
    from app.services.tactic_detector import TacticMotifInt

    blob_done = 4
    blob_pending = 6
    games = []
    for _ in range(blob_done):
        g = await _seed_game(db_session, user_id=_TEST_USER_BLOBS, user_color="white")
        await _seed_analyzed(db_session, game=g)
        games.append(g)
    for _ in range(blob_pending):
        g = await _seed_game(db_session, user_id=_TEST_USER_BLOBS, user_color="white")
        await _seed_analyzed(db_session, game=g, blobs_done=False)
    await _seed_flaw(
        db_session,
        game=games[0],
        ply=2,
        missed_motif=int(TacticMotifInt.FORK),
        missed_confidence=90,
    )

    tactic = await get_tactic_comparison(
        db_session, user_id=_TEST_USER_BLOBS, **_DEFAULT_FILTER_KWARGS
    )
    assert [tc.tc for tc in tactic.tcs] == ["blitz"]
    assert tactic.tcs[0].analyzed_n == blob_done
    fork_missed = tactic.tcs[0].bullets[0]
    assert (fork_missed.family, fork_missed.orientation) == ("fork", "missed")
    # 1 event over the 4 blob-done games only; the pending games add no false zeros.
    assert fork_missed.you_rate == pytest.approx(100.0 / blob_done)

    flaw = await get_flaw_comparison(
        db_session,
        _TEST_USER_BLOBS,
        **{k: v for k, v in _DEFAULT_FILTER_KWARGS.items() if k != "tactic_families"},
    )
    assert flaw.tcs[0].analyzed_n == blob_done + blob_pending


# D-14 significance fixture: 40 analyzed games. One missed fork leaves the 99% CI on the
# per-game gap covering 0; forks in 21 of the 40 games push it clear of 0.
_SIG_GAMES = 40
_SIG_FEW_FORKS = 1
_SIG_MANY_FORKS = 21


@pytest.mark.asyncio
async def test_significance_gate(db_session: AsyncSession) -> None:
    """significant is the 99% CI on the gap excluding 0 (D-14, replaces the D-12 count rule)."""
    from app.services.library_service import get_tactic_comparison
    from app.services.tactic_detector import TacticMotifInt

    games = []
    for _ in range(_SIG_GAMES):
        g = await _seed_game(db_session, user_id=_TEST_USER_LOW, user_color="white")
        await _seed_analyzed(db_session, game=g)
        games.append(g)

    async def seed_forks(batch: list) -> None:  # noqa: ANN001 — local helper
        # Player-side missed forks (ply 2 is a white move).
        for g in batch:
            await _seed_flaw(
                db_session,
                game=g,
                ply=2,
                missed_motif=int(TacticMotifInt.FORK),
                missed_confidence=90,
            )

    async def fork_missed_bullet():  # noqa: ANN202 — local helper
        result = await get_tactic_comparison(
            db_session, user_id=_TEST_USER_LOW, **_DEFAULT_FILTER_KWARGS
        )
        return next(
            b for b in result.tcs[0].bullets if (b.family, b.orientation) == ("fork", "missed")
        )

    await seed_forks(games[:_SIG_FEW_FORKS])
    few = await fork_missed_bullet()
    assert few.you_events == _SIG_FEW_FORKS
    assert few.ci_low is not None and few.ci_low < 0.0
    assert few.significant is False

    await seed_forks(games[_SIG_FEW_FORKS:_SIG_MANY_FORKS])
    many = await fork_missed_bullet()
    assert many.you_events == _SIG_MANY_FORKS
    assert many.ci_low is not None and many.ci_low > 0.0
    assert many.significant is True


@pytest.mark.asyncio
async def test_zone_lookup_uses_each_bullets_tc(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The (fork, missed) band is read per TC: classical its own, blitz and bullet the rapid one."""
    from app.services import tactic_delta_zones
    from app.services.flaw_delta_zones import ZoneBand
    from app.services.library_service import get_tactic_comparison
    from app.services.tactic_delta_zones import tactic_delta_zone

    rapid = ZoneBand(zone_lo=-2.0, zone_hi=3.0)
    classical = ZoneBand(zone_lo=-1.0, zone_hi=1.5)
    patched = {
        **tactic_delta_zones.TACTIC_DELTA_ZONES,
        ("fork", "missed"): {"rapid": rapid, "classical": classical},
    }
    monkeypatch.setattr(tactic_delta_zones, "TACTIC_DELTA_ZONES", patched)

    for tc in ("bullet", "blitz", "classical"):
        g = await _seed_game(
            db_session, user_id=_TEST_USER_BAND, user_color="white", time_control_bucket=tc
        )
        await _seed_analyzed(db_session, game=g)

    result = await get_tactic_comparison(
        db_session, user_id=_TEST_USER_BAND, **_DEFAULT_FILTER_KWARGS
    )

    assert [tc.tc for tc in result.tcs] == ["bullet", "blitz", "classical"]
    expected = {"bullet": rapid, "blitz": rapid, "classical": classical}
    for tc_entry in result.tcs:
        fork_missed = tc_entry.bullets[0]
        assert (fork_missed.family, fork_missed.orientation) == ("fork", "missed")
        assert fork_missed.has_zone is True
        assert fork_missed.zone_lo == expected[tc_entry.tc].zone_lo
        assert fork_missed.zone_hi == expected[tc_entry.tc].zone_hi
        # Every other family-side reads the (accepted) registry as usual.
        for b in tc_entry.bullets[1:]:
            other = tactic_delta_zone(b.family, b.orientation, tc_entry.tc)
            assert b.has_zone is (other is not None)


@pytest.mark.asyncio
async def test_accepted_viable_entries_report_the_registry_band_end_to_end(
    db_session: AsyncSession,
) -> None:
    """No monkeypatch: a blitz user's viable bullets carry the accepted rapid band (D-08/D-09/D-11).

    Unviable bullets report has_zone False and a zero-width 0.0 band.
    """
    from app.services.library_service import TACTIC_COMPARISON_GATE, get_tactic_comparison
    from app.services.tactic_delta_zones import TACTIC_DELTA_ZONES

    for _ in range(TACTIC_COMPARISON_GATE + 5):
        g = await _seed_game(db_session, user_id=_TEST_USER_E2E, user_color="white")
        await _seed_analyzed(db_session, game=g)

    result = await get_tactic_comparison(
        db_session, user_id=_TEST_USER_E2E, **_DEFAULT_FILTER_KWARGS
    )

    assert [tc.tc for tc in result.tcs] == ["blitz"]
    viable_seen = 0
    for bullet in result.tcs[0].bullets:
        zones = TACTIC_DELTA_ZONES[(bullet.family, bullet.orientation)]
        if zones is None:
            assert bullet.has_zone is False
            assert (bullet.zone_lo, bullet.zone_hi) == (0.0, 0.0)
            continue
        viable_seen += 1
        assert bullet.has_zone is True
        assert bullet.zone_lo == zones["rapid"].zone_lo
        assert bullet.zone_hi == zones["rapid"].zone_hi
    assert viable_seen == 9


@pytest.mark.asyncio
async def test_two_user_isolation(db_session: AsyncSession) -> None:
    """Each user's response carries only that user's counts (T-239-08)."""
    from app.services.library_service import get_tactic_comparison
    from app.services.tactic_detector import TacticMotifInt

    game_a = await _seed_game(db_session, user_id=_TEST_USER_ISO_A, user_color="white")
    await _seed_analyzed(db_session, game=game_a)
    await _seed_flaw(
        db_session,
        game=game_a,
        ply=2,
        missed_motif=int(TacticMotifInt.FORK),
        missed_confidence=90,
    )
    game_b = await _seed_game(db_session, user_id=_TEST_USER_ISO_B, user_color="white")
    await _seed_analyzed(db_session, game=game_b)
    await _seed_flaw(
        db_session,
        game=game_b,
        ply=2,
        missed_motif=int(TacticMotifInt.MATE),
        missed_confidence=90,
    )

    def events(result, family: str) -> int:  # noqa: ANN001
        bullet = next(
            b for b in result.tcs[0].bullets if (b.family, b.orientation) == (family, "missed")
        )
        return bullet.you_events + bullet.opp_events

    res_a = await get_tactic_comparison(
        db_session, user_id=_TEST_USER_ISO_A, **_DEFAULT_FILTER_KWARGS
    )
    res_b = await get_tactic_comparison(
        db_session, user_id=_TEST_USER_ISO_B, **_DEFAULT_FILTER_KWARGS
    )

    assert events(res_a, "fork") == 1
    assert events(res_a, "mate") == 0
    assert events(res_b, "fork") == 0
    assert events(res_b, "mate") == 1
    assert res_a.tcs[0].analyzed_n == 1
    assert res_b.tcs[0].analyzed_n == 1


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
