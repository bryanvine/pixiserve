from functools import lru_cache

from app.config import get_settings
from app.storage.base import StorageBackend
from app.storage.local import LocalStorageBackend
from app.storage.s3 import S3StorageBackend


@lru_cache
def get_storage() -> StorageBackend:
    settings = get_settings()

    if settings.storage_type == "s3":
        if not all([settings.s3_bucket, settings.s3_access_key, settings.s3_secret_key]):
            raise ValueError("S3 storage requires bucket, access_key, and secret_key")

        return S3StorageBackend(
            bucket=settings.s3_bucket,
            endpoint_url=settings.s3_endpoint,
            access_key=settings.s3_access_key,
            secret_key=settings.s3_secret_key,
            region=settings.s3_region,
        )

    return LocalStorageBackend(settings.storage_path)
