"""Regenerate the WRITE-03 write-path golden-snapshot fixtures (Phase 150 Plan 01).

Captures the CORRECT current (post-Phase-149, post-FLAWCHESS-8D-fix) `game_flaws`
output of the production submit/classify path — `app.routers.eval_remote._apply_atomic_submit`
— for 7 named scenarios (CONTEXT.md D-02), and writes one committed JSON fixture per
scenario to `tests/fixtures/write_path_golden/`. Plan 04 later swaps
`_classify_and_fill_oracle`'s delete-then-insert for a diff/upsert; the drift-check
equivalence test (`tests/services/test_flaw_upsert_equivalence.py`) re-runs the SAME
scenario setups (imported from `tests/services/write_path_golden_scenarios.py` — shared
with this script, so generator and test can never diverge) and asserts the new write
path reproduces these goldens byte-for-byte.

Regeneration one-liner (only if you intentionally change classify/gate/gate-margin
logic and have reviewed the diff)::

    uv run python -m scripts.gen_write_path_golden

Sequencing note (RESEARCH.md "Sequencing implication"): these goldens MUST be generated
BEFORE `_classify_and_fill_oracle`'s delete-then-insert is touched — the whole point of
D-01 is that the golden captures *current, correct* behavior. Re-running this script
after the diff/upsert lands and re-committing a changed fixture would make the
equivalence proof circular; if that ever happens, it must be a deliberate, reviewed
decision (documented in the relevant plan's SUMMARY), not a routine "fix the failing
test" reflex.

DB isolation (per CLAUDE.md "no dev DB reset in plans" + the plan's explicit
prohibition): this script NEVER touches `bin/reset_db.sh` or a production connection.
It spins up its own ephemeral per-run database cloned from the same migrated
`flawchess_test_template` that `tests/conftest.py` uses for every pytest run (same
template-clone-drop machinery, reused directly — not duplicated), runs all 7 scenarios
against it, writes the fixtures, then drops the ephemeral database.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import urllib.parse
from pathlib import Path
from typing import Any, Final

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Bootstrap project root so `app.*` / `tests.*` imports resolve when running as a script.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.config import settings  # noqa: E402
from tests.conftest import (  # noqa: E402
    _create_run_db,
    _drop_run_db,
    _ensure_template_fresh,
    _maint_dsn,
)
from tests.services.write_path_golden_scenarios import (  # noqa: E402
    SCENARIO_NAMES,
    run_scenario,
)

OUTPUT_DIR: Final[Path] = Path("tests/fixtures/write_path_golden")

# Safety-guard token (mirrors scripts/gen_global_percentile_cdf.py's
# _assert_benchmark_db pattern) -- refuses to run against anything that doesn't look
# like the isolated test DB.
_TEST_DB_NAME_TOKEN: Final[str] = "flawchess_test"

# Dedicated user for the golden generator's ephemeral DB (FK target for Game rows).
_GEN_USER_ID: Final[int] = 999_999


def _log(msg: str) -> None:
    print(f"[gen_write_path_golden] {msg}")


def _assert_test_db(url: str) -> None:
    """Refuse to run unless `url` points at a database named like the isolated test DB."""
    if _TEST_DB_NAME_TOKEN not in url:
        raise SystemExit(
            f"Refusing to run: resolved DB URL does not contain {_TEST_DB_NAME_TOKEN!r}. "
            f"This script only operates against an ephemeral clone of the isolated test "
            f"DB (DATABASE_URL_TEST) -- never bin/reset_db.sh, never production."
        )


async def _ensure_gen_user(session_maker: async_sessionmaker[AsyncSession]) -> int:
    """Ensure the golden generator's dedicated test user exists. Returns user_id."""
    from app.models.user import User

    async with session_maker() as session:
        result = await session.execute(select(User).where(User.id == _GEN_USER_ID))
        if result.unique().scalar_one_or_none() is None:
            session.add(
                User(
                    id=_GEN_USER_ID,
                    email=f"gen-write-path-golden-{_GEN_USER_ID}@example.com",
                    hashed_password="fakehash",
                    is_active=True,
                    is_superuser=False,
                    is_verified=True,
                )
            )
            await session.commit()
    return _GEN_USER_ID


def _write_golden(scenario_name: str, dump: dict[str, dict[str, Any]]) -> None:
    """Write one scenario's dump as a committed JSON fixture (ply-ascending insertion
    order preserved -- NOT sort_keys, since string-sorting ply keys would misorder "10"
    before "2"; the dump dict is already ORDER BY ply from the DB)."""
    path = OUTPUT_DIR / f"{scenario_name}.json"
    path.write_text(json.dumps(dump, indent=2) + "\n")
    _log(f"Wrote {path}")


async def regenerate() -> dict[str, dict[str, dict[str, Any]]]:
    """Spin up an ephemeral per-run DB, run all 7 scenarios, write the fixtures.

    Returns the full {scenario_name: dump} map for testing/inspection.
    """
    _assert_test_db(settings.DATABASE_URL_TEST)

    maint = _maint_dsn(settings.DATABASE_URL_TEST)
    _log("Ensuring flawchess_test_template is at Alembic head...")
    await _ensure_template_fresh(maint)

    run_db_name = f"flawchess_test_gengolden_{os.getpid()}"
    _log(f"Cloning ephemeral run DB {run_db_name!r} from the template...")
    await _create_run_db(maint, run_db_name)

    p = urllib.parse.urlparse(settings.DATABASE_URL_TEST)
    run_db_url = (
        f"postgresql+asyncpg://{p.username}:{p.password}@{p.hostname}:{p.port}/{run_db_name}"
    )

    engine = create_async_engine(run_db_url, echo=False)
    results: dict[str, dict[str, dict[str, Any]]] = {}
    try:
        session_maker = async_sessionmaker(engine, expire_on_commit=False)
        user_id = await _ensure_gen_user(session_maker)

        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        for scenario_name in SCENARIO_NAMES:
            _log(f"Running {scenario_name}...")
            dump = await run_scenario(scenario_name, session_maker, user_id)
            results[scenario_name] = dump
            _write_golden(scenario_name, dump)
    finally:
        # Async dispose (not sync_engine.dispose()) -- this script runs entirely
        # inside one asyncio.run() loop, so pooled asyncpg connections must be
        # closed while that loop is still alive. Closing them via the sync path
        # defers actual connection teardown to GC finalizers that fire after the
        # loop closes, which raises a benign-but-noisy MissingGreenlet warning.
        await engine.dispose()
        _log(f"Dropping ephemeral run DB {run_db_name!r}...")
        await _drop_run_db(maint, run_db_name)

    return results


async def main() -> None:
    await regenerate()
    _log("Done.")


if __name__ == "__main__":
    asyncio.run(main())
