"""知识库 CRUD 服务和无外键业务校验。"""

from __future__ import annotations

from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.db.models import Document, KnowledgeBase, utc_now
from src.services.errors import ResourceConflictError, ResourceNotFoundError


def _get_knowledge_base_for_update(db: Session, knowledge_base_id: UUID) -> KnowledgeBase:
    """锁定知识库行并校验其存在，供需要并发保护的写操作复用。"""
    knowledge_base = db.execute(
        select(KnowledgeBase)
        .where(KnowledgeBase.id == knowledge_base_id)
        .with_for_update()
    ).scalar_one_or_none()
    if knowledge_base is None:
        raise ResourceNotFoundError("知识库不存在")
    return knowledge_base


def create_knowledge_base(
    db: Session,
    *,
    name: str,
    description: str | None,
) -> KnowledgeBase:
    """创建知识库并提交事务。"""
    now = utc_now()
    knowledge_base = KnowledgeBase(
        id=uuid4(),
        name=name,
        description=description,
        created_at=now,
        updated_at=now,
    )
    try:
        db.add(knowledge_base)
        db.commit()
        db.refresh(knowledge_base)
        return knowledge_base
    except Exception:
        db.rollback()
        raise


def list_knowledge_bases(
    db: Session,
    *,
    skip: int,
    limit: int,
) -> tuple[list[KnowledgeBase], int]:
    """按创建时间倒序分页返回知识库。"""
    total = db.execute(select(func.count()).select_from(KnowledgeBase)).scalar_one()
    items = list(
        db.execute(
            select(KnowledgeBase)
            .order_by(KnowledgeBase.created_at.desc())
            .offset(skip)
            .limit(limit)
        ).scalars()
    )
    return items, total


def get_knowledge_base(db: Session, knowledge_base_id: UUID) -> KnowledgeBase:
    """读取知识库，不加锁。"""
    knowledge_base = db.execute(
        select(KnowledgeBase).where(KnowledgeBase.id == knowledge_base_id)
    ).scalar_one_or_none()
    if knowledge_base is None:
        raise ResourceNotFoundError("知识库不存在")
    return knowledge_base


def update_knowledge_base(
    db: Session,
    knowledge_base_id: UUID,
    *,
    name: str,
    description: str | None,
) -> KnowledgeBase:
    """锁定并更新知识库基本信息。"""
    try:
        knowledge_base = _get_knowledge_base_for_update(db, knowledge_base_id)
        knowledge_base.name = name
        knowledge_base.description = description
        knowledge_base.updated_at = utc_now()
        db.commit()
        db.refresh(knowledge_base)
        return knowledge_base
    except Exception:
        db.rollback()
        raise


def delete_knowledge_base(db: Session, knowledge_base_id: UUID) -> None:
    """锁定知识库并阻止删除仍有文档的知识库。"""
    try:
        knowledge_base = _get_knowledge_base_for_update(db, knowledge_base_id)
        count = db.execute(
            select(func.count())
            .select_from(Document)
            .where(Document.knowledge_base_id == knowledge_base_id)
        ).scalar_one()
        if count > 0:
            raise ResourceConflictError("知识库下存在文档，不能删除")
        db.delete(knowledge_base)
        db.commit()
    except Exception:
        db.rollback()
        raise
