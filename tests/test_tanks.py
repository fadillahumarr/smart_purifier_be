import pytest
import pytest_asyncio
from uuid import uuid4

from httpx import AsyncClient, ASGITransport

from app.main import app


pytestmark = pytest.mark.asyncio(loop_scope="session")

BASE_URL = "http://test"
AUTH_PREFIX = "/api/v1/auth"
PURIFIER_PREFIX = "/api/v1/purifiers"


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


def make_purifier_payload():
    unique = uuid4().hex[:10]

    return {
        "name": "Smart Purifier Test",
        "location": "Lab Testing",
        "mac_address": f"AA:BB:CC:{unique[:2]}:{unique[2:4]}:{unique[4:6]}",
        "device_code": f"DEVICE-{unique}",
        "mqtt_topic_base": f"smart-purifier/test/{unique}",
        "firmware_version": "1.0.0",
    }


async def register_and_login(client):
    user_payload = make_user_payload()

    register_response = await client.post(
        f"{AUTH_PREFIX}/register",
        json=user_payload,
    )

    assert register_response.status_code == 201

    login_response = await client.post(
        f"{AUTH_PREFIX}/login",
        json={
            "email": user_payload["email"],
            "password": user_payload["password"],
        },
    )

    assert login_response.status_code == 200

    access_token = login_response.json()["access_token"]

    return access_token


async def create_purifier(client, token):
    payload = make_purifier_payload()

    response = await client.post(
        f"{PURIFIER_PREFIX}/create",
        json=payload,
        headers={
            "Authorization": f"Bearer {token}",
        },
    )

    assert response.status_code == 201

    return response.json()


async def test_list_tanks_success(client):
    token = await register_and_login(client)

    purifier = await create_purifier(client, token)
    purifier_id = purifier["id"]

    response = await client.get(
        f"{PURIFIER_PREFIX}/{purifier_id}/tanks",
        headers={
            "Authorization": f"Bearer {token}",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert isinstance(data, list)
    assert len(data) == 3

    tank_names = [tank["name"] for tank in data]

    assert "Tangki Raw Water" in tank_names
    assert "Tangki Mixing" in tank_names
    assert "Tangki Settling" in tank_names


async def test_list_tanks_without_token(client):
    fake_purifier_id = uuid4()

    response = await client.get(
        f"{PURIFIER_PREFIX}/{fake_purifier_id}/tanks",
    )

    assert response.status_code in [401, 403]


async def test_list_tanks_purifier_not_found(client):
    token = await register_and_login(client)

    fake_purifier_id = uuid4()

    response = await client.get(
        f"{PURIFIER_PREFIX}/{fake_purifier_id}/tanks",
        headers={
            "Authorization": f"Bearer {token}",
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Purifier not found"


async def test_list_tanks_cannot_access_other_user_purifier(client):
    first_user_token = await register_and_login(client)
    second_user_token = await register_and_login(client)

    purifier = await create_purifier(client, first_user_token)
    purifier_id = purifier["id"]

    response = await client.get(
        f"{PURIFIER_PREFIX}/{purifier_id}/tanks",
        headers={
            "Authorization": f"Bearer {second_user_token}",
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Purifier not found"
