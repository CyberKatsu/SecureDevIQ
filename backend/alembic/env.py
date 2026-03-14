"""
alembic/env.py
──────────────
Alembic runtime environment.

Key design decision: DATABASE_URL is read from environment variables
via our Settings class — the same path used by the application itself.
This means a single .env file drives both the app and migrations.

Async-aware: we use AsyncEngine.connect() so Alembic can run migrations
against an asyncpg driver without requiring a synchronous psycopg2 fallback.
"""
import asyncio
import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import create_async_engine

# Import Base and all models so Alembic can detect schema changes
from app.database import Base
from app.models import Challenge, Submission, User  # noqa: F401

config = context.config
fileConfig(config.config_file_name)

target_metadata = Base.metadata


def get_url() -> str:
    """Prefer DATABASE_URL env var over alembic.ini placeholder."""
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL environment variable is not set")
    return url


def run_migrations_offline() -> None:
    """Run migrations without a live DB connection (generates SQL to stdout)."""
    context.configure(
        url=get_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """Run migrations with a live async DB connection."""
    connectable = create_async_engine(get_url(), poolclass=pool.NullPool)
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
