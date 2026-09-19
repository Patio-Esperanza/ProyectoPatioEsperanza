import os
import subprocess
import sys
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

os.environ.setdefault(
    "DATABASE_URL", "postgresql+asyncpg://patio_app:patio_app@localhost:5433/patio_test"
)
os.environ.setdefault(
    "MIGRATIONS_DATABASE_URL", "postgresql+asyncpg://patio:patio@localhost:5433/patio_test"
)
os.environ.setdefault("JWT_SECRET", "test-secret")
os.environ.setdefault("JWT_EXPIRES_MINUTES", "60")
os.environ.setdefault("SENDGRID_API_KEY", "test-sendgrid-key")
os.environ.setdefault("SENDGRID_FROM_EMAIL", "test@patio.mx")

from app.db import get_db  # noqa: E402
from app.main import app  # noqa: E402

BACKEND_DIR = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session", autouse=True)
def apply_migrations():
    subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=BACKEND_DIR,
        check=True,
    )
    yield


@pytest_asyncio.fixture
async def db_session():
    engine = create_async_engine(os.environ["DATABASE_URL"])
    connection = await engine.connect()
    trans = await connection.begin()
    session_factory = async_sessionmaker(
        bind=connection,
        join_transaction_mode="create_savepoint",
        expire_on_commit=False,
        class_=AsyncSession,
    )
    session = session_factory()
    try:
        yield session
    finally:
        await session.close()
        await trans.rollback()
        await connection.close()
        await engine.dispose()


@pytest_asyncio.fixture
async def client(db_session):
    async def _get_db():
        yield db_session

    app.dependency_overrides[get_db] = _get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()
