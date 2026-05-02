from datetime import datetime
from enum import Enum
from uuid import UUID

import sqlalchemy as sa
from sqlmodel import SQLModel, Field

from app.models.base import utc_now
from app.models.enums import SnapshotType


class SensorSnapshot(SQLModel, table=True):
    __tablename__ = "sensor_snapshots"

    __table_args__ = (
        sa.Index(
            "idx_sensor_snapshots_purifier_type_recorded",
            "water_purifier_id",
            "snapshot_type",
            sa.text("recorded_at DESC"),
        ),
        sa.Index(
            "idx_sensor_snapshots_tank_type_recorded",
            "tank_id",
            "snapshot_type",
            sa.text("recorded_at DESC"),
        ),
        sa.Index(
            "idx_sensor_snapshots_cycle_type",
            "cycle_id",
            "snapshot_type",
        ),
    )

    id: int | None = Field(default=None, primary_key=True)

    water_purifier_id: UUID = Field(
        foreign_key="water_purifiers.id",
        nullable=False,
        index=True,
    )

    tank_id: UUID = Field(
        foreign_key="tanks.id",
        nullable=False,
        index=True,
    )

    cycle_id: UUID | None = Field(
        default=None,
        foreign_key="purification_cycles.id",
        index=True,
    )

    snapshot_type: SnapshotType = Field(
        sa_column=sa.Column(
            sa.Enum(SnapshotType, name="snapshot_type_enum"),
            nullable=False,
            index=True,
        )
    )

    tds: float | None = Field(default=None)
    turbidity: float | None = Field(default=None)
    ph: float | None = Field(default=None)
    temperature: float | None = Field(default=None)
    water_volume: float | None = Field(default=None)

    recorded_at: datetime = Field(
        default_factory=utc_now,
        sa_column=sa.Column(
            sa.DateTime(timezone=True),
            nullable=False,
        ),
    )