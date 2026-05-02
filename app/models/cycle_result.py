from datetime import datetime
from uuid import UUID

import sqlalchemy as sa
from sqlmodel import SQLModel, Field

from app.models.base import UUIDPrimaryKeyModel, utc_now


class CycleResult(UUIDPrimaryKeyModel, SQLModel, table=True):
    __tablename__ = "cycle_results"

    purification_cycle_id: UUID = Field(
        sa_column=sa.Column(
            sa.ForeignKey("purification_cycles.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        )
    )

    final_tds: float | None = Field(
        default=None,
        sa_column=sa.Column(sa.Numeric(12, 4), nullable=True),
    )
    final_turbidity: float | None = Field(
        default=None,
        sa_column=sa.Column(sa.Numeric(12, 4), nullable=True),
    )
    final_ph: float | None = Field(
        default=None,
        sa_column=sa.Column(sa.Numeric(12, 4), nullable=True),
    )

    is_clean_water: bool = Field(nullable=False)

    created_at: datetime = Field(
        default_factory=utc_now,
        sa_type=sa.DateTime(timezone=True),
        nullable=False,
    )
