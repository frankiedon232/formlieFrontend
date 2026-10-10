"""Alembic environment: async (asyncpg), as formalie_owner. `-x db=test` targets DB_TEST_DATABASE instead."""

from __future__ import annotations

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import get_settings
from app.core.db.base import Base
from app.core.db.engines import async_url
from app.models import import_all_models

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name, disable_existing_loggers=False)

import_all_models()
target_metadata = Base.metadata


def _url() -> str:
    settings = get_settings()
    if settings.db_owner_url is None:
        raise SystemExit("DB_OWNER_URL is not set (see .env.example)")
    url = make_url(async_url(settings.db_owner_url.get_secret_value()))
    if context.get_x_argument(as_dictionary=True).get("db") == "test":
        url = url.set(database=settings.db_test_database)
    return url.render_as_string(hide_password=False)


def _include_object(obj, name, type_, reflected, compare_to):  # noqa: ANN001, ANN202
    # Monthly partitions are made by platform.ensure_monthly_partitions, not by models.
    return not (type_ == "table" and reflected and compare_to is None and "_p20" in (name or ""))


def _configure(connection) -> None:  # noqa: ANN001
    # alembic_version lives in the app schema too, so the schema must exist before Alembic reads it.
    connection.exec_driver_sql(f"CREATE SCHEMA IF NOT EXISTS {get_settings().db_schema}")
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        include_schemas=True,
        version_table_schema=get_settings().db_schema,
        include_object=_include_object,
        compare_type=True,
        transaction_per_migration=True,
    )


def run_offline() -> None:
    context.configure(url=_url(), target_metadata=target_metadata, literal_binds=True, include_schemas=True,
                      version_table_schema=get_settings().db_schema)
    with context.begin_transaction():
        context.run_migrations()


async def run_online() -> None:
    engine = create_async_engine(_url())
    async with engine.connect() as connection:
        await connection.run_sync(_configure)
        await connection.run_sync(lambda _: context.run_migrations())
        await connection.commit()
    await engine.dispose()


if context.is_offline_mode():
    run_offline()
else:
    asyncio.run(run_online())
