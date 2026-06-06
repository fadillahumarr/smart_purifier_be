import pytest
from uuid import uuid4
from types import SimpleNamespace

from app.services import dashboard_service
from app.services.dashboard_service import (
    get_latest_status,
    get_global_dashboard_summary,
)


class FakeScalarResult:
    def __init__(self, items):
        self.items = items

    def all(self):
        return self.items


class FakeSession:
    def __init__(
        self,
        purifiers=None,
        latest_status=None,
        active_alerts=0,
    ):
        self.purifiers = purifiers or []
        self.latest_status = latest_status
        self.active_alerts = active_alerts
        self.scalar_calls = 0

    async def scalars(self, statement):
        return FakeScalarResult(self.purifiers)

    async def scalar(self, statement):
        self.scalar_calls += 1

        if self.scalar_calls == 1 and self.latest_status is not None:
            return self.latest_status

        return self.active_alerts


def fake_user():
    return SimpleNamespace(
        id=uuid4(),
    )


def fake_purifier():
    return SimpleNamespace(
        id=uuid4(),
    )


def fake_status(status="online"):
    return SimpleNamespace(
        status=status,
    )


@pytest.mark.asyncio
async def test_get_latest_status_success():
    status = fake_status("online")

    session = FakeSession(
        latest_status=status,
    )

    result = await get_latest_status(
        session=session,
        purifier_id=uuid4(),
    )

    assert result == status


@pytest.mark.asyncio
async def test_get_global_dashboard_summary_all_online(monkeypatch):
    purifiers = [
        fake_purifier(),
        fake_purifier(),
    ]

    async def fake_get_latest_status(session, purifier_id):
        return fake_status("online")

    monkeypatch.setattr(
        dashboard_service,
        "get_latest_status",
        fake_get_latest_status,
    )

    session = FakeSession(
        purifiers=purifiers,
        active_alerts=3,
    )

    result = await get_global_dashboard_summary(
        session=session,
        current_user=fake_user(),
    )

    assert result.total_purifiers == 2
    assert result.online_purifiers == 2
    assert result.offline_purifiers == 0
    assert result.active_alerts == 3


@pytest.mark.asyncio
async def test_get_global_dashboard_summary_some_offline(monkeypatch):
    purifiers = [
        fake_purifier(),
        fake_purifier(),
        fake_purifier(),
    ]

    statuses = [
        fake_status("online"),
        fake_status("offline"),
        None,
    ]

    async def fake_get_latest_status(session, purifier_id):
        return statuses.pop(0)

    monkeypatch.setattr(
        dashboard_service,
        "get_latest_status",
        fake_get_latest_status,
    )

    session = FakeSession(
        purifiers=purifiers,
        active_alerts=1,
    )

    result = await get_global_dashboard_summary(
        session=session,
        current_user=fake_user(),
    )

    assert result.total_purifiers == 3
    assert result.online_purifiers == 1
    assert result.offline_purifiers == 2
    assert result.active_alerts == 1


@pytest.mark.asyncio
async def test_get_global_dashboard_summary_no_purifiers(monkeypatch):
    async def fake_get_latest_status(session, purifier_id):
        return None

    monkeypatch.setattr(
        dashboard_service,
        "get_latest_status",
        fake_get_latest_status,
    )

    session = FakeSession(
        purifiers=[],
        active_alerts=0,
    )

    result = await get_global_dashboard_summary(
        session=session,
        current_user=fake_user(),
    )

    assert result.total_purifiers == 0
    assert result.online_purifiers == 0
    assert result.offline_purifiers == 0
    assert result.active_alerts == 0


@pytest.mark.asyncio
async def test_get_global_dashboard_summary_active_alerts_none(monkeypatch):
    purifiers = [
        fake_purifier(),
    ]

    async def fake_get_latest_status(session, purifier_id):
        return fake_status("online")

    monkeypatch.setattr(
        dashboard_service,
        "get_latest_status",
        fake_get_latest_status,
    )

    session = FakeSession(
        purifiers=purifiers,
        active_alerts=None,
    )

    result = await get_global_dashboard_summary(
        session=session,
        current_user=fake_user(),
    )

    assert result.total_purifiers == 1
    assert result.online_purifiers == 1
    assert result.offline_purifiers == 0
    assert result.active_alerts == 0
