import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from expense_flow.database import get_session, init_db
from expense_flow.main import create_app


@pytest.fixture
async def session_factory():
    """A fresh in-memory database for every test."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", poolclass=StaticPool)
    await init_db(engine)
    yield async_sessionmaker(engine, expire_on_commit=False)
    await engine.dispose()


@pytest.fixture
async def session(session_factory):
    async with session_factory() as session:
        yield session


@pytest.fixture
async def client(session_factory):
    app = create_app()

    async def test_session():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = test_session
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client


@pytest.fixture
def submit_claim(client):
    """POST /claims with default values; keyword arguments override the payload."""

    async def _submit(**overrides):
        payload = {
            "employee_id": "emp-001",
            "category": "TRAVEL",
            "amount": "120.00",
            "description": "Train ticket Paris-Lyon",
            **overrides,
        }
        response = await client.post("/claims", json=payload)
        assert response.status_code == 201, response.text
        return response.json()

    return _submit
