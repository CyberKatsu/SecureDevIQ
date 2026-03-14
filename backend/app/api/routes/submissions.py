"""
Submission routes.

POST /api/submissions        – submit an answer for evaluation
GET  /api/submissions/{id}   – retrieve a submission result
GET  /api/submissions/me     – all submissions for the current user
"""
import asyncio
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Challenge, Submission, User
from app.schemas import SubmissionCreate, SubmissionResponse
from app.services.ai_service import evaluate_submission
from app.services.auth_service import get_current_user

router = APIRouter(prefix="/api/submissions", tags=["submissions"])


@router.post("", response_model=SubmissionResponse, status_code=201)
async def submit_answer(
    payload: SubmissionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Accept the user's vulnerability analysis, call Claude to evaluate it,
    persist the scored result, and return it.
    """
    # Fetch the challenge (we need the code and reference explanation)
    challenge_result = await db.execute(
        select(Challenge).where(Challenge.id == payload.challenge_id)
    )
    challenge = challenge_result.scalar_one_or_none()
    if not challenge:
        raise HTTPException(status_code=404, detail="Challenge not found")

    # Determine attempt number
    existing = await db.execute(
        select(Submission)
        .where(
            Submission.user_id == current_user.id,
            Submission.challenge_id == challenge.id,
        )
        .order_by(Submission.attempt_number.desc())
    )
    last = existing.scalars().first()
    attempt_number = (last.attempt_number + 1) if last else 1

    # Create submission record (initially unscored)
    submission = Submission(
        user_id=current_user.id,
        challenge_id=challenge.id,
        attempt_number=attempt_number,
        user_answer=payload.user_answer,
    )
    db.add(submission)
    await db.flush()

    # Evaluate via Claude (offloaded to thread pool)
    try:
        scoring = await asyncio.to_thread(
            evaluate_submission,
            challenge.code_snippet,
            challenge.reference_explanation,
            payload.user_answer,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"AI evaluation failed: {exc}",
        )

    # Persist the scored fields
    submission.score = scoring.score
    submission.correct_findings = "\n".join(scoring.correct_findings)
    submission.missed_findings = "\n".join(scoring.missed_findings)
    submission.explanation = scoring.explanation
    submission.fix_suggestion = scoring.fix_suggestion

    return submission


@router.get("/me", response_model=list[SubmissionResponse])
async def my_submissions(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Submission)
        .where(Submission.user_id == current_user.id)
        .order_by(Submission.submitted_at.desc())
    )
    return result.scalars().all()


@router.get("/{submission_id}", response_model=SubmissionResponse)
async def get_submission(
    submission_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Submission).where(
            Submission.id == submission_id,
            Submission.user_id == current_user.id,
        )
    )
    submission = result.scalar_one_or_none()
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    return submission
