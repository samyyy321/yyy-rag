"""创建知识库、文档和导入任务业务表。"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20260911_160524_rag_business"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """创建没有数据库外键的生产业务表，并写入完整中文注释。"""
    op.create_table(
        "knowledge_bases",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=False), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=False), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("knowledge_base_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("original_name", sa.String(length=255), nullable=False),
        sa.Column("object_key", sa.String(length=500), nullable=False),
        sa.Column("content_type", sa.String(length=100), nullable=True),
        sa.Column("file_size", sa.BigInteger(), nullable=False),
        sa.Column("doc_type", sa.String(length=50), nullable=False),
        sa.Column("category", sa.String(length=100), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("chunk_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=False), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=False), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "ingestion_tasks",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=False), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=False), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=False), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=False), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_documents_knowledge_base_id", "documents", ["knowledge_base_id"])
    op.create_index("ix_ingestion_tasks_document_id", "ingestion_tasks", ["document_id"])
    _comment_tables_and_columns()


def _comment_tables_and_columns() -> None:
    """为三张业务表及其全部字段写入 PostgreSQL 中文注释。"""
    table_comments = {
        "knowledge_bases": {
            "id": "知识库唯一标识，UUID4",
            "name": "知识库名称",
            "description": "知识库描述",
            "created_at": "创建时间，UTC",
            "updated_at": "最后更新时间，UTC",
        },
        "documents": {
            "id": "文档唯一标识，UUID4",
            "knowledge_base_id": "所属知识库唯一标识，由业务代码维护关联",
            "original_name": "上传时的原始文件名",
            "object_key": "MinIO 中的原始文件对象键",
            "content_type": "文件 MIME 类型",
            "file_size": "文件大小，单位为字节",
            "doc_type": "文档类型，例如 pdf、docx、txt、md",
            "category": "文档分类",
            "status": "文档导入状态",
            "chunk_count": "已写入 Milvus 的分块数量",
            "error_message": "最近一次导入失败信息",
            "created_at": "创建时间，UTC",
            "updated_at": "最后更新时间，UTC",
        },
        "ingestion_tasks": {
            "id": "导入任务唯一标识，UUID4",
            "document_id": "被导入的文档唯一标识，由业务代码维护关联",
            "status": "导入任务状态",
            "error_message": "导入失败信息",
            "started_at": "任务开始执行时间，UTC",
            "finished_at": "任务结束时间，UTC",
            "created_at": "任务创建时间，UTC",
            "updated_at": "任务最后更新时间，UTC",
        },
    }
    op.execute("COMMENT ON TABLE knowledge_bases IS '知识库主表'")
    op.execute("COMMENT ON TABLE documents IS '文档主表，保存原始文件和导入状态'")
    op.execute("COMMENT ON TABLE ingestion_tasks IS '文档导入任务表'")
    for table_name, columns in table_comments.items():
        for column_name, comment in columns.items():
            escaped_comment = comment.replace("'", "''")
            op.execute(
                f"COMMENT ON COLUMN {table_name}.{column_name} "
                f"IS '{escaped_comment}'"
            )


def downgrade() -> None:
    """按依赖的逆序删除业务表和索引。"""
    op.drop_index("ix_ingestion_tasks_document_id", table_name="ingestion_tasks")
    op.drop_index("ix_documents_knowledge_base_id", table_name="documents")
    op.drop_table("ingestion_tasks")
    op.drop_table("documents")
    op.drop_table("knowledge_bases")

