import pytest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from app.models.enums import SensorType, TankType
from app.services.monitoring_service import (
    parse_datetime,
    sensor_unit,
    redis_tank_key,
    calculate_mixing_times,
    empty_metric,
    redis_sensor_metric,
)


def test_parse_datetime_none():
    assert parse_datetime(None) is None
    assert parse_datetime("") is None


def test_parse_datetime_datetime_object():
    now = datetime.now(timezone.utc)

    assert parse_datetime(now) == now


def test_parse_datetime_iso_z():
    result = parse_datetime("2026-06-01T10:00:00Z")

    assert result is not None
    assert result.tzinfo is not None


def test_parse_datetime_invalid():
    assert parse_datetime("invalid-date") is None


def test_sensor_unit():
    assert sensor_unit(SensorType.turbidity) == "NTU"
    assert sensor_unit(SensorType.tds) == "ppm"
    assert sensor_unit(SensorType.ph) == ""
    assert sensor_unit(SensorType.temperature) == "°C"
    assert sensor_unit(SensorType.water_volume) == "L"


def test_redis_tank_key():
    assert redis_tank_key(TankType.settling) == TankType.settling.value


def test_calculate_mixing_times_without_cycle():
    result = calculate_mixing_times(
        cycle=None,
        ai_decision=None,
    )

    assert result == (None, None)


def test_calculate_mixing_times_without_ai_decision():
    cycle = SimpleNamespace(
        mixing_started_at=datetime.now(timezone.utc),
    )

    result = calculate_mixing_times(
        cycle=cycle,
        ai_decision=None,
    )

    assert result == (None, None)


def test_calculate_mixing_times_without_mixing_started_at():
    cycle = SimpleNamespace(
        mixing_started_at=None,
    )

    ai_decision = SimpleNamespace(
        recommended_mixing_duration_seconds=300,
    )

    result = calculate_mixing_times(
        cycle=cycle,
        ai_decision=ai_decision,
    )

    assert result == (None, None)


def test_calculate_mixing_times_success():
    cycle = SimpleNamespace(
        mixing_started_at=datetime.now(timezone.utc),
    )

    ai_decision = SimpleNamespace(
        recommended_mixing_duration_seconds=300,
    )

    mixing_end_at, remaining = calculate_mixing_times(
        cycle=cycle,
        ai_decision=ai_decision,
    )

    assert mixing_end_at is not None
    assert isinstance(remaining, int)
    assert remaining >= 0


def test_empty_metric():
    result = empty_metric(SensorType.turbidity)

    assert result.value is None
    assert result.unit == "NTU"
    assert result.recorded_at is None


def test_redis_sensor_metric_success():
    data = {
        "turbidity": "4.5",
        "recorded_at": "2026-06-01T10:00:00Z",
    }

    result = redis_sensor_metric(
        data=data,
        sensor_type=SensorType.turbidity,
    )

    assert result.value == 4.5
    assert result.unit == "NTU"
    assert result.recorded_at is not None


def test_redis_sensor_metric_missing_value():
    result = redis_sensor_metric(
        data={},
        sensor_type=SensorType.turbidity,
    )

    assert result.value is None
    assert result.unit == "NTU"


def test_redis_sensor_metric_invalid_value():
    data = {
        "turbidity": "not-number",
        "recorded_at": "2026-06-01T10:00:00Z",
    }

    result = redis_sensor_metric(
        data=data,
        sensor_type=SensorType.turbidity,
    )

    assert result.value is None
    assert result.unit == "NTU"
