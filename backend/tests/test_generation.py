"""
tests/test_generation.py
────────────────────────
Unit tests for the AI generation service (generate_challenge).

The Anthropic client is mocked — we test our JSON parsing, validation,
and error-handling logic, not the Claude API itself.
"""
import json
from unittest.mock import MagicMock, patch

import pytest

from app.models import Difficulty, Language, VulnCategory
from app.services.ai_service import GeneratedChallenge, generate_challenge


def make_client(response_text: str) -> MagicMock:
    content = MagicMock()
    content.text = response_text
    response = MagicMock()
    response.content = [content]
    client = MagicMock()
    client.messages.create.return_value = response
    return client


VALID_JSON = {
    "title": "Hardcoded AWS Key",
    "description": "A Lambda function with a hardcoded AWS secret access key.",
    "code_snippet": "AWS_SECRET = 'wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY'",
    "vuln_category": "hardcoded_secrets",
    "reference_explanation": (
        "The AWS secret access key is hardcoded on line 1. "
        "An attacker with access to source control can extract "
        "and use these credentials to access AWS resources."
    ),
}


class TestGenerateChallengeSuccess:
    def test_returns_generated_challenge_dataclass(self):
        with patch("app.services.ai_service._get_client") as mock_get:
            mock_get.return_value = make_client(json.dumps(VALID_JSON))
            result = generate_challenge(Language.PYTHON, Difficulty.JUNIOR, VulnCategory.HARDCODED_SECRETS)

        assert isinstance(result, GeneratedChallenge)
        assert result.title == VALID_JSON["title"]
        assert result.vuln_category == VulnCategory.HARDCODED_SECRETS
        assert len(result.reference_explanation) > 0

    def test_strips_markdown_fences(self):
        """Claude sometimes wraps JSON in ```json ... ``` despite instructions."""
        fenced = f"```json\n{json.dumps(VALID_JSON)}\n```"
        with patch("app.services.ai_service._get_client") as mock_get:
            mock_get.return_value = make_client(fenced)
            result = generate_challenge(Language.PYTHON, Difficulty.MID)

        assert result.title == VALID_JSON["title"]

    def test_vuln_category_parsed_from_string(self):
        """Ensure the string from JSON is converted to a VulnCategory enum."""
        with patch("app.services.ai_service._get_client") as mock_get:
            mock_get.return_value = make_client(json.dumps(VALID_JSON))
            result = generate_challenge(Language.PYTHON, Difficulty.JUNIOR)

        assert result.vuln_category == VulnCategory.HARDCODED_SECRETS

    def test_correct_system_prompt_is_passed(self):
        """Confirm the generation prompt (not the evaluation prompt) is used."""
        from app.prompts.generation import CHALLENGE_GENERATION_SYSTEM_PROMPT

        with patch("app.services.ai_service._get_client") as mock_get:
            mock_client = make_client(json.dumps(VALID_JSON))
            mock_get.return_value = mock_client
            generate_challenge(Language.SQL, Difficulty.SENIOR)

        call_kwargs = mock_client.messages.create.call_args.kwargs
        assert call_kwargs["system"] == CHALLENGE_GENERATION_SYSTEM_PROMPT

    def test_language_and_difficulty_appear_in_user_message(self):
        with patch("app.services.ai_service._get_client") as mock_get:
            mock_client = make_client(json.dumps(VALID_JSON))
            mock_get.return_value = mock_client
            generate_challenge(Language.BASH, Difficulty.SENIOR)

        messages = mock_client.messages.create.call_args.kwargs["messages"]
        user_content = messages[0]["content"]
        assert "bash" in user_content.lower()
        assert "senior" in user_content.lower()


class TestGenerateChallengeErrors:
    def test_invalid_json_raises_value_error(self):
        with patch("app.services.ai_service._get_client") as mock_get:
            mock_get.return_value = make_client("not valid json at all {{")
            with pytest.raises(ValueError, match="invalid JSON"):
                generate_challenge(Language.PYTHON, Difficulty.JUNIOR)

    def test_missing_required_field_raises_value_error(self):
        incomplete = {k: v for k, v in VALID_JSON.items() if k != "reference_explanation"}
        with patch("app.services.ai_service._get_client") as mock_get:
            mock_get.return_value = make_client(json.dumps(incomplete))
            with pytest.raises(ValueError, match="missing fields"):
                generate_challenge(Language.PYTHON, Difficulty.JUNIOR)

    def test_invalid_vuln_category_raises_value_error(self):
        bad = {**VALID_JSON, "vuln_category": "not_a_real_category"}
        with patch("app.services.ai_service._get_client") as mock_get:
            mock_get.return_value = make_client(json.dumps(bad))
            with pytest.raises((ValueError, KeyError)):
                generate_challenge(Language.PYTHON, Difficulty.JUNIOR)
