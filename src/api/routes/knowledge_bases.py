"""知识库 CRUD 路由。"""

from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from src.api.dependencies import get_database
from src.api.schemas import (
    KnowledgeBaseCreate,
    KnowledgeBaseListResponse,
    KnowledgeBaseResponse,
    KnowledgeBaseUpdate,
)
from src.services import knowledge_base_service

router = APIRouter(prefix="/knowledge-bases", tags=["knowledge-bases"])


@router.post("", response_model=KnowledgeBaseResponse, status_code=status.HTTP_201_CREATED)
def create_knowledge_base(
    payload: KnowledgeBaseCreate,
    db: Session = Depends(get_database),
) -> KnowledgeBaseResponse:
    """创建知识库。"""
    item = knowledge_base_service.create_knowledge_base(
        db, name=payload.name, description=payload.description
    )
    return KnowledgeBaseResponse.model_validate(item)


@router.get("", response_model=KnowledgeBaseListResponse)
def list_knowledge_bases(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, gt=0, le=100),
    db: Session = Depends(get_database),
) -> KnowledgeBaseListResponse:
    """分页查询知识库。"""
    items, total = knowledge_base_service.list_knowledge_bases(
        db, skip=skip, limit=limit
    )
    return KnowledgeBaseListResponse(
        items=[KnowledgeBaseResponse.model_validate(item) for item in items],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("/{knowledge_base_id}", response_model=KnowledgeBaseResponse)
def get_knowledge_base(
    knowledge_base_id: UUID,
    db: Session = Depends(get_database),
) -> KnowledgeBaseResponse:
    """查询单个知识库。"""
    item = knowledge_base_service.get_knowledge_base(db, knowledge_base_id)
    return KnowledgeBaseResponse.model_validate(item)


@router.put("/{knowledge_base_id}", response_model=KnowledgeBaseResponse)
def update_knowledge_base(
    knowledge_base_id: UUID,
    payload: KnowledgeBaseUpdate,
    db: Session = Depends(get_database),
) -> KnowledgeBaseResponse:
    """更新知识库名称和描述。"""
    item = knowledge_base_service.update_knowledge_base(
        db,
        knowledge_base_id,
        name=payload.name,
        description=payload.description,
    )
    return KnowledgeBaseResponse.model_validate(item)


@router.delete("/{knowledge_base_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_knowledge_base(
    knowledge_base_id: UUID,
    db: Session = Depends(get_database),
) -> Response:
    """删除没有任何文档的知识库。"""
    knowledge_base_service.delete_knowledge_base(db, knowledge_base_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
