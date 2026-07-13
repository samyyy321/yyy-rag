"""文档元数据、异步导入任务和外部存储清理服务。"""

from __future__ import annotations

import asyncio
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import BinaryIO
from uuid import UUID, uuid4

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from src.core.config import get_settings
from src.db.database import SessionLocal
from src.db.models import Document, IngestionTask, KnowledgeBase, utc_now
from src.infra.minio_client import ObjectStorage, build_document_object_key, get_object_storage
from src.infra.milvus_client import get_milvus_client
from src.services.errors import ExternalStorageError, ResourceConflictError, ResourceNotFoundError


def _get_knowledge_base_for_update(db: Session, knowledge_base_id: UUID) -> KnowledgeBase:
    """锁定知识库行，防止创建文档和删除知识库并发穿透。"""
    knowledge_base = db.execute(
        select(KnowledgeBase)
        .where(KnowledgeBase.id == knowledge_base_id)
        .with_for_update()
    ).scalar_one_or_none()
    if knowledge_base is None:
        raise ResourceNotFoundError("知识库不存在")
    return knowledge_base


def create_document(
    db: Session,
    storage: ObjectStorage,
    *,
    knowledge_base_id: UUID,
    original_name: str,
    content_type: str | None,
    file_size: int,
    doc_type: str,
    category: str,
    fileobj: BinaryIO,
    chunk_strategy: str = "recursive",
) -> tuple[Document, IngestionTask]:
    """上传原始文件并在同一业务事务内创建 pending 文档和导入任务。"""
    document_id = uuid4()
    task_id = uuid4()
    object_key = build_document_object_key(document_id, original_name)
    uploaded = False

    try:
        storage.put_file(fileobj, object_key, content_type, file_size)
        uploaded = True
        _get_knowledge_base_for_update(db, knowledge_base_id)
        now = utc_now()
        document = Document(
            id=document_id,
            knowledge_base_id=knowledge_base_id,
            original_name=original_name,
            object_key=object_key,
            content_type=content_type,
            file_size=file_size,
            doc_type=doc_type,
            category=category,
            chunk_strategy=chunk_strategy,
            status="pending",
            chunk_count=0,
            error_message=None,
            created_at=now,
            updated_at=now,
        )
        task = IngestionTask(
            id=task_id,
            document_id=document_id,
            status="pending",
            error_message=None,
            started_at=None,
            finished_at=None,
            created_at=now,
            updated_at=now,
        )
        db.add_all([document, task])
        db.commit()
        db.refresh(document)
        db.refresh(task)
        return document, task
    except Exception:
        db.rollback()
        if uploaded:
            try:
                storage.remove_file(object_key)
            except Exception:
                pass
        raise


def list_documents(
    db: Session,
    *,
    knowledge_base_id: UUID,
    skip: int,
    limit: int,
) -> tuple[list[Document], int]:
    """校验知识库存在后，按知识库返回文档分页列表。"""
    knowledge_base = db.execute(
        select(KnowledgeBase.id).where(KnowledgeBase.id == knowledge_base_id)
    ).scalar_one_or_none()
    if knowledge_base is None:
        raise ResourceNotFoundError("知识库不存在")

    total = db.execute(
        select(func.count()).select_from(Document).where(
            Document.knowledge_base_id == knowledge_base_id
        )
    ).scalar_one()
    documents = list(
        db.execute(
            select(Document)
            .where(Document.knowledge_base_id == knowledge_base_id)
            .order_by(Document.created_at.desc())
            .offset(skip)
            .limit(limit)
        ).scalars()
    )
    return documents, total


def get_document(db: Session, document_id: UUID) -> Document:
    """按文档 ID 查询元数据。"""
    document = db.execute(
        select(Document).where(Document.id == document_id)
    ).scalar_one_or_none()
    if document is None:
        raise ResourceNotFoundError("文档不存在")
    return document


def get_document_with_task(
    db: Session,
    document_id: UUID,
) -> tuple[Document, IngestionTask | None]:
    """返回文档及其最新导入任务，关联由显式 document_id 查询维护。"""
    document = get_document(db, document_id)
    task = db.execute(
        select(IngestionTask)
        .where(IngestionTask.document_id == document_id)
        .order_by(IngestionTask.created_at.desc())
        .limit(1)
    ).scalar_one_or_none()
    return document, task


def delete_document(
    db: Session,
    storage: ObjectStorage,
    milvus_client,
    document_id: UUID,
) -> None:
    """锁定文档并按 Milvus、MinIO、数据库顺序完成删除。"""
    settings = get_settings()
    try:
        document = db.execute(
            select(Document)
            .where(Document.id == document_id)
            .with_for_update()
        ).scalar_one_or_none()
        if document is None:
            raise ResourceNotFoundError("文档不存在")
        if document.status in {"pending", "processing"}:
            raise ResourceConflictError("文档正在导入，不能删除")

        milvus_client.delete(
            collection_name=settings.MILVUS_COLLECTION_NAME,
            filter=(
                f'knowledge_base_id == "{document.knowledge_base_id}" '
                f'&& doc_id == "{document.id}"'
            ),
        )
        storage.remove_file(document.object_key)
        db.execute(
            delete(IngestionTask).where(IngestionTask.document_id == document.id)
        )
        db.delete(document)
        db.commit()
    except (ResourceNotFoundError, ResourceConflictError):
        db.rollback()
        raise
    except Exception as exc:
        db.rollback()
        raise ExternalStorageError("文档外部存储清理失败") from exc


def _claim_ingestion_task(db: Session, task_id: UUID) -> tuple[IngestionTask, Document] | None:
    """以短事务锁定并认领 pending 任务，避免重复 worker 执行。"""
    task = db.execute(
        select(IngestionTask)
        .where(IngestionTask.id == task_id)
        .with_for_update()
    ).scalar_one_or_none()
    if task is None or task.status != "pending":
        db.rollback()
        return None

    document = db.execute(
        select(Document)
        .where(Document.id == task.document_id)
        .with_for_update()
    ).scalar_one_or_none()
    if document is None or document.status != "pending":
        db.rollback()
        return None

    now = utc_now()
    task.status = "processing"
    task.started_at = now
    task.updated_at = now
    document.status = "processing"
    document.error_message = None
    document.updated_at = now
    db.commit()
    return task, document


def _finish_ingestion_task(
    task_id: UUID,
    *,
    status: str,
    chunk_count: int = 0,
    error_message: str | None = None,
) -> None:
    """锁定 processing 任务并写入最终状态，避免覆盖删除后的记录。"""
    db = SessionLocal()
    try:
        task = db.execute(
            select(IngestionTask)
            .where(IngestionTask.id == task_id)
            .with_for_update()
        ).scalar_one_or_none()
        if task is None:
            db.rollback()
            return
        document = db.execute(
            select(Document)
            .where(Document.id == task.document_id)
            .with_for_update()
        ).scalar_one_or_none()
        if document is None or task.status != "processing" or document.status != "processing":
            db.rollback()
            return

        now = utc_now()
        task.status = status
        task.error_message = error_message
        task.finished_at = now
        task.updated_at = now
        document.status = status
        document.error_message = error_message
        document.updated_at = now
        if status == "completed":
            document.chunk_count = chunk_count
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def run_ingestion_task(task_id: UUID) -> None:
    """认领任务、执行导入并回写 completed/failed 状态。"""
    db = SessionLocal()
    try:
        claimed = _claim_ingestion_task(db, task_id)
    except Exception:
        db.rollback()
        db.close()
        raise
    finally:
        db.close()

    if claimed is None:
        return

    task, document = claimed
    try:
        from src.index.doc_ingestion import ingest_file
        from src.infra.embedding import get_embedding_model

        storage = get_object_storage()
        milvus_client = get_milvus_client()
        with TemporaryDirectory(prefix=f"rag-{document.id}-") as directory:
            local_path = Path(directory) / document.original_name
            storage.download_file(document.object_key, str(local_path))
            chunk_count = asyncio.run(
                ingest_file(
                    file_path=str(local_path),
                    document_id=str(document.id),
                    knowledge_base_id=str(document.knowledge_base_id),
                    doc_name=document.original_name,
                    doc_type=document.doc_type,
                    category=document.category,
                    chunk_strategy=document.chunk_strategy,
                    embedding_model=get_embedding_model(),
                    milvus_client=milvus_client,
                )
            )
        _finish_ingestion_task(task.id, status="completed", chunk_count=chunk_count)
    except Exception as exc:
        _finish_ingestion_task(
            task.id,
            status="failed",
            error_message=str(exc)[:2000],
        )
