"""
Face detection and recognition models.

Uses pgvector for efficient similarity search on face embeddings.
"""

import uuid
from datetime import datetime

from sqlalchemy import Float, ForeignKey, Integer, String, DateTime, Index
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class Face(Base, UUIDMixin, TimestampMixin):
    """
    Detected face in an asset.

    Stores bounding box coordinates and 512-dim embedding vector
    for face recognition/clustering.
    """
    __tablename__ = "faces"

    # Parent asset
    asset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("assets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Assigned person (nullable until clustered/assigned)
    person_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("people.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Bounding box (normalized 0-1 coordinates)
    bbox_x: Mapped[float] = mapped_column(Float, nullable=False)
    bbox_y: Mapped[float] = mapped_column(Float, nullable=False)
    bbox_width: Mapped[float] = mapped_column(Float, nullable=False)
    bbox_height: Mapped[float] = mapped_column(Float, nullable=False)

    # Face landmarks (5-point: left_eye, right_eye, nose, left_mouth, right_mouth)
    # Stored as flat array [x1, y1, x2, y2, ...]
    landmarks: Mapped[list[float] | None] = mapped_column(ARRAY(Float), nullable=True)

    # Detection confidence
    confidence: Mapped[float] = mapped_column(Float, nullable=False)

    # Face embedding (512-dim vector from ArcFace)
    # Using ARRAY instead of pgvector for compatibility
    # For production with many faces, migrate to pgvector
    embedding: Mapped[list[float] | None] = mapped_column(ARRAY(Float, dimensions=1), nullable=True)

    # Thumbnail path for face crop
    thumbnail_path: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Relationships
    asset = relationship("Asset", back_populates="faces")
    person = relationship("Person", back_populates="faces")

    __table_args__ = (
        Index("ix_faces_person_asset", "person_id", "asset_id"),
    )

    def __repr__(self) -> str:
        return f"<Face {self.id} asset={self.asset_id} person={self.person_id}>"


class Person(Base, UUIDMixin, TimestampMixin):
    """
    A recognized person (cluster of faces).

    Users can name people and merge duplicates.
    """
    __tablename__ = "people"

    # Owner of this person record
    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Display name (user-assigned)
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Representative face for avatar
    cover_face_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("faces.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Hidden from UI (user can hide people)
    is_hidden: Mapped[bool] = mapped_column(default=False)

    # Favorite for quick access
    is_favorite: Mapped[bool] = mapped_column(default=False)

    # Birth date (optional, for smart features)
    birth_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Face count (denormalized for performance)
    face_count: Mapped[int] = mapped_column(Integer, default=0)

    # For merging: points to the person this was merged into
    merged_into_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("people.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Relationships
    owner = relationship("User", back_populates="people")
    faces = relationship("Face", back_populates="person", foreign_keys=[Face.person_id])
    cover_face = relationship("Face", foreign_keys=[cover_face_id], post_update=True)

    def __repr__(self) -> str:
        return f"<Person {self.id} name={self.name}>"
