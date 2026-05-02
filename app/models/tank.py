from datetime import datetime
from uuid import UUID

import sqlalchemy as sa
from sqlmodel import SQLModel, Field

from app.models.base import UUIDPrimaryKeyModel, utc_now
from app.models.enums import TankType


class Tank(UUIDPrimaryKeyModel, SQLModel, table=True):
    __tablename__ = "tanks"
    __table_args__ = (
        sa.UniqueConstraint(
            "water_purifier_id",
            "tank_type",
            name="uq_tank_per_type",
        ),
    )

    water_purifier_id: UUID = Field(
        sa_column=sa.Column(
            sa.ForeignKey("water_purifiers.id", ondelete="CASCADE"),
            nullable=False,
        )
    )

    tank_type: TankType = Field(
        sa_column=sa.Column(
            sa.Enum(TankType, name="tank_type_enum"),
            nullable=False,
        )
    )

    name: str = Field(max_length=100, nullable=False)

    created_at: datetime = Field(
        default_factory=utc_now,
        sa_column=sa.Column(sa.DateTime(timezone=True), nullable=False),
    )
