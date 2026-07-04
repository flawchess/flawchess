"""Drift-check equivalence test for the WRITE-03 write-path golden-snapshot harness
(Phase 150 Plan 01).

Parametrized over the 7 named scenarios in ``write_path_golden_scenarios.py``, this
test re-runs the SAME setup through the production submit path
(``app.routers.eval_remote._apply_atomic_submit``) and asserts the resulting
``game_flaws`` state matches the committed golden fixture byte-for-byte (after a JSON
round-trip).

Green against current HEAD is expected — both are the delete-then-insert path, so this
is currently a tautology. This test only becomes a REAL equivalence proof once Plan 04
swaps ``_classify_and_fill_oracle``'s delete-then-insert for a diff/upsert: the SAME
scenarios must still produce byte-identical output, proving no behavior change
(WRITE-03).

Assert ``is None`` explicitly for every blob column the golden expects NULL (never a
truthy or ``==``-falsy check) per 150-RESEARCH.md Pitfall 2 /
``project_asyncpg_jsonb_null_vs_sql_null``: the dangerous implementation this guards
against is a single ``ON CONFLICT DO UPDATE ... COALESCE(EXCLUDED.col, existing.col)``
upsert, where a bound Python ``None`` for "no fresh blob this submit" serializes as a
real, non-NULL JSON ``null`` via asyncpg — so ``COALESCE`` always picks that JSON
``null`` over the existing preserved value, silently wiping it. A plain ``==``
equality check against a non-NULL golden value (e.g. scenario 2's preserved blob)
already fails loudly if that happens (``None != [...]``); the explicit ``is None``
branch below is the belt-and-suspenders assertion the plan's acceptance criteria
requires for the NULL-expected side of that same comparison.

Regenerating goldens (only after an intentional, reviewed classify/write-path change —
review the diff before committing)::

    uv run python -m scripts.gen_write_path_golden
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.user import User
from tests.services.write_path_golden_scenarios import SCENARIO_NAMES, run_scenario

_FIXTURE_DIR: Path = Path(__file__).resolve().parent.parent / "fixtures" / "write_path_golden"

# Blob columns that must be asserted with an explicit `is None` check (never
# truthy/`==`-falsy) when the golden expects NULL -- catches the asyncpg JSONB
# `None` -> `null::jsonb` pitfall (project_asyncpg_jsonb_null_vs_sql_null).
_BLOB_COLUMNS: tuple[str, ...] = ("allowed_pv_lines", "missed_pv_lines")

_TEST_USER_ID: int = 99_400  # unique to this module, avoids FK conflicts with other suites


@pytest_asyncio.fixture(scope="session")
async def write_path_session_maker(test_engine) -> async_sessionmaker[AsyncSession]:
    """async_sessionmaker bound to the per-run test engine."""
    return async_sessionmaker(test_engine, expire_on_commit=False)


@pytest_asyncio.fixture(scope="session")
async def write_path_test_user(
    write_path_session_maker: async_sessionmaker[AsyncSession],
) -> int:
    """Ensure the dedicated test user for this module exists. Returns user_id."""
    async with write_path_session_maker() as session:
        result = await session.execute(select(User).where(User.id == _TEST_USER_ID))
        if result.unique().scalar_one_or_none() is None:
            session.add(
                User(
                    id=_TEST_USER_ID,
                    email=f"write-path-equivalence-{_TEST_USER_ID}@example.com",
                    hashed_password="fakehash",
                    is_active=True,
                    is_superuser=False,
                    is_verified=True,
                )
            )
            await session.commit()
    return _TEST_USER_ID


def _load_golden(scenario_name: str) -> dict[str, dict[str, Any]]:
    path = _FIXTURE_DIR / f"{scenario_name}.json"
    if not path.exists():
        raise FileNotFoundError(
            f"Missing golden fixture {path}. Regenerate via "
            f"`uv run python -m scripts.gen_write_path_golden` (review the diff first)."
        )
    result: dict[str, dict[str, Any]] = json.loads(path.read_text())
    return result


@pytest.mark.asyncio
@pytest.mark.parametrize("scenario_name", SCENARIO_NAMES)
async def test_write_path_matches_golden(
    scenario_name: str,
    write_path_session_maker: async_sessionmaker[AsyncSession],
    write_path_test_user: int,
) -> None:
    """The production submit path reproduces the committed golden byte-for-byte."""
    golden = _load_golden(scenario_name)
    actual = await run_scenario(scenario_name, write_path_session_maker, write_path_test_user)

    # JSON round-trip `actual` through the same encode/decode as the golden so both
    # sides compare with identical Python types.
    actual_round_tripped: dict[str, dict[str, Any]] = json.loads(json.dumps(actual))

    assert set(actual_round_tripped) == set(golden), (
        f"{scenario_name}: flaw-ply set differs. "
        f"actual={sorted(actual_round_tripped)} golden={sorted(golden)}"
    )
    for ply, golden_row in golden.items():
        actual_row = actual_round_tripped[ply]
        for col, golden_val in golden_row.items():
            actual_val = actual_row[col]
            if col in _BLOB_COLUMNS and golden_val is None:
                # Explicit is-None check -- never a truthy/`==`-falsy comparison here
                # (RESEARCH.md Pitfall 2 / project_asyncpg_jsonb_null_vs_sql_null).
                assert actual_val is None, (
                    f"{scenario_name} ply={ply} {col}: expected NULL (Python None), "
                    f"got {actual_val!r} -- possible JSONB null::jsonb regression."
                )
            else:
                assert actual_val == golden_val, (
                    f"{scenario_name} ply={ply} {col}: expected {golden_val!r}, got {actual_val!r}"
                )


def test_fixture_directory_covers_all_named_scenarios() -> None:
    """Every named scenario has exactly one golden fixture file -- catches a future
    9th scenario shipping without a golden (mirrors
    tests/scripts/test_gen_global_percentile_cdf_unchanged.py's completeness guard)."""
    fixture_names = {p.stem for p in _FIXTURE_DIR.glob("*.json")}
    in_scope = set(SCENARIO_NAMES)
    missing = in_scope - fixture_names
    extra = fixture_names - in_scope
    assert not missing, f"Missing golden fixtures for: {sorted(missing)}"
    assert not extra, f"Stale golden fixtures (not in SCENARIO_NAMES): {sorted(extra)}"
