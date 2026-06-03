"""MinIO 原始文档对象存储适配器。"""

from __future__ import annotations

from pathlib import Path
from typing import BinaryIO
from uuid import UUID

from minio import Minio
from minio.error import S3Error

from src.core.config import get_settings


def build_document_object_key(document_id: UUID, original_name: str) -> str:
    """生成以文档 UUID 为目录的安全 MinIO 对象键。"""
    safe_name = Path(original_name.replace("\\", "/")).name
    return f"{document_id}/{safe_name}"


class ObjectStorage:
    """封装生产 API 使用的 MinIO bucket 和对象操作。"""

    def __init__(self, client: Minio, bucket: str) -> None:
        self.client = client
        self.bucket = bucket

    def put_file(
        self,
        fileobj: BinaryIO,
        object_key: str,
        content_type: str | None,
        length: int,
    ) -> None:
        """上传文件流，并写入明确的 MIME 类型。"""
        self.client.put_object(
            self.bucket,
            object_key,
            fileobj,
            length=length,
            content_type=content_type or "application/octet-stream",
        )

    def download_file(self, object_key: str, destination: str) -> None:
        """将对象下载到本地临时文件。"""
        self.client.fget_object(self.bucket, object_key, destination)

    def remove_file(self, object_key: str) -> None:
        """删除对象；对象不存在时按幂等成功处理。"""
        try:
            self.client.remove_object(self.bucket, object_key)
        except S3Error as exc:
            if exc.code not in {"NoSuchKey", "NoSuchObject"}:
                raise

    def ensure_bucket(self) -> None:
        """确保业务 bucket 已创建。"""
        if not self.client.bucket_exists(self.bucket):
            self.client.make_bucket(self.bucket)


def get_object_storage() -> ObjectStorage:
    """根据配置创建 MinIO 对象存储适配器。"""
    settings = get_settings()
    client = Minio(
        settings.MINIO_ENDPOINT,
        access_key=settings.MINIO_ACCESS_KEY,
        secret_key=settings.MINIO_SECRET_KEY,
        secure=settings.MINIO_SECURE,
    )
    return ObjectStorage(client=client, bucket=settings.MINIO_BUCKET)
