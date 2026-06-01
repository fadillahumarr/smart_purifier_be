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


async def create_purifier(client, token, payload=None):
    if payload is None:
        payload = make_purifier_payload()

    response = await client.post(
        f"{PURIFIER_PREFIX}/create",
        json=payload,
        headers={
            "Authorization": f"Bearer {token}",
        },
    )

    return response, payload


async def test_create_purifier_success(client):
    token = await register_and_login(client)

    response, payload = await create_purifier(client, token)

    assert response.status_code == 201

    data = response.json()

    assert "id" in data
    assert data["name"] == payload["name"]
    assert data["location"] == payload["location"]
    assert data["mac_address"] == payload["mac_address"]
    assert data["device_code"] == payload["device_code"]
    assert data["mqtt_topic_base"] == payload["mqtt_topic_base"]


async def test_create_purifier_without_token(client):
    payload = make_purifier_payload()

    response = await client.post(
        f"{PURIFIER_PREFIX}/create",
        json=payload,
    )

    assert response.status_code in [401, 403]


async def test_create_purifier_duplicate_device_code_or_mqtt_or_mac(client):
    token = await register_and_login(client)

    payload = make_purifier_payload()

    first_response, _ = await create_purifier(client, token, payload)

    second_response, _ = await create_purifier(client, token, payload)

    assert first_response.status_code == 201
    assert second_response.status_code == 409
    assert second_response.json()["detail"] == (
        "Device code, MQTT topic, or MAC address already exists"
    )


async def test_list_purifiers_success(client):
    token = await register_and_login(client)

    create_response, payload = await create_purifier(client, token)

    assert create_response.status_code == 201

    response = await client.get(
        PURIFIER_PREFIX,
        headers={
            "Authorization": f"Bearer {token}",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert isinstance(data, list)
    assert len(data) >= 1

    purifier_names = [item["name"] for item in data]

    assert payload["name"] in purifier_names


async def test_get_purifier_success(client):
    token = await register_and_login(client)

    create_response, payload = await create_purifier(client, token)

    assert create_response.status_code == 201

    purifier_id = create_response.json()["id"]

    response = await client.get(
        f"{PURIFIER_PREFIX}/{purifier_id}",
        headers={
            "Authorization": f"Bearer {token}",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["id"] == purifier_id
    assert data["name"] == payload["name"]
    assert data["device_code"] == payload["device_code"]


async def test_get_purifier_not_found(client):
    token = await register_and_login(client)

    fake_id = uuid4()

    response = await client.get(
        f"{PURIFIER_PREFIX}/{fake_id}",
        headers={
            "Authorization": f"Bearer {token}",
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Purifier not found"


async def test_update_purifier_success(client):
    token = await register_and_login(client)

    create_response, _ = await create_purifier(client, token)

    assert create_response.status_code == 201

    purifier_id = create_response.json()["id"]

    update_payload = {
        "name": "Updated Purifier Name",
        "location": "Updated Location",
    }

    response = await client.put(
        f"{PURIFIER_PREFIX}/{purifier_id}",
        json=update_payload,
        headers={
            "Authorization": f"Bearer {token}",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["id"] == purifier_id
    assert data["name"] == update_payload["name"]
    assert data["location"] == update_payload["location"]


async def test_update_purifier_not_found(client):
    token = await register_and_login(client)

    fake_id = uuid4()

    response = await client.put(
        f"{PURIFIER_PREFIX}/{fake_id}",
        json={
            "name": "Updated Name",
        },
        headers={
            "Authorization": f"Bearer {token}",
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Purifier not found"


async def test_delete_purifier_success(client):
    token = await register_and_login(client)

    create_response, _ = await create_purifier(client, token)

    assert create_response.status_code == 201

    purifier_id = create_response.json()["id"]

    delete_response = await client.delete(
        f"{PURIFIER_PREFIX}/{purifier_id}",
        headers={
            "Authorization": f"Bearer {token}",
        },
    )

    assert delete_response.status_code == 204

    get_response = await client.get(
        f"{PURIFIER_PREFIX}/{purifier_id}",
        headers={
            "Authorization": f"Bearer {token}",
        },
    )

    assert get_response.status_code == 404


async def test_delete_purifier_not_found(client):
    token = await register_and_login(client)

    fake_id = uuid4()

    response = await client.delete(
        f"{PURIFIER_PREFIX}/{fake_id}",
        headers={
            "Authorization": f"Bearer {token}",
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Purifier not found"
