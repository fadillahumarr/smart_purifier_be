from uuid import UUID

from sqlmodel import SQLModel, Field

from app.models.base import UUIDPrimaryKeyModel, TimestampModel


class WaterPurifier(UUIDPrimaryKeyModel, TimestampModel, SQLModel, table=True):
    __tablename__ = "water_purifiers"

    user_id: UUID = Field(
        foreign_key="users.id",
        nullable=False,
        index=True,
    )
    name: str = Field(max_length=100, nullable=False)
    location: str | None = Field(default=None, max_length=150)
    mac_address: str | None = Field(
        default=None,
        max_length=50,
        index=True,
        unique=True,
    )
    device_code: str = Field(max_length=100, nullable=False, unique=True)
    mqtt_topic_base: str = Field(max_length=150, nullable=False, unique=True)
    firmware_version: str | None = Field(default=None, max_length=50)
