"""
Thumbnail generation tasks.

Generates multiple thumbnail sizes for fast gallery loading:
- thumb: 256x256 (grid view)
- preview: 1080p max (lightbox view)
- tiny: 64x64 (face crops, placeholders)
"""

import logging
from io import BytesIO
from pathlib import Path

from celery import shared_task
from PIL import Image

from app.config import get_settings

logger = logging.getLogger(__name__)

# Thumbnail configurations
THUMBNAIL_SIZES = {
    "tiny": (64, 64),
    "thumb": (256, 256),
    "preview": (1920, 1080),
}

# WebP quality settings
WEBP_QUALITY = 85
WEBP_QUALITY_TINY = 70


def _get_thumbnail_path(storage_path: str, size_name: str) -> str:
    """Generate thumbnail path from original storage path."""
    settings = get_settings()

    # Convert storage path to thumbnail path
    # Original: /data/photos/ab/cd/abcd1234.jpg
    # Thumb: /data/thumbnails/ab/cd/abcd1234_thumb.webp
    path = Path(storage_path)
    thumb_dir = Path(settings.storage_path).parent / "thumbnails"

    # Preserve directory structure
    relative_path = path.relative_to(settings.storage_path) if storage_path.startswith(settings.storage_path) else path
    thumb_path = thumb_dir / relative_path.parent / f"{path.stem}_{size_name}.webp"

    return str(thumb_path)


def _generate_thumbnail(
    image: Image.Image,
    max_size: tuple[int, int],
    quality: int = WEBP_QUALITY,
) -> bytes:
    """Generate a thumbnail from PIL Image."""
    # Create a copy to avoid modifying original
    img = image.copy()

    # Handle EXIF orientation
    try:
        from PIL import ImageOps
        img = ImageOps.exif_transpose(img)
    except Exception:
        pass

    # Convert to RGB if necessary (WebP doesn't support all modes)
    if img.mode in ("RGBA", "LA", "P"):
        # Preserve alpha for RGBA
        if img.mode == "RGBA":
            background = Image.new("RGB", img.size, (255, 255, 255))
            background.paste(img, mask=img.split()[3])
            img = background
        else:
            img = img.convert("RGB")
    elif img.mode != "RGB":
        img = img.convert("RGB")

    # Resize maintaining aspect ratio
    img.thumbnail(max_size, Image.Resampling.LANCZOS)

    # Save to WebP
    buffer = BytesIO()
    img.save(buffer, format="WEBP", quality=quality, method=4)
    return buffer.getvalue()


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def generate_thumbnails(self, asset_id: str, storage_path: str) -> dict:
    """
    Generate all thumbnail sizes for an asset.

    Args:
        asset_id: UUID of the asset
        storage_path: Path to the original file

    Returns:
        Dictionary with paths to generated thumbnails
    """
    logger.info(f"Generating thumbnails for asset {asset_id}")

    settings = get_settings()
    results = {}

    try:
        # Load image
        # Support HEIF/HEIC format
        try:
            from pillow_heif import register_heif_opener
            register_heif_opener()
        except ImportError:
            pass

        with Image.open(storage_path) as img:
            original_width, original_height = img.size

            for size_name, max_size in THUMBNAIL_SIZES.items():
                quality = WEBP_QUALITY_TINY if size_name == "tiny" else WEBP_QUALITY

                # Generate thumbnail
                thumb_data = _generate_thumbnail(img, max_size, quality)

                # Determine output path
                thumb_path = _get_thumbnail_path(storage_path, size_name)

                # Create directory if needed
                Path(thumb_path).parent.mkdir(parents=True, exist_ok=True)

                # Write thumbnail
                with open(thumb_path, "wb") as f:
                    f.write(thumb_data)

                results[size_name] = thumb_path
                logger.debug(f"Generated {size_name} thumbnail: {thumb_path}")

        logger.info(f"Thumbnails generated for asset {asset_id}")
        return {
            "asset_id": asset_id,
            "thumbnails": results,
            "original_size": (original_width, original_height),
        }

    except Exception as e:
        logger.error(f"Failed to generate thumbnails for {asset_id}: {e}")
        raise


@shared_task
def generate_video_thumbnail(asset_id: str, storage_path: str) -> dict:
    """
    Generate thumbnail from video file.

    Extracts a frame from the video and generates thumbnails.

    Args:
        asset_id: UUID of the asset
        storage_path: Path to the video file

    Returns:
        Dictionary with paths to generated thumbnails
    """
    logger.info(f"Generating video thumbnail for asset {asset_id}")

    try:
        import subprocess
        import tempfile

        # Extract frame at 1 second using ffmpeg
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            subprocess.run(
                [
                    "ffmpeg",
                    "-i", storage_path,
                    "-ss", "00:00:01",  # 1 second in
                    "-frames:v", "1",
                    "-q:v", "2",
                    tmp_path,
                ],
                check=True,
                capture_output=True,
            )

            # Generate thumbnails from extracted frame
            return generate_thumbnails(asset_id, tmp_path)
        finally:
            # Clean up temp file
            Path(tmp_path).unlink(missing_ok=True)

    except Exception as e:
        logger.error(f"Failed to generate video thumbnail for {asset_id}: {e}")
        raise
