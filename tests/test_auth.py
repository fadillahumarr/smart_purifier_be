import pytest
import pytest_asyncio
from uuid import uuid4

from httpx import AsyncClient, ASGITransport

from app.main import app


pytestmark = pytest.mark.asyncio(loop_scope="session")

BASE_URL = "http://test"
AUTH_PREFIX = "/api/v1/auth"


@pytest_asyncio.fixture(scope="session")
async def client():
    transport = ASGITransport(app=app)

    async with AsyncClient(
        transport=transport,
        base_url=BASE_URL,
    ) as async_client:
        yield async_client


def make_user_payload():
    email = f"user_{uuid4().hex}@example.com"

    return {
        "name": "Test User",
        "email": email,
        "password": "password123",
    }


async def register_user(client, payload=None):
    if payload is None:
        payload = make_user_payload()

    response = await client.post(
        f"{AUTH_PREFIX}/register",
        json=payload,
    )

    return response, payload


async def login_user(client, email, password):
    response = await client.post(
        f"{AUTH_PREFIX}/login",
        json={
            "email": email,
            "password": password,
        },
    )

    return response


async def test_register_success(client):
    response, payload = await register_user(client)

    assert response.status_code == 201

    data = response.json()

    assert "id" in data
    assert data["name"] == payload["name"]
    assert data["email"] == payload["email"]

    assert "password" not in data
    assert "password_hash" not in data


async def test_register_duplicate_email(client):
    payload = make_user_payload()

    first_response = await client.post(
        f"{AUTH_PREFIX}/register",
        json=payload,
    )

    second_response = await client.post(
        f"{AUTH_PREFIX}/register",
        json=payload,
    )

    assert first_response.status_code == 201
    assert second_response.status_code == 409
    assert second_response.json()["detail"] == "Email already registered"


async def test_register_invalid_email(client):
    response = await client.post(
        f"{AUTH_PREFIX}/register",
        json={
            "name": "Test User",
            "email": "email-salah",
            "password": "password123",
        },
    )

    assert response.status_code == 422


async def test_register_missing_name(client):
    response = await client.post(
        f"{AUTH_PREFIX}/register",
        json={
            "email": f"user_{uuid4().hex}@example.com",
            "password": "password123",
        },
    )

    assert response.status_code == 422


async def test_register_missing_email(client):
    response = await client.post(
        f"{AUTH_PREFIX}/register",
        json={
            "name": "Test User",
            "password": "password123",
        },
    )

    assert response.status_code == 422


async def test_register_missing_password(client):
    response = await client.post(
        f"{AUTH_PREFIX}/register",
        json={
            "name": "Test User",
            "email": f"user_{uuid4().hex}@example.com",
        },
    )

    assert response.status_code == 422


async def test_login_success(client):
    register_response, payload = await register_user(client)

    assert register_response.status_code == 201

    login_response = await login_user(
        client,
        payload["email"],
        payload["password"],
    )

    assert login_response.status_code == 200

    data = login_response.json()

    assert "access_token" in data
    assert "refresh_token" in data

    assert isinstance(data["access_token"], str)
    assert isinstance(data["refresh_token"], str)

    assert len(data["access_token"]) > 0
    assert len(data["refresh_token"]) > 0


async def test_login_wrong_password(client):
    register_response, payload = await register_user(client)

    assert register_response.status_code == 201

    login_response = await login_user(
        client,
        payload["email"],
        "wrongpassword",
    )

    assert login_response.status_code == 401
    assert login_response.json()["detail"] == "Invalid email or password"


async def test_login_email_not_registered(client):
    login_response = await login_user(
        client,
        f"notfound_{uuid4().hex}@example.com",
        "password123",
    )

    assert login_response.status_code == 401
    assert login_response.json()["detail"] == "Invalid email or password"


async def test_me_success(client):
    register_response, payload = await register_user(client)

    assert register_response.status_code == 201

    login_response = await login_user(
        client,
        payload["email"],
        payload["password"],
    )

    assert login_response.status_code == 200

    access_token = login_response.json()["access_token"]

    me_response = await client.get(
        f"{AUTH_PREFIX}/me",
        headers={
            "Authorization": f"Bearer {access_token}",
        },
    )

    assert me_response.status_code == 200

    data = me_response.json()

    assert data["name"] == payload["name"]
    assert data["email"] == payload["email"]


async def test_me_without_token(client):
    response = await client.get(f"{AUTH_PREFIX}/me")

    assert response.status_code in [401, 403]


async def test_refresh_success(client):
    register_response, payload = await register_user(client)

    assert register_response.status_code == 201

    login_response = await login_user(
        client,
        payload["email"],
        payload["password"],
    )

    assert login_response.status_code == 200

    refresh_token = login_response.json()["refresh_token"]

    refresh_response = await client.post(
        f"{AUTH_PREFIX}/refresh",
        json={
            "refresh_token": refresh_token,
        },
    )

    assert refresh_response.status_code == 200

    data = refresh_response.json()

    assert "access_token" in data
    assert "refresh_token" in data

    assert isinstance(data["access_token"], str)
    assert isinstance(data["refresh_token"], str)


async def test_refresh_invalid_token(client):
    response = await client.post(
        f"{AUTH_PREFIX}/refresh",
        json={
            "refresh_token": "invalid-refresh-token",
        },
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid or expired refresh token"


async def test_logout_success(client):
    register_response, payload = await register_user(client)

    assert register_response.status_code == 201

    login_response = await login_user(
        client,
        payload["email"],
        payload["password"],
    )

    assert login_response.status_code == 200

    refresh_token = login_response.json()["refresh_token"]

    logout_response = await client.post(
        f"{AUTH_PREFIX}/logout",
        json={
            "refresh_token": refresh_token,
        },
    )

    assert logout_response.status_code == 200
    assert logout_response.json()["message"] == "Logged out successfully"


async def test_logout_invalid_token(client):
    response = await client.post(
        f"{AUTH_PREFIX}/logout",
        json={
            "refresh_token": "invalid-refresh-token",
        },
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid or expired refresh token"
