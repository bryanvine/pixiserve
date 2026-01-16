"""
Device model for mobile sync.
"""

import uuid
from datetime import datetime
from enum import Enum

from sqlalchemy import Boolean, ForeignKey, Integer, String, DateTime, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class DeviceType(str, Enum):
    """Types of sync devices."""
    ANDROID = "android"
    IOS = "ios"
    WEB = "web"
    DESKTOP = "desktop"


class Device(Base, UUIDMixin, TimestampMixin):
    """
    Registered sync device.

    Each device maintains its own sync cursor for incremental sync.
    """
    __tablename__ = "devices"

    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Device identification
    device_name: Mapped[str] = mapped_column(String(255), nullable=False)
    device_type: Mapped[DeviceType] = mapped_column(SQLEnum(DeviceType), nullable=False)
    device_id: Mapped[str] = mapped_column(String(255), nullable=False)  # Unique device identifier

    # Sync state
    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    sync_cursor: Mapped[str | None] = mapped_column(String(100), nullable=True)  # Timestamp or ID

    # Upload stats
    total_uploaded: Mapped[int] = mapped_column(Integer, default=0)
    total_bytes_uploaded: Mapped[int] = mapped_column(Integer, default=0)

    # Device status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    push_token: Mapped[str | None] = mapped_column(String(500), nullable=True)  # For notifications

    # App version
    app_version: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Relationships
    owner = relationship("User", back_populates="devices")

    def __repr__(self) -> str:
        return f"<Device {self.device_name} ({self.device_type})>"
