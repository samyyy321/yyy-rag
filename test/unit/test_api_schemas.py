from datetime import datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from src.api.schemas import ChatRequest, DocumentResponse, KnowledgeBaseCreate


def test_knowledge_base_name_is_required_and_limited():
    with pytest.raises(ValidationError):
        KnowledgeBaseCreate(name="", description=None)
    with pytest.raises(ValidationError):
        KnowledgeBaseCreate(name="a" * 101, description=None)


def test_chat_requires_knowledge_base_and_question():
    with pytest.raises(ValidationError):
        ChatRequest(question="问题")
    with pytest.raises(ValidationError):
        ChatRequest(knowledge_base_id=uuid4(), question="")


def test_chat_rerank_top_k_cannot_exceed_top_k():
    with pytest.raises(ValidationError):
        ChatRequest(
            knowledge_base_id=uuid4(), question="问题", top_k=5, rerank_top_k=6
        )


def test_document_response_requires_valid_chunk_strategy():
    """文档 API 响应必须包含受限的切分策略。"""
    values = {
        "id": uuid4(),
        "knowledge_base_id": uuid4(),
        "original_name": "a.md",
        "object_key": "documents/a/a.md",
        "content_type": "text/markdown",
        "file_size": 10,
        "doc_type": "md",
        "category": "default",
        "status": "completed",
        "chunk_count": 1,
        "error_message": None,
        "created_at": datetime.now(),
        "updated_at": datetime.now(),
    }

    response = DocumentResponse(**values, chunk_strategy="semantic")
    assert response.chunk_strategy == "semantic"

    with pytest.raises(ValidationError):
        DocumentResponse(**values, chunk_strategy="unknown")
