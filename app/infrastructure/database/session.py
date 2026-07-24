"""
Database session management using SQLAlchemy 2.0 with asyncpg.
"""

from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings

settings = get_settings()

# Create the async engine connected to PostgreSQL via asyncpg
engine = create_async_engine(
    settings.ASYNC_DATABASE_URL,
    echo=settings.DEBUG,  # Log SQL queries if DEBUG is True
    future=True,
    pool_size=10,
    max_overflow=20,
)

# Create a session factory bound to the engine
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency to yield an async database session per request.
    Ensures the session is safely closed after the request completes.
    """
    async with AsyncSessionLocal() as session:
        yield session
