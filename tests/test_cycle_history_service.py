import pytest
from uuid import uuid4
from datetime import datetime, timezone
from types import SimpleNamespace

from app.models.enums import CycleStatus
from app.services.cycle_history_service import (
    bool_to_label,
    make_cycle_code,
    get_cycle_history,
)


# pytestmark = pytest.mark.asyncio


class FakeResult:
    def __init__(self, rows=None):
        self._rows = rows or []

    def all(self):
        return self._rows


class FakeSession:
    def __init__(self, purifier=None, rows=None):
        self.purifier = purifier
        self.rows = rows or []
        self.got_model = None
        self.got_id = None

    async def get(self, model, object_id):
        self.got_model = model
        self.got_id = object_id
        return self.purifier

    async def execute(self, statement):
        return FakeResult(rows=self.rows)


def fake_purifier():
    return SimpleNamespace(
        id=uuid4(),
        name="LAB UNHAS",
    )


def fake_cycle_row(
    cycle_id=None,
    started_at=None,
    status=None,
    predicted=True,
    actual=False,
):
    return (
        cycle_id or uuid4(),
        started_at or datetime.now(timezone.utc),
        status or list(CycleStatus)[0],
        predicted,
        actual,
    )


def test_bool_to_label_clean():
    assert bool_to_label(True) == "Clean"


def test_bool_to_label_not_clean():
    assert bool_to_label(False) == "Not Clean"


def test_bool_to_label_none():
    assert bool_to_label(None) is None


def test_make_cycle_code():
    assert make_cycle_code(1) == "CYCLE-001"
    assert make_cycle_code(12) == "CYCLE-012"
    assert make_cycle_code(123) == "CYCLE-123"

@pytest.mark.asyncio
async def test_get_cycle_history_success():
    purifier_id = uuid4()

    row_1 = fake_cycle_row(
        predicted=True,
        actual=True,
    )

    row_2 = fake_cycle_row(
        predicted=False,
        actual=False,
    )

    session = FakeSession(
        purifier=fake_purifier(),
        rows=[
            row_1,
            row_2,
        ],
    )

    result = await get_cycle_history(
        session=session,
        purifier_id=purifier_id,
        limit=20,
    )

    assert result.purifier_id == purifier_id
    assert len(result.items) == 2

    assert result.items[0].cycle_code == "CYCLE-001"
    assert result.items[0].predicted == "Clean"
    assert result.items[0].actual == "Clean"

    assert result.items[1].cycle_code == "CYCLE-002"
    assert result.items[1].predicted == "Not Clean"
    assert result.items[1].actual == "Not Clean"

@pytest.mark.asyncio
async def test_get_cycle_history_with_none_prediction_and_actual():
    purifier_id = uuid4()

    row = fake_cycle_row(
        predicted=None,
        actual=None,
    )

    session = FakeSession(
        purifier=fake_purifier(),
        rows=[
            row,
        ],
    )

    result = await get_cycle_history(
        session=session,
        purifier_id=purifier_id,
        limit=5,
    )

    assert result.purifier_id == purifier_id
    assert len(result.items) == 1

    assert result.items[0].cycle_code == "CYCLE-001"
    assert result.items[0].predicted is None
    assert result.items[0].actual is None

@pytest.mark.asyncio
async def test_get_cycle_history_empty_items():
    purifier_id = uuid4()

    session = FakeSession(
        purifier=fake_purifier(),
        rows=[],
    )

    result = await get_cycle_history(
        session=session,
        purifier_id=purifier_id,
        limit=20,
    )

    assert result.purifier_id == purifier_id
    assert result.items == []

@pytest.mark.asyncio
async def test_get_cycle_history_purifier_not_found():
    session = FakeSession(
        purifier=None,
        rows=[],
    )

    with pytest.raises(ValueError) as exc:
        await get_cycle_history(
            session=session,
            purifier_id=uuid4(),
            limit=20,
        )

    assert str(exc.value) == "Purifier not found"
