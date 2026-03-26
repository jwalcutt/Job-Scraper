from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool

from app.config import settings

# Shared pooled engine for the FastAPI app (consistent event loop)
engine = create_async_engine(settings.database_url, echo=False, pool_pre_ping=True)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session


@asynccontextmanager
async def task_session():
    """
    Yields a fresh session backed by a NullPool engine.
    Use in Celery tasks — each task creates its own event loop via
    asyncio.new_event_loop(), so pooled connections from the shared engine
    would be bound to the wrong loop and crash with
    'Future attached to a different loop'.
    NullPool creates a new connection on every use and closes it immediately,
    avoiding all loop-affinity issues.
    """
    eng = create_async_engine(settings.database_url, poolclass=NullPool)
    factory = async_sessionmaker(eng, expire_on_commit=False)
    try:
        async with factory() as session:
            yield session
    finally:
        await eng.dispose()
