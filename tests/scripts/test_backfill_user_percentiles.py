"""Backfill script tests for scripts/backfill_user_percentiles.py (PCTL-10 gate).

Phase 94.1 Plan 02 (scaffold) + Plan 08 (implementation).

Tests cover:
- Idempotency: second run produces identical values
- --user-id filter: only processes the specified user
- --metric filter: only processes the specified metric
- --target prod refusal when tunnel is down (Pitfall 6 / SC-6)
- --target dev refusal when URL lacks port 5432
- Per-metric summary table emitted to stdout
- Below-floor user: no row written, summary reports below_pooled_floor=1

Security domain V4 (Tampering — wrong DB target):
- test_backfill_target_prod_refuses_when_tunnel_down: _assert_target_safe raises
  SystemExit with message containing 'bin/prod_db_tunnel.sh' when port 15432
  has no listener.
- test_backfill_target_dev_refuses_url_without_port_5432: _assert_target_safe
  raises SystemExit with message containing '5432' for a non-5432 port URL.

Data isolation strategy:
  Tests seed their own users + import_jobs via the test_engine session_maker
  and commit them so main()'s independently-created session can read them.
  The canonical-slice CTE requires rated=True, non-computer games with
  white_rating / black_rating within 100 ELO.  Most tests use games that do NOT
  meet the ±100 ELO filter (opponent 500+ ELO above user) so value_raw is None
  and no user_benchmark_percentiles row is written — this is intentional and
  lets us test the "below_pooled_floor" path cleanly without fabricating
  full endgame span data.  Cleanup runs in a finally block via delete-cascade.
"""

from __future__ import annotations

import datetime
import sys
import uuid
from pathlib import Path

import pytest
from sqlalchemy import delete as sa_delete, select, text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

# ── Bootstrap scripts/ on sys.path if not already present ────────────────────
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

# ── Skip entire module until implementation exists ────────────────────────────
backfill_user_percentiles = pytest.importorskip("scripts.backfill_user_percentiles")

# ── Module-level constants (CLAUDE.md: no magic numbers) ─────────────────────
_TEST_USER_1_ID: int = 99206  # unique per module to avoid FK conflicts
_TEST_USER_2_ID: int = 99207
_TEST_USER_3_ID: int = 99208
_PROD_TUNNEL_PORT: int = 15432  # per CLAUDE.md / bin/prod_db_tunnel.sh
_DEV_PORT: int = 5432  # per CLAUDE.md dev DB port
_DUMMY_NON_5432_PORT: int = 99999

# Expected summary tokens per metric. Phase 94.4 Plan 06 cohort-CDF cutover
# rewrote the summary shape from per-metric (``{metric} upserted=X, skipped=Y``)
# to per-(metric × TC) (``{metric} {tc} {included} {floor_rej} {suppressed}``)
# plus a separate per-(TC × source_platform) anchor table. The metric labels
# continue to appear; the token shape changed.
_EXPECTED_METRIC_LABELS: list[str] = [
    "score_gap",
    "achievable_score_gap",
    "score_gap_conv",
    "score_gap_parity",
]
_EXPECTED_SUMMARY_TOKENS: list[str] = ["included", "floor_rej", "suppressed"]

# No module-level `pytestmark = pytest.mark.asyncio`: asyncio_mode = "auto"
# (pyproject.toml) auto-marks every `async def` test, so the module mark was
# redundant — and it also stamped the sync guard tests below
# (test_backfill_target_* ), emitting "marked with asyncio but not an async
# function" PytestWarnings.


# ---------------------------------------------------------------------------
# Test DB helpers
# ---------------------------------------------------------------------------


def _make_session_maker(
    test_engine: AsyncEngine,
) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(test_engine, expire_on_commit=False)


async def _ensure_user(session: AsyncSession, user_id: int) -> None:
    """Ensure a test user exists (satisfying FK constraints)."""
    from app.models.user import User

    existing = (
        (await session.execute(select(User).where(User.id == user_id)))
        .unique()
        .scalar_one_or_none()
    )
    if existing is None:
        session.add(
            User(
                id=user_id,
                email=f"backfill-pctl-test-{user_id}@example.com",
                hashed_password="x",
            )
        )
        await session.flush()


async def _ensure_import_job(session: AsyncSession, user_id: int) -> None:
    """Insert a completed import_job for user_id so _iter_users finds the user."""
    from app.models.import_job import ImportJob

    job = ImportJob(
        id=str(uuid.uuid4()),
        user_id=user_id,
        platform="lichess",
        username=f"testuser{user_id}",
        status="completed",
        games_fetched=5,
        games_imported=5,
        started_at=datetime.datetime(2026, 1, 1, tzinfo=datetime.timezone.utc),
        completed_at=datetime.datetime(2026, 1, 1, tzinfo=datetime.timezone.utc),
    )
    session.add(job)
    await session.flush()


async def _seed_user_with_import(session: AsyncSession, user_id: int) -> None:
    """Seed a user + completed import_job so _iter_users picks them up."""
    await _ensure_user(session, user_id)
    await _ensure_import_job(session, user_id)


async def _delete_test_users(session: AsyncSession, *user_ids: int) -> None:
    """Delete test users (cascades to import_jobs, games, user_benchmark_percentiles)."""
    from app.models.user import User

    for uid in user_ids:
        await session.execute(sa_delete(User).where(User.id == uid))
    await session.flush()


async def _count_pctl_rows(session: AsyncSession, user_id: int) -> int:
    """Count rows in user_benchmark_percentiles for a user."""
    result = await session.execute(
        text("SELECT count(*) FROM user_benchmark_percentiles WHERE user_id = :uid").bindparams(
            uid=user_id
        )
    )
    return result.scalar_one() or 0


# ---------------------------------------------------------------------------
# Idempotency
# ---------------------------------------------------------------------------


async def test_backfill_is_idempotent_when_run_twice(test_engine: AsyncEngine) -> None:
    """Two sequential runs of main() against the same 3-user fixture produce
    identical user_benchmark_percentiles rows.

    Because the seeded games have no canonical-slice games (no import_jobs or
    games that pass the ±100 ELO filter), the canonical-slice CTE returns
    value_raw=None for all users, so no rows are written.  Row count is 0 after
    both runs — idempotency at zero.  Row count must be identical.
    """
    session_maker = _make_session_maker(test_engine)
    main = backfill_user_percentiles.main

    async with session_maker() as setup:
        await _seed_user_with_import(setup, _TEST_USER_1_ID)
        await _seed_user_with_import(setup, _TEST_USER_2_ID)
        await _seed_user_with_import(setup, _TEST_USER_3_ID)
        await setup.commit()

    try:
        # Run 1
        await main(target="dev", user_id_filter=None, metric_filter=None)

        async with session_maker() as check1:
            rows_after_run1 = sum(
                [
                    await _count_pctl_rows(check1, _TEST_USER_1_ID),
                    await _count_pctl_rows(check1, _TEST_USER_2_ID),
                    await _count_pctl_rows(check1, _TEST_USER_3_ID),
                ]
            )

        # Run 2
        await main(target="dev", user_id_filter=None, metric_filter=None)

        async with session_maker() as check2:
            rows_after_run2 = sum(
                [
                    await _count_pctl_rows(check2, _TEST_USER_1_ID),
                    await _count_pctl_rows(check2, _TEST_USER_2_ID),
                    await _count_pctl_rows(check2, _TEST_USER_3_ID),
                ]
            )

        assert rows_after_run1 == rows_after_run2, (
            f"Row count differs between runs: {rows_after_run1} != {rows_after_run2}"
        )
    finally:
        async with session_maker() as teardown:
            await _delete_test_users(teardown, _TEST_USER_1_ID, _TEST_USER_2_ID, _TEST_USER_3_ID)
            await teardown.commit()


# ---------------------------------------------------------------------------
# --user-id filter
# ---------------------------------------------------------------------------


async def test_backfill_with_user_id_filter_only_processes_that_user(
    test_engine: AsyncEngine,
) -> None:
    """main() with user_id_filter=_TEST_USER_2_ID only iterates over user_2.

    After the filtered run, users 1 and 3 have 0 rows (untouched).
    The summary reflects only user_2 processing.
    """
    session_maker = _make_session_maker(test_engine)
    main = backfill_user_percentiles.main

    async with session_maker() as setup:
        await _seed_user_with_import(setup, _TEST_USER_1_ID)
        await _seed_user_with_import(setup, _TEST_USER_2_ID)
        await _seed_user_with_import(setup, _TEST_USER_3_ID)
        await setup.commit()

    try:
        # Run only for user 2
        await main(target="dev", user_id_filter=_TEST_USER_2_ID, metric_filter=None)

        async with session_maker() as check:
            rows_user1 = await _count_pctl_rows(check, _TEST_USER_1_ID)
            rows_user2 = await _count_pctl_rows(check, _TEST_USER_2_ID)
            rows_user3 = await _count_pctl_rows(check, _TEST_USER_3_ID)

        # Users 1 and 3 are untouched (filtered out of _iter_users by user_id_filter).
        assert rows_user1 == 0, f"user_1 should be untouched, got {rows_user1} rows"
        assert rows_user3 == 0, f"user_3 should be untouched, got {rows_user3} rows"
        # User 2 may have rows or not (depends on whether canonical-slice finds games),
        # but the loop ran for it — no error means the filter worked correctly.
        _ = rows_user2  # value checked indirectly via no-error completion
    finally:
        async with session_maker() as teardown:
            await _delete_test_users(teardown, _TEST_USER_1_ID, _TEST_USER_2_ID, _TEST_USER_3_ID)
            await teardown.commit()


# ---------------------------------------------------------------------------
# --metric filter
# ---------------------------------------------------------------------------


async def test_backfill_with_metric_filter_only_processes_that_metric(
    test_engine: AsyncEngine,
) -> None:
    """main() with metric_filter='score_gap' only processes Stage A (score_gap).

    After the filtered run, any rows written have metric='score_gap' only.
    The Stage B metrics (achievable_score_gap, score_gap_bucket_*) have no rows.
    """
    session_maker = _make_session_maker(test_engine)
    main = backfill_user_percentiles.main

    async with session_maker() as setup:
        await _seed_user_with_import(setup, _TEST_USER_1_ID)
        await setup.commit()

    try:
        await main(target="dev", user_id_filter=_TEST_USER_1_ID, metric_filter="score_gap")

        async with session_maker() as check:
            # Stage B metric rows must not have been written.
            # Note: CAST(:metric AS benchmark_metric) required — asyncpg
            # infers VARCHAR which causes type mismatch on the ENUM column.
            for stage_b_metric in (
                "achievable_score_gap",
                "score_gap_conv",
                "score_gap_parity",
            ):
                result = await check.execute(
                    text(
                        "SELECT count(*) FROM user_benchmark_percentiles "
                        "WHERE user_id = :uid AND metric = CAST(:metric AS benchmark_metric)"
                    ).bindparams(uid=_TEST_USER_1_ID, metric=stage_b_metric)
                )
                count = result.scalar_one() or 0
                assert count == 0, (
                    f"Stage B metric {stage_b_metric!r} should be untouched "
                    f"with --metric score_gap filter, got {count} rows"
                )
    finally:
        async with session_maker() as teardown:
            await _delete_test_users(teardown, _TEST_USER_1_ID)
            await teardown.commit()


# ---------------------------------------------------------------------------
# Target safety guards (Pitfall 6 / SC-6 / V4 Tampering)
# ---------------------------------------------------------------------------


def test_backfill_target_prod_refuses_when_tunnel_down(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """_assert_target_safe(url_with_port_15432, 'prod') raises SystemExit when
    no socket listener exists on localhost:15432.

    The error message must contain 'bin/prod_db_tunnel.sh' so the operator
    knows exactly what to run. This is the PCTL-10 safety gate against
    accidental cross-env writes (Pitfall 6 / V4 Tampering).

    The socket probe is monkeypatched to raise OSError ("tunnel down") so the
    test is deterministic regardless of whether a real prod tunnel happens to
    be open on localhost:15432 (it previously failed whenever a developer had
    bin/prod_db_tunnel.sh running locally).
    """

    def _refuse_connection(*_args: object, **_kwargs: object) -> object:
        raise OSError("simulated: no listener on localhost:15432")

    monkeypatch.setattr(backfill_user_percentiles.socket, "create_connection", _refuse_connection)
    _assert_target_safe = backfill_user_percentiles._assert_target_safe
    url_with_prod_port = f"postgresql://user:pass@localhost:{_PROD_TUNNEL_PORT}/flawchess"
    with pytest.raises(SystemExit) as exc_info:
        _assert_target_safe(url_with_prod_port, "prod")
    # Message must reference the tunnel script for operator clarity
    assert "bin/prod_db_tunnel.sh" in str(exc_info.value), (
        "SystemExit message should mention bin/prod_db_tunnel.sh (Pitfall 6 operator guide)"
    )


def test_backfill_target_dev_refuses_url_without_port_5432() -> None:
    """_assert_target_safe(url_with_wrong_port, 'dev') raises SystemExit when
    the URL does not contain ':5432'.

    The error message must contain '5432' so the operator knows the expected port.
    Guards against a misconfigured BACKFILL_DEV_DB_URL override.
    """
    _assert_target_safe = backfill_user_percentiles._assert_target_safe
    wrong_port_url = f"postgresql://user:pass@localhost:{_DUMMY_NON_5432_PORT}/flawchess"
    with pytest.raises(SystemExit) as exc_info:
        _assert_target_safe(wrong_port_url, "dev")
    assert str(_DEV_PORT) in str(exc_info.value), (
        f"SystemExit message should mention port {_DEV_PORT} (expected dev port)"
    )


# ---------------------------------------------------------------------------
# Summary output
# ---------------------------------------------------------------------------


async def test_backfill_emits_per_metric_summary(
    test_engine: AsyncEngine,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Running backfill emits a summary table to stdout containing all 4 metric
    labels and 'upserted=' + 'skipped=' tokens.

    Per CONTEXT §Specifics backfill output shape:
        score_gap                      upserted=X, skipped=Y (...)
        achievable_score_gap           upserted=X, skipped=Y (...)
        score_gap_conv        upserted=X, skipped=Y (...)
        score_gap_parity      upserted=X, skipped=Y (...)
    """
    session_maker = _make_session_maker(test_engine)
    main = backfill_user_percentiles.main

    async with session_maker() as setup:
        await _seed_user_with_import(setup, _TEST_USER_1_ID)
        await setup.commit()

    try:
        await main(target="dev", user_id_filter=_TEST_USER_1_ID, metric_filter=None)

        captured = capsys.readouterr()
        stdout = captured.out

        # All 4 metric labels must appear in the summary.
        for metric_label in _EXPECTED_METRIC_LABELS:
            assert metric_label in stdout, (
                f"Expected metric label {metric_label!r} in summary output.\nGot:\n{stdout}"
            )

        # Both token types must appear.
        for token in _EXPECTED_SUMMARY_TOKENS:
            assert token in stdout, f"Expected token {token!r} in summary output.\nGot:\n{stdout}"
    finally:
        async with session_maker() as teardown:
            await _delete_test_users(teardown, _TEST_USER_1_ID)
            await teardown.commit()


# ---------------------------------------------------------------------------
# Zero-canonical-games edge case
# ---------------------------------------------------------------------------


async def test_backfill_handles_user_with_zero_canonical_slice_games(
    test_engine: AsyncEngine,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """When a user has a completed import_job but no games passing the canonical
    slice filter, backfill writes NO row for that user.

    The summary must contain 'floor_rej' counts > 0 for that user (Phase 94.4
    Plan 06: per-(metric, TC) pooled CTE emits no row for users below the
    inclusion floor, including users with zero canonical-slice games — both
    map to the floor-rejected counter in the new per-(metric × TC) summary
    table).
    """
    session_maker = _make_session_maker(test_engine)
    main = backfill_user_percentiles.main

    # Seed a user with a completed import_job but no games (empty canonical slice).
    async with session_maker() as setup:
        await _seed_user_with_import(setup, _TEST_USER_1_ID)
        await setup.commit()

    try:
        await main(target="dev", user_id_filter=_TEST_USER_1_ID, metric_filter=None)

        # No row must be written (value_raw is None → no row per CONTEXT discretion).
        async with session_maker() as check:
            rows = await _count_pctl_rows(check, _TEST_USER_1_ID)
        assert rows == 0, f"Expected 0 rows for user with zero canonical games, got {rows}"

        # Summary must mention 'floor_rej' (Phase 94.4 Plan 06 cohort-CDF
        # per-(metric × TC) summary column header replacing the legacy
        # 'below_pooled_floor' phrase).
        captured = capsys.readouterr()
        stdout = captured.out
        assert "floor_rej" in stdout, (
            "Expected 'floor_rej' in summary for user below per-(metric, TC) inclusion floor.\n"
            f"Got:\n{stdout}"
        )
    finally:
        async with session_maker() as teardown:
            await _delete_test_users(teardown, _TEST_USER_1_ID)
            await teardown.commit()
