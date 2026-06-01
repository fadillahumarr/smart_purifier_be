import pytest
import pytest_asyncio
from uuid import uuid4
from datetime import datetime, timezone
from types import SimpleNamespace

from httpx import AsyncClient, ASGITransport

from app.main import app
from app.models.enums import AlertSeverity


pytestmark = pytest.mark.asyncio(loop_scope="session")

BASE_URL = "http://test"
AUTH_PREFIX = "/api/v1/auth"
ALERT_PREFIX = "/api/v1/alerts"
ALERT_PATH = "app.api.v1.endpoints.alerts"


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


def fake_alert_dict():
    return {
        "id": uuid4(),
        "water_purifier_id": uuid4(),
        "purifier_name": "Smart Purifier Test",
        "purification_cycle_id": None,
        "alert_type": "water_quality",
        "severity": list(AlertSeverity)[0],
        "title": "High Turbidity",
        "message": "Turbidity value is too high",
        "is_resolved": False,
        "created_at": datetime.now(timezone.utc),
        "resolved_at": None,
    }


def fake_alert_object(alert_id=None):
    return SimpleNamespace(
        id=alert_id or uuid4(),
        water_purifier_id=uuid4(),
        purification_cycle_id=None,
        alert_type="water_quality",
        severity=list(AlertSeverity)[0],
        title="High Turbidity",
        message="Turbidity value is too high",
        is_resolved=True,
        created_at=datetime.now(timezone.utc),
        resolved_at=datetime.now(timezone.utc),
    )


async def test_read_alerts_success(client, monkeypatch):
    token = await register_and_login(client)

    async def fake_list_alerts(
        session,
        user_id,
        status_filter,
        severity,
        purifier_id,
    ):
        assert user_id is not None
        assert status_filter == "all"
        assert severity is None
        assert purifier_id is None

        return {
            "items": [
                fake_alert_dict()
            ]
        }

    monkeypatch.setattr(
        f"{ALERT_PATH}.list_alerts",
        fake_list_alerts,
    )

    response = await client.get(
        ALERT_PREFIX,
        headers={
            "Authorization": f"Bearer {token}",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert "items" in data
    assert isinstance(data["items"], list)
    assert len(data["items"]) == 1

    item = data["items"][0]

    assert item["title"] == "High Turbidity"
    assert item["message"] == "Turbidity value is too high"
    assert item["is_resolved"] is False


async def test_read_alerts_with_filters(client, monkeypatch):
    token = await register_and_login(client)

    purifier_id = uuid4()
    severity_value = list(AlertSeverity)[0]

    async def fake_list_alerts(
        session,
        user_id,
        status_filter,
        severity,
        purifier_id,
    ):
        assert user_id is not None
        assert status_filter == "active"
        assert severity == severity_value
        assert purifier_id is not None

        return {
            "items": [
                fake_alert_dict()
            ]
        }

    monkeypatch.setattr(
        f"{ALERT_PATH}.list_alerts",
        fake_list_alerts,
    )

    response = await client.get(
        f"{ALERT_PREFIX}?status=active&severity={severity_value.value}&purifier_id={purifier_id}",
        headers={
            "Authorization": f"Bearer {token}",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert "items" in data
    assert len(data["items"]) == 1


async def test_read_alerts_invalid_status(client):
    token = await register_and_login(client)

    response = await client.get(
        f"{ALERT_PREFIX}?status=invalid",
        headers={
            "Authorization": f"Bearer {token}",
        },
    )

    assert response.status_code == 400
    assert response.json()[
        "detail"] == "status must be one of: all, active, resolved"


async def test_read_alerts_without_token(client):
    response = await client.get(ALERT_PREFIX)

    assert response.status_code in [401, 403]


async def test_resolve_alert_success(client, monkeypatch):
    alert_id = uuid4()

    async def fake_resolve_alert(session, alert_id_param):
        assert alert_id_param == alert_id

        return fake_alert_object(alert_id=alert_id)

    monkeypatch.setattr(
        f"{ALERT_PATH}.resolve_alert",
        fake_resolve_alert,
    )

    response = await client.patch(
        f"{ALERT_PREFIX}/{alert_id}/resolve"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["id"] == str(alert_id)
    assert data["purifier_name"] is None
    assert data["title"] == "High Turbidity"
    assert data["is_resolved"] is True
    assert data["resolved_at"] is not None


async def test_resolve_alert_not_found(client, monkeypatch):
    alert_id = uuid4()

    async def fake_resolve_alert(session, alert_id_param):
        raise ValueError("Alert not found")

    monkeypatch.setattr(
        f"{ALERT_PATH}.resolve_alert",
        fake_resolve_alert,
    )

    response = await client.patch(
        f"{ALERT_PREFIX}/{alert_id}/resolve"
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Alert not found"


async def test_active_alert_count_success(client, monkeypatch):
    async def fake_get_active_alert_count(session):
        return {
            "count": 3
        }

    monkeypatch.setattr(
        f"{ALERT_PATH}.get_active_alert_count",
        fake_get_active_alert_count,
    )

    response = await client.get(
        f"{ALERT_PREFIX}/active-count"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["count"] == 3
