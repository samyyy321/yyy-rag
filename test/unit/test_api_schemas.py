from uuid import uuid4

import pytest
from pydantic import ValidationError

from src.api.schemas import ChatRequest, KnowledgeBaseCreate


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
