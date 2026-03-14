"""
app/services/ai_service.py
──────────────────────────
All Anthropic API calls are routed through this module and ONLY this module.

Two clearly-scoped public functions keep generation and evaluation completely
separate:

  generate_challenge()  → uses CHALLENGE_GENERATION_SYSTEM_PROMPT
  evaluate_submission() → uses CHALLENGE_EVALUATION_SYSTEM_PROMPT

Both functions are synchronous. When called from async FastAPI route handlers,
wrap them with `await asyncio.to_thread(fn, ...)` to avoid blocking the event
loop (see routes/challenges.py and routes/submissions.py for examples).

Both return typed Pydantic models — never raw strings — so all downstream code
can rely on validated, structured data.
"""
import json
import logging
from dataclasses import dataclass

import anthropic

from app.config import get_settings
from app.models import Difficulty, Language, VulnCategory
from app.prompts.evaluation import CHALLENGE_EVALUATION_SYSTEM_PROMPT
from app.prompts.generation import CHALLENGE_GENERATION_SYSTEM_PROMPT
from app.schemas import ScoringResult

logger = logging.getLogger(__name__)

MAX_TOKENS = 2048


def _get_client() -> anthropic.Anthropic:
    """Create a synchronous Anthropic client per-call (thread-safe)."""
    return anthropic.Anthropic(api_key=get_settings().anthropic_api_key)


def _strip_fences(text: str) -> str:
    """
    Strip markdown code fences that Claude occasionally wraps JSON in,
    despite system prompt instructions to the contrary.
    """
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        # Drop first line (```json or ```) and last line (```)
        text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
    return text.strip()


# ── Data class for generation output ─────────────────────────────────────────

@dataclass
class GeneratedChallenge:
    """Typed container for a freshly generated challenge.

    A dataclass rather than Pydantic model because it's internal to the
    service layer; the route converts it to an ORM model before persisting.
    """
    title: str
    description: str
    code_snippet: str
    vuln_category: VulnCategory
    reference_explanation: str


# ── Challenge generation ──────────────────────────────────────────────────────

def generate_challenge(
    language: Language,
    difficulty: Difficulty,
    vuln_category: VulnCategory | None = None,
) -> GeneratedChallenge:
    """
    Call Claude to generate a new vulnerability challenge.

    Args:
        language:      Target language for the code snippet.
        difficulty:    Junior / Mid / Senior — affects subtlety.
        vuln_category: If None, Claude picks the category freely.

    Returns:
        GeneratedChallenge with all fields populated.

    Raises:
        ValueError: If the API response cannot be parsed as valid JSON,
                    or if the JSON is missing required fields.
        anthropic.APIError: On network/API-level failures.
    """
    category_line = (
        f"The vulnerability MUST be of category: **{vuln_category.value}**"
        if vuln_category
        else "Choose the most interesting vulnerability category for this scenario."
    )

    user_message = (
        f"Generate a {difficulty.value}-difficulty security challenge.\n"
        f"Language: {language.value}\n"
        f"{category_line}\n"
        "Respond with JSON only — no markdown fences, no preamble."
    )

    client = _get_client()
    response = client.messages.create(
        model=get_settings().anthropic_model,
        max_tokens=MAX_TOKENS,
        system=CHALLENGE_GENERATION_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
    )

    raw = _strip_fences(response.content[0].text)

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        logger.error("generate_challenge: invalid JSON from Claude: %.500s", raw)
        raise ValueError(f"Claude returned invalid JSON: {exc}") from exc

    required = {"title", "description", "code_snippet", "vuln_category", "reference_explanation"}
    missing = required - data.keys()
    if missing:
        raise ValueError(f"Claude response missing fields: {missing}")

    return GeneratedChallenge(
        title=data["title"],
        description=data["description"],
        code_snippet=data["code_snippet"],
        vuln_category=VulnCategory(data["vuln_category"]),
        reference_explanation=data["reference_explanation"],
    )


# ── Submission evaluation ─────────────────────────────────────────────────────

def evaluate_submission(
    code_snippet: str,
    reference_explanation: str,
    user_answer: str,
) -> ScoringResult:
    """
    Call Claude to evaluate a user's vulnerability analysis.

    The reference_explanation (stored at challenge-generation time) is
    passed as ground truth, making scoring consistent regardless of when
    or by whom the challenge is attempted.

    Args:
        code_snippet:          The challenge code the user was reviewing.
        reference_explanation: The authoritative vulnerability description.
        user_answer:           The trainee's submitted analysis text.

    Returns:
        ScoringResult (Pydantic-validated) with score, findings, explanation.

    Raises:
        ValueError: If Claude's response cannot be parsed or Pydantic rejects it.
    """
    user_message = (
        "## Code snippet under review\n"
        f"```\n{code_snippet}\n```\n\n"
        "## Ground-truth reference explanation\n"
        f"{reference_explanation}\n\n"
        "## Trainee's submitted answer\n"
        f"{user_answer}\n\n"
        "Evaluate the trainee's answer and respond with JSON only."
    )

    client = _get_client()
    response = client.messages.create(
        model=get_settings().anthropic_model,
        max_tokens=MAX_TOKENS,
        system=CHALLENGE_EVALUATION_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
    )

    raw = _strip_fences(response.content[0].text)

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        logger.error("evaluate_submission: invalid JSON from Claude: %.500s", raw)
        raise ValueError(f"Claude returned invalid JSON: {exc}") from exc

    # Pydantic validates score bounds (ge=0, le=10) and required fields
    return ScoringResult(**data)
