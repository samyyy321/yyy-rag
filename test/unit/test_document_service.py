from io import BytesIO
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from src.services.document_service import (
    ResourceConflictError,
    create_document,
    delete_document,
    run_ingestion_task,
)


def test_create_document_checks_knowledge_base_with_row_lock():
    kb_id = uuid4()
    kb = Mock(id=kb_id)
    row_result = Mock()
    row_result.scalar_one_or_none.return_value = kb
    db = Mock()
    db.execute.return_value = row_result
    storage = Mock()

    document, task = create_document(
        db,
        storage,
        knowledge_base_id=kb_id,
        original_name="a.txt",
        content_type="text/plain",
        file_size=3,
        doc_type="txt",
        category="default",
        chunk_strategy="sliding_window",
        fileobj=BytesIO(b"abc"),
    )

    assert document.knowledge_base_id == kb_id
    assert document.status == "pending"
    assert document.chunk_strategy == "sliding_window"
    assert task.document_id == document.id
    assert task.status == "pending"
    statement = db.execute.call_args.args[0]
    assert statement._for_update_arg is not None
    storage.put_file.assert_called_once()


def test_delete_processing_document_rolls_back_without_external_cleanup():
    document = Mock(status="processing")
    db = Mock()
    result = Mock()
    result.scalar_one_or_none.return_value = document
    db.execute.return_value = result
    storage = Mock()
    milvus = Mock()

    with pytest.raises(ResourceConflictError):
        delete_document(db, storage, milvus, uuid4())

    db.rollback.assert_called_once()
    storage.remove_file.assert_not_called()
    milvus.delete.assert_not_called()


def test_ingestion_worker_does_not_claim_non_pending_task(monkeypatch):
    task = Mock(status="completed")
    db = Mock()
    result = Mock()
    result.scalar_one_or_none.return_value = task
    db.execute.return_value = result
    monkeypatch.setattr("src.services.document_service.SessionLocal", lambda: db)

    run_ingestion_task(uuid4())

    db.commit.assert_not_called()

def test_ingestion_worker_passes_persisted_chunk_strategy(monkeypatch):
    """后台任务必须使用文档持久化的策略，而不是读取上传请求临时状态。"""
    task_id = uuid4()
    document_id = uuid4()
    task = Mock(id=task_id)
    document = Mock(
        id=document_id,
        knowledge_base_id=uuid4(),
        original_name="a.md",
        doc_type="md",
        category="default",
        chunk_strategy="semantic",
    )
    db = Mock()
    storage = Mock()
    milvus = Mock()
    embedding = Mock()
    ingest = AsyncMock(return_value=2)
    finish = Mock()

    monkeypatch.setattr("src.services.document_service.SessionLocal", lambda: db)
    monkeypatch.setattr("src.services.document_service._claim_ingestion_task", lambda _db, _id: (task, document))
    monkeypatch.setattr("src.services.document_service._finish_ingestion_task", finish)
    monkeypatch.setattr("src.services.document_service.get_object_storage", lambda: storage)
    monkeypatch.setattr("src.services.document_service.get_milvus_client", lambda: milvus)
    monkeypatch.setattr("src.infra.embedding.get_embedding_model", lambda: embedding)
    monkeypatch.setattr("src.index.doc_ingestion.ingest_file", ingest)

    run_ingestion_task(task_id)

    assert ingest.call_args.kwargs["chunk_strategy"] == "semantic"
    finish.assert_called_once_with(task_id, status="completed", chunk_count=2)
