"""
Main entry point for the FastAPI application.

Responsibilities:
- Instantiate FastAPI application with metadata.
- Configure middleware (CORS).
- Register API routers.
"""

from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.health import router as health_router
from app.core.config import get_settings


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    """
    FastAPI lifespan context manager.

    Initializes application resources on startup and cleans them up on shutdown.
    """
    # ── Startup ──────────────────────────────────────────────────────
    settings = get_settings()
    if settings.DEBUG:
        print(f"🚀 {settings.APP_NAME} v{settings.APP_VERSION} starting in DEBUG mode")
    yield
    # ── Shutdown ─────────────────────────────────────────────────────


def create_app() -> FastAPI:
    """
    Application factory.

    Enables isolated application instances for testing and environment-specific configs.
    """
    settings = get_settings()

    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description=settings.APP_DESCRIPTION,
        docs_url="/docs" if settings.ENVIRONMENT != "production" else None,
        redoc_url="/redoc" if settings.ENVIRONMENT != "production" else None,
        lifespan=lifespan,
    )

    # ── CORS Middleware ──────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
        allow_headers=["*"],
    )

    # ── Routers ──────────────────────────────────────────────────────
    from app.api.routers.documents import router as documents_router
    from app.api.routers.extract import router as extract_router

    app.include_router(health_router)
    app.include_router(extract_router, prefix="/api/v1")
    app.include_router(documents_router, prefix="/api/v1")

    return app


app = create_app()
