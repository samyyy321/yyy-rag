import asyncio
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from src.query.channel_types import ChannelEvidence


@pytest.mark.asyncio
async def test_collect_evidence_uses_direct_call_for_single_channel(monkeypatch):
    """单通道不应启动无关通道或调用 asyncio.gather。"""
    from src.query import multi_channel

    document = AsyncMock(
        return_value=ChannelEvidence(channel="document", content="文档证据")
    )
    monkeypatch.setattr(multi_channel, "retrieve_document_evidence", document)

    async def unexpected_gather(*_tasks, **_kwargs):
        raise AssertionError("单通道不应调用 asyncio.gather")

    monkeypatch.setattr(multi_channel.asyncio, "gather", unexpected_gather)

    evidence = await multi_channel.collect_evidence(
        ["document"],
        knowledge_base_id=uuid4(),
        question="问题",
        top_k=20,
        rerank_top_k=5,
        use_hyde=True,
        db=object(),
        embedding_model=object(),
        milvus_client=object(),
        llm=object(),
    )

    assert evidence == [ChannelEvidence(channel="document", content="文档证据")]
    document.assert_awaited_once()


@pytest.mark.asyncio
async def test_collect_evidence_gathers_multiple_channels_and_keeps_success(monkeypatch):
    """多通道并发时，一个通道失败不应丢弃其他成功证据。"""
    from src.query import multi_channel

    document = AsyncMock(
        return_value=ChannelEvidence(channel="document", content="文档证据")
    )
    graph = AsyncMock(side_effect=RuntimeError("图谱暂不可用"))
    monkeypatch.setattr(multi_channel, "retrieve_document_evidence", document)
    monkeypatch.setattr(multi_channel, "retrieve_graph_evidence", graph)

    original_gather = asyncio.gather
    gather_calls = 0

    async def tracked_gather(*tasks, **kwargs):
        nonlocal gather_calls
        gather_calls += 1
        return await original_gather(*tasks, **kwargs)

    monkeypatch.setattr(multi_channel.asyncio, "gather", tracked_gather)

    evidence = await multi_channel.collect_evidence(
        ["document", "graph"],
        knowledge_base_id=uuid4(),
        question="问题",
        top_k=20,
        rerank_top_k=5,
        use_hyde=True,
        db=object(),
        embedding_model=object(),
        milvus_client=object(),
        llm=object(),
    )

    assert gather_calls == 1
    assert evidence == [ChannelEvidence(channel="document", content="文档证据")]
    document.assert_awaited_once()
    graph.assert_awaited_once()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("channel", "expected_text"),
    [
        ("document", "检索到的文档片段"),
        ("graph", "图谱查询结果"),
        ("sql", "执行的 SQL"),
    ],
)
async def test_generate_channel_answer_uses_single_channel_prompt(channel, expected_text):
    """每个单通道应选择自己的回答提示词。"""
    from src.query import multi_channel

    class FakeLlm:
        async def ainvoke(self, messages):
            self.prompt = messages[0].content
            return type("Response", (), {"content": "回答"})()

    llm = FakeLlm()
    answer = await multi_channel.generate_channel_answer(
        question="问题",
        role="patient",
        evidence=[ChannelEvidence(channel=channel, content="证据")],
        llm=llm,
    )

    assert answer == "回答"
    assert expected_text in llm.prompt


@pytest.mark.asyncio
async def test_generate_channel_answer_uses_fusion_prompt_for_multiple_channels():
    """多个成功通道应通过融合提示词生成最终答案。"""
    from src.query import multi_channel

    class FakeLlm:
        async def ainvoke(self, messages):
            self.prompt = messages[0].content
            return type("Response", (), {"content": "融合回答"})()

    llm = FakeLlm()
    answer = await multi_channel.generate_channel_answer(
        question="问题",
        role="patient",
        evidence=[
            ChannelEvidence(channel="document", content="文档证据"),
            ChannelEvidence(channel="graph", content="图谱证据"),
        ],
        llm=llm,
    )

    assert answer == "融合回答"
    assert "综合以下多个来源的检索结果" in llm.prompt
