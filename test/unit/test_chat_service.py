from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from src.services.chat_service import answer_question, check_health


@pytest.mark.asyncio
async def test_answer_question_passes_knowledge_base_id_to_rag_search(monkeypatch):
    kb_id = uuid4()
    doc_id = uuid4()
    db = Mock()
    result = Mock()
    result.scalar_one_or_none.return_value = Mock(id=kb_id)
    db.execute.return_value = result
    search = AsyncMock(return_value=[{
        "knowledge_base_id": str(kb_id),
        "doc_id": str(doc_id),
        "doc_name": "a.txt",
        "page_number": 0,
        "chunk_index": 0,
        "text": "evidence",
        "score": 0.9,
    }])
    generate = AsyncMock(return_value="answer")
    monkeypatch.setattr("src.services.chat_service.search_docs_raw", search)
    monkeypatch.setattr("src.services.chat_service.generate_answer", generate)

    result = await answer_question(
        knowledge_base_id=kb_id,
        question="问题",
        role="patient",
        top_k=20,
        rerank_top_k=5,
        use_hyde=True,
        db=db,
        embedding_model=Mock(),
        milvus_client=Mock(),
        llm=Mock(),
    )

    assert result.answer == "answer"
    assert search.await_args.kwargs["knowledge_base_id"] == str(kb_id)
    assert result.sources[0].document_id == doc_id


def test_check_health_returns_false_when_dependency_fails():
    db = Mock()
    db.execute.side_effect = RuntimeError("database unavailable")
    assert check_health(db, Mock(), Mock()) is False
