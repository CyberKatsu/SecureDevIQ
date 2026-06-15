"""
app/services/ai_service.py
──────────────────────────
All LLM API calls are routed through this module.

Architecture: provider abstraction
───────────────────────────────────
Anthropic, Qwen, and Openrouter expose the same two operations to the rest of the app:

  generate_challenge()  → GeneratedChallenge
  evaluate_submission() → ScoringResult

The active provider is chosen by the AI_PROVIDER env var and instantiated
once at module import via get_provider(). Switching providers requires only
a one-line environment variable change — no code edits.

Provider implementations
──────────────────────────
  AnthropicProvider  — uses the official `anthropic` SDK (sync client,
                        wrapped with asyncio.to_thread() at the route layer)
  QwenProvider       — uses the `openai` SDK pointed at DashScope's
                        OpenAI-compatible endpoint.
  OpenrouterProvider — uses the `openai` SDK pointed at Openrouter's API.
                        Both Qwen and Openrouter use identical call patterns;
                        only the client construction differs.

All implementations:
  • Use the same system prompt constants from app/prompts/
  • Parse LLM JSON response through _strip_fences() + json.loads()
  • Return typed objects (GeneratedChallenge dataclass, ScoringResult Pydantic)
  • Raise ValueError with a human-readable message on any parse/validation error

Adding a new provider
──────────────────────
1. Subclass BaseAIProvider and implement _call(system, user) -> str
2. Add the provider name to Settings.ai_provider Literal in config.py
3. Implement provider-specific settings in config.py (API key, model, base_url)
4. Add validation check in config.py:validate_provider_key()
5. Register it in get_provider() with logging
"""
import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from functools import lru_cache

import anthropic
from openai import OpenAI

from app.config import get_settings
from app.models import Difficulty, Language, VulnCategory
from app.prompts.evaluation import CHALLENGE_EVALUATION_SYSTEM_PROMPT
from app.prompts.generation import CHALLENGE_GENERATION_SYSTEM_PROMPT
from app.schemas import ScoringResult

logger = logging.getLogger(__name__)

MAX_TOKENS = 2048


# ── Shared output type ────────────────────────────────────────────────────────

@dataclass
class GeneratedChallenge:
    """Typed container for a freshly generated challenge.

    Internal to the service layer — the route converts it to an ORM model.
    """
    title: str
    description: str
    code_snippet: str
    vuln_category: VulnCategory
    reference_explanation: str


# ── Shared utilities ──────────────────────────────────────────────────────────

def _strip_fences(text: str) -> str:
    """Strip markdown code fences that LLMs occasionally wrap JSON in."""
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
    return text.strip()


def _parse_generation(raw: str) -> GeneratedChallenge:
    """Parse and validate a JSON generation response into GeneratedChallenge."""
    clean = _strip_fences(raw)
    try:
        data = json.loads(clean)
    except json.JSONDecodeError as exc:
        logger.error("generate_challenge: invalid JSON: %.500s", clean)
        raise ValueError(f"Provider returned invalid JSON: {exc}") from exc

    required = {"title", "description", "code_snippet", "vuln_category", "reference_explanation"}
    missing = required - data.keys()
    if missing:
        raise ValueError(f"Provider response missing fields: {missing}")

    return GeneratedChallenge(
        title=data["title"],
        description=data["description"],
        code_snippet=data["code_snippet"],
        vuln_category=VulnCategory(data["vuln_category"]),
        reference_explanation=data["reference_explanation"],
    )


def _parse_evaluation(raw: str) -> ScoringResult:
    """Parse and validate a JSON evaluation response into ScoringResult."""
    clean = _strip_fences(raw)
    try:
        data = json.loads(clean)
    except json.JSONDecodeError as exc:
        logger.error("evaluate_submission: invalid JSON: %.500s", clean)
        raise ValueError(f"Provider returned invalid JSON: {exc}") from exc

    # Pydantic validates score bounds (ge=0, le=10) and required fields
    return ScoringResult(**data)


def _build_generation_user_msg(
    language: Language,
    difficulty: Difficulty,
    vuln_category: VulnCategory | None,
) -> str:
    category_line = (
        f"The vulnerability MUST be of category: **{vuln_category.value}**"
        if vuln_category
        else "Choose the most interesting vulnerability category for this scenario."
    )
    return (
        f"Generate a {difficulty.value}-difficulty security challenge.\n"
        f"Language: {language.value}\n"
        f"{category_line}\n"
        "Respond with JSON only — no markdown fences, no preamble."
    )


def _build_evaluation_user_msg(
    code_snippet: str,
    reference_explanation: str,
    user_answer: str,
) -> str:
    return (
        "## Code snippet under review\n"
        f"```\n{code_snippet}\n```\n\n"
        "## Ground-truth reference explanation\n"
        f"{reference_explanation}\n\n"
        "## Trainee's submitted answer\n"
        f"{user_answer}\n\n"
        "Evaluate the trainee's answer and respond with JSON only."
    )


# ── Provider base class ───────────────────────────────────────────────────────

class BaseAIProvider(ABC):
    """Interface that every LLM provider must implement."""

    @abstractmethod
    def _call(self, system: str, user: str) -> str:
        """Make a synchronous chat completion and return the raw text response."""

    def generate_challenge(
        self,
        language: Language,
        difficulty: Difficulty,
        vuln_category: VulnCategory | None = None,
    ) -> GeneratedChallenge:
        """
        Generate a vulnerability challenge snippet.

        Synchronous — wrap with asyncio.to_thread() in async FastAPI routes.

        Args:
            language:      Target programming language.
            difficulty:    Junior / Mid / Senior.
            vuln_category: If None, the provider picks freely.

        Returns:
            GeneratedChallenge dataclass.

        Raises:
            ValueError: JSON parse failure or missing required fields.
            Provider-specific exception: on network/auth errors.
        """
        user_msg = _build_generation_user_msg(language, difficulty, vuln_category)
        raw = self._call(CHALLENGE_GENERATION_SYSTEM_PROMPT, user_msg)
        return _parse_generation(raw)

    def evaluate_submission(
        self,
        code_snippet: str,
        reference_explanation: str,
        user_answer: str,
    ) -> ScoringResult:
        """
        Evaluate a trainee's vulnerability analysis against the ground truth.

        Synchronous — wrap with asyncio.to_thread() in async FastAPI routes.

        Args:
            code_snippet:          The challenge code the trainee reviewed.
            reference_explanation: Authoritative ground truth from generation.
            user_answer:           The trainee's submitted analysis text.

        Returns:
            ScoringResult (Pydantic-validated): score, findings, explanation.

        Raises:
            ValueError: JSON parse failure or Pydantic validation error.
        """
        user_msg = _build_evaluation_user_msg(
            code_snippet, reference_explanation, user_answer
        )
        raw = self._call(CHALLENGE_EVALUATION_SYSTEM_PROMPT, user_msg)
        return _parse_evaluation(raw)


# ── Anthropic provider ────────────────────────────────────────────────────────

class AnthropicProvider(BaseAIProvider):
    """
    LLM provider backed by the Anthropic API.

    Uses the official `anthropic` Python SDK with a synchronous client.
    A new client is created per-call to be thread-safe when called via
    asyncio.to_thread() under concurrent load.
    """

    def _call(self, system: str, user: str) -> str:
        s = get_settings()
        client = anthropic.Anthropic(api_key=s.anthropic_api_key)
        response = client.messages.create(
            model=s.anthropic_model,
            max_tokens=MAX_TOKENS,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        return response.content[0].text


# ── Qwen provider ─────────────────────────────────────────────────────────────

class QwenProvider(BaseAIProvider):
    """
    LLM provider backed by Alibaba Cloud's DashScope Qwen models.

    DashScope exposes an OpenAI-compatible /chat/completions endpoint,
    so we use the `openai` SDK with a custom base_url and API key.

    Regional endpoints:
      International (Singapore/US): https://dashscope-intl.aliyuncs.com/compatible-mode/v1
      China (Beijing):              https://dashscope.aliyuncs.com/compatible-mode/v1

    The active base_url is configured via QWEN_BASE_URL in .env.

    Qwen's chat/completions response structure differs from Anthropic's:
      response.choices[0].message.content  (OpenAI-compatible)
    vs.
      response.content[0].text             (Anthropic native)

    This difference is encapsulated here — the rest of the app is unaware of it.
    """

    def _call(self, system: str, user: str) -> str:
        s = get_settings()
        client = OpenAI(
            api_key=s.dashscope_api_key,
            base_url=s.qwen_base_url,
        )
        response = client.chat.completions.create(
            model=s.qwen_model,
            max_tokens=MAX_TOKENS,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        return response.choices[0].message.content or ""


# ── Openrouter provider ───────────────────────────────────────────────────────

class OpenrouterProvider(BaseAIProvider):
    """
    LLM provider backed by Openrouter (https://openrouter.ai/).

    Openrouter is a unified API gateway that supports 100+ models including:
      • OpenAI (GPT-4, GPT-3.5)
      • Anthropic (Claude)
      • Meta (Llama)
      • Mistral
      • And many more

    Openrouter exposes an OpenAI-compatible /api/v1/chat/completions endpoint,
    so we use the `openai` SDK with a custom base_url and API key.

    The active base_url is configured via OPENROUTER_BASE_URL in .env.
    """

    def _call(self, system: str, user: str) -> str:
        s = get_settings()
        client = OpenAI(
            api_key=s.openrouter_api_key,
            base_url=s.openrouter_base_url,
        )
        response = client.chat.completions.create(
            model=s.openrouter_model,
            max_tokens=MAX_TOKENS,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        return response.choices[0].message.content or ""


# ── Provider factory ──────────────────────────────────────────────────────────

@lru_cache(maxsize=1)
def get_provider() -> BaseAIProvider:
    """
    Return the singleton provider instance for the configured AI_PROVIDER.

    Cached so the provider is instantiated only once per process lifetime.
    Tests clear this cache (via get_provider.cache_clear()) when monkeypatching
    settings.

    Raises:
        ValueError: If AI_PROVIDER is set to an unrecognised value.
    """
    provider_name = get_settings().ai_provider
    if provider_name == "anthropic":
        logger.info("AI provider: Anthropic (%s)", get_settings().anthropic_model)
        return AnthropicProvider()
    if provider_name == "qwen":
        logger.info("AI provider: Qwen (%s via DashScope)", get_settings().qwen_model)
        return QwenProvider()
    if provider_name == "openrouter":
        logger.info("AI provider: Openrouter (%s)", get_settings().openrouter_model)
        return OpenrouterProvider()
    raise ValueError(
        f"Unknown AI_PROVIDER '{provider_name}'. "
        "Valid values: 'anthropic', 'qwen', 'openrouter'."
    )


# ── Public API (used by route handlers) ───────────────────────────────────────
# These module-level functions delegate to the active provider, keeping the
# call sites in routes/challenges.py and routes/submissions.py unchanged.

def generate_challenge(
    language: Language,
    difficulty: Difficulty,
    vuln_category: VulnCategory | None = None,
) -> GeneratedChallenge:
    """Delegate to the active provider's generate_challenge()."""
    return get_provider().generate_challenge(language, difficulty, vuln_category)


def evaluate_submission(
    code_snippet: str,
    reference_explanation: str,
    user_answer: str,
) -> ScoringResult:
    """Delegate to the active provider's evaluate_submission()."""
    return get_provider().evaluate_submission(
        code_snippet, reference_explanation, user_answer
    )
