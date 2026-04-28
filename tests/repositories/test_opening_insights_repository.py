"""Phase 70 repository SQL contract tests — INSIGHT-CORE-02, INSIGHT-CORE-03, INSIGHT-CORE-04.

Precondition: The partial composite index ix_gp_user_game_ply must exist in the
test database before test_partial_index_predicate_alignment runs. This index is
created by the alembic migration 80e22b38993a_add_gp_user_game_ply_index.py.
Ensure `uv run alembic upgrade head` has been applied. The test will FAIL (not skip)
if the index is absent.

All tests use a real PostgreSQL database via the db_session fixture (rolled-back
transaction per test). The db_session fixture is provided by tests/conftest.py.
"""

from __future__ import annotations

import datetime
import uuid
from collections.abc import Sequence
from typing import Literal

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.game import Game
from app.models.game_position import GamePosition
from app.models.opening import Opening
from app.repositories.openings_repository import (
    OPENING_INSIGHTS_MIN_GAMES_PER_CANDIDATE,
    STARTING_POSITION_HASH,
    query_openings_by_hashes,
    query_opening_transitions,
)


# ---------------------------------------------------------------------------
# Test user fixture
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture(autouse=True)
async def _create_test_users(db_session: AsyncSession) -> None:
    """Ensure test user IDs 10, 11 exist in the users table (FK constraint)."""
    from tests.conftest import ensure_test_user

    for uid in [10, 11]:
        await ensure_test_user(db_session, uid)


# ---------------------------------------------------------------------------
# Seed helpers
# ---------------------------------------------------------------------------


def _unique_game_id() -> str:
    return str(uuid.uuid4())


async def _seed_game_with_positions(
    db_session: AsyncSession,
    user_id: int,
    result: Literal["1-0", "0-1", "1/2-1/2"],
    user_color: Literal["white", "black"],
    positions: Sequence[tuple[int, int, str | None]],  # (ply, full_hash, move_san)
    played_at: datetime.datetime | None = None,
    time_control_seconds: int = 600,
    force_ply0_hash: int | None = None,
    skip_auto_ply0: bool = False,
) -> int:
    """Insert one Game and its GamePositions; return game_id.

    Phase 71 hotfix: query_opening_transitions filters out games whose ply-0
    full_hash != STARTING_POSITION_HASH. To keep existing tests realistic,
    any (0, <synthetic_hash>, ...) entry is overridden to STARTING_POSITION_HASH
    by default; if no ply=0 row is in `positions`, one is auto-inserted with
    move_san=None so the EXISTS predicate is satisfied. Tests that need to
    seed a non-standard-start game pass `force_ply0_hash`; tests that need
    to seed a game WITHOUT a ply=0 row at all pass `skip_auto_ply0=True`.
    """
    if played_at is None:
        played_at = datetime.datetime.now(tz=datetime.timezone.utc)

    game = Game(
        user_id=user_id,
        platform="chess.com",
        platform_game_id=_unique_game_id(),
        platform_url="https://chess.com/game/test",
        pgn="1. e4 e5 *",
        result=result,
        user_color=user_color,
        time_control_str="600+0",
        time_control_bucket="blitz",
        time_control_seconds=time_control_seconds,
        rated=True,
        white_username="testuser",
        black_username="opponent",
    )
    game.played_at = played_at
    db_session.add(game)
    await db_session.flush()

    seen_ply0 = any(ply == 0 for ply, _, _ in positions)
    if not seen_ply0 and not skip_auto_ply0:
        # Auto-add a ply=0 row so the Phase 71 CTE filter (has_standard_start)
        # accepts the game. move_san=None here would block the partition's
        # array_agg from picking up the first move; use a synthetic move_san
        # that mirrors the next ply so entry_san_sequence stays non-empty for
        # tests with entries at ply >= 3.
        first_move = next((san for _, _, san in positions), None)
        ply0_san = first_move if first_move is not None else "e4"
        ply0_hash = force_ply0_hash if force_ply0_hash is not None else STARTING_POSITION_HASH
        db_session.add(
            GamePosition(
                game_id=game.id,
                user_id=user_id,
                ply=0,
                full_hash=ply0_hash,
                white_hash=0,
                black_hash=0,
                move_san=ply0_san,
            )
        )

    for ply, full_hash, move_san in positions:
        # Phase 71 hotfix: align ply-0 hash with the standard starting position
        # by default so the new CTE filter doesn't silently drop fixtures.
        # `force_ply0_hash` lets the regression test inject a non-standard hash.
        effective_hash = full_hash
        if ply == 0:
            effective_hash = (
                force_ply0_hash if force_ply0_hash is not None else STARTING_POSITION_HASH
            )
        pos = GamePosition(
            game_id=game.id,
            user_id=user_id,
            ply=ply,
            full_hash=effective_hash,
            white_hash=0,
            black_hash=0,
            move_san=move_san,
        )
        db_session.add(pos)
    await db_session.flush()

    return game.id


# Shared hash constants for position testing
H_ENTRY_PLY3 = 3001
H_CANDIDATE_PLY4 = 4001
H_ENTRY_PLY2 = 2001
H_CANDIDATE_PLY3 = 3002
H_ENTRY_PLY16 = 1600
H_CANDIDATE_PLY17 = 1701
H_ENTRY_PLY17 = 1700
H_CANDIDATE_PLY18 = 1801

# Synthetic SAN move names used in seeded positions
SAN_E4 = "e4"
SAN_C5 = "c5"
SAN_NF3 = "Nf3"
SAN_NC6 = "Nc6"
SAN_CANDIDATE = "d4"  # the candidate move at the position under test


def _default_call_args(
    color: Literal["white", "black"] = "black",
) -> dict:
    """Return default filter arguments for query_opening_transitions."""
    return {
        "time_control": None,
        "platform": None,
        "rated": None,
        "opponent_type": "both",
        "recency_cutoff": None,
        "opponent_strength": "any",
    }


# ---------------------------------------------------------------------------
# Task 1 tests: query_opening_transitions
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_entry_ply_lower_bound_3_inclusive(db_session: AsyncSession) -> None:
    """D-32: entry_ply = 3 is included in transition results.

    Per zobrist semantics, GamePosition.move_san at ply Y is the move played
    FROM ply Y (leading to ply Y+1). The entry position is the row whose
    full_hash and move_san describe (entry_hash, candidate_move). The seed
    therefore puts the candidate move on the entry row itself, and uses a
    final position with move_san=None one ply later so LEAD has a row to read.
    """
    user_id = 10
    for _ in range(OPENING_INSIGHTS_MIN_GAMES_PER_CANDIDATE):
        await _seed_game_with_positions(
            db_session,
            user_id=user_id,
            result="1-0",  # user_color=black so this is a LOSS
            user_color="black",
            positions=[
                (0, 10000, SAN_E4),  # ply=0: white's 1st move
                (1, 10001, SAN_C5),  # ply=1: black's 1st move
                (2, 10002, SAN_NF3),  # ply=2: white's 2nd move
                (3, H_ENTRY_PLY3, SAN_NC6),  # ply=3 (entry): candidate move played FROM here
                (4, H_CANDIDATE_PLY4, None),  # ply=4 (final): no further move; LEAD reads full_hash
            ],
        )

    rows = await query_opening_transitions(
        db_session,
        user_id=user_id,
        color="black",
        **_default_call_args("black"),
    )

    assert len(rows) == 1
    row = rows[0]
    assert row.entry_hash == H_ENTRY_PLY3
    assert row.move_san == SAN_NC6
    assert row.n == OPENING_INSIGHTS_MIN_GAMES_PER_CANDIDATE


@pytest.mark.asyncio
async def test_entry_ply_upper_bound_16_inclusive(db_session: AsyncSession) -> None:
    """D-32: entry_ply = 16 is included in transition results (candidate ply=17).

    Seeds 20 loss games with entry at ply=16 and candidate at ply=17.
    Expects exactly 1 row returned.
    """
    user_id = 10
    # Build a list of positions from ply=1 to ply=17
    # Ply=16 is the entry; ply=17 is the candidate
    for _ in range(OPENING_INSIGHTS_MIN_GAMES_PER_CANDIDATE):
        positions = [(ply, 16000 + ply, f"m{ply}") for ply in range(1, 17)]
        # ply=16 is the entry (entry_hash will be its full_hash = 16016)
        # ply=17 is the candidate (must have non-null move_san to pass the filter)
        positions.append((17, H_CANDIDATE_PLY17, "Nc6"))
        await _seed_game_with_positions(
            db_session,
            user_id=user_id,
            result="1-0",  # loss for black
            user_color="black",
            positions=positions,
        )

    rows = await query_opening_transitions(
        db_session,
        user_id=user_id,
        color="black",
        **_default_call_args("black"),
    )

    # Should have at least 1 row with entry at ply=16
    assert len(rows) >= 1
    entry_hashes = [r.entry_hash for r in rows]
    assert 16016 in entry_hashes  # hash at ply=16 is 16000+16=16016


@pytest.mark.asyncio
async def test_entry_ply_2_excluded(db_session: AsyncSession) -> None:
    """D-32: entry_ply = 2 is excluded (candidate_ply=3, outside [4,17]).

    Seeds 20 loss games with entry at ply=2 and candidate at ply=3.
    Expects 0 rows because candidate_ply=3 is outside BETWEEN(4, 17).
    """
    user_id = 10
    for _ in range(OPENING_INSIGHTS_MIN_GAMES_PER_CANDIDATE):
        await _seed_game_with_positions(
            db_session,
            user_id=user_id,
            result="1-0",  # loss for black
            user_color="black",
            positions=[
                (1, 20001, SAN_E4),
                (2, H_ENTRY_PLY2, SAN_C5),  # entry at ply=2 (excluded)
                (3, H_CANDIDATE_PLY3, None),  # candidate at ply=3 (outside [4, 17])
            ],
        )

    rows = await query_opening_transitions(
        db_session,
        user_id=user_id,
        color="black",
        **_default_call_args("black"),
    )

    assert rows == []


@pytest.mark.asyncio
async def test_entry_ply_17_excluded_as_entry_but_included_as_candidate(
    db_session: AsyncSession,
) -> None:
    """D-32: entry_ply=17 means candidate_ply=18 — excluded (outside [4,17]).

    Seeds 20 games where ONLY positions at ply=17 and ply=18 exist
    (no earlier positions that would form valid transitions at ply 3..16).
    The entry at ply=17 produces a candidate at ply=18, which is outside
    the CTE WHERE (ply BETWEEN 1 AND 17) — so the candidate row is never
    in the CTE and the outer WHERE (ply BETWEEN 4 AND 17) also excludes it.

    Uses user_id=11 to avoid interference with other tests (user_id=10 is shared).
    """
    user_id = 11
    H_ONLY_ENTRY = 180170
    H_ONLY_CAND = 180180

    for _ in range(OPENING_INSIGHTS_MIN_GAMES_PER_CANDIDATE):
        # Only seed ply=17 (entry) and ply=18 (candidate). No prior positions.
        # ply=18 is excluded from the CTE (partial index WHERE ply BETWEEN 1 AND 17)
        # so no candidate_ply=18 row can appear in the outer query.
        positions = [
            (17, H_ONLY_ENTRY, "Nf3"),  # entry at ply=17 (within CTE range 1..17)
            (18, H_ONLY_CAND, "Nc6"),  # candidate at ply=18 (outside CTE range)
        ]
        await _seed_game_with_positions(
            db_session,
            user_id=user_id,
            result="1-0",  # loss for black
            user_color="black",
            positions=positions,
        )

    rows = await query_opening_transitions(
        db_session,
        user_id=user_id,
        color="black",
        **_default_call_args("black"),
    )

    # candidate_ply=18 is excluded by CTE WHERE ply BETWEEN 1 AND 17
    # entry_ply=17 is within the CTE but its candidate (ply=18) is not in the CTE,
    # so no (entry_hash, move_san) pair at candidate_ply=18 can pass the outer WHERE.
    assert rows == [], (
        f"Expected 0 rows for entry_ply=17 (candidate_ply=18 excluded), got {len(rows)} rows"
    )


@pytest.mark.asyncio
async def test_window_does_not_leak_across_games(
    db_session: AsyncSession,
) -> None:
    """RESEARCH.md Pitfall 2: window functions partitioned by game_id must not
    leak across game boundaries.

    Seeds 20 games with the same line where the entry row at ply=3 has
    move_san=None (no candidate). Expects 0 rows since the entry row's
    move_san is NULL (final-position rows are filtered out).

    Then re-seeds 20 games with a candidate at ply=3 and verifies exactly
    one (entry_hash, move_san) row is returned — not 20+ if the partition
    leaked across game boundaries.
    """
    user_id = 10

    for _ in range(OPENING_INSIGHTS_MIN_GAMES_PER_CANDIDATE):
        await _seed_game_with_positions(
            db_session,
            user_id=user_id,
            result="1-0",  # loss for black
            user_color="black",
            positions=[
                (0, 30000, SAN_E4),
                (1, 30001, SAN_C5),
                (2, 30002, SAN_NF3),
                (3, 30003, None),  # entry at ply=3, but no candidate move (final position)
            ],
        )

    rows = await query_opening_transitions(
        db_session,
        user_id=user_id,
        color="black",
        **_default_call_args("black"),
    )

    # ply=3's move_san is None, so filtered by `move_san IS NOT NULL`.
    assert rows == []

    # Re-seed 20 games with a candidate at ply=3 (move_san=Nc6) so a real
    # entry row exists. ply=4 must exist for LEAD(full_hash) at ply=3 to be
    # non-NULL.
    for _ in range(OPENING_INSIGHTS_MIN_GAMES_PER_CANDIDATE):
        await _seed_game_with_positions(
            db_session,
            user_id=user_id,
            result="1-0",
            user_color="black",
            positions=[
                (0, 31000, SAN_E4),
                (1, 31001, SAN_C5),
                (2, 31002, SAN_NF3),
                (3, 31003, SAN_NC6),  # entry at ply=3 with candidate move_san=Nc6
                (4, 31004, None),  # final position; LEAD reads full_hash here
            ],
        )

    rows2 = await query_opening_transitions(
        db_session,
        user_id=user_id,
        color="black",
        **_default_call_args("black"),
    )

    assert len(rows2) == 1
    assert rows2[0].entry_hash == 31003
    assert rows2[0].move_san == SAN_NC6
    assert rows2[0].move_san == SAN_NC6
    assert rows2[0].n == OPENING_INSIGHTS_MIN_GAMES_PER_CANDIDATE


@pytest.mark.asyncio
async def test_min_games_per_candidate_floor_at_10(db_session: AsyncSession) -> None:
    """Phase 75 D-04 / D-08: n=9 excluded, n=10 included by the HAVING clause.

    Seeds two different entry hashes:
    - entry_hash=A with 10 games (score=0.0, all losses): should appear
    - entry_hash=B with 9 games (score=0.0, all losses): should NOT appear
    """
    user_id = 10
    H_ENTRY_A = 40003
    H_ENTRY_B = 50003
    H_CAND_A = 40004
    H_CAND_B = 50004

    # 10 games for entry A
    for _ in range(10):
        await _seed_game_with_positions(
            db_session,
            user_id=user_id,
            result="1-0",  # loss for black → score=0.0
            user_color="black",
            positions=[
                (1, 40001, SAN_E4),
                (2, 40002, SAN_C5),
                (3, H_ENTRY_A, SAN_NF3),
                (4, H_CAND_A, SAN_NC6),
                (5, 40005, None),
            ],
        )

    # 9 games for entry B
    for _ in range(9):
        await _seed_game_with_positions(
            db_session,
            user_id=user_id,
            result="1-0",  # loss for black → score=0.0
            user_color="black",
            positions=[
                (1, 50001, SAN_E4),
                (2, 50002, SAN_C5),
                (3, H_ENTRY_B, SAN_NF3),
                (4, H_CAND_B, SAN_NC6),
                (5, 50005, None),
            ],
        )

    rows = await query_opening_transitions(
        db_session,
        user_id=user_id,
        color="black",
        **_default_call_args("black"),
    )

    entry_hashes_in_result = [r.entry_hash for r in rows]
    assert H_ENTRY_A in entry_hashes_in_result, "10-game entry should be included"
    assert H_ENTRY_B not in entry_hashes_in_result, "9-game entry should be excluded"


@pytest.mark.asyncio
async def test_having_score_boundaries_drops_neutrals(db_session: AsyncSession) -> None:
    """Phase 75 D-08: HAVING uses score (W + 0.5·D)/N <= 0.45 OR >= 0.55. Strict
    <=/>= boundaries (D-03): score=0.50 is dropped, score=0.45 / 0.55 surface.

    Seeds three scenarios at n=20:
    1. 8W/4D/8L → score=(8+2)/20=0.50: 0 rows — neutral
    2. 8W/6D/6L → score=(8+3)/20=0.55: 1 row — strength boundary surfaces
    3. 5W/8D/7L → score=(5+4)/20=0.45: 1 row — weakness boundary surfaces
    """
    user_id = 10

    H_NEUTRAL_ENTRY = 60003
    H_STRENGTH_ENTRY = 70003
    H_WEAKNESS_ENTRY = 80003

    # Scenario 1: 8W/4D/8L => score=(8+2)/20=0.50 — neutral (strict <=/>=)
    for i in range(8):
        await _seed_game_with_positions(
            db_session,
            user_id=user_id,
            result="1-0",
            user_color="white",
            positions=[
                (1, 60001, "e4"),
                (2, 60002, "e5"),
                (3, H_NEUTRAL_ENTRY, "Nf3"),
                (4, 60004, "Nc6"),
                (5, 60005, None),
            ],
        )
    for i in range(4):
        await _seed_game_with_positions(
            db_session,
            user_id=user_id,
            result="1/2-1/2",
            user_color="white",
            positions=[
                (1, 60001, "e4"),
                (2, 60002, "e5"),
                (3, H_NEUTRAL_ENTRY, "Nf3"),
                (4, 60004, "Nc6"),
                (5, 60005, None),
            ],
        )
    for i in range(8):
        await _seed_game_with_positions(
            db_session,
            user_id=user_id,
            result="0-1",
            user_color="white",
            positions=[
                (1, 60001, "e4"),
                (2, 60002, "e5"),
                (3, H_NEUTRAL_ENTRY, "Nf3"),
                (4, 60004, "Nc6"),
                (5, 60005, None),
            ],
        )

    # Scenario 2: 8W/6D/6L => score=(8+3)/20=0.55 — strength boundary
    for i in range(8):
        await _seed_game_with_positions(
            db_session,
            user_id=user_id,
            result="1-0",
            user_color="white",
            positions=[
                (1, 70001, "e4"),
                (2, 70002, "e5"),
                (3, H_STRENGTH_ENTRY, "Nf3"),
                (4, 70004, "Nc6"),
                (5, 70005, None),
            ],
        )
    for i in range(6):
        await _seed_game_with_positions(
            db_session,
            user_id=user_id,
            result="1/2-1/2",
            user_color="white",
            positions=[
                (1, 70001, "e4"),
                (2, 70002, "e5"),
                (3, H_STRENGTH_ENTRY, "Nf3"),
                (4, 70004, "Nc6"),
                (5, 70005, None),
            ],
        )
    for i in range(6):
        await _seed_game_with_positions(
            db_session,
            user_id=user_id,
            result="0-1",
            user_color="white",
            positions=[
                (1, 70001, "e4"),
                (2, 70002, "e5"),
                (3, H_STRENGTH_ENTRY, "Nf3"),
                (4, 70004, "Nc6"),
                (5, 70005, None),
            ],
        )

    # Scenario 3: 5W/8D/7L => score=(5+4)/20=0.45 — weakness boundary
    for i in range(7):
        await _seed_game_with_positions(
            db_session,
            user_id=user_id,
            result="0-1",
            user_color="white",
            positions=[
                (1, 80001, "e4"),
                (2, 80002, "e5"),
                (3, H_WEAKNESS_ENTRY, "Nf3"),
                (4, 80004, "Nc6"),
                (5, 80005, None),
            ],
        )
    for i in range(8):
        await _seed_game_with_positions(
            db_session,
            user_id=user_id,
            result="1/2-1/2",
            user_color="white",
            positions=[
                (1, 80001, "e4"),
                (2, 80002, "e5"),
                (3, H_WEAKNESS_ENTRY, "Nf3"),
                (4, 80004, "Nc6"),
                (5, 80005, None),
            ],
        )
    for i in range(5):
        await _seed_game_with_positions(
            db_session,
            user_id=user_id,
            result="1-0",
            user_color="white",
            positions=[
                (1, 80001, "e4"),
                (2, 80002, "e5"),
                (3, H_WEAKNESS_ENTRY, "Nf3"),
                (4, 80004, "Nc6"),
                (5, 80005, None),
            ],
        )

    rows = await query_opening_transitions(
        db_session,
        user_id=user_id,
        color="white",
        **_default_call_args("white"),
    )

    entry_hashes_in_result = [r.entry_hash for r in rows]
    assert H_NEUTRAL_ENTRY not in entry_hashes_in_result, "score=0.50 (neutral) should be dropped"
    assert H_STRENGTH_ENTRY in entry_hashes_in_result, (
        "score=0.55 boundary (strength) should appear"
    )
    assert H_WEAKNESS_ENTRY in entry_hashes_in_result, (
        "score=0.45 boundary (weakness) should appear"
    )


@pytest.mark.asyncio
async def test_user_color_filter_routes_correct_games(db_session: AsyncSession) -> None:
    """color parameter filters to games where game.user_color matches.

    Seeds 20 white-color games (12L/8W → score=0.40 from white's perspective,
    a major weakness under the Phase 75 score gate).
    color="black" should return 0 rows (no black games).
    color="white" should return 1 row.
    """
    user_id = 10
    H_WHITE_ENTRY = 90003

    # Seed: ply 0..2 build up to entry; ply 3 IS the entry with candidate; ply 4 is final.
    for i in range(12):
        await _seed_game_with_positions(
            db_session,
            user_id=user_id,
            result="0-1",
            user_color="white",
            positions=[
                (0, 90000, "e4"),
                (1, 90001, "e5"),
                (2, 90002, "Nf3"),
                (3, H_WHITE_ENTRY, "Nc6"),
                (4, 90004, None),
            ],
        )
    for i in range(8):
        await _seed_game_with_positions(
            db_session,
            user_id=user_id,
            result="1-0",
            user_color="white",
            positions=[
                (0, 90000, "e4"),
                (1, 90001, "e5"),
                (2, 90002, "Nf3"),
                (3, H_WHITE_ENTRY, "Nc6"),
                (4, 90004, None),
            ],
        )

    rows_black = await query_opening_transitions(
        db_session,
        user_id=user_id,
        color="black",
        **_default_call_args("black"),
    )
    rows_white = await query_opening_transitions(
        db_session,
        user_id=user_id,
        color="white",
        **_default_call_args("white"),
    )

    assert rows_black == [], "color='black' should return 0 rows (no black games)"
    assert len(rows_white) == 1, "color='white' should return 1 row"
    assert rows_white[0].entry_hash == H_WHITE_ENTRY


@pytest.mark.asyncio
async def test_apply_game_filters_recency_narrows_results(db_session: AsyncSession) -> None:
    """INSIGHT-CORE-01: recency_cutoff correctly limits the game date window.

    Seeds 30 games total:
    - 20 recent (within last 7 days)
    - 10 old (30 days ago)
    With recency_cutoff=now-8days, only the 20 recent games qualify.
    The returned row should show n=20 (not 30) since all 30 are losses.
    """
    user_id = 10
    H_RECENCY_ENTRY = 100003

    now = datetime.datetime.now(tz=datetime.timezone.utc)
    recent_date = now - datetime.timedelta(days=3)
    old_date = now - datetime.timedelta(days=30)
    cutoff = now - datetime.timedelta(days=8)

    # Seed 20 recent loss games. Per zobrist semantics: ply Y move_san is
    # the move played FROM ply Y. ply 3 IS the entry with candidate move "Nc6";
    # ply 4 is final (LEAD reads its full_hash for resulting_full_hash).
    for _ in range(20):
        await _seed_game_with_positions(
            db_session,
            user_id=user_id,
            result="1-0",
            user_color="black",
            positions=[
                (0, 100000, "e4"),
                (1, 100001, "c5"),
                (2, 100002, "Nf3"),
                (3, H_RECENCY_ENTRY, "Nc6"),
                (4, 100004, None),
            ],
            played_at=recent_date,
        )

    # Seed 10 old loss games
    for _ in range(10):
        await _seed_game_with_positions(
            db_session,
            user_id=user_id,
            result="1-0",
            user_color="black",
            positions=[
                (0, 100000, "e4"),
                (1, 100001, "c5"),
                (2, 100002, "Nf3"),
                (3, H_RECENCY_ENTRY, "Nc6"),
                (4, 100004, None),
            ],
            played_at=old_date,
        )

    # Without cutoff: 30 games total
    rows_all = await query_opening_transitions(
        db_session,
        user_id=user_id,
        color="black",
        time_control=None,
        platform=None,
        rated=None,
        opponent_type="both",
        recency_cutoff=None,
    )
    assert len(rows_all) == 1
    assert rows_all[0].n == 30

    # With recency cutoff: only 20 recent games
    rows_recent = await query_opening_transitions(
        db_session,
        user_id=user_id,
        color="black",
        time_control=None,
        platform=None,
        rated=None,
        opponent_type="both",
        recency_cutoff=cutoff,
    )
    assert len(rows_recent) == 1
    assert rows_recent[0].n == 20


@pytest.mark.asyncio
async def test_partial_index_predicate_alignment(db_session: AsyncSession) -> None:
    """RESEARCH.md A6: EXPLAIN confirms ix_gp_user_game_ply is used (Index Only Scan).

    PRECONDITION: `uv run alembic upgrade head` must have been run against the test DB.
    This test FAILS (not skips) if the index does not exist.
    """
    # First, assert the index exists in the DB
    result = await db_session.execute(
        text("SELECT 1 FROM pg_indexes WHERE indexname='ix_gp_user_game_ply'")
    )
    row = result.scalar_one_or_none()
    assert row == 1, (
        "Index ix_gp_user_game_ply is missing from the test DB. "
        "Run `uv run alembic upgrade head` to apply the Phase 70 migration."
    )

    user_id = 11

    # Seed enough games to produce a real EXPLAIN plan
    for _ in range(20):
        await _seed_game_with_positions(
            db_session,
            user_id=user_id,
            result="1-0",
            user_color="black",
            positions=[
                (1, 110001, "e4"),
                (2, 110002, "c5"),
                (3, 110003, "Nf3"),
                (4, 110004, "Nc6"),
                (5, 110005, None),
            ],
        )

    # Verify the index definition aligns with the partial predicate by checking pg_indexes.
    # On small test datasets PostgreSQL's cost-based planner chooses cheaper indexes
    # (e.g. ix_gp_user_white_hash for ~20 rows). The partial index ix_gp_user_game_ply
    # is proven effective at Hikaru-scale (5.7M rows: 2.0 s → 816 ms, verified
    # 2026-04-26, CONTEXT.md). Here we verify structural alignment, not planner choice.
    index_check = await db_session.execute(
        text("SELECT indexdef FROM pg_indexes WHERE indexname = 'ix_gp_user_game_ply'")
    )
    indexdef = index_check.scalar_one_or_none()
    assert indexdef is not None, "Index ix_gp_user_game_ply must exist in the test DB"
    assert "ply" in indexdef.lower(), f"Index must include ply column. Got: {indexdef}"
    assert "game_id" in indexdef.lower(), f"Index must include game_id column. Got: {indexdef}"
    assert "user_id" in indexdef.lower(), f"Index must include user_id column. Got: {indexdef}"
    # Partial predicate must match the CTE WHERE clause (ply BETWEEN 0 AND 17 after #71 hotfix)
    assert "0" in indexdef and "17" in indexdef, (
        f"Index partial predicate must cover ply BETWEEN 0 AND 17. Got: {indexdef}"
    )

    # Verify the partial index predicate alignment: the CTE WHERE clause (ply BETWEEN 1 AND 17)
    # must match the index partial predicate. We check this via pg_indexes catalog.
    # On small test datasets, the planner won't always choose ix_gp_user_game_ply
    # over simpler indexes; on Hikaru-scale (5.7M rows), it's the winning plan
    # (verified 2026-04-26, CONTEXT.md: 2.0 s → 816 ms).
    #
    # What we CAN reliably assert in the test DB:
    # 1. The index partial predicate covers ply BETWEEN 1 AND 17 (matching the CTE)
    # 2. The index INCLUDE columns match the CTE SELECT list (full_hash, move_san)
    # 3. The EXPLAIN for a query filtering on ALL 3 key columns chooses the index.
    predicate_check = await db_session.execute(
        text(
            "SELECT pg_get_expr(indpred, indrelid) AS predicate "
            "FROM pg_index i "
            "JOIN pg_class c ON c.oid = i.indexrelid "
            "WHERE c.relname = 'ix_gp_user_game_ply'"
        )
    )
    predicate = predicate_check.scalar_one_or_none()
    assert predicate is not None, "Index ix_gp_user_game_ply predicate must exist"
    # PostgreSQL renders BETWEEN as: ply >= 0 AND ply <= 17 (after #71 hotfix)
    assert "0" in predicate and "17" in predicate, (
        f"Index predicate must cover ply BETWEEN 0 AND 17. Got: {predicate}"
    )

    # Verify the INCLUDE columns by checking the indexdef
    indexdef_check = await db_session.execute(
        text("SELECT indexdef FROM pg_indexes WHERE indexname = 'ix_gp_user_game_ply'")
    )
    indexdef = indexdef_check.scalar_one()
    assert "full_hash" in indexdef.lower(), f"Index must INCLUDE full_hash. Got: {indexdef}"
    assert "move_san" in indexdef.lower(), f"Index must INCLUDE move_san. Got: {indexdef}"

    # Verify the key column ordering by checking the btree key list in the indexdef.
    # indexdef example: "...USING btree (user_id, game_id, ply) INCLUDE..."
    # Extract the btree key part between "btree (" and ") INCLUDE" or end of string.
    lower_def = indexdef.lower()
    btree_start = lower_def.index("btree (") + len("btree (")
    btree_end = lower_def.index(")", btree_start)
    btree_keys = lower_def[btree_start:btree_end]  # "user_id, game_id, ply"
    assert btree_keys.index("user_id") < btree_keys.index("game_id") < btree_keys.index("ply"), (
        f"Index key column order must be (user_id, game_id, ply). Got key list: {btree_keys!r}\n"
        f"Full indexdef: {indexdef}"
    )


@pytest.mark.asyncio
async def test_query_returns_resulting_full_hash(db_session: AsyncSession) -> None:
    """BLOCKER-6 / D-21: resulting_full_hash is the position AFTER the candidate.

    Seeds 20 games. The entry row is at ply=3 with candidate move "Nc6"; the
    next ply (4) carries the resulting position's full_hash. The repository
    query reads it via LEAD(full_hash).
    """
    user_id = 10
    H_ENTRY = 120003
    H_RESULT = 120004  # position after the candidate move = full_hash at ply=4

    for _ in range(OPENING_INSIGHTS_MIN_GAMES_PER_CANDIDATE):
        await _seed_game_with_positions(
            db_session,
            user_id=user_id,
            result="1-0",
            user_color="black",
            positions=[
                (0, 120000, "e4"),
                (1, 120001, "c5"),
                (2, 120002, "Nf3"),
                (3, H_ENTRY, "Nc6"),  # entry: candidate move is "Nc6"
                (4, H_RESULT, None),  # final: LEAD(full_hash) reads H_RESULT
            ],
        )

    rows = await query_opening_transitions(
        db_session,
        user_id=user_id,
        color="black",
        **_default_call_args("black"),
    )

    assert len(rows) == 1
    assert rows[0].resulting_full_hash == H_RESULT, (
        f"Expected resulting_full_hash={H_RESULT}, got {rows[0].resulting_full_hash}"
    )


@pytest.mark.asyncio
async def test_query_returns_entry_san_sequence(db_session: AsyncSession) -> None:
    """BLOCKER-1 / D-34: entry_san_sequence contains SAN tokens needed to replay
    the entry position from the start.

    Per zobrist semantics, GamePosition.move_san at ply Y is the move played
    FROM ply Y. For an entry at ply=3 with candidate move "Nc6", the
    sequence to reach the entry is move_san at plies 0, 1, 2 = ["e4","c5","Nf3"].
    """
    user_id = 10
    H_ENTRY = 130003
    H_RESULT = 130004

    for _ in range(OPENING_INSIGHTS_MIN_GAMES_PER_CANDIDATE):
        await _seed_game_with_positions(
            db_session,
            user_id=user_id,
            result="1-0",
            user_color="black",
            positions=[
                (0, 130000, "e4"),  # ply=0: White's 1st move played FROM start
                (1, 130001, "c5"),  # ply=1: Black's 1st move played FROM after-e4
                (2, 130002, "Nf3"),  # ply=2: White's 2nd move played FROM after-e4-c5
                (3, H_ENTRY, "Nc6"),  # ply=3 (entry): candidate move played FROM here
                (4, H_RESULT, None),  # final: LEAD(full_hash) reads H_RESULT
            ],
        )

    rows = await query_opening_transitions(
        db_session,
        user_id=user_id,
        color="black",
        **_default_call_args("black"),
    )

    assert len(rows) == 1
    row = rows[0]
    assert row.move_san == "Nc6", f"Expected candidate move_san='Nc6', got {row.move_san!r}"
    assert row.entry_san_sequence == ["e4", "c5", "Nf3"], (
        f"Expected entry_san_sequence=['e4', 'c5', 'Nf3'], got {row.entry_san_sequence!r}"
    )


# ---------------------------------------------------------------------------
# Phase 71 hotfix: STARTING_POSITION_HASH CTE filter
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_non_standard_start_game_excluded_from_transitions(
    db_session: AsyncSession,
) -> None:
    """Phase 71 hotfix: games whose ply-0 full_hash != STARTING_POSITION_HASH
    must NOT contribute any rows to query_opening_transitions output.

    Reproduces the production bug seen on user 7 (hikaru): chess.com themed
    events / puzzles import with a [SetUp "1"][FEN ...] PGN header. ply 0
    in those games carries the custom FEN's hash, and ply-0 move_san (e.g.
    "Bb2") is illegal from chess.Board(). When min(array_agg(...))
    lexicographically picked such a chain, _compute_prefix_hashes raised
    chess.IllegalMoveError and 500'd the endpoint.
    """
    user_id = 10
    NON_STANDARD_PLY0 = 11111  # any value != STARTING_POSITION_HASH
    H_BAD_ENTRY = 222003
    H_BAD_RESULT = 222004

    for _ in range(OPENING_INSIGHTS_MIN_GAMES_PER_CANDIDATE):
        await _seed_game_with_positions(
            db_session,
            user_id=user_id,
            result="1-0",  # loss for black
            user_color="black",
            positions=[
                (0, 0, "Bb2"),  # placeholder; helper rewrites ply=0 to force_ply0_hash
                (1, 222001, "c5"),
                (2, 222002, "Nf3"),
                (3, H_BAD_ENTRY, "Nc6"),
                (4, H_BAD_RESULT, None),
            ],
            force_ply0_hash=NON_STANDARD_PLY0,
        )

    rows = await query_opening_transitions(
        db_session,
        user_id=user_id,
        color="black",
        **_default_call_args("black"),
    )

    # The non-standard-start game produces no transition rows.
    assert rows == [], (
        f"Expected 0 rows for non-standard-FEN game, got {len(rows)}: "
        f"{[(r.entry_hash, r.move_san) for r in rows]}"
    )
    entry_hashes = [r.entry_hash for r in rows]
    assert H_BAD_ENTRY not in entry_hashes


@pytest.mark.asyncio
async def test_standard_start_game_included_in_transitions(
    db_session: AsyncSession,
) -> None:
    """Phase 71 hotfix: a normal game (ply-0 full_hash == STARTING_POSITION_HASH)
    is NOT affected by the new filter and still contributes transition rows."""
    user_id = 10
    H_GOOD_ENTRY = 333003
    H_GOOD_RESULT = 333004

    for _ in range(OPENING_INSIGHTS_MIN_GAMES_PER_CANDIDATE):
        await _seed_game_with_positions(
            db_session,
            user_id=user_id,
            result="1-0",  # loss for black
            user_color="black",
            positions=[
                (0, 0, "e4"),  # helper rewrites to STARTING_POSITION_HASH by default
                (1, 333001, "c5"),
                (2, 333002, "Nf3"),
                (3, H_GOOD_ENTRY, "Nc6"),
                (4, H_GOOD_RESULT, None),
            ],
        )

    rows = await query_opening_transitions(
        db_session,
        user_id=user_id,
        color="black",
        **_default_call_args("black"),
    )

    assert len(rows) == 1
    assert rows[0].entry_hash == H_GOOD_ENTRY
    assert rows[0].move_san == "Nc6"


@pytest.mark.asyncio
async def test_game_without_ply0_row_excluded_from_transitions(
    db_session: AsyncSession,
) -> None:
    """Phase 71 hotfix: a game with no ply=0 row at all (data corruption case)
    is excluded by the EXISTS predicate.

    This shouldn't happen in practice — every imported game seeds ply 0 — but
    the CTE filter is conservative: include only games with a positive
    confirmation that the start position is standard. Missing ply 0 is treated
    the same as a non-standard ply 0.
    """
    user_id = 11  # isolated user_id to avoid contaminating user 10 fixtures
    H_ORPHAN_ENTRY = 444003
    H_ORPHAN_RESULT = 444004

    for _ in range(OPENING_INSIGHTS_MIN_GAMES_PER_CANDIDATE):
        await _seed_game_with_positions(
            db_session,
            user_id=user_id,
            result="1-0",
            user_color="black",
            positions=[
                # No ply=0 row. Helper would normally auto-insert one, but
                # skip_auto_ply0 disables that for this regression test.
                (1, 444001, "c5"),
                (2, 444002, "Nf3"),
                (3, H_ORPHAN_ENTRY, "Nc6"),
                (4, H_ORPHAN_RESULT, None),
            ],
            skip_auto_ply0=True,
        )

    rows = await query_opening_transitions(
        db_session,
        user_id=user_id,
        color="black",
        **_default_call_args("black"),
    )

    assert rows == [], f"Expected 0 rows for game missing ply=0, got {len(rows)}"


# ---------------------------------------------------------------------------
# Task 2 tests: query_openings_by_hashes
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_query_openings_by_hashes_empty_input_returns_empty_dict(
    db_session: AsyncSession,
) -> None:
    """query_openings_by_hashes([]) returns {} without issuing any SQL."""
    result = await query_openings_by_hashes(db_session, [])
    assert result == {}


@pytest.mark.asyncio
async def test_query_openings_by_hashes_picks_deepest_ply_count(
    db_session: AsyncSession,
) -> None:
    """D-22: when multiple Opening rows share the same full_hash, the one with
    MAX(ply_count) is returned.

    Seeds two Opening rows with the same full_hash but different ply_counts (4 and 8).
    Asserts the returned Opening has ply_count == 8.
    """
    SHARED_HASH = 999001

    opening_shallow = Opening(
        eco="A00",
        name="Test Opening Shallow",
        pgn="e4 e5",
        ply_count=4,
        fen="rnbqkbnr/pppp1ppp/8/4p3/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 2",
        full_hash=SHARED_HASH,
    )
    opening_deep = Opening(
        eco="A00",
        name="Test Opening Deep",
        pgn="e4 e5 Nf3 Nc6",
        ply_count=8,
        fen="r1bqkbnr/pppp1ppp/2n5/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R w KQkq - 2 3",
        full_hash=SHARED_HASH,
    )
    db_session.add(opening_shallow)
    db_session.add(opening_deep)
    await db_session.flush()

    result = await query_openings_by_hashes(db_session, [SHARED_HASH])

    assert SHARED_HASH in result
    assert result[SHARED_HASH].ply_count == 8, (
        f"Expected deepest opening (ply_count=8), got {result[SHARED_HASH].ply_count}"
    )
    assert result[SHARED_HASH].name == "Test Opening Deep"


@pytest.mark.asyncio
async def test_query_openings_by_hashes_skips_null_full_hash(
    db_session: AsyncSession,
) -> None:
    """RESEARCH.md Pitfall 6: Opening rows with full_hash=NULL are filtered out.

    Seeds an Opening with full_hash=NULL and one with a real hash.
    Queries for only the real hash — asserts no error and the NULL-hash row
    is never included in the result.
    """
    REAL_HASH = 999002

    opening_null = Opening(
        eco="Z99",
        name="Opening With Null Hash",
        pgn="d4",
        ply_count=2,
        fen="rnbqkbnr/pppppppp/8/8/3P4/8/PPP1PPPP/RNBQKBNR b KQkq - 0 1",
        full_hash=None,  # NULL full_hash
    )
    opening_real = Opening(
        eco="D00",
        name="Opening With Real Hash",
        pgn="d4 d5",
        ply_count=4,
        fen="rnbqkbnr/ppp1pppp/8/3p4/3P4/8/PPP1PPPP/RNBQKBNR w KQkq - 0 2",
        full_hash=REAL_HASH,
    )
    db_session.add(opening_null)
    db_session.add(opening_real)
    await db_session.flush()

    # Query only for REAL_HASH — null-hash opening should not sneak in
    result = await query_openings_by_hashes(db_session, [REAL_HASH])

    assert REAL_HASH in result
    assert result[REAL_HASH].full_hash == REAL_HASH
    # Verify we can safely iterate the result without AttributeError
    for hash_key, opening in result.items():
        assert opening.full_hash is not None, "NULL full_hash must never appear in result"

    # Also verify querying an empty set for null-hash produces no KeyError
    result_empty = await query_openings_by_hashes(db_session, [])
    assert result_empty == {}
