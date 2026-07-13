"""为 documents 增加文本切分策略字段。"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260915_203753_chunk_strategy"
down_revision: Union[str, None] = "20260911_160524_rag_business"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """为已有和新增文档持久化导入时选择的切分策略。"""
    op.add_column(
        "documents",
        sa.Column(
            "chunk_strategy",
            sa.String(length=30),
            server_default=sa.text("'recursive'"),
            nullable=False,
        ),
    )
    op.execute(
        "COMMENT ON COLUMN documents.chunk_strategy "
        "IS '文档导入时使用的文本切分策略'"
    )


def downgrade() -> None:
    """删除文档切分策略字段。"""
    op.drop_column("documents", "chunk_strategy")