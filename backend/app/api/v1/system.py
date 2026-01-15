"""
System information endpoints.
"""

from fastapi import APIRouter

from app.ml import get_accelerator_info

router = APIRouter()


@router.get("/info")
async def get_system_info():
    """Get system information including ML accelerator details."""
    return {
        "version": "0.1.0",
        "accelerator": get_accelerator_info(),
    }


@router.get("/accelerator")
async def get_ml_accelerator():
    """Get ML accelerator information."""
    return get_accelerator_info()
