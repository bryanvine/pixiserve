import os
from pathlib import Path
from typing import AsyncIterator, BinaryIO

import aiofiles
import aiofiles.os

from app.storage.base import StorageBackend


class LocalStorageBackend(StorageBackend):
    def __init__(self, base_path: str):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

    def _get_full_path(self, path: str) -> Path:
        return self.base_path / path

    async def write(self, path: str, data: bytes | BinaryIO) -> str:
        full_path = self._get_full_path(path)
        full_path.parent.mkdir(parents=True, exist_ok=True)

        if isinstance(data, bytes):
            async with aiofiles.open(full_path, "wb") as f:
                await f.write(data)
        else:
            # BinaryIO object - read in chunks
            async with aiofiles.open(full_path, "wb") as f:
                while chunk := data.read(8192):
                    await f.write(chunk)

        return path

    async def read(self, path: str) -> bytes:
        full_path = self._get_full_path(path)
        async with aiofiles.open(full_path, "rb") as f:
            return await f.read()

    async def read_stream(self, path: str, chunk_size: int = 8192) -> AsyncIterator[bytes]:
        full_path = self._get_full_path(path)
        async with aiofiles.open(full_path, "rb") as f:
            while chunk := await f.read(chunk_size):
                yield chunk

    async def delete(self, path: str) -> bool:
        full_path = self._get_full_path(path)
        try:
            await aiofiles.os.remove(full_path)
            return True
        except FileNotFoundError:
            return False

    async def exists(self, path: str) -> bool:
        full_path = self._get_full_path(path)
        return await aiofiles.os.path.exists(full_path)

    async def get_size(self, path: str) -> int:
        full_path = self._get_full_path(path)
        stat = await aiofiles.os.stat(full_path)
        return stat.st_size

    def get_url(self, path: str) -> str:
        return str(self._get_full_path(path))
