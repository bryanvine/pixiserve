import hashlib
from typing import BinaryIO


def compute_sha256(data: bytes | BinaryIO) -> str:
    hasher = hashlib.sha256()

    if isinstance(data, bytes):
        hasher.update(data)
    else:
        # BinaryIO - read in chunks
        data.seek(0)
        while chunk := data.read(8192):
            hasher.update(chunk)
        data.seek(0)  # Reset for later use

    return hasher.hexdigest()


async def compute_sha256_async(file) -> str:
    """Compute SHA256 for a SpooledTemporaryFile or similar."""
    hasher = hashlib.sha256()

    await file.seek(0)
    while chunk := await file.read(8192):
        hasher.update(chunk)
    await file.seek(0)

    return hasher.hexdigest()
