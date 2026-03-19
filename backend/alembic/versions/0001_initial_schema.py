"""Initial schema: users, challenges, submissions

Revision ID: 0001
Revises:
Create Date: 2025-03-14
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Enums ──────────────────────────────────────────────────────────────────
    # Create enums with try-except to handle cases where they already exist
    try:
        op.execute("CREATE TYPE difficulty AS ENUM ('junior', 'mid', 'senior')")
    except Exception:
        pass  # Type already exists
    
    try:
        op.execute("CREATE TYPE language AS ENUM ('python', 'sql', 'bash')")
    except Exception:
        pass  # Type already exists
    
    try:
        op.execute(
            "CREATE TYPE vulncategory AS ENUM ("
            "'prompt_injection', 'memory_issues', 'insecure_defaults', "
            "'missing_sanitisation', 'hardcoded_secrets')"
        )
    except Exception:
        pass  # Type already exists

    # ── users ─────────────────────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("username", sa.String(64), unique=True, nullable=False),
        sa.Column("email", sa.String(256), unique=True, nullable=False),
        sa.Column("hashed_password", sa.String(256), nullable=False),
        sa.Column("is_active", sa.Boolean(), default=True, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )

    # ── challenges ────────────────────────────────────────────────────────────
    op.create_table(
        "challenges",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("title", sa.String(256), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("code_snippet", sa.Text(), nullable=False),
        sa.Column("language", postgresql.ENUM("python", "sql", "bash", name="language", create_type=False), nullable=False),
        sa.Column("difficulty", postgresql.ENUM("junior", "mid", "senior", name="difficulty", create_type=False), nullable=False),
        sa.Column(
            "vuln_category",
            postgresql.ENUM(
                "prompt_injection", "memory_issues", "insecure_defaults",
                "missing_sanitisation", "hardcoded_secrets",
                name="vulncategory",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("reference_explanation", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )

    # ── submissions ───────────────────────────────────────────────────────────
    op.create_table(
        "submissions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "challenge_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("challenges.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("attempt_number", sa.Integer(), default=1, nullable=False),
        sa.Column("user_answer", sa.Text(), nullable=False),
        sa.Column("score", sa.Float(), nullable=True),
        sa.Column("correct_findings", sa.Text(), nullable=True),
        sa.Column("missed_findings", sa.Text(), nullable=True),
        sa.Column("explanation", sa.Text(), nullable=True),
        sa.Column("fix_suggestion", sa.Text(), nullable=True),
        sa.Column(
            "submitted_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.UniqueConstraint("user_id", "challenge_id", "attempt_number"),
    )


def downgrade() -> None:
    op.drop_table("submissions")
    op.drop_table("challenges")
    op.drop_table("users")
    for name in ("difficulty", "language", "vulncategory"):
        op.execute(f"DROP TYPE IF EXISTS {name}")
