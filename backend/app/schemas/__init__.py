"""
Pydantic v2 schemas for request/response validation.

Kept separate from ORM models (no SQLAlchemy coupling here) so the API
contract is clean and testable independently of the DB layer.
"""
import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator

from app.models import Difficulty, Language, VulnCategory


# ── Challenge schemas ─────────────────────────────────────────────────────────

class ChallengeGenerateRequest(BaseModel):
    language: Language
    difficulty: Difficulty
    vuln_category: Optional[VulnCategory] = None  # None → AI picks freely


class ChallengeResponse(BaseModel):
    id: uuid.UUID
    title: str
    description: str
    code_snippet: str
    language: Language
    difficulty: Difficulty
    vuln_category: VulnCategory
    created_at: datetime

    model_config = {"from_attributes": True}


class ChallengeListResponse(BaseModel):
    challenges: list[ChallengeResponse]
    total: int


# ── Scoring schema ────────────────────────────────────────────────────────────

class ScoringResult(BaseModel):
    """
    The structured output from Claude's evaluation step.
    This is the core artefact of the AI layer — a typed, validated
    representation of what Claude found in the user's answer.
    """
    score: float = Field(
        ...,
        ge=0.0,
        le=10.0,
        description="Score out of 10 for the user's submission",
    )
    correct_findings: list[str] = Field(
        default_factory=list,
        description="Findings the user correctly identified",
    )
    missed_findings: list[str] = Field(
        default_factory=list,
        description="Vulnerabilities the user missed or described incorrectly",
    )
    explanation: str = Field(
        ...,
        description="Plain-English explanation of the full evaluation",
    )
    fix_suggestion: str = Field(
        ...,
        description="Concrete remediation advice for the vulnerability",
    )

    @field_validator("score")
    @classmethod
    def round_score(cls, v: float) -> float:
        return round(v, 1)


# ── Submission schemas ────────────────────────────────────────────────────────

class SubmissionCreate(BaseModel):
    challenge_id: uuid.UUID
    user_answer: str = Field(
        ...,
        min_length=20,
        description="The user's written analysis of the code vulnerability",
    )


class SubmissionResponse(BaseModel):
    id: uuid.UUID
    challenge_id: uuid.UUID
    attempt_number: int
    user_answer: str
    score: Optional[float]
    correct_findings: Optional[str]
    missed_findings: Optional[str]
    explanation: Optional[str]
    fix_suggestion: Optional[str]
    submitted_at: datetime

    model_config = {"from_attributes": True}


# ── User / Auth schemas ───────────────────────────────────────────────────────

class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=64)
    email: str
    password: str = Field(..., min_length=8)


class UserResponse(BaseModel):
    id: uuid.UUID
    username: str
    email: str
    created_at: datetime

    model_config = {"from_attributes": True}


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    user_id: Optional[uuid.UUID] = None


# ── Dashboard schemas ─────────────────────────────────────────────────────────

class CategoryStats(BaseModel):
    category: VulnCategory
    attempts: int
    average_score: float
    completion_rate: float


class DifficultyStats(BaseModel):
    difficulty: Difficulty
    attempts: int
    average_score: float
    completion_rate: float


class DashboardResponse(BaseModel):
    total_attempts: int
    overall_average_score: float
    challenges_completed: int
    total_challenges_available: int
    category_breakdown: list[CategoryStats]
    difficulty_breakdown: list[DifficultyStats]
    recent_submissions: list[SubmissionResponse]
