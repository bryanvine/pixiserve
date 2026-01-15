"""
Reverse geocoding task.

Converts GPS coordinates to human-readable location names.
Uses Nominatim (OpenStreetMap) with caching to respect rate limits.
"""

import logging
from functools import lru_cache

from celery import shared_task

logger = logging.getLogger(__name__)

# In-memory cache for geocoding results
# Key: (lat, lon) rounded to ~100m precision
# Value: (city, state, country)
_geocode_cache: dict[tuple[float, float], tuple[str | None, str | None, str | None]] = {}


def _round_coords(lat: float, lon: float, precision: int = 3) -> tuple[float, float]:
    """Round coordinates to reduce cache misses for nearby locations."""
    return (round(lat, precision), round(lon, precision))


def _geocode_with_nominatim(lat: float, lon: float) -> tuple[str | None, str | None, str | None]:
    """
    Reverse geocode using Nominatim (OpenStreetMap).

    Returns:
        Tuple of (city, state, country)
    """
    from geopy.geocoders import Nominatim
    from geopy.exc import GeocoderTimedOut, GeocoderServiceError

    try:
        geolocator = Nominatim(
            user_agent="pixiserve/1.0",
            timeout=10,
        )

        location = geolocator.reverse(
            f"{lat}, {lon}",
            language="en",
            exactly_one=True,
        )

        if not location or not location.raw:
            return (None, None, None)

        address = location.raw.get("address", {})

        # Extract city (try multiple fields)
        city = (
            address.get("city")
            or address.get("town")
            or address.get("village")
            or address.get("municipality")
            or address.get("suburb")
        )

        # Extract state/province
        state = address.get("state") or address.get("province") or address.get("region")

        # Extract country
        country = address.get("country")

        return (city, state, country)

    except (GeocoderTimedOut, GeocoderServiceError) as e:
        logger.warning(f"Geocoding service error: {e}")
        raise
    except Exception as e:
        logger.error(f"Geocoding error: {e}")
        return (None, None, None)


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
    rate_limit="1/s",  # Respect Nominatim usage policy
)
def reverse_geocode(self, asset_id: str, latitude: float, longitude: float) -> dict:
    """
    Reverse geocode coordinates to location name.

    Args:
        asset_id: UUID of the asset
        latitude: GPS latitude
        longitude: GPS longitude

    Returns:
        Dictionary with location data
    """
    logger.info(f"Reverse geocoding for asset {asset_id}: ({latitude}, {longitude})")

    # Check cache first
    cache_key = _round_coords(latitude, longitude)
    if cache_key in _geocode_cache:
        city, state, country = _geocode_cache[cache_key]
        logger.debug(f"Cache hit for {cache_key}")
        return {
            "asset_id": asset_id,
            "city": city,
            "state": state,
            "country": country,
            "cached": True,
        }

    # Perform geocoding
    try:
        city, state, country = _geocode_with_nominatim(latitude, longitude)

        # Cache result
        _geocode_cache[cache_key] = (city, state, country)

        logger.info(f"Geocoded {asset_id}: {city}, {country}")
        return {
            "asset_id": asset_id,
            "city": city,
            "state": state,
            "country": country,
            "cached": False,
        }

    except Exception as e:
        logger.error(f"Failed to geocode {asset_id}: {e}")
        raise


@shared_task
def batch_reverse_geocode(assets: list[dict]) -> list[dict]:
    """
    Batch reverse geocode multiple assets.

    Args:
        assets: List of dicts with asset_id, latitude, longitude

    Returns:
        List of geocoding results
    """
    results = []

    for asset in assets:
        if not asset.get("latitude") or not asset.get("longitude"):
            continue

        try:
            result = reverse_geocode.delay(
                asset["asset_id"],
                asset["latitude"],
                asset["longitude"],
            )
            results.append({
                "asset_id": asset["asset_id"],
                "task_id": result.id,
            })
        except Exception as e:
            logger.error(f"Failed to queue geocoding for {asset['asset_id']}: {e}")

    return results
