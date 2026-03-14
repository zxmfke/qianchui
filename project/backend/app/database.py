from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.config import get_settings

settings = get_settings()

_engine_kwargs: dict = {"echo": False}

if settings.DATABASE_URL.startswith("postgresql"):
    _engine_kwargs["poolclass"] = NullPool

engine = create_async_engine(settings.DATABASE_URL, **_engine_kwargs)

if settings.DATABASE_URL.startswith("postgresql+asyncpg"):
    def _skip_init(connection):
        engine.dialect.server_version_info = (16, 9)
        engine.dialect.default_schema_name = "public"
        engine.dialect._backslash_escapes = False

    engine.dialect.initialize = _skip_init

async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
