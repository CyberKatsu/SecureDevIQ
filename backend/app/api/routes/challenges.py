"""
Challenge routes.

GET /api/challenges        – list existing cached challenges (with filters)
POST /api/challenges/generate – generate a new challenge via Claude
GET /api/challenges/{id}   – retrieve a single challenge
"""
import asyncio
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Challenge, Difficulty, Language, User, VulnCategory
from app.schemas import (
    ChallengeGenerateRequest,
    ChallengeListResponse,
    ChallengeResponse,
)
from app.services.ai_service import generate_challenge
from app.services.auth_service import get_current_user

router = APIRouter(prefix="/api/challenges", tags=["challenges"])


@router.get("", response_model=ChallengeListResponse)
async def list_challenges(
    language: Language | None = Query(None),
    difficulty: Difficulty | None = Query(None),
    vuln_category: VulnCategory | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Return paginated list of existing challenges with optional filters."""
    query = select(Challenge)
    if language:
        query = query.where(Challenge.language == language)
    if difficulty:
        query = query.where(Challenge.difficulty == difficulty)
    if vuln_category:
        query = query.where(Challenge.vuln_category == vuln_category)

    count_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = count_result.scalar_one()

    result = await db.execute(query.offset(offset).limit(limit))
    challenges = result.scalars().all()

    return ChallengeListResponse(challenges=challenges, total=total)


@router.post("/generate", response_model=ChallengeResponse, status_code=201)
async def generate_new_challenge(
    payload: ChallengeGenerateRequest,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """
    Generate a fresh challenge via Claude and persist it.

    Design decision: asyncio.to_thread() offloads the synchronous Anthropic
    SDK call to a thread pool, keeping the event loop unblocked.
    """
    try:
        generated = await asyncio.to_thread(
            generate_challenge,
            payload.language,
            payload.difficulty,
            payload.vuln_category,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"AI generation failed: {exc}",
        )

    challenge = Challenge(
        title=generated.title,
        description=generated.description,
        code_snippet=generated.code_snippet,
        language=payload.language,
        difficulty=payload.difficulty,
        vuln_category=generated.vuln_category,
        reference_explanation=generated.reference_explanation,
    )
    db.add(challenge)
    await db.flush()
    return challenge


@router.get("/{challenge_id}", response_model=ChallengeResponse)
async def get_challenge(
    challenge_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Challenge).where(Challenge.id == challenge_id)
    )
    challenge = result.scalar_one_or_none()
    if not challenge:
        raise HTTPException(status_code=404, detail="Challenge not found")
    return challenge
