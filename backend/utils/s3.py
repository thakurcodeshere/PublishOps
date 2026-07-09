"""S3 client wrapper for async file operations using aioboto3."""

from __future__ import annotations

import io
from typing import Any

import aioboto3

from backend.config import get_settings
from backend.utils.logger import get_logger

logger = get_logger(__name__)


class S3Client:
    """Async S3 client for asset upload/download/management."""

    def __init__(self) -> None:
        self._settings = get_settings()
        self._session = aioboto3.Session(
            aws_access_key_id=self._settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=self._settings.AWS_SECRET_ACCESS_KEY,
            region_name=self._settings.AWS_REGION,
        )

    def _get_bucket(self) -> str:
        return self._settings.S3_BUCKET

    async def upload_file(
        self,
        data: bytes,
        s3_key: str,
        content_type: str = "application/octet-stream",
        metadata: dict[str, str] | None = None,
    ) -> str:
        """Upload bytes to S3 and return the S3 URL."""
        bucket = self._get_bucket()
        extra_args: dict[str, Any] = {"ContentType": content_type}
        if metadata:
            extra_args["Metadata"] = metadata

        async with self._session.client("s3") as s3:
            await s3.upload_fileobj(
                io.BytesIO(data),
                bucket,
                s3_key,
                ExtraArgs=extra_args,
            )

        url = f"https://{bucket}.s3.{self._settings.AWS_REGION}.amazonaws.com/{s3_key}"
        logger.info("s3_upload_complete", s3_key=s3_key, size_bytes=len(data))
        return url

    async def download_file(self, s3_key: str) -> bytes:
        """Download a file from S3 and return its bytes."""
        bucket = self._get_bucket()
        buffer = io.BytesIO()

        async with self._session.client("s3") as s3:
            response = await s3.get_object(Bucket=bucket, Key=s3_key)
            async with response["Body"] as stream:
                buffer.write(await stream.read())

        logger.info("s3_download_complete", s3_key=s3_key, size_bytes=buffer.tell())
        return buffer.getvalue()

    async def generate_presigned_url(
        self, s3_key: str, expiration: int = 3600
    ) -> str:
        """Generate a presigned URL for temporary access."""
        bucket = self._get_bucket()
        async with self._session.client("s3") as s3:
            url: str = await s3.generate_presigned_url(
                "get_object",
                Params={"Bucket": bucket, "Key": s3_key},
                ExpiresIn=expiration,
            )
        return url

    async def delete_file(self, s3_key: str) -> None:
        """Delete a file from S3."""
        bucket = self._get_bucket()
        async with self._session.client("s3") as s3:
            await s3.delete_object(Bucket=bucket, Key=s3_key)
        logger.info("s3_delete_complete", s3_key=s3_key)

    async def file_exists(self, s3_key: str) -> bool:
        """Check if a file exists in S3."""
        bucket = self._get_bucket()
        try:
            async with self._session.client("s3") as s3:
                await s3.head_object(Bucket=bucket, Key=s3_key)
            return True
        except Exception:
            return False

    async def list_files(self, prefix: str, max_keys: int = 1000) -> list[str]:
        """List file keys under a given prefix."""
        bucket = self._get_bucket()
        keys: list[str] = []
        async with self._session.client("s3") as s3:
            paginator = s3.get_paginator("list_objects_v2")
            async for page in paginator.paginate(
                Bucket=bucket, Prefix=prefix, PaginationConfig={"MaxItems": max_keys}
            ):
                for obj in page.get("Contents", []):
                    keys.append(obj["Key"])
        return keys
