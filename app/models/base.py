from datetime import datetime, timezone
from uuid import UUID, uuid4

import sqlalchemy as sa
from sqlmodel import Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)

class UUIDPrimaryKeyModel:
    id: UUID = Field(default_factory=uuid4, primary_key=True)

class TimestampModel:
    created_at: datetime = Field(
        default_factory=utc_now,
        sa_type=sa.DateTime(timezone=True),
        nullable=False,
    )
    updated_at: datetime = Field(
        default_factory=utc_now,
        sa_type=sa.DateTime(timezone=True),
        nullable=False,
    )