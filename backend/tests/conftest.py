"""
tests/conftest.py
─────────────────
Shared pytest fixtures.

Design decisions:
- aiosqlite (in-memory SQLite) replaces PostgreSQL so CI needs no external
  service. We override DATABASE_URL and recreate the engine per test session.
- AnthropicClient is mocked at the service layer, not at the HTTP level,
  so we test our parsing and validation logic against controlled JSON.
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

# Override DATABASE_URL before app modules load it
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("ANTHROPIC_API_KEY", "sk-ant-test-000")
os.environ.setdefault("SECRET_KEY", "test-secret-key-not-for-production")

from app.database import Base, get_db  # noqa: E402 — must come after env override
from app.main import app  # noqa: E402


# ── In-memory SQLite engine for tests ────────────────────────────────────────

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

@pytest.fixture(scope="session")
def event_loop():
    """Use a single event loop for the whole test session."""
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
    """Yield a session that rolls back after each test (no data leaks)."""
    async_session = async_sessionmaker(test_engine, expire_on_commit=False)
    async with async_session() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """HTTP test client with the DB session overridden to the test session."""
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac
    app.dependency_overrides.clear()


# ── Mock Anthropic responses ──────────────────────────────────────────────────

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
        "The `query` variable on line 10 interpolates `username` directly "
        "into the SQL string using an f-string. An attacker can pass "
        "`' OR '1'='1` to bypass authentication, or `'; DROP TABLE users;--` "
        "to destroy data. The fix is to use parameterised queries: "
        "`conn.execute('SELECT * FROM users WHERE username = ?', (username,))`."
    ),
}

MOCK_EVALUATION_JSON = {
    "score": 8.5,
    "correct_findings": [
        "Correctly identified SQL injection via f-string interpolation on line 10",
        "Correctly identified that the username parameter is user-controlled",
    ],
    "missed_findings": [
        "Did not mention the specific exploit payload (' OR '1'='1)",
        "Did not suggest parameterised queries as the concrete fix",
    ],
    "explanation": (
        "The trainee correctly identified the core vulnerability (SQL injection "
        "via unsanitised string interpolation) and its location. The answer "
        "loses points for not specifying an exploit payload or the concrete "
        "remediation pattern."
    ),
    "fix_suggestion": (
        "Replace the f-string with a parameterised query: "
        "`conn.execute('SELECT * FROM users WHERE username = ?', (username,))`"
    ),
}


def make_mock_anthropic(response_json: dict) -> MagicMock:
    """Return a mock Anthropic client whose messages.create() returns given JSON."""
    mock_content = MagicMock()
    mock_content.text = json.dumps(response_json)
    mock_response = MagicMock()
    mock_response.content = [mock_content]
    mock_client = MagicMock()
    mock_client.messages.create.return_value = mock_response
    return mock_client


@pytest.fixture
def mock_anthropic_generate():
    with patch("app.services.ai_service._get_client") as mock:
        mock.return_value = make_mock_anthropic(MOCK_GENERATION_JSON)
        yield mock


@pytest.fixture
def mock_anthropic_evaluate():
    with patch("app.services.ai_service._get_client") as mock:
        mock.return_value = make_mock_anthropic(MOCK_EVALUATION_JSON)
        yield mock
