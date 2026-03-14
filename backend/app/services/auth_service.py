"""
app/services/auth_service.py
────────────────────────────
JWT-based authentication helpers.

Design decisions:
- bcrypt used directly (not via passlib) to avoid the passlib/bcrypt 4.x
  incompatibility (passlib has an open bug with bcrypt >=4.0.0).
- JWTs are stateless HS256 tokens; no server-side session storage needed.
- get_current_user() is the canonical FastAPI security dependency, injected
  into any route that requires authentication.
"""
import uuid
from datetime import datetime, timedelta, timezone

import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db
from app.models import User
from app.schemas import TokenData

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token")


# ── Password helpers ──────────────────────────────────────────────────────────

def hash_password(plain: str) -> str:
    """Hash a plaintext password using bcrypt."""
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    """Return True if the plaintext matches the bcrypt hash."""
    return bcrypt.checkpw(plain.encode(), hashed.encode())


# ── JWT helpers ───────────────────────────────────────────────────────────────

def create_access_token(user_id: uuid.UUID) -> str:
    s = get_settings()
    expire = datetime.now(timezone.utc) + timedelta(minutes=s.access_token_expire_minutes)
    return jwt.encode(
        {"sub": str(user_id), "exp": expire},
        s.secret_key,
        algorithm=s.algorithm,
    )


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """FastAPI dependency: decode JWT and return the authenticated User."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    s = get_settings()
    try:
        payload = jwt.decode(token, s.secret_key, algorithms=[s.algorithm])
        user_id_str: str | None = payload.get("sub")
        if not user_id_str:
            raise credentials_exception
        token_data = TokenData(user_id=uuid.UUID(user_id_str))
    except (JWTError, ValueError):
        raise credentials_exception

    result = await db.execute(select(User).where(User.id == token_data.user_id))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise credentials_exception
    return user
