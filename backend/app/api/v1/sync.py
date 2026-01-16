"""
Mobile sync API endpoints.

Supports offline-first sync protocol:
1. Client registers device
2. Client scans local media, computes hashes
3. Client sends hashes to check existence
4. Server returns which are new
5. Client uploads new files
6. Client updates sync cursor
"""

from datetime import datetime, timezone
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser
from app.database import get_db
from app.models import Device, DeviceType, Asset

router = APIRouter()


class DeviceRegisterRequest(BaseModel):
    """Device registration request."""
    device_name: str
    device_type: DeviceType
    device_id: str  # Unique device identifier
    app_version: str | None = None
    push_token: str | None = None


class DeviceResponse(BaseModel):
    """Device response model."""
    id: UUID
    device_name: str
    device_type: DeviceType
    device_id: str
    last_sync_at: datetime | None
    sync_cursor: str | None
    total_uploaded: int
    is_active: bool

    model_config = {"from_attributes": True}


class HashCheckRequest(BaseModel):
    """Request to check which hashes exist on server."""
    hashes: list[str]  # SHA256 hashes


class HashCheckResponse(BaseModel):
    """Response with existing/missing hashes."""
    existing: list[str]  # Hashes that already exist
    missing: list[str]  # Hashes that need to be uploaded


class SyncStatusResponse(BaseModel):
    """Sync status for a device."""
    device_id: UUID
    last_sync_at: datetime | None
    sync_cursor: str | None
    total_assets: int
    assets_since_cursor: int


class SyncCursorUpdate(BaseModel):
    """Update sync cursor."""
    cursor: str


@router.post("/devices", response_model=DeviceResponse, status_code=status.HTTP_201_CREATED)
async def register_device(
    request: DeviceRegisterRequest,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Register a new sync device or update existing."""
    # Check if device already exists
    existing = await db.execute(
        select(Device).where(
            Device.owner_id == current_user.id,
            Device.device_id == request.device_id,
        )
    )
    device = existing.scalar_one_or_none()

    if device:
        # Update existing device
        device.device_name = request.device_name
        device.device_type = request.device_type
        device.app_version = request.app_version
        device.push_token = request.push_token
        device.is_active = True
    else:
        # Create new device
        device = Device(
            owner_id=current_user.id,
            device_name=request.device_name,
            device_type=request.device_type,
            device_id=request.device_id,
            app_version=request.app_version,
            push_token=request.push_token,
        )
        db.add(device)

    await db.commit()
    await db.refresh(device)

    return DeviceResponse.model_validate(device)


@router.get("/devices", response_model=list[DeviceResponse])
async def list_devices(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """List all registered devices for the user."""
    result = await db.execute(
        select(Device)
        .where(Device.owner_id == current_user.id)
        .where(Device.is_active.is_(True))
        .order_by(Device.last_sync_at.desc().nullslast())
    )
    devices = result.scalars().all()

    return [DeviceResponse.model_validate(d) for d in devices]


@router.delete("/devices/{device_id}", status_code=status.HTTP_204_NO_CONTENT)
async def unregister_device(
    device_id: UUID,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Unregister a device (mark as inactive)."""
    device = await db.get(Device, device_id)

    if not device or device.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Device not found")

    device.is_active = False
    await db.commit()


@router.post("/check", response_model=HashCheckResponse)
async def check_hashes(
    request: HashCheckRequest,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Check which file hashes already exist on the server.

    Used by mobile clients to determine which files need uploading.
    """
    if not request.hashes:
        return HashCheckResponse(existing=[], missing=[])

    # Query existing hashes
    result = await db.execute(
        select(Asset.file_hash_sha256)
        .where(Asset.owner_id == current_user.id)
        .where(Asset.file_hash_sha256.in_(request.hashes))
        .where(Asset.deleted_at.is_(None))
    )
    existing_hashes = set(row[0] for row in result.all())

    existing = [h for h in request.hashes if h in existing_hashes]
    missing = [h for h in request.hashes if h not in existing_hashes]

    return HashCheckResponse(existing=existing, missing=missing)


@router.get("/status/{device_id}", response_model=SyncStatusResponse)
async def get_sync_status(
    device_id: UUID,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Get sync status for a device."""
    device = await db.get(Device, device_id)

    if not device or device.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Device not found")

    # Count total assets
    total_count = await db.scalar(
        select(func.count())
        .select_from(Asset)
        .where(Asset.owner_id == current_user.id)
        .where(Asset.deleted_at.is_(None))
    )

    # Count assets since cursor
    assets_since = 0
    if device.sync_cursor:
        try:
            cursor_time = datetime.fromisoformat(device.sync_cursor)
            assets_since = await db.scalar(
                select(func.count())
                .select_from(Asset)
                .where(Asset.owner_id == current_user.id)
                .where(Asset.deleted_at.is_(None))
                .where(Asset.created_at > cursor_time)
            )
        except ValueError:
            pass

    return SyncStatusResponse(
        device_id=device.id,
        last_sync_at=device.last_sync_at,
        sync_cursor=device.sync_cursor,
        total_assets=total_count,
        assets_since_cursor=assets_since,
    )


@router.put("/cursor/{device_id}")
async def update_sync_cursor(
    device_id: UUID,
    update: SyncCursorUpdate,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Update sync cursor after successful sync."""
    device = await db.get(Device, device_id)

    if not device or device.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Device not found")

    device.sync_cursor = update.cursor
    device.last_sync_at = datetime.now(timezone.utc)

    await db.commit()

    return {"status": "ok", "cursor": update.cursor}


@router.get("/changes/{device_id}")
async def get_changes_since_cursor(
    device_id: UUID,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: int = Query(100, ge=1, le=1000),
):
    """
    Get assets changed since the device's sync cursor.

    Returns asset metadata for download sync.
    """
    device = await db.get(Device, device_id)

    if not device or device.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Device not found")

    query = (
        select(Asset)
        .where(Asset.owner_id == current_user.id)
        .where(Asset.deleted_at.is_(None))
    )

    if device.sync_cursor:
        try:
            cursor_time = datetime.fromisoformat(device.sync_cursor)
            query = query.where(Asset.created_at > cursor_time)
        except ValueError:
            pass

    query = query.order_by(Asset.created_at.asc()).limit(limit)

    result = await db.execute(query)
    assets = result.scalars().all()

    # Calculate next cursor
    next_cursor = None
    if assets:
        next_cursor = assets[-1].created_at.isoformat()

    return {
        "assets": [
            {
                "id": str(a.id),
                "hash": a.file_hash_sha256,
                "filename": a.original_filename,
                "mime_type": a.mime_type,
                "size": a.file_size_bytes,
                "captured_at": a.captured_at.isoformat() if a.captured_at else None,
                "created_at": a.created_at.isoformat(),
            }
            for a in assets
        ],
        "next_cursor": next_cursor,
        "has_more": len(assets) == limit,
    }
