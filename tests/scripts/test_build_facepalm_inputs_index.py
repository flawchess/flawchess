"""Tests for scripts/build_facepalm_inputs_index.py (Phase 259 D-17, Pitfall 5).

The migration, the ORM declaration and the operator script must describe the same index:
IF NOT EXISTS checks the name only, so a drifted definition would be accepted silently on prod.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine

from app.models.base import Base
from scripts.build_facepalm_inputs_index import (
    EXIT_ABSENT,
    EXIT_INVALID,
    EXIT_MISMATCH,
    EXIT_OK,
    EXPECTED_INDEXDEF,
    INDEX_NAME,
    IndexState,
    build_sql,
    check_index,
    classify_index,
)

_MIGRATION_FILE = (
    Path(__file__).resolve().parents[2]
    / "alembic"
    / "versions"
    / "20261124_120000_e2f6a8b0d259_phase_259_ix_game_flaws_facepalm_inputs.py"
)


def _load_migration() -> ModuleType:
    spec = importlib.util.spec_from_file_location("migration_e2f6a8b0d259", _MIGRATION_FILE)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_build_sql_is_concurrent_if_not_exists_over_the_orm_index() -> None:
    sql = build_sql()
    assert sql.startswith(f"CREATE INDEX CONCURRENTLY IF NOT EXISTS {INDEX_NAME} ON game_flaws")
    index = next(i for i in Base.metadata.tables["game_flaws"].indexes if i.name == INDEX_NAME)
    for name in index.dialect_options["postgresql"]["include"]:
        assert name in sql
    assert sql.endswith("WHERE severity = 2")


def test_build_sql_leaves_the_orm_declaration_untouched() -> None:
    """The ORM metadata is process-wide; compiling the CONCURRENTLY text must not stick."""
    build_sql()
    index = next(i for i in Base.metadata.tables["game_flaws"].indexes if i.name == INDEX_NAME)
    assert not index.dialect_options["postgresql"]["concurrently"]


def test_migration_sql_equals_the_compiled_orm_index() -> None:
    migration = _load_migration()
    assert migration.CREATE_SQL == build_sql()
    assert migration.revision == "e2f6a8b0d259"


@pytest.mark.asyncio
async def test_expected_indexdef_matches_the_migrated_test_db(test_engine: AsyncEngine) -> None:
    """The test template is built by the migrations: its index is valid and equals the script's text."""
    async with test_engine.connect() as conn:
        assert await check_index(conn) == EXIT_OK


def test_check_reports_a_mismatch() -> None:
    drifted = EXPECTED_INDEXDEF.replace("maia_best_reply_prob", "maia_best_prob")
    assert classify_index(IndexState(is_valid=True, indexdef=drifted)) == EXIT_MISMATCH


def test_check_reports_invalid_and_absent() -> None:
    assert classify_index(IndexState(is_valid=False, indexdef=EXPECTED_INDEXDEF)) == EXIT_INVALID
    assert classify_index(None) == EXIT_ABSENT
    assert classify_index(IndexState(is_valid=True, indexdef=EXPECTED_INDEXDEF)) == EXIT_OK
