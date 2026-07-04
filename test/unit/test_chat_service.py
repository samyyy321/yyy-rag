from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from src.query.channel_types import ChannelEvidence
from src.services.chat_service import answer_question, check_health, stream_answer


@pytest.mark.asyncio
async def test_answer_question_collects_selected_channels_and_preserves_document_sources(
    monkeypatch,
):
    """非流式问答应交给通道编排，并保留文档通道原有来源响应。"""
    kb_id = uuid4()
    doc_id = uuid4()
    db = Mock()
    result = Mock()
    result.scalar_one_or_none.return_value = Mock(id=kb_id)
    db.execute.return_value = result
    evidence = ChannelEvidence(
        channel="document",
        content="文档证据",
        records=(
            {
                "doc_id": str(doc_id),
                "doc_name": "a.txt",
                "page_number": 0,
                "chunk_index": 0,
                "text": "evidence",
                "score": 0.9,
            },
        ),
    )
    collect = AsyncMock(return_value=[evidence])
    generate = AsyncMock(return_value="answer")
    monkeypatch.setattr("src.services.chat_service.collect_evidence", collect)
    monkeypatch.setattr("src.services.chat_service.generate_channel_answer", generate)

    response = await answer_question(
        knowledge_base_id=kb_id,
        question="问题",
        role="patient",
        top_k=20,
        rerank_top_k=5,
        use_hyde=True,
        channels=["document"],
        db=db,
        embedding_model=Mock(),
        milvus_client=Mock(),
        llm=Mock(),
    )

    assert response.answer == "answer"
    assert collect.await_args.args[0] == ["document"]
    assert response.sources[0].document_id == doc_id


@pytest.mark.asyncio
async def test_stream_answer_uses_selected_channels_before_yielding_model_chunks(monkeypatch):
    """流式问答应使用相同通道编排，再按模型顺序输出分片。"""
    kb_id = uuid4()
    db = Mock()
    result = Mock()
    result.scalar_one_or_none.return_value = Mock(id=kb_id)
    db.execute.return_value = result
    collect = AsyncMock(
        return_value=[ChannelEvidence(channel="graph", content="图谱证据")]
    )
    monkeypatch.setattr("src.services.chat_service.collect_evidence", collect)
    monkeypatch.setattr(
        "src.services.chat_service.build_answer_prompt",
        lambda **_kwargs: "融合后的提示词",
    )

    class StreamingLlm:
        """提供可预测分片的最小流式模型替身。"""

        async def astream(self, _messages):
            yield Mock(content="流式")
            yield Mock(content="回答")

    chunks = [
        chunk
        async for chunk in stream_answer(
            knowledge_base_id=kb_id,
            question="问题",
            role="patient",
            top_k=20,
            rerank_top_k=5,
            use_hyde=True,
            channels=["graph"],
            db=db,
            embedding_model=Mock(),
            milvus_client=Mock(),
            llm=StreamingLlm(),
        )
    ]

    assert chunks == ["流式", "回答"]
    assert collect.await_args.args[0] == ["graph"]


def test_check_health_returns_false_when_dependency_fails():
    """任一基础依赖异常时健康检查返回 false。"""
    db = Mock()
    db.execute.side_effect = RuntimeError("database unavailable")

    assert check_health(db, Mock(), Mock()) is False
@pytest.mark.asyncio
async def test_answer_question_skips_knowledge_base_lookup_for_graph_only(monkeypatch):
    """纯图谱问答不应访问文档知识库表。"""
    db = Mock()
    collect = AsyncMock(
        return_value=[ChannelEvidence(channel="graph", content="图谱证据")]
    )
    generate = AsyncMock(return_value="图谱回答")
    monkeypatch.setattr("src.services.chat_service.collect_evidence", collect)
    monkeypatch.setattr("src.services.chat_service.generate_channel_answer", generate)

    response = await answer_question(
        knowledge_base_id=None,
        question="图谱问题",
        role="patient",
        top_k=20,
        rerank_top_k=5,
        use_hyde=True,
        channels=["graph"],
        db=db,
        embedding_model=None,
        milvus_client=None,
        llm=Mock(),
    )

    assert response.answer == "图谱回答"
    assert response.sources == []
    db.execute.assert_not_called()
    assert collect.await_args.kwargs["knowledge_base_id"] is None
