from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.db import get_session
from app.main import app
from app.models.base import Base

TEST_URL = "postgresql+asyncpg://shop:shop@localhost:5433/shop_test"

engine = create_async_engine(TEST_URL, poolclass=NullPool)
TestSession = async_sessionmaker(engine, expire_on_commit=False)


@pytest.fixture(autouse=True)
async def prepare_db() -> AsyncGenerator[None, None]:
    # создаём схему перед тестом, сносим после — чистый лист каждый раз
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    async def override_session():
        async with TestSession() as session:
            yield session

    app.dependency_overrides[get_session] = override_session
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()
