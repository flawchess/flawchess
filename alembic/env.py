import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

from app.core.config import settings
from app.models.base import Base
from app.models.position_bookmark import PositionBookmark  # noqa: F401
from app.models.game import Game  # noqa: F401
from app.models.game_position import GamePosition  # noqa: F401
from app.models.oauth_account import OAuthAccount  # noqa: F401
from app.models.user import User  # noqa: F401
from app.models.opening import Opening  # noqa: F401
from app.models.llm_log import LlmLog  # noqa: F401

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Override sqlalchemy.url with the application settings
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


# Indexes that Alembic autogenerate keeps emitting as "changed" due to upstream
# bugs around postgresql_ops={"col": "DESC"} on functional/composite indexes
# (Alembic #1166 / #1213 / #1285). The ORM declaration matches the DB; autogen
# just can't see through the literal_column("col DESC") representation. Skip
# them so noise diffs stop landing in every fresh autogenerate run.
_AUTOGEN_INDEX_IGNORELIST = {
    "ix_llm_logs_endpoint_created_at",
    "ix_llm_logs_model_created_at",
    "ix_llm_logs_user_id_created_at",
}


def _include_object(object_, name, type_, reflected, compare_to):  # type: ignore[no-untyped-def]
    if type_ == "index" and name in _AUTOGEN_INDEX_IGNORELIST:
        return False
    return True


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        include_object=_include_object,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """In this scenario we need to create an Engine
    and associate a connection with the context.

    """

    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""

    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
