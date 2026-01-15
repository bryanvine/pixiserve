from io import BytesIO
from typing import AsyncIterator, BinaryIO

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

from app.storage.base import StorageBackend


class S3StorageBackend(StorageBackend):
    def __init__(
        self,
        bucket: str,
        endpoint_url: str | None = None,
        access_key: str | None = None,
        secret_key: str | None = None,
        region: str = "us-east-1",
    ):
        self.bucket = bucket
        self.endpoint_url = endpoint_url

        config = Config(
            signature_version="s3v4",
            s3={"addressing_style": "path"},
        )

        self.client = boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region,
            config=config,
        )

    async def write(self, path: str, data: bytes | BinaryIO) -> str:
        if isinstance(data, bytes):
            body = BytesIO(data)
        else:
            body = data

        self.client.upload_fileobj(body, self.bucket, path)
        return path

    async def read(self, path: str) -> bytes:
        response = self.client.get_object(Bucket=self.bucket, Key=path)
        return response["Body"].read()

    async def read_stream(self, path: str, chunk_size: int = 8192) -> AsyncIterator[bytes]:
        response = self.client.get_object(Bucket=self.bucket, Key=path)
        body = response["Body"]

        for chunk in body.iter_chunks(chunk_size=chunk_size):
            yield chunk

    async def delete(self, path: str) -> bool:
        try:
            self.client.delete_object(Bucket=self.bucket, Key=path)
            return True
        except ClientError:
            return False

    async def exists(self, path: str) -> bool:
        try:
            self.client.head_object(Bucket=self.bucket, Key=path)
            return True
        except ClientError:
            return False

    async def get_size(self, path: str) -> int:
        response = self.client.head_object(Bucket=self.bucket, Key=path)
        return response["ContentLength"]

    def get_url(self, path: str) -> str:
        if self.endpoint_url:
            return f"{self.endpoint_url}/{self.bucket}/{path}"
        return f"https://{self.bucket}.s3.amazonaws.com/{path}"
