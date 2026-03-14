import asyncio
import warnings
from collections.abc import AsyncGenerator
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.services.auth_service import AuthService
from app.main import app, register_skills
from app.database import get_db
from app.models.base import Base
from app.config import get_settings

settings = get_settings()


def _try_build_pg_engine():
    """Try connecting to the real PostgreSQL from .env config."""
    db_url = settings.DATABASE_URL
    if not db_url.startswith("postgresql"):
        return None

    _base = db_url.rsplit("/", 1)[0]
    test_url = f"{_base}/qianchui_test"

    engine = create_async_engine(test_url, echo=False, poolclass=NullPool)

    if test_url.startswith("postgresql+asyncpg"):
        def _skip_init(connection):
            engine.dialect.server_version_info = (16, 9)
            engine.dialect.default_schema_name = "public"
            engine.dialect._backslash_escapes = False
        engine.dialect.initialize = _skip_init

    loop = asyncio.new_event_loop()
    try:
        async def _ping():
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
        loop.run_until_complete(asyncio.wait_for(_ping(), timeout=5))
        return engine
    except Exception:
        pass
    finally:
        loop.run_until_complete(engine.dispose())
        loop.close()

    engine2 = create_async_engine(db_url, echo=False, poolclass=NullPool)
    if db_url.startswith("postgresql+asyncpg"):
        def _skip_init2(connection):
            engine2.dialect.server_version_info = (16, 9)
            engine2.dialect.default_schema_name = "public"
            engine2.dialect._backslash_escapes = False
        engine2.dialect.initialize = _skip_init2

    loop2 = asyncio.new_event_loop()
    try:
        async def _ping2():
            async with engine2.connect() as conn:
                await conn.execute(text("SELECT 1"))
        loop2.run_until_complete(asyncio.wait_for(_ping2(), timeout=5))
        return engine2
    except Exception:
        loop2.run_until_complete(engine2.dispose())
        return None
    finally:
        loop2.close()


def _build_sqlite_engine():
    engine = create_async_engine("sqlite+aiosqlite://", echo=False)

    @event.listens_for(engine.sync_engine, "connect")
    def _set_sqlite_pragma(dbapi_conn, _rec):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=OFF")
        cursor.close()

    return engine


_pg_engine = _try_build_pg_engine()
if _pg_engine is not None:
    engine_test = _pg_engine
    _DB_BACKEND = "postgresql"
else:
    engine_test = _build_sqlite_engine()
    _DB_BACKEND = "sqlite"
    warnings.warn(
        f"PostgreSQL not reachable ({settings.DATABASE_URL}), "
        "falling back to SQLite for tests.",
        stacklevel=1,
    )

async_session_test = async_sessionmaker(
    engine_test, class_=AsyncSession, expire_on_commit=False
)

_skills_registered = False


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def db_backend():
    return _DB_BACKEND


@pytest.fixture(scope="session", autouse=True)
def _register_skills():
    global _skills_registered
    if not _skills_registered:
        register_skills()
        _skills_registered = True


@pytest_asyncio.fixture(scope="function")
async def test_db() -> AsyncGenerator[AsyncSession, None]:
    async with engine_test.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    async with async_session_test() as session:
        yield session

    async with engine_test.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture(scope="function")
async def async_client(test_db: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    async def _override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield test_db

    app.dependency_overrides[get_db] = _override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def test_enterprise(test_db: AsyncSession):
    from app.models.enterprise import Enterprise

    enterprise = Enterprise(
        id=uuid4(),
        name="测试企业",
        industry="医疗美容",
    )
    test_db.add(enterprise)
    await test_db.commit()
    await test_db.refresh(enterprise)
    return enterprise


@pytest_asyncio.fixture
async def test_user(test_db: AsyncSession, test_enterprise):
    from app.models.user import User

    user = User(
        id=uuid4(),
        username="testuser",
        email="test@example.com",
        hashed_password=AuthService.hash_password("testpass123"),
        enterprise_id=test_enterprise.id,
        role="admin",
        is_active=True,
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    return user


@pytest_asyncio.fixture
def auth_headers(test_user) -> dict:
    token = AuthService.create_access_token(data={
        "sub": str(test_user.id),
        "enterprise_id": str(test_user.enterprise_id),
        "role": test_user.role,
    })
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def super_admin_enterprise(test_db: AsyncSession):
    from app.models.enterprise import Enterprise

    enterprise = Enterprise(
        id=uuid4(),
        name="千锤平台",
        industry="平台运营",
    )
    test_db.add(enterprise)
    await test_db.commit()
    await test_db.refresh(enterprise)
    return enterprise


@pytest_asyncio.fixture
async def super_admin_user(test_db: AsyncSession, super_admin_enterprise):
    from app.models.user import User

    user = User(
        id=uuid4(),
        username="superadmin",
        email="superadmin@test.com",
        hashed_password=AuthService.hash_password("superpass123"),
        enterprise_id=super_admin_enterprise.id,
        role="super_admin",
        is_active=True,
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    return user


@pytest_asyncio.fixture
def super_admin_headers(super_admin_user) -> dict:
    token = AuthService.create_access_token(data={
        "sub": str(super_admin_user.id),
        "enterprise_id": str(super_admin_user.enterprise_id),
        "role": super_admin_user.role,
    })
    return {"Authorization": f"Bearer {token}"}
