"""
app/database.py
───────────────
Async SQLAlchemy 2.0 engine and session factory.

Design decisions:
- create_async_engine with asyncpg for non-blocking PostgreSQL I/O.
- pool_pre_ping=True: heartbeat on checkout — catches stale connections.
- expire_on_commit=False: avoids lazy-load AttributeErrors inside async
  contexts after a session.commit().
- get_db(): FastAPI dependency that auto-commits on success, rolls back
  on exception, and always closes the session.
- Pool args (pool_size / max_overflow) are only passed for PostgreSQL;
  SQLite (used in tests) uses StaticPool and does not accept them.
"""
from collections.abc import AsyncGenerator

from sqlalchemy import event
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import StaticPool

from app.config import settings


def _make_engine():
    url = settings.database_url
    if url.startswith("sqlite"):
        # In-memory SQLite for testing — StaticPool keeps the same connection
        return create_async_engine(
            url,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
            echo=False,
        )
    # PostgreSQL (production / Docker)
    return create_async_engine(
        url,
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,
        echo=False,
    )


engine = _make_engine()

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


class Base(DeclarativeBase):
    """Shared declarative base for all ORM models."""
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency: yields a session, commits or rolls back."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
