"""
People (recognized faces) API endpoints.
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import CurrentUser
from app.database import get_db
from app.models import Person, Face, Asset

router = APIRouter()


class PersonResponse(BaseModel):
    """Person response model."""
    id: UUID
    name: str | None
    face_count: int
    is_hidden: bool
    is_favorite: bool
    thumbnail_url: str | None

    model_config = {"from_attributes": True}


class PersonListResponse(BaseModel):
    """Paginated person list response."""
    items: list[PersonResponse]
    total: int


class PersonUpdate(BaseModel):
    """Person update request."""
    name: str | None = None
    is_hidden: bool | None = None
    is_favorite: bool | None = None


class PersonMergeRequest(BaseModel):
    """Request to merge people."""
    merge_into_id: UUID


class PersonAssetsResponse(BaseModel):
    """Response with assets containing a person."""
    person_id: UUID
    asset_ids: list[UUID]
    total: int


@router.get("", response_model=PersonListResponse)
async def list_people(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    include_hidden: bool = False,
    favorites_only: bool = False,
):
    """List recognized people for the current user."""
    query = (
        select(Person)
        .where(Person.owner_id == current_user.id)
        .where(Person.merged_into_id.is_(None))  # Exclude merged people
        .where(Person.face_count > 0)  # Exclude empty people
    )

    if not include_hidden:
        query = query.where(Person.is_hidden.is_(False))

    if favorites_only:
        query = query.where(Person.is_favorite.is_(True))

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query)

    # Paginate and order by face count
    query = (
        query
        .order_by(Person.is_favorite.desc(), Person.face_count.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )

    result = await db.execute(query)
    people = result.scalars().all()

    items = []
    for person in people:
        thumbnail_url = None
        if person.cover_face_id:
            # Get thumbnail URL from cover face
            face = await db.get(Face, person.cover_face_id)
            if face and face.thumbnail_path:
                thumbnail_url = f"/api/v1/faces/{face.id}/thumbnail"

        items.append(PersonResponse(
            id=person.id,
            name=person.name,
            face_count=person.face_count,
            is_hidden=person.is_hidden,
            is_favorite=person.is_favorite,
            thumbnail_url=thumbnail_url,
        ))

    return PersonListResponse(items=items, total=total)


@router.get("/{person_id}", response_model=PersonResponse)
async def get_person(
    person_id: UUID,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Get a specific person."""
    person = await db.get(Person, person_id)

    if not person or person.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Person not found")

    thumbnail_url = None
    if person.cover_face_id:
        face = await db.get(Face, person.cover_face_id)
        if face and face.thumbnail_path:
            thumbnail_url = f"/api/v1/faces/{face.id}/thumbnail"

    return PersonResponse(
        id=person.id,
        name=person.name,
        face_count=person.face_count,
        is_hidden=person.is_hidden,
        is_favorite=person.is_favorite,
        thumbnail_url=thumbnail_url,
    )


@router.patch("/{person_id}", response_model=PersonResponse)
async def update_person(
    person_id: UUID,
    update: PersonUpdate,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Update a person (name, hidden status, favorite)."""
    person = await db.get(Person, person_id)

    if not person or person.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Person not found")

    if update.name is not None:
        person.name = update.name
    if update.is_hidden is not None:
        person.is_hidden = update.is_hidden
    if update.is_favorite is not None:
        person.is_favorite = update.is_favorite

    await db.commit()
    await db.refresh(person)

    thumbnail_url = None
    if person.cover_face_id:
        face = await db.get(Face, person.cover_face_id)
        if face and face.thumbnail_path:
            thumbnail_url = f"/api/v1/faces/{face.id}/thumbnail"

    return PersonResponse(
        id=person.id,
        name=person.name,
        face_count=person.face_count,
        is_hidden=person.is_hidden,
        is_favorite=person.is_favorite,
        thumbnail_url=thumbnail_url,
    )


@router.post("/{person_id}/merge", response_model=PersonResponse)
async def merge_people(
    person_id: UUID,
    request: PersonMergeRequest,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Merge another person into this one."""
    person_keep = await db.get(Person, person_id)
    person_merge = await db.get(Person, request.merge_into_id)

    if not person_keep or person_keep.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Person not found")

    if not person_merge or person_merge.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Person to merge not found")

    if person_keep.id == person_merge.id:
        raise HTTPException(status_code=400, detail="Cannot merge person with itself")

    # Move all faces
    faces_query = select(Face).where(Face.person_id == person_merge.id)
    result = await db.execute(faces_query)
    faces = result.scalars().all()

    for face in faces:
        face.person_id = person_keep.id

    # Update counts
    person_keep.face_count += person_merge.face_count
    person_merge.face_count = 0
    person_merge.merged_into_id = person_keep.id

    await db.commit()
    await db.refresh(person_keep)

    thumbnail_url = None
    if person_keep.cover_face_id:
        face = await db.get(Face, person_keep.cover_face_id)
        if face and face.thumbnail_path:
            thumbnail_url = f"/api/v1/faces/{face.id}/thumbnail"

    return PersonResponse(
        id=person_keep.id,
        name=person_keep.name,
        face_count=person_keep.face_count,
        is_hidden=person_keep.is_hidden,
        is_favorite=person_keep.is_favorite,
        thumbnail_url=thumbnail_url,
    )


@router.get("/{person_id}/assets", response_model=PersonAssetsResponse)
async def get_person_assets(
    person_id: UUID,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
):
    """Get assets containing a specific person."""
    person = await db.get(Person, person_id)

    if not person or person.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Person not found")

    # Get distinct asset IDs
    query = (
        select(Face.asset_id)
        .where(Face.person_id == person_id)
        .distinct()
    )

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query)

    # Paginate
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    asset_ids = [row[0] for row in result.all()]

    return PersonAssetsResponse(
        person_id=person_id,
        asset_ids=asset_ids,
        total=total,
    )


@router.delete("/{person_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_person(
    person_id: UUID,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Delete a person (unassigns all faces)."""
    person = await db.get(Person, person_id)

    if not person or person.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Person not found")

    # Unassign all faces
    faces_query = select(Face).where(Face.person_id == person_id)
    result = await db.execute(faces_query)
    faces = result.scalars().all()

    for face in faces:
        face.person_id = None

    # Delete person
    await db.delete(person)
    await db.commit()
