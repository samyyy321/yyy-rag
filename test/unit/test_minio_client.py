from io import BytesIO
from unittest.mock import Mock
from uuid import UUID

from src.infra.minio_client import ObjectStorage, build_document_object_key


def test_put_file_uses_configured_bucket_and_metadata():
    client = Mock()
    storage = ObjectStorage(client=client, bucket="rag-documents")
    storage.put_file(BytesIO(b"abc"), "doc-id/file.txt", "text/plain", 3)
    client.put_object.assert_called_once()
    call = client.put_object.call_args
    assert call.args[0] == "rag-documents"
    assert call.args[1] == "doc-id/file.txt"
    assert call.kwargs["length"] == 3
    assert call.kwargs["content_type"] == "text/plain"


def test_remove_file_uses_configured_bucket():
    client = Mock()
    storage = ObjectStorage(client=client, bucket="rag-documents")
    storage.remove_file("7f9c/file.pdf")
    client.remove_object.assert_called_once_with("rag-documents", "7f9c/file.pdf")


def test_build_document_object_key_removes_path_components():
    document_id = UUID("7f9c6b8e-7b6d-4c5a-9e2d-1c4f87b8a321")
    key = build_document_object_key(document_id, "../nested\\a.pdf")
    assert key == "7f9c6b8e-7b6d-4c5a-9e2d-1c4f87b8a321/a.pdf"
    assert ".." not in key


def test_ensure_bucket_creates_missing_bucket():
    client = Mock()
    client.bucket_exists.return_value = False
    storage = ObjectStorage(client=client, bucket="rag-documents")
    storage.ensure_bucket()
    client.make_bucket.assert_called_once_with("rag-documents")
