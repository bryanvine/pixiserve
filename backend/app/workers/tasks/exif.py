"""
EXIF metadata extraction task.

Extracts:
- Date/time captured
- GPS coordinates
- Camera make/model
- Exposure settings
- Image dimensions
"""

import logging
from datetime import datetime, timezone
from pathlib import Path

from celery import shared_task

logger = logging.getLogger(__name__)


def _parse_exif_datetime(value: str) -> datetime | None:
    """Parse EXIF datetime string to datetime object."""
    if not value:
        return None

    # Common EXIF datetime formats
    formats = [
        "%Y:%m:%d %H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
        "%Y:%m:%d %H:%M:%S.%f",
    ]

    for fmt in formats:
        try:
            return datetime.strptime(value.strip(), fmt)
        except ValueError:
            continue

    return None


def _convert_gps_to_decimal(gps_values, gps_ref: str) -> float | None:
    """Convert GPS coordinates from degrees/minutes/seconds to decimal."""
    try:
        # Handle different EXIF library formats
        if hasattr(gps_values, "values"):
            # exifread format
            values = gps_values.values
        elif isinstance(gps_values, (list, tuple)):
            values = gps_values
        else:
            return None

        # Convert to float
        def to_float(val):
            if hasattr(val, "num") and hasattr(val, "den"):
                return val.num / val.den if val.den != 0 else 0
            return float(val)

        degrees = to_float(values[0])
        minutes = to_float(values[1])
        seconds = to_float(values[2]) if len(values) > 2 else 0

        decimal = degrees + (minutes / 60) + (seconds / 3600)

        # Apply direction reference
        if gps_ref in ("S", "W"):
            decimal = -decimal

        return round(decimal, 8)

    except Exception as e:
        logger.debug(f"GPS conversion error: {e}")
        return None


def _extract_with_exifread(file_path: str) -> dict:
    """Extract EXIF using exifread library."""
    import exifread

    with open(file_path, "rb") as f:
        tags = exifread.process_file(f, details=False)

    if not tags:
        return {}

    result = {"raw": {}}

    # Date/time
    for tag in ["EXIF DateTimeOriginal", "EXIF DateTimeDigitized", "Image DateTime"]:
        if tag in tags:
            value = str(tags[tag])
            dt = _parse_exif_datetime(value)
            if dt:
                result["captured_at"] = dt.isoformat()
                break

    # GPS coordinates
    gps_lat = tags.get("GPS GPSLatitude")
    gps_lat_ref = str(tags.get("GPS GPSLatitudeRef", "N"))
    gps_lon = tags.get("GPS GPSLongitude")
    gps_lon_ref = str(tags.get("GPS GPSLongitudeRef", "E"))

    if gps_lat and gps_lon:
        lat = _convert_gps_to_decimal(gps_lat, gps_lat_ref)
        lon = _convert_gps_to_decimal(gps_lon, gps_lon_ref)
        if lat is not None and lon is not None:
            result["latitude"] = lat
            result["longitude"] = lon

    # Camera info
    if "Image Make" in tags:
        result["raw"]["camera_make"] = str(tags["Image Make"]).strip()
    if "Image Model" in tags:
        result["raw"]["camera_model"] = str(tags["Image Model"]).strip()

    # Dimensions
    if "EXIF ExifImageWidth" in tags:
        try:
            result["width"] = int(str(tags["EXIF ExifImageWidth"]))
        except ValueError:
            pass
    if "EXIF ExifImageLength" in tags:
        try:
            result["height"] = int(str(tags["EXIF ExifImageLength"]))
        except ValueError:
            pass

    # Exposure settings
    if "EXIF ExposureTime" in tags:
        result["raw"]["exposure_time"] = str(tags["EXIF ExposureTime"])
    if "EXIF FNumber" in tags:
        result["raw"]["f_number"] = str(tags["EXIF FNumber"])
    if "EXIF ISOSpeedRatings" in tags:
        result["raw"]["iso"] = str(tags["EXIF ISOSpeedRatings"])
    if "EXIF FocalLength" in tags:
        result["raw"]["focal_length"] = str(tags["EXIF FocalLength"])

    # Orientation
    if "Image Orientation" in tags:
        try:
            result["raw"]["orientation"] = int(str(tags["Image Orientation"]))
        except ValueError:
            pass

    return result


def _extract_with_pillow(file_path: str) -> dict:
    """Extract EXIF using Pillow as fallback."""
    from PIL import Image
    from PIL.ExifTags import TAGS, GPSTAGS

    with Image.open(file_path) as img:
        result = {
            "width": img.width,
            "height": img.height,
            "raw": {},
        }

        exif = img.getexif()
        if not exif:
            return result

        for tag_id, value in exif.items():
            tag = TAGS.get(tag_id, tag_id)

            if tag == "DateTimeOriginal":
                dt = _parse_exif_datetime(str(value))
                if dt:
                    result["captured_at"] = dt.isoformat()

            elif tag == "DateTime" and "captured_at" not in result:
                dt = _parse_exif_datetime(str(value))
                if dt:
                    result["captured_at"] = dt.isoformat()

            elif tag == "Make":
                result["raw"]["camera_make"] = str(value).strip()

            elif tag == "Model":
                result["raw"]["camera_model"] = str(value).strip()

        return result


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def extract_exif(self, asset_id: str, storage_path: str) -> dict:
    """
    Extract EXIF metadata from an image file.

    Args:
        asset_id: UUID of the asset
        storage_path: Path to the image file

    Returns:
        Dictionary with extracted metadata
    """
    logger.info(f"Extracting EXIF for asset {asset_id}")

    result = {
        "asset_id": asset_id,
        "metadata": {},
    }

    try:
        # Try exifread first (better EXIF support)
        try:
            exif_data = _extract_with_exifread(storage_path)
            if exif_data:
                result["metadata"] = exif_data
                logger.info(f"EXIF extracted for {asset_id}")
                return result
        except Exception as e:
            logger.debug(f"exifread failed, trying Pillow: {e}")

        # Fallback to Pillow
        exif_data = _extract_with_pillow(storage_path)
        result["metadata"] = exif_data

        logger.info(f"EXIF extracted for {asset_id} (via Pillow)")
        return result

    except Exception as e:
        logger.error(f"Failed to extract EXIF for {asset_id}: {e}")
        result["error"] = str(e)
        return result


@shared_task
def extract_video_metadata(asset_id: str, storage_path: str) -> dict:
    """
    Extract metadata from video file using ffprobe.

    Args:
        asset_id: UUID of the asset
        storage_path: Path to the video file

    Returns:
        Dictionary with extracted metadata
    """
    logger.info(f"Extracting video metadata for asset {asset_id}")

    try:
        import json
        import subprocess

        # Use ffprobe to get video metadata
        result = subprocess.run(
            [
                "ffprobe",
                "-v", "quiet",
                "-print_format", "json",
                "-show_format",
                "-show_streams",
                storage_path,
            ],
            capture_output=True,
            text=True,
            check=True,
        )

        probe_data = json.loads(result.stdout)

        metadata = {
            "asset_id": asset_id,
            "metadata": {"raw": {}},
        }

        # Extract format info
        if "format" in probe_data:
            fmt = probe_data["format"]
            if "duration" in fmt:
                metadata["metadata"]["duration_seconds"] = float(fmt["duration"])

            # Check for creation time
            if "tags" in fmt:
                tags = fmt["tags"]
                if "creation_time" in tags:
                    try:
                        dt = datetime.fromisoformat(tags["creation_time"].replace("Z", "+00:00"))
                        metadata["metadata"]["captured_at"] = dt.isoformat()
                    except ValueError:
                        pass

        # Extract stream info
        for stream in probe_data.get("streams", []):
            if stream.get("codec_type") == "video":
                if "width" in stream:
                    metadata["metadata"]["width"] = stream["width"]
                if "height" in stream:
                    metadata["metadata"]["height"] = stream["height"]
                if "codec_name" in stream:
                    metadata["metadata"]["raw"]["video_codec"] = stream["codec_name"]
                break

        logger.info(f"Video metadata extracted for {asset_id}")
        return metadata

    except Exception as e:
        logger.error(f"Failed to extract video metadata for {asset_id}: {e}")
        return {
            "asset_id": asset_id,
            "metadata": {},
            "error": str(e),
        }
