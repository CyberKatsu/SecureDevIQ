"""
tests/test_generation.py
────────────────────────
Unit tests for the generate_challenge() service function.

The active provider's _call() method is patched — we test JSON parsing,
fence stripping, field validation, and error handling, not the Claude/Qwen APIs.
"""
import json
from unittest.mock import patch

import pytest

from app.models import Difficulty, Language, VulnCategory
from app.services.ai_service import (
    AnthropicProvider,
    GeneratedChallenge,
    generate_challenge,
)
from app.prompts.generation import CHALLENGE_GENERATION_SYSTEM_PROMPT


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
        with patch.object(AnthropicProvider, "_call", return_value=json.dumps(VALID_JSON)):
            result = generate_challenge(Language.PYTHON, Difficulty.JUNIOR, VulnCategory.HARDCODED_SECRETS)
        assert isinstance(result, GeneratedChallenge)
        assert result.title == VALID_JSON["title"]
        assert result.vuln_category == VulnCategory.HARDCODED_SECRETS

    def test_strips_markdown_fences(self):
        """Provider sometimes wraps JSON in ```json ... ``` despite instructions."""
        fenced = f"```json\n{json.dumps(VALID_JSON)}\n```"
        with patch.object(AnthropicProvider, "_call", return_value=fenced):
            result = generate_challenge(Language.PYTHON, Difficulty.MID)
        assert result.title == VALID_JSON["title"]

    def test_strips_plain_code_fences(self):
        fenced = f"```\n{json.dumps(VALID_JSON)}\n```"
        with patch.object(AnthropicProvider, "_call", return_value=fenced):
            result = generate_challenge(Language.BASH, Difficulty.JUNIOR)
        assert result.title == VALID_JSON["title"]

    def test_vuln_category_parsed_from_string(self):
        with patch.object(AnthropicProvider, "_call", return_value=json.dumps(VALID_JSON)):
            result = generate_challenge(Language.PYTHON, Difficulty.JUNIOR)
        assert result.vuln_category == VulnCategory.HARDCODED_SECRETS

    def test_language_and_difficulty_in_user_message(self):
        """The user message passed to _call must mention the requested params."""
        with patch.object(AnthropicProvider, "_call", return_value=json.dumps(VALID_JSON)) as mock_call:
            generate_challenge(Language.BASH, Difficulty.SENIOR)
        user_msg = mock_call.call_args[0][1]   # positional arg: user
        assert "bash" in user_msg.lower()
        assert "senior" in user_msg.lower()

    def test_generation_system_prompt_used(self):
        with patch.object(AnthropicProvider, "_call", return_value=json.dumps(VALID_JSON)) as mock_call:
            generate_challenge(Language.SQL, Difficulty.MID)
        system_msg = mock_call.call_args[0][0]  # positional arg: system
        assert system_msg == CHALLENGE_GENERATION_SYSTEM_PROMPT

    def test_category_constraint_appears_in_user_message(self):
        with patch.object(AnthropicProvider, "_call", return_value=json.dumps(VALID_JSON)) as mock_call:
            generate_challenge(Language.PYTHON, Difficulty.JUNIOR, VulnCategory.PROMPT_INJECTION)
        user_msg = mock_call.call_args[0][1]
        assert "prompt_injection" in user_msg

    def test_no_category_gives_ai_free_choice(self):
        with patch.object(AnthropicProvider, "_call", return_value=json.dumps(VALID_JSON)) as mock_call:
            generate_challenge(Language.PYTHON, Difficulty.JUNIOR)
        user_msg = mock_call.call_args[0][1]
        assert "Choose" in user_msg or "interesting" in user_msg


class TestGenerateChallengeErrors:
    def test_invalid_json_raises_value_error(self):
        with patch.object(AnthropicProvider, "_call", return_value="not valid json {{"):
            with pytest.raises(ValueError, match="invalid JSON"):
                generate_challenge(Language.PYTHON, Difficulty.JUNIOR)

    def test_missing_required_field_raises_value_error(self):
        incomplete = {k: v for k, v in VALID_JSON.items() if k != "reference_explanation"}
        with patch.object(AnthropicProvider, "_call", return_value=json.dumps(incomplete)):
            with pytest.raises(ValueError, match="missing fields"):
                generate_challenge(Language.PYTHON, Difficulty.JUNIOR)

    def test_invalid_vuln_category_raises(self):
        bad = {**VALID_JSON, "vuln_category": "not_a_real_category"}
        with patch.object(AnthropicProvider, "_call", return_value=json.dumps(bad)):
            with pytest.raises((ValueError, KeyError)):
                generate_challenge(Language.PYTHON, Difficulty.JUNIOR)

    def test_empty_response_raises_value_error(self):
        with patch.object(AnthropicProvider, "_call", return_value=""):
            with pytest.raises((ValueError, Exception)):
                generate_challenge(Language.PYTHON, Difficulty.JUNIOR)
