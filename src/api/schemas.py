"""FastAPI 请求、响应和校验模型。"""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

RetrievalChannel = Literal["document", "graph", "sql"]


class KnowledgeBaseCreate(BaseModel):
    """创建知识库请求。"""

    name: str = Field(min_length=1, max_length=100)
    description: str | None = None


class KnowledgeBaseUpdate(KnowledgeBaseCreate):
    """更新知识库请求。"""


class KnowledgeBaseResponse(BaseModel):
    """知识库响应。"""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    description: str | None
    created_at: datetime
    updated_at: datetime


class KnowledgeBaseListResponse(BaseModel):
    """知识库分页响应。"""

    items: list[KnowledgeBaseResponse]
    total: int
    skip: int
    limit: int


class DocumentResponse(BaseModel):
    """文档详情响应。"""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    knowledge_base_id: UUID
    original_name: str
    object_key: str
    content_type: str | None
    file_size: int
    doc_type: str
    category: str
    status: str
    chunk_count: int
    error_message: str | None
    created_at: datetime
    updated_at: datetime
    task_id: UUID | None = None
    task_status: str | None = None
    task_error_message: str | None = None
    task_started_at: datetime | None = None
    task_finished_at: datetime | None = None


class DocumentListResponse(BaseModel):
    """文档分页响应。"""

    items: list[DocumentResponse]
    total: int
    skip: int
    limit: int


class DocumentUploadResponse(BaseModel):
    """异步文档上传响应。"""

    document_id: UUID
    task_id: UUID
    status: Literal["pending"]


class ChatRequest(BaseModel):
    """按知识库执行 RAG 问答的请求。"""

    knowledge_base_id: UUID
    question: str = Field(min_length=1)
    role: str = "patient"
    top_k: int = Field(default=20, gt=0)
    rerank_top_k: int = Field(default=5, gt=0)
    use_hyde: bool = True
    channels: list[RetrievalChannel] = Field(
        default_factory=lambda: ["document"],
        min_length=1,
        max_length=3,
    )

    @model_validator(mode="after")
    def validate_rerank_limit(self) -> "ChatRequest":
        """保证重排数量不超过粗检索数量。"""
        if self.rerank_top_k > self.top_k:
            raise ValueError("rerank_top_k 不能大于 top_k")
        if len(set(self.channels)) != len(self.channels):
            raise ValueError("channels 不能包含重复通道")
        return self


class ChatSource(BaseModel):
    """RAG 回答来源片段。"""

    document_id: UUID
    document_name: str
    page_number: int
    chunk_index: int
    score: float
    text: str


class ChatResponse(BaseModel):
    """RAG 回答和来源响应。"""

    answer: str
    sources: list[ChatSource]


class HealthResponse(BaseModel):
    """服务健康状态响应。"""

    status: Literal["ok", "unhealthy"]
