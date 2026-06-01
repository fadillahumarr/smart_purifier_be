import pytest
import pytest_asyncio
from uuid import uuid4
from datetime import datetime, timezone

from httpx import AsyncClient, ASGITransport

from app.main import app
from app.models.enums import DeviceStatus


pytestmark = pytest.mark.asyncio(loop_scope="session")

BASE_URL = "http://test"
PURIFIER_PREFIX = "/api/v1/purifiers"
MONITORING_PATH = "app.api.v1.endpoints.monitoring"


@pytest_asyncio.fixture(scope="session")
async def client():
    transport = ASGITransport(app=app)

    async with AsyncClient(
        transport=transport,
        base_url=BASE_URL,
    ) as async_client:
        yield async_client


def fake_device_status():
    return {
        "is_live": True,
        "status": list(DeviceStatus)[0],
        "message": "Device is online",
        "recorded_at": datetime.now(timezone.utc),
    }


def fake_metric(value, unit):
    return {
        "value": value,
        "unit": unit,
        "recorded_at": datetime.now(timezone.utc),
    }


def fake_summary_response(purifier_id):
    return {
        "purifier": {
            "id": purifier_id,
            "name": "Smart Purifier Test",
            "location": "Lab Testing",
            "device_code": "DEVICE-TEST",
            "firmware_version": "1.0.0",
        },
        "device_status": fake_device_status(),
        "initial_raw_snapshot": {
            "tds": 150.5,
            "turbidity": 5.2,
            "ph": 7.1,
            "temperature": 28.0,
            "water_volume": 10.0,
            "recorded_at": datetime.now(timezone.utc),
        },
        "current_cycle": None,
        "ai_decision": None,
        "latest_result": None,
    }


def fake_realtime_response(purifier_id):
    return {
        "purifier_id": purifier_id,
        "device_status": fake_device_status(),
        "settling_realtime": {
            "turbidity": fake_metric(1.2, "NTU"),
            "tds": fake_metric(80.5, "ppm"),
            "ph": fake_metric(7.0, "pH"),
            "temperature": fake_metric(28.0, "°C"),
            "water_volume": fake_metric(8.5, "L"),
        },
        "settling_trend": [
            {
                "time": datetime.now(timezone.utc),
                "tds": 80.5,
                "turbidity": 1.2,
                "ph": 7.0,
                "temperature": 28.0,
                "water_volume": 8.5,
            }
        ],
    }


async def test_monitoring_summary_success(client, monkeypatch):
    purifier_id = uuid4()

    async def fake_get_monitoring_summary(session, purifier_id_param):
        assert purifier_id_param == purifier_id
        return fake_summary_response(purifier_id)

    monkeypatch.setattr(
        f"{MONITORING_PATH}.get_monitoring_summary",
        fake_get_monitoring_summary,
    )

    response = await client.get(
        f"{PURIFIER_PREFIX}/{purifier_id}/monitoring/summary"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["purifier"]["id"] == str(purifier_id)
    assert data["purifier"]["name"] == "Smart Purifier Test"
    assert data["device_status"]["is_live"] is True
    assert data["initial_raw_snapshot"]["tds"] == 150.5
    assert data["current_cycle"] is None
    assert data["ai_decision"] is None
    assert data["latest_result"] is None


async def test_monitoring_summary_not_found(client, monkeypatch):
    purifier_id = uuid4()

    async def fake_get_monitoring_summary(session, purifier_id_param):
        raise ValueError("Purifier not found")

    monkeypatch.setattr(
        f"{MONITORING_PATH}.get_monitoring_summary",
        fake_get_monitoring_summary,
    )

    response = await client.get(
        f"{PURIFIER_PREFIX}/{purifier_id}/monitoring/summary"
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Purifier not found"


async def test_monitoring_realtime_success(client, monkeypatch):
    purifier_id = uuid4()

    async def fake_get_monitoring_realtime(
        session,
        purifier_id_param,
        trend_minutes,
    ):
        assert purifier_id_param == purifier_id
        assert trend_minutes == 5
        return fake_realtime_response(purifier_id)

    monkeypatch.setattr(
        f"{MONITORING_PATH}.get_monitoring_realtime",
        fake_get_monitoring_realtime,
    )

    response = await client.get(
        f"{PURIFIER_PREFIX}/{purifier_id}/monitoring/realtime"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["purifier_id"] == str(purifier_id)
    assert data["device_status"]["is_live"] is True
    assert data["settling_realtime"]["tds"]["value"] == 80.5
    assert data["settling_realtime"]["turbidity"]["unit"] == "NTU"
    assert isinstance(data["settling_trend"], list)
    assert len(data["settling_trend"]) == 1


async def test_monitoring_realtime_with_trend_minutes(client, monkeypatch):
    purifier_id = uuid4()

    async def fake_get_monitoring_realtime(
        session,
        purifier_id_param,
        trend_minutes,
    ):
        assert purifier_id_param == purifier_id
        assert trend_minutes == 10
        return fake_realtime_response(purifier_id)

    monkeypatch.setattr(
        f"{MONITORING_PATH}.get_monitoring_realtime",
        fake_get_monitoring_realtime,
    )

    response = await client.get(
        f"{PURIFIER_PREFIX}/{purifier_id}/monitoring/realtime?trend_minutes=10"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["purifier_id"] == str(purifier_id)
    assert data["settling_realtime"]["ph"]["value"] == 7.0


async def test_monitoring_realtime_not_found(client, monkeypatch):
    purifier_id = uuid4()

    async def fake_get_monitoring_realtime(
        session,
        purifier_id_param,
        trend_minutes,
    ):
        raise ValueError("Purifier not found")

    monkeypatch.setattr(
        f"{MONITORING_PATH}.get_monitoring_realtime",
        fake_get_monitoring_realtime,
    )

    response = await client.get(
        f"{PURIFIER_PREFIX}/{purifier_id}/monitoring/realtime"
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Purifier not found"


async def test_monitoring_realtime_invalid_trend_minutes_less_than_1(client):
    purifier_id = uuid4()

    response = await client.get(
        f"{PURIFIER_PREFIX}/{purifier_id}/monitoring/realtime?trend_minutes=0"
    )

    assert response.status_code == 422


async def test_monitoring_realtime_invalid_trend_minutes_more_than_30(client):
    purifier_id = uuid4()

    response = await client.get(
        f"{PURIFIER_PREFIX}/{purifier_id}/monitoring/realtime?trend_minutes=31"
    )

    assert response.status_code == 422
