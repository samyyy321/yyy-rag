"""文档上传、查询和删除路由。"""

from io import BytesIO
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, UploadFile, status
from sqlalchemy.orm import Session

from src.api.dependencies import get_database, get_milvus, get_storage
from src.api.schemas import (
    ChunkStrategy,
    DocumentListResponse,
    DocumentResponse,
    DocumentUploadResponse,
)
from src.infra.minio_client import ObjectStorage
from src.services import document_service

router = APIRouter(tags=["documents"])
_SUPPORTED_TYPES = {"pdf", "docx", "txt", "md"}


def _document_response(document, task=None) -> DocumentResponse:
    """将文档模型和最新任务转换为 API 响应。"""
    values = {
        "id": document.id,
        "knowledge_base_id": document.knowledge_base_id,
        "original_name": document.original_name,
        "object_key": document.object_key,
        "content_type": document.content_type,
        "file_size": document.file_size,
        "doc_type": document.doc_type,
        "category": document.category,
        "chunk_strategy": document.chunk_strategy,
        "status": document.status,
        "chunk_count": document.chunk_count,
        "error_message": document.error_message,
        "created_at": document.created_at,
        "updated_at": document.updated_at,
    }
    if task is not None:
        values.update(
            task_id=task.id,
            task_status=task.status,
            task_error_message=task.error_message,
            task_started_at=task.started_at,
            task_finished_at=task.finished_at,
        )
    return DocumentResponse(**values)


@router.post(
    "/api/v1/knowledge-bases/{knowledge_base_id}/documents",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def upload_document(
    knowledge_base_id: UUID,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    category: str = Form(default="default"),
    chunk_strategy: ChunkStrategy = Form(default="recursive"),
    db: Session = Depends(get_database),
    storage: ObjectStorage = Depends(get_storage),
) -> DocumentUploadResponse:
    """上传原始文档并在事务提交后注册后台导入任务。"""
    original_name = file.filename or "unnamed"
    suffix = Path(original_name.replace("\\", "/")).suffix.lower().lstrip(".")
    if suffix not in _SUPPORTED_TYPES:
        from fastapi import HTTPException

        raise HTTPException(status_code=422, detail="不支持的文档类型")
    content = await file.read()
    document, task = document_service.create_document(
        db,
        storage,
        knowledge_base_id=knowledge_base_id,
        original_name=original_name,
        content_type=file.content_type,
        file_size=len(content),
        doc_type=suffix,
        category=category,
        chunk_strategy=chunk_strategy,
        fileobj=BytesIO(content),
    )
    background_tasks.add_task(document_service.run_ingestion_task, task.id)
    return DocumentUploadResponse(
        document_id=document.id,
        task_id=task.id,
        status="pending",
    )


@router.get(
    "/api/v1/knowledge-bases/{knowledge_base_id}/documents",
    response_model=DocumentListResponse,
)
def list_documents(
    knowledge_base_id: UUID,
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_database),
) -> DocumentListResponse:
    """按知识库分页查询文档。"""
    items, total = document_service.list_documents(
        db, knowledge_base_id=knowledge_base_id, skip=skip, limit=limit
    )
    return DocumentListResponse(
        items=[_document_response(item) for item in items],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("/api/v1/documents/{document_id}", response_model=DocumentResponse)
def get_document(
    document_id: UUID,
    db: Session = Depends(get_database),
) -> DocumentResponse:
    """查询文档及最新导入任务状态。"""
    document, task = document_service.get_document_with_task(db, document_id)
    return _document_response(document, task)


@router.delete("/api/v1/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(
    document_id: UUID,
    db: Session = Depends(get_database),
    storage: ObjectStorage = Depends(get_storage),
    milvus=Depends(get_milvus),
):
    """删除已完成或已失败的文档及其外部存储。"""
    document_service.delete_document(db, storage, milvus, document_id)
    from fastapi import Response

    return Response(status_code=status.HTTP_204_NO_CONTENT)
