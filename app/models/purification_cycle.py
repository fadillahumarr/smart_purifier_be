from datetime import datetime
from uuid import UUID

import sqlalchemy as sa
from sqlmodel import SQLModel, Field

from app.models.base import UUIDPrimaryKeyModel, utc_now
from app.models.enums import CycleStatus, CycleStage


class PurificationCycle(UUIDPrimaryKeyModel, SQLModel, table=True):
    __tablename__ = "purification_cycles"
    __table_args__ = (
        sa.Index(
            "idx_purification_cycles_purifier_started",
            "water_purifier_id",
            sa.desc(sa.column("started_at")),
        ),
    )

    water_purifier_id: UUID = Field(
        sa_column=sa.Column(
            sa.ForeignKey("water_purifiers.id", ondelete="CASCADE"),
            nullable=False,
        )
    )

    started_at: datetime = Field(
        default_factory=utc_now,
        sa_column=sa.Column(sa.DateTime(timezone=True), nullable=False),
    )

    mixing_started_at: datetime | None = Field(
        default=None,
        sa_column=sa.Column(sa.DateTime(timezone=True), nullable=True),
    )

    settled_at: datetime | None = Field(
        default=None,
        sa_column=sa.Column(sa.DateTime(timezone=True), nullable=True),
    )

    finished_at: datetime | None = Field(
        default=None,
        sa_column=sa.Column(sa.DateTime(timezone=True), nullable=True),
    )

    current_stage: CycleStage | None = Field(
        default=None,
        sa_column=sa.Column(
            sa.Enum(CycleStage, name="cycle_stage_enum"),
            nullable=True,
        ),
    )

    status: CycleStatus = Field(
        default=CycleStatus.running,
        sa_column=sa.Column(
            sa.Enum(CycleStatus, name="cycle_status_enum"),
            nullable=False,
            server_default="running",
        ),
    )

    notes: str | None = Field(
        default=None,
        sa_column=sa.Column(sa.Text, nullable=True),
    )
