from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel.ext.asyncio.session import AsyncSession

from app.config import get_settings

engine = create_async_engine(get_settings().DB_URL, pool_pre_ping=True)


async def get_session() -> AsyncIterator[AsyncSession]:
    async with AsyncSession(engine) as session:
        yield session
