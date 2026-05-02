from datetime import datetime
from uuid import UUID

import sqlalchemy as sa
from sqlmodel import SQLModel, Field

from app.models.base import UUIDPrimaryKeyModel, utc_now
from app.models.enums import AlertSeverity


class Alert(UUIDPrimaryKeyModel, SQLModel, table=True):
    __tablename__ = "alerts"
    __table_args__ = (
        sa.Index(
            "idx_alerts_purifier_created",
            "water_purifier_id",
            sa.text("created_at desc"),
        ),
        sa.Index(
            "idx_alerts_unresolved",
            "is_resolved",
            sa.text("created_at desc"),
        ),
    )

    water_purifier_id: UUID = Field(
        sa_column=sa.Column(
            sa.ForeignKey("water_purifiers.id", ondelete="CASCADE"),
            nullable=False,
        )
    )

    purification_cycle_id: UUID | None = Field(
        default=None,
        sa_column=sa.Column(
            sa.ForeignKey("purification_cycles.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )

    alert_type: str = Field(
        max_length=50,
        nullable=False,
    )

    severity: AlertSeverity = Field(
        sa_column=sa.Column(
            sa.Enum(AlertSeverity, name="alert_severity_enum"),
            nullable=False,
        )
    )

    title: str = Field(
        max_length=150,
        nullable=False,
    )

    message: str | None = Field(
        default=None,
        sa_column=sa.Column(sa.Text, nullable=True),
    )

    is_resolved: bool = Field(
        default=False,
        nullable=False,
    )

    created_at: datetime = Field(
        default_factory=utc_now,
        sa_column=sa.Column(sa.DateTime(timezone=True), nullable=False),
    )

    resolved_at: datetime | None = Field(
        default=None,
        sa_column=sa.Column(sa.DateTime(timezone=True), nullable=True),
    )
