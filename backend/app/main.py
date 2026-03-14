"""
app/main.py
───────────
SecureDevIQ — FastAPI application entry point.

Lifespan:
  startup  → runs Alembic-equivalent table creation (safety net for dev)
  shutdown → cleanly disposes the async connection pool
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import auth, challenges, dashboard, submissions
from app.config import get_settings
from app.database import Base, engine
from app.models import Challenge, Submission, User  # noqa: F401 – registers tables


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Dev safety net: create tables if they don't already exist.
    # In production, Alembic migrations run before the server starts
    # (see the CMD in docker-compose.yml).
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


def create_app() -> FastAPI:
    s = get_settings()
    app = FastAPI(
        title=s.app_name,
        description=(
            "Interactive security training platform that teaches developers "
            "to identify and fix vulnerabilities in LLM-generated code."
        ),
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/api/docs",
        redoc_url="/api/redoc",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=s.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(auth.router)
    app.include_router(challenges.router)
    app.include_router(submissions.router)
    app.include_router(dashboard.router)

    @app.get("/health", tags=["meta"])
    async def health():
        return {"status": "ok", "app": s.app_name}

    return app


app = create_app()
