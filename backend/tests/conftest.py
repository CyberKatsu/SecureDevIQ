"""
tests/conftest.py
─────────────────
Shared pytest fixtures.

Design decisions:
- aiosqlite (in-memory SQLite) replaces PostgreSQL so CI needs no external
  service. We override DATABASE_URL and recreate the engine per test session.
- AI clients are mocked at the service layer (_call method), not at the HTTP
  level, so we test our JSON parsing and validation against controlled output.
- Both AnthropicProvider and QwenProvider expose the same _call() interface,
  so a single mock pattern covers both.
- httpx.AsyncClient with app=app gives us a real ASGI transport without
  spinning up a socket — fast, isolated integration tests.
"""
import asyncio
import json
import os
import uuid
from typing import AsyncGenerator
from unittest.mock import MagicMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# ── Override env vars before any app module is imported ───────────────────────
os.environ.update({
    "DATABASE_URL": "sqlite+aiosqlite:///:memory:",
    "ANTHROPIC_API_KEY": "sk-ant-test-000",
    "DASHSCOPE_API_KEY": "sk-test-qwen-000",
    "AI_PROVIDER": "anthropic",           # tests default to Anthropic
    "SECRET_KEY": "test-secret-key-32-chars-padxxxxx",
})

# Force settings and provider cache to reload with the test environment
from app.config import get_settings       # noqa: E402
from app.services.ai_service import get_provider  # noqa: E402
get_settings.cache_clear()
get_provider.cache_clear()

from app.database import Base, get_db     # noqa: E402
from app.main import app                  # noqa: E402


# ── In-memory SQLite engine ───────────────────────────────────────────────────

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop():
    """Single event loop for the whole test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def test_engine():
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Session that rolls back after each test — no data leaks between tests."""
    async_session = async_sessionmaker(test_engine, expire_on_commit=False)
    async with async_session() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """HTTP test client with the DB dependency overridden to the test session."""
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac
    app.dependency_overrides.clear()


# ── Mock response fixtures ─────────────────────────────────────────────────────

MOCK_GENERATION_JSON = {
    "title": "SQL Injection via Unsanitised User Input",
    "description": (
        "A Flask endpoint that queries a SQLite database using raw string "
        "formatting. The endpoint accepts a username parameter and builds "
        "the SQL query by directly interpolating user input."
    ),
    "code_snippet": (
        "from flask import Flask, request\n"
        "import sqlite3\n\n"
        "app = Flask(__name__)\n\n"
        "@app.route('/user')\n"
        "def get_user():\n"
        "    username = request.args.get('username', '')\n"
        "    conn = sqlite3.connect('users.db')\n"
        "    query = f\"SELECT * FROM users WHERE username = '{username}'\"\n"
        "    result = conn.execute(query).fetchall()\n"
        "    return str(result)\n"
    ),
    "vuln_category": "missing_sanitisation",
    "reference_explanation": (
        "The `query` variable interpolates `username` directly into the SQL "
        "string using an f-string. An attacker can pass `' OR '1'='1` to bypass "
        "authentication. Fix: use parameterised queries: "
        "`conn.execute('SELECT * FROM users WHERE username = ?', (username,))`."
    ),
}

MOCK_EVALUATION_JSON = {
    "score": 8.5,
    "correct_findings": [
        "Correctly identified SQL injection via f-string interpolation",
        "Correctly identified that the username parameter is user-controlled",
    ],
    "missed_findings": [
        "Did not mention a specific exploit payload",
        "Did not suggest parameterised queries as the fix",
    ],
    "explanation": (
        "Good identification of the core vulnerability and its location. "
        "Lost points for not specifying the exploit payload or remediation."
    ),
    "fix_suggestion": (
        "Replace the f-string with a parameterised query: "
        "`conn.execute('SELECT * FROM users WHERE username = ?', (username,))`"
    ),
}


@pytest.fixture
def mock_anthropic_generate():
    """Patch AnthropicProvider._call to return a generation JSON string."""
    with patch(
        "app.services.ai_service.AnthropicProvider._call",
        return_value=json.dumps(MOCK_GENERATION_JSON),
    ):
        yield


@pytest.fixture
def mock_anthropic_evaluate():
    """Patch AnthropicProvider._call to return an evaluation JSON string."""
    with patch(
        "app.services.ai_service.AnthropicProvider._call",
        return_value=json.dumps(MOCK_EVALUATION_JSON),
    ):
        yield


@pytest.fixture
def mock_qwen_generate():
    """Patch QwenProvider._call to return a generation JSON string."""
    with patch(
        "app.services.ai_service.QwenProvider._call",
        return_value=json.dumps(MOCK_GENERATION_JSON),
    ):
        yield


@pytest.fixture
def mock_qwen_evaluate():
    """Patch QwenProvider._call to return an evaluation JSON string."""
    with patch(
        "app.services.ai_service.QwenProvider._call",
        return_value=json.dumps(MOCK_EVALUATION_JSON),
    ):
        yield
