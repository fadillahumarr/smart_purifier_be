import pytest
import pytest_asyncio
from uuid import uuid4
from types import SimpleNamespace

from httpx import AsyncClient, ASGITransport

from app.main import app
from app.core.database import get_session


pytestmark = pytest.mark.asyncio(loop_scope="session")

BASE_URL = "http://test"
DEVICE_PREFIX = "/api/v1/devices"


@pytest_asyncio.fixture(scope="session")
async def client():
    transport = ASGITransport(app=app)

    async with AsyncClient(
        transport=transport,
        base_url=BASE_URL,
    ) as async_client:
        yield async_client


def make_unique_mac():
    unique = uuid4().hex[:6]

    return (
        f"AA:BB:CC:"
        f"{unique[0:2]}:"
        f"{unique[2:4]}:"
        f"{unique[4:6]}"
    )


def fake_purifier(
    mac_address=None,
    device_code="WP-TEST-001",
    mqtt_topic_base="smart-water/wp-test-001",
    firmware_version="v1.0",
):
    return SimpleNamespace(
        mac_address=mac_address or make_unique_mac(),
        device_code=device_code,
        mqtt_topic_base=mqtt_topic_base,
        firmware_version=firmware_version,
    )


class FakeSession:
    def __init__(self, purifier=None):
        self.purifier = purifier
        self.added_object = None
        self.committed = False
        self.refreshed_object = None

    async def scalar(self, statement):
        return self.purifier

    def add(self, obj):
        self.added_object = obj

    async def commit(self):
        self.committed = True

    async def refresh(self, obj):
        self.refreshed_object = obj


async def test_provision_registered_device_success(client):
    mac_address = make_unique_mac()

    purifier = fake_purifier(
        mac_address=mac_address,
        device_code="WP-TEST-001",
        mqtt_topic_base="smart-water/wp-test-001",
        firmware_version="v1.0",
    )

    fake_session = FakeSession(purifier=purifier)

    async def fake_get_session():
        yield fake_session

    app.dependency_overrides[get_session] = fake_get_session

    try:
        response = await client.post(
            f"{DEVICE_PREFIX}/provision",
            json={
                "mac_address": mac_address,
                "firmware_version": "v1.1",
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200

    data = response.json()

    assert data["device_code"] == "WP-TEST-001"
    assert data["mqtt_topic_base"] == "smart-water/wp-test-001"
    assert data["mqtt_host"] == "192.168.10.197"
    assert data["mqtt_port"] == 1883

    assert purifier.firmware_version == "v1.1"
    assert fake_session.added_object == purifier
    assert fake_session.committed is True
    assert fake_session.refreshed_object == purifier


async def test_provision_unregistered_device_failed(client):
    fake_session = FakeSession(purifier=None)

    async def fake_get_session():
        yield fake_session

    app.dependency_overrides[get_session] = fake_get_session

    try:
        response = await client.post(
            f"{DEVICE_PREFIX}/provision",
            json={
                "mac_address": make_unique_mac(),
                "firmware_version": "v1.0",
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404
    assert response.json()["detail"] == "Device is not registered"


async def test_provision_without_firmware_version_success(client):
    mac_address = make_unique_mac()

    purifier = fake_purifier(
        mac_address=mac_address,
        device_code="WP-TEST-002",
        mqtt_topic_base="smart-water/wp-test-002",
        firmware_version="v1.0",
    )

    fake_session = FakeSession(purifier=purifier)

    async def fake_get_session():
        yield fake_session

    app.dependency_overrides[get_session] = fake_get_session

    try:
        response = await client.post(
            f"{DEVICE_PREFIX}/provision",
            json={
                "mac_address": mac_address,
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200

    data = response.json()

    assert data["device_code"] == "WP-TEST-002"
    assert data["mqtt_topic_base"] == "smart-water/wp-test-002"
    assert data["mqtt_host"] == "192.168.10.197"
    assert data["mqtt_port"] == 1883

    assert purifier.firmware_version == "v1.0"
    assert fake_session.committed is False
