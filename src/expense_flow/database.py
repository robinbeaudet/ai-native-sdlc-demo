from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from expense_flow.config import get_settings

# The schema is managed only by Alembic migrations (`uv run alembic upgrade head`), in every
# environment. The app never calls `create_all`, so the database cannot drift from the
# migration history.
settings = get_settings()
engine = create_async_engine(settings.database_url, echo=settings.sql_echo)
SessionFactory = async_sessionmaker(engine, expire_on_commit=False)


async def get_session() -> AsyncGenerator[AsyncSession]:
    """FastAPI dependency: one database session per request."""
    async with SessionFactory() as session:
        yield session
