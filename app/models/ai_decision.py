from datetime import datetime
from uuid import UUID

import sqlalchemy as sa
from sqlmodel import SQLModel, Field

from app.models.base import UUIDPrimaryKeyModel, utc_now


class AIDecision(UUIDPrimaryKeyModel, SQLModel, table=True):
    __tablename__ = "ai_decisions"

    purification_cycle_id: UUID = Field(
        sa_column=sa.Column(
            sa.ForeignKey("purification_cycles.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        )
    )

    model_type: str = Field(max_length=50, nullable=False)
    model_version: str = Field(max_length=50, nullable=False)

    raw_tds: float = Field(
        sa_column=sa.Column(sa.Numeric(12, 4), nullable=False)
    )
    raw_turbidity: float = Field(
        sa_column=sa.Column(sa.Numeric(12, 4), nullable=False)
    )
    raw_water_volume: float = Field(
        sa_column=sa.Column(sa.Numeric(12, 4), nullable=False)
    )
    raw_temperature: float = Field(
        sa_column=sa.Column(sa.Numeric(12, 4), nullable=False)
    )
    raw_ph: float = Field(
        sa_column=sa.Column(sa.Numeric(12, 4), nullable=False)
    )

    recommended_moringa_dose_mg_per_l: int = Field(nullable=False)
    recommended_mixing_duration_seconds: int = Field(nullable=False)

    predicted_is_clean_water: bool = Field(nullable=False)

    created_at: datetime = Field(
        default_factory=utc_now,
        sa_type=sa.DateTime(timezone=True),
        nullable=False,
    )
