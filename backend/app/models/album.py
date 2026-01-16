"""
Album and sharing models.
"""

import uuid
from datetime import datetime
from enum import Enum

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text, DateTime, Enum as SQLEnum, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class AlbumType(str, Enum):
    """Types of albums."""
    STANDARD = "standard"  # Manual album
    SMART = "smart"        # Auto-populated by search criteria
    FAVORITES = "favorites"  # Special: user's favorites
    TRASH = "trash"        # Special: deleted items


class Album(Base, UUIDMixin, TimestampMixin):
    """
    User-created or smart album.
    """
    __tablename__ = "albums"

    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Album details
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    album_type: Mapped[AlbumType] = mapped_column(
        SQLEnum(AlbumType),
        default=AlbumType.STANDARD,
    )

    # Cover image
    cover_asset_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("assets.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Smart album: search criteria as JSON
    # e.g., {"people": ["uuid1"], "tags": ["beach"], "date_range": ["2024-01", "2024-06"]}
    smart_criteria: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Sort order
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    # Asset count (denormalized)
    asset_count: Mapped[int] = mapped_column(Integer, default=0)

    # Relationships
    owner = relationship("User", back_populates="albums")
    cover_asset = relationship("Asset", foreign_keys=[cover_asset_id])
    album_assets = relationship("AlbumAsset", back_populates="album", cascade="all, delete-orphan")
    shares = relationship("AlbumShare", back_populates="album", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Album {self.title} ({self.album_type})>"


class AlbumAsset(Base, UUIDMixin, TimestampMixin):
    """
    Association between albums and assets.
    """
    __tablename__ = "album_assets"

    album_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("albums.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    asset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("assets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Position in album (for manual ordering)
    position: Mapped[int] = mapped_column(Integer, default=0)

    # Added by (for shared albums)
    added_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Relationships
    album = relationship("Album", back_populates="album_assets")
    asset = relationship("Asset", back_populates="album_assets")
    added_by = relationship("User")

    __table_args__ = (
        UniqueConstraint("album_id", "asset_id", name="uq_album_asset"),
    )


class ShareType(str, Enum):
    """Types of sharing."""
    LINK = "link"      # Public link
    USER = "user"      # Shared with specific user
    FAMILY = "family"  # Family library


class AlbumShare(Base, UUIDMixin, TimestampMixin):
    """
    Sharing configuration for albums.
    """
    __tablename__ = "album_shares"

    album_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("albums.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    share_type: Mapped[ShareType] = mapped_column(SQLEnum(ShareType), nullable=False)

    # For user shares
    shared_with_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
    )

    # For link shares
    share_token: Mapped[str | None] = mapped_column(String(64), unique=True, nullable=True)
    link_password: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Permissions
    can_edit: Mapped[bool] = mapped_column(Boolean, default=False)
    can_add: Mapped[bool] = mapped_column(Boolean, default=False)
    can_download: Mapped[bool] = mapped_column(Boolean, default=True)

    # Expiration
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Access tracking
    view_count: Mapped[int] = mapped_column(Integer, default=0)
    last_accessed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    album = relationship("Album", back_populates="shares")
    shared_with = relationship("User")

    def __repr__(self) -> str:
        return f"<AlbumShare album={self.album_id} type={self.share_type}>"
