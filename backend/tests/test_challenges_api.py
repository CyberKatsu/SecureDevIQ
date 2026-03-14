"""
tests/test_challenges_api.py
────────────────────────────
Integration tests for the /api/challenges routes.

Uses httpx.AsyncClient with an in-memory SQLite DB and a mocked Anthropic
client, so no external services are required.

Auth is also tested: unauthenticated requests to protected routes must
return 401.
"""
import json
import uuid
from unittest.mock import MagicMock, patch

import pytest

from tests.conftest import MOCK_GENERATION_JSON


# ── Helpers ───────────────────────────────────────────────────────────────────

async def register_and_login(client) -> str:
    """Register a user and return a bearer token."""
    await client.post("/api/auth/register", json={
        "username": "testuser",
        "email": "test@example.com",
        "password": "securepass123",
    })
    resp = await client.post(
        "/api/auth/token",
        data={"username": "testuser", "password": "securepass123"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    return resp.json()["access_token"]


def auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ── Tests ─────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
class TestChallengesUnauthenticated:
    async def test_list_challenges_requires_auth(self, client):
        resp = await client.get("/api/challenges")
        assert resp.status_code == 401

    async def test_generate_challenge_requires_auth(self, client):
        resp = await client.post("/api/challenges/generate", json={
            "language": "python",
            "difficulty": "junior",
        })
        assert resp.status_code == 401


@pytest.mark.asyncio
class TestChallengeGeneration:
    async def test_generate_returns_201_with_valid_payload(self, client, mock_anthropic_generate):
        token = await register_and_login(client)
        resp = await client.post(
            "/api/challenges/generate",
            json={"language": "python", "difficulty": "junior", "vuln_category": "missing_sanitisation"},
            headers=auth_headers(token),
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["title"] == MOCK_GENERATION_JSON["title"]
        assert data["language"] == "python"
        assert data["difficulty"] == "junior"
        assert "id" in data
        assert "code_snippet" in data
        # reference_explanation is NOT returned (security: don't leak ground truth)
        assert "reference_explanation" not in data

    async def test_generate_persists_challenge(self, client, mock_anthropic_generate):
        token = await register_and_login(client)
        create_resp = await client.post(
            "/api/challenges/generate",
            json={"language": "sql", "difficulty": "mid"},
            headers=auth_headers(token),
        )
        challenge_id = create_resp.json()["id"]

        get_resp = await client.get(
            f"/api/challenges/{challenge_id}",
            headers=auth_headers(token),
        )
        assert get_resp.status_code == 200
        assert get_resp.json()["id"] == challenge_id

    async def test_generate_invalid_language_returns_422(self, client, mock_anthropic_generate):
        token = await register_and_login(client)
        resp = await client.post(
            "/api/challenges/generate",
            json={"language": "cobol", "difficulty": "junior"},
            headers=auth_headers(token),
        )
        assert resp.status_code == 422

    async def test_generate_invalid_difficulty_returns_422(self, client, mock_anthropic_generate):
        token = await register_and_login(client)
        resp = await client.post(
            "/api/challenges/generate",
            json={"language": "python", "difficulty": "expert"},
            headers=auth_headers(token),
        )
        assert resp.status_code == 422


@pytest.mark.asyncio
class TestChallengeRetrieval:
    async def test_get_nonexistent_challenge_returns_404(self, client):
        token = await register_and_login(client)
        resp = await client.get(
            f"/api/challenges/{uuid.uuid4()}",
            headers=auth_headers(token),
        )
        assert resp.status_code == 404

    async def test_list_challenges_returns_paginated_results(self, client, mock_anthropic_generate):
        token = await register_and_login(client)
        # Generate two challenges
        for lang in ("python", "sql"):
            await client.post(
                "/api/challenges/generate",
                json={"language": lang, "difficulty": "junior"},
                headers=auth_headers(token),
            )

        resp = await client.get("/api/challenges", headers=auth_headers(token))
        assert resp.status_code == 200
        data = resp.json()
        assert "challenges" in data
        assert "total" in data
        assert data["total"] >= 2

    async def test_list_challenges_filter_by_language(self, client, mock_anthropic_generate):
        token = await register_and_login(client)
        await client.post(
            "/api/challenges/generate",
            json={"language": "bash", "difficulty": "senior"},
            headers=auth_headers(token),
        )
        resp = await client.get(
            "/api/challenges?language=bash",
            headers=auth_headers(token),
        )
        assert resp.status_code == 200
        challenges = resp.json()["challenges"]
        assert all(c["language"] == "bash" for c in challenges)
