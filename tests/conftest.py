import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlmodel import SQLModel
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.core.database import get_session
from main import app

# ── Unit test DB (session-scoped, shared across unit tests) ──
TEST_DATABASE_URL = "sqlite+aiosqlite:///./test.db"
test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
test_async_session = sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)

async def override_get_session():
    async with test_async_session() as session:
        yield session

app.dependency_overrides[get_session] = override_get_session

@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_db():
    async with test_engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.drop_all)

@pytest_asyncio.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as c:
        yield c

@pytest_asyncio.fixture
async def tenant_api_key(client):
    response = await client.post(
        "/api/v1/tenants/",
        json={"name": "Test Tenant"},
        headers={"X-Admin-Token": "super-secret-admin-token"}
    )
    return response.json()["api_key"]

# ── Integration test DB (function-scoped, wiped after each test) ──
INTEGRATION_DATABASE_URL = "sqlite+aiosqlite:///./test_integration.db"

@pytest_asyncio.fixture
async def integration_engine():
    engine = create_async_engine(INTEGRATION_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.drop_all)
    await engine.dispose()

@pytest_asyncio.fixture
async def integration_client(integration_engine):
    integration_session = sessionmaker(
        integration_engine, class_=AsyncSession, expire_on_commit=False
    )

    async def override_integration_session():
        async with integration_session() as session:
            yield session

    app.dependency_overrides[get_session] = override_integration_session

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as c:
        yield c

    # Restore original override after test
    app.dependency_overrides[get_session] = override_get_session