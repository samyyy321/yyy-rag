"""生产业务表的 SQLAlchemy 模型定义。

这里故意不声明 ForeignKey 或 ORM relationship，知识库、文档和导入任务
之间的关联由服务层在事务中校验和维护。
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import ClassVar
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Integer, BigInteger, String, Text, text
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utc_now() -> datetime:
    """返回当前 UTC 时间，并去除时区信息以匹配 PostgreSQL TIMESTAMP。"""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Base(DeclarativeBase):
    """所有生产业务表共用的 SQLAlchemy 声明式基类。"""


class KnowledgeBase(Base):
    """知识库主表模型，不声明数据库外键。"""

    __tablename__ = "knowledge_bases"
    __table_args__: ClassVar[dict[str, str]] = {"comment": "知识库主表"}

    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        comment="知识库唯一标识，UUID4",
    )
    name: Mapped[str] = mapped_column(
        String(100), nullable=False, comment="知识库名称"
    )
    description: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="知识库描述"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), nullable=False, default=utc_now, comment="创建时间，UTC"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), nullable=False, default=utc_now, comment="最后更新时间，UTC"
    )


class Document(Base):
    """文档元数据和导入状态模型，不声明知识库外键。"""

    __tablename__ = "documents"
    __table_args__: ClassVar[dict[str, str]] = {
        "comment": "文档主表，保存原始文件和导入状态"
    }

    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        comment="文档唯一标识，UUID4",
    )
    knowledge_base_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        nullable=False,
        index=True,
        comment="所属知识库唯一标识，由业务代码维护关联",
    )
    original_name: Mapped[str] = mapped_column(
        String(255), nullable=False, comment="上传时的原始文件名"
    )
    object_key: Mapped[str] = mapped_column(
        String(500), nullable=False, comment="MinIO 中的原始文件对象键"
    )
    content_type: Mapped[str | None] = mapped_column(
        String(100), nullable=True, comment="文件 MIME 类型"
    )
    file_size: Mapped[int] = mapped_column(
        BigInteger, nullable=False, comment="文件大小，单位为字节"
    )
    doc_type: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="文档类型，例如 pdf、docx、txt、md"
    )
    category: Mapped[str] = mapped_column(
        String(100), nullable=False, comment="文档分类"
    )
    status: Mapped[str] = mapped_column(
        String(30), nullable=False, comment="文档导入状态"
    )
    chunk_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
        comment="已写入 Milvus 的分块数量",
    )
    error_message: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="最近一次导入失败信息"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), nullable=False, default=utc_now, comment="创建时间，UTC"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), nullable=False, default=utc_now, comment="最后更新时间，UTC"
    )


class IngestionTask(Base):
    """文档导入任务模型，不声明文档外键。"""

    __tablename__ = "ingestion_tasks"
    __table_args__: ClassVar[dict[str, str]] = {"comment": "文档导入任务表"}

    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        comment="导入任务唯一标识，UUID4",
    )
    document_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        nullable=False,
        index=True,
        comment="被导入的文档唯一标识，由业务代码维护关联",
    )
    status: Mapped[str] = mapped_column(
        String(30), nullable=False, comment="导入任务状态"
    )
    error_message: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="导入失败信息"
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=False), nullable=True, comment="任务开始执行时间，UTC"
    )
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=False), nullable=True, comment="任务结束时间，UTC"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), nullable=False, default=utc_now, comment="任务创建时间，UTC"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), nullable=False, default=utc_now, comment="任务最后更新时间，UTC"
    )
