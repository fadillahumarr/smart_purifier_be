import pytest
import pytest_asyncio
from uuid import uuid4

from httpx import AsyncClient, ASGITransport

from app.main import app


pytestmark = pytest.mark.asyncio(loop_scope="session")

BASE_URL = "http://test"
AUTH_PREFIX = "/api/v1/auth"
DASHBOARD_PREFIX = "/api/v1/dashboard"
DASHBOARD_PATH = "app.api.v1.endpoints.dashboard"


@pytest_asyncio.fixture(scope="session")
async def client():
    transport = ASGITransport(app=app)

    async with AsyncClient(
        transport=transport,
        base_url=BASE_URL,
    ) as async_client:
        yield async_client


def make_user_payload():
    return {
        "name": "Test User",
        "email": f"user_{uuid4().hex}@example.com",
        "password": "password123",
    }


async def register_and_login(client):
    payload = make_user_payload()

    register_response = await client.post(
        f"{AUTH_PREFIX}/register",
        json=payload,
    )

    assert register_response.status_code == 201

    login_response = await client.post(
        f"{AUTH_PREFIX}/login",
        json={
            "email": payload["email"],
            "password": payload["password"],
        },
    )

    assert login_response.status_code == 200

    return login_response.json()["access_token"]


async def test_dashboard_summary_without_token(client):
    response = await client.get(
        f"{DASHBOARD_PREFIX}/summary"
    )

    assert response.status_code in [401, 403]


async def test_dashboard_summary_success(client, monkeypatch):
    token = await register_and_login(client)

    async def fake_get_global_dashboard_summary(session, current_user):
        assert current_user is not None

        return {
            "total_purifiers": 5,
            "online_purifiers": 3,
            "offline_purifiers": 2,
            "active_alerts": 4,
        }

    monkeypatch.setattr(
        f"{DASHBOARD_PATH}.get_global_dashboard_summary",
        fake_get_global_dashboard_summary,
    )

    response = await client.get(
        f"{DASHBOARD_PREFIX}/summary",
        headers={
            "Authorization": f"Bearer {token}",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["total_purifiers"] == 5
    assert data["online_purifiers"] == 3
    assert data["offline_purifiers"] == 2
    assert data["active_alerts"] == 4


async def test_dashboard_summary_response_shape(client, monkeypatch):
    token = await register_and_login(client)

    async def fake_get_global_dashboard_summary(session, current_user):
        return {
            "total_purifiers": 0,
            "online_purifiers": 0,
            "offline_purifiers": 0,
            "active_alerts": 0,
        }

    monkeypatch.setattr(
        f"{DASHBOARD_PATH}.get_global_dashboard_summary",
        fake_get_global_dashboard_summary,
    )

    response = await client.get(
        f"{DASHBOARD_PREFIX}/summary",
        headers={
            "Authorization": f"Bearer {token}",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert set(data.keys()) == {
        "total_purifiers",
        "online_purifiers",
        "offline_purifiers",
        "active_alerts",
    }

    assert isinstance(data["total_purifiers"], int)
    assert isinstance(data["online_purifiers"], int)
    assert isinstance(data["offline_purifiers"], int)
    assert isinstance(data["active_alerts"], int)
