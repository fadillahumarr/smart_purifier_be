from datetime import datetime
from uuid import UUID

import sqlalchemy as sa
from sqlmodel import SQLModel, Field

from app.models.base import utc_now
from app.models.enums import DeviceStatus


class DeviceStatusLog(SQLModel, table=True):
    __tablename__ = "device_status_logs"

    id: int | None = Field(default=None, primary_key=True)
    water_purifier_id: UUID = Field(
        foreign_key="water_purifiers.id",
        nullable=False,
        index=True,
    )
    status: DeviceStatus = Field(
        sa_column=sa.Column(
            sa.Enum(DeviceStatus, name="device_status_enum"),
            nullable=False,
        )
    )
    message: str | None = Field(default=None)
    recorded_at: datetime = Field(
        default_factory=utc_now,
        sa_column=sa.Column(
            sa.DateTime(timezone=True),
            nullable=False,
        ),
    )
