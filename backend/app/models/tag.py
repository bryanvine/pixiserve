"""
Tag models for objects, scenes, and manual labels.
"""

import uuid
from enum import Enum

from sqlalchemy import Float, ForeignKey, Integer, String, Enum as SQLEnum, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class TagType(str, Enum):
    """Types of tags that can be applied to assets."""
    OBJECT = "object"      # Detected objects (car, dog, tree)
    SCENE = "scene"        # Scene classification (beach, mountain, indoor)
    MANUAL = "manual"      # User-added tags
    COLOR = "color"        # Dominant colors
    TEXT = "text"          # OCR detected text


class Tag(Base, UUIDMixin, TimestampMixin):
    """
    Reusable tag definitions.

    Tags are shared across users for consistency (e.g., "dog" is same tag for all).
    """
    __tablename__ = "tags"

    # Tag name (lowercase, normalized)
    name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    # Tag type
    tag_type: Mapped[TagType] = mapped_column(SQLEnum(TagType), nullable=False)

    # Parent tag for hierarchy (e.g., "golden retriever" -> "dog" -> "animal")
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tags.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Usage count (denormalized for popularity sorting)
    usage_count: Mapped[int] = mapped_column(Integer, default=0)

    # Relationships
    parent = relationship("Tag", remote_side="Tag.id", back_populates="children")
    children = relationship("Tag", back_populates="parent")

    __table_args__ = (
        UniqueConstraint("name", "tag_type", name="uq_tag_name_type"),
    )

    def __repr__(self) -> str:
        return f"<Tag {self.name} ({self.tag_type})>"


class AssetTag(Base, UUIDMixin, TimestampMixin):
    """
    Association between assets and tags with confidence scores.
    """
    __tablename__ = "asset_tags"

    asset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("assets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    tag_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tags.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ML confidence (1.0 for manual tags)
    confidence: Mapped[float] = mapped_column(Float, default=1.0)

    # Bounding box for object tags (normalized 0-1)
    bbox_x: Mapped[float | None] = mapped_column(Float, nullable=True)
    bbox_y: Mapped[float | None] = mapped_column(Float, nullable=True)
    bbox_width: Mapped[float | None] = mapped_column(Float, nullable=True)
    bbox_height: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Source of tag (model name or "user")
    source: Mapped[str] = mapped_column(String(50), default="user")

    # Relationships
    asset = relationship("Asset", back_populates="tags")
    tag = relationship("Tag")

    __table_args__ = (
        UniqueConstraint("asset_id", "tag_id", name="uq_asset_tag"),
    )

    def __repr__(self) -> str:
        return f"<AssetTag asset={self.asset_id} tag={self.tag_id}>"
