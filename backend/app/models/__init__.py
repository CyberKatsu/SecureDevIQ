"""
SQLAlchemy ORM models.

Three core tables:
- users           – registered learners
- challenges      – AI-generated vulnerability scenarios (cached after first gen)
- submissions     – a user's attempt at a challenge + AI-scored result

Relationships keep the schema normalised while still being easy to query
with SQLAlchemy's async select().
"""
import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


# ── Enums ─────────────────────────────────────────────────────────────────────

class Difficulty(str, enum.Enum):
    JUNIOR = "junior"
    MID = "mid"
    SENIOR = "senior"


class Language(str, enum.Enum):
    PYTHON = "python"
    SQL = "sql"
    BASH = "bash"


class VulnCategory(str, enum.Enum):
    PROMPT_INJECTION = "prompt_injection"
    MEMORY_ISSUES = "memory_issues"
    INSECURE_DEFAULTS = "insecure_defaults"
    MISSING_SANITISATION = "missing_sanitisation"
    HARDCODED_SECRETS = "hardcoded_secrets"


# ── Models ────────────────────────────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    username: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(256), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(256), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    submissions: Mapped[list["Submission"]] = relationship(
        back_populates="user", lazy="select"
    )


class Challenge(Base):
    """
    AI-generated challenge stored after first generation.
    Re-using cached challenges avoids redundant API calls and ensures
    consistent scoring baselines.
    """
    __tablename__ = "challenges"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    code_snippet: Mapped[str] = mapped_column(Text, nullable=False)
    language: Mapped[Language] = mapped_column(
        Enum(
            Language,
            name="language",
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
    )
    difficulty: Mapped[Difficulty] = mapped_column(
        Enum(
            Difficulty,
            name="difficulty",
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
    )
    vuln_category: Mapped[VulnCategory] = mapped_column(
        Enum(
            VulnCategory,
            name="vulncategory",
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
    )
    # Ground-truth explanation stored for the evaluator prompt
    reference_explanation: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    submissions: Mapped[list["Submission"]] = relationship(
        back_populates="challenge", lazy="select"
    )


class Submission(Base):
    """A user's attempt at identifying vulnerabilities in a challenge."""
    __tablename__ = "submissions"
    __table_args__ = (
        # one submission per user per challenge (re-attempts create a new row)
        UniqueConstraint("user_id", "challenge_id", "attempt_number"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    challenge_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("challenges.id", ondelete="CASCADE"), nullable=False
    )
    attempt_number: Mapped[int] = mapped_column(Integer, default=1)

    # What the user submitted
    user_answer: Mapped[str] = mapped_column(Text, nullable=False)

    # AI evaluation results
    score: Mapped[float] = mapped_column(Float, nullable=True)
    correct_findings: Mapped[str] = mapped_column(Text, nullable=True)
    missed_findings: Mapped[str] = mapped_column(Text, nullable=True)
    explanation: Mapped[str] = mapped_column(Text, nullable=True)
    fix_suggestion: Mapped[str] = mapped_column(Text, nullable=True)

    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    user: Mapped["User"] = relationship(back_populates="submissions")
    challenge: Mapped["Challenge"] = relationship(back_populates="submissions")
