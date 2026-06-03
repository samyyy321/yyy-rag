import os
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4

import pytest

from src.infra.minio_client import get_object_storage


pytestmark = pytest.mark.integration


def test_minio_file_round_trip():
    if not os.getenv("RUN_API_INTEGRATION"):
        pytest.skip("设置 RUN_API_INTEGRATION=1 才运行 MinIO 集成测试")

    storage = get_object_storage()
    storage.ensure_bucket()
    key = f"integration-test/{uuid4()}.txt"
    try:
        storage.put_file(BytesIO(b"minio-round-trip"), key, "text/plain", 16)
        with TemporaryDirectory() as directory:
            destination = Path(directory) / "download.txt"
            storage.download_file(key, str(destination))
            assert destination.read_bytes() == b"minio-round-trip"
    finally:
        storage.remove_file(key)
