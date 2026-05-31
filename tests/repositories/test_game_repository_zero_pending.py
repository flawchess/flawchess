"""Tests for users_with_zero_pending repository helper (WR-01 fix, Phase 94.1-12).

Locks the single-query contract: the aggregated helper MUST issue exactly ONE
SQL statement, and its return set MUST match a per-user count_pending_evals loop.

Phase 94.1 Plan 13 (gap-closure): extends the helper with an active-import gate.
Users with pending/in_progress import_jobs are excluded even when their pending-eval
count is zero. Test 7 below pins this contract.

Data isolation: all tests use the rollback-scoped ``db_session`` fixture from
``tests/conftest.py`` — no committed rows leak between tests.
"""

from __future__ import annotations

import datetime
import itertools
import uuid

import pytest
from sqlalchemy import event as sa_event
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.game import Game
from app.models.import_job import ImportJob
from app.repositories.game_repository import (
    count_pending_evals,
    users_with_zero_pending,
)

# Test constants — no magic numbers
_USER_A_ID: int = 99700
_USER_B_ID: int = 99701
_USER_C_ID: int = 99702
_USER_NO_GAMES_ID: int = 99703
_MIXED_COHORT_BASE_ID: int = 99800  # 5 users at 99800..99804
_MIXED_COHORT_SIZE: int = 5

# Additional users for Plan 13 Stage B gate tests (Test 7)
_IMPORT_GATE_USER_A_ID: int = 99710  # zero pending evals + no active import → returned
_IMPORT_GATE_USER_B_ID: int = 99711  # zero pending evals + in_progress import → excluded
_IMPORT_GATE_USER_C_ID: int = 99712  # zero pending evals + pending import → excluded
_IMPORT_GATE_USER_D_ID: int = 99713  # zero pending evals + completed import → returned

_FIXED_PLAYED_AT: datetime.datetime = datetime.datetime(
    2026, 1, 1, 12, 0, 0, tzinfo=datetime.timezone.utc
)
_FIXED_COMPLETED_AT: datetime.datetime = datetime.datetime(
    2026, 1, 2, 12, 0, 0, tzinfo=datetime.timezone.utc
)

pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# Seed helpers
# ---------------------------------------------------------------------------

_game_id_counter = itertools.count(1)


def _unique_platform_game_id() -> str:
    """Return a unique platform_game_id for each seeded Game (within one test)."""
    return f"zp-test-{next(_game_id_counter)}"


async def _seed_game(
    db_session: AsyncSession,
    user_id: int,
    *,
    evals_completed: bool,
) -> None:
    """Insert one Game for the given user. evals_completed=True sets evals_completed_at."""
    game = Game(
        user_id=user_id,
        platform="chess.com",
        platform_game_id=_unique_platform_game_id(),
        platform_url="https://chess.com/game/zp",
        pgn="1. e4 e5 *",
        result="1-0",
        user_color="white",
        time_control_str="600+0",
        time_control_bucket="blitz",
        time_control_seconds=600,
        rated=True,
        white_username="zptest",
        black_username="opponent",
    )
    game.played_at = _FIXED_PLAYED_AT
    if evals_completed:
        game.evals_completed_at = _FIXED_COMPLETED_AT
    db_session.add(game)
    await db_session.flush()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
async def _ensure_test_users(db_session: AsyncSession) -> None:
    """Insert all users referenced by FK constraints."""
    from tests.conftest import ensure_test_user

    base_uids = (_USER_A_ID, _USER_B_ID, _USER_C_ID, _USER_NO_GAMES_ID)
    mixed_uids = tuple(_MIXED_COHORT_BASE_ID + i for i in range(_MIXED_COHORT_SIZE))
    import_gate_uids = (
        _IMPORT_GATE_USER_A_ID,
        _IMPORT_GATE_USER_B_ID,
        _IMPORT_GATE_USER_C_ID,
        _IMPORT_GATE_USER_D_ID,
    )
    for uid in base_uids + mixed_uids + import_gate_uids:
        await ensure_test_user(db_session, uid)


# ---------------------------------------------------------------------------
# Test 1 — empty input short-circuits, no DB hit
# ---------------------------------------------------------------------------


async def test_empty_input_returns_empty_list(db_session: AsyncSession) -> None:
    """users_with_zero_pending(session, []) returns [] without issuing SQL."""
    result = await users_with_zero_pending(db_session, [])
    assert result == []


# ---------------------------------------------------------------------------
# Test 2 — all users have zero pending → all returned
# ---------------------------------------------------------------------------


async def test_all_users_have_zero_pending(db_session: AsyncSession) -> None:
    """Three users, all games evals_completed_at NOT NULL → helper returns all 3."""
    for uid in (_USER_A_ID, _USER_B_ID, _USER_C_ID):
        await _seed_game(db_session, uid, evals_completed=True)
        await _seed_game(db_session, uid, evals_completed=True)

    result = await users_with_zero_pending(db_session, [_USER_A_ID, _USER_B_ID, _USER_C_ID])
    assert set(result) == {_USER_A_ID, _USER_B_ID, _USER_C_ID}


# ---------------------------------------------------------------------------
# Test 3 — mixed pending counts → only zero-pending user returned
# ---------------------------------------------------------------------------


async def test_mixed_pending_counts(db_session: AsyncSession) -> None:
    """User A has 0 pending, B has 2 pending, C has 1 pending → only A returned."""
    # User A: 1 completed
    await _seed_game(db_session, _USER_A_ID, evals_completed=True)
    # User B: 2 pending
    await _seed_game(db_session, _USER_B_ID, evals_completed=False)
    await _seed_game(db_session, _USER_B_ID, evals_completed=False)
    # User C: 1 pending + 1 completed (still has pending → not returned)
    await _seed_game(db_session, _USER_C_ID, evals_completed=False)
    await _seed_game(db_session, _USER_C_ID, evals_completed=True)

    result = await users_with_zero_pending(db_session, [_USER_A_ID, _USER_B_ID, _USER_C_ID])
    assert set(result) == {_USER_A_ID}


# ---------------------------------------------------------------------------
# Test 4 — user with no games at all → returned (LEFT JOIN preserves them)
# ---------------------------------------------------------------------------


async def test_user_with_zero_games_returns_user(db_session: AsyncSession) -> None:
    """A user with NO games at all has zero pending by definition; LEFT JOIN keeps them."""
    # No seed for _USER_NO_GAMES_ID — user exists but owns no games.
    result = await users_with_zero_pending(db_session, [_USER_NO_GAMES_ID])
    assert result == [_USER_NO_GAMES_ID]


# ---------------------------------------------------------------------------
# Test 5 — aggregated helper matches the per-user loop it replaces
# ---------------------------------------------------------------------------


async def test_aggregate_matches_per_user_loop(db_session: AsyncSession) -> None:
    """Regression: aggregated helper return set equals the per-user count_pending_evals loop.

    This is the contract the WR-01 fix must preserve. Seed a mixed cohort of 5
    users with a deterministic mix of 0 / 1 / many pending, then verify the
    aggregated result equals the set of uids with count_pending_evals == 0.
    """
    uids = [_MIXED_COHORT_BASE_ID + i for i in range(_MIXED_COHORT_SIZE)]
    # Deterministic seed pattern:
    #   user 0: 0 pending, 1 completed       → zero-pending
    #   user 1: 2 pending                    → has pending
    #   user 2: no games at all              → zero-pending (LEFT JOIN)
    #   user 3: 1 pending, 1 completed       → has pending
    #   user 4: 3 completed                  → zero-pending
    await _seed_game(db_session, uids[0], evals_completed=True)
    await _seed_game(db_session, uids[1], evals_completed=False)
    await _seed_game(db_session, uids[1], evals_completed=False)
    # uids[2]: nothing
    await _seed_game(db_session, uids[3], evals_completed=False)
    await _seed_game(db_session, uids[3], evals_completed=True)
    for _ in range(3):
        await _seed_game(db_session, uids[4], evals_completed=True)

    aggregated = set(await users_with_zero_pending(db_session, uids))

    per_user_zero: set[int] = set()
    for uid in uids:
        if await count_pending_evals(db_session, uid) == 0:
            per_user_zero.add(uid)

    assert aggregated == per_user_zero
    # Sanity: the expected set matches the seed pattern.
    assert aggregated == {uids[0], uids[2], uids[4]}


# ---------------------------------------------------------------------------
# Test 6 — single-query contract: exactly ONE SQL statement issued
# ---------------------------------------------------------------------------


async def test_users_with_zero_pending_issues_single_query(
    db_session: AsyncSession,
) -> None:
    """Lock the WR-01 contract: helper issues exactly ONE SQL statement.

    Attaches a SQLAlchemy ``before_cursor_execute`` event listener to the
    underlying sync engine of the async connection, calls the helper, and
    asserts exactly one query was observed.
    """
    # Seed a mixed cohort so the query has real data to scan.
    await _seed_game(db_session, _USER_A_ID, evals_completed=True)
    await _seed_game(db_session, _USER_B_ID, evals_completed=False)
    await _seed_game(db_session, _USER_C_ID, evals_completed=True)

    statements: list[str] = []

    def _on_exec(conn, cursor, statement, parameters, context, executemany) -> None:  # noqa: ANN001 — SQLAlchemy event signature
        statements.append(statement)

    # Resolve the sync engine via the async connection's sync sibling.
    # async_session.bind is the AsyncConnection; .sync_engine gives the Engine.
    bind = db_session.bind
    sync_engine = bind.sync_engine  # type: ignore[union-attr]

    sa_event.listen(sync_engine, "before_cursor_execute", _on_exec)
    try:
        result = await users_with_zero_pending(db_session, [_USER_A_ID, _USER_B_ID, _USER_C_ID])
    finally:
        sa_event.remove(sync_engine, "before_cursor_execute", _on_exec)

    # _USER_A_ID and _USER_C_ID are zero-pending; _USER_B_ID has 1 pending.
    assert set(result) == {_USER_A_ID, _USER_C_ID}

    # Count actual data-fetching statements; filter out savepoints/begin/commit noise.
    query_count = sum(1 for s in statements if "FROM" in s.upper())
    assert query_count == 1, f"expected 1 query, got {query_count}: {statements}"


# ---------------------------------------------------------------------------
# Test 7 — Plan 13 Stage B gate: users with active imports are excluded
# ---------------------------------------------------------------------------


async def _seed_import_job(
    db_session: AsyncSession,
    user_id: int,
    status: str,
) -> None:
    """Insert one ImportJob row for the given user with the given status."""
    job = ImportJob(
        id=str(uuid.uuid4()),
        user_id=user_id,
        platform="lichess",
        username=f"testuser{user_id}",
        status=status,
        games_fetched=0,
        games_imported=0,
    )
    db_session.add(job)
    await db_session.flush()


async def test_users_with_active_imports_are_excluded_from_stage_b(
    db_session: AsyncSession,
) -> None:
    """Plan 13 Stage B gate: users with pending/in_progress imports are excluded.

    Seeds 4 users, all with zero pending evals:
    - User A: zero pending evals + NO active import → returned (should fire Stage B)
    - User B: zero pending evals + in_progress import → excluded (Stage B deferred)
    - User C: zero pending evals + pending import → excluded (Stage B deferred)
    - User D: zero pending evals + completed import → returned (completed = no longer active)

    This pins the Plan 13 correctness requirement: Stage B must NOT fire for users
    mid-import, even when their pending-eval count is zero. Without this gate,
    Stage B fires multiple times as eval batches drain, producing transient
    intermediate values visible on the chip.
    """
    # All 4 users: zero pending evals (one completed game each).
    for uid in (
        _IMPORT_GATE_USER_A_ID,
        _IMPORT_GATE_USER_B_ID,
        _IMPORT_GATE_USER_C_ID,
        _IMPORT_GATE_USER_D_ID,
    ):
        await _seed_game(db_session, uid, evals_completed=True)

    # Seed import_jobs per scenario
    # User A: no import_job row at all → no active import
    await _seed_import_job(db_session, _IMPORT_GATE_USER_B_ID, status="in_progress")
    await _seed_import_job(db_session, _IMPORT_GATE_USER_C_ID, status="pending")
    await _seed_import_job(db_session, _IMPORT_GATE_USER_D_ID, status="completed")

    result = await users_with_zero_pending(
        db_session,
        [
            _IMPORT_GATE_USER_A_ID,
            _IMPORT_GATE_USER_B_ID,
            _IMPORT_GATE_USER_C_ID,
            _IMPORT_GATE_USER_D_ID,
        ],
    )

    result_set = set(result)

    # Users A and D should be returned (no active import)
    assert _IMPORT_GATE_USER_A_ID in result_set, (
        "User A (no active import) must be returned to fire Stage B"
    )
    assert _IMPORT_GATE_USER_D_ID in result_set, (
        "User D (completed import) must be returned — completed is not active"
    )

    # Users B and C must be excluded (active imports)
    assert _IMPORT_GATE_USER_B_ID not in result_set, (
        "User B (in_progress import) must be excluded — Stage B must not fire mid-import"
    )
    assert _IMPORT_GATE_USER_C_ID not in result_set, (
        "User C (pending import) must be excluded — Stage B must not fire mid-import"
    )
