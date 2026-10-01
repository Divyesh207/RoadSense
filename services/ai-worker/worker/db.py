from app.core.config import settings
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

# Each Celery task runs its coroutine under a fresh asyncio.run() event loop.
# asyncpg connections are bound to the loop that opened them, so the worker
# must not reuse pooled connections across tasks: NullPool opens and closes a
# connection per session instead of sharing the API's pooled engine.
worker_engine = create_async_engine(settings.DATABASE_URL, poolclass=NullPool, future=True)

WorkerSessionLocal = async_sessionmaker(
    bind=worker_engine,
    class_=AsyncSession,
    autoflush=False,
    expire_on_commit=False,
)
