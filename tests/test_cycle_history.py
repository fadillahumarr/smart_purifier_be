import pytest
import pytest_asyncio
from uuid import uuid4
from datetime import datetime, timezone

from httpx import AsyncClient, ASGITransport

from app.main import app
from app.models.enums import CycleStatus


pytestmark = pytest.mark.asyncio(loop_scope="session")

BASE_URL = "http://test"
PURIFIER_PREFIX = "/api/v1/purifiers"
CYCLE_HISTORY_PATH = "app.api.v1.endpoints.cycle_history"


@pytest_asyncio.fixture(scope="session")
async def client():
    transport = ASGITransport(app=app)

    async with AsyncClient(
        transport=transport,
        base_url=BASE_URL,
    ) as async_client:
        yield async_client


def fake_cycle_history_response(purifier_id):
    return {
        "purifier_id": purifier_id,
        "items": [
            {
                "cycle_uuid": uuid4(),
                "cycle_code": "CYCLE-001",
                "started_at": datetime.now(timezone.utc),
                "status": list(CycleStatus)[0],
                "predicted": "Clean Water",
                "actual": "Clean Water",
            }
        ],
    }


async def test_cycle_history_success(client, monkeypatch):
    expected_purifier_id = uuid4()

    async def fake_get_cycle_history(session, purifier_id, limit):
        assert purifier_id == expected_purifier_id
        assert limit == 20

        return fake_cycle_history_response(purifier_id)

    monkeypatch.setattr(
        f"{CYCLE_HISTORY_PATH}.get_cycle_history",
        fake_get_cycle_history,
    )

    response = await client.get(
        f"{PURIFIER_PREFIX}/{expected_purifier_id}/cycles/history"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["purifier_id"] == str(expected_purifier_id)
    assert isinstance(data["items"], list)
    assert len(data["items"]) == 1


async def test_cycle_history_with_limit(client, monkeypatch):
    purifier_id = uuid4()

    async def fake_get_cycle_history(session, purifier_id, limit):
        assert limit == 5

        return fake_cycle_history_response(purifier_id)

    monkeypatch.setattr(
        f"{CYCLE_HISTORY_PATH}.get_cycle_history",
        fake_get_cycle_history,
    )

    response = await client.get(
        f"{PURIFIER_PREFIX}/{purifier_id}/cycles/history?limit=5"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["purifier_id"] == str(purifier_id)
    assert len(data["items"]) == 1


async def test_cycle_history_empty_items(client, monkeypatch):
    purifier_id = uuid4()

    async def fake_get_cycle_history(session, purifier_id, limit):
        assert limit == 20

        return {
            "purifier_id": purifier_id,
            "items": [],
        }

    monkeypatch.setattr(
        f"{CYCLE_HISTORY_PATH}.get_cycle_history",
        fake_get_cycle_history,
    )

    response = await client.get(
        f"{PURIFIER_PREFIX}/{purifier_id}/cycles/history"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["purifier_id"] == str(purifier_id)
    assert data["items"] == []


async def test_cycle_history_purifier_not_found(client, monkeypatch):
    purifier_id = uuid4()

    async def fake_get_cycle_history(session, purifier_id, limit):
        raise ValueError("Purifier not found")

    monkeypatch.setattr(
        f"{CYCLE_HISTORY_PATH}.get_cycle_history",
        fake_get_cycle_history,
    )

    response = await client.get(
        f"{PURIFIER_PREFIX}/{purifier_id}/cycles/history"
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Purifier not found"


async def test_cycle_history_invalid_limit_less_than_1(client):
    purifier_id = uuid4()

    response = await client.get(
        f"{PURIFIER_PREFIX}/{purifier_id}/cycles/history?limit=0"
    )

    assert response.status_code == 422


async def test_cycle_history_invalid_limit_more_than_100(client):
    purifier_id = uuid4()

    response = await client.get(
        f"{PURIFIER_PREFIX}/{purifier_id}/cycles/history?limit=101"
    )

    assert response.status_code == 422
