from sqlmodel import SQLModel, Field

from app.models.base import UUIDPrimaryKeyModel, TimestampModel

class User(UUIDPrimaryKeyModel, TimestampModel, SQLModel, table=True):
    __tablename__ = "users"

    name: str = Field(max_length=100, nullable=False)
    email: str = Field(max_length=150, nullable=False, unique=True, index=True)
    password_hash: str = Field(nullable=False)