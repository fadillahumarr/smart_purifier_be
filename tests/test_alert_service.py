import pytest
from uuid import uuid4
from datetime import datetime, timezone
from types import SimpleNamespace

from app.models.enums import AlertSeverity
from app.services.alert_service import (
    list_alerts,
    resolve_alert,
    get_active_alert_count,
)


pytestmark = pytest.mark.asyncio


class FakeResult:
    def __init__(self, rows=None, row=None):
        self._rows = rows or []
        self._row = row

    def all(self):
        return self._rows

    def one_or_none(self):
        return self._row


class FakeSession:
    def __init__(self, rows=None, row=None, scalar_value=0):
        self.rows = rows or []
        self.row = row
        self.scalar_value = scalar_value
        self.committed = False
        self.refreshed_object = None

    async def execute(self, statement):
        return FakeResult(
            rows=self.rows,
            row=self.row,
        )

    async def scalar(self, statement):
        return self.scalar_value

    async def commit(self):
        self.committed = True

    async def refresh(self, obj):
        self.refreshed_object = obj


def fake_alert(
    is_resolved=False,
    severity=AlertSeverity.warning,
):
    return SimpleNamespace(
        id=uuid4(),
        water_purifier_id=uuid4(),
        purification_cycle_id=None,
        alert_type="water_quality",
        severity=severity,
        title="High Turbidity",
        message="Turbidity value is too high",
        is_resolved=is_resolved,
        created_at=datetime.now(timezone.utc),
        resolved_at=None,
    )


async def test_list_alerts_success():
    alert = fake_alert(is_resolved=False)

    session = FakeSession(
        rows=[
            (alert, "LAB UNHAS")
        ]
    )

    result = await list_alerts(
        session=session,
        user_id=uuid4(),
    )

    assert len(result.items) == 1

    item = result.items[0]

    assert item.id == alert.id
    assert item.purifier_name == "LAB UNHAS"
    assert item.title == "High Turbidity"
    assert item.is_resolved is False


async def test_list_alerts_with_active_filter():
    alert = fake_alert(is_resolved=False)

    session = FakeSession(
        rows=[
            (alert, "LAB UNHAS")
        ]
    )

    result = await list_alerts(
        session=session,
        user_id=uuid4(),
        status_filter="active",
    )

    assert len(result.items) == 1
    assert result.items[0].is_resolved is False


async def test_list_alerts_with_resolved_filter():
    alert = fake_alert(is_resolved=True)

    session = FakeSession(
        rows=[
            (alert, "LAB UNHAS")
        ]
    )

    result = await list_alerts(
        session=session,
        user_id=uuid4(),
        status_filter="resolved",
    )

    assert len(result.items) == 1
    assert result.items[0].is_resolved is True


async def test_list_alerts_with_severity_filter():
    alert = fake_alert(
        is_resolved=False,
        severity=AlertSeverity.warning,
    )

    session = FakeSession(
        rows=[
            (alert, "LAB UNHAS")
        ]
    )

    result = await list_alerts(
        session=session,
        user_id=uuid4(),
        severity=AlertSeverity.warning,
    )

    assert len(result.items) == 1
    assert result.items[0].severity == AlertSeverity.warning


async def test_list_alerts_with_purifier_filter():
    purifier_id = uuid4()

    alert = fake_alert(is_resolved=False)
    alert.water_purifier_id = purifier_id

    session = FakeSession(
        rows=[
            (alert, "LAB UNHAS")
        ]
    )

    result = await list_alerts(
        session=session,
        user_id=uuid4(),
        purifier_id=purifier_id,
    )

    assert len(result.items) == 1
    assert result.items[0].water_purifier_id == purifier_id


async def test_resolve_alert_success():
    alert = fake_alert(is_resolved=False)

    session = FakeSession(
        row=(alert, "LAB UNHAS")
    )

    result = await resolve_alert(
        session=session,
        alert_id=alert.id,
        user_id=uuid4(),
    )

    assert result.id == alert.id
    assert result.purifier_name == "LAB UNHAS"
    assert result.is_resolved is True
    assert result.resolved_at is not None

    assert session.committed is True
    assert session.refreshed_object == alert


async def test_resolve_alert_already_resolved():
    resolved_at = datetime.now(timezone.utc)

    alert = fake_alert(is_resolved=True)
    alert.resolved_at = resolved_at

    session = FakeSession(
        row=(alert, "LAB UNHAS")
    )

    result = await resolve_alert(
        session=session,
        alert_id=alert.id,
        user_id=uuid4(),
    )

    assert result.is_resolved is True
    assert result.resolved_at == resolved_at

    assert session.committed is True
    assert session.refreshed_object == alert


async def test_resolve_alert_not_found():
    session = FakeSession(row=None)

    with pytest.raises(ValueError) as exc:
        await resolve_alert(
            session=session,
            alert_id=uuid4(),
            user_id=uuid4(),
        )

    assert str(exc.value) == "Alert not found"


async def test_get_active_alert_count_success():
    session = FakeSession(
        scalar_value=3,
    )

    result = await get_active_alert_count(
        session=session,
        user_id=uuid4(),
    )

    assert result.count == 3


async def test_get_active_alert_count_zero_when_none():
    session = FakeSession(
        scalar_value=None,
    )

    result = await get_active_alert_count(
        session=session,
        user_id=uuid4(),
    )

    assert result.count == 0
