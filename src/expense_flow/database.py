from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from expense_flow.config import get_settings
from expense_flow.models import Base

settings = get_settings()
engine = create_async_engine(settings.database_url, echo=settings.sql_echo)
SessionFactory = async_sessionmaker(engine, expire_on_commit=False)


async def get_session() -> AsyncGenerator[AsyncSession]:
    """FastAPI dependency: one database session per request."""
    async with SessionFactory() as session:
        yield session


async def init_db(bind: AsyncEngine = engine) -> None:
    """Create the tables directly from the models."""
    async with bind.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
