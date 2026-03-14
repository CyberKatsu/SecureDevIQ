"""Dashboard aggregation route."""
from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Challenge, Submission, User, VulnCategory, Difficulty
from app.schemas import (
    CategoryStats,
    DashboardResponse,
    DifficultyStats,
    SubmissionResponse,
)
from app.services.auth_service import get_current_user

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("", response_model=DashboardResponse)
async def get_dashboard(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return aggregated progress stats for the current user."""
    uid = current_user.id

    # ── Overall stats ─────────────────────────────────────────────────────────
    total_result = await db.execute(
        select(
            func.count(Submission.id),
            func.coalesce(func.avg(Submission.score), 0.0),
        ).where(Submission.user_id == uid)
    )
    total_attempts, overall_avg = total_result.one()

    # Distinct challenges completed (at least one submission)
    completed_result = await db.execute(
        select(func.count(func.distinct(Submission.challenge_id))).where(
            Submission.user_id == uid
        )
    )
    challenges_completed = completed_result.scalar_one()

    total_challenges_result = await db.execute(select(func.count(Challenge.id)))
    total_challenges = total_challenges_result.scalar_one()

    # ── Per-category breakdown ────────────────────────────────────────────────
    cat_result = await db.execute(
        select(
            Challenge.vuln_category,
            func.count(Submission.id),
            func.coalesce(func.avg(Submission.score), 0.0),
        )
        .join(Challenge, Submission.challenge_id == Challenge.id)
        .where(Submission.user_id == uid)
        .group_by(Challenge.vuln_category)
    )
    category_breakdown = [
        CategoryStats(
            category=row[0],
            attempts=row[1],
            average_score=round(float(row[2]), 1),
            completion_rate=round(min(row[1] / max(total_attempts, 1), 1.0), 2),
        )
        for row in cat_result.all()
    ]

    # ── Per-difficulty breakdown ──────────────────────────────────────────────
    diff_result = await db.execute(
        select(
            Challenge.difficulty,
            func.count(Submission.id),
            func.coalesce(func.avg(Submission.score), 0.0),
        )
        .join(Challenge, Submission.challenge_id == Challenge.id)
        .where(Submission.user_id == uid)
        .group_by(Challenge.difficulty)
    )
    difficulty_breakdown = [
        DifficultyStats(
            difficulty=row[0],
            attempts=row[1],
            average_score=round(float(row[2]), 1),
            completion_rate=round(min(row[1] / max(total_attempts, 1), 1.0), 2),
        )
        for row in diff_result.all()
    ]

    # ── Recent submissions ────────────────────────────────────────────────────
    recent_result = await db.execute(
        select(Submission)
        .where(Submission.user_id == uid)
        .order_by(Submission.submitted_at.desc())
        .limit(5)
    )
    recent = recent_result.scalars().all()

    return DashboardResponse(
        total_attempts=total_attempts,
        overall_average_score=round(float(overall_avg), 1),
        challenges_completed=challenges_completed,
        total_challenges_available=total_challenges,
        category_breakdown=category_breakdown,
        difficulty_breakdown=difficulty_breakdown,
        recent_submissions=[SubmissionResponse.model_validate(s) for s in recent],
    )
